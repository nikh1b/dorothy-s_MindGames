"""
Dorothy's Mind Games - How to Play State
==========================================
A lore-rich tutorial overlay that explains the core mechanics
to the player.  Pushed on top of the Main Menu (the menu is
still visible underneath, frozen).

A single "BACK" button at the bottom pops this state and
returns to the menu.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pygame

from src.core.constants import (
    COLOR_ACCENT,
    COLOR_BG,
    COLOR_DANGER,
    COLOR_TEXT,
    COLOR_TEXT_DIM,
    SCREEN_HEIGHT,
    SCREEN_WIDTH,
)
from src.ui.elements import UIButton

if TYPE_CHECKING:
    from src.core.state_manager import StateManager


# ── Tutorial content ────────────────────────────────────────────────
# Each section is a (heading, body_lines) pair.
_SECTIONS: list[tuple[str, list[str]]] = [
    (
        "THE MIND'S EYE",
        [
            "Sanity dictates your vision.  Think fast, or the board distorts.",
            "As your mental stability drops, the UI begins to lie — evaluation",
            "bars jitter, ghost arrows mislead, and reality frays at the edges.",
        ],
    ),
    (
        "THE BLUNDER AND LIMBO",
        [
            "Blunders (??) will drag you into Limbo.  Solve the chaos to escape.",
            "A single move that loses 200+ centipawns shatters the board and",
            "plunges Dorothy into a monochromatic nightmare dimension.  Solve",
            "three tactical puzzles under time pressure — or be lost forever.",
        ],
    ),
    (
        "GENIUS VISION",
        [
            "Use Focus to see the Engine Lines, but beware the cost.",
            "Press [G] or hold Right-Click to activate Genius Vision.",
            "It reveals the best move, threat heat-maps, and future lines,",
            "but every activation drains your Focus resource.",
        ],
    ),
    (
        "RESOURCES",
        [
            "SANITY  — Determines how reliable your interface is.",
            "SOUL    — Your life force.  Spend it to Rewind time [R].",
            "FOCUS   — Powers Genius Vision.  Regenerates each turn.",
        ],
    ),
    (
        "FLOW STATE",
        [
            "Play three consecutive best moves and enter the Flow State —",
            "visuals sharpen, Focus regenerates rapidly, and the board hums",
            "with the resonance of Heaven.",
        ],
    ),
]

_BACK_BTN_WIDTH = 200
_BACK_BTN_HEIGHT = 46


class HowToPlayState:
    """Full-screen tutorial overlay with multi-section lore text."""

    def __init__(self, state_manager: "StateManager") -> None:
        self._sm = state_manager

        # Fonts (initialised in enter())
        self._font_title: pygame.font.Font | None = None
        self._font_heading: pygame.font.Font | None = None
        self._font_body: pygame.font.Font | None = None

        # Back button
        self._back_btn: UIButton | None = None

        # Scroll / cosmetic
        self._scroll_y: int = 0
        self._max_scroll: int = 0

    # ── Lifecycle ───────────────────────────────────────────────────
    def enter(self) -> None:
        self._font_title = pygame.font.SysFont("georgia", 40, bold=True)
        self._font_heading = pygame.font.SysFont("consolas", 20, bold=True)
        self._font_body = pygame.font.SysFont("consolas", 16)
        self._scroll_y = 0

        bx = SCREEN_WIDTH // 2 - _BACK_BTN_WIDTH // 2
        by = SCREEN_HEIGHT - 70
        self._back_btn = UIButton(
            bx, by, _BACK_BTN_WIDTH, _BACK_BTN_HEIGHT, "BACK",
            font=pygame.font.SysFont("consolas", 20),
        )

        # Pre-calculate content height so we know the scroll limit
        self._max_scroll = self._content_height() - (SCREEN_HEIGHT - 180)
        if self._max_scroll < 0:
            self._max_scroll = 0

    def exit(self) -> None:
        pass

    # ── Events ──────────────────────────────────────────────────────
    def handle_event(self, event: pygame.event.Event) -> None:
        if self._back_btn is not None and self._back_btn.is_clicked(event):
            self._sm.pop()
            return

        if event.type == pygame.KEYDOWN:
            if event.key in (pygame.K_ESCAPE, pygame.K_BACKSPACE):
                self._sm.pop()
            elif event.key == pygame.K_UP:
                self._scroll_y = max(0, self._scroll_y - 30)
            elif event.key == pygame.K_DOWN:
                self._scroll_y = min(self._max_scroll, self._scroll_y + 30)

        # Mouse wheel scrolling
        elif event.type == pygame.MOUSEWHEEL:
            self._scroll_y -= event.y * 30
            self._scroll_y = max(0, min(self._max_scroll, self._scroll_y))

    # ── Update ──────────────────────────────────────────────────────
    def update(self, dt: float) -> None:
        if self._back_btn is not None:
            self._back_btn.is_hovered(pygame.mouse.get_pos())

    # ── Draw ────────────────────────────────────────────────────────
    def draw(self, surface: pygame.Surface) -> None:
        # Full-screen dark overlay (hides menu beneath)
        surface.fill(COLOR_BG)

        if not self._font_title or not self._font_heading or not self._font_body:
            return

        # ── Page title ──────────────────────────────────────────────
        title = self._font_title.render("How to Play", True, COLOR_ACCENT)
        surface.blit(title, (SCREEN_WIDTH // 2 - title.get_width() // 2, 30))

        # Thin divider under title
        pygame.draw.line(
            surface, COLOR_ACCENT,
            (SCREEN_WIDTH // 2 - 180, 82),
            (SCREEN_WIDTH // 2 + 180, 82),
            1,
        )

        # ── Scrollable content area ─────────────────────────────────
        content_top = 100
        content_bottom = SCREEN_HEIGHT - 90
        clip_rect = pygame.Rect(0, content_top, SCREEN_WIDTH, content_bottom - content_top)

        # Create a sub-surface we can clip into
        content_surf = pygame.Surface((SCREEN_WIDTH, content_bottom - content_top), pygame.SRCALPHA)
        content_surf.fill((0, 0, 0, 0))

        cursor_y = -self._scroll_y  # current draw-y inside the content surface
        margin_x = 120

        for heading, lines in _SECTIONS:
            # Section heading
            head_surf = self._font_heading.render(heading, True, COLOR_ACCENT)
            content_surf.blit(head_surf, (margin_x, cursor_y))
            cursor_y += head_surf.get_height() + 8

            # Body lines
            for line in lines:
                body_surf = self._font_body.render(line, True, COLOR_TEXT)
                content_surf.blit(body_surf, (margin_x + 12, cursor_y))
                cursor_y += body_surf.get_height() + 4

            # Gap between sections
            cursor_y += 22

        surface.blit(content_surf, (0, content_top))

        # ── Scroll indicator ────────────────────────────────────────
        if self._max_scroll > 0:
            ratio = self._scroll_y / self._max_scroll
            track_h = content_bottom - content_top
            thumb_h = max(20, int(track_h * (track_h / (track_h + self._max_scroll))))
            thumb_y = content_top + int(ratio * (track_h - thumb_h))
            bar_x = SCREEN_WIDTH - 18
            pygame.draw.rect(surface, (50, 48, 55), (bar_x, content_top, 6, track_h), border_radius=3)
            pygame.draw.rect(surface, COLOR_ACCENT, (bar_x, thumb_y, 6, thumb_h), border_radius=3)

        # ── Hint ────────────────────────────────────────────────────
        hint = self._font_body.render(
            "[ESC / BACK]  Return    [UP / DOWN / Scroll]  Navigate",
            True, COLOR_TEXT_DIM,
        )
        surface.blit(hint, (SCREEN_WIDTH // 2 - hint.get_width() // 2, SCREEN_HEIGHT - 28))

        # ── Back button ─────────────────────────────────────────────
        if self._back_btn:
            self._back_btn.draw(surface)

    # ── Helpers ─────────────────────────────────────────────────────
    def _content_height(self) -> int:
        """Estimate the total pixel height of all sections."""
        if not self._font_heading or not self._font_body:
            return 0

        h = 0
        for heading, lines in _SECTIONS:
            h += self._font_heading.get_linesize() + 8
            h += len(lines) * (self._font_body.get_linesize() + 4)
            h += 22
        return h
