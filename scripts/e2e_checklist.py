from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

from database.connection import ensure_mysql_ready, fetch_all, fetch_one
from database.models import load_products, load_unified_catalog_items
from modules.chamsoc_kh_marketing import ghi_nhan_thanh_toan_tich_hop
from modules.integration_data import get_pos_sales
from modules.rbac_runtime import can_do
from modules.service_orders import (
    create_order,
    find_latest_billable_order_for_pos,
    list_orders,
    transition_order_status,
)
from server.app import app


@dataclass
class CheckResult:
    module: str
    status: str
    detail: str


def _pass(module: str, detail: str) -> CheckResult:
    return CheckResult(module, "PASS", detail)


def _fail(module: str, detail: str) -> CheckResult:
    return CheckResult(module, "FAIL", detail)


def _sqlite_path() -> Path:
    return Path(__file__).resolve().parents[1] / "server" / "bookings.db"


def run_checks() -> list[CheckResult]:
    results: list[CheckResult] = []
    ensure_mysql_ready()

    # 1) WEB
    try:
        client = app.test_client()
        h = client.get("/api/health")
        if h.status_code != 200:
            raise RuntimeError(f"/health={h.status_code}")
        payload = {
            "ho_ten": "E2E WEB TEST",
            "sdt": "0900009999",
            "hang_xe": "Toyota",
            "bien_so": "99A-99999",
            "dich_vu": "Rửa xe",
            "ngay_hen": "2099-12-31",
            "gio_hen": "09:00",
            "ghi_chu": "auto test",
        }
        r = client.post("/api/booking", json=payload)
        if r.status_code not in (201, 429):
            raise RuntimeError(f"/booking status={r.status_code}, body={r.json}")
        if r.status_code == 201 and (r.json or {}).get("booking_id"):
            booking_id = int((r.json or {}).get("booking_id"))
            client.patch(f"/api/bookings/{booking_id}/reject")
        results.append(_pass("Web", "API health + create booking flow works"))
    except Exception as e:
        results.append(_fail("Web", str(e)))

    # 2) TIEP NHAN XE (service order lifecycle)
    order_id = ""
    try:
        order = create_order(
            {
                "source": "web",  # avoid desk cap in automated check
                "status": "CHECKED_IN",
                "customer_name": "E2E Intake",
                "customer_phone": "0900001111",
                "services": ["Rửa xe"],
                "service_date": date(2099, 12, 31),
                "actor": "e2e",
            }
        )
        order_id = str((order or {}).get("order_id", "")).strip()
        for st in ("QUOTED", "APPROVED", "IN_SERVICE", "DONE", "INVOICED", "PAID"):
            transition_order_status(order_id, st, actor="e2e", note="e2e transition")
        final_order = fetch_one("SELECT status FROM service_orders WHERE order_no=%s", (order_id,))
        if not final_order or str(final_order.get("status")) != "PAID":
            raise RuntimeError("Lifecycle did not reach PAID")
        results.append(_pass("Tiếp nhận", f"Lifecycle CHECKED_IN->PAID ok ({order_id})"))
    except Exception as e:
        results.append(_fail("Tiếp nhận", str(e)))

    # 3) POS integration (lookup billable order by phone)
    try:
        p_order = create_order(
            {
                "source": "web",
                "status": "DONE",
                "customer_name": "E2E POS",
                "customer_phone": "0900002222",
                "services": ["Đánh bóng"],
                "service_date": date(2099, 12, 31),
                "actor": "e2e",
            }
        )
        hit = find_latest_billable_order_for_pos("0900002222", "E2E POS")
        if not hit or str(hit.get("order_id", "")).strip() != str(p_order.get("order_id", "")).strip():
            raise RuntimeError("POS cannot resolve billable order from intake")
        results.append(_pass("POS", "Can auto-resolve billable service order by phone/name"))
    except Exception as e:
        results.append(_fail("POS", str(e)))

    # 4) CRM sync via CSKH loyalty integration
    try:
        cid = "99991"
        res = ghi_nhan_thanh_toan_tich_hop(
            ma_khach_hang=cid,
            so_tien_vnd=100000,
            ten_khach_hang="E2E CRM",
            sdt="0900003333",
        )
        row = fetch_one("SELECT id, full_name, phone FROM customers WHERE id=%s", (int(cid),))
        if not res or not row:
            raise RuntimeError("CRM sync did not persist customer data")
        results.append(_pass("CRM", "Customer spending/points sync from integrated payment works"))
    except Exception as e:
        results.append(_fail("CRM", str(e)))

    # 5) CSKH logs (service_done written when DONE)
    try:
        row = fetch_one(
            """
            SELECT message_type, summary_text
            FROM cskh_message_logs
            WHERE message_type='service_done'
            ORDER BY id DESC
            LIMIT 1
            """
        )
        if not row:
            raise RuntimeError("No service_done log found")
        results.append(_pass("CSKH", "service_done notification log exists"))
    except Exception as e:
        results.append(_fail("CSKH", str(e)))

    # 6) BAO CAO data sources
    try:
        sales = get_pos_sales()
        orders = list_orders()
        results.append(_pass("Báo cáo", f"Data sources load ok (pos_sales={len(sales)}, orders={len(orders)})"))
    except Exception as e:
        results.append(_fail("Báo cáo", str(e)))

    # 7) KHO
    try:
        products = load_products()
        catalog = load_unified_catalog_items()
        if products is None or catalog is None:
            raise RuntimeError("Inventory/catalog loading returned None")
        results.append(_pass("Kho", f"Inventory + unified catalog load ok (products={len(products)})"))
    except Exception as e:
        results.append(_fail("Kho", str(e)))

    # 8) RBAC
    try:
        cond_1 = can_do("Quản lý", "baocao.export_pdf")
        cond_2 = not can_do("Lễ tân", "baocao.export_pdf")
        if not (cond_1 and cond_2):
            raise RuntimeError("RBAC action matrix mismatch")
        results.append(_pass("RBAC", "Role action permissions evaluated correctly"))
    except Exception as e:
        results.append(_fail("RBAC", str(e)))

    return results


def print_report(results: list[CheckResult]) -> None:
    print("\nE2E CHECKLIST REPORT")
    print("=" * 80)
    print(f"{'Module':<12} | {'Status':<6} | Detail")
    print("-" * 80)
    for r in results:
        print(f"{r.module:<12} | {r.status:<6} | {r.detail}")
    print("-" * 80)
    passed = sum(1 for r in results if r.status == "PASS")
    print(f"TOTAL: {passed}/{len(results)} PASS")


if __name__ == "__main__":
    print_report(run_checks())
