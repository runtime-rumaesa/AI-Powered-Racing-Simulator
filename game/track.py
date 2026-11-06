import math

import pygame
from settings import *


def _ellipse_rect(a, b):
    cx, cy = TRACK_CENTER
    return (cx - a, cy - b, 2 * a, 2 * b)


def draw_track(screen):
    screen.fill(GRASS_COLOR)

    outer = _ellipse_rect(OUTER_A, OUTER_B)
    inner = _ellipse_rect(INNER_A, INNER_B)

    # Road, then the inner grass on top of it
    pygame.draw.ellipse(screen, ROAD_COLOR, outer)
    pygame.draw.ellipse(screen, GRASS_COLOR, inner)

    # Boundary lines
    pygame.draw.ellipse(screen, LINE_COLOR, outer, 4)
    pygame.draw.ellipse(screen, LINE_COLOR, inner, 4)

    # Starting / finish line
    cx, cy = TRACK_CENTER
    pygame.draw.line(
        screen,
        LINE_COLOR,
        (FINISH_LINE_X, cy - OUTER_B),
        (FINISH_LINE_X, cy - INNER_B),
        5,
    )


def get_waypoints(count=NUM_WAYPOINTS, offset=0):
    """Evenly spaced points along the middle of the road.

    Returned in driving order (clockwise on screen), starting at the
    finish line. `offset` pushes the line outward (+) or inward (-), so
    different cars can use different lanes.

    Phase 3 will connect these points into a graph for BFS / A*.
    """
    cx, cy = TRACK_CENTER
    a = MID_A + offset
    b = MID_B + offset
    points = []
    for i in range(count):
        t = -math.pi / 2 + 2 * math.pi * i / count  # -90 deg = top of the track
        points.append((cx + a * math.cos(t), cy + b * math.sin(t)))
    return points