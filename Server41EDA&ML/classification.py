from __future__ import annotations

from pathlib import Path
import json

import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    confusion_matrix,
    precision_recall_fscore_support,
)
from sklearn.inspection import permutation_importance


BASE_DIR = Path(__file__).resolve().parent
INPUT_FILE = BASE_DIR / "demo.xslx"
OUTPUT_DIR = BASE_DIR / "classification_output"
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


def make_demand_classes(train_demand: pd.Series, demand: pd.Series) -> tuple[pd.Series, dict]:
    low_cut, high_cut = train_demand.quantile([0.33, 0.66]).to_list()

    labels = pd.cut(
        demand,
        bins=[-np.inf, low_cut, high_cut, np.inf],
        labels=["low", "medium", "high"],
        include_lowest=True,
    )
    thresholds = {
        "low_max": round(float(low_cut), 4),
        "medium_max": round(float(high_cut), 4),
        "high_min": round(float(high_cut), 4),
    }
    return labels.astype(str), thresholds


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

    y_all, class_thresholds = make_demand_classes(train_df["demand"], df["demand"])
    y_train = y_all.iloc[:split_index]
    y_test = y_all.iloc[split_index:]
    x_train = train_df[feature_columns]
    x_test = test_df[feature_columns]

    model = HistGradientBoostingClassifier(random_state=RANDOM_STATE)
    model.fit(x_train, y_train)
    predictions = model.predict(x_test)

    precision, recall, f1, _ = precision_recall_fscore_support(
        y_test, predictions, average="macro", zero_division=0
    )

    metrics = {
        "dataset": INPUT_FILE.name,
        "task": "Classify demand into low, medium, and high bands",
        "rows_used": int(len(df)),
        "train_rows": int(len(train_df)),
        "test_rows": int(len(test_df)),
        "split_type": "chronological 80/20 split",
        "class_thresholds_from_training_data": class_thresholds,
        "accuracy": round(float(accuracy_score(y_test, predictions)), 6),
        "macro_precision": round(float(precision), 6),
        "macro_recall": round(float(recall), 6),
        "macro_f1": round(float(f1), 6),
        "train_date_range": {
            "start": str(train_df["datetime"].min()),
            "end": str(train_df["datetime"].max()),
        },
        "test_date_range": {
            "start": str(test_df["datetime"].min()),
            "end": str(test_df["datetime"].max()),
        },
    }

    report = classification_report(y_test, predictions, output_dict=True, zero_division=0)
    report_df = pd.DataFrame(report).T.round(6)

    labels = ["low", "medium", "high"]
    confusion_df = pd.DataFrame(
        confusion_matrix(y_test, predictions, labels=labels),
        index=[f"actual_{label}" for label in labels],
        columns=[f"predicted_{label}" for label in labels],
    )

    importance_sample = x_test.sample(n=min(10000, len(x_test)), random_state=RANDOM_STATE)
    importance = permutation_importance(
        model,
        importance_sample,
        y_test.loc[importance_sample.index],
        n_repeats=5,
        random_state=RANDOM_STATE,
        scoring="f1_macro",
    )
    importance_df = pd.DataFrame(
        {
            "feature": feature_columns,
            "importance_mean": importance.importances_mean,
            "importance_std": importance.importances_std,
        }
    ).sort_values("importance_mean", ascending=False)

    sample_predictions = test_df[["datetime", "demand"]].copy()
    sample_predictions["actual_class"] = y_test.values
    sample_predictions["predicted_class"] = predictions
    sample_predictions = sample_predictions.head(1000)

    (OUTPUT_DIR / "classification_metrics.json").write_text(
        json.dumps(metrics, indent=2), encoding="utf-8"
    )
    report_df.to_csv(OUTPUT_DIR / "classification_report.csv")
    confusion_df.to_csv(OUTPUT_DIR / "confusion_matrix.csv")
    importance_df.round(6).to_csv(OUTPUT_DIR / "feature_importance.csv", index=False)
    sample_predictions.to_csv(OUTPUT_DIR / "sample_predictions.csv", index=False)

    markdown = [
        "# Classification Model Report",
        "",
        f"- Dataset: `{metrics['dataset']}`",
        f"- Target: `{metrics['task']}`",
        f"- Split: `{metrics['split_type']}`",
        f"- Train rows: `{metrics['train_rows']}`",
        f"- Test rows: `{metrics['test_rows']}`",
        f"- Accuracy: `{metrics['accuracy']}`",
        f"- Macro F1: `{metrics['macro_f1']}`",
        f"- Macro precision: `{metrics['macro_precision']}`",
        f"- Macro recall: `{metrics['macro_recall']}`",
        f"- Demand bands: low <= `{class_thresholds['low_max']}`, medium <= `{class_thresholds['medium_max']}`, high > `{class_thresholds['high_min']}`",
        "",
        "## Files Generated",
        "- `classification_metrics.json`",
        "- `classification_report.csv`",
        "- `confusion_matrix.csv`",
        "- `feature_importance.csv`",
        "- `sample_predictions.csv`",
        "- `classification_model_report.md`",
    ]
    (OUTPUT_DIR / "classification_model_report.md").write_text("\n".join(markdown), encoding="utf-8")

    print("Classification completed.")
    print(f"Accuracy: {metrics['accuracy']}")
    print(f"Macro F1: {metrics['macro_f1']}")
    print(f"Report folder: {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
