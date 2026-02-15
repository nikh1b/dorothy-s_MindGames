"""
Dorothy's Mind Games - Opponent Personas
=========================================
AI opponents with distinct personalities, configured via
Stockfish UCI parameters.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum, auto


class PersonaType(Enum):
    BERSERKER = auto()
    GATEKEEPER = auto()
    SHADOW_SELF = auto()
    PRODIGY = auto()
    ENDGAME_MASTER = auto()


@dataclass(frozen=True)
class OpponentPersona:
    """Configuration for an AI opponent personality."""
    name: str
    persona_type: PersonaType
    description: str
    elo: int                     # UCI_Elo setting
    contempt: int = 0            # how aggressively to avoid draws
    skill_level: int = 20        # 0-20 Stockfish skill
    move_time_ms: int = 2000     # time per move in milliseconds
    opening_preference: str = "" # preferred opening (narrative flavour)
    taunt_lines: tuple[str, ...] = ()

    def uci_options(self) -> dict[str, str]:
        """Return the UCI setoption commands for this persona."""
        opts: dict[str, str] = {
            "UCI_LimitStrength": "true",
            "UCI_Elo": str(self.elo),
            "Skill Level": str(self.skill_level),
            "Contempt": str(self.contempt),
        }
        return opts


# ── Pre-built Personas ──────────────────────────────────────────────
BERSERKER = OpponentPersona(
    name="The Berserker",
    persona_type=PersonaType.BERSERKER,
    description="A reckless attacker who sacrifices pieces for initiative.",
    elo=1400,
    contempt=100,
    skill_level=10,
    move_time_ms=1000,
    opening_preference="King's Gambit / Sicilian Dragon",
    taunt_lines=(
        "You think too much. I act.",
        "Every piece I sacrifice brings me closer to your King.",
        "Hesitation is the first step to defeat.",
    ),
)

GATEKEEPER = OpponentPersona(
    name="The Gatekeeper",
    persona_type=PersonaType.GATEKEEPER,
    description="A fortress builder who grinds opponents in closed positions.",
    elo=1600,
    contempt=-50,
    skill_level=14,
    move_time_ms=3000,
    opening_preference="London System / Caro-Kann",
    taunt_lines=(
        "Patience is the highest form of intelligence.",
        "Your attack crumbles against my walls.",
        "In time, even mountains erode. So will you.",
    ),
)

SHADOW_SELF = OpponentPersona(
    name="The Shadow Self",
    persona_type=PersonaType.SHADOW_SELF,
    description="A mirror that plays your own style back at you.",
    elo=1800,
    contempt=0,
    skill_level=16,
    move_time_ms=2000,
    opening_preference="Mirror / Your favourite lines",
    taunt_lines=(
        "I know every move you'll make... because I am you.",
        "You cannot defeat yourself, Dorothy.",
        "Look into the board. Do you see me, or do you see you?",
    ),
)

PRODIGY = OpponentPersona(
    name="The Prodigy",
    persona_type=PersonaType.PRODIGY,
    description="A terrifyingly accurate child who sees 20 moves ahead.",
    elo=2200,
    contempt=0,
    skill_level=20,
    move_time_ms=2500,
    opening_preference="Ruy Lopez / Nimzo-Indian",
    taunt_lines=(
        "Checkmate in twelve. You just don't see it yet.",
        "Your moves are... adequate.",
        "I solved this position before you sat down.",
    ),
)

ENDGAME_MASTER = OpponentPersona(
    name="The Endgame Master",
    persona_type=PersonaType.ENDGAME_MASTER,
    description="A patient ghost who thrives when the board empties.",
    elo=1900,
    contempt=-25,
    skill_level=18,
    move_time_ms=3500,
    opening_preference="Queen's Gambit Declined / Endgame Tablebase",
    taunt_lines=(
        "The fewer the pieces, the louder the silence.",
        "In the endgame, truth is revealed.",
        "You trade pieces to simplify. I trade pieces to win.",
    ),
)

ALL_PERSONAS: list[OpponentPersona] = [BERSERKER, GATEKEEPER, SHADOW_SELF, PRODIGY, ENDGAME_MASTER]
