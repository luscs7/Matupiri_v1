# Dockerfile para rodar o Matupiri (Streamlit)
FROM python:3.11-slim

# Evita prompts e reduz cache
ENV PIP_NO_CACHE_DIR=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    STREAMLIT_BROWSER_GATHER_USAGE_STATS=false \
    STREAMLIT_SERVER_HEADLESS=true

WORKDIR /app

# Dependências básicas
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copia requisitos primeiro p/ cache
COPY requirements.txt /app/requirements.txt
RUN pip install --upgrade pip \
 && pip install -r requirements.txt \
 && pip install streamlit openpyxl geopandas pyogrio ruff mypy pytest pytest-cov

# Copia o projeto
COPY . /app

# Porta padrão do Streamlit
EXPOSE 8501

# Comando
CMD ["bash", "-lc", "streamlit run app/app.py --server.port=${PORT:-8501} --server.address=0.0.0.0"]
