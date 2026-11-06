import pygame
from settings import *


def draw_track(screen):
    screen.fill(GRASS_COLOR)

    # Outer road boundary
    pygame.draw.ellipse(
        screen,
        ROAD_COLOR,
        (80, 60, 640, 480)
    )

    # Inner grass area
    pygame.draw.ellipse(
        screen,
        GRASS_COLOR,
        (220, 160, 360, 280)
    )

    # Outer boundary line
    pygame.draw.ellipse(
        screen,
        LINE_COLOR,
        (80, 60, 640, 480),
        4
    )

    # Inner boundary line
    pygame.draw.ellipse(
        screen,
        LINE_COLOR,
        (220, 160, 360, 280),
        4
    )

    # Starting line
    pygame.draw.line(
        screen,
        LINE_COLOR,
        (400, 60),
        (400, 160),
        5
    )