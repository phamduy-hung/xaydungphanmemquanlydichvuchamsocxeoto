import json
import sys
from datetime import datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from database.connection import execute, fetch_one, is_mysql_available

ROOT = PROJECT_ROOT
DATA_DIR = ROOT / "data"


def _read_json(path: Path, default):
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


def _parse_dt(value: str, fmt: str):
    try:
        return datetime.strptime(value, fmt)
    except Exception:
        return None


def migrate_users():
    users = _read_json(DATA_DIR / "auth_accounts.json", [])
    for user in users:
        username = str(user.get("username", "")).strip()
        if not username:
            continue
        exists = fetch_one("SELECT id FROM users WHERE username=%s", (username,))
        if exists:
            continue
        execute(
            "INSERT INTO users(username, password_plain, role, is_active) VALUES (%s, %s, %s, 1)",
            (username, user.get("password", "123456"), user.get("role", "Lễ tân")),
        )


def migrate_settings():
    payload = _read_json(DATA_DIR / "system_settings.json", {})
    if not payload:
        return
    vat_raw = str(payload.get("default_vat", "10")).replace("%", "").strip() or "10"
    try:
        vat = float(vat_raw)
    except Exception:
        vat = 10.0

    row = fetch_one("SELECT id FROM system_settings ORDER BY id DESC LIMIT 1")
    args = (
        payload.get("store_name", ""),
        payload.get("store_address", ""),
        payload.get("store_hotline", ""),
        payload.get("api_endpoint", ""),
        payload.get("api_key", ""),
        1 if payload.get("sync_enabled", True) else 0,
        payload.get("invoice_printer", ""),
        vat,
        payload.get("bank_name", ""),
        payload.get("bank_account_number", ""),
        payload.get("bank_account_name", ""),
        payload.get("bank_transfer_note", ""),
        payload.get("qr_payload", ""),
        payload.get("qr_image_path", ""),
    )
    if row:
        execute(
            """
            UPDATE system_settings SET
                store_name=%s, store_address=%s, store_hotline=%s, api_endpoint=%s, api_key=%s,
                sync_enabled=%s, invoice_printer=%s, default_vat=%s, bank_name=%s,
                bank_account_number=%s, bank_account_name=%s, bank_transfer_note=%s,
                qr_payload=%s, qr_image_path=%s
            WHERE id=%s
            """,
            args + (row["id"],),
        )
    else:
        execute(
            """
            INSERT INTO system_settings(
                store_name, store_address, store_hotline, api_endpoint, api_key, sync_enabled,
                invoice_printer, default_vat, bank_name, bank_account_number, bank_account_name,
                bank_transfer_note, qr_payload, qr_image_path
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """,
            args,
        )


def migrate_audit_logs():
    rows = _read_json(DATA_DIR / "audit_logs.json", [])
    for row in rows:
        at_text = str(row.get("at", "")).strip()
        at_val = _parse_dt(at_text, "%d/%m/%Y %H:%M:%S") or datetime.now()
        execute(
            """
            INSERT INTO audit_logs(at_time, actor, action_key, detail_json)
            VALUES (%s, %s, %s, %s)
            """,
            (
                at_val,
                row.get("actor", "system"),
                row.get("action", "unknown"),
                json.dumps(row.get("detail", {}), ensure_ascii=False),
            ),
        )


def migrate_rbac():
    payload = _read_json(DATA_DIR / "rbac_permissions.json", {})
    sections = payload.get("sections", {}) if isinstance(payload, dict) else {}
    if not isinstance(sections, dict):
        return
    execute("DELETE FROM rbac_section_permissions")
    for role_name, section_map in sections.items():
        for section_key, can_access in (section_map or {}).items():
            execute(
                """
                INSERT INTO rbac_section_permissions(role_name, section_key, can_access)
                VALUES (%s, %s, %s)
                """,
                (role_name, section_key, 1 if bool(can_access) else 0),
            )


def migrate_service_orders():
    payload = _read_json(DATA_DIR / "service_orders.json", {"orders": []})
    orders = payload.get("orders", []) if isinstance(payload, dict) else []
    for order in orders:
        order_no = str(order.get("order_id", "")).strip()
        if not order_no:
            continue
        exists = fetch_one("SELECT id FROM service_orders WHERE order_no=%s", (order_no,))
        if exists:
            continue

        created_at = _parse_dt(str(order.get("created_at", "")).strip(), "%d/%m/%Y %H:%M") or datetime.now()
        execute(
            """
            INSERT INTO service_orders(order_no, created_at, status, customer_name, customer_phone, plate, source, assigned_to, invoice_no)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (
                order_no,
                created_at,
                order.get("status", "CHECKED_IN"),
                order.get("customer_name", "Khách lẻ"),
                order.get("customer_phone", ""),
                order.get("plate", ""),
                order.get("source", "desk"),
                order.get("assigned_to", ""),
                order.get("invoice_no", ""),
            ),
        )

        for s in order.get("services", []) or []:
            execute(
                "INSERT INTO service_order_services(order_no, service_name, qty, unit_price) VALUES (%s, %s, 1, 0)",
                (order_no, str(s)),
            )

        for req in order.get("material_requests", []) or []:
            requested_at = _parse_dt(str(req.get("requested_at", "")).strip(), "%d/%m/%Y %H:%M:%S") or datetime.now()
            exported_at = _parse_dt(str(req.get("exported_at", "")).strip(), "%d/%m/%Y %H:%M:%S")
            execute(
                """
                INSERT INTO service_order_material_requests(order_no, item_name, qty, requested_at, exported, exported_at)
                VALUES (%s, %s, %s, %s, %s, %s)
                """,
                (
                    order_no,
                    req.get("item_name", "Vật tư chung"),
                    int(req.get("qty", 1) or 1),
                    requested_at,
                    1 if req.get("exported") else 0,
                    exported_at,
                ),
            )

        for h in order.get("history", []) or []:
            at_time = _parse_dt(str(h.get("at", "")).strip(), "%d/%m/%Y %H:%M:%S") or datetime.now()
            execute(
                """
                INSERT INTO service_order_history(order_no, at_time, from_status, to_status, actor, note_text)
                VALUES (%s, %s, %s, %s, %s, %s)
                """,
                (
                    order_no,
                    at_time,
                    h.get("from", ""),
                    h.get("to", ""),
                    h.get("by", "system"),
                    h.get("note", ""),
                ),
            )


def migrate_integration_events():
    payload = _read_json(DATA_DIR / "integration_events.json", {"pos_sales": [], "web_accepts": []})
    if not isinstance(payload, dict):
        return
    execute("DELETE FROM integration_events")
    for e in payload.get("pos_sales", []) or []:
        execute(
            "INSERT INTO integration_events(event_type, payload_json, created_at) VALUES (%s, %s, NOW())",
            ("pos_sale", json.dumps(e, ensure_ascii=False)),
        )
    for e in payload.get("web_accepts", []) or []:
        execute(
            "INSERT INTO integration_events(event_type, payload_json, created_at) VALUES (%s, %s, NOW())",
            ("web_accept", json.dumps(e, ensure_ascii=False)),
        )


def migrate_cskh():
    payload = _read_json(DATA_DIR / "cham_soc_kh_marketing.json", {})
    if not isinstance(payload, dict) or not payload:
        return
    loyalty = payload.get("loyalty", {}) or {}
    thong_bao = payload.get("thong_bao", {}) or {}

    execute("DELETE FROM cskh_settings")
    execute(
        """
        INSERT INTO cskh_settings(
            diem_moi_1trieu, nguong_dong, nguong_bac, nguong_vang, nguong_vip,
            sms, zalo, email, mau_cam_on, mau_sinh_nhat
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """,
        (
            int(loyalty.get("diem_moi_1trieu", 10)),
            int(loyalty.get("nguong_dong", 0)),
            int(loyalty.get("nguong_bac", 500)),
            int(loyalty.get("nguong_vang", 1500)),
            int(loyalty.get("nguong_vip", 5000)),
            1 if thong_bao.get("sms", True) else 0,
            1 if thong_bao.get("zalo", False) else 0,
            1 if thong_bao.get("email", False) else 0,
            thong_bao.get("mau_cam_on", ""),
            thong_bao.get("mau_sinh_nhat", ""),
        ),
    )

    execute("DELETE FROM customer_care_vouchers")
    for v in payload.get("vouchers", []) or []:
        execute(
            """
            INSERT INTO customer_care_vouchers(voucher_code, campaign_name, voucher_type, voucher_value, start_date, end_date, note_text)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            """,
            (
                v.get("ma", ""),
                v.get("ten_chuong_trinh", ""),
                v.get("loai", "percent"),
                float(v.get("gia_tri", 0)),
                v.get("ngay_bd", datetime.now().strftime("%Y-%m-%d")),
                v.get("ngay_kt", datetime.now().strftime("%Y-%m-%d")),
                v.get("ghi_chu", ""),
            ),
        )

    execute("DELETE FROM cskh_message_logs")
    for r in payload.get("nhat_ky_gui", []) or []:
        execute(
            "INSERT INTO cskh_message_logs(sent_at, channel_text, summary_text, message_type) VALUES (%s, %s, %s, %s)",
            (
                r.get("thoi_gian", datetime.now().strftime("%Y-%m-%d %H:%M")),
                r.get("kenh", ""),
                r.get("tom_tat", ""),
                r.get("loai", ""),
            ),
        )

    execute("DELETE FROM cskh_reminders")
    for r in payload.get("nhac_lich", []) or []:
        execute(
            "INSERT INTO cskh_reminders(reminder_uid, service_name, remind_after_months, created_date) VALUES (%s, %s, %s, %s)",
            (
                r.get("id", ""),
                r.get("dich_vu", ""),
                int(r.get("sau_thang", 3)),
                r.get("ngay_tao", datetime.now().strftime("%Y-%m-%d")),
            ),
        )

    execute("DELETE FROM cskh_feedback")
    for r in payload.get("phan_hoi", []) or []:
        execute(
            """
            INSERT INTO cskh_feedback(feedback_uid, customer_name, feedback_type, feedback_text, created_date, service_date, called)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            """,
            (
                r.get("id", ""),
                r.get("ten_kh", ""),
                r.get("loai", ""),
                r.get("noi_dung", ""),
                r.get("ngay_ghi", datetime.now().strftime("%Y-%m-%d")),
                r.get("ngay_dich_vu", datetime.now().strftime("%Y-%m-%d")),
                1 if r.get("da_goi_tham") else 0,
            ),
        )


def migrate():
    if not is_mysql_available():
        raise RuntimeError("Thiếu mysql-connector-python. Hãy cài pip install -r requirements.txt")
    migrate_users()
    migrate_settings()
    migrate_rbac()
    migrate_audit_logs()
    migrate_service_orders()
    migrate_integration_events()
    migrate_cskh()
    print("Migrate JSON -> MySQL hoàn tất.")


if __name__ == "__main__":
    migrate()
