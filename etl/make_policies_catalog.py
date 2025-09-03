# etl/make_policies_catalog.py
from __future__ import annotations
import argparse, json, re
from pathlib import Path
from typing import Iterable, Dict, List, Optional, Tuple

import pandas as pd

# -------------- Config --------------
# Diretórios e padrões de arquivos lidos
INCLUDE_EXTS = {".xlsx", ".xlsm", ".xls", ".csv", ".tsv", ".txt"}

# Mapeamento de nomes de colunas (variações -> padronizado)
ALIASES: Dict[str, Iterable[str]] = {
    "policy_id": [
        "policy_id", "id", "código", "codigo", "número", "numero", "cod"
    ],
    "policy_name": [
        "policy_name", "política", "politica", "nome", "titulo", "título",
        "políticas públicas", "politicas publicas"
    ],
    "level": [
        "nivel", "nível", "coverage_level", "alcance", "abrangencia", "abrangência"
    ],
    "execution": [
        "operacionalização/aplicação", "execução", "operacionalizacao", "aplicacao",
        "como funciona", "implementação", "implementacao"
    ],
    "rights_desc": [
        "descrição dos direitos", "descricao dos direitos", "beneficios", "benefícios",
        "o que oferece", "direitos"
    ],
    "access": [
        "acesso", "como acessar", "requisitos gerais", "critérios gerais", "criterios gerais"
    ],
    "internal_org": [
        "organização interna (subprogramas e/ou eixos)", "organizacao interna",
        "subprogramas", "eixos", "estrutura interna", "organização interna"
    ],
    "link": [
        "link", "url", "site", "fonte", "pagina oficial", "página oficial"
    ],
    "notes": [
        "observações", "observacoes", "notas", "comentarios", "comentários", "obs"
    ],
}

# ordem final das colunas
OUTPUT_COLS = [
    "policy_id", "policy_name", "level", "execution", "rights_desc",
    "access", "internal_org", "link", "notes",
    "source_file", "source_sheet"
]

# -----------------------------------

def _norm(s: str) -> str:
    return re.sub(r"\s+", " ", s.strip().lower())

def _standardize_columns(cols: Iterable[str]) -> Dict[str, str]:
    """
    Recebe nomes originais de colunas e devolve um dict {original -> padronizado}
    quando houver match no ALIASES. Colunas não mapeadas permanecem como estão.
    """
    out = {}
    for c in cols:
        cn = _norm(c)
        mapped = None
        for target, variants in ALIASES.items():
            all_names = {target} | { _norm(v) for v in variants }
            if cn in all_names:
                mapped = target
                break
        out[c] = mapped if mapped else c
    return out

def _read_csv_like(path: Path, max_preview_rows: int = 5) -> Optional[pd.DataFrame]:
    """
    Lê CSV/TSV/TXT tentando detectar separador.
    """
    try:
        df = pd.read_csv(path, sep=None, engine="python")
        if df.empty:
            return None
        return df
    except Exception:
        # tenta com ; e \t
        for sep in [";", "\t", ","]:
            try:
                df = pd.read_csv(path, sep=sep)
                if not df.empty:
                    return df
            except Exception:
                continue
    return None

def _read_excel_all_sheets(path: Path) -> List[Tuple[str, pd.DataFrame]]:
    """
    Lê todas as abas do Excel. Retorna lista de (sheet_name, df).
    """
    out = []
    xls = pd.ExcelFile(path)
    for s in xls.sheet_names:
        try:
            df = pd.read_excel(xls, sheet_name=s)
            if not df.empty:
                out.append((s, df))
        except Exception:
            continue
    return out

def _normalize_frame(df: pd.DataFrame, source_file: str, source_sheet: str | None) -> pd.DataFrame:
    """
    Padroniza nomes de colunas, cria o esqueleto com OUTPUT_COLS,
    e adiciona metadados de origem.
    """
    if df is None or df.empty:
        return pd.DataFrame(columns=OUTPUT_COLS)

    # renomeia colunas conhecidas
    rename_map = _standardize_columns(df.columns)
    df = df.rename(columns=rename_map)

    # seleciona apenas colunas de interesse (as padronizadas + metadados)
    keep = [c for c in OUTPUT_COLS if c in df.columns]
    # se não tiver id/nome, tenta construir com o que tiver
    if "policy_id" not in df.columns and "policy_name" in df.columns:
        # gera id sintético a partir do nome (não ideal, mas impede perda de linhas)
        df["policy_id"] = (
            df["policy_name"].astype(str)
              .str.strip()
              .str.normalize("NFKD")
              .str.encode("ascii", errors="ignore")
              .str.decode("ascii")
              .str.lower()
              .str.replace(r"[^a-z0-9]+", "_", regex=True)
        )
    if "policy_name" not in df.columns and "policy_id" in df.columns:
        df["policy_name"] = df["policy_id"].astype(str)

    # agora limite às colunas relevantes
    cols_present = [c for c in ["policy_id","policy_name","level","execution",
                                "rights_desc","access","internal_org","link","notes"]
                    if c in df.columns]
    df = df[cols_present].copy()

    # limpeza básica
    for c in ["policy_id","policy_name","level","execution","rights_desc","access","internal_org","link","notes"]:
        if c in df.columns:
            df[c] = df[c].astype(str).str.strip()

    # metadados de origem
    df["source_file"] = source_file
    df["source_sheet"] = source_sheet if source_sheet is not None else ""

    # garante as colunas na ordem final (mesmo se ausentes)
    for c in OUTPUT_COLS:
        if c not in df.columns:
            df[c] = pd.NA
    df = df[OUTPUT_COLS]

    # remove linhas completamente vazias (id e nome faltando)
    df = df.dropna(subset=["policy_id","policy_name"], how="all")
    return df

def collect_policies(src_dir: Path) -> pd.DataFrame:
    """
    Varre recursivamente src_dir, lê todos os arquivos suportados,
    normaliza e concatena em um único DataFrame.
    """
    frames: List[pd.DataFrame] = []
    for p in src_dir.rglob("*"):
        if not p.is_file():
            continue
        if p.suffix.lower() not in INCLUDE_EXTS:
            continue

        rel = p.relative_to(src_dir).as_posix()

        if p.suffix.lower() in {".csv",".tsv",".txt"}:
            df = _read_csv_like(p)
            if df is not None and not df.empty:
                frames.append(_normalize_frame(df, source_file=rel, source_sheet=None))

        elif p.suffix.lower() in {".xlsx",".xlsm",".xls"}:
            for sheet, sdf in _read_excel_all_sheets(p):
                if sdf is not None and not sdf.empty:
                    frames.append(_normalize_frame(sdf, source_file=rel, source_sheet=sheet))

    if not frames:
        return pd.DataFrame(columns=OUTPUT_COLS)

    cat = pd.concat(frames, ignore_index=True)

    # deduplicação leve: por (policy_id, policy_name), mantendo a 1ª ocorrência
    # (Você pode mudar a chave conforme sua realidade)
    key_cols = ["policy_id","policy_name"]
    cat = cat.drop_duplicates(subset=key_cols, keep="first")

    # ordena por nome para ficar legível
    cat = cat.sort_values(by=["policy_name","policy_id"], na_position="last", kind="mergesort").reset_index(drop=True)
    return cat

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", default="data/raw/policies_source",
                    help="pasta RAIZ contendo os arquivos/planilhas de políticas (varre recursivamente)")
    ap.add_argument("--out", default="data/processed/politicas_publicas.xlsx",
                    help="arquivo .xlsx de saída (catálogo consolidado, aba 'policies')")
    ap.add_argument("--sheet-name", default="policies", help="nome da aba para salvar no XLSX")
    args = ap.parse_args()

    src_dir = Path(args.src)
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    df = collect_policies(src_dir)
    if df.empty:
        raise SystemExit(f"Nenhum dado de política encontrado em {src_dir}")

    with pd.ExcelWriter(out_path, engine="openpyxl") as writer:
        df.to_excel(writer, sheet_name=args.sheet_name, index=False)

    print(f"✅ salvo {out_path}  ({len(df)} políticas)")

if __name__ == "__main__":
    main()