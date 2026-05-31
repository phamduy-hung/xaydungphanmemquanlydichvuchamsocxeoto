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

from database.models import load_system_settings
from modules.invoices_store import get_invoice, list_invoices, update_invoice_status, delete_invoice
from modules.pos import InvoiceDialog
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
        self.tbl.cellDoubleClicked.connect(self._show_invoice_detail)
        root.addWidget(self.tbl)

    def _apply_style(self):
        self.setStyleSheet(
            """
            QWidget { background: transparent; color: #e2e8f0; font-family: "Segoe UI", "Inter"; }
            QLabel#invoiceTitle { color: #f8fafc; font-size: 20px; font-weight: 800; border: none; padding-bottom: 5px; }
            QTableWidget {
                background-color: #0c101a;
                alternate-background-color: #121824;
                color: #e2e8f0;
                border: 1px solid #27354a;
                gridline-color: #1b2336;
                selection-background-color: #0ea5e9;
                selection-color: #ffffff;
            }
            QTableWidget::item:hover {
                background-color: rgba(14, 165, 233, 0.15);
            }
            QHeaderView::section {
                background-color: #161e2e;
                color: #0ea5e9;
                border: 0px;
                padding: 8px;
                font-weight: 700;
                border-bottom: 2px solid #27354a;
            }
            QPushButton {
                background-color: #161e2e;
                color: #e2e8f0;
                border: 1px solid #27354a;
                border-radius: 8px;
                font-weight: 700;
                font-size: 13px;
                padding: 8px 12px;
            }
            QPushButton:hover {
                background-color: #f97316;
                border: 1px solid #ff7a22;
                color: #ffffff;
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
            total = inv.get("total_amount", inv.get("grand_total", 0))
            self.tbl.setItem(row, 6, QTableWidgetItem(self._money(total)))
            item_count = inv.get("item_count", len(inv.get("items", [])))
            self.tbl.setItem(row, 7, QTableWidgetItem(str(item_count)))

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

    def _show_invoice_detail(self, row, _column):
        if row < 0:
            return
        code_item = self.tbl.item(row, 0)
        invoice_no = code_item.text().strip() if code_item else ""
        if not invoice_no:
            return
        invoice = get_invoice(invoice_no)
        if not invoice:
            QMessageBox.warning(self, "Hóa đơn", f"Không tìm thấy chi tiết hóa đơn {invoice_no}.")
            return
        settings = load_system_settings() or {}
        invoice.setdefault("bank_name", settings.get("bank_name", "MB Bank"))
        invoice.setdefault("bank_account_number", settings.get("bank_account_number", "123456789"))
        invoice.setdefault("bank_account_name", settings.get("bank_account_name", "CONG TY PROCARE"))
        invoice.setdefault("qr_image_path", settings.get("qr_image_path", ""))
        dlg = InvoiceDialog(invoice, self, read_only=True)
        dlg.setWindowTitle(f"Hóa đơn chi tiết - {invoice_no}")
        dlg.exec_()

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
