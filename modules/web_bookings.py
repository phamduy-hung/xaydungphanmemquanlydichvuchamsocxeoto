"""
Module: Quản lý đặt lịch từ Web
- Polling API server mỗi 5 giây
- Hiển thị đơn pending
- Nhân viên duyệt / từ chối
- Chuyển sang CRM khi tiếp nhận
"""
import json
import sys
from pathlib import Path
from datetime import datetime
from urllib.request import urlopen, Request
from urllib.error import URLError

from PyQt5.QtCore import Qt, QTimer, pyqtSignal
from PyQt5.QtGui import QColor, QFont
from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QTableWidget, QTableWidgetItem,
    QHeaderView, QMessageBox, QTabWidget, QFrame,
    QAbstractItemView, QSizePolicy,
)

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

API_BASE = "http://localhost:8765/api"


def _http_get(url: str):
    """Gửi GET request, trả về dict hoặc list. None nếu lỗi."""
    try:
        with urlopen(url, timeout=3) as resp:
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

    def __init__(self, crm_widget=None, parent=None):
        super().__init__(parent)
        self.crm_widget = crm_widget   # Tham chiếu tới CRM widget nếu có
        self._pending_data = []        # Cache danh sách pending
        self._all_data = []            # Cache tất cả đơn
        self._api_online = False

        self.setWindowTitle("🌐 Đặt lịch từ Web")
        self.resize(1100, 700)
        self._build_ui()
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
        title = QLabel("🌐  Đặt lịch Online từ Website")
        title_font = QFont()
        title_font.setPointSize(16)
        title_font.setBold(True)
        title.setFont(title_font)
        header.addWidget(title)

        header.addStretch()

        self.lbl_status = QLabel("⚪ Đang kết nối API...")
        self.lbl_status.setStyleSheet("color: #94a3b8; font-size: 11pt;")
        header.addWidget(self.lbl_status)

        self.btn_refresh = QPushButton("🔄 Làm mới")
        self.btn_refresh.setFixedHeight(36)
        self.btn_refresh.clicked.connect(self._do_refresh)
        header.addWidget(self.btn_refresh)

        root.addLayout(header)

        # ─── Separator ───
        sep = QFrame()
        sep.setFrameShape(QFrame.HLine)
        sep.setStyleSheet("color: #334155;")
        root.addWidget(sep)

        # ─── Stat bar ───
        stat_bar = QHBoxLayout()
        self.lbl_pending_count = self._stat_card("Chờ xử lý", "0", "#f59e0b")
        self.lbl_accepted_count = self._stat_card("Đã tiếp nhận", "0", "#22c55e")
        self.lbl_rejected_count = self._stat_card("Đã từ chối", "0", "#ef4444")
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
        self.tabs.addTab(self.tab_pending, "📥 Chờ xử lý")

        # Tab 2: All history
        self.tab_all = QWidget()
        self._build_all_tab()
        self.tabs.addTab(self.tab_all, "📋 Tất cả đơn")

        root.addWidget(self.tabs)

    def _stat_card(self, label: str, value: str, color: str):
        frame = QFrame()
        frame.setFixedSize(180, 72)
        frame.setStyleSheet(f"QFrame {{ border-radius: 12px; border: 1.5px solid {color}33; }}")
        lay = QVBoxLayout(frame)
        lay.setContentsMargins(14, 8, 14, 8)
        lbl_val = QLabel(value)
        lbl_val.setStyleSheet(f"color: {color}; font-size: 24pt; font-weight: 900; border: none;")
        lbl_lbl = QLabel(label)
        lbl_lbl.setStyleSheet("color: #94a3b8; font-size: 10pt; border: none;")
        lay.addWidget(lbl_val)
        lay.addWidget(lbl_lbl)
        return lbl_val, lbl_lbl, frame

    def _build_pending_tab(self):
        lay = QVBoxLayout(self.tab_pending)
        lay.setContentsMargins(0, 10, 0, 0)
        lay.setSpacing(8)

        info = QLabel("Các đơn đặt lịch mới từ website đang chờ nhân viên xử lý. Bấm ✅ Tiếp nhận để chuyển khách hàng vào CRM.")
        info.setStyleSheet("color: #94a3b8; font-size: 10.5pt;")
        info.setWordWrap(True)
        lay.addWidget(info)

        self.tbl_pending = self._make_table([
            "ID", "Họ tên", "SĐT", "Biển số", "Dịch vụ", "Ngày hẹn", "Giờ hẹn", "Ghi chú", "Thời gian gửi"
        ])
        lay.addWidget(self.tbl_pending)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(10)

        self.btn_accept = QPushButton("✅  Tiếp nhận & chuyển sang CRM")
        self.btn_accept.setFixedHeight(40)
        self.btn_accept.setStyleSheet("""
            QPushButton { background-color: #22c55e; color: white; font-weight: bold; border-radius: 8px; font-size: 12pt; }
            QPushButton:hover { background-color: #16a34a; }
            QPushButton:pressed { background-color: #15803d; }
        """)
        self.btn_accept.clicked.connect(self._accept_selected)

        self.btn_reject = QPushButton("❌  Từ chối")
        self.btn_reject.setFixedHeight(40)
        self.btn_reject.setStyleSheet("""
            QPushButton { background-color: #ef4444; color: white; font-weight: bold; border-radius: 8px; font-size: 12pt; }
            QPushButton:hover { background-color: #dc2626; }
            QPushButton:pressed { background-color: #b91c1c; }
        """)
        self.btn_reject.clicked.connect(self._reject_selected)

        btn_row.addWidget(self.btn_accept)
        btn_row.addWidget(self.btn_reject)
        btn_row.addStretch()
        lay.addLayout(btn_row)

    def _build_all_tab(self):
        lay = QVBoxLayout(self.tab_all)
        lay.setContentsMargins(0, 10, 0, 0)
        self.tbl_all = self._make_table([
            "ID", "Họ tên", "SĐT", "Biển số", "Dịch vụ", "Ngày hẹn", "Giờ hẹn", "Ghi chú", "Trạng thái", "Thời gian"
        ])
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

    # ──────────────────────────────
    # Polling timer
    # ──────────────────────────────
    def _start_polling(self):
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._do_refresh)
        self._timer.start(5000)   # 5 giây
        self._do_refresh()        # Lần đầu ngay lập tức

    def _do_refresh(self):
        pending = _http_get(f"{API_BASE}/bookings/pending")
        all_bk  = _http_get(f"{API_BASE}/bookings/all")

        if pending is None:
            self._api_online = False
            self.lbl_status.setText("🔴 API offline — Chạy server/app.py")
            self.lbl_status.setStyleSheet("color: #ef4444; font-size: 11pt;")
            return

        self._api_online = True
        self.lbl_status.setText("🟢 API online — Đang theo dõi real-time")
        self.lbl_status.setStyleSheet("color: #22c55e; font-size: 11pt;")

        # Detect đơn mới
        old_ids = {b["id"] for b in self._pending_data}
        new_entries = [b for b in pending if b["id"] not in old_ids]

        self._pending_data = pending or []
        self._all_data = all_bk or []

        self._render_pending()
        self._render_all()
        self._update_stats()

        if new_entries:
            self.pending_count_changed.emit(len(self._pending_data))
            self._notify_new(new_entries)

    # ──────────────────────────────
    # Render
    # ──────────────────────────────
    def _render_pending(self):
        tbl = self.tbl_pending
        tbl.setRowCount(0)
        for row, b in enumerate(self._pending_data):
            tbl.insertRow(row)
            vals = [
                str(b.get("id", "")),
                b.get("ho_ten", ""),
                b.get("sdt", ""),
                b.get("bien_so", ""),
                b.get("dich_vu", ""),
                b.get("ngay_hen", ""),
                b.get("gio_hen", ""),
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
            "pending":  "⏳ Chờ xử lý",
            "accepted": "✅ Đã tiếp nhận",
            "rejected": "❌ Đã từ chối",
        }
        for row, b in enumerate(self._all_data):
            tbl.insertRow(row)
            status = b.get("status", "pending")
            vals = [
                str(b.get("id", "")),
                b.get("ho_ten", ""),
                b.get("sdt", ""),
                b.get("bien_so", ""),
                b.get("dich_vu", ""),
                b.get("ngay_hen", ""),
                b.get("gio_hen", ""),
                b.get("ghi_chu", ""),
                STATUS_LABEL.get(status, status),
                b.get("created_at", ""),
            ]
            for col, val in enumerate(vals):
                item = QTableWidgetItem(val)
                item.setTextAlignment(Qt.AlignVCenter | Qt.AlignLeft)
                if col == 8:  # status column
                    item.setForeground(QColor(STATUS_COLOR.get(status, "#ffffff")))
                tbl.setItem(row, col, item)

    def _update_stats(self):
        pending_n  = sum(1 for b in self._all_data if b.get("status") == "pending")
        accepted_n = sum(1 for b in self._all_data if b.get("status") == "accepted")
        rejected_n = sum(1 for b in self._all_data if b.get("status") == "rejected")
        self.lbl_pending_count[0].setText(str(pending_n))
        self.lbl_accepted_count[0].setText(str(accepted_n))
        self.lbl_rejected_count[0].setText(str(rejected_n))
        self.tabs.setTabText(0, f"📥 Chờ xử lý ({pending_n})")

    # ──────────────────────────────
    # Actions
    # ──────────────────────────────
    def _get_selected_booking_pending(self):
        row = self.tbl_pending.currentRow()
        if row < 0 or row >= len(self._pending_data):
            return None
        return self._pending_data[row]

    def _accept_selected(self):
        if not self._api_online:
            QMessageBox.warning(self, "API Offline", "Không thể kết nối API server.\nVui lòng chạy: python3 server/app.py")
            return
        booking = self._get_selected_booking_pending()
        if booking is None:
            QMessageBox.warning(self, "Chưa chọn", "Vui lòng chọn một đơn để tiếp nhận.")
            return

        result = _http_patch(f"{API_BASE}/bookings/{booking['id']}/accept")
        if result and result.get("success"):
            # Chuyển dữ liệu sang CRM nếu có
            if self.crm_widget:
                self._push_to_crm(booking)
            self._do_refresh()
            QMessageBox.information(
                self, "Thành công",
                f"✅ Đã tiếp nhận đơn của khách: {booking['ho_ten']}\n"
                f"Khách hàng đã được thêm vào CRM."
            )
        else:
            QMessageBox.critical(self, "Lỗi", "Không thể cập nhật trạng thái. Kiểm tra API server.")

    def _reject_selected(self):
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
        """Hiển thị thông báo khi có đơn mới."""
        names = ", ".join(b.get("ho_ten", "?") for b in new_entries[:3])
        if len(new_entries) > 3:
            names += f" và {len(new_entries) - 3} người khác"
        msg = QMessageBox(self)
        msg.setWindowTitle("🔔 Đặt lịch mới từ Web!")
        msg.setText(f"Có {len(new_entries)} đơn đặt lịch mới:\n{names}")
        msg.setIcon(QMessageBox.Information)
        msg.setStandardButtons(QMessageBox.Ok)
        msg.exec_()


# ──────────────────────────────────────────────
# Standalone test
# ──────────────────────────────────────────────
if __name__ == "__main__":
    app = QApplication(sys.argv)
    w = WebBookingsWidget()
    w.show()
    sys.exit(app.exec_())
