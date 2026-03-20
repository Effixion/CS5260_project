from __future__ import annotations

import pandas as pd
from .schemas import ColumnProfile, DatasetProfile


def profile_dataframe(df: pd.DataFrame) -> DatasetProfile:
    numeric_columns = df.select_dtypes(include=["number"]).columns.tolist()
    categorical_columns = [c for c in df.columns if c not in numeric_columns]

    profiles: list[ColumnProfile] = []
    for col in df.columns:
        sample_values = df[col].dropna().astype(str).head(5).tolist()
        profiles.append(
            ColumnProfile(
                name=col,
                dtype=str(df[col].dtype),
                missing_ratio=float(df[col].isna().mean()),
                unique_count=int(df[col].nunique(dropna=True)),
                sample_values=sample_values,
            )
        )

    return DatasetProfile(
        rows=int(df.shape[0]),
        columns=int(df.shape[1]),
        numeric_columns=numeric_columns,
        categorical_columns=categorical_columns,
        column_profiles=profiles,
    )
