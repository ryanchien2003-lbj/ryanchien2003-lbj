# Data Quality Agent

A research-style agent that uses two tools to inspect order data. It first profiles a dataset, then runs selected checks for completeness, duplicate order IDs, invalid amounts, customer references and order status.

## Try the demo

The synthetic fixture has 10 orders. The audit flags **7 distinct rows** across five rules. Duplicate-ID checks identify all occurrences, and a row that fails multiple rules counts once in the distinct-row total.

The Streamlit interface shows rule definitions, affected CSV row numbers, tool calls and a downloadable JSON audit report. A partial agent run is explicitly marked incomplete.

See [the complete sample audit report](sample-report.json) for rule counts and source row numbers.

## Execution modes

- **Local audit workflow** profiles the data and runs the returned list of checks. It works offline.
- **OpenAI agent** uses a language model to choose tool calls. Arguments are checked against the available rules. The loop is limited to eight rounds, with one tool call per round.

The optional API integration uses [OpenAI function calling](https://developers.openai.com/api/docs/guides/function-calling). The automated test uses a mocked planner response. A live API request has not been verified.

## Run

From this folder, using Python 3.11 or newer:

```sh
python -m pip install -r requirements.txt
python -m unittest -v
python -m streamlit run app.py
```

To enable the model planner, set `OPENAI_API_KEY` in the environment before launching. The default model is `gpt-4.1-mini`; `OPENAI_MODEL` can override it with another model supporting Chat Completions function calling. The API receives the dataset column names, rule counts and affected row numbers.

## Files and assumptions

`audit.py` holds the tools and agent loop. `orders.csv` and `customers.csv` are synthetic fixtures read as strings to preserve identifiers. The app uses these fixtures directly. Adjust both input files to investigate another small sample using the same schema.

The positive-amount rule assumes a refund is represented by its status with a positive original amount. Check the source system's refund convention before applying this rule elsewhere.

## Resume bullet to adapt

Built a Python data quality agent with validated tool calls, five audit rules and downloadable evidence, testing duplicate detection, invalid values, reference integrity and partial-run reporting.
