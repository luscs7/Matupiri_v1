# etl/ibge_from_shapefile.py
# -*- coding: utf-8 -*-
"""
Lê shapefiles IBGE (UF e Municípios), padroniza e exporta:
- data/ibge/ufs.csv
- data/ibge/municipios.csv
- data/geo/ibge/ufs.geojson
- data/geo/ibge/municipios.geojson
"""

from pathlib import Path
import sys


def find(path: Path, patterns: list[str]):
    """Procura arquivos de dados geoespaciais válidos (SHP/GPKG/GeoJSON).
    Ignora sidecars como .cpg/.dbf/.shx/.prj."""
    valid_suffixes = {".shp", ".gpkg", ".geojson"}
    candidates = []
    for p in path.rglob("*"):
        if not p.is_file():
            continue
        if p.suffix.lower() not in valid_suffixes:
            continue
        name = p.name.lower()
        if any(pat in name for pat in patterns):
            candidates.append(p)
    if not candidates:
        return None
    # prefere nomes mais longos (mais específicos); empate: shp > gpkg > geojson
    def score(p: Path):
        prio = {".shp": 3, ".gpkg": 2, ".geojson": 1}.get(p.suffix.lower(), 0)
        return (len(p.name), prio)
    return sorted(candidates, key=score, reverse=True)[0]


def main():
    import geopandas as gpd

    ROOT = Path(__file__).resolve().parents[1]
    raw = ROOT / "data" / "raw" / "ibge"
    out_tab = ROOT / "data" / "ibge"
    out_geo = ROOT / "data" / "geo" / "ibge"
    out_tab.mkdir(parents=True, exist_ok=True)
    out_geo.mkdir(parents=True, exist_ok=True)

    uf_fp = find(raw, ["unidades", "uf_", "br_uf", "federacao", "unidade_federacao"])
    mun_fp = find(raw, ["municip", "br_municip", "municipios", "mun_"])

    print("[IBGE] Procurando arquivos...")
    print("  UF :", uf_fp if uf_fp else "(não encontrado)")
    print("  MUN:", mun_fp if mun_fp else "(não encontrado)")

    if not uf_fp or not uf_fp.exists() or not mun_fp or not mun_fp.exists():
        raise FileNotFoundError(
            f"Não achei shapefile IBGE em {raw}. "
            "Coloque os arquivos de UF e Municípios (SHP/GPKG/GeoJSON) em data/raw/ibge/."
        )

    print(f"[IBGE] Lendo UF: {uf_fp.name}")
    gdf_uf = gpd.read_file(uf_fp)

    print(f"[IBGE] Lendo Municípios: {mun_fp.name}")
    gdf_mun = gpd.read_file(mun_fp)

    # ----------------- normalização de colunas -----------------
    def first_present(cols, *cands):
        low = {c.lower(): c for c in cols}
        for cand in cands:
            if cand.lower() in low:
                return low[cand.lower()]
        return None

    uf_id_col  = first_present(gdf_uf.columns, "CD_UF", "CD_GEOCUF", "ID_UF", "coduf")
    uf_sig_col = first_present(gdf_uf.columns, "SIGLA_UF", "SG_UF", "UF")
    uf_nom_col = first_present(gdf_uf.columns, "NM_UF", "NOME_UF", "NM_ESTADO", "nome")

    if not uf_sig_col:
        raise ValueError(f"Não encontrei coluna de sigla UF em {list(gdf_uf.columns)}")
    if not uf_nom_col:
        uf_nom_col = uf_sig_col
    if not uf_id_col:
        gdf_uf["uf_id_tmp"] = range(1, len(gdf_uf) + 1)
        uf_id_col = "uf_id_tmp"

    gdf_uf_out = gdf_uf.rename(columns={
        uf_id_col:  "uf_id",
        uf_sig_col: "uf_sigla",
        uf_nom_col: "uf_nome",
    })[["uf_id", "uf_sigla", "uf_nome", "geometry"]].copy()
    gdf_uf_out["uf_sigla"] = gdf_uf_out["uf_sigla"].astype(str).str.upper().str.strip()

    mun_id_col  = first_present(gdf_mun.columns, "CD_MUN", "CD_GEOCMU", "ID_MUN", "codmun")
    mun_nom_col = first_present(gdf_mun.columns, "NM_MUN", "NOME", "NM_MUNIC", "municipio")
    mun_ufsig   = first_present(gdf_mun.columns, "SIGLA_UF", "UF", "SG_UF")

    if not mun_nom_col:
        raise ValueError(f"Não encontrei coluna de nome de município em {list(gdf_mun.columns)}")
    if not mun_id_col:
        gdf_mun["mun_id_tmp"] = range(1, len(gdf_mun) + 1)
        mun_id_col = "mun_id_tmp"
    if not mun_ufsig:
        mun_ufsig = first_present(gdf_mun.columns, "NM_UF", "NOME_UF")
        if not mun_ufsig:
            raise ValueError("Não encontrei coluna de UF nos municípios.")

    gdf_mun_out = gdf_mun.rename(columns={
        mun_id_col:  "mun_id",
        mun_nom_col: "mun_nome",
        mun_ufsig:   "uf_sigla"
    })[["mun_id", "mun_nome", "uf_sigla", "geometry"]].copy()
    gdf_mun_out["uf_sigla"] = gdf_mun_out["uf_sigla"].astype(str).str.upper().str.strip()
    gdf_mun_out["mun_nome"] = gdf_mun_out["mun_nome"].astype(str).str.strip()

    gdf_mun_out = gdf_mun_out.merge(
        gdf_uf_out[["uf_id", "uf_sigla", "uf_nome"]].drop_duplicates("uf_sigla"),
        on="uf_sigla", how="left"
    )

    # ----------------- salvar -----------------
    gdf_uf_out.drop(columns="geometry").to_csv(out_tab / "ufs.csv", index=False, encoding="utf-8-sig")
    gdf_mun_out.drop(columns="geometry").to_csv(out_tab / "municipios.csv", index=False, encoding="utf-8-sig")
    print(f"[IBGE] Tabelas salvas em {out_tab}")

    gdf_uf_geo  = gdf_uf_out.to_crs(4326)
    gdf_mun_geo = gdf_mun_out.to_crs(4326)
    gdf_uf_geo["geometry"]  = gdf_uf_geo.geometry.simplify(0.01, preserve_topology=True)
    gdf_mun_geo["geometry"] = gdf_mun_geo.geometry.simplify(0.005, preserve_topology=True)

    gdf_uf_geo.to_file(out_geo / "ufs.geojson", driver="GeoJSON")
    gdf_mun_geo.to_file(out_geo / "municipios.geojson", driver="GeoJSON")
    print(f"[IBGE] GeoJSON salvos em {out_geo}")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print("[ERRO]", e)
        sys.exit(1)

