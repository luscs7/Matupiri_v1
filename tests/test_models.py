from __future__ import annotations
from app.models import Policy, PolicyLevel, UserProfile, Region, Requirement, RequirementType

def test_policy_from_row_and_level_parse():
    row = {
        "Número": "12/2024",
        "Politicas publicas": "Seguro-Defeso",
        "nivel": "federal",
        "Descrição dos direitos": "Benefício no defeso",
        "Acesso": "RGP; CPF regular",
        "Organização interna (Subprogramas e/ou Eixos)": "Regras | Fiscalização",
        "Link": "https://gov.br/x",
        "Observações": "",
    }
    p = Policy.from_row(row)
    assert p.title == "Seguro-Defeso"
    assert p.level == PolicyLevel.FEDERAL
    assert "Regras" in p.axes and "Fiscalização" in p.axes

def test_user_profile_normalization():
    up = UserProfile(estado="pa", municipio=" bragança ", genero=" Feminino ", cpf_ok=True)
    d = up.as_dict()
    assert d["estado"] == "PA"
    assert d["municipio"] == "bragança".strip()
    assert up.get_bool("cpf_ok") is True

def test_region_model():
    r = Region(uf=" pa ", municipio="Bragança", ibge_mun="150170", lat=-1.06, lon=-46.78)
    assert r.uf == "PA"
    assert r.municipio == "Bragança"

def test_requirement_model():
    rq = Requirement(code="cpf", label="CPF válido", profile_field="cpf_ok", type=RequirementType.DOC, any_of="cpf; documento")
    assert rq.type == RequirementType.DOC
    assert "cpf" in rq.any_of
