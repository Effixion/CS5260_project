from __future__ import annotations

import json
import os
from typing import Any

from openai import OpenAI
from pydantic import BaseModel, Field

from .schemas import DatasetProfile, PlotSpec, SlideSpec


class AIPlotSpec(BaseModel):
    plot_id: str
    chart_type: str
    title: str
    x: str
    y: str
    group_by: str | None = None
    rationale: str


class AIPlotsResponse(BaseModel):
    plots: list[AIPlotSpec] = Field(default_factory=list)


class AISlideSpec(BaseModel):
    title: str
    purpose: str
    bullets: list[str] = Field(default_factory=list)
    visual: str | None = None


class AISlidesResponse(BaseModel):
    slides: list[AISlideSpec] = Field(default_factory=list)


SYSTEM_PROMPT = """
You are a presentation-planning assistant.
You do not generate charts directly. You choose suitable chart specs and slide content for a business presentation.
Only use columns that exist in the dataset profile. Prefer chart types from this safe subset: line, bar, scatter.
Be concrete, concise, and business-friendly.
""".strip()


def _client() -> OpenAI:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY is not set.")
    return OpenAI(api_key=api_key)


def _profile_text(profile: DatasetProfile) -> str:
    rows = []
    for col in profile.column_profiles:
        rows.append(
            {
                "name": col.name,
                "dtype": col.dtype,
                "missing_ratio": round(col.missing_ratio, 4),
                "unique_count": col.unique_count,
                "sample_values": col.sample_values,
            }
        )
    return json.dumps(
        {
            "rows": profile.rows,
            "columns": profile.columns,
            "numeric_columns": profile.numeric_columns,
            "categorical_columns": profile.categorical_columns,
            "column_profiles": rows,
        },
        ensure_ascii=False,
        indent=2,
    )


def propose_plots_with_ai(
    profile: DatasetProfile,
    goal: str,
    audience: str,
    expected_slides: int,
    output_dir: str,
    model: str,
) -> list[PlotSpec]:
    client = _client()
    prompt = f"""
Goal: {goal}
Audience: {audience}
Expected slides: {expected_slides}

Dataset profile:
{_profile_text(profile)}

Return 3 to 5 useful chart specs.
Rules:
- Use only existing column names.
- Use safe chart types only: line, bar, scatter.
- Use line only for time-like columns.
- Use scatter only when both x and y are numeric.
- Keep plot_id short and filesystem-safe.
- Focus on executive-level insights.
""".strip()

    response = client.responses.parse(
        model=model,
        instructions=SYSTEM_PROMPT,
        input=prompt,
        text_format=AIPlotsResponse,
    )
    parsed = response.output_parsed or AIPlotsResponse()
    allowed_chart_types = {"line", "bar", "scatter"}
    existing_columns = {c.name for c in profile.column_profiles}

    plots: list[PlotSpec] = []
    for raw in parsed.plots:
        if raw.chart_type not in allowed_chart_types:
            continue
        if raw.x not in existing_columns or raw.y not in existing_columns:
            continue
        if raw.group_by and raw.group_by not in existing_columns:
            continue
        plots.append(
            PlotSpec(
                plot_id=raw.plot_id,
                chart_type=raw.chart_type,  # type: ignore[arg-type]
                title=raw.title,
                x=raw.x,
                y=raw.y,
                group_by=raw.group_by,
                rationale=raw.rationale,
                output_file=os.path.join(output_dir, f"{raw.plot_id}.png"),
            )
        )
    return plots


def build_slides_with_ai(
    profile: DatasetProfile,
    plots: list[PlotSpec],
    goal: str,
    audience: str,
    expected_slides: int,
    model: str,
) -> list[SlideSpec]:
    client = _client()
    plot_summary = [
        {
            "plot_id": p.plot_id,
            "title": p.title,
            "chart_type": p.chart_type,
            "x": p.x,
            "y": p.y,
            "group_by": p.group_by,
            "rationale": p.rationale,
            "visual_filename": os.path.basename(p.output_file),
        }
        for p in plots
    ]
    prompt = f"""
Goal: {goal}
Audience: {audience}
Expected slides: about {expected_slides}

Dataset profile:
{_profile_text(profile)}

Available visuals:
{json.dumps(plot_summary, ensure_ascii=False, indent=2)}

Create a concise presentation plan.
Rules:
- Return about {expected_slides} slides.
- Make slide titles executive-friendly.
- Each slide should have 2 to 4 short bullets.
- Refer to visuals only by the exact visual_filename values provided above.
- You may leave visual empty for title or closing slides.
""".strip()

    response = client.responses.parse(
        model=model,
        instructions=SYSTEM_PROMPT,
        input=prompt,
        text_format=AISlidesResponse,
    )
    parsed = response.output_parsed or AISlidesResponse()
    valid_visuals = {os.path.basename(p.output_file) for p in plots}

    slides: list[SlideSpec] = []
    for raw in parsed.slides:
        visual = raw.visual if raw.visual in valid_visuals else None
        bullets = [b.strip() for b in raw.bullets if b.strip()][:4]
        slides.append(
            SlideSpec(
                title=raw.title.strip(),
                purpose=raw.purpose.strip(),
                bullets=bullets,
                visual=visual,
            )
        )
    return slides
