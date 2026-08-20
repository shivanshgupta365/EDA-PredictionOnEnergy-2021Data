# Bivariate and Multivariate Analysis Report

- Dataset: `demo.xslx`
- Rows analysed: `173304`
- Datetime range: `2021-01-01 00:00:00` to `2025-12-11 05:45:00`

## Bivariate Analysis
- Strongest single correlation with demand: `hour` with Pearson correlation `0.386919`.
- Block vs demand ANOVA p-value: `0`.
- Hour vs demand ANOVA p-value: `0`.
- Day-of-week vs demand ANOVA p-value: `5.87946e-50`.

## Multivariate Analysis
- Linear regression R2: `-0.179243`, MAE: `234.632484`.
- Random forest R2: `0.65791`, MAE: `119.775714`, RMSE: `152.413397`.
- Most important multivariate feature: `block`.

## Files Generated
- `bivariate_multivariate_summary.json`
- `bivariate_correlations.csv`
- `demand_by_block.csv`
- `demand_by_hour.csv`
- `demand_by_day_of_week.csv`
- `demand_by_month.csv`
- `multivariate_correlation_matrix.csv`
- `multivariate_feature_importance.csv`
- `multivariate_mutual_information.csv`
- `pca_explained_variance.csv`
- `multivariate_sample_predictions.csv`
- `average_demand_by_block.png`
- `average_demand_by_hour.png`
- `average_demand_by_month.png`
- `multivariate_correlation_heatmap.png`