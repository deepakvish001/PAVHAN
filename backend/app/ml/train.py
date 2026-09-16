"""Train the pricing model.

    python -m app.ml.train

Writes app/ml/price_model.joblib together with the metrics it achieved, so the
served model can report its own accuracy instead of asking to be trusted.
"""

from __future__ import annotations

import json
import time
from pathlib import Path

import numpy as np
from sklearn.ensemble import GradientBoostingRegressor
from sklearn.inspection import permutation_importance
from sklearn.metrics import mean_absolute_error, r2_score
from sklearn.model_selection import train_test_split

from .dataset import FEATURES, build

MODEL_PATH = Path(__file__).resolve().parent / "price_model.joblib"


def train(rows: int = 24000, seed: int = 26090) -> dict:
    import joblib

    started = time.perf_counter()
    X, y, features = build(rows=rows, seed=seed)

    # Learn log-price: craft prices span three orders of magnitude, and in log
    # space the model optimises proportional error, which is what "10% off"
    # means to an artisan. A flat rupee error would let the model ignore
    # everything under a few thousand rupees.
    y_log = np.log1p(y)

    X_train, X_test, y_train, y_test = train_test_split(
        X, y_log, test_size=0.2, random_state=seed)

    model = GradientBoostingRegressor(
        n_estimators=400, learning_rate=0.06, max_depth=4,
        subsample=0.85, min_samples_leaf=12, random_state=seed,
    )
    model.fit(X_train, y_train)

    pred_log = model.predict(X_test)
    pred = np.expm1(pred_log)
    truth = np.expm1(y_test)

    metrics = {
        "rows": rows,
        "r2_log": round(float(r2_score(y_test, pred_log)), 4),
        "mae_rupees": round(float(mean_absolute_error(truth, pred)), 2),
        "median_abs_pct": round(float(np.median(np.abs(pred - truth) / truth) * 100), 2),
        "within_10pct": round(float(np.mean(np.abs(pred - truth) / truth < 0.10) * 100), 1),
        "within_20pct": round(float(np.mean(np.abs(pred - truth) / truth < 0.20) * 100), 1),
        "trained_seconds": round(time.perf_counter() - started, 1),
    }

    # Permutation importance rather than the tree's own split counts: it
    # measures what the model actually relies on, and it is what we show the
    # artisan as "what moved your price".
    perm = permutation_importance(model, X_test, y_test, n_repeats=6,
                                  random_state=seed, n_jobs=1)
    importance = sorted(
        ({"feature": f, "weight": round(float(w), 4)}
         for f, w in zip(features, perm.importances_mean)),
        key=lambda d: -d["weight"],
    )

    joblib.dump({"model": model, "features": features,
                 "metrics": metrics, "importance": importance}, MODEL_PATH)
    return {"metrics": metrics, "importance": importance, "path": str(MODEL_PATH)}


if __name__ == "__main__":
    result = train()
    print(json.dumps(result["metrics"], indent=2))
    print("\nWhat the model relies on:")
    for row in result["importance"][:8]:
        print(f"  {row['feature']:<18} {row['weight']}")
    print(f"\nSaved to {result['path']}")
