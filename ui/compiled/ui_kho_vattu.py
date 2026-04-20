import sys
from PyQt5.QtWidgets import *
from PyQt5.QtCore import Qt

# ======================
# DATA GIẢ
# ======================
vattu_list = [
    {"id": 1, "ten": "Dầu nhớt Castrol", "loai": "Dung dịch", "don_vi": "Lít", "gia": 120000, "min": 20},
    {"id": 2, "ten": "Nước rửa kính", "loai": "Dung dịch", "don_vi": "Chai", "gia": 50000, "min": 10},
    {"id": 3, "ten": "Lọc gió", "loai": "Phụ tùng", "don_vi": "Cái", "gia": 150000, "min": 5},
]

ton_kho = {1: 50, 2: 5, 3: 2}


# ======================
# UI
# ======================
class KhoVatTuUI(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Quản lý kho & vật tư")
        self.resize(900, 500)

        self.layout = QVBoxLayout()
        self.setLayout(self.layout)

        # ===== TOP BAR =====
        top_layout = QHBoxLayout()

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Tìm vật tư...")
        top_layout.addWidget(self.search_input)

        btn_search = QPushButton("Tìm")
        btn_search.clicked.connect(self.tim_kiem)
        top_layout.addWidget(btn_search)

        self.layout.addLayout(top_layout)

        # ===== TABLE =====
        self.table = QTableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(["ID", "Tên", "Loại", "Tồn"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.verticalHeader().setVisible(False)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.setAlternatingRowColors(True)
        self.layout.addWidget(self.table)

        # ===== BUTTONS =====
        btn_layout = QHBoxLayout()

        btn_nhap = QPushButton("Nhập kho")
        btn_nhap.clicked.connect(self.nhap_kho)
        btn_layout.addWidget(btn_nhap)

        btn_xuat = QPushButton("Xuất kho")
        btn_xuat.clicked.connect(self.xuat_kho)
        btn_layout.addWidget(btn_xuat)

        self.layout.addLayout(btn_layout)

        # ===== WARNING =====
        self.warning_label = QLabel("")
        self.warning_label.setStyleSheet("color: red; font-weight: bold;")
        self.layout.addWidget(self.warning_label)

        self.load_data()

    # ======================
    # LOAD DATA
    # ======================
    def load_data(self, data=None):
        if data is None:
            data = vattu_list

        self.table.setRowCount(len(data))

        for row, vt in enumerate(data):
            self.table.setItem(row, 0, QTableWidgetItem(str(vt["id"])))
            self.table.setItem(row, 1, QTableWidgetItem(vt["ten"]))
            self.table.setItem(row, 2, QTableWidgetItem(vt["loai"]))

            so_luong = ton_kho.get(vt["id"], 0)
            item = QTableWidgetItem(str(so_luong))

            # highlight nếu thấp
            if so_luong < vt["min"]:
                item.setBackground(Qt.red)

            self.table.setItem(row, 3, item)

        self.check_warning()

    # ======================
    # SEARCH
    # ======================
    def tim_kiem(self):
        keyword = self.search_input.text().lower()
        result = [vt for vt in vattu_list if keyword in vt["ten"].lower()]
        self.load_data(result)

    # ======================
    # NHẬP KHO
    # ======================
    def nhap_kho(self):
        row = self.table.currentRow()
        if row < 0:
            return

        vat_tu_id = int(self.table.item(row, 0).text())

        so_luong, ok = QInputDialog.getInt(self, "Nhập kho", "Số lượng:")
        if ok:
            ton_kho[vat_tu_id] = ton_kho.get(vat_tu_id, 0) + so_luong
            self.load_data()

    # ======================
    # XUẤT KHO
    # ======================
    def xuat_kho(self):
        row = self.table.currentRow()
        if row < 0:
            return

        vat_tu_id = int(self.table.item(row, 0).text())

        so_luong, ok = QInputDialog.getInt(self, "Xuất kho", "Số lượng:")
        if ok:
            if ton_kho.get(vat_tu_id, 0) < so_luong:
                QMessageBox.warning(self, "Lỗi", "Không đủ hàng!")
                return

            ton_kho[vat_tu_id] -= so_luong
            self.load_data()

    # ======================
    # CẢNH BÁO
    # ======================
    def check_warning(self):
        warnings = []
        for vt in vattu_list:
            so_luong = ton_kho.get(vt["id"], 0)
            if so_luong < vt["min"]:
                warnings.append(vt["ten"])

        if warnings:
            self.warning_label.setText("⚠️ Sắp hết: " + ", ".join(warnings))
        else:
            self.warning_label.setText("")


# ======================
# RUN
# ======================
if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = KhoVatTuUI()
    window.show()
    sys.exit(app.exec_())