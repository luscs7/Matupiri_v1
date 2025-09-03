from __future__ import annotations
from app.services.search_index import build_index, search_policies
import pandas as pd

def test_build_index_and_search():
    df = pd.DataFrame([{
        "Politicas publicas": "Bolsa Teste",
        "Descrição dos direitos": "Auxílio",
        "Acesso": "cpf; cadunico",
        "Organização interna (Subprogramas e/ou Eixos)": "Eixo A",
        "nivel": "Federal",
    }])
    idx = build_index(df, extra_synonyms={"cadunico": ["cad único", "cad-único"]})
    assert "search_text" in idx.columns and "cad unico" in idx.iloc[0]["search_text"]
    res = search_policies(idx, "cadunico", levels=["Federal"], top=10)
    assert len(res) == 1 and res.iloc[0]["score"] > 0
