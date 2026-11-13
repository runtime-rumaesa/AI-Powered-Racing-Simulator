import math

import pygame

from settings import *
from ai.optimization import load_best_style
from ai.search import plan_lap_route, STRATEGY_LABELS
from game import collision
from game.conditions import CarSetup, WeatherEffects, apply_conditions, tyre_wear_this_frame
from game.car import Car, AIController
from game.effects import Effects
from game.track import get_track, get_waypoints


LOST_SECONDS = 4.0   # an AI car with no new checkpoint for this long is put back on track
FINISH_GRACE_SECONDS = 20.0   # after the player finishes, the others get this long to finish too


# ----------------------------------------------------------------- AI lineups
class Preset:
    """A lineup of AI opponents the player can pick in the menu.

    `strategies` has one entry per AI car, in grid order (the first one starts
    just behind the player). The keys are the ones plan_lap_route() understands.
    """

    def __init__(self, key, name, summary, strategies):
        self.key = key
        self.name = name
        self.summary = summary
        self.strategies = list(strategies)


RACE_PRESETS = [
    Preset("mixed", "Mixed Grid",
           "One of everything: a search route (A*, BFS) and a tuned driver (Hill Climbing, Genetic) "
           "on the same grid. Who is fastest overall?",
           ["astar", "bfs", "hc", "ga"]),
    Preset("search", "Search Showdown",
           "Same default driving style, different routes: A* and BFS plan their line over the track "
           "graph, Baseline just follows the centre line.",
           ["astar", "bfs", "baseline"]),
    Preset("optimization", "Optimization Grid",
           "Same A* route, different driving styles: the hand-made default against the style "
           "tuned by Hill Climbing and by the Genetic Algorithm.",
           ["astar", "hc", "ga"]),
    Preset("baseline", "Baseline Grid",
           "Four identical Baseline cars: centre-line route and default style. "
           "The control group - nothing is searched or optimized.",
           ["baseline"] * 4),
]


def get_preset(key):
    """The preset with this key (or the first one if the key is unknown)."""
    for preset in RACE_PRESETS:
        if preset.key == key:
            return preset
    return RACE_PRESETS[0]


def lineup_names(strategies):
    """Display names for a lineup. Repeated strategies are numbered: Baseline AI, Baseline AI 2, ..."""
    seen = {}
    names = []
    for strategy in strategies:
        seen[strategy] = seen.get(strategy, 0) + 1
        name = STRATEGY_LABELS[strategy]
        if seen[strategy] > 1:
            name += f" {seen[strategy]}"
        names.append(name)
    return names


class Racer:
    """A car plus its race progress. controller=None means the human player."""

    def __init__(self, name, car, controller=None, strategy=None):
        self.name = name
        self.strategy = strategy
        self.car = car
        self.controller = controller

        self.laps = 0
        self.next_cp = 1          # next checkpoint to hit (0 is the start line)
        self.prev_pos = (car.x, car.y)
        self.finished = False
        self.finish_time = None
        self.lap_start = 0.0
        self.last_lap = None
        self.best_lap = None
        self.setup = CarSetup(car)   # the car's own physics, before weather and tyres change them
        self.tyre_wear = 0.0         # 0 = new .. TYRE_MAX_WEAR = destroyed
        self.grip = 1.0              # traction this frame (weather and tyres)
        self.corner_speed = controller.style["corner_speed"] if controller else None   # the driver's own gene
        self.lap_times = []       # seconds of every completed lap, in order
        self.finish_place = None  # 1 = first across the line
        self.respawns = 0         # times it was put back on the track
        self.progress_mark = 0    # laps * checkpoints + next_cp when it last moved on
        self.progress_time = 0.0  # race time of that moment (used to rescue lost AI cars)

    @property
    def is_player(self):
        return self.controller is None


class Race:
    """Owns the cars and runs the race: countdown -> racing -> finished.

    Time is counted in frames (1/FPS per frame), so a race is repeatable
    and can later be run without a window for the AI experiments.
    """

    def __init__(self, num_ai=NUM_AI_CARS, total_laps=NUM_LAPS, preset=None, weather="Clear"):
        """preset: a Preset (or its key) chooses the AI opponents. Without one, the
        opponents are the first `num_ai` entries of AI_STRATEGIES in settings.py.
        weather: "Clear", "Cloudy" or "Rainy" (see game/conditions.py)."""
        self.weather = weather if weather in WEATHER_NAMES else "Clear"
        self.weather_fx = WeatherEffects(self.weather)
        self.track = get_track()
        self.effects = Effects()
        self.total_laps = total_laps
        self.checkpoints = get_waypoints()[::CHECKPOINT_STEP]
        self.num_cp = len(self.checkpoints)

        self.state = "countdown"
        self.countdown = float(COUNTDOWN_SECONDS)
        self.race_time = 0.0
        self.finish_order = []

        if isinstance(preset, str):
            preset = get_preset(preset)
        self.preset = preset
        if preset is not None:
            strategies = preset.strategies
        else:
            strategies = [AI_STRATEGIES[i % len(AI_STRATEGIES)] for i in range(num_ai)]
        strategies = strategies[:5]          # the grid has room for the player and five AI cars
        names = lineup_names(strategies)

        self.racers = []
        x, y, angle = self.track.grid_slot(0)
        self.racers.append(Racer("You", Car(x=x, y=y, angle=angle)))
        for i, strategy in enumerate(strategies):
            slot = i + 1
            x, y, angle = self.track.grid_slot(slot)
            car = Car(
                x=x,
                y=y,
                angle=angle,
                color=AI_COLORS[i % len(AI_COLORS)],
                max_speed=CAR_MAX_SPEED * AI_SPEED_FACTOR,
            )
            # The route comes from a search algorithm (ai/search.py), the
            # driving style from an optimizer (ai/optimization.py)
            lateral = -LANE_OFFSET if slot % 2 == 0 else LANE_OFFSET  # grid lane
            route = list(plan_lap_route(strategy, lateral))
            style = load_best_style(strategy)  # None unless hc / ga
            self.racers.append(Racer(names[i], car, AIController(route, style), strategy))

        self.player = self.racers[0]

    # ----------------------------------------------------------------- update
    def update(self, keys):
        self.effects.update()
        self.weather_fx.update()

        if self.state == "countdown":
            self.countdown -= 1 / FPS
            if self.countdown <= 0:
                self.countdown = 0.0
                self.state = "racing"
            return
        if self.state == "finished":
            return

        self.race_time += 1 / FPS

        for racer in self.racers:
            car = racer.car
            # Weather, worn tyres and the weight of the fuel change how the car handles.
            # The AI drives to its grip: on a slippery road it keeps less speed in corners.
            racer.grip = apply_conditions(car, racer.setup, self.weather, racer.tyre_wear)
            if racer.finished:
                car.throttle = 0.0
                car.steer = 0.0
            elif racer.is_player:
                car.handle_input(keys)
            else:
                racer.controller.style["corner_speed"] = racer.corner_speed * racer.grip ** 2
                racer.controller.update(car)
                if racer.controller.needs_respawn or self._lost(racer):
                    self.respawn(racer)

            racer.prev_pos = (car.x, car.y)
            last_good = car.get_state()
            car.update()

            impact = abs(car.speed)
            if collision.resolve_wall_collision(car, last_good) and impact > 1.0:
                self.effects.add_sparks(car.x, car.y, impact / CAR_MAX_SPEED)
                if racer.is_player:
                    self.effects.shake_camera(2 + impact * 1.2)

            self._tyre_effects(car)
            if not racer.finished:
                racer.tyre_wear = min(TYRE_MAX_WEAR, racer.tyre_wear + tyre_wear_this_frame(car))

        # Cars that already finished are ignored so they don't block the others.
        # AI cars drive through each other and only bump the player: they all
        # follow similar racing lines, so contact between them would be luck
        # and would hide which route is really better.
        active = [r.car for r in self.racers if not r.finished]
        ai_pair = lambda a, b: a is not self.player.car and b is not self.player.car
        for x, y, a, b in collision.resolve_car_collisions(active, ignore_pair=ai_pair):
            self.effects.add_sparks(x, y, 0.6)
            if self.player.car in (a, b):
                self.effects.shake_camera(4)

        for racer in self.racers:
            if not racer.finished:
                self._update_progress(racer)

        # The race does not stop the moment the player finishes: the other cars keep
        # racing until they finish too (or FINISH_GRACE_SECONDS pass). Only then are
        # the results final - otherwise every slower car would be a "DNF".
        if self.state == "racing" and self.player.finished:
            self.state = "finishing"
        if self.state == "finishing":
            waited = self.race_time - self.player.finish_time
            if all(r.finished for r in self.racers) or waited > FINISH_GRACE_SECONDS:
                self.state = "finished"

    def skip_to_results(self):
        """The player does not want to wait for the other cars."""
        if self.state == "finishing":
            self.state = "finished"

    def _lost(self, racer):
        """True when an AI car has not reached a new checkpoint for LOST_SECONDS.

        The AI notices a car that sits still (needs_respawn), but one that keeps
        pushing against a wall and backing off again looks busy. This catches it.
        """
        mark = racer.laps * self.num_cp + racer.next_cp
        if mark != racer.progress_mark:
            racer.progress_mark = mark
            racer.progress_time = self.race_time
        return self.race_time - racer.progress_time > LOST_SECONDS

    def respawn(self, racer):
        """Put a stuck car back on the centre line, facing the right way."""
        car = racer.car
        racer.respawns += 1
        racer.progress_time = self.race_time
        x, y, angle = self.track.respawn_pose(car.x, car.y)
        car.set_state((x, y, angle))
        car.speed = 0.0
        racer.prev_pos = (x, y)
        if racer.controller is not None:
            racer.controller.reset_stuck()
            self.aim_ahead(racer.controller, x, y)

    @staticmethod
    def aim_ahead(controller, x, y):
        """Point an AI driver at the first waypoint in front of (x, y).

        After a car is put back on the track its old target can be behind it,
        and the car would drive the wrong way round the circuit.
        """
        points = controller.waypoints
        nearest = min(range(len(points)), key=lambda k: math.hypot(points[k][0] - x, points[k][1] - y))
        controller.target = (nearest + 1) % len(points)

    def _tyre_effects(self, car):
        if not car.skidding:
            return
        for wx, wy in car.rear_wheels():
            self.effects.add_skid(wx, wy)
            if int(self.race_time * FPS) % 3 == 0:
                self.effects.add_smoke(wx, wy)

    def _update_progress(self, racer):
        """Checkpoints must be hit in order, then the finish line is crossed."""
        car = racer.car

        if racer.next_cp < self.num_cp:
            cx, cy = self.checkpoints[racer.next_cp]
            if math.hypot(car.x - cx, car.y - cy) < CHECKPOINT_RADIUS:
                racer.next_cp += 1

        # All checkpoints done: crossing the finish line completes the lap
        elif self.track.crossed_finish(racer.prev_pos, (car.x, car.y)):
            racer.laps += 1
            racer.next_cp = 1

            lap_time = self.race_time - racer.lap_start
            racer.lap_start = self.race_time
            racer.last_lap = lap_time
            racer.lap_times.append(lap_time)
            if racer.best_lap is None or lap_time < racer.best_lap:
                racer.best_lap = lap_time

            if racer.laps >= self.total_laps:
                racer.finished = True
                racer.finish_time = self.race_time
                self.finish_order.append(racer)
                racer.finish_place = len(self.finish_order)

    # -------------------------------------------------------------- standings
    def _progress(self, racer):
        """Bigger = further ahead. Distance to the next checkpoint breaks ties."""
        target = self.checkpoints[racer.next_cp] if racer.next_cp < self.num_cp else self.checkpoints[0]
        dist = math.hypot(racer.car.x - target[0], racer.car.y - target[1])
        return racer.laps * self.num_cp + racer.next_cp - dist / 10000

    def standings(self):
        done = sorted((r for r in self.racers if r.finished), key=lambda r: r.finish_time)
        rest = sorted((r for r in self.racers if not r.finished), key=self._progress, reverse=True)
        return done + rest

    def position_of(self, racer):
        return self.standings().index(racer) + 1

    @property
    def winner(self):
        return self.finish_order[0] if self.finish_order else None

    # ---------------------------------------------------------------- drawing
    def draw_routes(self, screen):
        """Debug view: the route each AI planned, in the colour of its car."""
        for racer in self.racers:
            if racer.controller is None:
                continue
            points = racer.controller.waypoints
            pygame.draw.lines(screen, racer.car.color, True, points, 3)
            for p in points:
                pygame.draw.circle(screen, WHITE, (int(p[0]), int(p[1])), 2)

    def draw(self, screen):
        self.effects.draw_under(screen)
        for racer in reversed(self.racers):  # player is drawn last, on top
            racer.car.draw(screen)
        self.effects.draw_over(screen)
        self.weather_fx.draw(screen)