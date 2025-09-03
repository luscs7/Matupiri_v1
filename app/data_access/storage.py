from __future__ import annotations
from pathlib import Path
from typing import Any, Iterable, Optional
import json
import os

import pandas as pd

# -------------------- Diretórios & Paths --------------------

def project_root() -> Path:
    # Assume que este arquivo está em app/data_access/storage.py => suba 2 níveis
    return Path(__file__).resolve().parents[2]

def data_dir() -> Path:
    # Permite sobrescrever via env DATA_DIR
    base = os.environ.get("DATA_DIR")
    return Path(base).resolve() if base else project_root() / "data"

def processed_dir() -> Path:
    return data_dir() / "processed"

def docs_dir() -> Path:
    return data_dir() / "docs"

def ensure_dirs() -> None:
    for p in [data_dir(), processed_dir(), docs_dir()]:
        p.mkdir(parents=True, exist_ok=True)

def resolve(path_or_env: str) -> Path:
    """
    Aceita um path literal ou o nome de uma env var. Se existir arquivo relativo ao projeto, usa.
    Caso contrário, tenta em data/processed e data/.
    """
    # 1) Se for env var
    if path_or_env.isupper() and path_or_env in os.environ:
        return Path(os.environ[path_or_env]).resolve()

    p = Path(path_or_env)
    if p.exists():
        return p.resolve()

    # 2) Tenta em processed/ e data/
    cand = [processed_dir() / path_or_env, data_dir() / path_or_env, project_root() / path_or_env]
    for c in cand:
        if c.exists():
            return c.resolve()
    return p  # pode não existir ainda

# -------------------- Leitura de Arquivos --------------------

def read_excel(path: str, sheet: int | str = 0, usecols: Optional[Iterable[str]] = None) -> pd.DataFrame:
    p = resolve(path)
    if not p.exists():
        return pd.DataFrame()
    df = pd.read_excel(p, sheet_name=sheet)
    df.columns = [str(c).strip() for c in df.columns]
    if usecols:
        keep = [c for c in usecols if c in df.columns]
        return df[keep].copy()
    return df

def read_csv(path: str, **kwargs: Any) -> pd.DataFrame:
    p = resolve(path)
    if not p.exists():
        return pd.DataFrame()
    return pd.read_csv(p, **kwargs)

def read_json(path: str) -> dict:
    p = resolve(path)
    if not p.exists():
        return {}
    return json.loads(p.read_text(encoding="utf-8"))

def read_geojson(path: str) -> dict:
    return read_json(path)

# -------------------- Escrita (mínimo necessário) --------------------

def write_csv(df: pd.DataFrame, path: str, index: bool = False) -> Path:
    p = resolve(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(p, index=index)
    return p

def write_json(obj: Any, path: str) -> Path:
    p = resolve(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding="utf-8")
    return p