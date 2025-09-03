from __future__ import annotations
from datetime import date
import pandas as pd
from app.services.defeso_calendar import filter_defesos, active_defesos_on

def test_filter_and_active_defesos_on():
    df = pd.DataFrame([
        {"especie":"Camarão", "nome_popular":"camarão", "arte_pesca":"rede", "uf":"PA",
         "inicio":"2025-08-01", "fim":"2025-09-15", "esfera":"Federal", "fundamento_legal":"IN nº 1", "link_oficial":""},
        {"especie":"Peixe", "nome_popular":"tambaqui", "arte_pesca":"anzol", "uf":"AM",
         "inicio":"2025-01-01", "fim":"2025-02-01", "esfera":"Estadual", "fundamento_legal":"IN nº 2", "link_oficial":""},
    ])
    # ativos em 2025-08-10
    act = active_defesos_on(df, date(2025,8,10))
    assert len(act) == 1 and act.iloc[0]["uf"] == "PA"

    # filtro por UF e arte
    filt = filter_defesos(df, uf="PA", arte_query="re")
    assert len(filt) == 1 and filt.iloc[0]["especie"] == "Camarão"
