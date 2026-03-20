from __future__ import annotations

import os
import pandas as pd
import matplotlib.pyplot as plt
from .schemas import PlotSpec

MONTH_ORDER = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]


def _ordered_series(series: pd.Series) -> pd.Series:
    idx = [m for m in MONTH_ORDER if m in series.index]
    if idx:
        return series.reindex(idx).dropna()
    return series


def render_plot(df: pd.DataFrame, spec: PlotSpec) -> str:
    os.makedirs(os.path.dirname(spec.output_file), exist_ok=True)
    plt.figure(figsize=(8, 4.5))

    if spec.chart_type == "line":
        grouped = df.groupby(spec.x)[spec.y].sum()
        grouped = _ordered_series(grouped)
        plt.plot(grouped.index, grouped.values, marker="o")
        plt.xlabel(spec.x)
        plt.ylabel(spec.y)
        plt.title(spec.title)

    elif spec.chart_type == "bar":
        if spec.group_by:
            grouped = df.pivot_table(index=spec.x, columns=spec.group_by, values=spec.y, aggfunc="sum", fill_value=0)
            ordered_idx = [m for m in MONTH_ORDER if m in grouped.index]
            if ordered_idx:
                grouped = grouped.reindex(ordered_idx)
            grouped.plot(kind="bar", ax=plt.gca())
            plt.xlabel(spec.x)
            plt.ylabel(spec.y)
            plt.title(spec.title)
        else:
            grouped = df.groupby(spec.x)[spec.y].sum().sort_values(ascending=False)
            if spec.plot_id == "top_products":
                grouped = grouped.head(10)
            grouped.plot(kind="bar", ax=plt.gca())
            plt.xlabel(spec.x)
            plt.ylabel(spec.y)
            plt.title(spec.title)
            plt.xticks(rotation=30, ha="right")

    elif spec.chart_type == "scatter":
        plt.scatter(df[spec.x], df[spec.y], alpha=0.7)
        plt.xlabel(spec.x)
        plt.ylabel(spec.y)
        plt.title(spec.title)

    else:
        raise ValueError(f"Unsupported chart type: {spec.chart_type}")

    plt.tight_layout()
    plt.savefig(spec.output_file, dpi=180)
    plt.close()
    return spec.output_file
