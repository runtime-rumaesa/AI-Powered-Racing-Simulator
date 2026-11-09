"""Optimization: tune an AI driver's racing strategy with Hill Climbing and a Genetic Algorithm.

What is being optimized
-----------------------
A racing strategy is the AI driver's style, seven numbers (see GENES). The
car, the track and the route (planned by A*) stay the same; only the style
changes. As a chromosome it is just a list of seven floats in GENE_NAMES order.

    top_speed      how fast it aims to go on straights      (maximum speed)
    acceleration   how hard it presses the throttle         (acceleration)
    braking        how hard it presses the brake            (braking intensity)
    brake_margin   how much too fast it tolerates           (braking intensity)
    corner_speed   how fast it keeps going in sharp corners (turning speed)
    steering       how sharply it reacts to heading error
    lookahead      how far ahead it aims

How a strategy is judged
------------------------
LapSimulator drives one lap from a standing start with no window. The
fitness is the lap time in seconds plus penalties (lower is better):

    fitness = lap time + OPT_WALL_PENALTY * wall hits

A lap that is not finished gets the time limit plus OPT_DNF_PENALTY and a
bit more for every checkpoint missed. The simulation has no randomness, so
the same strategy always gets the same fitness.

Both algorithms get the same budget: a fixed number of lap simulations.
This module does not open a window; the evaluation script calls it directly.
"""

import json
import math
import os
import random
import sys
import time
from dataclasses import dataclass, field

if __name__ == "__main__":  # allow running this file directly from any folder
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

from settings import *
from ai.search import plan_lap_route
from game import collision
from game.car import Car, AIController
from game.track import get_track, get_waypoints

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STRATEGY_FILE = os.path.join(ROOT, "data", "optimized_strategies.json")

# gene name -> (lowest allowed, highest allowed)
GENES = {
    "top_speed": (0.60, 1.00),
    "acceleration": (0.40, 1.00),
    "braking": (0.20, 1.00),
    "brake_margin": (0.0, 2.0),
    "corner_speed": (0.25, 1.00),
    "steering": (0.03, 0.30),
    "lookahead": (30.0, 90.0),
}
GENE_NAMES = list(GENES)


# ---------------------------------------------------------------- chromosome
def to_chromosome(style):
    return [style[name] for name in GENE_NAMES]


def to_style(chromosome):
    return {name: value for name, value in zip(GENE_NAMES, chromosome)}


def clamp(chromosome):
    return [max(GENES[n][0], min(GENES[n][1], v)) for n, v in zip(GENE_NAMES, chromosome)]


def random_chromosome(rng):
    return [rng.uniform(*GENES[name]) for name in GENE_NAMES]


def baseline_chromosome():
    """The hand-tuned style the AI used before any optimization."""
    return to_chromosome(AI_DEFAULT_STYLE)


# ------------------------------------------------------------------ simulator
@dataclass
class LapResult:
    fitness: float
    lap_time: float       # seconds (the time limit when not finished)
    wall_hits: int
    finished: bool
    checkpoints: int      # checkpoints reached


class LapSimulator:
    """Drives one lap of the track with a given style and scores it."""

    def __init__(self, route=None, max_seconds=OPT_TIME_LIMIT):
        self.track = get_track()
        self.route = list(route) if route else list(plan_lap_route("astar"))
        self.checkpoints = get_waypoints()[::CHECKPOINT_STEP]
        self.max_frames = int(max_seconds * FPS)
        self.max_seconds = max_seconds

    def run(self, style):
        x, y, angle = self.track.grid_slot(0)
        car = Car(x=x, y=y, angle=angle, max_speed=CAR_MAX_SPEED * AI_SPEED_FACTOR, sprites=False)
        driver = AIController(self.route, style)

        next_cp = 1
        wall_hits = 0
        touching = False
        lap_time = None

        for frame in range(self.max_frames):
            driver.update(car)
            before = (car.x, car.y)
            last_good = car.get_state()
            car.update()

            hit = collision.resolve_wall_collision(car, last_good)
            if hit and not touching:
                wall_hits += 1
            touching = hit
            if wall_hits > 12:        # hopeless: stop wasting time
                break

            if next_cp < len(self.checkpoints):
                cx, cy = self.checkpoints[next_cp]
                if math.hypot(car.x - cx, car.y - cy) < CHECKPOINT_RADIUS:
                    next_cp += 1
            elif self.track.crossed_finish(before, (car.x, car.y)):
                lap_time = (frame + 1) / FPS
                break

        if lap_time is not None:
            fitness = lap_time + OPT_WALL_PENALTY * wall_hits
            return LapResult(fitness, lap_time, wall_hits, True, next_cp)

        missed = len(self.checkpoints) - next_cp
        fitness = self.max_seconds + OPT_DNF_PENALTY + 2.0 * missed + OPT_WALL_PENALTY * wall_hits
        return LapResult(fitness, self.max_seconds, wall_hits, False, next_cp)


class Evaluator:
    """Scores chromosomes for an optimizer and keeps track of the budget.

    Only real simulations use up the budget; a chromosome that was already
    scored is answered from memory. `history` holds the best fitness found
    after every simulation (used for the convergence graph).
    """

    def __init__(self, simulator, budget):
        self.simulator = simulator
        self.budget = budget
        self.count = 0
        self.cache = {}
        self.best_fitness = math.inf
        self.best = None
        self.history = []

    @property
    def exhausted(self):
        return self.count >= self.budget

    def __call__(self, chromosome):
        key = tuple(round(v, 5) for v in chromosome)
        if key in self.cache:
            return self.cache[key]
        fitness = self.simulator.run(to_style(chromosome)).fitness
        self.cache[key] = fitness
        self.count += 1
        if fitness < self.best_fitness:
            self.best_fitness = fitness
            self.best = list(chromosome)
        self.history.append(self.best_fitness)
        return fitness


@dataclass
class OptimizationResult:
    algorithm: str
    best_chromosome: list
    best_fitness: float
    evaluations: int
    history: list = field(repr=False)
    seconds: float = 0.0
    detail: str = ""          # e.g. "7 restarts" or "27 generations"

    @property
    def best_style(self):
        return to_style(self.best_chromosome)


# ------------------------------------------------------------- hill climbing
def hill_climbing(simulator, budget=OPT_EVALUATIONS, seed=0, patience=40, step=0.15):
    """Stochastic hill climbing with random restarts.

    1. Start from a strategy (the first run starts from the baseline, later
       runs from random strategies).
    2. Change a few genes by a small random amount.
    3. Drive the lap. If the result is no worse, keep the new strategy,
       otherwise throw it away.
    4. Make the changes smaller the longer it fails to improve. After
       `patience` failures in a row it is stuck on a hill top, so restart
       from a new random strategy.
    """
    rng = random.Random(seed)
    evaluate = Evaluator(simulator, budget)
    started = time.perf_counter()
    restarts = 0
    attempts_left = budget * 20  # safety net against endless re-tries of cached strategies

    while not evaluate.exhausted and attempts_left > 0:
        restarts += 1
        current = baseline_chromosome() if restarts == 1 else random_chromosome(rng)
        current_fitness = evaluate(current)
        sigma = step
        failures = 0

        while not evaluate.exhausted and failures < patience and attempts_left > 0:
            attempts_left -= 1
            candidate = list(current)
            for i in rng.sample(range(len(GENE_NAMES)), rng.randint(1, 3)):
                low, high = GENES[GENE_NAMES[i]]
                candidate[i] += rng.gauss(0, sigma * (high - low))
            candidate = clamp(candidate)

            fitness = evaluate(candidate)
            if fitness <= current_fitness:
                if fitness < current_fitness:
                    failures = 0
                else:
                    failures += 1
                current, current_fitness = candidate, fitness
            else:
                failures += 1
                if failures % 15 == 0:
                    sigma *= 0.6  # search closer to the current strategy

    return OptimizationResult("Hill Climbing", evaluate.best, evaluate.best_fitness, evaluate.count,
                              evaluate.history, time.perf_counter() - started, f"{restarts} restarts")


# --------------------------------------------------------- genetic algorithm
def genetic_algorithm(simulator, budget=OPT_EVALUATIONS, seed=0, population_size=24, elite=2,
                      tournament_size=3, crossover_rate=0.9, mutation_rate=0.2, mutation_sigma=0.10):
    """Genetic algorithm.

    1. Initial population: the baseline plus random strategies.
    2. Fitness: drive the lap (lap time + penalties).
    3. Selection: tournament, the best of a few random picks becomes a parent.
    4. Crossover: blend two parents gene by gene.
    5. Mutation: nudge some genes by a small random amount.
    6. Elitism: the best strategies go into the next generation unchanged.
    Repeat until the budget of lap simulations is used up.
    """
    rng = random.Random(seed)
    evaluate = Evaluator(simulator, budget)
    started = time.perf_counter()

    def tournament(scored):
        return min(rng.sample(scored, tournament_size), key=lambda item: item[0])[1]

    def crossover(a, b):
        # blend crossover: each gene lands between the parents, a little beyond is allowed
        return [x + (y - x) * rng.uniform(-0.25, 1.25) for x, y in zip(a, b)]

    def mutate(chromosome):
        out = list(chromosome)
        for i, name in enumerate(GENE_NAMES):
            if rng.random() < mutation_rate:
                low, high = GENES[name]
                out[i] += rng.gauss(0, mutation_sigma * (high - low))
        return out

    population = [baseline_chromosome()] + [random_chromosome(rng) for _ in range(population_size - 1)]
    scored = []
    for chromosome in population:
        if evaluate.exhausted:
            break
        scored.append((evaluate(chromosome), chromosome))

    generations = 0
    attempts_left = budget * 20
    while not evaluate.exhausted and attempts_left > 0:
        generations += 1
        scored.sort(key=lambda item: item[0])
        next_gen = scored[:elite]  # elites keep their fitness, no re-simulation needed

        while len(next_gen) < population_size and not evaluate.exhausted and attempts_left > 0:
            attempts_left -= 1
            a, b = tournament(scored), tournament(scored)
            child = crossover(a, b) if rng.random() < crossover_rate else list(a)
            child = clamp(mutate(child))
            next_gen.append((evaluate(child), child))
        scored = next_gen

    return OptimizationResult("Genetic Algorithm", evaluate.best, evaluate.best_fitness, evaluate.count,
                              evaluate.history, time.perf_counter() - started, f"{generations} generations")


# ----------------------------------------------------------- saving / loading
def save_strategies(strategies, path=STRATEGY_FILE):
    """strategies: {"hill_climbing": {"style": {...}, ...}, "genetic": {...}, ...}"""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        json.dump(strategies, f, indent=2)


_warned = set()


def load_best_style(strategy):
    """Optimized style for the "hc" / "ga" race strategies; None for any other."""
    key = {"hc": "hill_climbing", "ga": "genetic"}.get(strategy)
    if key is None:
        return None
    try:
        with open(STRATEGY_FILE) as f:
            return json.load(f)[key]["style"]
    except (OSError, KeyError, ValueError):
        if strategy not in _warned:
            _warned.add(strategy)
            print(f"[{strategy}] {os.path.basename(STRATEGY_FILE)} not found - using the default style. "
                  f"Run evaluation/evaluate_optimization.py to create it.")
        return None


if __name__ == "__main__":
    # Quick check without opening the game
    sim = LapSimulator()
    base = sim.run(AI_DEFAULT_STYLE)
    print(f"Baseline        lap {base.lap_time:6.2f}s  hits {base.wall_hits}  fitness {base.fitness:6.2f}")
    for algorithm in (hill_climbing, genetic_algorithm):
        r = algorithm(sim, budget=150, seed=1)
        final = sim.run(r.best_style)
        print(f"{r.algorithm:15} lap {final.lap_time:6.2f}s  hits {final.wall_hits}  fitness {final.fitness:6.2f}"
              f"  ({r.evaluations} laps simulated in {r.seconds:.1f}s, {r.detail})")