import os
import trino

TABELA = "seaweedfs.raw.inep_educacao_superior_cursos"

access = {
    "Vestibular": "qt_ing_vestibular",
    "ENEM": "qt_ing_enem",
    "Avaliacao seriada": "qt_ing_avaliacao_seriada",
    "Selecao simplificada": "qt_ing_selecao_simplifica",
    "Egresso": "qt_ing_egr",
    "Outro tipo de selecao": "qt_ing_outro_tipo_selecao",
    "Processo seletivo": "qt_ing_proc_seletivo",
    "Vaga remanescente": "qt_ing_vg_remanesc",
    "Programa especial": "qt_ing_vg_prog_especial",
    "Outra forma": "qt_ing_outra_forma",
}

# Somente categorias finais: os demais campos sao totais ou agrupadores.
financiamento = {
    "FIES reembolsavel": "qt_mat_rpfies",
    "Outros reembolsaveis": "qt_mat_financ_reemb_outros",
    "ProUni integral": "qt_mat_prounii",
    "ProUni parcial": "qt_mat_prounip",
    "FIES nao reembolsavel": "qt_mat_nrpfies",
    "Outros nao reembolsaveis": "qt_mat_financ_nreemb_outros",
}

host = os.environ.get("TRINO_HOST")
port = int(os.environ.get("TRINO_PORT", "443"))
user = os.environ.get("TRINO_USER")
password = os.environ.get("TRINO_PASSWORD")
if not host or not user or not password:
    raise SystemExit("Defina TRINO_HOST, TRINO_PORT, TRINO_USER e TRINO_PASSWORD no mesmo PowerShell.")

kwargs = {
    "host": host,
    "port": port,
    "user": user,
    "catalog": "seaweedfs",
    "schema": "raw",
    "http_scheme": "https",
    "auth": trino.auth.BasicAuthentication(user, password),
}

columns = [
    "MAX(nu_ano_censo) AS ano",
    "SUM(COALESCE(qt_ing, 0)) AS total_ingressantes",
    "SUM(COALESCE(qt_mat_financ, 0)) AS total_financiamento",
]
columns.extend(f"SUM(COALESCE({column}, 0)) AS {column}" for column in access.values())
columns.extend(f"SUM(COALESCE({column}, 0)) AS {column}" for column in financiamento.values())

query = f"""
SELECT {', '.join(columns)}
FROM {TABELA}
WHERE nu_ano_censo = (SELECT MAX(nu_ano_censo) FROM {TABELA})
"""

conn = trino.dbapi.connect(**kwargs)
try:
    cursor = conn.cursor()
    cursor.execute(query)
    row = dict(zip((item[0] for item in cursor.description), cursor.fetchone()))
finally:
    conn.close()

print(f"ANO: {row['ano']}")
print("\nFORMAS DE ACESSO")
access_sum = 0
for label, column in access.items():
    value = row[column] or 0
    access_sum += value
    print(f"{label}: {value:,.0f}")
print(f"SOMA DAS FORMAS DE ACESSO: {access_sum:,.0f}")
print(f"TOTAL DE INGRESSANTES (qt_ing): {row['total_ingressantes']:,.0f}")
print(f"DIFERENCA: {row['total_ingressantes'] - access_sum:,.0f}")

print("\nFORMAS DE FINANCIAMENTO DE MATRICULAS")
financing_sum = 0
for label, column in financiamento.items():
    value = row[column] or 0
    financing_sum += value
    print(f"{label}: {value:,.0f}")
print(f"SOMA DAS CATEGORIAS: {financing_sum:,.0f}")
print(f"TOTAL DE FINANCIAMENTO (qt_mat_financ): {row['total_financiamento']:,.0f}")
print(f"DIFERENCA: {row['total_financiamento'] - financing_sum:,.0f}")
