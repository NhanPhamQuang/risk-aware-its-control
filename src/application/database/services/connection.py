import os
from pathlib import Path

import psycopg2
from dotenv import load_dotenv

# Load .env from project root
_ENV_PATH = Path(__file__).resolve().parents[4] / ".env"
load_dotenv(_ENV_PATH)

# ── Aiven production connection (commented out for local development) ──
# _DEFAULT_DSN = {
#     "dbname": "defaultdb",
#     "user": "avnadmin",
#     "password": "AVNS_Es-E-izeKfjJkDmNly7",
#     "host": "pg-ff24d4c-ringo-6580.i.aivencloud.com",
#     "port": 13103,
#     "sslmode": "require",
# }


def get_connection(dsn: dict | None = None):
    """Return a new psycopg2 connection.

    Uses *dsn* if provided, otherwise falls back to ``DATABASE_URL`` env var.
    """
    if dsn:
        return psycopg2.connect(**dsn)

    database_url = os.getenv("DATABASE_URL")
    if database_url:
        return psycopg2.connect(database_url)

    raise RuntimeError(
        "No database configuration found. "
        "Set DATABASE_URL in .env or pass a dsn dict."
    )
