import streamlit as st
from app.components.layout import header_nav, footer, apply_global_style

# --- bootstrap de caminho para permitir 'from app. ...' ---
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]  # raiz do projeto: .../Matupiri_v1
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
# -----------------------------------------------------------

st.set_page_config(page_title="Matupiri • Política de Dados", layout="wide")
header_nav("🔏 Política de Dados", "Como tratamos seus dados")

st.markdown("""
**1. Finalidade**  
Os dados cadastrados são utilizados para sugerir políticas públicas adequadas ao seu perfil e para alimentar o Observatório (estatísticas agregadas e anonimizadas).

**2. Coleta e armazenamento**  
- Dados pessoais mínimos para autenticação (quando você opta por criar conta).  
- Dados de perfil (campos do cadastro) são armazenados para reuso e comparação de elegibilidade.  
- Eventos de uso (buscas, visualizações, métricas agregadas) são coletados de forma anonimizada.

**3. Compartilhamento**  
Não compartilhamos dados pessoais com terceiros sem consentimento. Resultados do Observatório são **agregados** (sem identificação individual).

**4. Segurança**  
Senhas são armazenadas com hash seguro. A comunicação ocorre sobre HTTPS quando hospedado publicamente.

**5. Transparência e Controle**  
Você pode solicitar a remoção dos seus dados e baixar seu perfil. Para dúvidas, entre em contato pelo e-mail indicado no rodapé da plataforma.

**6. Atualizações**  
Esta política pode ser atualizada. Manteremos registro de versões e data de vigência.
""")

st.caption("Dúvidas entre em contato: falecom@redecaete.com")
footer()
