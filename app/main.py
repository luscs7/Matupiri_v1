# app/app.py
from __future__ import annotations
import os
import sys
import streamlit as st

# Ajuste opcional do PYTHONPATH se você for rodar de fora do projeto
# root = Path(__file__).resolve().parents[1]
# if str(root) not in sys.path:
#     sys.path.insert(0, str(root))

from app.components.layout import header_nav, footer, apply_global_style
from app.data_access.repositories import boot_migrations

st.set_page_config(page_title="Matupiri", layout="wide")

# ---------------- Boot & Estado Global ----------------
if "boot_done" not in st.session_state:
    with st.spinner("Inicializando..."):
        try:
            boot_migrations()
        except Exception as e:
            st.error(f"Falha ao inicializar o banco: {e}")
        st.session_state.boot_done = True

# Estados comuns usados pelas páginas
st.session_state.setdefault("account", None)              # dict de conta logada
st.session_state.setdefault("profile", {})                # perfil corrente (dinâmico)
st.session_state.setdefault("current_profile_id", None)   # id da versão persistida
st.session_state.setdefault("eligible", [])               # [(idx, met, missing)]
st.session_state.setdefault("nearly", [])                 # [(idx, met, missing)]
st.session_state.setdefault("selected_policy_idx", None)  # índice selecionado na planilha

apply_global_style()

# ---------------- Deep-link por querystring ----------------
def _qs_params():
    # Compat: novas versões têm st.query_params; antigas têm experimental_get_query_params
    try:
        return dict(st.query_params)
    except Exception:
        return st.experimental_get_query_params()  # type: ignore[attr-defined]

PAGE_MAP = {
    "home": "pages/1_Home.py",
    "cadastro": "pages/2_Cadastro.py",
    "politicas": "pages/3_Políticas_Públicas_Cadastradas.py",
    "resultado_auto": "pages/4_Resultado_auto.py",
    "resultado_manual": "pages/5_Resultado_manual.py",
    "login": "pages/6_Login_e_Salvar_Perfil.py",
    "observatorio": "pages/7_Observatório.py",
    "creditos": "pages/8_Credits_app.py",
    "politica_dados": "pages/9_Política_de_Dados.py",
}

params = _qs_params()
requested = None
for k in ("page", "p", "goto"):
    if k in params:
        v = params[k]
        # v pode vir como list em versões antigas
        requested = (v[0] if isinstance(v, list) else v).lower()
        break

target = PAGE_MAP.get(requested, PAGE_MAP["home"])

# ---------------- Redirecionamento padrão para Home ----------------
if "routed_once" not in st.session_state:
    st.session_state.routed_once = True
    try:
        st.switch_page(target)  # redireciona imediatamente para a página desejada
    except Exception:
        # Fallback: sem switch_page, mostramos um hub simples aqui
        pass

# ---------------- Fallback (hub) se switch_page não existir ----------------
header_nav("🐟 Matupiri", "Bem-vind@ — escolha uma opção abaixo")
st.info("Você está vendo uma página de início alternativa. "
        "Em versões recentes do Streamlit, usamos redirecionamento automático para **1_Home**.")

c1, c2, c3 = st.columns(3)
with c1:
    st.page_link("pages/2_Cadastro.py", label="👤 Cadastro", use_container_width=True)
with c2:
    st.page_link("pages/3_Políticas_Públicas_Cadastradas.py", label="📚 Políticas Cadastradas", use_container_width=True)
with c3:
    st.page_link("pages/7_Observatório.py", label="📊 Observatório", use_container_width=True)

st.divider()
st.page_link("pages/1_Home.py", label="🏠 Ir para Home completa", use_container_width=True)
st.page_link("pages/4_Resultado_auto.py", label="🤖 Resultado Automático", use_container_width=True)
st.page_link("pages/5_Resultado_manual.py", label="🧭 Resultado Manual", use_container_width=True)
st.page_link("pages/6_Login_e_Salvar_Perfil.py", label="🔐 Login / Salvar Perfil", use_container_width=True)
st.page_link("pages/8_Creditos_app.py", label="🙌 Créditos", use_container_width=True)
st.page_link("pages/9_Política_de_Dados.py", label="🔏 Política de Dados", use_container_width=True)

footer()
