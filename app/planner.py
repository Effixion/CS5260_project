from __future__ import annotations

import os
import pandas as pd
from .schemas import DatasetProfile, PlotSpec, SlideSpec

MONTH_ORDER = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]


def _pick_column(candidates: list[str], preferred: list[str]) -> str | None:
    lowered = {c.lower(): c for c in candidates}
    for p in preferred:
        if p.lower() in lowered:
            return lowered[p.lower()]
    for c in candidates:
        if any(p in c.lower() for p in preferred):
            return c
    return None


def propose_plots(df: pd.DataFrame, profile: DatasetProfile, output_dir: str) -> list[PlotSpec]:
    cols = df.columns.tolist()
    month_col = _pick_column(cols, ["month", "date", "time"])
    sales_col = _pick_column(profile.numeric_columns, ["sales", "revenue"])
    marketing_col = _pick_column(profile.numeric_columns, ["marketing_spend", "marketing", "ad_spend"])
    region_col = _pick_column(cols, ["region", "market", "country"])
    category_col = _pick_column(cols, ["category", "segment"])
    product_col = _pick_column(cols, ["product", "item", "sku"])

    plots: list[PlotSpec] = []
    if month_col and sales_col:
        plots.append(
            PlotSpec(
                plot_id="sales_trend",
                chart_type="line",
                title="Sales Trend Over Time",
                x=month_col,
                y=sales_col,
                rationale="Shows the overall business trajectory across the year.",
                output_file=os.path.join(output_dir, "sales_trend.png"),
            )
        )

    if month_col and sales_col and region_col:
        plots.append(
            PlotSpec(
                plot_id="regional_sales",
                chart_type="bar",
                title="Regional Sales by Month",
                x=month_col,
                y=sales_col,
                group_by=region_col,
                rationale="Compares contribution and momentum across regions.",
                output_file=os.path.join(output_dir, "regional_sales.png"),
            )
        )

    if category_col and sales_col:
        plots.append(
            PlotSpec(
                plot_id="category_sales",
                chart_type="bar",
                title="Sales by Category",
                x=category_col,
                y=sales_col,
                rationale="Highlights which categories contribute the most revenue.",
                output_file=os.path.join(output_dir, "category_sales.png"),
            )
        )

    if marketing_col and sales_col:
        plots.append(
            PlotSpec(
                plot_id="marketing_vs_sales",
                chart_type="scatter",
                title="Marketing Spend vs Sales",
                x=marketing_col,
                y=sales_col,
                rationale="Tests whether higher marketing spend is associated with higher sales.",
                output_file=os.path.join(output_dir, "marketing_vs_sales.png"),
            )
        )

    if product_col and sales_col:
        plots.append(
            PlotSpec(
                plot_id="top_products",
                chart_type="bar",
                title="Top Products by Sales",
                x=product_col,
                y=sales_col,
                rationale="Shows the best-performing products to support product strategy.",
                output_file=os.path.join(output_dir, "top_products.png"),
            )
        )

    return plots


def _top_region(df: pd.DataFrame, region_col: str, sales_col: str) -> str:
    totals = df.groupby(region_col)[sales_col].sum().sort_values(ascending=False)
    return str(totals.index[0])


def _top_category(df: pd.DataFrame, category_col: str, sales_col: str) -> str:
    totals = df.groupby(category_col)[sales_col].sum().sort_values(ascending=False)
    return str(totals.index[0])


def _sales_growth(df: pd.DataFrame, month_col: str, sales_col: str) -> float:
    monthly = df.groupby(month_col)[sales_col].sum()
    ordered = monthly.reindex([m for m in MONTH_ORDER if m in monthly.index]).dropna()
    if len(ordered) < 2 or ordered.iloc[0] == 0:
        return 0.0
    return float((ordered.iloc[-1] - ordered.iloc[0]) / ordered.iloc[0] * 100)


def build_slides(df: pd.DataFrame, profile: DatasetProfile, plots: list[PlotSpec], goal: str, audience: str) -> list[SlideSpec]:
    cols = df.columns.tolist()
    month_col = _pick_column(cols, ["month", "date", "time"])
    sales_col = _pick_column(profile.numeric_columns, ["sales", "revenue"])
    region_col = _pick_column(cols, ["region", "market", "country"])
    category_col = _pick_column(cols, ["category", "segment"])

    top_region = _top_region(df, region_col, sales_col) if region_col and sales_col else "N/A"
    top_category = _top_category(df, category_col, sales_col) if category_col and sales_col else "N/A"
    growth = _sales_growth(df, month_col, sales_col) if month_col and sales_col else 0.0

    slides: list[SlideSpec] = [
        SlideSpec(
            title="Presentation Goal",
            purpose="Set the context for the deck.",
            bullets=[
                f"Goal: {goal}",
                f"Audience: {audience}",
                f"Dataset size: {profile.rows} rows and {profile.columns} columns",
            ],
        ),
        SlideSpec(
            title="Overall Sales Trend",
            purpose="Summarize the business trajectory over time.",
            bullets=[
                f"Overall sales changed by {growth:.1f}% from the first visible month to the last visible month.",
                f"The dataset contains {len(profile.numeric_columns)} numeric metrics that can support performance analysis.",
            ],
            visual="sales_trend.png",
        ),
        SlideSpec(
            title="Regional Performance",
            purpose="Compare the strongest markets.",
            bullets=[
                f"Top region by revenue: {top_region}",
                "Regional comparison helps identify where future investment may have the largest impact.",
            ],
            visual="regional_sales.png",
        ),
        SlideSpec(
            title="Category Mix",
            purpose="Explain which categories drive the business.",
            bullets=[
                f"Top category by revenue: {top_category}",
                "Category concentration can guide inventory and campaign planning.",
            ],
            visual="category_sales.png",
        ),
        SlideSpec(
            title="Marketing Effectiveness",
            purpose="Evaluate the relationship between spending and results.",
            bullets=[
                "Scatter analysis helps reveal whether higher spend aligns with higher sales.",
                "A stronger upward pattern suggests marketing is contributing to revenue growth.",
            ],
            visual="marketing_vs_sales.png",
        ),
        SlideSpec(
            title="Key Takeaways",
            purpose="End with concise recommendations.",
            bullets=[
                f"Protect momentum in {top_region} while improving weaker regions.",
                f"Double down on {top_category} while testing cross-sell opportunities.",
                "Use chart-backed findings to decide next-quarter allocation.",
            ],
        ),
    ]
    return slides
