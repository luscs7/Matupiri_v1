# etl/defesos_to_processed.py
# -*- coding: utf-8 -*-
"""
ETL de defesos (costeiros, federais) → CSV tidy.

Uso:
    python -m etl.defesos_to_processed --src data/raw/Defesos --out data/processed/defesos.csv
"""

from __future__ import annotations

import argparse
import re
from datetime import datetime
from pathlib import Path
from typing import Iterable, List, Optional, Sequence, Tuple

import pandas as pd


# ---------------------------- utilidades ---------------------------- #

def log(msg: str) -> None:
    print(f"[defesos_etl] {msg}")

DATE_FMTS = ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%Y/%m/%d")

def norm_date(val) -> Optional[str]:
    """Normaliza (robusto) para ISO YYYY-MM-DD ou retorna None."""
    if val is None or (isinstance(val, float) and pd.isna(val)):
        return None
    if isinstance(val, (pd.Timestamp, datetime)):
        try:
            return pd.to_datetime(val).date().isoformat()
        except Exception:
            return None
    s = str(val).strip()
    if not s:
        return None
    for fmt in DATE_FMTS:
        try:
            return datetime.strptime(s, fmt).date().isoformat()
        except ValueError:
            pass
    # fallback tolerante
    try:
        ts = pd.to_datetime(s, dayfirst=True, errors="coerce")
        return None if pd.isna(ts) else ts.date().isoformat()
    except Exception:
        return None

UF_SPLIT_RE = re.compile(r"[;,]")

def split_ufs(uf_cell) -> List[Optional[str]]:
    """Divide 'AP, PA; MA' → ['AP','PA','MA']. Se vazio, retorna [None] para não perder a linha."""
    if uf_cell is None or (isinstance(uf_cell, float) and pd.isna(uf_cell)):
        return [None]
    parts = UF_SPLIT_RE.split(str(uf_cell))
    parts = [p.strip() for p in parts if p.strip()]
    return parts or [None]

WIN_PAIR_SPLIT = re.compile(r"\s*;\s*")
RANGE_SPLIT = re.compile(r"\s*a\s*|\s*-\s*|\s*–\s*|\s*—\s*")  # 'a', '-', '–', '—'

def parse_windows(ws_cell) -> List[Tuple[str, str]]:
    """
    Converte "2024-12-30 a 2025-01-04; 2025-01-13 a 2025-01-18"
    → [("2024-12-30","2025-01-04"), ("2025-01-13","2025-01-18")]
    Ignora pares inválidos.
    """
    if ws_cell is None or (isinstance(ws_cell, float) and pd.isna(ws_cell)):
        return []
    s = str(ws_cell).strip()
    if not s:
        return []
    pairs = []
    for chunk in WIN_PAIR_SPLIT.split(s):
        chunk = chunk.strip()
        if not chunk:
            continue
        parts = RANGE_SPLIT.split(chunk)
        if len(parts) >= 2:
            s_raw, e_raw = parts[0].strip(), parts[1].strip()
            s_iso, e_iso = norm_date(s_raw), norm_date(e_raw)
            if s_iso and e_iso:
                pairs.append((s_iso, e_iso))
    return pairs

def normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    cols = (
        df.columns.str.strip()
        .str.lower()
        .str.replace(r"\s+", "_", regex=True)
        .str.replace("[()]", "", regex=True)
    )
    df = df.copy()
    df.columns = cols
    # mapear eventuais variações pt/en
    rename_map = {
        "recurso_comum": "resource_common",
        "recurso": "resource_common",
        "nome_comum": "resource_common",
        "arte": "gear_category",
        "categoria_de_arte": "gear_category",
        "unidades_federativas": "uf",
        "unidade_federativa": "uf",
        "periodo_inicio": "start_date",
        "periodo_fim": "end_date",
        "janelas_no_ano": "windows_per_year",
        "ato_legal": "legal_act_number",
        "ato_legal_numero": "legal_act_number",
    }
    for k, v in rename_map.items():
        if k in df.columns and v not in df.columns:
            df = df.rename(columns={k: v})
    return df


def explode_periods_and_ufs(df: pd.DataFrame,
                            source_file: str,
                            source_sheet: Optional[str] = None) -> pd.DataFrame:
    """
    Recebe df com colunas (resource_common, gear_category, uf, start_date, end_date, windows_per_year, legal_act_number)
    e retorna linhas explodidas por UF e por cada janela de 'windows_per_year' (ou start/end).
    """
    keep_cols = [c for c in [
        "resource_common", "gear_category", "uf",
        "start_date", "end_date", "windows_per_year",
        "legal_act_number"
    ] if c in df.columns]
    df = df[keep_cols].copy()

    rows = []
    for _, row in df.iterrows():
        resource = row.get("resource_common")
        gear = row.get("gear_category")
        ufs = split_ufs(row.get("uf"))
        start_iso = norm_date(row.get("start_date"))
        end_iso = norm_date(row.get("end_date"))
        window_pairs = parse_windows(row.get("windows_per_year"))

        if window_pairs:
            periods = window_pairs
            period_source = "windows_per_year"
        elif start_iso and end_iso:
            periods = [(start_iso, end_iso)]
            period_source = "start_end"
        else:
            periods = []
            period_source = "none"

        if not periods:
            # preserva linha sem datas
            for uf in ufs:
                rows.append({
                    "resource_common": resource,
                    "gear_category": gear,
                    "uf": uf,
                    "start_date": None,
                    "end_date": None,
                    "legal_act_number": row.get("legal_act_number"),
                    "period_source": period_source,
                    "source_file": source_file,
                    "source_sheet": source_sheet
                })
        else:
            for uf in ufs:
                for sdt, edt in periods:
                    rows.append({
                        "resource_common": resource,
                        "gear_category": gear,
                        "uf": uf,
                        "start_date": sdt,
                        "end_date": edt,
                        "legal_act_number": row.get("legal_act_number"),
                        "period_source": period_source,
                        "source_file": source_file,
                        "source_sheet": source_sheet
                    })

    out = pd.DataFrame(rows)
    if not out.empty:
        out = out.sort_values(
            ["resource_common", "gear_category", "uf", "start_date"],
            na_position="last"
        ).reset_index(drop=True)
    return out


# ---------------------------- leitores ---------------------------- #

def load_federais(fpath: Path) -> pd.DataFrame:
    log(f"Lendo Federais: {fpath.name}")
    df = pd.read_excel(fpath, sheet_name="defesos")
    df = normalize_columns(df)
    tidy = explode_periods_and_ufs(df, source_file=fpath.name, source_sheet="defesos")
    log(f"Federais → {tidy.shape[0]} linhas")
    return tidy

def load_por_arte(fpath: Path) -> pd.DataFrame:
    log(f"Lendo Por Arte: {fpath.name}")
    xls = pd.ExcelFile(fpath)
    sheets = [s for s in xls.sheet_names if not s.lower().startswith("indice")]
    all_parts = []
    for s in sheets:
        try:
            df = pd.read_excel(fpath, sheet_name=s)
            df = normalize_columns(df)
            # fallback: se não houver gear_category, usa o nome da aba
            if "gear_category" not in df.columns:
                df["gear_category"] = s
            part = explode_periods_and_ufs(df, source_file=fpath.name, source_sheet=s)
            all_parts.append(part)
        except Exception as e:
            log(f"  ! Falha na aba '{s}': {e}")
    out = pd.concat(all_parts, ignore_index=True) if all_parts else pd.DataFrame()
    log(f"Por Arte → {out.shape[0]} linhas")
    return out

# Hook opcional para calendário por UF (layout costuma variar; implementar depois):
def load_calendario_uf(_fpath: Path) -> pd.DataFrame:
    # TODO: implementar parser específico das abas (variam por agrupamentos de UFs e cabeçalhos)
    return pd.DataFrame()


# ---------------------------- pipeline ---------------------------- #

def find_file(src_dir: Path, pattern: str) -> Optional[Path]:
    matches = sorted(src_dir.glob(pattern))
    return matches[0] if matches else None

def run(src_dir: Path, out_csv: Path) -> None:
    src_dir = src_dir.resolve()
    out_csv.parent.mkdir(parents=True, exist_ok=True)

    fed = find_file(src_dir, "defesos_brasil_costeiros_Federais.xlsx")
    por = find_file(src_dir, "defesos_brasil_federais_costeiros_por_arte.xlsx")
    cal = find_file(src_dir, "defesos_brasil_costeiros_calendarioUF.xlsx")  # opcional

    parts: List[pd.DataFrame] = []

    if fed and fed.exists():
        parts.append(load_federais(fed))
    else:
        log("! Federais não encontrado (defesos_brasil_costeiros_Federais.xlsx)")

    if por and por.exists():
        parts.append(load_por_arte(por))
    else:
        log("! Por Arte não encontrado (defesos_brasil_federais_costeiros_por_arte.xlsx)")

    if cal and cal.exists():
        log("(opcional) Calendário UF encontrado; parser ainda não implementado.")
        # parts.append(load_calendario_uf(cal))

    if not parts:
        raise FileNotFoundError("Nenhuma fonte válida encontrada no diretório --src.")

    df = pd.concat(parts, ignore_index=True)
    # Mantém apenas as colunas do esquema final
    final_cols = ["resource_common", "gear_category", "uf", "start_date", "end_date", "legal_act_number"]
    missing = [c for c in final_cols if c not in df.columns]
    if missing:
        # se vieram colunas extras (period_source, source_file, source_sheet) não tem problema
        raise ValueError(f"Colunas ausentes no consolidado: {missing}")

    # Dedup e ordenação
    before = df.shape[0]
    df = df[final_cols].drop_duplicates().sort_values(
        ["resource_common", "gear_category", "uf", "start_date"],
        na_position="last"
    ).reset_index(drop=True)
    after = df.shape[0]
    log(f"Linhas combinadas: {before} → dedup: {after}")

    df.to_csv(out_csv, index=False, encoding="utf-8")
    log(f"✅ salvo {out_csv}  ({after} linhas)")


def parse_args(argv: Optional[Sequence[str]] = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="ETL de defesos (costeiros/federais) → CSV tidy")
    p.add_argument("--src", required=True, help="Diretório com os arquivos xlsx de defeso")
    p.add_argument("--out", required=True, help="Caminho do CSV de saída")
    return p.parse_args(argv)


def main(argv: Optional[Sequence[str]] = None) -> None:
    args = parse_args(argv)
    run(Path(args.src), Path(args.out))


if __name__ == "__main__":
    main()