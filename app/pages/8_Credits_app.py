import streamlit as st
from app.components.layout import header_nav, footer, apply_global_style

# --- bootstrap de caminho para permitir 'from app. ...' ---
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]  # raiz do projeto: .../Matupiri_v1
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
# -----------------------------------------------------------

st.set_page_config(page_title="Matupiri • Créditos", layout="wide")
header_nav("Equipe Técnica", "")

st.markdown("""
**Coordenação de Projeto**
- Lucas Pereira da Silva
            
**Pesquisa**
- Layza Lisboa
- Isabela Nunes

**Equipe de Programação**
- Lucas Pereira da Silva
- Eduardo Pantoja 
            
**Desenvolvimento:**
- Caeté – Coletivo de Articulações Marginais

**Parcerias e Apoios**
- UFPA - Universidade Federal do Pará 
- GIBI - Grupo de Investigação Biológica Integrada
- Ceabio - Centro de Estudos Avançados da Biodiversidade
- Uchile - Universidad Chile

**Tecnologias**
- Streamlit, Python (pandas, pydeck)
- SQLite
""")

st.caption("falecom@redecaete.com | @o_caete ")
footer()
