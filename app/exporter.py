from __future__ import annotations

import json
import os
from jinja2 import Template
from .schemas import AgentResult

HTML_TEMPLATE = """
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>Presentation Agent Deck</title>
  <style>
    body { font-family: Arial, sans-serif; margin: 24px; line-height: 1.5; }
    .slide { border: 1px solid #ddd; border-radius: 12px; padding: 20px; margin-bottom: 24px; }
    .slide h2 { margin-top: 0; }
    img { max-width: 100%; border-radius: 8px; border: 1px solid #eee; }
    .meta { color: #666; font-size: 14px; }
  </style>
</head>
<body>
  <h1>Presentation Agent Output</h1>
  <p class="meta">Generated deck preview</p>
  {% for slide in slides %}
  <div class="slide">
    <h2>{{ loop.index }}. {{ slide.title }}</h2>
    <p><strong>Purpose:</strong> {{ slide.purpose }}</p>
    <ul>
      {% for bullet in slide.bullets %}
      <li>{{ bullet }}</li>
      {% endfor %}
    </ul>
    {% if slide.visual %}
    <img src="{{ slide.visual }}" alt="{{ slide.title }} visual">
    {% endif %}
  </div>
  {% endfor %}
</body>
</html>
"""


def export_markdown(result: AgentResult, output_dir: str) -> str:
    os.makedirs(output_dir, exist_ok=True)
    md_path = os.path.join(output_dir, "deck.md")
    with open(md_path, "w", encoding="utf-8") as f:
        f.write("# Presentation Agent Deck\n\n")
        for i, slide in enumerate(result.slides, start=1):
            f.write(f"## {i}. {slide.title}\n\n")
            f.write(f"**Purpose:** {slide.purpose}\n\n")
            for bullet in slide.bullets:
                f.write(f"- {bullet}\n")
            f.write("\n")
            if slide.visual:
                f.write(f"![{slide.title}]({slide.visual})\n\n")
    return md_path


def export_html(result: AgentResult, output_dir: str) -> str:
    os.makedirs(output_dir, exist_ok=True)
    html_path = os.path.join(output_dir, "deck.html")
    template = Template(HTML_TEMPLATE)
    rendered = template.render(slides=result.slides)
    with open(html_path, "w", encoding="utf-8") as f:
        f.write(rendered)
    return html_path


def export_json(result: AgentResult, output_dir: str) -> str:
    os.makedirs(output_dir, exist_ok=True)
    json_path = os.path.join(output_dir, "result.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(result.model_dump(), f, indent=2)
    return json_path
