# Haitham

AI-powered academic presentation generator using a multi-agent pipeline.

## Structure

- `frontend/` — Next.js app (TypeScript, Tailwind CSS)
- `backend/` — FastAPI app (Python, CrewAI)

## Prerequisites

- [Bun](https://bun.sh/) (JS runtime/package manager)
- Python 3.12+ with `venv`
- **Backend**: Docker (the image bundles LaTeX). For local dev without Docker, install TeX Live: `brew install --cask mactex-no-gui` on macOS, `apt install texlive-latex-extra texlive-fonts-recommended texlive-pictures` on Linux, or MiKTeX on Windows.

## Setup

### Frontend

```bash
cd frontend
bun install
bun run dev
```

### Backend (Docker — recommended for deployment)

```bash
cd backend
docker build -t haitham-backend .
docker run --rm -p 8000:8000 --env-file .env haitham-backend
```

### Backend (local venv, for development)

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
| `ALLOWED_ORIGINS` | `http://localhost:3000` | Comma-separated CORS allowlist for frontend origins |
| **API Keys** | | |
| `ANTHROPIC_API_KEY` | — | API key for Claude models (`anthropic/...`) |
| `GEMINI_API_KEY` | — | API key for Gemini models (`gemini/...`) |
| `OPENAI_API_KEY` | — | API key for OpenAI models (`openai/...`) |
| **Agent Models** | | |
| `ORCHESTRATOR_MODEL` | — | Model for the orchestrator |
| `STRATEGIST_MODEL` | — | Model for the strategist agent |
| `DATA_ANALYST_MODEL` | — | Model for the data analyst agent |
| `PLOT_GENERATOR_MODEL` | — | Model for the plot generator agent |
| `LATEX_AUTHOR_MODEL` | — | Model for the LaTeX author agent |
| `QA_REVIEWER_MODEL` | — | Model for the QA reviewer agent |
| `PRESENTER_MODEL` | — | Model for the presenter agent |

Each agent requires its own model env var. Model names use the LiteLLM provider prefix format (e.g. `gemini/gemini-2.5-flash`, `anthropic/claude-sonnet-4-20250514`, `openai/gpt-4o`). The matching API key env var is resolved automatically based on the prefix — just set the key for the provider you're using.
