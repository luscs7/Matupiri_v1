from __future__ import annotations
import logging, os, re, sys
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Optional

import pandas as pd

# ----------------- logging -----------------
def get_logger(name: str = "etl", level: int = logging.INFO) -> logging.Logger:
    logger = logging.getLogger(name)
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        fmt = logging.Formatter("[%(levelname)s] %(message)s")
        handler.setFormatter(fmt)
        logger.addHandler(handler)
    logger.setLevel(level)
    return logger

# ----------------- paths -----------------
def project_root() -> Path:
    return Path(__file__).resolve().parents[1]

def data_dir() -> Path:
    return project_root() / "data"

def processed_dir() -> Path:
    return data_dir() / "processed"

def interim_dir() -> Path:
    return data_dir() / "interim"

def docs_dir() -> Path:
    return data_dir() / "docs"

def ensure_parent(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)

# ----------------- io helpers -----------------
def read_excel(path: Path, sheet: int | str = 0) -> pd.DataFrame:
    df = pd.read_excel(path, sheet_name=sheet, engine="openpyxl")
    df.columns = [str(c).strip() for c in df.columns]
    return df

def write_csv(df: pd.DataFrame, path: Path) -> None:
    ensure_parent(path)
    df.to_csv(path, index=False)

def write_excel(df: pd.DataFrame, path: Path, sheet: str = "Sheet1") -> None:
    ensure_parent(path)
    with pd.ExcelWriter(path, engine="openpyxl") as xw:
        df.to_excel(xw, index=False, sheet_name=sheet)

# ----------------- text/columns -----------------
def norm_token(s: str) -> str:
    return re.sub(r"\s+"," ", re.sub(r"[^a-z0-9_ ]","", (s or "").lower())).strip()

def rename_using_aliases(df: pd.DataFrame, aliases: Dict[str, Iterable[str]]) -> pd.DataFrame:
    mapping: Dict[str, str] = {}
    current = {norm_token(c): c for c in df.columns}
    for canon, al in aliases.items():
        wanted = {norm_token(canon), *[norm_token(a) for a in al]}
        for k, orig in current.items():
            if k in wanted:
                mapping[orig] = canon
    return df.rename(columns=mapping)

@dataclass
class SaveInterim:
    enable: bool = False
    prefix: str = ""

    def save(self, df: pd.DataFrame, name: str) -> None:
        if not self.enable: return
        out = interim_dir() / f"{self.prefix}{name}"
        write_csv(df, out)
