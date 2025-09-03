import json
import pydeck as pdk
import pandas as pd
import streamlit as st

def _guess_latlon_cols(df: pd.DataFrame):
    if df is None or df.empty: return None, None
    cand = [("lat","lon"),("latitude","longitude"),("y","x")]
    cols = {c.lower(): c for c in df.columns}
    for la, lo in cand:
        if la in cols and lo in cols:
            return cols[la], cols[lo]
    return None, None

def _normalize_text(s): return (str(s).strip().lower()) if s is not None else ""

def heatmap_from_counts(base_df: pd.DataFrame, ufs_df: pd.DataFrame, mun_df: pd.DataFrame,
                        value_col: str = "weight", label: str = "Eventos"):
    """
    Recebe um DF com colunas ['uf','municipio', value_col] e desenha um Heatmap.
    Faz merge com coordenadas por município (se houver), senão por UF.
    """
    lat_mun, lon_mun = _guess_latlon_cols(mun_df)
    lat_uf, lon_uf = _guess_latlon_cols(ufs_df)

    if base_df is None or base_df.empty:
        st.info("Sem dados para o mapa.")
        return

    use_mun = lat_mun and lon_mun and ("nome_mun" in getattr(mun_df, "columns", []))
    if use_mun:
        mun_aux = mun_df.copy()
        mun_aux["_key"] = mun_aux["nome_mun"].map(_normalize_text) + "||" + mun_aux["uf"].map(_normalize_text)
        base_df = base_df.copy()
        base_df["_key"] = base_df["municipio"].map(_normalize_text) + "||" + base_df["uf"].map(_normalize_text)
        heat_df = base_df.merge(
            mun_aux[["_key", lat_mun, lon_mun, "nome_mun", "uf"]],
            on="_key", how="left"
        ).dropna(subset=[lat_mun, lon_mun])
        tooltip = {"html": f"<b>Município:</b> {{nome_mun}} {{uf}}<br/><b>{label}:</b> {{{value_col}}}"}
        lon_col, lat_col = lon_mun, lat_mun
    else:
        if not (lat_uf and lon_uf and ("uf" in getattr(ufs_df, "columns", []))):
            st.warning("Inclua colunas lat/lon em `ufs.csv` para habilitar o mapa.")
            return
        ufs_aux = ufs_df.copy()
        ufs_aux["_key"] = ufs_aux["uf"].map(_normalize_text)
        base_df = base_df.copy()
        base_df["_key"] = base_df["uf"].map(_normalize_text)
        heat_df = base_df.merge(
            ufs_aux[["_key", lat_uf, lon_uf, "uf"]],
            on="_key", how="left"
        ).dropna(subset=[lat_uf, lon_uf])
        tooltip = {"html": f"<b>UF:</b> {{uf}}<br/><b>{label}:</b> {{{value_col}}}"}
        lon_col, lat_col = lon_uf, lat_uf

    layer = pdk.Layer(
        "HeatmapLayer",
        data=heat_df,
        get_position=f"[{lon_col}, {lat_col}]",
        get_weight=value_col,
        radiusPixels=40,
        intensity=1.0,
        threshold=0.03,
    )
    view = pdk.ViewState(latitude=-14.235, longitude=-51.925, zoom=3.5)
    deck = pdk.Deck(layers=[layer], initial_view_state=view,
                    tooltip=tooltip,
                    map_style="https://basemaps.cartocdn.com/gl/positron-gl-style/style.json")
    st.pydeck_chart(deck, use_container_width=True)

def geojson_layer(geojson_path: str, stroke_width: int = 1):
    """
    Desenha um GeoJsonLayer a partir de um arquivo. Útil p/ UCs, Territórios etc.
    """
    try:
        gj = json.loads(open(geojson_path, "r", encoding="utf-8").read())
    except FileNotFoundError:
        st.warning(f"GeoJSON não encontrado: {geojson_path}")
        return

    layer = pdk.Layer(
        "GeoJsonLayer",
        data=gj,
        pickable=True,
        stroked=True,
        filled=True,
        extruded=False,
        wireframe=False,
        get_line_width=stroke_width,
    )
    view = pdk.ViewState(latitude=-7.5, longitude=-54.0, zoom=4.2)
    deck = pdk.Deck(layers=[layer], initial_view_state=view,
                    map_style="https://basemaps.cartocdn.com/gl/positron-gl-style/style.json")
    st.pydeck_chart(deck, use_container_width=True)
