"""
Dorothy's Mind Games - Resource Manager
========================================
Manages the three core resources: Sanity, Soul, and Focus.
Also tracks Flow State streaks and Limbo trauma stacks.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from src.core.constants import (
    FOCUS_COST_GENIUS_VISION,
    FOCUS_REGEN_PER_TURN,
    FLOW_STATE_DURATION,
    FLOW_STATE_STREAK,
    MAX_FOCUS,
    MAX_SANITY,
    MAX_SOUL,
    SANITY_COST_LIMBO,
    SOUL_COST_REWIND,
)


@dataclass
class PlayerResources:
    """Mutable container for Dorothy's RPG-style resources."""

    # ── Core values ─────────────────────────────────────────────────
    sanity: int = MAX_SANITY
    sanity_max: int = MAX_SANITY  # can decrease from Limbo trauma
    soul: int = MAX_SOUL
    soul_max: int = MAX_SOUL
    focus: int = MAX_FOCUS
    focus_max: int = MAX_FOCUS

    # ── Flow State ──────────────────────────────────────────────────
    best_move_streak: int = 0
    flow_state_active: bool = False
    flow_state_timer: float = 0.0

    # ── Limbo statistics ────────────────────────────────────────────
    limbo_entries: int = 0
    trauma_stacks: int = 0

    # ── Move accuracy history ───────────────────────────────────────
    total_moves: int = 0
    brilliant_moves: int = 0
    best_moves: int = 0
    good_moves: int = 0
    inaccuracies: int = 0
    mistakes: int = 0
    blunders: int = 0

    # ── Sanity ──────────────────────────────────────────────────────
    def drain_sanity(self, amount: int) -> None:
        self.sanity = max(0, self.sanity - amount)

    def restore_sanity(self, amount: int) -> None:
        self.sanity = min(self.sanity_max, self.sanity + amount)

    def apply_limbo_trauma(self) -> None:
        """Permanent max-sanity reduction from a Limbo visit."""
        self.limbo_entries += 1
        self.trauma_stacks += 1
        self.sanity_max = max(20, self.sanity_max - SANITY_COST_LIMBO)
        self.sanity = min(self.sanity, self.sanity_max)

    @property
    def sanity_ratio(self) -> float:
        return self.sanity / self.sanity_max if self.sanity_max else 0.0

    @property
    def is_insane(self) -> bool:
        return self.sanity <= 0

    # ── Soul ────────────────────────────────────────────────────────
    def drain_soul(self, amount: int) -> None:
        self.soul = max(0, self.soul - amount)

    def restore_soul(self, amount: int) -> None:
        self.soul = min(self.soul_max, self.soul + amount)

    def spend_soul_for_rewind(self) -> bool:
        """Attempt to spend Soul for a Temporal Rewind.  Returns success."""
        if self.soul >= SOUL_COST_REWIND:
            self.soul -= SOUL_COST_REWIND
            return True
        return False

    @property
    def soul_ratio(self) -> float:
        return self.soul / self.soul_max if self.soul_max else 0.0

    @property
    def is_dead(self) -> bool:
        return self.soul <= 0

    # ── Focus ───────────────────────────────────────────────────────
    def spend_focus(self, amount: int = FOCUS_COST_GENIUS_VISION) -> bool:
        if self.focus >= amount:
            self.focus -= amount
            return True
        return False

    def regen_focus(self, multiplier: float = 1.0) -> None:
        regen = int(FOCUS_REGEN_PER_TURN * multiplier)
        self.focus = min(self.focus_max, self.focus + regen)

    @property
    def focus_ratio(self) -> float:
        return self.focus / self.focus_max if self.focus_max else 0.0

    # ── Flow State ──────────────────────────────────────────────────
    def register_best_move(self) -> None:
        self.best_move_streak += 1
        self.best_moves += 1
        self.total_moves += 1
        if self.best_move_streak >= FLOW_STATE_STREAK and not self.flow_state_active:
            self.flow_state_active = True
            self.flow_state_timer = FLOW_STATE_DURATION

    def break_streak(self) -> None:
        self.best_move_streak = 0
        self.flow_state_active = False
        self.flow_state_timer = 0.0

    def update_flow_timer(self, dt: float) -> None:
        if self.flow_state_active:
            self.flow_state_timer -= dt
            if self.flow_state_timer <= 0:
                self.flow_state_active = False
                self.flow_state_timer = 0.0

    # ── Accuracy ────────────────────────────────────────────────────
    @property
    def accuracy_percent(self) -> float:
        if self.total_moves == 0:
            return 100.0
        good = self.brilliant_moves + self.best_moves + self.good_moves
        return (good / self.total_moves) * 100.0
