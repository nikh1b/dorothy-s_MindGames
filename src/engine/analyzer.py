"""
Dorothy's Mind Games - Stockfish Analyzer
==========================================
Asynchronous chess engine integration via UCI protocol.

Runs Stockfish in a background thread, continuously analysing
the current board position. Results are pushed into a thread-safe
queue that the main loop can poll without blocking rendering.
"""

from __future__ import annotations

import subprocess
import threading
import time
from dataclasses import dataclass, field
from queue import Empty, Queue
from typing import Optional

import chess

from src.core.constants import (
    BLUNDER_THRESHOLD_CP,
    INACCURACY_THRESHOLD_CP,
    MISTAKE_THRESHOLD_CP,
    STOCKFISH_ANALYSIS_DEPTH,
    STOCKFISH_DEFAULT_DEPTH,
    STOCKFISH_PATH,
)


# ── Data Structures ─────────────────────────────────────────────────
@dataclass
class AnalysisResult:
    """Snapshot of engine evaluation at a given depth."""
    depth: int = 0
    score_cp: int = 0            # centipawns from White's perspective
    score_mate: int | None = None  # mate-in-N (positive = White wins)
    best_move: str = ""          # UCI string e.g. "e2e4"
    pv: list[str] = field(default_factory=list)  # principal variation
    nodes: int = 0
    nps: int = 0
    is_mate: bool = False

    @property
    def display_eval(self) -> str:
        if self.is_mate and self.score_mate is not None:
            return f"M{self.score_mate}"
        return f"{self.score_cp / 100:+.2f}"


@dataclass
class MoveClassification:
    """How good was the player's move compared to the engine's best?"""
    uci_move: str
    eval_before: int  # cp before the move
    eval_after: int   # cp after the move
    cp_loss: int      # absolute centipawn loss
    label: str        # "brilliant", "best", "good", "inaccuracy", "mistake", "blunder"
    is_blunder: bool = False

    @staticmethod
    def classify(cp_loss: int) -> str:
        if cp_loss <= 0:
            return "brilliant"
        elif cp_loss <= 10:
            return "best"
        elif cp_loss < INACCURACY_THRESHOLD_CP:
            return "good"
        elif cp_loss < MISTAKE_THRESHOLD_CP:
            return "inaccuracy"
        elif cp_loss < BLUNDER_THRESHOLD_CP:
            return "mistake"
        else:
            return "blunder"


# ── Stockfish Analyzer ──────────────────────────────────────────────
class StockfishAnalyzer:
    """Manages a Stockfish subprocess and provides non-blocking analysis.

    Usage::

        analyzer = StockfishAnalyzer()
        analyzer.start()
        analyzer.set_position(board.fen())
        ...
        result = analyzer.get_latest()
        ...
        analyzer.stop()
    """

    def __init__(self, path: str = STOCKFISH_PATH, depth: int = STOCKFISH_DEFAULT_DEPTH) -> None:
        self._path = path
        self._depth = depth
        self._process: subprocess.Popen | None = None
        self._thread: threading.Thread | None = None
        self._queue: Queue[AnalysisResult] = Queue(maxsize=64)
        self._running = threading.Event()
        self._new_position = threading.Event()
        self._lock = threading.Lock()
        self._current_fen: str = chess.STARTING_FEN
        self._latest: AnalysisResult = AnalysisResult()
        self._available: bool = False

    # ── Lifecycle ───────────────────────────────────────────────────
    def start(self) -> bool:
        """Launch the Stockfish process and reader thread.
        Returns True if engine started successfully."""
        try:
            self._process = subprocess.Popen(
                [self._path],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
                text=True,
                bufsize=1,
            )
            self._send("uci")
            # Wait for "uciok"
            deadline = time.time() + 5.0
            while time.time() < deadline:
                line = self._process.stdout.readline().strip()  # type: ignore[union-attr]
                if line == "uciok":
                    break
            else:
                self._kill()
                return False

            self._send("isready")
            deadline = time.time() + 5.0
            while time.time() < deadline:
                line = self._process.stdout.readline().strip()  # type: ignore[union-attr]
                if line == "readyok":
                    break

            self._available = True
            self._running.set()
            self._thread = threading.Thread(target=self._analysis_loop, daemon=True)
            self._thread.start()
            return True

        except FileNotFoundError:
            print(f"[Analyzer] Stockfish not found at '{self._path}'. "
                  "AI analysis will be disabled.")
            self._available = False
            return False
        except Exception as exc:
            print(f"[Analyzer] Failed to start Stockfish: {exc}")
            self._available = False
            return False

    def stop(self) -> None:
        """Gracefully shut down the engine."""
        self._running.clear()
        self._new_position.set()  # unblock the thread if waiting
        if self._process:
            self._send("quit")
            try:
                self._process.wait(timeout=3)
            except subprocess.TimeoutExpired:
                self._kill()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=2)

    @property
    def is_available(self) -> bool:
        return self._available

    # ── Position Control ────────────────────────────────────────────
    def set_position(self, fen: str) -> None:
        """Update the position the engine should analyse."""
        with self._lock:
            self._current_fen = fen
        self._new_position.set()

    # ── Results ─────────────────────────────────────────────────────
    def get_latest(self) -> AnalysisResult:
        """Return the most recent analysis result (non-blocking)."""
        # Drain the queue and keep only the freshest result.
        latest = self._latest
        try:
            while True:
                latest = self._queue.get_nowait()
        except Empty:
            pass
        self._latest = latest
        return latest

    def classify_move(
        self, eval_before_cp: int, eval_after_cp: int, uci_move: str, player_is_white: bool
    ) -> MoveClassification:
        """Classify a player move by comparing evaluations."""
        # Normalise to the player's perspective
        if player_is_white:
            loss = eval_before_cp - eval_after_cp
        else:
            loss = eval_after_cp - eval_before_cp  # from Black's view, lower is better
        loss = max(0, loss)
        label = MoveClassification.classify(loss)
        return MoveClassification(
            uci_move=uci_move,
            eval_before=eval_before_cp,
            eval_after=eval_after_cp,
            cp_loss=loss,
            label=label,
            is_blunder=(loss >= BLUNDER_THRESHOLD_CP),
        )

    # ── Internal ────────────────────────────────────────────────────
    def _send(self, command: str) -> None:
        if self._process and self._process.stdin:
            self._process.stdin.write(command + "\n")
            self._process.stdin.flush()

    def _kill(self) -> None:
        if self._process:
            try:
                self._process.kill()
            except OSError:
                pass
            self._process = None

    def _analysis_loop(self) -> None:
        """Background thread: continuously analyse positions."""
        while self._running.is_set():
            self._new_position.wait(timeout=0.5)
            self._new_position.clear()

            if not self._running.is_set():
                break

            with self._lock:
                fen = self._current_fen

            # Stop any in-progress search and start a new one
            self._send("stop")
            self._send(f"position fen {fen}")
            self._send(f"go depth {self._depth}")

            # Read engine output until "bestmove"
            result = AnalysisResult()
            while self._running.is_set():
                if not self._process or not self._process.stdout:
                    break
                line = self._process.stdout.readline().strip()
                if not line:
                    continue

                if line.startswith("info depth"):
                    result = self._parse_info(line)
                    # Push intermediate results so UI stays responsive
                    if not self._queue.full():
                        self._queue.put(result)

                elif line.startswith("bestmove"):
                    tokens = line.split()
                    if len(tokens) >= 2:
                        result.best_move = tokens[1]
                    if not self._queue.full():
                        self._queue.put(result)
                    break

    @staticmethod
    def _parse_info(line: str) -> AnalysisResult:
        """Parse a UCI ``info`` line into an AnalysisResult."""
        tokens = line.split()
        result = AnalysisResult()
        i = 0
        while i < len(tokens):
            tok = tokens[i]
            if tok == "depth" and i + 1 < len(tokens):
                result.depth = int(tokens[i + 1])
                i += 2
            elif tok == "score" and i + 2 < len(tokens):
                kind = tokens[i + 1]
                val = int(tokens[i + 2])
                if kind == "cp":
                    result.score_cp = val
                    result.is_mate = False
                elif kind == "mate":
                    result.score_mate = val
                    result.is_mate = True
                    result.score_cp = 30000 if val > 0 else -30000
                i += 3
            elif tok == "nodes" and i + 1 < len(tokens):
                result.nodes = int(tokens[i + 1])
                i += 2
            elif tok == "nps" and i + 1 < len(tokens):
                result.nps = int(tokens[i + 1])
                i += 2
            elif tok == "pv":
                result.pv = tokens[i + 1:]
                if result.pv:
                    result.best_move = result.pv[0]
                break
            else:
                i += 1
        return result
