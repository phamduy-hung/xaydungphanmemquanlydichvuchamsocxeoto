"""
Module: Quản lý đặt lịch từ Web
- Polling API server mỗi 5 giây
- Hiển thị đơn pending
- Nhân viên duyệt / từ chối
- Chuyển sang CRM khi tiếp nhận
"""
import json
import sys
import threading
from pathlib import Path
from datetime import datetime
from urllib.request import urlopen, Request
from urllib.error import URLError
import time
import re
import unicodedata

from PyQt5.QtCore import Qt, QTimer, pyqtSignal
from PyQt5.QtGui import QColor, QFont
from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QLineEdit, QTableWidget, QTableWidgetItem,
    QHeaderView, QMessageBox, QTabWidget, QFrame,
    QSizePolicy, QAbstractItemView
)
from modules.integration_data import append_web_accept
from modules.service_orders import (
    create_order_from_web_booking,
    get_web_booking_technician_map,
    transition_order_status,
)
from modules.rbac_runtime import can_do
from modules.audit_log import append_audit_log
from database.models import get_service_price_map

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

API_BASE = "http://localhost:8765/api"


def _http_get(url: str):
    """Gửi GET request, trả về dict hoặc list. None nếu lỗi."""
    try:
        # Keep timeout short to avoid freezing the Qt UI thread.
        with urlopen(url, timeout=1) as resp:
            return json.loads(resp.read().decode())
    except Exception:
        return None


def _http_patch(url: str):
    """Gửi PATCH request, trả về dict hoặc None."""
    try:
        req = Request(url, method="PATCH")
        req.add_header("Content-Length", "0")
        with urlopen(req, timeout=3) as resp:
            return json.loads(resp.read().decode())
    except Exception:
        return None


# ──────────────────────────────────────────────
# Widget đặt lịch từ web
# ──────────────────────────────────────────────
class WebBookingsWidget(QWidget):
    # Phát signal khi có đơn mới (desktop app có thể kết nối để hiển thị badge)
    pending_count_changed = pyqtSignal(int)
    # Phát signal khi nhân viên tiếp nhận đơn → truyền data sang CRM
    booking_accepted = pyqtSignal(dict)
    refresh_data_ready = pyqtSignal(object, object)

    def __init__(self, crm_widget=None, current_role="Quản lý", current_user="system", parent=None):
        super().__init__(parent)
        self.setObjectName("webBookingRoot")
        self.crm_widget = crm_widget   # Tham chiếu tới CRM widget nếu có
        self.current_role = current_role
        self.current_user = current_user
        self._pending_data = []        # Cache danh sách pending
        self._pending_view_data = []   # Dữ liệu pending sau khi lọc
        self._all_data = []            # Cache tất cả đơn
        self._service_price_map = {}
        self._service_name_index = {}
        self._service_price_last_sync = 0.0
        self._tech_map_by_booking_id = {}
        self._tech_map_by_phone = {}
        self._api_online = False
        self._polling_enabled = False
        self._refresh_in_progress = False
        self._refresh_queued = False

        self.setWindowTitle("ProCare: Web Bookings")
        self.resize(1100, 700)
        self._build_ui()
        self._apply_dark_style()
        self.refresh_data_ready.connect(self._apply_refresh_results)
        self._start_polling()

    # ──────────────────────────────
    # Build UI
    # ──────────────────────────────
    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(20, 20, 20, 20)
        root.setSpacing(14)

        # ─── Header ───
        header = QHBoxLayout()
        title = QLabel("DANH SÁCH ĐẶT LỊCH TRỰC TUYẾN")
        title.setObjectName("webBookingTitle")
        header.addWidget(title)

        header.addStretch()

        self.lbl_status = QLabel("CONNECTING...")
        header.addWidget(self.lbl_status)

        self.btn_refresh = QPushButton("LÀM MỚI")
        self.btn_refresh.setObjectName("btnWebRefresh")
        self.btn_refresh.setFixedWidth(120)
        self.btn_refresh.clicked.connect(self.request_refresh)
        header.addWidget(self.btn_refresh)

        root.addLayout(header)

        # ─── Separator ───
        sep = QFrame()
        sep.setFrameShape(QFrame.HLine)
        root.addWidget(sep)

        # ─── Stat bar ───
        stat_bar = QHBoxLayout()
        stat_bar.setSpacing(20)
        self.lbl_pending_count = self._stat_card("Chờ tiếp nhận", "0", "#f59e0b")
        self.lbl_accepted_count = self._stat_card("Đã xử lý", "0", "#10b981")
        self.lbl_rejected_count = self._stat_card("Đã hủy", "0", "#ef4444")
        stat_bar.addWidget(self.lbl_pending_count[2])
        stat_bar.addWidget(self.lbl_accepted_count[2])
        stat_bar.addWidget(self.lbl_rejected_count[2])
        stat_bar.addStretch()
        root.addLayout(stat_bar)

        # ─── Tabs ───
        self.tabs = QTabWidget()
        self.tabs.setTabPosition(QTabWidget.North)

        # Tab 1: Pending
        self.tab_pending = QWidget()
        self._build_pending_tab()
        self.tabs.addTab(self.tab_pending, "CHỜ XỬ LÝ")

        # Tab 2: All history
        self.tab_all = QWidget()
        self._build_all_tab()
        self.tabs.addTab(self.tab_all, "TẤT CẢ ĐƠN")

        root.addWidget(self.tabs)

    def _stat_card(self, label: str, value: str, color: str):
        frame = QFrame()
        frame.setObjectName("webStatCard")
        frame.setFixedSize(220, 100)
        lay = QVBoxLayout(frame)
        lay.setContentsMargins(20, 12, 20, 12)
        
        lbl_val = QLabel(value)
        lbl_val.setObjectName("webStatValue")
        
        lbl_lbl = QLabel(label.upper())
        lbl_lbl.setObjectName("webStatLabel")
        
        lay.addWidget(lbl_lbl)
        lay.addWidget(lbl_val)
        return lbl_val, lbl_lbl, frame

    def _build_pending_tab(self):
        lay = QVBoxLayout(self.tab_pending)
        lay.setContentsMargins(0, 10, 0, 0)
        lay.setSpacing(8)

        info = QLabel("Các đơn đặt lịch mới từ website đang chờ nhân viên xử lý. Bấm [TIẾP NHẬN] để chuyển dữ liệu khách hàng vào hệ thống CRM.")
        info.setObjectName("webPendingInfo")
        info.setWordWrap(True)
        lay.addWidget(info)

        search_row = QHBoxLayout()
        self.txt_search_pending = QLineEdit()
        self.txt_search_pending.setObjectName("webSearchInput")
        self.txt_search_pending.setPlaceholderText("Tìm khách hàng / SĐT...")
        self.txt_search_pending.setMinimumHeight(36)
        self.txt_search_pending.textChanged.connect(self._render_pending)
        self.btn_clear_search_pending = QPushButton("XÓA LỌC")
        self.btn_clear_search_pending.setObjectName("btnWebSearchClear")
        self.btn_clear_search_pending.setFixedWidth(110)
        self.btn_clear_search_pending.setFixedHeight(36)
        self.btn_clear_search_pending.clicked.connect(lambda: self.txt_search_pending.setText(""))
        search_row.addWidget(self.txt_search_pending)
        search_row.addWidget(self.btn_clear_search_pending)
        lay.addLayout(search_row)

        self.tbl_pending = QTableWidget()
        self.tbl_pending.setColumnCount(12)
        self.tbl_pending.setHorizontalHeaderLabels(
            ["ID", "HỌ TÊN", "SĐT", "HÃNG XE", "BIỂN SỐ", "DỊCH VỤ", "TỔNG GIÁ THÀNH", "NGÀY HẸN", "GIỜ HẸN", "KTV PHỤ TRÁCH", "GHI CHÚ", "THỜI GIAN ĐẶT"]
        )
        header = self.tbl_pending.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.Stretch)
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.ResizeToContents)
        self.tbl_pending.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.tbl_pending.setSelectionMode(QAbstractItemView.SingleSelection)
        self.tbl_pending.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.tbl_pending.verticalHeader().setVisible(False)
        self.tbl_pending.setAlternatingRowColors(True)
        lay.addWidget(self.tbl_pending)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(10)

        self.btn_accept = QPushButton("TIẾP NHẬN VÀO CRM")
        self.btn_accept.setObjectName("btnWebAccept")
        self.btn_accept.setFixedWidth(220)
        self.btn_accept.setFixedHeight(40)
        self.btn_accept.clicked.connect(self._accept_selected)

        self.btn_reject = QPushButton("TỪ CHỐI")
        self.btn_reject.setObjectName("btnWebReject")
        self.btn_reject.setFixedWidth(120)
        self.btn_reject.setFixedHeight(40)
        self.btn_reject.clicked.connect(self._reject_selected)

        btn_row.addWidget(self.btn_accept)
        btn_row.addWidget(self.btn_reject)
        btn_row.addStretch()
        lay.addLayout(btn_row)

    def _build_all_tab(self):
        lay = QVBoxLayout(self.tab_all)
        lay.setContentsMargins(0, 10, 0, 0)

        search_row = QHBoxLayout()
        self.txt_search_all = QLineEdit()
        self.txt_search_all.setObjectName("webSearchInput")
        self.txt_search_all.setPlaceholderText("Tìm khách hàng / SĐT...")
        self.txt_search_all.setMinimumHeight(36)
        self.txt_search_all.textChanged.connect(self._render_all)
        self.btn_clear_search_all = QPushButton("XÓA LỌC")
        self.btn_clear_search_all.setObjectName("btnWebSearchClear")
        self.btn_clear_search_all.setFixedWidth(110)
        self.btn_clear_search_all.setFixedHeight(36)
        self.btn_clear_search_all.clicked.connect(lambda: self.txt_search_all.setText(""))
        search_row.addWidget(self.txt_search_all)
        search_row.addWidget(self.btn_clear_search_all)
        lay.addLayout(search_row)

        self.tbl_all = QTableWidget()
        self.tbl_all.setColumnCount(13)
        self.tbl_all.setHorizontalHeaderLabels(
            ["ID", "HỌ TÊN", "SĐT", "HÃNG XE", "BIỂN SỐ", "DỊCH VỤ", "TỔNG GIÁ THÀNH", "NGÀY HẸN", "GIỜ HẸN", "KTV PHỤ TRÁCH", "GHI CHÚ", "TRẠNG THÁI", "THỜI GIAN ĐẶT"]
        )
        header2 = self.tbl_all.horizontalHeader()
        header2.setSectionResizeMode(QHeaderView.Stretch)
        header2.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        header2.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        header2.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        header2.setSectionResizeMode(4, QHeaderView.ResizeToContents)
        header2.setSectionResizeMode(11, QHeaderView.ResizeToContents)
        self.tbl_all.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.tbl_all.setSelectionMode(QAbstractItemView.SingleSelection)
        self.tbl_all.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.tbl_all.verticalHeader().setVisible(False)
        self.tbl_all.setAlternatingRowColors(True)
        lay.addWidget(self.tbl_all)

    def _make_table(self, headers: list) -> QTableWidget:
        tbl = QTableWidget()
        tbl.setColumnCount(len(headers))
        tbl.setHorizontalHeaderLabels(headers)
        tbl.setSelectionBehavior(QAbstractItemView.SelectRows)
        tbl.setSelectionMode(QAbstractItemView.SingleSelection)
        tbl.setEditTriggers(QAbstractItemView.NoEditTriggers)
        tbl.verticalHeader().setVisible(False)
        tbl.horizontalHeader().setStretchLastSection(True)
        tbl.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        tbl.setAlternatingRowColors(True)
        return tbl

    def _apply_dark_style(self):
        self.setStyleSheet("""
            QWidget#webBookingRoot {
                background: transparent;
                color: #dbeafe;
                font-family: "Segoe UI";
            }
            QLabel {
                color: #dbeafe;
            }
            QLabel#webBookingTitle,
            QLabel#webPendingInfo {
                border: none;
                background: transparent;
                padding: 0;
            }
            QLineEdit#webSearchInput {
                background-color: #0b1220;
                color: #e2e8f0;
                border: 1px solid #334155;
                border-radius: 10px;
                padding: 0 12px;
                font-size: 11px;
                selection-background-color: #0ea5e9;
            }
            QLineEdit#webSearchInput:focus {
                border: 1px solid #38bdf8;
                background-color: #0f172a;
            }
            QLineEdit#webSearchInput::placeholder {
                color: #94a3b8;
            }
            QLabel#webBookingTitle {
                color: #f8fafc;
                font-size: 18px;
                font-weight: 800;
            }
            QLabel#webPendingInfo {
                color: #cbd5e1;
                font-size: 11px;
            }
            QFrame {
                background-color: #111827;
                border: 1px solid #334155;
                border-radius: 10px;
            }
            QFrame#webStatCard {
                background-color: #111827;
                border: 1px solid #2b3d57;
                border-radius: 12px;
            }
            QLabel#webStatLabel {
                color: #cbd5e1;
                font-size: 11px;
                font-weight: 700;
                letter-spacing: 0.4px;
                border: none;
                background: transparent;
            }
            QLabel#webStatValue {
                color: #f8fafc;
                font-size: 24px;
                font-weight: 800;
                border: none;
                background: transparent;
            }
            QTabWidget::pane {
                border: 1px solid #334155;
                background-color: #111827;
                border-radius: 10px;
            }
            QTabBar::tab {
                background: #1e293b;
                color: #cbd5e1;
                padding: 8px 14px;
                border-top-left-radius: 8px;
                border-top-right-radius: 8px;
                margin-right: 3px;
            }
            QTabBar::tab:selected {
                background: #0ea5e9;
                color: #f8fafc;
            }
            QPushButton {
                background-color: #1e293b;
                color: #e2e8f0;
                border: 1px solid #334155;
                border-radius: 10px;
                font-weight: 700;
                font-size: 11px;
                padding: 9px 14px;
            }
            QPushButton:hover {
                background-color: #0ea5e9;
                border: 1px solid #38bdf8;
                color: #f8fafc;
            }
            QPushButton#btnWebAccept {
                background-color: #0f766e;
                border: 1px solid #14b8a6;
            }
            QPushButton#btnWebReject {
                background-color: #7f1d1d;
                border: 1px solid #ef4444;
            }
            QPushButton#btnWebSearchClear {
                background-color: #1f2937;
                border: 1px solid #334155;
                color: #cbd5e1;
                border-radius: 10px;
                font-size: 12px;
                font-weight: 700;
                padding: 0 10px;
            }
            QPushButton#btnWebSearchClear:hover {
                background-color: #334155;
                border: 1px solid #475569;
                color: #f8fafc;
            }
            QTableWidget {
                background-color: #0f172a;
                alternate-background-color: #111b31;
                color: #e2e8f0;
                border: 1px solid #334155;
                gridline-color: #1f2937;
                selection-background-color: #0ea5e9;
                selection-color: #f8fafc;
            }
            QTableWidget::item {
                background-color: #0f172a;
                color: #e2e8f0;
            }
            QTableWidget::item:alternate {
                background-color: #111b31;
            }
            QHeaderView::section {
                background-color: #1e293b;
                color: #bae6fd;
                border: 0px;
                padding: 8px;
                font-weight: 700;
            }
        """)

    # ──────────────────────────────
    # Polling timer
    # ──────────────────────────────
    def _start_polling(self):
        self._timer = QTimer(self)
        self._timer.timeout.connect(self.request_refresh)
        self.set_polling_enabled(True)

    def set_polling_enabled(self, enabled: bool, refresh_now: bool = True):
        """Bật/tắt polling để tránh chặn UI khi user không ở trang web bookings."""
        self._polling_enabled = bool(enabled)
        if self._polling_enabled:
            if not self._timer.isActive():
                self._timer.start(5000)   # 5 giây
            if refresh_now:
                self.request_refresh()    # Refresh ngay khi bật (nếu cần)
        else:
            self._timer.stop()

    def request_refresh(self):
        if self._refresh_in_progress:
            self._refresh_queued = True
            return
        self._refresh_in_progress = True
        worker = threading.Thread(target=self._refresh_worker, daemon=True)
        worker.start()

    def _refresh_worker(self):
        pending = _http_get(f"{API_BASE}/bookings/pending")
        all_bk = _http_get(f"{API_BASE}/bookings/all")
        self.refresh_data_ready.emit(pending, all_bk)

    def _do_refresh(self):
        # Backward compatibility for callers in main.py / action handlers.
        self.request_refresh()

    def _apply_refresh_results(self, pending, all_bk):
        if pending is None:
            self._api_online = False
            self.lbl_status.setText("API OFFLINE")
        else:
            self._api_online = True
            self.lbl_status.setText("API ONLINE")

            # Detect đơn mới
            old_ids = {b["id"] for b in self._pending_data}
            new_entries = [b for b in pending if b["id"] not in old_ids]

            self._pending_data = pending or []
            self._all_data = all_bk or []
            self._refresh_technician_map()

            self._render_pending()
            self._render_all()
            self._update_stats()
            self.pending_count_changed.emit(len(self._pending_data))

            if new_entries:
                self._notify_new(new_entries)

        self._refresh_in_progress = False
        if self._refresh_queued:
            self._refresh_queued = False
            QTimer.singleShot(0, self.request_refresh)

    def _refresh_technician_map(self):
        try:
            tech_map = get_web_booking_technician_map() or {}
            self._tech_map_by_booking_id = tech_map.get("by_booking_id", {}) or {}
            self._tech_map_by_phone = tech_map.get("by_phone", {}) or {}
        except Exception:
            self._tech_map_by_booking_id = {}
            self._tech_map_by_phone = {}

    def _refresh_service_price_map(self, force=False):
        now = time.time()
        if not force and self._service_price_map and (now - self._service_price_last_sync) < 60:
            return
        try:
            self._service_price_map = get_service_price_map(active_only=True) or {}
            self._service_name_index = {
                self._normalize_text(name): name for name in self._service_price_map.keys() if str(name).strip()
            }
            self._service_price_last_sync = now
        except Exception:
            # Keep previous cache if DB is temporarily unavailable.
            if force:
                self._service_price_map = {}
                self._service_name_index = {}

    @staticmethod
    def _normalize_text(text):
        raw = str(text or "").strip().lower()
        if not raw:
            return ""
        raw = unicodedata.normalize("NFD", raw)
        raw = "".join(ch for ch in raw if unicodedata.category(ch) != "Mn")
        raw = raw.replace("đ", "d")
        raw = re.sub(r"[^a-z0-9]+", " ", raw)
        return re.sub(r"\s+", " ", raw).strip()

    def _match_service_name(self, token):
        norm = self._normalize_text(token)
        if not norm:
            return ""
        if norm in self._service_name_index:
            return self._service_name_index[norm]
        for key_norm, name in self._service_name_index.items():
            if norm in key_norm or key_norm in norm:
                return name
        return ""

    def _technician_for_booking(self, booking: dict):
        status = str(booking.get("status", "pending")).strip().lower()
        if status == "pending":
            return "Chờ tiếp nhận"

        booking_id = str(booking.get("id", "")).strip()
        phone = str(booking.get("sdt", "")).strip()
        by_id = self._tech_map_by_booking_id.get(booking_id, "")
        if by_id:
            return by_id
        by_phone = self._tech_map_by_phone.get(phone, "")
        if by_phone:
            return by_phone
        return "Chưa phân công"

    def _total_cost_for_booking(self, booking: dict):
        raw_amount = booking.get("tong_gia")
        if raw_amount in (None, ""):
            raw_amount = booking.get("total_amount")
        if raw_amount in (None, ""):
            raw_amount = booking.get("gia_du_kien")
        amount = None
        try:
            if raw_amount not in (None, ""):
                amount = int(float(str(raw_amount).replace(",", "").strip()))
        except Exception:
            amount = None
        if amount is None:
            self._refresh_service_price_map()
            formula = str(booking.get("dich_vu", "")).strip()
            parts = [x.strip() for x in re.split(r"[+,;/|]", formula) if str(x).strip()]
            if not parts and formula:
                parts = [formula]
            amount = 0
            for part in parts:
                matched = self._match_service_name(part) or part
                amount += int(self._service_price_map.get(matched, 0))
        if amount <= 0:
            return "Chưa báo giá"
        return f"{amount:,.0f} VNĐ"

    # ──────────────────────────────
    # Render
    # ──────────────────────────────
    def _render_pending(self):
        tbl = self.tbl_pending
        tbl.setRowCount(0)
        keyword = (self.txt_search_pending.text() if hasattr(self, "txt_search_pending") else "").strip().lower()
        self._pending_view_data = []
        for b in self._pending_data:
            customer_name = str(b.get("ho_ten", "")).strip().lower()
            phone = str(b.get("sdt", "")).strip().lower()
            if keyword and keyword not in customer_name and keyword not in phone:
                continue
            self._pending_view_data.append(b)

        for row, b in enumerate(self._pending_view_data):
            tbl.insertRow(row)
            vals = [
                str(b.get("id", "")),
                b.get("ho_ten", ""),
                b.get("sdt", ""),
                b.get("hang_xe", ""),
                b.get("bien_so", ""),
                b.get("dich_vu", ""),
                self._total_cost_for_booking(b),
                b.get("ngay_hen", ""),
                b.get("gio_hen", ""),
                self._technician_for_booking(b),
                b.get("ghi_chu", ""),
                b.get("created_at", ""),
            ]
            for col, val in enumerate(vals):
                item = QTableWidgetItem(val)
                item.setTextAlignment(Qt.AlignVCenter | Qt.AlignLeft)
                tbl.setItem(row, col, item)

    def _render_all(self):
        tbl = self.tbl_all
        tbl.setRowCount(0)
        STATUS_COLOR = {
            "pending":  "#f59e0b",
            "accepted": "#22c55e",
            "rejected": "#ef4444",
        }
        STATUS_LABEL = {
            "pending":  "CHỜ XỬ LÝ",
            "accepted": "ĐÃ TIẾP NHẬN",
            "rejected": "ĐÃ TỪ CHỐI",
        }
        keyword = (self.txt_search_all.text() if hasattr(self, "txt_search_all") else "").strip().lower()
        filtered = []
        for b in self._all_data:
            customer_name = str(b.get("ho_ten", "")).strip().lower()
            phone = str(b.get("sdt", "")).strip().lower()
            if keyword and keyword not in customer_name and keyword not in phone:
                continue
            filtered.append(b)

        for row, b in enumerate(filtered):
            tbl.insertRow(row)
            status = b.get("status", "pending")
            vals = [
                str(b.get("id", "")),
                b.get("ho_ten", ""),
                b.get("sdt", ""),
                b.get("hang_xe", ""),
                b.get("bien_so", ""),
                b.get("dich_vu", ""),
                self._total_cost_for_booking(b),
                b.get("ngay_hen", ""),
                b.get("gio_hen", ""),
                self._technician_for_booking(b),
                b.get("ghi_chu", ""),
                STATUS_LABEL.get(status, status),
                b.get("created_at", ""),
            ]
            for col, val in enumerate(vals):
                item = QTableWidgetItem(val)
                item.setTextAlignment(Qt.AlignVCenter | Qt.AlignLeft)
                if col == 11:  # status column
                    item.setForeground(QColor(STATUS_COLOR.get(status, "#ffffff")))
                tbl.setItem(row, col, item)

    def _update_stats(self):
        pending_n  = sum(1 for b in self._all_data if b.get("status") == "pending")
        accepted_n = sum(1 for b in self._all_data if b.get("status") == "accepted")
        rejected_n = sum(1 for b in self._all_data if b.get("status") == "rejected")
        self.lbl_pending_count[0].setText(str(pending_n))
        self.lbl_accepted_count[0].setText(str(accepted_n))
        self.lbl_rejected_count[0].setText(str(rejected_n))
        self.tabs.setTabText(0, f"CHỜ XỬ LÝ ({pending_n})")

    # ──────────────────────────────
    # Actions
    # ──────────────────────────────
    def _get_selected_booking_pending(self):
        row = self.tbl_pending.currentRow()
        if row < 0 or row >= len(self._pending_view_data):
            return None
        return self._pending_view_data[row]

    def _accept_selected(self):
        if not can_do(self.current_role, "web.accept"):
            QMessageBox.warning(self, "Không có quyền", "Vai trò hiện tại không có quyền tiếp nhận đơn.")
            return
        if not self._api_online:
            QMessageBox.warning(self, "API Offline", "Không thể kết nối API server.\nVui lòng chạy: python3 server/app.py")
            return
        booking = self._get_selected_booking_pending()
        if booking is None:
            QMessageBox.warning(self, "Chưa chọn", "Vui lòng chọn một đơn để tiếp nhận.")
            return

        created_order = None
        try:
            # Create MySQL service order first so we never have "accepted" web booking without an order.
            created_order = create_order_from_web_booking(booking, actor=self.current_user)
        except Exception as e:
            QMessageBox.warning(
                self,
                "Không thể tiếp nhận",
                f"Không thể tạo lệnh dịch vụ: {e}",
            )
            return

        result = _http_patch(f"{API_BASE}/bookings/{booking['id']}/accept")
        if result and result.get("success"):
            # Chuyển dữ liệu sang CRM nếu có
            if self.crm_widget:
                self._push_to_crm(booking)
            append_web_accept(
                {
                    "booking_id": booking.get("id"),
                    "customer_name": booking.get("ho_ten", ""),
                    "phone": booking.get("sdt", ""),
                    "car_model": booking.get("hang_xe", ""),
                    "service": booking.get("dich_vu", ""),
                    "appointment_date": booking.get("ngay_hen", ""),
                    "appointment_time": booking.get("gio_hen", ""),
                }
            )
            self._do_refresh()
            append_audit_log(
                "web.accept_booking",
                self.current_user,
                {"booking_id": booking.get("id"), "phone": booking.get("sdt", "")},
            )
            QMessageBox.information(
                self, "Thành công",
                f"✅ Đã tiếp nhận đơn của khách: {booking['ho_ten']}\n"
                f"Khách hàng đã được thêm vào CRM."
            )
        else:
            # Rollback logical flow: booking not accepted -> cancel created order.
            try:
                order_id = str((created_order or {}).get("order_id", "")).strip()
                if order_id:
                    transition_order_status(
                        order_id,
                        "CANCELLED",
                        actor=self.current_user,
                        note="Rollback do API accept booking thất bại",
                    )
            except Exception:
                pass
            QMessageBox.critical(self, "Lỗi", "Không thể cập nhật trạng thái. Kiểm tra API server.")

    def _reject_selected(self):
        if not can_do(self.current_role, "web.reject"):
            QMessageBox.warning(self, "Không có quyền", "Vai trò hiện tại không có quyền từ chối đơn.")
            return
        if not self._api_online:
            QMessageBox.warning(self, "API Offline", "Không thể kết nối API server.")
            return
        booking = self._get_selected_booking_pending()
        if booking is None:
            QMessageBox.warning(self, "Chưa chọn", "Vui lòng chọn một đơn để từ chối.")
            return

        reply = QMessageBox.question(
            self, "Xác nhận",
            f"Từ chối đơn của: {booking['ho_ten']} ({booking['sdt']})?",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No,
        )
        if reply != QMessageBox.Yes:
            return

        result = _http_patch(f"{API_BASE}/bookings/{booking['id']}/reject")
        if result and result.get("success"):
            self._do_refresh()
            append_audit_log(
                "web.reject_booking",
                self.current_user,
                {"booking_id": booking.get("id"), "phone": booking.get("sdt", "")},
            )
        else:
            QMessageBox.critical(self, "Lỗi", "Không thể cập nhật trạng thái.")

    def _push_to_crm(self, booking: dict):
        """Thêm khách hàng từ đơn đặt lịch vào CRM widget."""
        try:
            crm_data = {
                "ten": booking.get("ho_ten", ""),
                "sdt": booking.get("sdt", ""),
                "bien_so": booking.get("bien_so", ""),
                "phan_loai": "Khách mới",
                "tong_chi_tieu": 0,
                "ghi_chu": (
                    f"[Đặt lịch web #{booking.get('id')}] "
                    f"Dịch vụ: {booking.get('dich_vu', 'N/A')} | "
                    f"Ngày: {booking.get('ngay_hen', '')} {booking.get('gio_hen', '')}"
                ),
            }
            self.crm_widget._append_customer(crm_data)
            self.crm_widget.refresh_customer_table()
        except Exception as e:
            print(f"[WebBookings] Không thể push sang CRM: {e}")

    def _notify_new(self, new_entries):
        """Thông báo nhẹ, không block UI."""
        names = ", ".join(b.get("ho_ten", "?") for b in new_entries[:3])
        if len(new_entries) > 3:
            names += f" và {len(new_entries) - 3} người khác"
        self.lbl_status.setText(f"{len(new_entries)} đơn mới: {names}")


# ──────────────────────────────────────────────
# Standalone test
# ──────────────────────────────────────────────
if __name__ == "__main__":
    app = QApplication(sys.argv)
    w = WebBookingsWidget()
    w.show()
    sys.exit(app.exec_())
