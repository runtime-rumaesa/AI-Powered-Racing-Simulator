import math
import random

import pygame
from settings import *


# ----------------------------------------------------------------- geometry
def _catmull_rom(points, samples=30):
    """Smooth closed curve through the control points."""
    n = len(points)
    out = []
    for i in range(n):
        p0, p1, p2, p3 = points[(i - 1) % n], points[i], points[(i + 1) % n], points[(i + 2) % n]
        for s in range(samples):
            t = s / samples
            t2, t3 = t * t, t * t * t
            x = 0.5 * (2 * p1[0] + (-p0[0] + p2[0]) * t
                       + (2 * p0[0] - 5 * p1[0] + 4 * p2[0] - p3[0]) * t2
                       + (-p0[0] + 3 * p1[0] - 3 * p2[0] + p3[0]) * t3)
            y = 0.5 * (2 * p1[1] + (-p0[1] + p2[1]) * t
                       + (2 * p0[1] - 5 * p1[1] + 4 * p2[1] - p3[1]) * t2
                       + (-p0[1] + 3 * p1[1] - 3 * p2[1] + p3[1]) * t3)
            out.append((x, y))
    return out


def _resample(points, step):
    """Re-space a closed polyline so points are `step` pixels apart."""
    n = len(points)
    seg = [math.dist(points[i], points[(i + 1) % n]) for i in range(n)]
    total = sum(seg)
    count = max(8, int(total / step))
    out, i, acc = [], 0, 0.0
    for k in range(count):
        target = total * k / count
        while acc + seg[i] < target:
            acc += seg[i]
            i += 1
        f = (target - acc) / seg[i] if seg[i] else 0.0
        a, b = points[i], points[(i + 1) % n]
        out.append((a[0] + (b[0] - a[0]) * f, a[1] + (b[1] - a[1]) * f))
    return out, total


def _angle_diff(a, b):
    return abs((b - a + 180) % 360 - 180)


# -------------------------------------------------------------------- track
class Track:
    """The circuit: centre line, collision mask and a pre-rendered picture."""

    def __init__(self):
        raw = _catmull_rom(TRACK_POINTS)
        self.center, self.length = _resample(raw, TRACK_STEP)
        n = len(self.center)

        self.tangents = []
        for i in range(n):
            ax, ay = self.center[(i - 1) % n]
            bx, by = self.center[(i + 1) % n]
            dx, dy = bx - ax, by - ay
            d = math.hypot(dx, dy) or 1.0
            self.tangents.append((dx / d, dy / d))

        headings = [math.degrees(math.atan2(ty, tx)) for tx, ty in self.tangents]
        self.turning = [_angle_diff(headings[(i - 8) % n], headings[(i + 8) % n]) for i in range(n)]

        self.mask = self._build_mask()
        self.background = self._build_background()

    # ------------------------------------------------------------- queries
    def edge_point(self, i, lateral):
        """Point `lateral` pixels to the right of the centre line at sample i."""
        x, y = self.center[i % len(self.center)]
        tx, ty = self.tangents[i % len(self.center)]
        return (x - ty * lateral, y + tx * lateral)

    def is_on_road(self, x, y):
        ix, iy = int(x), int(y)
        if 0 <= ix < WIDTH and 0 <= iy < HEIGHT:
            return bool(self.mask.get_at((ix, iy)))
        return False

    def crossed_finish(self, prev, cur):
        """Did a car moving prev -> cur cross the finish line (in the right direction)?"""
        px, py = self.center[0]
        tx, ty = self.tangents[0]
        d_prev = (prev[0] - px) * tx + (prev[1] - py) * ty
        d_cur = (cur[0] - px) * tx + (cur[1] - py) * ty
        lateral = (cur[0] - px) * -ty + (cur[1] - py) * tx
        return d_prev < 0 <= d_cur and abs(lateral) <= ROAD_HALF_WIDTH + 5

    def respawn_pose(self, x, y):
        """(x, y, angle) on the centre line, facing the right way, nearest to (x, y)."""
        i = min(range(len(self.center)), key=lambda k: math.hypot(self.center[k][0] - x, self.center[k][1] - y))
        tx, ty = self.tangents[i]
        return self.center[i][0], self.center[i][1], math.degrees(math.atan2(ty, tx))

    def grid_slot(self, slot):
        """(x, y, angle) for a starting-grid slot: two cars per row behind the line."""
        row = slot // 2
        back = (20 + 55 * row) / TRACK_STEP
        i = -int(back)
        lateral = -LANE_OFFSET if slot % 2 == 0 else LANE_OFFSET
        x, y = self.edge_point(i, lateral)
        tx, ty = self.tangents[i % len(self.center)]
        return x, y, math.degrees(math.atan2(ty, tx))

    # ----------------------------------------------------------- rendering
    def _build_mask(self):
        surf = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        for x, y in self.center:
            pygame.draw.circle(surf, (255, 255, 255, 255), (int(x), int(y)), ROAD_HALF_WIDTH)
        self._road_surface = surf
        return pygame.mask.from_surface(surf)

    def _build_background(self):
        rng = random.Random(7)
        bg = pygame.Surface((WIDTH, HEIGHT))

        # Grass with mowing stripes and speckles
        bg.fill(GRASS_COLOR)
        for k, y in enumerate(range(0, HEIGHT, 56)):
            if k % 2:
                pygame.draw.rect(bg, (51, 133, 56), (0, y, WIDTH, 56))
        for _ in range(7000):
            shade = rng.choice([(40, 112, 44), (56, 140, 60), (36, 104, 40)])
            bg.fill(shade, (rng.randrange(WIDTH), rng.randrange(HEIGHT), 2, 2))

        self._draw_trees(bg, rng)

        # Light run-off band, then a dark barrier right at the wall
        for x, y in self.center:
            pygame.draw.circle(bg, (70, 158, 72), (int(x), int(y)), ROAD_HALF_WIDTH + 20)
        for x, y in self.center:
            pygame.draw.circle(bg, (38, 38, 44), (int(x), int(y)), ROAD_HALF_WIDTH + 5)

        # Asphalt: speckled texture cut out with the road mask
        asphalt = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        asphalt.fill(ROAD_COLOR)
        for _ in range(14000):
            shade = rng.choice([(58, 60, 66), (76, 78, 84), (62, 64, 70)])
            asphalt.fill(shade, (rng.randrange(WIDTH), rng.randrange(HEIGHT), 2, 2))
        asphalt.blit(self._road_surface, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
        bg.blit(asphalt, (0, 0))

        self._draw_curbs(bg)
        self._draw_lines(bg)
        self._draw_finish_line(bg)
        return bg

    def _draw_trees(self, bg, rng):
        near = self.center[::3]
        placed = []
        for _ in range(900):
            if len(placed) >= 70:
                break
            x, y = rng.randrange(20, WIDTH - 20), rng.randrange(20, HEIGHT - 20)
            r = rng.randrange(13, 22)
            if any(math.hypot(x - cx, y - cy) < ROAD_HALF_WIDTH + 30 + r for cx, cy in near):
                continue
            if any(math.hypot(x - px, y - py) < 36 for px, py, _ in placed):
                continue
            placed.append((x, y, r))

        for x, y, r in placed:
            shadow = pygame.Surface((r * 3, r * 3), pygame.SRCALPHA)
            pygame.draw.ellipse(shadow, (0, 0, 0, 70), (r // 2, r // 2, r * 2, r * 2))
            bg.blit(shadow, (x - r * 1.5 + 5, y - r * 1.5 + 6))
            pygame.draw.circle(bg, (22, 88, 34), (x, y), r)
            pygame.draw.circle(bg, (34, 115, 46), (x, y), int(r * 0.78))
            pygame.draw.circle(bg, (62, 152, 68), (x - r * 0.18, y - r * 0.18), int(r * 0.48))

    def _draw_curbs(self, bg):
        n = len(self.center)
        for i in range(n):
            if self.turning[i] < CURB_ANGLE:
                continue
            color = (215, 35, 45) if (i // 5) % 2 == 0 else (245, 245, 245)
            for side in (-1, 1):
                quad = [
                    self.edge_point(i, side * (ROAD_HALF_WIDTH - 10)),
                    self.edge_point(i, side * ROAD_HALF_WIDTH),
                    self.edge_point(i + 1, side * ROAD_HALF_WIDTH),
                    self.edge_point(i + 1, side * (ROAD_HALF_WIDTH - 10)),
                ]
                pygame.draw.polygon(bg, color, quad)

    def _draw_lines(self, bg):
        n = len(self.center)
        # White edge lines
        for side in (-1, 1):
            pts = [self.edge_point(i, side * (ROAD_HALF_WIDTH - 2)) for i in range(n)]
            pygame.draw.lines(bg, (235, 235, 235), True, pts, 2)
        # Dashed centre line
        for i in range(n):
            if (i // 6) % 2 == 0:
                pygame.draw.line(bg, (225, 225, 225), self.center[i], self.center[(i + 3) % n], 3)

    def _draw_finish_line(self, bg):
        cell = 10
        cols = (2 * ROAD_HALF_WIDTH - 14) // cell
        px, py = self.center[0]
        tx, ty = self.tangents[0]
        nx, ny = -ty, tx
        left = -cols * cell / 2
        for row in range(2):
            for col in range(cols):
                color = WHITE if (row + col) % 2 == 0 else BLACK
                a0, a1 = (row - 1) * cell, row * cell        # along the road
                b0, b1 = left + col * cell, left + (col + 1) * cell  # across it
                quad = [(px + tx * a + nx * b, py + ty * a + ny * b)
                        for a, b in ((a0, b0), (a1, b0), (a1, b1), (a0, b1))]
                pygame.draw.polygon(bg, color, quad)


_track = None


def get_track():
    """The one shared Track (built the first time it is needed)."""
    global _track
    if _track is None:
        _track = Track()
    return _track


def get_waypoints(count=NUM_WAYPOINTS, offset=0):
    """Evenly spaced points along the road, in driving order from the start line.

    `offset` shifts the line to the right (+) or left (-) of the centre,
    so different cars can use different lanes.

    Phase 3 will connect these points into a graph for BFS / A*.
    """
    track = get_track()
    n = len(track.center)
    points = []
    for k in range(count):
        i = (k * n) // count
        x, y = track.edge_point(i, offset)
        points.append((x, y))
    return points


def draw_track(screen):
    screen.blit(get_track().background, (0, 0))