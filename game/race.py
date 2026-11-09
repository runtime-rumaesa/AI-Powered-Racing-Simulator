import math

import pygame

from settings import *
from ai.optimization import load_best_style
from ai.search import plan_lap_route, STRATEGY_LABELS
from game import collision
from game.car import Car, AIController
from game.effects import Effects
from game.track import get_track, get_waypoints


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

    @property
    def is_player(self):
        return self.controller is None


class Race:
    """Owns the cars and runs the race: countdown -> racing -> finished.

    Time is counted in frames (1/FPS per frame), so a race is repeatable
    and can later be run without a window for the AI experiments.
    """

    def __init__(self, num_ai=NUM_AI_CARS, total_laps=NUM_LAPS):
        self.track = get_track()
        self.effects = Effects()
        self.total_laps = total_laps
        self.checkpoints = get_waypoints()[::CHECKPOINT_STEP]
        self.num_cp = len(self.checkpoints)

        self.state = "countdown"
        self.countdown = float(COUNTDOWN_SECONDS)
        self.race_time = 0.0
        self.finish_order = []

        self.racers = []
        num_ai = max(0, min(num_ai, 5))
        for slot in range(num_ai + 1):
            x, y, angle = self.track.grid_slot(slot)
            if slot == 0:
                self.racers.append(Racer("You", Car(x=x, y=y, angle=angle)))
            else:
                i = slot - 1
                strategy = AI_STRATEGIES[i % len(AI_STRATEGIES)]
                name = STRATEGY_LABELS[strategy]
                if i >= len(AI_STRATEGIES):
                    name += f" {i // len(AI_STRATEGIES) + 1}"
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
                self.racers.append(Racer(name, car, AIController(route, style), strategy))

        self.player = self.racers[0]

    # ----------------------------------------------------------------- update
    def update(self, keys):
        self.effects.update()

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
            if racer.finished:
                car.throttle = 0.0
                car.steer = 0.0
            elif racer.is_player:
                car.handle_input(keys)
            else:
                racer.controller.update(car)
                if racer.controller.needs_respawn:
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

        if self.player.finished:
            self.state = "finished"

    def respawn(self, racer):
        """Put a stuck car back on the centre line, facing the right way."""
        car = racer.car
        x, y, angle = self.track.respawn_pose(car.x, car.y)
        car.set_state((x, y, angle))
        car.speed = 0.0
        racer.prev_pos = (x, y)
        if racer.controller is not None:
            racer.controller.reset_stuck()

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
            if racer.best_lap is None or lap_time < racer.best_lap:
                racer.best_lap = lap_time

            if racer.laps >= self.total_laps:
                racer.finished = True
                racer.finish_time = self.race_time
                self.finish_order.append(racer)

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