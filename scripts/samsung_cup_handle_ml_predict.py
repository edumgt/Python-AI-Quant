"""Train a simple linear-regression model on the Samsung cup-with-handle
dataset (with Gaussian-jitter data augmentation) and compare its forecast
for the final two trading days against the actual recorded prices.

No third-party ML libraries are used (pure stdlib) so this runs anywhere.

Usage:
    python3 scripts/samsung_cup_handle_ml_predict.py \
        [--csv csv/samsung_cup_handle_2022_2023.csv] [--augment 4] [--seed 0]
"""
from __future__ import annotations

import argparse
import csv
import random
import statistics
from dataclasses import dataclass


@dataclass
class Bar:
    date: str
    open: float
    high: float
    low: float
    close: float
    volume: float


def load(path: str) -> list[Bar]:
    bars = []
    with open(path, newline="") as f:
        for row in csv.DictReader(f):
            bars.append(Bar(
                row["Date"], float(row["Open"]), float(row["High"]),
                float(row["Low"]), float(row["Close"]), float(row["Volume"]),
            ))
    return bars


FEATURE_NAMES = ["ret_1", "ret_2", "ret_3", "ret_4", "ret_5", "ma5_dev", "vol_z"]
LOOKBACK = 5
VOL_WINDOW = 20


def make_features(closes: list[float], volumes: list[float], t: int) -> list[float]:
    """Features observable using data up to and including index t."""
    rets = [(closes[t - k] - closes[t - k - 1]) / closes[t - k - 1] for k in range(LOOKBACK)]
    ma5 = sum(closes[t - 4:t + 1]) / 5
    ma5_dev = (closes[t] - ma5) / ma5
    vol_window = volumes[t - VOL_WINDOW + 1:t + 1]
    vmean = sum(vol_window) / len(vol_window)
    vstd = statistics.pstdev(vol_window) or 1.0
    vol_z = (volumes[t] - vmean) / vstd
    return rets + [ma5_dev, vol_z]


def build_dataset(bars: list[Bar], last_train_t: int):
    closes = [b.close for b in bars]
    volumes = [b.volume for b in bars]
    first_t = max(LOOKBACK - 1, VOL_WINDOW - 1)
    X, y = [], []
    for t in range(first_t, last_train_t + 1):
        X.append(make_features(closes, volumes, t))
        y.append((closes[t + 1] - closes[t]) / closes[t])  # next-day return
    return X, y


def augment(X: list[list[float]], y: list[float], factor: int, rng: random.Random):
    """Gaussian-jitter augmentation: add noise proportional to each feature's
    own spread, target left untouched. A standard, simple technique for
    inflating a small tabular training set."""
    if factor <= 0:
        return list(X), list(y)
    cols = list(zip(*X))
    stds = [statistics.pstdev(c) or 1e-6 for c in cols]
    aug_X, aug_y = list(X), list(y)
    for _ in range(factor):
        for row, target in zip(X, y):
            jittered = [v + rng.gauss(0, 0.1 * s) for v, s in zip(row, stds)]
            aug_X.append(jittered)
            aug_y.append(target)
    return aug_X, aug_y


def standardize(X: list[list[float]]):
    cols = list(zip(*X))
    means = [sum(c) / len(c) for c in cols]
    stds = [statistics.pstdev(c) or 1e-6 for c in cols]
    Xs = [[(v - m) / s for v, m, s in zip(row, means, stds)] for row in X]
    return Xs, means, stds


def apply_standardize(row: list[float], means: list[float], stds: list[float]):
    return [(v - m) / s for v, m, s in zip(row, means, stds)]


def train_linear_regression(X: list[list[float]], y: list[float], lr=0.05, epochs=2000, l2=1e-3):
    n, d = len(X), len(X[0])
    w = [0.0] * d
    b = 0.0
    for _ in range(epochs):
        grad_w = [0.0] * d
        grad_b = 0.0
        for row, target in zip(X, y):
            pred = sum(wi * xi for wi, xi in zip(w, row)) + b
            err = pred - target
            for j in range(d):
                grad_w[j] += err * row[j]
            grad_b += err
        for j in range(d):
            grad_w[j] = grad_w[j] / n + l2 * w[j]
            w[j] -= lr * grad_w[j]
        b -= lr * (grad_b / n)
    return w, b


def predict(w, b, row):
    return sum(wi * xi for wi, xi in zip(w, row)) + b


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--csv", default="csv/samsung_cup_handle_2022_2023.csv")
    parser.add_argument("--augment", type=int, default=4, help="jittered copies per training row")
    parser.add_argument("--seed", type=int, default=0)
    args = parser.parse_args()
    rng = random.Random(args.seed)

    bars = load(args.csv)
    closes = [b.close for b in bars]
    volumes = [b.volume for b in bars]
    n = len(bars)

    # Hold out the final two trading days entirely from training.
    idx_last = n - 1          # 2023-06-30
    idx_penultimate = n - 2   # 2023-06-29
    last_train_t = idx_penultimate - 2  # target for this t is close[idx_penultimate-1]

    X_raw, y = build_dataset(bars, last_train_t)
    X_aug, y_aug = augment(X_raw, y, args.augment, rng)
    Xs, means, stds = standardize(X_aug)

    w, b = train_linear_regression(Xs, y_aug)

    # Training fit quality (on the un-augmented, real rows only)
    Xs_real = [apply_standardize(row, means, stds) for row in X_raw]
    train_preds = [predict(w, b, row) for row in Xs_real]
    train_mae_ret = sum(abs(p - t) for p, t in zip(train_preds, y)) / len(y)

    # --- Forecast 2023-06-29 using data through 2023-06-28 (idx_penultimate - 1) ---
    t1 = idx_penultimate - 1
    feat1 = apply_standardize(make_features(closes, volumes, t1), means, stds)
    pred_ret1 = predict(w, b, feat1)
    pred_close1 = closes[t1] * (1 + pred_ret1)
    actual_close1 = closes[idx_penultimate]

    # --- Forecast 2023-06-30 using actual data through 2023-06-29 (walk-forward) ---
    t2 = idx_penultimate
    feat2 = apply_standardize(make_features(closes, volumes, t2), means, stds)
    pred_ret2 = predict(w, b, feat2)
    pred_close2 = closes[t2] * (1 + pred_ret2)
    actual_close2 = closes[idx_last]

    # Naive baseline: "no change" forecast, for context
    naive1, naive2 = closes[t1], closes[t2]

    def pct_err(pred, actual):
        return (pred - actual) / actual * 100

    print(f"Loaded {n} bars from {args.csv}: {bars[0].date} -> {bars[-1].date}")
    print(f"Training rows: {len(X_raw)} real + {len(X_aug) - len(X_raw)} augmented "
          f"(x{args.augment} Gaussian jitter) = {len(X_aug)} total")
    print(f"Held out from training entirely: {bars[idx_penultimate].date}, {bars[idx_last].date}")
    print(f"Train MAE (next-day return, real rows only): {train_mae_ret * 100:.3f}%\n")

    print(f"{'Date':<12}{'Actual':>10}{'Predicted':>12}{'Error':>10}{'Error%':>9}{'Naive':>10}{'Naive%':>9}")
    for date, actual, pred, naive in [
        (bars[idx_penultimate].date, actual_close1, pred_close1, naive1),
        (bars[idx_last].date, actual_close2, pred_close2, naive2),
    ]:
        err = pred - actual
        print(f"{date:<12}{actual:>10,.0f}{pred:>12,.0f}{err:>10,.0f}{pct_err(pred, actual):>8.2f}%"
              f"{naive:>10,.0f}{pct_err(naive, actual):>8.2f}%")

    ml_mape = (abs(pct_err(pred_close1, actual_close1)) + abs(pct_err(pred_close2, actual_close2))) / 2
    naive_mape = (abs(pct_err(naive1, actual_close1)) + abs(pct_err(naive2, actual_close2))) / 2
    print(f"\nMAPE over held-out days -> ML model: {ml_mape:.2f}%  |  naive (no-change): {naive_mape:.2f}%")


if __name__ == "__main__":
    main()
