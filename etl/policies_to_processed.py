# etl/policies_to_processed.py
r"""
Consolida políticas a partir de Matupiri_v1\\data\\raw\\policies_source
e gera:
  - data/processed/policies_master.csv
  - data/processed/policy_regulations.csv

Uso:
    python -m etl.policies_to_processed
"""
from __future__ import annotations
from pathlib import Path
import re
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = ROOT / "data" / "raw" / "policies_source"
OUT_DIR = ROOT / "data" / "processed"
OUT_DIR.mkdir(parents=True, exist_ok=True)

def _xlsx(path: Path) -> pd.DataFrame:
    xls = pd.ExcelFile(path)
    return xls.parse(xls.sheet_names[0])

def _load_or_empty(p: Path) -> pd.DataFrame:
    if not p.exists():
        return pd.DataFrame()
    if p.suffix.lower() in (".xlsx", ".xls"):
        return _xlsx(p)
    return pd.read_csv(p, dtype=str)

# ----------------- Normalizações ----------------- #

_ACRONYM_MAP = {
    # Federações comuns
    "ministério do meio ambiente e mudança do clima": "MMA",
    "ministério do meio ambiente": "MMA",
    "ministério da pesca e aquicultura": "MPA",
    "ministério do trabalho e emprego": "MTE",
    "ministério do desenvolvimento agrário e agricultura familiar": "MDA",
    "instituto nacional do seguro social": "INSS",
    "banco central do brasil": "BCB",
    "ministério da cidadania": "MCID",
    # Pará (exemplos)
    "secretaria de estado de meio ambiente e sustentabilidade": "SEMAS/PA",
    "secretaria de estado de desenvolvimento econômico, mineração e energia": "SEDEME/PA",
    "secretaria de desenvolvimento agropecuário e da pesca": "SEDAP/PA",
}

_SPLIT_STOP_WORDS = (
    " em articulação", "articulação com", " em parceria", " parceria com",
    " executado por", " executor", " implementa", " implementado por",
    " coordenação", " com apoio", " apoio de", " juntamente com"
)

def normalize_nivel(raw: str) -> str:
    if not isinstance(raw, str):
        return ""
    s = raw.strip().lower()
    if not s:
        return ""
    # mapeamentos
    if any(k in s for k in ("federal", "nacional", "união", "brasil")):
        return "Nacional"
    if any(k in s for k in ("estadual", "estado", "uf", "secretaria de estado")):
        return "Estadual"
    if any(k in s for k in ("regional", "amazônia", "amazonia", "bioma", "interfederativo", "consórcio")):
        return "Regional"
    # último recurso: capitaliza
    return s.capitalize()

def _first_chunk(text: str) -> str:
    """Retorna o primeiro trecho antes de conectivos/complementos comuns."""
    s = text
    for key in _SPLIT_STOP_WORDS:
        idx = s.lower().find(key)
        if idx != -1:
            s = s[:idx]
    # também corta em separadores comuns
    s = re.split(r"[;|,]", s)[0]
    return s.strip()

def _first_acronym(text: str) -> str | None:
    """
    Tenta extrair a primeira sigla relevante (ex.: SEMAS/PA, MPA, MDA, INSS).
    - aceita combinações com / e hífen.
    """
    # prioriza padrões com UF anexada (SEMAS/PA)
    m = re.search(r"\b([A-Z]{2,}(?:/[A-Z]{2,})+)\b", text)
    if m:
        return m.group(1).upper()
    # senão, pega a primeira sigla simples com 2+ letras
    m = re.search(r"\b([A-Z]{2,})\b", text)
    if m:
        return m.group(1).upper()
    return None

def normalize_responsavel(raw: str) -> str:
    """
    Mantém somente o órgão preponente:
    - remove trechos de 'em articulação', 'executado por', etc.
    - tenta usar sigla oficial (SEMAS/PA, MMA, MPA, MDA, INSS…)
    - se não houver sigla, mantém o primeiro trecho limpo.
    """
    if not isinstance(raw, str):
        return ""
    s = raw.strip()
    if not s:
        return ""

    # 1) corta complementos (executores, articulações)
    s0 = _first_chunk(s)

    # 2) se já tiver sigla explícita, usa a primeira
    acr = _first_acronym(s0)
    if acr:
        # normaliza separadores / e -
        acr = acr.replace("–", "-").replace("—", "-")
        return acr

    # 3) tenta mapear pelo nome por extenso -> sigla
    key = s0.lower()
    for full_name, ac in _ACRONYM_MAP.items():
        if full_name in key:
            return ac

    # 4) se nada encontrado, devolve o trecho em Title Case simplificado
    return re.sub(r"\s+", " ", s0).strip().title()

# ------------------------------------------------ #

def run() -> None:
    # Arquivos esperados (podem faltar; tratamos vazio):
    files = {
        "policies": RAW_DIR / "policies.xlsx",
        "contacts": RAW_DIR / "policy_contacts.xlsx",
        "requirements": RAW_DIR / "policy_requirements.xlsx",
        "regulations": RAW_DIR / "policy_regulations_all.xlsx",
        "financial": RAW_DIR / "policy_financial_params.xlsx",
        "subprograms": RAW_DIR / "policy_subprograms.xlsx",
    }

    pol = _load_or_empty(files["policies"]).copy()
    if pol.empty or not {"Policy_id", "name"}.issubset(set(pol.columns)):
        raise RuntimeError(
            f"Catálogo base inválido/ausente: {files['policies']} — esperadas as colunas 'Policy_id' e 'name'."
        )

    contacts = _load_or_empty(files["contacts"]).copy()
    regs     = _load_or_empty(files["regulations"]).copy()
    req      = _load_or_empty(files["requirements"]).copy()
    finp     = _load_or_empty(files["financial"]).copy()
    subs     = _load_or_empty(files["subprograms"]).copy()

    pol.columns = [c.strip() for c in pol.columns]

    base_df = pd.DataFrame({
        "policy_id": pol["Policy_id"].astype(str).str.strip(),
        "nome": pol.get("name", "").astype(str).str.strip(),
        "nivel": pol.get("coverage_level", "").astype(str),
        "tipo_beneficio": pol.get("benefit_type", "").astype(str),
        "responsavel": pol.get("managing_body", "").astype(str),
        "descricao": pol.get("benefit_summary", "").astype(str),
        "info_url": pol.get("source_of_truth_url", "").astype(str),
    })

    # Normalizações principais
    base_df["nivel"] = base_df["nivel"].map(normalize_nivel)
    base_df["responsavel"] = base_df["responsavel"].map(normalize_responsavel)

    # Contatos
    if not contacts.empty:
        contacts.columns = [c.strip().lower() for c in contacts.columns]
        grp = contacts.groupby("policy_id", dropna=True)
        def _compact(series):
            vals = [str(x).strip() for x in series if str(x).strip() and str(x).strip().lower() != "nan"]
            return "; ".join(sorted(set(vals)))
        cmap = grp.agg({
            "phone": _compact if "phone" in contacts.columns else lambda s: "",
            "email": _compact if "email" in contacts.columns else lambda s: "",
            "url":   _compact if "url"   in contacts.columns else lambda s: "",
        }).reset_index().rename(columns={"url": "contact_site"})
        base_df = base_df.merge(cmap, on="policy_id", how="left")
    else:
        base_df["phone"] = ""
        base_df["email"] = ""
        base_df["contact_site"] = ""

    # Requisitos -> resumo 'criterios'
    if not req.empty:
        req.columns = [c.strip().lower() for c in req.columns]
        def summarize_requirements(df):
            parts = []
            for _, r in df.iterrows():
                name = str(r.get("requirement_name","") or "").strip()
                desc = str(r.get("requirement_description","") or "").strip()
                mandatory = str(r.get("mandatory_flag","") or "").strip()
                txt = "- " + (name if name else desc if desc else "").strip()
                if not txt.strip("- ").strip():
                    continue
                if mandatory and mandatory.lower() in ("y","yes","sim","true","1"):
                    txt += " (obrigatório)"
                parts.append(txt)
            return "\n".join(parts[:8])

        try:
            req_sum = req.groupby("policy_id").apply(
                summarize_requirements, include_groups=False
            ).reset_index(name="criterios")
        except TypeError:
            req_sum = req.groupby("policy_id", group_keys=False).apply(
                summarize_requirements
            ).reset_index(name="criterios")

        base_df = base_df.merge(req_sum, on="policy_id", how="left")
    else:
        base_df["criterios"] = ""

    # Regulamentos -> legislação principal
    if not regs.empty:
        regs.columns = [c.strip().lower() for c in regs.columns]
        def pick_best_regs(df):
            d = df.copy()
            d["citation"] = d["citation"].astype(str)
            d["url"] = d["url"].astype(str)
            d["regulation_type"] = d["regulation_type"].astype(str)
            d["has_url"] = d["url"].str.len() > 0
            d["kw"] = d["regulation_type"].str.lower().str.contains("lei|decreto|portaria|instru", na=False)
            d["citlen"] = d["citation"].str.len()
            d = d.sort_values(["has_url","kw","citlen"], ascending=[False, False, False])
            top = d.iloc[0]
            return pd.Series({
                "legislacao_titulo": str(top.get("citation","")),
                "legislacao_url": str(top.get("url",""))
            })

        try:
            regs_best = regs.groupby("policy_id").apply(
                pick_best_regs, include_groups=False
            ).reset_index()
        except TypeError:
            regs_best = regs.groupby("policy_id", group_keys=False).apply(
                pick_best_regs
            ).reset_index()

        base_df = base_df.merge(regs_best, on="policy_id", how="left")

        regs_out = regs[["policy_id","regulation_type","citation","url","notes"]].copy()
        regs_out.to_csv(OUT_DIR / "policy_regulations.csv", index=False, encoding="utf-8")
    else:
        base_df["legislacao_titulo"] = ""
        base_df["legislacao_url"] = ""

    # Financeiros -> resumo
    if not finp.empty:
        finp.columns = [c.strip().lower() for c in finp.columns]
        def financial_blurb(dfg):
            vals = []
            for _, r in dfg.iterrows():
                name = str(r.get("param_name","") or "").strip()
                val  = str(r.get("param_value","") or "").strip()
                if name or val:
                    vals.append(f"• {name}: {val}".strip(": "))
            return "\n".join(vals[:8])

        try:
            fin_sum = finp.groupby("policy_id").apply(
                financial_blurb, include_groups=False
            ).reset_index(name="financas_resumo")
        except TypeError:
            fin_sum = finp.groupby("policy_id", group_keys=False).apply(
                financial_blurb
            ).reset_index(name="financas_resumo")

        base_df = base_df.merge(fin_sum, on="policy_id", how="left")
    else:
        base_df["financas_resumo"] = ""

    # Subprogramas
    if not subs.empty:
        subs.columns = [c.strip().lower() for c in subs.columns]
        if "subprogram_name" in subs.columns:
            subs_sum = subs.groupby("policy_id")["subprogram_name"].apply(
                lambda s: ", ".join(sorted(set([str(x).strip() for x in s if str(x).strip()])))
            ).reset_index(name="subprogramas")
            base_df = base_df.merge(subs_sum, on="policy_id", how="left")
        else:
            base_df["subprogramas"] = ""
    else:
        base_df["subprogramas"] = ""

    # Como acessar (texto curto)
    def build_howto(row):
        tips = []
        if isinstance(row.get("criterios",""), str) and row["criterios"].strip():
            tips.append("Confira os critérios listados.")
        if isinstance(row.get("info_url",""), str) and row["info_url"].strip():
            tips.append("Acesse a página oficial (Mais informações).")
        if isinstance(row.get("contact_site",""), str) and row["contact_site"].strip():
            tips.append("Use o site de atendimento informado.")
        if isinstance(row.get("phone",""), str) and row["phone"].strip():
            tips.append(f"Telefones: {row['phone']}.")
        if isinstance(row.get("email",""), str) and row["email"].strip():
            tips.append(f"E-mails: {row['email']}.")
        return " ".join(tips)

    base_df["como_acessar"] = base_df.apply(build_howto, axis=1)

    # Ordena e grava
    cols = ["policy_id","nome","nivel","tipo_beneficio","responsavel",
            "descricao","criterios","legislacao_titulo","legislacao_url",
            "info_url","phone","email","contact_site","financas_resumo","subprogramas","como_acessar"]
    for c in cols:
        if c not in base_df.columns: base_df[c] = ""
    base_df = base_df[cols].fillna("")
    base_df = base_df.sort_values(["nivel","responsavel","nome","policy_id"])
    base_df.to_csv(OUT_DIR / "policies_master.csv", index=False, encoding="utf-8")

    print(f"[OK] policies_master.csv -> {OUT_DIR / 'policies_master.csv'}  ({len(base_df)} linhas)")

if __name__ == "__main__":
    run()