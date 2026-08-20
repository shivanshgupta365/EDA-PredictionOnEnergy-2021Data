# Inferential Data Quality Report

- Dataset: `demo.xslx`
- Rows analysed: `173304`
- Datetime range: `2021-01-01 00:00:00` to `2025-12-11 05:45:00`

## Key Statistical Findings
- 95% CI for mean demand: `1351.3421` to `1353.9582`
- Normality rejected on sampled demand values: Shapiro p-value `1.01673e-09`, D'Agostino p-value `1.57937e-16`
- Weekday vs weekend demand differs significantly: Welch p-value `0`, Cohen's d `0.356977`
- Hour-of-day means differ significantly: ANOVA p-value `0`, eta-squared `0.364754`
- Hourly variances are not homogeneous: Levene p-value `3.82341e-181`
- Daily average demand shows a positive trend: slope/day `0.195298`, p-value `4.77459e-112`
- Strong serial dependence exists: ADF p-value `5.07257e-27`, anomaly rows by |z| > 3: `28`

## Files Generated
- `inferential_quality_summary.json`
- `ljung_box_results.csv`
- `hourly_demand_summary.csv`
- `zscore_anomalies.csv`
- `inferential_quality_report.md`