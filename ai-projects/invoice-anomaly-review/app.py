import numpy as np
import pandas as pd
import streamlit as st
from sklearn.ensemble import IsolationForest
from sklearn.metrics import average_precision_score

st.set_page_config(page_title="Invoice Anomaly Review", layout="wide")
st.title("Invoice Anomaly Review")
st.caption("Synthetic accounts-payable sandbox � Isolation Forest + duplicate rule")


def generate():
    rng = np.random.default_rng(42)
    n = 720
    vendor = rng.integers(0, 12, n)
    center = 150 + 90 * vendor
    invoices = pd.DataFrame({
        "day": np.arange(n) // 12 + 1,
        "vendor": vendor,
        "reference": [f"INV-{i:04}" for i in range(n)],
        "amount": np.round(center * rng.lognormal(0, 0.23, n), 2),
        "terms": rng.choice([15, 30, 45, 60], n, p=[0.1, 0.65, 0.2, 0.05]),
    })
    invoices["scenario"] = "routine"
    for i in [508, 546, 589, 623, 650, 701]:
        invoices.loc[i, "amount"] *= 3.5
        invoices.loc[i, "scenario"] = "amount spike"
    for i in [522, 557, 599, 636, 676, 711]:
        invoices.loc[i, ["vendor", "reference", "amount", "terms"]] = invoices.loc[
            i - 7, ["vendor", "reference", "amount", "terms"]
        ].values
        invoices.loc[i, "scenario"] = "duplicate reference"
    return invoices


@st.cache_data
def score():
    invoices = generate()
    train = invoices[invoices["day"] <= 40]
    test = invoices[invoices["day"] > 40].copy()
    typical = train.groupby("vendor")["amount"].median()
    features = pd.DataFrame({
        "log_amount_ratio": np.log(invoices["amount"] / invoices["vendor"].map(typical)),
        "terms": invoices["terms"],
    })
    detector = IsolationForest(n_estimators=150, random_state=42).fit(features.loc[train.index])
    risk = -detector.score_samples(features.loc[test.index])
    test["Duplicate reference"] = invoices.duplicated(["vendor", "reference"]).loc[test.index]
    test["Risk score"] = np.where(test["Duplicate reference"], 1 + risk, risk)
    test["Amount vs. vendor median"] = np.exp(features.loc[test.index, "log_amount_ratio"])
    test["Review reason"] = np.where(
        test["Duplicate reference"], "Vendor reference already seen",
        np.where(test["Amount vs. vendor median"] >= 2, "Amount exceeds 2x vendor median",
                 "Unusual amount or payment terms"),
    )
    test["Injected anomaly"] = test["scenario"].ne("routine")
    return test.sort_values("Risk score", ascending=False), len(train)


review, training_count = score()
budget = st.slider("Review budget", 5, 40, 15)
queue = review.head(budget)
first, second, third = st.columns(3)
first.metric("Holdout invoices", len(review))
second.metric("Injected cases in review queue", f"{queue['Injected anomaly'].sum()} / {review['Injected anomaly'].sum()}")
third.metric("Precision at review budget", f"{queue['Injected anomaly'].mean():.0%}")
st.dataframe(queue[["day", "vendor", "reference", "amount", "Amount vs. vendor median",
                   "Review reason", "Risk score", "scenario"]], hide_index=True, width="stretch")
st.caption(f"Trained on {training_count} earlier invoices. Average precision on the synthetic holdout is "
           f"{average_precision_score(review['Injected anomaly'], review['Risk score']):.3f}.")
st.write("The model ranks unusual amounts and terms. A repeated vendor reference moves an invoice "
         "ahead of model-only alerts. Review reasons are descriptive heuristics.")
