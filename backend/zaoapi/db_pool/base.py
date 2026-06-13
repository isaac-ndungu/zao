import os
from django.db.backends.postgresql.base import DatabaseWrapper as BaseWrapper


class DatabaseWrapper(BaseWrapper):
    """PostgreSQL backend with psycopg3 connection pool support.

    Uses ``psycopg_pool.PooledConnectionPool`` when the environment variables
    ``DB_POOL_MIN`` / ``DB_POOL_MAX`` are set (falls back to persistent
    connections when omitted).
    """

    def get_new_connection(self, conn_params):
        min_size = os.environ.get('DB_POOL_MIN')
        max_size = os.environ.get('DB_POOL_MAX')
        if min_size and max_size:
            from psycopg_pool import PooledConnectionPool
            pool = PooledConnectionPool(
                conn_params['dsn'],
                min_size=int(min_size),
                max_size=int(max_size),
                kwargs=conn_params.get('options', None),
                open=False,
            )
            pool.open()
            return pool.getconn()
        return super().get_new_connection(conn_params)
