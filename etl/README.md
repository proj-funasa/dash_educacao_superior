# ETL — Educação Superior (INEP)

Promove o Censo da Educação Superior do INEP pelas camadas do data lake
(SeaweedFS via Trino):

```
seaweedfs.raw.inep_educacao_superior_cursos ─┐
seaweedfs.raw.inep_educacao_superior_ies    ─┤
                                              ├─▶ bronze ─▶ silver ─▶ gold
                                              │   (recorte    (limpeza,   (projeção
                                              │    tipado)     COALESCE)   final)
                                              ▼
                       gold.gold.educacao_superior_cursos / _ies
                                (tabelas lidas pelo dashboard)
```

## Camadas

| Arquivo          | Camada | O que faz |
|------------------|--------|-----------|
| `01_bronze.sql`  | bronze | Recorte tipado das colunas usadas pelo dashboard (a partir de `seaweedfs.raw`) |
| `02_silver.sql`  | silver | Limpeza: `TRIM` em rótulos, `COALESCE(...,0)` nas métricas, mantém o grão |
| `03_gold.sql`    | gold   | Projeção final estável consumida pelo app |

Cada camada materializa Parquet em `s3a://funasa/{bronze,silver,gold}/educacao_superior_*`.

## Rodar manualmente

```bash
pip install trino
# usa o Trino interno do cluster por padrão (trino.trino.svc.cluster.local:8080)
python run.py                 # bronze → silver → gold
python run.py --layer gold    # apenas gold
```

Requer um usuário Trino com permissão de escrita nos catalogs
`bronze`/`silver`/`gold` (ex.: `admin`). Defina `TRINO_ADMIN_USER` e, se o
endpoint for externo/autenticado, `TRINO_ADMIN_PASSWORD`.

## Airflow

A DAG `etl_educacao_superior` (em `../../_split_airflow/dags/`) roda este
pipeline via `KubernetesPodOperator`. Publique com o `deploy-dags.sh` do
repositório `_split_airflow`.

## Apontar o dashboard para o gold

Após popular o gold, atualizar as variáveis de ambiente do deployment para:

```
TRINO_CATALOG=gold
TRINO_SCHEMA=gold
```

e ajustar as queries do app para `gold.gold.educacao_superior_cursos` /
`_ies` (hoje leem `seaweedfs.raw.inep_educacao_superior_*`).
