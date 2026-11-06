import pygame
from settings import *


def format_time(seconds):
    minutes = int(seconds // 60)
    return f"{minutes:02d}:{seconds - minutes * 60:05.2f}"


class HUD:
    """Draws race information. Create it after pygame.init()."""

    def __init__(self):
        self.font = pygame.font.SysFont("arial", 22, bold=True)
        self.small = pygame.font.SysFont("arial", 16)
        self.big = pygame.font.SysFont("arial", 72, bold=True)

    # ---------------------------------------------------------------- helpers
    @staticmethod
    def _text(screen, font, text, center, color=WHITE):
        surface = font.render(text, True, color)
        screen.blit(surface, surface.get_rect(center=center))

    # ------------------------------------------------------------------- main
    def draw(self, screen, race):
        player = race.player
        cx = WIDTH // 2

        # The info sits in the grass infield in the middle of the track
        lap = min(player.laps + 1, race.total_laps)
        self._text(screen, self.font, f"LAP {lap}/{race.total_laps}", (cx, 190))
        self._text(screen, self.font, f"POS {race.position_of(player)}/{len(race.racers)}", (cx, 220))
        self._text(screen, self.font, format_time(race.race_time), (cx, 252))
        self._text(screen, self.font, f"{abs(player.car.speed) * HUD_SPEED_SCALE:.0f} km/h", (cx, 286))
        self._draw_fuel(screen, player.car, cx, 330)

        if player.best_lap is not None:
            self._text(screen, self.small, f"Best lap {format_time(player.best_lap)}", (cx, 372))
        self._text(screen, self.small, "R = restart", (cx, 410), (200, 200, 200))

        if race.state == "countdown":
            self._text(screen, self.big, str(int(race.countdown) + 1), (cx, HEIGHT // 2), YELLOW)
        elif race.state == "racing" and race.race_time < 0.7:
            self._text(screen, self.big, "GO!", (cx, HEIGHT // 2), GREEN)
        elif race.state == "finished":
            self._draw_results(screen, race)

    def _draw_fuel(self, screen, car, cx, y):
        width, height = 140, 14
        fraction = car.fuel / FUEL_MAX
        color = GREEN if fraction > 0.3 else ORANGE if fraction > 0.15 else RED

        self._text(screen, self.small, "FUEL", (cx, y - 14))
        bar = pygame.Rect(cx - width // 2, y, width, height)
        pygame.draw.rect(screen, (30, 30, 30), bar)
        pygame.draw.rect(screen, color, (bar.x, bar.y, int(width * fraction), height))
        pygame.draw.rect(screen, WHITE, bar, 2)

    def _draw_results(self, screen, race):
        rows = race.standings()
        height = 130 + 28 * len(rows)

        panel = pygame.Surface((440, height), pygame.SRCALPHA)
        panel.fill((0, 0, 0, 205))
        rect = panel.get_rect(center=(WIDTH // 2, HEIGHT // 2))
        screen.blit(panel, rect)

        y = rect.top + 28
        self._text(screen, self.font, "RACE FINISHED", (rect.centerx, y), YELLOW)
        y += 30
        winner = race.winner
        self._text(screen, self.small, f"Winner: {winner.name}", (rect.centerx, y))
        y += 34

        for place, racer in enumerate(rows, start=1):
            color = YELLOW if racer.is_player else WHITE
            time_text = format_time(racer.finish_time) if racer.finished else "DNF"
            label = self.small.render(f"{place}.  {racer.name}", True, color)
            value = self.small.render(time_text, True, color)
            screen.blit(label, (rect.left + 40, y))
            screen.blit(value, value.get_rect(topright=(rect.right - 40, y)))
            y += 28

        self._text(screen, self.small, "Press R to race again", (rect.centerx, rect.bottom - 22), (200, 200, 200))