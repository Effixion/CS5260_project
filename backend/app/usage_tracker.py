"""Tracks LLM usage and cost across any LiteLLM-backed call (CrewAI, direct completion, LLM.call).

Register once at import; every `litellm.completion` success fires `_on_success`,
which accumulates tokens and cost into a ContextVar-scoped dict. Callers wrap
their LLM invocation in `with track_usage() as usage:` and read the populated
dict back after.
"""

from contextlib import contextmanager
from contextvars import ContextVar
from typing import Any

import litellm

_current_bucket: ContextVar[dict | None] = ContextVar("usage_bucket", default=None)


def _empty_bucket() -> dict[str, Any]:
    return {
        "prompt_tokens": 0,
        "completion_tokens": 0,
        "total_tokens": 0,
        "cost_usd": 0.0,
    }


def _on_success(kwargs, response_obj, start_time, end_time):
    bucket = _current_bucket.get()
    if bucket is None:
        return

    cost = kwargs.get("response_cost")
    if cost is None:
        try:
            cost = litellm.completion_cost(completion_response=response_obj)
        except Exception:
            cost = 0.0

    usage = getattr(response_obj, "usage", None)
    prompt = getattr(usage, "prompt_tokens", 0) if usage else 0
    completion = getattr(usage, "completion_tokens", 0) if usage else 0
    total = getattr(usage, "total_tokens", 0) if usage else (prompt + completion)

    bucket["prompt_tokens"] += int(prompt or 0)
    bucket["completion_tokens"] += int(completion or 0)
    bucket["total_tokens"] += int(total or 0)
    bucket["cost_usd"] += float(cost or 0.0)


if _on_success not in (litellm.success_callback or []):
    litellm.success_callback = list(litellm.success_callback or []) + [_on_success]


@contextmanager
def track_usage():
    bucket = _empty_bucket()
    token = _current_bucket.set(bucket)
    try:
        yield bucket
    finally:
        _current_bucket.reset(token)
