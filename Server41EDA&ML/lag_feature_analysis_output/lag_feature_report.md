# Lag Feature Analysis Report

- Dataset: `demo.xslx`
- Rows after lag creation: `172632`
- Rows dropped because lag history was unavailable: `672`
- Split: `chronological 80/20 split`
- Base time-feature model R2: `0.689617`, MAE: `114.315828`
- Lag-feature model R2: `0.999065`, MAE: `5.412749`
- MAE reduction from lag features: `108.903079`
- RMSE reduction from lag features: `136.907862`
- R2 gain from lag features: `0.309448`
- Most important feature in lag model: `lag_15min`

## Files Generated
- `lag_feature_summary.json`
- `lag_feature_importance.csv`
- `lag_correlations.csv`
- `lag_sample_predictions.csv`
- `largest_lag_model_errors.csv`
- `actual_vs_lag_prediction.png`
- `lag_feature_report.md`