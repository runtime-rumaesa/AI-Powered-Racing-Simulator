"""Racing conditions: weather, tyre wear and the weight of the fuel.

How they change a car is exactly what ai/generate_data.py does to its
simulated laps, so the Bayesian network and the predictors (which learned
from that data) describe this game: when the HUD says "Rainy, tyres 80%
worn" the models know what that means.

    grip   = weather grip * (1 - 0.45 * (tyre wear / max wear) ** 1.5)

    turning and braking are multiplied by grip,
    acceleration by (0.55 + 0.45 * grip),
    and a full tank makes the car heavier: acceleration -10 %, top speed -3 %.

The Car class itself does not know about conditions. Every frame the race calls
apply_conditions() for each car, then adds tyre_wear_this_frame() to its wear.
"""

import random

import pygame

from settings import *


def grip_of(weather, tyre_wear):
    """Traction from 0 to 1: 1 = dry road and new tyres."""
    return WEATHER_GRIP[weather] * (1 - 0.45 * (tyre_wear / TYRE_MAX_WEAR) ** 1.5)


class CarSetup:
    """A car's own values, before the conditions change them. Take it right after the Car is created."""

    def __init__(self, car):
        self.turn_speed = car.turn_speed
        self.brake_power = car.brake_power
        self.acceleration = car.acceleration
        self.max_speed = car.max_speed


def apply_conditions(car, setup, weather, tyre_wear):
    """Set the car's turning, braking, acceleration and top speed for this frame. Returns the grip."""
    grip = grip_of(weather, tyre_wear)
    weight = car.fuel / FUEL_MAX
    car.turn_speed = setup.turn_speed * grip
    car.brake_power = setup.brake_power * grip
    car.acceleration = setup.acceleration * (0.55 + 0.45 * grip) * (1 - 0.10 * weight)
    car.max_speed = setup.max_speed * (1 - 0.03 * weight)
    return grip


def tyre_wear_this_frame(car):
    """Tyres wear with the distance driven, and faster the harder the car steers."""
    return TYRE_WEAR_RATE * (abs(car.speed) / CAR_MAX_SPEED) * (1 + TYRE_WEAR_CORNERING * abs(car.steer))


def tyre_life(wear):
    """Tyre life left in percent (100 = new)."""
    return max(0.0, 100.0 * (1 - wear / TYRE_MAX_WEAR))


class WeatherEffects:
    """Looks only: a grey tint for Cloudy, a darker tint and falling rain for Rainy. Draw it over the cars."""

    def __init__(self, weather, seed=11):
        rng = random.Random(seed)
        self.weather = weather
        tint = {"Cloudy": (70, 80, 100, 38), "Rainy": (24, 34, 62, 92)}.get(weather)
        self.tint = None
        if tint:
            self.tint = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
            self.tint.fill(tint)
        count = 170 if weather == "Rainy" else 0
        self.drops = [[rng.uniform(0, WIDTH), rng.uniform(0, HEIGHT), rng.uniform(15, 24)] for _ in range(count)]

    def update(self):
        for drop in self.drops:
            drop[1] += drop[2]
            drop[0] -= drop[2] * 0.22
            if drop[1] > HEIGHT:
                drop[1] -= HEIGHT + 30
            if drop[0] < -10:
                drop[0] += WIDTH + 20

    def draw(self, screen):
        if self.tint is not None:
            screen.blit(self.tint, (0, 0))
        for x, y, speed in self.drops:
            pygame.draw.line(screen, (170, 190, 225), (x, y), (x - speed * 0.22, y + speed * 0.9), 1)