# Dicionário de Dados — Planilha de Políticas (`processed/politicas_publicas.xlsx`)

| Coluna | Tipo | Obrigatória | Descrição | Exemplo |
|---|---|:---:|---|---|
| Número | string |  | Identificador (lei/portaria) | 12/2024 |
| Politicas publicas | string | ✅ | Título da política | Seguro-Defeso |
| nivel | string |  | Esfera federativa | Federal / Estadual / Municipal |
| Operacionalização/Aplicação | string |  | Como se implementa / órgãos responsáveis | INSS / MPA |
| Descrição dos direitos | string |  | O que a política garante | Benefício durante o defeso |
| Acesso | string (livre) | ✅* | **Texto com requisitos** lido pelo motor de regras | RGP ativo; CadÚnico; CPF regular |
| Organização interna (Subprogramas e/ou Eixos) | string/lista |  | Subprogramas/eixos | Regras; Fiscalização |
| Link | url |  | Endereço oficial | https://www.gov.br/... |
| Observações | string |  | Observações gerais | — |

\*Obrigatória para avaliação automática; se vazia, a política ainda aparece no catálogo mas não será avaliada.
