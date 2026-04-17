import sys
from pathlib import Path

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QApplication, QDialog, QMessageBox, QTableWidgetItem, QWidget

# Đảm bảo import được module trong project khi chạy trực tiếp file này
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

# Import đúng theo cấu trúc hiện tại của project
from ui.compiled.ui_qlkhachhang import Ui_Form as Ui_Form_QLKhachHang
from ui.compiled.ui_themkhachhang import Ui_Dialog as Ui_Dialog_ThemKhachHang


class AddCustomerDialog(QDialog):
    def __init__(self, parent=None, customer_data=None):
        super().__init__(parent)
        self.ui = Ui_Dialog_ThemKhachHang()
        self.ui.setupUi(self)

        self.customer_data = customer_data or {}
        self.saved_customer_data = None
        self.is_edit_mode = bool(customer_data)

        if self.is_edit_mode:
            self.setWindowTitle("Sửa thông tin khách hàng")
            self._fill_old_data()
        else:
            self.setWindowTitle("Thêm khách hàng mới")

        self._setup_signals()

    def _setup_signals(self):
        self.ui.btn_save.clicked.connect(self._save_data)
        self.ui.btn_cancel.clicked.connect(self.reject)

    def _fill_old_data(self):
        self.ui.txt_name.setText(self.customer_data.get("ten", ""))
        self.ui.txt_phone.setText(self.customer_data.get("sdt", ""))
        self.ui.txt_plate.setText(self.customer_data.get("bien_so", ""))
        self.ui.txt_note.setPlainText(self.customer_data.get("ghi_chu", ""))

        current_classification = self.customer_data.get("phan_loai", "Khách mới")
        index = self.ui.comboBox.findText(current_classification, Qt.MatchFixedString)
        self.ui.comboBox.setCurrentIndex(index if index >= 0 else 0)

    def _save_data(self):
        ten = self.ui.txt_name.text().strip()
        sdt = self.ui.txt_phone.text().strip()
        bien_so = self.ui.txt_plate.text().strip()
        ghi_chu = self.ui.txt_note.toPlainText().strip()
        phan_loai = self.ui.comboBox.currentText()

        if not ten or not sdt:
            QMessageBox.warning(self, "Thiếu dữ liệu", "Vui lòng nhập Tên khách hàng và Số điện thoại.")
            return

        self.saved_customer_data = {
            "id": self.customer_data.get("id"),
            "ten": ten,
            "sdt": sdt,
            "bien_so": bien_so,
            "phan_loai": phan_loai,
            "tong_chi_tieu": self.customer_data.get("tong_chi_tieu", 0),
            "ghi_chu": ghi_chu,
        }
        self.accept()


class CustomerManagerWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.ui = Ui_Form_QLKhachHang()
        self.ui.setupUi(self)

        self.customers = []
        self.service_history_map = {}
        self.next_customer_id = 1
        self.search_keyword = ""

        self._setup_tables()
        self._seed_demo_data()
        self._setup_signals()
        self.refresh_customer_table()

    def _setup_tables(self):
        customer_table = self.ui.tbl_customers
        customer_table.setSelectionBehavior(customer_table.SelectRows)
        customer_table.setSelectionMode(customer_table.SingleSelection)
        customer_table.setEditTriggers(customer_table.NoEditTriggers)

        history_table = self.ui.tbl_history
        history_table.setSelectionBehavior(history_table.SelectRows)
        history_table.setSelectionMode(history_table.SingleSelection)
        history_table.setEditTriggers(history_table.NoEditTriggers)

    def _setup_signals(self):
        self.ui.btn_themKH.clicked.connect(self.open_add_dialog)
        self.ui.btn_suaKH.clicked.connect(self.open_edit_dialog)
        self.ui.btn_xoaKH.clicked.connect(self.delete_customer)
        self.ui.btn_timkiem.clicked.connect(self.search_customers)
        self.ui.txt_search.returnPressed.connect(self.search_customers)
        self.ui.comboBox.currentIndexChanged.connect(self.refresh_customer_table)
        self.ui.tbl_customers.itemSelectionChanged.connect(self.on_customer_selection_changed)

    def _seed_demo_data(self):
        self._append_customer(
            {
                "ten": "Nguyen Van A",
                "sdt": "0901122334",
                "bien_so": "51A-12345",
                "phan_loai": "Khách mới",
                "tong_chi_tieu": 350000,
                "ghi_chu": "Khách hàng mới, cần tư vấn thêm gói vệ sinh nội thất.",
            }
        )
        self._append_customer(
            {
                "ten": "Tran Thi B",
                "sdt": "0988777666",
                "bien_so": "59G2-88991",
                "phan_loai": "Khách VIP",
                "tong_chi_tieu": 2750000,
                "ghi_chu": "Khách thường xuyên, ưu tiên xếp lịch cuối tuần.",
            }
        )
        self.service_history_map = {
            1: [
                {
                    "ngay": "2026-04-10",
                    "bien_so": "51A-12345",
                    "dich_vu": "Rửa xe + hút bụi",
                    "tong_tien": 150000,
                    "ktv": "Minh",
                },
                {
                    "ngay": "2026-04-15",
                    "bien_so": "51A-12345",
                    "dich_vu": "Phủ ceramic nhanh",
                    "tong_tien": 200000,
                    "ktv": "Dat",
                },
            ],
            2: [
                {
                    "ngay": "2026-03-28",
                    "bien_so": "59G2-88991",
                    "dich_vu": "Bảo dưỡng tổng quát",
                    "tong_tien": 1250000,
                    "ktv": "Khanh",
                },
                {
                    "ngay": "2026-04-12",
                    "bien_so": "59G2-88991",
                    "dich_vu": "Vệ sinh khoang máy",
                    "tong_tien": 1500000,
                    "ktv": "Phuc",
                },
            ],
        }

    def _append_customer(self, data):
        customer = {
            "id": self.next_customer_id,
            "ten": data.get("ten", ""),
            "sdt": data.get("sdt", ""),
            "bien_so": data.get("bien_so", ""),
            "phan_loai": data.get("phan_loai", "Khách mới"),
            "tong_chi_tieu": int(data.get("tong_chi_tieu", 0)),
            "ghi_chu": data.get("ghi_chu", ""),
        }
        self.customers.append(customer)
        self.next_customer_id += 1
        return customer

    def _format_currency(self, value):
        return f"{int(value):,}".replace(",", ".")

    def _filtered_customers(self):
        keyword = self.search_keyword.strip().lower()
        selected_group = self.ui.comboBox.currentText()
        result = []

        for customer in self.customers:
            if selected_group != "Tất cả" and customer["phan_loai"] != selected_group:
                continue

            if keyword:
                customer_id_text = str(customer["id"]).lower()
                customer_name_text = customer["ten"].lower()
                if keyword not in customer_id_text and keyword not in customer_name_text:
                    continue

            result.append(customer)
        return result

    def search_customers(self):
        # Tìm theo đúng yêu cầu: Mã khách hàng hoặc Tên khách hàng
        self.search_keyword = self.ui.txt_search.text().strip()
        self.refresh_customer_table()

    def refresh_customer_table(self):
        filtered = self._filtered_customers()
        table = self.ui.tbl_customers
        table.setRowCount(0)

        for row, customer in enumerate(filtered):
            table.insertRow(row)
            table.setItem(row, 0, QTableWidgetItem(str(customer["id"])))
            table.setItem(row, 1, QTableWidgetItem(customer["ten"]))
            table.setItem(row, 2, QTableWidgetItem(customer["sdt"]))
            table.setItem(row, 3, QTableWidgetItem(customer["bien_so"]))
            table.setItem(row, 4, QTableWidgetItem(customer["phan_loai"]))
            table.setItem(row, 5, QTableWidgetItem(self._format_currency(customer["tong_chi_tieu"])))

        if filtered:
            table.selectRow(0)
        else:
            self.ui.label_2.setText("Tên:")
            self.ui.label_3.setText("Hạng:")
            self.ui.tbl_history.setRowCount(0)

    def _get_selected_customer_id(self):
        current_row = self.ui.tbl_customers.currentRow()
        if current_row < 0:
            return None
        id_item = self.ui.tbl_customers.item(current_row, 0)
        if id_item is None:
            return None
        try:
            return int(id_item.text())
        except ValueError:
            return None

    def _find_customer_index_by_id(self, customer_id):
        for index, customer in enumerate(self.customers):
            if customer["id"] == customer_id:
                return index
        return None

    def open_add_dialog(self):
        dialog = AddCustomerDialog(self)
        if dialog.exec_() and dialog.saved_customer_data:
            new_customer = self._append_customer(dialog.saved_customer_data)
            self.service_history_map.setdefault(new_customer["id"], [])
            self.refresh_customer_table()

    def open_edit_dialog(self):
        customer_id = self._get_selected_customer_id()
        if customer_id is None:
            QMessageBox.warning(self, "Chưa chọn khách hàng", "Vui lòng chọn khách hàng cần sửa.")
            return

        customer_index = self._find_customer_index_by_id(customer_id)
        if customer_index is None:
            QMessageBox.warning(self, "Không tìm thấy", "Không tìm thấy dữ liệu khách hàng đã chọn.")
            return

        dialog = AddCustomerDialog(self, customer_data=self.customers[customer_index])
        if dialog.exec_() and dialog.saved_customer_data:
            dialog.saved_customer_data["id"] = customer_id
            dialog.saved_customer_data["tong_chi_tieu"] = self.customers[customer_index]["tong_chi_tieu"]
            self.customers[customer_index] = dialog.saved_customer_data
            self.refresh_customer_table()
            self._select_customer_by_id(customer_id)

    def delete_customer(self):
        customer_id = self._get_selected_customer_id()
        if customer_id is None:
            QMessageBox.warning(self, "Chưa chọn khách hàng", "Vui lòng chọn khách hàng cần xóa.")
            return

        reply = QMessageBox.question(
            self,
            "Xác nhận xóa",
            "Bạn có chắc chắn muốn xóa khách hàng này không?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if reply != QMessageBox.Yes:
            return

        customer_index = self._find_customer_index_by_id(customer_id)
        if customer_index is None:
            return

        self.customers.pop(customer_index)
        self.service_history_map.pop(customer_id, None)
        self.refresh_customer_table()

    def _select_customer_by_id(self, customer_id):
        table = self.ui.tbl_customers
        for row in range(table.rowCount()):
            item = table.item(row, 0)
            if item and item.text() == str(customer_id):
                table.selectRow(row)
                return

    def on_customer_selection_changed(self):
        customer_id = self._get_selected_customer_id()
        if customer_id is None:
            self.ui.label_2.setText("Tên:")
            self.ui.label_3.setText("Hạng:")
            self.ui.tbl_history.setRowCount(0)
            return

        customer_index = self._find_customer_index_by_id(customer_id)
        if customer_index is None:
            return

        customer = self.customers[customer_index]
        self.ui.label_2.setText(f"Tên: {customer['ten']}")
        self.ui.label_3.setText(f"Hạng: {customer['phan_loai']}")
        self._render_history(customer_id)

    def _render_history(self, customer_id):
        histories = self.service_history_map.get(customer_id, [])
        table = self.ui.tbl_history
        table.setRowCount(0)

        for row, history in enumerate(histories):
            table.insertRow(row)
            table.setItem(row, 0, QTableWidgetItem(history["ngay"]))
            table.setItem(row, 1, QTableWidgetItem(history["bien_so"]))
            table.setItem(row, 2, QTableWidgetItem(history["dich_vu"]))
            table.setItem(row, 3, QTableWidgetItem(self._format_currency(history["tong_tien"])))
            table.setItem(row, 4, QTableWidgetItem(history["ktv"]))


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = CustomerManagerWidget()
    window.show()
    sys.exit(app.exec_())
