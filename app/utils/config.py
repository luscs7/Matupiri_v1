from __future__ import annotations
import os
from functools import lru_cache
from pathlib import Path
from typing import Dict

_DEFAULTS: Dict[str, str] = {
    # Catálogo
    "POLICIES_XLSX": "data/processed/politicas_publicas.xlsx",
    "PROFILE_SCHEMA": "data/docs/profile_schema.json",
    "KEYWORD_MAP": "data/docs/keyword_map.json",
    # Geo
    "GEO_UFS": "data/processed/geo/ufs.csv",
    "GEO_MUN": "data/processed/geo/municipios.csv",
    "GEO_MUN_GJ": "data/processed/geo/municipios_simplificado.geojson",
    # Defesos / UCs
    "DEFESOS_CSV": "data/processed/defesos.csv",
    "UCS_CSV": "data/processed/ucs.csv",
    "UCS_GEOJSON": "data/processed/ucs.geojson",
}

# armazenamento interno para overrides em tempo de execução
_runtime_overrides: Dict[str, str] = {}

def _project_root() -> Path:
    # app/utils/config.py => sobe 2 níveis
    return Path(__file__).resolve().parents[2]

def _coerce(p: str) -> str:
    # normaliza separador e expande ~ e vars
    return str(Path(os.path.expandvars(os.path.expanduser(p))))

@lru_cache(maxsize=1)
def paths() -> Dict[str, str]:
    """
    Retorna um dicionário **imutável** de paths:
    - ENV tem prioridade (chave igual ao nome exato, p.ex. POLICIES_XLSX)
    - overrides definidos via set_paths()
    - defaults do projeto
    """
    merged: Dict[str, str] = {}
    for k, default in _DEFAULTS.items():
        env_val = os.environ.get(k)
        if env_val:
            merged[k] = _coerce(env_val)
        elif k in _runtime_overrides:
            merged[k] = _coerce(_runtime_overrides[k])
        else:
            merged[k] = _coerce(default)
    return dict(merged)

def set_paths(overrides: Dict[str, str]) -> None:
    """
    Define overrides em tempo de execução (útil em testes).
    Invalida o cache de paths().
    """
    global _runtime_overrides
    _runtime_overrides.update({k: _coerce(v) for k, v in (overrides or {}).items()})
    paths.cache_clear()  # type: ignore[attr-defined]

def path(key: str) -> str:
    """Atalho: paths()[key] com KeyError amigável."""
    p = paths()
    if key not in p:
        raise KeyError(f"Path '{key}' não configurado. Chaves válidas: {', '.join(sorted(p.keys()))}")
    return p[key]
