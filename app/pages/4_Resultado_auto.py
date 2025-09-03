from __future__ import annotations
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd
import streamlit as st

# ===============================================================
# Caminhos
# ===============================================================
REPO_ROOT = Path(__file__).resolve().parents[2]
APP_DIR   = Path(__file__).resolve().parents[1]
DATA_DIR  = REPO_ROOT / "data"
RAW_DIR   = DATA_DIR / "raw" / "policies_source"
PROFILE_DIR = DATA_DIR / "processed" / "profiles"
PROFILE_ACTIVE_JSON = PROFILE_DIR / "profile_active.json"

PAGE_TITLE = "Resultado automático"
st.set_page_config(page_title=PAGE_TITLE, layout="wide")
st.title(PAGE_TITLE)
DEBUG = st.toggle("🔎 Debug", value=False, help="Exibe estados para diagnóstico (não mostra o JSON do perfil)")

# ===============================================================
# Integrações tolerantes (opcional; não exige login)
# ===============================================================
try:
    from db import (get_profiles_by_account, load_profile)
except Exception:
    def get_profiles_by_account(account_id: str) -> List[Dict[str, Any]]: return []
    def load_profile(profile_id: str) -> Dict[str, Any]: return {}

# ===============================================================
# IO helpers
# ===============================================================
def _normalize(df: Optional[pd.DataFrame]) -> pd.DataFrame:
    if df is None:
        return pd.DataFrame()
    df = df.copy()
    df.columns = [str(c).strip() for c in df.columns]
    return df

def _read_excel_if_exists(p: Path) -> Optional[pd.DataFrame]:
    if p.exists():
        try:
            return pd.read_excel(p)
        except Exception as e:
            st.warning(f"Falha ao ler {p.name}: {e}")
    return None

def _load_first_available(rel_or_patterns: List[str]) -> Optional[pd.DataFrame]:
    exts = (".csv", ".parquet", ".json", ".xlsx")
    cand: List[Path] = []
    for rel in rel_or_patterns:
        base = DATA_DIR / rel
        for ext in exts:
            cand.append(base.with_suffix(ext))
        if any(ch in rel for ch in ["*", "?", "[", "]"]):
            for p in (DATA_DIR / rel).parent.glob((DATA_DIR / rel).name + "*"):
                if p.suffix.lower() in exts:
                    cand.append(p)
    seen = set()
    cand = [p for p in cand if not (str(p) in seen or seen.add(str(p)))]
    for p in cand:
        if p.exists():
            try:
                if p.suffix.lower() == ".csv":     return pd.read_csv(p)
                if p.suffix.lower() == ".parquet": return pd.read_parquet(p)
                if p.suffix.lower() == ".json":    return pd.DataFrame(json.load(open(p, "r", encoding="utf-8")))
                if p.suffix.lower() == ".xlsx":    return pd.read_excel(p)
            except Exception as e:
                st.warning(f"Falha ao ler {p.name}: {e}")
    return None

# ===============================================================
# Carregamento preferencial RAW (e estruturas auxiliares)
# ===============================================================
# guardaremos os documentos exigidos para checagem de presença
docs_by_policy: Dict[Any, List[Tuple[str, bool]]] = {}

def load_from_raw_source() -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    global docs_by_policy

    df_policies      = _normalize(_read_excel_if_exists(RAW_DIR / "policies.xlsx"))
    df_requirements  = _normalize(_read_excel_if_exists(RAW_DIR / "policy_requirements.xlsx"))
    df_contacts      = _normalize(_read_excel_if_exists(RAW_DIR / "policy_contacts.xlsx"))
    df_docs          = _normalize(_read_excel_if_exists(RAW_DIR / "policy_documents.xlsx"))
    df_fin           = _normalize(_read_excel_if_exists(RAW_DIR / "policy_financial_params.xlsx"))
    df_regions       = _normalize(_read_excel_if_exists(RAW_DIR / "policy_regions.xlsx"))
    df_regs_all      = _normalize(_read_excel_if_exists(RAW_DIR / "policy_regulations_all.xlsx"))
    df_subprograms   = _normalize(_read_excel_if_exists(RAW_DIR / "policy_subprograms.xlsx"))
    df_reqs_contacts = _normalize(_read_excel_if_exists(RAW_DIR / "policy_requirements_contacts.xlsx"))

    if df_policies.empty:
        return pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), pd.DataFrame()

    # ----- Policies -----
    low = {c.lower(): c for c in df_policies.columns}
    rename = {}
    for a, b in [
        ("name","policy_name"), ("nome","policy_name"), ("titulo","policy_name"), ("título","policy_name"),
        ("description","description"), ("descricao","description"), ("descrição","description"), ("resumo","description"),
    ]:
        if a in low: rename[low[a]] = b
    if "policy_id" not in low and "id" in low:
        rename[low["id"]] = "policy_id"
    policies_df = df_policies.rename(columns=rename).copy()
    if "policy_id" not in policies_df.columns:
        policies_df["policy_id"] = range(1, len(policies_df) + 1)
    if "policy_name" not in policies_df.columns:
        raise ValueError("policies.xlsx precisa ter 'policy_name' (ou Nome/Título).")

    # ----- Requirements -----
    reqs_df = pd.DataFrame(columns=["policy_id","attribute","operator","value","mandatory_flag"])
    if not df_requirements.empty:
        low = {c.lower(): c for c in df_requirements.columns}
        colmap = {
            low.get("policy_id","policy_id"): "policy_id",
            low.get("attribute","attribute"): "attribute",
            low.get("operator","operator"): "operator",
            low.get("value","value"): "value",
        }
        reqs_df = df_requirements.rename(columns=colmap)
        if "mandatory_flag" not in reqs_df.columns:
            for cand in ["mandatory_flag","obrigatorio","obrigatório","required"]:
                if cand in low:
                    reqs_df["mandatory_flag"] = df_requirements[low[cand]]
                    break
            else:
                reqs_df["mandatory_flag"] = True
        reqs_df["mandatory_flag"] = reqs_df["mandatory_flag"].astype(str).str.lower().isin(["1","true","sim","yes"])

    # ----- Contacts (contacts + requirements_contacts) -----
    contacts_df = pd.DataFrame(columns=["policy_id","org_name","phone","email","url","notes"])
    if not df_contacts.empty:
        low = {c.lower(): c for c in df_contacts.columns}
        colmap = {}
        for src, dst in [
            ("policy_id","policy_id"),
            ("org_name","org_name"), ("organization","org_name"), ("org","org_name"),
            ("phone","phone"), ("telefone","phone"), ("contato","phone"),
            ("email","email"),
            ("url","url"), ("site","url"),
            ("notes","notes"), ("obs","notes"),
        ]:
            if src in low: colmap[low[src]] = dst
        contacts_df = df_contacts.rename(columns=colmap)
    if not df_reqs_contacts.empty:
        low = {c.lower(): c for c in df_reqs_contacts.columns}
        colmap = {}
        for src, dst in [
            ("policy_id","policy_id"),
            ("org_name","org_name"), ("organization","org_name"), ("org","org_name"),
            ("phone","phone"), ("telefone","phone"), ("contato","phone"),
            ("email","email"),
            ("url","url"), ("site","url"),
            ("notes","notes"), ("obs","notes"),
        ]:
            if src in low: colmap[low[src]] = dst
        extra = df_reqs_contacts.rename(columns=colmap)
        contacts_df = pd.concat([contacts_df, extra], ignore_index=True).drop_duplicates()

    # ----- Info agregada + DOCS obrigatórios -----
    info_rows: List[Tuple[Any, str, str]] = []
    docs_by_policy = {}

    if not df_docs.empty:
        low = {c.lower(): c for c in df_docs.columns}
        k_doc = low.get("doc_name") or low.get("documento") or low.get("doc")
        k_mand = low.get("mandatory_flag") or low.get("obrigatorio") or low.get("obrigatório") or low.get("required")

        for _, r in df_docs.iterrows():
            pid = r.get("policy_id")
            dname = str(r.get(k_doc) or "").strip()
            mand = bool(str(r.get(k_mand, "false")).strip().lower() in ["1","true","sim","yes"])
            if dname:
                # guarda para checagem de presença no perfil
                docs_by_policy.setdefault(pid, []).append((dname, mand))
                # e também adiciona nas informações importantes (só para leitura)
                info_rows.append((pid, "Documento exigido", dname + (" (obrigatório)" if mand else "")))

    if not df_fin.empty:
        low = {c.lower(): c for c in df_fin.columns}
        kcol = low.get("param_name") or low.get("param") or low.get("chave")
        vcol = low.get("param_value") or low.get("valor") or low.get("value")
        for _, r in df_fin.iterrows():
            info_rows.append((r.get("policy_id"), str(r.get(kcol) or "Parâmetro financeiro"), str(r.get(vcol) or "")))

    if not df_regions.empty:
        grp = df_regions.groupby("policy_id")
        for pid, g in grp:
            nm = "region_name" if "region_name" in g.columns else ("uf" if "uf" in g.columns else None)
            if nm:
                regs = ", ".join(sorted({str(x) for x in g[nm] if pd.notna(x)}))
                if regs:
                    info_rows.append((pid, "Abrangência", regs))

    if not df_regs_all.empty:
        grp = df_regs_all.groupby("policy_id")
        nm = "regulation" if "regulation" in df_regs_all.columns else ("lei" if "lei" in df_regs_all.columns else None)
        for pid, g in grp:
            bases = "; ".join([str(x) for x in (g[nm] if nm else []) if pd.notna(x)]) if nm else ""
            if bases:
                info_rows.append((pid, "Base legal", bases))

    if not df_subprograms.empty:
        grp = df_subprograms.groupby("policy_id")
        nm = "subprogram_name" if "subprogram_name" in df_subprograms.columns else ("nome_subprograma" if "nome_subprograma" in df_subprograms.columns else None)
        for pid, g in grp:
            subs = ", ".join([str(x) for x in (g[nm] if nm else []) if pd.notna(x)]) if nm else ""
            if subs:
                info_rows.append((pid, "Subprogramas", subs))

    info_df = pd.DataFrame(info_rows, columns=["policy_id","info_key","info_value"]) if info_rows else pd.DataFrame()
    return policies_df, reqs_df, info_df, contacts_df

def raw_source_available() -> bool:
    return RAW_DIR.exists() and any(RAW_DIR.glob("*.xlsx"))

# ===============================================================
# Carregamento (RAW primeiro; depois fallback)
# ===============================================================
if raw_source_available():
    try:
        policies_df, reqs_df, info_df, contacts_df = load_from_raw_source()
    except Exception as e:
        st.error(f"Falha ao ler data/raw/policies_source: {e}")
        policies_df = None
        reqs_df = info_df = contacts_df = None
else:
    policies_df = None

if policies_df is None or policies_df.empty:
    policies_df = _load_first_available([
        "policies", "policy_index", "01_policies",
        "processed/policies", "processed/policy_index",
        "politicas", "processed/politicas",
        "programas", "processed/programas",
        "policy*", "processed/policy*",
        "politic*", "processed/politic*",
    ])

if policies_df is None or policies_df.empty:
    st.error(
        f"Não encontrei a tabela de políticas. Coloque seus arquivos em {RAW_DIR} "
        "ou crie 'policies/politicas/programas' em /data (CSV/JSON/Parquet/XLSX)."
    )
    if DEBUG:
        st.write({"DATA_DIR": str(DATA_DIR), "RAW_DIR": str(RAW_DIR), "cwd": str(Path.cwd())})
    st.stop()

policies_df = _normalize(policies_df)
rename_map = {
    "name": "policy_name", "nome": "policy_name", "titulo": "policy_name", "título": "policy_name",
    "nome_politica": "policy_name", "titulo_politica": "policy_name",
    "descr": "description", "descricao": "description", "descrição": "description", "resumo": "description",
}
for k, v in rename_map.items():
    if k in policies_df.columns and v not in policies_df.columns:
        policies_df = policies_df.rename(columns={k: v})
if "policy_id" not in policies_df.columns:
    if "id" in policies_df.columns:
        policies_df = policies_df.rename(columns={"id": "policy_id"})
    else:
        policies_df["policy_id"] = range(1, len(policies_df) + 1)
if "policy_name" not in policies_df.columns:
    st.error("A tabela de políticas precisa ter 'policy_name' (ou Nome/Título).")
    st.stop()

if 'reqs_df' not in locals() or reqs_df is None:
    reqs_df = _load_first_available([
        "policy_requirements", "requirements", "02_policy_requirements",
        "processed/policy_requirements", "processed/requirements",
        "requisit*", "processed/requisit*",
    ]) or pd.DataFrame(columns=["policy_id","attribute","operator","value","mandatory_flag"])
reqs_df = _normalize(reqs_df)
if "mandatory_flag" not in reqs_df.columns:
    reqs_df["mandatory_flag"] = True

if 'info_df' not in locals() or info_df is None:
    info_df = _load_first_available([
        "policy_info", "03_policy_info",
        "processed/policy_info", "info", "processed/info",
    ]) or pd.DataFrame(columns=["policy_id","info_key","info_value"])
info_df = _normalize(info_df) if not info_df.empty else info_df

if 'contacts_df' not in locals() or contacts_df is None:
    contacts_df = _load_first_available([
        "policy_contacts", "contacts", "04_policy_contacts",
        "processed/policy_contacts", "processed/contacts",
    ]) or pd.DataFrame(columns=["policy_id","org_name","phone","email","url","notes"])
contacts_df = _normalize(contacts_df) if not contacts_df.empty else contacts_df

# índices auxiliares
reqs_by_policy: Dict[Any, pd.DataFrame] = {pid: g for pid, g in reqs_df.groupby("policy_id")} if len(reqs_df) else {}
info_by_policy: Dict[Any, pd.DataFrame] = {pid: g for pid, g in (info_df.groupby("policy_id") if not info_df.empty else [])} if info_df is not None and len(info_df) else {}
contacts_by_policy: Dict[Any, pd.DataFrame] = {pid: g for pid, g in (contacts_df.groupby("policy_id") if not contacts_df.empty else [])} if contacts_df is not None and len(contacts_df) else {}

# ===============================================================
# Obter PERFIL (sem login obrigatório)
# ===============================================================
profile_data: Dict[str, Any] = {}

# 1) ?profile_id=... (se houver db)
qp = {}
try:
    qp = dict(getattr(st, "query_params", {}) or st.experimental_get_query_params())
except Exception:
    pass
param_profile_id = (qp.get("profile_id")[0] if isinstance(qp.get("profile_id"), list) else qp.get("profile_id")) if qp.get("profile_id") else None
if param_profile_id:
    try:
        tmp = load_profile(str(param_profile_id)) or {}
        if tmp:
            profile_data = tmp
            st.session_state["selected_profile"] = param_profile_id
    except Exception:
        pass

# 2) sessão (da página de cadastro)
if not profile_data and isinstance(st.session_state.get("profile"), dict) and st.session_state["profile"]:
    profile_data = st.session_state["profile"]

# 3) arquivo salvo pelo Cadastro
if not profile_data and PROFILE_ACTIVE_JSON.exists():
    try:
        profile_data = json.load(open(PROFILE_ACTIVE_JSON, "r", encoding="utf-8"))
    except Exception as e:
        if DEBUG: st.warning(f"Falha ao ler {PROFILE_ACTIVE_JSON.name}: {e}")

# 4) upload manual (sidebar)
with st.sidebar:
    with st.expander("Ou carregue um JSON de perfil (chave → valor)"):
        uploaded = st.file_uploader("perfil.json", type=["json"], accept_multiple_files=False)
        if uploaded is not None:
            try:
                tmp = json.load(uploaded)
                if tmp:
                    profile_data = tmp
                    sel_id = tmp.get("id") or tmp.get("profile_id") or tmp.get("profile_code")
                    if sel_id:
                        st.session_state["selected_profile"] = sel_id
                        try:
                            st.query_params["profile_id"] = str(sel_id)
                        except Exception:
                            st.experimental_set_query_params(profile_id=str(sel_id))
                    st.success("Perfil carregado do arquivo.")
            except Exception as e:
                st.error(f"Não foi possível ler o JSON: {e}")

if not profile_data:
    st.warning("Nenhum perfil ativo. Volte ao Cadastro, selecione/edite um perfil, ou faça upload de JSON na barra lateral.")
    if DEBUG:
        st.write({
            "selected_profile": st.session_state.get("selected_profile"),
            "DATA_DIR": str(DATA_DIR), "RAW_DIR": str(RAW_DIR),
            "PROFILE_ACTIVE_JSON": str(PROFILE_ACTIVE_JSON),
        })
    st.stop()

# >>> NÃO mostramos o JSON do perfil na tela principal (pedido do usuário) <<<

# ===============================================================
# Motor de avaliação
# ===============================================================
@dataclass
class RequirementResult:
    passed: bool
    message: str
    is_mandatory: bool

@dataclass
class PolicyMatch:
    policy_id: Any
    policy_name: str
    description: str
    info_rows: List[Tuple[str, str]]
    contacts: List[Dict[str, Any]]
    eligible: bool
    near_miss: bool
    missing: List[str]
    details: List[str]
    score_passed: int
    score_total: int

def _coerce_numeric(x: Any) -> Optional[float]:
    try: return float(x)
    except Exception: return None

def _value_in(left: Any, right: Any) -> bool:
    if isinstance(right, (list, tuple, set)): return left in right
    if isinstance(right, str):
        items = [s.strip() for s in re.split(r",|;|\|", right) if s.strip()]
        return str(left) in items
    return False

def _contains_text(container: Any, needle: str) -> bool:
    if container is None: return False
    if isinstance(container, str): return needle.lower() in container.lower()
    if isinstance(container, (list, tuple, set)):
        return any(_contains_text(x, needle) for x in container)
    return needle.lower() in str(container).lower()

def _eval_operator(attr_value: Any, operator: str, expected: Any) -> bool:
    op = (operator or "").strip().lower()
    lv, rv = _coerce_numeric(attr_value), _coerce_numeric(expected)

    if op in {"==","=","eq"}:  return str(attr_value) == str(expected)
    if op in {"!=","<>","ne"}: return str(attr_value) != str(expected)
    if op in {">=","ge"} and lv is not None and rv is not None: return lv >= rv
    if op in {"<=","le"} and lv is not None and rv is not None: return lv <= rv
    if op in {">","gt"} and lv is not None and rv is not None:  return lv >  rv
    if op in {"<","lt"} and lv is not None and rv is not None:  return lv <  rv
    if op in {"in","∈"}:      return _value_in(attr_value, expected)
    if op in {"not in","∉"}:  return not _value_in(attr_value, expected)
    if op in {"contains","has","∋"}:      return _contains_text(attr_value, str(expected))
    if op in {"not contains","!contains"}: return not _contains_text(attr_value, str(expected))
    if op in {"regex","match"}:
        try:
            pat = re.compile(str(expected))
            return bool(pat.search(str(attr_value)))
        except Exception:
            return False
    return False

def evaluate_policies(profile: Dict[str, Any]) -> List[PolicyMatch]:
    results: List[PolicyMatch] = []

    # docs presentes no perfil
    profile_docs: Dict[str, bool] = {k: bool(v) for k, v in (profile.get("docs") or {}).items()}

    for _, row in policies_df.iterrows():
        pid = row.get("policy_id")
        pname = row.get("policy_name") or str(pid)
        pdesc = row.get("description") or "(sem descrição)"

        info_rows: List[Tuple[str, str]] = []
        if pid in info_by_policy:
            g = info_by_policy[pid]
            kcol = "info_key" if "info_key" in g.columns else ("key" if "key" in g.columns else "label")
            vcol = "info_value" if "info_value" in g.columns else ("value" if "value" in g.columns else "text")
            for _, ir in g.iterrows():
                k = str(ir.get(kcol) or "Informação")
                v = str(ir.get(vcol) or "")
                info_rows.append((k, v))

        contacts: List[Dict[str, Any]] = []
        if pid in contacts_by_policy:
            g = contacts_by_policy[pid].rename(columns={
                "organization": "org_name",
                "org": "org_name",
                "telefone": "phone",
                "contato": "phone",
                "site": "url",
            }).copy()
            for _, cr in g.iterrows():
                contacts.append({
                    "org_name": cr.get("org_name"),
                    "phone": cr.get("phone"),
                    "email": cr.get("email"),
                    "url": cr.get("url"),
                    "notes": cr.get("notes"),
                })

        missing: List[str] = []
        details: List[str] = []
        passed_count = 0
        total_checks = 0
        hard_fail = False  # se algum requisito obrigatório falhar

        # 1) Requisitos declarados em policy_requirements
        req_rows = reqs_by_policy.get(pid)
        if req_rows is not None and len(req_rows):
            for _, r in req_rows.iterrows():
                attr = str(r.get("attribute") or "").strip()
                op   = str(r.get("operator") or "").strip()
                exp  = r.get("value")
                mand = bool(r.get("mandatory_flag"))

                val = profile.get(attr)
                ok = _eval_operator(val, op, exp)
                total_checks += 1
                if ok:
                    passed_count += 1
                    details.append(f"✓ {attr} {op} {exp}")
                else:
                    details.append(f"✗ {attr} {op} {exp} (atual: {val})")
                    if mand:
                        hard_fail = True
                        missing.append(f"{attr} {op} {exp}")

        # 2) Documentos obrigatórios (do policy_documents.xlsx)
        doc_reqs = docs_by_policy.get(pid, [])
        for dname, mand in doc_reqs:
            # checa presença exata pelo nome do catálogo do cadastro
            has_doc = bool(profile_docs.get(dname, False))
            total_checks += 1
            if has_doc:
                passed_count += 1
                details.append(f"✓ doc: {dname}")
            else:
                details.append(f"✗ doc: {dname}")
                if mand:
                    hard_fail = True
                    missing.append(f"Documento obrigatório: {dname}")

        # decide status
        eligible = (not hard_fail)
        # "Quase lá" = falhou poucos obrigatórios (<=2) OU só docs faltando (até 2)
        near_miss = False
        if not eligible:
            mand_missing = [m for m in missing if m.lower().startswith("documento obrigatório") or True]
            if 0 < len(mand_missing) <= 2:
                near_miss = True

        results.append(PolicyMatch(
            policy_id=pid,
            policy_name=str(pname),
            description=str(pdesc),
            info_rows=info_rows,
            contacts=contacts,
            eligible=eligible,
            near_miss=near_miss and not eligible,
            missing=missing,
            details=details,
            score_passed=passed_count,
            score_total=max(1, total_checks),
        ))

    return results

matches = evaluate_policies(profile_data)

# ===============================================================
# Filtros & resumo
# ===============================================================
left, right = st.columns([1, 2])
with left:
    show_eligible   = st.checkbox("Mostrar elegíveis", value=True)
    show_nearmiss   = st.checkbox("Mostrar 'Quase lá'", value=True)
    show_not_elig   = st.checkbox("Mostrar não elegíveis", value=False)
    show_debug      = st.checkbox("Exibir detalhes (debug)", value=False)

def status_key(m: PolicyMatch) -> Tuple[int, float, str]:
    # ordena por: estado (Elegível < Quase lá < Não), depois score (desc), nome
    state_rank = 0 if m.eligible else (1 if m.near_miss else 2)
    score = m.score_passed / max(1, m.score_total)
    return (state_rank, -score, m.policy_name.lower())

filtered = []
for m in matches:
    if m.eligible and not show_eligible: continue
    if (not m.eligible and m.near_miss) and not show_nearmiss: continue
    if (not m.eligible and not m.near_miss) and not show_not_elig: continue
    filtered.append(m)

matches_sorted = sorted(filtered, key=status_key)

total = len(matches)
eligible_n = sum(1 for m in matches if m.eligible)
near_n = sum(1 for m in matches if (not m.eligible and m.near_miss))
st.caption(f"{eligible_n} elegíveis, {near_n} 'quase lá', de {total} políticas avaliadas.")

# ===============================================================
# Renderização
# ===============================================================
def _badge(text: str, style: str):
    return f'<span style="font-size:.8rem;padding:.2rem .6rem;border-radius:999px;border:1px solid #e5e7eb;{style}">{text}</span>'

def render_policy_card(m: PolicyMatch):
    if m.eligible:
        tag = _badge("Elegível", "background:#ecfdf5;color:#065f46;border-color:#a7f3d0;")
    elif m.near_miss:
        tag = _badge("Quase lá", "background:#fff7ed;color:#92400e;border-color:#fed7aa;")
    else:
        tag = _badge("Não elegível", "background:#fef2f2;color:#991b1b;border-color:#fecaca;")

    st.markdown(
        f"""
<div style="border:1px solid #e5e7eb;border-radius:1rem;padding:1rem;margin-bottom:1rem;background:#fff;">
  <div style="display:flex;gap:.5rem;align-items:center;justify-content:space-between;flex-wrap:wrap;">
    <h3 style="margin:0;">{m.policy_name}</h3>
    <div style="display:flex;gap:.5rem;align-items:center;">
      {tag}
      <span style="font-size:.8rem;color:#6b7280;">{m.score_passed}/{m.score_total} requisitos</span>
    </div>
  </div>
  <p style="margin:.5rem 0 0 0;color:#374151;">{m.description}</p>
""",
        unsafe_allow_html=True,
    )

    # Informações importantes (mostra as 6 primeiras; expande para ver todas)
    if m.info_rows:
        head = m.info_rows[:6]
        if head:
            st.markdown("**Informações importantes**")
            for k, v in head:
                st.markdown(f"- **{k}:** {v}")
        if len(m.info_rows) > 6:
            with st.expander("Ver mais informações"):
                for k, v in m.info_rows[6:]:
                    st.markdown(f"- **{k}:** {v}")

    # Contatos
    if m.contacts:
        with st.expander("Contatos para mais informações", expanded=True if m.near_miss else False):
            for c in m.contacts:
                parts = []
                if c.get("org_name"): parts.append(f"**{c['org_name']}**")
                if c.get("phone"):    parts.append(f"📞 {c['phone']}")
                if c.get("email"):    parts.append(f"✉️ {c['email']}")
                if c.get("url"):      parts.append(f"🔗 {c['url']}")
                if c.get("notes"):    parts.append(f"_({c['notes']})_")
                st.markdown(" • ".join(parts))

    # Pendências (curtas) e detalhes opcionais
    if (not m.eligible) and m.missing:
        resumen = "; ".join(m.missing[:3]) + ("..." if len(m.missing) > 3 else "")
        st.warning(f"Pendências: {resumen}")

    if show_debug and m.details:
        with st.expander("Detalhes de avaliação (debug)"):
            for d in m.details:
                st.code(d)

    st.markdown("</div>", unsafe_allow_html=True)

for m in matches_sorted:
    render_policy_card(m)

# ===============================================================
# Exportar CSV
# ===============================================================
export_rows = [{
    "policy_id": m.policy_id,
    "policy_name": m.policy_name,
    "status": ("Elegível" if m.eligible else ("Quase lá" if m.near_miss else "Não elegível")),
    "score": f"{m.score_passed}/{m.score_total}",
    "missing": "; ".join(m.missing),
    "description": m.description,
    "info": "; ".join([f"{k}: {v}" for k, v in m.info_rows]),
    "contacts": "; ".join([
        ", ".join(filter(None, [
            c.get("org_name") and f"Org: {c['org_name']}",
            c.get("phone") and f"Tel: {c['phone']}",
            c.get("email") and f"Email: {c['email']}",
            c.get("url") and f"URL: {c['url']}",
        ])) for c in m.contacts
    ]),
} for m in matches_sorted]

if export_rows:
    export_df = pd.DataFrame(export_rows)
    st.download_button(
        "Baixar resultados (CSV)",
        data=export_df.to_csv(index=False).encode("utf-8"),
        file_name="resultado_auto.csv",
        mime="text/csv",
    )
