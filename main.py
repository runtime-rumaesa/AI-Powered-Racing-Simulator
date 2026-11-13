import sys
import pygame
import matplotlib

matplotlib.use("Agg")  # Render charts off-screen to Pygame surfaces
import matplotlib.pyplot as plt

from settings import *
from game.track import draw_track, get_track
from game.race import Race
from game.hud import HUD
from ai.search import TrackGraph, bfs, astar
from ai.prediction import RacePredictor
from ai.bayesian import AccidentRiskModel
from ai.csp import PitStopCSP, solve, make_scenario


class GameEngine:
    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((WIDTH, HEIGHT))
        pygame.display.set_caption(TITLE)
        self.clock = pygame.time.Clock()

        self.state = "MENU"  # MENU, RACING, RESULTS, AI_DEMO
        self.track = get_track()
        self.hud = HUD(self.track)
        self.race = None
        self.show_routes = False
        self.world = pygame.Surface((WIDTH, HEIGHT))

        # UI & Fonts
        self.font_title = pygame.font.SysFont("arial", 48, bold=True)
        self.font_sub = pygame.font.SysFont("arial", 24, bold=True)
        self.font_btn = pygame.font.SysFont("arial", 20, bold=True)
        self.font_small = pygame.font.SysFont("arial", 14)

        # Dynamic Chart Surfaces
        self.perf_chart_surface = None
        self.ai_demo_surface = None

    def run(self):
        running = True
        while running:
            keys = pygame.key.get_pressed()
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                elif event.type == pygame.KEYDOWN:
                    self._handle_keydown(event.key)
                elif event.type == pygame.MOUSEBUTTONDOWN:
                    self._handle_click(event.pos)

            if self.state == "MENU":
                self._draw_menu()
            elif self.state == "RACING":
                self._update_racing(keys)
                self._draw_racing()
            elif self.state == "RESULTS":
                self._draw_results()
            elif self.state == "AI_DEMO":
                self._draw_ai_demo()

            pygame.display.update()
            self.clock.tick(FPS)

        pygame.quit()
        sys.exit()

    # ------------------------------------------------------------------ Event handling
    def _handle_keydown(self, key):
        if key == pygame.K_ESCAPE:
            if self.state in ("RACING", "RESULTS", "AI_DEMO"):
                self.state = "MENU"
        elif self.state == "RACING":
            if key == pygame.K_r:
                self.race = Race()
            elif key == pygame.K_t:
                self.race.respawn(self.race.player)
            elif key == pygame.K_p:
                self.show_routes = not self.show_routes

    def _handle_click(self, pos):
        if self.state == "MENU":
            if self.btn_start.collidepoint(pos):
                self.race = Race()
                self.state = "RACING"
            elif self.btn_demo.collidepoint(pos):
                self._generate_ai_demo_chart()
                self.state = "AI_DEMO"
            elif self.btn_quit.collidepoint(pos):
                pygame.event.post(pygame.event.Event(pygame.QUIT))
        elif self.state in ("RESULTS", "AI_DEMO"):
            if self.btn_back.collidepoint(pos):
                self.state = "MENU"

    # ------------------------------------------------------------------ Main Menu
    def _draw_menu(self):
        self.screen.fill(BACKGROUND)
        draw_track(self.screen)

        # Dark overlay
        overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        overlay.fill((10, 15, 25, 200))
        self.screen.blit(overlay, (0, 0))

        # Title
        t_surf = self.font_title.render("AI RACING SIMULATOR", True, YELLOW)
        self.screen.blit(t_surf, t_surf.get_rect(center=(WIDTH // 2, 120)))

        s_surf = self.font_sub.render("Fast Car Racing & Autonomous Agent Suite", True, WHITE)
        self.screen.blit(s_surf, s_surf.get_rect(center=(WIDTH // 2, 170)))

        # Buttons
        self.btn_start = pygame.Rect(WIDTH // 2 - 140, 260, 280, 50)
        self.btn_demo = pygame.Rect(WIDTH // 2 - 140, 330, 280, 50)
        self.btn_quit = pygame.Rect(WIDTH // 2 - 140, 400, 280, 50)

        for btn, label in [(self.btn_start, "START RACE"), (self.btn_demo, "AI DEMONSTRATION"),
                           (self.btn_quit, "QUIT")]:
            pygame.draw.rect(self.screen, (40, 120, 240), btn, border_radius=8)
            pygame.draw.rect(self.screen, WHITE, btn, 2, border_radius=8)
            txt = self.font_btn.render(label, True, WHITE)
            self.screen.blit(txt, txt.get_rect(center=btn.center))

    # ------------------------------------------------------------------ Racing
    def _update_racing(self, keys):
        if self.race:
            self.race.update(keys)
            if self.race.state == "finished" and self.perf_chart_surface is None:
                self._generate_performance_chart()
                self.state = "RESULTS"

    def _draw_racing(self):
        draw_track(self.world)
        if self.show_routes:
            self.race.draw_routes(self.world)
        self.race.draw(self.world)

        self.screen.fill(GRASS_COLOR)
        self.screen.blit(self.world, self.race.effects.shake_offset())
        self.hud.draw(self.screen, self.race)

    # ------------------------------------------------------------------ Results Screen
    def _generate_performance_chart(self):
        """Build Matplotlib performance charts directly after race end."""
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(8.5, 3.5), facecolor='#0C101C')

        names = [r.name for r in self.race.racers]
        times = [r.finish_time if r.finished else 99.0 for r in self.race.racers]
        colors = [r.car.color for r in self.race.racers]
        rgb_colors = [[c[0] / 255, c[1] / 255, c[2] / 255] for c in colors]

        # Bar chart: Lap Times
        ax1.set_facecolor('#0C101C')
        ax1.barh(names, times, color=rgb_colors)
        ax1.set_title("Race Completion Time (s)", color='white', fontsize=10)
        ax1.tick_params(colors='white', labelsize=8)
        ax1.invert_yaxis()

        # Scatter/Line chart: Simulated Fuel Depletion
        ax2.set_facecolor('#0C101C')
        for r, col in zip(self.race.racers, rgb_colors):
            ax2.plot([0, 1, 2, 3], [100, r.car.fuel + 20, r.car.fuel + 10, r.car.fuel], label=r.name, color=col)
        ax2.set_title("Fuel Remaining per Lap", color='white', fontsize=10)
        ax2.tick_params(colors='white', labelsize=8)
        ax2.grid(True, alpha=0.2)

        fig.tight_layout()
        canvas = plt.get_current_fig_manager().canvas
        canvas.draw()
        raw_data = canvas.buffer_rgba().tobytes()
        size = canvas.get_width_height()
        self.perf_chart_surface = pygame.image.fromstring(raw_data, size, "RGBA")
        plt.close(fig)

    def _draw_results(self):
        self.screen.fill((12, 16, 28))
        self.hud._draw_results(self.screen, self.race)

        if self.perf_chart_surface:
            rect = self.perf_chart_surface.get_rect(center=(WIDTH // 2, HEIGHT - 180))
            self.screen.blit(self.perf_chart_surface, rect)

        self.btn_back = pygame.Rect(20, 20, 120, 40)
        pygame.draw.rect(self.screen, (40, 120, 240), self.btn_back, border_radius=6)
        txt = self.font_btn.render("MAIN MENU", True, WHITE)
        self.screen.blit(txt, txt.get_rect(center=self.btn_back.center))

    # ------------------------------------------------------------------ AI Demo View
    def _generate_ai_demo_chart(self):
        """Render Search Paths, Optimization, and Prediction Visualizations."""
        fig, axes = plt.subplots(1, 3, figsize=(11.5, 4.0), facecolor='#0C101C')

        # 1. Search Comparison
        graph = TrackGraph()
        s, t = (0, graph.centre_lane), (graph.stations, graph.centre_lane)
        r_bfs = bfs(graph, s, t)
        r_astar = astar(graph, s, t, "track")

        axes[0].set_facecolor('#0C101C')
        axes[0].bar(["BFS", "A* (Track)"], [r_bfs.expanded, r_astar.expanded], color=['#e0524d', '#3b82f6'])
        axes[0].set_title("Search Frontier: Nodes Expanded", color='white', fontsize=10)
        axes[0].tick_params(colors='white', labelsize=8)

        # 2. Risk Prediction Probabilities
        predictor = RacePredictor()
        proba, _ = predictor.risk(140, 45, 80, "Rainy")
        axes[1].set_facecolor('#0C101C')
        axes[1].pie(proba.values(), labels=proba.keys(), colors=['#60c850', '#fa7d28', '#e12832'],
                    textprops={'color': 'w', 'fontsize': 8}, autopct='%1.0f%%')
        axes[1].set_title("Bayesian Risk (Wet+Worn)", color='white', fontsize=10)

        # 3. Pit Stop CSP Scheduling
        cars = make_scenario(4, seed=1)
        res = solve(PitStopCSP(cars, 15))
        axes[2].set_facecolor('#0C101C')
        if res.solved:
            stops_per_car = [len([s for s in res.stops if s.car == c.name]) for c in cars]
            axes[2].bar([c.name for c in cars], stops_per_car, color='#fae528')
            axes[2].set_title(f"Scheduled Pit Stops ({res.time_ms:.1f}ms)", color='white', fontsize=10)
            axes[2].tick_params(colors='white', labelsize=7)

        fig.tight_layout()
        canvas = plt.get_current_fig_manager().canvas
        canvas.draw()
        raw_data = canvas.buffer_rgba().tobytes()
        size = canvas.get_width_height()
        self.ai_demo_surface = pygame.image.fromstring(raw_data, size, "RGBA")
        plt.close(fig)

    def _draw_ai_demo(self):
        self.screen.fill((12, 16, 28))

        t_surf = self.font_sub.render("AI PATHFINDING, PREDICTION & CONSTRAINT DIAGNOSTICS", True, YELLOW)
        self.screen.blit(t_surf, t_surf.get_rect(center=(WIDTH // 2, 40)))

        if self.ai_demo_surface:
            rect = self.ai_demo_surface.get_rect(center=(WIDTH // 2, HEIGHT // 2 + 10))
            self.screen.blit(self.ai_demo_surface, rect)

        self.btn_back = pygame.Rect(20, 20, 120, 40)
        pygame.draw.rect(self.screen, (40, 120, 240), self.btn_back, border_radius=6)
        txt = self.font_btn.render("MAIN MENU", True, WHITE)
        self.screen.blit(txt, txt.get_rect(center=self.btn_back.center))


if __name__ == "__main__":
    engine = GameEngine()
    engine.run()