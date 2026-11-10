import numpy as np
import streamlit as st
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, f1_score
from sklearn.pipeline import make_pipeline

TRAIN = {
    "Billing": ["card charged twice", "invoice total is wrong", "refund never arrived", "update payment method",
                "unrecognized charge on invoice", "discount missing from bill", "payment declined at checkout",
                "charged after cancellation", "where can I download receipt", "subscription price increased"],
    "Account access": ["password reset link expired", "cannot sign in", "locked out of my account",
                       "two factor code never came", "login loop after password change", "forgot username",
                       "authentication app lost", "verification email not arriving", "account login disabled",
                       "sign in from new device fails"],
    "Technical issue": ["dashboard freezes on load", "file export times out", "mobile app crashes",
                        "blank page after update", "upload fails with error", "report takes forever to load",
                        "integration returns server error", "chart does not render", "sync stuck on processing",
                        "app shows error after upgrade"],
    "Feature request": ["please add dark mode", "would like scheduled reports", "need custom dashboard filters",
                        "could you add bulk editing", "request support for export to excel", "add search shortcuts",
                        "please offer more notification settings", "want recurring reminders",
                        "can you build a calendar integration", "would love a configurable report template"],
}
HOLDOUT = {
    "Billing": ["my invoice shows a duplicate charge", "refund still pending", "card payment was declined"],
    "Account access": ["password reset email never arrived", "unable to sign in on phone", "login verification code missing"],
    "Technical issue": ["the dashboard freezes every morning", "export returns an error", "upload stuck on processing"],
    "Feature request": ["please add scheduled notifications", "could we have dark mode", "would like more filters"],
}


def flatten(groups):
    return [(message, label) for label, messages in groups.items() for message in messages]


@st.cache_resource
def fit():
    messages, labels = zip(*flatten(TRAIN))
    return make_pipeline(TfidfVectorizer(ngram_range=(1, 2), stop_words="english"),
                         LogisticRegression(C=8)).fit(messages, labels)


def route(model, message, threshold):
    features = model[0].transform([message])
    scores = model[1].predict_proba(features)[0]
    best = int(scores.argmax())
    label = model.classes_[best]
    if not features.nnz or scores[best] < threshold:
        return "Human review", scores, []
    contributions = features.multiply(model[1].coef_[best]).tocoo()
    ranked = sorted(zip(contributions.data, contributions.col), reverse=True)
    terms = model[0].get_feature_names_out()
    return label, scores, [terms[index] for weight, index in ranked if weight > 0][:5]


st.set_page_config(page_title="Support Ticket Triage", layout="centered")
st.title("Support Ticket Triage")
st.caption("Synthetic support messages � TF-IDF + logistic regression")
model = fit()
threshold = st.slider("Minimum score for automatic routing", 0.25, 0.95, 0.42, 0.01)
message = st.text_area("Ticket", "My card was charged twice and I need a refund.", max_chars=1000)
if message.strip():
    label, scores, terms = route(model, message, threshold)
    st.metric("Suggested queue", label)
    st.bar_chart(dict(zip(model.classes_, scores)), horizontal=True)
    if terms:
        st.caption("Positive terms for the suggested queue � " + ", ".join(terms))
    st.caption("Classifier scores are uncalibrated.")

messages, labels = zip(*flatten(HOLDOUT))
prediction = model.predict(messages)
routed = [route(model, text, threshold)[0] for text in messages]
accepted = np.array(routed) != "Human review"
st.subheader("Toy holdout")
a, b, c = st.columns(3)
a.metric("Top-label macro F1", f"{f1_score(labels, prediction, average='macro'):.2f}")
b.metric("Automatic coverage", f"{accepted.mean():.0%}")
accepted_accuracy = accuracy_score(np.array(labels)[accepted], np.array(routed)[accepted]) if accepted.any() else None
c.metric("Accuracy on routed tickets", f"{accepted_accuracy:.0%}" if accepted_accuracy is not None else "-")
st.caption(f"{len(messages)} separately written synthetic examples. Threshold is exploratory.")
