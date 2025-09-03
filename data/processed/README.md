# processed/
Artefatos **finais** consumidos diretamente pelo app.

## Catálogo de Políticas — `politicas_publicas.xlsx`
Colunas mínimas (aba 0):
- Número
- Politicas publicas
- nivel
- Operacionalização/Aplicação
- Descrição dos direitos
- Acesso
- Organização interna (Subprogramas e/ou Eixos)
- Link
- Observações

## Geografia — `geo/`
- `ufs.csv`: deve conter `uf`, `ibge_uf` e algum par de lat/lon (`lat,lon` ou `latitude,longitude`).
- `municipios.csv`: deve conter `nome_mun`, `uf`, `ibge_mun` e lat/lon.
- `municipios_simplificado.geojson` (opcional): base cartográfica leve para mapas.

## Defesos — `defesos.csv`
Colunas recomendadas:
`especie, nome_popular, arte_pesca, uf, inicio, fim, fundamento_legal, esfera, link_oficial`
- `inicio` e `fim` em `YYYY-MM-DD`.

## UCs — `ucs.csv` e `ucs.geojson`
- CSV: `nome, categoria, esfera, uf, area_ha, link`
- GeoJSON: `FeatureCollection` com `properties` contendo ao menos `nome, categoria, esfera, uf`.

> Estes arquivos são produzidos pelos ETLs em `etl/` (consulte o repositório).
