import sys
from pathlib import Path

from PyQt5.QtWidgets import QApplication, QMainWindow, QMessageBox

PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from ui.compiled.ui_trangchu import Ui_MainWindow

try:
    from modules.qlkhachhang import CustomerManagerWidget
except Exception:
    CustomerManagerWidget = None

BaoCaoWindow = None


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)

        self.btn_login = getattr(self.ui, "btnLogin", None)
        self.btn_logout = getattr(self.ui, "btnLogout", None)

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
        self.statusBar().showMessage("San sang.")

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

    def open_appointment_module(self):
        self._show_placeholder("Quan ly Lich hen & Tiep nhan")

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
                from modules.baocao_thongke import BaoCaoWindow as _BaoCaoWindow
                BaoCaoWindow = _BaoCaoWindow
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
            QMessageBox.critical(
                self,
                "Loi module",
                "Khong the tai module Bao cao & Thong ke.\nKiem tra lai file modules/baocao_thongke.py.",
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


def main():
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()