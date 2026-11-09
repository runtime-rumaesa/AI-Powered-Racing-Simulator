"""Route planning for AI cars: BFS and A* over a graph of track waypoints.

The graph
---------
The track is cut into `stations` slices across the road (the waypoints).
Each slice has several lanes, so a node is (station, lane). From a node a
car can drive on to the next station in the same lane or in a neighbouring
lane. Edges only point forward, so every route goes round the track the
right way.

    station 0     station 1     station 2
       o  <------>  o  <------>  o      lane 0 (outside)
       o            o            o      lane 1
       o            o            o      lane 2 (centre line)

The cost of an edge is the distance driven plus a small penalty for every
lane stepped (steering effort). Because every edge advances exactly one
station, *every* route to a goal has the same number of hops. So:

    BFS  minimises hops   -> all routes tie, it returns an arbitrary one
    A*   minimises cost   -> it finds the shortest route (a racing line)

This module does not open a window and can be run on its own; the
evaluation scripts call it directly.
"""

import heapq
import math
import os
import sys
import time
from collections import deque
from dataclasses import dataclass
from functools import lru_cache

if __name__ == "__main__":  # allow running this file directly from any folder
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from settings import *
from game.track import get_waypoints

STRATEGY_LABELS = {
    "astar": "A* AI",           # A* route, default driving style
    "bfs": "BFS AI",            # BFS route, default driving style
    "baseline": "Baseline AI",  # centre line, default driving style
    "hc": "Hill Climb AI",      # A* route, driving style tuned by Hill Climbing
    "ga": "Genetic AI",         # A* route, driving style tuned by the Genetic Algorithm
}


# ------------------------------------------------------------------- graph
class TrackGraph:
    """Layered waypoint graph. A node is the tuple (station, lane)."""

    def __init__(self, stations=NUM_WAYPOINTS, lane_offsets=SEARCH_LANE_OFFSETS,
                 lane_change_penalty=SEARCH_LANE_CHANGE_PENALTY):
        self.stations = stations
        self.lane_offsets = list(lane_offsets)
        self.num_lanes = len(self.lane_offsets)
        self.penalty = lane_change_penalty
        self.centre_lane = self.lane_offsets.index(0)

        # positions[lane][station] -> (x, y). Station `stations` is the start line again.
        self._positions = [get_waypoints(stations, off) for off in self.lane_offsets]
        self._lower_bound = self._build_lower_bound()

    # ------------------------------------------------------------- basics
    def position(self, node):
        station, lane = node
        return self._positions[lane][station % self.stations]

    def edge_cost(self, a, b):
        (ax, ay), (bx, by) = self.position(a), self.position(b)
        return math.hypot(bx - ax, by - ay) + self.penalty * abs(a[1] - b[1])

    def neighbors(self, node, blocked=None):
        """[(next_node, cost), ...]: the stations ahead we can reach from `node`."""
        station, lane = node
        if station >= self.stations:
            return []
        result = []
        for next_lane in (lane - 1, lane, lane + 1):
            if 0 <= next_lane < self.num_lanes:
                nxt = (station + 1, next_lane)
                if blocked and nxt in blocked:
                    continue
                result.append((nxt, self.edge_cost(node, nxt)))
        return result

    def node_count(self):
        return (self.stations + 1) * self.num_lanes

    # --------------------------------------------------------- heuristics
    def _build_lower_bound(self):
        """cum[k] = cheapest possible cost of driving from station 0 to station k
        if lane changes were free to plan (each step takes its cheapest edge)."""
        cum = [0.0]
        for k in range(self.stations):
            cheapest = min(
                self.edge_cost((k, a), (k + 1, b))
                for a in range(self.num_lanes)
                for b in (a - 1, a, a + 1)
                if 0 <= b < self.num_lanes
            )
            cum.append(cum[-1] + cheapest)
        return cum

    def heuristic(self, kind, node, goal):
        """Estimated remaining cost. Both kinds never overestimate (admissible).

        euclid: straight-line distance to the goal point.
        track:  sum of the cheapest edge at every remaining station.
        """
        if kind == "euclid":
            (x1, y1), (x2, y2) = self.position(node), self.position(goal)
            return math.hypot(x2 - x1, y2 - y1)
        if kind == "track":
            return max(0.0, self._lower_bound[goal[0]] - self._lower_bound[node[0]])
        raise ValueError(f"unknown heuristic: {kind}")

    # ------------------------------------------------------- path helpers
    def path_cost(self, path):
        return sum(self.edge_cost(a, b) for a, b in zip(path, path[1:]))

    def path_length(self, path):
        """Distance driven in pixels (no steering penalty)."""
        total = 0.0
        for a, b in zip(path, path[1:]):
            (ax, ay), (bx, by) = self.position(a), self.position(b)
            total += math.hypot(bx - ax, by - ay)
        return total

    def lane_changes(self, path):
        return sum(abs(a[1] - b[1]) for a, b in zip(path, path[1:]))

    def route_waypoints(self, path):
        """Positions for an AI controller. A closed lap drops its last point,
        which sits on top of the first one."""
        nodes = path[:-1] if path[-1][0] >= self.stations else path
        return [self.position(n) for n in nodes]


# ------------------------------------------------------------------ result
@dataclass
class SearchResult:
    algorithm: str
    path: list            # list of nodes, or None when there is no route
    cost: float           # distance + steering penalties (same formula for every algorithm)
    length: float         # pixels driven
    hops: int
    expanded: int         # nodes taken off the frontier and expanded
    generated: int        # nodes put on the frontier
    time_ms: float

    @property
    def found(self):
        return self.path is not None


def _result(name, graph, path, expanded, generated, started):
    elapsed = (time.perf_counter() - started) * 1000
    if path is None:
        return SearchResult(name, None, math.inf, math.inf, 0, expanded, generated, elapsed)
    return SearchResult(name, path, graph.path_cost(path), graph.path_length(path),
                        len(path) - 1, expanded, generated, elapsed)


def _rebuild(parent, node):
    path = [node]
    while parent[node] is not None:
        node = parent[node]
        path.append(node)
    return path[::-1]


# --------------------------------------------------------------------- BFS
def bfs(graph, start, goal, blocked=None):
    """Breadth-first search: the route with the fewest steps. Ignores distance."""
    started = time.perf_counter()
    if start == goal:
        return _result("BFS", graph, [start], 0, 1, started)

    parent = {start: None}
    frontier = deque([start])
    expanded = 0
    while frontier:
        node = frontier.popleft()
        expanded += 1
        for nxt, _ in graph.neighbors(node, blocked):
            if nxt in parent or nxt[0] > goal[0]:
                continue
            parent[nxt] = node
            if nxt == goal:
                return _result("BFS", graph, _rebuild(parent, nxt), expanded, len(parent), started)
            frontier.append(nxt)
    return _result("BFS", graph, None, expanded, len(parent), started)


# ---------------------------------------------------------------------- A*
def astar(graph, start, goal, heuristic="track", blocked=None):
    """A*: always expands the node with the lowest cost-so-far + estimated-remaining."""
    started = time.perf_counter()
    name = f"A* ({heuristic})"

    g = {start: 0.0}
    parent = {start: None}
    tie = 0  # keeps the heap from ever comparing nodes
    frontier = [(graph.heuristic(heuristic, start, goal), tie, start)]
    closed = set()
    expanded = 0
    generated = 1

    while frontier:
        _, _, node = heapq.heappop(frontier)
        if node in closed:
            continue
        if node == goal:
            return _result(name, graph, _rebuild(parent, node), expanded, generated, started)
        closed.add(node)
        expanded += 1

        for nxt, cost in graph.neighbors(node, blocked):
            if nxt[0] > goal[0]:
                continue
            new_g = g[node] + cost
            if nxt not in g or new_g < g[nxt]:
                g[nxt] = new_g
                parent[nxt] = node
                tie += 1
                generated += 1
                heapq.heappush(frontier, (new_g + graph.heuristic(heuristic, nxt, goal), tie, nxt))
    return _result(name, graph, None, expanded, generated, started)


# ------------------------------------------------------- planning for the game
def lane_for_offset(offset):
    """Index of the search lane closest to `offset` pixels from the centre line."""
    return min(range(len(SEARCH_LANE_OFFSETS)), key=lambda i: abs(SEARCH_LANE_OFFSETS[i] - offset))


@lru_cache(maxsize=None)
def _plan(algorithm, lane):
    if algorithm == "baseline":
        return tuple(get_waypoints(NUM_WAYPOINTS, SEARCH_LANE_OFFSETS[lane]))

    graph = TrackGraph()
    start = (0, lane)
    goal = (graph.stations, lane)  # finish where it started so the next lap joins up
    result = bfs(graph, start, goal) if algorithm == "bfs" else astar(graph, start, goal, "track")
    return tuple(graph.route_waypoints(result.path))


def plan_lap_route(strategy, lane_offset=0):
    """Waypoints for one full lap, planned with the chosen strategy (cached).

    strategy:    "astar", "bfs" or "baseline" (a fixed line, no search).
                 "hc" and "ga" drive the A* route; they differ only in driving style.
    lane_offset: where the car starts, in pixels left (-) or right (+) of the centre
                 line. The route starts in the nearest lane, so cars on the grid
                 don't have to cut across each other.
    """
    algorithm = "astar" if strategy in ("hc", "ga") else strategy
    return _plan(algorithm, lane_for_offset(lane_offset))


if __name__ == "__main__":
    # Quick check without opening the game
    g = TrackGraph()
    s, t = (0, g.centre_lane), (g.stations, g.centre_lane)
    for r in (bfs(g, s, t), astar(g, s, t, "euclid"), astar(g, s, t, "track")):
        print(f"{r.algorithm:15} cost={r.cost:8.1f} length={r.length:8.1f} "
              f"expanded={r.expanded:4} generated={r.generated:4} time={r.time_ms:.2f} ms")