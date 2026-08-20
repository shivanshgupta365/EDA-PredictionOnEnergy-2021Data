from __future__ import annotations

from pathlib import Path
import json

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.inspection import permutation_importance
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score


BASE_DIR = Path(__file__).resolve().parent
INPUT_FILE = BASE_DIR / "demo.xslx"
OUTPUT_DIR = BASE_DIR / "lag_feature_analysis_output"
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
    data["demand"] = pd.to_numeric(data["demand"], errors="coerce")
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

    lag_steps = {
        "lag_15min": 1,
        "lag_30min": 2,
        "lag_1hour": 4,
        "lag_2hour": 8,
        "lag_6hour": 24,
        "lag_12hour": 48,
        "lag_1day": 96,
        "lag_1week": 672,
    }
    for column, periods in lag_steps.items():
        data[column] = data["demand"].shift(periods)

    data["rolling_mean_1hour"] = data["demand"].shift(1).rolling(window=4).mean()
    data["rolling_mean_6hour"] = data["demand"].shift(1).rolling(window=24).mean()
    data["rolling_mean_1day"] = data["demand"].shift(1).rolling(window=96).mean()
    data["rolling_std_1day"] = data["demand"].shift(1).rolling(window=96).std()

    return data


def metrics(y_true: pd.Series, y_pred: np.ndarray) -> dict:
    return {
        "mae": round(float(mean_absolute_error(y_true, y_pred)), 6),
        "rmse": round(float(np.sqrt(mean_squared_error(y_true, y_pred))), 6),
        "r2": round(float(r2_score(y_true, y_pred)), 6),
        "mape_pct": round(
            float(np.mean(np.abs((y_true.to_numpy() - y_pred) / y_true.to_numpy())) * 100),
            6,
        ),
    }


def save_actual_vs_predicted_plot(predictions: pd.DataFrame) -> None:
    sample = predictions.head(300)
    plt.figure(figsize=(12, 5))
    plt.plot(sample["datetime"], sample["actual_demand"], label="Actual", linewidth=1.8)
    plt.plot(sample["datetime"], sample["lag_model_prediction"], label="Lag model", linewidth=1.4)
    plt.title("Actual vs Lag-Feature Model Prediction")
    plt.xlabel("Datetime")
    plt.ylabel("Demand")
    plt.legend()
    plt.grid(alpha=0.3)
    plt.tight_layout()
    plt.savefig(OUTPUT_DIR / "actual_vs_lag_prediction.png", dpi=150)
    plt.close()


def main() -> None:
    OUTPUT_DIR.mkdir(exist_ok=True)
    data = prepare_features(load_dataset(INPUT_FILE))

    base_features = [
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
    lag_features = [
        "lag_15min",
        "lag_30min",
        "lag_1hour",
        "lag_2hour",
        "lag_6hour",
        "lag_12hour",
        "lag_1day",
        "lag_1week",
        "rolling_mean_1hour",
        "rolling_mean_6hour",
        "rolling_mean_1day",
        "rolling_std_1day",
    ]
    all_features = base_features + lag_features

    model_data = data.dropna(subset=all_features + ["demand"]).reset_index(drop=True)
    split_index = int(len(model_data) * 0.8)
    train_df = model_data.iloc[:split_index].copy()
    test_df = model_data.iloc[split_index:].copy()

    base_model = HistGradientBoostingRegressor(random_state=RANDOM_STATE, max_iter=250)
    lag_model = HistGradientBoostingRegressor(random_state=RANDOM_STATE, max_iter=250)

    base_model.fit(train_df[base_features], train_df["demand"])
    lag_model.fit(train_df[all_features], train_df["demand"])

    base_predictions = base_model.predict(test_df[base_features])
    lag_predictions = lag_model.predict(test_df[all_features])

    base_metrics = metrics(test_df["demand"], base_predictions)
    lag_metrics = metrics(test_df["demand"], lag_predictions)

    improvement = {
        "mae_reduction": round(base_metrics["mae"] - lag_metrics["mae"], 6),
        "rmse_reduction": round(base_metrics["rmse"] - lag_metrics["rmse"], 6),
        "r2_gain": round(lag_metrics["r2"] - base_metrics["r2"], 6),
        "mape_reduction_pct_points": round(base_metrics["mape_pct"] - lag_metrics["mape_pct"], 6),
    }

    importance_sample = test_df[all_features].sample(
        n=min(10000, len(test_df)), random_state=RANDOM_STATE
    )
    importance = permutation_importance(
        lag_model,
        importance_sample,
        test_df.loc[importance_sample.index, "demand"],
        n_repeats=5,
        random_state=RANDOM_STATE,
        scoring="neg_mean_absolute_error",
    )
    importance_df = pd.DataFrame(
        {
            "feature": all_features,
            "importance_mean": importance.importances_mean,
            "importance_std": importance.importances_std,
        }
    ).sort_values("importance_mean", ascending=False)

    lag_correlation_df = (
        model_data[lag_features + ["demand"]]
        .corr()[["demand"]]
        .drop(index="demand")
        .rename(columns={"demand": "correlation_with_demand"})
        .sort_values("correlation_with_demand", key=lambda s: s.abs(), ascending=False)
        .reset_index()
        .rename(columns={"index": "lag_feature"})
    )

    predictions_df = test_df[["datetime", "demand"]].copy()
    predictions_df.rename(columns={"demand": "actual_demand"}, inplace=True)
    predictions_df["base_model_prediction"] = base_predictions
    predictions_df["lag_model_prediction"] = lag_predictions
    predictions_df["lag_model_absolute_error"] = (
        predictions_df["actual_demand"] - predictions_df["lag_model_prediction"]
    ).abs()

    save_actual_vs_predicted_plot(predictions_df)

    summary = {
        "dataset": INPUT_FILE.name,
        "rows_after_lag_creation": int(len(model_data)),
        "dropped_rows_due_to_lags": int(len(data) - len(model_data)),
        "split_type": "chronological 80/20 split",
        "train_rows": int(len(train_df)),
        "test_rows": int(len(test_df)),
        "train_date_range": {
            "start": str(train_df["datetime"].min()),
            "end": str(train_df["datetime"].max()),
        },
        "test_date_range": {
            "start": str(test_df["datetime"].min()),
            "end": str(test_df["datetime"].max()),
        },
        "base_time_feature_model_metrics": base_metrics,
        "lag_feature_model_metrics": lag_metrics,
        "improvement_from_lag_features": improvement,
        "top_lag_correlations": lag_correlation_df.head(6).round(6).to_dict(orient="records"),
        "top_feature_importance": importance_df.head(10).round(6).to_dict(orient="records"),
    }

    (OUTPUT_DIR / "lag_feature_summary.json").write_text(
        json.dumps(summary, indent=2), encoding="utf-8"
    )
    importance_df.round(6).to_csv(OUTPUT_DIR / "lag_feature_importance.csv", index=False)
    lag_correlation_df.round(6).to_csv(OUTPUT_DIR / "lag_correlations.csv", index=False)
    predictions_df.head(1000).to_csv(
        OUTPUT_DIR / "lag_sample_predictions.csv", index=False, float_format="%.6f"
    )
    predictions_df.nlargest(100, "lag_model_absolute_error").to_csv(
        OUTPUT_DIR / "largest_lag_model_errors.csv", index=False, float_format="%.6f"
    )

    top_feature = summary["top_feature_importance"][0]
    report_lines = [
        "# Lag Feature Analysis Report",
        "",
        f"- Dataset: `{summary['dataset']}`",
        f"- Rows after lag creation: `{summary['rows_after_lag_creation']}`",
        f"- Rows dropped because lag history was unavailable: `{summary['dropped_rows_due_to_lags']}`",
        f"- Split: `{summary['split_type']}`",
        f"- Base time-feature model R2: `{base_metrics['r2']}`, MAE: `{base_metrics['mae']}`",
        f"- Lag-feature model R2: `{lag_metrics['r2']}`, MAE: `{lag_metrics['mae']}`",
        f"- MAE reduction from lag features: `{improvement['mae_reduction']}`",
        f"- RMSE reduction from lag features: `{improvement['rmse_reduction']}`",
        f"- R2 gain from lag features: `{improvement['r2_gain']}`",
        f"- Most important feature in lag model: `{top_feature['feature']}`",
        "",
        "## Files Generated",
        "- `lag_feature_summary.json`",
        "- `lag_feature_importance.csv`",
        "- `lag_correlations.csv`",
        "- `lag_sample_predictions.csv`",
        "- `largest_lag_model_errors.csv`",
        "- `actual_vs_lag_prediction.png`",
        "- `lag_feature_report.md`",
    ]
    (OUTPUT_DIR / "lag_feature_report.md").write_text("\n".join(report_lines), encoding="utf-8")

    print("Lag feature analysis completed.")
    print(f"Base model R2: {base_metrics['r2']}, MAE: {base_metrics['mae']}")
    print(f"Lag model R2: {lag_metrics['r2']}, MAE: {lag_metrics['mae']}")
    print(f"Top lag-model feature: {top_feature['feature']}")
    print(f"Report folder: {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
