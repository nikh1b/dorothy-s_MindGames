"""
Dorothy's Mind Games - State Manager
=====================================
A stack-based state machine that governs the flow between
MainMenu → GameState → LimboState → GameOverState.

States are pushed/popped like a call-stack so that Limbo can
overlay the game and return to it when the puzzle is solved.
"""

from __future__ import annotations

from typing import Protocol

import pygame


# ── State Protocol ──────────────────────────────────────────────────
class GameStateProtocol(Protocol):
    """Every state must implement these four methods."""

    def enter(self) -> None: ...
    def exit(self) -> None: ...
    def handle_event(self, event: pygame.event.Event) -> None: ...
    def update(self, dt: float) -> None: ...
    def draw(self, surface: pygame.Surface) -> None: ...


# ── State Manager ───────────────────────────────────────────────────
class StateManager:
    """Stack-based finite state machine.

    * ``push(state)`` – push *state* on top (calls ``state.enter``).
    * ``pop()``       – remove the top state (calls ``state.exit``).
    * ``switch(state)`` – pop current, then push *state*.
    """

    def __init__(self) -> None:
        self._stack: list[GameStateProtocol] = []
        self._pending_push: GameStateProtocol | None = None
        self._pending_pop: bool = False
        self._pending_switch: GameStateProtocol | None = None

    # ── public API ──────────────────────────────────────────────────
    @property
    def current(self) -> GameStateProtocol | None:
        return self._stack[-1] if self._stack else None

    @property
    def is_empty(self) -> bool:
        return len(self._stack) == 0

    def push(self, state: GameStateProtocol) -> None:
        """Schedule *state* to be pushed at the end of the frame."""
        self._pending_push = state

    def pop(self) -> None:
        """Schedule the top state to be popped at the end of the frame."""
        self._pending_pop = True

    def switch(self, state: GameStateProtocol) -> None:
        """Schedule a pop-then-push (swap) at the end of the frame."""
        self._pending_switch = state

    # ── frame lifecycle ─────────────────────────────────────────────
    def process_pending(self) -> None:
        """Apply deferred push/pop/switch.  Call once per frame AFTER update."""
        if self._pending_switch is not None:
            if self._stack:
                self._stack[-1].exit()
                self._stack.pop()
            self._pending_switch.enter()
            self._stack.append(self._pending_switch)
            self._pending_switch = None
            return

        if self._pending_pop:
            if self._stack:
                self._stack[-1].exit()
                self._stack.pop()
                if self._stack:
                    self._stack[-1].enter()
            self._pending_pop = False

        if self._pending_push is not None:
            self._pending_push.enter()
            self._stack.append(self._pending_push)
            self._pending_push = None

    def handle_event(self, event: pygame.event.Event) -> None:
        if self.current:
            self.current.handle_event(event)

    def update(self, dt: float) -> None:
        if self.current:
            self.current.update(dt)

    def draw(self, surface: pygame.Surface) -> None:
        # Draw all states bottom-up so overlays (e.g. Limbo) can
        # render on top of the frozen game board.
        for state in self._stack:
            state.draw(surface)
