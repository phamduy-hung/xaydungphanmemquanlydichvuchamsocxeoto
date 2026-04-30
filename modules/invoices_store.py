import json
from datetime import datetime
from pathlib import Path


DATA_PATH = Path("data/invoices_store.json")
FINAL_STATUSES = {"paid", "cancelled", "refunded"}


def _default_payload():
    return {"invoices": []}


def load_invoices():
    if not DATA_PATH.exists():
        return _default_payload()
    try:
        raw = json.loads(DATA_PATH.read_text(encoding="utf-8"))
        if isinstance(raw, dict) and isinstance(raw.get("invoices"), list):
            return raw
    except Exception:
        pass
    return _default_payload()


def save_invoices(payload):
    DATA_PATH.parent.mkdir(parents=True, exist_ok=True)
    DATA_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def list_invoices():
    return list(load_invoices().get("invoices", []))


def append_invoice(invoice):
    payload = load_invoices()
    data = dict(invoice)
    data.setdefault("created_at", datetime.now().strftime("%d/%m/%Y %H:%M"))
    data.setdefault("status", "paid")
    payload["invoices"].append(data)
    save_invoices(payload)


def update_invoice_status(invoice_no, to_status):
    payload = load_invoices()
    for item in payload.get("invoices", []):
        if item.get("invoice_no") == invoice_no:
            to_status = str(to_status or "").strip().lower()
            if not to_status:
                return None
            item["status"] = to_status
            save_invoices(payload)
            return item
    return None


def delete_invoice(invoice_no, current_role="Lễ tân"):
    payload = load_invoices()
    invoices = payload.get("invoices", [])
    for idx, item in enumerate(invoices):
        if item.get("invoice_no") != invoice_no:
            continue
        status = str(item.get("status", "")).lower()
        # Sau khi paid/cancelled/refunded chỉ quản lý mới được xóa.
        if status in FINAL_STATUSES and current_role != "Quản lý":
            raise PermissionError("Hóa đơn đã chốt, chỉ Quản lý mới được xóa.")
        invoices.pop(idx)
        save_invoices(payload)
        return True
    return False
