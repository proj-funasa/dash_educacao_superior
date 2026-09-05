# Implementation Plan: Melhorias na Aba "Visão por Município"

## Overview

Implementação incremental de 12 melhorias no arquivo `dash_educacao_superior.py`, cobrindo: decodificação de categorias administrativas, ordenação interativa da Tabela_IES, filtros adicionais, exibição completa e numerada da Tabela_Cursos, linha de totais, exportação CSV/Excel, abertura em nova aba, opção "Todos os Municípios", limpeza de dropdown, sub-abas internas com mapa de pontos e testes de propriedade.

A ordem das tarefas respeita dependências: constantes e helpers primeiro, callbacks de UI depois, testes por último.

## Tasks

- [x] 1. Definir constantes e helpers de decodificação
  - Adicionar o dicionário `CATEGORIA_ADM_MAP` com os 6 mapeamentos (códigos 1–7, exceto 6) logo após as listas de filtros globais
  - Adicionar a lista `CATEGORIAS_ADM = ["Todas"] + list(CATEGORIA_ADM_MAP.values())`
  - Criar a função helper `_decode_categoria(val)` que aplica `CATEGORIA_ADM_MAP.get(val, val)` para retornar o rótulo legível ou o valor original se não mapeado
  - _Requisitos: 12.1, 12.3_

- [x] 2. Configurar infraestrutura de carregamento de coordenadas municipais
  - [x] 2.1 Implementar a função `_carregar_coordenadas_municipios()` que baixa o CSV de geocódigos IBGE (kelvins/municipios-brasileiros), faz cache em `.cache/municipios_coords.csv` e retorna um DataFrame com colunas `codigo_ibge`, `latitude`, `longitude`, `nome`, `uf`
    - Envolver em `try/except`; em caso de falha, retornar DataFrame vazio com as mesmas colunas e imprimir aviso `[EDUC] AVISO: falha ao carregar coordenadas municipais — {e}`
    - Chamar a função no startup e armazenar em `_df_coords`
    - _Requisitos: 11.3, 11.6_
  - [ ]* 2.2 Escrever teste unitário para `_carregar_coordenadas_municipios()` com falha de rede
    - Verificar que o DataFrame retornado é vazio mas possui as colunas esperadas
    - _Requisitos: 11.7_

- [x] 3. Atualizar `_aba_municipio_layout()` com novos controles de UI
  - [x] 3.1 Tornar o `dcc.Dropdown` de município `clearable=True` e remover `clearable=False` existente
    - _Requisitos: 9.1_
  - [x] 3.2 Adicionar `dcc.Store(id="mun-sort-state", data={"col": "total_mat", "asc": False})` ao layout da aba
    - _Requisitos: 1.1, 1.2, 1.3_
  - [x] 3.3 Adicionar os dropdowns de "Categoria Administrativa" (`id="mun-categoria"`, opções `CATEGORIAS_ADM`, valor `"Todas"`) e "Modalidade" (`id="mun-modalidade"`, opções `["Todas", "Presencial", "EAD"]`, valor `"Todas"`) à barra de filtros existente, usando `_filtro_label()`
    - _Requisitos: 10.1, 10.2_
  - [x] 3.4 Adicionar `dcc.Tabs(id="mun-sub-abas", value="sub-tabela")` com dois `dcc.Tab` — `"Tabela de IES"` (`value="sub-tabela"`) e `"Mapa por Município"` (`value="sub-mapa"`) — logo antes dos containers de saída existentes
    - Substituir os containers de saída por um único `html.Div(id="mun-sub-aba-conteudo")` que será controlado por callback
    - _Requisitos: 11.1_

- [x] 4. Implementar ordenação interativa da Tabela_IES
  - [x] 4.1 Refatorar `renderizar_tabela_faculdades()` para aceitar o novo input `State("mun-sort-state", "data")` e aplicar `.sort_values()` com base em `sort_state["col"]` e `sort_state["asc"]` antes de construir as linhas HTML
    - Garantir que a ordenação usa valores numéricos (não formatados com `_fmt_mil`)
    - _Requisitos: 1.4, 1.5_
  - [x] 4.2 Adicionar `id={"type": "th-sort-ies", "col": <nome_col>}` e cursor `pointer` aos cabeçalhos das colunas ordenáveis (Matrículas, Ingressantes, Concluintes, Cursos Únicos)
    - Exibir seta ↑ ou ↓ no cabeçalho ativo conforme `mun-sort-state`
    - _Requisitos: 1.1, 1.2, 1.3_
  - [x] 4.3 Criar callback `atualizar_sort_state()` com `Input({"type": "th-sort-ies", "col": dash.ALL}, "n_clicks")` e `State("mun-sort-state", "data")` que atualiza o store `mun-sort-state` alternando `asc` se a mesma coluna for clicada, ou resetando para crescente se for coluna diferente
    - _Requisitos: 1.1, 1.2, 1.3_
  - [ ]* 4.4 Escrever teste de propriedade para Property 1 (ordenação crescente e decrescente são inversas)
    - **Property 1: Ordenação crescente e decrescente são inversas entre si**
    - **Validates: Requirements 1.1, 1.2, 1.5**

- [x] 5. Implementar decodificação de `tp_categoria_administrativa` na Tabela_IES
  - [x] 5.1 Aplicar `_decode_categoria()` na coluna `categoria` do DataFrame `tabela` dentro de `renderizar_tabela_faculdades()`, após o `merge` e antes de construir as linhas HTML
    - Exibir o rótulo decodificado na coluna "Categoria" da tabela
    - _Requisitos: 12.2, 12.3_
  - [ ]* 5.2 Escrever teste de propriedade para Property 7 (decodificação consistente entre Tabela_IES, dropdown e Painel_Detalhe)
    - **Property 7: Decodificação de categoria administrativa é total e internamente consistente**
    - **Validates: Requirements 12.2, 12.3, 12.4, 12.5**

- [x] 6. Implementar filtros de Categoria Administrativa e Modalidade na Tabela_IES
  - [x] 6.1 Adicionar os inputs `Input("mun-categoria", "value")` e `Input("mun-modalidade", "value")` ao callback `renderizar_tabela_faculdades()` e aplicar os filtros no DataFrame antes da agregação:
    - Filtro de categoria: `df_i[df_i["tp_categoria_administrativa"].map(_decode_categoria) == categoria]` quando categoria ≠ "Todas"
    - Filtro de modalidade: filtrar `df_c` por `tp_modalidade_ensino` e cruzar com os `co_ies` resultantes antes de montar `ies_cursos`
    - _Requisitos: 10.3, 10.4, 10.6_
  - [ ]* 6.2 Escrever teste de propriedade para Property 2 (filtros aplicam interseção estrita)
    - **Property 2: Filtros aplicam interseção estrita**
    - **Validates: Requirements 3.5, 10.3, 10.4, 10.6**

- [x] 7. Implementar opção "Todos os Municípios" no dropdown
  - [x] 7.1 Modificar `atualizar_municipios_por_uf()` para inserir `{"label": "Todos os Municípios", "value": "TODOS"}` como primeira opção antes dos municípios individuais e definir esse como valor inicial
    - _Requisitos: 7.1_
  - [x] 7.2 Adaptar `renderizar_tabela_faculdades()` para tratar `mun == "TODOS"`: remover o filtro por `no_municipio` nos DataFrames `df_c` e `df_i`, agregando por toda a UF
    - _Requisitos: 7.2, 7.3, 7.5_
  - [x] 7.3 Adaptar `renderizar_detalhes_ies()` para tratar `mun == "TODOS"`: filtrar `df_c` por `co_ies` e `sg_uf` sem filtro de município, exibindo dados agregados de todos os municípios da UF para a IES
    - _Requisitos: 7.4_
  - [ ]* 7.4 Escrever teste de propriedade para Property 9 ("Todos os Municípios" é sempre a primeira opção)
    - **Property 9: "Todos os Municípios" é sempre a primeira opção do dropdown**
    - **Validates: Requirements 7.1**

- [x] 8. Checkpoint — Testar ordenação, filtros e dropdown de município
  - Garantir que todos os testes passam, verificar comportamento dos callbacks 4.3 e 6.1, perguntar ao usuário se houver dúvidas.

- [x] 9. Implementar Painel_Detalhe com correção de FIES e linha de totais
  - [x] 9.1 Refatorar a agregação de `df_cursos_tab` em `renderizar_detalhes_ies()` para calcular os KPIs de financiamento (`fies`, `prouni`, `enem`) como soma direta de `df_c` **antes** do groupby, e manter o groupby separado para a tabela
    - _Requisitos: 4.1, 4.2, 4.3, 4.4, 4.5_
  - [x] 9.2 Adicionar a linha de totais ao final de `df_cursos_tab`: criar um dicionário `total_row` somando todas as colunas numéricas, inserir `"—"` nas colunas textuais (Modalidade, Grau, Área) e `"TOTAL"` na coluna "Curso"; concatenar ao DataFrame antes da renderização
    - Estilizar a linha de totais com fundo `#EBF5FB` e `fontWeight: 700`
    - _Requisitos: 5.1, 5.2, 5.3, 5.5_
  - [ ]* 9.3 Escrever teste de propriedade para Property 5 (indicadores de financiamento consistentes entre card e tabela)
    - **Property 5: Indicadores de financiamento são consistentes entre card e tabela**
    - **Validates: Requirements 4.1, 4.2, 4.3, 4.5**
  - [ ]* 9.4 Escrever teste de propriedade para Property 3 (linha de totais é soma das linhas visíveis)
    - **Property 3: Linha de totais é igual à soma das linhas visíveis**
    - **Validates: Requirements 3.7, 5.1, 5.3, 5.4**

- [x] 10. Implementar exibição completa, numerada e com scroll na Tabela_Cursos
  - [x] 10.1 Substituir a chamada `_tabela_html(df_cursos_tab)` no Painel_Detalhe pela renderização inline que não usa `max_rows` e inclui a coluna `"#"` como primeira coluna com valores `1..N`
    - Envolver a tabela em `html.Div(..., style={"overflowY": "auto", "maxHeight": "600px"})` dentro do card de detalhes
    - _Requisitos: 8.1, 8.2, 8.4, 8.5_
  - [ ]* 10.2 Escrever teste de propriedade para Property 6 (numeração "#" é sequencial e sem lacunas)
    - **Property 6: Numeração da coluna "#" é sequencial e sem lacunas após qualquer filtragem**
    - **Validates: Requirements 8.1, 8.2, 8.3**

- [x] 11. Implementar filtros de cursos no Painel_Detalhe
  - [x] 11.1 Adicionar controles de filtro no topo da seção da Tabela_Cursos dentro de `renderizar_detalhes_ies()`:
    - `dcc.Input(id="mun-curso-busca", type="text", placeholder="Buscar curso...")` para busca textual
    - `dcc.Dropdown(id="mun-curso-modal")` populado com modalidades disponíveis na IES + "Todas"
    - `dcc.Dropdown(id="mun-curso-grau")` populado com graus disponíveis + "Todos"
    - `dcc.Dropdown(id="mun-curso-area")` populado com áreas CINE disponíveis + "Todas"
    - _Requisitos: 3.1, 3.2, 3.3, 3.4_
  - [x] 11.2 Criar callback `filtrar_tabela_cursos()` com `Input("mun-curso-busca", "value")`, `Input("mun-curso-modal", "value")`, `Input("mun-curso-grau", "value")`, `Input("mun-curso-area", "value")` e `State("mun-ies-selecionada", "data")` que:
    - Aplica busca case-insensitive por substring em `no_curso`
    - Aplica filtros de modalidade, grau e área por igualdade exata quando diferente de "Todas/Todos"
    - Reconstrói a tabela com renumeração sequencial da coluna `"#"`, linha de totais recalculada e mensagem de vazio quando necessário
    - _Requisitos: 3.5, 3.6, 3.7, 5.4, 8.3, 10.5_
  - [ ]* 11.3 Escrever teste de propriedade para Property 8 (busca textual é case-insensitive e por substring)
    - **Property 8: Busca textual é case-insensitive e baseada em substring**
    - **Validates: Requirements 3.1**

- [x] 12. Implementar exportação CSV e Excel da Tabela_Cursos
  - [x] 12.1 Adicionar `dcc.Download(id="mun-download")` ao layout do Painel_Detalhe e os botões "Exportar CSV" (`id="mun-btn-export-csv"`) e, condicionalmente quando `_HAS_OPENPYXL=True`, "Exportar Excel" (`id="mun-btn-export-xlsx"`) posicionados na primeira linha do card de detalhes, ao lado do título
    - Adicionar `_HAS_OPENPYXL` como constante global usando `try/import openpyxl`
    - _Requisitos: 6.1, 6.6_
  - [x] 12.2 Criar callback `exportar_cursos()` com `Input("mun-btn-export-csv", "n_clicks")`, `Input("mun-btn-export-xlsx", "n_clicks")` e os `State` necessários (co_ies, uf, mun, ano, filtros de curso) que:
    - Reconstrói o DataFrame filtrado exatamente como está visível (mesma lógica de `filtrar_tabela_cursos`)
    - Para CSV: usa `dcc.send_data_frame(df.to_csv, filename, index=False)` com nome `cursos_<sg_ies>_<co_ies>_<ano>.csv`
    - Para Excel: usa `dcc.send_bytes(lambda b: df.to_excel(b, index=False), filename)` com extensão `.xlsx`
    - _Requisitos: 6.2, 6.3, 6.4, 6.5_
  - [ ]* 12.3 Escrever teste de propriedade para Property 4 (exportação CSV preserva exatamente o conteúdo filtrado)
    - **Property 4: Exportação CSV preserva exatamente o conteúdo filtrado**
    - **Validates: Requirements 6.2, 6.5**
  - [ ]* 12.4 Escrever teste de propriedade para Property 10 (nome do arquivo CSV segue o padrão definido)
    - **Property 10: Nome do arquivo CSV exportado segue o padrão definido**
    - **Validates: Requirements 6.4**

- [x] 13. Checkpoint — Testar Painel_Detalhe: totais, filtros de curso e exportação
  - Garantir que todos os testes passam, verificar que FIES no card bate com a coluna FIES na tabela, perguntar ao usuário se houver dúvidas.

- [x] 14. Implementar abertura do Painel_Detalhe em nova aba do navegador
  - [x] 14.1 Adicionar rota `/educacao-superior/ies` ao layout raiz declarando um callback `renderizar_pagina_ies()` que intercepta `dcc.Location` quando `pathname` termina em `/ies`, extrai `co_ies`, `uf`, `municipio` e `ano` da query string e renderiza o Painel_Detalhe isolado
    - Implementar validação de `co_ies`: se não encontrado em `df_cursos`, exibir mensagem de erro com link de volta
    - _Requisitos: 2.2, 2.3, 2.4_
  - [x] 14.2 Substituir o botão `"Ver Cursos e Alunos"` na Tabela_IES por um componente `html.A` com `href` apontando para `/educacao-superior/ies?co_ies=<val>&uf=<uf>&municipio=<mun>&ano=<ano>` e `target="_blank"`
    - Manter o estado visual de seleção na Tabela_IES por meio de cor de fundo via `is_selected`
    - _Requisitos: 2.1, 2.5_
  - [ ]* 14.3 Escrever teste unitário para renderização de URL inválida (co_ies inexistente retorna mensagem de erro legível)
    - _Requisitos: 2.4_

- [x] 15. Implementar sub-abas internas e mapa de pontos por município
  - [x] 15.1 Criar callback `renderizar_sub_aba_municipio()` com `Input("mun-sub-abas", "value")` que controla o conteúdo de `mun-sub-aba-conteudo`: para `"sub-tabela"` retorna os containers atuais (Tabela_IES + Painel_Detalhe); para `"sub-mapa"` retorna o layout do mapa
    - _Requisitos: 11.1, 11.2_
  - [x] 15.2 Criar a função `_aba_mapa_municipio_layout()` que retorna o layout da sub-aba de mapa: dropdown de indicador (`id="mun-mapa-indicador"`, opções Matrículas/Ingressantes/Concluintes/IES/Cursos) e container `id="mun-mapa-mun-container"`
    - _Requisitos: 11.3, 11.4_
  - [x] 15.3 Criar callback `renderizar_mapa_municipios()` com inputs `mun-uf`, `mun-ano`, `mun-mapa-indicador` que:
    - Agrega o indicador por `co_municipio` no DataFrame filtrado por UF e ano
    - Faz join com `_df_coords` via `co_municipio` → `codigo_ibge`
    - Normaliza tamanho dos pontos proporcionalmente ao valor do indicador
    - Renderiza `go.Scattermap` com `hovertemplate` contendo nome do município, valor do indicador e número de IES
    - Exibe mensagem de aviso se DataFrame resultante for vazio
    - _Requisitos: 11.3, 11.5, 11.6, 11.7_

- [x] 16. Implementar decodificação no cabeçalho do Painel_Detalhe
  - Aplicar `_decode_categoria()` ao campo `tp_categoria_administrativa` da IES selecionada em `renderizar_detalhes_ies()` e exibir o rótulo ao lado do campo de rede no cabeçalho da IES
  - _Requisitos: 12.5_

- [x] 17. Checkpoint final — Garantir todos os testes passam
  - Rodar `pytest tests/ -v` (ou o equivalente no ambiente), verificar cobertura de todos os 12 requisitos, perguntar ao usuário se houver dúvidas.

## Notes

- Tarefas marcadas com `*` são opcionais e podem ser puladas para entrega mais rápida do MVP
- Cada tarefa referencia os requisitos específicos para rastreabilidade
- Checkpoints garantem validação incremental antes de avançar para o próximo grupo
- Os testes PBT usam `hypothesis` com mínimo de 100 exemplos cada
- Testes unitários ficam em `tests/test_municipio_callbacks.py`; PBTs em `tests/test_municipio_transformations.py`
- A constante `_HAS_OPENPYXL` deve ser definida globalmente (após os imports) para controle condicional do botão Excel
- O valor `"TODOS"` é usado como sentinel interno para "Todos os Municípios" — nunca expor ao usuário

## Task Dependency Graph

```json
{
  "waves": [
    { "id": 0, "tasks": ["2.1", "3.1", "3.2", "3.3", "3.4"] },
    { "id": 1, "tasks": ["4.1", "4.2", "4.3", "5.1", "7.1", "9.1", "10.1", "12.1", "15.2"] },
    { "id": 2, "tasks": ["6.1", "7.2", "9.2", "11.1", "14.2", "15.1"] },
    { "id": 3, "tasks": ["7.3", "11.2", "12.2", "14.1", "15.3", "16"] },
    { "id": 4, "tasks": ["2.2", "4.4", "5.2", "6.2", "7.4", "9.3", "9.4", "10.2", "11.3", "12.3", "12.4", "14.3"] }
  ]
}
```
