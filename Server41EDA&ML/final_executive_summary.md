# Final Executive Summary

## Project Overview

The project analyses `demo.xslx`, a time-series demand dataset with 173,304 records from `2021-01-01 00:00:00` to `2025-12-11 05:45:00`. Although the file extension is `.xslx`, the data is actually tab-separated text, so all analysis scripts load it accordingly.

## Data Quality Summary

The dataset is generally clean and suitable for analysis.

- Total rows: 173,304
- Total columns: 6
- Missing/null cells: 0
- Duplicate timestamps: 0
- Missing timestamps on 15-minute grid: 0
- Actual data interval: 15 minutes
- Invalid demand values: 0
- Zero demand rows: 0
- Negative demand rows: 0
- Demand range: 519.28 to 2268.14
- One incomplete final day: `2025-12-11` has 24 records instead of 96

## EDA and Pattern Findings

The analysis covered descriptive quality, inferential quality, bivariate analysis, multivariate analysis, classification, regression, timestamp checks, and lag-feature analysis.

Important demand patterns found:

- Demand follows a strong 15-minute time-series pattern.
- Demand varies significantly by block and hour.
- Weekday and weekend demand are statistically different.
- Demand changes across day of week and day of year.
- Seasonal and yearly effects are present.
- Recent demand values are the strongest predictors of future demand.

## Bivariate and Multivariate Findings

Bivariate analysis studied one variable at a time against demand. The strongest single relationships were:

- `hour` correlation with demand: 0.386919
- `block` correlation with demand: 0.386689
- `year` correlation with demand: 0.354379
- `is_weekend` correlation with demand: -0.154944
- `day_of_week` correlation with demand: -0.129996

Multivariate analysis studied how multiple features together explain demand.

- Linear regression R2: -0.179243
- Random Forest R2: 0.65791
- Random Forest MAE: 119.775714
- Most important multivariate features: `block`, `day_of_year`, and `day_of_week`

This shows that demand behavior is not purely linear. Tree-based models capture demand patterns better.

## Classification Summary

Classification was used to group demand into `low`, `medium`, and `high` categories.

- Model target: low, medium, high demand class
- Split method: chronological 80/20 split
- Accuracy: 74.50%
- Macro F1 score: 0.7187
- Most useful features: `block`, `day_of_year`, and `day_of_week`

## Regression Summary

Regression was used to predict actual numeric demand.

- Model: HistGradientBoostingRegressor
- Split method: chronological 80/20 split
- MAE: 112.63809
- RMSE: 143.265044
- R2: 0.697744
- MAPE: 7.990385%
- Baseline MAE: 239.630661

The regression model performs much better than a simple baseline mean model.

## Lag Feature Analysis Summary

Lag-feature analysis checked whether previous demand values help predict future demand.

Lag features created:

- 15 minutes previous demand
- 30 minutes previous demand
- 1 hour previous demand
- 2 hours previous demand
- 6 hours previous demand
- 12 hours previous demand
- 1 day previous demand
- 1 week previous demand
- Rolling means and rolling standard deviation

Main results:

- Base time-feature model R2: 0.689617
- Lag-feature model R2: 0.999065
- Base MAE: 114.315828
- Lag model MAE: 5.412749
- MAE improvement: 108.903079
- Most important feature: `lag_15min`
- `lag_15min` correlation with demand: 0.997388
- `lag_30min` correlation with demand: 0.991162

This confirms that demand is highly dependent on recent previous demand values. Lag features are extremely useful for forecasting.

## Final Conclusion

The dataset is clean, regularly spaced at 15-minute intervals, and appropriate for time-series demand analysis. The main business insight is that demand is strongly time-dependent. Block, hour, day of year, weekday pattern, and recent demand history are the most important drivers.

For prediction, lag-based forecasting performs best because the current demand is highly related to recent previous demand. The project is now ready for manager review, model discussion, and possible next steps such as dashboard creation, deployment, or advanced time-series forecasting.

## Manager Update

I have completed the main EDA and modelling work on the demand dataset.

First, I checked the basic data quality. The data is clean overall: there are no null values, no duplicate timestamps, no missing timestamps, and the records are consistently available at 15-minute intervals. Demand values are also valid, with no zero, negative, or non-numeric demand entries. The only small point to note is that the last day, `2025-12-11`, is incomplete because the data is available only up to `05:45`.

After that, I studied demand patterns using bivariate and multivariate analysis. Demand changes clearly by block, hour, day of week, and season. The models also show that `block`, `day_of_year`, and `day_of_week` are important factors.

I also built classification and regression models. Classification groups demand into low, medium, and high categories and gives around 74.5% accuracy. Regression predicts actual demand values and gives an R2 of around 0.70 with around 8% MAPE.

The most useful part is the lag-feature analysis. When previous demand values are added, especially the demand from 15 minutes ago, prediction accuracy improves a lot. The lag model reaches around 0.999 R2 and reduces MAE to around 5.41. This means recent demand history is the strongest signal for forecasting.

Finally, I created a Streamlit dashboard so all the results can be reviewed visually in one place.
