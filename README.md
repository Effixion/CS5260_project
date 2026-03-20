# Haitham

AI-powered academic presentation generator using a multi-agent pipeline.

## Structure

- `frontend/` — Next.js app (TypeScript, Tailwind CSS)
- `backend/` — FastAPI app (Python, CrewAI)

## Prerequisites

- [Bun](https://bun.sh/) (JS runtime/package manager)
- Python 3.12+ with `venv`
- `pdflatex` and `pdftoppm` (for PDF generation and preview)

## Setup

### Frontend

```bash
cd frontend
bun install
bun run dev
```

### Backend

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
uv pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

### Both (from root)

```bash
bun run dev
```

## Environment Variables

| Variable | Default | Description |
|---|---|---|
| `SESSION_STORAGE_PATH` | `./sessions` | Directory for file-backed session data |
| `ANTHROPIC_API_KEY` | — | API key for Claude models |
