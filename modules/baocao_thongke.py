from PyQt5.QtCore import QDate
from PyQt5.QtWidgets import QMainWindow, QTableWidgetItem

from modules.kho_vattu.data_store import nhap_kho_log, xuat_kho_log
from ui.compiled.ui_baocao_thongke import Ui_MainWindow


class BaoCaoKho:
    def tong_nhap(self):
        result = {}
        for item in nhap_kho_log:
            result[item["vat_tu_id"]] = result.get(item["vat_tu_id"], 0) + item["so_luong"]
        return result

    def tong_xuat(self):
        result = {}
        for item in xuat_kho_log:
            result[item["vat_tu_id"]] = result.get(item["vat_tu_id"], 0) + item["so_luong"]
        return result


class BaoCaoWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)
        self._setup_default_dates()
        self._setup_signals()
        self.show_report_doanh_thu()

    def _setup_default_dates(self):
        today = QDate.currentDate()
        self.ui.date_den_ngay.setDate(today)
        self.ui.date_tu_ngay.setDate(today.addMonths(-1))

    def _setup_signals(self):
        self.ui.btn_doanh_thu.clicked.connect(self.show_report_doanh_thu)
        self.ui.btn_dich_vu.clicked.connect(self.show_report_dich_vu)
        self.ui.btn_nhan_vien.clicked.connect(self.show_report_nhan_vien)

    def _render_table(self, headers, rows):
        table = self.ui.table_report
        table.clear()
        table.setColumnCount(len(headers))
        table.setHorizontalHeaderLabels(headers)
        table.setRowCount(len(rows))

        for row_idx, row_data in enumerate(rows):
            for col_idx, value in enumerate(row_data):
                table.setItem(row_idx, col_idx, QTableWidgetItem(str(value)))
        table.resizeColumnsToContents()

    def show_report_doanh_thu(self):
        rows = [
            ("Rua xe + hut bui", 120, "18.000.000"),
            ("Phu ceramic", 34, "22.100.000"),
            ("Bao duong tong quat", 15, "19.500.000"),
        ]
        self._render_table(["Dich vu", "So luot", "Doanh thu (VND)"], rows)
        self.ui.lbl_summary.setText("Tong doanh thu: 59.600.000 VND")

    def show_report_dich_vu(self):
        rows = [
            ("Rua xe + hut bui", 120),
            ("Phu ceramic", 34),
            ("Ve sinh khoang may", 21),
            ("Danh bong den pha", 17),
        ]
        self._render_table(["Dich vu", "So luot"], rows)
        self.ui.lbl_summary.setText("Tong luot dich vu: 192")

    def show_report_nhan_vien(self):
        rows = [
            ("Minh", 58, "97%"),
            ("Dat", 47, "94%"),
            ("Phuc", 45, "92%"),
            ("Khanh", 42, "90%"),
        ]
        self._render_table(["Nhan vien", "So xe phuc vu", "Hieu suat"], rows)
        self.ui.lbl_summary.setText("So nhan vien co du lieu: 4")