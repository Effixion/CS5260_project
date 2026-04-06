import json
from pathlib import Path
from typing import Any

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd
from crewai import Agent as CrewAgent, Task

from app.agents.base import BaseAgent
from app.storage import ProjectManager


class PlotGeneratorAgent(BaseAgent):
    """Generates candidate plot images from analyzed data."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    async def execute(self, manager: ProjectManager, state: dict) -> dict[str, Any]:
        uploaded_files = state.get("uploaded_files", [])
        analysis = self._read_artifact_json(manager, "data_analysis.json")

        # Load DataFrames
        dataframes: dict[str, pd.DataFrame] = {}
        column_info = {}
        for filename in uploaded_files:
            if filename.lower().endswith(".csv"):
                path = manager.get_file_path(filename)
                if path.exists():
                    df = pd.read_csv(path)
                    dataframes[filename] = df
                    column_info[filename] = {
                        "columns": list(df.columns),
                        "dtypes": {col: str(dtype) for col, dtype in df.dtypes.items()},
                        "shape": list(df.shape),
                    }

        brief = state.get("brief", {})
        if not brief:
            brief = self._read_artifact_json(manager, "brief.json")
        num_viz = brief.get("num_visualizations", 4)
        brief_block = json.dumps(brief, indent=2) if brief else "No brief provided."

        analysis_block = json.dumps(analysis, indent=2) if analysis else "No analysis available."
        columns_block = json.dumps(column_info, indent=2)

        agent = CrewAgent(
            role="Data Visualization Expert",
            goal="Design effective chart specifications that clearly communicate data insights.",
            backstory=(
                "You are a data visualization specialist who creates clear, informative "
                "charts. You choose the right chart type for each dataset and insight."
            ),
            llm=self.llm,
            verbose=False,
        )

        task = Task(
            description=f"""Based on the data analysis and available columns, specify exactly {num_viz} charts to create.

ORCHESTRATOR BRIEF (follow these instructions closely):
{brief_block}

DATA ANALYSIS:
{analysis_block}

AVAILABLE COLUMNS PER FILE:
{columns_block}

Respond with ONLY a valid JSON array (no markdown, no explanation):
[
  {{
    "filename": "exact_filename.csv",
    "chart_type": "bar",
    "title": "Chart Title",
    "x_column": "exact_column_name",
    "y_column": "exact_column_name",
    "xlabel": "X Axis Label",
    "ylabel": "Y Axis Label",
    "color": "#3b82f6"
  }}
]

Rules:
- Only use column names that exist in AVAILABLE COLUMNS
- chart_type must be one of: bar, line, scatter, pie, histogram
- For pie charts, use x_column for labels and y_column for values
- For histogram, only x_column is needed
- Create exactly {num_viz} visualizations (as specified in the brief)

SLIDE-FIT CONSTRAINTS (these charts will be embedded on Beamer slides):
- Keep titles SHORT (max ~60 chars) so they don't overflow on a slide
- Limit bar/pie charts to at most 8-10 categories — group the rest into "Other"
- Prefer concise axis labels; abbreviate units (e.g. "$M" not "Millions of Dollars")
- Avoid charts that need wide x-axis labels (long dates, long category names) — if unavoidable, suggest rotating labels
- Each chart must be readable at slide size (~10×6 inches at 150 dpi)""",
            expected_output="A JSON array of plot specifications.",
            agent=agent,
        )

        result, usage = self._run_crew(agent, task)

        try:
            plot_specs = self._parse_json(result)
            if not isinstance(plot_specs, list):
                plot_specs = [plot_specs]
        except (json.JSONDecodeError, ValueError):
            plot_specs = []

        artifacts = []
        plot_index = 0

        for spec in plot_specs:
            try:
                src_file = spec.get("filename", "")
                if src_file not in dataframes:
                    continue

                df = dataframes[src_file]
                plot_index += 1
                out_filename = f"candidate_plot_{plot_index}.png"
                out_path = manager.artifacts_dir / out_filename

                self._render_plot(df, spec, out_path)

                url = f"/projects/{state['id']}/artifacts/{out_filename}"
                artifacts.append({"type": "candidate_plots", "url": url, "filename": out_filename})

            except Exception:
                continue

        # If no plots were generated, create at least one basic plot
        if not artifacts and dataframes:
            plot_index += 1
            out_filename = f"candidate_plot_{plot_index}.png"
            out_path = manager.artifacts_dir / out_filename
            first_file, first_df = next(iter(dataframes.items()))
            self._render_fallback_plot(first_df, first_file, out_path)
            url = f"/projects/{state['id']}/artifacts/{out_filename}"
            artifacts.append({"type": "candidate_plots", "url": url, "filename": out_filename})

        return {"artifacts": artifacts, "usage": usage}

    def _render_plot(self, df: pd.DataFrame, spec: dict, output_path: Path) -> None:
        """Render a single plot from a specification dict."""
        plt.style.use("seaborn-v0_8-whitegrid")
        fig, ax = plt.subplots(figsize=(10, 6))

        chart_type = spec.get("chart_type", "bar")
        title = spec.get("title", "Chart")
        x_col = spec.get("x_column", "")
        y_col = spec.get("y_column", "")
        color = spec.get("color", "#3b82f6")
        xlabel = spec.get("xlabel", x_col)
        ylabel = spec.get("ylabel", y_col)

        if chart_type == "bar":
            plot_df = df[[x_col, y_col]].dropna()
            if len(plot_df) > 10:
                # Group smaller values into "Other" to fit on a slide
                plot_df = plot_df.sort_values(y_col, ascending=False)
                top = plot_df.head(9)
                other_val = plot_df.iloc[9:][y_col].sum()
                other_row = pd.DataFrame({x_col: ["Other"], y_col: [other_val]})
                plot_df = pd.concat([top, other_row], ignore_index=True)
            labels = plot_df[x_col].astype(str).apply(lambda s: s[:20] + "…" if len(s) > 20 else s)
            ax.bar(labels, plot_df[y_col], color=color)
            plt.xticks(rotation=45, ha="right")

        elif chart_type == "line":
            plot_df = df[[x_col, y_col]].dropna()
            ax.plot(plot_df[x_col], plot_df[y_col], color=color, linewidth=2, marker="o", markersize=4)
            plt.xticks(rotation=45, ha="right")

        elif chart_type == "scatter":
            plot_df = df[[x_col, y_col]].dropna()
            ax.scatter(plot_df[x_col], plot_df[y_col], color=color, alpha=0.7)

        elif chart_type == "pie":
            plot_df = df[[x_col, y_col]].dropna()
            if len(plot_df) > 8:
                plot_df = plot_df.sort_values(y_col, ascending=False)
                top = plot_df.head(7)
                other_val = plot_df.iloc[7:][y_col].sum()
                other_row = pd.DataFrame({x_col: ["Other"], y_col: [other_val]})
                plot_df = pd.concat([top, other_row], ignore_index=True)
            labels = plot_df[x_col].astype(str).apply(lambda s: s[:15] + "…" if len(s) > 15 else s)
            ax.pie(plot_df[y_col], labels=labels, autopct="%1.1f%%", startangle=90)
            ax.set_aspect("equal")

        elif chart_type == "histogram":
            plot_df = df[[x_col]].dropna()
            ax.hist(plot_df[x_col], bins=20, color=color, edgecolor="white")

        ax.set_title(title, fontsize=14, fontweight="bold", pad=15)
        if chart_type != "pie":
            ax.set_xlabel(xlabel, fontsize=11)
            ax.set_ylabel(ylabel, fontsize=11)

        fig.tight_layout()
        fig.savefig(output_path, dpi=150, bbox_inches="tight", facecolor="white")
        plt.close(fig)

    def _render_fallback_plot(self, df: pd.DataFrame, filename: str, output_path: Path) -> None:
        """Create a basic bar chart of the first numeric column as a fallback."""
        plt.style.use("seaborn-v0_8-whitegrid")
        fig, ax = plt.subplots(figsize=(10, 6))

        numeric_cols = df.select_dtypes(include="number").columns.tolist()
        if numeric_cols:
            col = numeric_cols[0]
            data = df[col].dropna().head(20)
            ax.bar(range(len(data)), data, color="#3b82f6")
            ax.set_title(f"{col} — {filename}", fontsize=14, fontweight="bold")
            ax.set_ylabel(col)
        else:
            ax.text(0.5, 0.5, "No numeric data to plot", ha="center", va="center", fontsize=14)
            ax.set_title(filename)

        fig.tight_layout()
        fig.savefig(output_path, dpi=150, bbox_inches="tight", facecolor="white")
        plt.close(fig)
