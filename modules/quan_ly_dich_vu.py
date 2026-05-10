"""Quản lý danh mục dịch vụ và định mức vật tư (BOM)."""

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QAbstractItemView,
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QSplitter,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from database.connection import ensure_mysql_ready
from database.models import (
    delete_service_bom_line,
    fetch_bom_lines_admin,
    insert_service_catalog_admin,
    list_service_catalog_admin,
    load_products,
    update_service_catalog_admin,
    upsert_service_bom_line,
)
from modules.audit_log import append_audit_log


class QuanLyDichVuWidget(QWidget):
    def __init__(self, on_catalog_changed=None):
        super().__init__()
        self.on_catalog_changed = on_catalog_changed
        self._selected_id = None
        self._products = []
        self._build_ui()
        self.reload_services_table()

    def _notify_changed(self):
        append_audit_log("service_catalog.changed", "quan_ly_dich_vu", {})
        if callable(self.on_catalog_changed):
            try:
                self.on_catalog_changed()
            except Exception:
                pass

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(0)

        header = QWidget()
        header.setMaximumHeight(62)
        hv = QVBoxLayout(header)
        hv.setContentsMargins(0, 0, 0, 0)
        hv.setSpacing(2)

        title = QLabel("DANH MỤC DỊCH VỤ & ĐỊNH MỨC VẬT TƯ")
        title.setStyleSheet("font-size: 17px; font-weight: 800; color: #f8fafc; padding: 0px; margin: 0px;")
        hv.addWidget(title)

        hint = QLabel(
            "Bật: dùng ở Tiếp nhận, POS, web. Tắt: ẩn khỏi chọn — không ảnh hưởng lịch sử lệnh."
        )
        hint.setWordWrap(False)
        hint.setStyleSheet(
            "color: #94a3b8; font-size: 11px; padding: 0px; margin: 0px; line-height: 1.15;"
        )
        hv.addWidget(hint)
        layout.addWidget(header)

        layout.addSpacing(8)

        top = QHBoxLayout()
        self.chk_inactive = QCheckBox("Hiển thị cả dịch vụ đã tắt")
        self.chk_inactive.stateChanged.connect(self.reload_services_table)
        top.addWidget(self.chk_inactive)
        btn_refresh = QPushButton("Làm mới")
        btn_refresh.clicked.connect(self.reload_services_table)
        top.addWidget(btn_refresh)
        btn_add = QPushButton("+ Thêm dịch vụ")
        btn_add.clicked.connect(self._add_service_dialog)
        top.addWidget(btn_add)
        top.addStretch()
        layout.addLayout(top)

        splitter = QSplitter(Qt.Horizontal)

        left = QWidget()
        ll = QVBoxLayout(left)
        ll.addWidget(QLabel("Danh sách dịch vụ"))
        self.tbl_services = QTableWidget()
        self.tbl_services.setColumnCount(5)
        self.tbl_services.setHorizontalHeaderLabels(["id", "Mã", "Tên dịch vụ", "Giá (đ)", "Hiệu lực"])
        self.tbl_services.setColumnHidden(0, True)
        self.tbl_services.verticalHeader().setVisible(False)
        self.tbl_services.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.tbl_services.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.tbl_services.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        self.tbl_services.itemSelectionChanged.connect(self._on_service_selected)
        ll.addWidget(self.tbl_services)

        right = QWidget()
        rl = QVBoxLayout(right)

        grp_detail = QGroupBox("Chi tiết dịch vụ")
        form = QFormLayout()
        self.txt_code = QLineEdit()
        self.txt_name = QLineEdit()
        self.txt_price = QLineEdit()
        self.txt_price.setPlaceholderText("VND")
        self.chk_active = QCheckBox("Đang hoạt động")
        self.chk_active.setChecked(True)
        form.addRow("Mã:", self.txt_code)
        form.addRow("Tên:", self.txt_name)
        form.addRow("Giá:", self.txt_price)
        form.addRow("", self.chk_active)
        row_btn = QHBoxLayout()
        self.btn_save_svc = QPushButton("Lưu thông tin dịch vụ")
        self.btn_save_svc.clicked.connect(self._save_service_detail)
        row_btn.addWidget(self.btn_save_svc)
        form.addRow(row_btn)
        grp_detail.setLayout(form)
        rl.addWidget(grp_detail)

        grp_bom = QGroupBox("Định mức vật tư (BOM) — xuất kho khi yêu cầu vật tư")
        bl = QVBoxLayout()
        self.lbl_bom_hint = QLabel("Chọn một dịch vụ bên trái để chỉnh BOM.")
        self.lbl_bom_hint.setStyleSheet("color:#94a3b8;")
        bl.addWidget(self.lbl_bom_hint)

        add_row = QHBoxLayout()
        self.cmb_product = QComboBox()
        self.spin_qty = QSpinBox()
        self.spin_qty.setMinimum(1)
        self.spin_qty.setMaximum(99999)
        self.spin_qty.setValue(1)
        self.btn_add_bom = QPushButton("Thêm vật tư")
        self.btn_add_bom.clicked.connect(self._add_bom_line)
        add_row.addWidget(QLabel("Vật tư:"))
        add_row.addWidget(self.cmb_product, 2)
        add_row.addWidget(QLabel("SL:"))
        add_row.addWidget(self.spin_qty)
        add_row.addWidget(self.btn_add_bom)
        bl.addLayout(add_row)

        self.tbl_bom = QTableWidget()
        self.tbl_bom.setColumnCount(4)
        self.tbl_bom.setHorizontalHeaderLabels(["bom_id", "Mã SP", "Tên vật tư", "SL"])
        self.tbl_bom.setColumnHidden(0, True)
        self.tbl_bom.verticalHeader().setVisible(False)
        self.tbl_bom.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.tbl_bom.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.tbl_bom.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        bl.addWidget(self.tbl_bom)

        btn_del_bom = QPushButton("Xóa dòng BOM đã chọn")
        btn_del_bom.clicked.connect(self._delete_bom_selected)
        bl.addWidget(btn_del_bom)
        grp_bom.setLayout(bl)
        rl.addWidget(grp_bom)

        splitter.addWidget(left)
        splitter.addWidget(right)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 1)
        layout.addWidget(splitter)

        self._load_product_combo()
        self._apply_style()

    def _apply_style(self):
        self.setStyleSheet(
            """
            QWidget { background: transparent; color: #dbeafe; font-family: "Segoe UI","Inter"; }
            QGroupBox { font-weight: 700; color: #bae6fd; border: 1px solid #334155; border-radius: 10px; margin-top: 10px; padding-top: 10px; }
            QLineEdit, QComboBox, QSpinBox {
                background: #0f172a; color: #e2e8f0; border: 1px solid #334155; border-radius: 8px; padding: 6px;
            }
            QTableWidget { background: #0f172a; color: #e2e8f0; border: 1px solid #334155; gridline-color: #1f2937; }
            QHeaderView::section { background: #1e293b; color: #bae6fd; border: 0; padding: 7px; font-weight: 700; }
            QPushButton { background: #1e293b; color: #e2e8f0; border: 1px solid #334155; border-radius: 10px; padding: 8px 12px; font-weight: 700; }
            QPushButton:hover { background: #0ea5e9; border-color: #38bdf8; color: #f8fafc; }
            """
        )

    def _load_product_combo(self):
        self.cmb_product.clear()
        self._products = []
        try:
            ensure_mysql_ready()
            self._products = load_products() or []
        except Exception:
            self._products = []
        for p in self._products:
            pid = int(p.get("id") or 0)
            code = str(p.get("product_code") or "").strip()
            name = str(p.get("name") or "").strip()
            label = f"{code} — {name}" if code else name
            self.cmb_product.addItem(label, pid)

    def reload_services_table(self):
        try:
            ensure_mysql_ready()
            include = self.chk_inactive.isChecked()
            rows = list_service_catalog_admin(include_inactive=include)
        except Exception as exc:
            QMessageBox.warning(self, "Lỗi", str(exc))
            rows = []
        self.tbl_services.setRowCount(len(rows))
        for i, r in enumerate(rows):
            sid = int(r.get("id") or 0)
            self.tbl_services.setItem(i, 0, QTableWidgetItem(str(sid)))
            self.tbl_services.setItem(i, 1, QTableWidgetItem(str(r.get("service_code") or "")))
            self.tbl_services.setItem(i, 2, QTableWidgetItem(str(r.get("service_name") or "")))
            price = int(float(r.get("price") or 0))
            self.tbl_services.setItem(i, 3, QTableWidgetItem(f"{price:,}".replace(",", ".")))
            active = bool(r.get("is_active"))
            self.tbl_services.setItem(i, 4, QTableWidgetItem("Có" if active else "Không"))
            if not active:
                for c in range(5):
                    it = self.tbl_services.item(i, c)
                    if it:
                        it.setForeground(Qt.gray)

    def _current_service_id_from_table(self):
        r = self.tbl_services.currentRow()
        if r < 0:
            return None
        it = self.tbl_services.item(r, 0)
        if not it:
            return None
        try:
            return int(it.text())
        except ValueError:
            return None

    def _on_service_selected(self):
        sid = self._current_service_id_from_table()
        self._selected_id = sid
        if not sid:
            self.lbl_bom_hint.setText("Chọn một dịch vụ bên trái để chỉnh BOM.")
            self.tbl_bom.setRowCount(0)
            return
        row = None
        for i in range(self.tbl_services.rowCount()):
            it = self.tbl_services.item(i, 0)
            if it and int(it.text()) == sid:
                row = i
                break
        if row is None:
            return
        self.txt_code.setText(self.tbl_services.item(row, 1).text() if self.tbl_services.item(row, 1) else "")
        self.txt_name.setText(self.tbl_services.item(row, 2).text() if self.tbl_services.item(row, 2) else "")
        ptxt = self.tbl_services.item(row, 3).text() if self.tbl_services.item(row, 3) else "0"
        ptxt = ptxt.replace(".", "").replace(",", "")
        try:
            self.txt_price.setText(str(int(ptxt)))
        except ValueError:
            self.txt_price.setText("0")
        act = self.tbl_services.item(row, 4)
        self.chk_active.setChecked(act is not None and act.text() == "Có")

        self.lbl_bom_hint.setText(f"BOM cho dịch vụ id={sid}")
        self._reload_bom_table(sid)

    def _reload_bom_table(self, catalog_id):
        self.tbl_bom.setRowCount(0)
        try:
            lines = fetch_bom_lines_admin(catalog_id)
        except Exception as exc:
            QMessageBox.warning(self, "Lỗi BOM", str(exc))
            return
        self.tbl_bom.setRowCount(len(lines))
        for i, ln in enumerate(lines):
            self.tbl_bom.setItem(i, 0, QTableWidgetItem(str(int(ln.get("bom_id") or 0))))
            self.tbl_bom.setItem(i, 1, QTableWidgetItem(str(ln.get("product_code") or "")))
            self.tbl_bom.setItem(i, 2, QTableWidgetItem(str(ln.get("product_name") or "")))
            self.tbl_bom.setItem(i, 3, QTableWidgetItem(str(int(ln.get("qty") or 1))))

    def _save_service_detail(self):
        sid = self._selected_id or self._current_service_id_from_table()
        if not sid:
            QMessageBox.warning(self, "Thiếu dữ liệu", "Chọn dịch vụ trong bảng trước.")
            return
        try:
            price = int(float(str(self.txt_price.text()).replace(",", "").replace(".", "") or 0))
        except ValueError:
            QMessageBox.warning(self, "Giá không hợp lệ", "Nhập số nguyên VND.")
            return
        try:
            update_service_catalog_admin(
                sid,
                self.txt_code.text().strip(),
                self.txt_name.text().strip(),
                float(price),
                self.chk_active.isChecked(),
            )
        except Exception as exc:
            QMessageBox.warning(self, "Không lưu được", str(exc))
            return
        QMessageBox.information(self, "Đã lưu", "Đã cập nhật danh mục dịch vụ.")
        self.reload_services_table()
        self._notify_changed()

    def _add_service_dialog(self):
        dlg = QDialog(self)
        dlg.setWindowTitle("Thêm dịch vụ mới")
        fl = QFormLayout(dlg)
        txt_name = QLineEdit()
        txt_code = QLineEdit()
        txt_code.setPlaceholderText("Để trống để hệ thống sinh mã")
        txt_price = QLineEdit()
        txt_price.setText("0")
        fl.addRow("Tên dịch vụ *:", txt_name)
        fl.addRow("Mã (tuỳ chọn):", txt_code)
        fl.addRow("Giá (VND):", txt_price)
        bb = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        fl.addRow(bb)
        bb.accepted.connect(dlg.accept)
        bb.rejected.connect(dlg.reject)
        if dlg.exec_() != QDialog.Accepted:
            return
        name = txt_name.text().strip()
        if not name:
            QMessageBox.warning(self, "Thiếu tên", "Nhập tên dịch vụ.")
            return
        try:
            price = int(float(str(txt_price.text()).replace(",", "").replace(".", "") or 0))
        except ValueError:
            QMessageBox.warning(self, "Giá", "Nhập số hợp lệ.")
            return
        try:
            insert_service_catalog_admin(txt_code.text().strip(), name, float(price))
        except Exception as exc:
            QMessageBox.warning(self, "Không thêm được", str(exc))
            return
        QMessageBox.information(self, "Đã thêm", "Đã thêm dịch vụ mới.")
        self.reload_services_table()
        self._notify_changed()

    def _add_bom_line(self):
        sid = self._selected_id or self._current_service_id_from_table()
        if not sid:
            QMessageBox.warning(self, "Chọn dịch vụ", "Chọn một dịch vụ ở bảng trái.")
            return
        pid = self.cmb_product.currentData()
        if pid is None or int(pid) <= 0:
            QMessageBox.warning(self, "Vật tư", "Chọn sản phẩm trong kho.")
            return
        qty = self.spin_qty.value()
        try:
            upsert_service_bom_line(int(sid), int(pid), qty, "")
        except Exception as exc:
            QMessageBox.warning(self, "Lỗi", str(exc))
            return
        self._reload_bom_table(sid)
        self._notify_changed()

    def _delete_bom_selected(self):
        sid = self._selected_id or self._current_service_id_from_table()
        r = self.tbl_bom.currentRow()
        if r < 0 or not sid:
            QMessageBox.warning(self, "Chọn dòng", "Chọn một dòng trong bảng BOM.")
            return
        it = self.tbl_bom.item(r, 0)
        if not it:
            return
        try:
            bom_id = int(it.text())
        except ValueError:
            return
        reply = QMessageBox.question(
            self,
            "Xác nhận",
            "Xóa dòng định mức này?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if reply != QMessageBox.Yes:
            return
        try:
            delete_service_bom_line(bom_id)
        except Exception as exc:
            QMessageBox.warning(self, "Lỗi", str(exc))
            return
        self._reload_bom_table(sid)
        self._notify_changed()
