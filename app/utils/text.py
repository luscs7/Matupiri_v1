from __future__ import annotations
import re
import unicodedata
from typing import Iterable, List, Optional

def strip_accents(s: str) -> str:
    if s is None:
        return ""
    return "".join(ch for ch in unicodedata.normalize("NFKD", str(s)) if not unicodedata.combining(ch))

def normalize(s: Optional[str]) -> str:
    """minúsculas, sem acentos e sem pontuação exótica; espaços normalizados"""
    if s is None:
        return ""
    s = strip_accents(str(s).lower())
    s = re.sub(r"[^a-z0-9\s]", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s

def tokenize(s: str) -> List[str]:
    return [t for t in normalize(s).split() if t]

def slugify(s: str) -> str:
    s = normalize(s)
    return s.replace(" ", "-")

def to_bool(v) -> Optional[bool]:
    if v is None: return None
    if isinstance(v, bool): return v
    s = normalize(str(v))
    if s in {"1","true","t","sim","yes","y"}: return True
    if s in {"0","false","f","nao","não","no","n"}: return False
    return None

def safe_int(v, default: Optional[int] = None) -> Optional[int]:
    try:
        if v is None or v == "": return default
        return int(float(str(v)))
    except Exception:
        return default

def safe_float(v, default: Optional[float] = None) -> Optional[float]:
    try:
        if v is None or v == "": return default
        return float(str(v).replace(",", "."))
    except Exception:
        return default
