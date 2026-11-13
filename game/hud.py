import pygame
from settings import *


class HUD:
    def __init__(self, track):
        self.track = track
        self.font_large = pygame.font.SysFont("arial", 32, bold=True)
        self.font_medium = pygame.font.SysFont("arial", 20, bold=True)
        self.font_small = pygame.font.SysFont("arial", 14)

    def draw(self, surface, race):
        self._draw_leaderboard(surface, race)
        self._draw_player_telemetry(surface, race.player)
        self._draw_race_status(surface, race)

    def _draw_leaderboard(self, surface, race):
        panel = pygame.Surface((220, 160), pygame.SRCALPHA)
        panel.fill((10, 15, 25, 210))
        surface.blit(panel, (10, 10))
        pygame.draw.rect(surface, WHITE, (10, 10, 220, 160), 1, border_radius=4)

        title = self.font_medium.render("LEADERBOARD", True, YELLOW)
        surface.blit(title, (20, 15))

        standings = race.get_standings()
        for idx, racer in enumerate(standings):
            pos_txt = f"{idx + 1}."
            name_txt = racer.name
            lap_txt = f"L{racer.current_lap}/{TOTAL_LAPS}" if not racer.finished else "FINISH"

            color = racer.car.color
            pygame.draw.circle(surface, color, (25, 45 + idx * 25), 6)

            p_surf = self.font_small.render(pos_txt, True, WHITE)
            n_surf = self.font_small.render(name_txt, True, WHITE)
            l_surf = self.font_small.render(lap_txt, True, GRAY)

            surface.blit(p_surf, (35, 37 + idx * 25))
            surface.blit(n_surf, (60, 37 + idx * 25))
            surface.blit(l_surf, (170, 37 + idx * 25))

    def _draw_player_telemetry(self, surface, player):
        panel = pygame.Surface((240, 120), pygame.SRCALPHA)
        panel.fill((10, 15, 25, 210))
        x_pos = WIDTH - 250
        surface.blit(panel, (x_pos, HEIGHT - 130))
        pygame.draw.rect(surface, WHITE, (x_pos, HEIGHT - 130, 240, 120), 1, border_radius=4)

        # Speedometer
        speed = int(player.car.speed * 10)
        s_surf = self.font_large.render(f"{speed} KM/H", True, WHITE)
        surface.blit(s_surf, (x_pos + 15, HEIGHT - 120))

        # Fuel Bar
        self._draw_bar(surface, x_pos + 15, HEIGHT - 75, 210, 12, player.car.fuel, 100, "Fuel", GREEN)

        # Tire Wear Bar
        self._draw_bar(surface, x_pos + 15, HEIGHT - 45, 210, 12, player.car.tire_health, 100, "Tires", ORANGE)

    def _draw_bar(self, surface, x, y, width, height, val, max_val, label, color):
        lbl_surf = self.font_small.render(label, True, WHITE)
        surface.blit(lbl_surf, (x, y - 14))

        ratio = max(0.0, min(1.0, val / max_val))
        pygame.draw.rect(surface, (40, 40, 40), (x, y, width, height), border_radius=3)
        pygame.draw.rect(surface, color, (x, y, int(width * ratio), height), border_radius=3)

    def _draw_race_status(self, surface, race):
        if race.state == "countdown":
            txt = self.font_large.render("READY...", True, YELLOW)
            surface.blit(txt, txt.get_rect(center=(WIDTH // 2, HEIGHT // 2)))
        elif race.state == "finished":
            txt = self.font_large.render("RACE OVER!", True, RED)
            surface.blit(txt, txt.get_rect(center=(WIDTH // 2, 80)))

    def _draw_results(self, surface, race):
        title = self.font_large.render("FINAL RACE RESULTS", True, YELLOW)
        surface.blit(title, title.get_rect(center=(WIDTH // 2, 50)))

        standings = race.get_standings()
        for i, racer in enumerate(standings):
            row_y = 110 + i * 45
            pygame.draw.rect(surface, (20, 30, 50), (WIDTH // 2 - 250, row_y, 500, 35), border_radius=5)

            pos_str = f"#{i + 1}"
            time_str = f"{racer.finish_time:.2f}s" if racer.finished else "DNF"

            p_surf = self.font_medium.render(pos_str, True, WHITE)
            n_surf = self.font_medium.render(racer.name, True, racer.car.color)
            t_surf = self.font_medium.render(time_str, True, WHITE)

            surface.blit(p_surf, (WIDTH // 2 - 230, row_y + 5))
            surface.blit(n_surf, (WIDTH // 2 - 150, row_y + 5))
            surface.blit(t_surf, (WIDTH // 2 + 150, row_y + 5))