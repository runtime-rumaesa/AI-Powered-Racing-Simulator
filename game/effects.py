import pygame
import random

class SkidMark:
    def __init__(self, position):
        self.position = pygame.math.Vector2(position)
        self.alpha = 150  # Initial opacity
        self.lifetime = 180  # Frames before disappearing

    def update(self):
        self.alpha -= 1
        self.lifetime -= 1

    def draw(self, surface):
        if self.lifetime > 0 and self.alpha > 0:
            mark_surf = pygame.Surface((4, 4), pygame.SRCALPHA)
            mark_surf.fill((40, 40, 40, max(0, self.alpha)))
            surface.blit(mark_surf, self.position)


class Particle:
    def __init__(self, x, y, color):
        self.position = pygame.math.Vector2(x, y)
        self.velocity = pygame.math.Vector2(random.uniform(-1, 1), random.uniform(-1, 1))
        self.color = color
        self.radius = random.randint(2, 4)
        self.lifetime = 20

    def update(self):
        self.position += self.velocity
        self.radius = max(0, self.radius - 0.1)
        self.lifetime -= 1

    def draw(self, surface):
        if self.lifetime > 0 and self.radius > 0:
            pygame.draw.circle(surface, self.color, (int(self.position.x), int(self.position.y)), int(self.radius))


class EffectsManager:
    def __init__(self):
        self.skid_marks = []
        self.particles = []
        self.shake_intensity = 0

    def add_skid_mark(self, position):
        self.skid_marks.append(SkidMark(position))

    def add_smoke(self, x, y):
        self.particles.append(Particle(x, y, (200, 200, 200)))

    def trigger_shake(self, intensity=5):
        self.shake_intensity = intensity

    def shake_offset(self):
        if self.shake_intensity > 0:
            offset_x = random.randint(-self.shake_intensity, self.shake_intensity)
            offset_y = random.randint(-self.shake_intensity, self.shake_intensity)
            return (offset_x, offset_y)
        return (0, 0)

    def update(self):
        # Update skid marks
        for mark in self.skid_marks[:]:
            mark.update()
            if mark.lifetime <= 0:
                self.skid_marks.remove(mark)

        # Update particles
        for p in self.particles[:]:
            p.update()
            if p.lifetime <= 0:
                self.particles.remove(p)

        # Decay screen shake
        if self.shake_intensity > 0:
            self.shake_intensity -= 1

    def draw(self, surface):
        for mark in self.skid_marks:
            mark.draw(surface)
        for p in self.particles:
            p.draw(surface)