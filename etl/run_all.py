import subprocess
import sys

def main():
    STEPS = [
    ["python", "-m", "etl.fetch_ibge_geo", "--out-dir", "data/processed"],
    ["python", "-m", "etl.defesos_to_processed", "--src", "data/raw/Defesos", "--out", "data/processed/defesos.csv"],
    ["python", "-m", "etl.ucs_to_processed", "--src", "data/raw/UCs/shp_cnuc_2025_03",
     "--geojson", "data/processed/ucs.geojson", "--csv", "data/processed/ucs.csv"],

    # >>> NOVO: varrer *raiz* de políticas, recursivo
    ["python", "-m", "etl.make_policies_catalog", "--src", "data/raw/policies_source",
     "--out", "data/processed/politicas_publicas.xlsx"],

    # índice (CSV, sem depender de pyarrow)
    ["python", "-m", "etl.make_index", "--policies", "data/processed/politicas_publicas.xlsx",
     "--out", "data/processed/policies_index.csv"],
]

    for cmd in STEPS:
        print("→", " ".join(cmd))
        res = subprocess.run(cmd)
        if res.returncode != 0:
            print("✖ etapa falhou:", " ".join(cmd))
            sys.exit(1)

if __name__ == "__main__":
    main()