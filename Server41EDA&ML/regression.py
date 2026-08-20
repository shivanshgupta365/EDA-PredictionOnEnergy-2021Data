from __future__ import annotations

from pathlib import Path
import json

import numpy as np
import pandas as pd
from sklearn.dummy import DummyRegressor
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.inspection import permutation_importance
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score


BASE_DIR = Path(__file__).resolve().parent
INPUT_FILE = BASE_DIR / "demo.xslx"
OUTPUT_DIR = BASE_DIR / "regression_output"
RANDOM_STATE = 42


def load_dataset(file_path: Path) -> pd.DataFrame:
    """Load demo.xslx, which is tab-separated text with a misleading extension."""
    loaders = (
        lambda: pd.read_csv(file_path, sep="\t"),
        lambda: pd.read_csv(file_path),
        lambda: pd.read_excel(file_path),
    )

    last_error: Exception | None = None
    for loader in loaders:
        try:
            return loader()
        except Exception as exc:
            last_error = exc

    raise ValueError(f"Could not load {file_path.name}: {last_error}") from last_error


def prepare_features(df: pd.DataFrame) -> pd.DataFrame:
    data = df.copy()
    data["datetime"] = pd.to_datetime(data["datetime"], format="%d-%m-%Y %H:%M", errors="coerce")
    data = data.dropna(subset=["datetime", "demand", "block"]).sort_values("datetime").reset_index(drop=True)

    data["hour"] = data["datetime"].dt.hour
    data["minute"] = data["datetime"].dt.minute
    data["day"] = data["datetime"].dt.day
    data["month"] = data["datetime"].dt.month
    data["year"] = data["datetime"].dt.year
    data["day_of_week"] = data["datetime"].dt.dayofweek
    data["day_of_year"] = data["datetime"].dt.dayofyear
    data["quarter"] = data["datetime"].dt.quarter
    data["is_weekend"] = (data["day_of_week"] >= 5).astype(int)
    return data


def mape(y_true: pd.Series, y_pred: np.ndarray) -> float:
    y_true_array = y_true.to_numpy(dtype=float)
    mask = y_true_array != 0
    if not mask.any():
        return 0.0
    return float(np.mean(np.abs((y_true_array[mask] - y_pred[mask]) / y_true_array[mask])) * 100)


def regression_metrics(y_true: pd.Series, y_pred: np.ndarray) -> dict:
    rmse = np.sqrt(mean_squared_error(y_true, y_pred))
    return {
        "mae": round(float(mean_absolute_error(y_true, y_pred)), 6),
        "rmse": round(float(rmse), 6),
        "r2": round(float(r2_score(y_true, y_pred)), 6),
        "mape_pct": round(mape(y_true, y_pred), 6),
    }


def main() -> None:
    OUTPUT_DIR.mkdir(exist_ok=True)
    df = prepare_features(load_dataset(INPUT_FILE))

    feature_columns = [
        "block",
        "hour",
        "minute",
        "day",
        "month",
        "year",
        "day_of_week",
        "day_of_year",
        "quarter",
        "is_weekend",
    ]

    split_index = int(len(df) * 0.8)
    train_df = df.iloc[:split_index].copy()
    test_df = df.iloc[split_index:].copy()

    x_train = train_df[feature_columns]
    y_train = train_df["demand"]
    x_test = test_df[feature_columns]
    y_test = test_df["demand"]

    baseline = DummyRegressor(strategy="mean")
    baseline.fit(x_train, y_train)
    baseline_predictions = baseline.predict(x_test)

    model = HistGradientBoostingRegressor(
        random_state=RANDOM_STATE,
        max_iter=250,
        learning_rate=0.08,
        l2_regularization=0.05,
    )
    model.fit(x_train, y_train)
    predictions = model.predict(x_test)

    model_metrics = regression_metrics(y_test, predictions)
    baseline_metrics = regression_metrics(y_test, baseline_predictions)

    residuals = y_test.to_numpy(dtype=float) - predictions
    metrics = {
        "dataset": INPUT_FILE.name,
        "task": "Predict numeric demand",
        "rows_used": int(len(df)),
        "train_rows": int(len(train_df)),
        "test_rows": int(len(test_df)),
        "split_type": "chronological 80/20 split",
        "model": "HistGradientBoostingRegressor",
        "model_metrics": model_metrics,
        "baseline_mean_model_metrics": baseline_metrics,
        "residual_summary": {
            "mean_residual": round(float(np.mean(residuals)), 6),
            "median_residual": round(float(np.median(residuals)), 6),
            "std_residual": round(float(np.std(residuals, ddof=1)), 6),
            "min_residual": round(float(np.min(residuals)), 6),
            "max_residual": round(float(np.max(residuals)), 6),
        },
        "train_date_range": {
            "start": str(train_df["datetime"].min()),
            "end": str(train_df["datetime"].max()),
        },
        "test_date_range": {
            "start": str(test_df["datetime"].min()),
            "end": str(test_df["datetime"].max()),
        },
    }

    importance_sample = x_test.sample(n=min(10000, len(x_test)), random_state=RANDOM_STATE)
    importance = permutation_importance(
        model,
        importance_sample,
        y_test.loc[importance_sample.index],
        n_repeats=5,
        random_state=RANDOM_STATE,
        scoring="neg_mean_absolute_error",
    )
    importance_df = pd.DataFrame(
        {
            "feature": feature_columns,
            "importance_mean": importance.importances_mean,
            "importance_std": importance.importances_std,
        }
    ).sort_values("importance_mean", ascending=False)

    predictions_df = test_df[["datetime", "demand"]].copy()
    predictions_df["predicted_demand"] = predictions
    predictions_df["residual"] = predictions_df["demand"] - predictions_df["predicted_demand"]
    predictions_df["absolute_error"] = predictions_df["residual"].abs()

    (OUTPUT_DIR / "regression_metrics.json").write_text(
        json.dumps(metrics, indent=2), encoding="utf-8"
    )
    importance_df.round(6).to_csv(OUTPUT_DIR / "feature_importance.csv", index=False)
    predictions_df.to_csv(OUTPUT_DIR / "all_predictions.csv", index=False, float_format="%.6f")
    predictions_df.head(1000).to_csv(
        OUTPUT_DIR / "sample_predictions.csv", index=False, float_format="%.6f"
    )
    predictions_df.nlargest(100, "absolute_error").to_csv(
        OUTPUT_DIR / "largest_prediction_errors.csv", index=False, float_format="%.6f"
    )

    markdown = [
        "# Regression Model Report",
        "",
        f"- Dataset: `{metrics['dataset']}`",
        f"- Target: `{metrics['task']}`",
        f"- Model: `{metrics['model']}`",
        f"- Split: `{metrics['split_type']}`",
        f"- Train rows: `{metrics['train_rows']}`",
        f"- Test rows: `{metrics['test_rows']}`",
        f"- MAE: `{model_metrics['mae']}`",
        f"- RMSE: `{model_metrics['rmse']}`",
        f"- R2: `{model_metrics['r2']}`",
        f"- MAPE: `{model_metrics['mape_pct']}%`",
        f"- Baseline MAE: `{baseline_metrics['mae']}`",
        f"- Baseline RMSE: `{baseline_metrics['rmse']}`",
        "",
        "## Files Generated",
        "- `regression_metrics.json`",
        "- `feature_importance.csv`",
        "- `all_predictions.csv`",
        "- `sample_predictions.csv`",
        "- `largest_prediction_errors.csv`",
        "- `regression_model_report.md`",
    ]
    (OUTPUT_DIR / "regression_model_report.md").write_text("\n".join(markdown), encoding="utf-8")

    print("Regression completed.")
    print(f"MAE: {model_metrics['mae']}")
    print(f"RMSE: {model_metrics['rmse']}")
    print(f"R2: {model_metrics['r2']}")
    print(f"Report folder: {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
