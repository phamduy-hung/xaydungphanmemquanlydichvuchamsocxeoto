import sys
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget,
                             QPushButton, QVBoxLayout, QHBoxLayout, QStackedWidget,
                             QFrame, QLabel)
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QPixmap

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

class MainWindow(QMainWindow):
    def __init__(self):
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
        self._add_nav_button(sidebar_layout, "📊  TỔNG QUAN", self.show_dashboard)
        self._add_nav_button(sidebar_layout, "📅  ĐẶT LỊCH WEB", self.show_web_bookings)
        self._add_nav_button(sidebar_layout, "👥  KHÁCH HÀNG (CRM)", self.show_crm)
        self._add_nav_button(sidebar_layout, "💌  CHĂM SÓC KHÁCH HÀNG", self.show_chamsoc_kh)
        self._add_nav_button(sidebar_layout, "📦  KHO & VẬT TƯ", self.show_kho_vattu)
        self._add_nav_button(sidebar_layout, "📈  BÁO CÁO THỐNG KÊ", self.show_baocao)
        self._add_nav_button(sidebar_layout, "💰  BÁN HÀNG & POS", self.show_pos)
        self._add_nav_button(sidebar_layout, "💼  QUẢN LÝ NHÂN SỰ", self.show_nhan_su)
        self._add_nav_button(sidebar_layout, "⚙️  CÀI ĐẶT HỆ THỐNG", self.show_settings)
        
        sidebar_layout.addStretch()
        
        logout_btn = QPushButton("ĐĂNG XUẤT")
        logout_btn.setObjectName("btnLogout")
        logout_btn.setFixedHeight(45)
        sidebar_layout.addWidget(logout_btn)

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
        self.status_box = QLabel("Admin | Trực tuyến")
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
                border-radius: 16px;
                padding: 6px 14px;
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

    def _add_nav_button(self, layout, text, callback):
        btn = QPushButton(text)
        btn.setProperty("navButton", "true")
        btn.setCheckable(True)
        btn.setFixedHeight(50)
        btn.clicked.connect(callback)
        self.nav_buttons.append(btn)
        layout.addWidget(btn)
        return btn

    def _reset_nav(self):
        for b in self.nav_buttons:
            b.setChecked(False)

    def _init_modules(self):
        self.dashboard_mod = None
        self.crm = None
        self.web = None
        self.kho = None
        self.cskh_marketing = None
        self.baocao = None
        self.pos_mod = None
        self.nhansu_mod = None
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
            self.crm = CustomerManagerWidget()
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
        return self.crm is not None

    def _ensure_web_bookings(self):
        if self.web is None and WEB_BOOKINGS_AVAILABLE:
            self.web = WebBookingsWidget(crm_widget=self.crm)
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
            self.baocao = BaoCaoWindow()
            try:
                self.baocao.setWindowFlags(Qt.Widget)
            except Exception:
                pass
            self.baocao_lay.addWidget(self.baocao)
        return self.baocao is not None

    def _ensure_pos(self):
        if self.pos_mod is None and POSWidget:
            self.pos_mod = POSWidget()
            try:
                self.pos_mod.setWindowFlags(Qt.Widget)
            except Exception:
                pass
            self.pos_lay.addWidget(self.pos_mod)
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
            lambda: self._ensure_deferred("kho", self._ensure_kho),
            lambda: self._ensure_deferred("baocao", self._ensure_baocao),
            lambda: self._ensure_deferred("pos_mod", self._ensure_pos),
            lambda: self._ensure_deferred("nhansu_mod", self._ensure_nhan_su),
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

    def show_crm(self):
        self._last_user_action = time.monotonic()
        self._set_web_polling(False)
        self._reset_nav()
        if len(self.nav_buttons) > 2: self.nav_buttons[2].setChecked(True)
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
        if len(self.nav_buttons) > 3: self.nav_buttons[3].setChecked(True)
        self.lbl_page_title.setText("Chăm Sóc Khách Hàng")
        if ChamSocKhachHangVaMarketingWindow:
            self.stack.setCurrentWidget(self.page_cskh)
            if self.cskh_marketing is None:
                self._ensure_deferred("cskh_marketing", self._ensure_chamsoc_kh)
        else:
            self.show_placeholder("Không tìm thấy module CHĂM SÓC KHÁCH HÀNG")

    def show_kho_vattu(self):
        self._last_user_action = time.monotonic()
        self._set_web_polling(False)
        self._reset_nav()
        if len(self.nav_buttons) > 4: self.nav_buttons[4].setChecked(True)
        self.lbl_page_title.setText("Kho & Vật Tư")
        if KhoVatTuUI:
            self.stack.setCurrentWidget(self.page_kho)
            if self.kho is None:
                self._ensure_deferred("kho", self._ensure_kho)
        else:
            self.show_placeholder("Không tìm thấy module KHO & VẬT TƯ")

    def show_baocao(self):
        self._last_user_action = time.monotonic()
        self._set_web_polling(False)
        self._reset_nav()
        if len(self.nav_buttons) > 5: self.nav_buttons[5].setChecked(True)
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
        if len(self.nav_buttons) > 6: self.nav_buttons[6].setChecked(True)
        self.lbl_page_title.setText("Bán Hàng & POS")
        if POSWidget:
            self.stack.setCurrentWidget(self.page_pos)
            if self.pos_mod is None:
                self._ensure_deferred("pos_mod", self._ensure_pos)
        else:
            self.show_placeholder("Không tìm thấy module BÁN HÀNG & POS")

    def show_settings(self):
        self._last_user_action = time.monotonic()
        self._set_web_polling(False)
        self._reset_nav()
        if len(self.nav_buttons) > 8: self.nav_buttons[8].setChecked(True)
        self.lbl_page_title.setText("Cài Đặt Hệ Thống")
        if SettingsWidget:
            self.stack.setCurrentWidget(self.page_set)
            if self.settings_mod is None:
                self._ensure_deferred("settings_mod", self._ensure_settings)
        else:
            self.show_placeholder("Không tìm thấy module CÀI ĐẶT HỆ THỐNG")

    def show_nhan_su(self):
        self._last_user_action = time.monotonic()
        self._set_web_polling(False)
        self._reset_nav()
        if len(self.nav_buttons) > 7: self.nav_buttons[7].setChecked(True)
        self.lbl_page_title.setText("Quản Lý Nhân Sự")
        if QuanLyNhanVienWidget:
            self.stack.setCurrentWidget(self.page_nhansu)
            if self.nhansu_mod is None:
                self._ensure_deferred("nhansu_mod", self._ensure_nhan_su)
        else:
            self.show_placeholder("Không tìm thấy module QUẢN LÝ NHÂN SỰ")

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
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()