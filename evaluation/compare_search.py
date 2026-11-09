"""BFS vs A*: path cost, nodes expanded and execution time.

Run from anywhere:   python evaluation/compare_search.py

Every algorithm gets exactly the same graph, start, goal and blocked nodes.
Results are printed, saved to data/search_results.json and (if matplotlib is
installed) drawn to evaluation/results/compare_search.png.
"""

import json
import os
import random
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")  # no window needed

from ai.search import TrackGraph, bfs, astar

TIMING_RUNS = 200      # each search is repeated this many times for a stable time
OBSTACLE_RATE = 0.20   # share of nodes blocked in the "obstacles" test
SEED = 42


def make_obstacles(graph, start, goal, rate, seed):
    """Random blocked nodes (think slow cars or oil), never the start or goal."""
    rng = random.Random(seed)
    blocked = set()
    for station in range(1, graph.stations):
        for lane in range(graph.num_lanes):
            if rng.random() < rate:
                blocked.add((station, lane))
    # keep at least one lane open at every station so a route can exist
    for station in range(1, graph.stations):
        if all((station, lane) in blocked for lane in range(graph.num_lanes)):
            blocked.discard((station, graph.centre_lane))
    blocked.discard(start)
    blocked.discard(goal)
    return blocked


def timed(search, *args, **kwargs):
    """Run a search several times; keep the result and the average time."""
    total = 0.0
    result = None
    for _ in range(TIMING_RUNS):
        result = search(*args, **kwargs)
        total += result.time_ms
    result.time_ms = total / TIMING_RUNS
    return result


def main():
    graph = TrackGraph()
    c = graph.centre_lane
    n = graph.stations
    start = (0, c)

    cases = [
        ("Quarter lap", (n // 4, c), None),
        ("Half lap", (n // 2, c), None),
        ("Three-quarter lap", (3 * n // 4, c), None),
        ("Full lap", (n, c), None),
        ("Full lap + obstacles", (n, c), make_obstacles(graph, start, (n, c), OBSTACLE_RATE, SEED)),
    ]

    rows = []
    for case, goal, blocked in cases:
        results = [
            timed(bfs, graph, start, goal, blocked),
            timed(astar, graph, start, goal, "euclid", blocked),
            timed(astar, graph, start, goal, "track", blocked),
        ]
        for r in results:
            rows.append({
                "case": case,
                "algorithm": r.algorithm,
                "found": r.found,
                "path_cost": round(r.cost, 1) if r.found else "",
                "length_px": round(r.length, 1) if r.found else "",
                "hops": r.hops,
                "lane_changes": graph.lane_changes(r.path) if r.found else "",
                "expanded": r.expanded,
                "generated": r.generated,
                "time_ms": round(r.time_ms, 3),
            })

    print_table(rows)
    save_json(rows)
    save_chart(rows)


def print_table(rows):
    header = f"{'Case':<22}{'Algorithm':<14}{'Found':<7}{'Cost':>9}{'Length':>9}{'Hops':>6}{'Lanes':>7}{'Expanded':>10}{'Generated':>11}{'ms':>8}"
    print(header)
    print("-" * len(header))
    last = None
    for r in rows:
        if last and r["case"] != last:
            print()
        last = r["case"]
        print(f"{r['case']:<22}{r['algorithm']:<14}{str(r['found']):<7}{r['path_cost']:>9}{r['length_px']:>9}"
              f"{r['hops']:>6}{r['lane_changes']:>7}{r['expanded']:>10}{r['generated']:>11}{r['time_ms']:>8}")


def save_json(rows):
    path = os.path.join(ROOT, "data", "search_results.json")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        json.dump(rows, f, indent=2)
    print(f"\nSaved {os.path.relpath(path, ROOT)}")


def save_chart(rows):
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        print("matplotlib not installed - skipping the chart (pip install matplotlib)")
        return

    cases = list(dict.fromkeys(r["case"] for r in rows))
    algorithms = list(dict.fromkeys(r["algorithm"] for r in rows))
    metrics = [("path_cost", "Path cost (lower is better)"),
               ("expanded", "Nodes expanded (lower is better)"),
               ("time_ms", "Time in ms (lower is better)")]
    colors = ["#e0524d", "#f2a53a", "#3b82f6"]

    fig, axes = plt.subplots(1, 3, figsize=(16, 4.6))
    width = 0.26
    for ax, (key, title) in zip(axes, metrics):
        for i, algo in enumerate(algorithms):
            values = [next(r[key] for r in rows if r["case"] == c and r["algorithm"] == algo) for c in cases]
            ax.bar([x + (i - 1) * width for x in range(len(cases))], values, width, label=algo, color=colors[i])
        ax.set_title(title)
        ax.set_xticks(range(len(cases)))
        ax.set_xticklabels([c.replace(" + ", "\n+ ").replace(" lap", "\nlap") for c in cases], fontsize=8)
        ax.grid(axis="y", alpha=0.3)
    axes[0].legend()
    fig.tight_layout()

    path = os.path.join(ROOT, "evaluation", "results", "compare_search.png")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    fig.savefig(path, dpi=130)
    print(f"Saved {os.path.relpath(path, ROOT)}")


if __name__ == "__main__":
    main()