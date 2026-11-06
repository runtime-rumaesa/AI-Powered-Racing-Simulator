import math

from settings import *
from game import collision
from game.car import Car, AIController
from game.track import get_waypoints


class Racer:
    """A car plus its race progress. controller=None means the human player."""

    def __init__(self, name, car, controller=None):
        self.name = name
        self.car = car
        self.controller = controller

        self.laps = 0
        self.next_cp = 1          # next checkpoint to hit (0 is the start line)
        self.prev_x = car.x
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
            x, y = self._grid_slot(slot)
            if slot == 0:
                self.racers.append(Racer("You", Car(x=x, y=y)))
            else:
                i = slot - 1
                car = Car(
                    x=x,
                    y=y,
                    color=AI_COLORS[i % len(AI_COLORS)],
                    max_speed=CAR_MAX_SPEED * AI_SPEED_FACTORS[i % len(AI_SPEED_FACTORS)],
                )
                # Each AI drives a lane that matches its grid slot
                lane = get_waypoints(offset=CAR_START_Y - y)
                self.racers.append(Racer(f"AI {slot}", car, AIController(lane)))

        self.player = self.racers[0]

    @staticmethod
    def _grid_slot(slot):
        """Two cars per row, rows going back from the start line."""
        row = slot // 2
        x = FINISH_LINE_X - 20 - 35 * row
        y = CAR_START_Y - 20 if slot % 2 == 0 else CAR_START_Y + 20
        return x, y

    # ----------------------------------------------------------------- update
    def update(self, keys):
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

            racer.prev_x = car.x
            last_good = car.get_state()
            car.update()
            collision.resolve_wall_collision(car, last_good)

        # Cars that already finished are ignored so they don't block the others
        collision.resolve_car_collisions([r.car for r in self.racers if not r.finished])

        for racer in self.racers:
            if not racer.finished:
                self._update_progress(racer)

        if self.player.finished:
            self.state = "finished"

    def _update_progress(self, racer):
        """Checkpoints must be hit in order, then the finish line is crossed."""
        car = racer.car

        if racer.next_cp < self.num_cp:
            cx, cy = self.checkpoints[racer.next_cp]
            if math.hypot(car.x - cx, car.y - cy) < CHECKPOINT_RADIUS:
                racer.next_cp += 1

        # All checkpoints done: crossing the line left-to-right on the top
        # straight completes the lap
        elif racer.prev_x < FINISH_LINE_X <= car.x and car.y < TRACK_CENTER[1]:
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
    def draw(self, screen):
        for racer in reversed(self.racers):  # player is drawn last, on top
            racer.car.draw(screen)