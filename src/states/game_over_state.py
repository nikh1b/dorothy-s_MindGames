"""
Dorothy's Mind Games - Game Over State
=======================================
Displays the final result: Heaven (victory), Hell (defeat),
or the Void (draw / resource death).
"""

from __future__ import annotations

import math
from typing import TYPE_CHECKING

import pygame

from src.core.constants import (
    COLOR_ACCENT,
    COLOR_BG,
    COLOR_DANGER,
    COLOR_HEAVEN_TINT,
    COLOR_HELL_TINT,
    COLOR_TEXT,
    COLOR_TEXT_DIM,
    SCREEN_HEIGHT,
    SCREEN_WIDTH,
)

if TYPE_CHECKING:
    from src.core.state_manager import StateManager


class GameOverState:
    """Final results screen with thematic visuals."""

    def __init__(
        self,
        state_manager: "StateManager",
        result_text: str,
        accuracy: float,
        total_moves: int,
        blunders: int,
    ) -> None:
        self._sm = state_manager
        self._result_text = result_text
        self._accuracy = accuracy
        self._total_moves = total_moves
        self._blunders = blunders
        self._time: float = 0.0
        self._is_victory = "HEAVEN" in result_text or "ASCENSION" in result_text

    def enter(self) -> None:
        pass

    def exit(self) -> None:
        pass

    def handle_event(self, event: pygame.event.Event) -> None:
        if event.type == pygame.KEYDOWN:
            if event.key in (pygame.K_ESCAPE, pygame.K_RETURN, pygame.K_SPACE):
                from src.states.main_menu_state import MainMenuState
                self._sm.switch(MainMenuState(self._sm))

    def update(self, dt: float) -> None:
        self._time += dt

    def draw(self, surface: pygame.Surface) -> None:
        # Background
        if self._is_victory:
            bg = COLOR_HEAVEN_TINT
        else:
            bg = COLOR_HELL_TINT
        surface.fill(bg)

        # Pulsing overlay
        alpha = int(30 + 20 * math.sin(self._time * 2))
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        overlay.fill((*COLOR_BG, alpha))
        surface.blit(overlay, (0, 0))

        font_big = pygame.font.SysFont("georgia", 44, bold=True)
        font_md = pygame.font.SysFont("consolas", 22)
        font_sm = pygame.font.SysFont("consolas", 16)

        # Result
        color = COLOR_ACCENT if self._is_victory else COLOR_DANGER
        result = font_big.render(self._result_text, True, color)
        surface.blit(result, (
            SCREEN_WIDTH // 2 - result.get_width() // 2,
            SCREEN_HEIGHT // 3 - 40,
        ))

        # Stats
        stats_lines = [
            f"Accuracy: {self._accuracy:.1f}%",
            f"Total Moves: {self._total_moves}",
            f"Blunders: {self._blunders}",
        ]
        for i, line in enumerate(stats_lines):
            txt = font_md.render(line, True, COLOR_TEXT)
            surface.blit(txt, (
                SCREEN_WIDTH // 2 - txt.get_width() // 2,
                SCREEN_HEIGHT // 2 + i * 36,
            ))

        # Hint
        hint = font_sm.render("[ESC / ENTER] Return to Menu", True, COLOR_TEXT_DIM)
        surface.blit(hint, (
            SCREEN_WIDTH // 2 - hint.get_width() // 2,
            SCREEN_HEIGHT - 80,
        ))
