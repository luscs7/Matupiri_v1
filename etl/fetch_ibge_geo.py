# etl/fetch_ibge_geo.py
import argparse
import csv
from pathlib import Path

import requests

UF_URL = "https://servicodados.ibge.gov.br/api/v1/localidades/estados?orderBy=nome"
MUN_URL = "https://servicodados.ibge.gov.br/api/v1/localidades/municipios?orderBy=nome&view=nivelado"


def fetch_json(url: str):
    r = requests.get(url, timeout=60)
    r.raise_for_status()
    return r.json()


def save_csv(path: Path, rows, fieldnames):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        for row in rows:
            w.writerow({k: row.get(k) for k in fieldnames})


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--out-dir", default="data/processed", help="Diretório de saída")
    args = parser.parse_args()
    out_dir = Path(args.out_dir)

    # UFs
    ufs = fetch_json(UF_URL)
    ufs_norm = [{"uf_id": u["id"], "uf_sigla": u["sigla"], "uf_nome": u["nome"]} for u in ufs]
    save_csv(out_dir / "ufs.csv", ufs_norm, ["uf_id", "uf_sigla", "uf_nome"])
    print(f"[OK] ufs.csv ({len(ufs_norm)} linhas)")

    # Municípios (view nivelado)
    muns = fetch_json(MUN_URL)
    muns_norm = []
    for m in muns:
    # Campos típicos no 'view=nivelado':
    # "id", "nome", "UF-id", "UF-sigla", "UF-nome", ...
        muns_norm.append({
            "mun_id": m.get("id"),
            "mun_nome": m.get("nome"),
            "uf_id": m.get("UF-id"),
            "uf_sigla": m.get("UF-sigla"),
            "uf_nome": m.get("UF-nome"),
    })
    save_csv(out_dir / "municipios.csv", muns_norm, ["mun_id", "mun_nome", "uf_id", "uf_sigla", "uf_nome"])
    print(f"[OK] municipios.csv ({len(muns_norm)} linhas)")


if __name__ == "__main__":
    main()