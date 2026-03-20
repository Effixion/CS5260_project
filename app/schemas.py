from __future__ import annotations

from typing import Any, Literal
from pydantic import BaseModel, Field


class ColumnProfile(BaseModel):
    name: str
    dtype: str
    missing_ratio: float
    unique_count: int
    sample_values: list[str]


class DatasetProfile(BaseModel):
    rows: int
    columns: int
    numeric_columns: list[str]
    categorical_columns: list[str]
    column_profiles: list[ColumnProfile]


class PlotSpec(BaseModel):
    plot_id: str
    chart_type: Literal["line", "bar", "scatter"]
    title: str
    x: str
    y: str
    group_by: str | None = None
    rationale: str
    output_file: str


class SlideSpec(BaseModel):
    title: str
    purpose: str
    bullets: list[str] = Field(default_factory=list)
    visual: str | None = None


class AgentRequest(BaseModel):
    csv_path: str
    output_dir: str = "output"
    goal: str = "Explain annual e-commerce performance"
    audience: str = "senior business managers"
    expected_slides: int = 5
    use_ai: bool = False
    model: str = "gpt-5.2"


class AgentResult(BaseModel):
    profile: DatasetProfile
    plot_specs: list[PlotSpec]
    slides: list[SlideSpec]
    artifacts: dict[str, Any]
    mode: Literal["rule_based", "ai"] = "rule_based"
    notes: list[str] = Field(default_factory=list)
