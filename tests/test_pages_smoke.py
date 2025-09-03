from __future__ import annotations
from pathlib import Path

PAGES = [
    "pages/1_Home.py",
    "pages/2_Cadastro.py",
    "pages/3_Políticas_Públicas_Cadastradas.py",
    "pages/4_Resultado_auto.py",
    "pages/5_Resultado_manual.py",
    "pages/6_Login_e_Salvar_Perfil.py",
    "pages/7_Observatório.py",
    "pages/8_Credits_app.py",
    "pages/9_Política_de_Dados.py",
]

def test_pages_files_exist():
    missing = [p for p in PAGES if not Path(p).exists()]
    assert not missing, f"Arquivos de páginas ausentes: {missing}"
