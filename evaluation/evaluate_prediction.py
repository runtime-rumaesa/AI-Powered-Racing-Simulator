"""Prediction accuracy: risk classifiers (confusion matrix) and lap-time regression (MAE, RMSE).

Run from anywhere:   python evaluation/evaluate_prediction.py

If data/race_data.csv is missing it is generated first.

Part 1 - risk (Low / Medium / High)
    always-Low baseline, Naive Bayes and the Bayesian network, compared by
    5-fold cross-validation (every lap is tested exactly once, by a model
    that never saw it), plus one 80/20 hold-out split for the confusion
    matrices and per-class precision / recall.
    Accuracy alone can mislead when one class dominates, so macro-F1 (all
    classes count equally) and log-loss (how good the probabilities are,
    lower = better) are reported too.

Part 2 - lap time
    predict-the-average baseline vs linear regression (basic and extended),
    by 5-fold cross-validation: MAE, RMSE and R2.

Results are printed, saved to data/prediction_results.json and (if
matplotlib is installed) drawn to evaluation/results/evaluate_prediction.png.
"""

import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")  # no window needed

from ai.prediction import (LEVELS, DATA_FILE, NaiveBayes, LapTimeModel, load_dataset, train_test_split,
                           k_folds, confusion_matrix, class_report, accuracy, log_loss, mae, rmse, r_squared)
from ai.bayesian import AccidentRiskModel

FOLDS = 5
SEED = 0


class MajorityBaseline:
    """Always answers with the most common class of the training laps."""

    def __init__(self, rows):
        counts = {c: sum(r["risk"] == c for r in rows) for c in LEVELS}
        self.total = len(rows)
        self.proba = {c: (counts[c] + 1) / (self.total + 3) for c in LEVELS}
        self.best = max(self.proba, key=self.proba.get)

    def predict(self, row):
        return self.best

    def predict_proba(self, row):
        return self.proba


def classifier_factories():
    return {
        "Always Low": MajorityBaseline,
        "Naive Bayes": lambda rows: NaiveBayes().fit(rows),
        "Bayesian network": lambda rows: AccidentRiskModel(rows),
    }


def score(model, test):
    actual = [r["risk"] for r in test]
    predicted = [model.predict(r) for r in test]
    probabilities = [model.predict_proba(r) for r in test]
    matrix = confusion_matrix(actual, predicted)
    return {
        "accuracy": accuracy(actual, predicted),
        "macro_f1": class_report(matrix)["macro_f1"],
        "log_loss": log_loss(actual, probabilities),
    }


def mean_std(values):
    m = sum(values) / len(values)
    return m, (sum((v - m) ** 2 for v in values) / len(values)) ** 0.5


def evaluate_risk(rows):
    results = {}
    for name, make in classifier_factories().items():
        folds = [score(make(train), test) for train, test in k_folds(rows, FOLDS, SEED)]
        results[name] = {metric: mean_std([f[metric] for f in folds]) for metric in folds[0]}

    train, test = train_test_split(rows, 0.2, SEED)
    detail = {}
    for name, make in classifier_factories().items():
        model = make(train)
        actual = [r["risk"] for r in test]
        matrix = confusion_matrix(actual, [model.predict(r) for r in test])
        detail[name] = {"matrix": matrix, "report": class_report(matrix)}
    return results, detail, len(train), len(test)


def evaluate_lap_time(rows):
    models = {
        "Predict the average": None,
        "Linear regression": False,
        "Linear regression (extended)": True,
    }
    results, points = {}, {}
    done_all = [r for r in rows if r["lap_time"] is not None]
    for name, extended in models.items():
        folds, actual_all, pred_all = [], [], []
        for train, test in k_folds(rows, FOLDS, SEED):
            test = [r for r in test if r["lap_time"] is not None]
            actual = [r["lap_time"] for r in test]
            if extended is None:
                train_times = [r["lap_time"] for r in train if r["lap_time"] is not None]
                mean = sum(train_times) / len(train_times)
                pred = [mean] * len(test)
            else:
                model = LapTimeModel(extended).fit(train)
                pred = [model.predict(r) for r in test]
            folds.append({"mae": mae(actual, pred), "rmse": rmse(actual, pred), "r2": r_squared(actual, pred)})
            actual_all += actual
            pred_all += pred
        results[name] = {m: mean_std([f[m] for f in folds]) for m in folds[0]}
        points[name] = (actual_all, pred_all)

    best = LapTimeModel(True).fit(rows)
    coefficients = best.regression.coefficients(best.names)
    return results, coefficients, points, len(done_all)


def print_table(title, results, metrics):
    print(title)
    print(f"{'':<30}" + "".join(f"{m:>18}" for m in metrics))
    for name, row in results.items():
        print(f"{name:<30}" + "".join(f"{row[m][0]:>12.3f} ±{row[m][1]:.3f}" for m in metrics))
    print()


def main():
    if not os.path.exists(DATA_FILE):
        print("No data yet - simulating laps first ...")
        from ai.generate_data import generate
        generate(2500, seed=7)
    rows = load_dataset()
    print(f"{len(rows)} simulated laps, {FOLDS}-fold cross-validation (mean ± std over folds)\n")

    risk, detail, n_train, n_test = evaluate_risk(rows)
    print_table("RISK CLASSIFICATION", risk, ["accuracy", "macro_f1", "log_loss"])

    print(f"Confusion matrices, one 80/20 split ({n_train} train / {n_test} test). Rows = real, columns = predicted")
    for name in ("Naive Bayes", "Bayesian network"):
        d = detail[name]
        print(f"\n{name}\n{'':<14}" + "".join(f"{l:>9}" for l in LEVELS) + f"{'recall':>9}")
        for label, row in zip(LEVELS, d["matrix"]):
            print(f"real {label:<9}" + "".join(f"{v:>9}" for v in row) + f"{d['report'][label]['recall']:>9.2f}")
        print(f"{'precision':<14}" + "".join(f"{d['report'][l]['precision']:>9.2f}" for l in LEVELS))
    print()

    lap, coefficients, points, n_done = evaluate_lap_time(rows)
    print_table(f"LAP TIME ({n_done} finished laps, seconds)", lap, ["mae", "rmse", "r2"])
    print("Extended model, seconds per unit:")
    for name, value in coefficients.items():
        print(f"  {name:<12}{value:>10.4f}")

    out = {
        "risk_cross_validation": {n: {m: {"mean": v[0], "std": v[1]} for m, v in r.items()} for n, r in risk.items()},
        "risk_holdout": detail,
        "lap_time_cross_validation": {n: {m: {"mean": v[0], "std": v[1]} for m, v in r.items()} for n, r in lap.items()},
        "lap_time_coefficients": coefficients,
    }
    path = os.path.join(ROOT, "data", "prediction_results.json")
    with open(path, "w") as f:
        json.dump(out, f, indent=2)
    print("\nsaved", os.path.relpath(path, ROOT))
    plot(detail, points)


def plot(detail, points):
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        print("matplotlib not installed - skipping the chart")
        return
    fig, axes = plt.subplots(1, 3, figsize=(15, 4.4))
    for ax, name in zip(axes[:2], ("Naive Bayes", "Bayesian network")):
        m = detail[name]["matrix"]
        ax.imshow(m, cmap="Blues")
        ax.set_xticks(range(3), LEVELS)
        ax.set_yticks(range(3), LEVELS)
        ax.set_xlabel("predicted")
        ax.set_ylabel("real")
        ax.set_title(f"{name}: confusion matrix")
        top = max(max(r) for r in m)
        for i in range(3):
            for j in range(3):
                ax.text(j, i, m[i][j], ha="center", va="center", color="white" if m[i][j] > top / 2 else "black")
    actual, predicted = points["Linear regression (extended)"]
    ax = axes[2]
    ax.scatter(actual, predicted, s=6, alpha=0.4)
    lo, hi = min(actual), max(actual)
    ax.plot([lo, hi], [lo, hi], "r--", label="perfect prediction")
    ax.set_xlabel("real lap time (s)")
    ax.set_ylabel("predicted lap time (s)")
    ax.set_title("Linear regression: lap time (cross-validated)")
    ax.legend()
    fig.tight_layout()
    out = os.path.join(ROOT, "evaluation", "results")
    os.makedirs(out, exist_ok=True)
    fig.savefig(os.path.join(out, "evaluate_prediction.png"), dpi=120)
    print("saved evaluation/results/evaluate_prediction.png")


if __name__ == "__main__":
    main()