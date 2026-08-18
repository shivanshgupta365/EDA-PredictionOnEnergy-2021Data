# Timestamp and Missing Data Quality Checks

- Dataset: `demo.xslx`
- Rows: `173304`
- Datetime range: `2021-01-01 00:00:00` to `2025-12-11 05:45:00`
- Expected interval checked: `0 days 00:15:00`
- Most common actual interval: `0 days 00:15:00`
- Missing timestamps on 15-minute grid: `0`
- Duplicate timestamp rows: `0`
- Irregular interval rows against 15-minute rule: `0`
- Incomplete days: `1`
- Total null cells: `0`
- Null demand rows: `0`
- Non-numeric demand rows: `0`
- Zero demand rows: `0`
- Negative demand rows: `0`
- Demand min/max: `519.28` / `2268.14`

## Files Generated
- `timestamp_data_quality_summary.json`
- `interval_distribution.csv`
- `missing_timestamps_15min_grid.csv`
- `duplicate_timestamp_rows.csv`
- `irregular_intervals.csv`
- `daily_record_counts.csv`
- `incomplete_days.csv`
- `null_counts.csv`