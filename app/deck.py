from __future__ import annotations
import html
def _normalize_chart_map(rendered_charts):
    m={}
    for item in rendered_charts:
        cid=item.get("id")
        if cid: m[cid]=item
    return m
def build_deck_markdown(slides,rendered_charts,goal,audience):
    chart_map=_normalize_chart_map(rendered_charts)
    parts=["# AI Presentation Deck\n",f"**Goal:** {goal}  ",f"**Audience:** {audience}\n"]
    for i,slide in enumerate(slides,start=1):
        title=slide.get("title",f"Slide {i}"); bullets=slide.get("bullets",[]); chart_id=slide.get("chart_id")
        parts.append(f"\n## Slide {i}: {title}\n")
        for bullet in bullets: parts.append(f"- {bullet}")
        if bullets: parts.append("")
        if chart_id and chart_id in chart_map:
            chart=chart_map[chart_id]; chart_title=chart.get("title",chart_id)
            parts.append(f"**Chart:** {chart_title}")
            parts.append(f"![{chart_title}]({chart.get('path','')})\n")
    return "\n".join(parts).strip()+"\n"
def build_deck_html(markdown_text:str):
    lines=markdown_text.splitlines()
    html_parts=['<!DOCTYPE html><html lang="en"><head><meta charset="utf-8"/><meta name="viewport" content="width=device-width, initial-scale=1"/><title>AI Deck</title><style>body{font-family:Arial,sans-serif;max-width:1000px;margin:40px auto;padding:0 16px;line-height:1.6}.slide{border:1px solid #ddd;border-radius:12px;padding:20px;margin:24px 0}img{max-width:100%;height:auto;border:1px solid #ddd;border-radius:8px;margin-top:12px}</style></head><body>']
    in_list=False; in_slide=False
    def close_list():
        nonlocal in_list
        if in_list: html_parts.append("</ul>"); in_list=False
    def close_slide():
        nonlocal in_slide
        if in_slide: close_list(); html_parts.append("</div>"); in_slide=False
    for raw in lines:
        line=raw.strip()
        if not line:
            close_list(); continue
        if line.startswith("# "):
            close_slide(); html_parts.append(f"<h1>{html.escape(line[2:])}</h1>"); continue
        if line.startswith("## "):
            close_slide(); html_parts.append('<div class="slide">'); in_slide=True; html_parts.append(f"<h2>{html.escape(line[3:])}</h2>"); continue
        if line.startswith("- "):
            if not in_list: html_parts.append("<ul>"); in_list=True
            html_parts.append(f"<li>{html.escape(line[2:])}</li>"); continue
        if line.startswith("![") and "](" in line and line.endswith(")"):
            close_list(); alt=line[2:line.index("]")]; path=line[line.index("(")+1:-1]
            html_parts.append(f'<p><img src="{html.escape(path)}" alt="{html.escape(alt)}"></p>'); continue
        if line.startswith("**") and line.endswith("**"):
            close_list(); html_parts.append(f"<p><strong>{html.escape(line[2:-2])}</strong></p>"); continue
        close_list(); html_parts.append(f"<p>{html.escape(line)}</p>")
    close_slide(); html_parts.append("</body></html>")
    return "\n".join(html_parts)
