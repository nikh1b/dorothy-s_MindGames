"""
Dorothy's Mind Games - Tutorial State
======================================
Beginner-friendly tutorial page from the main menu.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pygame

from src.core.constants import (
    COLOR_ACCENT,
    COLOR_BG,
    COLOR_TEXT,
    COLOR_TEXT_DIM,
    SCREEN_HEIGHT,
    SCREEN_WIDTH,
)
from src.ui.elements import UIButton

if TYPE_CHECKING:
    from src.core.state_manager import StateManager


_BACK_W = 220
_BACK_H = 48
_PRACTICE_W = 280
_PRACTICE_H = 50


class TutorialState:
    """A practical quick-start guide for new players."""

    def __init__(self, state_manager: "StateManager") -> None:
        self._sm = state_manager
        self._font_title: pygame.font.Font | None = None
        self._font_sub: pygame.font.Font | None = None
        self._font_body: pygame.font.Font | None = None
        self._btn_back: UIButton | None = None
        self._btn_practice: UIButton | None = None

    def enter(self) -> None:
        self._font_title = pygame.font.SysFont("georgia", 40, bold=True)
        self._font_sub = pygame.font.SysFont("consolas", 20, bold=True)
        self._font_body = pygame.font.SysFont("consolas", 17)

        self._btn_back = UIButton(
            SCREEN_WIDTH // 2 - _BACK_W // 2,
            SCREEN_HEIGHT - 68,
            _BACK_W,
            _BACK_H,
            "BACK",
            font=pygame.font.SysFont("consolas", 20),
        )
        self._btn_practice = UIButton(
            SCREEN_WIDTH // 2 - _PRACTICE_W // 2,
            SCREEN_HEIGHT - 132,
            _PRACTICE_W,
            _PRACTICE_H,
            "START PRACTICE MATCH",
            font=pygame.font.SysFont("consolas", 18),
        )

    def exit(self) -> None:
        pass

    def handle_event(self, event: pygame.event.Event) -> None:
        if event.type == pygame.KEYDOWN and event.key in (pygame.K_ESCAPE, pygame.K_BACKSPACE):
            self._sm.pop()
            return

        if self._btn_back and self._btn_back.is_clicked(event):
            self._sm.pop()
            return

        if self._btn_practice and self._btn_practice.is_clicked(event):
            from src.engine.opponent import BERSERKER
            from src.states.game_state import ChessGameState

            # Start a forgiving opponent so new players can learn flow.
            self._sm.switch(ChessGameState(self._sm, BERSERKER))

    def update(self, dt: float) -> None:
        pos = pygame.mouse.get_pos()
        if self._btn_back:
            self._btn_back.is_hovered(pos)
        if self._btn_practice:
            self._btn_practice.is_hovered(pos)

    def draw(self, surface: pygame.Surface) -> None:
        surface.fill(COLOR_BG)
        if not self._font_title or not self._font_sub or not self._font_body:
            return

        title = self._font_title.render("Tutorial", True, COLOR_ACCENT)
        surface.blit(title, (SCREEN_WIDTH // 2 - title.get_width() // 2, 30))

        y = 104
        sections = [
            (
                "1) MOVE PIECES",
                [
                    "Click a piece, then click a destination square.",
                    "Legal moves are highlighted. Press [F] to flip the board.",
                ],
            ),
            (
                "2) USE GENIUS VISION",
                [
                    "Press [G] to toggle engine assistance (costs Focus).",
                    "Hold right-click for a quick principal-variation preview.",
                ],
            ),
            (
                "3) AVOID BLUNDERS",
                [
                    "Large mistakes can trigger Limbo. Stay calm and calculate.",
                    "If needed, press [R] to rewind time (costs Soul).",
                ],
            ),
            (
                "4) RESOURCE BASICS",
                [
                    "Sanity: UI reliability. Soul: life force. Focus: analysis fuel.",
                    "Three best moves in a row activate Flow State bonuses.",
                ],
            ),
        ]

        for heading, lines in sections:
            h = self._font_sub.render(heading, True, COLOR_ACCENT)
            surface.blit(h, (120, y))
            y += 30
            for line in lines:
                body = self._font_body.render(line, True, COLOR_TEXT)
                surface.blit(body, (142, y))
                y += 24
            y += 10

        hint = self._font_body.render(
            "Tip: Start with Practice Match before the story run.",
            True,
            COLOR_TEXT_DIM,
        )
        surface.blit(hint, (SCREEN_WIDTH // 2 - hint.get_width() // 2, SCREEN_HEIGHT - 172))

        if self._btn_practice:
            self._btn_practice.draw(surface)
        if self._btn_back:
            self._btn_back.draw(surface)

