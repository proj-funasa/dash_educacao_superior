-- ============================================================
-- ETL: Gold Layer — Educação Superior (INEP)
-- Source: silver.silver.educacao_superior_cursos
--         silver.silver.educacao_superior_ies
-- Target: gold.gold.educacao_superior_cursos
--         gold.gold.educacao_superior_ies
--
-- Projeção final consumida pelo dashboard `dash_educacao_superior`.
-- O grão é preservado (curso / IES por ano-censo); o gold é a tabela
-- estável e enxuta que a aplicação lê via Trino (catalog seaweedfs → gold).
--
-- Após popular o gold, apontar o app para:
--   TRINO_CATALOG=gold  TRINO_SCHEMA=gold
-- (ou ajustar as queries para gold.gold.educacao_superior_*).
--
-- Executar com usuário admin do Trino.
-- ============================================================

DROP TABLE IF EXISTS gold.gold.educacao_superior_cursos;

CREATE TABLE gold.gold.educacao_superior_cursos
WITH (
    external_location = 's3a://funasa/gold/educacao_superior_cursos_v2',
    format = 'PARQUET',
    partitioned_by = ARRAY['nu_ano_censo']
)
AS
SELECT
    no_regiao, co_regiao, no_uf, sg_uf, co_uf, no_municipio, co_municipio, in_capital,
    tp_organizacao_academica, tp_rede, tp_categoria_administrativa,
    co_ies, no_curso, co_curso, no_cine_area_geral, no_cine_area_especifica,
    tp_grau_academico, tp_modalidade_ensino, tp_nivel_academico,
    qt_curso, qt_vg_total, qt_inscrito_total,
    qt_ing, qt_ing_fem, qt_ing_masc,
    qt_ing_vestibular, qt_ing_enem, qt_ing_avaliacao_seriada,
    qt_ing_selecao_simplifica, qt_ing_egr, qt_ing_outro_tipo_selecao,
    qt_ing_proc_seletivo, qt_ing_vg_remanesc, qt_ing_vg_prog_especial,
    qt_ing_outra_forma,
    qt_mat, qt_mat_fem, qt_mat_masc,
    qt_conc, qt_conc_fem, qt_conc_masc,
    qt_ing_financ, qt_ing_financ_reemb, qt_ing_fies, qt_ing_rpfies,
    qt_ing_financ_reemb_outros, qt_ing_financ_nreemb, qt_ing_prounii,
    qt_ing_prounip, qt_ing_nrpfies, qt_ing_financ_nreemb_outros,
    qt_mat_financ, qt_mat_financ_reemb, qt_mat_fies, qt_mat_rpfies,
    qt_mat_financ_reemb_outros, qt_mat_financ_nreemb, qt_mat_prounii,
    qt_mat_prounip, qt_mat_nrpfies, qt_mat_financ_nreemb_outros,
    qt_aluno_deficiente, qt_mat_deficiente,
    nu_ano_censo
FROM silver.silver.educacao_superior_cursos;

DROP TABLE IF EXISTS gold.gold.educacao_superior_ies;

CREATE TABLE gold.gold.educacao_superior_ies
WITH (
    external_location = 's3a://funasa/gold/educacao_superior_ies_v2',
    format = 'PARQUET',
    partitioned_by = ARRAY['nu_ano_censo']
)
AS
SELECT
    no_regiao_ies, co_regiao_ies, no_uf_ies, sg_uf_ies,
    co_municipio_ies, no_municipio_ies, in_capital_ies,
    tp_organizacao_academica, tp_rede, tp_categoria_administrativa,
    co_ies, no_ies, sg_ies,
    qt_doc_total, qt_doc_exe, qt_doc_ex_dout, qt_doc_ex_mest,
    qt_doc_ex_esp, qt_doc_ex_femi, qt_doc_ex_masc, qt_tec_total,
    nu_ano_censo
FROM silver.silver.educacao_superior_ies;
