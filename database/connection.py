import os
from contextlib import contextmanager

try:
    import mysql.connector
    from mysql.connector import pooling
except Exception:  # pragma: no cover
    mysql = None
    pooling = None


_POOL = None
_ENV_LOADED = False


def _load_env_file():
    global _ENV_LOADED
    if _ENV_LOADED:
        return
    env_path = os.path.join(os.getcwd(), ".env")
    if not os.path.exists(env_path):
        _ENV_LOADED = True
        return
    try:
        with open(env_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, val = line.split("=", 1)
                key = key.strip()
                val = val.strip().strip("'").strip('"')
                if key and key not in os.environ:
                    os.environ[key] = val
    except Exception:
        pass
    _ENV_LOADED = True


def is_mysql_available() -> bool:
    return mysql is not None and pooling is not None


def is_mysql_enabled() -> bool:
    _load_env_file()
    return os.getenv("DB_ENABLED", "1").strip().lower() not in {"0", "false", "no"}


def ensure_mysql_ready():
    if not is_mysql_enabled():
        raise RuntimeError(
            "DB_ENABLED đang tắt. Production mode yêu cầu bật MySQL (DB_ENABLED=1)."
        )
    if not is_mysql_available():
        raise RuntimeError(
            "Thiếu mysql-connector-python. Hãy cài bằng: pip install -r requirements.txt"
        )


def health_check():
    try:
        ensure_mysql_ready()
        with get_connection() as conn:
            cur = conn.cursor()
            cur.execute("SELECT 1")
            cur.fetchone()
            cur.close()
        return True, "Kết nối MySQL thành công."
    except Exception as exc:
        return False, str(exc)


def get_db_config() -> dict:
    _load_env_file()
    return {
        "host": os.getenv("DB_HOST", "127.0.0.1"),
        "port": int(os.getenv("DB_PORT", "3306")),
        "database": os.getenv("DB_NAME", "car_care_management"),
        "user": os.getenv("DB_USER", "root"),
        "password": os.getenv("DB_PASS", ""),
        # Python 3.14 + mysql-connector C extension can crash on Windows.
        # Force pure-python mode for better stability.
        "use_pure": True,
        "autocommit": False,
    }


def _get_pool():
    global _POOL
    if _POOL is not None:
        return _POOL
    if not is_mysql_available():
        raise RuntimeError("Thiếu gói mysql-connector-python. Hãy cài qua pip.")
    cfg = get_db_config()
    _POOL = pooling.MySQLConnectionPool(pool_name="app_pool", pool_size=5, **cfg)
    return _POOL


@contextmanager
def get_connection():
    pool = _get_pool()
    conn = pool.get_connection()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def fetch_all(query: str, params=None):
    with get_connection() as conn:
        cur = conn.cursor(dictionary=True)
        cur.execute(query, params or ())
        rows = cur.fetchall()
        cur.close()
        return rows


def fetch_one(query: str, params=None):
    with get_connection() as conn:
        cur = conn.cursor(dictionary=True)
        cur.execute(query, params or ())
        row = cur.fetchone()
        cur.close()
        return row


def execute(query: str, params=None):
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute(query, params or ())
        last_id = cur.lastrowid
        cur.close()
        return last_id


def execute_many(query: str, seq_params):
    with get_connection() as conn:
        cur = conn.cursor()
        cur.executemany(query, seq_params)
        count = cur.rowcount
        cur.close()
        return count