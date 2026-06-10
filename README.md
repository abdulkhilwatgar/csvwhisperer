---
title: CSVWhisperer
emoji: 🔍
colorFrom: blue
colorTo: indigo
sdk: streamlit
sdk_version: 1.32.0
app_file: app.py
pinned: false
license: mit
short_description: Ask questions about any CSV in plain English.
---

# 🔍 CSVWhisperer

> Ask questions about any CSV file in plain English. No SQL. No Python.

![Python](https://img.shields.io/badge/Python-3.11+-blue)
![Streamlit](https://img.shields.io/badge/Streamlit-1.32+-red)
![DuckDB](https://img.shields.io/badge/DuckDB-0.10+-yellow)
![License](https://img.shields.io/badge/License-MIT-green)

---

## What it does

CSVWhisperer lets you upload any CSV and query it conversationally. Under the hood:

1. Your CSV is loaded into an in-memory **DuckDB** database
2. Your question (plus a short schema description) is sent to a **Qwen2.5-Coder** model
3. The model generates a SQL query against your schema
4. The query runs against your data and results appear as a table + auto-generated chart
5. If the SQL fails, the model retries automatically (up to 3 attempts)

CSVWhisperer runs in two modes:

- **Local** — run `streamlit run app.py` on your own machine. The model runs
  through a local **Ollama** instance, so nothing about your data ever leaves
  your computer.
- **Hugging Face Space** — anyone can open the hosted Space, upload their own
  CSV, and ask questions. The model runs through the **HF Inference API**
  instead of Ollama (everything else is identical). See
  [Privacy on Hugging Face Spaces](#privacy-on-hugging-face-spaces) below.

---

## Demo

```
User: What are the top 5 products by total revenue?

→ SELECT product_name, SUM(revenue) as total_revenue
  FROM data
  GROUP BY product_name
  ORDER BY total_revenue DESC
  LIMIT 5

┌──────────────────┬───────────────┐
│ product_name     │ total_revenue │
│ Widget Pro       │ 847,293       │
│ Gadget Plus      │ 623,810       │
│ ...              │ ...           │
└──────────────────┴───────────────┘
[bar chart renders automatically]
```

---

## Setup

### Prerequisites
- Python 3.11+
- [Ollama](https://ollama.com) installed and running
- Qwen2.5-Coder model pulled:

```bash
ollama pull qwen2.5-coder:7b
```

### Install & run

```bash
git clone https://github.com/yourusername/csvwhisperer
cd csvwhisperer
pip install -r requirements.txt
streamlit run app.py
```

Open `http://localhost:8501` in your browser.

---

## Deploy to Hugging Face Spaces

CSVWhisperer supports a cloud deployment mode. When `HF_SPACE=true` is set,
the app automatically switches its SQL-generation backend from local Ollama
to the **HF Inference API** (`Qwen/Qwen2.5-Coder-7B-Instruct`). Everything
else — uploading a CSV, querying it, charts — works exactly the same as
local mode, and is usable by anyone who opens the Space.

1. Fork this repo to your HF account as a new Space (SDK: Streamlit)
2. Add your HF token as a Space secret named `HF_TOKEN` (create one at
   [huggingface.co/settings/tokens](https://huggingface.co/settings/tokens) —
   a token with "Make calls to Inference Providers" permission is enough)
3. Add a Space variable: `HF_SPACE=true`
4. Push — the Space builds automatically

### Privacy on Hugging Face Spaces

- Your CSV is processed in-memory by DuckDB inside the Space, the same as
  local mode — it is not stored or persisted.
- However, to generate SQL, a short **schema description** (column names,
  inferred types, and up to 3 sample values per column) is sent to the HF
  Inference API as part of the prompt. If your data is sensitive, run
  CSVWhisperer locally instead, where this never leaves your machine.

> Note: Inference Providers can be slower than a local GPU/CPU running
> Ollama, and are subject to your HF account's rate limits.

---

## Features

- **Natural language querying** — no SQL knowledge required
- **Auto-visualization** — bar charts, line charts, scatter plots chosen automatically
- **Retry loop** — if SQL fails, the model fixes it automatically
- **Follow-up awareness** — ask follow-up questions that reference previous results
- **Schema explorer** — sidebar shows column types, samples, and null counts
- **Local mode** — Ollama runs on your machine, nothing is sent to any API
- **Hosted mode** — deploy to HF Spaces so anyone can upload their own CSV and query it, no local setup required

---

## Architecture

```
CSVWhisperer/
├── app.py                  # Streamlit UI + session management
├── sample_data.csv         # Demo dataset (e-commerce, 500 rows)
├── core/
│   ├── schema.py           # CSV loading, column sanitization, schema inference
│   ├── sql.py              # LLM SQL generation + retry loop
│   ├── executor.py         # DuckDB query execution
│   └── visualizer.py       # Auto chart selection and generation
├── .streamlit/
│   └── config.toml         # Dark theme config
└── requirements.txt
```

---

## Supported question types

| Question type | Example |
|---|---|
| Aggregation | "What's the total revenue by region?" |
| Filtering | "Show me all orders over $500" |
| Ranking | "Top 10 customers by spend" |
| Trend | "Monthly signups over time" |
| Distribution | "How is revenue distributed across categories?" |
| Counting | "How many rows have missing email addresses?" |
| Multi-step | "Which region had the highest growth from Q1 to Q2?" |

---

## Limitations

- Works best with well-structured CSVs (consistent column types, clean headers)
- Aggregation across very large files (500k+ rows) may be slow on CPU
- The LLM occasionally misinterprets ambiguous column names — renaming columns helps
- Does not support multi-table JOINs in this version (planned)

---

## License

MIT — use freely, attribution appreciated.
