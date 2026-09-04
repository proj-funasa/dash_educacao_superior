#!/usr/bin/env python3
"""
ETL Runner — Educação Superior (INEP): raw → bronze → silver → gold no Trino.

A camada raw (seaweedfs.raw.inep_educacao_superior_cursos / _ies) é a
ingestão bruta do Censo da Educação Superior do INEP e não é produzida aqui.
Este runner promove raw → bronze → silver → gold, materializando Parquet no
SeaweedFS (s3a://funasa/{bronze,silver,gold}/educacao_superior_*).

Uso:
    python run.py                 # executa todas as camadas (bronze → gold)
    python run.py --layer silver  # executa da silver em diante
    python run.py --layer gold    # executa apenas gold

Variáveis (com defaults para o Trino interno do cluster):
    TRINO_HOST (default trino.trino.svc.cluster.local)
    TRINO_PORT (default 8080)
    TRINO_ADMIN_USER (default admin)     — precisa de permissão de escrita
    TRINO_ADMIN_PASSWORD (opcional)      — se definido, usa HTTPS + BasicAuth
"""

import os
import sys
import time
import argparse
from pathlib import Path

import trino.dbapi
from trino.auth import BasicAuthentication

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

try:
    import urllib3
    urllib3.disable_warnings()
except ImportError:
    pass

TRINO_HOST = os.getenv("TRINO_HOST", "trino.trino.svc.cluster.local")
TRINO_PORT = int(os.getenv("TRINO_PORT", "8080"))
TRINO_ADMIN_USER = os.getenv("TRINO_ADMIN_USER", "admin")
TRINO_ADMIN_PASSWORD = os.getenv("TRINO_ADMIN_PASSWORD", "")

ETL_DIR = Path(__file__).parent

LAYERS = ["01_bronze.sql", "02_silver.sql", "03_gold.sql"]
LAYER_START = {"bronze": 0, "silver": 1, "gold": 2}


def get_conn():
    scheme = "https" if (TRINO_PORT == 443 or TRINO_ADMIN_PASSWORD) else "http"
    kwargs = dict(
        host=TRINO_HOST, port=TRINO_PORT,
        user=TRINO_ADMIN_USER, http_scheme=scheme,
    )
    if TRINO_ADMIN_PASSWORD:
        kwargs["auth"] = BasicAuthentication(TRINO_ADMIN_USER, TRINO_ADMIN_PASSWORD)
    if scheme == "https":
        kwargs["verify"] = False
    return trino.dbapi.connect(**kwargs)


def run_sql_file(conn, filepath: Path):
    """Executa cada statement (separado por ;) do arquivo SQL."""
    sql = filepath.read_text()
    statements = [s.strip() for s in sql.split(";") if s.strip()]

    for stmt in statements:
        # Remove linhas de comentário puro
        lines = [l for l in stmt.splitlines() if not l.strip().startswith("--")]
        clean = "\n".join(lines).strip()
        if not clean:
            continue

        print(f"  → {clean[:80].replace(chr(10), ' ')}...")
        cur = conn.cursor()
        t0 = time.time()
        cur.execute(clean)
        result = cur.fetchall()
        elapsed = time.time() - t0
        print(f"    ✓ {result} ({elapsed:.1f}s)")


def main():
    parser = argparse.ArgumentParser(description="ETL Runner — Educação Superior (bronze/silver/gold)")
    parser.add_argument("--layer", choices=["bronze", "silver", "gold"], default="bronze",
                        help="Camada inicial (executa dela em diante)")
    args = parser.parse_args()

    start_idx = LAYER_START[args.layer]
    layers_to_run = LAYERS[start_idx:]

    print("═══ ETL educacao_superior (INEP) ═══")
    print(f"  Trino: {TRINO_HOST}:{TRINO_PORT} (user: {TRINO_ADMIN_USER})")
    print(f"  Layers: {' → '.join(l.replace('.sql', '') for l in layers_to_run)}")
    print()

    conn = get_conn()

    for layer_file in layers_to_run:
        filepath = ETL_DIR / layer_file
        print(f"▶ {layer_file}")
        run_sql_file(conn, filepath)
        print()

    print("═══ ETL concluído ═══")


if __name__ == "__main__":
    main()
