from __future__ import annotations

from pathlib import Path
import json

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st


BASE_DIR = Path(__file__).resolve().parent
DATA_FILE = BASE_DIR / "demo.xslx"


st.set_page_config(
    page_title="Demand Intelligence Dashboard",
    page_icon="chart_with_upwards_trend",
    layout="wide",
    initial_sidebar_state="expanded",
)


def read_json(path: Path) -> dict:
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return {}


@st.cache_data(show_spinner=False)
def load_data() -> pd.DataFrame:
    df = pd.read_csv(DATA_FILE, sep="\t")
    df["datetime"] = pd.to_datetime(df["datetime"], format="%d-%m-%Y %H:%M", errors="coerce")
    df["demand"] = pd.to_numeric(df["demand"], errors="coerce")
    df = df.dropna(subset=["datetime", "demand"]).sort_values("datetime").reset_index(drop=True)
    df["hour"] = df["datetime"].dt.hour
    df["month"] = df["datetime"].dt.month
    df["year"] = df["datetime"].dt.year
    df["day_of_week"] = df["datetime"].dt.day_name()
    df["date"] = df["datetime"].dt.date
    df["is_weekend"] = df["datetime"].dt.dayofweek >= 5
    return df


@st.cache_data(show_spinner=False)
def load_outputs() -> dict:
    return {
        "timestamp": read_json(BASE_DIR / "timestamp_data_quality_output" / "timestamp_data_quality_summary.json"),
        "descriptive": read_json(BASE_DIR / "descriptive_data_quality_output" / "descriptive_quality_summary.json"),
        "inferential": read_json(BASE_DIR / "inferential_data_quality_output" / "inferential_quality_summary.json"),
        "classification": read_json(BASE_DIR / "classification_output" / "classification_metrics.json"),
        "regression": read_json(BASE_DIR / "regression_output" / "regression_metrics.json"),
        "bimulti": read_json(BASE_DIR / "bivariate_multivariate_output" / "bivariate_multivariate_summary.json"),
        "lag": read_json(BASE_DIR / "lag_feature_analysis_output" / "lag_feature_summary.json"),
    }


@st.cache_data(show_spinner=False)
def load_csv(path: str) -> pd.DataFrame:
    file_path = BASE_DIR / path
    if file_path.exists():
        return pd.read_csv(file_path)
    return pd.DataFrame()


def apply_styles() -> None:
    st.markdown(
        """
        <style>
        :root {
            --ink: #18211f;
            --muted: #60706a;
            --mint: #12a886;
            --coral: #f05d4f;
            --amber: #f2a93b;
            --blue: #3867d6;
            --paper: #f7f4ee;
            --panel: rgba(255, 255, 255, 0.78);
            --line: rgba(24, 33, 31, 0.13);
        }
        .stApp {
            background:
                linear-gradient(135deg, rgba(18,168,134,.16), rgba(240,93,79,.10) 42%, rgba(56,103,214,.12)),
                radial-gradient(circle at top left, rgba(242,169,59,.22), transparent 32%),
                var(--paper);
            color: var(--ink);
        }
        [data-testid="stSidebar"] {
            background: rgba(24, 33, 31, 0.92);
        }
        [data-testid="stSidebar"] * {
            color: #f7f4ee;
        }
        .hero {
            padding: 28px 30px;
            border: 1px solid var(--line);
            background: linear-gradient(120deg, rgba(255,255,255,.88), rgba(255,255,255,.58));
            box-shadow: 0 18px 45px rgba(24,33,31,.10);
            margin-bottom: 18px;
        }
        .hero h1 {
            font-size: 42px;
            line-height: 1.05;
            margin: 0 0 8px 0;
            color: var(--ink);
        }
        .hero p {
            margin: 0;
            color: var(--muted);
            font-size: 17px;
        }
        .insight {
            padding: 18px 20px;
            background: var(--panel);
            border: 1px solid var(--line);
            border-left: 5px solid var(--mint);
            margin: 10px 0;
        }
        .manager-note {
            padding: 22px;
            background: #18211f;
            color: #f7f4ee;
            border-left: 6px solid var(--amber);
            font-size: 18px;
            line-height: 1.6;
        }
        div[data-testid="stMetric"] {
            background: rgba(255,255,255,.72);
            border: 1px solid var(--line);
            padding: 16px;
            box-shadow: 0 10px 28px rgba(24,33,31,.06);
        }
        h2, h3 {
            color: var(--ink);
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def metric_row(items: list[tuple[str, str, str | None]]) -> None:
    columns = st.columns(len(items))
    for col, (label, value, delta) in zip(columns, items):
        col.metric(label, value, delta)


def demand_line_chart(df: pd.DataFrame) -> go.Figure:
    daily = df.groupby("date", as_index=False)["demand"].mean()
    fig = px.line(
        daily,
        x="date",
        y="demand",
        title="Daily Average Demand Trend",
        color_discrete_sequence=["#12a886"],
    )
    fig.update_layout(height=420, margin=dict(l=20, r=20, t=55, b=20))
    return fig


def grouped_bar(df: pd.DataFrame, group_col: str, title: str, color: str) -> go.Figure:
    grouped = df.groupby(group_col, as_index=False)["demand"].mean()
    fig = px.bar(grouped, x=group_col, y="demand", title=title, color_discrete_sequence=[color])
    fig.update_layout(height=390, margin=dict(l=20, r=20, t=55, b=20))
    return fig


def overview_tab(df: pd.DataFrame, outputs: dict) -> None:
    timestamp = outputs["timestamp"]
    regression = outputs["regression"].get("model_metrics", {})
    lag = outputs["lag"].get("lag_feature_model_metrics", {})

    metric_row(
        [
            ("Rows", f"{len(df):,}", None),
            ("Interval", "15 minutes", "0 missing timestamps"),
            ("Demand Avg", f"{df['demand'].mean():,.2f}", None),
            ("Best R2", f"{lag.get('r2', 0):.4f}", "Lag model"),
        ]
    )

    st.plotly_chart(demand_line_chart(df), use_container_width=True)

    left, right = st.columns([1.1, 0.9])
    with left:
        st.markdown("### Demand Shape")
        st.plotly_chart(grouped_bar(df, "hour", "Average Demand by Hour", "#3867d6"), use_container_width=True)
    with right:
        st.markdown("### Project Health")
        st.markdown(
            f"""
            <div class="insight">
            <b>Data quality:</b> clean timestamp grid with
            {timestamp.get('missing_timestamp_count_for_15min_grid', 0)} missing timestamps,
            {timestamp.get('duplicate_timestamp_rows', 0)} duplicate timestamps, and no null demand rows.
            </div>
            <div class="insight">
            <b>Standard regression:</b> R2 {regression.get('r2', 0):.4f}, MAE {regression.get('mae', 0):.2f}.
            </div>
            <div class="insight">
            <b>Lag forecasting:</b> R2 {lag.get('r2', 0):.4f}, MAE {lag.get('mae', 0):.2f}. Previous demand is the strongest signal.
            </div>
            """,
            unsafe_allow_html=True,
        )


def data_quality_tab(outputs: dict) -> None:
    timestamp = outputs["timestamp"]
    demand = timestamp.get("demand_checks", {})
    metric_row(
        [
            ("Missing Timestamps", str(timestamp.get("missing_timestamp_count_for_15min_grid", 0)), None),
            ("Duplicate Timestamps", str(timestamp.get("duplicate_timestamp_rows", 0)), None),
            ("Null Demand", str(demand.get("null_demand_rows", 0)), None),
            ("Incomplete Days", str(timestamp.get("incomplete_day_count", 0)), "final day only"),
        ]
    )

    left, right = st.columns(2)
    with left:
        interval_df = load_csv("timestamp_data_quality_output/interval_distribution.csv")
        if not interval_df.empty:
            fig = px.bar(
                interval_df,
                x="interval",
                y="count",
                title="Actual Timestamp Interval Distribution",
                color_discrete_sequence=["#12a886"],
            )
            st.plotly_chart(fig, use_container_width=True)
    with right:
        null_df = load_csv("timestamp_data_quality_output/null_counts.csv")
        if not null_df.empty:
            fig = px.bar(
                null_df,
                x="column",
                y="null_count",
                title="Null Count by Column",
                color_discrete_sequence=["#f05d4f"],
            )
            st.plotly_chart(fig, use_container_width=True)

    incomplete = load_csv("timestamp_data_quality_output/incomplete_days.csv")
    st.markdown("### Incomplete Days")
    st.dataframe(incomplete, use_container_width=True, hide_index=True)


def patterns_tab(df: pd.DataFrame) -> None:
    col1, col2 = st.columns(2)
    with col1:
        st.plotly_chart(grouped_bar(df, "block", "Average Demand by Block", "#f2a93b"), use_container_width=True)
        st.plotly_chart(grouped_bar(df, "month", "Average Demand by Month", "#12a886"), use_container_width=True)
    with col2:
        weekday_order = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
        weekday = df.groupby("day_of_week", as_index=False)["demand"].mean()
        weekday["day_of_week"] = pd.Categorical(weekday["day_of_week"], weekday_order, ordered=True)
        weekday = weekday.sort_values("day_of_week")
        fig = px.bar(
            weekday,
            x="day_of_week",
            y="demand",
            title="Average Demand by Day of Week",
            color_discrete_sequence=["#3867d6"],
        )
        st.plotly_chart(fig, use_container_width=True)

        corr = load_csv("bivariate_multivariate_output/bivariate_correlations.csv")
        if not corr.empty:
            fig = px.bar(
                corr,
                x="feature",
                y="pearson_correlation",
                title="Bivariate Correlation with Demand",
                color="pearson_correlation",
                color_continuous_scale=["#f05d4f", "#f7f4ee", "#12a886"],
            )
            st.plotly_chart(fig, use_container_width=True)


def models_tab(outputs: dict) -> None:
    classification = outputs["classification"]
    regression = outputs["regression"]
    bimulti = outputs["bimulti"].get("multivariate_analysis", {})

    metric_row(
        [
            ("Classification Accuracy", f"{classification.get('accuracy', 0) * 100:.2f}%", None),
            ("Classification Macro F1", f"{classification.get('macro_f1', 0):.4f}", None),
            ("Regression R2", f"{regression.get('model_metrics', {}).get('r2', 0):.4f}", None),
            ("Regression MAPE", f"{regression.get('model_metrics', {}).get('mape_pct', 0):.2f}%", None),
        ]
    )

    col1, col2 = st.columns(2)
    with col1:
        confusion = load_csv("classification_output/confusion_matrix.csv")
        if not confusion.empty:
            confusion = confusion.rename(columns={confusion.columns[0]: "actual"})
            matrix = confusion.set_index("actual")
            fig = px.imshow(
                matrix,
                text_auto=True,
                title="Classification Confusion Matrix",
                color_continuous_scale="YlGnBu",
            )
            st.plotly_chart(fig, use_container_width=True)
    with col2:
        importance = load_csv("regression_output/feature_importance.csv")
        if not importance.empty:
            fig = px.bar(
                importance,
                x="importance_mean",
                y="feature",
                orientation="h",
                title="Regression Feature Importance",
                color_discrete_sequence=["#f2a93b"],
            )
            fig.update_yaxes(categoryorder="total ascending")
            st.plotly_chart(fig, use_container_width=True)

    st.markdown("### Multivariate Model Comparison")
    st.dataframe(
        pd.DataFrame(
            [
                {"model": "Linear Regression", **bimulti.get("linear_regression_metrics", {})},
                {"model": "Random Forest", **bimulti.get("random_forest_metrics", {})},
            ]
        ),
        use_container_width=True,
        hide_index=True,
    )


def lag_tab(outputs: dict) -> None:
    lag = outputs["lag"]
    base = lag.get("base_time_feature_model_metrics", {})
    lag_metrics = lag.get("lag_feature_model_metrics", {})
    improvement = lag.get("improvement_from_lag_features", {})

    metric_row(
        [
            ("Base R2", f"{base.get('r2', 0):.4f}", None),
            ("Lag R2", f"{lag_metrics.get('r2', 0):.4f}", f"+{improvement.get('r2_gain', 0):.4f}"),
            ("Base MAE", f"{base.get('mae', 0):.2f}", None),
            ("Lag MAE", f"{lag_metrics.get('mae', 0):.2f}", f"-{improvement.get('mae_reduction', 0):.2f}"),
        ]
    )

    col1, col2 = st.columns(2)
    with col1:
        lag_corr = load_csv("lag_feature_analysis_output/lag_correlations.csv")
        if not lag_corr.empty:
            fig = px.bar(
                lag_corr,
                x="correlation_with_demand",
                y="lag_feature",
                orientation="h",
                title="Lag Correlation with Demand",
                color_discrete_sequence=["#12a886"],
            )
            fig.update_yaxes(categoryorder="total ascending")
            st.plotly_chart(fig, use_container_width=True)
    with col2:
        lag_importance = load_csv("lag_feature_analysis_output/lag_feature_importance.csv")
        if not lag_importance.empty:
            fig = px.bar(
                lag_importance.head(12),
                x="importance_mean",
                y="feature",
                orientation="h",
                title="Lag Model Feature Importance",
                color_discrete_sequence=["#3867d6"],
            )
            fig.update_yaxes(categoryorder="total ascending")
            st.plotly_chart(fig, use_container_width=True)

    predictions = load_csv("lag_feature_analysis_output/lag_sample_predictions.csv")
    if not predictions.empty:
        predictions["datetime"] = pd.to_datetime(predictions["datetime"])
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=predictions["datetime"], y=predictions["actual_demand"], name="Actual", mode="lines"))
        fig.add_trace(go.Scatter(x=predictions["datetime"], y=predictions["lag_model_prediction"], name="Lag prediction", mode="lines"))
        fig.update_layout(title="Actual vs Lag Prediction Sample", height=420)
        st.plotly_chart(fig, use_container_width=True)


def summary_tab() -> None:
    summary_path = BASE_DIR / "final_executive_summary.md"
    if summary_path.exists():
        summary_text = summary_path.read_text(encoding="utf-8")
    else:
        summary_text = "Final executive summary is not available yet."

    with st.expander("Full executive summary", expanded=True):
        st.markdown(summary_text)


def main() -> None:
    apply_styles()
    df = load_data()
    outputs = load_outputs()

    st.sidebar.title("Demand EDA")
    date_min = df["datetime"].min().date()
    date_max = df["datetime"].max().date()
    selected_range = st.sidebar.date_input(
        "Date range",
        value=(date_min, date_max),
        min_value=date_min,
        max_value=date_max,
    )

    filtered = df
    if isinstance(selected_range, tuple) and len(selected_range) == 2:
        start, end = selected_range
        filtered = df[(df["datetime"].dt.date >= start) & (df["datetime"].dt.date <= end)]

    st.markdown(
        """
        <div class="hero">
            <h1>Demand Intelligence Dashboard</h1>
            <p>EDA, data quality, bivariate and multivariate patterns, ML results, and lag-feature forecasting in one presentation-ready Streamlit app.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    tabs = st.tabs(
        [
            "Overview",
            "Data Quality",
            "Patterns",
            "Models",
            "Lag Forecasting",
            "Manager Summary",
        ]
    )

    with tabs[0]:
        overview_tab(filtered, outputs)
    with tabs[1]:
        data_quality_tab(outputs)
    with tabs[2]:
        patterns_tab(filtered)
    with tabs[3]:
        models_tab(outputs)
    with tabs[4]:
        lag_tab(outputs)
    with tabs[5]:
        summary_tab()


if __name__ == "__main__":
    main()
