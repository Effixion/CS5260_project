from __future__ import annotations
import json, os
DEFAULT_STATE = {"goal":"","audience":"","slides_requested":5,"csv_path":"","profile":{},"summary":{},"plan":{},"slides":[],"rendered_charts":[],"history":[],"last_feedback":""}
def load_state(state_path:str):
    if not os.path.exists(state_path): return DEFAULT_STATE.copy()
    with open(state_path,"r",encoding="utf-8") as f: data=json.load(f)
    s=DEFAULT_STATE.copy(); s.update(data); return s
def save_state(state,state_path:str):
    os.makedirs(os.path.dirname(state_path),exist_ok=True)
    with open(state_path,"w",encoding="utf-8") as f: json.dump(state,f,ensure_ascii=False,indent=2)
def append_history(state,role:str,content:str):
    state.setdefault("history",[]); state["history"].append({"role":role,"content":content})
