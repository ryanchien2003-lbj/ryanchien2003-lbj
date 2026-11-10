# Support Ticket Triage

Routes synthetic tickets using TF-IDF and logistic regression. Low-score and out-of-vocabulary tickets go to human review. The app shows influential terms and how changing the threshold affects automatic coverage and accuracy on a 12-ticket holdout. The examples and scores are illustrative.

## Run locally

From this folder, with Python 3.11 or newer:

```sh
python -m pip install -r requirements.txt
python -m streamlit run app.py
```

## Resume bullet to adapt

Built an NLP ticket router with TF-IDF, logistic regression, and a human-review threshold, measuring automatic routing coverage and accuracy on labeled test fixtures.
