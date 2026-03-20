from __future__ import annotations

import argparse
import os
import pandas as pd
from .schemas import AgentRequest, AgentResult
from .profiler import profile_dataframe
from .planner import propose_plots, build_slides
from .charts import render_plot
from .exporter import export_html, export_json, export_markdown


def run_agent(request: AgentRequest) -> AgentResult:
    df = pd.read_csv(request.csv_path)
    os.makedirs(request.output_dir, exist_ok=True)

    profile = profile_dataframe(df)
    plot_specs = propose_plots(df, profile, request.output_dir)
    for spec in plot_specs:
        render_plot(df, spec)

    slides = build_slides(df, profile, plot_specs, request.goal, request.audience)

    result = AgentResult(
        profile=profile,
        plot_specs=plot_specs,
        slides=slides,
        artifacts={},
    )

    md_path = export_markdown(result, request.output_dir)
    html_path = export_html(result, request.output_dir)
    json_path = export_json(result, request.output_dir)

    result.artifacts = {
        "markdown": md_path,
        "html": html_path,
        "json": json_path,
        "plots": [spec.output_file for spec in plot_specs],
    }
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the minimal presentation agent.")
    parser.add_argument("--csv", required=True, help="Path to input CSV file")
    parser.add_argument("--out", default="output", help="Output directory")
    parser.add_argument("--goal", default="Explain annual e-commerce performance")
    parser.add_argument("--audience", default="senior business managers")
    parser.add_argument("--slides", type=int, default=5)
    args = parser.parse_args()

    request = AgentRequest(
        csv_path=args.csv,
        output_dir=args.out,
        goal=args.goal,
        audience=args.audience,
        expected_slides=args.slides,
    )
    result = run_agent(request)
    print("Generated artifacts:")
    for key, value in result.artifacts.items():
        print(f"- {key}: {value}")


if __name__ == "__main__":
    main()
