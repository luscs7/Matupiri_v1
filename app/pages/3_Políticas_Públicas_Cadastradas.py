# app/pages/3_Políticas_Públicas_Cadastradas.py
from __future__ import annotations
from pathlib import Path
import sys
import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

try:
    from app.components.layout import header_nav, footer
except Exception:
    def header_nav(title, subtitle=""): st.title(title); st.caption(subtitle)
    def footer(): st.caption("")

@st.cache_data(show_spinner=False)
def load_master() -> pd.DataFrame:
    csv = ROOT / "data" / "processed" / "policies_master.csv"
    if not csv.exists():
        return pd.DataFrame()
    df = pd.read_csv(csv, dtype=str).fillna("")
    needed = ["policy_id","nome","nivel","tipo_beneficio","responsavel",
              "descricao","criterios","legislacao_titulo","legislacao_url",
              "info_url","phone","email","contact_site","financas_resumo","subprogramas","como_acessar"]
    for c in needed:
        if c not in df.columns: df[c] = ""
    # Garante níveis esperados
    df["nivel"] = df["nivel"].where(df["nivel"].isin(["Nacional","Estadual","Regional"]), df["nivel"])
    # Ordenação padrão agradável
    df = df.sort_values(["nivel","responsavel","nome","policy_id"])
    return df[needed]

# ---- estilo leve (sem HTML cru nos cards) ----
st.markdown("""
<style>
.badge {display:inline-block; padding:3px 8px; border-radius:999px; border:1px solid #e5e7eb; background:#f3f4f6; margin-right:6px; font-size:0.82rem; color:#374151;}
.card {border:1px solid #e5e7eb; border-radius:14px; padding:14px 16px; background:white;}
.card h3 {margin:0 0 6px 0;}
.section-title {font-weight:600; margin:8px 0 4px 0;}
.dim {color:#6b7280; font-size:0.86rem;}
.small {font-size:0.92rem;}
.rule {height:1px; background:#f1f5f9; border:0; margin:10px 0;}
</style>
""", unsafe_allow_html=True)

def page():
    header_nav("Políticas públicas cadastradas", "Use os filtros abaixo para refinar a lista.")

    df = load_master()
    if df.empty:
        st.warning("Nenhum dado processado. Rode:  python -m etl.policies_to_processed")
        return

    with st.expander("Filtros", expanded=True):
        c1, c2, c3, c4 = st.columns([2, 1.1, 1.3, 1.5])
        with c1:
            nomes = ["(Todos)"] + sorted([x for x in df["nome"].unique() if x.strip()])
            nome_sel = st.selectbox("Nome", nomes, index=0)
        with c2:
            nivel_opts = ["(Todos)", "Nacional", "Estadual", "Regional"]
            nivel_sel = st.selectbox("Nível", nivel_opts, index=0)
        with c3:
            tipo_opts = ["(Todos)"] + sorted([x for x in df["tipo_beneficio"].unique() if x.strip()])
            tipo_sel = st.selectbox("Tipo de Benefício", tipo_opts, index=0)
        with c4:
            resp_opts = ["(Todos)"] + sorted([x for x in df["responsavel"].unique() if x.strip()])
            resp_sel = st.selectbox("Responsável (órgão preponente)", resp_opts, index=0)

    filt = df.copy()
    if nome_sel != "(Todos)":
        filt = filt[filt["nome"] == nome_sel]
    if nivel_sel != "(Todos)":
        filt = filt[filt["nivel"] == nivel_sel]
    if tipo_sel != "(Todos)":
        filt = filt[filt["tipo_beneficio"] == tipo_sel]
    if resp_sel != "(Todos)":
        filt = filt[filt["responsavel"] == resp_sel]

    st.caption(f"{len(filt)} políticas encontradas")

    # --------- lista vertical (sem HTML cru) ----------
    for _, r in filt.iterrows():
        with st.container(border=False):
            st.markdown('<div class="card">', unsafe_allow_html=True)

            st.markdown(f'<div class="dim">{r.policy_id}</div>', unsafe_allow_html=True)
            st.markdown(f"### {r.nome}")

            # badges
            badges = []
            if r.nivel.strip():
                badges.append(f'<span class="badge">Nível: {r.nivel}</span>')
            if r.tipo_beneficio.strip():
                badges.append(f'<span class="badge">Tipo: {r.tipo_beneficio}</span>')
            if r.responsavel.strip():
                badges.append(f'<span class="badge">Responsável: {r.responsavel}</span>')
            if badges:
                st.markdown(" ".join(badges), unsafe_allow_html=True)

            # Descrição
            if r.descricao.strip():
                st.markdown('<div class="section-title">Descrição</div>', unsafe_allow_html=True)
                st.write(r.descricao)

            # Critérios
            if r.criterios.strip():
                st.markdown('<div class="section-title">Critérios</div>', unsafe_allow_html=True)
                # criterios já vem como bullets com "-" — respeita quebras de linha
                st.text(r.criterios)

            # Legislação
            if r.legislacao_titulo.strip() or r.legislacao_url.strip():
                st.markdown('<div class="section-title">Legislação</div>', unsafe_allow_html=True)
                if r.legislacao_url.strip():
                    st.markdown(f"[{r.legislacao_titulo or 'Legislação'}]({r.legislacao_url})")
                else:
                    st.markdown(r.legislacao_titulo)

            # Mais informações
            if r.info_url.strip():
                st.markdown('<div class="section-title">Mais informações</div>', unsafe_allow_html=True)
                st.markdown(f"[{r.info_url}]({r.info_url})")

            # Contatos
            has_phone = bool(r.phone.strip())
            has_mail  = bool(r.email.strip())
            has_site  = bool(r.contact_site.strip())
            if has_phone or has_mail or has_site:
                st.markdown('<div class="section-title">Contatos</div>', unsafe_allow_html=True)
                if has_phone:
                    st.write(f"📞 {r.phone}")
                if has_mail:
                    st.write(f"✉️ {r.email}")
                if has_site:
                    st.markdown(f"[Site de atendimento]({r.contact_site})")

            # Extras
            if r.financas_resumo.strip() or r.subprogramas.strip():
                st.markdown('<hr class="rule">', unsafe_allow_html=True)
                if r.financas_resumo.strip():
                    st.markdown("**Parâmetros financeiros**")
                    st.text(r.financas_resumo)
                if r.subprogramas.strip():
                    st.markdown("**Subprogramas**")
                    st.write(r.subprogramas)

            # Como acessar
            if r.como_acessar.strip():
                st.markdown('<hr class="rule">', unsafe_allow_html=True)
                st.markdown("**Como acessar**")
                st.write(r.como_acessar)

            st.markdown('</div>', unsafe_allow_html=True)  # fecha .card

    footer()

if __name__ == "__main__" or True:
    page()

