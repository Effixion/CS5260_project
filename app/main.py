from __future__ import annotations

from fastapi import FastAPI
from .schemas import AgentRequest
from .pipeline import run_agent

app = FastAPI(title="Minimal Presentation Agent")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/run")
def run(request: AgentRequest):
    result = run_agent(request)
    return result.model_dump()
