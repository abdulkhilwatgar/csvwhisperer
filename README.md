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
short_description: Ask questions about any CSV in plain English. Fully local.
---

# 🔍 CSVWhisperer

> Ask questions about any CSV file in plain English. No SQL. No Python. Fully local — your data never leaves your machine.

![Python](https://img.shields.io/badge/Python-3.11+-blue)
![Streamlit](https://img.shields.io/badge/Streamlit-1.32+-red)
![DuckDB](https://img.shields.io/badge/DuckDB-0.10+-yellow)
![License](https://img.shields.io/badge/License-MIT-green)

---

## What it does

CSVWhisperer lets you upload any CSV and query it conversationally. Under the hood:

1. Your CSV is loaded into an in-memory **DuckDB** database
2. Your question is sent to a local **Qwen2.5-Coder** model via **Ollama**
3. The model generates a SQL query against your schema
4. The query runs locally and results appear as a table + auto-generated chart
5. If the SQL fails, the model retries automatically (up to 3 attempts)

No data ever leaves your machine.

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

CSVWhisperer supports a cloud deployment mode. When deployed to HF Spaces, it
automatically switches from local Ollama to the HF Inference API and loads a
sample e-commerce dataset for the demo.

1. Fork this repo to your HF account as a new Space (SDK: Streamlit)
2. Add your HF token as a Space secret named `HF_TOKEN`
3. Add a Space variable: `HF_SPACE=true`
4. Push — the Space builds automatically

> **Data privacy:** The HF deployment uses only the bundled `sample_data.csv`.
> Your real data is never uploaded anywhere. For sensitive data, always run locally.

> Note: The free HF CPU tier is slower than local. For best performance, run locally.

---

## Features

- **Natural language querying** — no SQL knowledge required
- **Auto-visualization** — bar charts, line charts, scatter plots chosen automatically
- **Retry loop** — if SQL fails, the model fixes it automatically
- **Follow-up awareness** — ask follow-up questions that reference previous results
- **Schema explorer** — sidebar shows column types, samples, and null counts
- **100% local** — Ollama runs on your machine, nothing is sent to any API
- **HF Spaces compatible** — deploy publicly with one environment variable

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
