"""
Dorothy's Mind Games - Limbo State
====================================
The monochromatic, high-pressure puzzle dimension that Dorothy
enters after committing a Blunder.

The player must solve N tactical puzzles within a time limit
to escape.  Failure means Game Over (Hell).
"""

from __future__ import annotations

import random
import time
from typing import TYPE_CHECKING, Optional

import chess
import pygame

from src.core.constants import (
    BOARD_ORIGIN_X,
    BOARD_ORIGIN_Y,
    BOARD_PIXEL_SIZE,
    COLOR_ACCENT,
    COLOR_BG,
    COLOR_DANGER,
    COLOR_TEXT,
    COLOR_TEXT_DIM,
    LIMBO_PUZZLE_TIME_LIMIT,
    LIMBO_PUZZLES_REQUIRED,
    SCREEN_HEIGHT,
    SCREEN_WIDTH,
    SQUARE_SIZE,
)
from src.ui.renderer import BoardRenderer

if TYPE_CHECKING:
    from src.core.state_manager import StateManager
    from src.states.game_state import ChessGameState


# ── Puzzle Bank ─────────────────────────────────────────────────────
# Each tuple: (FEN, solution_moves_uci)
# Solutions are the winning sequence from the player's perspective.
PUZZLE_BANK: list[tuple[str, list[str]]] = [
    # Mate in 1
    ("6k1/5ppp/8/8/8/8/5PPP/4R1K1 w - - 0 1", ["e1e8"]),
    ("r1bqkb1r/pppp1ppp/2n2n2/4p2Q/2B1P3/8/PPPP1PPP/RNB1K1NR w KQkq - 0 1", ["h5f7"]),
    ("rnb1kbnr/pppp1ppp/8/4p3/6Pq/5P2/PPPPP2P/RNBQKBNR b KQkq - 0 1", ["h4e1"]),
    # Mate in 2
    ("2bqkbn1/2pppp2/np2N3/r3P1p1/p2N2B1/5Q2/PPPPPP1P/RNB1K2R w KQ - 0 1", ["f3f7"]),
    ("r2qk2r/pb4pp/1n2Pb2/2B2Q2/p1p5/2P5/PP2B1PP/RN2K2R w KQkq - 0 1", ["f5g6"]),
    # Tactical: fork / pin
    ("r1bqkbnr/pppppppp/2n5/8/4P3/5N2/PPPP1PPP/RNBQKB1R b KQkq - 0 1", ["d7d5"]),
    ("rnbqkb1r/ppp1pppp/5n2/3p4/3P1B2/5N2/PPP1PPPP/RN1QKB1R b KQkq - 0 1", ["c7c5"]),
    # Endgame technique
    ("8/8/8/8/8/5K2/4Q3/7k w - - 0 1", ["f3f2"]),
    ("8/8/8/8/1k6/8/1K1R4/8 w - - 0 1", ["d2d1"]),
]


class LimboState:
    """The Limbo nightmare dimension — solve puzzles to escape."""

    def __init__(
        self,
        state_manager: "StateManager",
        game_state: "ChessGameState",
        return_fen: str,
    ) -> None:
        self._sm = state_manager
        self._game_state = game_state
        self._return_fen = return_fen

        # ── Puzzle state ────────────────────────────────────────────
        self._puzzles: list[tuple[str, list[str]]] = []
        self._current_puzzle_idx: int = 0
        self._puzzle_board: chess.Board = chess.Board()
        self._solution_moves: list[str] = []
        self._solution_step: int = 0
        self._puzzles_solved: int = 0

        # ── Interaction ─────────────────────────────────────────────
        self._selected_sq: int | None = None
        self._legal_moves: list[chess.Move] = []

        # ── Timer ───────────────────────────────────────────────────
        self._time_remaining: float = LIMBO_PUZZLE_TIME_LIMIT
        self._total_time: float = LIMBO_PUZZLE_TIME_LIMIT

        # ── Visual ──────────────────────────────────────────────────
        self._renderer = BoardRenderer()
        self._flash_timer: float = 0.0
        self._shake_offset: tuple[int, int] = (0, 0)
        self._noise_intensity: float = 0.5
        self._transition_alpha: float = 255.0  # fade in from black
        self._time: float = 0.0
        self._failed: bool = False
        self._escaped: bool = False
        self._result_timer: float = 0.0

    # ── Lifecycle ───────────────────────────────────────────────────
    def enter(self) -> None:
        self._renderer.init_fonts()

        # Select random puzzles
        bank = list(PUZZLE_BANK)
        random.shuffle(bank)
        self._puzzles = bank[:LIMBO_PUZZLES_REQUIRED]
        self._current_puzzle_idx = 0
        self._load_puzzle(0)

    def exit(self) -> None:
        pass

    # ── Events ──────────────────────────────────────────────────────
    def handle_event(self, event: pygame.event.Event) -> None:
        if self._failed or self._escaped:
            return

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            mx, my = event.pos
            # Account for screen shake
            mx -= self._shake_offset[0]
            my -= self._shake_offset[1]
            sq = self._renderer.pixel_to_square(mx, my)
            if sq is not None:
                self._handle_square_click(sq)

    # ── Update ──────────────────────────────────────────────────────
    def update(self, dt: float) -> None:
        self._time += dt

        # Fade in
        if self._transition_alpha > 0:
            self._transition_alpha = max(0, self._transition_alpha - 400 * dt)
            return

        if self._failed or self._escaped:
            self._result_timer += dt
            if self._result_timer > 2.5:
                self._sm.pop()
                if self._escaped:
                    self._game_state.on_limbo_escaped()
                else:
                    self._game_state.on_limbo_failed()
            return

        # Timer
        self._time_remaining -= dt
        if self._time_remaining <= 0:
            self._time_remaining = 0
            self._failed = True
            return

        # Screen shake when time is low
        if self._time_remaining < 15:
            intensity = int(3 * (1 - self._time_remaining / 15))
            self._shake_offset = (
                random.randint(-intensity, intensity),
                random.randint(-intensity, intensity),
            )
        else:
            self._shake_offset = (0, 0)

        # Noise increases as time decreases
        self._noise_intensity = 0.2 + 0.6 * (1 - self._time_remaining / self._total_time)

    # ── Draw ────────────────────────────────────────────────────────
    def draw(self, surface: pygame.Surface) -> None:
        surface.fill((15, 15, 18))

        # Apply shake offset
        board_surface = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
        board_surface.fill((15, 15, 18))

        # Draw the puzzle board
        self._renderer.draw_board_grid(board_surface)

        # Highlights
        self._renderer.draw_highlights(
            board_surface, self._selected_sq, self._legal_moves, None, self._puzzle_board
        )

        # Pieces
        self._renderer.draw_pieces(board_surface, self._puzzle_board)

        # Apply noir filter
        self._renderer.apply_noir_filter(board_surface, self._noise_intensity)

        # Blit with shake
        surface.blit(board_surface, self._shake_offset)

        # ── HUD ─────────────────────────────────────────────────────
        font = pygame.font.SysFont("consolas", 22, bold=True)
        font_sm = pygame.font.SysFont("consolas", 16)
        font_lg = pygame.font.SysFont("georgia", 40, bold=True)

        # Title
        title = font_lg.render("L I M B O", True, (200, 60, 60))
        title.set_alpha(int(150 + 100 * abs(self._time * 2 % 2 - 1)))
        surface.blit(title, (SCREEN_WIDTH // 2 - title.get_width() // 2, 10))

        # Timer
        timer_color = COLOR_DANGER if self._time_remaining < 15 else COLOR_TEXT
        timer_txt = font.render(f"TIME: {self._time_remaining:.1f}s", True, timer_color)
        surface.blit(timer_txt, (BOARD_ORIGIN_X + BOARD_PIXEL_SIZE + 60, 80))

        # Progress
        prog = font.render(
            f"PUZZLE {self._puzzles_solved + 1} / {LIMBO_PUZZLES_REQUIRED}",
            True, COLOR_ACCENT,
        )
        surface.blit(prog, (BOARD_ORIGIN_X + BOARD_PIXEL_SIZE + 60, 120))

        # Instruction
        inst = font_sm.render("Solve the position. Find the best move.", True, COLOR_TEXT_DIM)
        surface.blit(inst, (BOARD_ORIGIN_X + BOARD_PIXEL_SIZE + 60, 170))

        side = "White" if self._puzzle_board.turn == chess.WHITE else "Black"
        side_txt = font_sm.render(f"{side} to move", True, COLOR_TEXT)
        surface.blit(side_txt, (BOARD_ORIGIN_X + BOARD_PIXEL_SIZE + 60, 200))

        # ── Result overlay ──────────────────────────────────────────
        if self._failed:
            overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
            overlay.fill((100, 0, 0, 150))
            surface.blit(overlay, (0, 0))
            fail_txt = font_lg.render("CONSUMED BY THE VOID", True, (255, 50, 50))
            surface.blit(fail_txt, (
                SCREEN_WIDTH // 2 - fail_txt.get_width() // 2,
                SCREEN_HEIGHT // 2 - 30,
            ))

        elif self._escaped:
            overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
            overlay.fill((80, 60, 140, 100))
            surface.blit(overlay, (0, 0))
            esc_txt = font_lg.render("ESCAPED FROM LIMBO", True, COLOR_ACCENT)
            surface.blit(esc_txt, (
                SCREEN_WIDTH // 2 - esc_txt.get_width() // 2,
                SCREEN_HEIGHT // 2 - 30,
            ))

        # ── Transition fade ─────────────────────────────────────────
        if self._transition_alpha > 0:
            fade = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
            fade.fill((0, 0, 0))
            fade.set_alpha(int(self._transition_alpha))
            surface.blit(fade, (0, 0))

    # ── Internal ────────────────────────────────────────────────────
    def _load_puzzle(self, index: int) -> None:
        if index >= len(self._puzzles):
            self._escaped = True
            return

        fen, solution = self._puzzles[index]
        self._puzzle_board = chess.Board(fen)
        self._solution_moves = solution
        self._solution_step = 0
        self._selected_sq = None
        self._legal_moves = list(self._puzzle_board.legal_moves)

    def _handle_square_click(self, sq: int) -> None:
        piece = self._puzzle_board.piece_at(sq)

        if self._selected_sq is None:
            if piece and piece.color == self._puzzle_board.turn:
                self._selected_sq = sq
        else:
            move = chess.Move(self._selected_sq, sq)
            # Check promotion
            moved_piece = self._puzzle_board.piece_at(self._selected_sq)
            if moved_piece and moved_piece.piece_type == chess.PAWN:
                to_rank = chess.square_rank(sq)
                if (moved_piece.color == chess.WHITE and to_rank == 7) or \
                   (moved_piece.color == chess.BLACK and to_rank == 0):
                    move = chess.Move(self._selected_sq, sq, promotion=chess.QUEEN)

            if move in self._legal_moves:
                self._try_puzzle_move(move)
            elif piece and piece.color == self._puzzle_board.turn:
                self._selected_sq = sq
            else:
                self._selected_sq = None

    def _try_puzzle_move(self, move: chess.Move) -> None:
        """Check if the move matches the puzzle solution."""
        if self._solution_step < len(self._solution_moves):
            expected_uci = self._solution_moves[self._solution_step]
            if move.uci() == expected_uci:
                # Correct!
                self._puzzle_board.push(move)
                self._solution_step += 1
                self._selected_sq = None

                if self._solution_step >= len(self._solution_moves):
                    # Puzzle solved
                    self._puzzles_solved += 1
                    if self._puzzles_solved >= LIMBO_PUZZLES_REQUIRED:
                        self._escaped = True
                    else:
                        self._current_puzzle_idx += 1
                        self._load_puzzle(self._current_puzzle_idx)
                else:
                    self._legal_moves = list(self._puzzle_board.legal_moves)
            else:
                # Wrong move — instant fail in Limbo
                self._failed = True
        else:
            self._failed = True
