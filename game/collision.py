import pygame
from settings import WALL_BOUNCE

def check_wall_collisions(car, track):
    """
    Checks if a vehicle has collided with inner or outer track walls,
    bounces it back, and dampens speed.
    """
    # Check bounding bounds / wall distance relative to track geometry
    if hasattr(track, 'is_off_track') and track.is_off_track(car.position):
        # Reverse velocity component and apply wall bounce damping
        car.speed *= -WALL_BOUNCE
        car.position += car.direction * -5  # Push car back onto track boundary

    # Check outer perimeter boundary box
    if car.position.x < 10 or car.position.x > track.width - 10:
        car.speed *= -WALL_BOUNCE
        car.position.x = max(10, min(track.width - 10, car.position.x))

    if car.position.y < 10 or car.position.y > track.height - 10:
        car.speed *= -WALL_BOUNCE
        car.position.y = max(10, min(track.height - 10, car.position.y))


def resolve_car_collisions(cars):
    """
    Handles circle-to-circle collision detection and response between cars.
    """
    num_cars = len(cars)
    for i in range(num_cars):
        for j in range(i + 1, num_cars):
            car1 = cars[i]
            car2 = cars[j]

            # Simple bounding circle collision
            dist_vec = car1.position - car2.position
            distance = dist_vec.length()
            min_dist = (car1.width + car2.width) / 2.0

            if 0 < distance < min_dist:
                # Calculate overlap distance
                overlap = min_dist - distance
                normal = dist_vec.normalize()

                # Separate positions
                car1.position += normal * (overlap / 2.0)
                car2.position -= normal * (overlap / 2.0)

                # Transfer/dampen speed
                temp_speed = car1.speed
                car1.speed = car2.speed * 0.8
                car2.speed = temp_speed * 0.8