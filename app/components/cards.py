import streamlit as st
from typing import Iterable

def _list(items: Iterable[str] | None):
    if not items: return
    for m in items:
        st.write(f"- {m}")

def policy_card(row: dict, met=None, missing=None, show_link=True, selectable=False, on_select=None):
    """Cartão principal para políticas (usado nas páginas 3, 4 e 5)."""
    title = row.get("Politicas publicas", "(sem título)")
    nivel = row.get("nivel", "")
    with st.container(border=True):
        st.markdown(f"**{title}**  — *{nivel}*")
        desc = row.get("Descrição dos direitos") or ""
        if desc: st.write(desc)

        acesso = row.get("Acesso") or ""
        if acesso:
            with st.expander("Ver texto original de acesso"):
                st.write(acesso)

        link = row.get("Link")
        if show_link and isinstance(link, str) and link.startswith("http"):
            st.markdown(f"[Abrir link oficial]({link})")

        if met or missing:
            c1, c2 = st.columns(2)
            with c1:
                if met:
                    st.write("✅ **Atendidos:**")
                    _list(met)
            with c2:
                if missing:
                    st.write("🟡 **Faltantes:**")
                    _list(missing)

        if selectable and on_select:
            st.button("Selecionar esta política", use_container_width=True, on_click=on_select)

def policy_mini_card(row: dict):
    """Cartão compacto (para listas grandes)."""
    title = row.get("Politicas publicas", "(sem título)")
    nivel = row.get("nivel", "")
    with st.container(border=True):
        st.markdown(f"**{title}**  — *{nivel}*")
        if row.get("Descrição dos direitos"):
            st.caption(str(row["Descrição dos direitos"])[:180] + "…")
        link = row.get("Link")
        if isinstance(link, str) and link.startswith("http"):
            st.markdown(f"[Abrir link]({link})")

def metric_card(label: str, value, help_text: str | None = None):
    col = st.container(border=True)
    with col:
        st.metric(label, value)
        if help_text:
            st.caption(help_text)

def profile_summary_card(profile: dict):
    """Resumo de alguns campos do perfil."""
    with st.container(border=True):
        st.markdown("**Resumo do Perfil**")
        keys = ["estado", "municipio"]
        for k in keys:
            if k in profile and profile[k]:
                st.write(f"- **{k.capitalize()}**: {profile[k]}")