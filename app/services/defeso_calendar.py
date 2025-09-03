from __future__ import annotations
from typing import Optional
from datetime import date
import pandas as pd

from app.data_access.repositories import load_defesos_csv

DATE_COLS = ("inicio", "fim")

def _coerce_dates(df: pd.DataFrame) -> pd.DataFrame:
    for c in DATE_COLS:
        if c in df.columns:
            df[c] = pd.to_datetime(df[c], errors="coerce")
    return df

def load_defesos(path: Optional[str] = None) -> pd.DataFrame:
    """
    Esperado CSV com colunas mínimas:
    ['especie','nome_popular','arte_pesca','uf','inicio','fim','fundamento_legal','esfera','link_oficial']
    """
    df = load_defesos_csv(path).fillna("")
    if not df.empty:
        df = _coerce_dates(df)
    return df

def filter_defesos(df: pd.DataFrame,
                   uf: Optional[str] = None,
                   especie_query: Optional[str] = None,
                   arte_query: Optional[str] = None,
                   esfera: Optional[str] = None) -> pd.DataFrame:
    """Filtra defesos por UF, espécie (ou nome popular), arte de pesca e esfera."""
    if df is None or df.empty:
        return df
    view = df.copy()
    if uf and "uf" in view.columns:
        view = view[view["uf"].astype(str).str.upper() == uf.upper()]
    if especie_query:
        q = especie_query.lower()
        view = view[
            view.get("especie", "").astype(str).str.lower().str.contains(q, na=False) |
            view.get("nome_popular", "").astype(str).str.lower().str.contains(q, na=False)
        ]
    if arte_query and "arte_pesca" in view.columns:
        view = view[view["arte_pesca"].astype(str).str.lower().str.contains(arte_query.lower(), na=False)]
    if esfera and "esfera" in view.columns and esfera.lower() != "todas":
        view = view[view["esfera"].astype(str).str.casefold() == esfera.casefold()]
    return view

def active_defesos_on(df: pd.DataFrame, on: date) -> pd.DataFrame:
    """
    Retorna os defesos ativos em uma data específica (inclusivo: inicio <= on <= fim).
    """
    if df is None or df.empty:
        return df
    if not {"inicio", "fim"}.issubset(df.columns):
        return pd.DataFrame(columns=df.columns)
    # garante datetime
    df = _coerce_dates(df)
    on_ts = pd.Timestamp(on)
    mask = (df["inicio"].notna()) & (df["fim"].notna()) & (df["inicio"] <= on_ts) & (df["fim"] >= on_ts)
    return df.loc[mask].copy()
