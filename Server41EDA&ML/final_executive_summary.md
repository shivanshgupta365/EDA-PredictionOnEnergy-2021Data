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

## Work Done Process

The work started with loading and understanding the demand dataset. Since `demo.xslx` is not a real Excel file and is actually tab-separated text, the data was loaded using a tab-separated reader.

Next, data quality checks were performed. This included checking null values, duplicate rows, duplicate timestamps, timestamp parsing, missing timestamps, interval consistency, and demand validity. The dataset was found to be clean overall, with no null values, no duplicate timestamps, no missing timestamps, and a regular 15-minute interval. The only small issue found was that the last day, `2025-12-11`, is incomplete because data is available only up to `05:45`.

After the quality checks, descriptive EDA was done to understand the basic structure of the data. This included row and column counts, data types, demand summary statistics, demand distribution, boxplot, and outlier checks.

Then timestamp and time-based patterns were analysed. Demand was studied by block, hour, day of week, month, year, and day of year. This helped identify that demand changes strongly with time-based features.

Bivariate analysis was performed by comparing one feature at a time with demand. Correlation and grouped summaries showed that `hour`, `block`, and `year` have strong relationships with demand.

Multivariate analysis was performed to understand how multiple features work together. Correlation matrix, feature importance, mutual information, and model comparison were used. This showed that `block`, `day_of_year`, and `day_of_week` are important combined drivers of demand.

Classification modelling was done by converting demand into low, medium, and high categories. The classification model achieved around 74.5% accuracy.

Regression modelling was done to predict actual numeric demand values. The regression model achieved an R2 of around 0.70 and MAPE of around 8%, which was much better than the baseline mean model.

Lag-feature analysis was done after that. Previous demand values such as 15-minute lag, 30-minute lag, 1-hour lag, 1-day lag, and rolling averages were created. This gave the strongest result: the lag model reached around 0.999 R2 and reduced MAE to around 5.41. This shows that recent demand history is the most important signal for forecasting.

Finally, all outputs were combined into a Streamlit dashboard so the EDA, data quality checks, patterns, model results, lag analysis, and final process summary can be reviewed visually in one place.
