"""
PixelLab-powered intro cinematic for Dorothy's Mind Games.

This version uses generated PixelLab character sprites and composes them
into a fully scripted four-scene intro with strict ordering, typewriter text,
and atmospheric transitions.
"""

from __future__ import annotations

from dataclasses import dataclass
from io import BytesIO
from pathlib import Path
from typing import TYPE_CHECKING
import math
import random
import urllib.request

import pygame

from src.core.constants import COLOR_BG, SCREEN_HEIGHT, SCREEN_WIDTH

if TYPE_CHECKING:
    from src.core.state_manager import StateManager


# -------------------- Visual palette --------------------
MIDNIGHT_TOP = (6, 12, 30)
MIDNIGHT_BOTTOM = (18, 30, 62)
STAGE_DARK = (10, 10, 16)
NEON_CYAN = (86, 224, 255)
BLOOD_RED = (186, 30, 56)
WINDOW_YELLOW = (236, 206, 115)
TEXT_WHITE = (238, 244, 255)
OFF_WHITE = (236, 240, 248)
SHADOW = (12, 12, 16)


# -------------------- Narrative script --------------------
# (time_from_scene_start, speaker, line)
DIALOGUE_CUES: dict[str, list[tuple[float, str, str]]] = {
    "exterior": [
        (0.2, "NARRATOR", "On this night, the impossible happened. The Titan fell."),
    ],
    "defeat": [
        (1.8, "SYSTEM", "Queen to H8. Checkmate."),
        (3.4, "NARRATOR", "Silence. Then the crowd erupted like thunder."),
        (5.2, "NARRATOR", "The Grandmaster laughed—proud, relieved, and free."),
    ],
    "warning": [
        (0.8, "GRANDMASTER", "...Finally. I am free of it."),
        (2.3, "DOROTHY", "Free?"),
        (3.3, "GRANDMASTER", "They cheer for you now, little genius. They see the crown."),
        (5.2, "GRANDMASTER", "They do not see the weight."),
        (6.3, "GRANDMASTER", "It is easy to climb. It is terrifying to stay at the summit."),
    ],
    "fracture": [
        (1.0, "GRANDMASTER", "Now you must face the burden of being No. 1."),
        (3.3, "VOICE", "Try to keep your Sanity. Only your moves will prevail now."),
    ],
}


# -------------------- PixelLab sprite URLs --------------------
# Pulled from the generated character outputs in this session.
DOROTHY_URLS: dict[str, str] = {
    "west": "https://backblaze.pixellab.ai/file/pixellab-characters/4540cfab-6348-4db3-a492-6c55e0b1c37e/64c63f37-31fa-4af3-b9c2-80091ab2fc82/rotations/west.png?t=1771147884581",
    "east": "https://backblaze.pixellab.ai/file/pixellab-characters/4540cfab-6348-4db3-a492-6c55e0b1c37e/64c63f37-31fa-4af3-b9c2-80091ab2fc82/rotations/east.png?t=1771147884581",
    "north-west": "https://backblaze.pixellab.ai/file/pixellab-characters/4540cfab-6348-4db3-a492-6c55e0b1c37e/64c63f37-31fa-4af3-b9c2-80091ab2fc82/rotations/north-west.png?t=1771147884581",
    "north-east": "https://backblaze.pixellab.ai/file/pixellab-characters/4540cfab-6348-4db3-a492-6c55e0b1c37e/64c63f37-31fa-4af3-b9c2-80091ab2fc82/rotations/north-east.png?t=1771147884581",
}

GRANDMASTER_URLS: dict[str, str] = {
    "west": "https://backblaze.pixellab.ai/file/pixellab-characters/4540cfab-6348-4db3-a492-6c55e0b1c37e/9b7d7e79-37f0-4177-9946-f8f1ea9fba40/rotations/west.png?t=1771147884628",
    "east": "https://backblaze.pixellab.ai/file/pixellab-characters/4540cfab-6348-4db3-a492-6c55e0b1c37e/9b7d7e79-37f0-4177-9946-f8f1ea9fba40/rotations/east.png?t=1771147884628",
    "north-west": "https://backblaze.pixellab.ai/file/pixellab-characters/4540cfab-6348-4db3-a492-6c55e0b1c37e/9b7d7e79-37f0-4177-9946-f8f1ea9fba40/rotations/north-west.png?t=1771147884628",
    "north-east": "https://backblaze.pixellab.ai/file/pixellab-characters/4540cfab-6348-4db3-a492-6c55e0b1c37e/9b7d7e79-37f0-4177-9946-f8f1ea9fba40/rotations/north-east.png?t=1771147884628",
}

# PixelLab-generated background tilesets (4x4 sheet, 16x16 each tile)
EXTERIOR_TILESET_URL = "https://api.pixellab.ai/mcp/tilesets/09a6e07d-b565-40fd-aa05-a0e6466a5467/image"
STAGE_TILESET_URL = "https://api.pixellab.ai/mcp/tilesets/5681e9c1-0d4f-45f8-aaac-eba34b5cbaac/image"
VOID_TILESET_URL = "https://api.pixellab.ai/mcp/tilesets/d20a6544-e213-4640-9be7-2994da8733d5/image"


# -------------------- Helpers --------------------
def clamp01(v: float) -> float:
    return max(0.0, min(1.0, v))


def ease(t: float) -> float:
    t = clamp01(t)
    return t * t * (3.0 - 2.0 * t)


def lerp(a: float, b: float, t: float) -> float:
    return a + (b - a) * clamp01(t)


def lerp_color(a: tuple[int, int, int], b: tuple[int, int, int], t: float) -> tuple[int, int, int]:
    return (
        int(lerp(a[0], b[0], t)),
        int(lerp(a[1], b[1], t)),
        int(lerp(a[2], b[2], t)),
    )


def build_gradient(height: int, top: tuple[int, int, int], bottom: tuple[int, int, int]) -> pygame.Surface:
    surf = pygame.Surface((SCREEN_WIDTH, height), pygame.SRCALPHA)
    for y in range(height):
        t = y / max(1, height - 1)
        col = lerp_color(top, bottom, t)
        pygame.draw.line(surf, col, (0, y), (SCREEN_WIDTH, y))
    return surf


def load_pixel_font(size: int) -> pygame.font.Font:
    candidates = [
        Path(r"D:\Nick-Works\dorothy's_MindGames\src\assets\fonts\PressStart2P-Regular.ttf"),
        Path(r"D:\Nick-Works\dorothy's_MindGames\assets\fonts\PressStart2P-Regular.ttf"),
        Path(r"D:\Nick-Works\dorothy's_MindGames\src\assets\fonts\Silver.ttf"),
        Path(r"D:\Nick-Works\dorothy's_MindGames\assets\fonts\Silver.ttf"),
    ]
    for path in candidates:
        if path.exists():
            return pygame.font.Font(str(path), size)
    return pygame.font.SysFont("consolas", size, bold=False)


def load_image_from_url(url: str, timeout: float = 8.0) -> pygame.Surface | None:
    try:
        req = urllib.request.Request(
            url,
            headers={
                "User-Agent": "DorothyMindGames/1.0",
                "Accept": "image/png,image/*;q=0.8,*/*;q=0.5",
            },
        )
        with urllib.request.urlopen(req, timeout=timeout) as response:
            data = response.read()
        image = pygame.image.load(BytesIO(data)).convert_alpha()
        return image
    except Exception:
        return None


@dataclass(frozen=True)
class Scene:
    name: str
    duration: float
    transition: float


@dataclass
class Snow:
    x: float
    y: float
    vy: float
    vx: float
    alpha: int
    size: int


class SceneManager:
    """Strictly sequential scene controller."""

    def __init__(self) -> None:
        self._timeline = [
            Scene("exterior", 9.0, 1.2),
            Scene("defeat", 8.5, 1.1),
            Scene("warning", 9.0, 1.4),
            Scene("fracture", 9.5, 0.0),
        ]
        self._index = 0
        self._scene_t = 0.0
        self._global_t = 0.0

    @property
    def name(self) -> str:
        return self._timeline[self._index].name

    @property
    def scene_time(self) -> float:
        return self._scene_t

    @property
    def scene_progress(self) -> float:
        d = self._timeline[self._index].duration
        if d <= 0:
            return 1.0
        return clamp01(self._scene_t / d)

    @property
    def transition_progress(self) -> float:
        scene = self._timeline[self._index]
        if scene.transition <= 0:
            return 0.0
        start = max(0.0, scene.duration - scene.transition)
        if self._scene_t <= start:
            return 0.0
        return clamp01((self._scene_t - start) / scene.transition)

    @property
    def global_time(self) -> float:
        return self._global_t

    def update(self, dt: float) -> bool:
        self._global_t += dt
        self._scene_t += dt
        scene = self._timeline[self._index]
        if self._scene_t < scene.duration:
            return False
        if self._index < len(self._timeline) - 1:
            self._index += 1
            self._scene_t = 0.0
            return True
        return False


class Typewriter:
    def __init__(self, cps: float = 22.0) -> None:
        self._cps = cps
        self._text = ""
        self._elapsed = 0.0

    def set_text(self, text: str) -> None:
        if text != self._text:
            self._text = text
            self._elapsed = 0.0

    def update(self, dt: float) -> None:
        self._elapsed += dt

    @property
    def text(self) -> str:
        n = int(self._elapsed * self._cps)
        n = max(0, min(n, len(self._text)))
        return self._text[:n]


class IntroState:
    """PixelLab-quality intro state."""

    def __init__(self, state_manager: "StateManager") -> None:
        self._sm = state_manager
        self._scene = SceneManager()
        self._typewriter = Typewriter(22.0)
        self._speaker = "NARRATOR"
        self._line = ""
        self._title_alpha = 0
        self._can_continue = False
        self._clack_flash = 0.0

        # layers
        self._world = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        self._fx = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        self._story = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)  # dedicated story layer

        self._rng = random.Random(1337)
        self._snow: list[Snow] = []

        self._font_dialogue: pygame.font.Font | None = None
        self._font_speaker: pygame.font.Font | None = None
        self._font_title: pygame.font.Font | None = None
        self._font_hint: pygame.font.Font | None = None

        # PixelLab sprites
        self._dorothy: dict[str, pygame.Surface] = {}
        self._grandmaster: dict[str, pygame.Surface] = {}
        self._bg_sheets: dict[str, pygame.Surface] = {}
        self._bg_tiles: dict[str, list[pygame.Surface]] = {}
        self._assets_ready = False

    def enter(self) -> None:
        self._font_dialogue = load_pixel_font(26)
        self._font_speaker = load_pixel_font(22)
        self._font_title = load_pixel_font(72)
        self._font_hint = load_pixel_font(16)
        self._set_dialogue("NARRATOR", "On this night, the impossible happened. The Titan fell.")
        self._init_snow()
        self._load_pixellab_assets()

    def exit(self) -> None:
        pass

    def handle_event(self, event: pygame.event.Event) -> None:
        if event.type != pygame.KEYDOWN:
            return
        if event.key == pygame.K_ESCAPE:
            self._go_to_menu()
            return
        if self._can_continue:
            self._go_to_menu()

    def update(self, dt: float) -> None:
        changed = self._scene.update(dt)
        self._typewriter.update(dt)
        self._update_snow(dt)
        self._clack_flash = max(0.0, self._clack_flash - dt)

        if changed:
            self._set_dialogue("", "")

        self._update_dialogue_timeline()

        if self._scene.name == "defeat" and 2.0 < self._scene.scene_time < 2.2 and self._clack_flash <= 0:
            self._clack_flash = 0.22

        if self._scene.name == "fracture":
            if self._scene.scene_progress > 0.35:
                self._title_alpha = int(255 * ease((self._scene.scene_progress - 0.35) / 0.5))
            if self._scene.scene_progress > 0.88:
                self._can_continue = True

    def draw(self, surface: pygame.Surface) -> None:
        self._world.fill((0, 0, 0, 0))
        self._fx.fill((0, 0, 0, 0))
        self._story.fill((0, 0, 0, 0))

        if self._scene.name == "exterior":
            self._draw_scene_exterior()
        elif self._scene.name == "defeat":
            self._draw_scene_defeat()
        elif self._scene.name == "warning":
            self._draw_scene_warning()
        else:
            self._draw_scene_fracture()

        self._draw_transition()
        self._draw_story_layer()
        self._draw_hint()

        surface.fill(COLOR_BG)
        surface.blit(self._world, (0, 0))
        surface.blit(self._fx, (0, 0))
        surface.blit(self._story, (0, 0))

    # -------------------- Scene render --------------------
    def _draw_scene_exterior(self) -> None:
        self._world.blit(build_gradient(SCREEN_HEIGHT, MIDNIGHT_TOP, MIDNIGHT_BOTTOM), (0, 0))
        # Base and depth layers from PixelLab exterior tiles
        self._draw_tiled_layer(self._world, "exterior", scale=20, alpha=150, seed_shift=1)
        self._draw_tiled_layer(self._fx, "exterior", scale=14, alpha=70, seed_shift=2)
        self._draw_film_grain(18)

        # Hall silhouette now textured with PixelLab exterior tiles
        hall_main = [(180, 590), (320, 190), (980, 190), (1100, 590)]
        hall_inner = [(260, 570), (395, 280), (900, 280), (1010, 570)]
        roof = [(248, 252), (640, 110), (1032, 252)]
        tower_l = [(310, 255), (372, 255), (360, 122), (322, 122)]
        tower_r = [(910, 255), (972, 255), (958, 136), (920, 136)]
        self._draw_textured_polygon(self._world, "exterior", hall_main, scale=14, alpha=220, seed_shift=3)
        self._draw_textured_polygon(self._world, "exterior", hall_inner, scale=12, alpha=210, seed_shift=4)
        self._draw_textured_polygon(self._world, "exterior", roof, scale=12, alpha=225, seed_shift=5)
        self._draw_textured_polygon(self._world, "exterior", tower_l, scale=10, alpha=225, seed_shift=6)
        self._draw_textured_polygon(self._world, "exterior", tower_r, scale=10, alpha=225, seed_shift=7)

        # crisp silhouette and readable sign so hall is unmistakable
        pygame.draw.polygon(self._fx, (4, 8, 16, 210), hall_main, 3)
        sign_rect = pygame.Rect(470, 360, 340, 72)
        pygame.draw.rect(self._fx, (222, 232, 246, 235), sign_rect, border_radius=4)
        pygame.draw.rect(self._fx, (28, 40, 62, 255), sign_rect, 2, border_radius=4)
        if self._font_hint:
            s1 = self._font_hint.render("WORLD CHESS", True, (24, 34, 58))
            s2 = self._font_hint.render("CHAMPIONSHIP", True, (24, 34, 58))
            self._fx.blit(s1, (sign_rect.centerx - s1.get_width() // 2, sign_rect.y + 14))
            self._fx.blit(s2, (sign_rect.centerx - s2.get_width() // 2, sign_rect.y + 38))

        # Window slits with glow
        for i in range(10):
            y = 306 + i * 20
            glow = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
            pygame.draw.line(glow, (255, 220, 132, 62), (502, y), (778, y), 4)
            pygame.draw.line(self._world, WINDOW_YELLOW, (506, y), (774, y), 2)
            self._fx.blit(glow, (0, 0))

        # Ground
        pygame.draw.polygon(self._world, (10, 14, 24), [(0, 558), (1280, 558), (1280, 720), (0, 720)])
        pygame.draw.polygon(self._world, (14, 18, 28), [(420, 558), (860, 558), (770, 720), (510, 720)])

        # Spotlights
        spot = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        pygame.draw.polygon(spot, (120, 220, 255, 36), [(130, 545), (352, 196), (500, 196)])
        pygame.draw.polygon(spot, (120, 220, 255, 36), [(1150, 545), (780, 196), (928, 196)])
        self._fx.blit(spot, (0, 0))

        self._draw_snow()

    def _draw_scene_defeat(self) -> None:
        self._world.blit(build_gradient(SCREEN_HEIGHT, (8, 10, 18), (24, 18, 28)), (0, 0))
        self._draw_tiled_layer(self._world, "stage", scale=16, alpha=170, seed_shift=20)
        self._draw_film_grain(12)

        # Dark stage + spotlight
        pygame.draw.polygon(self._world, (20, 14, 20), [(220, 548), (1060, 548), (1240, 720), (40, 720)])
        spot = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        pygame.draw.polygon(spot, (255, 255, 255, 68), [(640, 28), (484, 542), (796, 542)])
        pygame.draw.polygon(spot, (255, 255, 255, 32), [(640, 28), (430, 640), (850, 640)])
        self._fx.blit(spot, (0, 0))

        # Table / board
        table_poly = [(494, 522), (786, 522), (740, 616), (540, 616)]
        board_poly = [(556, 506), (724, 506), (697, 564), (583, 564)]
        self._draw_textured_polygon(self._world, "stage", table_poly, scale=10, alpha=230, seed_shift=21)
        self._draw_textured_polygon(self._world, "stage", board_poly, scale=8, alpha=235, seed_shift=22)
        self._draw_board_lines(board_poly)

        # Handshake action
        shake_y = int(470 + math.sin(self._scene.scene_time * 2.4) * 1.8)
        self._draw_character("dorothy", "east", (470, 476), scale=4.5)
        laugh_shake = int(math.sin(self._scene.scene_time * 21.0) * 4) if self._scene.scene_time > 2.1 else 0
        self._draw_character("grandmaster", "west", (760, 458 + laugh_shake), scale=4.8)
        pygame.draw.line(self._fx, OFF_WHITE, (565, shake_y), (706, shake_y - 8), 3)

        # Piece move + clack flash
        piece_t = ease(min(1.0, self._scene.scene_time / 2.0))
        px = int(lerp(592, 664, piece_t))
        pygame.draw.polygon(self._fx, (220, 232, 250, 220), [(px, 530), (px + 8, 517), (px + 16, 530), (px + 8, 542)])

        if self._clack_flash > 0:
            flash = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
            flash.fill((255, 255, 255, int(125 * (self._clack_flash / 0.22))))
            self._fx.blit(flash, (0, 0))

    def _draw_scene_warning(self) -> None:
        self._world.blit(build_gradient(SCREEN_HEIGHT, (30, 8, 18), (70, 10, 22)), (0, 0))
        self._draw_tiled_layer(self._world, "void", scale=14, alpha=150, seed_shift=30)
        self._draw_tiled_layer(self._fx, "stage", scale=12, alpha=80, seed_shift=31)
        self._draw_film_grain(20)

        # fracture shards
        pygame.draw.polygon(self._world, (92, 20, 34), [(0, 186), (420, 142), (365, 236), (0, 274)])
        pygame.draw.polygon(self._world, (92, 20, 34), [(1280, 144), (878, 196), (912, 284), (1280, 250)])
        pygame.draw.polygon(self._world, (92, 20, 34), [(250, 490), (640, 434), (716, 562), (290, 606)])

        # frozen stance
        self._draw_character("dorothy", "east", (490, 486), scale=4.5)
        self._draw_character("grandmaster", "west", (760, 458), scale=4.8, silhouette=True)

        # glitch row offset (pulsed, not constant)
        if int(self._scene.global_time * 5) % 3 == 0:
            src = self._world.copy()
            self._world.fill((0, 0, 0, 0))
            row_h = 4
            for y in range(0, SCREEN_HEIGHT, row_h):
                dx = random.randint(-18, 18) if random.random() < 0.28 else 0
                rect = pygame.Rect(0, y, SCREEN_WIDTH, min(row_h, SCREEN_HEIGHT - y))
                self._world.blit(src, (dx, y), rect)

        red_wash = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        red_wash.fill((BLOOD_RED[0], BLOOD_RED[1], BLOOD_RED[2], 58))
        self._fx.blit(red_wash, (0, 0))

    def _draw_scene_fracture(self) -> None:
        self._world.fill((0, 0, 0, 255))
        self._draw_tiled_layer(self._world, "void", scale=16, alpha=155, seed_shift=40)

        # chess-grid void
        for x in range(0, SCREEN_WIDTH, 52):
            pygame.draw.line(self._world, (18, 28, 48), (x, SCREEN_HEIGHT // 2), (x + 180, SCREEN_HEIGHT), 1)
        for y in range(SCREEN_HEIGHT // 2, SCREEN_HEIGHT, 24):
            pygame.draw.line(self._world, (16, 24, 42), (0, y), (SCREEN_WIDTH, y), 1)

        self._draw_eye_glow(520, 328)
        self._draw_eye_glow(760, 328)

        if self._font_title and self._title_alpha > 0:
            title = self._font_title.render("DOROTHY'S MIND GAMES", True, (214, 234, 255))
            title.set_alpha(self._title_alpha)
            self._fx.blit(title, (SCREEN_WIDTH // 2 - title.get_width() // 2, 96))

    # -------------------- Story/UI layer --------------------
    def _draw_story_layer(self) -> None:
        if not self._font_dialogue or not self._font_speaker:
            return

        bar_h = int(SCREEN_HEIGHT * 0.20)
        bar = pygame.Surface((SCREEN_WIDTH, bar_h), pygame.SRCALPHA)
        bar.fill((0, 0, 0, 150))
        self._story.blit(bar, (0, SCREEN_HEIGHT - bar_h))

        sp_col = NEON_CYAN if self._speaker != "GRANDMASTER" else (240, 240, 240)
        sp = self._font_speaker.render(f"[{self._speaker}]", True, sp_col)
        self._story.blit(sp, (36, SCREEN_HEIGHT - bar_h + 18))

        txt = self._typewriter.text
        line = self._font_dialogue.render(txt, True, TEXT_WHITE)
        tx = (SCREEN_WIDTH - line.get_width()) // 2
        ty = SCREEN_HEIGHT - bar_h + (bar_h - line.get_height()) // 2 + 16
        self._story.blit(line, (tx, ty))

    def _draw_hint(self) -> None:
        if not self._font_hint:
            return
        hint = "PRESS ANY KEY" if self._can_continue else "ESC TO SKIP"
        surf = self._font_hint.render(hint, True, (152, 166, 190))
        self._story.blit(surf, (SCREEN_WIDTH - surf.get_width() - 24, 18))

    # -------------------- Effects/helpers --------------------
    def _draw_transition(self) -> None:
        t = self._scene.transition_progress
        if t <= 0:
            return
        ov = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        ov.fill((0, 0, 0, int(165 * t)))
        self._fx.blit(ov, (0, 0))

    def _draw_snow(self) -> None:
        layer = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        for p in self._snow:
            layer.set_at((int(p.x), int(p.y)), (246, 248, 255, p.alpha))
            if p.size > 1 and int(p.x) + 1 < SCREEN_WIDTH:
                layer.set_at((int(p.x) + 1, int(p.y)), (246, 248, 255, p.alpha // 2))
        self._fx.blit(layer, (0, 0))

    def _draw_film_grain(self, strength: int) -> None:
        grain = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        for _ in range(3000):
            x = self._rng.randint(0, SCREEN_WIDTH - 1)
            y = self._rng.randint(0, SCREEN_HEIGHT - 1)
            a = self._rng.randint(0, strength)
            grain.set_at((x, y), (255, 255, 255, a))
        self._fx.blit(grain, (0, 0))

    def _draw_eye_glow(self, x: int, y: int) -> None:
        glow = pygame.Surface((260, 260), pygame.SRCALPHA)
        cx, cy = 130, 130
        for r, a in [(98, 16), (74, 28), (52, 52), (32, 100), (16, 215)]:
            pygame.draw.circle(glow, (NEON_CYAN[0], NEON_CYAN[1], NEON_CYAN[2], a), (cx, cy), r)
        self._fx.blit(glow, (x - 130, y - 130))
        pygame.draw.circle(self._fx, (214, 245, 255), (x, y), 6)

    def _draw_board_lines(self, board_poly: list[tuple[int, int]]) -> None:
        layer = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        x1, y1 = board_poly[0]
        x2, y2 = board_poly[1]
        x3, y3 = board_poly[2]
        x4, y4 = board_poly[3]
        for i in range(1, 8):
            t = i / 8.0
            ax = int(lerp(x1, x2, t))
            ay = int(lerp(y1, y2, t))
            bx = int(lerp(x4, x3, t))
            by = int(lerp(y4, y3, t))
            pygame.draw.line(layer, (82, 92, 112, 115), (ax, ay), (bx, by), 1)
        for i in range(1, 5):
            t = i / 5.0
            ax = int(lerp(x1, x4, t))
            ay = int(lerp(y1, y4, t))
            bx = int(lerp(x2, x3, t))
            by = int(lerp(y2, y3, t))
            pygame.draw.line(layer, (82, 92, 112, 115), (ax, ay), (bx, by), 1)
        self._fx.blit(layer, (0, 0))

    def _slice_tilesheet(self, sheet: pygame.Surface, tile_size: int = 16) -> list[pygame.Surface]:
        tiles: list[pygame.Surface] = []
        sw, sh = sheet.get_size()
        for y in range(0, sh, tile_size):
            for x in range(0, sw, tile_size):
                rect = pygame.Rect(x, y, tile_size, tile_size)
                tiles.append(sheet.subsurface(rect).copy())
        return tiles

    def _draw_tiled_layer(
        self,
        target: pygame.Surface,
        key: str,
        *,
        scale: int = 12,
        alpha: int = 255,
        seed_shift: int = 0,
    ) -> None:
        tiles = self._bg_tiles.get(key)
        if not tiles:
            return
        tile_px = max(8, scale)
        cols = SCREEN_WIDTH // tile_px + 2
        rows = SCREEN_HEIGHT // tile_px + 2
        for gy in range(rows):
            for gx in range(cols):
                # deterministic tile choice (no temporal flicker)
                idx = (gx * 31 + gy * 17 + seed_shift * 13) % len(tiles)
                src = tiles[idx]
                tile = pygame.transform.scale(src, (tile_px, tile_px))
                if alpha < 255:
                    tile.set_alpha(alpha)
                target.blit(tile, (gx * tile_px - tile_px // 2, gy * tile_px - tile_px // 2))

    def _draw_textured_polygon(
        self,
        target: pygame.Surface,
        key: str,
        polygon: list[tuple[int, int]],
        *,
        scale: int = 12,
        alpha: int = 255,
        seed_shift: int = 0,
    ) -> None:
        # Fill polygon with pixellab tile texture.
        mask = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        pygame.draw.polygon(mask, (255, 255, 255, 255), polygon)
        tex = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        self._draw_tiled_layer(tex, key, scale=scale, alpha=alpha, seed_shift=seed_shift)
        tex.blit(mask, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
        target.blit(tex, (0, 0))

    def _draw_character(
        self,
        which: str,
        direction: str,
        pos: tuple[int, int],
        *,
        scale: float,
        silhouette: bool = False,
    ) -> None:
        sprite_map = self._dorothy if which == "dorothy" else self._grandmaster
        surf = sprite_map.get(direction)
        if surf is None:
            # fallback silhouette block if loading fails
            x, y = pos
            color = SHADOW if silhouette else (16, 18, 24)
            pygame.draw.polygon(
                self._world,
                color,
                [(x, y + 42), (x + 18, y - 38), (x + 46, y - 30), (x + 40, y + 42)],
            )
            return

        w = int(surf.get_width() * scale)
        h = int(surf.get_height() * scale)
        sprite = pygame.transform.scale(surf, (w, h))
        if silhouette:
            sil = sprite.copy()
            sil.fill((12, 12, 16, 240), special_flags=pygame.BLEND_RGBA_MULT)
            sprite = sil
        self._world.blit(sprite, pos)

    # -------------------- Data setup --------------------
    def _set_dialogue(self, speaker: str, text: str) -> None:
        if speaker == self._speaker and text == self._line:
            return
        self._speaker = speaker
        self._line = text
        self._typewriter.set_text(text)

    def _update_dialogue_timeline(self) -> None:
        cues = DIALOGUE_CUES.get(self._scene.name, [])
        if not cues:
            self._set_dialogue("", "")
            return
        st = self._scene.scene_time
        chosen: tuple[str, str] | None = None
        for t, speaker, text in cues:
            if st >= t:
                chosen = (speaker, text)
            else:
                break
        if chosen is None:
            self._set_dialogue("", "")
            return
        self._set_dialogue(chosen[0], chosen[1])

    def _init_snow(self) -> None:
        self._snow.clear()
        for _ in range(320):
            self._snow.append(
                Snow(
                    x=random.uniform(0, SCREEN_WIDTH),
                    y=random.uniform(-SCREEN_HEIGHT, SCREEN_HEIGHT),
                    vy=random.uniform(24, 165),
                    vx=random.uniform(-40, -8),
                    alpha=random.randint(80, 220),
                    size=random.choice([1, 1, 1, 2]),
                )
            )

    def _update_snow(self, dt: float) -> None:
        if self._scene.name != "exterior":
            return
        for p in self._snow:
            p.y += p.vy * dt
            p.x += p.vx * dt
            if p.y > SCREEN_HEIGHT:
                p.y = random.uniform(-32, -4)
                p.x = random.uniform(0, SCREEN_WIDTH)

    def _load_pixellab_assets(self) -> None:
        self._dorothy.clear()
        self._grandmaster.clear()
        self._bg_sheets.clear()
        self._bg_tiles.clear()

        # Attempt network loading; if unavailable, scene still runs with fallback silhouettes.
        for key, url in DOROTHY_URLS.items():
            img = load_image_from_url(url)
            if img is not None:
                self._dorothy[key] = img

        for key, url in GRANDMASTER_URLS.items():
            img = load_image_from_url(url)
            if img is not None:
                self._grandmaster[key] = img

        bg_sources = {
            "exterior": EXTERIOR_TILESET_URL,
            "stage": STAGE_TILESET_URL,
            "void": VOID_TILESET_URL,
        }
        for key, url in bg_sources.items():
            img = load_image_from_url(url)
            if img is not None:
                self._bg_sheets[key] = img
                self._bg_tiles[key] = self._slice_tilesheet(img, tile_size=16)

        self._assets_ready = bool(self._dorothy) and bool(self._grandmaster)

    def _go_to_menu(self) -> None:
        from src.states.main_menu_state import MainMenuState

        self._sm.switch(MainMenuState(self._sm))

