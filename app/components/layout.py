from pathlib import Path
import base64
import streamlit as st

_GLOBAL_CSS = """
<style>
.block-container { max-width: 1200px; }
button[kind="primary"] { padding: 0.6rem 1rem; }
.stMetric { text-align: center; }
</style>
"""

def apply_global_style():
    st.markdown(_GLOBAL_CSS, unsafe_allow_html=True)

def header_nav(title: str, subtitle: str = ""):
    """Título padrão de páginas."""
    apply_global_style()
    st.title(title)
    if subtitle:
        st.caption(subtitle)
    st.divider()

def section(title: str, subtitle: str | None = None):
    st.subheader(title)
    if subtitle:
        st.caption(subtitle)

def footer():
    """
    Rodapé com:
      - botões pretos centralizados para Equipe técnica e Política de dados
      - bloco 'Desenvolvido por:' com logo do Caeté clicável
    """
    import base64
    from pathlib import Path

    st.markdown("---")

    # CSS customizado
    custom_css = """
    <style>
    .footer-container {
        text-align: center;
        margin-top: 1rem;
    }
    .footer-buttons {
        display: flex;
        justify-content: center;
        gap: 1rem;
        margin-bottom: 1rem;
    }
    .footer-buttons button {
        background-color: black !important;
        color: white !important;
        font-weight: bold;
        border-radius: 6px !important;
    }
    </style>
    """
    st.markdown(custom_css, unsafe_allow_html=True)

    # Logo Caeté (base64 embutido)
    st.markdown('<div class="footer-container">', unsafe_allow_html=True)
    st.write("**Desenvolvido por:**")

    assets_dir = Path(__file__).resolve().parents[1] / "assets"
    logo_path = assets_dir / "logo_caete.png"

    if logo_path.exists():
        b64 = base64.b64encode(logo_path.read_bytes()).decode()
        st.markdown(
            f'<a href="https://redecaete.com" target="_blank">'
            f'<img src="data:image/png;base64,{b64}" alt="Caeté" style="height:60px;">'
            f"</a>",
            unsafe_allow_html=True
        )
    else:
        st.markdown(
            '[**Caeté – Coletivo de Articulações**](https://redecaete.com)',
            unsafe_allow_html=True
        )

    st.markdown("</div>", unsafe_allow_html=True)

def toolbar(*buttons: tuple[str, str]):
    """
    Renderiza um conjunto de botões de navegação.
    Ex.: toolbar(("👤 Cadastro","pages/2_Cadastro.py"), ("📚 Políticas","pages/3_Políticas_Públicas_Cadastradas.py"))
    """
    cols = st.columns(len(buttons))
    for col, (label, target) in zip(cols, buttons):
        with col:
            st.page_link(target, label=label, use_container_width=True)
