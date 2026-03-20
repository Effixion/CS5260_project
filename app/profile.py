from __future__ import annotations
import pandas as pd
def _series_profile(s:pd.Series):
    info={"name":s.name,"dtype":str(s.dtype),"missing_ratio":float(s.isna().mean()) if len(s) else 0.0,"n_unique":int(s.nunique(dropna=True)),"sample_values":s.dropna().astype(str).head(5).tolist()}
    if pd.api.types.is_numeric_dtype(s):
        numeric=pd.to_numeric(s,errors="coerce").dropna()
        if len(numeric)>0: info.update({"min":float(numeric.min()),"max":float(numeric.max()),"mean":float(numeric.mean())})
    return info
def profile_dataframe(df:pd.DataFrame):
    return {"n_rows":int(len(df)),"n_columns":int(len(df.columns)),"columns":[_series_profile(df[c]) for c in df.columns],"column_names":list(df.columns)}
def summarize_for_deck(df:pd.DataFrame):
    summary={"n_rows":int(len(df)),"columns":list(df.columns)}
    if "sales" in df.columns:
        sales=pd.to_numeric(df["sales"],errors="coerce"); summary["total_sales"]=float(sales.sum()); summary["avg_sales"]=float(sales.mean())
    if "region" in df.columns and "sales" in df.columns:
        d=df.groupby("region",dropna=False)["sales"].sum().sort_values(ascending=False).to_dict(); summary["sales_by_region"]={str(k):float(v) for k,v in d.items()}
    if "category" in df.columns and "sales" in df.columns:
        d=df.groupby("category",dropna=False)["sales"].sum().sort_values(ascending=False).to_dict(); summary["sales_by_category"]={str(k):float(v) for k,v in d.items()}
    if "month" in df.columns and "sales" in df.columns:
        d=df.groupby("month",dropna=False)["sales"].sum().to_dict(); summary["sales_by_month"]={str(k):float(v) for k,v in d.items()}
    return summary
