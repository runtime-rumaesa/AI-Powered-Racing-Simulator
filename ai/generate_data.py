"""Generate the simulated race data used by the Bayesian network and the predictors.

Run from anywhere:   python ai/generate_data.py [number of laps] [seed]

Every record in data/race_data.json is one lap driven headlessly by the game's
own Car, AIController and A* route (the same simulator as the optimizer).
Before the lap, the conditions are drawn at random:

    speed       the driver's chosen top speed, in km/h on the HUD scale
    fuel        fuel left, % of a tank
    tyre_wear   0 = new, 100 = worn out
    weather     Clear, Cloudy or Rainy

and they change how the car behaves (see apply_conditions): wet weather and
worn tyres reduce grip (turning, braking, traction), a full tank makes the
car heavier. A little random steering error is added so identical
conditions do not give identical laps. What is recorded afterwards comes
out of the simulation, nothing is computed from a formula:

    collisions  how many times the car hit a wall
    lap_time    seconds for the lap (null if the lap was not finished)
    finished    true if the lap was completed, false if not (out of fuel, stuck, ...)
    risk        Low / Medium / High, from the outcome (see risk_label)

The game itself has no tyre wear or weather yet, so these two are added
here as modifiers on the car's physics.
"""

import json
import os
import random
import sys

if __name__ == "__main__":  # allow running this file directly from any folder
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

import math

from settings import *
from ai.search import plan_lap_route
from game import collision
from game.car import Car, AIController
from game.track import get_track, get_waypoints

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_FILE = os.path.join(ROOT, "data", "race_data.json")

WEATHERS = ["Clear", "Cloudy", "Rainy"]
WEATHER_WEIGHTS = [0.50, 0.25, 0.25]
WEATHER_GRIP = {"Clear": 1.00, "Cloudy": 0.92, "Rainy": 0.68}

# The game's tank is sized for a 3-lap race. A lap here costs about 8% of the
# tank (as in a ~12-lap race), so only an almost empty tank runs dry.
LAP_FUEL_SCALE = 5.0
LAP_SECONDS_LIMIT = 40
STEERING_NOISE = 0.12      # random steering error per frame (driver imperfection)

# Loss of traction: a "slide" pushes the car's heading off line for SLIDE_FRAMES
# frames. The chance per frame grows with speed and shrinks with grip.
SLIDE_RATE = 0.012
SLIDE_FRAMES = 8
SLIDE_DEGREES = 5.0          # heading change per frame while sliding (the car is pushed off line)


# ----------------------------------------------------------------- conditions
def random_conditions(rng):
    """Draw one set of racing conditions. Fuel and tyres tend to go together
    (late in a stint the tank is low and the tyres are worn), but after a pit
    stop they don't, so a part of the laps is drawn independently."""
    weather = rng.choices(WEATHERS, WEATHER_WEIGHTS)[0]
    if rng.random() < 0.7:
        stage = rng.random()
        fuel = 100 * (1 - 0.92 * stage) + rng.gauss(0, 6)
        wear = 90 * stage + rng.gauss(0, 10)
    else:
        fuel = rng.uniform(3, 100)
        wear = rng.uniform(0, 100)
    # Drivers back off a little in the rain
    top_speed = rng.uniform(0.62, 1.0) - (0.08 if weather == "Rainy" else 0.0)
    return {
        "top_speed": max(0.5, top_speed),
        "fuel": max(2.0, min(100.0, fuel)),
        "tyre_wear": max(0.0, min(100.0, wear)),
        "weather": weather,
        "corner_speed": rng.uniform(0.55, 1.00),    # how bold the driver is in corners (not recorded)
    }


def speed_kmh(top_speed):
    return top_speed * CAR_MAX_SPEED * AI_SPEED_FACTOR * HUD_SPEED_SCALE


def grip_of(weather, tyre_wear):
    return WEATHER_GRIP[weather] * (1 - 0.45 * (tyre_wear / 100) ** 1.5)


def apply_conditions(car, cond):
    """Change the car's physics according to the conditions."""
    grip = grip_of(cond["weather"], cond["tyre_wear"])
    weight = cond["fuel"] / 100
    car.turn_speed *= grip
    car.brake_power *= grip
    car.acceleration *= (0.55 + 0.45 * grip) * (1 - 0.10 * weight)
    car.max_speed *= 1 - 0.03 * weight
    car.fuel = FUEL_MAX * LAP_FUEL_SCALE * cond["fuel"] / 100


def slide_probability(speed_ratio, grip):
    """Chance per frame that the car breaks traction and slides."""
    return SLIDE_RATE * speed_ratio ** 2 * max(0.0, 1.25 - grip) ** 2


def risk_label(collisions, finished):
    """How dangerous the lap was, judged from what happened.

        High    not finished, or three or more wall hits
        Medium  one or two wall hits
        Low     no wall hits
    """
    if not finished or collisions >= 3:
        return "High"
    return "Medium" if collisions >= 1 else "Low"


# ------------------------------------------------------------------ simulator
class RaceDataSimulator:
    """Drives one lap under given conditions and records what happened."""

    def __init__(self):
        self.track = get_track()
        self.route = list(plan_lap_route("astar"))
        self.checkpoints = get_waypoints()[::CHECKPOINT_STEP]
        self.max_frames = int(LAP_SECONDS_LIMIT * FPS)

    def run(self, cond, rng):
        x, y, angle = self.track.grid_slot(0)
        car = Car(x=x, y=y, angle=angle, max_speed=CAR_MAX_SPEED * AI_SPEED_FACTOR, sprites=False)
        apply_conditions(car, cond)
        grip = grip_of(cond["weather"], cond["tyre_wear"])
        driver = AIController(self.route, {"top_speed": cond["top_speed"],
                                           "corner_speed": cond["corner_speed"]})
        next_cp, hits, touching, lap_time = 1, 0, False, None
        slide_left, slide_dir = 0, 0.0

        for frame in range(self.max_frames):
            driver.update(car)
            car.steer += rng.gauss(0, STEERING_NOISE)
            if slide_left == 0 and rng.random() < slide_probability(abs(car.speed) / car.max_speed, grip):
                slide_left, slide_dir = SLIDE_FRAMES, rng.choice((-1.0, 1.0))
            if slide_left > 0:
                car.angle += slide_dir * SLIDE_DEGREES
                slide_left -= 1
            car.steer = max(-1.0, min(1.0, car.steer))
            before = (car.x, car.y)
            last_good = car.get_state()
            car.update()

            hit = collision.resolve_wall_collision(car, last_good)
            if hit and not touching:
                hits += 1
            touching = hit
            if hits > 12:
                break

            if next_cp < len(self.checkpoints):
                cx, cy = self.checkpoints[next_cp]
                if math.hypot(car.x - cx, car.y - cy) < CHECKPOINT_RADIUS:
                    next_cp += 1
            elif self.track.crossed_finish(before, (car.x, car.y)):
                lap_time = (frame + 1) / FPS
                break

        finished = lap_time is not None
        return {
            "speed": round(speed_kmh(cond["top_speed"]), 1),
            "fuel": round(cond["fuel"], 1),
            "tyre_wear": round(cond["tyre_wear"], 1),
            "weather": cond["weather"],
            "collisions": hits,
            "lap_time": round(lap_time, 2) if finished else None,
            "finished": finished,
            "risk": risk_label(hits, finished),
        }


def generate(laps, seed=0, path=DATA_FILE, progress=True):
    rng = random.Random(seed)
    sim = RaceDataSimulator()
    rows = []
    for i in range(laps):
        rows.append(sim.run(random_conditions(rng), rng))
        if progress and (i + 1) % 100 == 0:
            print(f"  {i + 1}/{laps} laps")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        json.dump(rows, f, indent=1)
    return rows


if __name__ == "__main__":
    laps = int(sys.argv[1]) if len(sys.argv) > 1 else 2000
    seed = int(sys.argv[2]) if len(sys.argv) > 2 else 0
    print(f"Simulating {laps} laps (seed {seed}) ...")
    rows = generate(laps, seed)
    print(f"Saved {len(rows)} laps to {os.path.relpath(DATA_FILE, ROOT)}")
    for label in ("Low", "Medium", "High"):
        print(f"  {label:<6} {sum(r['risk'] == label for r in rows)}")
    print(f"  finished {sum(r['finished'] for r in rows)} of {len(rows)} laps")