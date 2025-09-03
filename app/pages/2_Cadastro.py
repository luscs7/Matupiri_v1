from __future__ import annotations
import json
import sys
from pathlib import Path
from datetime import datetime, timezone
from uuid import uuid4
from typing import Dict, Any

import pandas as pd
import streamlit as st

# --- bootstrap raiz ---
ROOT = Path(__file__).resolve().parents[2]  # .../Matupiri_v1
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# --- componentes (tolerante) ---
try:
    from app.components.layout import header_nav, footer, apply_global_style
except Exception:
    def header_nav(title, subtitle=""): st.title(title); st.caption(subtitle)
    def footer(): st.caption("")
    def apply_global_style(): pass

# --- repositório (tolerante: não quebra se faltar) ---
try:
    from app.data_access.repositories import (
        boot_migrations, save_profile_for_account, update_profile_for_account,
        get_profiles_by_account, load_profile,
    )
    _HAS_REPO = True
except Exception:
    _HAS_REPO = False
    def boot_migrations(): pass
    def save_profile_for_account(*a, **k): pass
    def update_profile_for_account(*a, **k): pass
    def get_profiles_by_account(*a, **k): return []
    def load_profile(*a, **k): return {}

# =========================
# Helpers de UF/Municípios
# =========================
@st.cache_data(show_spinner=False)
def _load_ufs_muns_from_processed():
    base = ROOT / "data" / "processed" / "ibge"
    uf_csv  = base / "ufs.csv"
    mun_csv = base / "municipios.csv"

    if uf_csv.exists() and mun_csv.exists():
        ufs = pd.read_csv(uf_csv, dtype=str, usecols=["uf","nome_uf"]).fillna("")
        muns = pd.read_csv(mun_csv, dtype=str, usecols=["cod_mun","nome_mun","uf"]).fillna("")
    else:
        ufs = pd.DataFrame([{"uf":"PA","nome_uf":"Pará"},
                            {"uf":"AP","nome_uf":"Amapá"},
                            {"uf":"MA","nome_uf":"Maranhão"}])
        muns = pd.DataFrame([
            {"cod_mun":"150170","nome_mun":"Bragança","uf":"PA"},
            {"cod_mun":"150620","nome_mun":"Salvaterra","uf":"PA"},
            {"cod_mun":"160030","nome_mun":"Macapá","uf":"AP"},
            {"cod_mun":"210300","nome_mun":"Capanema","uf":"MA"},
        ])

    for df in (ufs, muns):
        for c in df.columns:
            df[c] = df[c].astype(str).str.strip()

    ufs = ufs.dropna(subset=["uf"]).drop_duplicates("uf").sort_values("uf")
    muns = muns.dropna(subset=["cod_mun"]).drop_duplicates("cod_mun")
    return ufs, muns

@st.cache_data(show_spinner=False)
def list_ufs_for_select(ufs_df: pd.DataFrame):
    return [f"{row.uf} — {row.nome_uf}" for _, row in ufs_df.iterrows()]

@st.cache_data(show_spinner=False)
def list_municipios_for_uf(muns_df: pd.DataFrame, uf: str):
    df = muns_df[muns_df["uf"] == uf].sort_values("nome_mun")
    return [(f"{r.nome_mun} ({r.cod_mun})", r.cod_mun) for _, r in df.iterrows()]

def _extract_uf_code(label: str) -> str:
    return label.split("—")[0].strip() if "—" in label else label.strip()

# =========================
# Requisitos/documentos
# =========================
@st.cache_data(show_spinner=False)
def _read_csv_smart(path: Path):
    if not path.exists():
        return None
    for enc in ("utf-8-sig","utf-8","latin1"):
        for sep in (",",";"):
            try:
                return pd.read_csv(path, dtype=str, encoding=enc, sep=sep)
            except Exception:
                continue
    return None

@st.cache_data(show_spinner=False)
def load_requisitos_catalogo():
    candidates = [
        ROOT / "data" / "processed" / "policy_documents.csv",
        ROOT / "data" / "processed" / "policies_requirements.csv",
    ]
    for fp in candidates:
        df = _read_csv_smart(fp)
        if df is None:
            continue
        low = {c.lower(): c for c in df.columns}
        doc = low.get("doc_name") or low.get("documento") or low.get("doc")
        desc = low.get("description") or low.get("descricao") or low.get("descrição")
        mand = low.get("mandatory_flag") or low.get("obrigatorio") or low.get("obrigatório") or low.get("required")
        if not doc:
            continue
        keep = [c for c in [doc, desc, mand] if c]
        out = df[keep].copy()
        out.columns = ["doc_name"] + (["description"] if desc else []) + (["mandatory_flag"] if mand else [])
        if "mandatory_flag" in out.columns:
            out["mandatory_flag"] = out["mandatory_flag"].astype(str).str.lower().isin(["1","true","sim","yes"])
        else:
            out["mandatory_flag"] = False
        out["description"] = out.get("description","")
        out = out.dropna(subset=["doc_name"]).drop_duplicates(subset=["doc_name"])
        return out.to_dict(orient="records")

    # fallback amigável
    return [
        {"doc_name": "CAF/DAP ativa (Agricultura Familiar)", "description": "Cadastro da Agricultura Familiar (substitui DAP).", "mandatory_flag": True},
        {"doc_name": "RGP/Registro Pesca", "description": "Registro Geral da Atividade Pesqueira (pessoa física).", "mandatory_flag": True},
        {"doc_name": "Comprovante de residência", "description": "Conta de água/luz, declaração associação, etc.", "mandatory_flag": False},
        {"doc_name": "Comprovante de atividade", "description": "Declaração de colônia/associação; notas de venda, etc.", "mandatory_flag": False},
        {"doc_name": "NIS/PIS", "description": "Número de Identificação Social.", "mandatory_flag": False},
    ]

# =========================
# Persistência do perfil (conversa com Resultado_Auto)
# =========================
PROFILE_DIR = ROOT / "data" / "processed" / "profiles"
PROFILE_DIR.mkdir(parents=True, exist_ok=True)

def _profile_files(code: str):
    return {
        "json": PROFILE_DIR / "profile_active.json",
        "csv":  PROFILE_DIR / "profile_active.csv",
        "timestamped_json": PROFILE_DIR / f"profile_{code}.json",
    }

def _normalize_profile_for_io(p: Dict[str, Any]) -> Dict[str, Any]:
    out = dict(p)
    out["docs_presentes"] = sorted([k for k, v in p.get("docs", {}).items() if v])
    return out

def _generate_profile_code() -> str:
    ts = datetime.now(timezone.utc).strftime("%y%m%d%H%M%S")
    rand = uuid4().hex[:4].upper()
    return f"PRF-{ts}-{rand}"

def _repo_save_flexible(profile: dict, profile_code: str, account_id: str | None = None):
    if not _HAS_REPO:
        return None
    try:
        return save_profile_for_account(profile=profile, profile_code=profile_code, account_id=account_id)
    except TypeError:
        pass
    try:
        return save_profile_for_account(account_id=account_id, profile=profile, code=profile_code)
    except TypeError:
        pass
    try:
        return save_profile_for_account(profile)
    except Exception:
        pass
    try:
        return update_profile_for_account(profile=profile, profile_code=profile_code, account_id=account_id)
    except Exception:
        return None

def persist_profile(account_id: str | None = None) -> dict:
    ensure_profile_state()
    P = st.session_state.profile
    now_iso = datetime.now(timezone.utc).isoformat()
    if not P.get("profile_code"):
        P["profile_code"] = _generate_profile_code()
        P.setdefault("created_at", now_iso)
    P["updated_at"] = now_iso

    if account_id:
        P["owner_account_id"] = account_id
        P.setdefault("account_id", account_id)

    code = P["profile_code"]
    profile_io = _normalize_profile_for_io(P)

    files = _profile_files(code)
    with open(files["json"], "w", encoding="utf-8") as f:
        json.dump(profile_io, f, ensure_ascii=False, indent=2)
    rows = [{"key": k, "value": (", ".join(v) if isinstance(v, (list, tuple, set)) else v)}
            for k, v in profile_io.items()]
    pd.DataFrame(rows).to_csv(files["csv"], index=False, encoding="utf-8")
    with open(files["timestamped_json"], "w", encoding="utf-8") as f:
        json.dump(profile_io, f, ensure_ascii=False, indent=2)

    repo_result = _repo_save_flexible(profile_io, code, account_id=account_id)

    selected_profile_id = None
    if isinstance(repo_result, dict):
        selected_profile_id = repo_result.get("id") or repo_result.get("profile_id") or repo_result.get("uuid")
    selected_profile_id = selected_profile_id or code

    st.session_state["selected_profile"] = selected_profile_id
    try:
        st.query_params["profile_id"] = selected_profile_id
    except Exception:
        st.experimental_set_query_params(profile_id=selected_profile_id)

    return {"profile": profile_io, "profile_code": code, "files": files, "selected_profile_id": selected_profile_id}

# =========================
# Estado / Boot
# =========================
def ensure_boot():
    if "booted_cadastro" not in st.session_state:
        boot_migrations()
        st.session_state.booted_cadastro = True

def ensure_profile_state():
    if "profile" not in st.session_state or not isinstance(st.session_state.profile, dict):
        st.session_state.profile = {}
    P = st.session_state.profile
    P.setdefault("profile_code", "")
    P.setdefault("nome","")
    P.setdefault("genero","")
    P.setdefault("segmento","")
    P.setdefault("cpf_cnpj","")
    P.setdefault("uf","")
    P.setdefault("municipio","")
    P.setdefault("municipio_label","")
    P.setdefault("uf_display","")
    P.setdefault("atividade","")
    P.setdefault("experiencia_anos",0)
    P.setdefault("docs", {})

# =========================
# PÁGINA
# =========================
st.set_page_config(page_title="Matupiri • Cadastro", layout="wide")
apply_global_style()
header_nav("👤 Cadastro", "Seu perfil alimenta o Resultado Automático e o Observatório.")
ensure_boot()
ensure_profile_state()

# ------- Identificação -------
st.subheader("1) Identificação")
c1, c2, c3 = st.columns([3, 2, 2])
with c1:
    st.session_state.profile["nome"] = st.text_input("Nome completo", value=st.session_state.profile.get("nome",""))
with c2:
    st.session_state.profile["genero"] = st.selectbox(
        "Gênero (opcional)",
        options=["", "Mulher", "Homem", "Outro/Prefere não dizer"],
        index=["", "Mulher", "Homem", "Outro/Prefere não dizer"].index(
            st.session_state.profile.get("genero","")) if st.session_state.profile.get("genero","") in ["","Mulher","Homem","Outro/Prefere não dizer"] else 0
    )
with c3:
    st.session_state.profile["segmento"] = st.selectbox(
        "Segmento",
        options=["", "Pessoa Física", "Coletivo/Associação"],
        index=["", "Pessoa Física", "Coletivo/Associação"].index(
            st.session_state.profile.get("segmento","")) if st.session_state.profile.get("segmento","") in ["","Pessoa Física","Coletivo/Associação"] else 0
    )

# ------- Localização -------
st.subheader("2) Localização")
ufs_df, muns_df = _load_ufs_muns_from_processed()
uf_options = [""] + list_ufs_for_select(ufs_df)

uf_display = st.selectbox(
    "UF",
    options=uf_options,
    index= uf_options.index(st.session_state.profile.get("uf_display","")) if st.session_state.profile.get("uf_display","") in uf_options else 0,
)
uf_code = _extract_uf_code(uf_display) if uf_display else ""
st.session_state.profile["uf_display"] = uf_display
st.session_state.profile["uf"] = uf_code

mun_pairs = list_municipios_for_uf(muns_df, uf_code) if uf_code else []
mun_labels = [""] + [lbl for (lbl, _cod) in mun_pairs]
mun_label = st.selectbox(
    "Município",
    options=mun_labels,
    index= mun_labels.index(st.session_state.profile.get("municipio_label","")) if st.session_state.profile.get("municipio_label","") in mun_labels else 0,
)
if mun_label and dict(mun_pairs).get(mun_label):
    st.session_state.profile["municipio"] = dict(mun_pairs)[mun_label]
    st.session_state.profile["municipio_label"] = mun_label
else:
    st.session_state.profile["municipio"] = ""
    st.session_state.profile["municipio_label"] = ""

st.caption("Esses campos serão usados como filtros no **Observatório**.")

# ------- Atividade -------
st.subheader("3) Atividade principal")
colA, colB = st.columns([2, 2])
with colA:
    st.session_state.profile["atividade"] = st.selectbox(
        "Qual a sua atividade principal?",
        options=["", "Pesca artesanal", "Aquicultura", "Agroextrativismo", "Outros"],
        index=["", "Pesca artesanal", "Aquicultura", "Agroextrativismo", "Outros"].index(
            st.session_state.profile.get("atividade","")) if st.session_state.profile.get("atividade","") in ["","Pesca artesanal","Aquicultura","Agroextrativismo","Outros"] else 0
    )
with colB:
    st.session_state.profile["experiencia_anos"] = st.number_input("Há quantos anos você exerce a atividade? (opcional)", min_value=0, max_value=80, value=int(st.session_state.profile.get("experiencia_anos",0)))

# ------- Documentos & Requisitos -------
st.subheader("4) Documentos & Requisitos")
catalogo = load_requisitos_catalogo()
docs_state = st.session_state.profile.get("docs", {})
mand_cols = st.columns(2)
opt_cols = st.columns(2)
mand_i = opt_i = 0

for item in catalogo:
    name = item["doc_name"]
    desc = item.get("description", "")
    is_mand = bool(item.get("mandatory_flag", False))
    prev = bool(docs_state.get(name, False))
    label = f"**{name}**" + (f" — {desc}" if desc else "")
    if is_mand:
        with mand_cols[mand_i % 2]:
            docs_state[name] = st.checkbox(label, value=prev)
            mand_i += 1
    else:
        with opt_cols[opt_i % 2]:
            docs_state[name] = st.checkbox(label, value=prev)
            opt_i += 1

st.session_state.profile["docs"] = docs_state
st.caption("Marque apenas o que você já possui — isso cruza com os **requisitos** das políticas.")
st.divider()

# ------- Ações -------
c1, c2, c3 = st.columns([2,2,3])

with c1:
    if st.button("⚙️ Ver resultado automático"):
        persisted = persist_profile(account_id=st.session_state.get("account_id"))
        st.session_state["profile_code"] = persisted["profile_code"]
        # deep-link
        try:
            st.query_params["profile_id"] = persisted["selected_profile_id"]
        except Exception:
            st.experimental_set_query_params(profile_id=persisted["selected_profile_id"])
        st.switch_page("pages/4_Resultado_auto.py")

with c2:
    if st.button("🧭 Ver resultado manual (por política)"):
        persisted = persist_profile(account_id=st.session_state.get("account_id"))
        st.session_state["profile_code"] = persisted["profile_code"]
        st.switch_page("pages/5_Resultado_manual.py")

with c3:
    if st.button("🔐 Salvar na minha conta"):
        account_id = st.session_state.get("account_id")
        if account_id:
            persisted = persist_profile(account_id=account_id)
            st.session_state["profile_code"] = persisted["profile_code"]
            st.success(f"Perfil vinculado à conta. Código: {persisted['profile_code']}")
        else:
            st.session_state["pending_profile_to_link"] = _normalize_profile_for_io(st.session_state.profile)
            if not st.session_state.profile.get("profile_code"):
                st.session_state.profile["profile_code"] = _generate_profile_code()
            st.session_state["pending_profile_code"] = st.session_state.profile["profile_code"]
            st.switch_page("pages/6_Login_e_Salvar_Perfil.py")

# Debug opcional
if st.toggle("Ver JSON do perfil", value=False):
    st.json(st.session_state.profile, expanded=False)

footer()
