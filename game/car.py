import pygame
import math
from settings import (
    CAR_LENGTH, CAR_WIDTH, CAR_ACCELERATION, CAR_BRAKE_POWER,
    CAR_FRICTION, CAR_MAX_SPEED, CAR_MAX_REVERSE, CAR_TURN_SPEED,
    FUEL_MAX, FUEL_USE_PER_FRAME, SKID_SPEED, WHITE, RED, AI_DEFAULT_STYLE
)


class Car:
    def __init__(self, start_pos, color=RED):
        self.position = pygame.math.Vector2(start_pos)
        self.angle = 0.0  # Heading angle in degrees
        self.speed = 0.0
        self.color = color
        self.width = CAR_WIDTH
        self.length = CAR_LENGTH

        # Telemetry & State
        self.fuel = FUEL_MAX
        self.tire_health = 100.0
        self.is_drifting = False
        self.target_path = []

    @property
    def direction(self):
        """Returns normalized vector in the direction the car is facing."""
        rad = math.radians(self.angle)
        return pygame.math.Vector2(math.cos(rad), math.sin(rad))

    def update_human(self, keys):
        """Handles human keyboard controls (Arrow keys or WASD)."""
        if self.fuel <= 0:
            self._apply_friction()
            return

        # Acceleration / Braking
        if keys[pygame.K_UP] or keys[pygame.K_w]:
            self.speed = min(CAR_MAX_SPEED, self.speed + CAR_ACCELERATION)
            self.fuel = max(0.0, self.fuel - FUEL_USE_PER_FRAME)
        elif keys[pygame.K_DOWN] or keys[pygame.K_s]:
            self.speed = max(-CAR_MAX_REVERSE, self.speed - CAR_BRAKE_POWER)
        else:
            self._apply_friction()

        # Steering
        if abs(self.speed) > 0.1:
            steer = CAR_TURN_SPEED * (1.0 if self.speed > 0 else -1.0)
            if keys[pygame.K_LEFT] or keys[pygame.K_a]:
                self.angle -= steer
                if self.speed > SKID_SPEED:
                    self.is_drifting = True
            elif keys[pygame.K_RIGHT] or keys[pygame.K_d]:
                self.angle += steer
                if self.speed > SKID_SPEED:
                    self.is_drifting = True
            else:
                self.is_drifting = False
        else:
            self.is_drifting = False

        # Move position
        self.position += self.direction * self.speed

    def update_ai(self, track, strategy=None, style=AI_DEFAULT_STYLE):
        """Autonomous navigation towards track checkpoints."""
        if self.fuel <= 0:
            self._apply_friction()
            return

        # Find closest checkpoint forward target
        target = track.checkpoints[0]
        min_dist = float('inf')
        for cp in track.checkpoints:
            d = self.position.distance_to(cp)
            if d < min_dist and d > style.get("lookahead", 55):
                min_dist = d
                target = cp

        self.target_path = [target]

        # Calculate angle to target
        target_dir = (target - self.position)
        if target_dir.length() > 0:
            target_angle = math.degrees(math.atan2(target_dir.y, target_dir.x))
            angle_diff = (target_angle - self.angle + 180) % 360 - 180

            # Steering adjustment
            steering_response = style.get("steering", 1 / 15) * 45
            if abs(angle_diff) > 2:
                self.angle += math.copysign(min(abs(angle_diff), CAR_TURN_SPEED), angle_diff)

        # AI Speed Control
        target_speed = CAR_MAX_SPEED * style.get("top_speed", 0.95)
        if self.speed < target_speed:
            self.speed = min(target_speed, self.speed + CAR_ACCELERATION * style.get("acceleration", 1.0))
            self.fuel = max(0.0, self.fuel - FUEL_USE_PER_FRAME)
        else:
            self._apply_friction()

        self.position += self.direction * self.speed

    def _apply_friction(self):
        if self.speed > 0:
            self.speed = max(0.0, self.speed - CAR_FRICTION)
        elif self.speed < 0:
            self.speed = min(0.0, self.speed + CAR_FRICTION)

    def draw(self, surface):
        # Create rotated surface for the car sprite
        car_surf = pygame.Surface((self.length, self.width), pygame.SRCALPHA)
        pygame.draw.rect(car_surf, self.color, (0, 0, self.length, self.width), border_radius=4)

        # Headlights / Windshield detail
        pygame.draw.rect(car_surf, (200, 240, 255), (self.length - 12, 3, 8, self.width - 6), border_radius=2)

        rotated_surf = pygame.transform.rotate(car_surf, -self.angle)
        rect = rotated_surf.get_rect(center=(int(self.position.x), int(self.position.y)))
        surface.blit(rotated_surf, rect)

    def draw_path(self, surface):
        if self.target_path:
            for pt in self.target_path:
                pygame.draw.circle(surface, self.color, (int(pt.x), int(pt.y)), 6, 2)