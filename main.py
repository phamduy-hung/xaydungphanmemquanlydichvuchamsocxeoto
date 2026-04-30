import sys
import time
import json
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget,
                             QPushButton, QVBoxLayout, QHBoxLayout, QStackedWidget,
                             QFrame, QLabel, QDialog, QLineEdit, QMessageBox, QToolButton)
from PyQt5.QtCore import Qt, QTimer, QSize
from PyQt5.QtGui import QPixmap, QIcon, QPainter, QPen, QColor, QPainterPath
from modules.audit_log import append_audit_log

try:
    from modules.qlkhachhang import CustomerManagerWidget
except Exception:
    CustomerManagerWidget = None

try:
    from modules.web_bookings import WebBookingsWidget
    WEB_BOOKINGS_AVAILABLE = True
except Exception:
    WebBookingsWidget = None
    WEB_BOOKINGS_AVAILABLE = False

try:
    from ui.compiled.ui_kho_vattu import KhoVatTuUI
except Exception:
    KhoVatTuUI = None
    
try:
    from modules.baocao_thongke import BaoCaoWindow
except Exception:
    BaoCaoWindow = None

try:
    from modules.dashboard import DashboardWidget
except Exception:
    DashboardWidget = None

try:
    from modules.pos import POSWidget
except Exception:
    POSWidget = None

try:
    from modules.settings import SettingsWidget
except Exception:
    SettingsWidget = None

try:
    from modules.chamsoc_kh_marketing import ChamSocKhachHangVaMarketingWindow
except Exception:
    ChamSocKhachHangVaMarketingWindow = None

try:
    from modules.ql_nhan_su import QuanLyNhanVienWidget
except Exception:
    QuanLyNhanVienWidget = None

try:
    from modules.hoa_don import HoaDonManagerWidget
except Exception:
    HoaDonManagerWidget = None

try:
    from modules.tiep_nhan_xe import TiepNhanXeWidget
except Exception:
    TiepNhanXeWidget = None

try:
    from modules.audit_log_view import AuditLogViewWidget
except Exception:
    AuditLogViewWidget = None

try:
    from modules.rbac_runtime import allowed_sections_for_role, can_access_section
except Exception:
    allowed_sections_for_role = None
    can_access_section = None

class MainWindow(QMainWindow):
    def __init__(self, auth_user=None):
        super().__init__()
        self.setWindowTitle("PROCARE - Premium AutoCare System")
        self.resize(1400, 850)
        self.auth_required = False
        self.is_logged_in = True
        self.child_windows = {}
        self._web_pending_count = 0
        self._module_loading = set()
        self._warmup_queue = []
        self._last_user_action = time.monotonic()
        self.auth_user = auth_user or {"username": "admin", "role": "Quản lý"}
        self.current_role = self.auth_user.get("role", "Quản lý")

        central_widget = QWidget()
        central_widget.setObjectName("mainRoot")
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Build Sidebar
        self.sidebar = QFrame()
        self.sidebar.setObjectName("sidebar")
        self.sidebar.setFixedWidth(280)
        sidebar_layout = QVBoxLayout(self.sidebar)
        sidebar_layout.setContentsMargins(20, 35, 20, 30)

        logo_lbl = QLabel()
        logo_lbl.setAlignment(Qt.AlignCenter)
        logo_lbl.setMinimumHeight(100)
        logo_path = PROJECT_ROOT / "assets" / "images" / "logo-removebg-preview.png"
        logo_pixmap = QPixmap(str(logo_path))
        if not logo_pixmap.isNull():
            logo_lbl.setPixmap(
                logo_pixmap.scaled(260, 100, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            )
        else:
            # Fallback nếu không tải được ảnh logo.
            logo_lbl.setText("ProCare")
        sidebar_layout.addWidget(logo_lbl)
        sidebar_layout.addSpacing(50)

        # Nav Buttons
        self.nav_buttons = []
        self.nav_button_meta = []
        self._add_nav_button(sidebar_layout, "dashboard", "📊  TỔNG QUAN", self.show_dashboard)
        self._add_nav_button(sidebar_layout, "web", "📅  ĐẶT LỊCH WEB", self.show_web_bookings)
        self._add_nav_button(sidebar_layout, "tiepnhan", "🛎️  TIẾP NHẬN XE", self.show_tiep_nhan_xe)
        self._add_nav_button(sidebar_layout, "crm", "👥  KHÁCH HÀNG (CRM)", self.show_crm)
        self._add_nav_button(sidebar_layout, "cskh", "💌  CHĂM SÓC KHÁCH HÀNG", self.show_chamsoc_kh)
        self._add_nav_button(sidebar_layout, "kho", "📦  KHO & VẬT TƯ", self.show_kho_vattu)
        self._add_nav_button(sidebar_layout, "baocao", "📈  BÁO CÁO THỐNG KÊ", self.show_baocao)
        self._add_nav_button(sidebar_layout, "pos", "💰  BÁN HÀNG & POS", self.show_pos)
        self._add_nav_button(sidebar_layout, "nhansu", "💼  QUẢN LÝ NHÂN SỰ", self.show_nhan_su)
        self._add_nav_button(sidebar_layout, "invoices", "🧾  QUẢN LÝ HÓA ĐƠN", self.show_hoa_don)
        self._add_nav_button(sidebar_layout, "audit", "📝  NHẬT KÝ HỆ THỐNG", self.show_audit)
        self._add_nav_button(sidebar_layout, "settings", "⚙️  CÀI ĐẶT HỆ THỐNG", self.show_settings)
        
        sidebar_layout.addStretch()
        
        self.logout_btn = QPushButton("ĐĂNG XUẤT")
        self.logout_btn.setObjectName("btnLogout")
        self.logout_btn.setFixedHeight(45)
        self.logout_btn.clicked.connect(self._logout)
        sidebar_layout.addWidget(self.logout_btn)

        # Build Stack
        self.stack = QStackedWidget()
        
        # Page 0: Dashboard Placeholder
        self.page_dash = QWidget()
        self.dash_lay = QVBoxLayout(self.page_dash)
        self.dash_lay.setContentsMargins(30, 30, 30, 30)
        self.stack.addWidget(self.page_dash)

        # Page 1: Web Bookings
        self.page_web = QWidget()
        self.web_lay = QVBoxLayout(self.page_web)
        self.web_lay.setContentsMargins(30, 30, 30, 30)
        self.stack.addWidget(self.page_web)
        
        # Page 2: CRM
        self.page_crm = QWidget()
        self.crm_lay = QVBoxLayout(self.page_crm)
        self.crm_lay.setContentsMargins(30, 30, 30, 30)
        self.stack.addWidget(self.page_crm)

        # Page 2b: Tiep nhan xe
        self.page_tiepnhan = QWidget()
        self.tiepnhan_lay = QVBoxLayout(self.page_tiepnhan)
        self.tiepnhan_lay.setContentsMargins(30, 30, 30, 30)
        self.stack.addWidget(self.page_tiepnhan)

        # Page 3: Cham soc KH
        self.page_cskh = QWidget()
        self.cskh_lay = QVBoxLayout(self.page_cskh)
        self.cskh_lay.setContentsMargins(30, 30, 30, 30)
        self.stack.addWidget(self.page_cskh)

        # Page 4: Kho Vat Tu
        self.page_kho = QWidget()
        self.kho_lay = QVBoxLayout(self.page_kho)
        self.kho_lay.setContentsMargins(30, 30, 30, 30)
        self.stack.addWidget(self.page_kho)

        # Page 5: Bao Cao
        self.page_baocao = QWidget()
        self.baocao_lay = QVBoxLayout(self.page_baocao)
        self.baocao_lay.setContentsMargins(30, 30, 30, 30)
        self.stack.addWidget(self.page_baocao)

        # Page 6: POS
        self.page_pos = QWidget()
        self.pos_lay = QVBoxLayout(self.page_pos)
        self.pos_lay.setContentsMargins(30, 30, 30, 30)
        self.stack.addWidget(self.page_pos)

        # Page 7: Settings
        self.page_nhansu = QWidget()
        self.nhansu_lay = QVBoxLayout(self.page_nhansu)
        self.nhansu_lay.setContentsMargins(30, 30, 30, 30)
        self.stack.addWidget(self.page_nhansu)

        # Page 8b: Hoa don
        self.page_hoadon = QWidget()
        self.hoadon_lay = QVBoxLayout(self.page_hoadon)
        self.hoadon_lay.setContentsMargins(30, 30, 30, 30)
        self.stack.addWidget(self.page_hoadon)

        # Page 8c: Audit
        self.page_audit = QWidget()
        self.audit_lay = QVBoxLayout(self.page_audit)
        self.audit_lay.setContentsMargins(30, 30, 30, 30)
        self.stack.addWidget(self.page_audit)

        # Page 8: Settings
        self.page_set = QWidget()
        self.set_lay = QVBoxLayout(self.page_set)
        self.set_lay.setContentsMargins(30, 30, 30, 30)
        self.stack.addWidget(self.page_set)
        
        # Page N: Generic Placeholder
        self.page_placeholder = QWidget()
        self.place_lay = QVBoxLayout(self.page_placeholder)
        self.lbl_place = QLabel("MODULE")
        self.lbl_place.setObjectName("placeholderLabel")
        self.place_lay.addWidget(self.lbl_place, alignment=Qt.AlignCenter)
        self.stack.addWidget(self.page_placeholder)

        # --- Build Content Area ---
        self.content_area = QWidget()
        content_layout = QVBoxLayout(self.content_area)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(0)

        # Unified Header Bar
        self.header_bar = QFrame()
        self.header_bar.setObjectName("topHeaderBar")
        self.header_bar.setFixedHeight(80)
        h_layout = QHBoxLayout(self.header_bar)
        h_layout.setContentsMargins(35, 0, 35, 0)
        self.lbl_page_title = QLabel("Bảng Tổng Quan")
        self.lbl_page_title.setObjectName("lblPageTitle")
        h_layout.addWidget(self.lbl_page_title)
        h_layout.addStretch()
        self.status_box = QLabel(f"{self.auth_user.get('username', 'user')} | {self.current_role}")
        self.status_box.setObjectName("statusBadge")
        h_layout.addWidget(self.status_box)

        content_layout.addWidget(self.header_bar)
        content_layout.addWidget(self.stack)

        main_layout.addWidget(self.sidebar)
        main_layout.addWidget(self.content_area)
        self._apply_dark_theme()

        # Init modules
        self._init_modules()

        # Set default
        self._apply_role_visibility()
        self.show_dashboard()

        self._update_web_badge(0)
        # Delay warm-up; avoid stealing responsiveness at startup.
        QTimer.singleShot(5000, self._start_module_warmup)

    def _apply_dark_theme(self):
        self.setStyleSheet("""
            QMainWindow, QWidget#mainRoot {
                background-color: #0b1220;
                color: #dbeafe;
            }
            #sidebar {
                background-color: #0f172a;
                border-right: 1px solid #1f2937;
            }
            QPushButton[navButton="true"] {
                background-color: transparent;
                color: #cbd5e1;
                border: 1px solid transparent;
                border-radius: 10px;
                padding: 10px 14px;
                text-align: left;
                font-weight: 600;
            }
            QPushButton[navButton="true"]:hover {
                background-color: #1e293b;
                border: 1px solid #334155;
                color: #f8fafc;
            }
            QPushButton[navButton="true"]:checked {
                background-color: #0ea5e9;
                border: 1px solid #38bdf8;
                color: #f8fafc;
                font-weight: 700;
            }
            #btnLogout {
                background-color: #111827;
                border: 1px solid #374151;
                color: #f87171;
                border-radius: 8px;
                font-weight: 700;
            }
            #btnLogout:hover {
                background-color: #7f1d1d;
                border: 1px solid #ef4444;
                color: #fee2e2;
            }
            #topHeaderBar {
                background-color: #111827;
                border-bottom: 1px solid #1f2937;
            }
            #lblPageTitle {
                color: #f8fafc;
                font-size: 22px;
                font-weight: 800;
            }
            #statusBadge {
                background-color: #1e293b;
                color: #93c5fd;
                border: 1px solid #334155;
                border-radius: 12px;
                padding: 4px 10px;
                font-weight: 600;
            }
            QStackedWidget {
                background-color: #0b1220;
            }
            #placeholderLabel {
                color: #93c5fd;
                font-size: 22px;
                font-weight: 700;
            }
        """)

    def _add_nav_button(self, layout, key, text, callback):
        btn = QPushButton(text)
        btn.setProperty("navButton", "true")
        btn.setCheckable(True)
        btn.setFixedHeight(50)
        btn.clicked.connect(callback)
        self.nav_buttons.append(btn)
        self.nav_button_meta.append((key, btn))
        layout.addWidget(btn)
        return btn

    def _allowed_sections(self):
        if callable(allowed_sections_for_role):
            return allowed_sections_for_role(self.current_role)
        if self.current_role == "Lễ tân":
            return {"dashboard", "web", "tiepnhan", "crm", "cskh", "pos", "invoices"}
        return {"dashboard", "web", "tiepnhan", "crm", "cskh", "kho", "baocao", "pos", "nhansu", "invoices", "audit", "settings"}

    def _can_access(self, section_key):
        if callable(can_access_section):
            return can_access_section(self.current_role, section_key)
        return section_key in self._allowed_sections()

    def _apply_role_visibility(self):
        allowed = self._allowed_sections()
        for key, btn in self.nav_button_meta:
            btn.setVisible(key in allowed)

    def _access_denied(self):
        QMessageBox.warning(self, "Không có quyền", "Tài khoản hiện tại không có quyền truy cập chức năng này.")

    def _logout(self):
        # Đóng giao diện quản lý hiện tại trước để chỉ còn màn đăng nhập.
        append_audit_log(
            "auth.logout",
            self.auth_user.get("username", "system"),
            {"role": self.current_role},
        )
        self.hide()
        auth_user = show_login_dialog()
        if auth_user is None:
            # Nếu đóng màn đăng nhập, thoát hẳn ứng dụng.
            QApplication.instance().quit()
            return
        next_window = MainWindow(auth_user=auth_user)
        next_window.show()
        # Giữ reference tạm để tránh bị GC trước khi window cũ đóng.
        self._next_window = next_window
        self.close()

    def _reset_nav(self):
        for b in self.nav_buttons:
            b.setChecked(False)

    def _init_modules(self):
        self.dashboard_mod = None
        self.crm = None
        self.tiepnhan = None
        self.web = None
        self.kho = None
        self.cskh_marketing = None
        self.baocao = None
        self.pos_mod = None
        self.nhansu_mod = None
        self.hoadon_mod = None
        self.audit_mod = None
        self.settings_mod = None

    def _ensure_dashboard(self):
        if self.dashboard_mod is None and DashboardWidget:
            self.dashboard_mod = DashboardWidget()
            try:
                self.dashboard_mod.setWindowFlags(Qt.Widget)
            except Exception:
                pass
            try:
                self.dashboard_mod.go_to_pos.connect(self.show_pos)
                self.dashboard_mod.go_to_kho.connect(self.show_kho_vattu)
                self.dashboard_mod.go_to_cskh.connect(self.show_chamsoc_kh)
            except Exception:
                pass
            self.dash_lay.addWidget(self.dashboard_mod)
        return self.dashboard_mod is not None

    def _ensure_crm(self):
        if self.crm is None and CustomerManagerWidget:
            self.crm = CustomerManagerWidget(
                current_role=self.current_role,
                current_user=self.auth_user.get("username", "system"),
            )
            try:
                self.crm.setWindowFlags(Qt.Widget)
            except Exception:
                pass
            self.crm_lay.addWidget(self.crm)
            # Bind CRM to web module when both are available.
            if self.web is not None:
                try:
                    self.web.crm_widget = self.crm
                except Exception:
                    pass
            if self.pos_mod is not None:
                try:
                    self.pos_mod.crm_widget = self.crm
                except Exception:
                    pass
        return self.crm is not None

    def _ensure_web_bookings(self):
        if self.web is None and WEB_BOOKINGS_AVAILABLE:
            self.web = WebBookingsWidget(
                crm_widget=self.crm,
                current_role=self.current_role,
                current_user=self.auth_user.get("username", "system"),
            )
            try:
                self.web.setWindowFlags(Qt.Widget)
            except Exception:
                pass
            try:
                self.web.pending_count_changed.connect(self._update_web_badge)
            except Exception:
                pass
            self.web_lay.addWidget(self.web)
        return self.web is not None

    def _ensure_kho(self):
        if self.kho is None and KhoVatTuUI:
            self.kho = KhoVatTuUI()
            try:
                self.kho.setWindowFlags(Qt.Widget)
            except Exception:
                pass
            try:
                self.kho.setStyleSheet("""
                    QWidget {
                        background-color: #0b1220;
                        color: #dbeafe;
                        font-family: "Segoe UI", "Inter";
                    }
                    QFrame, QGroupBox {
                        background-color: #111827;
                        border: 1px solid #334155;
                        border-radius: 10px;
                    }
                    QLineEdit, QComboBox, QDateEdit, QTextEdit {
                        background-color: #0f172a;
                        color: #e2e8f0;
                        border: 1px solid #334155;
                        border-radius: 8px;
                        padding: 6px 8px;
                    }
                    QTableWidget, QTableView {
                        background-color: #0f172a;
                        alternate-background-color: #111b31;
                        color: #e2e8f0;
                        border: 1px solid #334155;
                        gridline-color: #1f2937;
                        selection-background-color: #0ea5e9;
                        selection-color: #f8fafc;
                    }
                    QHeaderView::section {
                        background-color: #1e293b;
                        color: #bae6fd;
                        border: 0px;
                        padding: 8px;
                        font-weight: 700;
                    }
                    QPushButton {
                        background-color: #1e293b;
                        color: #e2e8f0;
                        border: 1px solid #334155;
                        border-radius: 10px;
                        font-weight: 700;
                        font-size: 13px;
                        padding: 8px 12px;
                    }
                    QPushButton:hover {
                        background-color: #0ea5e9;
                        border: 1px solid #38bdf8;
                        color: #f8fafc;
                    }
                """)
            except Exception:
                pass
            self.kho_lay.addWidget(self.kho)
        return self.kho is not None

    def _ensure_chamsoc_kh(self):
        if self.cskh_marketing is None and ChamSocKhachHangVaMarketingWindow:
            self.cskh_marketing = ChamSocKhachHangVaMarketingWindow()
            try:
                self.cskh_marketing.setWindowFlags(Qt.Widget)
            except Exception:
                pass
            self.cskh_lay.addWidget(self.cskh_marketing)
        return self.cskh_marketing is not None

    def _ensure_baocao(self):
        if self.baocao is None and BaoCaoWindow:
            self.baocao = BaoCaoWindow(
                current_role=self.current_role,
                current_user=self.auth_user.get("username", "system"),
            )
            try:
                self.baocao.setWindowFlags(Qt.Widget)
            except Exception:
                pass
            self.baocao_lay.addWidget(self.baocao)
        return self.baocao is not None

    def _ensure_pos(self):
        if self.pos_mod is None and POSWidget:
            self.pos_mod = POSWidget(
                current_role=self.current_role,
                current_user=self.auth_user.get("username", "system"),
            )
            try:
                self.pos_mod.setWindowFlags(Qt.Widget)
            except Exception:
                pass
            self.pos_lay.addWidget(self.pos_mod)
            if self.crm is not None:
                try:
                    self.pos_mod.crm_widget = self.crm
                except Exception:
                    pass
        return self.pos_mod is not None

    def _ensure_settings(self):
        if self.settings_mod is None and SettingsWidget:
            self.settings_mod = SettingsWidget()
            try:
                self.settings_mod.setWindowFlags(Qt.Widget)
            except Exception:
                pass
            self.set_lay.addWidget(self.settings_mod)
        return self.settings_mod is not None

    def _ensure_nhan_su(self):
        if self.nhansu_mod is None and QuanLyNhanVienWidget:
            self.nhansu_mod = QuanLyNhanVienWidget()
            try:
                self.nhansu_mod.setWindowFlags(Qt.Widget)
            except Exception:
                pass
            self.nhansu_lay.addWidget(self.nhansu_mod)
        return self.nhansu_mod is not None

    def _ensure_tiep_nhan(self):
        if self.tiepnhan is None and TiepNhanXeWidget:
            self.tiepnhan = TiepNhanXeWidget(current_user=self.auth_user.get("username", "system"))
            try:
                self.tiepnhan.setWindowFlags(Qt.Widget)
            except Exception:
                pass
            self.tiepnhan_lay.addWidget(self.tiepnhan)
        return self.tiepnhan is not None

    def _ensure_hoa_don(self):
        if self.hoadon_mod is None and HoaDonManagerWidget:
            self.hoadon_mod = HoaDonManagerWidget(
                current_role=self.current_role,
                current_user=self.auth_user.get("username", "system"),
            )
            try:
                self.hoadon_mod.setWindowFlags(Qt.Widget)
            except Exception:
                pass
            self.hoadon_lay.addWidget(self.hoadon_mod)
        return self.hoadon_mod is not None

    def _ensure_audit(self):
        if self.audit_mod is None and AuditLogViewWidget:
            self.audit_mod = AuditLogViewWidget()
            try:
                self.audit_mod.setWindowFlags(Qt.Widget)
            except Exception:
                pass
            self.audit_lay.addWidget(self.audit_mod)
        return self.audit_mod is not None

    def _ensure_deferred(self, key: str, ensure_func):
        if getattr(self, key, None) is not None or key in self._module_loading:
            return
        self._module_loading.add(key)

        def _load():
            try:
                ensure_func()
            finally:
                self._module_loading.discard(key)

        QTimer.singleShot(0, _load)

    def _start_module_warmup(self):
        # Warm-up theo nhịp để giảm khựng khi mở tab lần đầu.
        self._warmup_queue = [
            lambda: self._ensure_deferred("crm", self._ensure_crm),
            lambda: self._ensure_deferred("tiepnhan", self._ensure_tiep_nhan),
            lambda: self._ensure_deferred("kho", self._ensure_kho),
            lambda: self._ensure_deferred("baocao", self._ensure_baocao),
            lambda: self._ensure_deferred("pos_mod", self._ensure_pos),
            lambda: self._ensure_deferred("nhansu_mod", self._ensure_nhan_su),
            lambda: self._ensure_deferred("hoadon_mod", self._ensure_hoa_don),
            lambda: self._ensure_deferred("audit_mod", self._ensure_audit),
            lambda: self._ensure_deferred("settings_mod", self._ensure_settings),
        ]
        self._warmup_next()

    def _warmup_next(self):
        if not self._warmup_queue:
            return
        # Do not warm-up while user is actively navigating.
        if (time.monotonic() - self._last_user_action) < 1.2:
            QTimer.singleShot(900, self._warmup_next)
            return
        task = self._warmup_queue.pop(0)
        task()
        QTimer.singleShot(1400, self._warmup_next)


    def show_dashboard(self):
        self._last_user_action = time.monotonic()
        self._set_web_polling(False)
        self._reset_nav()
        if len(self.nav_buttons) > 0: self.nav_buttons[0].setChecked(True)
        self.lbl_page_title.setText("Bảng Tổng Quan")
        self.stack.setCurrentWidget(self.page_dash)
        if self.dashboard_mod is None:
            self._ensure_deferred("dashboard_mod", self._ensure_dashboard)

    def show_web_bookings(self):
        self._last_user_action = time.monotonic()
        self._reset_nav()
        if len(self.nav_buttons) > 1: self.nav_buttons[1].setChecked(True)
        self.lbl_page_title.setText("Đặt Lịch Trực Tuyến")
        if WEB_BOOKINGS_AVAILABLE:
            self.stack.setCurrentWidget(self.page_web)
            if self.web is None:
                self._ensure_deferred("web", self._ensure_web_bookings)
            if self.web is not None:
                try:
                    self.web.crm_widget = self.crm
                except Exception:
                    pass
            # Bật timer trước, refresh trễ 1 nhịp để tránh khựng khi vừa bấm chuyển trang.
            self._set_web_polling(True, refresh_now=False)
            QTimer.singleShot(120, self._refresh_web_bookings_deferred)
        else:
            self.show_placeholder("Không tìm thấy module Đặt Lịch Web")

    def show_tiep_nhan_xe(self):
        if not self._can_access("tiepnhan"):
            self._access_denied()
            return
        self._last_user_action = time.monotonic()
        self._set_web_polling(False)
        self._reset_nav()
        if len(self.nav_buttons) > 2: self.nav_buttons[2].setChecked(True)
        self.lbl_page_title.setText("Tiếp Nhận Xe / Lệnh Dịch Vụ")
        if TiepNhanXeWidget:
            self.stack.setCurrentWidget(self.page_tiepnhan)
            if self.tiepnhan is None:
                self._ensure_deferred("tiepnhan", self._ensure_tiep_nhan)
            elif hasattr(self.tiepnhan, "refresh_data"):
                self.tiepnhan.refresh_data()
        else:
            self.show_placeholder("Không tìm thấy module TIẾP NHẬN XE")

    def show_crm(self):
        self._last_user_action = time.monotonic()
        self._set_web_polling(False)
        self._reset_nav()
        if len(self.nav_buttons) > 3: self.nav_buttons[3].setChecked(True)
        self.lbl_page_title.setText("Quản Lý Khách Hàng")
        if CustomerManagerWidget:
            self.stack.setCurrentWidget(self.page_crm)
            if self.crm is None:
                self._ensure_deferred("crm", self._ensure_crm)
        else:
            self.show_placeholder("Không tìm thấy module CRM")

    def show_chamsoc_kh(self):
        self._last_user_action = time.monotonic()
        self._set_web_polling(False)
        self._reset_nav()
        if len(self.nav_buttons) > 4: self.nav_buttons[4].setChecked(True)
        self.lbl_page_title.setText("Chăm Sóc Khách Hàng")
        if ChamSocKhachHangVaMarketingWindow:
            self.stack.setCurrentWidget(self.page_cskh)
            if self.cskh_marketing is None:
                self._ensure_deferred("cskh_marketing", self._ensure_chamsoc_kh)
        else:
            self.show_placeholder("Không tìm thấy module CHĂM SÓC KHÁCH HÀNG")

    def show_kho_vattu(self):
        if not self._can_access("kho"):
            self._access_denied()
            return
        self._last_user_action = time.monotonic()
        self._set_web_polling(False)
        self._reset_nav()
        if len(self.nav_buttons) > 5: self.nav_buttons[5].setChecked(True)
        self.lbl_page_title.setText("Kho & Vật Tư")
        if KhoVatTuUI:
            self.stack.setCurrentWidget(self.page_kho)
            if self.kho is None:
                self._ensure_deferred("kho", self._ensure_kho)
        else:
            self.show_placeholder("Không tìm thấy module KHO & VẬT TƯ")

    def show_baocao(self):
        if not self._can_access("baocao"):
            self._access_denied()
            return
        self._last_user_action = time.monotonic()
        self._set_web_polling(False)
        self._reset_nav()
        if len(self.nav_buttons) > 6: self.nav_buttons[6].setChecked(True)
        self.lbl_page_title.setText("Báo Cáo & Thống Kê")
        if BaoCaoWindow:
            self.stack.setCurrentWidget(self.page_baocao)
            if self.baocao is None:
                self._ensure_deferred("baocao", self._ensure_baocao)
        else:
            self.show_placeholder("Không tìm thấy module BÁO CÁO THỐNG KÊ")

    def show_pos(self):
        self._last_user_action = time.monotonic()
        self._set_web_polling(False)
        self._reset_nav()
        if len(self.nav_buttons) > 7: self.nav_buttons[7].setChecked(True)
        self.lbl_page_title.setText("Bán Hàng & POS")
        if POSWidget:
            self.stack.setCurrentWidget(self.page_pos)
            if self.pos_mod is None:
                self._ensure_deferred("pos_mod", self._ensure_pos)
        else:
            self.show_placeholder("Không tìm thấy module BÁN HÀNG & POS")

    def show_settings(self):
        if not self._can_access("settings"):
            self._access_denied()
            return
        self._last_user_action = time.monotonic()
        self._set_web_polling(False)
        self._reset_nav()
        if len(self.nav_buttons) > 11: self.nav_buttons[11].setChecked(True)
        self.lbl_page_title.setText("Cài Đặt Hệ Thống")
        if SettingsWidget:
            self.stack.setCurrentWidget(self.page_set)
            if self.settings_mod is None:
                self._ensure_deferred("settings_mod", self._ensure_settings)
        else:
            self.show_placeholder("Không tìm thấy module CÀI ĐẶT HỆ THỐNG")

    def show_nhan_su(self):
        if not self._can_access("nhansu"):
            self._access_denied()
            return
        self._last_user_action = time.monotonic()
        self._set_web_polling(False)
        self._reset_nav()
        if len(self.nav_buttons) > 8: self.nav_buttons[8].setChecked(True)
        self.lbl_page_title.setText("Quản Lý Nhân Sự")
        if QuanLyNhanVienWidget:
            self.stack.setCurrentWidget(self.page_nhansu)
            if self.nhansu_mod is None:
                self._ensure_deferred("nhansu_mod", self._ensure_nhan_su)
        else:
            self.show_placeholder("Không tìm thấy module QUẢN LÝ NHÂN SỰ")

    def show_hoa_don(self):
        if not self._can_access("invoices"):
            self._access_denied()
            return
        self._last_user_action = time.monotonic()
        self._set_web_polling(False)
        self._reset_nav()
        if len(self.nav_buttons) > 9: self.nav_buttons[9].setChecked(True)
        self.lbl_page_title.setText("Quản Lý Hóa Đơn")
        if HoaDonManagerWidget:
            self.stack.setCurrentWidget(self.page_hoadon)
            if self.hoadon_mod is None:
                self._ensure_deferred("hoadon_mod", self._ensure_hoa_don)
            elif hasattr(self.hoadon_mod, "refresh_data"):
                self.hoadon_mod.refresh_data()
        else:
            self.show_placeholder("Không tìm thấy module QUẢN LÝ HÓA ĐƠN")

    def show_audit(self):
        if not self._can_access("audit"):
            self._access_denied()
            return
        self._last_user_action = time.monotonic()
        self._set_web_polling(False)
        self._reset_nav()
        if len(self.nav_buttons) > 10: self.nav_buttons[10].setChecked(True)
        self.lbl_page_title.setText("Nhật Ký Hệ Thống")
        if AuditLogViewWidget:
            self.stack.setCurrentWidget(self.page_audit)
            if self.audit_mod is None:
                self._ensure_deferred("audit_mod", self._ensure_audit)
            elif hasattr(self.audit_mod, "refresh_data"):
                self.audit_mod.refresh_data()
        else:
            self.show_placeholder("Không tìm thấy module NHẬT KÝ HỆ THỐNG")

    def show_placeholder(self, title):
        self._set_web_polling(False)
        self._reset_nav()
        for b in self.nav_buttons:
            if title in b.text():
                b.setChecked(True)
                break
        self.lbl_place.setText(f"MODULE ĐANG PHÁT TRIỂN:\n\n{title}")
        self.stack.setCurrentWidget(self.page_placeholder)

    def _refresh_web_bookings_deferred(self):
        if self.stack.currentWidget() is not self.page_web:
            return
        if WEB_BOOKINGS_AVAILABLE and hasattr(self, "web") and self.web is not None:
            try:
                self.web._do_refresh()
            except Exception:
                pass

    def _set_web_polling(self, enabled: bool, refresh_now: bool = False):
        if WEB_BOOKINGS_AVAILABLE and hasattr(self, "web"):
            try:
                self.web.set_polling_enabled(enabled, refresh_now=refresh_now)
            except Exception:
                pass

    def _update_web_badge(self, count):
        try:
            count = int(count)
        except Exception:
            count = 0
        self._web_pending_count = max(0, count)
        if len(self.nav_buttons) > 1:
            btn = self.nav_buttons[1]  # Web Bookings button
            base_text = "📅  ĐẶT LỊCH WEB"
            if self._web_pending_count > 0:
                btn.setText(f"{base_text}  ({self._web_pending_count})")
            else:
                btn.setText(base_text)

    def closeEvent(self, event):
        try:
            self._set_web_polling(False)
        except Exception:
            pass
        super().closeEvent(event)


def main():
    app = QApplication(sys.argv)
    auth_user = show_login_dialog()
    if auth_user is None:
        return
    window = MainWindow(auth_user=auth_user)
    window.show()
    sys.exit(app.exec_())


def _load_auth_accounts():
    cfg_path = PROJECT_ROOT / "data" / "auth_accounts.json"
    if cfg_path.exists():
        try:
            payload = json.loads(cfg_path.read_text(encoding="utf-8"))
            if isinstance(payload, list):
                return payload
        except Exception:
            pass
    return [
        {"username": "admin", "password": "123456", "role": "Quản lý"},
        {"username": "letan", "password": "123456", "role": "Lễ tân"},
        {"username": "admin1", "password": "123456", "role": "Quản lý"},
    ]


def show_login_dialog():
    def _eye_icon(crossed=False):
        pix = QPixmap(42, 42)
        pix.fill(Qt.transparent)
        p = QPainter(pix)
        p.setRenderHint(QPainter.Antialiasing)
        white = QColor("#f8fafc")
        pen = QPen(white, 2.8)
        p.setPen(pen)
        p.setBrush(Qt.NoBrush)

        # Eye outline
        path = QPainterPath()
        path.moveTo(6, 21)
        path.cubicTo(13, 10, 29, 10, 36, 21)
        path.cubicTo(29, 32, 13, 32, 6, 21)
        p.drawPath(path)

        # Iris + pupil
        p.setBrush(white)
        p.drawEllipse(16, 16, 10, 10)
        p.setBrush(QColor("#0b1220"))
        p.setPen(Qt.NoPen)
        p.drawEllipse(20, 20, 3, 3)

        # Cross slash when hidden
        if crossed:
            p.setPen(QPen(white, 3.0))
            p.setBrush(Qt.NoBrush)
            p.drawLine(8, 34, 34, 8)

        p.end()
        return QIcon(pix)

    dialog = QDialog()
    dialog.setWindowTitle("Đăng nhập hệ thống")
    dialog.setFixedSize(460, 420)
    layout = QVBoxLayout(dialog)
    layout.setContentsMargins(18, 18, 18, 18)
    layout.setSpacing(12)

    card = QFrame()
    card.setObjectName("loginCard")
    card_lay = QVBoxLayout(card)
    card_lay.setContentsMargins(22, 22, 22, 22)
    card_lay.setSpacing(10)

    logo_lbl = QLabel()
    logo_lbl.setObjectName("loginLogo")
    logo_lbl.setAlignment(Qt.AlignCenter)
    logo_pix = QPixmap(str(PROJECT_ROOT / "assets" / "images" / "logo-removebg-preview.png"))
    if not logo_pix.isNull():
        logo_lbl.setPixmap(logo_pix.scaled(280, 130, Qt.KeepAspectRatio, Qt.SmoothTransformation))
    else:
        logo_lbl.setText("PROCARE")
    card_lay.addWidget(logo_lbl)

    lbl = QLabel("ĐĂNG NHẬP HỆ THỐNG")
    lbl.setObjectName("loginTitle")
    lbl.setAlignment(Qt.AlignCenter)
    card_lay.addWidget(lbl)

    subtitle = QLabel("Sử dụng tài khoản Quản lý hoặc Lễ tân để tiếp tục")
    subtitle.setObjectName("loginSubtitle")
    subtitle.setAlignment(Qt.AlignCenter)
    card_lay.addWidget(subtitle)

    txt_user = QLineEdit()
    txt_user.setPlaceholderText("Tên đăng nhập")
    txt_pass = QLineEdit()
    txt_pass.setPlaceholderText("Mật khẩu")
    txt_pass.setEchoMode(QLineEdit.Password)
    btn_toggle_pwd = QToolButton(txt_pass)
    btn_toggle_pwd.setObjectName("btnTogglePwd")
    btn_toggle_pwd.setCursor(Qt.PointingHandCursor)
    btn_toggle_pwd.setIcon(_eye_icon(crossed=False))
    btn_toggle_pwd.setIconSize(QSize(24, 24))
    btn_toggle_pwd.setFixedSize(30, 30)
    btn_toggle_pwd.setToolTip("Ẩn/hiện mật khẩu")
    btn_toggle_pwd.setStyleSheet("""
        QToolButton#btnTogglePwd {
            border: none;
            background: transparent;
            padding: 0;
        }
        QToolButton#btnTogglePwd:hover {
            background: rgba(56, 189, 248, 0.15);
            border-radius: 15px;
        }
    """)
    txt_pass.setTextMargins(0, 0, 36, 0)

    def _position_pwd_button():
        x = txt_pass.width() - btn_toggle_pwd.width() - 6
        y = (txt_pass.height() - btn_toggle_pwd.height()) // 2
        btn_toggle_pwd.move(max(0, x), max(0, y))

    _orig_resize_event = txt_pass.resizeEvent

    def _patched_resize_event(event):
        _orig_resize_event(event)
        _position_pwd_button()

    txt_pass.resizeEvent = _patched_resize_event
    _position_pwd_button()
    lbl_error = QLabel("")
    lbl_error.setObjectName("loginError")
    lbl_error.setVisible(False)
    btn_login = QPushButton("ĐĂNG NHẬP")
    card_lay.addWidget(txt_user)
    card_lay.addWidget(txt_pass)
    card_lay.addWidget(lbl_error)
    card_lay.addSpacing(8)
    card_lay.addWidget(btn_login)
    layout.addWidget(card)
    dialog.setStyleSheet("""
        QDialog { background-color: #0b1220; color: #dbeafe; }
        QFrame#loginCard {
            background: #111827;
            border: 1px solid #334155;
            border-radius: 14px;
        }
        QLabel#loginLogo {
            border: none;
            background: transparent;
            padding: 0;
        }
        QLabel#loginTitle { color: #f8fafc; font-size: 24px; font-weight: 800; }
        QLabel#loginSubtitle { color: #94a3b8; font-size: 12px; }
        QLabel#loginError {
            color: #fca5a5;
            background: #2b1220;
            border: 1px solid #7f1d1d;
            border-radius: 8px;
            padding: 6px 10px;
            font-weight: 600;
        }
        QLineEdit {
            background:#0f172a;
            color:#e2e8f0;
            border:1px solid #334155;
            border-radius:8px;
            padding:10px 12px;
            min-height:20px;
            font-size: 16px;
            font-weight: 600;
        }
        QLineEdit:focus { border:1px solid #38bdf8; }
        QPushButton { background:#0ea5e9; color:#f8fafc; border:1px solid #38bdf8; border-radius:10px; font-weight:700; min-height:42px; }
        QPushButton:hover { background:#0284c7; }
    """)
    accounts = _load_auth_accounts()
    auth = {"user": None}

    def do_login():
        lbl_error.setVisible(False)
        username = txt_user.text().strip()
        password = txt_pass.text().strip()
        for acc in accounts:
            if acc.get("username") == username and acc.get("password") == password:
                role = acc.get("role", "Lễ tân")
                if role not in ("Quản lý", "Lễ tân"):
                    role = "Lễ tân"
                auth["user"] = {"username": username, "role": role}
                append_audit_log("auth.login_success", username, {"role": role})
                dialog.accept()
                return
        append_audit_log("auth.login_failed", username or "unknown", {})
        lbl_error.setText("Sai tên đăng nhập hoặc mật khẩu.")
        lbl_error.setVisible(True)

    btn_login.clicked.connect(do_login)
    def toggle_password():
        if txt_pass.echoMode() == QLineEdit.Password:
            txt_pass.setEchoMode(QLineEdit.Normal)
            btn_toggle_pwd.setIcon(_eye_icon(crossed=True))
        else:
            txt_pass.setEchoMode(QLineEdit.Password)
            btn_toggle_pwd.setIcon(_eye_icon(crossed=False))

    btn_toggle_pwd.clicked.connect(toggle_password)
    txt_user.returnPressed.connect(do_login)
    txt_pass.returnPressed.connect(do_login)
    if dialog.exec_() != QDialog.Accepted:
        return None
    return auth["user"]


if __name__ == "__main__":
    main()