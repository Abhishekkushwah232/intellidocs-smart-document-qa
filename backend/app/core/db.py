from __future__ import annotations

from typing import Any

import psycopg
from pgvector.psycopg import register_vector
from psycopg_pool import ConnectionPool

from app.core.config import settings


pool = ConnectionPool(conninfo=settings.database_url, min_size=1, max_size=5)


def ensure_pool_started() -> None:
    # Safe to call multiple times; pool will no-op if already started.
    if not getattr(pool, "_started", False):
        pool.open()
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

