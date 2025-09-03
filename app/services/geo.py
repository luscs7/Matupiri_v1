from __future__ import annotations
import json
from functools import lru_cache
from typing import Tuple, Optional

import pandas as pd

from app.utils.config import paths

def normalize_text(s: Optional[str]) -> str:
    if s is None:
        return ""
    return str(s).strip().lower()

def guess_latlon_cols(df: pd.DataFrame) -> Tuple[Optional[str], Optional[str]]:
    """Tenta inferir colunas de latitude/longitude em um DataFrame."""
    if df is None or df.empty:
        return None, None
    candidates = [("lat", "lon"), ("latitude", "longitude"), ("y", "x")]
    cols = {c.lower(): c for c in df.columns}
    for la, lo in candidates:
        if la in cols and lo in cols:
            return cols[la], cols[lo]
    return None, None

@lru_cache(maxsize=1)
def load_geo():
    """
    Carrega referências geográficas:
    - ufs.csv (deve conter UF e lat/lon)
    - municipios.csv (deve conter nome_mun, UF e lat/lon)
    - municipios_simplificado.geojson (opcional)
    Retorna (ufs_df, mun_df, mun_geojson|None)
    """
    P = paths()
    ufs_path = P.get("GEO_UFS", "data/processed/geo/ufs.csv")
    mun_path = P.get("GEO_MUN", "data/processed/geo/municipios.csv")
    gj_path  = P.get("GEO_MUN_GJ", "data/processed/geo/municipios_simplificado.geojson")

    try:
        ufs = pd.read_csv(ufs_path, dtype={"ibge_uf": str})
    except Exception:
        ufs = pd.DataFrame()

    try:
        mun = pd.read_csv(mun_path, dtype={"ibge_mun": str})
    except Exception:
        mun = pd.DataFrame()

    gj = None
    try:
        with open(gj_path, "r", encoding="utf-8") as f:
            gj = json.load(f)
    except Exception:
        gj = None

    return ufs, mun, gj
