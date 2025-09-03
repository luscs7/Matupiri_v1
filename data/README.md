# 📦 Pasta `data/`

Esta árvore segue o fluxo **raw → interim → processed**:

- **raw/**: fontes originais (APIs/planilhas/shapefiles) — sem alterações.
- **interim/**: resultados intermediários/limpezas temporárias.
- **processed/**: artefatos finais consumidos pelo app.
- **docs/**: contratos de dados, dicionários e esquemas.

## Arquivos esperados pelo app (defaults)
- `processed/politicas_publicas.xlsx`
- `processed/defesos.csv`
- `processed/ucs.csv`
- `processed/ucs.geojson`
- `processed/geo/ufs.csv`
- `processed/geo/municipios.csv`
- `docs/profile_schema.json`
- `docs/keyword_map.json`

> Você pode sobrescrever caminhos via variáveis de ambiente (ex.: `POLICIES_XLSX`, `DEFESOS_CSV` etc).
