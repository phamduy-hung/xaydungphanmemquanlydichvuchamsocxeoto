import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from PyQt5.QtWidgets import (QApplication, QMainWindow, QMessageBox, QWidget, 
                             QPushButton, QVBoxLayout, QHBoxLayout, QStackedWidget,
                             QFrame, QLabel)
from PyQt5.QtCore import Qt, QTimer

try:
    from modules.qlkhachhang import CustomerManagerWidget
except Exception:
    CustomerManagerWidget = None

try:
    from modules.web_bookings import WebBookingsWidget, _http_get
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

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("PROCARE - Premium AutoCare System")
        self.resize(1400, 850)
        self.auth_required = False
        self.is_logged_in = True
        self.child_windows = {}

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Build Sidebar
        self.sidebar = QFrame()
        self.sidebar.setObjectName("sidebar")
        self.sidebar.setFixedWidth(280)
        self.sidebar.setStyleSheet("""
            #sidebar {
                background-color: #ffffff;
                border-right: 1px solid #e2e8f0;
            }
        """)
        sidebar_layout = QVBoxLayout(self.sidebar)
        sidebar_layout.setContentsMargins(20, 35, 20, 30)

        brand_lbl = QLabel("ProCare")
        brand_lbl.setStyleSheet("color: #10b981; font-size: 28pt; font-weight: 900;")
        brand_lbl.setAlignment(Qt.AlignCenter)
        sidebar_layout.addWidget(brand_lbl)
        
        sub_lbl = QLabel("HỆ THỐNG AUTOCARE")
        sub_lbl.setStyleSheet("color: #64748b; font-size: 10pt; font-weight: bold;")
        sub_lbl.setAlignment(Qt.AlignCenter)
        sidebar_layout.addWidget(sub_lbl)
        sidebar_layout.addSpacing(50)

        # Nav Buttons
        self.nav_buttons = []
        self._add_nav_button(sidebar_layout, "📊  TỔNG QUAN", self.show_dashboard)
        self._add_nav_button(sidebar_layout, "📅  ĐẶT LỊCH WEB", self.show_web_bookings)
        self._add_nav_button(sidebar_layout, "👥  KHÁCH HÀNG (CRM)", self.show_crm)
        self._add_nav_button(sidebar_layout, "📦  KHO & VẬT TƯ", self.show_kho_vattu)
        self._add_nav_button(sidebar_layout, "📈  BÁO CÁO THỐNG KÊ", self.show_baocao)
        self._add_nav_button(sidebar_layout, "💰  BÁN HÀNG & POS", self.show_pos)
        self._add_nav_button(sidebar_layout, "⚙️  CÀI ĐẶT HỆ THỐNG", self.show_settings)
        
        sidebar_layout.addStretch()
        
        logout_btn = QPushButton("ĐĂNG XUẤT")
        logout_btn.setObjectName("btnLogout")
        logout_btn.setFixedHeight(45)
        logout_btn.setStyleSheet("""
            QPushButton {
                background-color: #f8fafc;
                border: 1px solid #e2e8f0;
                color: #ef4444;
                font-weight: bold;
                border-radius: 8px;
            }
            QPushButton:hover {
                background-color: #fef2f2;
                border: 1px solid #fca5a5;
                color: #ef4444;
            }
        """)
        sidebar_layout.addWidget(logout_btn)

        # Build Stack
        self.stack = QStackedWidget()
        self.stack.setStyleSheet("background-color: #f1f5f9;")
        
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

        # Page 3: Kho Vat Tu
        self.page_kho = QWidget()
        self.kho_lay = QVBoxLayout(self.page_kho)
        self.kho_lay.setContentsMargins(30, 30, 30, 30)
        self.stack.addWidget(self.page_kho)

        # Page 4: Bao Cao
        self.page_baocao = QWidget()
        self.baocao_lay = QVBoxLayout(self.page_baocao)
        self.baocao_lay.setContentsMargins(30, 30, 30, 30)
        self.stack.addWidget(self.page_baocao)

        # Page 5: POS
        self.page_pos = QWidget()
        self.pos_lay = QVBoxLayout(self.page_pos)
        self.pos_lay.setContentsMargins(30, 30, 30, 30)
        self.stack.addWidget(self.page_pos)

        # Page 6: Settings
        self.page_set = QWidget()
        self.set_lay = QVBoxLayout(self.page_set)
        self.set_lay.setContentsMargins(30, 30, 30, 30)
        self.stack.addWidget(self.page_set)
        
        # Page N: Generic Placeholder
        self.page_placeholder = QWidget()
        self.place_lay = QVBoxLayout(self.page_placeholder)
        self.lbl_place = QLabel("MODULE")
        self.lbl_place.setStyleSheet("color: #64748b; font-size: 22pt; font-weight: bold;")
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
        status_box = QLabel("Admin | Trực tuyến")
        status_box.setStyleSheet("background: #f1f5f9; color: #64748b; font-weight: bold; padding: 8px 18px; border-radius: 20px;")
        h_layout.addWidget(status_box)

        content_layout.addWidget(self.header_bar)
        content_layout.addWidget(self.stack)

        main_layout.addWidget(self.sidebar)
        main_layout.addWidget(self.content_area)

        # Init modules
        self._init_modules()

        # Set default
        self.show_dashboard()

        # Badge polling
        self._badge_timer = QTimer(self)
        self._badge_timer.timeout.connect(self._update_badge)
        self._badge_timer.start(5000)
        self._update_badge()

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
        # Setup Dashboard
        if DashboardWidget:
            self.dashboard_mod = DashboardWidget()
            try: self.dashboard_mod.setWindowFlags(Qt.Widget)
            except: pass
            self.dash_lay.addWidget(self.dashboard_mod)

        # Setup CRM
        if CustomerManagerWidget:
            self.crm = CustomerManagerWidget()
            try:
                self.crm.setWindowFlags(Qt.Widget)
            except:
                pass
            self.crm_lay.addWidget(self.crm)
        
        # Setup Web Bookings
        if WEB_BOOKINGS_AVAILABLE:
            self.web = WebBookingsWidget(crm_widget=getattr(self, 'crm', None))
            try:
                self.web.setWindowFlags(Qt.Widget)
            except:
                pass
            self.web_lay.addWidget(self.web)

        # Setup Kho Vat Tu
        if KhoVatTuUI:
            self.kho = KhoVatTuUI()
            try:
                self.kho.setWindowFlags(Qt.Widget)
            except:
                pass
            self.kho_lay.addWidget(self.kho)

        # Setup Bao Cao
        if BaoCaoWindow:
            self.baocao = BaoCaoWindow()
            try:
                self.baocao.setWindowFlags(Qt.Widget)
            except:
                pass
            self.baocao_lay.addWidget(self.baocao)

        # Setup POS
        if POSWidget:
            self.pos_mod = POSWidget()
            try: self.pos_mod.setWindowFlags(Qt.Widget)
            except: pass
            self.pos_lay.addWidget(self.pos_mod)

        # Setup Settings
        if SettingsWidget:
            self.settings_mod = SettingsWidget()
            try: self.settings_mod.setWindowFlags(Qt.Widget)
            except: pass
            self.set_lay.addWidget(self.settings_mod)


    def show_dashboard(self):
        self._reset_nav()
        if len(self.nav_buttons) > 0: self.nav_buttons[0].setChecked(True)
        self.lbl_page_title.setText("Bảng Tổng Quan")
        self.stack.setCurrentWidget(self.page_dash)

    def show_web_bookings(self):
        self._reset_nav()
        if len(self.nav_buttons) > 1: self.nav_buttons[1].setChecked(True)
        self.lbl_page_title.setText("Đặt Lịch Trực Tuyến")
        if WEB_BOOKINGS_AVAILABLE:
            self.stack.setCurrentWidget(self.page_web)
        else:
            self.show_placeholder("Không tìm thấy module Đặt Lịch Web")

    def show_crm(self):
        self._reset_nav()
        if len(self.nav_buttons) > 2: self.nav_buttons[2].setChecked(True)
        self.lbl_page_title.setText("Quản Lý Khách Hàng")
        if CustomerManagerWidget:
            self.stack.setCurrentWidget(self.page_crm)
        else:
            self.show_placeholder("Không tìm thấy module CRM")

    def show_kho_vattu(self):
        self._reset_nav()
        if len(self.nav_buttons) > 3: self.nav_buttons[3].setChecked(True)
        self.lbl_page_title.setText("Kho & Vật Tư")
        if KhoVatTuUI:
            self.stack.setCurrentWidget(self.page_kho)
        else:
            self.show_placeholder("Không tìm thấy module KHO & VẬT TƯ")

    def show_baocao(self):
        self._reset_nav()
        if len(self.nav_buttons) > 4: self.nav_buttons[4].setChecked(True)
        self.lbl_page_title.setText("Báo Cáo & Thống Kê")
        if BaoCaoWindow:
            self.stack.setCurrentWidget(self.page_baocao)
        else:
            self.show_placeholder("Không tìm thấy module BÁO CÁO THỐNG KÊ")

    def show_pos(self):
        self._reset_nav()
        if len(self.nav_buttons) > 5: self.nav_buttons[5].setChecked(True)
        self.lbl_page_title.setText("Bán Hàng & POS")
        if POSWidget:
            self.stack.setCurrentWidget(self.page_pos)
        else:
            self.show_placeholder("Không tìm thấy module BÁN HÀNG & POS")

    def show_settings(self):
        self._reset_nav()
        if len(self.nav_buttons) > 6: self.nav_buttons[6].setChecked(True)
        self.lbl_page_title.setText("Cài Đặt Hệ Thống")
        if SettingsWidget:
            self.stack.setCurrentWidget(self.page_set)
        else:
            self.show_placeholder("Không tìm thấy module CÀI ĐẶT HỆ THỐNG")

    def show_placeholder(self, title):
        self._reset_nav()
        for b in self.nav_buttons:
            if title in b.text():
                b.setChecked(True)
                break
        self.lbl_place.setText(f"MODULE ĐANG PHÁT TRIỂN:\n\n{title}")
        self.stack.setCurrentWidget(self.page_placeholder)

    def _update_badge(self):
        if not WEB_BOOKINGS_AVAILABLE:
            return
        try:
            from modules.web_bookings import _http_get
            result = _http_get("http://localhost:8765/api/bookings/count/pending")
            if result and isinstance(result, dict):
                count = result.get("count", 0)
                btn = self.nav_buttons[1]  # Web Bookings button
                current_text = btn.text()
                base_text = "   ĐẶT LỊCH WEB"
                if count > 0:
                    btn.setText(f"{base_text}  ({count})")
                    btn.setStyleSheet(btn.styleSheet().replace("color: #94a3b8;", "color: #f59e0b;"))
                else:
                    btn.setText(base_text)
                    btn.setStyleSheet(btn.styleSheet().replace("color: #f59e0b;", "color: #94a3b8;"))
        except Exception:
            pass


app_style = """
/* ========================================================
   PROCARE - Ultra-Premium Modern UI (Emerald Ocean)
   ======================================================== */

QMainWindow {
    background-color: #f8fafc;
}

QWidget {
    font-family: "Geist Sans", "Inter", "Helvetica Neue", "Arial", sans-serif;
    color: #1e293b;
    font-size: 11pt;
}

/* Sidebar Styling */
#sidebar {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #ffffff, stop:1 #f8fafc);
    border-right: 1px solid #e2e8f0;
}

/* Nav Buttons Upgrade */
QPushButton[navButton="true"] {
    background-color: transparent;
    color: #64748b;
    border: none;
    text-align: left;
    padding: 12px 20px;
    font-size: 11pt;
    font-weight: 600;
    border-radius: 10px;
    margin: 2px 0;
}

QPushButton[navButton="true"]:hover {
    background-color: #f1f5f9;
    color: #0ea5e9;
}

QPushButton[navButton="true"]:checked {
    background-color: #0ea5e9;
    color: #ffffff;
    font-weight: 800;
}

/* Unified Top Header */
#topHeaderBar {
    background-color: #ffffff;
    border-bottom: 1px solid #e2e8f0;
}

#lblPageTitle {
    color: #0f172a;
    font-size: 20pt;
    font-weight: 900;
}

/* Global Card & Input Styling */
QFrame#cardFrame, QGroupBox {
    background-color: #ffffff;
    border: 1px solid #e2e8f0;
    border-radius: 16px;
}

QPushButton {
    background-color: #0ea5e9;
    color: white;
    border-radius: 10px;
    padding: 10px 20px;
    font-weight: 700;
}

QPushButton:hover {
    background-color: #0284c7;
}

QTableWidget, QTableView {
    border-radius: 12px;
    border: 1px solid #e2e8f0;
    gridline-color: #f1f5f9;
}

QHeaderView::section {
    background-color: #f8fafc;
    border: none;
    border-bottom: 2px solid #e2e8f0;
    padding: 12px;
    font-weight: 800;
    color: #475569;
}

/* ================= TABS ================= */
QTabWidget::pane {
    border: 1px solid #e2e8f0;
    background-color: #ffffff;
    border-radius: 12px;
}
QTabBar::tab {
    background-color: #f1f5f9;
    color: #64748b;
    padding: 12px 30px;
    font-weight: 700;
    border-top-left-radius: 10px;
    border-top-right-radius: 10px;
    margin-right: 5px;
}
QTabBar::tab:selected {
    background-color: #ffffff;
    color: #0ea5e9;
}

/* ================= INPUTS ================= */
QLineEdit, QComboBox, QDateEdit, QTextEdit {
    background-color: #ffffff;
    border: 1px solid #cbd5e1;
    border-radius: 10px;
    padding: 10px 15px;
    color: #1e293b;
}
QLineEdit:focus, QComboBox:focus, QDateEdit:focus {
    border: 2px solid #0ea5e9;
    background-color: #f0f9ff;
}

/* ================= BUTTONS ================= */
#btn_logout, #btnLogout, #btn_xoaKH {
    background-color: #fef2f2;
    color: #ef4444;
    border: 1px solid #fee2e2;
}
#btn_logout:hover, #btnLogout:hover, #btn_xoaKH:hover {
    background-color: #ef4444;
    color: white;
}

/* ================= SCROLLBARS ================= */
QScrollBar:vertical {
    border: none;
    background: #f8fafc;
    width: 10px;
    border-radius: 5px;
}
QScrollBar::handle:vertical {
    background: #cbd5e1;
    border-radius: 5px;
    min-height: 20px;
}
QScrollBar::handle:vertical:hover {
    background: #94a3b8;
}


"""

def main():
    app = QApplication(sys.argv)
    app.setStyleSheet(app_style)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()