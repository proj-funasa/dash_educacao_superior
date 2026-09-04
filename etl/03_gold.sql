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
    external_location = 's3a://funasa/gold/educacao_superior_cursos',
    format = 'PARQUET'
)
AS
SELECT * FROM silver.silver.educacao_superior_cursos;

DROP TABLE IF EXISTS gold.gold.educacao_superior_ies;

CREATE TABLE gold.gold.educacao_superior_ies
WITH (
    external_location = 's3a://funasa/gold/educacao_superior_ies',
    format = 'PARQUET'
)
AS
SELECT * FROM silver.silver.educacao_superior_ies;
