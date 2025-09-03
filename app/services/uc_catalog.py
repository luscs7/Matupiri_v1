from __future__ import annotations
from typing import Optional, Tuple
import pandas as pd

from app.data_access.repositories import load_ucs_csv, load_ucs_geojson

def load_ucs(csv_path: Optional[str] = None, geojson_path: Optional[str] = None) -> Tuple[pd.DataFrame, dict | None]:
    """
    Carrega catálogo de UCs tabular (csv) e opcionalmente o GeoJSON.
    CSV esperado: ['nome','categoria','esfera','uf','area_ha','link']
    """
    df = load_ucs_csv(csv_path)
    gj = None
    try:
        gj = load_ucs_geojson(geojson_path)
        if not isinstance(gj, dict):
            gj = None
    except Exception:
        gj = None
    return df, gj

def filter_ucs(df: pd.DataFrame, uf: Optional[str] = None, esfera: Optional[str] = None, categoria: Optional[str] = None) -> pd.DataFrame:
    """Filtra UCs por UF, esfera e categoria."""
    if df is None or df.empty:
        return df
    view = df.copy()
    if uf and "uf" in view.columns:
        view = view[view["uf"].astype(str).str.upper() == uf.upper()]
    if esfera and "esfera" in view.columns:
        view = view[view["esfera"].astype(str).str.casefold() == esfera.casefold()]
    if categoria and "categoria" in view.columns:
        view = view[view["categoria"].astype(str).str.upper() == categoria.upper()]
    return view
