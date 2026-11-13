"""Race results screen, shown when a race is over (Race.state == "finished").

It has two views, switched with TAB (or the left / right arrows):

    Standings   place, driver, laps done, best lap, total time, gap to the winner
                and how often the car had to be put back on the track
    Lap times   every lap of every car; the fastest in each lap is green and the
                fastest lap of the race is purple
    Charts      bar charts of the finish times and the best laps, and a line chart
                of the lap time in every lap (pygame drawing, no plotting library)

handle_event() returns what the player chose and main.py acts on it:

    "again"   race the same lineup again
    "menu"    back to the main menu
    None      nothing (switching the view is handled here)

The views are listed in PAGES, so a new one only needs a name there and a method for it.
"""

import math

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

GRID = (52, 60, 84)
AXIS = (120, 128, 150)
CARD = (22, 28, 46)

PAGES = ("Standings", "Lap times", "Charts")


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
        elif self.page == 1:
            self._draw_lap_times(screen, left, right)
        else:
            self._draw_charts(screen, left, right)

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

    # --------------------------------------------------------------- charts
    @staticmethod
    def _nice_axis(lo, hi, ticks=4):
        """Round the range to 'nice' numbers: returns (axis_lo, axis_hi, step)."""
        span = max(hi - lo, 1e-6)
        raw = span / ticks
        magnitude = 10 ** math.floor(math.log10(raw))
        step = next(m * magnitude for m in (1, 2, 2.5, 5, 10) if raw <= m * magnitude + 1e-12)
        return math.floor(lo / step + 1e-9) * step, math.ceil(hi / step - 1e-9) * step, step

    @staticmethod
    def _tick_text(value, step):
        return f"{value:.0f}" if step >= 1 else f"{value:.1f}" if step >= 0.1 else f"{value:.2f}"

    def _fit(self, text, width):
        """Shorten text with '..' until it fits in `width` pixels."""
        while len(text) > 3 and self.f_tiny.size(text)[0] > width:
            text = text[:-3] + ".."
        return text

    def _card(self, screen, rect, title, note=None):
        pygame.draw.rect(screen, CARD, rect, border_radius=14)
        self._text(screen, self.f_small, title, (rect.x + 14, rect.y + 10), WHITE, "topleft", False)
        if note:
            self._text(screen, self.f_tiny, note, (rect.right - 14, rect.y + 12), DIM, "topright", False)

    def _draw_charts(self, screen, left, right):
        top = self.PANEL_RECT.y + 186
        bottom = self.PANEL_RECT.bottom - 70
        gap = 14
        column = (right - left - gap) // 2
        half = (bottom - top - gap) // 2

        # Finish times: finished cars in the order they finished, DNFs at the end
        finish = [(r, r.finish_time if r.finished else None) for r in self.rows]
        self._draw_bars(screen, pygame.Rect(left, top, column, half), "Finish time (s)", finish,
                        lambda v: f"{v:.1f}s", GOLD)

        # Best laps: fastest first
        best = sorted(((r, r.best_lap) for r in self.rows), key=lambda item: (item[1] is None, item[1] or 0))
        self._draw_bars(screen, pygame.Rect(left, top + half + gap, column, half), "Best lap (s)", best,
                        lambda v: f"{v:.2f}s", FASTEST)

        self._draw_line_chart(screen, pygame.Rect(left + column + gap, top, column, bottom - top))

    def _draw_bars(self, screen, rect, title, items, fmt, highlight):
        """Horizontal bars, one per car. items: [(racer, value or None)]; the lowest value wins."""
        values = [v for _, v in items if v is not None]
        if values:
            lo_v, hi_v = min(values), max(values)
            span = hi_v - lo_v
            # Times are close together, so the axis does not start at 0 - it says where it starts
            raw_lo = max(0.0, lo_v - span * 1.2) if span > 1e-6 else 0.0
            axis_lo, axis_hi, step = self._nice_axis(raw_lo, hi_v + span * 0.08 + 1e-6)
        else:
            axis_lo, axis_hi, step = 0.0, 1.0, 0.25
        self._card(screen, rect, title, f"axis starts at {self._tick_text(axis_lo, step)}s" if axis_lo > 0 else None)

        label_w = 96
        plot_l, plot_r = rect.x + 14 + label_w, rect.right - 64
        plot_t, plot_b = rect.y + 34, rect.bottom - 22
        scale = (plot_r - plot_l) / (axis_hi - axis_lo)

        # Gridlines and tick labels
        v = axis_lo
        while v <= axis_hi + 1e-9:
            x = int(plot_l + (v - axis_lo) * scale)
            pygame.draw.line(screen, GRID, (x, plot_t - 2), (x, plot_b), 1)
            self._text(screen, self.f_tiny, self._tick_text(v, step), (x, plot_b + 4), DIM, "midtop", False)
            v += step
        pygame.draw.line(screen, AXIS, (plot_l, plot_t - 2), (plot_l, plot_b), 1)

        row = (plot_b - plot_t) / max(1, len(items))
        bar_h = max(6, min(18, int(row) - 6))
        best_value = min(values) if values else None
        for i, (racer, value) in enumerate(items):
            cy = int(plot_t + row * (i + 0.5))
            self._text(screen, self.f_tiny, self._fit(racer.name, label_w - 6), (plot_l - 8, cy),
                       YELLOW if racer.is_player else WHITE, "midright", False)
            if value is None:
                self._text(screen, self.f_tiny, "DNF" if not racer.finished else "--", (plot_l + 8, cy),
                           RED if not racer.finished else DIM, "midleft", False)
                continue
            bar = pygame.Rect(plot_l, cy - bar_h // 2, max(3, int((value - axis_lo) * scale)), bar_h)
            pygame.draw.rect(screen, racer.car.color, bar, border_radius=4)
            is_best = value == best_value
            if is_best:
                pygame.draw.rect(screen, highlight, bar, 2, border_radius=4)
            self._text(screen, self.f_tiny, fmt(value), (bar.right + 6, cy), highlight if is_best else WHITE, "midleft", False)

    def _draw_line_chart(self, screen, rect):
        """Lap time of every car in every lap. A lap far slower than the rest (a car that was stuck)
        is drawn at the top edge with a triangle instead of squashing the other lines."""
        self._card(screen, rect, "Lap time per lap (s)")
        series = [(r, r.lap_times) for r in self.rows if r.lap_times]
        times = sorted(t for _, ts in series for t in ts)
        if not times:
            self._text(screen, self.f_small, "no laps were completed", rect.center, DIM, "center", False)
            return
        median = times[len(times) // 2]
        cap = min(times[-1], median * 1.5)
        axis_lo, axis_hi, step = self._nice_axis(times[0] - (cap - times[0]) * 0.1, cap + (cap - times[0]) * 0.05 + 1e-6)

        legend_rows = (len(self.rows) + 1) // 2
        plot_l, plot_r = rect.x + 52, rect.right - 20
        plot_t, plot_b = rect.y + 40, rect.bottom - 40 - legend_rows * 20
        laps = self.race.total_laps

        def px(lap):                                    # lap number 1..laps -> x
            return plot_l + (plot_r - plot_l) * ((lap - 1) / (laps - 1) if laps > 1 else 0.5)

        def py(t):
            return plot_b - (min(t, axis_hi) - axis_lo) / (axis_hi - axis_lo) * (plot_b - plot_t)

        v = axis_lo
        while v <= axis_hi + 1e-9:
            y = int(py(v))
            pygame.draw.line(screen, GRID, (plot_l, y), (plot_r, y), 1)
            self._text(screen, self.f_tiny, self._tick_text(v, step), (plot_l - 8, y), DIM, "midright", False)
            v += step
        for lap in range(1, laps + 1):
            self._text(screen, self.f_tiny, str(lap), (px(lap), plot_b + 6), DIM, "midtop", False)
        self._text(screen, self.f_tiny, "lap", (plot_r, plot_b + 22), DIM, "topright", False)
        pygame.draw.line(screen, AXIS, (plot_l, plot_b), (plot_r, plot_b), 1)
        pygame.draw.line(screen, AXIS, (plot_l, plot_t), (plot_l, plot_b), 1)

        for racer, ts in reversed(series):              # the player is drawn last, on top
            points = [(px(i + 1), py(t)) for i, t in enumerate(ts)]
            width = 4 if racer.is_player else 2
            if len(points) > 1:
                pygame.draw.lines(screen, racer.car.color, False, points, width)
            for (x, y), t in zip(points, ts):
                if t > axis_hi:                         # off the chart
                    pygame.draw.polygon(screen, racer.car.color, [(x - 5, y + 8), (x + 5, y + 8), (x, y - 2)])
                else:
                    pygame.draw.circle(screen, CARD, (int(x), int(y)), 6 if racer.is_player else 5)
                    pygame.draw.circle(screen, racer.car.color, (int(x), int(y)), 4 if racer.is_player else 3)

        # Legend: two columns under the plot
        half = (rect.width - 28) // 2
        for i, racer in enumerate(self.rows):
            x = rect.x + 16 + (i % 2) * half
            y = rect.bottom - 14 - legend_rows * 20 + (i // 2) * 20 + 10
            pygame.draw.circle(screen, racer.car.color, (x + 5, y), 5)
            self._text(screen, self.f_tiny, self._fit(racer.name, half - 26), (x + 16, y),
                       YELLOW if racer.is_player else WHITE, "midleft", False)
