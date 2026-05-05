from datetime import datetime

import json

from database.connection import ensure_mysql_ready, execute, fetch_all


def load_payload():
    ensure_mysql_ready()
    pos_rows = fetch_all(
        "SELECT payload_json, created_at FROM integration_events WHERE event_type='pos_sale' ORDER BY id ASC"
    )
    web_rows = fetch_all(
        "SELECT payload_json, created_at FROM integration_events WHERE event_type='web_accept' ORDER BY id ASC"
    )

    def _norm(rows, field):
        out = []
        for r in rows:
            payload = r.get("payload_json") or {}
            if isinstance(payload, str):
                try:
                    payload = json.loads(payload)
                except Exception:
                    payload = {}
            payload = dict(payload)
            if field not in payload:
                created = r.get("created_at")
                payload[field] = created.strftime("%d/%m/%Y %H:%M") if created else ""
            out.append(payload)
        return out

    return {
        "pos_sales": _norm(pos_rows, "created_at"),
        "web_accepts": _norm(web_rows, "accepted_at"),
    }


def append_pos_sale(event: dict):
    ensure_mysql_ready()
    data = dict(event or {})
    data.setdefault("created_at", datetime.now().strftime("%d/%m/%Y %H:%M"))
    execute(
        """
        INSERT INTO integration_events(event_type, payload_json, created_at)
        VALUES ('pos_sale', %s, NOW())
        """,
        (json.dumps(data, ensure_ascii=False),),
    )


def append_web_accept(event: dict):
    ensure_mysql_ready()
    data = dict(event or {})
    data.setdefault("accepted_at", datetime.now().strftime("%d/%m/%Y %H:%M"))
    execute(
        """
        INSERT INTO integration_events(event_type, payload_json, created_at)
        VALUES ('web_accept', %s, NOW())
        """,
        (json.dumps(data, ensure_ascii=False),),
    )


def get_pos_sales():
    return list(load_payload().get("pos_sales", []))
