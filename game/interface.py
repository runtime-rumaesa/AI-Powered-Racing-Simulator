"""Menu screens for the game: the main menu, where the player picks the AI lineup.

The menu never starts a race itself. handle_event() returns what the player
asked for and main.py acts on it:

    None                          nothing happened
    ("start", preset, laps, weather)   start a race against this lineup
    ("quit",)                     leave the game

Keys
----
    UP / DOWN   (W / S)   move between the rows
    LEFT / RIGHT (A / D)  change the lineup (or the laps / the weather, on their rows)
    1 2 3 4               pick a lineup directly
    ENTER / SPACE         start the race
    ESC                   quit
"""

import math

import pygame

from settings import *
from game.race import RACE_PRESETS, lineup_names
from game.track import get_track, draw_track

# A full tank lasts about three laps (FUEL_MAX / FUEL_USE_PER_FRAME) and there are no pit stops yet,
# so longer races could not be finished. Add 5 and 8 back together with the pit stops.
LAP_CHOICES = (1, 2, 3)

# What each strategy is made of: the route it drives and the driving style it uses
STRATEGY_INFO = {
    "astar": "A* route, default style",
    "bfs": "BFS route, default style",
    "baseline": "centre line, default style",
    "hc": "A* route, Hill Climbing style",
    "ga": "A* route, Genetic style",
}

WEATHER_COLORS = {"Clear": (255, 214, 64), "Cloudy": (195, 205, 220), "Rainy": (110, 165, 255)}
PANEL = (12, 16, 28, 215)
DIM = (150, 158, 175)
ROW_OFF = (30, 36, 54)
ROW_ON = (44, 54, 84)


def wrap(font, text, width):
    """Split text into lines that fit `width` pixels."""
    lines, line = [], ""
    for word in text.split():
        trial = f"{line} {word}".strip()
        if font.size(trial)[0] <= width:
            line = trial
        else:
            lines.append(line)
            line = word
    if line:
        lines.append(line)
    return lines


class MainMenu:
    """Title screen with the lineup selector. Create it after pygame.init()."""

    ROWS = ("lineup", "laps", "weather", "start", "quit")

    def __init__(self, preset_index=0, laps=NUM_LAPS):
        self.f_title = pygame.font.SysFont("arial", 56, bold=True)
        self.f_big = pygame.font.SysFont("arial", 30, bold=True)
        self.f_mid = pygame.font.SysFont("arial", 20, bold=True)
        self.f_small = pygame.font.SysFont("arial", 14, bold=True)
        self.f_text = pygame.font.SysFont("arial", 15)

        self.preset_index = preset_index % len(RACE_PRESETS)
        self.laps_index = LAP_CHOICES.index(laps) if laps in LAP_CHOICES else LAP_CHOICES.index(3)
        self.weather_index = 0
        self.row = self.ROWS.index("start")

        self.track = get_track()
        self.backdrop = pygame.Surface((WIDTH, HEIGHT))
        draw_track(self.backdrop)
        shade = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        shade.fill((6, 9, 18, 175))
        self.backdrop.blit(shade, (0, 0))
        self.ticks = 0

    # ---------------------------------------------------------------- state
    @property
    def preset(self):
        return RACE_PRESETS[self.preset_index]

    @property
    def laps(self):
        return LAP_CHOICES[self.laps_index]

    @property
    def weather(self):
        return WEATHER_NAMES[self.weather_index]

    def _change(self, step):
        if self.ROWS[self.row] == "laps":
            self.laps_index = (self.laps_index + step) % len(LAP_CHOICES)
        elif self.ROWS[self.row] == "weather":
            self.weather_index = (self.weather_index + step) % len(WEATHER_NAMES)
        else:
            self.preset_index = (self.preset_index + step) % len(RACE_PRESETS)

    def _start(self):
        return ("start", self.preset, self.laps, self.weather)

    # ---------------------------------------------------------------- input
    def handle_event(self, event):
        if event.type != pygame.KEYDOWN:
            return None
        key = event.key

        if key == pygame.K_ESCAPE:
            return ("quit",)
        if key in (pygame.K_UP, pygame.K_w):
            self.row = (self.row - 1) % len(self.ROWS)
        elif key in (pygame.K_DOWN, pygame.K_s):
            self.row = (self.row + 1) % len(self.ROWS)
        elif key in (pygame.K_LEFT, pygame.K_a):
            self._change(-1)
        elif key in (pygame.K_RIGHT, pygame.K_d):
            self._change(+1)
        elif key == pygame.K_TAB:
            self.preset_index = (self.preset_index + 1) % len(RACE_PRESETS)
        elif pygame.K_1 <= key <= pygame.K_9 or pygame.K_KP1 <= key <= pygame.K_KP9:
            number = key - pygame.K_1 if key <= pygame.K_9 else key - pygame.K_KP1
            if number < len(RACE_PRESETS):
                self.preset_index = number
        elif key in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE):
            return ("quit",) if self.ROWS[self.row] == "quit" else self._start()
        return None

    def update(self):
        self.ticks += 1

    # -------------------------------------------------------------- drawing
    @staticmethod
    def _text(screen, font, text, pos, color=WHITE, anchor="center", shadow=True):
        if shadow:
            s = font.render(text, True, (0, 0, 0))
            screen.blit(s, s.get_rect(**{anchor: (pos[0] + 2, pos[1] + 2)}))
        surf = font.render(text, True, color)
        screen.blit(surf, surf.get_rect(**{anchor: pos}))

    @staticmethod
    def _arrow(screen, cx, cy, direction, color):
        pts = [(cx + 7 * direction, cy), (cx - 5 * direction, cy - 9), (cx - 5 * direction, cy + 9)]
        pygame.draw.polygon(screen, color, pts)

    def _draw_cars(self, screen):
        """Decoration: the lineup's cars (and yours, in red) cruise around the track behind the menu."""
        center = self.track.center
        n = len(center)
        colors = [CAR_COLOR] + [AI_COLORS[i % len(AI_COLORS)] for i in range(len(self.preset.strategies))]
        for i, color in enumerate(colors):
            index = int(self.ticks * (0.9 + 0.05 * i) + i * n / len(colors)) % n
            (x0, y0), (x1, y1) = center[index - 1], center[(index + 1) % n]
            angle = math.atan2(y1 - y0, x1 - x0)
            cx, cy = center[index]
            fx, fy = math.cos(angle), math.sin(angle)
            rx, ry = -fy, fx
            hl, hw = CAR_LENGTH / 2, CAR_WIDTH / 2
            pts = [(cx + fx * s * hl + rx * t * hw, cy + fy * s * hl + ry * t * hw)
                   for s, t in ((1, -1), (1, 1), (-1, 1), (-1, -1))]
            pygame.draw.polygon(screen, (0, 0, 0), [(px + 3, py + 4) for px, py in pts])
            pygame.draw.polygon(screen, color, pts)
            pygame.draw.polygon(screen, WHITE, pts, 2)

    def _draw_selector(self, screen, rect, label, value, selected, dots=None, font=None, color=WHITE, note=None):
        pygame.draw.rect(screen, ROW_ON if selected else ROW_OFF, rect, border_radius=12)
        pygame.draw.rect(screen, YELLOW if selected else (70, 78, 104), rect, 2, border_radius=12)
        self._text(screen, self.f_small, label, (rect.x + 52, rect.y + 7), DIM, "topleft", False)
        arrow_color = YELLOW if selected else DIM
        self._arrow(screen, rect.x + 30, rect.centery + 4, -1, arrow_color)
        self._arrow(screen, rect.right - 30, rect.centery + 4, +1, arrow_color)
        font = font or self.f_big
        self._text(screen, font, value, (rect.centerx, rect.centery + 2), color)
        if note:
            x = rect.centerx + font.size(value)[0] / 2 + 14
            self._text(screen, self.f_small, note, (x, rect.centery + 3), DIM, "midleft", False)
        if dots:
            count, active = dots
            for k in range(count):
                x = rect.centerx + (k - (count - 1) / 2) * 16
                pygame.draw.circle(screen, YELLOW if k == active else (80, 88, 112), (x, rect.bottom - 9), 4)

    def _draw_button(self, screen, rect, text, selected, color, font):
        fill = color if selected else tuple(int(c * 0.45) for c in color)
        pygame.draw.rect(screen, fill, rect, border_radius=12)
        pygame.draw.rect(screen, WHITE if selected else (90, 98, 120), rect, 2, border_radius=12)
        self._text(screen, font, text, rect.center, WHITE if selected else (190, 195, 205))

    def draw(self, screen):
        screen.blit(self.backdrop, (0, 0))
        self._draw_cars(screen)
        cx = WIDTH // 2

        self._text(screen, self.f_title, "AI RACING SIMULATOR", (cx, 58), WHITE)
        self._text(screen, self.f_text, "Choose your opponents, then race them", (cx, 102), DIM, "center", False)

        panel = pygame.Rect(cx - 320, 128, 640, 512)
        surf = pygame.Surface(panel.size, pygame.SRCALPHA)
        pygame.draw.rect(surf, PANEL, surf.get_rect(), border_radius=18)
        pygame.draw.rect(surf, (255, 255, 255, 60), surf.get_rect(), 2, border_radius=18)
        screen.blit(surf, panel.topleft)
        left, width = panel.x + 30, panel.w - 60

        preset = self.preset
        selected = self.ROWS[self.row]
        self._draw_selector(screen, pygame.Rect(left, 146, width, 60), "AI LINEUP", preset.name,
                            selected == "lineup", (len(RACE_PRESETS), self.preset_index))
        self._draw_selector(screen, pygame.Rect(left, 212, width, 42), "LAPS", str(self.laps),
                            selected == "laps", font=self.f_mid)
        self._draw_selector(screen, pygame.Rect(left, 260, width, 42), "WEATHER", self.weather,
                            selected == "weather", font=self.f_mid, color=WEATHER_COLORS[self.weather],
                            note=f"grip {WEATHER_GRIP[self.weather] * 100:.0f}%")

        # What this lineup is about
        y = 314
        for line in wrap(self.f_text, preset.summary, width - 8):
            self._text(screen, self.f_text, line, (left + 4, y), (215, 220, 232), "topleft", False)
            y += 20

        # The grid: you first, then the AI cars in grid order
        y = 378
        self._text(screen, self.f_small, "STARTING GRID", (left + 4, y), DIM, "topleft", False)
        y += 22
        names = lineup_names(preset.strategies)
        rows = [("You", "keyboard", CAR_COLOR)]
        for i, (strategy, name) in enumerate(zip(preset.strategies, names)):
            rows.append((name, STRATEGY_INFO[strategy], AI_COLORS[i % len(AI_COLORS)]))
        for place, (name, info, color) in enumerate(rows, start=1):
            self._text(screen, self.f_small, f"{place}", (left + 14, y + 8), DIM, "center", False)
            pygame.draw.circle(screen, WHITE, (left + 40, y + 8), 8)
            pygame.draw.circle(screen, color, (left + 40, y + 8), 7)
            self._text(screen, self.f_mid, name, (left + 62, y + 8), WHITE, "midleft", False)
            self._text(screen, self.f_small, info, (left + width - 4, y + 8), DIM, "midright", False)
            y += 24

        self._draw_button(screen, pygame.Rect(left, 534, width, 48), "START RACE",
                          selected == "start", (40, 150, 70), self.f_big)
        self._draw_button(screen, pygame.Rect(left, 590, width, 34), "QUIT",
                          selected == "quit", (150, 50, 55), self.f_mid)

        self._text(screen, self.f_small, "UP / DOWN select     LEFT / RIGHT change     1-4 lineup     "
                                         "ENTER start     ESC quit", (cx, HEIGHT - 20), (200, 205, 215), "center")


def draw_race_tag(screen, race, font):
    """Small label under the lap panel: which lineup is racing."""
    if race.preset is None:
        return
    text = f"{race.preset.name.upper()}   |   {race.weather.upper()}"
    shadow = font.render(text, True, (0, 0, 0))
    label = font.render(text, True, (230, 230, 230))
    screen.blit(shadow, (18, 108))
    screen.blit(label, (16, 106))