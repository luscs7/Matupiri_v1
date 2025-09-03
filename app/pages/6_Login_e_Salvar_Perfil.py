import streamlit as st
from app.components.layout import header_nav, footer, apply_global_style
from app.data_access.repositories import (
    boot_migrations, authenticate_person, authenticate_collective,
    create_person_account, create_collective_account,
    save_profile_for_account,
)

# --- bootstrap de caminho para permitir 'from app. ...' ---
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]  # raiz do projeto: .../Matupiri_v1
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
# -----------------------------------------------------------

st.set_page_config(page_title="Matupiri • Login / Salvar", layout="wide")
header_nav("🔐 Login e Salvar Perfil", "Entre para salvar seu perfil e consultar depois")
boot_migrations()

if "account" not in st.session_state:
    st.session_state.account = None

tab1, tab2 = st.tabs(["Pessoa Física", "Coletivo"])

with tab1:
    st.subheader("Entrar")
    u = st.text_input("Usuário", key="person_login_user")
    p = st.text_input("Senha", type="password", key="person_login_pass")
    if st.button("Entrar (PF)"):
        acc = authenticate_person(u, p)
        if acc:
            st.session_state.account = acc
            st.success(f"Bem-vindo(a), {acc.get('display_name') or acc.get('username')}!")
        else:
            st.error("Usuário/senha inválidos.")

    st.divider()
    st.subheader("Criar conta (Pessoa Física)")
    name = st.text_input("Nome")
    new_user = st.text_input("Usuário (login)", key="new_user_pf")
    new_pass = st.text_input("Senha", type="password", key="new_pass_pf")
    if st.button("Criar conta (PF)"):
        try:
            _ = create_person_account(name, new_user, new_pass)
            st.success("Conta criada! Agora faça login.")
        except Exception as e:
            st.error(f"Erro: {e}")

with tab2:
    st.subheader("Entrar (Coletivo)")
    cnpj = st.text_input("CNPJ (somente números)")
    p2 = st.text_input("Senha", type="password")
    if st.button("Entrar (Coletivo)"):
        acc = authenticate_collective(cnpj, p2)
        if acc:
            st.session_state.account = acc
            st.success("Bem-vind@, coletivo!")
        else:
            st.error("CNPJ/senha inválidos.")

    st.divider()
    st.subheader("Criar conta (Coletivo)")
    new_cnpj = st.text_input("CNPJ do coletivo")
    contact = st.text_input("Contato (e-mail/telefone)")
    new_pass2 = st.text_input("Senha do coletivo", type="password")
    if st.button("Criar conta (Coletivo)"):
        try:
            _ = create_collective_account(new_cnpj, contact, new_pass2)
            st.success("Conta criada! Agora faça login.")
        except Exception as e:
            st.error(f"Erro: {e}")

st.divider()
if st.session_state.account:
    st.subheader("Salvar meu perfil atual")
    if st.button("💾 Salvar perfil atual (da página Cadastro)"):
        profile = st.session_state.get("profile")
        if not profile:
            st.warning("Não há perfil em memória. Preencha antes a página **Cadastro**.")
        else:
            pid = save_profile_for_account(st.session_state.account["id"], profile)
            st.success(f"Perfil salvo! (id={pid})")

footer()
