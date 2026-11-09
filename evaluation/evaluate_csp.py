"""Constraint Satisfaction: schedule pit stops with backtracking and forward checking.

The problem
-----------
A race is `total_laps` long. Fuel and tyres do not last that long, so cars
have to pit. The pit lane is a shared resource, so the stops of all cars
have to be scheduled without getting in each other's way.

Time is cut into laps: a car pits at the end of lap `p`, refuels and gets
fresh tyres, and carries on. A car's state is its fuel, its tyre wear and
how much each lap uses (see CarState).

The CSP
-------
    Variables   one per pit stop that a car needs: (car name, stop number).
                How many stops a car needs follows from its fuel/tyre range.
    Domains     (lap, bay) pairs: when the stop happens and in which pit box.
                Values are tried latest lap first, so cars use their full range.
    Constraints
      fuel/tyres  stop 1 must come before the car runs dry or the tyres are
                  gone; each later stop must come within one full tank /
                  one set of tyres of the previous one; the last stop must
                  leave enough race for a full range to finish.
                  (A safety margin is always kept: PIT_SAFETY_MARGIN.)
      no overlap  two stops cannot use the same bay in the same lap.
      resources   at most PIT_MAX_STOPS_PER_LAP stops in one lap (crews),
                  and at most PIT_TYRE_SETS stops in the whole race.

Solvers (all in solve())
------------------------
    plain backtracking     assign variables one by one, undo on conflict
    + forward checking     after each assignment, remove the values it rules
                           out from the unassigned variables; backtrack at
                           once if any domain becomes empty
    + MRV                  always pick the variable with the fewest values left

verify_schedule() re-checks a schedule by simulating every car lap by lap,
independently of the constraints above.

This module does not open a window and can be run on its own:
    python ai/csp.py
"""

import math
import os
import sys
import time
from dataclasses import dataclass

if __name__ == "__main__":  # allow running this file directly from any folder
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from settings import *


# ---------------------------------------------------------------- the problem
@dataclass
class CarState:
    """What the scheduler needs to know about a car."""
    name: str
    fuel: float = FUEL_MAX        # fuel left now
    tyre_wear: float = 0.0        # 0 = new, TYRE_MAX_WEAR = destroyed
    fuel_per_lap: float = 12.0    # fuel used per lap
    wear_per_lap: float = 14.0    # tyre wear added per lap
    lap: int = 0                  # laps already completed (0 = before the start)


def _laps_left(amount_left, per_lap):
    """Whole laps that fit into `amount_left` (a tiny epsilon avoids float noise)."""
    return max(0, math.floor(amount_left / per_lap + 1e-9))


class PitStopCSP:
    """Builds the variables, domains and constraints for a list of cars."""

    def __init__(self, cars, total_laps, bays=PIT_BAYS,
                 max_per_lap=PIT_MAX_STOPS_PER_LAP, tyre_sets=PIT_TYRE_SETS):
        self.cars = list(cars)
        self.total_laps = total_laps
        self.bays = bays
        self.max_per_lap = max_per_lap
        self.tyre_sets = tyre_sets

        self.variables = []       # [(car name, stop number)]
        self.domains = {}         # variable -> [(lap, bay)]
        self.range_full = {}      # car name -> laps it can drive after a stop
        self.range_now = {}       # car name -> laps it can drive from now
        self.stops_needed = {}    # car name -> number of stops
        self.infeasible = None    # reason, if the problem can't be solved at all

        for car in self.cars:
            self._add_car(car)
        if self.infeasible is None and len(self.variables) > tyre_sets:
            self.infeasible = (f"{len(self.variables)} stops needed but only "
                               f"{tyre_sets} tyre sets are available")

    # ----------------------------------------------------------------- set-up
    def _add_car(self, car):
        reserve_fuel = FUEL_MAX * PIT_SAFETY_MARGIN
        reserve_tyre = TYRE_MAX_WEAR * PIT_SAFETY_MARGIN

        def laps_on(fuel, wear):
            return min(_laps_left(fuel - reserve_fuel, car.fuel_per_lap),
                       _laps_left(TYRE_MAX_WEAR - reserve_tyre - wear, car.wear_per_lap))

        now = laps_on(car.fuel, car.tyre_wear)
        full = laps_on(FUEL_MAX, 0.0)
        self.range_now[car.name] = now
        self.range_full[car.name] = full

        remaining = self.total_laps - car.lap
        if now >= remaining:                       # can finish without stopping
            self.stops_needed[car.name] = 0
            return
        if full < 1:
            self._fail(f"{car.name} cannot complete one lap on fresh fuel and tyres")
            return

        n = math.ceil((remaining - now) / full)    # fewest stops that are enough
        self.stops_needed[car.name] = n

        first_lap = max(1, car.lap)                # "pit now" = end of the current lap
        for k in range(1, n + 1):
            # Unary constraints: the earliest and latest lap this stop can be at
            lo = max(first_lap + k - 1, self.total_laps - (n - k + 1) * full)
            hi = min(self.total_laps - 1, car.lap + now + (k - 1) * full)
            laps = range(hi, lo - 1, -1)   # latest lap first: use the whole fuel/tyre range
            var = (car.name, k)
            self.variables.append(var)
            self.domains[var] = [(lap, bay) for lap in laps for bay in range(self.bays)]
            if not self.domains[var]:
                self._fail(f"{car.name}: no lap is possible for pit stop {k} "
                           f"(fuel/tyre range is {now} laps now, {full} after a stop)")

    def _fail(self, reason):
        if self.infeasible is None:
            self.infeasible = reason

    # ------------------------------------------------------------ constraints
    def consistent(self, a, va, b, vb):
        """Binary constraints between two different stops a=va and b=vb."""
        if a[0] == b[0]:                           # two stops of the same car
            if a[1] > b[1]:
                a, va, b, vb = b, vb, a, va
            gap = vb[0] - va[0]
            if b[1] == a[1] + 1:                   # consecutive: within one full range
                return 1 <= gap <= self.range_full[a[0]]
            return gap >= 1                        # otherwise just keep the order
        return va != vb                            # different cars: no shared (lap, bay)

    def value_ok(self, var, val, assignment):
        """Is var=val consistent with everything assigned so far?"""
        in_lap = 0
        for other, other_val in assignment.items():
            if not self.consistent(var, val, other, other_val):
                return False
            if other_val[0] == val[0]:
                in_lap += 1
        return in_lap < self.max_per_lap           # crew limit per lap


# ---------------------------------------------------------------- the solver
@dataclass
class PitStop:
    car: str
    number: int
    lap: int
    bay: int


@dataclass
class CSPResult:
    solved: bool
    stops: list              # [PitStop], sorted by lap
    nodes: int               # values tried
    backtracks: int          # assignments that had to be undone
    time_ms: float
    reason: str = ""         # why there is no schedule (if solved is False)


def solve(csp, forward_checking=True, mrv=True, node_limit=2_000_000):
    """Backtracking search, optionally with forward checking and MRV ordering."""
    start = time.perf_counter()
    stats = {"nodes": 0, "backtracks": 0}

    def finish(solved, assignment=None, reason=""):
        stops = []
        if solved:
            stops = sorted((PitStop(v[0], v[1], val[0], val[1]) for v, val in assignment.items()),
                           key=lambda s: (s.lap, s.bay))
        return CSPResult(solved, stops, stats["nodes"], stats["backtracks"],
                         (time.perf_counter() - start) * 1000, reason)

    if csp.infeasible:
        return finish(False, reason=csp.infeasible)
    if not csp.variables:
        return finish(True, {})

    assignment = {}

    def pick(domains):
        free = [v for v in csp.variables if v not in assignment]
        return min(free, key=lambda v: len(domains[v])) if mrv else free[0]

    def forward_check(var, val, domains):
        """Remove values that var=val rules out; None if a domain becomes empty."""
        lap_full = sum(1 for v in assignment.values() if v[0] == val[0]) >= csp.max_per_lap
        new = dict(domains)
        for other in csp.variables:
            if other in assignment:
                continue
            kept = [x for x in domains[other]
                    if csp.consistent(var, val, other, x) and not (lap_full and x[0] == val[0])]
            if not kept:
                return None
            new[other] = kept
        return new

    def backtrack(domains):
        if len(assignment) == len(csp.variables):
            return True
        var = pick(domains)
        for val in domains[var]:
            if stats["nodes"] >= node_limit:
                return False
            stats["nodes"] += 1
            if not csp.value_ok(var, val, assignment):
                continue
            assignment[var] = val
            if forward_checking:
                pruned = forward_check(var, val, domains)
                if pruned is not None and backtrack(pruned):
                    return True
            elif backtrack(domains):
                return True
            del assignment[var]
            stats["backtracks"] += 1
        return False

    if backtrack({v: list(d) for v, d in csp.domains.items()}):
        return finish(True, assignment)
    if stats["nodes"] >= node_limit:
        return finish(False, reason=f"gave up after {node_limit} nodes")
    return finish(False, reason="no schedule satisfies all constraints")


def schedule_pit_stops(cars, total_laps, **options):
    """Convenience wrapper: build the CSP and solve it with forward checking + MRV."""
    return solve(PitStopCSP(cars, total_laps, **options))


# ------------------------------------------------------------- verification
def verify_schedule(cars, total_laps, stops, bays=PIT_BAYS,
                    max_per_lap=PIT_MAX_STOPS_PER_LAP, tyre_sets=PIT_TYRE_SETS):
    """Check a schedule by simulating each car. Returns a list of problems (empty = valid)."""
    problems = []
    if len(stops) > tyre_sets:
        problems.append(f"{len(stops)} stops use more than {tyre_sets} tyre sets")

    seen = {}
    per_lap = {}
    for s in stops:
        if not 1 <= s.lap < total_laps:
            problems.append(f"{s.car}: stop at lap {s.lap} is outside the race")
        if not 0 <= s.bay < bays:
            problems.append(f"{s.car}: bay {s.bay} does not exist")
        if (s.lap, s.bay) in seen:
            problems.append(f"{s.car} and {seen[(s.lap, s.bay)]} both use bay {s.bay} in lap {s.lap}")
        seen[(s.lap, s.bay)] = s.car
        per_lap[s.lap] = per_lap.get(s.lap, 0) + 1
    for lap, count in per_lap.items():
        if count > max_per_lap:
            problems.append(f"lap {lap} has {count} stops (limit {max_per_lap})")

    reserve_fuel = FUEL_MAX * PIT_SAFETY_MARGIN
    max_wear = TYRE_MAX_WEAR * (1 - PIT_SAFETY_MARGIN)
    for car in cars:
        pit_laps = {s.lap for s in stops if s.car == car.name}
        fuel, wear = car.fuel, car.tyre_wear
        if car.lap in pit_laps and car.lap >= 1:   # "pit now"
            fuel, wear = FUEL_MAX, 0.0
        for lap in range(car.lap + 1, total_laps + 1):
            fuel -= car.fuel_per_lap
            wear += car.wear_per_lap
            if fuel < reserve_fuel - 1e-9:
                problems.append(f"{car.name} runs out of fuel in lap {lap}")
                break
            if wear > max_wear + 1e-9:
                problems.append(f"{car.name}'s tyres are worn out in lap {lap}")
                break
            if lap in pit_laps and lap < total_laps:
                fuel, wear = FUEL_MAX, 0.0
    return problems


# ----------------------------------------------------------------- scenarios
def make_scenario(num_cars, seed=0):
    """Random but repeatable cars: different fuel loads, tyre wear and driving styles."""
    import random
    rng = random.Random(seed)
    cars = []
    for i in range(num_cars):
        cars.append(CarState(
            name=f"Car {i + 1}",
            fuel=round(rng.uniform(55, 100), 1),
            tyre_wear=round(rng.uniform(0, 45), 1),
            fuel_per_lap=round(rng.uniform(9, 14), 1),
            wear_per_lap=round(rng.uniform(10, 17), 1),
        ))
    return cars


def format_schedule(result):
    if not result.solved:
        return f"No schedule: {result.reason}"
    if not result.stops:
        return "No pit stops needed."
    lines = ["lap  bay  car (stop)"]
    for s in result.stops:
        lines.append(f"{s.lap:>3}  {s.bay + 1:>3}  {s.car} (stop {s.number})")
    return "\n".join(lines)


if __name__ == "__main__":
    laps = PIT_DEMO_LAPS
    cars = make_scenario(6, seed=3)
    csp = PitStopCSP(cars, laps)

    print(f"{laps}-lap race, {csp.bays} pit bays, max {csp.max_per_lap} stops per lap, "
          f"{csp.tyre_sets} tyre sets\n")
    for car in cars:
        print(f"{car.name}: fuel {car.fuel:.0f}, tyre wear {car.tyre_wear:.0f} -> "
              f"{csp.range_now[car.name]} laps now, {csp.range_full[car.name]} per stop, "
              f"{csp.stops_needed[car.name]} stop(s) needed")

    for fc, mrv, label in ((False, False, "backtracking"), (True, False, "+ forward checking"),
                           (True, True, "+ forward checking + MRV")):
        r = solve(csp, forward_checking=fc, mrv=mrv)
        print(f"\n{label}: solved={r.solved}  nodes={r.nodes}  backtracks={r.backtracks}  {r.time_ms:.2f} ms")

    result = schedule_pit_stops(cars, laps)
    print("\nSchedule:\n" + format_schedule(result))
    if result.solved:
        print("\nVerification:", verify_schedule(cars, laps, result.stops) or "all constraints satisfied")