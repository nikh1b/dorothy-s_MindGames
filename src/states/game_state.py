"""
Dorothy's Mind Games - Chess Game State
========================================
The core gameplay state: a full chess game with Genius Vision,
resource management, blunder detection, and Limbo transitions.
"""

from __future__ import annotations

from dataclasses import dataclass
import random
import time
from typing import TYPE_CHECKING, Optional

import chess
import pygame

from src.core.constants import (
    BLUNDER_THRESHOLD_CP,
    BOARD_ORIGIN_X,
    BOARD_ORIGIN_Y,
    BOARD_PIXEL_SIZE,
    COLOR_ACCENT,
    COLOR_BG,
    COLOR_DANGER,
    COLOR_TEXT,
    COLOR_TEXT_DIM,
    FOCUS_COST_GENIUS_VISION,
    INACCURACY_THRESHOLD_CP,
    MISTAKE_THRESHOLD_CP,
    SCREEN_HEIGHT,
    SCREEN_WIDTH,
    SOUL_COST_REWIND,
    SQUARE_SIZE,
)
from src.core.resource_manager import PlayerResources
from src.engine.analyzer import AnalysisResult, StockfishAnalyzer
from src.engine.opponent import OpponentPersona
from src.ui.dialogue import DialogueBox, DialogueLine
from src.ui.renderer import BoardRenderer

if TYPE_CHECKING:
    from src.core.state_manager import StateManager


@dataclass
class MoveAnimation:
    """Visual tween for piece motion between two squares."""

    piece: chess.Piece
    from_square: int
    to_square: int
    elapsed: float = 0.0
    duration: float = 0.20
    on_complete: str | None = None

    @property
    def progress(self) -> float:
        if self.duration <= 0:
            return 1.0
        return max(0.0, min(1.0, self.elapsed / self.duration))


class ChessGameState:
    """The main chess gameplay state."""

    def __init__(self, state_manager: "StateManager", opponent: OpponentPersona) -> None:
        self._sm = state_manager
        self._opponent = opponent

        # ── Chess state ─────────────────────────────────────────────
        self._board = chess.Board()
        self._move_history: list[chess.Move] = []
        self._move_log: list[tuple[str, str, str]] = []  # (num, SAN, label)
        self._player_is_white: bool = True
        self._flipped: bool = False

        # ── Interaction ─────────────────────────────────────────────
        self._selected_sq: int | None = None
        self._dragging: bool = False
        self._drag_piece: chess.Piece | None = None
        self._drag_from_sq: int | None = None
        self._legal_moves: list[chess.Move] = []
        self._move_animation: MoveAnimation | None = None

        # ── Engine ──────────────────────────────────────────────────
        self._analyzer = StockfishAnalyzer()
        self._ai_analyzer = StockfishAnalyzer()  # separate instance for AI moves
        self._analysis: AnalysisResult = AnalysisResult()
        self._prev_eval_cp: int = 0
        self._waiting_for_ai: bool = False
        self._ai_think_timer: float = 0.0

        # ── Resources ───────────────────────────────────────────────
        self.resources = PlayerResources()

        # ── Genius Vision ───────────────────────────────────────────
        self._genius_active: bool = False
        self._show_threats: bool = False

        # ── Visual ──────────────────────────────────────────────────
        self._renderer = BoardRenderer()
        self._dialogue = DialogueBox()
        self._pulse_time: float = 0.0
        self._time: float = 0.0

        # ── Game result ─────────────────────────────────────────────
        self._game_over: bool = False
        self._game_result: str = ""

    # ── Lifecycle ───────────────────────────────────────────────────
    def enter(self) -> None:
        self._renderer.init_fonts()
        self._dialogue.init_fonts()

        # Start analysis engine
        engine_ok = self._analyzer.start()
        if engine_ok:
            self._analyzer.set_position(self._board.fen())

        # Start AI engine
        ai_ok = self._ai_analyzer.start()

        # Welcome dialogue
        self._dialogue.enqueue(
            DialogueLine("Dorothy", "Another opponent stands before me...", duration=2.0),
            DialogueLine("Dorothy", f"They call this one '{self._opponent.name}'.", duration=2.0),
            DialogueLine(self._opponent.name,
                         random.choice(self._opponent.taunt_lines) if self._opponent.taunt_lines else "...",
                         speaker_color=COLOR_DANGER),
        )

        self._legal_moves = list(self._board.legal_moves)

        if not engine_ok:
            self._dialogue.enqueue(
                DialogueLine("System",
                             "Stockfish engine not found. AI moves will be random. "
                             "Place stockfish.exe on your PATH for full experience.",
                             color=COLOR_DANGER, duration=4.0),
            )

    def exit(self) -> None:
        self._analyzer.stop()
        self._ai_analyzer.stop()

    # ── Events ──────────────────────────────────────────────────────
    def handle_event(self, event: pygame.event.Event) -> None:
        # Dialogue takes priority
        if self._dialogue.is_active:
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                self._dialogue.skip_or_advance()
            elif event.type == pygame.KEYDOWN and event.key in (pygame.K_SPACE, pygame.K_RETURN):
                self._dialogue.skip_or_advance()
            return

        if self._game_over:
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    from src.states.main_menu_state import MainMenuState
                    self._sm.switch(MainMenuState(self._sm))
            return

        # During tween animation, lock input so moves feel deliberate and fluid.
        if self._move_animation is not None:
            return

        if self._waiting_for_ai:
            return  # player can't act during AI turn

        # ── Keyboard shortcuts ──────────────────────────────────────
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                from src.states.main_menu_state import MainMenuState
                self._sm.switch(MainMenuState(self._sm))
            elif event.key == pygame.K_g:
                # Toggle Genius Vision
                if self.resources.spend_focus(FOCUS_COST_GENIUS_VISION):
                    self._genius_active = not self._genius_active
            elif event.key == pygame.K_t:
                self._show_threats = not self._show_threats
            elif event.key == pygame.K_r:
                # Temporal Rewind
                self._attempt_rewind()
            elif event.key == pygame.K_f:
                self._flipped = not self._flipped

        # ── Mouse: click to select / move ───────────────────────────
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            mx, my = event.pos
            sq = self._renderer.pixel_to_square(mx, my, self._flipped)
            if sq is not None:
                self._handle_square_click(sq)

        # ── Mouse: drag start ───────────────────────────────────────
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            pass  # handled above

        # ── Mouse: drag ─────────────────────────────────────────────
        elif event.type == pygame.MOUSEMOTION and self._dragging:
            pass  # piece follows cursor in draw

        # ── Mouse: drop ─────────────────────────────────────────────
        elif event.type == pygame.MOUSEBUTTONUP and event.button == 1 and self._dragging:
            mx, my = event.pos
            drop_sq = self._renderer.pixel_to_square(mx, my, self._flipped)
            if drop_sq is not None and self._drag_from_sq is not None:
                move = chess.Move(self._drag_from_sq, drop_sq)
                if move in self._legal_moves:
                    self._make_player_move(move)
            self._dragging = False
            self._drag_piece = None
            self._drag_from_sq = None

        # ── Right-click: hold for PV preview ────────────────────────
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 3:
            if self.resources.spend_focus(5):
                self._genius_active = True
        elif event.type == pygame.MOUSEBUTTONUP and event.button == 3:
            self._genius_active = False

    # ── Update ──────────────────────────────────────────────────────
    def update(self, dt: float) -> None:
        self._time += dt
        self._pulse_time += dt
        self._dialogue.update(dt)
        self.resources.update_flow_timer(dt)

        # Smoothly animate moved pieces across squares.
        if self._move_animation is not None:
            self._move_animation.elapsed += dt
            if self._move_animation.progress >= 1.0:
                action = self._move_animation.on_complete
                self._move_animation = None
                if action == "start_ai" and not self._board.is_game_over():
                    self._waiting_for_ai = True
                    self._ai_think_timer = 0.0

        # Poll analysis
        if self._analyzer.is_available:
            self._analysis = self._analyzer.get_latest()

        # AI turn
        if self._waiting_for_ai and not self._dialogue.is_active and self._move_animation is None:
            self._ai_think_timer += dt
            ai_time = self._opponent.move_time_ms / 1000.0
            if self._ai_think_timer >= ai_time:
                self._make_ai_move()

        # Check game end
        if not self._game_over:
            self._check_game_end()

    # ── Draw ────────────────────────────────────────────────────────
    def draw(self, surface: pygame.Surface) -> None:
        surface.fill(COLOR_BG)

        # Layer 1: Board grid
        self._renderer.draw_board_grid(surface)

        # Layer 2: Highlights
        last_move = self._move_history[-1] if self._move_history else None
        self._renderer.draw_highlights(
            surface, self._selected_sq, self._legal_moves,
            last_move, self._board, self._flipped
        )

        # Layer 3: Threat map
        if self._show_threats:
            opacity = self.resources.focus_ratio
            self._renderer.draw_threat_map(surface, self._board, opacity, self._flipped)

        # Layer 4: Pieces
        suppress_sq = self._drag_from_sq if self._dragging else (
            self._move_animation.to_square if self._move_animation else None
        )
        self._renderer.draw_pieces(
            surface, self._board, self._flipped,
            dragging_sq=suppress_sq,
        )

        # Dragging piece at cursor
        if self._dragging and self._drag_piece:
            mx, my = pygame.mouse.get_pos()
            self._renderer.draw_dragging_piece(surface, self._drag_piece, mx, my)

        # Draw smooth move tween on top of board pieces.
        if self._move_animation is not None:
            anim = self._move_animation
            fx, fy = self._renderer.square_to_pixel(anim.from_square, self._flipped)
            tx, ty = self._renderer.square_to_pixel(anim.to_square, self._flipped)
            t = anim.progress
            t = t * t * (3.0 - 2.0 * t)  # smoothstep easing
            px = int(fx + (tx - fx) * t + SQUARE_SIZE // 2)
            py = int(fy + (ty - fy) * t + SQUARE_SIZE // 2)
            self._renderer.draw_dragging_piece(surface, anim.piece, px, py)

        # Layer 5: Ghost PV
        if self._genius_active and self._analysis.pv:
            self._renderer.draw_ghost_pv(
                surface, self._board, self._analysis.pv,
                max_depth=4, flipped=self._flipped,
            )

        # Layer 6: Best move arrow
        if self._genius_active and self._analysis.best_move:
            self._renderer.draw_best_move_arrow(
                surface, self._analysis.best_move, self._pulse_time, self._flipped,
            )

        # Layer 7: HUD
        self._renderer.draw_eval_bar(surface, self._analysis, self.resources.sanity_ratio)
        self._renderer.draw_resource_meters(surface, self.resources)
        self._renderer.draw_move_log(surface, self._move_log)
        self._renderer.draw_game_info(
            surface, self._opponent.name,
            self.resources.accuracy_percent,
            len(self._move_history),
        )

        # Layer 8: Sanity distortion
        self._renderer.apply_sanity_distortion(surface, self.resources.sanity_ratio)

        # ── AI thinking indicator ───────────────────────────────────
        if self._waiting_for_ai:
            font = pygame.font.SysFont("consolas", 18)
            dots = "." * (int(self._time * 2) % 4)
            txt = font.render(f"{self._opponent.name} is thinking{dots}", True, COLOR_TEXT_DIM)
            surface.blit(txt, (BOARD_ORIGIN_X, BOARD_ORIGIN_Y + BOARD_PIXEL_SIZE + 28))

        # ── Game Over overlay ───────────────────────────────────────
        if self._game_over:
            self._draw_game_over(surface)

        # Dialogue on top
        self._dialogue.draw(surface)

        # ── Flow state glow ─────────────────────────────────────────
        if self.resources.flow_state_active:
            glow = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
            alpha = int(15 + 10 * abs(pygame.time.get_ticks() / 300 % 2 - 1))
            glow.fill((*COLOR_ACCENT, alpha))
            surface.blit(glow, (0, 0))

    # ── Internal Logic ──────────────────────────────────────────────
    def _handle_square_click(self, sq: int) -> None:
        """Process a click on a board square."""
        piece = self._board.piece_at(sq)

        if self._selected_sq is None:
            # Select own piece
            if piece and piece.color == self._board.turn:
                self._selected_sq = sq
                self._dragging = True
                self._drag_piece = piece
                self._drag_from_sq = sq
        else:
            # Try to make move
            move = chess.Move(self._selected_sq, sq)
            # Check for promotion
            if self._is_promotion(move):
                move = chess.Move(self._selected_sq, sq, promotion=chess.QUEEN)

            if move in self._legal_moves:
                self._make_player_move(move)
            elif piece and piece.color == self._board.turn:
                # Select a different piece
                self._selected_sq = sq
                self._dragging = True
                self._drag_piece = piece
                self._drag_from_sq = sq
            else:
                self._selected_sq = None

    def _is_promotion(self, move: chess.Move) -> bool:
        piece = self._board.piece_at(move.from_square)
        if piece and piece.piece_type == chess.PAWN:
            to_rank = chess.square_rank(move.to_square)
            if (piece.color == chess.WHITE and to_rank == 7) or \
               (piece.color == chess.BLACK and to_rank == 0):
                return True
        return False

    def _make_player_move(self, move: chess.Move) -> None:
        """Execute a player move, classify it, and check for blunders."""
        eval_before = self._analysis.score_cp
        moving_piece = self._board.piece_at(move.from_square)

        # Push the move
        san = self._board.san(move)
        self._board.push(move)
        self._move_history.append(move)
        self._selected_sq = None
        self._dragging = False

        # Update analysis
        if self._analyzer.is_available:
            self._analyzer.set_position(self._board.fen())

        # Wait briefly then classify
        # (In a real async system we'd defer this; for now use previous eval)
        eval_after = -eval_before  # rough estimate until engine catches up

        # Classify the move
        classification = self._analyzer.classify_move(
            eval_before, eval_after, move.uci(), self._player_is_white
        )

        # Update move log
        move_num = (len(self._move_history) + 1) // 2
        move_str = f"{move_num}" if self._board.turn == chess.BLACK else f"{move_num}..."
        self._move_log.append((move_str, san, classification.label))

        # Update resources based on classification
        self._apply_move_classification(classification)

        # Regen focus
        multiplier = 2.0 if self.resources.flow_state_active else 1.0
        self.resources.regen_focus(multiplier)
        self.resources.total_moves += 1

        self._prev_eval_cp = eval_after
        self._legal_moves = list(self._board.legal_moves)

        # Animate move; AI turn begins when animation completes.
        if moving_piece is not None:
            self._move_animation = MoveAnimation(
                piece=moving_piece,
                from_square=move.from_square,
                to_square=move.to_square,
                on_complete="start_ai",
            )
        elif not self._board.is_game_over():
            self._waiting_for_ai = True
            self._ai_think_timer = 0.0

    def _apply_move_classification(self, classification) -> None:
        """Update resources and trigger events based on move quality."""
        label = classification.label

        if label in ("brilliant", "best"):
            self.resources.register_best_move()
            self.resources.restore_sanity(5)
            self.resources.restore_soul(3)
        elif label == "good":
            self.resources.good_moves += 1
            self.resources.break_streak()
        elif label == "inaccuracy":
            self.resources.inaccuracies += 1
            self.resources.break_streak()
            self.resources.drain_sanity(5)
        elif label == "mistake":
            self.resources.mistakes += 1
            self.resources.break_streak()
            self.resources.drain_sanity(15)
            self.resources.drain_soul(5)
            self._dialogue.enqueue(
                DialogueLine("Dorothy", "That wasn't right... I can feel the cracks forming.",
                             color=COLOR_DANGER, duration=2.0),
            )
        elif label == "blunder":
            self.resources.blunders += 1
            self.resources.break_streak()
            self._trigger_limbo()

    def _trigger_limbo(self) -> None:
        """Enter the Limbo state after a blunder."""
        self._dialogue.enqueue(
            DialogueLine("???", "Y O U   B L U N D E R E D.", color=COLOR_DANGER, duration=1.5),
            DialogueLine("Dorothy", "No... the world is fracturing—!", color=(200, 180, 255), duration=1.5),
        )
        # Push Limbo state on top
        from src.states.limbo_state import LimboState
        limbo = LimboState(self._sm, self, self._board.fen())
        self._sm.push(limbo)

    def _make_ai_move(self) -> None:
        """Execute the AI's move."""
        self._waiting_for_ai = False

        if self._board.is_game_over():
            return

        # Get AI move
        ai_move: chess.Move | None = None

        if self._ai_analyzer.is_available:
            self._ai_analyzer.set_position(self._board.fen())
            # Give the AI time to think
            import time as _time
            _time.sleep(0.1)  # brief sync wait
            result = self._ai_analyzer.get_latest()
            if result.best_move:
                try:
                    ai_move = chess.Move.from_uci(result.best_move)
                    if ai_move not in self._board.legal_moves:
                        ai_move = None
                except ValueError:
                    ai_move = None

        # Fallback: random legal move
        if ai_move is None:
            legal = list(self._board.legal_moves)
            if legal:
                ai_move = random.choice(legal)

        if ai_move is None:
            return

        moving_piece = self._board.piece_at(ai_move.from_square)

        # Push AI move
        san = self._board.san(ai_move)
        self._board.push(ai_move)
        self._move_history.append(ai_move)

        move_num = (len(self._move_history) + 1) // 2
        self._move_log.append((str(move_num), san, "ai"))

        # Update engine
        if self._analyzer.is_available:
            self._analyzer.set_position(self._board.fen())

        self._legal_moves = list(self._board.legal_moves)
        self._prev_eval_cp = self._analysis.score_cp

        # Occasional taunt
        if random.random() < 0.15 and self._opponent.taunt_lines:
            self._dialogue.enqueue(
                DialogueLine(self._opponent.name,
                             random.choice(self._opponent.taunt_lines),
                             speaker_color=COLOR_DANGER, duration=2.5),
            )

        # Animate AI piece movement for readability.
        if moving_piece is not None:
            self._move_animation = MoveAnimation(
                piece=moving_piece,
                from_square=ai_move.from_square,
                to_square=ai_move.to_square,
            )

    def _attempt_rewind(self) -> None:
        """Temporal Rewind: undo last move pair at the cost of Soul."""
        if len(self._move_history) < 2:
            return

        if self.resources.spend_soul_for_rewind():
            # Undo AI move + player move
            self._board.pop()
            self._board.pop()
            self._move_history.pop()
            self._move_history.pop()
            if len(self._move_log) >= 2:
                self._move_log.pop()
                self._move_log.pop()

            self._legal_moves = list(self._board.legal_moves)
            self._waiting_for_ai = False

            if self._analyzer.is_available:
                self._analyzer.set_position(self._board.fen())

            self._dialogue.enqueue(
                DialogueLine("Dorothy",
                             f"Time bends... but it costs a piece of my soul. ({self.resources.soul} remaining)",
                             color=COLOR_ACCENT, duration=2.0),
            )
        else:
            self._dialogue.enqueue(
                DialogueLine("Dorothy",
                             "I don't have enough soul left to rewind...",
                             color=COLOR_DANGER, duration=2.0),
            )

    def _check_game_end(self) -> None:
        """Check for checkmate, stalemate, or resource death."""
        if self.resources.is_dead:
            self._game_over = True
            self._game_result = "HELL - Your soul has been consumed."
            return

        if self._board.is_checkmate():
            self._game_over = True
            if self._board.turn != (chess.WHITE if self._player_is_white else chess.BLACK):
                self._game_result = "HEAVEN - Checkmate! Dorothy's genius prevails."
                # Check for perfect game
                if self.resources.accuracy_percent >= 95:
                    self._game_result = "ASCENSION - A perfect game. Heaven opens its gates."
            else:
                self._game_result = "HELL - Checkmate. The darkness claims another mind."
        elif self._board.is_stalemate():
            self._game_over = True
            self._game_result = "LIMBO ETERNAL - Stalemate. Neither heaven nor hell."
        elif self._board.is_insufficient_material():
            self._game_over = True
            self._game_result = "THE VOID - Insufficient material. Reality dissolves."
        elif self._board.can_claim_threefold_repetition():
            self._game_over = True
            self._game_result = "TIME LOOP - The same moves echo endlessly."

    def _draw_game_over(self, surface: pygame.Surface) -> None:
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 180))
        surface.blit(overlay, (0, 0))

        font_big = pygame.font.SysFont("georgia", 36, bold=True)
        font_sm = pygame.font.SysFont("consolas", 18)

        # Result
        is_victory = "HEAVEN" in self._game_result or "ASCENSION" in self._game_result
        color = COLOR_ACCENT if is_victory else COLOR_DANGER
        result_surf = font_big.render(self._game_result, True, color)
        surface.blit(result_surf, (
            SCREEN_WIDTH // 2 - result_surf.get_width() // 2,
            SCREEN_HEIGHT // 2 - 60,
        ))

        # Stats
        stats = f"Accuracy: {self.resources.accuracy_percent:.1f}%  |  Moves: {self.resources.total_moves}  |  Blunders: {self.resources.blunders}"
        stats_surf = font_sm.render(stats, True, COLOR_TEXT)
        surface.blit(stats_surf, (
            SCREEN_WIDTH // 2 - stats_surf.get_width() // 2,
            SCREEN_HEIGHT // 2 + 10,
        ))

        # Hint
        hint = font_sm.render("[ESC] Return to menu", True, COLOR_TEXT_DIM)
        surface.blit(hint, (
            SCREEN_WIDTH // 2 - hint.get_width() // 2,
            SCREEN_HEIGHT // 2 + 60,
        ))

    # ── Public (for Limbo callbacks) ────────────────────────────────
    def on_limbo_escaped(self) -> None:
        """Called when the player escapes Limbo."""
        self.resources.apply_limbo_trauma()
        self._dialogue.enqueue(
            DialogueLine("Dorothy",
                         f"I escaped... but the scars remain. (Max Sanity: {self.resources.sanity_max})",
                         color=COLOR_ACCENT, duration=2.5),
        )

    def on_limbo_failed(self) -> None:
        """Called when the player fails in Limbo."""
        self._game_over = True
        self._game_result = "HELL - Lost in Limbo. The Void claims you."
