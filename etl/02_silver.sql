-- ============================================================
-- ETL: Silver Layer — Educação Superior (INEP)
-- Source: bronze.bronze.educacao_superior_cursos
--         bronze.bronze.educacao_superior_ies
-- Target: silver.silver.educacao_superior_cursos
--         silver.silver.educacao_superior_ies
--
-- Transformações:
--   - Normaliza métricas nulas para 0 (COALESCE) — o dashboard soma/agrega
--     essas colunas e nulos quebram os KPIs.
--   - Mantém o grão original (uma linha por curso / por IES por ano-censo).
--   - Trim de rótulos textuais.
--
-- Executar com usuário admin do Trino.
-- ============================================================

DROP TABLE IF EXISTS silver.silver.educacao_superior_cursos;

CREATE TABLE silver.silver.educacao_superior_cursos
WITH (
    external_location = 's3a://funasa/silver/educacao_superior_cursos',
    format = 'PARQUET'
)
AS
SELECT
    nu_ano_censo,
    TRIM(no_regiao)    AS no_regiao,
    co_regiao,
    TRIM(no_uf)        AS no_uf,
    TRIM(sg_uf)        AS sg_uf,
    co_uf,
    TRIM(no_municipio) AS no_municipio,
    co_municipio,
    in_capital,
    TRIM(tp_organizacao_academica)    AS tp_organizacao_academica,
    TRIM(tp_rede)                     AS tp_rede,
    TRIM(tp_categoria_administrativa) AS tp_categoria_administrativa,
    co_ies,
    TRIM(no_curso)                AS no_curso,
    co_curso,
    TRIM(no_cine_area_geral)      AS no_cine_area_geral,
    TRIM(no_cine_area_especifica) AS no_cine_area_especifica,
    TRIM(tp_grau_academico)       AS tp_grau_academico,
    TRIM(tp_modalidade_ensino)    AS tp_modalidade_ensino,
    TRIM(tp_nivel_academico)      AS tp_nivel_academico,
    COALESCE(qt_curso, 0)          AS qt_curso,
    COALESCE(qt_vg_total, 0)       AS qt_vg_total,
    COALESCE(qt_inscrito_total, 0) AS qt_inscrito_total,
    COALESCE(qt_ing, 0)            AS qt_ing,
    COALESCE(qt_ing_fem, 0)        AS qt_ing_fem,
    COALESCE(qt_ing_masc, 0)       AS qt_ing_masc,
    COALESCE(qt_mat, 0)            AS qt_mat,
    COALESCE(qt_mat_fem, 0)        AS qt_mat_fem,
    COALESCE(qt_mat_masc, 0)       AS qt_mat_masc,
    COALESCE(qt_conc, 0)           AS qt_conc,
    COALESCE(qt_conc_fem, 0)       AS qt_conc_fem,
    COALESCE(qt_conc_masc, 0)      AS qt_conc_masc,
    COALESCE(qt_ing_enem, 0)       AS qt_ing_enem,
    COALESCE(qt_ing_financ, 0)     AS qt_ing_financ,
    COALESCE(qt_mat_prounii, 0)    AS qt_mat_prounii,
    COALESCE(qt_mat_prounip, 0)    AS qt_mat_prounip,
    COALESCE(qt_mat_fies, 0)       AS qt_mat_fies,
    COALESCE(qt_aluno_deficiente, 0) AS qt_aluno_deficiente,
    COALESCE(qt_mat_deficiente, 0)   AS qt_mat_deficiente
FROM bronze.bronze.educacao_superior_cursos;

DROP TABLE IF EXISTS silver.silver.educacao_superior_ies;

CREATE TABLE silver.silver.educacao_superior_ies
WITH (
    external_location = 's3a://funasa/silver/educacao_superior_ies',
    format = 'PARQUET'
)
AS
SELECT
    nu_ano_censo,
    TRIM(no_regiao_ies) AS no_regiao_ies,
    co_regiao_ies,
    TRIM(no_uf_ies)     AS no_uf_ies,
    TRIM(sg_uf_ies)     AS sg_uf_ies,
    co_municipio_ies,
    TRIM(no_municipio_ies) AS no_municipio_ies,
    in_capital_ies,
    TRIM(tp_organizacao_academica)    AS tp_organizacao_academica,
    tp_rede,
    TRIM(tp_categoria_administrativa) AS tp_categoria_administrativa,
    co_ies,
    TRIM(no_ies) AS no_ies,
    TRIM(sg_ies) AS sg_ies,
    COALESCE(qt_doc_total, 0)   AS qt_doc_total,
    COALESCE(qt_doc_exe, 0)     AS qt_doc_exe,
    COALESCE(qt_doc_ex_dout, 0) AS qt_doc_ex_dout,
    COALESCE(qt_doc_ex_mest, 0) AS qt_doc_ex_mest,
    COALESCE(qt_doc_ex_femi, 0) AS qt_doc_ex_femi,
    COALESCE(qt_doc_ex_masc, 0) AS qt_doc_ex_masc,
    COALESCE(qt_tec_total, 0)   AS qt_tec_total
FROM bronze.bronze.educacao_superior_ies;
