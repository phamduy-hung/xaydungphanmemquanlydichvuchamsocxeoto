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
        self._apply_dark_style()
        
        self._setup_default_dates()
        self._setup_signals()
        self.show_report_doanh_thu()

    def _setup_default_dates(self):
        today = QDate.currentDate()
        self.ui.date_den_ngay.setDate(today)
        self.ui.date_tu_ngay.setDate(today.addMonths(-1))

    def _setup_signals(self):
        for btn in [self.ui.btn_doanh_thu, self.ui.btn_dich_vu, self.ui.btn_nhan_vien]:
            btn.setCheckable(True)
            btn.setAutoExclusive(True)

        self.ui.btn_doanh_thu.clicked.connect(self.show_report_doanh_thu)
        self.ui.btn_dich_vu.clicked.connect(self.show_report_dich_vu)
        self.ui.btn_nhan_vien.clicked.connect(self.show_report_nhan_vien)
        self.ui.btn_doanh_thu.setChecked(True)

    def _apply_dark_style(self):
        self.setStyleSheet("""
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
            QLabel {
                color: #dbeafe;
            }
            #lbl_summary {
                color: #22d3ee;
                font-weight: 800;
            }
            QDateEdit, QComboBox, QLineEdit {
                background-color: #0f172a;
                color: #e2e8f0;
                border: 1px solid #334155;
                border-radius: 8px;
                padding: 6px 10px;
            }
            QPushButton {
                background-color: #1e293b;
                color: #e2e8f0;
                border: 1px solid #334155;
                border-radius: 10px;
                font-weight: 700;
                font-size: 13px;
                padding: 9px 14px;
            }
            QPushButton:hover {
                background-color: #0ea5e9;
                border: 1px solid #38bdf8;
                color: #f8fafc;
            }
            QPushButton:checked {
                background-color: #0284c7;
                border: 1px solid #38bdf8;
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
            QHeaderView::section {
                background-color: #1e293b;
                color: #bae6fd;
                border: 0px;
                padding: 8px;
                font-weight: 700;
            }
        """)

    def _render_table(self, headers, rows):
        table = self.ui.table_report
        table.clear()
        table.setColumnCount(len(headers))
        table.setHorizontalHeaderLabels(headers)
        table.setRowCount(len(rows))
        
        # Make the table fill horizontally and hide vertical headers (row indices)
        from PyQt5.QtWidgets import QHeaderView, QAbstractItemView
        table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        table.verticalHeader().setVisible(False)
        table.setSelectionBehavior(QAbstractItemView.SelectRows)
        table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        table.setAlternatingRowColors(True)

        for row_idx, row_data in enumerate(rows):
            for col_idx, value in enumerate(row_data):
                table.setItem(row_idx, col_idx, QTableWidgetItem(str(value)))
        table.resizeColumnsToContents()

    def show_report_doanh_thu(self):
        rows = [
            ("Rửa xe + hút bụi", 120, "18.000.000"),
            ("Phủ ceramic", 34, "22.100.000"),
            ("Bảo dưỡng tổng quát", 15, "19.500.000"),
        ]
        self._render_table(["Dịch vụ", "Số lượt", "Doanh thu (VND)"], rows)
        self.ui.lbl_summary.setText("Tổng doanh thu: 59.600.000 VND")

    def show_report_dich_vu(self):
        rows = [
            ("Rửa xe + hút bụi", 120),
            ("Phủ ceramic", 34),
            ("Vệ sinh khoang máy", 21),
            ("Đánh bóng đèn pha", 17),
        ]
        self._render_table(["Dịch vụ", "Số lượt"], rows)
        self.ui.lbl_summary.setText("Tổng lượt dịch vụ: 192")

    def show_report_nhan_vien(self):
        rows = [
            ("Minh", 58, "97%"),
            ("Đạt", 47, "94%"),
            ("Phúc", 45, "92%"),
            ("Khánh", 42, "90%"),
        ]
        self._render_table(["Nhân viên", "Số xe phục vụ", "Hiệu suất"], rows)
        self.ui.lbl_summary.setText("Số nhân viên có dữ liệu: 4")