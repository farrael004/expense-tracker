import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from scipy import stats
from expense_tracker.storage import load_config, load_transactions


def render_page():
    st.title("Analysis")

    config = load_config()
    people = config["people"]
    all_tags = config["default_tags"]
    transactions = load_transactions()

    if not transactions:
        st.info("No transactions found. Upload data or load dummy data first.")
        return

    df = _build_dataframe(transactions)

    df = _render_filters(df, people, all_tags)

    if df.empty:
        st.warning("No transactions match the current filters.")
        return

    tab1, tab2, tab3 = st.tabs(["Charts", "Insights", "Raw Data"])

    with tab1:
        _render_charts(df)
    with tab2:
        _render_insights(df)
    with tab3:
        st.dataframe(
            df[["date", "description", "amount", "person", "tags_str"]].rename(
                columns={"date": "Date", "description": "Description",
                         "amount": "Amount ($)", "person": "Person", "tags_str": "Tags"}
            ),
            use_container_width=True,
            hide_index=True,
        )


def _build_dataframe(transactions: list[dict]) -> pd.DataFrame:
    df = pd.DataFrame(transactions)
    df["date"] = pd.to_datetime(df["date"])
    df["amount"] = pd.to_numeric(df["amount"], errors="coerce").fillna(0)
    df["tags_str"] = df["tags"].apply(lambda x: ", ".join(x) if isinstance(x, list) else str(x))
    df["primary_tag"] = df["tags"].apply(lambda x: x[0] if isinstance(x, list) and x else "Other")
    df["month"] = df["date"].dt.to_period("M").astype(str)
    df["day_of_week"] = df["date"].dt.day_name()
    return df


def _render_filters(df: pd.DataFrame, people: list[str], all_tags: list[str]) -> pd.DataFrame:
    with st.sidebar:
        st.header("Filters")

        min_date = df["date"].min().date()
        max_date = df["date"].max().date()
        date_range = st.date_input("Date range", value=(min_date, max_date), key="analysis_date")

        selected_people = st.multiselect("Person", people, default=people, key="analysis_people")

        available_tags = sorted(df["primary_tag"].unique().tolist())
        selected_tags = st.multiselect("Tags", available_tags, default=available_tags, key="analysis_tags")

        min_amt = float(df["amount"].min())
        max_amt = float(df["amount"].max())
        if min_amt < max_amt:
            amount_range = st.slider("Amount range ($)", min_amt, max_amt, (min_amt, max_amt), key="analysis_amount")
        else:
            amount_range = (min_amt, max_amt)

    if isinstance(date_range, (list, tuple)) and len(date_range) == 2:
        start, end = pd.Timestamp(date_range[0]), pd.Timestamp(date_range[1])
        df = df[(df["date"] >= start) & (df["date"] <= end)]

    if selected_people:
        df = df[df["person"].isin(selected_people)]
    if selected_tags:
        df = df[df["primary_tag"].isin(selected_tags)]

    df = df[(df["amount"] >= amount_range[0]) & (df["amount"] <= amount_range[1])]
    return df


def _render_charts(df: pd.DataFrame):
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Total Spending", f"${df['amount'].sum():,.2f}")
    with col2:
        st.metric("Transactions", len(df))
    with col3:
        st.metric("Avg Transaction", f"${df['amount'].mean():,.2f}")

    st.subheader("Spending Over Time")
    monthly = df.groupby("month")["amount"].sum().reset_index()
    monthly.columns = ["Month", "Amount"]
    fig = px.line(monthly, x="Month", y="Amount", markers=True)
    fig.update_layout(yaxis_tickprefix="$", xaxis_title="", yaxis_title="Total Spending ($)")
    st.plotly_chart(fig, use_container_width=True)

    col_left, col_right = st.columns(2)

    with col_left:
        st.subheader("Spending by Tag")
        by_tag = df.groupby("primary_tag")["amount"].sum().reset_index()
        by_tag.columns = ["Tag", "Amount"]
        fig_pie = px.pie(by_tag, names="Tag", values="Amount", hole=0.35)
        st.plotly_chart(fig_pie, use_container_width=True)

    with col_right:
        st.subheader("Spending by Tag (Bar)")
        by_tag_sorted = by_tag.sort_values("Amount", ascending=False)
        fig_bar = px.bar(by_tag_sorted, x="Tag", y="Amount")
        fig_bar.update_layout(yaxis_tickprefix="$", xaxis_title="", yaxis_title="Amount ($)")
        st.plotly_chart(fig_bar, use_container_width=True)

    st.subheader("Monthly Breakdown by Tag")
    monthly_tag = df.groupby(["month", "primary_tag"])["amount"].sum().reset_index()
    monthly_tag.columns = ["Month", "Tag", "Amount"]
    fig_stacked = px.bar(monthly_tag, x="Month", y="Amount", color="Tag", barmode="stack")
    fig_stacked.update_layout(yaxis_tickprefix="$", xaxis_title="", yaxis_title="Amount ($)")
    st.plotly_chart(fig_stacked, use_container_width=True)

    col_left2, col_right2 = st.columns(2)

    with col_left2:
        st.subheader("Spending by Person (Monthly)")
        by_person_month = df.groupby(["month", "person"])["amount"].sum().reset_index()
        by_person_month.columns = ["Month", "Person", "Amount"]
        fig_person = px.bar(by_person_month, x="Month", y="Amount", color="Person", barmode="group")
        fig_person.update_layout(yaxis_tickprefix="$", xaxis_title="", yaxis_title="Amount ($)")
        st.plotly_chart(fig_person, use_container_width=True)

    with col_right2:
        st.subheader("Spending by Day of Week")
        dow_order = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
        by_dow = df.groupby("day_of_week")["amount"].sum().reindex(dow_order).fillna(0).reset_index()
        by_dow.columns = ["Day", "Amount"]
        fig_dow = px.bar(by_dow, x="Day", y="Amount", color="Amount",
                         color_continuous_scale="Blues")
        fig_dow.update_layout(yaxis_tickprefix="$", xaxis_title="", yaxis_title="Amount ($)", showlegend=False)
        st.plotly_chart(fig_dow, use_container_width=True)

    st.subheader("Cumulative Spending Over Time")
    df_sorted = df.sort_values("date")
    df_sorted["cumulative"] = df_sorted["amount"].cumsum()
    fig_cum = px.line(df_sorted, x="date", y="cumulative")
    fig_cum.update_layout(yaxis_tickprefix="$", xaxis_title="", yaxis_title="Cumulative Spending ($)")
    st.plotly_chart(fig_cum, use_container_width=True)

    st.subheader("Top 10 Expenses")
    top10 = df.nlargest(10, "amount")[["date", "description", "amount", "person", "tags_str"]]
    top10 = top10.rename(columns={"date": "Date", "description": "Description",
                                   "amount": "Amount ($)", "person": "Person", "tags_str": "Tags"})
    st.dataframe(top10, use_container_width=True, hide_index=True)


def _render_insights(df: pd.DataFrame):
    st.subheader("Monthly Averages by Tag")
    monthly_tag = df.groupby(["month", "primary_tag"])["amount"].sum().reset_index()
    avg_by_tag = monthly_tag.groupby("primary_tag")["amount"].mean().sort_values(ascending=False).reset_index()
    avg_by_tag.columns = ["Tag", "Monthly Avg ($)"]
    avg_by_tag["Monthly Avg ($)"] = avg_by_tag["Monthly Avg ($)"].apply(lambda x: f"${x:,.2f}")
    st.dataframe(avg_by_tag, use_container_width=True, hide_index=True)

    st.subheader("Spending Trend")
    monthly = df.groupby("month")["amount"].sum().reset_index()
    if len(monthly) >= 2:
        x = np.arange(len(monthly))
        y = monthly["amount"].values
        slope, intercept, r_value, p_value, _ = stats.linregress(x, y)
        direction = "up" if slope > 0 else "down"
        pct = abs(slope / (y.mean() or 1)) * 100
        st.info(f"Spending is trending **{direction}** by approximately **{pct:.1f}%** per month "
                f"(R²={r_value**2:.2f}).")

        months_ahead = 1
        forecast = intercept + slope * (len(monthly) + months_ahead - 1)
        std_err = y.std()
        st.metric(
            label="Next Month Forecast",
            value=f"${max(forecast, 0):,.2f}",
            delta=f"±${std_err:,.2f}",
        )

        fig_trend = go.Figure()
        fig_trend.add_trace(go.Scatter(x=monthly["month"], y=y, mode="lines+markers", name="Actual"))
        trend_line = intercept + slope * x
        fig_trend.add_trace(go.Scatter(x=monthly["month"], y=trend_line, mode="lines",
                                       name="Trend", line=dict(dash="dash", color="red")))
        forecast_month = f"Forecast +1"
        fig_trend.add_trace(go.Scatter(
            x=[monthly["month"].iloc[-1], forecast_month],
            y=[y[-1], max(forecast, 0)],
            mode="lines+markers", name="Forecast",
            line=dict(dash="dot", color="orange"),
        ))
        fig_trend.update_layout(yaxis_tickprefix="$", xaxis_title="", yaxis_title="Amount ($)")
        st.plotly_chart(fig_trend, use_container_width=True)
    else:
        st.info("Need at least 2 months of data for trend analysis.")

    st.subheader("Anomaly Detection")
    anomalies = []
    for tag, group in df.groupby("primary_tag"):
        if len(group) < 3:
            continue
        mean = group["amount"].mean()
        std = group["amount"].std()
        if std == 0:
            continue
        flagged = group[group["amount"] > mean + 2 * std]
        for _, row in flagged.iterrows():
            anomalies.append({
                "Date": row["date"].date(),
                "Description": row["description"],
                "Amount ($)": f"${row['amount']:,.2f}",
                "Tag": tag,
                "Category Avg": f"${mean:,.2f}",
            })

    if anomalies:
        st.warning(f"{len(anomalies)} anomalous transaction(s) detected (>2 std above category mean).")
        st.dataframe(pd.DataFrame(anomalies), use_container_width=True, hide_index=True)
    else:
        st.success("No spending anomalies detected.")

    st.subheader("Recurring Expense Detection")
    candidate_groups = df.groupby("description").filter(lambda g: len(g["month"].unique()) >= 2)
    if candidate_groups.empty:
        st.info("No recurring expenses detected yet (need 2+ months of same description).")
    else:
        recurring = (
            candidate_groups.groupby("description")
            .agg(
                Occurrences=("amount", "count"),
                Avg_Amount=("amount", "mean"),
                Months=("month", lambda x: len(x.unique())),
            )
            .reset_index()
            .sort_values("Avg_Amount", ascending=False)
        )
        recurring["Avg_Amount"] = recurring["Avg_Amount"].apply(lambda x: f"${x:,.2f}")
        recurring.columns = ["Description", "Occurrences", "Avg Amount ($)", "Months Active"]
        st.dataframe(recurring, use_container_width=True, hide_index=True)

    st.subheader("Category Growth (Latest vs Prior Period)")
    months_sorted = sorted(df["month"].unique())
    if len(months_sorted) >= 2:
        mid = len(months_sorted) // 2
        prior_months = months_sorted[:mid]
        recent_months = months_sorted[mid:]

        prior = df[df["month"].isin(prior_months)].groupby("primary_tag")["amount"].sum()
        recent = df[df["month"].isin(recent_months)].groupby("primary_tag")["amount"].sum()
        growth = pd.DataFrame({"Prior": prior, "Recent": recent}).fillna(0)
        growth["Change (%)"] = ((growth["Recent"] - growth["Prior"]) / (growth["Prior"].replace(0, np.nan))) * 100
        growth = growth.sort_values("Change (%)", ascending=False).reset_index()
        growth.columns = ["Tag", "Prior ($)", "Recent ($)", "Change (%)"]
        growth["Prior ($)"] = growth["Prior ($)"].apply(lambda x: f"${x:,.2f}")
        growth["Recent ($)"] = growth["Recent ($)"].apply(lambda x: f"${x:,.2f}")
        growth["Change (%)"] = growth["Change (%)"].apply(lambda x: f"{x:+.1f}%" if pd.notna(x) else "N/A")
        st.dataframe(growth, use_container_width=True, hide_index=True)
    else:
        st.info("Need at least 2 months of data for category growth analysis.")
