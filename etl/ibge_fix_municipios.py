# etl/ibge_fix_municipios.py
# -*- coding: utf-8 -*-
"""
Regera data/ibge/municipios.csv a partir da API IBGE.
Saída: mun_id, mun_nome, uf_id, uf_sigla, uf_nome
"""
from __future__ import annotations
import csv
from pathlib import Path
import requests
import sys

ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "data" / "ibge"
OUT_DIR.mkdir(parents=True, exist_ok=True)
OUT = OUT_DIR / "municipios.csv"

UF_API = "https://servicodados.ibge.gov.br/api/v1/localidades/estados"
MUN_API = "https://servicodados.ibge.gov.br/api/v1/localidades/estados/{uf}/municipios"

def main():
    # UFs
    r = requests.get(UF_API, timeout=30)
    r.raise_for_status()
    ufs = r.json()
    # ordenar por sigla
    ufs = sorted(ufs, key=lambda x: x["sigla"])

    rows = []
    for uf in ufs:
        uf_id = int(uf["id"])
        uf_sigla = uf["sigla"].upper()
        uf_nome = uf["nome"]
        # municípios
        rm = requests.get(MUN_API.format(uf=uf_id), timeout=30)
        rm.raise_for_status()
        for m in rm.json():
            mun_id = int(m["id"])
            mun_nome = m["nome"]
            rows.append([mun_id, mun_nome, uf_id, uf_sigla, uf_nome])

    with OUT.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        w.writerow(["mun_id", "mun_nome", "uf_id", "uf_sigla", "uf_nome"])
        w.writerows(rows)

    print(f"ok: {OUT} ({len(rows)} linhas)")

if __name__ == "__main__":
    main()
