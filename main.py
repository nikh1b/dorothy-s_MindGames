"""
Dorothy's Mind Games
=====================
A narrative-driven chess roguelike where moves decide everything.

Entry point — initialises Pygame, creates the state machine,
and runs the main game loop at 60 FPS.

Controls:
  Mouse Left    — Select / move pieces
  Mouse Right   — Hold for Genius Vision (PV preview)
  G             — Toggle Genius Vision (costs Focus)
  T             — Toggle Threat Map overlay
  R             — Temporal Rewind (costs Soul)
  F             — Flip board
  ESC           — Menu / Quit
"""

from __future__ import annotations

import sys

import pygame

from src.core.constants import FPS, SCREEN_HEIGHT, SCREEN_WIDTH, TITLE
from src.core.state_manager import StateManager
from src.states.intro_state import IntroState


class Game:
    """Top-level application: owns the window, clock, and state machine."""

    def __init__(self) -> None:
        pygame.init()
        pygame.display.set_caption(TITLE)
        self._screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        self._clock = pygame.time.Clock()
        self._running = True

        # State machine — start with the intro cinematic
        self._state_manager = StateManager()
        self._state_manager.push(IntroState(self._state_manager))
        self._state_manager.process_pending()  # immediately push the intro

    def run(self) -> None:
        """Main loop."""
        while self._running:
            dt = self._clock.tick(FPS) / 1000.0  # seconds

            # ── Events ──────────────────────────────────────────────
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self._running = False
                    break
                self._state_manager.handle_event(event)

            # ── Update ──────────────────────────────────────────────
            self._state_manager.update(dt)
            self._state_manager.process_pending()

            # Exit if stack is empty
            if self._state_manager.is_empty:
                self._running = False
                break

            # ── Draw ────────────────────────────────────────────────
            self._state_manager.draw(self._screen)
            pygame.display.flip()

        pygame.quit()
        sys.exit()


def main() -> None:
    game = Game()
    game.run()


if __name__ == "__main__":
    main()
