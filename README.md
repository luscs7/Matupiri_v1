# Matupiri

Plataforma de **busca e recomendação de políticas públicas** (Streamlit), com observatório,
catálogo de políticas e análise automática de elegibilidade por perfil.

## Quickstart

```bash
# 1) Ambiente
python -m venv .venv && source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt || pip install -e .[dev]

# 2) Dados (ETL → processed/)
python etl/run_all.py

# 3) Rodar app
streamlit run app/app.py
