from __future__ import annotations
import argparse, json, os
import pandas as pd
from .charts import render_chart_bundle
from .deck import build_deck_markdown, build_deck_html
from .profile import profile_dataframe, summarize_for_deck
try:
    from .ai import ai_generate_slides, ai_propose_chart_candidates, ai_select_charts_from_candidates
except Exception:
    ai_generate_slides = ai_propose_chart_candidates = ai_select_charts_from_candidates = None
DEFAULT_RULE_CHARTS=[{"id":"sales_trend","title":"Sales Trend","chart_type":"line","x":"month","y":"sales","group_by":None},{"id":"region_sales","title":"Sales by Region","chart_type":"stacked_bar","x":"month","y":"sales","group_by":"region"},{"id":"category_sales","title":"Sales by Category","chart_type":"bar","x":"category","y":"sales","group_by":None},{"id":"marketing_scatter","title":"Marketing vs Sales","chart_type":"scatter","x":"marketing_spend","y":"sales","group_by":"region"}]
def ensure_dir(path): os.makedirs(path,exist_ok=True)
def choose_rule_based_charts(df):
    cols=set(df.columns); chosen=[]
    for spec in DEFAULT_RULE_CHARTS:
        needed={spec["x"],spec["y"]}; 
        if spec.get("group_by"): needed.add(spec["group_by"])
        if needed.issubset(cols): chosen.append(spec)
    return chosen
def normalize_candidates(candidates,fallback):
    valid={"line","bar","stacked_bar","scatter"}; out=[]
    for i,c in enumerate(candidates or []):
        if not isinstance(c,dict) or c.get("chart_type") not in valid or not c.get("x") or not c.get("y"): continue
        out.append({"id":c.get("id") or f"chart_{i+1}","title":c.get("title") or f"Chart {i+1}","chart_type":c.get("chart_type"),"x":c.get("x"),"y":c.get("y"),"group_by":c.get("group_by"),"why_useful":c.get("why_useful",""),"priority":c.get("priority",i+1)})
    return out or fallback
def build_default_slides(summary,chart_specs,goal,n_slides):
    slides=[{"title":"Business Overview","bullets":[goal,f"Dataset rows: {summary.get('n_rows',0)}",f"Columns analyzed: {len(summary.get('columns',[]))}"],"chart_id":None}]
    title_to_bullets={"Sales Trend":["Sales trend over time is the main performance signal.","Use this to spot seasonality and momentum.","Track whether growth is consistent."],"Sales by Region":["Regional mix highlights where growth is concentrated.","Compare relative strength across markets.","Useful for resource allocation decisions."],"Sales by Category":["Category mix shows which product lines matter most.","Supports merchandising and inventory prioritization.","Useful for portfolio strategy."],"Marketing vs Sales":["Shows whether higher spend is associated with higher sales.","Helps discuss efficiency and ROI directionally.","Useful for budget planning."]}
    for c in chart_specs[:max(0,n_slides-2)]:
        slides.append({"title":c["title"],"bullets":title_to_bullets.get(c["title"],["Key performance view.","Supports business discussion.","Use for decision making."]),"chart_id":c["id"]})
    slides.append({"title":"Key Takeaways","bullets":["The selected charts summarize trend, mix, and drivers.","Use these patterns to guide action planning.","Consider follow-up deep dives for anomalies and outliers."],"chart_id":None})
    return slides[:n_slides]
def run_pipeline(csv_path,out_dir,goal,audience,slides_requested=5,use_ai=False,model="gpt-5.2",user_feedback=""):
    ensure_dir(out_dir); plots_dir=os.path.join(out_dir,"plots"); ensure_dir(plots_dir)
    df=pd.read_csv(csv_path); profile=profile_dataframe(df); summary=summarize_for_deck(df); rule_charts=choose_rule_based_charts(df)
    plan={"used_ai":False,"ai_stage":None,"candidate_charts":[],"selected_charts":[],"selection_mode":"rule_based","user_feedback":user_feedback}; chart_specs=rule_charts
    if use_ai and ai_propose_chart_candidates and ai_select_charts_from_candidates and ai_generate_slides:
        try:
            candidates=normalize_candidates(ai_propose_chart_candidates(profile,goal,audience,max_candidates=6,model=model),rule_charts)
            selected=normalize_candidates(ai_select_charts_from_candidates(profile,goal,audience,candidates,desired_count=min(4,max(1,slides_requested-1)),user_feedback=user_feedback,model=model),rule_charts)
            chart_specs=selected or rule_charts
            plan.update({"used_ai":True,"ai_stage":"propose_and_select","candidate_charts":candidates,"selected_charts":chart_specs,"selection_mode":"ai_two_layer"})
        except Exception as e:
            plan["ai_error"]=str(e); chart_specs=rule_charts
    rendered=render_chart_bundle(df,chart_specs,plots_dir)
    slides=None
    if use_ai and ai_generate_slides and plan.get("used_ai"):
        try: slides=ai_generate_slides(summary,chart_specs,goal,audience,n_slides=slides_requested,model=model).get("slides",[])
        except Exception as e: plan["ai_slide_error"]=str(e)
    if not slides: slides=build_default_slides(summary,chart_specs,goal,slides_requested)
    deck_md=build_deck_markdown(slides,rendered,goal,audience); deck_html=build_deck_html(deck_md)
    md_path=os.path.join(out_dir,"deck.md"); html_path=os.path.join(out_dir,"deck.html"); plan_path=os.path.join(out_dir,"plan.json"); result_path=os.path.join(out_dir,"result.json")
    open(md_path,"w",encoding="utf-8").write(deck_md); open(html_path,"w",encoding="utf-8").write(deck_html)
    json.dump(plan,open(plan_path,"w",encoding="utf-8"),ensure_ascii=False,indent=2)
    result={"csv":csv_path,"goal":goal,"audience":audience,"slides_requested":slides_requested,"plots_dir":plots_dir,"deck_md":md_path,"deck_html":html_path,"plan_json":plan_path,"used_ai":plan.get("used_ai",False),"selection_mode":plan.get("selection_mode"),"profile":profile,"summary":summary,"slides":slides,"rendered_charts":rendered,"plan":plan}
    json.dump({k:v for k,v in result.items() if k not in {"profile","summary","slides","rendered_charts","plan"}},open(result_path,"w",encoding="utf-8"),ensure_ascii=False,indent=2)
    return result
def main():
    p=argparse.ArgumentParser(); p.add_argument("--csv",required=True); p.add_argument("--out",required=True); p.add_argument("--goal",default="Explain business performance and recommend actions"); p.add_argument("--audience",default="senior business managers"); p.add_argument("--slides",type=int,default=5); p.add_argument("--use-ai",action="store_true"); p.add_argument("--model",default="gpt-5.2"); p.add_argument("--user-feedback",default="")
    a=p.parse_args(); result=run_pipeline(a.csv,a.out,a.goal,a.audience,a.slides,a.use_ai,a.model,a.user_feedback)
    print(json.dumps({"csv":result["csv"],"goal":result["goal"],"audience":result["audience"],"slides_requested":result["slides_requested"],"deck_html":result["deck_html"],"plan_json":result["plan_json"],"used_ai":result["used_ai"],"selection_mode":result["selection_mode"]},ensure_ascii=False,indent=2))
if __name__=="__main__": main()
