from __future__ import annotations

from pathlib import Path
import json

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy import stats
from sklearn.ensemble import RandomForestRegressor
from sklearn.feature_selection import mutual_info_regression
from sklearn.inspection import permutation_importance
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.decomposition import PCA


BASE_DIR = Path(__file__).resolve().parent
INPUT_FILE = BASE_DIR / "demo.xslx"
OUTPUT_DIR = BASE_DIR / "bivariate_multivariate_output"
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


def prepare_data(df: pd.DataFrame) -> pd.DataFrame:
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


def save_line_plot(df: pd.DataFrame, x_col: str, y_col: str, title: str, output_path: Path) -> None:
    plt.figure(figsize=(10, 5))
    plt.plot(df[x_col], df[y_col], marker="o", linewidth=1.8)
    plt.title(title)
    plt.xlabel(x_col)
    plt.ylabel(y_col)
    plt.grid(alpha=0.3)
    plt.tight_layout()
    plt.savefig(output_path, dpi=150)
    plt.close()


def save_heatmap(correlation: pd.DataFrame, output_path: Path) -> None:
    plt.figure(figsize=(9, 7))
    plt.imshow(correlation, cmap="coolwarm", vmin=-1, vmax=1)
    plt.colorbar(label="Correlation")
    plt.xticks(range(len(correlation.columns)), correlation.columns, rotation=45, ha="right")
    plt.yticks(range(len(correlation.index)), correlation.index)
    plt.title("Multivariate Correlation Heatmap")
    plt.tight_layout()
    plt.savefig(output_path, dpi=150)
    plt.close()


def regression_metrics(y_true: pd.Series, y_pred: np.ndarray) -> dict:
    return {
        "mae": round(float(mean_absolute_error(y_true, y_pred)), 6),
        "rmse": round(float(np.sqrt(mean_squared_error(y_true, y_pred))), 6),
        "r2": round(float(r2_score(y_true, y_pred)), 6),
    }


def run_bivariate_analysis(data: pd.DataFrame) -> dict:
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

    pearson_rows = []
    for feature in feature_columns:
        pearson = stats.pearsonr(data[feature], data["demand"])
        spearman = stats.spearmanr(data[feature], data["demand"])
        pearson_rows.append(
            {
                "feature": feature,
                "pearson_correlation": round(float(pearson.statistic), 6),
                "pearson_pvalue": float(pearson.pvalue),
                "spearman_correlation": round(float(spearman.statistic), 6),
                "spearman_pvalue": float(spearman.pvalue),
            }
        )

    correlation_df = pd.DataFrame(pearson_rows).sort_values(
        "pearson_correlation", key=lambda s: s.abs(), ascending=False
    )
    correlation_df.to_csv(OUTPUT_DIR / "bivariate_correlations.csv", index=False)

    grouped_specs = {
        "block": "demand_by_block.csv",
        "hour": "demand_by_hour.csv",
        "day_of_week": "demand_by_day_of_week.csv",
        "month": "demand_by_month.csv",
        "is_weekend": "demand_by_weekend_flag.csv",
    }

    group_outputs = {}
    for column, filename in grouped_specs.items():
        grouped = (
            data.groupby(column)["demand"]
            .agg(["count", "mean", "median", "std", "min", "max"])
            .round(6)
            .reset_index()
        )
        grouped.to_csv(OUTPUT_DIR / filename, index=False)
        group_outputs[column] = grouped

    block_anova = stats.f_oneway(
        *[
            group["demand"].sample(n=min(1000, len(group)), random_state=RANDOM_STATE).to_numpy()
            for _, group in data.groupby("block")
        ]
    )
    hour_anova = stats.f_oneway(
        *[
            group["demand"].sample(n=min(1000, len(group)), random_state=RANDOM_STATE).to_numpy()
            for _, group in data.groupby("hour")
        ]
    )
    weekday_anova = stats.f_oneway(
        *[
            group["demand"].sample(n=min(1000, len(group)), random_state=RANDOM_STATE).to_numpy()
            for _, group in data.groupby("day_of_week")
        ]
    )

    save_line_plot(
        group_outputs["block"],
        "block",
        "mean",
        "Average Demand by Block",
        OUTPUT_DIR / "average_demand_by_block.png",
    )
    save_line_plot(
        group_outputs["hour"],
        "hour",
        "mean",
        "Average Demand by Hour",
        OUTPUT_DIR / "average_demand_by_hour.png",
    )
    save_line_plot(
        group_outputs["month"],
        "month",
        "mean",
        "Average Demand by Month",
        OUTPUT_DIR / "average_demand_by_month.png",
    )

    return {
        "top_absolute_correlations": correlation_df.head(5).to_dict(orient="records"),
        "anova_tests": {
            "block_vs_demand": {
                "f_statistic": round(float(block_anova.statistic), 6),
                "pvalue": float(block_anova.pvalue),
            },
            "hour_vs_demand": {
                "f_statistic": round(float(hour_anova.statistic), 6),
                "pvalue": float(hour_anova.pvalue),
            },
            "day_of_week_vs_demand": {
                "f_statistic": round(float(weekday_anova.statistic), 6),
                "pvalue": float(weekday_anova.pvalue),
            },
        },
    }


def run_multivariate_analysis(data: pd.DataFrame) -> dict:
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
    x = data[feature_columns]
    y = data["demand"]

    multivariate_correlation = data[feature_columns + ["demand"]].corr().round(6)
    multivariate_correlation.to_csv(OUTPUT_DIR / "multivariate_correlation_matrix.csv")
    save_heatmap(multivariate_correlation, OUTPUT_DIR / "multivariate_correlation_heatmap.png")

    x_train, x_test, y_train, y_test = train_test_split(
        x, y, test_size=0.2, random_state=RANDOM_STATE, shuffle=False
    )

    linear_model = LinearRegression()
    linear_model.fit(x_train, y_train)
    linear_predictions = linear_model.predict(x_test)

    forest_model = RandomForestRegressor(
        n_estimators=120,
        max_depth=16,
        min_samples_leaf=5,
        random_state=RANDOM_STATE,
        n_jobs=-1,
    )
    forest_model.fit(x_train, y_train)
    forest_predictions = forest_model.predict(x_test)

    importance_sample = x_test.sample(n=min(10000, len(x_test)), random_state=RANDOM_STATE)
    forest_importance = permutation_importance(
        forest_model,
        importance_sample,
        y_test.loc[importance_sample.index],
        n_repeats=5,
        random_state=RANDOM_STATE,
        scoring="neg_mean_absolute_error",
    )
    importance_df = pd.DataFrame(
        {
            "feature": feature_columns,
            "permutation_importance_mean": forest_importance.importances_mean,
            "permutation_importance_std": forest_importance.importances_std,
        }
    ).sort_values("permutation_importance_mean", ascending=False)
    importance_df.round(6).to_csv(OUTPUT_DIR / "multivariate_feature_importance.csv", index=False)

    mutual_information = mutual_info_regression(x, y, random_state=RANDOM_STATE)
    mutual_info_df = pd.DataFrame(
        {"feature": feature_columns, "mutual_information": mutual_information}
    ).sort_values("mutual_information", ascending=False)
    mutual_info_df.round(6).to_csv(OUTPUT_DIR / "multivariate_mutual_information.csv", index=False)

    scaled_x = StandardScaler().fit_transform(x)
    pca = PCA(n_components=5, random_state=RANDOM_STATE)
    pca.fit(scaled_x)
    pca_df = pd.DataFrame(
        {
            "principal_component": [f"PC{i}" for i in range(1, 6)],
            "explained_variance_ratio": pca.explained_variance_ratio_,
            "cumulative_explained_variance": np.cumsum(pca.explained_variance_ratio_),
        }
    )
    pca_df.round(6).to_csv(OUTPUT_DIR / "pca_explained_variance.csv", index=False)

    predictions_df = data.iloc[x_test.index][["datetime", "demand"]].copy()
    predictions_df["linear_prediction"] = linear_predictions
    predictions_df["random_forest_prediction"] = forest_predictions
    predictions_df["random_forest_error"] = predictions_df["demand"] - predictions_df["random_forest_prediction"]
    predictions_df.head(1000).to_csv(
        OUTPUT_DIR / "multivariate_sample_predictions.csv", index=False, float_format="%.6f"
    )

    return {
        "linear_regression_metrics": regression_metrics(y_test, linear_predictions),
        "random_forest_metrics": regression_metrics(y_test, forest_predictions),
        "top_feature_importance": importance_df.head(5).round(6).to_dict(orient="records"),
        "top_mutual_information": mutual_info_df.head(5).round(6).to_dict(orient="records"),
        "pca_first_5_components": pca_df.round(6).to_dict(orient="records"),
    }


def main() -> None:
    OUTPUT_DIR.mkdir(exist_ok=True)
    data = prepare_data(load_dataset(INPUT_FILE))

    bivariate_results = run_bivariate_analysis(data)
    multivariate_results = run_multivariate_analysis(data)

    summary = {
        "dataset": INPUT_FILE.name,
        "rows_used": int(len(data)),
        "datetime_range": {
            "start": str(data["datetime"].min()),
            "end": str(data["datetime"].max()),
        },
        "bivariate_analysis": bivariate_results,
        "multivariate_analysis": multivariate_results,
    }

    (OUTPUT_DIR / "bivariate_multivariate_summary.json").write_text(
        json.dumps(summary, indent=2), encoding="utf-8"
    )

    rf_metrics = multivariate_results["random_forest_metrics"]
    linear_metrics = multivariate_results["linear_regression_metrics"]
    top_corr = bivariate_results["top_absolute_correlations"][0]
    top_feature = multivariate_results["top_feature_importance"][0]

    report_lines = [
        "# Bivariate and Multivariate Analysis Report",
        "",
        f"- Dataset: `{summary['dataset']}`",
        f"- Rows analysed: `{summary['rows_used']}`",
        f"- Datetime range: `{summary['datetime_range']['start']}` to `{summary['datetime_range']['end']}`",
        "",
        "## Bivariate Analysis",
        f"- Strongest single correlation with demand: `{top_corr['feature']}` with Pearson correlation `{top_corr['pearson_correlation']}`.",
        f"- Block vs demand ANOVA p-value: `{bivariate_results['anova_tests']['block_vs_demand']['pvalue']:.6g}`.",
        f"- Hour vs demand ANOVA p-value: `{bivariate_results['anova_tests']['hour_vs_demand']['pvalue']:.6g}`.",
        f"- Day-of-week vs demand ANOVA p-value: `{bivariate_results['anova_tests']['day_of_week_vs_demand']['pvalue']:.6g}`.",
        "",
        "## Multivariate Analysis",
        f"- Linear regression R2: `{linear_metrics['r2']}`, MAE: `{linear_metrics['mae']}`.",
        f"- Random forest R2: `{rf_metrics['r2']}`, MAE: `{rf_metrics['mae']}`, RMSE: `{rf_metrics['rmse']}`.",
        f"- Most important multivariate feature: `{top_feature['feature']}`.",
        "",
        "## Files Generated",
        "- `bivariate_multivariate_summary.json`",
        "- `bivariate_correlations.csv`",
        "- `demand_by_block.csv`",
        "- `demand_by_hour.csv`",
        "- `demand_by_day_of_week.csv`",
        "- `demand_by_month.csv`",
        "- `multivariate_correlation_matrix.csv`",
        "- `multivariate_feature_importance.csv`",
        "- `multivariate_mutual_information.csv`",
        "- `pca_explained_variance.csv`",
        "- `multivariate_sample_predictions.csv`",
        "- `average_demand_by_block.png`",
        "- `average_demand_by_hour.png`",
        "- `average_demand_by_month.png`",
        "- `multivariate_correlation_heatmap.png`",
    ]
    (OUTPUT_DIR / "bivariate_multivariate_report.md").write_text(
        "\n".join(report_lines), encoding="utf-8"
    )

    print("Bivariate and multivariate analysis completed.")
    print(f"Strongest bivariate correlation: {top_corr['feature']} ({top_corr['pearson_correlation']})")
    print(f"Random forest R2: {rf_metrics['r2']}")
    print(f"Random forest MAE: {rf_metrics['mae']}")
    print(f"Report folder: {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
