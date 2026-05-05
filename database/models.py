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