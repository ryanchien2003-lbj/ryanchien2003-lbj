# Operations Knowledge Assistant

Searches eight fictional operations policies using TF-IDF and cosine similarity. It returns source passages with policy IDs and abstains below the evidence threshold. Ten fixture queries show retrieval and abstention behavior. The assistant uses extractive retrieval and runs without a language-model API.

## Run locally

From this folder, with Python 3.11 or newer:

```sh
python -m pip install -r requirements.txt
python -m streamlit run app.py
```

## Resume bullet to adapt

Built a source-linked policy retrieval assistant with similarity ranking, evidence thresholds, and fixture checks for retrieval and abstention.
