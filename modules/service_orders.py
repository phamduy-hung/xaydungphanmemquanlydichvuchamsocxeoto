import json
from datetime import datetime
from pathlib import Path


DATA_PATH = Path("data/service_orders.json")

ALLOWED_TRANSITIONS = {
    "NEW_WEB": {"CHECKED_IN", "CANCELLED"},
    "CHECKED_IN": {"QUOTED", "CANCELLED"},
    "QUOTED": {"APPROVED", "CANCELLED"},
    "APPROVED": {"IN_SERVICE", "WAITING_PARTS", "CANCELLED"},
    "IN_SERVICE": {"WAITING_PARTS", "DONE", "CANCELLED"},
    "WAITING_PARTS": {"IN_SERVICE", "CANCELLED"},
    "DONE": {"INVOICED"},
    "INVOICED": {"PAID", "CANCELLED"},
    "PAID": {"AFTERCARE"},
    "AFTERCARE": set(),
    "CANCELLED": set(),
}


def _default_payload():
    return {"orders": []}


def load_orders():
    if not DATA_PATH.exists():
        return _default_payload()
    try:
        raw = json.loads(DATA_PATH.read_text(encoding="utf-8"))
        if isinstance(raw, dict) and isinstance(raw.get("orders"), list):
            return raw
    except Exception:
        pass
    return _default_payload()


def save_orders(payload):
    DATA_PATH.parent.mkdir(parents=True, exist_ok=True)
    DATA_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def list_orders():
    return list(load_orders().get("orders", []))


def get_order(order_id):
    for item in list_orders():
        if item.get("order_id") == order_id:
            return item
    return None


def _next_order_id():
    now = datetime.now().strftime("%Y%m%d%H%M%S")
    return f"SO{now}"


def append_order_history(order, from_status, to_status, actor, note=""):
    order.setdefault("history", [])
    order["history"].append(
        {
            "at": datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
            "from": from_status,
            "to": to_status,
            "by": actor or "system",
            "note": note or "",
        }
    )


def create_order(data):
    payload = load_orders()
    order = {
        "order_id": data.get("order_id") or _next_order_id(),
        "created_at": datetime.now().strftime("%d/%m/%Y %H:%M"),
        "status": data.get("status", "CHECKED_IN"),
        "customer_name": data.get("customer_name", "Khách lẻ"),
        "customer_phone": data.get("customer_phone", ""),
        "plate": data.get("plate", ""),
        "services": data.get("services", []),
        "source": data.get("source", "desk"),
        "assigned_to": data.get("assigned_to", ""),
        "material_requests": data.get("material_requests", []),
        "invoice_no": data.get("invoice_no", ""),
        "history": [],
    }
    append_order_history(order, "-", order["status"], data.get("actor", "system"), "Tạo lệnh dịch vụ")
    payload["orders"].append(order)
    save_orders(payload)
    return order


def create_order_from_web_booking(booking, actor="system"):
    services = [booking.get("dich_vu", "")] if booking.get("dich_vu") else []
    return create_order(
        {
            "status": "NEW_WEB",
            "customer_name": booking.get("ho_ten", "Khách web"),
            "customer_phone": booking.get("sdt", ""),
            "plate": booking.get("bien_so", ""),
            "services": services,
            "source": "web",
            "actor": actor,
        }
    )


def transition_order_status(order_id, to_status, actor="system", note=""):
    payload = load_orders()
    for order in payload.get("orders", []):
        if order.get("order_id") != order_id:
            continue
        from_status = order.get("status", "")
        allowed = ALLOWED_TRANSITIONS.get(from_status, set())
        if to_status not in allowed:
            raise ValueError(f"Không thể chuyển từ {from_status} sang {to_status}")
        order["status"] = to_status
        append_order_history(order, from_status, to_status, actor, note)
        save_orders(payload)
        return order
    raise ValueError("Không tìm thấy lệnh dịch vụ")


def add_material_request(order_id, item_name, qty, actor="system"):
    payload = load_orders()
    for order in payload.get("orders", []):
        if order.get("order_id") != order_id:
            continue
        req = {
            "item_name": str(item_name or "").strip() or "Vật tư chung",
            "qty": max(1, int(qty or 1)),
            "requested_at": datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
            "exported": False,
            "exported_at": "",
        }
        order.setdefault("material_requests", []).append(req)
        append_order_history(order, order.get("status", ""), order.get("status", ""), actor, f"Yêu cầu vật tư: {req['item_name']} x{req['qty']}")
        save_orders(payload)
        return req
    raise ValueError("Không tìm thấy lệnh dịch vụ")


def mark_materials_exported(order_id, actor="system"):
    payload = load_orders()
    for order in payload.get("orders", []):
        if order.get("order_id") != order_id:
            continue
        changed = False
        for req in order.setdefault("material_requests", []):
            if not req.get("exported"):
                req["exported"] = True
                req["exported_at"] = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
                changed = True
        if changed:
            append_order_history(order, order.get("status", ""), order.get("status", ""), actor, "Đã xác nhận xuất kho vật tư")
            save_orders(payload)
        return changed
    raise ValueError("Không tìm thấy lệnh dịch vụ")


def attach_invoice_to_order(order_id, invoice_no, actor="system"):
    payload = load_orders()
    for order in payload.get("orders", []):
        if order.get("order_id") != order_id:
            continue
        order["invoice_no"] = str(invoice_no or "").strip()
        append_order_history(order, order.get("status", ""), order.get("status", ""), actor, f"Gắn hóa đơn {order['invoice_no']}")
        save_orders(payload)
        return order
    raise ValueError("Không tìm thấy lệnh dịch vụ")


def find_latest_order_by_phone(phone, statuses=None):
    p = (phone or "").strip()
    if not p:
        return None
    items = list_orders()
    if statuses:
        statuses = set(statuses)
        items = [x for x in items if x.get("status") in statuses]
    items = [x for x in items if str(x.get("customer_phone", "")).strip() == p]
    if not items:
        return None
    return sorted(items, key=lambda x: x.get("created_at", ""), reverse=True)[0]
