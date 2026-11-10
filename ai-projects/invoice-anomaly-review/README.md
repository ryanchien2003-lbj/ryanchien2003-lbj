# Invoice Anomaly Review

Ranks synthetic accounts-payable invoices for review using Isolation Forest, vendor-relative amounts, and an explicit duplicate-reference rule. Training uses the first 40 days, with alerts evaluated on the final 20 days. A review-budget slider shows precision at the selected queue size. The injected cases are synthetic and performance measures apply only to this fixture.

## Run locally

From this folder, with Python 3.11 or newer:

```sh
python -m pip install -r requirements.txt
python -m streamlit run app.py
```

## Resume bullet to adapt

Built a Python anomaly-detection dashboard that combines Isolation Forest with duplicate-invoice checks and evaluates alert precision at adjustable review budgets.
