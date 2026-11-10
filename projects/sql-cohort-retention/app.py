from pathlib import Path

import altair as alt
import pandas as pd
import streamlit as st

from analysis import retention, sample_orders

st.set_page_config(page_title="SQL Cohort Retention", page_icon="📈", layout="wide")
st.caption("CUSTOMER ANALYTICS / SQL COHORTS")
st.title("When do customers come back?")
st.info("Synthetic retail orders for January–August 2025. August is the final fully observed month.")
orders = sample_orders()
result = retention(orders)
month_one = result[result["month_index"].eq(1)]
weighted = month_one["active_customers"].sum() / month_one["cohort_size"].sum()
a, b, c = st.columns(3)
a.metric("Purchasing customers", result[result["month_index"].eq(0)]["cohort_size"].sum())
b.metric("Completed orders", orders["status"].eq("completed").sum())
c.metric("Weighted month-one retention", f"{weighted:.1%}")
st.caption("Month-one retention is the share of a cohort that purchases in the next calendar month. "
           "Multiple orders from one customer count as one active customer.")
chart = alt.Chart(result).mark_rect().encode(
    x=alt.X("month_index:O", title="Months since first purchase"),
    y=alt.Y("cohort_month:O", title="First purchase month"),
    color=alt.Color("retention:Q", scale=alt.Scale(domain=[0, 1], scheme="blues"),
                    legend=alt.Legend(format=".0%")),
    tooltip=["cohort_month:O", "month_index:O", "cohort_size:Q", "active_customers:Q",
             alt.Tooltip("retention:Q", format=".1%")],
).properties(height=280)
st.altair_chart(chart, width="stretch")
st.caption("Unobserved future months have no cells. Mature months with no returning customers show 0%.")
selected = st.selectbox("Inspect a cohort", result["cohort_month"].unique())
cohort = result[result["cohort_month"].eq(selected)].copy()
st.dataframe(cohort, hide_index=True, width="stretch")
st.download_button("Download cohort results", result.to_csv(index=False),
                   file_name="cohort-results.csv", mime="text/csv")
with st.expander("Read the SQL"):
    st.code(Path(__file__).with_name("cohort.sql").read_text(encoding="utf-8-sig"), language="sql")
