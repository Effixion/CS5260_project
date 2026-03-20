# Minimal Presentation Agent (Runnable MVP)

This is a minimal runnable demo of a presentation agent inspired by your proposal.
It does **not** require an LLM API key. It uses deterministic logic to:

1. load and profile a CSV dataset
2. propose useful charts
3. render charts with matplotlib
4. generate a slide outline
5. export a markdown deck and an HTML preview
6. expose the workflow with FastAPI

## Quick start

```bash
cd min_agent
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python -m app.pipeline --csv data/sales_data.csv --out output
uvicorn app.main:app --reload
```

Then open:
- API docs: `http://127.0.0.1:8000/docs`
- HTML deck: `output/deck.html`

## CLI usage

```bash
python -m app.pipeline --csv data/sales_data.csv --out output
```

## API usage

### Health check
```bash
curl http://127.0.0.1:8000/health
```

### Run agent
```bash
curl -X POST http://127.0.0.1:8000/run \
  -H "Content-Type: application/json" \
  -d '{
    "csv_path": "data/sales_data.csv",
    "output_dir": "output",
    "goal": "Explain annual e-commerce performance",
    "audience": "senior business managers",
    "expected_slides": 5
  }'
```

## Project structure

```text
min_agent/
├── app/
│   ├── main.py
│   ├── pipeline.py
│   ├── schemas.py
│   ├── profiler.py
│   ├── planner.py
│   ├── charts.py
│   └── exporter.py
├── data/
│   └── sales_data.csv
├── output/
├── requirements.txt
└── README.md
```

## Notes

- This MVP is intentionally deterministic so it runs immediately.
- You can later replace `planner.py` with LLM-based planning.
- You can later replace HTML export with Beamer/LaTeX export.
