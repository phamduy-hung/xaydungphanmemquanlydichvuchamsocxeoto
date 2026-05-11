from datetime import datetime

from database.connection import ensure_mysql_ready, execute, fetch_all, fetch_one
from database.models import get_product_by_code, update_product_stock, insert_inventory_transaction

FINAL_STATUSES = {"paid", "cancelled", "refunded"}


def list_invoices():
    ensure_mysql_ready()
    rows = fetch_all(
        """
        SELECT
            i.invoice_no, i.created_at, i.customer_name, i.customer_phone,
            i.subtotal, i.discount_type, i.discount_value, i.vat_percent, i.vat_amount,
            i.total_amount, i.payment_method, i.status, i.linked_order_no,
            (
                SELECT COUNT(*)
                FROM invoice_items ii
                WHERE ii.invoice_no = i.invoice_no
            ) AS item_count
        FROM invoices i
        ORDER BY i.id DESC
        """
    )
    result = []
    for row in rows:
        total_amount = float(row.get("total_amount") or 0)
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
                "total_amount": total_amount,
                "grand_total": total_amount,
                "payment_method": row.get("payment_method", ""),
                "status": row.get("status", ""),
                "linked_order_no": row.get("linked_order_no", ""),
                "item_count": int(row.get("item_count") or 0),
            }
        )
    return result


def get_invoice(invoice_no):
    ensure_mysql_ready()
    invoice_no = str(invoice_no or "").strip()
    if not invoice_no:
        return None
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
    item_rows = fetch_all(
        """
        SELECT item_name, item_type, qty, unit_price, line_total
        FROM invoice_items
        WHERE invoice_no=%s
        ORDER BY id ASC
        """,
        (invoice_no,),
    )
    lines = []
    for item in item_rows or []:
        lines.append(
            {
                "name": str(item.get("item_name") or ""),
                "item_type": str(item.get("item_type") or "service"),
                "qty": int(item.get("qty") or 1),
                "unit_price": float(item.get("unit_price") or 0),
                "line_total": float(item.get("line_total") or 0),
            }
        )
    total_amount = float(row.get("total_amount") or 0)
    return {
        "invoice_no": row.get("invoice_no", ""),
        "created_at": row["created_at"].strftime("%d/%m/%Y %H:%M") if row.get("created_at") else "",
        "customer_name": row.get("customer_name", ""),
        "customer_phone": row.get("customer_phone", ""),
        "subtotal": float(row.get("subtotal") or 0),
        "discount_type": row.get("discount_type", "none"),
        "discount_amount": float(row.get("discount_value") or 0),
        "vat_percent": float(row.get("vat_percent") or 0),
        "vat_amount": float(row.get("vat_amount") or 0),
        "total_amount": total_amount,
        "grand_total": total_amount,
        "payment_method": row.get("payment_method", ""),
        "status": row.get("status", ""),
        "linked_order_no": row.get("linked_order_no", ""),
        "lines": lines,
        "items": lines,
        "payment_payload": invoice_no,
    }


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
            _num(
                data.get("grand_total", data.get("total", data.get("total_amount", 0)))
            ),
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

        # Reduce inventory for products
        item_type = str(item.get("type", item.get("item_type", "service")))
        if item_type == "product":
            item_name = str(item.get("name", item.get("item_name", "")))
            # Assume item_name is product_code for now
            product = get_product_by_code(item_name)
            if product and product["current_stock"] >= qty:
                new_stock = product["current_stock"] - qty
                update_product_stock(product["id"], new_stock)
                insert_inventory_transaction(product["id"], 'OUT', qty, 'Bán hàng', invoice_no)
                print(f"Reduced stock for {item_name}: {product['current_stock']} -> {new_stock}")  # Debug
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
