from __future__ import annotations
import sys
from pathlib import Path
import pandas as pd

from etl.common import get_logger, data_dir

try:
    import yaml  # type: ignore
except Exception as e:
    raise SystemExit("Instale pyyaml para usar o validador: pip install pyyaml") from e

def check_columns(df: pd.DataFrame, required: list[str]) -> list[str]:
    missing = [c for c in required if c not in df.columns]
    return missing

def main(contract_path: Path):
    log = get_logger("validate")
    spec = yaml.safe_load(contract_path.read_text(encoding="utf-8"))
    base = data_dir()

    errors = 0

    # policies_xlsx
    pol = spec["policies_xlsx"]
    p_path = base / pol["path"]
    if not p_path.exists():
        log.error(f"Faltando: {p_path}")
        errors += 1
    else:
        df = pd.read_excel(p_path, sheet_name=pol.get("sheet", 0))
        miss = check_columns(df, pol["required_columns"])
        if miss: log.error(f"Colunas faltando em {p_path.name}: {miss}"); errors += 1

    # geo ufs
    ufs = spec["geo_ufs_csv"]
    u_path = base / ufs["path"]
    if not u_path.exists():
        log.error(f"Faltando: {u_path}"); errors += 1
    else:
        df = pd.read_csv(u_path)
        miss = check_columns(df, ufs["required_columns"])
        if miss: log.error(f"Colunas faltando em {u_path.name}: {miss}"); errors += 1

    # geo municipios
    mun = spec["geo_municipios_csv"]
    m_path = base / mun["path"]
    if not m_path.exists():
        log.error(f"Faltando: {m_path}"); errors += 1
    else:
        df = pd.read_csv(m_path)
        miss = check_columns(df, mun["required_columns"])
        if miss: log.error(f"Colunas faltando em {m_path.name}: {miss}"); errors += 1

    # defesos
    d = spec["defesos_csv"]
    d_path = base / d["path"]
    if not d_path.exists():
        log.error(f"Faltando: {d_path}"); errors += 1
    else:
        df = pd.read_csv(d_path)
        miss = check_columns(df, d["required_columns"])
        if miss: log.error(f"Colunas faltando em {d_path.name}: {miss}"); errors += 1

    # ucs csv
    u = spec["ucs_csv"]
    u_csv = base / u["path"]
    if not u_csv.exists():
        log.error(f"Faltando: {u_csv}"); errors += 1
    else:
        df = pd.read_csv(u_csv)
        miss = check_columns(df, u["required_columns"])
        if miss: log.error(f"Colunas faltando em {u_csv.name}: {miss}"); errors += 1

    # ucs geojson
    gj = spec["ucs_geojson"]
    gj_path = base / gj["path"]
    if not gj_path.exists():
        log.error(f"Faltando: {gj_path}"); errors += 1

    if errors:
        sys.exit(1)
    else:
        log.info("✅ Todos os arquivos/colunas essenciais estão OK.")

if __name__ == "__main__":
    contract = data_dir() / "docs" / "data_contracts.yaml"
    main(contract)
