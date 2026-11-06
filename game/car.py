import math

import pygame
from settings import *


class Car:
    """A car that can be driven by the player or by an AI controller.

    Movement is driven by two control values, so any controller can reuse it:
        throttle: -1 (brake / reverse) .. +1 (accelerate)
        steer:    -1 (left) .. +1 (right)

    handle_input() sets them from the keyboard; an AI controller will set
    them directly. update() then applies the physics.

    Angles are in degrees. 0 faces right and angles increase clockwise on
    screen (because the screen's y axis points down).
    """

    def __init__(
        self,
        x=CAR_START_X,
        y=CAR_START_Y,
        angle=CAR_START_ANGLE,
        color=CAR_COLOR,
        acceleration=CAR_ACCELERATION,
        max_speed=CAR_MAX_SPEED,
        turn_speed=CAR_TURN_SPEED,
    ):
        self.x = x
        self.y = y
        self.angle = angle
        self.speed = 0.0

        self.acceleration = acceleration
        self.max_speed = max_speed
        self.turn_speed = turn_speed
        self.brake_power = CAR_BRAKE_POWER
        self.friction = CAR_FRICTION
        self.max_reverse = CAR_MAX_REVERSE

        self.throttle = 0.0
        self.steer = 0.0
        self.fuel = FUEL_MAX

        self.color = color
        self._base_image = self._make_image(color)

    # ------------------------------------------------------------------ setup
    @staticmethod
    def _make_image(color):
        """Draw the car once, facing right; it is rotated when drawn."""
        image = pygame.Surface((CAR_LENGTH, CAR_WIDTH), pygame.SRCALPHA)
        pygame.draw.rect(image, color, (0, 0, CAR_LENGTH, CAR_WIDTH), border_radius=5)
        # Windscreen near the front so the direction is obvious
        windscreen = (CAR_LENGTH * 0.60, 3, CAR_LENGTH * 0.22, CAR_WIDTH - 6)
        pygame.draw.rect(image, (30, 30, 30), windscreen, border_radius=2)
        return image

    # ---------------------------------------------------------------- control
    def handle_input(self, keys):
        """Read the arrow keys (pass in pygame.key.get_pressed())."""
        self.throttle = 0.0
        self.steer = 0.0

        if keys[pygame.K_UP]:
            self.throttle += 1.0
        if keys[pygame.K_DOWN]:
            self.throttle -= 1.0
        if keys[pygame.K_LEFT]:
            self.steer -= 1.0
        if keys[pygame.K_RIGHT]:
            self.steer += 1.0

    # ------------------------------------------------------------------ state
    def get_state(self):
        """Snapshot of the position, used to undo a move that hit a wall."""
        return (self.x, self.y, self.angle)

    def set_state(self, state):
        self.x, self.y, self.angle = state

    # ---------------------------------------------------------------- physics
    def update(self):
        """Advance the car by one frame."""
        self._update_speed()
        self._update_angle()
        self._use_fuel()

        rad = math.radians(self.angle)
        self.x += math.cos(rad) * self.speed
        self.y += math.sin(rad) * self.speed

    def _update_speed(self):
        throttle = self.throttle
        if self.fuel <= 0 and throttle > 0:
            throttle = 0.0  # out of fuel: no more acceleration

        if throttle > 0:
            self.speed += self.acceleration * throttle
        elif throttle < 0:
            if self.speed > 0:
                self.speed -= self.brake_power      # braking
            else:
                self.speed += self.acceleration * throttle  # reversing
        else:
            self._apply_friction()

        self.speed = max(-self.max_reverse, min(self.max_speed, self.speed))

    def _apply_friction(self):
        if self.speed > 0:
            self.speed = max(0.0, self.speed - self.friction)
        elif self.speed < 0:
            self.speed = min(0.0, self.speed + self.friction)

    def _update_angle(self):
        # A car can't turn on the spot: turning scales with how fast it moves
        # and flips when reversing, like a real steering wheel.
        speed_factor = min(1.0, abs(self.speed) / 2.0)
        direction = 1 if self.speed >= 0 else -1
        self.angle += self.steer * self.turn_speed * speed_factor * direction
        self.angle %= 360

    def _use_fuel(self):
        self.fuel = max(0.0, self.fuel - FUEL_USE_PER_FRAME * max(self.throttle, 0.0))

    # ---------------------------------------------------------------- drawing
    def draw(self, screen):
        # pygame rotates counter-clockwise, our angle is clockwise -> negate
        rotated = pygame.transform.rotate(self._base_image, -self.angle)
        rect = rotated.get_rect(center=(self.x, self.y))
        screen.blit(rotated, rect)


class AIController:
    """Drives a Car along a list of waypoints.

    It only decides throttle and steer; the Car does the moving. In Phase 3
    the waypoint list will come from BFS / A* instead of being fixed.
    """

    def __init__(self, waypoints):
        self.waypoints = waypoints
        self.target = 0  # index of the waypoint we are driving toward

    def update(self, car):
        tx, ty = self.waypoints[self.target]
        dx, dy = tx - car.x, ty - car.y

        # Close enough: aim for the next waypoint
        if math.hypot(dx, dy) < WAYPOINT_REACH_DISTANCE:
            self.target = (self.target + 1) % len(self.waypoints)
            tx, ty = self.waypoints[self.target]
            dx, dy = tx - car.x, ty - car.y

        # Smallest signed angle from where we face to where we want to go
        desired = math.degrees(math.atan2(dy, dx))
        diff = (desired - car.angle + 180) % 360 - 180

        car.steer = max(-1.0, min(1.0, diff / 15.0))

        # Slow down in sharp turns
        turn = min(abs(diff), 60)
        target_speed = car.max_speed * (1 - 0.5 * turn / 60)
        if car.speed < target_speed:
            car.throttle = 1.0
        elif car.speed > target_speed + 0.5:
            car.throttle = -1.0
        else:
            car.throttle = 0.0