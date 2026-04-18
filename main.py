import inspect
import sys
from pathlib import Path

from PyQt5.QtCore import QTimer
from PyQt5.QtWidgets import QApplication, QMainWindow, QMessageBox, QWidget, QPushButton

PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from ui.compiled.ui_trangchu import Ui_MainWindow

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

BaoCaoWindow = None


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)
        self.setStyleSheet("") # Clear local UI stylesheet to use global


        self.btn_login = getattr(self.ui, "btnLogin", None)
        self.btn_logout = getattr(self.ui, "btnLogout", None)

        if self.btn_login:
            self.btn_login.setStyleSheet("")
        if self.btn_logout:
            self.btn_logout.setStyleSheet("")

        # Nếu UI không còn nút đăng nhập thì cho phép dùng chức năng luôn
        self.auth_required = self.btn_login is not None
        self.is_logged_in = not self.auth_required
        self.child_windows = {}

        self.feature_handlers = {
            "btn_lichhen_tiepnhan": self.open_appointment_module,
            "btn_banhang_thanhtoan": self.open_pos_module,
            "btn_crm_khachhang": self.open_crm_module,
            "btn_kho_vattu": self.open_inventory_module,
            "btn_nhansu_nangsuat": self.open_staff_module,
            "btn_customer_care": self.open_customer_care_module,
            "btn_baocao_thongke": self.open_report_module,
            "btn_hethong_caidat": self.open_settings_module,
        }

        self._setup_signals()
        self._update_auth_ui()
        self.statusBar().showMessage("Sẵn sàng.")

        # Badge polling: hiển thị số đơn pending trên nút lịch hẹn
        self._badge_timer = QTimer(self)
        self._badge_timer.timeout.connect(self._update_badge)
        self._badge_timer.start(6000)   # 6 giây
        self._update_badge()            # Lần đầu ngay lập tức

    def _setup_signals(self):
        if self.btn_login is not None:
            self.btn_login.clicked.connect(self.handle_login)
        if self.btn_logout is not None:
            self.btn_logout.clicked.connect(self.handle_logout)

        for button_name, handler in self.feature_handlers.items():
            button = getattr(self.ui, button_name, None)
            if button is not None:
                button.clicked.connect(handler)

    def _update_auth_ui(self):
        if self.btn_login is not None:
            self.btn_login.setEnabled(not self.is_logged_in)
        if self.btn_logout is not None:
            self.btn_logout.setEnabled(self.is_logged_in)

        if not self.auth_required:
            self.statusBar().showMessage("Che do khong yeu cau dang nhap.")
        elif self.is_logged_in:
            self.statusBar().showMessage("Dang nhap thanh cong. Ban co the su dung cac chuc nang.")
        else:
            self.statusBar().showMessage("Chua dang nhap. Vui long dang nhap de su dung day du chuc nang.")

    def _require_login(self, feature_label):
        if not self.auth_required:
            return True
        if self.is_logged_in:
            return True

        QMessageBox.warning(
            self,
            "Yeu cau dang nhap",
            f"Vui long dang nhap truoc khi mo chuc nang: {feature_label}.",
        )
        return False

    def _show_placeholder(self, feature_label):
        if not self._require_login(feature_label):
            return
        QMessageBox.information(
            self,
            "Thong bao",
            f"Chuc nang '{feature_label}' dang duoc phat trien.\n"
            "Ban co the mo CRM de thu nghiem luong quan ly khach hang.",
        )

    def handle_login(self):
        if not self.auth_required:
            return
        if self.is_logged_in:
            return
        self.is_logged_in = True
        self._update_auth_ui()
        QMessageBox.information(self, "Dang nhap", "Dang nhap thanh cong.")

    def handle_logout(self):
        if not self.auth_required:
            QMessageBox.information(self, "Dang xuat", "UI hien tai khong su dung che do dang nhap.")
            return
        if not self.is_logged_in:
            return

        reply = QMessageBox.question(
            self,
            "Dang xuat",
            "Ban co chac chan muon dang xuat?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if reply != QMessageBox.Yes:
            return

        self.is_logged_in = False
        self._update_auth_ui()
        QMessageBox.information(self, "Dang xuat", "Da dang xuat thanh cong.")

    def _update_badge(self):
        """Cập nhật badge số đơn web đang pending trên nút trang chủ."""
        if not WEB_BOOKINGS_AVAILABLE:
            return
        btn = getattr(self.ui, "btn_lichhen_tiepnhan", None)
        if btn is None:
            return
        try:
            result = _http_get("http://localhost:8765/api/bookings/count/pending")
            if result and isinstance(result, dict):
                count = result.get("count", 0)
                if count > 0:
                    btn.setText(f"Mở chức năng  🔔{count}")
                    btn.setStyleSheet("""
                        QPushButton {
                            background-color: #f59e0b;
                            color: #0f172a;
                            font-weight: bold;
                            border-radius: 10px;
                            padding: 10px 20px;
                            font-size: 11.5pt;
                        }
                        QPushButton:hover { background-color: #d97706; }
                    """)
                else:
                    btn.setText("Mở chức năng")
                    btn.setStyleSheet("")
        except Exception:
            pass

    def open_appointment_module(self):
        feature_label = "Lịch hẹn & Đặt lịch Online"
        if not self._require_login(feature_label):
            return

        if not WEB_BOOKINGS_AVAILABLE:
            QMessageBox.critical(
                self, "Lỗi module",
                "Không thể tải module Đặt lịch.\nKiểm tra file modules/web_bookings.py."
            )
            return

        window = self.child_windows.get("web_bookings")
        crm_widget = self.child_windows.get("crm")

        if window is None:
            window = WebBookingsWidget(crm_widget=crm_widget)
            window.setWindowTitle("🌐 Đặt lịch Online từ Website")
            self.child_windows["web_bookings"] = window

        window.show()
        window.raise_()
        window.activateWindow()
        self.statusBar().showMessage("Đã mở module Lịch hẹn & Đặt lịch Online.")

    def open_pos_module(self):
        self._show_placeholder("Ban hang & Thanh toan (POS)")

    def open_crm_module(self):
        feature_label = "Quan ly Khach hang (CRM)"
        if not self._require_login(feature_label):
            return

        if CustomerManagerWidget is None:
            QMessageBox.critical(
                self,
                "Loi module",
                "Khong the tai module CRM.\nKiem tra lai file modules/qlkhachhang.py.",
            )
            return

        window = self.child_windows.get("crm")
        if window is None:
            window = CustomerManagerWidget()
            window.setWindowTitle("CRM - Quan ly khach hang")
            self.child_windows["crm"] = window

        window.show()
        window.raise_()
        window.activateWindow()
        self.statusBar().showMessage("Da mo module CRM.")

    def open_inventory_module(self):
        feature_label = "Quan ly Kho & Vat tu"
        if not self._require_login(feature_label):
            return
        try:
            from ui.compiled.ui_kho_vattu import KhoVatTuUI
        except ImportError:
            QMessageBox.information(
                self,
                "Thong bao",
                f"Chuc nang '{feature_label}' dang duoc phat trien.\n"
                "Ban co the mo CRM de thu nghiem luong quan ly khach hang.",
            )
            return

        window = self.child_windows.get("kho")
        if window is None:
            window = KhoVatTuUI()
            self.child_windows["kho"] = window

        window.show()
        window.raise_()
        window.activateWindow()
        self.statusBar().showMessage("Da mo module Kho & Vat tu.")

    def open_staff_module(self):
        self._show_placeholder("Quan ly Nhan su & Nang suat")

    def open_customer_care_module(self):
        self._show_placeholder("Cham soc KH & Marketing")

    def open_report_module(self):
        global BaoCaoWindow
        feature_label = "Bao cao & Thong ke"
        if not self._require_login(feature_label):
            return

        if BaoCaoWindow is None:
            try:
                from modules import baocao_thongke as baocao_module
                candidate_names = (
                    "BaoCaoWindow",
                    "BaoCaoThongKeWindow",
                    "ReportWindow",
                )
                for name in candidate_names:
                    candidate = getattr(baocao_module, name, None)
                    if inspect.isclass(candidate) and issubclass(candidate, QWidget):
                        BaoCaoWindow = candidate
                        break
            except ModuleNotFoundError as exc:
                QMessageBox.critical(
                    self,
                    "Thieu thu vien",
                    f"Khong mo duoc Bao cao & Thong ke do thieu thu vien: {exc.name}\n"
                    f"Hay cai dat bang lenh: pip install {exc.name}",
                )
                return
            except Exception as exc:
                QMessageBox.critical(
                    self,
                    "Loi module",
                    f"Khong the tai module Bao cao & Thong ke.\nChi tiet: {exc}",
                )
                return

        if BaoCaoWindow is None:
            QMessageBox.information(
                self,
                "Thong bao",
                "Module Bao cao & Thong ke da duoc nap, nhung chua co class giao dien.\n"
                "Vui long tao class QWidget (vi du: BaoCaoWindow) trong modules/baocao_thongke.py.",
            )
            return

        window = self.child_windows.get("report")
        if window is None:
            window = BaoCaoWindow()
            window.setWindowTitle("Bao cao & Thong ke")
            self.child_windows["report"] = window

        window.show()
        window.raise_()
        window.activateWindow()
        self.statusBar().showMessage("Da mo module Bao cao & Thong ke.")

    def open_settings_module(self):
        self._show_placeholder("Quan ly He thong & Cai dat")


app_style = """
/* Tối ưu hóa UI theo phong cách Dark Mode Hiện đại cao cấp (Modern Dark Premium Mode) */
QMainWindow, QWidget#centralwidget {
    background-color: #0b1120; /* Nền tối đậm, cực sâu (Ultra-deep slate) */
}
QWidget {
    font-family: "Segoe UI", "Inter", sans-serif;
    color: #f8fafc;
    font-size: 10.5pt;
}

/* Vùng Header thanh lịch */
#headerFrame {
    background-color: rgba(30, 41, 59, 0.7); /* Kính bóng mờ (Glassmorphism effect) */
    border: 1px solid #334155;
    border-radius: 16px;
    padding: 4px;
}

#headerFrame:hover {
    border-color: #475569;
}

/* Label Logo cực bắt mắt */
#logoLabel {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #38bdf8, stop:1 #818cf8);
    color: #ffffff;
    border-radius: 28px;
    font-size: 24px;
    font-weight: 800;
}

/* Tên ứng dụng nổi bật */
#appName {
    color: #f8fafc;
    font-size: 24px;
    font-weight: 900;
    border: none;
    letter-spacing: 1px;
}

#appDesc {
    color: #94a3b8;
    font-size: 11.5pt;
    border: none;
}

/* Các QFrame (Thẻ Card) */
QFrame {
    background-color: #1e293b;
    border: 1px solid #334155;
    border-radius: 16px;
}

/* Hiệu ứng nổi bật khi Hover vào Card */
QFrame:hover {
    border: 1px solid #38bdf8;
    background-color: #26334a;
}

/* Nhãn Text không bị ghi đè màu nền */
QLabel {
    border: none;
    background: transparent;
}

/* Tiêu đề Chức năng (Card Title) */
QLabel[objectName^="lblTitle"] {
    color: #f1f5f9;
    font-size: 15pt;
    font-weight: bold;
}

/* Mô tả Chức năng (Card Description) */
QLabel[objectName^="lblDesc"] {
    color: #94a3b8;
    font-size: 11pt;
    line-height: 1.5;
}

/* Nút bấm (Button) thiết kế cao cấp, bo góc thanh lịch */
QPushButton {
    background-color: #2563eb;
    color: #ffffff;
    border: none;
    border-radius: 10px;
    font-weight: bold;
    padding: 10px 20px;
    font-size: 11.5pt;
}

QPushButton:hover {
    background-color: #3b82f6;
}

QPushButton:pressed {
    background-color: #1d4ed8;
}

/* Nút Đăng xuất riêng biệt */
#btnLogout, #btn_logout {
    background-color: rgba(239, 68, 68, 0.85); /* Đỏ nổi bật */
    color: white;
    border-radius: 8px;
    font-weight: bold;
}
#btnLogout:hover, #btn_logout:hover {
    background-color: #f87171;
}
#btnLogout:pressed, #btn_logout:pressed {
    background-color: #b91c1c;
}

/* Dòng trạng thái (Status Bar) */
QStatusBar {
    background-color: #0b1120;
    color: #94a3b8;
    border-top: 1px solid #1e293b;
}

/* Footer chữ rõ ràng nhưng nhẹ nhàng */
#footerText {
    color: #64748b;
    font-size: 10.5pt;
    font-weight: 500;
}

/* Bảng dữ liệu CRM & Kho: Glass + Flat mix */
QTableWidget, QTableView {
    background-color: #1e293b;
    border: 1px solid #334155;
    border-radius: 12px;
    color: #f1f5f9;
    gridline-color: #334155;
    selection-background-color: #38bdf8;
    selection-color: #0f172a;
    alternate-background-color: #223044;
}
QTableView::item {
    padding: 4px;
}
QHeaderView::section {
    background-color: #0f172a;
    color: #94a3b8;
    padding: 10px;
    border: none;
    border-right: 1px solid #334155;
    border-bottom: 2px solid #334155;
    font-weight: bold;
    font-size: 11pt;
}

/* Các Ô nhập liệu (Input/Combo boxes) thiết kế phẳng */
QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox, QDateEdit, QTextEdit {
    background-color: #0f172a;
    border: 1px solid #334155;
    border-radius: 8px;
    padding: 8px;
    color: #f1f5f9;
    font-size: 11pt;
}
QLineEdit:focus, QComboBox:focus, QSpinBox:focus, QDoubleSpinBox:focus, QDateEdit:focus, QTextEdit:focus {
    border: 1px solid #38bdf8;
    background-color: #1e293b;
}

/* Danh sách cuộn mượt mà (Modern Scrollbar) */
QScrollBar:vertical {
    border: none;
    background: #0f172a;
    width: 6px;
    margin: 0px;
    border-radius: 3px;
}
QScrollBar::handle:vertical {
    background: #475569;
    min-height: 25px;
    border-radius: 3px;
}
QScrollBar::handle:vertical:hover {
    background: #94a3b8;
}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    border: none;
    background: none;
}
QScrollBar:horizontal {
    border: none;
    background: #0f172a;
    height: 6px;
    margin: 0px;
    border-radius: 3px;
}
QScrollBar::handle:horizontal {
    background: #475569;
    min-width: 25px;
    border-radius: 3px;
}
QScrollBar::handle:horizontal:hover {
    background: #94a3b8;
}
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
    border: none;
    background: none;
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