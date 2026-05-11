from datetime import date, datetime
import re
import sqlite3
import unicodedata
from pathlib import Path

from database.connection import ensure_mysql_ready, execute, fetch_all, fetch_one
from database.models import get_service_price, get_service_price_map
from database.models import load_products, update_product_stock, insert_inventory_transaction
from database.models import load_active_technician_names
from database.models import ensure_service_catalog, fetch_bom_lines_for_catalog_id, seed_service_material_bom_defaults
from modules.audit_log import append_audit_log

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

DEFAULT_TECH_POOL = ["Nguyen Minh Dat", "Le Quoc Khanh", "Pham Van Phuc"]

# Tối đa số xe đang trong quy trình (web pending + lệnh chưa thanh toán) / mỗi ngày làm việc.
MAX_PIPELINE_SLOTS_PER_DAY = 10

# Quy tắc vật tư mặc định theo dịch vụ (có thể mở rộng thêm).
# Mỗi dòng: "từ khóa dịch vụ": [(từ khóa sản phẩm kho, số lượng), ...]
DEFAULT_SERVICE_MATERIAL_RULES = {
    "rửa xe": [("nước rửa kính meguiar", 1), ("bọt rửa xe", 1)],
    "rua xe": [("nuoc rua kinh meguiar", 1), ("bot rua xe", 1)],
    "hút bụi": [("khăn microfiber", 1)],
    "hut bui": [("khan microfiber", 1)],
    "vệ sinh nội thất": [("dung dịch vệ sinh nội thất", 1)],
    "ve sinh noi that": [("dung dich ve sinh noi that", 1)],
    "đánh bóng": [("dung dịch đánh bóng", 1)],
    "danh bong": [("dung dich danh bong", 1)],
    "phủ ceramic": [("dung dịch ceramic", 1)],
    "phu ceramic": [("dung dich ceramic", 1)],
    "thay dầu": [("dầu", 1)],
    "thay dau": [("dau", 1)],
}

_SCHEMA_READY = False


def _ensure_schema_updates():
    global _SCHEMA_READY
    if _SCHEMA_READY:
        return
    # Backward-compatible migration for existing databases.
    # Some MySQL versions do not support "ADD COLUMN IF NOT EXISTS".
    col = fetch_one(
        """
        SELECT COLUMN_NAME
        FROM information_schema.COLUMNS
        WHERE TABLE_SCHEMA = DATABASE()
          AND TABLE_NAME = 'service_orders'
          AND COLUMN_NAME = 'car_model'
        LIMIT 1
        """
    )
    if not col:
        execute("ALTER TABLE service_orders ADD COLUMN car_model VARCHAR(100) DEFAULT ''")
    booking_col = fetch_one(
        """
        SELECT COLUMN_NAME
        FROM information_schema.COLUMNS
        WHERE TABLE_SCHEMA = DATABASE()
          AND TABLE_NAME = 'service_orders'
          AND COLUMN_NAME = 'web_booking_id'
        LIMIT 1
        """
    )
    if not booking_col:
        execute("ALTER TABLE service_orders ADD COLUMN web_booking_id VARCHAR(40) DEFAULT ''")
    svc_day_col = fetch_one(
        """
        SELECT COLUMN_NAME
        FROM information_schema.COLUMNS
        WHERE TABLE_SCHEMA = DATABASE()
          AND TABLE_NAME = 'service_orders'
          AND COLUMN_NAME = 'service_date'
        LIMIT 1
        """
    )
    if not svc_day_col:
        execute("ALTER TABLE service_orders ADD COLUMN service_date DATE NULL")
        execute(
            """
            UPDATE service_orders
            SET service_date = DATE(created_at)
            WHERE service_date IS NULL
            """
        )
    execute(
        """
        CREATE TABLE IF NOT EXISTS cskh_message_logs (
            id BIGINT AUTO_INCREMENT PRIMARY KEY,
            sent_at DATETIME NOT NULL,
            channel_text VARCHAR(80) NOT NULL,
            summary_text VARCHAR(500) NOT NULL,
            message_type VARCHAR(40) DEFAULT '',
            created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
        ) ENGINE=InnoDB
        """
    )
    _SCHEMA_READY = True


def _sqlite_bookings_db_path() -> Path:
    return Path(__file__).resolve().parent.parent / "server" / "bookings.db"


def parse_appointment_date_to_date(raw) -> date:
    """Chuẩn hóa ngày hẹn từ web / form (YYYY-MM-DD, DD/MM/YYYY)."""
    s = str(raw or "").strip()
    if not s:
        return datetime.now().date()
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y"):
        try:
            return datetime.strptime(s[: len(fmt) + 2] if fmt == "%Y-%m-%d" and len(s) > 10 else s, fmt).date()
        except ValueError:
            try:
                return datetime.strptime(s, fmt).date()
            except ValueError:
                continue
    try:
        return datetime.fromisoformat(s.replace("Z", "")[:10]).date()
    except ValueError:
        return datetime.now().date()


def count_mysql_pipeline_for_service_day(day: date) -> int:
    ensure_mysql_ready()
    _ensure_schema_updates()
    row = fetch_one(
        """
        SELECT COUNT(*) AS c
        FROM service_orders
        WHERE COALESCE(service_date, DATE(created_at)) = %s
          AND status NOT IN ('PAID', 'AFTERCARE', 'CANCELLED')
        """,
        (day.isoformat(),),
    )
    return int((row or {}).get("c", 0))


def count_sqlite_pending_bookings_for_service_day(day: date) -> int:
    db_path = _sqlite_bookings_db_path()
    if not db_path.exists():
        return 0
    try:
        conn = sqlite3.connect(str(db_path))
        cur = conn.execute("SELECT ngay_hen FROM bookings WHERE status = 'pending'")
        n = 0
        for row in cur:
            d = parse_appointment_date_to_date(row[0])
            if d == day:
                n += 1
        conn.close()
        return n
    except Exception:
        return 0


def count_occupied_pipeline_slots_for_day(day: date) -> int:
    """Đơn web chờ tiếp nhận (SQLite) + lệnh MySQL chưa thanh toán xong, cùng ngày làm việc."""
    return count_mysql_pipeline_for_service_day(day) + count_sqlite_pending_bookings_for_service_day(day)


def assert_can_add_walk_in_for_today() -> None:
    """Trực tiếp: thêm 1 slot mới trong ngày hôm nay."""
    day = datetime.now().date()
    if count_occupied_pipeline_slots_for_day(day) >= MAX_PIPELINE_SLOTS_PER_DAY:
        raise ValueError(
            f"Đã đủ {MAX_PIPELINE_SLOTS_PER_DAY} xe trong ngày {day.strftime('%d/%m/%Y')} "
            "(đang xử lý + đặt web chờ). Vui lòng chờ hoàn tất & thanh toán để nhận thêm."
        )


def assert_can_add_web_booking_pending_for_day(day: date) -> None:
    """Đặt lịch web mới: thêm 1 đơn pending cho ngày hẹn."""
    if count_occupied_pipeline_slots_for_day(day) >= MAX_PIPELINE_SLOTS_PER_DAY:
        raise ValueError(
            f"Ngày {day.strftime('%d/%m/%Y')} đã đủ {MAX_PIPELINE_SLOTS_PER_DAY} lượt đặt/xử lý. "
            "Vui lòng chọn ngày khác hoặc liên hệ cửa hàng."
        )


def _ensure_crm_vehicle_table():
    execute(
        """
        CREATE TABLE IF NOT EXISTS crm_customer_vehicles (
            id BIGINT AUTO_INCREMENT PRIMARY KEY,
            customer_id BIGINT NOT NULL,
            car_model VARCHAR(100) NOT NULL DEFAULT '',
            plate_no VARCHAR(20) NOT NULL DEFAULT '',
            UNIQUE KEY uk_customer_vehicle (customer_id, car_model, plate_no),
            INDEX idx_customer_vehicles (customer_id),
            FOREIGN KEY (customer_id) REFERENCES customers(id) ON DELETE CASCADE
        ) ENGINE=InnoDB
        """
    )


def _sync_customer_from_order(data):
    phone = str(data.get("customer_phone", "")).strip()
    if not phone:
        return
    customer_name = str(data.get("customer_name", "")).strip() or "Khách lẻ"

    row = fetch_one("SELECT id FROM customers WHERE phone=%s", (phone,))
    if row:
        customer_id = int(row["id"])
        execute(
            """
            UPDATE customers
            SET full_name=%s
            WHERE id=%s
            """,
            (customer_name, customer_id),
        )
        return

    # Seed new CRM customer from direct intake (vehicle is added after payment).
    customer_code = f"KH{datetime.now().strftime('%y%m%d%H%M%S')}"
    execute(
        """
        INSERT INTO customers(customer_code, full_name, phone, vehicle_plate, points, tier, discount_percent, total_spent)
        VALUES (%s, %s, %s, %s, 0, 'Đồng', 1, 0)
        """,
        (customer_code, customer_name, phone, ""),
    )


def list_orders():
    ensure_mysql_ready()
    _ensure_schema_updates()
    rows = fetch_all(
        """
        SELECT
            o.order_no, o.created_at, o.status, o.customer_name, o.customer_phone, o.plate, o.car_model,
            o.source, o.assigned_to, o.invoice_no, o.web_booking_id
        FROM service_orders o
        ORDER BY o.created_at ASC, o.id ASC
        """
    )
    result = []
    for row in rows:
        order_id = row.get("order_no", "")
        service_rows = fetch_all(
            "SELECT service_name, unit_price FROM service_order_services WHERE order_no=%s ORDER BY id ASC",
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
                "car_model": row.get("car_model", ""),
                "services": [x.get("service_name", "") for x in service_rows],
                "service_items": [
                    {
                        "service_name": x.get("service_name", ""),
                        "unit_price": int(float(x.get("unit_price") or 0)),
                    }
                    for x in service_rows
                ],
                "service_total": sum(int(float(x.get("unit_price") or 0)) for x in service_rows),
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
                "web_booking_id": row.get("web_booking_id", ""),
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
    ensure_mysql_ready()
    base = datetime.now().strftime("%Y%m%d%H%M%S")
    candidate = f"SO{base}"
    suffix = 0
    while fetch_one("SELECT id FROM service_orders WHERE order_no=%s LIMIT 1", (candidate,)):
        suffix += 1
        candidate = f"SO{base}{suffix:02d}"[:30]
        if suffix > 99:
            candidate = f"SO{datetime.now().strftime('%Y%m%d%H%M%S%f')}"[:30]
    return candidate


def _normalize_text(text):
    raw = str(text or "").strip().lower()
    if not raw:
        return ""
    raw = unicodedata.normalize("NFD", raw)
    raw = "".join(ch for ch in raw if unicodedata.category(ch) != "Mn")
    raw = raw.replace("đ", "d")
    raw = re.sub(r"[^a-z0-9]+", " ", raw)
    return re.sub(r"\s+", " ", raw).strip()


def _split_services_formula(text):
    raw = str(text or "").strip()
    if not raw:
        return []
    parts = [x.strip() for x in re.split(r"[+,;/|]", raw) if str(x).strip()]
    return parts if parts else [raw]


def _resolve_service_names(parts):
    price_map = get_service_price_map(active_only=True) or {}
    index = {_normalize_text(name): name for name in price_map.keys()}
    resolved = []
    for part in parts:
        norm = _normalize_text(part)
        if not norm:
            continue
        if norm in index:
            resolved.append(index[norm])
            continue
        picked = ""
        for k, name in index.items():
            if norm in k or k in norm:
                picked = name
                break
        resolved.append(picked or part.strip())
    return [x for x in resolved if x]


def _pick_balanced_technician():
    # Auto-assign technician using current open-order load.
    # Danh sách KTV hợp lệ lấy từ hr_employees (role Kỹ thuật, đang làm).
    names = set()
    try:
        names.update(load_active_technician_names())
    except Exception:
        pass
    if not names:
        names.update(DEFAULT_TECH_POOL)

    candidates = sorted(name for name in names if name)
    if not candidates:
        return ""

    open_statuses = {"NEW_WEB", "CHECKED_IN", "QUOTED", "APPROVED", "IN_SERVICE", "WAITING_PARTS"}
    today_prefix = datetime.now().strftime("%d/%m/%Y")
    open_load_by_tech = {name: 0 for name in candidates}
    today_open_load_by_tech = {name: 0 for name in candidates}
    for order in list_orders():
        assigned = str(order.get("assigned_to", "")).strip()
        if assigned not in open_load_by_tech:
            continue
        if order.get("status") not in open_statuses:
            continue
        open_load_by_tech[assigned] += 1
        created_at = str(order.get("created_at", "")).strip()
        if created_at.startswith(today_prefix):
            today_open_load_by_tech[assigned] += 1

    # Balance by current open workload first (all dates),
    # then today's open workload, then stable name tie-break.
    return min(
        candidates,
        key=lambda name: (
            open_load_by_tech.get(name, 0),
            today_open_load_by_tech.get(name, 0),
            name,
        ),
    )


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


def _notify_customer_service_done(order_id, actor="system"):
    """
    Create a CSKH message log when service is completed (status DONE).
    This is a notification record flow (SMS/Zalo/Email channels from cskh_settings).
    """
    order = get_order(order_id)
    if not order:
        return
    phone = str(order.get("customer_phone", "")).strip()
    if not phone:
        return

    cfg = fetch_one(
        """
        SELECT sms, zalo, email, mau_cam_on
        FROM cskh_settings
        ORDER BY id DESC
        LIMIT 1
        """
    ) or {}

    channels = []
    if int(cfg.get("sms") or 0):
        channels.append("SMS")
    if int(cfg.get("zalo") or 0):
        channels.append("Zalo")
    if int(cfg.get("email") or 0):
        channels.append("Email")
    channel_text = ", ".join(channels) if channels else "(chưa bật)"

    services = [str(x or "").strip() for x in (order.get("services") or []) if str(x or "").strip()]
    service_text = " + ".join(services) if services else "dịch vụ đã đăng ký"
    template = str(cfg.get("mau_cam_on") or "").strip() or "Cảm ơn {ten}! Xe đã hoàn tất dịch vụ: {dich_vu}."
    summary = (
        template.replace("{ten}", str(order.get("customer_name", "Quý khách")))
        .replace("{dich_vu}", service_text)
        .replace("{ma_hd}", str(order.get("invoice_no", "")).strip() or "sẽ cập nhật khi thanh toán")
        .replace("{link_hd}", "sẽ gửi khi xuất hóa đơn")
    )
    summary = f"{summary} (SĐT: {phone})"

    execute(
        """
        INSERT INTO cskh_message_logs(sent_at, channel_text, summary_text, message_type)
        VALUES (NOW(), %s, %s, %s)
        """,
        (channel_text, summary[:500], "service_done"),
    )
    append_audit_log(
        "service_order.notify_done",
        actor,
        {
            "order_id": order_id,
            "customer_phone": phone,
            "channel": channel_text,
            "message_type": "service_done",
        },
    )


def create_order(data):
    ensure_mysql_ready()
    _ensure_schema_updates()
    src = str(data.get("source", "desk") or "desk").strip().lower()
    if src == "desk":
        assert_can_add_walk_in_for_today()

    order_id = data.get("order_id") or _next_order_id()
    created_at = datetime.now()
    sd = data.get("service_date")
    if sd is None:
        service_date = created_at.date()
    elif isinstance(sd, datetime):
        service_date = sd.date()
    elif isinstance(sd, date):
        service_date = sd
    else:
        service_date = parse_appointment_date_to_date(sd)

    execute(
        """
        INSERT INTO service_orders(
            order_no, created_at, service_date, status, customer_name, customer_phone, plate, car_model,
            source, assigned_to, invoice_no, web_booking_id
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """,
        (
            order_id,
            created_at,
            service_date,
            data.get("status", "CHECKED_IN"),
            data.get("customer_name", "Khách lẻ"),
            data.get("customer_phone", ""),
            data.get("plate", ""),
            data.get("car_model", ""),
            data.get("source", "desk"),
            data.get("assigned_to", ""),
            data.get("invoice_no", ""),
            data.get("web_booking_id", ""),
        ),
    )
    for service_name in data.get("services", []) or []:
        service_name = str(service_name or "").strip()
        if service_name:
            unit_price = int(data.get("service_price") or get_service_price(service_name, default=0))
            execute(
                "INSERT INTO service_order_services(order_no, service_name, qty, unit_price) VALUES (%s, %s, 1, %s)",
                (order_id, service_name, unit_price),
            )
    _sync_customer_from_order(data)
    append_order_history(order={"order_id": order_id}, from_status="-", to_status=data.get("status", "CHECKED_IN"), actor=data.get("actor", "system"), note="Tạo lệnh dịch vụ")
    return get_order(order_id)


def create_order_from_web_booking(booking, actor="system"):
    raw_formula = str(booking.get("dich_vu", "")).strip()
    services = _resolve_service_names(_split_services_formula(raw_formula))
    assigned_to = _pick_balanced_technician()
    svc_day = parse_appointment_date_to_date(booking.get("ngay_hen"))
    return create_order(
        {
            "status": "NEW_WEB",
            "customer_name": booking.get("ho_ten", "Khách web"),
            "customer_phone": booking.get("sdt", ""),
            "plate": booking.get("bien_so", ""),
            "car_model": booking.get("hang_xe", ""),
            "services": services,
            "source": "web",
            "assigned_to": assigned_to,
            "web_booking_id": str(booking.get("id", "")),
            "actor": actor,
            "service_date": svc_day,
        }
    )


def get_web_booking_technician_map():
    ensure_mysql_ready()
    _ensure_schema_updates()
    rows = fetch_all(
        """
        SELECT web_booking_id, customer_phone, assigned_to, created_at
        FROM service_orders
        WHERE source='web'
        ORDER BY created_at DESC, id DESC
        """
    )
    by_booking_id = {}
    by_phone = {}
    for row in rows:
        assigned_to = str(row.get("assigned_to", "")).strip()
        if not assigned_to:
            continue
        booking_id = str(row.get("web_booking_id", "")).strip()
        phone = str(row.get("customer_phone", "")).strip()
        if booking_id and booking_id not in by_booking_id:
            by_booking_id[booking_id] = assigned_to
        if phone and phone not in by_phone:
            by_phone[phone] = assigned_to
    return {"by_booking_id": by_booking_id, "by_phone": by_phone}


def _digits_only(s):
    return re.sub(r"\D", "", str(s or ""))


def _phones_match(input_digits: str, db_phone: str) -> bool:
    """So khớp SĐT (hỗ trợ 0xxxx / 84xxxx)."""
    a = _digits_only(input_digits)
    b = _digits_only(db_phone)
    if not a or not b:
        return False
    if a == b:
        return True

    def vn_norm(d):
        if len(d) >= 11 and d.startswith("84"):
            return "0" + d[2:]
        return d

    a, b = vn_norm(a), vn_norm(b)
    if a == b:
        return True
    return len(a) >= 9 and len(b) >= 9 and a[-9:] == b[-9:]


def _name_hint_matches(hint: str, full_name: str) -> bool:
    hint_t = _normalize_text(hint)
    full_t = _normalize_text(full_name)
    if len(hint.strip()) < 2:
        return True
    if not full_t:
        return True
    return hint_t in full_t or full_t in hint_t


def find_latest_billable_order_for_pos(phone: str, customer_name_hint: str = ""):
    """
    Lệnh tiếp nhận gần nhất của khách còn thanh toán được ở POS
    (trạng thái chưa PAID / AFTERCARE / CANCELLED).
    """
    ensure_mysql_ready()
    _ensure_schema_updates()
    digits = _digits_only(phone)
    if len(digits) < 8:
        return None
    rows = fetch_all(
        """
        SELECT order_no, customer_name, customer_phone, status
        FROM service_orders
        WHERE status NOT IN ('PAID', 'AFTERCARE', 'CANCELLED')
        ORDER BY created_at DESC, id DESC
        LIMIT 400
        """
    )
    hint = str(customer_name_hint or "").strip()
    for row in rows:
        if not _phones_match(digits, row.get("customer_phone") or ""):
            continue
        if not _name_hint_matches(hint, row.get("customer_name") or ""):
            continue
        oid = row.get("order_no")
        if oid:
            return get_order(oid)
    return None


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
    if to_status == "DONE":
        try:
            _notify_customer_service_done(order_id, actor=actor)
        except Exception:
            # Notification failures must not block status transition.
            pass
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


def _resolve_catalog_id_for_service_line(service_line: str):
    """Khớp dòng dịch vụ trên lệnh với service_catalog (ưu tiên trùng khớp tên dài hơn)."""
    ensure_service_catalog()
    name = str(service_line or "").strip()
    if not name:
        return None
    row = fetch_one(
        "SELECT id FROM service_catalog WHERE TRIM(service_name)=%s AND is_active=1 LIMIT 1",
        (name,),
    )
    if row:
        return int(row["id"])
    rows = fetch_all(
        """
        SELECT id, service_name FROM service_catalog
        WHERE is_active=1
        ORDER BY CHAR_LENGTH(service_name) DESC
        """
    )
    snorm = _normalize_text(name)
    if not snorm:
        return None
    for r in rows or []:
        cn = _normalize_text(str(r.get("service_name") or ""))
        if cn and cn == snorm:
            return int(r["id"])
    for r in rows or []:
        cn = _normalize_text(str(r.get("service_name") or ""))
        if cn and cn in snorm:
            return int(r["id"])
    return None


def _pick_product_by_keyword(keyword: str, products: list[dict]):
    k = _normalize_text(keyword)
    if not k:
        return None
    # exact match first
    for p in products:
        p_name = _normalize_text(p.get("name", ""))
        p_code = _normalize_text(p.get("product_code", ""))
        if k == p_name or k == p_code:
            return p
    # then contains
    for p in products:
        p_name = _normalize_text(p.get("name", ""))
        p_code = _normalize_text(p.get("product_code", ""))
        if (p_name and (k in p_name or p_name in k)) or (p_code and (k in p_code or p_code in k)):
            return p
    return None


def suggest_materials_for_services(services: list[str]) -> list[tuple[str, int]]:
    """
    Từ danh sách dịch vụ -> vật tư theo BOM trong MySQL (service_material_bom).
    Fallback: DEFAULT_SERVICE_MATERIAL_RULES nếu không khớp catalog.
    Trả về list (tên sản phẩm trong kho, tổng SL).
    """
    ensure_service_catalog()
    seed_service_material_bom_defaults()
    products = load_products() or []
    if not products:
        return []

    totals: dict[str, int] = {}
    for svc in services or []:
        cid = _resolve_catalog_id_for_service_line(svc)
        if cid:
            for row in fetch_bom_lines_for_catalog_id(cid):
                pname = str(row.get("product_name") or "").strip()
                q = max(1, int(row.get("qty") or 1))
                if pname:
                    totals[pname] = totals.get(pname, 0) + q
            continue

        svc_norm = _normalize_text(svc)
        if not svc_norm:
            continue
        for key, mats in DEFAULT_SERVICE_MATERIAL_RULES.items():
            if _normalize_text(key) not in svc_norm:
                continue
            for keyword, qty in mats:
                prod = _pick_product_by_keyword(keyword, products)
                if not prod:
                    continue
                pn = str(prod.get("name", "")).strip()
                if not pn:
                    continue
                totals[pn] = totals.get(pn, 0) + max(1, int(qty or 1))
    return [(k, v) for k, v in totals.items() if k and v > 0]


def expand_pos_cart_to_invoice_lines(cart_items: dict):
    """
    Chuẩn bị dòng hóa đơn POS: dịch vụ có BOM trong DB (hoặc quy tắc mặc định)
    được tách thành nhiều dòng vật tư (đơn giá = giá kho). Không có định mức
    thì giữ một dòng theo giá gói trong giỏ.
    Trả về (lines, subtotal) với subtotal = tổng line_total.
    """
    if not cart_items:
        return [], 0
    ensure_mysql_ready()
    ensure_service_catalog()
    seed_service_material_bom_defaults()
    products = load_products() or []

    lines = []
    subtotal = 0

    for name, row in cart_items.items():
        itype = str(row.get("type") or "")
        is_service = "dịch vụ" in itype.lower()
        price = int(row.get("price") or 0)
        qty = max(1, int(row.get("qty") or 1))

        if not is_service:
            lt = price * qty
            lines.append(
                {
                    "name": str(name).strip(),
                    "unit_price": price,
                    "qty": qty,
                    "line_total": lt,
                    "item_type": itype or "Sản phẩm",
                }
            )
            subtotal += lt
            continue

        cid = _resolve_catalog_id_for_service_line(str(name))
        bom_rows = []
        if cid:
            bom_rows = (
                fetch_all(
                    """
                    SELECT smb.qty AS bom_qty, p.name AS product_name, p.price
                    FROM service_material_bom smb
                    INNER JOIN products p ON p.id = smb.product_id
                    WHERE smb.service_catalog_id = %s
                    ORDER BY p.name ASC
                    """,
                    (int(cid),),
                )
                or []
            )

        mat_specs = []
        if bom_rows:
            for br in bom_rows:
                pname = str(br.get("product_name") or "").strip()
                if not pname:
                    continue
                bq = max(1, int(br.get("bom_qty") or 1))
                unit = int(float(br.get("price") or 0))
                mat_specs.append((pname, bq, unit))
        # POS billing only expands services when BOM is explicitly configured.
        # If BOM is not found, keep the packaged service price from cart.

        if mat_specs:
            for pname, bq, unit in mat_specs:
                line_qty = bq * qty
                lt = unit * line_qty
                lines.append(
                    {
                        "name": f"{pname} (định mức — {name})",
                        "unit_price": unit,
                        "qty": line_qty,
                        "line_total": lt,
                        "item_type": "Vật tư",
                    }
                )
                subtotal += lt
        else:
            lt = price * qty
            lines.append(
                {
                    "name": str(name).strip(),
                    "unit_price": price,
                    "qty": qty,
                    "line_total": lt,
                    "item_type": itype or "Dịch vụ",
                }
            )
            subtotal += lt

    return lines, subtotal


def add_material_requests_auto(order_id, actor="system"):
    """
    Tự động tạo yêu cầu vật tư từ dịch vụ trong lệnh.
    """
    ensure_mysql_ready()
    exists = fetch_one("SELECT order_no FROM service_orders WHERE order_no=%s", (order_id,))
    if not exists:
        raise ValueError("Không tìm thấy lệnh dịch vụ")
    service_rows = fetch_all(
        "SELECT service_name FROM service_order_services WHERE order_no=%s ORDER BY id ASC",
        (order_id,),
    )
    services = [str(x.get("service_name", "")).strip() for x in service_rows if str(x.get("service_name", "")).strip()]
    if not services:
        raise ValueError("Lệnh chưa có dịch vụ để gợi ý vật tư")
    suggestions = suggest_materials_for_services(services)
    if not suggestions:
        raise ValueError("Chưa có quy tắc vật tư cho các dịch vụ đã chọn")

    # Replace old pending requests to avoid stale/invalid item names from previous logic.
    execute(
        """
        DELETE FROM service_order_material_requests
        WHERE order_no=%s AND exported=0
        """,
        (order_id,),
    )

    created = []
    for item_name, qty in suggestions:
        add_material_request(order_id, item_name, qty, actor=actor)
        created.append({"item_name": item_name, "qty": qty})
    return created


def mark_materials_exported(order_id, actor="system"):
    ensure_mysql_ready()
    exists = fetch_one("SELECT status FROM service_orders WHERE order_no=%s", (order_id,))
    if not exists:
        raise ValueError("Không tìm thấy lệnh dịch vụ")

    pending_rows = fetch_all(
        """
        SELECT id, item_name, qty
        FROM service_order_material_requests
        WHERE order_no=%s AND exported=0
        ORDER BY id ASC
        """,
        (order_id,),
    )
    if not pending_rows:
        return False

    products = load_products() or []
    if not products:
        raise ValueError("Kho vật tư chưa có dữ liệu sản phẩm để xuất kho.")

    def _pick_product(req_name: str):
        req = _normalize_text(req_name)
        if not req:
            return None
        # 1) exact by normalized product name / code
        for p in products:
            p_name = _normalize_text(p.get("name", ""))
            p_code = _normalize_text(p.get("product_code", ""))
            if req == p_name or req == p_code:
                return p
        # 2) contains match
        for p in products:
            p_name = _normalize_text(p.get("name", ""))
            p_code = _normalize_text(p.get("product_code", ""))
            if (req and p_name and (req in p_name or p_name in req)) or (req and p_code and (req in p_code or p_code in req)):
                return p
        return None

    required_by_pid = {}
    product_by_pid = {}
    not_found = []
    for row in pending_rows:
        req_name = str(row.get("item_name", "")).strip()
        req_qty = max(1, int(row.get("qty") or 1))
        prod = _pick_product(req_name)
        if not prod:
            not_found.append(f"- {req_name} (SL yêu cầu: {req_qty}): không map được sang sản phẩm trong kho")
            continue
        pid = int(prod.get("id") or 0)
        if pid <= 0:
            not_found.append(f"- {req_name} (SL yêu cầu: {req_qty}): sản phẩm không hợp lệ")
            continue
        required_by_pid[pid] = required_by_pid.get(pid, 0) + req_qty
        product_by_pid[pid] = prod

    shortage = []
    for pid, req_qty in required_by_pid.items():
        prod = product_by_pid[pid]
        current = int(prod.get("current_stock") or 0)
        if current < req_qty:
            shortage.append(
                f"- {prod.get('name', '')}: cần {req_qty}, tồn {current}"
            )

    problems = []
    if not_found:
        problems.extend(not_found)
    if shortage:
        problems.extend(shortage)
    if problems:
        detail = "\n".join(problems[:20])
        raise ValueError(
            "Không thể xác nhận xuất kho vì thiếu/không khớp vật tư:\n"
            f"{detail}\n"
            "Vui lòng cập nhật đúng tên vật tư yêu cầu hoặc nhập thêm tồn kho."
        )

    # All checks passed -> commit inventory OUT then mark exported.
    for pid, req_qty in required_by_pid.items():
        prod = product_by_pid[pid]
        current = int(prod.get("current_stock") or 0)
        new_stock = max(0, current - req_qty)
        update_product_stock(pid, new_stock)
        insert_inventory_transaction(
            pid,
            "OUT",
            req_qty,
            reason=f"Xuất kho cho lệnh dịch vụ {order_id}",
            reference_no=order_id,
        )

    execute(
        """
        UPDATE service_order_material_requests
        SET exported=1, exported_at=NOW()
        WHERE order_no=%s AND exported=0
        """,
        (order_id,),
    )
    append_order_history(
        {"order_id": order_id},
        exists.get("status", ""),
        exists.get("status", ""),
        actor,
        "Đã xác nhận xuất kho vật tư và trừ tồn kho",
    )
    return True


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


def update_order_services(order_id, services, actor="system", reason=""):
    ensure_mysql_ready()
    row = fetch_one("SELECT status FROM service_orders WHERE order_no=%s", (order_id,))
    if not row:
        raise ValueError("Không tìm thấy lệnh dịch vụ")

    status = str(row.get("status", "")).strip()
    if status in {"PAID", "AFTERCARE", "CANCELLED"}:
        raise ValueError("Không thể chỉnh sửa dịch vụ ở trạng thái hiện tại")

    cleaned = [str(x or "").strip() for x in (services or []) if str(x or "").strip()]
    if not cleaned:
        raise ValueError("Cần ít nhất 1 dịch vụ")
    cleaned = _resolve_service_names(cleaned)
    cleaned = [x for x in cleaned if str(x or "").strip()]
    if not cleaned:
        raise ValueError("Không nhận diện được dịch vụ hợp lệ")

    old = fetch_all(
        "SELECT service_name FROM service_order_services WHERE order_no=%s ORDER BY id ASC",
        (order_id,),
    )
    old_names = [str(x.get("service_name", "")).strip() for x in old]

    execute("DELETE FROM service_order_services WHERE order_no=%s", (order_id,))
    for service_name in cleaned:
        unit_price = int(get_service_price(service_name, default=0))
        if unit_price <= 0:
            # Fallback to price map in case name was normalized from formula/typing.
            price_map = get_service_price_map(active_only=True) or {}
            unit_price = int(price_map.get(service_name, 0) or 0)
        execute(
            "INSERT INTO service_order_services(order_no, service_name, qty, unit_price) VALUES (%s, %s, 1, %s)",
            (order_id, service_name, unit_price),
        )

    before_txt = ", ".join(old_names) if old_names else "(trống)"
    after_txt = ", ".join(cleaned)
    note = (
        f"Chỉnh sửa dịch vụ: {before_txt} -> {after_txt}. "
        f"Lý do: {str(reason or 'Không ghi chú').strip()}"
    )
    append_order_history({"order_id": order_id}, status, status, actor, note)
    return get_order(order_id)
