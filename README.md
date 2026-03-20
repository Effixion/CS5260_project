# Minimal Presentation Agent (AI edition)

This version adds optional OpenAI-powered planning for:
- plot selection
- slide titles and bullets

The plotting and export steps stay deterministic.

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
export OPENAI_API_KEY=your_key_here
```

## Run without AI

```bash
python -m app.pipeline --csv data/sales_data.csv --out output
```

## Run with AI

```bash
python -m app.pipeline \
  --csv data/sales_data.csv \
  --out output_ai \
  --goal "Explain first-half e-commerce performance and recommend actions" \
  --audience "senior business managers" \
  --slides 5 \
  --use-ai \
  --model gpt-5.2
```

## Start API server

```bash
uvicorn app.main:app --reload
```

Then open:

- http://127.0.0.1:8000/docs

## Notes

- If AI mode fails, the pipeline falls back to the rule-based planner.
- AI is only used for planning. Chart rendering and export remain deterministic.
