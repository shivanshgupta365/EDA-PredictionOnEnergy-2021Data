from __future__ import annotations

from pathlib import Path
import json

import pandas as pd


BASE_DIR = Path(__file__).resolve().parent
INPUT_FILE = BASE_DIR / "demo.xslx"
OUTPUT_DIR = BASE_DIR / "timestamp_data_quality_output"
EXPECTED_INTERVAL = pd.Timedelta(minutes=15)


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


def main() -> None:
    OUTPUT_DIR.mkdir(exist_ok=True)

    df = load_dataset(INPUT_FILE)
    df["parsed_datetime"] = pd.to_datetime(df["datetime"], format="%d-%m-%Y %H:%M", errors="coerce")
    df["parsed_date"] = pd.to_datetime(df["date"], format="%d-%m-%Y %H:%M", errors="coerce")
    df["parsed_time"] = pd.to_timedelta(df["time"], errors="coerce")
    df["demand_numeric"] = pd.to_numeric(df["demand"], errors="coerce")

    sorted_df = df.sort_values("parsed_datetime").reset_index(drop=True)
    interval_counts = (
        sorted_df["parsed_datetime"].diff().dropna().value_counts().sort_index().rename_axis("interval")
    )
    interval_counts_df = interval_counts.reset_index(name="count")
    interval_counts_df["interval"] = interval_counts_df["interval"].astype(str)

    full_range = pd.date_range(
        start=sorted_df["parsed_datetime"].min(),
        end=sorted_df["parsed_datetime"].max(),
        freq=EXPECTED_INTERVAL,
    )
    actual_timestamps = pd.DatetimeIndex(sorted_df["parsed_datetime"].dropna().unique())
    missing_timestamps = pd.DatetimeIndex(full_range).difference(actual_timestamps)
    duplicate_timestamp_rows = sorted_df[sorted_df.duplicated("parsed_datetime", keep=False)].copy()

    gaps = sorted_df[["parsed_datetime"]].copy()
    gaps["previous_datetime"] = gaps["parsed_datetime"].shift(1)
    gaps["interval"] = gaps["parsed_datetime"] - gaps["previous_datetime"]
    irregular_gaps = gaps[gaps["interval"] != EXPECTED_INTERVAL].dropna().copy()

    daily_counts = (
        sorted_df["parsed_datetime"]
        .dt.date.value_counts()
        .sort_index()
        .rename_axis("date")
        .reset_index(name="record_count")
    )
    incomplete_days = daily_counts[daily_counts["record_count"] != 96].copy()

    null_counts = df.isna().sum().rename_axis("column").reset_index(name="null_count")
    parse_failure_counts = {
        "datetime_parse_failures": int(df["parsed_datetime"].isna().sum()),
        "date_parse_failures": int(df["parsed_date"].isna().sum()),
        "time_parse_failures": int(df["parsed_time"].isna().sum()),
        "demand_numeric_parse_failures": int(df["demand_numeric"].isna().sum()),
    }

    demand_checks = {
        "null_demand_rows": int(df["demand"].isna().sum()),
        "non_numeric_demand_rows": int(df["demand_numeric"].isna().sum()),
        "zero_demand_rows": int((df["demand_numeric"] == 0).sum()),
        "negative_demand_rows": int((df["demand_numeric"] < 0).sum()),
        "minimum_demand": round(float(df["demand_numeric"].min()), 6),
        "maximum_demand": round(float(df["demand_numeric"].max()), 6),
        "average_demand": round(float(df["demand_numeric"].mean()), 6),
    }

    summary = {
        "dataset": INPUT_FILE.name,
        "rows": int(len(df)),
        "columns": int(len(df.columns) - 4),
        "datetime_range": {
            "start": str(sorted_df["parsed_datetime"].min()),
            "end": str(sorted_df["parsed_datetime"].max()),
        },
        "expected_interval": str(EXPECTED_INTERVAL),
        "actual_interval_distribution": interval_counts_df.to_dict(orient="records"),
        "most_common_interval": str(interval_counts.idxmax()),
        "most_common_interval_count": int(interval_counts.max()),
        "missing_timestamp_count_for_15min_grid": int(len(missing_timestamps)),
        "duplicate_timestamp_rows": int(len(duplicate_timestamp_rows)),
        "irregular_interval_rows_against_15min": int(len(irregular_gaps)),
        "incomplete_day_count": int(len(incomplete_days)),
        "null_counts": null_counts.to_dict(orient="records"),
        "parse_failure_counts": parse_failure_counts,
        "demand_checks": demand_checks,
    }

    interval_counts_df.to_csv(OUTPUT_DIR / "interval_distribution.csv", index=False)
    pd.DataFrame({"missing_timestamp": missing_timestamps}).to_csv(
        OUTPUT_DIR / "missing_timestamps_15min_grid.csv", index=False
    )
    duplicate_timestamp_rows.to_csv(OUTPUT_DIR / "duplicate_timestamp_rows.csv", index=False)
    irregular_gaps.to_csv(OUTPUT_DIR / "irregular_intervals.csv", index=False)
    daily_counts.to_csv(OUTPUT_DIR / "daily_record_counts.csv", index=False)
    incomplete_days.to_csv(OUTPUT_DIR / "incomplete_days.csv", index=False)
    null_counts.to_csv(OUTPUT_DIR / "null_counts.csv", index=False)

    (OUTPUT_DIR / "timestamp_data_quality_summary.json").write_text(
        json.dumps(summary, indent=2), encoding="utf-8"
    )

    report = [
        "# Timestamp and Missing Data Quality Checks",
        "",
        f"- Dataset: `{summary['dataset']}`",
        f"- Rows: `{summary['rows']}`",
        f"- Datetime range: `{summary['datetime_range']['start']}` to `{summary['datetime_range']['end']}`",
        f"- Expected interval checked: `{summary['expected_interval']}`",
        f"- Most common actual interval: `{summary['most_common_interval']}`",
        f"- Missing timestamps on 15-minute grid: `{summary['missing_timestamp_count_for_15min_grid']}`",
        f"- Duplicate timestamp rows: `{summary['duplicate_timestamp_rows']}`",
        f"- Irregular interval rows against 15-minute rule: `{summary['irregular_interval_rows_against_15min']}`",
        f"- Incomplete days: `{summary['incomplete_day_count']}`",
        f"- Total null cells: `{int(df.isna().sum().sum())}`",
        f"- Null demand rows: `{demand_checks['null_demand_rows']}`",
        f"- Non-numeric demand rows: `{demand_checks['non_numeric_demand_rows']}`",
        f"- Zero demand rows: `{demand_checks['zero_demand_rows']}`",
        f"- Negative demand rows: `{demand_checks['negative_demand_rows']}`",
        f"- Demand min/max: `{demand_checks['minimum_demand']}` / `{demand_checks['maximum_demand']}`",
        "",
        "## Files Generated",
        "- `timestamp_data_quality_summary.json`",
        "- `interval_distribution.csv`",
        "- `missing_timestamps_15min_grid.csv`",
        "- `duplicate_timestamp_rows.csv`",
        "- `irregular_intervals.csv`",
        "- `daily_record_counts.csv`",
        "- `incomplete_days.csv`",
        "- `null_counts.csv`",
    ]
    (OUTPUT_DIR / "timestamp_data_quality_report.md").write_text("\n".join(report), encoding="utf-8")

    print("Timestamp data quality checks completed.")
    print(f"Most common interval: {summary['most_common_interval']}")
    print(f"Missing timestamps on 15-minute grid: {summary['missing_timestamp_count_for_15min_grid']}")
    print(f"Total null cells: {int(df.isna().sum().sum())}")
    print(f"Report folder: {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
