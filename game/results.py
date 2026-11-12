"""Race results screen, shown when a race is over (Race.state == "finished").

It has two views, switched with TAB (or the left / right arrows):

    Standings   place, driver, laps done, best lap, total time, gap to the winner
                and how often the car had to be put back on the track
    Lap times   every lap of every car; the fastest in each lap is green and the
                fastest lap of the race is purple

handle_event() returns what the player chose and main.py acts on it:

    "again"   race the same lineup again
    "menu"    back to the main menu
    None      nothing (switching the view is handled here)

The views are listed in PAGES, so a new one (for example the performance
charts) only needs a name there and a method for it.
"""

import pygame

from settings import *
from game.hud import format_time, ordinal
from game.interface import STRATEGY_INFO
from game.race import FINISH_GRACE_SECONDS

PANEL = (10, 13, 24, 236)
DIM = (150, 158, 175)
GOLD = (255, 214, 64)
SILVER = (205, 210, 220)
BRONZE = (214, 140, 80)
FASTEST = (200, 130, 255)      # fastest lap of the race
ROW_A = (24, 30, 48)
ROW_B = (30, 37, 58)
ROW_YOU = (66, 58, 24)

PAGES = ("Standings", "Lap times")


def lap_text(seconds):
    return f"{seconds:.2f}" if seconds < 100 else f"{int(seconds // 60)}:{seconds % 60:04.1f}"


class ResultsScreen:
    """Create it after pygame.init(), when the race has finished."""

    PANEL_RECT = pygame.Rect(60, 36, 880, 628)
    ROW_TOP = 262
    ROW_STEP = 50
    ROW_HEIGHT = 46

    def __init__(self, race, backdrop=None):
        self.race = race
        self.page = 0
        self.rows = race.standings()
        self.winner = race.winner

        self.f_title = pygame.font.SysFont("arial", 40, bold=True)
        self.f_big = pygame.font.SysFont("arial", 34, bold=True)
        self.f_mid = pygame.font.SysFont("arial", 20, bold=True)
        self.f_small = pygame.font.SysFont("arial", 14, bold=True)
        self.f_tiny = pygame.font.SysFont("arial", 12, bold=True)

        # The fastest single lap of the race, and the fastest lap number by number
        laps = [(t, r) for r in self.rows for t in r.lap_times]
        self.fastest = min(laps, key=lambda item: item[0]) if laps else None
        self.lap_best = {}
        for racer in self.rows:
            for i, t in enumerate(racer.lap_times):
                self.lap_best[i] = min(t, self.lap_best.get(i, t))

        self.backdrop = pygame.Surface((WIDTH, HEIGHT))
        if backdrop is not None:
            self.backdrop.blit(backdrop, (0, 0))
        shade = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        shade.fill((4, 6, 14, 190))
        self.backdrop.blit(shade, (0, 0))

    # ---------------------------------------------------------------- input
    def handle_event(self, event):
        if event.type != pygame.KEYDOWN:
            return None
        key = event.key
        if key in (pygame.K_r, pygame.K_RETURN, pygame.K_KP_ENTER):
            return "again"
        if key in (pygame.K_ESCAPE, pygame.K_m):
            return "menu"
        if key in (pygame.K_TAB, pygame.K_RIGHT, pygame.K_d):
            self.page = (self.page + 1) % len(PAGES)
        elif key in (pygame.K_LEFT, pygame.K_a):
            self.page = (self.page - 1) % len(PAGES)
        elif pygame.K_1 <= key < pygame.K_1 + len(PAGES):
            self.page = key - pygame.K_1
        return None

    # -------------------------------------------------------------- helpers
    @staticmethod
    def _text(screen, font, text, pos, color=WHITE, anchor="center", shadow=True):
        if shadow:
            s = font.render(text, True, (0, 0, 0))
            screen.blit(s, s.get_rect(**{anchor: (pos[0] + 2, pos[1] + 2)}))
        surf = font.render(text, True, color)
        screen.blit(surf, surf.get_rect(**{anchor: pos}))

    def _place_color(self, racer):
        return {1: GOLD, 2: SILVER, 3: BRONZE}.get(racer.finish_place, WHITE) if racer.finished else DIM

    def _headline(self):
        """(big text, colour, small text) about how the player did."""
        player = self.race.player
        if not player.finished:
            return "DID NOT FINISH", RED, "You were still racing when the race was closed."
        place = player.finish_place
        count = len(self.race.racers)
        if place == 1:
            return "VICTORY!", GOLD, f"You won against {count - 1} AI cars."
        if place <= 3 and count > 3:
            return f"PODIUM - {ordinal(place).upper()} PLACE", SILVER if place == 2 else BRONZE, \
                   f"{player.finish_time - self.winner.finish_time:.2f}s behind {self.winner.name}."
        return f"YOU FINISHED {ordinal(place).upper()}", WHITE, f"{self.winner.name} won the race."

    # -------------------------------------------------------------- drawing
    def draw(self, screen):
        race = self.race
        screen.blit(self.backdrop, (0, 0))

        panel = self.PANEL_RECT
        surf = pygame.Surface(panel.size, pygame.SRCALPHA)
        pygame.draw.rect(surf, PANEL, surf.get_rect(), border_radius=18)
        pygame.draw.rect(surf, (255, 255, 255, 70), surf.get_rect(), 2, border_radius=18)
        screen.blit(surf, panel.topleft)
        left, right = panel.x + 30, panel.right - 30

        # Title and view tabs
        self._text(screen, self.f_title, "RACE RESULTS", (left, panel.y + 22), WHITE, "topleft")
        name = race.preset.name if race.preset is not None else "Custom grid"
        laps = f"{race.total_laps} lap" + ("s" if race.total_laps != 1 else "")
        self._text(screen, self.f_small, f"{name}   |   {laps}   |   {race.weather}", (left + 2, panel.y + 70), DIM, "topleft", False)
        x = right
        for i in reversed(range(len(PAGES))):
            label = f"{i + 1}  {PAGES[i].upper()}"
            w = self.f_small.size(label)[0] + 28
            tab = pygame.Rect(x - w, panel.y + 30, w, 30)
            active = i == self.page
            pygame.draw.rect(screen, (60, 72, 110) if active else (28, 34, 52), tab, border_radius=15)
            pygame.draw.rect(screen, YELLOW if active else (70, 78, 104), tab, 2, border_radius=15)
            self._text(screen, self.f_small, label, tab.center, WHITE if active else DIM, "center", False)
            x -= w + 10

        # How the player did
        box = pygame.Rect(left, panel.y + 100, right - left, 72)
        pygame.draw.rect(screen, (22, 28, 46), box, border_radius=14)
        text, color, sub = self._headline()
        self._text(screen, self.f_big, text, (box.x + 20, box.y + 8), color, "topleft")
        self._text(screen, self.f_small, sub, (box.x + 22, box.y + 48), (205, 210, 222), "topleft", False)
        if self.fastest is not None:
            t, racer = self.fastest
            self._text(screen, self.f_tiny, "FASTEST LAP", (box.right - 20, box.y + 12), FASTEST, "topright", False)
            self._text(screen, self.f_mid, f"{lap_text(t)}s", (box.right - 20, box.y + 26), WHITE, "topright", False)
            self._text(screen, self.f_small, racer.name, (box.right - 20, box.y + 52), DIM, "topright", False)

        if self.page == 0:
            self._draw_standings(screen, left, right)
        else:
            self._draw_lap_times(screen, left, right)

        if any(not r.finished for r in self.rows):
            self._text(screen, self.f_tiny, f"DNF: did not finish within {FINISH_GRACE_SECONDS:.0f} seconds of the player.",
                       (left, panel.bottom - 62), DIM, "topleft", False)
        self._text(screen, self.f_small, "TAB switch view      R / ENTER race again      ESC menu",
                   (panel.centerx, panel.bottom - 28), (210, 214, 224), "center")

    def _row_background(self, screen, racer, y, left, right):
        rect = pygame.Rect(left, y, right - left, self.ROW_HEIGHT)
        pygame.draw.rect(screen, ROW_YOU if racer.is_player else (ROW_A if (y // self.ROW_STEP) % 2 else ROW_B),
                         rect, border_radius=10)
        if racer.is_player:
            pygame.draw.rect(screen, GOLD, rect, 2, border_radius=10)
        return rect

    def _driver_cell(self, screen, racer, place, rect, with_info=True):
        self._text(screen, self.f_big if with_info else self.f_mid, str(place) if racer.finished else "-",
                   (rect.x + 28, rect.centery), self._place_color(racer), "center", False)
        pygame.draw.circle(screen, WHITE, (rect.x + 66, rect.centery), 9)
        pygame.draw.circle(screen, racer.car.color, (rect.x + 66, rect.centery), 8)
        if with_info:
            info = "keyboard" if racer.is_player else STRATEGY_INFO.get(racer.strategy, "")
            self._text(screen, self.f_mid, racer.name, (rect.x + 88, rect.y + 6), YELLOW if racer.is_player else WHITE,
                       "topleft", False)
            self._text(screen, self.f_tiny, info, (rect.x + 88, rect.y + 28), DIM, "topleft", False)
        else:
            self._text(screen, self.f_mid, racer.name, (rect.x + 88, rect.centery), YELLOW if racer.is_player else WHITE,
                       "midleft", False)

    def _draw_standings(self, screen, left, right):
        columns = {"LAPS": left + 410, "BEST LAP": left + 495, "TIME": left + 595, "GAP": left + 695,
                   "RESETS": left + 785}
        header_y = self.ROW_TOP - 24
        self._text(screen, self.f_tiny, "DRIVER", (left + 90, header_y), DIM, "topleft", False)
        for label, x in columns.items():
            self._text(screen, self.f_tiny, label, (x, header_y), DIM, "midtop", False)

        for place, racer in enumerate(self.rows, start=1):
            y = self.ROW_TOP + (place - 1) * self.ROW_STEP
            rect = self._row_background(screen, racer, y, left, right)
            self._driver_cell(screen, racer, place, rect)
            cy = rect.centery

            self._text(screen, self.f_mid, f"{racer.laps}/{self.race.total_laps}", (columns["LAPS"], cy), WHITE, "center", False)

            is_fastest = self.fastest is not None and racer.best_lap is not None and racer.best_lap == self.fastest[0]
            best = f"{lap_text(racer.best_lap)}s" if racer.best_lap is not None else "--"
            self._text(screen, self.f_mid, best, (columns["BEST LAP"], cy), FASTEST if is_fastest else WHITE, "center", False)

            if racer.finished:
                self._text(screen, self.f_mid, format_time(racer.finish_time), (columns["TIME"], cy), WHITE, "center", False)
                gap = "leader" if racer is self.winner else f"+{racer.finish_time - self.winner.finish_time:.2f}s"
                self._text(screen, self.f_mid, gap, (columns["GAP"], cy), DIM if racer is self.winner else WHITE, "center", False)
            else:
                self._text(screen, self.f_mid, "DNF", (columns["TIME"], cy), RED, "center", False)
                self._text(screen, self.f_mid, "--", (columns["GAP"], cy), DIM, "center", False)

            resets = str(racer.respawns) if racer.respawns else "0"
            self._text(screen, self.f_mid, resets, (columns["RESETS"], cy), ORANGE if racer.respawns else DIM, "center", False)

    def _draw_lap_times(self, screen, left, right):
        laps = self.race.total_laps
        first = left + 250
        width = min(86, (right - first - 120) / laps)
        best_x = first + width * laps + 56
        header_y = self.ROW_TOP - 24
        self._text(screen, self.f_tiny, "DRIVER", (left + 90, header_y), DIM, "topleft", False)
        for i in range(laps):
            self._text(screen, self.f_tiny, f"LAP {i + 1}", (first + width * (i + 0.5), header_y), DIM, "midtop", False)
        self._text(screen, self.f_tiny, "BEST", (best_x, header_y), DIM, "midtop", False)

        for place, racer in enumerate(self.rows, start=1):
            y = self.ROW_TOP + (place - 1) * self.ROW_STEP
            rect = self._row_background(screen, racer, y, left, right)
            self._driver_cell(screen, racer, place, rect, with_info=False)
            cy = rect.centery
            for i in range(laps):
                x = first + width * (i + 0.5)
                if i < len(racer.lap_times):
                    t = racer.lap_times[i]
                    if self.fastest is not None and t == self.fastest[0]:
                        color = FASTEST
                    elif t == self.lap_best[i] and len(self.rows) > 1:
                        color = GREEN
                    else:
                        color = WHITE
                    self._text(screen, self.f_mid, lap_text(t), (x, cy), color, "center", False)
                else:
                    self._text(screen, self.f_mid, "--", (x, cy), DIM, "center", False)
            if racer.best_lap is not None:
                is_fastest = self.fastest is not None and racer.best_lap == self.fastest[0]
                self._text(screen, self.f_mid, lap_text(racer.best_lap), (best_x, cy),
                           FASTEST if is_fastest else WHITE, "center", False)
            else:
                self._text(screen, self.f_mid, "--", (best_x, cy), DIM, "center", False)

        self._text(screen, self.f_tiny, "green = fastest car in that lap      purple = fastest lap of the race",
                   (left, self.ROW_TOP + len(self.rows) * self.ROW_STEP + 8), DIM, "topleft", False)