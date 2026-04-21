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
from ui.compiled.ui_suathongtinKH import Ui_Dialog as Ui_Dialog_SuaThongTinKH
from ui.compiled.ui_themkhachhang import Ui_Dialog as Ui_Dialog_ThemKhachHang

# Phân loại khớp bộ lọc trên ui_qlkhachhang (comboBox)
CLASS_NEW = "Khách mới"
CLASS_RETURN = "Khách quay lại"
CLASS_VIP = "Khách VIP"
VIP_THRESHOLD = 50_000_000  # Trên 50 triệu → tự xếp VIP


def _apply_vip_rule(customer):
    """Tổng chi tiêu > 50 triệu: bắt buộc phân loại VIP."""
    if int(customer.get("tong_chi_tieu", 0)) > VIP_THRESHOLD:
        customer["phan_loai"] = CLASS_VIP


class AddCustomerDialog(QDialog):
    """Thêm KH: không chọn phân loại; luôn là Khách mới (theo yêu cầu)."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.ui = Ui_Dialog_ThemKhachHang()
        self.ui.setupUi(self)
        self._apply_input_text_dark_style()
        self.saved_customer_data = None
        self.setWindowTitle("Thêm khách hàng mới")
        self._setup_signals()

    def _apply_input_text_dark_style(self):
        self.setStyleSheet("""
            QLineEdit, QTextEdit, QComboBox {
                background-color: #ffffff;
                color: #111827;
            }
        """)

    def _setup_signals(self):
        self.ui.btn_save.clicked.connect(self._save_data)
        self.ui.btn_cancel.clicked.connect(self.reject)

    def _save_data(self):
        ten = self.ui.txt_name.text().strip()
        sdt = self.ui.txt_phone.text().strip()
        hang_xe = self.ui.txt_hangxe.text().strip()
        bien_so = self.ui.txt_plate.text().strip()
        ghi_chu = self.ui.txt_note.toPlainText().strip()

        if not ten or not sdt:
            QMessageBox.warning(self, "Thiếu dữ liệu", "Vui lòng nhập Tên khách hàng và Số điện thoại.")
            return

        self.saved_customer_data = {
            "ten": ten,
            "sdt": sdt,
            "hang_xe": hang_xe,
            "bien_so": bien_so,
            "phan_loai": CLASS_NEW,
            "tong_chi_tieu": 0,
            "ghi_chu": ghi_chu,
        }
        self.accept()


class EditCustomerDialog(QDialog):
    """Sửa KH: có phân loại; dưới ngưỡng chỉ đổi Khách mới ↔ Khách quay lại; trên ngưỡng khóa VIP."""

    def __init__(self, parent=None, customer_data=None):
        super().__init__(parent)
        self.ui = Ui_Dialog_SuaThongTinKH()
        self.ui.setupUi(self)
        self._apply_input_text_dark_style()
        self.customer_data = customer_data or {}
        self.saved_customer_data = None
        self.setWindowTitle("Sửa thông tin khách hàng")
        self._setup_classification_combo()
        self._fill_old_data()
        self._setup_signals()

    def _apply_input_text_dark_style(self):
        self.setStyleSheet("""
            QLineEdit, QTextEdit, QComboBox {
                background-color: #ffffff;
                color: #111827;
            }
        """)

    def _setup_classification_combo(self):
        """Đồng bộ nhãn với màn hình chính; ẩn VIP khi chưa đủ ngưỡng (cho phép chỉ 2 lựa chọn)."""
        spending = int(self.customer_data.get("tong_chi_tieu", 0))
        cb = self.ui.comboBox
        cb.blockSignals(True)
        cb.clear()
        if spending > VIP_THRESHOLD:
            cb.addItem(CLASS_VIP)
            cb.setCurrentIndex(0)
            cb.setEnabled(False)
        else:
            cb.addItem(CLASS_NEW)
            cb.addItem(CLASS_RETURN)
            cb.setEnabled(True)
        cb.blockSignals(False)

    def _set_combo_from_phan_loai(self):
        spending = int(self.customer_data.get("tong_chi_tieu", 0))
        raw = self.customer_data.get("phan_loai", CLASS_NEW)
        cb = self.ui.comboBox

        if spending > VIP_THRESHOLD:
            return

        if raw == CLASS_VIP:
            idx = cb.findText(CLASS_RETURN, Qt.MatchFixedString)
            cb.setCurrentIndex(idx if idx >= 0 else 0)
            return

        idx = cb.findText(raw, Qt.MatchFixedString)
        if idx >= 0:
            cb.setCurrentIndex(idx)
        else:
            idx = cb.findText(CLASS_NEW, Qt.MatchFixedString)
            cb.setCurrentIndex(idx if idx >= 0 else 0)

    def _setup_signals(self):
        self.ui.btn_save.clicked.connect(self._save_data)
        self.ui.btn_cancel.clicked.connect(self.reject)

    def _fill_old_data(self):
        self.ui.txt_name.setText(self.customer_data.get("ten", ""))
        self.ui.txt_phone.setText(self.customer_data.get("sdt", ""))
        self.ui.txt_hangxe.setText(self.customer_data.get("hang_xe", ""))
        self.ui.txt_plate.setText(self.customer_data.get("bien_so", ""))
        self.ui.txt_note.setPlainText(self.customer_data.get("ghi_chu", ""))
        self._set_combo_from_phan_loai()

    def _save_data(self):
        ten = self.ui.txt_name.text().strip()
        sdt = self.ui.txt_phone.text().strip()
        hang_xe = self.ui.txt_hangxe.text().strip()
        bien_so = self.ui.txt_plate.text().strip()
        ghi_chu = self.ui.txt_note.toPlainText().strip()
        spending = int(self.customer_data.get("tong_chi_tieu", 0))

        if not ten or not sdt:
            QMessageBox.warning(self, "Thiếu dữ liệu", "Vui lòng nhập Tên khách hàng và Số điện thoại.")
            return

        if spending > VIP_THRESHOLD:
            phan_loai = CLASS_VIP
        else:
            phan_loai = self.ui.comboBox.currentText()

        self.saved_customer_data = {
            "id": self.customer_data.get("id"),
            "ten": ten,
            "sdt": sdt,
            "hang_xe": hang_xe,
            "bien_so": bien_so,
            "phan_loai": phan_loai,
            "tong_chi_tieu": spending,
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
        self._apply_dark_style()
        self._seed_demo_data()
        self._setup_signals()
        self.refresh_customer_table()

    def _setup_tables(self):
        # Clear legacy styling
        self.ui.btn_themKH.setStyleSheet("")
        self.ui.btn_suaKH.setStyleSheet("")
        self.ui.btn_xoaKH.setStyleSheet("")
        self.ui.btn_timkiem.setStyleSheet("")
        self.ui.txt_search.setStyleSheet("")
        self.ui.comboBox.setStyleSheet("")
        self.ui.tbl_customers.setStyleSheet("")
        self.ui.tbl_history.setStyleSheet("")
        
        # Clear legacy minimum sizes
        self.ui.btn_themKH.setMinimumSize(0, 0)
        self.ui.btn_suaKH.setMinimumSize(0, 0)
        self.ui.btn_xoaKH.setMinimumSize(0, 0)

        from PyQt5.QtWidgets import QHeaderView
        customer_table = self.ui.tbl_customers
        customer_table.setSelectionBehavior(customer_table.SelectRows)
        customer_table.setSelectionMode(customer_table.SingleSelection)
        customer_table.setEditTriggers(customer_table.NoEditTriggers)
        customer_table.verticalHeader().setVisible(False)
        customer_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        customer_table.setAlternatingRowColors(True)

        history_table = self.ui.tbl_history
        history_table.setSelectionBehavior(history_table.SelectRows)
        history_table.setSelectionMode(history_table.SingleSelection)
        history_table.setEditTriggers(history_table.NoEditTriggers)
        history_table.verticalHeader().setVisible(False)
        history_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        history_table.setAlternatingRowColors(True)
        
        self.ui.grp_history.setStyleSheet("")
        self.ui.label_2.setStyleSheet("")
        self.ui.label_3.setStyleSheet("")

    def _apply_dark_style(self):
        self.setStyleSheet("""
            QWidget {
                background-color: #0b1220;
                color: #dbeafe;
                font-family: "Segoe UI", "Inter";
            }
            QGroupBox {
                background-color: #111827;
                border: 1px solid #334155;
                border-radius: 10px;
                margin-top: 8px;
            }
            QGroupBox::title {
                color: #93c5fd;
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 4px;
            }
            QLineEdit, QComboBox, QTextEdit {
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
                padding: 9px 12px;
            }
            QPushButton:hover {
                background-color: #0ea5e9;
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
                "hang_xe": "Toyota",
                "bien_so": "51A-12345",
                "phan_loai": CLASS_NEW,
                "tong_chi_tieu": 35_000_000,
                "ghi_chu": "Khách hàng mới, cần tư vấn thêm gói vệ sinh nội thất.",
            }
        )
        self._append_customer(
            {
                "ten": "Tran Thi B",
                "sdt": "0988777666",
                "hang_xe": "Mercedes",
                "bien_so": "59G2-88991",
                "phan_loai": CLASS_RETURN,
                "tong_chi_tieu": 52_000_000,
                "ghi_chu": "Tổng chi tiêu trên 50 triệu — hệ thống xếp VIP.",
            }
        )
        self.service_history_map = {
            1: [
                {
                    "ngay": "2026-04-10",
                    "hang_xe": "Toyota",
                    "bien_so": "51A-12345",
                    "dich_vu": "Rửa xe + hút bụi",
                    "tong_tien": 150000,
                    "ktv": "Minh",
                },
                {
                    "ngay": "2026-04-15",
                    "hang_xe": "Toyota",
                    "bien_so": "51A-12345",
                    "dich_vu": "Phủ ceramic nhanh",
                    "tong_tien": 200000,
                    "ktv": "Dat",
                },
            ],
            2: [
                {
                    "ngay": "2026-03-28",
                    "hang_xe": "Mercedes",
                    "bien_so": "59G2-88991",
                    "dich_vu": "Bảo dưỡng tổng quát",
                    "tong_tien": 1250000,
                    "ktv": "Khanh",
                },
                {
                    "ngay": "2026-04-12",
                    "hang_xe": "Mercedes",
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
            "hang_xe": data.get("hang_xe", ""),
            "bien_so": data.get("bien_so", ""),
            "phan_loai": data.get("phan_loai", CLASS_NEW),
            "tong_chi_tieu": int(data.get("tong_chi_tieu", 0)),
            "ghi_chu": data.get("ghi_chu", ""),
        }
        _apply_vip_rule(customer)
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
                hang_xe_text = customer.get("hang_xe", "").lower()
                if (
                    keyword not in customer_id_text
                    and keyword not in customer_name_text
                    and keyword not in hang_xe_text
                ):
                    continue

            result.append(customer)
        return result

    def search_customers(self):
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
            table.setItem(row, 3, QTableWidgetItem(customer.get("hang_xe", "")))
            table.setItem(row, 4, QTableWidgetItem(customer["bien_so"]))
            table.setItem(row, 5, QTableWidgetItem(customer["phan_loai"]))
            table.setItem(row, 6, QTableWidgetItem(self._format_currency(customer["tong_chi_tieu"])))

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

        dialog = EditCustomerDialog(self, customer_data=dict(self.customers[customer_index]))
        if dialog.exec_() and dialog.saved_customer_data:
            dialog.saved_customer_data["id"] = customer_id
            dialog.saved_customer_data["tong_chi_tieu"] = self.customers[customer_index]["tong_chi_tieu"]
            updated = dialog.saved_customer_data
            _apply_vip_rule(updated)
            self.customers[customer_index] = updated
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
            table.setItem(row, 1, QTableWidgetItem(history.get("hang_xe", "")))
            table.setItem(row, 2, QTableWidgetItem(history["bien_so"]))
            table.setItem(row, 3, QTableWidgetItem(history["dich_vu"]))
            table.setItem(row, 4, QTableWidgetItem(self._format_currency(history["tong_tien"])))
            table.setItem(row, 5, QTableWidgetItem(history["ktv"]))


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = CustomerManagerWidget()
    window.show()
    sys.exit(app.exec_())
