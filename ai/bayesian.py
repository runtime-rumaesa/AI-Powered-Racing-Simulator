"""Bayesian network: how likely is an accident, given what we know about the car?

The network
-----------
Five discrete variables. An arrow means "directly influences":

    Weather ---------> Speed          drivers back off in the rain
       |                  |
       |   Fuel --------> TyreWear    late in a stint: low fuel, worn tyres
       |    |                |
       v    v                v
    +------------- Risk <-----+      risk of an accident (Low / Medium / High)
         (Risk has four parents: Weather, Fuel, TyreWear, Speed)

The arrows are chosen from how the simulator works; the numbers are learned.
Every node has a conditional probability table (CPT), P(node | its parents),
and the CPTs are counted from the laps in data/race_data.csv (with Laplace
smoothing, so no combination is ever impossible).

Inference
---------
query(target, evidence) answers questions like

    P(Risk | Weather=Rainy, TyreWear=High)

by enumeration: it adds up the joint probability of every way the unknown
variables could be, then normalises. Unlike Naive Bayes, the network can
(1) answer with *partial* evidence (unknown variables are summed out) and
(2) learn interactions, because Risk has its own row for every combination
of its parents (rain AND worn tyres is not just rain plus worn tyres).

This module does not open a window and can be run on its own:
    python ai/bayesian.py
"""

import itertools
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if __name__ == "__main__":  # allow running this file directly from any folder
    sys.path.insert(0, ROOT)

from ai.prediction import LEVELS, WEATHERS, level, load_dataset, train_test_split, accuracy


class BayesianNetwork:
    """A small discrete Bayesian network with CPTs learned by counting."""

    def __init__(self):
        self.states = {}     # node -> list of states
        self.parents = {}    # node -> tuple of parent names
        self.order = []      # nodes, parents always before children
        self.cpt = {}        # node -> {parent states tuple -> {state: probability}}

    def add_node(self, name, states, parents=()):
        for p in parents:
            if p not in self.states:
                raise ValueError(f"add parent {p!r} before {name!r}")
        self.states[name] = list(states)
        self.parents[name] = tuple(parents)
        self.order.append(name)

    # --------------------------------------------------------------- learning
    def fit(self, samples, alpha=1.0):
        """samples: list of {node: state}. Estimate every CPT by counting."""
        for node in self.order:
            counts = {}
            for config in itertools.product(*(self.states[p] for p in self.parents[node])):
                counts[config] = {s: alpha for s in self.states[node]}
            for sample in samples:
                config = tuple(sample[p] for p in self.parents[node])
                counts[config][sample[node]] += 1
            self.cpt[node] = {
                config: {s: c / sum(row.values()) for s, c in row.items()}
                for config, row in counts.items()
            }
        return self

    # -------------------------------------------------------------- inference
    def probability(self, node, state, assignment):
        config = tuple(assignment[p] for p in self.parents[node])
        return self.cpt[node][config][state]

    def joint(self, assignment):
        """P(every variable takes the value in `assignment`)."""
        p = 1.0
        for node in self.order:
            p *= self.probability(node, assignment[node], assignment)
        return p

    def query(self, target, evidence):
        """P(target | evidence) as {state: probability}, by enumeration."""
        free = [n for n in self.order if n not in evidence and n != target]
        totals = {s: 0.0 for s in self.states[target]}
        for state in self.states[target]:
            for values in itertools.product(*(self.states[n] for n in free)):
                assignment = dict(evidence)
                assignment.update(zip(free, values))
                assignment[target] = state
                totals[state] += self.joint(assignment)
        z = sum(totals.values())
        return {s: v / z for s, v in totals.items()}


# ------------------------------------------------------------ the risk model
def build_network():
    net = BayesianNetwork()
    net.add_node("Weather", WEATHERS)
    net.add_node("Fuel", LEVELS)
    net.add_node("Speed", LEVELS, parents=("Weather",))
    net.add_node("TyreWear", LEVELS, parents=("Fuel",))
    net.add_node("Risk", LEVELS, parents=("Weather", "Fuel", "TyreWear", "Speed"))
    return net


def to_sample(row):
    """A data row as discrete states, one per network node."""
    return {
        "Weather": row["weather"],
        "Fuel": level("fuel", row["fuel"]),
        "TyreWear": level("tyre_wear", row["tyre_wear"]),
        "Speed": level("speed", row["speed"]),
        "Risk": row["risk"],
    }


def evidence_of(row, known=("Weather", "Fuel", "TyreWear", "Speed")):
    sample = to_sample(row)
    return {k: sample[k] for k in known}


class AccidentRiskModel:
    """The Bayesian network trained on race data, with a simple interface."""

    def __init__(self, rows=None, alpha=1.0):
        rows = rows if rows is not None else load_dataset()
        self.net = build_network().fit([to_sample(r) for r in rows], alpha)

    def risk(self, speed=None, fuel=None, tyre_wear=None, weather=None):
        """P(Risk | whatever is known). Leave out (None) what you don't know.

        Returns ({'Low': p, 'Medium': p, 'High': p}, most likely class).
        """
        evidence = {}
        if weather is not None:
            evidence["Weather"] = weather
        if fuel is not None:
            evidence["Fuel"] = level("fuel", fuel)
        if tyre_wear is not None:
            evidence["TyreWear"] = level("tyre_wear", tyre_wear)
        if speed is not None:
            evidence["Speed"] = level("speed", speed)
        proba = self.net.query("Risk", evidence)
        return proba, max(proba, key=proba.get)

    def predict_proba(self, row, known=("Weather", "Fuel", "TyreWear", "Speed")):
        return self.net.query("Risk", evidence_of(row, known))

    def predict(self, row, known=("Weather", "Fuel", "TyreWear", "Speed")):
        proba = self.predict_proba(row, known)
        return max(proba, key=proba.get)

    def riskiest_conditions(self, count=5):
        """The combinations of (Weather, Fuel, TyreWear, Speed) with the highest P(High)."""
        table = self.net.cpt["Risk"]
        parents = self.net.parents["Risk"]
        ranked = sorted(table.items(), key=lambda item: item[1]["High"], reverse=True)[:count]
        return [(dict(zip(parents, config)), probs["High"]) for config, probs in ranked]


if __name__ == "__main__":
    rows = load_dataset()
    train, test = train_test_split(rows)
    model = AccidentRiskModel(train)

    print("Learned from", len(train), "laps\n")
    def show(label, **known):
        proba, best = model.risk(**known)
        print(f"{label:<44} Low {proba['Low']:.0%}  Medium {proba['Medium']:.0%}  "
              f"High {proba['High']:.0%}  -> {best}")

    show("Nothing known")
    show("It is raining", weather="Rainy")
    show("Clear weather", weather="Clear")
    show("Rainy + worn tyres (wear 80)", weather="Rainy", tyre_wear=80)
    show("Clear + new tyres (wear 5)", weather="Clear", tyre_wear=5)
    show("Rainy + worn tyres + fast (150 km/h)", weather="Rainy", tyre_wear=80, speed=150)
    show("Rainy + worn tyres + slow (90 km/h)", weather="Rainy", tyre_wear=80, speed=90)

    print("\nMost dangerous combinations (highest P(High)):")
    for config, p in model.riskiest_conditions():
        print(f"  {p:.0%}  {config}")

    actual = [r["risk"] for r in test]
    print(f"\nAccuracy on {len(test)} unseen laps (all four conditions known): "
          f"{accuracy(actual, [model.predict(r) for r in test]):.1%}")
    print(f"Accuracy with only weather + tyre wear known:           "
          f"{accuracy(actual, [model.predict(r, ('Weather', 'TyreWear')) for r in test]):.1%}")