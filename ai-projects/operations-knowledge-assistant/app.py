import re

import numpy as np
import streamlit as st
from sklearn.feature_extraction.text import TfidfVectorizer

POLICIES = {
    "OPS-01": ("Purchase approvals", "A purchase order above $5,000 requires Finance approval before ordering."),
    "OPS-02": ("Vendor bank changes", "Verify vendor bank changes by calling the existing phone number in the vendor record."),
    "OPS-03": ("Travel receipts", "Submit travel receipts within 15 calendar days after the trip ends."),
    "OPS-04": ("System access", "The department manager approves new system access. Security handles privileged access."),
    "OPS-05": ("Incident escalation", "Notify the on-call operations lead immediately for a service outage affecting customers."),
    "OPS-06": ("Data retention", "Keep routine support records for 12 months. Escalate legal holds to the compliance team."),
    "OPS-07": ("Inventory discrepancies", "Recount the item with a second employee before posting an inventory adjustment."),
    "OPS-08": ("Contract renewals", "Send renewal requests to Procurement at least 45 days before the contract expires."),
}
ALIASES = {
    "expense": "travel", "expenses": "travel", "purchasing": "purchase",
    "supplier": "vendor", "renew": "renewal", "downtime": "outage",
    "permissions": "access", "privilege": "privileged", "stocktake": "inventory",
}
QUESTIONS = [
    ("Who approves a purchase above $5,000?", "OPS-01"),
    ("How should I verify supplier bank changes?", "OPS-02"),
    ("When are travel receipts due?", "OPS-03"),
    ("Who handles privileged system permissions?", "OPS-04"),
    ("Who should I call about customer downtime?", "OPS-05"),
    ("How long are support records kept?", "OPS-06"),
    ("What should I do about an inventory discrepancy?", "OPS-07"),
    ("When do I submit a contract renewal request?", "OPS-08"),
    ("How do I bake sourdough?", None),
    ("What is the corporate gym discount?", None),
]


def normalize(text):
    return " ".join(ALIASES.get(token, token) for token in re.findall(r"[a-z0-9]+", text.lower()))


@st.cache_resource
def index():
    vectorizer = TfidfVectorizer(stop_words="english", ngram_range=(1, 2))
    documents = [normalize(title + " " + passage) for title, passage in POLICIES.values()]
    return vectorizer, vectorizer.fit_transform(documents)


def retrieve(question, cutoff=0.18):
    vectorizer, matrix = index()
    scores = (matrix @ vectorizer.transform([normalize(question)]).T).toarray().ravel()
    ids = list(POLICIES)
    return [(ids[i], scores[i]) for i in np.argsort(-scores, kind="stable")[:3] if scores[i] >= cutoff]


st.set_page_config(page_title="Operations Knowledge Assistant", layout="centered")
st.title("Operations Knowledge Assistant")
st.caption("Extractive policy retrieval � Eight fictional operations policies")
question = st.text_input("Ask a policy question", "How do I verify a supplier bank change?", max_chars=400)
if question.strip():
    matches = retrieve(question)
    if matches:
        for source, score in matches:
            title, passage = POLICIES[source]
            with st.container(border=True):
                st.markdown(f"**{title} � {source}**")
                st.write(passage)
                st.caption(f"Cosine similarity � {score:.2f}")
    else:
        st.info("No policy passage met the evidence threshold.")
with st.expander("Open the source policies"):
    for source, (title, passage) in POLICIES.items():
        st.markdown(f"**{source} � {title}**")
        st.write(passage)
with st.expander("See the fixture evaluation"):
    rows = []
    for example, expected in QUESTIONS:
        hits = retrieve(example)
        top = hits[0][0] if hits else None
        rows.append({"Question": example, "Expected": expected or "Abstain",
                     "Retrieved": top or "Abstain", "Match": top == expected})
    st.write(f"{sum(row['Match'] for row in rows)} / {len(rows)} fixture checks matched.")
    st.dataframe(rows, hide_index=True, width="stretch")
