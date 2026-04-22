import re
from datetime import datetime
from pathlib import Path

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QImage, QPainter, QPixmap, QColor, QKeySequence
from PyQt5.QtWidgets import (
    QAbstractItemView,
    QDialog,
    QHeaderView,
    QMessageBox,
    QPushButton,
    QShortcut,
    QTableWidgetItem,
    QWidget,
)
from ui.compiled.ui_bill_pos import Ui_BillPOSDialog
from ui.compiled.ui_pos import Ui_POSForm
from modules.integration_data import append_pos_sale


class InvoiceDialog(QDialog):
    def __init__(self, invoice_data, parent=None):
        super().__init__(parent)
        self.ui = Ui_BillPOSDialog()
        self.ui.setupUi(self)
        self.invoice_data = invoice_data
        self.payment_method = ""
        self._bind_data()
        self._apply_style()

    def _bind_data(self):
        self.ui.lbl_bill_meta.setText(
            f"Mã hóa đơn: {self.invoice_data['invoice_no']}    |    "
            f"Thời gian: {self.invoice_data['created_at']}"
        )
        self.ui.lbl_bill_customer.setText(
            f"Khách hàng: {self.invoice_data['customer_name']}    |    "
            f"SĐT: {self.invoice_data['customer_phone']}"
        )

        table = self.ui.tbl_bill_items
        table.verticalHeader().setVisible(False)
        table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        table.setSelectionBehavior(QAbstractItemView.SelectRows)
        header = table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.ResizeToContents)
        table.setRowCount(len(self.invoice_data["lines"]))

        for r, row in enumerate(self.invoice_data["lines"]):
            table.setItem(r, 0, QTableWidgetItem(row["name"]))
            table.setItem(r, 1, QTableWidgetItem(POSWidget.format_money(row["unit_price"])))
            table.setItem(r, 2, QTableWidgetItem(str(row["qty"])))
            table.setItem(r, 3, QTableWidgetItem(POSWidget.format_money(row["line_total"])))
            table.setItem(r, 4, QTableWidgetItem(row["item_type"]))

        qr_image_path = (self.invoice_data.get("qr_image_path") or "").strip()
        if qr_image_path and Path(qr_image_path).exists():
            pix = QPixmap(qr_image_path)
            if not pix.isNull():
                self.ui.lbl_qr_image.setPixmap(
                    pix.scaled(180, 180, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                )
            else:
                self.ui.lbl_qr_image.setPixmap(self._make_qr_pixmap(self.invoice_data["payment_payload"]))
        else:
            self.ui.lbl_qr_image.setPixmap(self._make_qr_pixmap(self.invoice_data["payment_payload"]))
        self.ui.lbl_bank_info.setText(
            f"Ngân hàng: {self.invoice_data.get('bank_name', '-')}\n"
            f"Số TK: {self.invoice_data.get('bank_account_number', '-')}\n"
            f"Tên TK: {self.invoice_data.get('bank_account_name', '-')}\n"
            f"Nội dung: {self.invoice_data['invoice_no']}"
        )
        self.ui.lbl_subtotal_value.setText(POSWidget.format_money(self.invoice_data["subtotal"]))
        self.ui.lbl_discount_value.setText(POSWidget.format_money(-self.invoice_data["discount_amount"]))
        self.ui.lbl_vat_text.setText(f"VAT ({self.invoice_data['vat_percent']:.1f}%)")
        self.ui.lbl_vat_value.setText(POSWidget.format_money(self.invoice_data["vat_amount"]))
        self.ui.lbl_grand_value.setText(POSWidget.format_money(self.invoice_data["grand_total"]))

        self.ui.btn_mark_paid.setText("Đã thanh toán qua ngân hàng")
        self.ui.btn_mark_paid.clicked.connect(self._mark_paid_bank)

        self.btn_mark_paid_cash = QPushButton("Đã thanh toán tiền mặt")
        self.btn_mark_paid_cash.clicked.connect(self._mark_paid_cash)
        self.ui.btnLayout.addWidget(self.btn_mark_paid_cash)

    def _mark_paid_bank(self):
        self.payment_method = "Chuyển khoản ngân hàng"
        self.accept()

    def _mark_paid_cash(self):
        self.payment_method = "Tiền mặt"
        self.accept()

    def _make_qr_pixmap(self, payload: str) -> QPixmap:
        size = 180
        grid = 29
        module = max(4, size // grid)
        img = QImage(grid * module, grid * module, QImage.Format_RGB32)
        img.fill(QColor("#ffffff"))
        p = QPainter(img)
        p.setPen(Qt.NoPen)
        p.setBrush(QColor("#000000"))

        seed = sum(ord(ch) for ch in payload) or 1

        def is_finder(r, c):
            corners = [(0, 0), (0, grid - 7), (grid - 7, 0)]
            for fr, fc in corners:
                if fr <= r < fr + 7 and fc <= c < fc + 7:
                    rr, cc = r - fr, c - fc
                    return rr in (0, 6) or cc in (0, 6) or (2 <= rr <= 4 and 2 <= cc <= 4)
            return False

        for r in range(grid):
            for c in range(grid):
                if is_finder(r, c):
                    dark = True
                else:
                    dark = ((r * 31 + c * 17 + seed) % 7) < 3
                if dark:
                    p.drawRect(c * module, r * module, module, module)
        p.end()
        return QPixmap.fromImage(img)

    def _apply_style(self):
        self.ui.lbl_bill_title.setObjectName("billTitle")
        self.ui.lbl_qr_title.setObjectName("billSub")
        self.ui.lbl_sum_title.setObjectName("billSub")
        self.ui.lbl_bill_meta.setObjectName("billMeta")
        self.ui.lbl_bill_customer.setObjectName("billMeta")
        self.ui.lbl_bank_info.setObjectName("billMeta")
        self.ui.lbl_subtotal_text.setObjectName("billMeta")
        self.ui.lbl_subtotal_value.setObjectName("billMeta")
        self.ui.lbl_discount_text.setObjectName("billMeta")
        self.ui.lbl_discount_value.setObjectName("billMeta")
        self.ui.lbl_vat_text.setObjectName("billMeta")
        self.ui.lbl_vat_value.setObjectName("billMeta")
        self.ui.lbl_grand_text.setObjectName("billMeta")
        self.ui.lbl_grand_value.setObjectName("billTotal")
        self.ui.frame_qr.setObjectName("billCard")
        self.ui.frame_summary.setObjectName("billCard")
        self.setStyleSheet(
            """
            QDialog {
                background-color: #0b1220;
                color: #dbeafe;
            }
            QLabel {
                border: none;
                background: transparent;
            }
            QFrame#billCard {
                background-color: #111827;
                border: none;
                border-radius: 10px;
            }
            QLabel#billTitle {
                color: #f8fafc;
                font-size: 18px;
                font-weight: 800;
            }
            QLabel#billSub {
                color: #93c5fd;
                font-weight: 700;
                font-size: 13px;
            }
            QLabel#billMeta {
                color: #cbd5e1;
                font-size: 12px;
            }
            QLabel#billTotal {
                color: #22d3ee;
                font-size: 15px;
                font-weight: 800;
            }
            QTableWidget {
                background-color: #0f172a;
                color: #e2e8f0;
                border: 1px solid #334155;
                gridline-color: #1f2937;
                selection-background-color: #0ea5e9;
                selection-color: #f8fafc;
            }
            QHeaderView::section {
                background-color: #1e293b;
                color: #bae6fd;
                border: 0;
                padding: 7px;
                font-weight: 700;
            }
            QPushButton {
                background-color: #0ea5e9;
                color: #f8fafc;
                border: 1px solid #38bdf8;
                border-radius: 8px;
                font-weight: 700;
                padding: 8px 14px;
            }
            QPushButton:hover {
                background-color: #0284c7;
            }
            """
        )


class POSWidget(QWidget):
    DISCOUNT_CODES = {
        "GIAM5": ("percent", 5),
        "GIAM10": ("percent", 10),
        "GIAM50K": ("fixed", 50000),
    }

    def __init__(self):
        super().__init__()
        self.ui = Ui_POSForm()
        self.ui.setupUi(self)
        self.setObjectName("posRoot")
        self._updating_cart = False
        self._applied_discount_code = ""
        self._applied_discount_value = ("none", 0)
        self.crm_widget = None

        self.catalog_items = [
            {"name": "Rửa xe detailing bọt tuyết", "price": 150000, "type": "Dịch vụ"},
            {"name": "Phủ Ceramic 9H Pro", "price": 4500000, "type": "Dịch vụ"},
            {"name": "Vệ sinh dàn lạnh", "price": 300000, "type": "Dịch vụ"},
            {"name": "Nước hoa xe hơi (Chai)", "price": 650000, "type": "Sản phẩm"},
            {"name": "Dầu nhớt Castrol 1L", "price": 145000, "type": "Sản phẩm"},
        ]
        self.cart_items = {}
        self.vat_percent = self._load_vat_percent()
        self.payment_info = self._load_payment_info()

        self._bind_ui()
        self._apply_dark_style()
        self._render_catalog(self.catalog_items)

    def _bind_ui(self):
        self.ui.rootLayout.setStretch(0, 7)
        self.ui.rootLayout.setStretch(1, 3)

        self.lbl_avail_title = self.ui.lbl_avail_title
        self.lbl_invoice_title = self.ui.lbl_invoice_title
        self.lbl_customer_title = self.ui.lbl_customer_title
        self.lbl_total_title = self.ui.lbl_total_title
        self.lbl_total_v = self.ui.lbl_total_v
        self.lbl_discount_note = self.ui.lbl_discount_note
        self.lbl_subtotal = self.ui.lbl_subtotal
        self.lbl_discount = self.ui.lbl_discount
        self.lbl_vat = self.ui.lbl_vat
        self.rightPanel = self.ui.rightPanel
        self.tbl_items = self.ui.tbl_items
        self.btn_add_selected = self.ui.btn_add_selected
        self.tbl_cart = self.ui.tbl_cart
        self.cmb_discount = self.ui.cmb_discount
        self.btn_apply_discount = self.ui.btn_apply_discount
        self.btn_pay = self.ui.btn_pay
        self.txt_search_item = self.ui.txt_search_item
        self.txt_discount_code = self.ui.txt_discount_code
        self.txt_customer = self.ui.txt_customer
        self.txt_customer_phone = self.ui.txt_customer_phone

        self.lbl_avail_title.setObjectName("posTitle")
        self.lbl_avail_title.setProperty("plainTitle", "true")
        self.lbl_invoice_title.setObjectName("posTitle")
        self.lbl_invoice_title.setProperty("plainTitle", "true")
        self.lbl_customer_title.setObjectName("posSubTitle")
        self.lbl_customer_title.setProperty("plainTitle", "true")
        self.lbl_total_title.setObjectName("posSubTitle")
        self.lbl_total_title.setProperty("plainTitle", "true")
        self.lbl_total_v.setObjectName("posTotal")
        self.lbl_discount_note.setObjectName("posMuted")
        self.lbl_subtotal.setObjectName("posMuted")
        self.lbl_discount.setObjectName("posMuted")
        self.lbl_vat.setObjectName("posMuted")
        self.rightPanel.setObjectName("posCard")
        self.btn_pay.setObjectName("btnPay")

        self.txt_search_item.textChanged.connect(self._filter_catalog)
        header = self.tbl_items.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.Stretch)
        self.tbl_items.verticalHeader().setVisible(False)
        self.tbl_items.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.tbl_items.setSelectionMode(QAbstractItemView.SingleSelection)
        self.tbl_items.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.tbl_items.itemDoubleClicked.connect(self._on_item_double_clicked)
        self.tbl_items.itemActivated.connect(self._on_item_double_clicked)
        self.btn_add_selected.clicked.connect(self._add_selected_item_to_cart)

        c_header = self.tbl_cart.horizontalHeader()
        c_header.setSectionResizeMode(0, QHeaderView.Stretch)
        c_header.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        c_header.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        c_header.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        self.tbl_cart.verticalHeader().setVisible(False)
        self.tbl_cart.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.tbl_cart.setSelectionMode(QAbstractItemView.SingleSelection)
        self.tbl_cart.itemChanged.connect(self._on_cart_item_changed)
        self.btn_remove_cart_item = QPushButton("XÓA DÒNG ĐÃ CHỌN")
        self.btn_remove_cart_item.clicked.connect(self._remove_selected_cart_item)
        self.ui.rightLayout.insertWidget(3, self.btn_remove_cart_item)
        self.shortcut_remove_cart = QShortcut(QKeySequence.Delete, self.tbl_cart)
        self.shortcut_remove_cart.activated.connect(self._remove_selected_cart_item)
        self.cmb_discount.setEditable(False)
        self.cmb_discount.clear()
        self.cmb_discount.addItems(
            ["Chọn mã giảm giá...", "GIAM5 (5%)", "GIAM10 (10%)", "GIAM50K (50.000đ)", "Tự nhập"]
        )
        self.cmb_discount.currentIndexChanged.connect(self._on_discount_combo_changed)
        self.btn_apply_discount.clicked.connect(self._apply_discount_code)
        self.btn_pay.clicked.connect(self._show_payment_invoice)
        self.lbl_vat.setText(f"VAT ({self.vat_percent:.1f}%): 0 đ")

    def _render_catalog(self, items):
        self.tbl_items.setRowCount(len(items))
        for r, item in enumerate(items):
            self.tbl_items.setItem(r, 0, QTableWidgetItem(item["name"]))
            self.tbl_items.setItem(r, 1, QTableWidgetItem(self.format_money(item["price"])))
            self.tbl_items.setItem(r, 2, QTableWidgetItem(item["type"]))

    def _filter_catalog(self, text):
        key = (text or "").strip().lower()
        if not key:
            self._render_catalog(self.catalog_items)
            return
        filtered = [
            item
            for item in self.catalog_items
            if key in item["name"].lower() or key in item["type"].lower()
        ]
        self._render_catalog(filtered)

    def _on_item_double_clicked(self, item):
        self._add_item_by_row(item.row())

    def _add_selected_item_to_cart(self):
        row = self.tbl_items.currentRow()
        if row < 0:
            self._show_notice("Bán hàng POS", "Vui lòng chọn dịch vụ/sản phẩm trước.", "info")
            return
        self._add_item_by_row(row)

    def _add_item_by_row(self, row: int):
        name_item = self.tbl_items.item(row, 0)
        price_item = self.tbl_items.item(row, 1)
        type_item = self.tbl_items.item(row, 2)
        if not name_item or not price_item:
            return

        name = name_item.text().strip()
        price = self.parse_money(price_item.text())
        item_type = type_item.text().strip() if type_item else "Khác"
        if name in self.cart_items:
            self.cart_items[name]["qty"] += 1
        else:
            self.cart_items[name] = {"price": price, "qty": 1, "type": item_type}
        self._render_cart()

    def _render_cart(self):
        self._updating_cart = True
        self.tbl_cart.setRowCount(len(self.cart_items))
        for r, (name, data) in enumerate(self.cart_items.items()):
            unit_price = int(data["price"])
            qty = max(1, int(data["qty"]))
            line_total = unit_price * qty
            name_item = QTableWidgetItem(name)
            name_item.setFlags(name_item.flags() & ~Qt.ItemIsEditable)
            price_item = QTableWidgetItem(self.format_money(unit_price))
            price_item.setFlags(price_item.flags() & ~Qt.ItemIsEditable)
            total_item = QTableWidgetItem(self.format_money(line_total))
            total_item.setFlags(total_item.flags() & ~Qt.ItemIsEditable)
            qty_item = QTableWidgetItem(str(qty))
            self.tbl_cart.setItem(r, 0, name_item)
            self.tbl_cart.setItem(r, 1, price_item)
            self.tbl_cart.setItem(r, 2, qty_item)
            self.tbl_cart.setItem(r, 3, total_item)
        self._updating_cart = False
        self._recalculate_totals()

    def _on_cart_item_changed(self, item):
        if self._updating_cart:
            return
        if item.column() != 2:
            return
        name_item = self.tbl_cart.item(item.row(), 0)
        if not name_item:
            return
        name = name_item.text().strip()
        if name not in self.cart_items:
            return

        try:
            qty = int(item.text().strip())
        except ValueError:
            qty = 1
        qty = max(1, qty)
        self.cart_items[name]["qty"] = qty
        self._render_cart()

    def _remove_selected_cart_item(self):
        row = self.tbl_cart.currentRow()
        if row < 0:
            return
        name_item = self.tbl_cart.item(row, 0)
        if not name_item:
            return
        name = name_item.text().strip()
        if name in self.cart_items:
            del self.cart_items[name]
            self._render_cart()

    def _apply_discount_code(self):
        code = (self.txt_discount_code.text() or "").strip().upper()
        if not code:
            self._applied_discount_code = ""
            self._applied_discount_value = ("none", 0)
            self.lbl_discount_note.setText("Đã xóa mã giảm giá")
            self._recalculate_totals()
            return

        if code not in self.DISCOUNT_CODES:
            custom = self._parse_custom_discount(code)
            if not custom:
                self._applied_discount_code = ""
                self._applied_discount_value = ("none", 0)
                self.lbl_discount_note.setText("Mã không hợp lệ")
                self._recalculate_totals()
                return
            self._applied_discount_code = "CUSTOM"
            self._applied_discount_value = custom
            t, v = custom
            if t == "percent":
                self.lbl_discount_note.setText(f"Đã áp giảm thủ công: {v}%")
            else:
                self.lbl_discount_note.setText(f"Đã áp giảm thủ công: {self.format_money(v)}")
            self._recalculate_totals()
            return

        self._applied_discount_code = code
        self._applied_discount_value = self.DISCOUNT_CODES[code]
        t, v = self._applied_discount_value
        if t == "percent":
            self.lbl_discount_note.setText(f"Đã áp mã {code}: giảm {v}%")
        else:
            self.lbl_discount_note.setText(f"Đã áp mã {code}: giảm {self.format_money(v)}")
        self._recalculate_totals()

    def _on_discount_combo_changed(self):
        current = (self.cmb_discount.currentText() or "").strip()
        if current.startswith("GIAM5"):
            self.txt_discount_code.setText("GIAM5")
        elif current.startswith("GIAM10"):
            self.txt_discount_code.setText("GIAM10")
        elif current.startswith("GIAM50K"):
            self.txt_discount_code.setText("GIAM50K")
        elif current == "Tự nhập":
            self.txt_discount_code.clear()
            self.txt_discount_code.setFocus()

    def _parse_custom_discount(self, raw_code):
        raw = (raw_code or "").strip().lower().replace(" ", "")
        if not raw:
            return None
        if raw.endswith("%"):
            try:
                val = float(raw[:-1].replace(",", "."))
                val = max(0.0, min(100.0, val))
                return ("percent", val)
            except ValueError:
                return None
        if raw.endswith("k"):
            body = raw[:-1]
            if body.isdigit():
                return ("fixed", int(body) * 1000)
            return None
        if raw.isdigit():
            return ("fixed", int(raw))
        return None

    def _current_totals(self):
        subtotal = 0
        for row in self.cart_items.values():
            subtotal += int(row["price"]) * int(row["qty"])

        discount_amount = 0
        discount_type, discount_val = self._applied_discount_value
        if discount_type == "percent":
            discount_amount = int(subtotal * (float(discount_val) / 100.0))
        elif discount_type == "fixed":
            discount_amount = int(discount_val)
        discount_amount = min(discount_amount, subtotal)

        after_discount = max(0, subtotal - discount_amount)
        vat_amount = int(round(after_discount * (self.vat_percent / 100.0)))
        grand_total = after_discount + vat_amount
        return subtotal, discount_amount, vat_amount, grand_total

    def _recalculate_totals(self):
        subtotal, discount_amount, vat_amount, grand_total = self._current_totals()
        self.lbl_subtotal.setText(f"Tạm tính: {self.format_money(subtotal)}")
        self.lbl_discount.setText(f"Giảm giá: -{self.format_money(discount_amount)}")
        self.lbl_vat.setText(f"VAT ({self.vat_percent:.1f}%): {self.format_money(vat_amount)}")
        self.lbl_total_v.setText(f"{self.format_money(grand_total)}")

    def _show_payment_invoice(self):
        if not self.cart_items:
            self._show_notice("Thanh toán", "Giỏ hàng đang trống.", "warning")
            return
        # Reload latest payment/settings values saved from System Settings.
        self.vat_percent = self._load_vat_percent()
        self.payment_info = self._load_payment_info()
        self.lbl_vat.setText(f"VAT ({self.vat_percent:.1f}%): 0 đ")
        self._recalculate_totals()

        subtotal, discount_amount, vat_amount, grand_total = self._current_totals()
        lines = []
        for name, row in self.cart_items.items():
            unit_price = int(row["price"])
            qty = int(row["qty"])
            lines.append(
                {
                    "name": name,
                    "unit_price": unit_price,
                    "qty": qty,
                    "line_total": unit_price * qty,
                    "item_type": row.get("type", "Khác"),
                }
            )
        invoice_no = f"HD{datetime.now().strftime('%Y%m%d%H%M%S')}"
        qr_base = self.payment_info.get("qr_payload") or "PROCARE_QR"
        payload = f"{qr_base}|{invoice_no}|{grand_total}"
        customer_name = (self.txt_customer.text() or "").strip() or "Khách lẻ"
        customer_phone = (self.txt_customer_phone.text() or "").strip() or "-"
        invoice_data = {
            "invoice_no": invoice_no,
            "created_at": datetime.now().strftime("%d/%m/%Y %H:%M"),
            "customer_name": customer_name,
            "customer_phone": customer_phone,
            "lines": lines,
            "subtotal": subtotal,
            "discount_amount": discount_amount,
            "vat_percent": self.vat_percent,
            "vat_amount": vat_amount,
            "grand_total": grand_total,
            "payment_payload": payload,
            "bank_name": self.payment_info.get("bank_name", "MB Bank"),
            "bank_account_number": self.payment_info.get("bank_account_number", "123456789"),
            "bank_account_name": self.payment_info.get("bank_account_name", "CONG TY PROCARE"),
            "qr_image_path": self.payment_info.get("qr_image_path", ""),
        }
        dlg = InvoiceDialog(invoice_data, self)
        if dlg.exec_():
            paid_label = dlg.payment_method or "Không xác định"
            self._after_payment_integrations(invoice_data, paid_label)
            self._show_notice(
                "Thanh toán",
                f"Đã thanh toán hóa đơn {invoice_no} ({paid_label}).",
                "info",
            )
            self.cart_items = {}
            self._applied_discount_code = ""
            self._applied_discount_value = ("none", 0)
            self.txt_discount_code.clear()
            self.lbl_discount_note.setText("Chưa áp mã giảm giá")
            self._render_cart()

    def _after_payment_integrations(self, invoice_data, paid_label):
        event = {
            "invoice_no": invoice_data.get("invoice_no"),
            "created_at": invoice_data.get("created_at"),
            "customer_name": invoice_data.get("customer_name"),
            "customer_phone": invoice_data.get("customer_phone"),
            "subtotal": invoice_data.get("subtotal", 0),
            "discount_amount": invoice_data.get("discount_amount", 0),
            "vat_amount": invoice_data.get("vat_amount", 0),
            "grand_total": invoice_data.get("grand_total", 0),
            "payment_method": paid_label,
            "items": invoice_data.get("lines", []),
        }
        append_pos_sale(event)

        # POS -> CRM: tự ghi nhận mua hàng/lịch sử.
        if self.crm_widget is not None and hasattr(self.crm_widget, "record_pos_invoice"):
            try:
                self.crm_widget.record_pos_invoice(
                    invoice_data.get("customer_name", ""),
                    invoice_data.get("customer_phone", ""),
                    int(invoice_data.get("grand_total", 0)),
                    invoice_data.get("lines", []),
                    invoice_data.get("created_at", ""),
                )
            except Exception:
                pass

        # POS -> Kho: trừ kho cho các dòng sản phẩm có ánh xạ tên.
        self._sync_inventory_from_invoice(invoice_data.get("lines", []))

        # POS -> CSKH loyalty: cộng điểm nếu có dữ liệu khách.
        try:
            from modules.chamsoc_kh_marketing import ghi_nhan_thanh_toan_tich_hop

            phone = (invoice_data.get("customer_phone") or "").strip()
            if phone and phone != "-":
                ghi_nhan_thanh_toan_tich_hop(
                    ma_khach_hang=phone,
                    so_tien_vnd=int(invoice_data.get("grand_total", 0)),
                    ten_khach_hang=invoice_data.get("customer_name", ""),
                    sdt=phone,
                )
        except Exception:
            pass

    def _sync_inventory_from_invoice(self, lines):
        try:
            from modules.kho_vattu.data_store import vattu_list, ton_kho, xuat_kho_log
        except Exception:
            return
        for line in lines or []:
            item_type = (line.get("item_type") or "").strip().lower()
            if "sản phẩm" not in item_type and "san pham" not in item_type:
                continue
            name = (line.get("name") or "").strip().lower()
            qty = max(1, int(line.get("qty") or 1))
            matched = None
            for vt in vattu_list:
                vt_name = str(vt.get("ten", "")).strip().lower()
                if vt_name and (vt_name in name or name in vt_name):
                    matched = vt
                    break
            if not matched:
                continue
            vt_id = matched.get("id")
            current = int(ton_kho.get(vt_id, 0))
            used = min(current, qty)
            ton_kho[vt_id] = max(0, current - used)
            xuat_kho_log.append(
                {
                    "vat_tu_id": vt_id,
                    "so_luong": used,
                    "ghi_chu": f"Trừ kho từ POS ({line.get('name', '')})",
                }
            )

    def _show_notice(self, title: str, message: str, level: str = "info"):
        box = QMessageBox(self)
        box.setWindowTitle(title)
        box.setText(message)
        if level == "warning":
            box.setIcon(QMessageBox.Warning)
        else:
            box.setIcon(QMessageBox.Information)
        box.setStandardButtons(QMessageBox.Ok)
        box.setStyleSheet(
            """
            QMessageBox {
                background-color: #0b1220;
            }
            QMessageBox QLabel {
                color: #e2e8f0;
                background: transparent;
                border: none;
                font-size: 13px;
            }
            QMessageBox QPushButton {
                min-width: 80px;
                background-color: #1e293b;
                color: #e2e8f0;
                border: 1px solid #334155;
                border-radius: 10px;
                font-weight: 700;
                padding: 6px 10px;
            }
            QMessageBox QPushButton:hover {
                background-color: #0ea5e9;
                border: 1px solid #38bdf8;
                color: #f8fafc;
            }
            """
        )
        box.exec_()

    def _load_vat_percent(self) -> float:
        config_path = Path("data/system_settings.json")
        if config_path.exists():
            try:
                import json

                payload = json.loads(config_path.read_text(encoding="utf-8"))
                raw = payload.get("default_vat") or payload.get("vat_percent")
                if raw is not None:
                    return self._parse_percent(raw, default=10.0)
            except Exception:
                pass
        return 10.0

    def _load_payment_info(self):
        config_path = Path("data/system_settings.json")
        default = {
            "bank_name": "MB Bank",
            "bank_account_number": "123456789",
            "bank_account_name": "CONG TY PROCARE",
            "bank_transfer_note": "Thanh toan hoa don",
            "qr_payload": "PROCARE_QR",
            "qr_image_path": "",
        }
        if not config_path.exists():
            return default
        try:
            import json

            payload = json.loads(config_path.read_text(encoding="utf-8"))
            result = dict(default)
            for key in default:
                if payload.get(key):
                    result[key] = payload.get(key)
            return result
        except Exception:
            return default

    @staticmethod
    def _parse_percent(raw, default=10.0):
        text = str(raw or "").strip().replace(",", ".")
        m = re.search(r"(\d+(\.\d+)?)", text)
        if not m:
            return float(default)
        try:
            return max(0.0, float(m.group(1)))
        except ValueError:
            return float(default)

    @staticmethod
    def parse_money(text):
        raw = re.sub(r"[^\d]", "", str(text or ""))
        return int(raw or 0)

    @staticmethod
    def format_money(value):
        return f"{int(value):,}".replace(",", ".") + " đ"

    def _apply_dark_style(self):
        self.setStyleSheet(
            """
            QWidget#posRoot {
                background: transparent;
                color: #dbeafe;
                font-family: "Segoe UI";
            }
            QLabel {
                border: none;
                background: transparent;
            }
            QLabel#posTitle {
                color: #f8fafc;
                font-size: 18px;
                font-weight: 800;
            }
            QLabel#posSubTitle {
                color: #93c5fd;
                font-weight: 700;
            }
            QLabel#posMuted {
                color: #94a3b8;
                font-size: 12px;
                border: none;
                background: transparent;
            }
            QLabel[plainTitle="true"] {
                border: none;
                background: transparent;
                padding: 0;
            }
            QLabel#posTotal {
                color: #22d3ee;
                font-size: 20px;
                font-weight: 800;
                border: none;
                background: transparent;
            }
            QFrame#posCard {
                background-color: #111827;
                border: 1px solid #334155;
                border-radius: 12px;
            }
            QFrame#customerFrame {
                background-color: transparent;
                border: 1px solid #334155;
                border-radius: 10px;
            }
            QLineEdit {
                background-color: #0f172a;
                color: #e2e8f0;
                border: 1px solid #334155;
                border-radius: 8px;
                padding: 8px 10px;
            }
            QComboBox {
                background-color: #0f172a;
                color: #e2e8f0;
                border: 1px solid #334155;
                border-radius: 8px;
                padding: 7px 10px;
                min-height: 18px;
            }
            QComboBox:hover {
                border: 1px solid #38bdf8;
            }
            QComboBox:focus {
                border: 1px solid #38bdf8;
            }
            QComboBox::drop-down {
                border: none;
                width: 24px;
                background: transparent;
            }
            QComboBox::down-arrow {
                image: none;
                width: 8px;
                height: 8px;
            }
            QComboBox QAbstractItemView {
                background-color: #0f172a;
                color: #e2e8f0;
                border: 1px solid #334155;
                selection-background-color: #0ea5e9;
                selection-color: #f8fafc;
                outline: 0;
            }
            QLineEdit:focus {
                border: 1px solid #38bdf8;
            }
            QTableWidget {
                background-color: #0f172a;
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
            QPushButton#btnPay {
                background-color: #0ea5e9;
                border: 1px solid #38bdf8;
                color: #f8fafc;
                font-size: 16px;
            }
            QPushButton#btnPay:hover {
                background-color: #0284c7;
            }
            """
        )
