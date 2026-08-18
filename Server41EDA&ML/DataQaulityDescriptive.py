from __future__ import annotations

from pathlib import Path
import json

import pandas as pd


BASE_DIR = Path(__file__).resolve().parent
INPUT_FILE = BASE_DIR / "demo.xslx"
OUTPUT_DIR = BASE_DIR / "descriptive_data_quality_output"


def load_dataset(file_path: Path) -> pd.DataFrame:
    """Load the source data, even if the extension is misleading."""
    loaders = (
        ("tab-separated text", lambda: pd.read_csv(file_path, sep="\t")),
        ("comma-separated text", lambda: pd.read_csv(file_path)),
        ("excel workbook", lambda: pd.read_excel(file_path)),
    )

    last_error: Exception | None = None
    for _, loader in loaders:
        try:
            return loader()
        except Exception as exc:  # pragma: no cover - fallback path
            last_error = exc

    raise ValueError(f"Could not load {file_path.name}: {last_error}") from last_error


def build_summary(df: pd.DataFrame) -> tuple[dict, pd.DataFrame, pd.DataFrame]:
    datetime_parsed = pd.to_datetime(df["datetime"], format="%d-%m-%Y %H:%M", errors="coerce")
    date_parsed = pd.to_datetime(df["date"], format="%d-%m-%Y %H:%M", errors="coerce")
    time_parsed = pd.to_timedelta(df["time"], errors="coerce")
    entry_time_parsed = pd.to_timedelta("00:" + df["entrydatetime"].astype(str), errors="coerce")

    sorted_datetime = datetime_parsed.sort_values().reset_index(drop=True)
    diff_counts = (
        sorted_datetime.diff().dropna().astype(str).value_counts().sort_values(ascending=False)
    )

    daily_counts = datetime_parsed.dt.date.value_counts().sort_index()
    expected_block = (((time_parsed.dt.total_seconds() // 900).astype("Int64") + 95) % 96) + 1

    column_profile = pd.DataFrame(
        {
            "column": df.columns,
            "dtype": [str(dtype) for dtype in df.dtypes],
            "non_null_count": df.notna().sum().values,
            "missing_count": df.isna().sum().values,
            "missing_pct": (df.isna().mean().mul(100).round(4)).values,
            "unique_count": df.nunique(dropna=False).values,
        }
    )

    numeric_columns = df.select_dtypes(include="number").columns.tolist()
    numeric_summary = (
        df[numeric_columns]
        .describe(percentiles=[0.25, 0.5, 0.75])
        .T.reset_index()
        .rename(columns={"index": "column"})
        .round(4)
    )

    q1 = df["demand"].quantile(0.25)
    q3 = df["demand"].quantile(0.75)
    iqr = q3 - q1
    lower_bound = q1 - 1.5 * iqr
    upper_bound = q3 + 1.5 * iqr
    demand_outliers = df[(df["demand"] < lower_bound) | (df["demand"] > upper_bound)].copy()

    summary = {
        "dataset_name": INPUT_FILE.name,
        "rows": int(len(df)),
        "columns": int(len(df.columns)),
        "date_range": {
            "datetime_min": str(datetime_parsed.min()),
            "datetime_max": str(datetime_parsed.max()),
            "date_min": str(date_parsed.min()),
            "date_max": str(date_parsed.max()),
        },
        "quality_checks": {
            "fully_duplicated_rows": int(df.duplicated().sum()),
            "duplicate_datetime_rows": int(df.duplicated(subset=["datetime"]).sum()),
            "missing_values_total": int(df.isna().sum().sum()),
            "datetime_parse_failures": int(datetime_parsed.isna().sum()),
            "date_parse_failures": int(date_parsed.isna().sum()),
            "time_parse_failures": int(time_parsed.isna().sum()),
            "entrydatetime_parse_failures": int(entry_time_parsed.isna().sum()),
            "negative_datetime_steps_in_original_order": int(datetime_parsed.diff().lt(pd.Timedelta(0)).sum()),
            "invalid_block_range_rows": int((~df["block"].between(1, 96)).sum()),
            "datetime_date_mismatches": int((datetime_parsed.dt.normalize() != date_parsed).sum()),
            "datetime_time_mismatches": int(((datetime_parsed - datetime_parsed.dt.normalize()) != time_parsed).sum()),
            "time_block_mismatches": int((expected_block != df["block"]).sum()),
            "days_with_unexpected_record_count": int((daily_counts != 96).sum()),
            "zero_demand_rows": int((df["demand"] == 0).sum()),
            "negative_demand_rows": int((df["demand"] < 0).sum()),
            "demand_iqr_outlier_rows": int(len(demand_outliers)),
        },
        "record_count_per_day": {
            "expected_records_per_day": 96,
            "minimum_records_in_a_day": int(daily_counts.min()),
            "maximum_records_in_a_day": int(daily_counts.max()),
        },
        "interval_distribution": diff_counts.head(10).to_dict(),
        "demand_statistics": {
            "mean": round(float(df["demand"].mean()), 4),
            "median": round(float(df["demand"].median()), 4),
            "std_dev": round(float(df["demand"].std()), 4),
            "min": round(float(df["demand"].min()), 4),
            "max": round(float(df["demand"].max()), 4),
            "iqr_lower_bound": round(float(lower_bound), 4),
            "iqr_upper_bound": round(float(upper_bound), 4),
        },
    }

    return summary, column_profile, numeric_summary


def write_outputs(
    summary: dict,
    column_profile: pd.DataFrame,
    numeric_summary: pd.DataFrame,
    df: pd.DataFrame,
) -> None:
    OUTPUT_DIR.mkdir(exist_ok=True)

    summary_path = OUTPUT_DIR / "descriptive_quality_summary.json"
    column_profile_path = OUTPUT_DIR / "column_profile.csv"
    numeric_summary_path = OUTPUT_DIR / "numeric_summary.csv"
    daily_counts_path = OUTPUT_DIR / "daily_record_counts.csv"
    markdown_path = OUTPUT_DIR / "descriptive_quality_report.md"

    summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    column_profile.to_csv(column_profile_path, index=False)
    numeric_summary.to_csv(numeric_summary_path, index=False)

    datetime_parsed = pd.to_datetime(df["datetime"], format="%d-%m-%Y %H:%M", errors="coerce")
    daily_counts = (
        datetime_parsed.dt.date.value_counts().sort_index().rename_axis("date").reset_index(name="record_count")
    )
    daily_counts.to_csv(daily_counts_path, index=False)

    report_lines = [
        "# Descriptive Data Quality Report",
        "",
        f"- Dataset: `{summary['dataset_name']}`",
        f"- Rows: `{summary['rows']}`",
        f"- Columns: `{summary['columns']}`",
        f"- Datetime range: `{summary['date_range']['datetime_min']}` to `{summary['date_range']['datetime_max']}`",
        "",
        "## Key Findings",
        f"- Missing values: `{summary['quality_checks']['missing_values_total']}`",
        f"- Fully duplicated rows: `{summary['quality_checks']['fully_duplicated_rows']}`",
        f"- Duplicate `datetime` rows: `{summary['quality_checks']['duplicate_datetime_rows']}`",
        f"- Parsing failures (`datetime`, `date`, `time`, `entrydatetime`): "
        f"`{summary['quality_checks']['datetime_parse_failures']}`, "
        f"`{summary['quality_checks']['date_parse_failures']}`, "
        f"`{summary['quality_checks']['time_parse_failures']}`, "
        f"`{summary['quality_checks']['entrydatetime_parse_failures']}`",
        f"- `datetime` vs `date` mismatches: `{summary['quality_checks']['datetime_date_mismatches']}`",
        f"- `datetime` vs `time` mismatches: `{summary['quality_checks']['datetime_time_mismatches']}`",
        f"- `block` values outside 1-96: `{summary['quality_checks']['invalid_block_range_rows']}`",
        f"- `time` vs `block` mismatches: `{summary['quality_checks']['time_block_mismatches']}`",
        f"- Original-order backward datetime jumps: `{summary['quality_checks']['negative_datetime_steps_in_original_order']}`",
        f"- Days with unexpected record counts: `{summary['quality_checks']['days_with_unexpected_record_count']}`",
        f"- Zero/negative demand rows: `{summary['quality_checks']['zero_demand_rows']}` / `{summary['quality_checks']['negative_demand_rows']}`",
        f"- Demand IQR outliers: `{summary['quality_checks']['demand_iqr_outlier_rows']}`",
        "",
        "## Demand Summary",
        f"- Mean: `{summary['demand_statistics']['mean']}`",
        f"- Median: `{summary['demand_statistics']['median']}`",
        f"- Std. dev.: `{summary['demand_statistics']['std_dev']}`",
        f"- Min/Max: `{summary['demand_statistics']['min']}` / `{summary['demand_statistics']['max']}`",
        "",
        "## Files Generated",
        "- `descriptive_quality_summary.json`",
        "- `column_profile.csv`",
        "- `numeric_summary.csv`",
        "- `daily_record_counts.csv`",
        "- `descriptive_quality_report.md`",
    ]
    markdown_path.write_text("\n".join(report_lines), encoding="utf-8")


def main() -> None:
    df = load_dataset(INPUT_FILE)
    summary, column_profile, numeric_summary = build_summary(df)
    write_outputs(summary, column_profile, numeric_summary, df)

    print("Descriptive data quality analysis completed.")
    print(f"Input file: {INPUT_FILE.name}")
    print(f"Rows: {summary['rows']}, Columns: {summary['columns']}")
    print(
        "Missing values total: "
        f"{summary['quality_checks']['missing_values_total']}, "
        f"duplicate rows: {summary['quality_checks']['fully_duplicated_rows']}, "
        f"time-block mismatches: {summary['quality_checks']['time_block_mismatches']}"
    )
    print(f"Report folder: {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
