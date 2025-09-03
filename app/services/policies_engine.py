from __future__ import annotations
from typing import Any, Dict, Iterable, List, Tuple
from functools import lru_cache

# Reaproveita sua lógica madura no utils.py legado
from utils import evaluate_requirements as _evaluate_requirements  # noqa: F401
from utils import load_keyword_map as _load_keyword_map  # noqa: F401

def evaluate_requirements(requirement_text: str, profile: Dict[str, Any], kw_map: Dict[str, Any]) -> Tuple[List[str], List[str]]:
    """
    Avalia o texto de 'Acesso' de uma política contra um perfil usando o mapa de palavras-chave.
    Retorna (met, missing) — listas ordenadas.
    """
    met, missing = _evaluate_requirements(requirement_text or "", profile or {}, kw_map or {})
    return list(met or []), list(missing or [])

@lru_cache(maxsize=1)
def load_keyword_map(path: str) -> Dict[str, Any]:
    """Carrega e memoriza o keyword_map.json (usa função já validada no utils.py)."""
    return _load_keyword_map(path) or {}

def batch_evaluate_policies(df, profile: Dict[str, Any], kw_map: Dict[str, Any]) -> Tuple[List[Tuple[int, List[str], List[str]]], List[Tuple[int, List[str], List[str]]]]:
    """
    Percorre um DataFrame de políticas (coluna 'Acesso') e separa
    em elegíveis (sem missing) e quase elegíveis (com missing).
    Retorna (eligible, nearly) onde cada item é (row_index, met, missing).
    """
    eligible, nearly = [], []
    if df is None or df.empty or "Acesso" not in df.columns:
        return eligible, nearly

    for idx, row in df.iterrows():
        met, missing = evaluate_requirements(str(row.get("Acesso", "")), profile, kw_map)
        if met or missing:
            (nearly if missing else eligible).append((idx, met, missing))
    return eligible, nearly
