# etl/make_index.py
from __future__ import annotations
import argparse
from pathlib import Path
import pandas as pd

def norm(s: str) -> str:
    return (
        str(s).strip()
        .replace("\n", " ")
        .replace("\r", " ")
    )

def load_policies_table(xlsx: Path, sheet_name: str | None, id_col: str | None, name_col: str | None) -> pd.DataFrame:
    if not xlsx.exists():
        raise SystemExit(f"Arquivo não encontrado: {xlsx}")
    xls = pd.ExcelFile(xlsx)
    sheet = sheet_name or ("policies" if "policies" in [s.lower() for s in xls.sheet_names] else xls.sheet_names[0])
    df = pd.read_excel(xlsx, sheet_name=sheet, engine="openpyxl")
    cols = [c.strip().lower() for c in df.columns]
    df.columns = cols

    # Se vier de make_policies_catalog.py, já teremos 'policy_id' e 'policy_name'
    if "policy_id" in df.columns and "policy_name" in df.columns:
        out = df[["policy_id","policy_name"]].copy()
        out["policy_id"] = out["policy_id"].astype(str).str.strip()
        out["policy_name"] = out["policy_name"].map(norm)
        return out

    # Caso contrário, tenta resolver por nomes alternativos ou CLI
    if id_col and id_col.lower() in df.columns:
        pid = id_col.lower()
    else:
        pid = next((c for c in df.columns if c in ("policy_id","id","código","codigo","número","numero","cod")), None)

    if name_col and name_col.lower() in df.columns:
        pname = name_col.lower()
    else:
        pname = next((c for c in df.columns if c in ("policy_name","nome","política","politica","titulo","título","politicas publicas","políticas públicas")), None)

    if not pid or not pname:
        raise SystemExit(f"Colunas essenciais não encontradas em '{sheet}'. Encontrei: {list(df.columns)}")

    out = df[[pid, pname]].copy().rename(columns={pid:"policy_id", pname:"policy_name"})
    out["policy_id"] = out["policy_id"].astype(str).str.strip()
    out["policy_name"] = out["policy_name"].map(norm)
    return out

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--policies", default="data/processed/politicas_publicas.xlsx")
    ap.add_argument("--sheet", default=None, help="nome da aba (default: 'policies' se existir)")
    ap.add_argument("--id-col", default=None)
    ap.add_argument("--name-col", default=None)
    ap.add_argument("--out", default="data/processed/policies_index.csv")
    args = ap.parse_args()

    xlsx = Path(args.policies)
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)

    df = load_policies_table(xlsx, args.sheet, args.id_col, args.name_col)
    if df.empty:
        raise SystemExit("Catálogo de políticas vazio.")

    # índice simples — dá pra enriquecer depois
    df = df.drop_duplicates(subset=["policy_id","policy_name"], keep="first")
    if out.suffix.lower() == ".csv":
        df.to_csv(out, index=False)
    else:
        try:
            import pyarrow  # noqa: F401
            df.to_parquet(out, index=False)
        except Exception as e:
            print(f"[WARN] falha no Parquet ({e}); salvando CSV: {out.with_suffix('.csv')}")
            df.to_csv(out.with_suffix(".csv"), index=False)

    print(f"✅ índice salvo em {out} ({len(df)} linhas)")

if __name__ == "__main__":
    main()