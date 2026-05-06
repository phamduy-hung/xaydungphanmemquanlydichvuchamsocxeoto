from database.connection import execute, fetch_all, fetch_one


def load_users():
    rows = fetch_all(
        "SELECT username, password_plain AS password, role FROM users WHERE is_active = 1 ORDER BY id ASC"
    )
    return [dict(r) for r in rows]


def load_system_settings():
    row = fetch_one(
        """
        SELECT
            store_name, store_address, store_hotline, api_endpoint, api_key, sync_enabled,
            invoice_printer, default_vat, bank_name, bank_account_number, bank_account_name,
            bank_transfer_note, qr_payload, qr_image_path
        FROM system_settings
        ORDER BY id DESC
        LIMIT 1
        """
    )
    return dict(row) if row else None


def upsert_system_settings(payload: dict):
    current = fetch_one("SELECT id FROM system_settings ORDER BY id DESC LIMIT 1")
    if current:
        execute(
            """
            UPDATE system_settings SET
                store_name=%s,
                store_address=%s,
                store_hotline=%s,
                api_endpoint=%s,
                api_key=%s,
                sync_enabled=%s,
                invoice_printer=%s,
                default_vat=%s,
                bank_name=%s,
                bank_account_number=%s,
                bank_account_name=%s,
                bank_transfer_note=%s,
                qr_payload=%s,
                qr_image_path=%s
            WHERE id=%s
            """,
            (
                payload.get("store_name", ""),
                payload.get("store_address", ""),
                payload.get("store_hotline", ""),
                payload.get("api_endpoint", ""),
                payload.get("api_key", ""),
                1 if payload.get("sync_enabled", True) else 0,
                payload.get("invoice_printer", ""),
                float(payload.get("default_vat", 10) or 10),
                payload.get("bank_name", ""),
                payload.get("bank_account_number", ""),
                payload.get("bank_account_name", ""),
                payload.get("bank_transfer_note", ""),
                payload.get("qr_payload", ""),
                payload.get("qr_image_path", ""),
                current["id"],
            ),
        )
        return current["id"]

    return execute(
        """
        INSERT INTO system_settings (
            store_name, store_address, store_hotline, api_endpoint, api_key, sync_enabled,
            invoice_printer, default_vat, bank_name, bank_account_number, bank_account_name,
            bank_transfer_note, qr_payload, qr_image_path
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """,
        (
            payload.get("store_name", ""),
            payload.get("store_address", ""),
            payload.get("store_hotline", ""),
            payload.get("api_endpoint", ""),
            payload.get("api_key", ""),
            1 if payload.get("sync_enabled", True) else 0,
            payload.get("invoice_printer", ""),
            float(payload.get("default_vat", 10) or 10),
            payload.get("bank_name", ""),
            payload.get("bank_account_number", ""),
            payload.get("bank_account_name", ""),
            payload.get("bank_transfer_note", ""),
            payload.get("qr_payload", ""),
            payload.get("qr_image_path", ""),
        ),
    )


# Product/Inventory functions
def load_products():
    try:
        rows = fetch_all(
            "SELECT id, product_code, name, category, unit, price, min_stock, current_stock FROM products ORDER BY id ASC"
        )
        if rows is False:
            return []
        return [dict(r) for r in rows]
    except Exception as e:
        print(f"Error loading products: {e}")
        return []


def get_product_by_id(product_id):
    try:
        row = fetch_one(
            "SELECT id, product_code, name, category, unit, price, min_stock, current_stock FROM products WHERE id = %s",
            (product_id,)
        )
        return dict(row) if row else None
    except Exception as e:
        print(f"Error getting product by id: {e}")
        return None


def get_product_by_code(product_code):
    try:
        row = fetch_one(
            "SELECT id, product_code, name, category, unit, price, min_stock, current_stock FROM products WHERE product_code = %s",
            (product_code,)
        )
        return dict(row) if row else None
    except Exception as e:
        print(f"Error getting product by code: {e}")
        return None


def insert_product(product_code, name, category, unit, price, min_stock, current_stock=0):
    try:
        return execute(
            "INSERT INTO products (product_code, name, category, unit, price, min_stock, current_stock) VALUES (%s, %s, %s, %s, %s, %s, %s)",
            (product_code, name, category, unit, price, min_stock, current_stock)
        )
    except Exception as e:
        print(f"Error inserting product: {e}")
        raise


def update_product(product_id, product_code, name, category, unit, price, min_stock):
    try:
        execute(
            "UPDATE products SET product_code=%s, name=%s, category=%s, unit=%s, price=%s, min_stock=%s WHERE id=%s",
            (product_code, name, category, unit, price, min_stock, product_id)
        )
    except Exception as e:
        print(f"Error updating product: {e}")
        raise


def delete_product(product_id):
    try:
        execute("DELETE FROM products WHERE id = %s", (product_id,))
    except Exception as e:
        print(f"Error deleting product: {e}")
        raise


def update_product_stock(product_id, new_stock):
    try:
        execute("UPDATE products SET current_stock = %s WHERE id = %s", (new_stock, product_id))
    except Exception as e:
        print(f"Error updating product stock: {e}")
        raise


def insert_inventory_transaction(product_id, transaction_type, quantity, reason='', reference_no=''):
    try:
        execute(
            "INSERT INTO inventory_transactions (product_id, transaction_type, quantity, reason, reference_no) VALUES (%s, %s, %s, %s, %s)",
            (product_id, transaction_type, quantity, reason, reference_no)
        )
    except Exception as e:
        print(f"Error inserting inventory transaction: {e}")
        raise


def get_inventory_transactions(product_id=None, limit=100):
    try:
        if product_id:
            rows = fetch_all(
                "SELECT * FROM inventory_transactions WHERE product_id = %s ORDER BY created_at DESC LIMIT %s",
                (product_id, limit)
            )
        else:
            rows = fetch_all(
                "SELECT * FROM inventory_transactions ORDER BY created_at DESC LIMIT %s",
                (limit,)
            )
        if rows is False:
            return []
        return [dict(r) for r in rows]
    except Exception as e:
        print(f"Error getting inventory transactions: {e}")
        return []


def get_low_stock_products():
    try:
        rows = fetch_all(
            "SELECT id, product_code, name, current_stock, min_stock FROM products WHERE current_stock <= min_stock ORDER BY current_stock ASC"
        )
        if rows is False:
            return []
        return [dict(r) for r in rows]
    except Exception as e:
        print(f"Error getting low stock products: {e}")
        return []