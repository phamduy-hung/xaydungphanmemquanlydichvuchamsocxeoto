from datetime import datetime

from database.connection import ensure_mysql_ready, execute, fetch_all, fetch_one

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


def list_orders():
    ensure_mysql_ready()
    rows = fetch_all(
        """
        SELECT
            o.order_no, o.created_at, o.status, o.customer_name, o.customer_phone, o.plate,
            o.source, o.assigned_to, o.invoice_no
        FROM service_orders o
        ORDER BY o.id DESC
        """
    )
    result = []
    for row in rows:
        order_id = row.get("order_no", "")
        service_rows = fetch_all(
            "SELECT service_name FROM service_order_services WHERE order_no=%s ORDER BY id ASC",
            (order_id,),
        )
        material_rows = fetch_all(
            """
            SELECT item_name, qty, requested_at, exported, exported_at
            FROM service_order_material_requests
            WHERE order_no=%s
            ORDER BY id ASC
            """,
            (order_id,),
        )
        history_rows = fetch_all(
            """
            SELECT at_time, from_status, to_status, actor, note_text
            FROM service_order_history
            WHERE order_no=%s
            ORDER BY id ASC
            """,
            (order_id,),
        )
        result.append(
            {
                "order_id": order_id,
                "created_at": row["created_at"].strftime("%d/%m/%Y %H:%M") if row.get("created_at") else "",
                "status": row.get("status", ""),
                "customer_name": row.get("customer_name", ""),
                "customer_phone": row.get("customer_phone", ""),
                "plate": row.get("plate", ""),
                "services": [x.get("service_name", "") for x in service_rows],
                "source": row.get("source", "desk"),
                "assigned_to": row.get("assigned_to", ""),
                "material_requests": [
                    {
                        "item_name": x.get("item_name", ""),
                        "qty": int(x.get("qty") or 1),
                        "requested_at": x["requested_at"].strftime("%d/%m/%Y %H:%M:%S") if x.get("requested_at") else "",
                        "exported": bool(x.get("exported")),
                        "exported_at": x["exported_at"].strftime("%d/%m/%Y %H:%M:%S") if x.get("exported_at") else "",
                    }
                    for x in material_rows
                ],
                "invoice_no": row.get("invoice_no", ""),
                "history": [
                    {
                        "at": x["at_time"].strftime("%d/%m/%Y %H:%M:%S") if x.get("at_time") else "",
                        "from": x.get("from_status", ""),
                        "to": x.get("to_status", ""),
                        "by": x.get("actor", "system"),
                        "note": x.get("note_text", ""),
                    }
                    for x in history_rows
                ],
            }
        )
    return result


def get_order(order_id):
    for item in list_orders():
        if item.get("order_id") == order_id:
            return item
    return None


def _next_order_id():
    now = datetime.now().strftime("%Y%m%d%H%M%S")
    return f"SO{now}"


def append_order_history(order, from_status, to_status, actor, note=""):
    ensure_mysql_ready()
    order_id = (order or {}).get("order_id", "")
    if not order_id:
        return
    execute(
        """
        INSERT INTO service_order_history(order_no, at_time, from_status, to_status, actor, note_text)
        VALUES (%s, NOW(), %s, %s, %s, %s)
        """,
        (order_id, from_status, to_status, actor or "system", note or ""),
    )


def create_order(data):
    ensure_mysql_ready()
    order_id = data.get("order_id") or _next_order_id()
    created_at = datetime.now()
    execute(
        """
        INSERT INTO service_orders(
            order_no, created_at, status, customer_name, customer_phone, plate,
            source, assigned_to, invoice_no
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        """,
        (
            order_id,
            created_at,
            data.get("status", "CHECKED_IN"),
            data.get("customer_name", "Khách lẻ"),
            data.get("customer_phone", ""),
            data.get("plate", ""),
            data.get("source", "desk"),
            data.get("assigned_to", ""),
            data.get("invoice_no", ""),
        ),
    )
    for service_name in data.get("services", []) or []:
        if str(service_name or "").strip():
            execute(
                "INSERT INTO service_order_services(order_no, service_name, qty, unit_price) VALUES (%s, %s, 1, 0)",
                (order_id, str(service_name)),
            )
    append_order_history(order={"order_id": order_id}, from_status="-", to_status=data.get("status", "CHECKED_IN"), actor=data.get("actor", "system"), note="Tạo lệnh dịch vụ")
    return get_order(order_id)


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
    ensure_mysql_ready()
    row = fetch_one("SELECT status FROM service_orders WHERE order_no=%s", (order_id,))
    if not row:
        raise ValueError("Không tìm thấy lệnh dịch vụ")
    from_status = row.get("status", "")
    allowed = ALLOWED_TRANSITIONS.get(from_status, set())
    if to_status not in allowed:
        raise ValueError(f"Không thể chuyển từ {from_status} sang {to_status}")
    execute("UPDATE service_orders SET status=%s WHERE order_no=%s", (to_status, order_id))
    append_order_history({"order_id": order_id}, from_status, to_status, actor, note)
    return get_order(order_id)


def add_material_request(order_id, item_name, qty, actor="system"):
    ensure_mysql_ready()
    exists = fetch_one("SELECT order_no, status FROM service_orders WHERE order_no=%s", (order_id,))
    if not exists:
        raise ValueError("Không tìm thấy lệnh dịch vụ")
    req_item = str(item_name or "").strip() or "Vật tư chung"
    req_qty = max(1, int(qty or 1))
    execute(
        """
        INSERT INTO service_order_material_requests(order_no, item_name, qty, requested_at, exported, exported_at)
        VALUES (%s, %s, %s, NOW(), 0, NULL)
        """,
        (order_id, req_item, req_qty),
    )
    append_order_history({"order_id": order_id}, exists.get("status", ""), exists.get("status", ""), actor, f"Yêu cầu vật tư: {req_item} x{req_qty}")
    return {
        "item_name": req_item,
        "qty": req_qty,
        "requested_at": datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
        "exported": False,
        "exported_at": "",
    }


def mark_materials_exported(order_id, actor="system"):
    ensure_mysql_ready()
    exists = fetch_one("SELECT status FROM service_orders WHERE order_no=%s", (order_id,))
    if not exists:
        raise ValueError("Không tìm thấy lệnh dịch vụ")
    before = fetch_one(
        "SELECT COUNT(*) AS c FROM service_order_material_requests WHERE order_no=%s AND exported=0",
        (order_id,),
    )
    execute(
        """
        UPDATE service_order_material_requests
        SET exported=1, exported_at=NOW()
        WHERE order_no=%s AND exported=0
        """,
        (order_id,),
    )
    changed = int((before or {}).get("c", 0)) > 0
    if changed:
        append_order_history({"order_id": order_id}, exists.get("status", ""), exists.get("status", ""), actor, "Đã xác nhận xuất kho vật tư")
    return changed


def attach_invoice_to_order(order_id, invoice_no, actor="system"):
    ensure_mysql_ready()
    exists = fetch_one("SELECT status FROM service_orders WHERE order_no=%s", (order_id,))
    if not exists:
        raise ValueError("Không tìm thấy lệnh dịch vụ")
    invoice_no = str(invoice_no or "").strip()
    execute("UPDATE service_orders SET invoice_no=%s WHERE order_no=%s", (invoice_no, order_id))
    append_order_history({"order_id": order_id}, exists.get("status", ""), exists.get("status", ""), actor, f"Gắn hóa đơn {invoice_no}")
    return get_order(order_id)


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
