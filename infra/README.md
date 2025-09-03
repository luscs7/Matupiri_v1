# infra/

Automação de **CI/CD** e **deploy**.

## Fluxo recomendado

- **CI (`ci.yml`)**: roda em PR/push → ruff (lint), mypy (types), pytest (com cobertura).
- **ETL (`run-etl.yml`)**: manual (workflow_dispatch) → executa todos ETLs e faz upload de `data/processed` como artefato.
- **Docker (`docker-image.yml`)**: opcional; faz build/push da imagem no Docker Hub (ou outro registry).

> Para os workflows funcionarem, copie os YAMLs para: `.github/workflows/`.

## Deploys

- **Streamlit Community Cloud**: crie o app apontando para este repo/branch.  
  Use `streamlit_secrets.example.toml` como base para **Secrets** no painel do Streamlit.
- **Docker (qualquer PaaS)**: use o `Dockerfile`. Local: `docker-compose.yml`.

## Variáveis/Secrets úteis

### GitHub (para `docker-image.yml`)
- `DOCKERHUB_USERNAME`
- `DOCKERHUB_TOKEN`
- `IMAGE_NAME` (ex.: `seuuser/matupiri`)

### Streamlit (no painel do Streamlit Cloud)
Ver `streamlit_secrets.example.toml`.

## Requisitos no CI
As wheels de `geopandas`/`pyogrio`/`shapely` já resolvem GDAL/PROJ, sem `apt-get`.  
Se for preciso usar `fiona`/GDAL nativo, vamos ajustar o workflow (me avise).

