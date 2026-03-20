# min_agent_ai_v3

This version adds a simple interactive agent loop with persistent state.

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
export OPENAI_API_KEY=your_key
```

## Interactive agent mode

```bash
python -m app.agent \
  --csv data/sales_data.csv \
  --workspace agent_workspace \
  --goal "Explain first-half e-commerce performance and recommend actions" \
  --audience "senior business managers" \
  --slides 5 \
  --use-ai \
  --model gpt-5.2
```

Then use:
- `generate`
- `feedback replace slide 3 with category comparison`
- `feedback simplify slide 2`
- `show slides`
- `show state`
- `export`
- `exit`
