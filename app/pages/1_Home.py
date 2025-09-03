import streamlit as st
from app.components.layout import header_nav, footer, apply_global_style

# --- bootstrap de caminho para permitir 'from app. ...' ---
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]  # raiz do projeto: .../Matupiri_v1
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
# -----------------------------------------------------------

st.set_page_config(page_title="Matupiri • Home", layout="wide")

header_nav("Matupiri", "Plataforma Facilitadora de Políticas Públicas")

# Conteúdo
st.markdown("## O que é a Plataforma Matupiri")
st.markdown(
    """
A **Plataforma Matupiri** é uma aplicação aberta que **traduz, organiza e facilita o acesso** a políticas públicas
relevantes para famílias, coletivos e organizações do Brasil, com foco na Amazônia Costeira. Em vez de você “caçar informação”
em dezenas de sites e portarias, a Matupiri **centraliza requisitos, períodos, contatos e documentos** — e compara com
o **seu perfil** para indicar **o que você já pode acessar** e **o que está faltando para a política que você quer acessar**.

**Objetivos principais:**
- **Elegibilidade orientada por perfil:** identificar quais políticas você já pode acessar hoje;
- **Caminhos de acesso:** apontar requisitos faltantes e **como** obtê-los;
- **Observatório vivo:** acompanhar demandas mais frequentes por região (o que as pessoas têm buscado);
- **Aprendizado coletivo:** apoiar associações, grupos e gestores na leitura do território e no planejamento local.
    """
)

st.markdown("## Como usar (passo a passo)")
st.markdown(
    """
1. **Cadastro** → preencha seu perfil básico (atividade, local, documentos que já possui).  
2. **Resultado automático** → veja as políticas para as quais você **provavelmente já é elegível**.  
3. **Resultado manual** → escolha uma política específica e veja **o que falta** no seu perfil para acessá-la.  
4. **Login (opcional)** → crie uma conta para **salvar** seus perfis e consultar depois.  
5. **Observatório** → acompanhe o que as pessoas buscam por região.  
    """
)

st.info(
    "Dica: os resultados são estimativas automatizadas. **Confirme sempre** com o órgão responsável."
)

st.markdown("## Sobre o Caeté")
st.markdown(
    """
O **Caeté – Coletivo de Articulações Marginais** é uma Organização da Sociedade Civil situada na **Amazônia Costeira** que conecta pesquisa, educação e tecnologia social
para fortalecer comunidades tradicionais que margeiam corpos de água. Atuamos com metodologias participativas, cartografias
críticas, comunicação comunitária e desenvolvimento de ferramentas digitais de interesse público — sempre guiados pelo
**direito ao território e à dignidade**.
    """
)

st.divider()

st.markdown("## Vamos Começar?")

st.markdown(
    """
Abaixo você poderá escolher o que fazer agora! 
    """
)

c1, c2, c3 = st.columns(3)
with c1:
    st.page_link("pages/2_Cadastro.py", label="Cadastro", use_container_width=True)
with c2:
    st.page_link("pages/3_Políticas_Públicas_Cadastradas.py", label="Conhecer Políticas Cadastradas", use_container_width=True)
with c3:
    st.page_link("pages/7_Observatório.py", label="Observatório", use_container_width=True)

st.markdown("""
""")
st.divider()

st.markdown("""
Você também pode Salvar Seu perfil para consultar no futuro:
""")

st.page_link("pages/6_Login_e_Salvar_Perfil.py", label="🔐 Login / Salvar Perfil", use_container_width=True)

 # Botões de navegação (Equipe técnica / Política de dados)
 
st.markdown('<div class="footer-buttons">', unsafe_allow_html=True)
col1, col2 = st.columns([1, 1], gap="medium")
with col1:
    st.page_link("pages/8_Credits_app.py", label="👥 Equipe técnica", use_container_width=True)
with col2:
    st.page_link("pages/9_Política_de_Dados.py", label="🔏 Política de dados", use_container_width=True)
st.markdown("</div>", unsafe_allow_html=True)


footer()