"""Baseline vs Hill Climbing vs Genetic Algorithm.

Run from anywhere:   python evaluation/evaluate_optimization.py

Fair test: every algorithm drives the same track and route in the same
simulator and gets the same budget of lap simulations. Each one is run with
several random seeds, because both are random searches.

Writes:  data/optimization_results.json      one entry per run
         data/optimized_strategies.json      best strategy per algorithm (the game loads this)
         evaluation/results/evaluate_optimization.png
"""

import json
import os
import statistics
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")  # no window needed

from settings import *
from ai.optimization import (GENES, GENE_NAMES, LapSimulator, hill_climbing, genetic_algorithm,
                             save_strategies)

SEEDS = list(range(1, 11))
BUDGET = OPT_EVALUATIONS


def main():
    sim = LapSimulator()
    baseline = sim.run(AI_DEFAULT_STYLE)

    runs = []   # (algorithm name, seed, OptimizationResult, LapResult of its best strategy)
    for algorithm in (hill_climbing, genetic_algorithm):
        for seed in SEEDS:
            result = algorithm(sim, budget=BUDGET, seed=seed)
            runs.append((result.algorithm, seed, result, sim.run(result.best_style)))
            print(f"  {result.algorithm:<18} seed {seed:>2}: lap {runs[-1][3].lap_time:5.2f}s "
                  f"({result.evaluations} laps, {result.detail})")

    print()
    summarise(baseline, runs)
    save_json(baseline, runs)
    best = save_best(baseline, runs)
    save_chart(baseline, runs, best)


def group(runs, name):
    return [r for r in runs if r[0] == name]


def laps_to_reach(result, target):
    """How many lap simulations until the best fitness found was within `target`."""
    for i, fitness in enumerate(result.history, start=1):
        if fitness <= target:
            return i
    return None


def convergence_target(runs):
    """1% worse than the best fitness any run found."""
    return 1.01 * min(r[3].fitness for r in runs)


def summarise(baseline, runs):
    print(f"Budget: {BUDGET} lap simulations per run, {len(SEEDS)} runs per algorithm\n")
    target = convergence_target(runs)
    header = f"{'Strategy':<20}{'Lap time (s)':>14}{'Best lap':>10}{'Worst lap':>11}{'Wall hits':>11}{'Fitness':>10}{'vs baseline':>13}{'Laps to 1%':>12}"
    print(header)
    print("-" * len(header))
    print(f"{'Baseline':<20}{baseline.lap_time:>14.2f}{baseline.lap_time:>10.2f}{baseline.lap_time:>11.2f}"
          f"{baseline.wall_hits:>11}{baseline.fitness:>10.2f}{'-':>13}{'-':>12}")
    for name in dict.fromkeys(r[0] for r in runs):
        rows = group(runs, name)
        laps = [r[3].lap_time for r in rows]
        fits = [r[3].fitness for r in rows]
        hits = statistics.mean(r[3].wall_hits for r in rows)
        reached = [laps_to_reach(r[2], target) for r in rows]
        reached = [x for x in reached if x is not None]
        speed = f"{statistics.mean(reached):.0f}" if reached else "never"
        gain = 100 * (baseline.fitness - statistics.mean(fits)) / baseline.fitness
        print(f"{name:<20}{statistics.mean(laps):>14.2f}{min(laps):>10.2f}{max(laps):>11.2f}"
              f"{hits:>11.1f}{statistics.mean(fits):>10.2f}{gain:>12.1f}%{speed:>12}")
    print("\nLap time, fitness and wall hits are averages over the runs (lower is better).")
    print(f"'Laps to 1%' = average number of lap simulations until a run found a strategy within 1% of the "
          f"best fitness seen ({target:.2f}).")


def save_json(baseline, runs):
    path = os.path.join(ROOT, "data", "optimization_results.json")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    target = convergence_target(runs)

    entries = [{
        "algorithm": "Baseline", "seed": None, "lap_time": baseline.lap_time,
        "wall_hits": baseline.wall_hits, "fitness": round(baseline.fitness, 3),
        "evaluations": 1, "laps_to_1pct": None, "seconds": 0,
        "strategy": dict(AI_DEFAULT_STYLE),
    }]
    for name, seed, result, lap in runs:
        entries.append({
            "algorithm": name, "seed": seed, "lap_time": lap.lap_time, "wall_hits": lap.wall_hits,
            "fitness": round(lap.fitness, 3), "evaluations": result.evaluations,
            "laps_to_1pct": laps_to_reach(result, target), "seconds": round(result.seconds, 2),
            "strategy": {g: round(result.best_style[g], 4) for g in GENE_NAMES},
        })
    with open(path, "w") as f:
        json.dump(entries, f, indent=2)
    print(f"\nSaved {os.path.relpath(path, ROOT)}")


def save_best(baseline, runs):
    """Keep the best run of each algorithm; the game's "hc" and "ga" AIs load these."""
    keys = {"Hill Climbing": "hill_climbing", "Genetic Algorithm": "genetic"}
    best = {"baseline": {"style": dict(AI_DEFAULT_STYLE), "lap_time": baseline.lap_time,
                         "wall_hits": baseline.wall_hits, "fitness": baseline.fitness}}
    for name, key in keys.items():
        seed, result, lap = min(((s, r, l) for n, s, r, l in group(runs, name)), key=lambda t: t[2].fitness)
        best[key] = {"style": {g: round(v, 4) for g, v in result.best_style.items()}, "seed": seed,
                     "lap_time": lap.lap_time, "wall_hits": lap.wall_hits, "fitness": lap.fitness}
    save_strategies(best)
    print("Saved data/optimized_strategies.json")

    print("\nBest strategies found:")
    print(f"{'Gene':<14}{'Baseline':>10}{'Hill Climbing':>15}{'Genetic':>10}")
    for g in GENE_NAMES:
        print(f"{g:<14}{AI_DEFAULT_STYLE[g]:>10.3f}{best['hill_climbing']['style'][g]:>15.3f}{best['genetic']['style'][g]:>10.3f}")
    return best


def save_chart(baseline, runs, best):
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        print("matplotlib not installed - skipping the chart (pip install matplotlib)")
        return

    colors = {"Hill Climbing": "#f2a53a", "Genetic Algorithm": "#3b82f6", "Baseline": "#e0524d"}
    fig, axes = plt.subplots(1, 3, figsize=(17, 4.8))

    # 1. Convergence: best fitness found so far
    ax = axes[0]
    for name in ("Hill Climbing", "Genetic Algorithm"):
        curves = []
        for _, _, result, _ in group(runs, name):
            h = result.history + [result.history[-1]] * (BUDGET - len(result.history))
            curves.append(h[:BUDGET])
        xs = range(1, BUDGET + 1)
        mean = [statistics.mean(c[i] for c in curves) for i in range(BUDGET)]
        low = [min(c[i] for c in curves) for i in range(BUDGET)]
        high = [max(c[i] for c in curves) for i in range(BUDGET)]
        ax.plot(xs, mean, label=name, color=colors[name], linewidth=2)
        ax.fill_between(xs, low, high, color=colors[name], alpha=0.15)
    ax.axhline(baseline.fitness, color=colors["Baseline"], linestyle="--", label="Baseline")
    ax.set_title("Convergence (mean, min-max band)")
    ax.set_xlabel("Lap simulations used (log scale)")
    ax.set_ylabel("Best fitness so far (s, lower is better)")
    ax.set_ylim(min(r[3].fitness for r in runs) - 0.1, baseline.fitness + 0.3)
    ax.set_xscale("log")
    ax.legend()
    ax.grid(alpha=0.3)

    # 2. Final lap time of every run
    ax = axes[1]
    labels = ["Baseline", "Hill Climbing", "Genetic Algorithm"]
    means = [baseline.lap_time] + [statistics.mean(r[3].lap_time for r in group(runs, n)) for n in labels[1:]]
    errs = [0] + [statistics.pstdev(r[3].lap_time for r in group(runs, n)) for n in labels[1:]]
    ax.bar(labels, means, yerr=errs, capsize=6, color=[colors[l] for l in labels])
    for i, n in enumerate(labels[1:], start=1):
        ax.scatter([i] * len(SEEDS), [r[3].lap_time for r in group(runs, n)], color="black", s=14, zorder=3)
    for i, v in enumerate(means):
        ax.text(i, v + 0.05, f"{v:.2f}s", ha="center", fontsize=9)
    ax.set_title("Lap time of the best strategy (dots = each run)")
    ax.set_ylabel("Seconds (lower is better)")
    ax.set_ylim(min(means) - 1.0, max(means) + 0.5)
    ax.grid(axis="y", alpha=0.3)

    # 3. What was learned: genes scaled to 0..1 of their allowed range
    ax = axes[2]
    width = 0.27
    sets = [("Baseline", AI_DEFAULT_STYLE), ("Hill Climbing", best["hill_climbing"]["style"]),
            ("Genetic Algorithm", best["genetic"]["style"])]
    for i, (name, style) in enumerate(sets):
        vals = [(style[g] - GENES[g][0]) / (GENES[g][1] - GENES[g][0]) for g in GENE_NAMES]
        ax.bar([x + (i - 1) * width for x in range(len(GENE_NAMES))], vals, width, label=name, color=colors[name])
    ax.set_xticks(range(len(GENE_NAMES)))
    ax.set_xticklabels(GENE_NAMES, rotation=30, ha="right", fontsize=8)
    ax.set_title("Strategy parameters (0 = lowest allowed, 1 = highest)")
    ax.legend(fontsize=8)
    ax.grid(axis="y", alpha=0.3)

    fig.tight_layout()
    path = os.path.join(ROOT, "evaluation", "results", "evaluate_optimization.png")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    fig.savefig(path, dpi=130)
    print(f"Saved {os.path.relpath(path, ROOT)}")


if __name__ == "__main__":
    main()