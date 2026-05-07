from datetime import datetime

from PyQt5.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from modules.service_orders import (
    list_orders,
    create_order,
    transition_order_status,
    add_material_request,
    mark_materials_exported,
)
from modules.audit_log import append_audit_log


class TiepNhanXeWidget(QWidget):
    def __init__(self, current_user="system"):
        super().__init__()
        self.current_user = current_user
        self.tech_pool = ["Nguyen Minh Dat", "Le Quoc Khanh", "Pham Van Phuc"]
        self._build_ui()
        self._apply_style()
        self.refresh_data()

    def _build_ui(self):
        root = QVBoxLayout(self)
        title = QLabel("TIẾP NHẬN XE / LỆNH DỊCH VỤ")
        title.setObjectName("orderTitle")
        root.addWidget(title)

        form = QHBoxLayout()
        self.txt_customer = QLineEdit()
        self.txt_customer.setPlaceholderText("Khách hàng")
        self.txt_phone = QLineEdit()
        self.txt_phone.setPlaceholderText("SĐT")
        self.txt_plate = QLineEdit()
        self.txt_plate.setPlaceholderText("Biển số")
        self.txt_car_model = QLineEdit()
        self.txt_car_model.setPlaceholderText("Hãng xe")
        self.txt_service = QLineEdit()
        self.txt_service.setPlaceholderText("Dịch vụ")
        self.cmb_technician = QComboBox()
        self.cmb_technician.setEditable(True)
        self.cmb_technician.setInsertPolicy(QComboBox.NoInsert)
        self._reload_technician_combo()
        self.btn_auto_tech = QPushButton("Tự phân công KTV")
        self.btn_auto_tech.setCheckable(True)
        self.btn_auto_tech.clicked.connect(self._auto_assign_technician_for_input)
        self.btn_add = QPushButton("Tạo lệnh")
        self.btn_add.setCheckable(True)
        self.btn_add.clicked.connect(self.create_manual_order)
        form.addWidget(self.txt_customer)
        form.addWidget(self.txt_phone)
        form.addWidget(self.txt_plate)
        form.addWidget(self.txt_car_model)
        form.addWidget(self.txt_service)
        form.addWidget(self.cmb_technician)
        form.addWidget(self.btn_auto_tech)
        form.addWidget(self.btn_add)
        root.addLayout(form)

        action = QHBoxLayout()
        self.btn_quote = QPushButton("Đánh dấu Đã báo giá")
        self.btn_approve = QPushButton("Đánh dấu Đã duyệt")
        self.btn_done = QPushButton("Đánh dấu Hoàn tất")
        self.btn_wait_parts = QPushButton("Yêu cầu vật tư")
        self.btn_exported = QPushButton("Xác nhận xuất kho")
        for b in (self.btn_quote, self.btn_approve, self.btn_done, self.btn_wait_parts, self.btn_exported):
            b.setCheckable(True)
        self.btn_quote.clicked.connect(lambda: self._transition_selected("QUOTED"))
        self.btn_approve.clicked.connect(lambda: self._transition_selected("APPROVED"))
        self.btn_done.clicked.connect(lambda: self._transition_selected("DONE"))
        self.btn_wait_parts.clicked.connect(self._request_parts_for_selected)
        self.btn_exported.clicked.connect(self._mark_parts_exported_selected)
        action.addWidget(self.btn_quote)
        action.addWidget(self.btn_approve)
        action.addWidget(self.btn_wait_parts)
        action.addWidget(self.btn_exported)
        action.addWidget(self.btn_done)
        action.addStretch()
        root.addLayout(action)

        self.tbl = QTableWidget()
        self.tbl.setColumnCount(10)
        self.tbl.setHorizontalHeaderLabels(
            ["Mã lệnh", "Nguồn", "Khách hàng", "SĐT", "Hãng xe", "Biển số", "Dịch vụ", "KTV phụ trách", "Trạng thái", "Vật tư"]
        )
        self.tbl.verticalHeader().setVisible(False)
        self.tbl.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.tbl.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.tbl.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        self.tbl.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)
        self.tbl.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeToContents)
        self.tbl.horizontalHeader().setSectionResizeMode(5, QHeaderView.ResizeToContents)
        self.tbl.horizontalHeader().setSectionResizeMode(6, QHeaderView.Stretch)
        self.tbl.horizontalHeader().setSectionResizeMode(7, QHeaderView.ResizeToContents)
        self.tbl.horizontalHeader().setSectionResizeMode(8, QHeaderView.ResizeToContents)
        self.tbl.horizontalHeader().setSectionResizeMode(9, QHeaderView.Stretch)
        root.addWidget(self.tbl)

    def _apply_style(self):
        self.setStyleSheet(
            """
            QWidget { background: transparent; color: #dbeafe; }
            QLabel#orderTitle { color: #f8fafc; font-size: 18px; font-weight: 800; border: none; }
            QLineEdit { background:#0f172a; color:#e2e8f0; border:1px solid #334155; border-radius:8px; padding:6px; }
            QPushButton { background:#1e293b; color:#e2e8f0; border:1px solid #334155; border-radius:10px; padding:8px; }
            QPushButton:checked { background:#0ea5e9; color:#f8fafc; border:1px solid #38bdf8; }
            QTableWidget { background:#0f172a; color:#e2e8f0; border:1px solid #334155; gridline-color:#1f2937; }
            QHeaderView::section { background:#1e293b; color:#bae6fd; border:0; padding:7px; font-weight:700; }
            """
        )

    def _reload_technician_combo(self):
        current = self.cmb_technician.currentText().strip() if hasattr(self, "cmb_technician") else ""
        names = set(self.tech_pool)
        try:
            for o in list_orders():
                n = str(o.get("assigned_to", "")).strip()
                if n:
                    names.add(n)
        except Exception:
            pass
        items = sorted(names)
        self.cmb_technician.clear()
        self.cmb_technician.addItem("")
        self.cmb_technician.addItems(items)
        if current and current in items:
            self.cmb_technician.setCurrentText(current)

    def _current_shift_label(self):
        hour = datetime.now().hour
        if 6 <= hour < 12:
            return "Sáng"
        if 12 <= hour < 18:
            return "Chiều"
        return "Tối"

    def _pick_balanced_technician(self):
        self._reload_technician_combo()
        candidates = [self.cmb_technician.itemText(i).strip() for i in range(1, self.cmb_technician.count())]
        candidates = [x for x in candidates if x]
        if not candidates:
            return ""
        today = datetime.now().strftime("%d/%m/%Y")
        counts = {name: 0 for name in candidates}
        for o in list_orders():
            assigned = str(o.get("assigned_to", "")).strip()
            if assigned not in counts:
                continue
            created_at = str(o.get("created_at", ""))
            status = str(o.get("status", ""))
            # Cân bằng tải theo số lệnh còn xử lý trong ngày.
            if not created_at.startswith(today):
                continue
            if status in {"PAID", "AFTERCARE", "CANCELLED"}:
                continue
            counts[assigned] += 1
        best = sorted(candidates, key=lambda n: (counts.get(n, 0), n))[0]
        return best

    def _auto_assign_technician_for_input(self):
        chosen = self._pick_balanced_technician()
        if chosen:
            self.cmb_technician.setCurrentText(chosen)
            self.btn_auto_tech.setText(f"Tự phân công KTV ({self._current_shift_label()}): {chosen}")
            self.btn_auto_tech.setChecked(True)
        else:
            self.btn_auto_tech.setText("Tự phân công KTV")
            self.btn_auto_tech.setChecked(False)

    def refresh_data(self):
        self._reload_technician_combo()
        data = list(reversed(list_orders()))
        self.tbl.setRowCount(0)
        for row, it in enumerate(data):
            self.tbl.insertRow(row)
            self.tbl.setItem(row, 0, QTableWidgetItem(str(it.get("order_id", "-"))))
            self.tbl.setItem(row, 1, QTableWidgetItem(str(it.get("source", "-"))))
            self.tbl.setItem(row, 2, QTableWidgetItem(str(it.get("customer_name", ""))))
            self.tbl.setItem(row, 3, QTableWidgetItem(str(it.get("customer_phone", ""))))
            self.tbl.setItem(row, 4, QTableWidgetItem(str(it.get("car_model", ""))))
            self.tbl.setItem(row, 5, QTableWidgetItem(str(it.get("plate", ""))))
            self.tbl.setItem(row, 6, QTableWidgetItem(", ".join(it.get("services", []))))
            self.tbl.setItem(row, 7, QTableWidgetItem(str(it.get("assigned_to", ""))))
            self.tbl.setItem(row, 8, QTableWidgetItem(str(it.get("status", ""))))
            parts = it.get("material_requests", []) or []
            pending = sum(1 for x in parts if not x.get("exported"))
            exported = sum(1 for x in parts if x.get("exported"))
            self.tbl.setItem(row, 9, QTableWidgetItem(f"chờ: {pending} | đã xuất: {exported}"))

    def create_manual_order(self):
        customer = (self.txt_customer.text() or "").strip() or "Khách lẻ"
        phone = (self.txt_phone.text() or "").strip()
        plate = (self.txt_plate.text() or "").strip()
        car_model = (self.txt_car_model.text() or "").strip()
        service = (self.txt_service.text() or "").strip()
        technician = (self.cmb_technician.currentText() or "").strip()
        if not technician:
            technician = self._pick_balanced_technician()
            if technician:
                self.cmb_technician.setCurrentText(technician)
        create_order(
            {
                "customer_name": customer,
                "customer_phone": phone,
                "plate": plate,
                "car_model": car_model,
                "services": [service] if service else [],
                "assigned_to": technician,
                "source": "desk",
                "status": "CHECKED_IN",
                "actor": self.current_user,
            }
        )
        append_audit_log(
            "service_order.create",
            self.current_user,
            {"customer_phone": phone, "plate": plate, "car_model": car_model, "assigned_to": technician},
        )
        self.btn_add.setChecked(True)
        self.btn_add.setText("Đã tạo lệnh")
        self.btn_auto_tech.setChecked(False)
        self.btn_auto_tech.setText("Tự phân công KTV")
        self.refresh_data()

    def _transition_selected(self, to_status):
        row = self.tbl.currentRow()
        if row < 0:
            return
        item = self.tbl.item(row, 0)
        if not item:
            return
        order_id = item.text()
        try:
            transition_order_status(order_id, to_status, actor=self.current_user)
            append_audit_log("service_order.transition", self.current_user, {"order_id": order_id, "to": to_status})
        except Exception:
            return
        mapping = {"QUOTED": self.btn_quote, "APPROVED": self.btn_approve, "DONE": self.btn_done}
        for b in (self.btn_quote, self.btn_approve, self.btn_done):
            b.setChecked(False)
        if to_status in mapping:
            mapping[to_status].setChecked(True)
        self.refresh_data()

    def _request_parts_for_selected(self):
        row = self.tbl.currentRow()
        if row < 0:
            return
        order_id = (self.tbl.item(row, 0).text() if self.tbl.item(row, 0) else "").strip()
        service_name = (self.tbl.item(row, 5).text() if self.tbl.item(row, 5) else "").strip()
        if not order_id:
            return
        try:
            add_material_request(order_id, service_name or "Vật tư dịch vụ", 1, actor=self.current_user)
            try:
                transition_order_status(order_id, "WAITING_PARTS", actor=self.current_user, note="Chờ xuất kho vật tư")
            except Exception:
                pass
            append_audit_log("service_order.request_parts", self.current_user, {"order_id": order_id, "item": service_name})
        except Exception:
            return
        self.btn_wait_parts.setChecked(True)
        self.refresh_data()

    def _mark_parts_exported_selected(self):
        row = self.tbl.currentRow()
        if row < 0:
            return
        order_id = (self.tbl.item(row, 0).text() if self.tbl.item(row, 0) else "").strip()
        if not order_id:
            return
        try:
            changed = mark_materials_exported(order_id, actor=self.current_user)
            if changed:
                try:
                    transition_order_status(order_id, "IN_SERVICE", actor=self.current_user, note="Đã có vật tư, tiếp tục thi công")
                except Exception:
                    pass
                append_audit_log("service_order.parts_exported", self.current_user, {"order_id": order_id})
        except Exception:
            return
        self.btn_exported.setChecked(True)
        self.refresh_data()
