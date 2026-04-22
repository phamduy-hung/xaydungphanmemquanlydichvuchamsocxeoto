import json
from datetime import datetime
from pathlib import Path

DATA_PATH = Path("data/integration_events.json")


def _default_payload():
    return {"pos_sales": [], "web_accepts": []}


def load_payload():
    if not DATA_PATH.exists():
        return _default_payload()
    try:
        raw = json.loads(DATA_PATH.read_text(encoding="utf-8"))
        if not isinstance(raw, dict):
            return _default_payload()
        data = _default_payload()
        data.update(raw)
        if not isinstance(data.get("pos_sales"), list):
            data["pos_sales"] = []
        if not isinstance(data.get("web_accepts"), list):
            data["web_accepts"] = []
        return data
    except Exception:
        return _default_payload()


def save_payload(payload):
    DATA_PATH.parent.mkdir(parents=True, exist_ok=True)
    DATA_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def append_pos_sale(event: dict):
    payload = load_payload()
    event = dict(event)
    event.setdefault("created_at", datetime.now().strftime("%d/%m/%Y %H:%M"))
    payload["pos_sales"].append(event)
    save_payload(payload)


def append_web_accept(event: dict):
    payload = load_payload()
    event = dict(event)
    event.setdefault("accepted_at", datetime.now().strftime("%d/%m/%Y %H:%M"))
    payload["web_accepts"].append(event)
    save_payload(payload)


def get_pos_sales():
    return list(load_payload().get("pos_sales", []))
