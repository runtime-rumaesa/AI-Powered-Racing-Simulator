import math

import pygame
from settings import *


def _shade(color, factor):
    """Lighter (>1) or darker (<1) version of a colour."""
    return tuple(max(0, min(255, int(c * factor))) for c in color)


class Car:
    """A car that can be driven by the player or by an AI controller.

    Movement is driven by two control values, so any controller can reuse it:
        throttle: -1 (brake / reverse) .. +1 (accelerate)
        steer:    -1 (left) .. +1 (right)

    handle_input() sets them from the keyboard; an AI controller sets
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
        self._base_image, self._shadow_image = self._make_images(color)

    # ------------------------------------------------------------------ setup
    @staticmethod
    def _make_images(color):
        """Paint a top-down sports car once (facing right) plus its shadow.

        It is drawn 4x too big and scaled down, which gives smooth edges.
        """
        S = 4
        L, W = CAR_LENGTH * S, CAR_WIDTH * S
        big = pygame.Surface((L, W), pygame.SRCALPHA)
        dark = _shade(color, 0.55)
        light = _shade(color, 1.30)
        draw = pygame.draw

        def rect(fx, fy, fw, fh, col, radius=0, width=0):
            draw.rect(big, col, (fx * L, fy * W, fw * L, fh * W), width, border_radius=radius)

        # Wheels (peek out from under the body)
        for fx in (0.13, 0.66):
            for fy in (0.0, 0.80):
                rect(fx, fy, 0.19, 0.20, (18, 18, 20), radius=10)
                rect(fx + 0.05, fy + 0.05, 0.09, 0.10, (85, 85, 92), radius=6)

        # Body: rounded rear block + tapered nose
        rect(0.06, 0.17, 0.60, 0.66, color, radius=34)
        nose = [(0.50 * L, 0.17 * W), (0.80 * L, 0.21 * W), (0.985 * L, 0.38 * W),
                (0.985 * L, 0.62 * W), (0.80 * L, 0.79 * W), (0.50 * L, 0.83 * W)]
        draw.polygon(big, color, nose)
        draw.polygon(big, dark, nose, 4)
        rect(0.06, 0.17, 0.60, 0.66, dark, radius=34, width=4)
        draw.polygon(big, color, nose)  # hide the seam between block and nose

        # Highlights and racing stripes
        draw.line(big, light, (0.12 * L, 0.27 * W), (0.36 * L, 0.27 * W), 6)
        draw.line(big, light, (0.72 * L, 0.30 * W), (0.93 * L, 0.40 * W), 6)
        rect(0.08, 0.44, 0.30, 0.12, (245, 245, 245))
        rect(0.68, 0.44, 0.29, 0.12, (245, 245, 245))

        # Cockpit, windscreen reflection and driver's helmet
        draw.ellipse(big, (22, 30, 48), (0.37 * L, 0.26 * W, 0.31 * L, 0.48 * W))
        draw.ellipse(big, (80, 110, 150), (0.55 * L, 0.31 * W, 0.10 * L, 0.14 * W))
        draw.circle(big, (240, 240, 240), (int(0.50 * L), int(0.50 * W)), int(0.11 * W))
        draw.circle(big, color, (int(0.50 * L), int(0.50 * W)), int(0.06 * W))

        # Wings
        rect(0.0, 0.10, 0.08, 0.80, dark, radius=4)           # rear spoiler
        rect(0.0, 0.06, 0.11, 0.06, dark)                      # end plates
        rect(0.0, 0.88, 0.11, 0.06, dark)
        rect(0.945, 0.12, 0.055, 0.76, dark, radius=4)         # front wing

        # Lights
        draw.ellipse(big, (255, 245, 170), (0.88 * L, 0.24 * W, 0.06 * L, 0.13 * W))
        draw.ellipse(big, (255, 245, 170), (0.88 * L, 0.63 * W, 0.06 * L, 0.13 * W))
        rect(0.085, 0.22, 0.03, 0.12, (255, 40, 40))
        rect(0.085, 0.66, 0.03, 0.12, (255, 40, 40))

        image = pygame.transform.smoothscale(big, (CAR_LENGTH, CAR_WIDTH))
        shadow = pygame.mask.from_surface(image).to_surface(
            setcolor=(0, 0, 0, 95), unsetcolor=(0, 0, 0, 0))
        return image, shadow

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

    @property
    def braking(self):
        return self.throttle < 0 and self.speed > 2.0

    @property
    def skidding(self):
        """Braking hard, or turning hard at speed."""
        return self.braking or (abs(self.steer) > 0.5 and self.speed > SKID_SPEED)

    def rear_wheels(self):
        """World positions of the two rear tyres."""
        rad = math.radians(self.angle)
        fx, fy = math.cos(rad), math.sin(rad)
        rx, ry = -fy, fx  # points to the car's right
        bx = self.x - fx * CAR_LENGTH * 0.28
        by = self.y - fy * CAR_LENGTH * 0.28
        off = CAR_WIDTH * 0.36
        return (bx - rx * off, by - ry * off), (bx + rx * off, by + ry * off)

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
        shadow = pygame.transform.rotozoom(self._shadow_image, -self.angle, 1)
        screen.blit(shadow, shadow.get_rect(center=(self.x + 4, self.y + 5)))

        rotated = pygame.transform.rotozoom(self._base_image, -self.angle, 1)
        screen.blit(rotated, rotated.get_rect(center=(self.x, self.y)))

        if self.throttle < 0 and self.speed > 0.3:  # brake lights
            rad = math.radians(self.angle)
            fx, fy = math.cos(rad), math.sin(rad)
            rx, ry = -fy, fx
            bx = self.x - fx * CAR_LENGTH * 0.40
            by = self.y - fy * CAR_LENGTH * 0.40
            for side in (-1, 1):
                px = bx + rx * side * CAR_WIDTH * 0.22
                py = by + ry * side * CAR_WIDTH * 0.22
                pygame.draw.circle(screen, (170, 20, 20), (int(px), int(py)), 6)
                pygame.draw.circle(screen, (255, 100, 80), (int(px), int(py)), 3)


class AIController:
    """Drives a Car along a list of waypoints.

    It only decides throttle and steer; the Car does the moving. In Phase 3
    the waypoint list will come from BFS / A* instead of being fixed.
    """

    def __init__(self, waypoints):
        self.waypoints = waypoints
        self.target = 0  # index of the waypoint we are driving toward
        self.stuck = 0
        self.reverse_frames = 0

        # How sharp is the road just ahead of each waypoint? (0 straight .. 1 sharp)
        n = len(waypoints)
        headings = []
        for i in range(n):
            ax, ay = waypoints[i]
            bx, by = waypoints[(i + 1) % n]
            headings.append(math.degrees(math.atan2(by - ay, bx - ax)))
        self.severity = []
        for i in range(n):
            worst = 0.0
            for j in range(1, 5):
                diff = abs((headings[(i + j) % n] - headings[i] + 180) % 360 - 180)
                worst = max(worst, diff)
            self.severity.append(min(1.0, worst / 80.0))

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
        steer = max(-1.0, min(1.0, diff / 15.0))

        # Wedged against a wall? Back up for a moment.
        if self.reverse_frames > 0:
            self.reverse_frames -= 1
            car.throttle, car.steer = -1.0, -steer
            return
        self.stuck = self.stuck + 1 if abs(car.speed) < 0.4 else 0
        if self.stuck > 40:
            self.stuck = 0
            self.reverse_frames = 35

        # Slow down for sharp corners ahead and for big steering errors
        turn = min(abs(diff), 60) / 60
        corner = self.severity[self.target]
        target_speed = car.max_speed * (1 - 0.55 * max(turn, corner))
        car.steer = steer
        if car.speed < target_speed:
            car.throttle = 1.0
        elif car.speed > target_speed + 0.5:
            car.throttle = -1.0
        else:
            car.throttle = 0.0