import pygame
import math
from settings import (
    WIDTH, HEIGHT, TRACK_WIDTH, TRACK_POINTS,
    NUM_WAYPOINTS, CHECKPOINT_RADIUS, ROAD_HALF_WIDTH,
    WHITE, GRAY, GREEN
)


class Track:
    def __init__(self):
        self.width = WIDTH
        self.height = HEIGHT

        # Base centerline control waypoints for the circuit from settings
        self.waypoints = [pygame.math.Vector2(pt) for pt in TRACK_POINTS]

        # Generate checkpoints along the track path
        self.checkpoints = self._generate_checkpoints(density=3)

        # Grid spawn positions for race cars (Player + AI cars)
        start_pos = self.checkpoints[0]
        direction = (self.checkpoints[1] - start_pos).normalize()
        perp = pygame.math.Vector2(-direction.y, direction.x)

        self.spawn_points = [
            start_pos - direction * 30 + perp * 20,  # Grid 1 (Player)
            start_pos - direction * 30 - perp * 20,  # Grid 2 (AI A*)
            start_pos - direction * 70 + perp * 20,  # Grid 3 (AI GA)
            start_pos - direction * 70 - perp * 20  # Grid 4 (AI BFS)
        ]

    def _generate_checkpoints(self, density=3):
        cps = []
        num_pts = len(self.waypoints)
        for i in range(num_pts):
            p0 = self.waypoints[i]
            p1 = self.waypoints[(i + 1) % num_pts]
            for t_step in range(density):
                t = t_step / density
                cps.append(p0.lerp(p1, t))
        return cps

    def is_off_track(self, point):
        """Calculates distance from point to nearest track centerline segment."""
        min_dist = float('inf')
        num_pts = len(self.checkpoints)
        for i in range(num_pts):
            p1 = self.checkpoints[i]
            p2 = self.checkpoints[(i + 1) % num_pts]

            l2 = p1.distance_squared_to(p2)
            if l2 == 0:
                dist = point.distance_to(p1)
            else:
                t = max(0, min(1, (point - p1).dot(p2 - p1) / l2))
                projection = p1 + t * (p2 - p1)
                dist = point.distance_to(projection)

            if dist < min_dist:
                min_dist = dist

        return min_dist > ROAD_HALF_WIDTH

    def draw(self, surface):
        surface.fill((46, 125, 50))  # Track grass background

        # Draw track surface
        if len(self.checkpoints) > 2:
            pts = [(int(p.x), int(p.y)) for p in self.checkpoints]
            pygame.draw.polygon(surface, (66, 68, 74), pts, width=ROAD_HALF_WIDTH * 2)
            pygame.draw.polygon(surface, (200, 200, 200), pts, width=(ROAD_HALF_WIDTH * 2) + 6)
            pygame.draw.polygon(surface, (66, 68, 74), pts, width=ROAD_HALF_WIDTH * 2)

            # Center line
            pygame.draw.lines(surface, (250, 205, 40), True, pts, 2)

        # Draw Finish Line
        if len(self.checkpoints) >= 2:
            p1 = self.checkpoints[0]
            p2 = self.checkpoints[1]
            dir_vec = (p2 - p1).normalize()
            perp = pygame.math.Vector2(-dir_vec.y, dir_vec.x) * ROAD_HALF_WIDTH
            pygame.draw.line(surface, WHITE, p1 - perp, p1 + perp, 6)


_track_instance = None


def get_track():
    global _track_instance
    if _track_instance is None:
        _track_instance = Track()
    return _track_instance


def get_waypoints():
    """Returns the generated track waypoints list for search graph construction."""
    return get_track().waypoints


def draw_track(surface):
    track = get_track()
    track.draw(surface)