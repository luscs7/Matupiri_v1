from __future__ import annotations
from typing import Dict, Iterable, List, Tuple
import re
import unicodedata
import pandas as pd

FIELDS_TO_SCAN = [
    "Politicas publicas",
    "Descrição dos direitos",
    "Acesso",
    "Organização interna (Subprogramas e/ou Eixos)",
]

def _norm(s: str) -> str:
    if s is None:
        return ""
    s = str(s).lower()
    s = "".join(ch for ch in unicodedata.normalize("NFKD", s) if not unicodedata.combining(ch))
    return re.sub(r"[^a-z0-9\s]", " ", s)

def _tokenize(q: str) -> List[str]:
    return [t for t in _norm(q).split() if t]

def build_index(df: pd.DataFrame, extra_synonyms: Dict[str, Iterable[str]] | None = None) -> pd.DataFrame:
    """
    Cria uma coluna 'search_text' concatenando campos relevantes e, opcionalmente,
    injeta sinônimos (ex.: 'cadunico' ~ 'cad-único').
    Retorna um DataFrame com a coluna adicional, sem alterar o original.
    """
    if df is None or df.empty:
        return pd.DataFrame()
    view = df.copy()
    def _row_text(row):
        parts = []
        for c in FIELDS_TO_SCAN:
            if c in row and pd.notna(row[c]):
                parts.append(str(row[c]))
        return _norm(" | ".join(parts))
    view["search_text"] = view.apply(_row_text, axis=1)

    # injeta sinônimos no texto de busca (simples)
    if extra_synonyms:
        for key, syns in extra_synonyms.items():
            k = _norm(key)
            for s in syns or []:
                s_norm = _norm(s)
                if s_norm and k != s_norm:
                    view["search_text"] = view["search_text"].str.replace(fr"\b{k}\b", f"{k} {s_norm}", regex=True)

    return view

def _score_row(text: str, tokens: List[str]) -> int:
    # pontuação simples: soma de ocorrências exatas de cada token
    score = 0
    for t in tokens:
        score += len(re.findall(fr"\b{re.escape(t)}\b", text))
    return score

def search_policies(index_df: pd.DataFrame, query: str, levels: Iterable[str] | None = None, top: int = 50) -> pd.DataFrame:
    """
    Busca simples por tokens em 'search_text' com filtro opcional de 'nivel'.
    Retorna um DataFrame ordenado por 'score' desc.
    """
    if index_df is None or index_df.empty or not query:
        return index_df.head(0)

    tokens = _tokenize(query)
    if not tokens:
        return index_df.head(0)

    view = index_df.copy()
    if levels and "nivel" in view.columns:
        view = view[view["nivel"].isin(list(levels))]

    view["score"] = view["search_text"].apply(lambda txt: _score_row(txt, tokens))
    view = view[view["score"] > 0].sort_values("score", ascending=False)
    return view.head(int(top))
