from __future__ import annotations
import pandas as pd
import app.services.policies_engine as pe

def test_evaluate_requirements_wrapper(monkeypatch, keyword_map_dict, profile_ok):
    # stub no motor legado para ficar determinístico
    def fake_eval(txt, profile, km):
        met, missing = [], []
        if "cpf" in txt: met.append("cpf")
        if "rgp" in txt: missing.append("rgp")  # perfil não tem rgp
        if "cadunico" in txt and profile.get("cadunico"): met.append("cadunico")
        return met, missing
    monkeypatch.setattr(pe, "_evaluate_requirements", fake_eval, raising=True)
    met, missing = pe.evaluate_requirements("cpf; cadunico; rgp", profile_ok, keyword_map_dict)
    assert "cpf" in met and "cadunico" in met and "rgp" in missing

def test_batch_evaluate_policies(monkeypatch, keyword_map_dict, profile_ok):
    def fake_eval(txt, profile, km):
        return (["ok"], []) if "cpf" in txt and "rgp" not in txt else (["ok"], ["rgp"])
    monkeypatch.setattr(pe, "_evaluate_requirements", fake_eval, raising=True)

    df = pd.DataFrame([
        {"Acesso": "cpf; cadunico"},     # elegível
        {"Acesso": "rgp; cpf"},          # quase
        {"Acesso": ""},                  # ignora
    ])
    eligible, nearly = pe.batch_evaluate_policies(df, profile_ok, keyword_map_dict)
    assert len(eligible) == 1 and len(nearly) == 1
