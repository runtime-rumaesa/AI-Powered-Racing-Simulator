import math
import random

import pygame
from settings import *


class Effects:
    """Skid marks, tyre smoke, crash sparks and camera shake."""

    def __init__(self):
        self.skids = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        self.smoke = []   # [x, y, vx, vy, age, life, size]
        self.sparks = []  # [x, y, vx, vy, life]
        self.shake = 0.0

    # ---------------------------------------------------------------- adding
    def add_skid(self, x, y):
        pygame.draw.circle(self.skids, (12, 12, 12, 46), (int(x), int(y)), 2)

    def add_smoke(self, x, y):
        if len(self.smoke) < 160:
            self.smoke.append([x, y, random.uniform(-0.3, 0.3), random.uniform(-0.3, 0.3),
                               0, random.randint(22, 38), random.uniform(3, 5)])

    def add_sparks(self, x, y, strength=1.0):
        for _ in range(int(6 + 8 * strength)):
            angle = random.uniform(0, math.tau)
            speed = random.uniform(1.5, 4.5) * (0.6 + strength * 0.5)
            self.sparks.append([x, y, math.cos(angle) * speed, math.sin(angle) * speed,
                                random.randint(10, 22)])

    def shake_camera(self, amount):
        self.shake = max(self.shake, amount)

    def shake_offset(self):
        if self.shake < 0.3:
            return 0, 0
        return (random.uniform(-self.shake, self.shake), random.uniform(-self.shake, self.shake))

    # ---------------------------------------------------------------- update
    def update(self):
        self.shake *= 0.86

        for p in self.smoke:
            p[0] += p[2]
            p[1] += p[3]
            p[4] += 1
            p[6] += 0.18
        self.smoke = [p for p in self.smoke if p[4] < p[5]]

        for p in self.sparks:
            p[0] += p[2]
            p[1] += p[3]
            p[2] *= 0.92
            p[3] *= 0.92
            p[4] -= 1
        self.sparks = [p for p in self.sparks if p[4] > 0]

    # ---------------------------------------------------------------- drawing
    def draw_under(self, screen):
        """Skid marks and smoke: drawn below the cars."""
        screen.blit(self.skids, (0, 0))
        for x, y, _, _, age, life, size in self.smoke:
            alpha = int(110 * (1 - age / life))
            r = int(size)
            puff = pygame.Surface((r * 2, r * 2), pygame.SRCALPHA)
            pygame.draw.circle(puff, (235, 235, 235, alpha), (r, r), r)
            screen.blit(puff, (x - r, y - r))

    def draw_over(self, screen):
        """Sparks: drawn above the cars."""
        for x, y, vx, vy, life in self.sparks:
            color = (255, 235, 120) if life > 10 else (255, 140, 40)
            pygame.draw.line(screen, color, (x, y), (x - vx * 1.6, y - vy * 1.6), 2)