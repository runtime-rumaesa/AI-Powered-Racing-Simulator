import math

from settings import *


# ------------------------------------------------------------------ track
def is_on_road(x, y):
    """True if the point is inside the outer ellipse and outside the inner one."""
    cx, cy = TRACK_CENTER
    dx, dy = x - cx, y - cy
    inside_outer = (dx / OUTER_A) ** 2 + (dy / OUTER_B) ** 2 <= 1
    inside_inner = (dx / INNER_A) ** 2 + (dy / INNER_B) ** 2 < 1
    return inside_outer and not inside_inner


def car_corners(car):
    """The four corners of the car's rectangle, after rotation."""
    rad = math.radians(car.angle)
    cos_a, sin_a = math.cos(rad), math.sin(rad)
    half_l, half_w = CAR_LENGTH / 2, CAR_WIDTH / 2
    corners = []
    for lx, ly in ((half_l, half_w), (half_l, -half_w), (-half_l, -half_w), (-half_l, half_w)):
        corners.append((car.x + lx * cos_a - ly * sin_a, car.y + lx * sin_a + ly * cos_a))
    return corners


def car_on_road(car):
    return all(is_on_road(x, y) for x, y in car_corners(car))


def resolve_wall_collision(car, last_good_state):
    """If the car left the road, put it back and bounce it off the wall.

    Returns True when a collision happened.
    """
    if car_on_road(car):
        return False
    car.set_state(last_good_state)
    car.speed *= -WALL_BOUNCE
    return True


# ------------------------------------------------------------------- cars
def resolve_car_collisions(cars):
    """Push overlapping cars apart and slow them down.

    Each car is approximated by a circle, which is simple and good enough
    for arcade racing.
    """
    min_dist = 2 * CAR_COLLISION_RADIUS
    for i in range(len(cars)):
        for j in range(i + 1, len(cars)):
            a, b = cars[i], cars[j]
            dx, dy = b.x - a.x, b.y - a.y
            dist = math.hypot(dx, dy)
            if dist >= min_dist:
                continue
            if dist == 0:
                dx, dy, dist = 1.0, 0.0, 1.0

            nx, ny = dx / dist, dy / dist
            push = (min_dist - dist) / 2
            _nudge(a, -nx * push, -ny * push)
            _nudge(b, nx * push, ny * push)

            a.speed *= CAR_COLLISION_DAMPING
            b.speed *= CAR_COLLISION_DAMPING


def _nudge(car, dx, dy):
    """Move a car, unless that would push it off the road."""
    old = (car.x, car.y)
    car.x += dx
    car.y += dy
    if not car_on_road(car):
        car.x, car.y = old