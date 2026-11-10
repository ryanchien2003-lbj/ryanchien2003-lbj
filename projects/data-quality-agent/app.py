import json
import os
from pathlib import Path
from urllib.error import URLError

import pandas as pd
import streamlit as st

from audit import api_completion, audit

ROOT = Path(__file__).resolve().parent
st.set_page_config(page_title="Data Quality Agent", page_icon="🔎", layout="wide")
st.caption("ANALYTICS ENGINEERING / ORDERS AUDIT")
st.title("Data Quality Agent")
st.write("Inspect an orders file for missing fields, repeated IDs, invalid values and broken customer references.")
st.info("The included orders and customer records are synthetic. CSV row numbers include the header.")
orders = pd.read_csv(ROOT / "orders.csv", dtype=str, keep_default_na=False)
customers = pd.read_csv(ROOT / "customers.csv", dtype=str)
with st.expander("Inspect the input data"):
    st.dataframe(orders, hide_index=True, width="stretch")
    st.dataframe(customers, hide_index=True, width="stretch")
modes = ["Local audit workflow"]
if os.getenv("OPENAI_API_KEY"):
    modes.append("OpenAI agent")
mode = st.radio("Execution mode", modes, horizontal=True)
if mode == "OpenAI agent":
    st.caption("The API receives dataset column names, rule counts and affected row numbers. "
               "It chooses the next tool. Set OPENAI_API_KEY in the launch environment to enable this mode.")
if st.button("Run audit", type="primary"):
    st.session_state.pop("audit_report", None)
    try:
        st.session_state["audit_report"] = audit(
            orders, customers, api_completion if mode == "OpenAI agent" else None)
    except (URLError, TimeoutError, ValueError, KeyError, TypeError):
        st.error("The audit could not complete. Check the planner configuration or run the local workflow.")
report = st.session_state.get("audit_report")
if report:
    a, b, c = st.columns(3)
    a.metric("Rows reviewed", len(orders))
    b.metric("Rules completed", f"{len(report['checks'])} / 5")
    c.metric("Distinct rows flagged", report["distinct_flagged_rows"])
    if not report["complete"]:
        st.warning("The planner stopped before all checks ran. Treat this as a partial audit.")
    st.dataframe(pd.DataFrame(report["checks"]), hide_index=True, width="stretch")
    with st.expander("Inspect tool calls"):
        st.json(report["trace"])
    st.download_button("Download audit JSON", json.dumps(report, indent=2),
                       file_name="audit-report.json", mime="application/json")
