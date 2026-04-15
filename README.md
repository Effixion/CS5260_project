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
| `ANTHROPIC_API_KEY` | — | API key for Claude models |
| `ALLOWED_ORIGINS` | `http://localhost:3000` | Comma-separated CORS allowlist for frontend origins |
