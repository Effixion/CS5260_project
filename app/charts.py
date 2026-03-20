from __future__ import annotations
import os
import matplotlib.pyplot as plt
import pandas as pd
MONTH_ORDER=["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"]
def _ordered(df,x):
    if x=="month" and x in df.columns:
        tmp=df.copy(); tmp[x]=pd.Categorical(tmp[x],categories=MONTH_ORDER,ordered=True); return tmp.sort_values(x)
    return df
def generate_line_chart(df,x,y,group_by,title,out_path):
    plt.figure(figsize=(8,4.5)); work=_ordered(df,x)
    if group_by:
        grouped=work.groupby([x,group_by],dropna=False)[y].sum().reset_index()
        for key,sub in grouped.groupby(group_by): plt.plot(sub[x].astype(str),sub[y],marker="o",label=str(key))
        plt.legend()
    else:
        grouped=work.groupby(x,dropna=False)[y].sum().reset_index(); plt.plot(grouped[x].astype(str),grouped[y],marker="o")
    plt.title(title); plt.xlabel(x); plt.ylabel(y); plt.xticks(rotation=45); plt.tight_layout(); plt.savefig(out_path,dpi=160); plt.close()
def generate_bar_chart(df,x,y,group_by,title,out_path):
    plt.figure(figsize=(8,4.5)); work=_ordered(df,x)
    if group_by: work.groupby([x,group_by],dropna=False)[y].sum().unstack(fill_value=0).plot(kind="bar",ax=plt.gca())
    else: work.groupby(x,dropna=False)[y].sum().plot(kind="bar",ax=plt.gca())
    plt.title(title); plt.xlabel(x); plt.ylabel(y); plt.xticks(rotation=45); plt.tight_layout(); plt.savefig(out_path,dpi=160); plt.close()
def generate_stacked_bar_chart(df,x,y,group_by,title,out_path):
    plt.figure(figsize=(8,4.5)); work=_ordered(df,x); work.groupby([x,group_by],dropna=False)[y].sum().unstack(fill_value=0).plot(kind="bar",stacked=True,ax=plt.gca())
    plt.title(title); plt.xlabel(x); plt.ylabel(y); plt.xticks(rotation=45); plt.tight_layout(); plt.savefig(out_path,dpi=160); plt.close()
def generate_scatter_plot(df,x,y,group_by,title,out_path):
    plt.figure(figsize=(8,4.5))
    if group_by:
        for key,sub in df.groupby(group_by): plt.scatter(sub[x],sub[y],label=str(key),alpha=0.8)
        plt.legend()
    else: plt.scatter(df[x],df[y],alpha=0.8)
    plt.title(title); plt.xlabel(x); plt.ylabel(y); plt.tight_layout(); plt.savefig(out_path,dpi=160); plt.close()
def render_chart_bundle(df,chart_specs,out_dir):
    os.makedirs(out_dir,exist_ok=True); results=[]
    for spec in chart_specs:
        chart_type=spec["chart_type"]; chart_id=spec["id"]; x=spec["x"]; y=spec["y"]; group_by=spec.get("group_by"); out_path=os.path.join(out_dir,f"{chart_id}.png")
        try:
            if chart_type=="line": generate_line_chart(df,x,y,group_by,spec["title"],out_path)
            elif chart_type=="bar": generate_bar_chart(df,x,y,group_by,spec["title"],out_path)
            elif chart_type=="stacked_bar": generate_stacked_bar_chart(df,x,y,group_by,spec["title"],out_path)
            elif chart_type=="scatter": generate_scatter_plot(df,x,y,group_by,spec["title"],out_path)
            else: continue
            results.append({"id":chart_id,"path":out_path,"title":spec["title"]})
        except Exception as e:
            print(f"[WARN] Failed to render {chart_id}: {e}")
    return results
