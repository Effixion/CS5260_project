from __future__ import annotations
import argparse, json, os
from .agent_state import append_history, load_state, save_state
from .deck import build_deck_html, build_deck_markdown
from .pipeline import run_pipeline
try:
    from .ai import ai_apply_feedback_to_state, ai_regenerate_single_slide
except Exception:
    ai_apply_feedback_to_state = ai_regenerate_single_slide = None
HELP_TEXT="""Commands:
  generate
  feedback <your instruction>
  show state
  show slides
  export
  help
  exit"""
def export_from_state(state,workspace):
    deck_md=build_deck_markdown(state.get("slides",[]),state.get("rendered_charts",[]),state.get("goal",""),state.get("audience",""))
    deck_html=build_deck_html(deck_md)
    open(os.path.join(workspace,"deck.md"),"w",encoding="utf-8").write(deck_md)
    open(os.path.join(workspace,"deck.html"),"w",encoding="utf-8").write(deck_html)
def initial_generate(state,workspace,use_ai,model):
    result=run_pipeline(state["csv_path"],workspace,state["goal"],state["audience"],state["slides_requested"],use_ai,model,state.get("last_feedback",""))
    state["profile"]=result["profile"]; state["summary"]=result["summary"]; state["plan"]=result["plan"]; state["slides"]=result["slides"]; state["rendered_charts"]=result["rendered_charts"]
    return state
def apply_feedback(state,workspace,feedback,use_ai,model):
    state["last_feedback"]=feedback; append_history(state,"user",feedback)
    if not use_ai or not ai_apply_feedback_to_state: return initial_generate(state,workspace,False,model)
    update=ai_apply_feedback_to_state(state,feedback,model=model); action=update.get("action","noop"); slide_number=update.get("slide_number")
    if update.get("updated_goal"): state["goal"]=update["updated_goal"]
    if update.get("updated_audience"): state["audience"]=update["updated_audience"]
    if action in {"regenerate_all","reselect_charts"}: return initial_generate(state,workspace,True,model)
    if action in {"replace_slide","retitle_slide","simplify_slide"} and isinstance(slide_number,int):
        idx=slide_number-1
        if 0 <= idx < len(state.get("slides",[])) and ai_regenerate_single_slide:
            state["slides"][idx]=ai_regenerate_single_slide(state,slide_number,feedback,model=model); export_from_state(state,workspace); append_history(state,"assistant",f"Updated slide {slide_number}."); return state
    if update.get("selection_feedback"): state["last_feedback"]=update["selection_feedback"]; return initial_generate(state,workspace,True,model)
    append_history(state,"assistant","No actionable update detected; deck unchanged."); return state
def main():
    p=argparse.ArgumentParser(); p.add_argument("--csv",required=True); p.add_argument("--workspace",default="agent_workspace"); p.add_argument("--goal",default="Explain business performance and recommend actions"); p.add_argument("--audience",default="senior business managers"); p.add_argument("--slides",type=int,default=5); p.add_argument("--use-ai",action="store_true"); p.add_argument("--model",default="gpt-5.2")
    a=p.parse_args(); os.makedirs(a.workspace,exist_ok=True); state_path=os.path.join(a.workspace,"state.json"); state=load_state(state_path)
    state["csv_path"]=a.csv; state["goal"]=state.get("goal") or a.goal; state["audience"]=state.get("audience") or a.audience; state["slides_requested"]=state.get("slides_requested") or a.slides
    print("Manus-lite v3 interactive agent"); print(HELP_TEXT)
    while True:
        cmd=input("\nagent> ").strip()
        if not cmd: continue
        if cmd=="exit": save_state(state,state_path); print("State saved. Bye."); break
        if cmd=="help": print(HELP_TEXT); continue
        if cmd=="generate":
            state=initial_generate(state,a.workspace,a.use_ai,a.model); save_state(state,state_path); print("Deck generated."); print(f"Open: {os.path.join(a.workspace,'deck.html')}"); continue
        if cmd.startswith("feedback "):
            state=apply_feedback(state,a.workspace,cmd[len("feedback "):].strip(),a.use_ai,a.model); save_state(state,state_path); print("Feedback applied."); print(f"Open: {os.path.join(a.workspace,'deck.html')}"); continue
        if cmd=="show state":
            print(json.dumps({"goal":state.get("goal"),"audience":state.get("audience"),"slides_requested":state.get("slides_requested"),"last_feedback":state.get("last_feedback"),"selected_charts":state.get("plan",{}).get("selected_charts",[])},ensure_ascii=False,indent=2)); continue
        if cmd=="show slides":
            for i,slide in enumerate(state.get("slides",[]),start=1):
                print(f"\nSlide {i}: {slide.get('title')}")
                for b in slide.get("bullets",[]): print(f"- {b}")
                print(f"chart_id: {slide.get('chart_id')}")
            continue
        if cmd=="export":
            export_from_state(state,a.workspace); save_state(state,state_path); print(f"Exported to {os.path.join(a.workspace,'deck.html')}"); continue
        print("Unknown command. Type 'help'.")
if __name__=="__main__": main()
