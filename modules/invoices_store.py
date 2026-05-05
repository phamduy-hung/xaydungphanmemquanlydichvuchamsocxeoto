from datetime import datetime

from database.connection import ensure_mysql_ready, execute, fetch_all, fetch_one

FINAL_STATUSES = {"paid", "cancelled", "refunded"}


def list_invoices():
    ensure_mysql_ready()
    rows = fetch_all(
        """
        SELECT
            invoice_no, created_at, customer_name, customer_phone,
            subtotal, discount_type, discount_value, vat_percent, vat_amount,
            total_amount, payment_method, status, linked_order_no
        FROM invoices
        ORDER BY id DESC
        """
    )
    result = []
    for row in rows:
        result.append(
            {
                "invoice_no": row.get("invoice_no", ""),
                "created_at": row["created_at"].strftime("%d/%m/%Y %H:%M") if row.get("created_at") else "",
                "customer_name": row.get("customer_name", ""),
                "customer_phone": row.get("customer_phone", ""),
                "subtotal": float(row.get("subtotal") or 0),
                "discount_type": row.get("discount_type", "none"),
                "discount_value": float(row.get("discount_value") or 0),
                "vat_percent": float(row.get("vat_percent") or 0),
                "vat_amount": float(row.get("vat_amount") or 0),
                "total_amount": float(row.get("total_amount") or 0),
                "payment_method": row.get("payment_method", ""),
                "status": row.get("status", ""),
                "linked_order_no": row.get("linked_order_no", ""),
            }
        )
    return result


def append_invoice(invoice):
    ensure_mysql_ready()
    data = dict(invoice)
    invoice_no = str(data.get("invoice_no", "")).strip()
    if not invoice_no:
        invoice_no = f"INV{datetime.now().strftime('%Y%m%d%H%M%S')}"
        data["invoice_no"] = invoice_no

    exists = fetch_one("SELECT id FROM invoices WHERE invoice_no=%s", (invoice_no,))
    if exists:
        return

    def _num(v, default=0.0):
        try:
            return float(v)
        except Exception:
            return default

    execute(
        """
        INSERT INTO invoices(
            invoice_no, created_at, customer_name, customer_phone,
            subtotal, discount_type, discount_value, vat_percent, vat_amount,
            total_amount, payment_method, status, linked_order_no
        ) VALUES (%s, NOW(), %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """,
        (
            invoice_no,
            data.get("customer_name", "Khách lẻ"),
            data.get("customer_phone", ""),
            _num(data.get("subtotal", data.get("sub_total", 0))),
            str(data.get("discount_type", "none")),
            _num(data.get("discount_value", data.get("discount_amount", 0))),
            _num(data.get("vat_percent", 10)),
            _num(data.get("vat_amount", 0)),
            _num(data.get("total", data.get("total_amount", 0))),
            str(data.get("payment_method", "bank")),
            str(data.get("status", "paid")).lower(),
            str(data.get("order_id", data.get("linked_order_no", ""))),
        ),
    )

    items = data.get("items", []) or []
    for item in items:
        qty = int(item.get("qty", 1) or 1)
        unit = _num(item.get("price", item.get("unit_price", 0)))
        line_total = _num(item.get("line_total", unit * qty))
        execute(
            """
            INSERT INTO invoice_items(invoice_no, item_name, item_type, qty, unit_price, line_total)
            VALUES (%s, %s, %s, %s, %s, %s)
            """,
            (
                invoice_no,
                str(item.get("name", item.get("item_name", ""))),
                str(item.get("type", item.get("item_type", "service"))),
                max(1, qty),
                unit,
                line_total,
            ),
        )
    return


def update_invoice_status(invoice_no, to_status):
    ensure_mysql_ready()
    to_status = str(to_status or "").strip().lower()
    if not to_status:
        return None
    execute("UPDATE invoices SET status=%s WHERE invoice_no=%s", (to_status, invoice_no))
    row = fetch_one(
        """
        SELECT
            invoice_no, created_at, customer_name, customer_phone,
            subtotal, discount_type, discount_value, vat_percent, vat_amount,
            total_amount, payment_method, status, linked_order_no
        FROM invoices
        WHERE invoice_no=%s
        """,
        (invoice_no,),
    )
    if not row:
        return None
    return {
        "invoice_no": row.get("invoice_no", ""),
        "created_at": row["created_at"].strftime("%d/%m/%Y %H:%M") if row.get("created_at") else "",
        "customer_name": row.get("customer_name", ""),
        "customer_phone": row.get("customer_phone", ""),
        "subtotal": float(row.get("subtotal") or 0),
        "discount_type": row.get("discount_type", "none"),
        "discount_value": float(row.get("discount_value") or 0),
        "vat_percent": float(row.get("vat_percent") or 0),
        "vat_amount": float(row.get("vat_amount") or 0),
        "total_amount": float(row.get("total_amount") or 0),
        "payment_method": row.get("payment_method", ""),
        "status": row.get("status", ""),
        "linked_order_no": row.get("linked_order_no", ""),
    }


def delete_invoice(invoice_no, current_role="Lễ tân"):
    ensure_mysql_ready()
    row = fetch_one("SELECT status FROM invoices WHERE invoice_no=%s", (invoice_no,))
    if not row:
        return False
    status = str(row.get("status", "")).lower()
    if status in FINAL_STATUSES and current_role != "Quản lý":
        raise PermissionError("Hóa đơn đã chốt, chỉ Quản lý mới được xóa.")
    execute("DELETE FROM invoices WHERE invoice_no=%s", (invoice_no,))
    return True
