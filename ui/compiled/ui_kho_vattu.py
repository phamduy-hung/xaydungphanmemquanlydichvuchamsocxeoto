import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from PyQt5.QtWidgets import *
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QIntValidator

from modules.kho_vattu.ql_vattu import QuanLyVatTu
from modules.kho_vattu.ton_kho import TonKho
from modules.kho_vattu.nhap_kho import NhapKho
from database.models import get_low_stock_products


# ======================
# UI
# ======================
class KhoVatTuUI(QWidget):
    def __init__(self):
        super().__init__()
        self.ql_vattu = QuanLyVatTu()
        self.ton_kho = TonKho()
        self.nhap_kho_handler = NhapKho()

        self.setWindowTitle("Quản lý kho & vật tư")
        self.resize(1000, 600)

        self.layout = QVBoxLayout()
        self.setLayout(self.layout)

        # ===== TOP BAR =====
        top_layout = QHBoxLayout()

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Tìm vật tư...")
        self.search_input.textChanged.connect(self.tim_kiem)
        top_layout.addWidget(self.search_input)

        btn_refresh = QPushButton("Làm mới")
        btn_refresh.clicked.connect(self.load_data)
        top_layout.addWidget(btn_refresh)

        top_layout.addStretch()

        btn_add = QPushButton("Thêm sản phẩm")
        btn_add.clicked.connect(self.them_san_pham)
        top_layout.addWidget(btn_add)

        self.layout.addLayout(top_layout)

        # ===== TABLE =====
        self.table = QTableWidget()
        self.table.setColumnCount(7)
        self.table.setHorizontalHeaderLabels(["ID", "Mã SP", "Tên", "Loại", "Đơn vị", "Giá", "Tồn"])
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

        btn_edit = QPushButton("Sửa sản phẩm")
        btn_edit.clicked.connect(self.sua_san_pham)
        btn_layout.addWidget(btn_edit)

        btn_delete = QPushButton("Xóa sản phẩm")
        btn_delete.clicked.connect(self.xoa_san_pham)
        btn_layout.addWidget(btn_delete)

        btn_layout.addStretch()

        btn_report = QPushButton("Báo cáo")
        btn_report.clicked.connect(self.xem_bao_cao)
        btn_layout.addWidget(btn_report)

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
        try:
            if data is None:
                data = self.ql_vattu.danh_sach()

            # Check if data is valid
            if not data or not isinstance(data, list):
                QMessageBox.warning(self, "Lỗi", "Không thể tải dữ liệu sản phẩm từ database!")
                return

            self.table.setRowCount(len(data))

            # Get stock info
            stock_info = self.ton_kho.xem_ton()
            if not stock_info or not isinstance(stock_info, list):
                stock_info = []

            for row, vt in enumerate(data):
                self.table.setItem(row, 0, QTableWidgetItem(str(vt["id"])))
                self.table.setItem(row, 1, QTableWidgetItem(f"VT{vt['id']:03d}"))  # Simple code
                self.table.setItem(row, 2, QTableWidgetItem(vt["ten"]))
                self.table.setItem(row, 3, QTableWidgetItem(vt["loai"]))
                self.table.setItem(row, 4, QTableWidgetItem(vt["don_vi"]))
                self.table.setItem(row, 5, QTableWidgetItem(f"{vt['gia']:,.0f} VND"))

                # Get current stock
                current_stock = 0
                for name, stock in stock_info:
                    if name == vt["ten"]:
                        current_stock = stock
                        break

                item = QTableWidgetItem(str(current_stock))
                if current_stock <= vt["min"]:
                    item.setBackground(Qt.red)
                self.table.setItem(row, 6, item)

            self.check_warning()
        except Exception as e:
            QMessageBox.critical(self, "Lỗi", f"Lỗi khi tải dữ liệu: {str(e)}")

    # ======================
    # SEARCH
    # ======================
    def tim_kiem(self):
        try:
            keyword = self.search_input.text().strip()
            if keyword:
                result = self.ql_vattu.tim_kiem(keyword)
            else:
                result = self.ql_vattu.danh_sach()

            if result is False or not isinstance(result, list):
                QMessageBox.warning(self, "Lỗi", "Không thể tìm kiếm sản phẩm!")
                return

            self.load_data(result)
        except Exception as e:
            QMessageBox.critical(self, "Lỗi", f"Lỗi khi tìm kiếm: {str(e)}")

    # ======================
    # ADD PRODUCT
    # ======================
    def them_san_pham(self):
        dialog = ProductDialog()
        if dialog.exec_() == QDialog.Accepted:
            data = dialog.get_data()
            try:
                self.ql_vattu.them(data["ten"], data["loai"], data["don_vi"], data["gia"], data["min"])
                self.load_data()
                QMessageBox.information(self, "Thành công", "Đã thêm sản phẩm!")
            except Exception as e:
                QMessageBox.warning(self, "Lỗi", str(e))

    # ======================
    # EDIT PRODUCT
    # ======================
    def sua_san_pham(self):
        row = self.table.currentRow()
        if row < 0:
            QMessageBox.warning(self, "Lỗi", "Chọn sản phẩm cần sửa!")
            return

        product_id = int(self.table.item(row, 0).text())
        product = self.ql_vattu.lay_theo_id(product_id)
        if not product:
            QMessageBox.warning(self, "Lỗi", "Không tìm thấy sản phẩm!")
            return

        dialog = ProductDialog(product)
        if dialog.exec_() == QDialog.Accepted:
            data = dialog.get_data()
            try:
                self.ql_vattu.sua(product_id, data["ten"], data["loai"], data["don_vi"], data["gia"], data["min"])
                self.load_data()
                QMessageBox.information(self, "Thành công", "Đã cập nhật sản phẩm!")
            except Exception as e:
                QMessageBox.warning(self, "Lỗi", str(e))

    # ======================
    # DELETE PRODUCT
    # ======================
    def xoa_san_pham(self):
        row = self.table.currentRow()
        if row < 0:
            QMessageBox.warning(self, "Lỗi", "Chọn sản phẩm cần xóa!")
            return

        product_id = int(self.table.item(row, 0).text())
        reply = QMessageBox.question(self, "Xác nhận", "Bạn có chắc muốn xóa sản phẩm này?",
                                   QMessageBox.Yes | QMessageBox.No)
        if reply == QMessageBox.Yes:
            try:
                self.ql_vattu.xoa(product_id)
                self.load_data()
                QMessageBox.information(self, "Thành công", "Đã xóa sản phẩm!")
            except Exception as e:
                QMessageBox.warning(self, "Lỗi", str(e))

    # ======================
    # IMPORT STOCK
    # ======================
    def nhap_kho(self):
        row = self.table.currentRow()
        if row < 0:
            QMessageBox.warning(self, "Lỗi", "Chọn sản phẩm cần nhập kho!")
            return

        product_id = int(self.table.item(row, 0).text())

        so_luong, ok = QInputDialog.getInt(self, "Nhập kho", "Số lượng:", min=1)
        if ok and so_luong > 0:
            try:
                self.nhap_kho_handler.nhap(product_id, so_luong)
                self.load_data()
                QMessageBox.information(self, "Thành công", f"Đã nhập {so_luong} sản phẩm!")
            except Exception as e:
                QMessageBox.warning(self, "Lỗi", str(e))

    # ======================
    # REPORT
    # ======================
    def xem_bao_cao(self):
        from modules.kho_vattu.bao_cao import BaoCaoKho
        bao_cao = BaoCaoKho()

        nhap = bao_cao.thong_ke_nhap()
        xuat = bao_cao.thong_ke_xuat()

        msg = "=== BÁO CÁO KHO ===\n\n"
        msg += "NHẬP KHO:\n"
        for pid, qty in nhap:
            msg += f"- Sản phẩm {pid}: {qty}\n"

        msg += "\nXUẤT KHO:\n"
        for pid, qty in xuat:
            msg += f"- Sản phẩm {pid}: {qty}\n"

        QMessageBox.information(self, "Báo cáo kho", msg)

    # ======================
    # WARNING
    # ======================
    def check_warning(self):
        try:
            warnings = self.ton_kho.canh_bao_ton_thap()
            if warnings and isinstance(warnings, list):
                warning_text = "⚠️ Sắp hết: " + ", ".join([f"{name} ({stock}/{min_stock})" for name, stock, min_stock in warnings])
                self.warning_label.setText(warning_text)
            else:
                self.warning_label.setText("✅ Tất cả sản phẩm đủ tồn kho")
        except Exception as e:
            self.warning_label.setText(f"❌ Lỗi kiểm tra tồn kho: {str(e)}")


class ProductDialog(QDialog):
    def __init__(self, product=None):
        super().__init__()
        self.product = product
        self.setWindowTitle("Thêm/Sửa sản phẩm")
        self.resize(400, 300)

        layout = QVBoxLayout()
        self.setLayout(layout)

        # Name
        layout.addWidget(QLabel("Tên sản phẩm:"))
        self.name_input = QLineEdit()
        if product:
            self.name_input.setText(product["ten"])
        layout.addWidget(self.name_input)

        # Category
        layout.addWidget(QLabel("Loại:"))
        self.category_input = QComboBox()
        self.category_input.addItems(["Dung dịch", "Phụ tùng", "Công cụ", "Khác"])
        if product:
            index = self.category_input.findText(product["loai"])
            if index >= 0:
                self.category_input.setCurrentIndex(index)
        layout.addWidget(self.category_input)

        # Unit
        layout.addWidget(QLabel("Đơn vị:"))
        self.unit_input = QComboBox()
        self.unit_input.addItems(["Cái", "Chai", "Lít", "Kg", "Thùng"])
        if product:
            index = self.unit_input.findText(product["don_vi"])
            if index >= 0:
                self.unit_input.setCurrentIndex(index)
        layout.addWidget(self.unit_input)

        # Price
        layout.addWidget(QLabel("Giá (VND):"))
        self.price_input = QLineEdit()
        self.price_input.setValidator(QIntValidator(0, 999999999))
        if product:
            self.price_input.setText(str(int(product["gia"])))
        layout.addWidget(self.price_input)

        # Min stock
        layout.addWidget(QLabel("Tồn tối thiểu:"))
        self.min_stock_input = QLineEdit()
        self.min_stock_input.setValidator(QIntValidator(0, 999999))
        if product:
            self.min_stock_input.setText(str(product["min"]))
        else:
            self.min_stock_input.setText("10")
        layout.addWidget(self.min_stock_input)

        # Buttons
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        btn_cancel = QPushButton("Hủy")
        btn_cancel.clicked.connect(self.reject)
        btn_layout.addWidget(btn_cancel)

        btn_save = QPushButton("Lưu")
        btn_save.clicked.connect(self.accept)
        btn_layout.addWidget(btn_save)

        layout.addLayout(btn_layout)

    def get_data(self):
        return {
            "ten": self.name_input.text().strip(),
            "loai": self.category_input.currentText(),
            "don_vi": self.unit_input.currentText(),
            "gia": int(self.price_input.text() or 0),
            "min": int(self.min_stock_input.text() or 0)
        }


# ======================
# RUN
# ======================
if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = KhoVatTuUI()
    window.show()
    sys.exit(app.exec_())
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