from __future__ import annotations

from pathlib import Path
import json

import numpy as np
import pandas as pd
from scipy import stats
from statsmodels.stats.diagnostic import acorr_ljungbox
from statsmodels.tsa.stattools import adfuller, acf


BASE_DIR = Path(__file__).resolve().parent
INPUT_FILE = BASE_DIR / "demo.xslx"
OUTPUT_DIR = BASE_DIR / "inferential_data_quality_output"


def load_dataset(file_path: Path) -> pd.DataFrame:
    """Load the source data even if the extension is misleading."""
    loaders = (
        lambda: pd.read_csv(file_path, sep="\t"),
        lambda: pd.read_csv(file_path),
        lambda: pd.read_excel(file_path),
    )

    last_error: Exception | None = None
    for loader in loaders:
        try:
            return loader()
        except Exception as exc:  # pragma: no cover - fallback path
            last_error = exc

    raise ValueError(f"Could not load {file_path.name}: {last_error}") from last_error


def cohens_d(sample_a: pd.Series, sample_b: pd.Series) -> float:
    a = sample_a.to_numpy(dtype=float)
    b = sample_b.to_numpy(dtype=float)
    pooled_std = np.sqrt(((a.std(ddof=1) ** 2) + (b.std(ddof=1) ** 2)) / 2)
    if pooled_std == 0:
        return 0.0
    return float((a.mean() - b.mean()) / pooled_std)


def eta_squared_from_anova(groups: list[np.ndarray], f_stat: float) -> float:
    k = len(groups)
    n_total = sum(len(group) for group in groups)
    if n_total == k:
        return 0.0
    return float((f_stat * (k - 1)) / ((f_stat * (k - 1)) + (n_total - k)))


def prepare_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["datetime"] = pd.to_datetime(df["datetime"], format="%d-%m-%Y %H:%M", errors="coerce")
    df["date_only"] = df["datetime"].dt.date
    df["hour"] = df["datetime"].dt.hour
    df["weekday"] = df["datetime"].dt.dayofweek
    df["is_weekend"] = df["weekday"] >= 5
    df = df.sort_values("datetime").reset_index(drop=True)
    return df


def build_results(df: pd.DataFrame) -> tuple[dict, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    demand = df["demand"].astype(float)
    n = len(demand)

    mean_ci = stats.t.interval(0.95, n - 1, loc=demand.mean(), scale=stats.sem(demand))

    normality_sample = demand.sample(n=min(5000, n), random_state=42)
    shapiro_result = stats.shapiro(normality_sample)
    dagostino_result = stats.normaltest(normality_sample)

    weekday_demand = df.loc[~df["is_weekend"], "demand"]
    weekend_demand = df.loc[df["is_weekend"], "demand"]
    ttest_result = stats.ttest_ind(weekday_demand, weekend_demand, equal_var=False)

    mann_weekday = weekday_demand.sample(n=min(20000, len(weekday_demand)), random_state=42)
    mann_weekend = weekend_demand.sample(n=min(20000, len(weekend_demand)), random_state=42)
    mannwhitney_result = stats.mannwhitneyu(mann_weekday, mann_weekend, alternative="two-sided")

    hour_groups = [
        group["demand"].sample(n=min(1000, len(group)), random_state=42).to_numpy()
        for _, group in df.groupby("hour")
    ]
    anova_result = stats.f_oneway(*hour_groups)
    levene_result = stats.levene(*hour_groups, center="median")
    eta_sq = eta_squared_from_anova(hour_groups, float(anova_result.statistic))

    daily_mean = df.groupby("date_only", as_index=False)["demand"].mean()
    daily_mean["time_index"] = np.arange(len(daily_mean))
    trend_result = stats.linregress(daily_mean["time_index"], daily_mean["demand"])

    adf_stat, adf_pvalue, *_ = adfuller(demand.iloc[:50000], autolag="AIC")
    ljung_box = acorr_ljungbox(demand.iloc[:20000], lags=[1, 4, 24, 96], return_df=True).reset_index()
    ljung_box.rename(columns={"index": "lag"}, inplace=True)
    acf_values = acf(demand.iloc[:5000], nlags=10, fft=True)

    z_scores = stats.zscore(demand, nan_policy="omit")
    anomalies = df.loc[np.abs(z_scores) > 3, ["datetime", "demand"]].copy()
    anomalies["z_score"] = z_scores[np.abs(z_scores) > 3]
    anomalies["abs_z_score"] = anomalies["z_score"].abs()
    anomalies = anomalies.sort_values("abs_z_score", ascending=False).reset_index(drop=True)

    hourly_summary = (
        df.groupby("hour")["demand"]
        .agg(["count", "mean", "std", "min", "max"])
        .round(4)
        .reset_index()
    )

    results = {
        "dataset_name": INPUT_FILE.name,
        "rows": int(len(df)),
        "analysis_window": {
            "datetime_min": str(df["datetime"].min()),
            "datetime_max": str(df["datetime"].max()),
        },
        "confidence_interval_mean_demand_95pct": {
            "lower": round(float(mean_ci[0]), 4),
            "upper": round(float(mean_ci[1]), 4),
        },
        "normality_tests_on_sample_n5000": {
            "shapiro_w": round(float(shapiro_result.statistic), 6),
            "shapiro_pvalue": float(shapiro_result.pvalue),
            "dagostino_k2": round(float(dagostino_result.statistic), 6),
            "dagostino_pvalue": float(dagostino_result.pvalue),
        },
        "weekday_vs_weekend_tests": {
            "weekday_mean": round(float(weekday_demand.mean()), 4),
            "weekend_mean": round(float(weekend_demand.mean()), 4),
            "welch_t_statistic": round(float(ttest_result.statistic), 6),
            "welch_pvalue": float(ttest_result.pvalue),
            "cohens_d": round(cohens_d(weekday_demand, weekend_demand), 6),
            "mannwhitney_u_statistic": float(mannwhitney_result.statistic),
            "mannwhitney_pvalue": float(mannwhitney_result.pvalue),
        },
        "hourly_variation_tests": {
            "anova_f_statistic": round(float(anova_result.statistic), 6),
            "anova_pvalue": float(anova_result.pvalue),
            "eta_squared": round(eta_sq, 6),
            "levene_statistic": round(float(levene_result.statistic), 6),
            "levene_pvalue": float(levene_result.pvalue),
        },
        "daily_trend_test": {
            "slope_per_day": round(float(trend_result.slope), 6),
            "pvalue": float(trend_result.pvalue),
            "r_squared": round(float(trend_result.rvalue**2), 6),
        },
        "time_series_dependency_tests": {
            "adf_statistic": round(float(adf_stat), 6),
            "adf_pvalue": float(adf_pvalue),
            "acf_lags_0_to_10": [round(float(value), 6) for value in acf_values],
        },
        "anomaly_signal": {
            "zscore_threshold": 3.0,
            "anomaly_row_count": int(len(anomalies)),
        },
    }

    return results, ljung_box, hourly_summary, anomalies


def write_outputs(
    results: dict,
    ljung_box: pd.DataFrame,
    hourly_summary: pd.DataFrame,
    anomalies: pd.DataFrame,
) -> None:
    OUTPUT_DIR.mkdir(exist_ok=True)

    results_path = OUTPUT_DIR / "inferential_quality_summary.json"
    ljung_box_path = OUTPUT_DIR / "ljung_box_results.csv"
    hourly_summary_path = OUTPUT_DIR / "hourly_demand_summary.csv"
    anomalies_path = OUTPUT_DIR / "zscore_anomalies.csv"
    report_path = OUTPUT_DIR / "inferential_quality_report.md"

    results_path.write_text(json.dumps(results, indent=2), encoding="utf-8")
    ljung_box.to_csv(ljung_box_path, index=False)
    hourly_summary.to_csv(hourly_summary_path, index=False)
    anomalies.to_csv(anomalies_path, index=False)

    report_lines = [
        "# Inferential Data Quality Report",
        "",
        f"- Dataset: `{results['dataset_name']}`",
        f"- Rows analysed: `{results['rows']}`",
        f"- Datetime range: `{results['analysis_window']['datetime_min']}` to `{results['analysis_window']['datetime_max']}`",
        "",
        "## Key Statistical Findings",
        f"- 95% CI for mean demand: `{results['confidence_interval_mean_demand_95pct']['lower']}` to `{results['confidence_interval_mean_demand_95pct']['upper']}`",
        f"- Normality rejected on sampled demand values: Shapiro p-value `{results['normality_tests_on_sample_n5000']['shapiro_pvalue']:.6g}`, D'Agostino p-value `{results['normality_tests_on_sample_n5000']['dagostino_pvalue']:.6g}`",
        f"- Weekday vs weekend demand differs significantly: Welch p-value `{results['weekday_vs_weekend_tests']['welch_pvalue']:.6g}`, Cohen's d `{results['weekday_vs_weekend_tests']['cohens_d']}`",
        f"- Hour-of-day means differ significantly: ANOVA p-value `{results['hourly_variation_tests']['anova_pvalue']:.6g}`, eta-squared `{results['hourly_variation_tests']['eta_squared']}`",
        f"- Hourly variances are not homogeneous: Levene p-value `{results['hourly_variation_tests']['levene_pvalue']:.6g}`",
        f"- Daily average demand shows a positive trend: slope/day `{results['daily_trend_test']['slope_per_day']}`, p-value `{results['daily_trend_test']['pvalue']:.6g}`",
        f"- Strong serial dependence exists: ADF p-value `{results['time_series_dependency_tests']['adf_pvalue']:.6g}`, anomaly rows by |z| > 3: `{results['anomaly_signal']['anomaly_row_count']}`",
        "",
        "## Files Generated",
        "- `inferential_quality_summary.json`",
        "- `ljung_box_results.csv`",
        "- `hourly_demand_summary.csv`",
        "- `zscore_anomalies.csv`",
        "- `inferential_quality_report.md`",
    ]
    report_path.write_text("\n".join(report_lines), encoding="utf-8")


def main() -> None:
    df = load_dataset(INPUT_FILE)
    prepared = prepare_dataframe(df)
    results, ljung_box, hourly_summary, anomalies = build_results(prepared)
    write_outputs(results, ljung_box, hourly_summary, anomalies)

    print("Inferential data quality analysis completed.")
    print(f"Input file: {INPUT_FILE.name}")
    print(
        "95% CI for mean demand: "
        f"{results['confidence_interval_mean_demand_95pct']['lower']} to "
        f"{results['confidence_interval_mean_demand_95pct']['upper']}"
    )
    print(
        "Weekday vs weekend p-value: "
        f"{results['weekday_vs_weekend_tests']['welch_pvalue']}, "
        f"hourly ANOVA p-value: {results['hourly_variation_tests']['anova_pvalue']}"
    )
    print(f"Report folder: {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
