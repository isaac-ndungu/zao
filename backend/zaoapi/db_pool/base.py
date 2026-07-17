import os
from django.db.backends.postgresql.base import DatabaseWrapper as BaseWrapper

_pool = None


class DatabaseWrapper(BaseWrapper):
    """PostgreSQL backend with psycopg3 connection pool support.

    Uses a shared ``psycopg_pool.ConnectionPool`` singleton when the
    environment variables ``DB_POOL_MIN`` / ``DB_POOL_MAX`` are set
    (falls back to persistent connections when omitted).
    """

    def get_new_connection(self, conn_params):
        global _pool
        min_size = os.environ.get('DB_POOL_MIN')
        max_size = os.environ.get('DB_POOL_MAX')
        if min_size and max_size:
            if _pool is None:
                from psycopg_pool import ConnectionPool
                _pool = ConnectionPool(
                    min_size=int(min_size),
                    max_size=int(max_size),
                    kwargs=conn_params,
                    open=True,
                )
            return _pool.getconn()
        return super().get_new_connection(conn_params)
