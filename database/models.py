import re
from datetime import date

from database.connection import execute, execute_many, fetch_all, fetch_one, ensure_mysql_ready


DEFAULT_SERVICE_CATALOG = [
    ("DV-RUA-THUONG", "Rửa xe thường", 120000),
    ("DV-RUA-HUT-BUI", "Rửa xe + hút bụi", 180000),
    ("DV-DANH-BONG", "Đánh bóng", 450000),
    ("DV-CERAMIC-NHANH", "Phủ ceramic nhanh", 1200000),
    ("DV-CERAMIC-CAO-CAP", "Phủ ceramic cao cấp", 2500000),
    ("DV-VE-SINH-NOI-THAT", "Vệ sinh nội thất", 350000),
    ("DV-VE-SINH-KHOANG-MAY", "Vệ sinh khoang máy", 300000),
    ("DV-BAO-DUONG-TONG-QUAT", "Bảo dưỡng tổng quát", 900000),
    ("DV-THAY-DAU-MAY", "Thay dầu máy", 550000),
    ("DV-SUA-CHUA-DIEN", "Sửa chữa điện", 700000),
    ("DV-RUA-XE", "Rửa xe", 120000),
    ("DV-PHU-CERAMIC", "Phủ ceramic", 1500000),
]


def load_users():
    rows = fetch_all(
        "SELECT username, password_plain AS password, role FROM users WHERE is_active = 1 ORDER BY id ASC"
    )
    return [dict(r) for r in rows]


def _slug_code(prefix: str, name: str):
    text = re.sub(r"[^a-zA-Z0-9]+", "-", str(name or "").strip()).strip("-").upper()
    if not text:
        text = "ITEM"
    return f"{prefix}-{text}"[:30]


def ensure_service_catalog():
    execute(
        """
        CREATE TABLE IF NOT EXISTS service_catalog (
            id BIGINT AUTO_INCREMENT PRIMARY KEY,
            service_code VARCHAR(30) NOT NULL UNIQUE,
            service_name VARCHAR(120) NOT NULL UNIQUE,
            price DECIMAL(14,2) NOT NULL DEFAULT 0.00,
            is_active TINYINT(1) NOT NULL DEFAULT 1,
            created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
        ) ENGINE=InnoDB
        """
    )
    for code, name, price in DEFAULT_SERVICE_CATALOG:
        execute(
            """
            INSERT INTO service_catalog(service_code, service_name, price, is_active)
            VALUES (%s, %s, %s, 1)
            ON DUPLICATE KEY UPDATE service_name=VALUES(service_name)
            """,
            (code, name, float(price or 0)),
        )


def load_service_catalog(active_only=True):
    ensure_service_catalog()
    query = """
        SELECT service_code, service_name, price, is_active
        FROM service_catalog
    """
    params = ()
    if active_only:
        query += " WHERE is_active=1"
    query += " ORDER BY service_name ASC"
    rows = fetch_all(query, params)
    return [dict(r) for r in rows]


def get_service_price_map(active_only=True):
    rows = load_service_catalog(active_only=active_only)
    return {str(r.get("service_name", "")).strip(): int(float(r.get("price") or 0)) for r in rows}


def get_service_price(service_name, default=0):
    name = str(service_name or "").strip()
    if not name:
        return int(default or 0)
    ensure_service_catalog()
    row = fetch_one(
        """
        SELECT price
        FROM service_catalog
        WHERE service_name=%s AND is_active=1
        LIMIT 1
        """,
        (name,),
    )
    if row:
        return int(float(row.get("price") or 0))

    # Auto-seed unknown service names to keep one-source model in MySQL.
    code = _slug_code("DV", name)
    execute(
        """
        INSERT INTO service_catalog(service_code, service_name, price, is_active)
        VALUES (%s, %s, %s, 1)
        ON DUPLICATE KEY UPDATE
          service_name=VALUES(service_name),
          price=VALUES(price),
          is_active=VALUES(is_active)
        """,
        (code, name, float(default or 0)),
    )
    return int(default or 0)


def load_unified_catalog_items():
    ensure_service_catalog()
    items = []
    for row in load_service_catalog(active_only=True):
        items.append(
            {
                "name": str(row.get("service_name", "")).strip(),
                "price": int(float(row.get("price") or 0)),
                "type": "Dịch vụ",
            }
        )
    for row in load_products():
        items.append(
            {
                "name": str(row.get("name", "")).strip(),
                "price": int(float(row.get("price") or 0)),
                "type": "Sản phẩm",
            }
        )
    return items


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


# --- HR / Kỹ thuật viên (Tiếp nhận xe, phân công tự động web) ---

def ensure_hr_employees():
    """Tạo bảng nhân sự nếu DB cũ chưa có (không phụ thuộc chạy lại mysql_schema_seed.sql)."""
    execute(
        """
        CREATE TABLE IF NOT EXISTS hr_employees (
          id BIGINT AUTO_INCREMENT PRIMARY KEY,
          full_name VARCHAR(120) NOT NULL,
          phone VARCHAR(20) NOT NULL,
          role VARCHAR(30) NOT NULL,
          join_date VARCHAR(20) NOT NULL DEFAULT '',
          status VARCHAR(30) NOT NULL DEFAULT 'Đang làm',
          created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
          UNIQUE KEY uk_hr_phone (phone),
          INDEX idx_hr_role_status (role, status)
        ) ENGINE=InnoDB
        """
    )


def seed_hr_employees_if_empty():
    """Chèn dữ liệu mẫu một lần khi bảng trống."""
    ensure_hr_employees()
    row = fetch_one("SELECT COUNT(*) AS c FROM hr_employees")
    if row and int(row.get("c") or 0) > 0:
        return
    defaults = [
        ("Nguyen Minh Dat", "0902111222", "Kỹ thuật", "10/01/2025", "Đang làm"),
        ("Tran Bao Ngoc", "0913555444", "Lễ tân", "18/03/2025", "Đang làm"),
        ("Le Quoc Khanh", "0938222111", "Kỹ thuật", "25/11/2024", "Đang làm"),
        ("Pham Anh Thu", "0977666111", "Quản lý", "15/07/2023", "Đang làm"),
        ("Pham Van Phuc", "0966333444", "Kỹ thuật", "01/02/2025", "Đang làm"),
    ]
    for full_name, phone, role, join_date, status in defaults:
        try:
            execute(
                """
                INSERT INTO hr_employees (full_name, phone, role, join_date, status)
                VALUES (%s, %s, %s, %s, %s)
                """,
                (full_name, phone, role, join_date, status),
            )
        except Exception:
            pass


def load_active_technician_names():
    """Danh sách KTV đang làm việc — dùng cho combobox Tiếp nhận và cân bằng tải."""
    ensure_hr_employees()
    seed_hr_employees_if_empty()
    rows = fetch_all(
        """
        SELECT full_name
        FROM hr_employees
        WHERE role=%s AND status=%s
        ORDER BY full_name ASC
        """,
        ("Kỹ thuật", "Đang làm"),
    )
    out = []
    for r in rows or []:
        name = str(r.get("full_name", "")).strip()
        if name:
            out.append(name)
    return out


def load_hr_employees():
    ensure_hr_employees()
    seed_hr_employees_if_empty()
    rows = fetch_all(
        """
        SELECT id, full_name, phone, role, join_date, status
        FROM hr_employees
        ORDER BY id ASC
        """
    )
    return [dict(r) for r in rows or []]


def insert_hr_employee(full_name, phone, role, join_date, status):
    ensure_hr_employees()
    return execute(
        """
        INSERT INTO hr_employees (full_name, phone, role, join_date, status)
        VALUES (%s, %s, %s, %s, %s)
        """,
        (str(full_name or "").strip(), str(phone or "").strip(), str(role or "").strip(), str(join_date or "").strip(), str(status or "").strip()),
    )


def update_hr_employee(emp_id, full_name, phone, role, join_date, status):
    ensure_hr_employees()
    execute(
        """
        UPDATE hr_employees
        SET full_name=%s, phone=%s, role=%s, join_date=%s, status=%s
        WHERE id=%s
        """,
        (
            str(full_name or "").strip(),
            str(phone or "").strip(),
            str(role or "").strip(),
            str(join_date or "").strip(),
            str(status or "").strip(),
            int(emp_id),
        ),
    )


def update_hr_employee_status(emp_id, status):
    ensure_hr_employees()
    execute(
        "UPDATE hr_employees SET status=%s WHERE id=%s",
        (str(status or "").strip(), int(emp_id)),
    )


def _normalize_period_month(period_month):
    if period_month is None:
        return None
    if hasattr(period_month, "replace") and hasattr(period_month, "year"):
        return period_month.replace(day=1)
    text = str(period_month or "").strip()
    if not text:
        return None
    if len(text) == 7:
        text = f"{text}-01"
    if len(text) >= 10:
        text = text[:10]
    try:
        year_s, month_s, _day_s = text.split("-", 2)
        return date(int(year_s), int(month_s), 1)
    except Exception:
        return None


def ensure_hr_monthly_salary():
    ensure_hr_employees()
    execute(
        """
        CREATE TABLE IF NOT EXISTS hr_monthly_salary (
          id BIGINT AUTO_INCREMENT PRIMARY KEY,
          employee_id BIGINT NOT NULL,
          period_month DATE NOT NULL,
          provisional_salary DECIMAL(14,2) NOT NULL DEFAULT 0.00,
          updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
          UNIQUE KEY uk_hr_salary_emp_month (employee_id, period_month),
          INDEX idx_hr_salary_period (period_month),
          CONSTRAINT fk_hr_salary_employee FOREIGN KEY (employee_id) REFERENCES hr_employees (id) ON DELETE CASCADE
        ) ENGINE=InnoDB
        """
    )


def load_hr_monthly_salary_map(period_month):
    """Trả về dict[employee_id] = lương tháng tạm tính đã lưu cho kỳ tháng."""
    ensure_hr_monthly_salary()
    month = _normalize_period_month(period_month)
    if not month:
        return {}
    rows = fetch_all(
        """
        SELECT employee_id, provisional_salary
        FROM hr_monthly_salary
        WHERE period_month=%s
        """,
        (month,),
    )
    out = {}
    for row in rows or []:
        emp_id = int(row.get("employee_id") or 0)
        if emp_id <= 0:
            continue
        out[emp_id] = int(float(row.get("provisional_salary") or 0))
    return out


def upsert_hr_monthly_salary(employee_id, period_month, provisional_salary):
    ensure_hr_monthly_salary()
    month = _normalize_period_month(period_month)
    if not month:
        raise ValueError("Kỳ lương tháng không hợp lệ")
    emp_id = int(employee_id)
    if emp_id <= 0:
        raise ValueError("Nhân viên không hợp lệ")
    execute(
        """
        INSERT INTO hr_monthly_salary (employee_id, period_month, provisional_salary)
        VALUES (%s, %s, %s)
        ON DUPLICATE KEY UPDATE
          provisional_salary = VALUES(provisional_salary),
          updated_at = CURRENT_TIMESTAMP
        """,
        (emp_id, month, float(provisional_salary or 0)),
    )


def _normalize_shift_date_key(cell):
    if cell is None:
        return ""
    if hasattr(cell, "strftime") and not isinstance(cell, str):
        return cell.strftime("%Y-%m-%d")
    s = str(cell).strip()
    return s[:10] if len(s) >= 10 else s


def ensure_hr_shift_cells():
    ensure_hr_employees()
    execute(
        """
        CREATE TABLE IF NOT EXISTS hr_shift_cells (
          id BIGINT AUTO_INCREMENT PRIMARY KEY,
          employee_id BIGINT NOT NULL,
          shift_date DATE NOT NULL,
          shift_value VARCHAR(40) NOT NULL DEFAULT '-',
          updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
          UNIQUE KEY uk_hr_shift_emp_day (employee_id, shift_date),
          INDEX idx_hr_shift_date (shift_date),
          CONSTRAINT fk_hr_shift_employee FOREIGN KEY (employee_id) REFERENCES hr_employees (id) ON DELETE CASCADE
        ) ENGINE=InnoDB
        """
    )


def load_shift_map_for_all():
    """Trả về dict[employee_id][YYYY-MM-DD] = shift_value."""
    ensure_hr_shift_cells()
    rows = fetch_all(
        """
        SELECT employee_id, shift_date, shift_value
        FROM hr_shift_cells
        """
    )
    out = {}
    for r in rows or []:
        eid = int(r.get("employee_id") or 0)
        if not eid:
            continue
        day = _normalize_shift_date_key(r.get("shift_date"))
        if not day:
            continue
        val = str(r.get("shift_value") or "-").strip() or "-"
        out.setdefault(eid, {})[day] = val
    return out


def upsert_shift_cells_batch(rows):
    """rows: list of (employee_id, shift_date, shift_value) — shift_date: date hoặc 'YYYY-MM-DD'."""
    if not rows:
        return
    ensure_hr_shift_cells()
    payload = []
    for eid, d, val in rows:
        v = str(val or "").strip() or "-"
        payload.append((int(eid), d, v))
    execute_many(
        """
        INSERT INTO hr_shift_cells (employee_id, shift_date, shift_value)
        VALUES (%s, %s, %s)
        ON DUPLICATE KEY UPDATE
          shift_value = VALUES(shift_value),
          updated_at = CURRENT_TIMESTAMP
        """,
        payload,
    )


def get_technician_commission_base(employee_full_name, period_start, period_end):
    """
    Số dòng dịch vụ và doanh thu (VND) gán cho KTV theo tên trong assigned_to (service_orders),
    chỉ tính lệnh đã thanh toán (PAID / AFTERCARE), trong khoảng ngày COALESCE(service_date, DATE(created_at)).
    """
    name = str(employee_full_name or "").strip()
    if not name:
        return 0, 0
    row = fetch_one(
        """
        SELECT
          COUNT(sos.id) AS n_jobs,
          COALESCE(SUM(sos.qty * sos.unit_price), 0) AS revenue
        FROM service_orders so
        INNER JOIN service_order_services sos ON sos.order_no = so.order_no
        WHERE TRIM(so.assigned_to) = %s
          AND so.status IN ('PAID', 'AFTERCARE')
          AND DATE(COALESCE(so.service_date, so.created_at)) >= %s
          AND DATE(COALESCE(so.service_date, so.created_at)) <= %s
        """,
        (name, period_start, period_end),
    )
    if not row:
        return 0, 0
    jobs = int(row.get("n_jobs") or 0)
    revenue = int(float(row.get("revenue") or 0))
    return jobs, revenue


# --- Định mức vật tư / BOM (dịch vụ ↔ sản phẩm kho) ---

SERVICE_MATERIAL_BOM_SEED = [
    ("DV-RUA-XE", "VT002", 1, "Nuoc rua kinh Meguiar"),
    ("DV-RUA-XE", "VT005", 1, "Bot rua xe Sonax"),
    ("DV-RUA-XE", "VT010", 1, "Choi lau kinh"),
    ("DV-RUA-THUONG", "VT002", 1, ""),
    ("DV-RUA-THUONG", "VT005", 1, ""),
    ("DV-RUA-THUONG", "VT010", 1, ""),
    ("DV-RUA-HUT-BUI", "VT002", 1, ""),
    ("DV-RUA-HUT-BUI", "VT005", 1, ""),
    ("DV-RUA-HUT-BUI", "VT011", 2, "Khan microfiber hut bui"),
    ("DV-DANH-BONG", "VT012", 2, ""),
    ("DV-DANH-BONG", "VT006", 1, ""),
    ("DV-CERAMIC-NHANH", "VT013", 1, ""),
    ("DV-CERAMIC-NHANH", "VT002", 1, ""),
    ("DV-CERAMIC-CAO-CAP", "VT013", 2, ""),
    ("DV-CERAMIC-CAO-CAP", "VT012", 1, ""),
    ("DV-VE-SINH-NOI-THAT", "VT006", 1, ""),
    ("DV-VE-SINH-NOI-THAT", "VT011", 2, ""),
    ("DV-VE-SINH-KHOANG-MAY", "VT014", 1, ""),
    ("DV-VE-SINH-KHOANG-MAY", "VT009", 1, ""),
    ("DV-BAO-DUONG-TONG-QUAT", "VT001", 4, ""),
    ("DV-BAO-DUONG-TONG-QUAT", "VT003", 1, ""),
    ("DV-BAO-DUONG-TONG-QUAT", "VT009", 2, ""),
    ("DV-THAY-DAU-MAY", "VT001", 5, ""),
    ("DV-THAY-DAU-MAY", "VT003", 1, ""),
    ("DV-SUA-CHUA-DIEN", "VT008", 1, ""),
    ("DV-SUA-CHUA-DIEN", "VT010", 2, ""),
    ("DV-PHU-CERAMIC", "VT013", 1, ""),
    ("DV-PHU-CERAMIC", "VT002", 1, ""),
]

_SERVICE_MATERIAL_BOM_UPSERTED = False


def ensure_service_material_bom():
    ensure_service_catalog()
    execute(
        """
        CREATE TABLE IF NOT EXISTS service_material_bom (
          id BIGINT AUTO_INCREMENT PRIMARY KEY,
          service_catalog_id BIGINT NOT NULL,
          product_id BIGINT NOT NULL,
          qty INT NOT NULL DEFAULT 1,
          note VARCHAR(160) DEFAULT '',
          UNIQUE KEY uk_svc_product (service_catalog_id, product_id),
          CONSTRAINT fk_bom_catalog FOREIGN KEY (service_catalog_id) REFERENCES service_catalog(id) ON DELETE CASCADE,
          CONSTRAINT fk_bom_product FOREIGN KEY (product_id) REFERENCES products(id) ON DELETE CASCADE,
          INDEX idx_bom_service (service_catalog_id),
          INDEX idx_bom_product (product_id)
        ) ENGINE=InnoDB
        """
    )


def seed_service_material_bom_defaults():
    """Đồng bộ định mức từ SERVICE_MATERIAL_BOM_SEED (idempotent)."""
    global _SERVICE_MATERIAL_BOM_UPSERTED
    ensure_service_material_bom()
    if _SERVICE_MATERIAL_BOM_UPSERTED:
        return
    for svc_code, prod_code, qty, note in SERVICE_MATERIAL_BOM_SEED:
        sc = fetch_one("SELECT id FROM service_catalog WHERE service_code=%s LIMIT 1", (svc_code,))
        pr = fetch_one("SELECT id FROM products WHERE product_code=%s LIMIT 1", (prod_code,))
        if not sc or not pr:
            continue
        execute(
            """
            INSERT INTO service_material_bom (service_catalog_id, product_id, qty, note)
            VALUES (%s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE
              qty = VALUES(qty),
              note = VALUES(note)
            """,
            (
                int(sc["id"]),
                int(pr["id"]),
                max(1, int(qty)),
                str(note or ""),
            ),
        )
    _SERVICE_MATERIAL_BOM_UPSERTED = True


def fetch_bom_lines_for_catalog_id(catalog_id: int):
    seed_service_material_bom_defaults()
    return fetch_all(
        """
        SELECT smb.qty, p.id AS product_id, p.name AS product_name
        FROM service_material_bom smb
        INNER JOIN products p ON p.id = smb.product_id
        WHERE smb.service_catalog_id = %s
        ORDER BY p.name ASC
        """,
        (int(catalog_id),),
    )


def list_service_catalog_admin(include_inactive=False):
    """Danh sách đầy đủ cho màn quản lý (có id)."""
    ensure_service_catalog()
    q = "SELECT id, service_code, service_name, price, is_active FROM service_catalog"
    if not include_inactive:
        q += " WHERE is_active=1"
    q += " ORDER BY service_name ASC"
    rows = fetch_all(q)
    return [dict(r) for r in rows] if rows else []


def insert_service_catalog_admin(service_code: str, service_name: str, price: float):
    ensure_service_catalog()
    name = str(service_name or "").strip()
    if not name:
        raise ValueError("Tên dịch vụ không được để trống")
    dup = fetch_one(
        "SELECT id FROM service_catalog WHERE TRIM(service_name)=%s LIMIT 1",
        (name,),
    )
    if dup:
        raise ValueError("Tên dịch vụ đã tồn tại")
    code = str(service_code or "").strip().upper()
    if not code:
        code = _slug_code("DV", name).upper()
    code = code[:30]
    base = code
    n = 0
    while fetch_one("SELECT id FROM service_catalog WHERE service_code=%s LIMIT 1", (code,)):
        n += 1
        suffix = f"-{n}"
        code = (base[: max(1, 30 - len(suffix))] + suffix)[:30]
    new_id = execute(
        """
        INSERT INTO service_catalog (service_code, service_name, price, is_active)
        VALUES (%s, %s, %s, 1)
        """,
        (code, name, float(price or 0)),
    )
    return int(new_id) if new_id else None


def update_service_catalog_admin(row_id: int, service_code: str, service_name: str, price: float, is_active: bool):
    row_id = int(row_id)
    row = fetch_one("SELECT id FROM service_catalog WHERE id=%s", (row_id,))
    if not row:
        raise ValueError("Không tìm thấy dịch vụ")
    name = str(service_name or "").strip()
    if not name:
        raise ValueError("Tên dịch vụ không được để trống")
    dup = fetch_one(
        "SELECT id FROM service_catalog WHERE TRIM(service_name)=%s AND id<>%s LIMIT 1",
        (name, row_id),
    )
    if dup:
        raise ValueError("Tên dịch vụ đã được dùng cho dịch vụ khác")
    code = str(service_code or "").strip().upper()[:30]
    if not code:
        prev = fetch_one("SELECT service_code FROM service_catalog WHERE id=%s", (row_id,))
        code = str(prev.get("service_code") or "").strip().upper()[:30]
    execute(
        """
        UPDATE service_catalog
        SET service_code=%s, service_name=%s, price=%s, is_active=%s
        WHERE id=%s
        """,
        (code, name, float(price or 0), 1 if is_active else 0, row_id),
    )


def fetch_bom_lines_admin(catalog_id: int):
    ensure_service_material_bom()
    seed_service_material_bom_defaults()
    rows = fetch_all(
        """
        SELECT smb.id AS bom_id, smb.qty, smb.note,
               p.id AS product_id, p.product_code, p.name AS product_name
        FROM service_material_bom smb
        INNER JOIN products p ON p.id = smb.product_id
        WHERE smb.service_catalog_id = %s
        ORDER BY p.name ASC
        """,
        (int(catalog_id),),
    )
    return [dict(r) for r in rows] if rows else []


def upsert_service_bom_line(service_catalog_id: int, product_id: int, qty: int, note: str = ""):
    ensure_service_material_bom()
    seed_service_material_bom_defaults()
    execute(
        """
        INSERT INTO service_material_bom (service_catalog_id, product_id, qty, note)
        VALUES (%s, %s, %s, %s)
        ON DUPLICATE KEY UPDATE qty = VALUES(qty), note = VALUES(note)
        """,
        (
            int(service_catalog_id),
            int(product_id),
            max(1, int(qty)),
            str(note or "")[:160],
        ),
    )


def delete_service_bom_line(bom_id: int):
    ensure_service_material_bom()
    execute("DELETE FROM service_material_bom WHERE id=%s", (int(bom_id),))


def fetch_dashboard_snapshot():
    """KPI + chuỗi biểu đồ tổng quan — đọc trực tiếp MySQL."""
    from datetime import date, timedelta

    ensure_mysql_ready()
    today = date.today()
    yesterday = today - timedelta(days=1)
    week_start = today - timedelta(days=today.weekday())

    def revenue_for_day(d):
        row = fetch_one(
            """
            SELECT COALESCE(SUM(total_amount), 0) AS s
            FROM invoices
            WHERE LOWER(TRIM(status)) = 'paid' AND DATE(created_at) = %s
            """,
            (d,),
        )
        return float(row["s"] or 0) if row else 0.0

    rev_today = revenue_for_day(today)
    rev_yesterday = revenue_for_day(yesterday)

    bar_labels = []
    bar_values = []
    start_7 = today - timedelta(days=6)
    for i in range(7):
        d = start_7 + timedelta(days=i)
        bar_labels.append(d.strftime("%d/%m"))
        bar_values.append(revenue_for_day(d))

    row_p = fetch_one(
        """
        SELECT COUNT(*) AS c FROM service_orders
        WHERE status NOT IN ('PAID', 'AFTERCARE', 'CANCELLED')
        """
    )
    pipeline_orders = int(row_p["c"] if row_p else 0)

    row_near = fetch_one(
        """
        SELECT COUNT(*) AS c FROM service_orders
        WHERE status IN ('DONE', 'INVOICED')
        """
    )
    orders_awaiting_payment = int(row_near["c"] if row_near else 0)

    row_wb_t = fetch_one(
        "SELECT COUNT(*) AS c FROM web_bookings WHERE DATE(created_at) = %s",
        (today,),
    )
    web_bookings_today = int(row_wb_t["c"] if row_wb_t else 0)

    row_wb_p = fetch_one(
        """
        SELECT COUNT(*) AS c FROM web_bookings
        WHERE LOWER(TRIM(status)) = 'pending'
        """
    )
    web_bookings_pending = int(row_wb_p["c"] if row_wb_p else 0)

    row_nc = fetch_one(
        "SELECT COUNT(*) AS c FROM customers WHERE DATE(created_at) = %s",
        (today,),
    )
    new_customers_today = int(row_nc["c"] if row_nc else 0)

    row_nc_w = fetch_one(
        "SELECT COUNT(*) AS c FROM customers WHERE DATE(created_at) >= %s",
        (week_start,),
    )
    new_customers_week = int(row_nc_w["c"] if row_nc_w else 0)

    rows_os = fetch_all(
        """
        SELECT status, COUNT(*) AS c
        FROM service_orders
        WHERE DATE(created_at) = %s
        GROUP BY status
        """,
        (today,),
    )

    stat_new = frozenset({"NEW_WEB", "CHECKED_IN", "QUOTED"})
    stat_run = frozenset({"APPROVED", "IN_SERVICE", "WAITING_PARTS"})
    stat_end = frozenset({"DONE", "INVOICED", "PAID", "AFTERCARE"})
    pie_new = pie_run = pie_end = pie_cancel = pie_other = 0
    for r in rows_os or []:
        st = str(r.get("status") or "").strip().upper()
        c = int(r.get("c") or 0)
        if st in stat_new:
            pie_new += c
        elif st in stat_run:
            pie_run += c
        elif st in stat_end:
            pie_end += c
        elif st == "CANCELLED":
            pie_cancel += c
        else:
            pie_other += c

    pct_change = None
    if rev_yesterday > 0:
        pct_change = (rev_today - rev_yesterday) / rev_yesterday * 100.0

    return {
        "revenue_today": rev_today,
        "revenue_yesterday": rev_yesterday,
        "revenue_change_pct": pct_change,
        "pipeline_orders": pipeline_orders,
        "orders_awaiting_payment": orders_awaiting_payment,
        "web_bookings_today": web_bookings_today,
        "web_bookings_pending": web_bookings_pending,
        "new_customers_today": new_customers_today,
        "new_customers_week": new_customers_week,
        "bar_labels": bar_labels,
        "bar_values": bar_values,
        "pie_counts": (pie_new, pie_run, pie_end, pie_cancel, pie_other),
    }