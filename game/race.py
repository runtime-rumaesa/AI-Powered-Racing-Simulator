import pygame
import time
from settings import *
from game.car import Car
from game.track import get_track
from game.effects import EffectsManager
from game.collision import resolve_car_collisions, check_wall_collisions


class Racer:
    def __init__(self, name, car, controller_type="ai", strategy=None):
        self.name = name
        self.car = car
        self.controller_type = controller_type
        self.strategy = strategy
        self.current_lap = 1
        self.checkpoint_idx = 0
        self.finished = False
        self.finish_time = 0.0
        self.lap_times = []


class Race:
    def __init__(self):
        self.track = get_track()
        self.effects = EffectsManager()
        self.state = "racing"  # "countdown", "racing", "finished"
        self.start_time = time.time()

        # Initialize Player and AI Racers
        self.racers = [
            Racer("Player (Human)", Car(self.track.spawn_points[0], RED), controller_type="human"),
            Racer("AI - A* Search", Car(self.track.spawn_points[1], BLUE), controller_type="ai", strategy="astar"),
            Racer("AI - Genetic", Car(self.track.spawn_points[2], GREEN), controller_type="ai", strategy="ga"),
            Racer("AI - BFS Route", Car(self.track.spawn_points[3], YELLOW), controller_type="ai", strategy="bfs")
        ]

        self.player = self.racers[0]

    def update(self, keys):
        if self.state == "finished":
            return

        current_time = time.time() - self.start_time

        # Update each vehicle
        for racer in self.racers:
            if racer.finished:
                continue

            if racer.controller_type == "human":
                racer.car.update_human(keys)
            else:
                racer.car.update_ai(self.track, racer.strategy)

            # Physics & Wall collision
            check_wall_collisions(racer.car, self.track)

            # Progress & Lap tracking
            self._update_progress(racer, current_time)

            # Spawn skid marks/smoke
            if racer.car.is_drifting:
                self.effects.add_skid_mark(racer.car.position)

        # Handle vehicle-to-vehicle impacts
        resolve_car_collisions([r.car for r in self.racers])

        self.effects.update()

        # Check race end conditions
        if all(r.finished for r in self.racers) or self.player.finished:
            self.state = "finished"

    def _update_progress(self, racer, current_time):
        target_checkpoint = self.track.checkpoints[racer.checkpoint_idx]
        dist_sq = racer.car.position.distance_to(target_checkpoint)

        if dist_sq < CHECKPOINT_RADIUS ** 2:
            racer.checkpoint_idx += 1

            # Completed a lap
            if racer.checkpoint_idx >= len(self.track.checkpoints):
                racer.checkpoint_idx = 0
                racer.current_lap += 1

                if racer.current_lap > TOTAL_LAPS:
                    racer.finished = True
                    racer.finish_time = current_time

    def get_standings(self):
        """Sort racers by lap count, checkpoint progression, and distance to next checkpoint."""

        def key_func(racer):
            if racer.finished:
                return (TOTAL_LAPS + 1, -racer.finish_time)
            dist_to_next = racer.car.position.distance_to(self.track.checkpoints[racer.checkpoint_idx])
            return (racer.current_lap, racer.checkpoint_idx, -dist_to_next)

        return sorted(self.racers, key=key_func, reverse=True)

    def respawn(self, racer):
        """Reset vehicle position back to the previous checkpoint."""
        cp = self.track.checkpoints[racer.checkpoint_idx - 1]
        racer.car.position = pygame.math.Vector2(cp)
        racer.car.speed = 0.0

    def draw(self, surface):
        self.effects.draw(surface)
        for racer in self.racers:
            racer.car.draw(surface)

    def draw_routes(self, surface):
        """Overlay target paths calculated by search algorithms."""
        for racer in self.racers:
            if racer.controller_type == "ai":
                racer.car.draw_path(surface)