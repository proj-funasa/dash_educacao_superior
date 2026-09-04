-- ============================================================
-- ETL: Bronze Layer — Educação Superior (INEP)
-- Source: seaweedfs.raw.inep_educacao_superior_cursos
--         seaweedfs.raw.inep_educacao_superior_ies
-- Target: bronze.bronze.educacao_superior_cursos
--         bronze.bronze.educacao_superior_ies
--
-- A camada raw é a ingestão bruta do Censo da Educação Superior do INEP
-- (já carregada em seaweedfs.raw). O bronze aqui é um recorte tipado das
-- colunas efetivamente usadas pelo dashboard `dash_educacao_superior`
-- (ver COLS_CURSOS / COLS_IES em dash_educacao_superior.py), reduzindo o
-- volume lido em runtime.
--
-- Executar com usuário admin do Trino.
-- ============================================================

DROP TABLE IF EXISTS bronze.bronze.educacao_superior_cursos;

CREATE TABLE bronze.bronze.educacao_superior_cursos
WITH (
    external_location = 's3a://funasa/bronze/educacao_superior_cursos',
    format = 'PARQUET'
)
AS
SELECT
    CAST(nu_ano_censo AS INTEGER)            AS nu_ano_censo,
    no_regiao,
    co_regiao,
    no_uf,
    sg_uf,
    co_uf,
    no_municipio,
    co_municipio,
    in_capital,
    tp_organizacao_academica,
    tp_rede,
    tp_categoria_administrativa,
    co_ies,
    no_curso,
    co_curso,
    no_cine_area_geral,
    no_cine_area_especifica,
    tp_grau_academico,
    tp_modalidade_ensino,
    tp_nivel_academico,
    CAST(qt_curso          AS INTEGER) AS qt_curso,
    CAST(qt_vg_total       AS INTEGER) AS qt_vg_total,
    CAST(qt_inscrito_total AS INTEGER) AS qt_inscrito_total,
    CAST(qt_ing            AS INTEGER) AS qt_ing,
    CAST(qt_ing_fem        AS INTEGER) AS qt_ing_fem,
    CAST(qt_ing_masc       AS INTEGER) AS qt_ing_masc,
    CAST(qt_mat            AS INTEGER) AS qt_mat,
    CAST(qt_mat_fem        AS INTEGER) AS qt_mat_fem,
    CAST(qt_mat_masc       AS INTEGER) AS qt_mat_masc,
    CAST(qt_conc           AS INTEGER) AS qt_conc,
    CAST(qt_conc_fem       AS INTEGER) AS qt_conc_fem,
    CAST(qt_conc_masc      AS INTEGER) AS qt_conc_masc,
    CAST(qt_ing_enem       AS INTEGER) AS qt_ing_enem,
    CAST(qt_ing_financ     AS INTEGER) AS qt_ing_financ,
    CAST(qt_mat_prounii    AS INTEGER) AS qt_mat_prounii,
    CAST(qt_mat_prounip    AS INTEGER) AS qt_mat_prounip,
    CAST(qt_mat_fies       AS INTEGER) AS qt_mat_fies,
    CAST(qt_aluno_deficiente AS INTEGER) AS qt_aluno_deficiente,
    CAST(qt_mat_deficiente   AS INTEGER) AS qt_mat_deficiente
FROM seaweedfs.raw.inep_educacao_superior_cursos;

DROP TABLE IF EXISTS bronze.bronze.educacao_superior_ies;

CREATE TABLE bronze.bronze.educacao_superior_ies
WITH (
    external_location = 's3a://funasa/bronze/educacao_superior_ies',
    format = 'PARQUET'
)
AS
SELECT
    CAST(nu_ano_censo AS INTEGER)            AS nu_ano_censo,
    no_regiao_ies,
    CAST(co_regiao_ies AS INTEGER)           AS co_regiao_ies,
    no_uf_ies,
    sg_uf_ies,
    co_municipio_ies,
    no_municipio_ies,
    in_capital_ies,
    tp_organizacao_academica,
    CAST(tp_rede AS INTEGER)                 AS tp_rede,
    tp_categoria_administrativa,
    CAST(co_ies AS INTEGER)                  AS co_ies,
    no_ies,
    sg_ies,
    CAST(qt_doc_total   AS INTEGER) AS qt_doc_total,
    CAST(qt_doc_exe     AS INTEGER) AS qt_doc_exe,
    CAST(qt_doc_ex_dout AS INTEGER) AS qt_doc_ex_dout,
    CAST(qt_doc_ex_mest AS INTEGER) AS qt_doc_ex_mest,
    CAST(qt_doc_ex_femi AS INTEGER) AS qt_doc_ex_femi,
    CAST(qt_doc_ex_masc AS INTEGER) AS qt_doc_ex_masc,
    CAST(qt_tec_total   AS INTEGER) AS qt_tec_total
FROM seaweedfs.raw.inep_educacao_superior_ies;
