import json

from database.connection import ensure_mysql_ready, execute, fetch_all


MAX_LOG_ENTRIES = 10000


def load_audit_logs():
    ensure_mysql_ready()
    rows = fetch_all(
        """
        SELECT at_time, actor, action_key, detail_json
        FROM audit_logs
        ORDER BY id ASC
        """
    )
    result = []
    for row in rows:
        at_time = row.get("at_time")
        detail = row.get("detail_json") or {}
        if isinstance(detail, str):
            try:
                detail = json.loads(detail)
            except Exception:
                detail = {}
        result.append(
            {
                "at": at_time.strftime("%d/%m/%Y %H:%M:%S") if at_time else "",
                "actor": row.get("actor", "system"),
                "action": row.get("action_key", "unknown"),
                "detail": detail,
            }
        )
    return result


def append_audit_log(action, actor="system", detail=None):
    ensure_mysql_ready()
    execute(
        """
        INSERT INTO audit_logs(at_time, actor, action_key, detail_json)
        VALUES (NOW(), %s, %s, %s)
        """,
        (actor or "system", action or "unknown", json.dumps(detail or {}, ensure_ascii=False)),
    )
    execute(
        """
        DELETE FROM audit_logs
        WHERE id NOT IN (
            SELECT id FROM (
                SELECT id FROM audit_logs ORDER BY id DESC LIMIT %s
            ) t
        )
        """,
        (MAX_LOG_ENTRIES,),
    )


def prune_logs_older_than(days: int):
    days = max(0, int(days or 0))
    ensure_mysql_ready()
    before_row = fetch_all("SELECT COUNT(*) AS total FROM audit_logs")
    before = int(before_row[0]["total"]) if before_row else 0
    execute(
        """
        DELETE FROM audit_logs
        WHERE at_time < DATE_SUB(NOW(), INTERVAL %s DAY)
        """,
        (days,),
    )
    after_row = fetch_all("SELECT COUNT(*) AS total FROM audit_logs")
    after = int(after_row[0]["total"]) if after_row else 0
    return before - after, after
