from __future__ import annotations
import json
from openai import OpenAI
def _client(): return OpenAI()
def _safe_json_loads(text,default):
    try: return json.loads(text)
    except Exception: return default
def _extract_text(resp):
    if hasattr(resp,"output_text") and resp.output_text: return resp.output_text
    try:
        parts=[]
        for item in resp.output:
            if getattr(item,"type",None)=="message":
                for c in getattr(item,"content",[]):
                    if getattr(c,"type",None) in ("output_text","text"): parts.append(getattr(c,"text",""))
        return "\n".join([p for p in parts if p])
    except Exception: return ""
def ai_propose_chart_candidates(df_profile,goal,audience,max_candidates=6,model="gpt-5.2"):
    prompt=f"""You are helping generate business presentation charts.
Presentation goal:
{goal}
Audience:
{audience}
Dataset profile (JSON):
{json.dumps(df_profile, ensure_ascii=False, indent=2)}
Return ONLY valid JSON:
{{"candidates":[{{"id":"chart_1","title":"short chart title","chart_type":"line|bar|stacked_bar|scatter","x":"column name","y":"column name","group_by":"column name or null","why_useful":"one sentence","priority":1}}]}}
"""
    return _safe_json_loads(_extract_text(_client().responses.create(model=model,input=prompt)),{"candidates":[]}).get("candidates",[])[:max_candidates]
def ai_select_charts_from_candidates(df_profile,goal,audience,candidates,desired_count=4,user_feedback=None,model="gpt-5.2"):
    prompt=f"""You are selecting the final charts for a presentation.
Presentation goal:
{goal}
Audience:
{audience}
Dataset profile (JSON):
{json.dumps(df_profile, ensure_ascii=False, indent=2)}
Candidate charts (JSON):
{json.dumps(candidates, ensure_ascii=False, indent=2)}
User feedback:
{user_feedback or "None"}
Return ONLY valid JSON:
{{"selected_ids":["chart_1","chart_2"],"selection_rationale":["reason 1"]}}
"""
    ids=_safe_json_loads(_extract_text(_client().responses.create(model=model,input=prompt)),{"selected_ids":[]}).get("selected_ids",[])
    return [c for c in candidates if c.get("id") in ids][:desired_count] if isinstance(ids,list) else []
def ai_generate_slides(summary,selected_charts,goal,audience,n_slides=5,model="gpt-5.2"):
    prompt=f"""Create an executive-friendly slide outline.
Goal:
{goal}
Audience:
{audience}
Dataset summary:
{json.dumps(summary, ensure_ascii=False, indent=2)}
Selected charts:
{json.dumps(selected_charts, ensure_ascii=False, indent=2)}
Return ONLY valid JSON:
{{"slides":[{{"title":"slide title","bullets":["bullet 1","bullet 2","bullet 3"],"chart_id":"chart_1 or null"}}]}}
Rules:
- Create exactly {n_slides} slides.
- Use at most 3 bullets per slide.
"""
    slides=_safe_json_loads(_extract_text(_client().responses.create(model=model,input=prompt)),{"slides":[]}).get("slides",[])
    return {"slides":slides[:n_slides] if isinstance(slides,list) else []}
def ai_apply_feedback_to_state(state,feedback,model="gpt-5.2"):
    prompt=f"""You are updating a presentation plan based on user feedback.
Current state JSON:
{json.dumps(state, ensure_ascii=False, indent=2)}
User feedback:
{feedback}
Return ONLY valid JSON:
{{"action":"regenerate_all|replace_slide|retitle_slide|simplify_slide|reselect_charts|noop","slide_number":1,"notes":"short explanation","updated_goal":"","updated_audience":"","selection_feedback":""}}
"""
    return _safe_json_loads(_extract_text(_client().responses.create(model=model,input=prompt)),{"action":"noop","slide_number":None,"notes":"","updated_goal":"","updated_audience":"","selection_feedback":""})
def ai_regenerate_single_slide(state,slide_number,feedback,model="gpt-5.2"):
    prompt=f"""You are editing exactly one slide in a business presentation.
Current state JSON:
{json.dumps(state, ensure_ascii=False, indent=2)}
Slide number to update:
{slide_number}
User feedback:
{feedback}
Return ONLY valid JSON:
{{"title":"new slide title","bullets":["bullet 1","bullet 2"],"chart_id":"existing chart id or null"}}
"""
    return _safe_json_loads(_extract_text(_client().responses.create(model=model,input=prompt)),{"title":f"Slide {slide_number}","bullets":[],"chart_id":None})
