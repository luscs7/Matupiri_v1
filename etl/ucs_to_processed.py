# etl/ucs_to_processed.py
from __future__ import annotations
import argparse
import re
from pathlib import Path
from typing import Iterable, Dict, Any

import geopandas as gpd
import pandas as pd

# -----------------------------
# Normalização de nomes/alias
# -----------------------------
ALIASES: Dict[str, Iterable[str]] = {
    "nome": ["nome", "nm_uc", "nm_area", "unidade_conservacao", "nm_prot"],
    "categoria": ["categoria", "categoria_uc", "cat", "grupo", "grupo_categoria", "categoria_sigla", "categoria_uc_sigla"],
    "esfera": ["esfera", "jurisdicao", "gestao", "administracao", "administradora", "orgao_gestor", "esfera_adm"],
    "uf": ["uf", "sg_uf", "estado", "sigla_uf"],
    "link": ["link", "url", "fonte", "site"],
}

def _norm(s: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9_ ]", "", s.lower())).strip()

def _rename_like(gdf: gpd.GeoDataFrame, col: str) -> None:
    wanted = {_norm(a) for a in [col] + list(ALIASES.get(col, []))}
    rename_map = {}
    for c in list(gdf.columns):
        if _norm(c) in wanted:
            rename_map[c] = col
    if rename_map:
        gdf.rename(columns=rename_map, inplace=True)

# -----------------------------
# Leitura robusta do SHP
# -----------------------------
def read_shapefile_robust(path: Path) -> gpd.GeoDataFrame:
    """
    Tenta ler o SHP com diferentes estratégias de codificação e engines,
    resolvendo UnicodeDecodeError (UTF-8 vs CP1252/Latin-1) comuns em Windows.
    """
    # 1) tentar padrão (pyogrio) → UTF-8
    try:
        return gpd.read_file(path)
    except Exception:
        pass

    # 2) tentar encodings comuns
    for enc in ("latin1", "cp1252", "iso-8859-1"):
        try:
            return gpd.read_file(path, encoding=enc)
        except Exception:
            continue

    # 3) tentar engine fiona (melhor com SHP antigo/Windows)
    try:
        return gpd.read_file(path, engine="fiona", encoding="latin1")
    except Exception:
        # 4) fallback manual com fiona.open
        import fiona
        with fiona.Env():
            with fiona.open(path, encoding="latin1") as src:
                gdf = gpd.GeoDataFrame.from_features(src, crs=src.crs)
        return gdf

def dedupe_columns(gdf: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    """
    Remove/resolve colunas com nomes duplicados:
      1) Se duas colunas com o MESMO nome têm exatamente o mesmo conteúdo, mantém a primeira e remove as outras.
      2) Caso contrário, renomeia as subsequentes adicionando sufixos _2, _3... (para não perder dados).
    Retorna um novo GeoDataFrame com nomes únicos.
    """
    cols = list(gdf.columns)
    seen = {}
    rename_map = {}
    drop_idxs = set()

    for idx, c in enumerate(cols):
        if c not in seen:
            seen[c] = [idx]
        else:
            seen[c].append(idx)

    # Para cada grupo de duplicatas
    for name, idxs in seen.items():
        if len(idxs) == 1:
            continue

        # Compare conteúdo das duplicatas
        ref_idx = idxs[0]
        ref_series = gdf.iloc[:, ref_idx]
        equal_mask = [ref_series.equals(gdf.iloc[:, i]) for i in idxs]

        # Se todas iguais, drop as extras
        if all(equal_mask):
            for i in idxs[1:]:
                drop_idxs.add(i)
        else:
            # Mantém a primeira; renomeia subsequentes com sufixos
            counter = 2
            for i in idxs[1:]:
                new_name = f"{name}_{counter}"
                while new_name in gdf.columns:
                    counter += 1
                    new_name = f"{name}_{counter}"
                rename_map[cols[i]] = new_name
                counter += 1

    # Aplicar drops e renomes
    if drop_idxs:
        keep_idxs = [i for i in range(len(cols)) if i not in drop_idxs]
        gdf = gdf.iloc[:, keep_idxs].copy()

    if rename_map:
        gdf = gdf.rename(columns=rename_map).copy()

    return gdf

def list_duplicated_cols(df):
    import pandas as pd
    dup = pd.Index(df.columns).duplicated(keep=False)
    return [c for c, d in zip(df.columns, dup) if d]

def force_unique_columns(df):
    """
    Garante nomes únicos SEM perder dados: renomeia repetidos com _2, _3, ...
    (não descarta nenhuma coluna).
    """
    counts = {}
    new_cols = []
    for c in list(df.columns):
        if c in counts:
            counts[c] += 1
            new_cols.append(f"{c}_{counts[c]}")
        else:
            counts[c] = 1
            new_cols.append(c)
    df = df.copy()
    df.columns = new_cols
    return df

# -----------------------------
# Pipeline principal
# -----------------------------
def main(shp_folder: str, out_geojson: str, out_csv: str):
    shp_folder_p = Path(shp_folder)
    shp_files = list(shp_folder_p.glob("*.shp"))
    if not shp_files:
        raise SystemExit(f"Nenhum .shp encontrado em {shp_folder_p}")

    shp_path = shp_files[0]

    # Ler shapefile com tolerância a encoding
    gdf = read_shapefile_robust(shp_path)

    # Garantir geometria válida e não nula
    if "geometry" not in gdf.columns:
        raise SystemExit("Arquivo não possui coluna 'geometry'. Verifique o shapefile.")
    gdf = gdf[~gdf.geometry.is_empty & gdf.geometry.notna()].copy()
    gdf = gdf.explode(index_parts=False, ignore_index=True)

    # Se vier sem CRS, assume SIRGAS 2000 (EPSG:4674), comum em bases nacionais
    if gdf.crs is None:
        gdf.set_crs(4674, inplace=True)

    # Normalizar nomes de colunas importantes
    for k in ["nome", "categoria", "esfera", "uf", "link"]:
        _rename_like(gdf, k)
    
    # Resolver Colunas Duplicadas

    gdf = dedupe_columns(gdf)
    

    # Reprojetar para WGS84 para GeoJSON
    gdf = gdf.to_crs(4326)

    # Calcular área em hectares usando projeção equal-area da América do Sul
    # EPSG:5880 (South America Albers Equal Area Conic)
    try:
        g_area = gdf.to_crs(5880)
        gdf["area_ha"] = g_area.geometry.area / 10_000.0
    except Exception:
        # fallback: sem área se reprojeção falhar
        gdf["area_ha"] = pd.NA

    # --- GUARD 1: tentar coalescer/renomear duplicatas por conteúdo (se você já tinha) ---
    try:
        gdf = dedupe_columns(gdf)  # se você já adicionou anteriormente
    except NameError:
        pass  # caso não tenha a função

    dups = list_duplicated_cols(gdf)
    if dups:
        print("[WARN] colunas duplicadas detectadas (antes do force_unique):", dups)
        gdf = force_unique_columns(gdf)
        # conferir novamente
        dups2 = list_duplicated_cols(gdf)
        if dups2:
            # Em teoria não deve sobrar nenhuma; se sobrar, algo muito anômalo
            raise RuntimeError(f"Ainda há colunas duplicadas mesmo após force_unique: {dups2}")

    # Exportar GeoJSON
    out_geojson_p = Path(out_geojson)
    out_geojson_p.parent.mkdir(parents=True, exist_ok=True)
    gdf.to_file(out_geojson_p, driver="GeoJSON")
    print("✅ geojson:", out_geojson_p)

    # Exportar CSV resumido
    cols = ["nome", "categoria", "esfera", "uf", "area_ha", "link"]
    have = [c for c in cols if c in gdf.columns]
    df = gdf[have].copy()
    out_csv_p = Path(out_csv)
    out_csv_p.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(out_csv_p, index=False)
    print("✅ csv:", out_csv_p, f"({len(df)} linhas)")

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", default="data/raw/UCs/shp_cnuc_2025_03", help="Pasta contendo o .shp")
    ap.add_argument("--geojson", default="data/processed/ucs.geojson")
    ap.add_argument("--csv", default="data/processed/ucs.csv")
    args = ap.parse_args()
    main(args.src, args.geojson, args.csv)