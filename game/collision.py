import math

from settings import *
from game.track import get_track


# ------------------------------------------------------------------ track
def is_on_road(x, y):
    """True if the point is on the road (curbs count as road)."""
    return get_track().is_on_road(x, y)


def car_points(car):
    """Corners and side midpoints of the car's rectangle, after rotation."""
    rad = math.radians(car.angle)
    cos_a, sin_a = math.cos(rad), math.sin(rad)
    half_l, half_w = CAR_LENGTH / 2, CAR_WIDTH / 2
    local = ((half_l, half_w), (half_l, -half_w), (-half_l, -half_w), (-half_l, half_w),
             (0, half_w), (0, -half_w))
    return [(car.x + lx * cos_a - ly * sin_a, car.y + lx * sin_a + ly * cos_a) for lx, ly in local]


def car_on_road(car):
    return all(is_on_road(x, y) for x, y in car_points(car))


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
    for arcade racing. Returns a list of (x, y, car_a, car_b) for each bump.
    """
    bumps = []
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

            bumps.append(((a.x + b.x) / 2, (a.y + b.y) / 2, a, b))

            nx, ny = dx / dist, dy / dist
            push = (min_dist - dist) / 2
            _nudge(a, -nx * push, -ny * push)
            _nudge(b, nx * push, ny * push)

            a.speed *= CAR_COLLISION_DAMPING
            b.speed *= CAR_COLLISION_DAMPING
    return bumps


def _nudge(car, dx, dy):
    """Move a car, unless that would push it off the road."""
    old = (car.x, car.y)
    car.x += dx
    car.y += dy
    if not car_on_road(car):
        car.x, car.y = old