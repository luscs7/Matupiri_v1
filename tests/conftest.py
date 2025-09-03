from __future__ import annotations
import os
from pathlib import Path
import types
import sys
import json
import pytest
import pandas as pd

# ---------- FIXTURES DE DADOS BÁSICOS ----------

@pytest.fixture
def tmpdir_path(tmp_path: Path) -> Path:
    return tmp_path

@pytest.fixture
def keyword_map_dict() -> dict:
    # mapa mínimo só para testes
    return {
        "cpf": {"label": "CPF regular", "profile_field": "cpf_ok", "type": "bool", "tokens": ["cpf", "cpf regular"]},
        "rgp": {"label": "RGP ativo", "profile_field": "rgp", "type": "bool", "tokens": ["rgp", "registro geral da pesca"]},
        "cadunico": {"label": "CadÚnico", "profile_field": "cadunico", "type": "bool", "tokens": ["cadunico", "cad único", "cad-único"]},
    }

@pytest.fixture
def policies_df() -> pd.DataFrame:
    return pd.DataFrame([
        {
            "Número": "01/2025",
            "Politicas publicas": "Bolsa Teste",
            "nivel": "Federal",
            "Operacionalização/Aplicação": "INSS",
            "Descrição dos direitos": "Auxílio financeiro",
            "Acesso": "cpf; cadunico",
            "Organização interna (Subprogramas e/ou Eixos)": "Eixo A; Eixo B",
            "Link": "https://exemplo.gov.br/bolsa",
            "Observações": "",
        },
        {
            "Número": "02/2025",
            "Politicas publicas": "Seguro Defeso Teste",
            "nivel": "Federal",
            "Operacionalização/Aplicação": "MPA",
            "Descrição dos direitos": "Benefício no defeso",
            "Acesso": "rgp; cpf",
            "Organização interna (Subprogramas e/ou Eixos)": "",
            "Link": "https://exemplo.gov.br/defeso",
            "Observações": "",
        },
    ])

@pytest.fixture
def tmp_policies_xlsx(tmpdir_path: Path, policies_df) -> str:
    out = tmpdir_path / "politicas_publicas.xlsx"
    with pd.ExcelWriter(out, engine="openpyxl") as xw:
        policies_df.to_excel(xw, index=False, sheet_name="catalogo")
    return str(out)

@pytest.fixture
def profile_ok() -> dict:
    return {"cpf_ok": True, "cadunico": True, "rgp": False, "estado": "PA", "municipio": "Bragança"}

# ---------- MOCK: DB BRIDGE (evita tocar no SQLite real) ----------

@pytest.fixture(autouse=True)
def mock_db_bridge(monkeypatch):
    """
    Evita que testes acionem o banco real.
    """
    from types import SimpleNamespace
    calls = []
    fake = SimpleNamespace(
        init_db=lambda: calls.append(("init_db",)),
        migrate_db=lambda: calls.append(("migrate_db",)),
        migrate_accounts=lambda: calls.append(("migrate_accounts",)),
        migrate_analytics=lambda: calls.append(("migrate_analytics",)),
        log_event=lambda **kw: calls.append(("log_event", kw)),
        get_analytics=lambda **kw: [],
        create_person_account=lambda *a, **k: {"id": 1, "display_name": "Teste"},
        create_collective_account=lambda *a, **k: {"id": 2, "cnpj": "00000000000000"},
        authenticate_person=lambda *a, **k: {"id": 1, "username": "u"} if a and a[0] == "u" else None,
        authenticate_collective=lambda *a, **k: {"id": 2, "cnpj": "123"} if a and a[0] == "123" else None,
        save_profile_for_account=lambda *a, **k: 42,
        update_profile_for_account=lambda *a, **k: True,
        get_profiles_by_account=lambda *a, **k: [(42, 1, "2025-01-01", "2025-01-02")],
        load_profile=lambda *a, **k: {"estado": "PA", "municipio": "Bragança"},
    )
    import app.data_access.adapters.bridge_legacy_db as bridge
    for attr in vars(fake):
        monkeypatch.setattr(bridge, attr, getattr(fake, attr), raising=True)

# ---------- AJUSTES DE AMBIENTE PARA PATHS ----------
@pytest.fixture(autouse=True)
def ensure_env_paths(tmpdir_path: Path, monkeypatch):
    # Redireciona POLICIES_XLSX para o tmp (quando usado nos testes)
    monkeypatch.setenv("POLICIES_XLSX", str(tmpdir_path / "politicas_publicas.xlsx"), prepend=False)

# ---------- UTIL: MOCK STREAMLIT PARA TESTES DE PÁGINA ----------
@pytest.fixture
def mock_streamlit(monkeypatch):
    """
    Injeta um módulo 'streamlit' mínimo em sys.modules para importar páginas sem rodar Streamlit.
    """
    st = types.SimpleNamespace()
    # funções básicas usadas nas páginas
    def _noop(*a, **k): return None
    def _cols(n): return [types.SimpleNamespace()] * n
    st.set_page_config = _noop
    st.title = _noop
    st.caption = _noop
    st.divider = _noop
    st.write = _noop
    st.markdown = _noop
    st.subheader = _noop
    st.columns = _cols
    st.button = lambda *a, **k: False
    st.page_link = _noop
    st.sidebar = types.SimpleNamespace()
    st.sidebar.header = _noop
    st.sidebar.write = _noop
    st.session_state = {}
    st.cache_data = lambda **k: (lambda f: f)
    st.cache_resource = lambda **k: (lambda f: f)
    st.pydeck_chart = _noop
    st.container = lambda **k: types.SimpleNamespace(__enter__=lambda s: s, __exit__=lambda *e: False)
    st.tabs = lambda labels: [types.SimpleNamespace()]
    st.selectbox = lambda *a, **k: (k.get("options", [""])[0] if "options" in k else None)
    st.multiselect = lambda *a, **k: []
    st.number_input = lambda *a, **k: 10
    st.text_input = lambda *a, **k: ""
    st.checkbox = lambda *a, **k: False
    st.form = lambda name: types.SimpleNamespace(__enter__=lambda s: s, __exit__=lambda *e: False)
    sys.modules["streamlit"] = st
    return st
