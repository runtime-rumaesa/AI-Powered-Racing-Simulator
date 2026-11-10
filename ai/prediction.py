"""Machine learning on the simulated races: classify risk and predict lap time.

Data
----
data/race_data.json, made by ai/generate_data.py. One row is one simulated
lap: speed, fuel, tyre wear and weather go in; collisions, lap time and the
risk label come out of the simulation.

Two models, both written from scratch (no ML library) so every step can be
explained:

Naive Bayes classifier   conditions -> risk (Low / Medium / High)
    Speed, fuel and tyre wear are cut into Low / Medium / High levels
    (see CUTS). For a lap with conditions x it picks the risk class with the
    largest

        P(class) * P(speed level | class) * P(fuel level | class)
                 * P(wear level | class)  * P(weather | class)

    "Naive" because it treats the conditions as independent given the class.
    Probabilities are counted from the training laps with Laplace smoothing
    (add 1 to every count) so nothing is ever impossible.

Linear regression        conditions -> lap time in seconds
    lap_time = w0 + w1*speed + w2*fuel + w3*wear + w4*rainy + w5*cloudy
    The weights are found in closed form (the normal equations, with a tiny
    ridge term). `extended=True` adds three features that capture the shape of
    the relationship better (1/speed, wear squared, rain x wear). Only
    finished laps are used: a lap that was not finished has no lap time.

This module does not open a window and can be run on its own:
    python ai/prediction.py
"""

import json
import math
import os
import random
import sys
from collections import Counter, defaultdict

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if __name__ == "__main__":  # allow running this file directly from any folder
    sys.path.insert(0, ROOT)

DATA_FILE = os.path.join(ROOT, "data", "race_data.json")

LEVELS = ["Low", "Medium", "High"]
WEATHERS = ["Clear", "Cloudy", "Rainy"]

# Where Low / Medium / High start for each numeric condition
CUTS = {
    "speed": (110, 135),       # km/h on the HUD scale
    "fuel": (30, 65),          # % of a tank
    "tyre_wear": (30, 65),     # 0 new .. 100 worn out
}


# ----------------------------------------------------------------------- data
def level(feature, value):
    """Cut a number into 'Low', 'Medium' or 'High'."""
    low, high = CUTS[feature]
    return LEVELS[0] if value < low else LEVELS[1] if value < high else LEVELS[2]


def load_dataset(path=DATA_FILE):
    """Read race_data.json into a list of dicts with proper types."""
    if not os.path.exists(path):
        raise FileNotFoundError(f"{path} not found - run: python ai/generate_data.py")
    with open(path) as f:
        records = json.load(f)
    return [{
        "speed": float(r["speed"]),
        "fuel": float(r["fuel"]),
        "tyre_wear": float(r["tyre_wear"]),
        "weather": r["weather"],
        "collisions": int(r["collisions"]),
        "lap_time": float(r["lap_time"]) if r["lap_time"] is not None else None,
        "finished": bool(r["finished"]),
        "risk": r["risk"],
    } for r in records]


def train_test_split(rows, test_fraction=0.2, seed=0):
    """Random split that keeps the share of each risk class in both parts."""
    rng = random.Random(seed)
    by_class = defaultdict(list)
    for r in rows:
        by_class[r["risk"]].append(r)
    train, test = [], []
    for group in by_class.values():
        rng.shuffle(group)
        cut = round(len(group) * test_fraction)
        test += group[:cut]
        train += group[cut:]
    rng.shuffle(train)
    rng.shuffle(test)
    return train, test


def k_folds(rows, k=5, seed=0):
    """Yield (train, test) for k-fold cross-validation, classes kept balanced."""
    rng = random.Random(seed)
    by_class = defaultdict(list)
    for r in rows:
        by_class[r["risk"]].append(r)
    folds = [[] for _ in range(k)]
    for group in by_class.values():
        rng.shuffle(group)
        for i, r in enumerate(group):
            folds[i % k].append(r)
    for i in range(k):
        train = [r for j, fold in enumerate(folds) if j != i for r in fold]
        yield train, folds[i]


# ---------------------------------------------------------------- Naive Bayes
class NaiveBayes:
    """Categorical Naive Bayes: conditions -> risk class."""

    FEATURES = ("speed", "fuel", "tyre_wear", "weather")

    def __init__(self, alpha=1.0):
        self.alpha = alpha
        self.classes = list(LEVELS)
        self.class_counts = Counter()
        self.value_counts = {c: [Counter() for _ in self.FEATURES] for c in self.classes}
        self.values = [LEVELS, LEVELS, LEVELS, WEATHERS]
        self.total = 0

    @staticmethod
    def features_of(row):
        return [level("speed", row["speed"]), level("fuel", row["fuel"]),
                level("tyre_wear", row["tyre_wear"]), row["weather"]]

    def fit(self, rows):
        for row in rows:
            c = row["risk"]
            self.class_counts[c] += 1
            self.total += 1
            for i, v in enumerate(self.features_of(row)):
                self.value_counts[c][i][v] += 1
        return self

    def log_scores(self, row):
        """log P(class) + sum of log P(feature value | class), for every class."""
        x = self.features_of(row)
        scores = {}
        for c in self.classes:
            n = self.class_counts[c]
            score = math.log((n + self.alpha) / (self.total + self.alpha * len(self.classes)))
            for i, v in enumerate(x):
                p = (self.value_counts[c][i][v] + self.alpha) / (n + self.alpha * len(self.values[i]))
                score += math.log(p)
            scores[c] = score
        return scores

    def predict_proba(self, row):
        scores = self.log_scores(row)
        top = max(scores.values())
        exp = {c: math.exp(s - top) for c, s in scores.items()}
        z = sum(exp.values())
        return {c: v / z for c, v in exp.items()}

    def predict(self, row):
        proba = self.predict_proba(row)
        return max(proba, key=proba.get)


# ---------------------------------------------------------- linear regression
def _solve(a, b):
    """Solve a x = b by Gaussian elimination with partial pivoting."""
    n = len(b)
    m = [row[:] + [b[i]] for i, row in enumerate(a)]
    for col in range(n):
        pivot = max(range(col, n), key=lambda r: abs(m[r][col]))
        m[col], m[pivot] = m[pivot], m[col]
        for r in range(col + 1, n):
            f = m[r][col] / m[col][col]
            for k in range(col, n + 1):
                m[r][k] -= f * m[col][k]
    x = [0.0] * n
    for i in range(n - 1, -1, -1):
        x[i] = (m[i][n] - sum(m[i][k] * x[k] for k in range(i + 1, n))) / m[i][i]
    return x


def lap_time_features(row, extended=False):
    rainy = 1.0 if row["weather"] == "Rainy" else 0.0
    cloudy = 1.0 if row["weather"] == "Cloudy" else 0.0
    x = [row["speed"], row["fuel"], row["tyre_wear"], rainy, cloudy]
    if extended:
        x += [1000.0 / row["speed"], (row["tyre_wear"] / 100) ** 2, rainy * row["tyre_wear"] / 100]
    return x


class LinearRegression:
    """Ordinary least squares with a tiny ridge term, solved in closed form."""

    def __init__(self, ridge=1e-6):
        self.ridge = ridge
        self.weights = None

    def fit(self, X, y):
        n, d = len(X), len(X[0])
        self.mean = [sum(r[j] for r in X) / n for j in range(d)]
        self.std = [(sum((r[j] - self.mean[j]) ** 2 for r in X) / n) ** 0.5 or 1.0 for j in range(d)]
        Z = [[1.0] + [(r[j] - self.mean[j]) / self.std[j] for j in range(d)] for r in X]
        # normal equations: (Z'Z + ridge I) w = Z'y
        a = [[sum(z[i] * z[j] for z in Z) + (self.ridge if i == j and i > 0 else 0.0)
              for j in range(d + 1)] for i in range(d + 1)]
        b = [sum(z[i] * t for z, t in zip(Z, y)) for i in range(d + 1)]
        self.weights = _solve(a, b)
        return self

    def predict(self, x):
        z = [1.0] + [(x[j] - self.mean[j]) / self.std[j] for j in range(len(x))]
        return sum(w * v for w, v in zip(self.weights, z))

    def coefficients(self, names):
        """Weights in the original units (seconds per unit of each feature)."""
        w = self.weights
        coef = {n: w[j + 1] / self.std[j] for j, n in enumerate(names)}
        coef["intercept"] = w[0] - sum(w[j + 1] * self.mean[j] / self.std[j] for j in range(len(names)))
        return coef


class LapTimeModel:
    """Linear regression on laps that were finished: conditions -> seconds."""

    NAMES = ["speed", "fuel", "tyre_wear", "rainy", "cloudy"]
    EXTRA = ["1000/speed", "wear^2", "rain*wear"]

    def __init__(self, extended=False):
        self.extended = extended
        self.regression = LinearRegression()

    @property
    def names(self):
        return self.NAMES + (self.EXTRA if self.extended else [])

    def fit(self, rows):
        done = [r for r in rows if r["lap_time"] is not None]
        self.regression.fit([lap_time_features(r, self.extended) for r in done],
                            [r["lap_time"] for r in done])
        return self

    def predict(self, row):
        return self.regression.predict(lap_time_features(row, self.extended))


# -------------------------------------------------------------------- metrics
def confusion_matrix(actual, predicted, labels=LEVELS):
    """matrix[i][j] = laps whose real class is labels[i] and predicted class labels[j]."""
    index = {l: i for i, l in enumerate(labels)}
    m = [[0] * len(labels) for _ in labels]
    for a, p in zip(actual, predicted):
        m[index[a]][index[p]] += 1
    return m


def accuracy(actual, predicted):
    return sum(a == p for a, p in zip(actual, predicted)) / len(actual)


def class_report(matrix, labels=LEVELS):
    """Precision, recall and F1 for every class, plus the macro-average F1."""
    report = {}
    for i, label in enumerate(labels):
        tp = matrix[i][i]
        fp = sum(matrix[r][i] for r in range(len(labels))) - tp
        fn = sum(matrix[i]) - tp
        precision = tp / (tp + fp) if tp + fp else 0.0
        recall = tp / (tp + fn) if tp + fn else 0.0
        f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
        report[label] = {"precision": precision, "recall": recall, "f1": f1, "support": sum(matrix[i])}
    report["macro_f1"] = sum(report[l]["f1"] for l in labels) / len(labels)
    return report


def log_loss(actual, probabilities):
    """Average -log of the probability given to the true class (lower is better)."""
    return -sum(math.log(max(p[a], 1e-12)) for a, p in zip(actual, probabilities)) / len(actual)


def mae(actual, predicted):
    return sum(abs(a - p) for a, p in zip(actual, predicted)) / len(actual)


def rmse(actual, predicted):
    return (sum((a - p) ** 2 for a, p in zip(actual, predicted)) / len(actual)) ** 0.5


def r_squared(actual, predicted):
    mean = sum(actual) / len(actual)
    total = sum((a - mean) ** 2 for a in actual)
    return 1 - sum((a - p) ** 2 for a, p in zip(actual, predicted)) / total if total else 0.0


# ------------------------------------------------------------ ready-made use
class RacePredictor:
    """Both models trained on the data file, with an easy interface for the game."""

    def __init__(self, rows=None, extended=True):
        rows = rows if rows is not None else load_dataset()
        self.risk_model = NaiveBayes().fit(rows)
        self.time_model = LapTimeModel(extended).fit(rows)

    @staticmethod
    def conditions(speed, fuel, tyre_wear, weather):
        return {"speed": speed, "fuel": fuel, "tyre_wear": tyre_wear, "weather": weather}

    def risk(self, speed, fuel, tyre_wear, weather):
        """({'Low': p, 'Medium': p, 'High': p}, most likely class)"""
        proba = self.risk_model.predict_proba(self.conditions(speed, fuel, tyre_wear, weather))
        return proba, max(proba, key=proba.get)

    def lap_time(self, speed, fuel, tyre_wear, weather):
        return self.time_model.predict(self.conditions(speed, fuel, tyre_wear, weather))


if __name__ == "__main__":
    rows = load_dataset()
    train, test = train_test_split(rows)
    print(f"{len(rows)} laps: {len(train)} to train on, {len(test)} to test on")
    print("risk classes:", dict(Counter(r["risk"] for r in rows)), "\n")

    nb = NaiveBayes().fit(train)
    actual = [r["risk"] for r in test]
    predicted = [nb.predict(r) for r in test]
    print(f"Naive Bayes accuracy on unseen laps: {accuracy(actual, predicted):.1%}")
    for label, row in zip(LEVELS, confusion_matrix(actual, predicted)):
        print(f"  real {label:<7}", row)

    for extended in (False, True):
        lt = LapTimeModel(extended).fit(train)
        done = [r for r in test if r["lap_time"] is not None]
        pred = [lt.predict(r) for r in done]
        real = [r["lap_time"] for r in done]
        print(f"\nLap time ({'extended' if extended else 'basic'} regression): "
              f"MAE {mae(real, pred):.2f}s  RMSE {rmse(real, pred):.2f}s  R2 {r_squared(real, pred):.3f}")

    predictor = RacePredictor(train)
    print("\nExamples:")
    for cond in [(80, 90, 10, "Clear"), (120, 30, 75, "Rainy"), (100, 65, 40, "Clear")]:
        proba, label = predictor.risk(*cond)
        print(f"  speed {cond[0]}, fuel {cond[1]}, wear {cond[2]}, {cond[3]:<6} -> risk {label:<6} "
              f"(Low {proba['Low']:.0%} / Med {proba['Medium']:.0%} / High {proba['High']:.0%}), "
              f"lap time {predictor.lap_time(*cond):.1f}s")