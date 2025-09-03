# Matupiri • Observatório (com choropleth por UF usando uf_sigla no GeoJSON)
from datetime import datetime, timedelta, timezone
import json
import hashlib
from pathlib import Path

import pandas as pd
import pydeck as pdk
import streamlit as st
import streamlit as st

def ensure_boot():
    if "booted_obs" not in st.session_state:
        from app.data_access.repositories import boot_migrations
        boot_migrations()
        st.session_state.booted_obs = True


# --- bootstrap para permitir 'from app. ...' ---
import sys
ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
# ------------------------------------------------

from app.components.layout import header_nav, footer, apply_global_style
from app.data_access.repositories import boot_migrations, get_analytics
from app.services.geo import load_geo  # mantém tua função

# --------------------------------------------------------------------------------------
# Helpers
# --------------------------------------------------------------------------------------

def _normalize_text(s): 
    return (str(s).strip().lower()) if s is not None else ""

def _guess_latlon_cols(df):
    if df is None or df.empty: 
        return None, None
    cand = [("lat","lon"),("latitude","longitude"),("y","x")]
    cols = {c.lower(): c for c in df.columns}
    for la, lo in cand:
        if la in cols and lo in cols: 
            return cols[la], cols[lo]
    return None, None

@st.cache_data(show_spinner=False)
def _load_ufs_geojson():
    """
    Tenta obter o GeoJSON de UFs de 3 jeitos:
      1) via load_geo() (se ele já devolver o caminho/objeto)
      2) arquivo local data/geo/ibge/ufs.geojson
      3) None (sem choropleth; cai em fallback de heatmap)
    Retorno: (geojson_dict | None)
    """
    # 1) tenta pela tua função load_geo (3º retorno pode ser dict com caminhos)
    try:
        ufs_df, mun_df, extra = load_geo()
        if isinstance(extra, (dict, list)):
            # tenta chave óbvia
            if isinstance(extra, dict):
                cand = extra.get("ufs_geojson") or extra.get("ufs_path") or extra.get("ufs")
                if cand:
                    p = Path(cand)
                    if p.exists():
                        return json.loads(p.read_text(encoding="utf-8"))
                # se já veio como objeto dict
                if isinstance(extra.get("ufs_geojson"), dict):
                    return extra["ufs_geojson"]
    except Exception:
        pass

    # 2) caminho canônico do ETL
    p = Path(ROOT) / "data" / "geo" / "ibge" / "ufs.geojson"
    if p.exists():
        return json.loads(p.read_text(encoding="utf-8"))

    # 3) nada
    return None

def _hash_color(s, alpha=160):
    """
    Cor determinística por string (ex.: 'PA' -> RGB fixo).
    Gera uma cor agradável (HSL→RGB simplificado).
    """
    h = int(hashlib.sha1(s.encode("utf-8")).hexdigest(), 16)
    # paleta: roda o matiz; saturação e luminosidade fixas (0.55/0.60)
    hue = (h % 360) / 360.0
    sat = 0.55
    lum = 0.60
    # HSL -> RGB (simples)
    def h2rgb(p, q, t):
        if t < 0: t += 1
        if t > 1: t -= 1
        if t < 1/6: return p + (q - p) * 6 * t
        if t < 1/2: return q
        if t < 2/3: return p + (q - p) * (2/3 - t) * 6
        return p
    q = lum + sat - lum * sat
    p = 2 * lum - q
    r = int(255 * h2rgb(p, q, hue + 1/3))
    g = int(255 * h2rgb(p, q, hue))
    b = int(255 * h2rgb(p, q, hue - 1/3))
    return [r, g, b, alpha]

def _feature_keys_lookup(props: dict):
    """
    Descobre as chaves mais prováveis de uf_sigla e uf_nome no GeoJSON.
    """
    keys = {k.lower(): k for k in props.keys()}
    uf_sig = keys.get("uf_sigla") or keys.get("sigla_uf") or keys.get("sg_uf") or keys.get("uf")
    uf_nom = keys.get("uf_nome")  or keys.get("nm_uf")   or keys.get("nome_uf") or keys.get("nome")
    return uf_sig, uf_nom

# --------------------------------------------------------------------------------------
# Página
# --------------------------------------------------------------------------------------

st.set_page_config(page_title="Matupiri • Observatório", layout="wide")
apply_global_style()
header_nav("📊 Observatório", "Mapa e rankings por região; visão de defesos e UCs")

ensure_boot()

# Carrega geometrias rápidas (tuas tabelas) para fallback de pontos / chaves
ufs_df, mun_df, _ = load_geo()
lat_mun, lon_mun = _guess_latlon_cols(mun_df)
lat_uf,  lon_uf  = _guess_latlon_cols(ufs_df)

# filtros
with st.sidebar:
    st.header("Filtros")
    period = st.selectbox("Período", ["Últimos 7 dias","Últimos 30 dias","Últimos 90 dias","Tudo"], index=1)
    uf_f  = st.text_input("UF (ex.: PA, AP, MA)", value="").strip().upper() or None
    mun_f = st.text_input("Município", value="").strip() or None
    gen_f = st.text_input("Gênero (opcional)", value="").strip() or None
    metric = st.selectbox("Métrica",
                          ["Acessos", "Elegíveis", "Requisitos Ausentes", "Requisitos Presentes", "Requeridas por Gênero"],
                          index=0)
    topn = st.number_input("Top N ranking", min_value=3, max_value=50, value=10)

now = datetime.now(timezone.utc)
if period == "Últimos 7 dias":      start_iso, end_iso = (now - timedelta(days=7)).isoformat(), now.isoformat()
elif period == "Últimos 30 dias":   start_iso, end_iso = (now - timedelta(days=30)).isoformat(), now.isoformat()
elif period == "Últimos 90 dias":   start_iso, end_iso = (now - timedelta(days=90)).isoformat(), now.isoformat()
else:                               start_iso, end_iso = None, None

events = get_analytics(start_iso=start_iso, end_iso=end_iso, uf=uf_f, municipio=mun_f, gender=gen_f) or []
ev = pd.DataFrame(events)
if ev.empty:
    st.info("Sem eventos para os filtros atuais.")
    footer(); st.stop()

# --------------------------------------------------------------------------------------
# Métricas (ranking e peso espacial por UF/Município)
# --------------------------------------------------------------------------------------
ranking_df, heat_source, heat_label = None, None, "Eventos"

if metric == "Acessos":
    view = ev[ev["kind"] == "view"].copy()
    if not view.empty:
        group_cols = (["uf","municipio","policy"] if (uf_f is None and mun_f is None) else ["policy"])
        ranking_df = (view.groupby(group_cols).size().reset_index(name="acessos").sort_values("acessos", ascending=False).head(int(topn)))
        heat_source = view.groupby(["uf","municipio"]).size().reset_index(name="weight")
        heat_label = "Acessos"

elif metric == "Elegíveis":
    elig = ev[ev["kind"] == "eligible"].copy()
    if not elig.empty:
        group_cols = (["uf","municipio","policy"] if (uf_f is None and mun_f is None) else ["policy"])
        ranking_df = (elig.groupby(group_cols).size().reset_index(name="adequações").sort_values("adequações", ascending=False).head(int(topn)))
        heat_source = elig.groupby(["uf","municipio"]).size().reset_index(name="weight")
        heat_label = "Adequações"

elif metric == "Requisitos Ausentes":
    mt = ev[(ev["kind"] == "matches") & ev["missing"].notna()].copy()
    if not mt.empty:
        expl = mt.explode("missing")
        group_cols = (["uf","municipio","missing"] if (uf_f is None and mun_f is None) else ["missing"])
        ranking_df = (expl.groupby(group_cols).size().reset_index(name="ocorrências").sort_values("ocorrências", ascending=False).head(int(topn)))
        heat_source = expl.groupby(["uf","municipio"]).size().reset_index(name="weight")
        heat_label = "Ocorrências"

elif metric == "Requisitos Presentes":
    mt = ev[(ev["kind"] == "matches") & ev["met"].notna()].copy()
    if not mt.empty:
        expl = mt.explode("met")
        group_cols = (["uf","municipio","met"] if (uf_f is None and mun_f is None) else ["met"])
        ranking_df = (expl.groupby(group_cols).size().reset_index(name="ocorrências").sort_values("ocorrências", ascending=False).head(int(topn)))
        heat_source = expl.groupby(["uf","municipio"]).size().reset_index(name="weight")
        heat_label = "Ocorrências"

else:  # Requeridas por Gênero
    vw = ev[ev["kind"] == "view"].copy()
    if not vw.empty:
        grp = ["gender","policy"] if (uf_f or mun_f) else ["uf","municipio","gender","policy"]
        ranking_df = (vw.groupby(grp).size().reset_index(name="requeridas").sort_values("requeridas", ascending=False).head(int(topn)))
        heat_source = vw.groupby(["uf","municipio"]).size().reset_index(name="weight")
        heat_label = "Requisições"

# --------------------------------------------------------------------------------------
# Ranking
# --------------------------------------------------------------------------------------
if ranking_df is not None and not ranking_df.empty:
    st.subheader("Ranking")
    st.dataframe(ranking_df, use_container_width=True)
else:
    st.caption("Sem dados para o ranking com a métrica/filtros atuais.")

# --------------------------------------------------------------------------------------
# Choropleth por UF (preferido). Se não houver GeoJSON, fallback para Heatmap.
# --------------------------------------------------------------------------------------
ufs_geojson = _load_ufs_geojson()

if ufs_geojson:
    # total por UF (soma dos pesos por município → UF)
    by_uf = (heat_source.groupby("uf")["weight"].sum().reset_index()
             if "uf" in heat_source.columns else pd.DataFrame(columns=["uf","weight"]))
    by_uf["_key"] = by_uf["uf"].map(_normalize_text)
    totals = dict(zip(by_uf["_key"], by_uf["weight"]))

    # percorre features e injeta propriedades: uf_sigla normalizada, total e cor
    # detecta chaves uf_sigla/uf_nome na primeira feature
    if len(ufs_geojson.get("features", [])) == 0:
        st.info("GeoJSON de UF sem features; usando fallback de pontos.")
        ufs_geojson = None
    else:
        p0 = ufs_geojson["features"][0].get("properties", {})
        key_sig, key_nome = _feature_keys_lookup(p0)
        # default: usa 'uf_sigla' se existir; senão primeira chave textual
        for feat in ufs_geojson["features"]:
            props = feat.get("properties", {})
            uf_val = ""
            if key_sig and key_sig in props and props[key_sig]:
                uf_val = str(props[key_sig]).upper().strip()
            elif "uf_sigla" in props:
                uf_val = str(props["uf_sigla"]).upper().strip()
            elif "UF" in props:
                uf_val = str(props["UF"]).upper().strip()
            # normalizado para lookup
            k = _normalize_text(uf_val)
            tot = int(totals.get(k, 0)) if k else 0
            color = _hash_color(uf_val or "NA", alpha=160)  # cor categórica por UF
            # injeta propriedades novas
            props["uf_sigla"] = uf_val or props.get("uf_sigla") or props.get("UF") or ""
            props["uf_total"] = tot
            props["fill_color"] = color
            feat["properties"] = props

    # camada de polígonos coloridos por UF
    uf_layer = pdk.Layer(
        "GeoJsonLayer",
        ufs_geojson,
        pickable=True,
        stroked=True,
        filled=True,
        extruded=False,
        get_fill_color="properties.fill_color",
        get_line_color=[30, 30, 30, 200],
        get_line_width=1,
    )

    tooltip = {
        "html": "<b>UF:</b> {uf_sigla}<br/><b>" + heat_label + ":</b> {uf_total}",
        "style": {"backgroundColor": "white", "color": "black"}
    }

    view = pdk.ViewState(latitude=-14.2, longitude=-51.9, zoom=3.5)
    deck = pdk.Deck(
        layers=[uf_layer],
        initial_view_state=view,
        tooltip=tooltip,
        map_style="https://basemaps.cartocdn.com/gl/positron-gl-style/style.json",
    )

    st.subheader(f"🗺️ Mapa — {heat_label} por UF")
    st.pydeck_chart(deck, use_container_width=True)

    # legenda: UF → cor + total
    st.markdown("##### Legenda (UF)")
    legend_df = by_uf.copy()
    if not legend_df.empty:
        legend_df["cor"] = legend_df["uf"].apply(lambda x: _hash_color(x))
        # renderiza como html simples com swatch
        rows = []
        for _, r in legend_df.sort_values("uf").iterrows():
            rgba = r["cor"]
            rows.append(f'<div style="display:flex;align-items:center;gap:.5rem;margin-bottom:.25rem;">'
                        f'<span style="display:inline-block;width:14px;height:14px;border-radius:2px;'
                        f'background: rgba({rgba[0]},{rgba[1]},{rgba[2]},{rgba[3]/255});"></span>'
                        f'<span><b>{r["uf"]}</b> — {int(r["weight"])} {heat_label.lower()}</span>'
                        f'</div>')
        st.markdown("\n".join(rows), unsafe_allow_html=True)

else:
    # ---------------- Fallback: Heatmap de pontos (como tua versão anterior) ----------------
    if (heat_source is None or heat_source.empty) and not ev[ev["kind"] == "search"].empty:
        heat_source = ev[ev["kind"] == "search"].groupby(["uf","municipio"]).size().reset_index(name="weight")
        heat_label = "Buscas"

    if heat_source is None or heat_source.empty:
        st.info("Sem dados georreferenciados para o mapa.")
        footer(); st.stop()

    use_mun = lat_mun and lon_mun and ("nome_mun" in mun_df.columns)
    if use_mun:
        mun_aux = mun_df.copy()
        mun_aux["_key"] = mun_aux["nome_mun"].map(_normalize_text) + "||" + mun_aux["uf"].map(_normalize_text)
        heat_source["_key"] = heat_source["municipio"].map(_normalize_text) + "||" + heat_source["uf"].map(_normalize_text)
        heat_df = heat_source.merge(mun_aux[["_key", lat_mun, lon_mun, "nome_mun", "uf"]], on="_key", how="left").dropna(subset=[lat_mun, lon_mun])
        tooltip = {"html": f"<b>Município:</b> {{nome_mun}} {{uf}}<br/><b>{heat_label}:</b> {{weight}}"}
        lon_col, lat_col = lon_mun, lat_mun
    else:
        ufs_aux = ufs_df.copy()
        ufs_aux["_key"] = ufs_aux["uf"].map(_normalize_text)
        heat_source["_key"] = heat_source["uf"].map(_normalize_text)
        heat_df = heat_source.merge(ufs_aux[["_key", lat_uf, lon_uf, "uf"]], on="_key", how="left").dropna(subset=[lat_uf, lon_uf])
        tooltip = {"html": f"<b>UF:</b> {{uf}}<br/><b>{heat_label}:</b> {{weight}}"}
        lon_col, lat_col = lon_uf, lat_uf

    layer = pdk.Layer(
        "HeatmapLayer",
        data=heat_df,
        get_position=f"[{lon_col}, {lat_col}]",
        get_weight="weight",
        radiusPixels=40,
        intensity=1.0,
        threshold=0.03,
    )
    view = pdk.ViewState(latitude=-14.2, longitude=-51.9, zoom=3.5)
    deck = pdk.Deck(
        layers=[layer],
        initial_view_state=view,
        tooltip=tooltip,
        map_style="https://basemaps.cartocdn.com/gl/positron-gl-style/style.json"
    )
    st.subheader(f"🗺️ Mapa — {heat_label} (fallback por pontos)")
    st.pydeck_chart(deck, use_container_width=True)

# --------------------------------------------------------------------------------------
# Espaços para painéis futuros
# --------------------------------------------------------------------------------------
st.divider()
st.markdown("#### Outros painéis (ativar quando houver dados processados)")
col1, col2 = st.columns(2)
with col1:
    st.markdown("**Seguros-Defesos ativos por região**")
    st.caption("Carregar de `data/processed/defesos.csv` (ETL).")
with col2:
    st.markdown("**Unidades de Conservação ativas**")
    st.caption("Carregar de `data/processed/ucs.geojson` e `ucs.csv` (ETL).")

footer()