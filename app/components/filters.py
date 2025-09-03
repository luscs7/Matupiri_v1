import streamlit as st

def search_and_level_filters(levels: list[str] | None, default_levels: list[str] | None = None):
    """Busca textual + multiselect de nível. Retorna (q, selected_levels)"""
    q = st.text_input("Buscar por nome/descrição/requisitos",
                      placeholder="Ex.: Pronaf, mulher, jovem, pescador...").strip().lower()
    selected = []
    if levels:
        selected = st.multiselect("Filtrar por nível", options=levels, default=default_levels or [])
    return q, selected

def period_filter():
    return st.selectbox("Período", ["Últimos 7 dias","Últimos 30 dias","Últimos 90 dias","Tudo"], index=1)

def region_filters():
    c1, c2 = st.columns(2)
    with c1:
        uf = st.text_input("UF (ex.: PA, AP, MA)", value="").strip().upper() or None
    with c2:
        mun = st.text_input("Município (opcional)", value="").strip() or None
    return uf, mun