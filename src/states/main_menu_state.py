"""
Dorothy's Mind Games - Main Menu State
=======================================
The primary entry screen.  A dark void background with four
vertically-centred buttons:

    START GAME   → switches to the chess gameplay state.
    HOW TO PLAY  → pushes the tutorial / lore overlay.
    OPTIONS      → placeholder (prints to console).
    QUIT GAME    → posts a QUIT event to exit cleanly.

Navigation works via both mouse clicks and keyboard (UP/DOWN + ENTER).
"""

from __future__ import annotations

import math
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


# ── Menu item labels & helpers ──────────────────────────────────────
_BUTTON_LABELS: list[str] = [
    "START GAME",
    "TUTORIAL",
    "HOW TO PLAY",
    "OPTIONS",
    "QUIT GAME",
]

_BTN_WIDTH = 320
_BTN_HEIGHT = 52
_BTN_SPACING = 18  # vertical gap between buttons


class MainMenuState:
    """Atmospheric main menu with four navigation buttons."""

    def __init__(self, state_manager: "StateManager") -> None:
        self._sm = state_manager

        # Fonts (initialised in enter())
        self._font_title: pygame.font.Font | None = None
        self._font_subtitle: pygame.font.Font | None = None
        self._font_btn: pygame.font.Font | None = None
        self._font_hint: pygame.font.Font | None = None

        # Buttons (built in enter() once fonts are ready)
        self._buttons: list[UIButton] = []
        self._selected_index: int = 0

        # Cosmetic
        self._time: float = 0.0

    # ── Lifecycle ───────────────────────────────────────────────────
    def enter(self) -> None:
        self._font_title = pygame.font.SysFont("georgia", 52, bold=True)
        self._font_subtitle = pygame.font.SysFont("consolas", 18)
        self._font_btn = pygame.font.SysFont("consolas", 22)
        self._font_hint = pygame.font.SysFont("consolas", 14)
        self._selected_index = 0
        self._time = 0.0

        # Build centred button column
        total_h = len(_BUTTON_LABELS) * _BTN_HEIGHT + (len(_BUTTON_LABELS) - 1) * _BTN_SPACING
        start_y = (SCREEN_HEIGHT // 2) - (total_h // 2) + 60  # nudge down from centre to leave room for title
        bx = SCREEN_WIDTH // 2 - _BTN_WIDTH // 2

        self._buttons = []
        for i, label in enumerate(_BUTTON_LABELS):
            by = start_y + i * (_BTN_HEIGHT + _BTN_SPACING)
            self._buttons.append(
                UIButton(bx, by, _BTN_WIDTH, _BTN_HEIGHT, label, font=self._font_btn)
            )

    def exit(self) -> None:
        pass

    # ── Events ──────────────────────────────────────────────────────
    def handle_event(self, event: pygame.event.Event) -> None:
        # ── Keyboard navigation ─────────────────────────────────────
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_UP:
                self._selected_index = (self._selected_index - 1) % len(self._buttons)
            elif event.key == pygame.K_DOWN:
                self._selected_index = (self._selected_index + 1) % len(self._buttons)
            elif event.key in (pygame.K_RETURN, pygame.K_SPACE):
                self._activate(self._selected_index)
            elif event.key == pygame.K_ESCAPE:
                pygame.event.post(pygame.event.Event(pygame.QUIT))

        # ── Mouse clicks ────────────────────────────────────────────
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            for i, btn in enumerate(self._buttons):
                if btn.is_clicked(event):
                    self._selected_index = i
                    self._activate(i)
                    break

    # ── Update ──────────────────────────────────────────────────────
    def update(self, dt: float) -> None:
        self._time += dt

        # Keep hover state in sync with mouse each frame
        mouse_pos = pygame.mouse.get_pos()
        for i, btn in enumerate(self._buttons):
            if btn.is_hovered(mouse_pos):
                self._selected_index = i

        # Also mark the keyboard-selected button as hovered so it
        # renders with the highlight style even when the mouse is
        # elsewhere.
        for i, btn in enumerate(self._buttons):
            btn._hovered = (i == self._selected_index)

    # ── Draw ────────────────────────────────────────────────────────
    def draw(self, surface: pygame.Surface) -> None:
        # ── Void background ─────────────────────────────────────────
        surface.fill(COLOR_BG)

        if not self._font_title:
            return

        # ── Title (pulsing) ─────────────────────────────────────────
        pulse = 0.7 + 0.3 * math.sin(self._time * 1.5)
        title_color = tuple(int(c * pulse) for c in COLOR_ACCENT)
        title_surf = self._font_title.render("Dorothy's Mind Games", True, title_color)
        surface.blit(
            title_surf,
            (SCREEN_WIDTH // 2 - title_surf.get_width() // 2, 70),
        )

        # ── Subtitle ────────────────────────────────────────────────
        sub = self._font_subtitle.render(  # type: ignore[union-attr]
            '"In this world, moves decide everything."', True, COLOR_TEXT_DIM
        )
        surface.blit(sub, (SCREEN_WIDTH // 2 - sub.get_width() // 2, 140))

        # ── Thin accent divider ─────────────────────────────────────
        div_y = 180
        pygame.draw.line(
            surface, COLOR_ACCENT,
            (SCREEN_WIDTH // 2 - 200, div_y),
            (SCREEN_WIDTH // 2 + 200, div_y),
            1,
        )

        # ── Buttons ─────────────────────────────────────────────────
        for btn in self._buttons:
            btn.draw(surface)

        # ── Controls hint at bottom ─────────────────────────────────
        hint = self._font_hint.render(  # type: ignore[union-attr]
            "[UP / DOWN]  Navigate    [ENTER]  Select    [ESC]  Quit",
            True,
            COLOR_TEXT_DIM,
        )
        surface.blit(hint, (SCREEN_WIDTH // 2 - hint.get_width() // 2, SCREEN_HEIGHT - 44))

    # ── Button actions ──────────────────────────────────────────────
    def _activate(self, index: int) -> None:
        """Dispatch the action tied to button *index*."""
        label = _BUTTON_LABELS[index]

        if label == "START GAME":
            self._start_game()
        elif label == "TUTORIAL":
            self._open_tutorial()
        elif label == "HOW TO PLAY":
            self._open_how_to_play()
        elif label == "OPTIONS":
            print("[MainMenu] OPTIONS selected — not yet implemented.")
        elif label == "QUIT GAME":
            pygame.event.post(pygame.event.Event(pygame.QUIT))

    def _start_game(self) -> None:
        from src.engine.opponent import ALL_PERSONAS
        from src.states.game_state import ChessGameState

        # Default to the first persona; a persona-picker can be added later.
        game = ChessGameState(self._sm, ALL_PERSONAS[0])
        self._sm.switch(game)

    def _open_how_to_play(self) -> None:
        from src.states.how_to_play_state import HowToPlayState

        self._sm.push(HowToPlayState(self._sm))

    def _open_tutorial(self) -> None:
        from src.states.tutorial_state import TutorialState

        self._sm.push(TutorialState(self._sm))
