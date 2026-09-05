# Requirements Document

## Introduction

Este documento define os requisitos para as melhorias na aba "Visão por Município" do Dashboard de Educação Superior (INEP/FUNASA). A aba atualmente exibe uma tabela de instituições de ensino superior (IES) por município e um painel detalhado de cursos da IES selecionada. As melhorias ampliam a usabilidade, corrigem inconsistências de dados, expandem os filtros disponíveis e introduzem novas visualizações.

O escopo é restrito ao arquivo `dash_educacao_superior.py` e às funções e callbacks associados à aba `aba-municipio`.

## Glossary

- **Dashboard**: Aplicação Plotly Dash em Python descrita em `dash_educacao_superior.py`.
- **Aba Município**: Aba `aba-municipio` do Dashboard, renderizada pela função `_aba_municipio_layout()` e seus callbacks.
- **IES**: Instituição de Ensino Superior, identificada pela coluna `co_ies` nos DataFrames.
- **Tabela_IES**: Tabela HTML que lista as IES ativas no município selecionado, construída no callback `renderizar_tabela_faculdades()`.
- **Painel_Detalhe**: Seção expansível exibida após o usuário selecionar uma IES, construída no callback `renderizar_detalhes_ies()`.
- **Tabela_Cursos**: Tabela HTML no Painel_Detalhe que lista os cursos da IES selecionada, atualmente limitada a 50 linhas pelo parâmetro `max_rows=50` da função `_tabela_html()`.
- **df_cursos**: DataFrame global com dados de cursos carregados da tabela Trino `TBL_CURSOS`.
- **df_ies**: DataFrame global com dados cadastrais de IES carregados da tabela Trino `TBL_IES`.
- **CINE**: Classificação Internacional Normalizada da Educação, fonte das colunas `no_cine_area_geral` e `no_cine_area_especifica`.
- **tp_categoria_administrativa**: Coluna numérica em `df_ies` que codifica a categoria administrativa da IES (1–7).
- **tp_rede**: Coluna textual em `df_ies` com a rede (Pública/Privada).
- **tp_modalidade_ensino**: Coluna em `df_cursos` com a modalidade (Presencial/EAD).
- **qt_mat_fies**: Coluna numérica em `df_cursos` com o total de matrículas financiadas pelo FIES.
- **Sub-aba**: Componente `dcc.Tabs` interno à Aba Município para separar visões distintas.
- **Mapa_Município**: Visualização coroplética ou de pontos mostrando distribuição de indicadores por município dentro da UF.
- **GeoJSON_Municípios**: Arquivo GeoJSON com geometrias municipais do Brasil, a ser obtido de fonte pública.

---

## Requirements

### Requirement 1: Ordenação Interativa das Colunas da Tabela_IES

**User Story:** Como analista de dados, quero clicar nos cabeçalhos das colunas da Tabela_IES para ordenar as linhas de forma crescente ou decrescente, para que eu possa priorizar rapidamente as instituições com mais matrículas, mais cursos ou outro critério relevante.

#### Acceptance Criteria

1. WHEN o usuário clica em um cabeçalho de coluna da Tabela_IES pela primeira vez, THE Dashboard SHALL reordenar as linhas por aquela coluna em ordem crescente e exibir um indicador visual (ex.: seta ↑) no cabeçalho.
2. WHEN o usuário clica no mesmo cabeçalho de coluna pela segunda vez, THE Dashboard SHALL reordenar as linhas por aquela coluna em ordem decrescente e alterar o indicador visual para ↓.
3. WHEN o usuário clica em um cabeçalho diferente, THE Dashboard SHALL reordenar por aquela nova coluna em ordem crescente e remover o indicador do cabeçalho anterior.
4. THE Tabela_IES SHALL manter a ordenação selecionada enquanto os filtros de UF, município, ano e categoria permanecerem inalterados.
5. WHEN a ordenação é aplicada a colunas numéricas (Matrículas, Ingressantes, Concluintes, Cursos Únicos), THE Dashboard SHALL ordenar pelos valores numéricos, não pela representação textual formatada.

---

### Requirement 2: Abertura do Painel_Detalhe em Nova Página do Navegador

**User Story:** Como usuário do dashboard, quero abrir o detalhamento de uma IES em uma nova aba do navegador, para que eu possa comparar múltiplas instituições simultaneamente sem perder a lista de IES do município.

#### Acceptance Criteria

1. WHEN o usuário clica no botão "Ver Cursos e Alunos" de uma IES, THE Dashboard SHALL abrir o Painel_Detalhe completo daquela IES em uma nova aba do navegador, sem navegar para fora da página atual.
2. THE nova página SHALL exibir o Painel_Detalhe com todas as seções: cabeçalho da IES, KPIs discentes/docentes, perfil de alunos, corpo docente e Tabela_Cursos completa.
3. THE URL da nova página SHALL conter os parâmetros necessários para reconstruir o painel (co_ies, uf, municipio, ano) de forma que a página seja diretamente acessível via link.
4. IF o parâmetro co_ies na URL for inválido ou não encontrado nos dados, THEN THE Dashboard SHALL exibir uma mensagem de erro legível em vez de uma página em branco.
5. THE Dashboard SHALL manter o estado da aba origem (Aba Município) inalterado após o clique que abre a nova aba.

---

### Requirement 3: Busca e Filtro de Cursos no Painel_Detalhe

**User Story:** Como usuário, quero filtrar os cursos exibidos no Painel_Detalhe por nome, modalidade, grau acadêmico ou área do conhecimento, para localizar rapidamente o curso de interesse em IES com muitos cursos (ex.: USP com 173 cursos).

#### Acceptance Criteria

1. THE Painel_Detalhe SHALL exibir um campo de busca textual posicionado acima da Tabela_Cursos que filtra as linhas cujo campo "Curso" contenha o texto digitado, sem distinção de maiúsculas/minúsculas.
2. THE Painel_Detalhe SHALL exibir um dropdown de "Modalidade" acima da Tabela_Cursos com as opções disponíveis na IES selecionada mais a opção "Todas".
3. THE Painel_Detalhe SHALL exibir um dropdown de "Grau Acadêmico" acima da Tabela_Cursos com os graus disponíveis na IES selecionada mais a opção "Todos".
4. THE Painel_Detalhe SHALL exibir um dropdown de "Área do Conhecimento" acima da Tabela_Cursos com as áreas CINE disponíveis na IES selecionada mais a opção "Todas".
5. WHEN o usuário altera qualquer filtro de busca, THE Dashboard SHALL atualizar a Tabela_Cursos imediatamente para exibir apenas as linhas que satisfazem todos os critérios ativos simultaneamente.
6. WHEN nenhum curso satisfaz os critérios de busca ativos, THE Dashboard SHALL exibir a mensagem "Nenhum curso encontrado para os filtros selecionados." no lugar da tabela.
7. THE linha de totais na Tabela_Cursos (Requirement 5) SHALL refletir apenas os cursos visíveis após aplicação dos filtros de busca.

---

### Requirement 4: Correção do Cálculo de FIES na Agregação por IES

**User Story:** Como analista de dados, quero que o total de alunos financiados pelo FIES exibido no Painel_Detalhe seja calculado corretamente para IES com múltiplos cursos, para que os números apresentados sejam confiáveis para análise.

#### Acceptance Criteria

1. WHEN o Painel_Detalhe é renderizado para uma IES, THE Dashboard SHALL calcular o total de `qt_mat_fies` somando todas as linhas do DataFrame `df_cursos` filtradas por `co_ies`, `sg_uf`, `no_municipio` e `nu_ano_censo` antes de qualquer agrupamento ou deduplicação.
2. WHEN a Tabela_Cursos agrupa cursos por `no_curso`, `tp_modalidade_ensino` e `tp_grau_academico`, THE Dashboard SHALL somar a coluna `qt_mat_fies` para cada grupo, sem descartar linhas duplicadas de autorização antes da soma.
3. THE Dashboard SHALL exibir o valor agregado de FIES no card "Perfil dos Alunos" usando a mesma fonte de dados (soma direta de `qt_mat_fies` sobre o DataFrame filtrado) que é usada na Tabela_Cursos.
4. IF o valor resultante de `qt_mat_fies` para uma IES for zero após a soma correta, THEN THE Dashboard SHALL exibir "0" sem ocultar ou substituir o valor.
5. THE mesma lógica de agregação SHALL ser aplicada às colunas `qt_mat_prounii`, `qt_mat_prounip` e `qt_ing_enem` para garantir consistência em todos os indicadores de financiamento.

---

### Requirement 5: Linha de Totais na Tabela_Cursos

**User Story:** Como usuário, quero ver uma linha "TOTAL" ao final da Tabela_Cursos que some todas as colunas numéricas, para obter uma visão consolidada dos indicadores da IES sem precisar somar manualmente.

#### Acceptance Criteria

1. THE Tabela_Cursos SHALL exibir uma linha de totais como última linha, com o rótulo "TOTAL" na coluna "Curso" e a soma de cada coluna numérica nas respectivas células.
2. THE linha de totais SHALL ser visualmente diferenciada das demais linhas por meio de negrito, cor de fundo distinta ou borda superior destacada.
3. THE linha de totais SHALL somar as colunas: Vagas, Ingressantes, Matrículas, Concluintes, FIES, ProUni, Mat. Fem., Mat. Masc., ENEM e Deficientes.
4. WHEN o usuário aplica filtros de busca (Requirement 3), THE linha de totais SHALL recalcular e exibir a soma apenas dos cursos filtrados visíveis.
5. THE colunas não numéricas da linha de totais (Modalidade, Grau, Área) SHALL exibir uma célula vazia ou traço "—".

---

### Requirement 6: Exportação da Tabela_Cursos para CSV/Excel

**User Story:** Como analista, quero exportar a tabela de cursos de uma IES para um arquivo CSV ou Excel, para analisar os dados fora do dashboard ou compartilhá-los com terceiros.

#### Acceptance Criteria

1. THE Painel_Detalhe SHALL exibir um botão "Exportar CSV" posicionado na primeira linha do card de detalhes, ao lado do título do card.
2. WHEN o usuário clica no botão "Exportar CSV", THE Dashboard SHALL iniciar o download de um arquivo `.csv` contendo todas as linhas da Tabela_Cursos da IES selecionada, incluindo a linha de totais (Requirement 5).
3. THE arquivo CSV exportado SHALL incluir um cabeçalho com os nomes das colunas conforme exibidos na tabela: Curso, Modalidade, Grau, Área, Vagas, Ingressantes, Matrículas, Concluintes, FIES, ProUni, Mat. Fem., Mat. Masc., ENEM, Deficientes.
4. THE nome do arquivo CSV SHALL seguir o padrão `cursos_<sg_ies>_<co_ies>_<ano>.csv`, usando a sigla da IES, código da IES e ano do censo.
5. WHEN o usuário aplica filtros de busca (Requirement 3), THE exportação SHALL incluir apenas os cursos filtrados visíveis, não o conjunto completo.
6. WHERE o ambiente de execução suportar a biblioteca `openpyxl`, THE Dashboard SHALL também oferecer um botão "Exportar Excel" que gera um arquivo `.xlsx` com as mesmas colunas e linha de totais.

---

### Requirement 7: Opção "Todos os Municípios" no Dropdown de Município

**User Story:** Como analista, quero selecionar "Todos os Municípios" no dropdown de município para visualizar os dados agregados de todas as IES do estado (UF), sem precisar selecionar um município específico.

#### Acceptance Criteria

1. THE dropdown de município SHALL incluir "Todos os Municípios" como primeira opção, antes dos municípios individuais.
2. WHEN o usuário seleciona "Todos os Municípios", THE Tabela_IES SHALL exibir todas as IES com cursos na UF selecionada, agregando os indicadores por IES independentemente do município.
3. WHEN o usuário seleciona "Todos os Municípios", THE Dashboard SHALL exibir no KPI de IES o total de IES únicas da UF.
4. WHEN o usuário seleciona "Todos os Municípios", THE Painel_Detalhe de uma IES clicada SHALL exibir os dados agregados de todos os municípios da UF para aquela IES, não apenas de um município.
5. THE ordenação por colunas (Requirement 1) SHALL funcionar normalmente quando "Todos os Municípios" estiver selecionado.

---

### Requirement 8: Exibição Completa e Numerada da Tabela_Cursos

**User Story:** Como usuário, quero que a tabela de cursos da IES mostre todos os cursos disponíveis (sem limite de linhas) e com numeração sequencial, para visualizar o catálogo completo de uma IES como a USP, que possui 173 cursos.

#### Acceptance Criteria

1. THE Tabela_Cursos SHALL exibir todas as linhas do DataFrame `df_cursos_tab` sem limite de linhas, removendo o parâmetro `max_rows=50` que atualmente trunca a tabela.
2. THE Tabela_Cursos SHALL incluir uma coluna "#" como primeira coluna, exibindo o número sequencial de cada linha começando em 1.
3. THE coluna "#" SHALL ser renumerada sequencialmente após a aplicação de filtros de busca (Requirement 3), de forma que a numeração reflita a posição na lista filtrada.
4. THE Tabela_Cursos SHALL manter a rolagem vertical dentro do card do Painel_Detalhe por meio de `overflowY: auto` com altura máxima definida (ex.: 600px), para evitar que tabelas longas ocupem a página inteira.
5. THE remoção do limite de linhas SHALL ser aplicada exclusivamente à Tabela_Cursos no Painel_Detalhe, sem afetar outras tabelas do dashboard que usam `_tabela_html()` com seus limites padrão.

---

### Requirement 9: Limpeza da Seleção de Município

**User Story:** Como usuário, quero poder limpar a seleção do dropdown de município para redefinir a visualização e selecionar outro município, sem precisar interagir com o filtro de UF.

#### Acceptance Criteria

1. THE dropdown de município SHALL ter a propriedade `clearable=True`, permitindo que o usuário remova a seleção com o ícone "×" nativo do componente `dcc.Dropdown`.
2. WHEN o usuário limpa a seleção do dropdown de município, THE Tabela_IES SHALL ser substituída pela mensagem "Selecione um município para visualizar as instituições."
3. WHEN o usuário limpa a seleção do dropdown de município, THE Painel_Detalhe SHALL ser ocultado ou substituído pela mensagem de instrução padrão.
4. WHEN o usuário seleciona um novo município após ter limpado a seleção, THE Dashboard SHALL carregar e exibir normalmente a Tabela_IES para o novo município.

---

### Requirement 10: Filtros Adicionais na Aba Município

**User Story:** Como analista, quero filtrar as IES e cursos exibidos na Aba Município por categoria administrativa e por modalidade de ensino, para segmentar a análise entre instituições públicas e privadas ou entre oferta presencial e EAD.

#### Acceptance Criteria

1. THE Aba Município SHALL exibir um filtro dropdown de "Categoria Administrativa" na barra de filtros existente, com as opções: "Todas", "Pública Federal", "Pública Estadual", "Pública Municipal", "Privada com fins lucrativos", "Privada sem fins lucrativos", "Especial".
2. THE Aba Município SHALL exibir um filtro dropdown de "Modalidade" na barra de filtros existente, com as opções: "Todas", "Presencial", "EAD".
3. WHEN o usuário seleciona uma Categoria Administrativa diferente de "Todas", THE Tabela_IES SHALL exibir somente as IES cuja coluna `tp_categoria_administrativa` corresponde à opção selecionada após aplicação do mapeamento definido no Requirement 12.
4. WHEN o usuário seleciona uma Modalidade diferente de "Todas", THE Tabela_IES SHALL exibir somente as IES que possuem ao menos um curso com `tp_modalidade_ensino` correspondente na UF e município filtrados.
5. WHEN o usuário seleciona uma Modalidade diferente de "Todas", THE Painel_Detalhe SHALL filtrar a Tabela_Cursos para exibir apenas os cursos com aquela modalidade.
6. WHEN filtros de Categoria Administrativa e Modalidade são combinados, THE Dashboard SHALL aplicar ambos os filtros simultaneamente (interseção).

---

### Requirement 11: Sub-abas Internas na Aba Município

**User Story:** Como analista, quero uma sub-aba de mapa coroplético dentro da Aba Município que exiba a concentração de matrículas ou IES por município dentro da UF selecionada, para identificar geograficamente os municípios mais relevantes em educação superior.

#### Acceptance Criteria

1. THE Aba Município SHALL exibir dois componentes `dcc.Tab` internos: "Tabela de IES" (conteúdo atual) e "Mapa por Município".
2. THE sub-aba "Tabela de IES" SHALL reproduzir integralmente o comportamento atual da Aba Município, incluindo todas as melhorias dos demais requisitos.
3. THE sub-aba "Mapa por Município" SHALL exibir uma visualização `go.Scattermap` (scatter map com pontos) posicionando cada município da UF como um ponto proporcional ao indicador selecionado, dada a ausência de GeoJSON municipal disponível localmente.
4. THE sub-aba "Mapa por Município" SHALL permitir ao usuário selecionar o indicador exibido (Matrículas, Ingressantes, Concluintes, IES, Cursos) via dropdown.
5. WHEN o usuário passa o cursor sobre um ponto no Scattermap, THE Dashboard SHALL exibir tooltip com: nome do município, valor do indicador selecionado e número de IES no município.
6. THE sub-aba "Mapa por Município" SHALL utilizar as colunas de latitude/longitude dos municípios calculadas como centróides aproximados a partir dos dados disponíveis em `df_cursos` (coluna `co_municipio`), obtidos de tabela de geocódigos IBGE via requisição pública ou constante embutida.
7. WHEN a UF selecionada não possuir dados para nenhum município, THE sub-aba "Mapa por Município" SHALL exibir a mensagem "Nenhum dado disponível para o estado selecionado."

---

### Requirement 12: Decodificação de `tp_categoria_administrativa`

**User Story:** Como usuário, quero que a coluna "Categoria" na Tabela_IES exiba o nome legível da categoria administrativa da instituição (ex.: "Pública Federal") em vez do código numérico, para facilitar a leitura e interpretação dos dados.

#### Acceptance Criteria

1. THE Dashboard SHALL definir um dicionário de mapeamento `CATEGORIA_ADM_MAP` que converta os valores numéricos de `tp_categoria_administrativa` para rótulos legíveis: `{1: "Pública Federal", 2: "Pública Estadual", 3: "Pública Municipal", 4: "Privada c/ fins lucrativos", 5: "Privada s/ fins lucrativos", 7: "Especial"}`.
2. THE Tabela_IES SHALL exibir uma coluna "Categoria" cujos valores são obtidos pela aplicação de `CATEGORIA_ADM_MAP` ao campo `tp_categoria_administrativa` da IES correspondente.
3. IF um valor de `tp_categoria_administrativa` não estiver no `CATEGORIA_ADM_MAP`, THEN THE Dashboard SHALL exibir o valor original sem conversão, em vez de exibir vazio ou erro.
4. THE rótulo decodificado SHALL ser utilizado também como chave de filtro no dropdown de Categoria Administrativa (Requirement 10), garantindo consistência entre a exibição e a filtragem.
5. THE Painel_Detalhe SHALL exibir o rótulo decodificado de `tp_categoria_administrativa` no cabeçalho da IES, ao lado da rede (Pública/Privada).
