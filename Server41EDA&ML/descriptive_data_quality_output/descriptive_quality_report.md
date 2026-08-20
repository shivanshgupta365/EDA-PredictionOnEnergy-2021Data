# Descriptive Data Quality Report

- Dataset: `demo.xslx`
- Rows: `173304`
- Columns: `6`
- Datetime range: `2021-01-01 00:00:00` to `2025-12-11 05:45:00`

## Key Findings
- Missing values: `0`
- Fully duplicated rows: `0`
- Duplicate `datetime` rows: `0`
- Parsing failures (`datetime`, `date`, `time`, `entrydatetime`): `0`, `0`, `0`, `0`
- `datetime` vs `date` mismatches: `0`
- `datetime` vs `time` mismatches: `0`
- `block` values outside 1-96: `0`
- `time` vs `block` mismatches: `52152`
- Original-order backward datetime jumps: `12`
- Days with unexpected record counts: `1`
- Zero/negative demand rows: `0` / `0`
- Demand IQR outliers: `127`

## Demand Summary
- Mean: `1352.6502`
- Median: `1355.47`
- Std. dev.: `277.8383`
- Min/Max: `519.28` / `2268.14`

## Files Generated
- `descriptive_quality_summary.json`
- `column_profile.csv`
- `numeric_summary.csv`
- `daily_record_counts.csv`
- `descriptive_quality_report.md`