import csv
from pathlib import Path

from PyQt5.QtWidgets import (
    QFileDialog,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from modules.invoices_store import list_invoices, update_invoice_status, delete_invoice
from modules.rbac_runtime import can_do
from modules.audit_log import append_audit_log


class HoaDonManagerWidget(QWidget):
    def __init__(self, current_role="Quản lý", current_user="system"):
        super().__init__()
        self.current_role = current_role
        self.current_user = current_user
        self._build_ui()
        self._apply_style()
        self.refresh_data()

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(8, 8, 8, 8)
        root.setSpacing(10)
        title = QLabel("QUẢN LÝ HÓA ĐƠN")
        title.setObjectName("invoiceTitle")
        root.addWidget(title)

        row = QHBoxLayout()
        row.addStretch()
        self.btn_refresh = QPushButton("Làm mới")
        self.btn_export = QPushButton("Xuất CSV")
        self.btn_mark_issued = QPushButton("Chuyển Issued")
        self.btn_mark_paid = QPushButton("Chuyển Paid")
        self.btn_mark_cancel = QPushButton("Chuyển Cancelled")
        self.btn_mark_refund = QPushButton("Chuyển Refunded")
        self.btn_delete = QPushButton("Xóa hóa đơn")
        self.btn_refresh.clicked.connect(self.refresh_data)
        self.btn_export.clicked.connect(self.export_csv)
        self.btn_mark_issued.clicked.connect(lambda: self._change_status_selected("issued"))
        self.btn_mark_paid.clicked.connect(lambda: self._change_status_selected("paid"))
        self.btn_mark_cancel.clicked.connect(lambda: self._change_status_selected("cancelled"))
        self.btn_mark_refund.clicked.connect(lambda: self._change_status_selected("refunded"))
        self.btn_delete.clicked.connect(self._delete_selected)
        row.addWidget(self.btn_refresh)
        row.addWidget(self.btn_mark_issued)
        row.addWidget(self.btn_mark_paid)
        row.addWidget(self.btn_mark_cancel)
        row.addWidget(self.btn_mark_refund)
        row.addWidget(self.btn_delete)
        row.addWidget(self.btn_export)
        root.addLayout(row)

        self.tbl = QTableWidget()
        self.tbl.setColumnCount(8)
        self.tbl.setHorizontalHeaderLabels(
            ["Mã HĐ", "Thời gian", "Khách hàng", "SĐT", "Thanh toán", "Trạng thái", "Tổng tiền", "Số dòng"]
        )
        self.tbl.verticalHeader().setVisible(False)
        self.tbl.setAlternatingRowColors(True)
        header = self.tbl.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.Stretch)
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(5, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(6, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(7, QHeaderView.ResizeToContents)
        root.addWidget(self.tbl)

    def _apply_style(self):
        self.setStyleSheet(
            """
            QWidget { background: transparent; color: #dbeafe; }
            QLabel#invoiceTitle { color: #f8fafc; font-size: 18px; font-weight: 800; border: none; }
            QTableWidget {
                background-color: #0f172a;
                alternate-background-color: #111b31;
                color: #e2e8f0;
                border: 1px solid #334155;
                gridline-color: #1f2937;
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
                padding: 8px 12px;
            }
            """
        )

    def refresh_data(self):
        data = list(reversed(list_invoices()))
        self.tbl.setRowCount(0)
        for row, inv in enumerate(data):
            self.tbl.insertRow(row)
            self.tbl.setItem(row, 0, QTableWidgetItem(str(inv.get("invoice_no", "-"))))
            self.tbl.setItem(row, 1, QTableWidgetItem(str(inv.get("created_at", "-"))))
            self.tbl.setItem(row, 2, QTableWidgetItem(str(inv.get("customer_name", "Khách lẻ"))))
            self.tbl.setItem(row, 3, QTableWidgetItem(str(inv.get("customer_phone", "-"))))
            self.tbl.setItem(row, 4, QTableWidgetItem(str(inv.get("payment_method", "-"))))
            self.tbl.setItem(row, 5, QTableWidgetItem(str(inv.get("status", "paid"))))
            self.tbl.setItem(row, 6, QTableWidgetItem(self._money(inv.get("grand_total", 0))))
            self.tbl.setItem(row, 7, QTableWidgetItem(str(len(inv.get("items", [])))))

    def export_csv(self):
        if not can_do(self.current_role, "invoices.export"):
            QMessageBox.warning(self, "Không có quyền", "Vai trò hiện tại không có quyền xuất hóa đơn.")
            return
        if self.tbl.rowCount() == 0:
            return
        save_path, _ = QFileDialog.getSaveFileName(
            self, "Xuất danh sách hóa đơn", "danh_sach_hoa_don.csv", "CSV Files (*.csv)"
        )
        if not save_path:
            return
        path = Path(save_path)
        headers = [self.tbl.horizontalHeaderItem(c).text() for c in range(self.tbl.columnCount())]
        rows = []
        for r in range(self.tbl.rowCount()):
            row = []
            for c in range(self.tbl.columnCount()):
                item = self.tbl.item(r, c)
                row.append(item.text() if item else "")
            rows.append(row)
        with path.open("w", newline="", encoding="utf-8-sig") as f:
            writer = csv.writer(f)
            writer.writerow(headers)
            writer.writerows(rows)
        append_audit_log("invoice.export_csv", self.current_user, {"path": str(path)})

    def _selected_invoice_no(self):
        row = self.tbl.currentRow()
        if row < 0:
            return ""
        item = self.tbl.item(row, 0)
        return item.text().strip() if item else ""

    def _change_status_selected(self, to_status):
        invoice_no = self._selected_invoice_no()
        if not invoice_no:
            return
        updated = update_invoice_status(invoice_no, to_status)
        if not updated:
            return
        append_audit_log("invoice.update_status", self.current_user, {"invoice_no": invoice_no, "to": to_status})
        self.refresh_data()

    def _delete_selected(self):
        invoice_no = self._selected_invoice_no()
        if not invoice_no:
            return
        try:
            ok = delete_invoice(invoice_no, current_role=self.current_role)
            if not ok:
                return
            append_audit_log("invoice.delete", self.current_user, {"invoice_no": invoice_no})
            self.refresh_data()
        except PermissionError as e:
            QMessageBox.warning(self, "Không thể xóa", str(e))

    @staticmethod
    def _money(value):
        return f"{int(value):,} đ".replace(",", ".")
