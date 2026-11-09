import pygame
from settings import *

PANEL = (12, 16, 28, 180)
DIM = (150, 158, 175)
SEGMENT_OFF = (44, 48, 62)


def format_time(seconds):
    minutes = int(seconds // 60)
    return f"{minutes:02d}:{seconds - minutes * 60:05.2f}"


class HUD:
    """Draws race information. Create it after pygame.init()."""

    MAP_SIZE = (170, 100)

    def __init__(self, track):
        self.track = track
        self.f_huge = pygame.font.SysFont("arial", 110, bold=True)
        self.f_big = pygame.font.SysFont("arial", 44, bold=True)
        self.f_mid = pygame.font.SysFont("arial", 24, bold=True)
        self.f_small = pygame.font.SysFont("arial", 14, bold=True)
        self._build_minimap()

    # ---------------------------------------------------------------- helpers
    @staticmethod
    def _panel(screen, rect):
        surf = pygame.Surface((rect[2], rect[3]), pygame.SRCALPHA)
        pygame.draw.rect(surf, PANEL, surf.get_rect(), border_radius=12)
        pygame.draw.rect(surf, (255, 255, 255, 45), surf.get_rect(), 1, border_radius=12)
        screen.blit(surf, (rect[0], rect[1]))

    @staticmethod
    def _text(screen, font, text, pos, color=WHITE, anchor="center", shadow=True):
        if shadow:
            s = font.render(text, True, (0, 0, 0))
            screen.blit(s, s.get_rect(**{anchor: (pos[0] + 2, pos[1] + 2)}))
        surf = font.render(text, True, color)
        screen.blit(surf, surf.get_rect(**{anchor: pos}))

    # ---------------------------------------------------------------- minimap
    def _build_minimap(self):
        w, h = self.MAP_SIZE
        xs = [p[0] for p in self.track.center]
        ys = [p[1] for p in self.track.center]
        pad = 12
        self.map_scale = min((w - 2 * pad) / (max(xs) - min(xs)), (h - 2 * pad) / (max(ys) - min(ys)))
        self.map_off = (pad - min(xs) * self.map_scale + (w - 2 * pad - (max(xs) - min(xs)) * self.map_scale) / 2,
                        pad - min(ys) * self.map_scale + (h - 2 * pad - (max(ys) - min(ys)) * self.map_scale) / 2)

        surf = pygame.Surface((w, h), pygame.SRCALPHA)
        pygame.draw.rect(surf, PANEL, surf.get_rect(), border_radius=12)
        pygame.draw.rect(surf, (255, 255, 255, 45), surf.get_rect(), 1, border_radius=12)
        pts = [self._map_point(p) for p in self.track.center]
        pygame.draw.lines(surf, (210, 215, 225), True, pts, 7)
        pygame.draw.lines(surf, (70, 74, 88), True, pts, 4)
        a, b = self._map_point(self.track.edge_point(0, -ROAD_HALF_WIDTH)), self._map_point(self.track.edge_point(0, ROAD_HALF_WIDTH))
        pygame.draw.line(surf, WHITE, a, b, 2)
        self.minimap = surf

    def _map_point(self, p):
        return (p[0] * self.map_scale + self.map_off[0], p[1] * self.map_scale + self.map_off[1])

    def _draw_minimap(self, screen, race):
        x0, y0 = WIDTH - self.MAP_SIZE[0] - 16, HEIGHT - self.MAP_SIZE[1] - 16
        screen.blit(self.minimap, (x0, y0))
        for racer in reversed(race.racers):
            mx, my = self._map_point((racer.car.x, racer.car.y))
            radius = 5 if racer.is_player else 4
            pygame.draw.circle(screen, WHITE, (x0 + mx, y0 + my), radius + 1)
            pygame.draw.circle(screen, racer.car.color, (x0 + mx, y0 + my), radius)

    def _draw_legend(self, screen, race):
        rows = len(race.racers)
        height = 14 + 21 * rows
        x = WIDTH - self.MAP_SIZE[0] - 16
        y = HEIGHT - self.MAP_SIZE[1] - 16 - 8 - height
        self._panel(screen, (x, y, self.MAP_SIZE[0], height))
        for i, racer in enumerate(race.racers):
            row_y = y + 17 + 21 * i
            pygame.draw.circle(screen, WHITE, (x + 18, row_y), 7)
            pygame.draw.circle(screen, racer.car.color, (x + 18, row_y), 6)
            self._text(screen, self.f_small, racer.name, (x + 34, row_y), WHITE, "midleft", False)

    # ------------------------------------------------------------------- main
    def draw(self, screen, race):
        player = race.player
        car = player.car
        cx = WIDTH // 2

        # Lap and position (top-left)
        self._panel(screen, (16, 16, 200, 84))
        lap = min(player.laps + 1, race.total_laps)
        self._text(screen, self.f_small, "LAP", (34, 26), DIM, "topleft", False)
        self._text(screen, self.f_big, f"{lap}/{race.total_laps}", (34, 42), WHITE, "topleft")
        self._text(screen, self.f_small, "POS", (130, 26), DIM, "topleft", False)
        self._text(screen, self.f_big, f"{race.position_of(player)}/{len(race.racers)}", (130, 42), YELLOW, "topleft")

        # Timer (top-centre)
        self._panel(screen, (cx - 90, 12, 180, 58))
        self._text(screen, self.f_mid, format_time(race.race_time), (cx, 30))
        best = format_time(player.best_lap) if player.best_lap is not None else "--:--.--"
        self._text(screen, self.f_small, f"BEST {best}", (cx, 56), DIM, "center", False)

        # Speedometer and fuel (infield)
        self._draw_speed(screen, car, cx)
        self._draw_fuel(screen, car, cx)

        self._draw_legend(screen, race)
        self._draw_minimap(screen, race)
        self._text(screen, self.f_small, "ARROWS drive    T respawn    P AI routes    R restart    ESC quit", (20, HEIGHT - 22), (230, 230, 230), "midleft")

        if race.state == "countdown":
            self._text(screen, self.f_huge, str(int(race.countdown) + 1), (cx, HEIGHT // 2), YELLOW)
        elif race.state == "racing" and race.race_time < 0.8:
            self._text(screen, self.f_huge, "GO!", (cx, HEIGHT // 2), GREEN)
        elif race.state == "finished":
            self._draw_results(screen, race)

    def _draw_speed(self, screen, car, cx):
        rect = (cx - 100, 225, 200, 100)
        self._panel(screen, rect)
        kmh = abs(car.speed) * HUD_SPEED_SCALE
        self._text(screen, self.f_big, f"{kmh:.0f}", (cx - 8, 255), WHITE, "midright")
        self._text(screen, self.f_small, "km/h", (cx - 2, 262), DIM, "midleft", False)

        segments = 18
        lit = round(segments * min(1.0, abs(car.speed) / CAR_MAX_SPEED))
        for i in range(segments):
            if i >= lit:
                color = SEGMENT_OFF
            elif i < 11:
                color = GREEN
            elif i < 15:
                color = YELLOW
            else:
                color = RED
            pygame.draw.rect(screen, color, (rect[0] + 12 + i * 10, rect[1] + 66, 8, 20), border_radius=2)

    def _draw_fuel(self, screen, car, cx):
        rect = (cx - 100, 335, 200, 46)
        self._panel(screen, rect)
        fraction = car.fuel / FUEL_MAX
        color = GREEN if fraction > 0.3 else ORANGE if fraction > 0.15 else RED
        self._text(screen, self.f_small, "FUEL", (rect[0] + 14, rect[1] + 8), DIM, "topleft", False)
        self._text(screen, self.f_small, f"{fraction * 100:.0f}%", (rect[0] + 186, rect[1] + 8), DIM, "topright", False)
        bar = pygame.Rect(rect[0] + 14, rect[1] + 28, 172, 10)
        pygame.draw.rect(screen, SEGMENT_OFF, bar, border_radius=5)
        if fraction > 0:
            pygame.draw.rect(screen, color, (bar.x, bar.y, int(bar.w * fraction), bar.h), border_radius=5)

    def _draw_results(self, screen, race):
        rows = race.standings()
        height = 140 + 30 * len(rows)

        panel = pygame.Surface((460, height), pygame.SRCALPHA)
        pygame.draw.rect(panel, (8, 10, 20, 225), panel.get_rect(), border_radius=16)
        pygame.draw.rect(panel, (255, 255, 255, 70), panel.get_rect(), 2, border_radius=16)
        rect = panel.get_rect(center=(WIDTH // 2, HEIGHT // 2))
        screen.blit(panel, rect)

        y = rect.top + 34
        self._text(screen, self.f_mid, "RACE FINISHED", (rect.centerx, y), YELLOW)
        y += 30
        self._text(screen, self.f_small, f"Winner: {race.winner.name}", (rect.centerx, y), WHITE, "center", False)
        y += 34

        for place, racer in enumerate(rows, start=1):
            color = YELLOW if racer.is_player else WHITE
            time_text = format_time(racer.finish_time) if racer.finished else "DNF"
            pygame.draw.circle(screen, racer.car.color, (rect.left + 42, y + 9), 7)
            self._text(screen, self.f_small, f"{place}.  {racer.name}", (rect.left + 62, y), color, "topleft", False)
            self._text(screen, self.f_small, time_text, (rect.right - 40, y), color, "topright", False)
            y += 30

        self._text(screen, self.f_small, "Press R to race again", (rect.centerx, rect.bottom - 24), DIM, "center", False)