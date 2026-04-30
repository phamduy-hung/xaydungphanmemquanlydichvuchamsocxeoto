import json
from datetime import datetime
from pathlib import Path


AUDIT_PATH = Path("data/audit_logs.json")
MAX_LOG_ENTRIES = 10000


def load_audit_logs():
    if not AUDIT_PATH.exists():
        return []
    try:
        payload = json.loads(AUDIT_PATH.read_text(encoding="utf-8"))
        if isinstance(payload, list):
            return payload
    except Exception:
        pass
    return []


def append_audit_log(action, actor="system", detail=None):
    logs = load_audit_logs()
    logs.append(
        {
            "at": datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
            "actor": actor or "system",
            "action": action or "unknown",
            "detail": detail or {},
        }
    )
    if len(logs) > MAX_LOG_ENTRIES:
        logs = logs[-MAX_LOG_ENTRIES:]
    AUDIT_PATH.parent.mkdir(parents=True, exist_ok=True)
    AUDIT_PATH.write_text(json.dumps(logs, ensure_ascii=False, indent=2), encoding="utf-8")


def prune_logs_older_than(days: int):
    days = max(0, int(days or 0))
    logs = load_audit_logs()
    if not logs:
        return 0, 0
    now = datetime.now()
    kept = []
    removed = 0
    for row in logs:
        try:
            at = datetime.strptime(str(row.get("at", "")), "%d/%m/%Y %H:%M:%S")
            if (now - at).days > days:
                removed += 1
                continue
        except Exception:
            pass
        kept.append(row)
    AUDIT_PATH.parent.mkdir(parents=True, exist_ok=True)
    AUDIT_PATH.write_text(json.dumps(kept, ensure_ascii=False, indent=2), encoding="utf-8")
    return removed, len(kept)
