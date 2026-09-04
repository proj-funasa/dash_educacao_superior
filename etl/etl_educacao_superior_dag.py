"""DAG: Educação Superior (INEP) — raw → bronze → silver → gold (Trino).

Promove o Censo da Educação Superior do INEP pelas camadas do data lake,
executando SQL no Trino interno do cluster (trino.trino.svc.cluster.local).
A camada raw (seaweedfs.raw.inep_educacao_superior_cursos / _ies) já está
ingerida; esta DAG materializa bronze → silver → gold como Parquet no
SeaweedFS (s3a://funasa/{bronze,silver,gold}/educacao_superior_*).

Diferente das DAGs rds_to_seaweedfs_* (que extraem do Postgres via imagem
dedicada), aqui a transformação é 100% Trino SQL — cada camada roda como uma
task KubernetesPodOperator numa imagem python:slim que instala `trino` e
executa os statements. As definições SQL ficam versionadas no repositório do
dashboard (dash_educacao_superior/etl/*.sql); aqui são embutidas para a DAG
ser autossuficiente no PVC do Airflow.

Escrita nos catalogs bronze/silver/gold exige um usuário Trino com permissão
(ex.: admin). Se o Trino interno aceitar escrita sem senha para esse usuário,
basta TRINO_USER; caso contrário, injetar TRINO_PASSWORD via Secret.
"""
from __future__ import annotations

import pendulum
from airflow import DAG
from airflow.providers.cncf.kubernetes.operators.pod import KubernetesPodOperator
from kubernetes.client import models as k8s

from datasus_common import DEFAULT_ARGS, NAMESPACE, NODE_SELECTOR, RESOURCES

TRINO_HOST = "trino.trino.svc.cluster.local"
TRINO_PORT = "8080"
TRINO_USER = "admin"  # precisa de permissão de escrita em bronze/silver/gold

# ── SQL de cada camada (mantido em sincronia com etl/*.sql do dashboard) ──────

BRONZE_SQL = r"""
DROP TABLE IF EXISTS bronze.bronze.educacao_superior_cursos;
CREATE TABLE bronze.bronze.educacao_superior_cursos
WITH (external_location = 's3a://funasa/bronze/educacao_superior_cursos', format = 'PARQUET') AS
SELECT
    CAST(nu_ano_censo AS INTEGER) AS nu_ano_censo,
    no_regiao, co_regiao, no_uf, sg_uf, co_uf, no_municipio, co_municipio, in_capital,
    tp_organizacao_academica, tp_rede, tp_categoria_administrativa, co_ies, no_curso, co_curso,
    no_cine_area_geral, no_cine_area_especifica, tp_grau_academico, tp_modalidade_ensino, tp_nivel_academico,
    CAST(qt_curso AS INTEGER) AS qt_curso, CAST(qt_vg_total AS INTEGER) AS qt_vg_total,
    CAST(qt_inscrito_total AS INTEGER) AS qt_inscrito_total, CAST(qt_ing AS INTEGER) AS qt_ing,
    CAST(qt_ing_fem AS INTEGER) AS qt_ing_fem, CAST(qt_ing_masc AS INTEGER) AS qt_ing_masc,
    CAST(qt_mat AS INTEGER) AS qt_mat, CAST(qt_mat_fem AS INTEGER) AS qt_mat_fem, CAST(qt_mat_masc AS INTEGER) AS qt_mat_masc,
    CAST(qt_conc AS INTEGER) AS qt_conc, CAST(qt_conc_fem AS INTEGER) AS qt_conc_fem, CAST(qt_conc_masc AS INTEGER) AS qt_conc_masc,
    CAST(qt_ing_enem AS INTEGER) AS qt_ing_enem, CAST(qt_ing_financ AS INTEGER) AS qt_ing_financ,
    CAST(qt_mat_prounii AS INTEGER) AS qt_mat_prounii, CAST(qt_mat_prounip AS INTEGER) AS qt_mat_prounip,
    CAST(qt_mat_fies AS INTEGER) AS qt_mat_fies, CAST(qt_aluno_deficiente AS INTEGER) AS qt_aluno_deficiente,
    CAST(qt_mat_deficiente AS INTEGER) AS qt_mat_deficiente
FROM seaweedfs.raw.inep_educacao_superior_cursos;
DROP TABLE IF EXISTS bronze.bronze.educacao_superior_ies;
CREATE TABLE bronze.bronze.educacao_superior_ies
WITH (external_location = 's3a://funasa/bronze/educacao_superior_ies', format = 'PARQUET') AS
SELECT
    CAST(nu_ano_censo AS INTEGER) AS nu_ano_censo,
    no_regiao_ies, CAST(co_regiao_ies AS INTEGER) AS co_regiao_ies, no_uf_ies, sg_uf_ies,
    co_municipio_ies, no_municipio_ies, in_capital_ies, tp_organizacao_academica,
    CAST(tp_rede AS INTEGER) AS tp_rede, tp_categoria_administrativa, CAST(co_ies AS INTEGER) AS co_ies, no_ies, sg_ies,
    CAST(qt_doc_total AS INTEGER) AS qt_doc_total, CAST(qt_doc_exe AS INTEGER) AS qt_doc_exe,
    CAST(qt_doc_ex_dout AS INTEGER) AS qt_doc_ex_dout, CAST(qt_doc_ex_mest AS INTEGER) AS qt_doc_ex_mest,
    CAST(qt_doc_ex_femi AS INTEGER) AS qt_doc_ex_femi, CAST(qt_doc_ex_masc AS INTEGER) AS qt_doc_ex_masc,
    CAST(qt_tec_total AS INTEGER) AS qt_tec_total
FROM seaweedfs.raw.inep_educacao_superior_ies;
"""

SILVER_SQL = r"""
DROP TABLE IF EXISTS silver.silver.educacao_superior_cursos;
CREATE TABLE silver.silver.educacao_superior_cursos
WITH (external_location = 's3a://funasa/silver/educacao_superior_cursos', format = 'PARQUET') AS
SELECT
    nu_ano_censo, TRIM(no_regiao) AS no_regiao, co_regiao, TRIM(no_uf) AS no_uf, TRIM(sg_uf) AS sg_uf, co_uf,
    TRIM(no_municipio) AS no_municipio, co_municipio, in_capital,
    TRIM(tp_organizacao_academica) AS tp_organizacao_academica, TRIM(tp_rede) AS tp_rede,
    TRIM(tp_categoria_administrativa) AS tp_categoria_administrativa, co_ies,
    TRIM(no_curso) AS no_curso, co_curso, TRIM(no_cine_area_geral) AS no_cine_area_geral,
    TRIM(no_cine_area_especifica) AS no_cine_area_especifica, TRIM(tp_grau_academico) AS tp_grau_academico,
    TRIM(tp_modalidade_ensino) AS tp_modalidade_ensino, TRIM(tp_nivel_academico) AS tp_nivel_academico,
    COALESCE(qt_curso,0) AS qt_curso, COALESCE(qt_vg_total,0) AS qt_vg_total, COALESCE(qt_inscrito_total,0) AS qt_inscrito_total,
    COALESCE(qt_ing,0) AS qt_ing, COALESCE(qt_ing_fem,0) AS qt_ing_fem, COALESCE(qt_ing_masc,0) AS qt_ing_masc,
    COALESCE(qt_mat,0) AS qt_mat, COALESCE(qt_mat_fem,0) AS qt_mat_fem, COALESCE(qt_mat_masc,0) AS qt_mat_masc,
    COALESCE(qt_conc,0) AS qt_conc, COALESCE(qt_conc_fem,0) AS qt_conc_fem, COALESCE(qt_conc_masc,0) AS qt_conc_masc,
    COALESCE(qt_ing_enem,0) AS qt_ing_enem, COALESCE(qt_ing_financ,0) AS qt_ing_financ,
    COALESCE(qt_mat_prounii,0) AS qt_mat_prounii, COALESCE(qt_mat_prounip,0) AS qt_mat_prounip,
    COALESCE(qt_mat_fies,0) AS qt_mat_fies, COALESCE(qt_aluno_deficiente,0) AS qt_aluno_deficiente,
    COALESCE(qt_mat_deficiente,0) AS qt_mat_deficiente
FROM bronze.bronze.educacao_superior_cursos;
DROP TABLE IF EXISTS silver.silver.educacao_superior_ies;
CREATE TABLE silver.silver.educacao_superior_ies
WITH (external_location = 's3a://funasa/silver/educacao_superior_ies', format = 'PARQUET') AS
SELECT
    nu_ano_censo, TRIM(no_regiao_ies) AS no_regiao_ies, co_regiao_ies, TRIM(no_uf_ies) AS no_uf_ies,
    TRIM(sg_uf_ies) AS sg_uf_ies, co_municipio_ies, TRIM(no_municipio_ies) AS no_municipio_ies, in_capital_ies,
    TRIM(tp_organizacao_academica) AS tp_organizacao_academica, tp_rede,
    TRIM(tp_categoria_administrativa) AS tp_categoria_administrativa, co_ies, TRIM(no_ies) AS no_ies, TRIM(sg_ies) AS sg_ies,
    COALESCE(qt_doc_total,0) AS qt_doc_total, COALESCE(qt_doc_exe,0) AS qt_doc_exe,
    COALESCE(qt_doc_ex_dout,0) AS qt_doc_ex_dout, COALESCE(qt_doc_ex_mest,0) AS qt_doc_ex_mest,
    COALESCE(qt_doc_ex_femi,0) AS qt_doc_ex_femi, COALESCE(qt_doc_ex_masc,0) AS qt_doc_ex_masc,
    COALESCE(qt_tec_total,0) AS qt_tec_total
FROM bronze.bronze.educacao_superior_ies;
"""

GOLD_SQL = r"""
DROP TABLE IF EXISTS gold.gold.educacao_superior_cursos;
CREATE TABLE gold.gold.educacao_superior_cursos
WITH (external_location = 's3a://funasa/gold/educacao_superior_cursos', format = 'PARQUET') AS
SELECT * FROM silver.silver.educacao_superior_cursos;
DROP TABLE IF EXISTS gold.gold.educacao_superior_ies;
CREATE TABLE gold.gold.educacao_superior_ies
WITH (external_location = 's3a://funasa/gold/educacao_superior_ies', format = 'PARQUET') AS
SELECT * FROM silver.silver.educacao_superior_ies;
"""

# Runner inline: conecta no Trino e executa cada statement do SQL passado em $LAYER_SQL.
RUNNER = r"""
import os, time, trino.dbapi
conn = trino.dbapi.connect(host=os.environ["TRINO_HOST"], port=int(os.environ["TRINO_PORT"]),
                           user=os.environ["TRINO_USER"], http_scheme="http")
sql = os.environ["LAYER_SQL"]
for stmt in [s.strip() for s in sql.split(";") if s.strip()]:
    print("->", stmt[:90].replace(chr(10), " "), flush=True)
    cur = conn.cursor(); t0 = time.time(); cur.execute(stmt); res = cur.fetchall()
    print("   OK", res, round(time.time() - t0, 1), "s", flush=True)
print("=== layer done ===", flush=True)
"""

COMMON_ENV = [
    k8s.V1EnvVar(name="TRINO_HOST", value=TRINO_HOST),
    k8s.V1EnvVar(name="TRINO_PORT", value=TRINO_PORT),
    k8s.V1EnvVar(name="TRINO_USER", value=TRINO_USER),
]


def _layer_task(task_id: str, layer_sql: str) -> KubernetesPodOperator:
    return KubernetesPodOperator(
        task_id=task_id,
        name="etl-edu-" + task_id.replace("_", "-")[:48],
        namespace=NAMESPACE,
        service_account_name="airflow",
        image="python:3.12-slim",
        image_pull_policy="IfNotPresent",
        node_selector=NODE_SELECTOR,
        container_resources=RESOURCES,
        cmds=["/bin/sh", "-c"],
        arguments=["pip install --no-cache-dir trino >/dev/null && python -c \"$RUNNER\""],
        env_vars=[
            *COMMON_ENV,
            k8s.V1EnvVar(name="LAYER_SQL", value=layer_sql),
            k8s.V1EnvVar(name="RUNNER", value=RUNNER),
        ],
        get_logs=True,
        is_delete_operator_pod=True,
        startup_timeout_seconds=300,
    )


with DAG(
    dag_id="etl_educacao_superior",
    description="Educação Superior (INEP): raw -> bronze -> silver -> gold (Trino SQL)",
    schedule=None,  # sob demanda (re-trigger após nova carga do INEP na raw)
    start_date=pendulum.datetime(2024, 1, 1, tz="America/Sao_Paulo"),
    catchup=False,
    default_args=DEFAULT_ARGS,
    tags=["educacao-superior", "inep", "trino", "bronze", "silver", "gold", "seaweedfs", "funasa"],
) as dag:

    bronze = _layer_task("bronze", BRONZE_SQL)
    silver = _layer_task("silver", SILVER_SQL)
    gold = _layer_task("gold", GOLD_SQL)

    bronze >> silver >> gold
