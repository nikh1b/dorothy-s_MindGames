"""
Dorothy's Mind Games - Global Constants
========================================
All magic numbers, colors, and configuration values live here.
"""

from __future__ import annotations

# ── Window ──────────────────────────────────────────────────────────
SCREEN_WIDTH: int = 1280
SCREEN_HEIGHT: int = 720
FPS: int = 60
TITLE: str = "Dorothy's Mind Games"

# ── Board Layout ────────────────────────────────────────────────────
BOARD_SIZE: int = 8
SQUARE_SIZE: int = 80  # px per square
BOARD_ORIGIN_X: int = 40  # left margin
BOARD_ORIGIN_Y: int = 40  # top margin
BOARD_PIXEL_SIZE: int = SQUARE_SIZE * BOARD_SIZE  # 640

# ── UI Panel (right side) ──────────────────────────────────────────
PANEL_X: int = BOARD_ORIGIN_X + BOARD_PIXEL_SIZE + 20  # 700
PANEL_Y: int = 40
PANEL_WIDTH: int = SCREEN_WIDTH - PANEL_X - 20  # ~520
PANEL_HEIGHT: int = SCREEN_HEIGHT - 80

# ── Evaluation Bar ──────────────────────────────────────────────────
EVAL_BAR_X: int = PANEL_X
EVAL_BAR_Y: int = PANEL_Y
EVAL_BAR_WIDTH: int = 30
EVAL_BAR_HEIGHT: int = BOARD_PIXEL_SIZE
EVAL_BAR_MAX_CP: int = 1000  # clamp centipawns to ±1000 for display

# ── Colors ──────────────────────────────────────────────────────────
# Board
COLOR_LIGHT_SQUARE: tuple[int, int, int] = (234, 226, 206)
COLOR_DARK_SQUARE: tuple[int, int, int] = (119, 149, 86)
COLOR_HIGHLIGHT: tuple[int, int, int, int] = (255, 255, 0, 100)
COLOR_LEGAL_MOVE: tuple[int, int, int, int] = (100, 200, 100, 120)
COLOR_LAST_MOVE: tuple[int, int, int, int] = (180, 180, 50, 80)
COLOR_CHECK: tuple[int, int, int, int] = (255, 50, 50, 120)

# UI
COLOR_BG: tuple[int, int, int] = (22, 21, 25)
COLOR_PANEL_BG: tuple[int, int, int] = (32, 31, 38)
COLOR_TEXT: tuple[int, int, int] = (220, 218, 225)
COLOR_TEXT_DIM: tuple[int, int, int] = (130, 128, 135)
COLOR_ACCENT: tuple[int, int, int] = (170, 130, 255)
COLOR_DANGER: tuple[int, int, int] = (255, 70, 70)
COLOR_SAFE: tuple[int, int, int] = (70, 200, 120)
COLOR_WHITE_EVAL: tuple[int, int, int] = (245, 245, 245)
COLOR_BLACK_EVAL: tuple[int, int, int] = (30, 30, 30)

# Buttons
COLOR_BTN_NORMAL: tuple[int, int, int] = (42, 40, 50)
COLOR_BTN_HOVER: tuple[int, int, int] = (62, 58, 75)
COLOR_BTN_BORDER: tuple[int, int, int] = (90, 85, 110)
COLOR_BTN_BORDER_HOVER: tuple[int, int, int] = (170, 130, 255)  # accent border on hover
COLOR_BTN_TEXT: tuple[int, int, int] = (220, 218, 225)

# ── Intro Cutscene Palette ────────────────────────────────────────
# Warm tournament hall colours
CS_GOLD: tuple[int, int, int] = (218, 175, 80)
CS_WARM_BROWN: tuple[int, int, int] = (92, 64, 42)
CS_DEEP_RED: tuple[int, int, int] = (140, 30, 30)
CS_SPOTLIGHT: tuple[int, int, int] = (255, 240, 200)
CS_CROWD_DIM: tuple[int, int, int] = (35, 28, 22)
CS_WOOD: tuple[int, int, int] = (110, 75, 48)
CS_SKIN_LIGHT: tuple[int, int, int] = (235, 200, 170)
CS_SKIN_SHADOW: tuple[int, int, int] = (180, 140, 110)
CS_DOROTHY_HAIR: tuple[int, int, int] = (50, 35, 60)
CS_DOROTHY_EYE: tuple[int, int, int] = (80, 160, 255)
CS_GM_BEARD: tuple[int, int, int] = (170, 165, 160)
CS_GM_SUIT: tuple[int, int, int] = (45, 42, 50)
# Cold void colours (palette shift target)
CS_VOID_PURPLE: tuple[int, int, int] = (40, 20, 65)
CS_VOID_BLUE: tuple[int, int, int] = (30, 35, 80)
CS_COLD_WHITE: tuple[int, int, int] = (200, 205, 220)
CS_SANITY_RED: tuple[int, int, int] = (220, 40, 40)
# Pixel art render scale
CS_PIXEL_SCALE: int = 4  # render at 320×180, upscale 4×

# Heaven / Limbo / Hell
COLOR_HEAVEN_TINT: tuple[int, int, int] = (220, 240, 255)
COLOR_LIMBO_TINT: tuple[int, int, int] = (60, 60, 70)
COLOR_HELL_TINT: tuple[int, int, int] = (100, 20, 20)

# ── Resources ───────────────────────────────────────────────────────
MAX_SANITY: int = 100
MAX_SOUL: int = 100
MAX_FOCUS: int = 100
FOCUS_REGEN_PER_TURN: int = 8
FOCUS_COST_GENIUS_VISION: int = 15
SANITY_COST_LIMBO: int = 20
SOUL_COST_REWIND: int = 25

# ── Blunder Detection ──────────────────────────────────────────────
BLUNDER_THRESHOLD_CP: int = 200  # centipawn drop to trigger Limbo
MISTAKE_THRESHOLD_CP: int = 100
INACCURACY_THRESHOLD_CP: int = 50

# ── Limbo Puzzles ──────────────────────────────────────────────────
LIMBO_PUZZLE_TIME_LIMIT: float = 60.0  # seconds
LIMBO_PUZZLES_REQUIRED: int = 3

# ── Flow State ──────────────────────────────────────────────────────
FLOW_STATE_STREAK: int = 3  # consecutive best-moves to trigger
FLOW_STATE_DURATION: float = 15.0  # seconds

# ── Stockfish ───────────────────────────────────────────────────────
STOCKFISH_DEFAULT_DEPTH: int = 18
STOCKFISH_ANALYSIS_DEPTH: int = 22
STOCKFISH_PATH: str = r"D:\Nick-Works\dorothy's_MindGames\stockfish\stockfish-windows-x86-64-avx2.exe"

# ── Piece Unicode (fallback when no sprites) ───────────────────────
PIECE_UNICODE: dict[str, str] = {
    "K": "\u2654", "Q": "\u2655", "R": "\u2656", "B": "\u2657", "N": "\u2658", "P": "\u2659",
    "k": "\u265A", "q": "\u265B", "r": "\u265C", "b": "\u265D", "n": "\u265E", "p": "\u265F",
}
