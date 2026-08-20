# EDA-PredictionOnEnergy-2021Data-Server41

# Demand Intelligence EDA and Prediction Dashboard

This project is an end-to-end analysis of a demand time-series dataset. The work covers data quality checks, EDA, timestamp validation, pattern analysis, classification, regression, lag-feature analysis, and a Streamlit dashboard for presenting the findings.

The source file is named `demo.xslx`, but it is actually a tab-separated text file. Because of that, the analysis reads it using `pandas.read_csv(..., sep="\t")`.

## What This Project Does

The project answers these main questions:

- Is the data clean and usable?
- Are there missing timestamps or null values?
- What is the actual time interval of the data?
- How does demand change by hour, block, weekday, month, year, and season?
- Which variables are most related to demand?
- Can demand be classified into low, medium, and high categories?
- Can actual demand values be predicted?
- Do previous demand values improve forecasting?

## Main Work Completed

- Descriptive data quality checks
- Inferential data quality checks
- Missing/null value checks
- Timestamp continuity checks
- 15-minute interval validation
- Demand validity checks
- Bivariate analysis
- Multivariate analysis
- Daily, weekly, monthly, yearly, and season-based pattern analysis
- Classification model
- Regression model
- Lag-feature forecasting analysis
- Jupyter notebook version of the EDA
- Streamlit dashboard for visual presentation

## Key Findings

The dataset is generally clean and suitable for time-series analysis.

- Total records: `173,304`
- Time interval: `15 minutes`
- Missing timestamps: `0`
- Duplicate timestamps: `0`
- Null values: `0`
- Zero demand rows: `0`
- Negative demand rows: `0`
- Demand range: `519.28` to `2268.14`
- One incomplete final day: `2025-12-11`, where data is available only up to `05:45`

Demand is strongly time-dependent. Important patterns were found across:

- 15-minute blocks
- Hours of the day
- Days of the week
- Months
- Years
- Indian seasons: Winter, Summer, Monsoon, and Post-Monsoon

Season-wise average demand:

- Winter: `1138.771`
- Summer: `1482.145`
- Monsoon: `1352.596`
- Post-Monsoon: `1395.452`

Summer has the highest average demand in this dataset.

## Model Results

Classification was used to group demand into `low`, `medium`, and `high` categories.

- Classification accuracy: `74.50%`
- Macro F1 score: `0.7187`

Regression was used to predict actual demand values.

- Regression R2: `0.6977`
- Regression MAE: `112.64`
- Regression RMSE: `143.27`
- Regression MAPE: `7.99%`

Lag-feature analysis gave the strongest result. Previous demand values, especially the demand from 15 minutes ago, were highly useful for prediction.

- Lag-feature model R2: `0.9991`
- Lag-feature model MAE: `5.41`
- Strongest lag feature: `lag_15min`
- `lag_15min` correlation with demand: `0.9974`

This shows that recent demand history is the strongest signal for forecasting.

## Dashboard Sections

The Streamlit dashboard contains:

- EDA Notebook
- Overview
- Data Quality
- Patterns
- Models
- Lag Forecasting
- Work Done Process

The dashboard is designed so the analysis can be explained visually instead of only through raw code and CSV files.

## Work Done Process

The work started with loading and understanding the dataset. Then data quality checks were performed to confirm null values, duplicate rows, duplicate timestamps, timestamp continuity, interval consistency, and demand validity.

After that, EDA was done using descriptive statistics, distribution plots, boxplots, trend charts, and grouped demand analysis. Bivariate analysis checked one variable at a time against demand, while multivariate analysis checked how multiple variables work together.

Prediction work was done in two ways. First, demand was classified into low, medium, and high categories. Then regression was used to predict actual demand values. Finally, lag features were added to check whether previous demand values improve forecasting. The lag-feature model performed best, confirming that recent demand history is the most important signal.

The final result is a complete EDA and prediction workflow with notebook outputs, generated reports, model results, and a Streamlit dashboard.


## Project Files

Important files:

- `EDA_Demand_Analysis_Notebook.ipynb` - main EDA notebook
- `EDA_Demand_Analysis_Notebook_executed.ipynb` - executed notebook with outputs
- `streamlit_app.py` - Streamlit dashboard
- `DataQaulityDescriptive.py` - descriptive data quality analysis
- `DataQualityInferential.py` - inferential data quality analysis
- `timestamp_data_quality_checks.py` - timestamp and missing-data checks
- `bivariate_multivariate_analysis.py` - bivariate and multivariate analysis
- `classification.py` - classification model
- `regression.py` - regression model
- `lag_feature_analysis.py` - lag-feature forecasting analysis
- `final_executive_summary.md` - final work summary

Output folders:

- `descriptive_data_quality_output/`
- `inferential_data_quality_output/`
- `timestamp_data_quality_output/`
- `bivariate_multivariate_output/`
- `classification_output/`
- `regression_output/`
- `lag_feature_analysis_output/`

## Deploying the Dashboard

This repository contains two dashboard entry points:

- **Vercel:** deploy the repository root. Vercel serves the static, interactive
  dashboard at `/` using the generated CSV and JSON analysis outputs. It does
  not run `streamlit_app.py`.
- **Streamlit:** run the Python dashboard on a platform that supports a
  persistent Python web process, such as Streamlit Community Cloud:
  `streamlit run "Server41EDA&ML/streamlit_app.py"`.

The root `vercel.json` is intentional: the visual dashboard and its data files
live in `Server41EDA&ML/`, while the GitHub repository root is one level above.
It rewrites `/` and each dashboard asset request to that directory so a Vercel
deployment made from the repository root works correctly.
