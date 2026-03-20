"""
PostgreSQL connection pool for Supabase-hosted Postgres.

Uses psycopg3 ConnectionPool with explicit SSL and longer timeouts so
Railway / pooler connections do not fail or hang on cold start.
"""
from __future__ import annotations

from typing import Any

import psycopg
from pgvector.psycopg import register_vector
from psycopg_pool import ConnectionPool

from app.core.config import settings

# Defer opening until first request: avoids import-time connection failures.
# `wait=True` blocks until at least one connection is ready (up to timeout).
pool = ConnectionPool(
    conninfo=settings.database_url,
    min_size=1,
    max_size=5,
    open=False,
    timeout=60.0,
    kwargs={"sslmode": "require"},
)


def ensure_pool_started() -> None:
    # Safe to call multiple times; pool will no-op if already started.
    if not getattr(pool, "_started", False):
        pool.open(wait=True, timeout=60.0)
        with pool.connection() as conn:
            register_vector(conn)
        pool._started = True


def execute_one(query: str, params: tuple[Any, ...] = ()) -> Any:
    ensure_pool_started()
    with pool.connection() as conn:
        with conn.cursor() as cur:
            cur.execute(query, params)
            return cur.fetchone()


def execute_all(query: str, params: tuple[Any, ...] = ()) -> list[Any]:
    ensure_pool_started()
    with pool.connection() as conn:
        with conn.cursor() as cur:
            cur.execute(query, params)
            return cur.fetchall()

