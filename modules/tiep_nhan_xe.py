from datetime import datetime
import re
import unicodedata

from PyQt5.QtCore import QTimer
from PyQt5.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QMessageBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from modules.service_orders import (
    list_orders,
    create_order,
    get_order,
    transition_order_status,
    update_order_services,
    add_material_requests_auto,
    mark_materials_exported,
)
from modules.audit_log import append_audit_log
from database.models import load_service_catalog, get_service_price_map, get_service_price, load_active_technician_names


class TiepNhanXeWidget(QWidget):
    def __init__(self, current_user="system"):
        super().__init__()
        self.current_user = current_user
        self.tech_pool = []
        self._orders_cache = []
        self._service_price_map = {}
        self._service_name_index = {}
        self._service_input_cache = ""
        self._service_combo_guard = False
        self._selected_order_id = ""
        self._build_ui()
        self._search_timer = QTimer(self)
        self._search_timer.setSingleShot(True)
        self._search_timer.setInterval(160)
        self._search_timer.timeout.connect(self._render_table)
        self._apply_style()
        self.refresh_data()

    def _build_ui(self):
        root = QVBoxLayout(self)
        title = QLabel("TIẾP NHẬN XE / LỆNH DỊCH VỤ")
        title.setObjectName("orderTitle")
        root.addWidget(title)

        search_row = QHBoxLayout()
        self.txt_search = QLineEdit()
        self.txt_search.setPlaceholderText("Tìm khách hàng / SĐT...")
        self.txt_search.textChanged.connect(self._on_search_text_changed)
        self.btn_clear_search = QPushButton("Xóa lọc")
        self.btn_clear_search.clicked.connect(lambda: self.txt_search.setText(""))
        search_row.addWidget(self.txt_search)
        search_row.addWidget(self.btn_clear_search)
        root.addLayout(search_row)

        form = QHBoxLayout()
        self.txt_customer = QLineEdit()
        self.txt_customer.setPlaceholderText("Khách hàng")
        self.txt_phone = QLineEdit()
        self.txt_phone.setPlaceholderText("SĐT")
        self.txt_plate = QLineEdit()
        self.txt_plate.setPlaceholderText("Biển số")
        self.txt_car_model = QLineEdit()
        self.txt_car_model.setPlaceholderText("Hãng xe")
        self.cmb_service = QComboBox()
        self.cmb_service.setEditable(True)
        self.cmb_service.setInsertPolicy(QComboBox.NoInsert)
        self.cmb_service.setPlaceholderText("Dịch vụ")
        if self.cmb_service.lineEdit():
            self.cmb_service.lineEdit().setPlaceholderText("Dịch vụ")
            self.cmb_service.lineEdit().textEdited.connect(self._on_service_text_edited)
        self.cmb_service.activated[str].connect(self._on_service_picked_from_dropdown)
        self._reload_service_combo()
        self.cmb_technician = QComboBox()
        self.cmb_technician.setEditable(True)
        self.cmb_technician.setInsertPolicy(QComboBox.NoInsert)
        self.cmb_technician.setPlaceholderText("Chọn KTV")
        if self.cmb_technician.lineEdit():
            self.cmb_technician.lineEdit().setPlaceholderText("Chọn KTV")
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
        form.addWidget(self.cmb_service)
        form.addWidget(self.cmb_technician)
        form.addWidget(self.btn_auto_tech)
        form.addWidget(self.btn_add)
        root.addLayout(form)

        action = QHBoxLayout()
        self.btn_quote = QPushButton("Đánh dấu Đã báo giá")
        self.btn_approve = QPushButton("Đánh dấu Đã duyệt")
        self.btn_done = QPushButton("Đánh dấu Hoàn tất")
        self.btn_edit_services = QPushButton("Chỉnh sửa dịch vụ")
        self.btn_wait_parts = QPushButton("Yêu cầu vật tư")
        self.btn_exported = QPushButton("Xác nhận xuất kho")
        for b in (self.btn_quote, self.btn_approve, self.btn_done, self.btn_edit_services, self.btn_wait_parts, self.btn_exported):
            b.setCheckable(True)
        self.btn_quote.clicked.connect(lambda: self._transition_selected("QUOTED"))
        self.btn_approve.clicked.connect(lambda: self._transition_selected("APPROVED"))
        self.btn_done.clicked.connect(lambda: self._transition_selected("DONE"))
        self.btn_edit_services.clicked.connect(self._edit_services_for_selected)
        self.btn_wait_parts.clicked.connect(self._request_parts_for_selected)
        self.btn_exported.clicked.connect(self._mark_parts_exported_selected)
        action.addWidget(self.btn_quote)
        action.addWidget(self.btn_approve)
        action.addWidget(self.btn_edit_services)
        action.addWidget(self.btn_wait_parts)
        action.addWidget(self.btn_exported)
        action.addWidget(self.btn_done)
        action.addStretch()
        root.addLayout(action)

        self.tbl = QTableWidget()
        self.tbl.setColumnCount(11)
        self.tbl.setHorizontalHeaderLabels(
            ["Mã lệnh", "Nguồn", "Khách hàng", "SĐT", "Hãng xe", "Biển số", "Dịch vụ", "Tổng giá thành", "KTV phụ trách", "Trạng thái", "Vật tư"]
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
        self.tbl.horizontalHeader().setSectionResizeMode(9, QHeaderView.ResizeToContents)
        self.tbl.horizontalHeader().setSectionResizeMode(10, QHeaderView.Stretch)
        self.tbl.itemSelectionChanged.connect(self._remember_current_selection)
        root.addWidget(self.tbl)

    def _apply_style(self):
        self.setStyleSheet(
            """
            QWidget { background: transparent; color: #dbeafe; }
            QLabel#orderTitle { color: #f8fafc; font-size: 18px; font-weight: 800; border: none; }
            QLineEdit { background:#0f172a; color:#e2e8f0; border:1px solid #334155; border-radius:8px; padding:6px; }
            QComboBox { background:#0f172a; color:#e2e8f0; border:1px solid #334155; border-radius:8px; padding:6px; }
            QComboBox QAbstractItemView {
                background:#0f172a;
                color:#e2e8f0;
                border:1px solid #334155;
                selection-background-color:#0ea5e9;
                selection-color:#f8fafc;
            }
            QPushButton { background:#1e293b; color:#e2e8f0; border:1px solid #334155; border-radius:10px; padding:8px; }
            QPushButton:checked { background:#0ea5e9; color:#f8fafc; border:1px solid #38bdf8; }
            QTableWidget { background:#0f172a; color:#e2e8f0; border:1px solid #334155; gridline-color:#1f2937; }
            QHeaderView::section { background:#1e293b; color:#bae6fd; border:0; padding:7px; font-weight:700; }
            """
        )

    def _reload_service_combo(self):
        current = self.cmb_service.currentText().strip() if hasattr(self, "cmb_service") else ""
        names = []
        try:
            rows = load_service_catalog(active_only=True)
            names = [str(x.get("service_name", "")).strip() for x in rows if str(x.get("service_name", "")).strip()]
        except Exception:
            names = []
        self.cmb_service.clear()
        self.cmb_service.addItem("")
        if names:
            self.cmb_service.addItems(sorted(set(names)))
        if current:
            self.cmb_service.setCurrentText(current)

    def _on_service_text_edited(self, text):
        self._service_input_cache = str(text or "")

    def _on_service_picked_from_dropdown(self, chosen):
        """Chọn một dòng trong dropdown: chỉ hiển thị đúng dịch vụ đó (không tự nối/chuỗi hóa)."""
        chosen = str(chosen or "").strip()
        if not chosen:
            return
        if self._service_combo_guard:
            return
        self._service_combo_guard = True
        try:
            self.cmb_service.setCurrentText(chosen)
            self._service_input_cache = chosen
        finally:
            self._service_combo_guard = False

    def _reload_service_price_map(self):
        try:
            self._service_price_map = get_service_price_map(active_only=True) or {}
            self._service_name_index = {
                self._normalize_text(name): name for name in self._service_price_map.keys() if str(name).strip()
            }
        except Exception:
            self._service_price_map = {}
            self._service_name_index = {}

    def refresh_service_catalog(self):
        """Gọi khi danh mục dịch vụ/BOM thay đổi (menu Quản lý dịch vụ)."""
        self._reload_service_combo()
        self._reload_service_price_map()

    @staticmethod
    def _format_vnd(value):
        return f"{int(value):,} đ".replace(",", ".")

    @staticmethod
    def _normalize_text(text):
        raw = str(text or "").strip().lower()
        if not raw:
            return ""
        raw = unicodedata.normalize("NFD", raw)
        raw = "".join(ch for ch in raw if unicodedata.category(ch) != "Mn")
        raw = raw.replace("đ", "d")
        raw = re.sub(r"[^a-z0-9]+", " ", raw)
        return re.sub(r"\s+", " ", raw).strip()

    def _match_service_name(self, token):
        norm = self._normalize_text(token)
        if not norm:
            return ""
        if norm in self._service_name_index:
            return self._service_name_index[norm]
        for key_norm, service_name in self._service_name_index.items():
            if norm in key_norm or key_norm in norm:
                return service_name
        return str(token or "").strip()

    def _parse_service_formula(self, text):
        raw = str(text or "").strip()
        if not raw:
            return []
        parts = re.split(r"[+,;/|]", raw)
        result = []
        for part in parts:
            token = str(part or "").strip()
            if not token:
                continue
            result.append(self._match_service_name(token))
        return [x for x in result if x]

    def _expand_services(self, services):
        expanded = []
        for item in services or []:
            raw = str(item or "").strip()
            if not raw:
                continue
            # If this is already an exact service in catalog (even contains '+'),
            # keep it as a single service item and do not split again.
            norm = self._normalize_text(raw)
            exact = self._service_name_index.get(norm, "")
            if exact:
                expanded.append(exact)
                continue
            expanded.extend(self._parse_service_formula(raw))
        return [x for x in expanded if x]

    def _calc_order_total_from_services(self, services):
        total = 0
        for service_name in self._expand_services(services):
            name = str(service_name or "").strip()
            if not name:
                continue
            mapped = int(self._service_price_map.get(name, 0))
            if mapped <= 0:
                mapped = int(get_service_price(name, default=0))
            total += mapped
        return total

    def _reload_technician_pool(self):
        try:
            self.tech_pool = list(load_active_technician_names())
        except Exception:
            self.tech_pool = []

    def _reload_technician_combo(self, orders=None):
        self._reload_technician_pool()
        current = self.cmb_technician.currentText().strip() if hasattr(self, "cmb_technician") else ""
        names = set(self.tech_pool)
        source_orders = orders if orders is not None else list(self._orders_cache)
        if not source_orders:
            source_orders = list_orders()
        try:
            for o in source_orders:
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
        # Chỉ cân bằng giữa KTV lấy từ DB (hr_employees); không dùng mã cũ kiểu NV001 trong combo.
        self._reload_technician_pool()
        candidates = sorted({str(x).strip() for x in self.tech_pool if str(x).strip()})
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

    def _get_selected_order_id(self):
        row = self.tbl.currentRow()
        if row < 0:
            return ""
        item = self.tbl.item(row, 0)
        return item.text().strip() if item else ""

    def _remember_current_selection(self):
        picked = self._get_selected_order_id()
        if picked:
            self._selected_order_id = picked

    def _restore_selection(self, preferred_order_id):
        target = str(preferred_order_id or "").strip()
        if not target:
            return
        for row in range(self.tbl.rowCount()):
            item = self.tbl.item(row, 0)
            if not item:
                continue
            if item.text().strip() == target:
                self.tbl.selectRow(row)
                self.tbl.setCurrentCell(row, 0)
                self.tbl.scrollToItem(item, QTableWidget.PositionAtCenter)
                self._selected_order_id = target
                return

    def refresh_data(self):
        keep_order_id = self._get_selected_order_id() or self._selected_order_id
        orders = list(reversed(list_orders()))
        self._orders_cache = orders
        self._reload_service_price_map()
        self._reload_service_combo()
        self._reload_technician_combo(orders)
        self._render_table(keep_order_id)

    def _on_search_text_changed(self):
        # Debounce typing to keep UI smooth on lower-end machines.
        self._search_timer.start()

    def _render_table(self, preferred_order_id=""):
        data = self._orders_cache
        keyword = (self.txt_search.text() if hasattr(self, "txt_search") else "").strip().lower()
        if keyword:
            data = [
                it
                for it in data
                if keyword in str(it.get("customer_name", "")).strip().lower()
                or keyword in str(it.get("customer_phone", "")).strip().lower()
            ]
        self.tbl.setRowCount(0)
        for row, it in enumerate(data):
            self.tbl.insertRow(row)
            self.tbl.setItem(row, 0, QTableWidgetItem(str(it.get("order_id", "-"))))
            self.tbl.setItem(row, 1, QTableWidgetItem(str(it.get("source", "-"))))
            self.tbl.setItem(row, 2, QTableWidgetItem(str(it.get("customer_name", ""))))
            self.tbl.setItem(row, 3, QTableWidgetItem(str(it.get("customer_phone", ""))))
            self.tbl.setItem(row, 4, QTableWidgetItem(str(it.get("car_model", ""))))
            self.tbl.setItem(row, 5, QTableWidgetItem(str(it.get("plate", ""))))
            services = it.get("services", []) or []
            self.tbl.setItem(row, 6, QTableWidgetItem(", ".join(services)))
            total_price = int(it.get("service_total") or 0)
            if total_price <= 0:
                service_items = it.get("service_items", []) or []
                if service_items:
                    total_price = sum(int(x.get("unit_price") or 0) for x in service_items)
            if total_price <= 0:
                total_price = self._calc_order_total_from_services(services)
            self.tbl.setItem(row, 7, QTableWidgetItem(self._format_vnd(total_price) if total_price > 0 else "Chưa báo giá"))
            self.tbl.setItem(row, 8, QTableWidgetItem(str(it.get("assigned_to", ""))))
            self.tbl.setItem(row, 9, QTableWidgetItem(str(it.get("status", ""))))
            parts = it.get("material_requests", []) or []
            pending = sum(1 for x in parts if not x.get("exported"))
            exported = sum(1 for x in parts if x.get("exported"))
            self.tbl.setItem(row, 10, QTableWidgetItem(f"chờ: {pending} | đã xuất: {exported}"))
        self._restore_selection(preferred_order_id)

    def create_manual_order(self):
        customer = (self.txt_customer.text() or "").strip() or "Khách lẻ"
        phone = (self.txt_phone.text() or "").strip()
        plate = (self.txt_plate.text() or "").strip()
        car_model = (self.txt_car_model.text() or "").strip()
        service = (self.cmb_service.currentText() or "").strip()
        services = self._parse_service_formula(service) if service else []
        services = [x for x in self._expand_services(services) if str(x or "").strip()]
        technician = (self.cmb_technician.currentText() or "").strip()
        if not technician:
            technician = self._pick_balanced_technician()
            if technician:
                self.cmb_technician.setCurrentText(technician)
        try:
            create_order(
                {
                    "customer_name": customer,
                    "customer_phone": phone,
                    "plate": plate,
                    "car_model": car_model,
                    "services": services,
                    "assigned_to": technician,
                    "source": "desk",
                    "status": "CHECKED_IN",
                    "actor": self.current_user,
                }
            )
        except ValueError as e:
            QMessageBox.warning(self, "Đủ số xe trong ngày", str(e))
            return
        append_audit_log(
            "service_order.create",
            self.current_user,
            {"customer_phone": phone, "plate": plate, "car_model": car_model, "assigned_to": technician},
        )
        self.btn_add.setChecked(True)
        self.btn_add.setText("Đã tạo lệnh")
        self.btn_auto_tech.setChecked(False)
        self.btn_auto_tech.setText("Tự phân công KTV")
        self.cmb_service.setCurrentText("")
        self._service_input_cache = ""
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

    def _edit_services_for_selected(self):
        row = self.tbl.currentRow()
        if row < 0:
            return
        order_id = (self.tbl.item(row, 0).text() if self.tbl.item(row, 0) else "").strip()
        if not order_id:
            return
        order = get_order(order_id)
        if not order:
            return

        dlg = QDialog(self)
        dlg.setWindowTitle(f"Chỉnh sửa dịch vụ - {order_id}")
        layout = QVBoxLayout(dlg)

        lbl = QLabel("Danh sách dịch vụ của lệnh:")
        layout.addWidget(lbl)

        list_services = QListWidget()
        for name in order.get("services", []) or []:
            list_services.addItem(QListWidgetItem(str(name)))
        layout.addWidget(list_services)

        row_add = QHBoxLayout()
        cmb = QComboBox()
        cmb.setEditable(True)
        cmb.setInsertPolicy(QComboBox.NoInsert)
        cmb.addItem("")
        for x in load_service_catalog(active_only=True) or []:
            n = str(x.get("service_name", "")).strip()
            if n:
                cmb.addItem(n)
        btn_plus = QPushButton("+ Thêm")
        btn_minus = QPushButton("- Bỏ đã chọn")
        row_add.addWidget(cmb, 1)
        row_add.addWidget(btn_plus)
        row_add.addWidget(btn_minus)
        layout.addLayout(row_add)

        txt_reason = QLineEdit()
        txt_reason.setPlaceholderText("Lý do chỉnh sửa (bắt buộc)")
        layout.addWidget(txt_reason)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        layout.addWidget(buttons)

        def _add():
            n = str(cmb.currentText() or "").strip()
            if n:
                list_services.addItem(QListWidgetItem(n))
                cmb.setCurrentText("")

        def _remove():
            idx = list_services.currentRow()
            if idx >= 0:
                list_services.takeItem(idx)

        btn_plus.clicked.connect(_add)
        btn_minus.clicked.connect(_remove)
        buttons.accepted.connect(dlg.accept)
        buttons.rejected.connect(dlg.reject)

        if dlg.exec_() != QDialog.Accepted:
            return

        reason = (txt_reason.text() or "").strip()
        if not reason:
            return
        services = [list_services.item(i).text().strip() for i in range(list_services.count()) if list_services.item(i)]
        services = [x for x in services if x]
        if not services:
            return

        try:
            update_order_services(order_id, services, actor=self.current_user, reason=reason)
            append_audit_log(
                "service_order.update_services",
                self.current_user,
                {"order_id": order_id, "services": services, "reason": reason},
            )
        except Exception:
            return

        self.btn_edit_services.setChecked(True)
        self.refresh_data()

    def _request_parts_for_selected(self):
        row = self.tbl.currentRow()
        if row < 0:
            QMessageBox.warning(self, "Chưa chọn lệnh", "Vui lòng chọn một lệnh dịch vụ trước khi yêu cầu vật tư.")
            return
        order_id = (self.tbl.item(row, 0).text() if self.tbl.item(row, 0) else "").strip()
        if not order_id:
            QMessageBox.warning(self, "Thiếu mã lệnh", "Không xác định được mã lệnh dịch vụ đang chọn.")
            return
        try:
            created = add_material_requests_auto(order_id, actor=self.current_user)
            try:
                transition_order_status(order_id, "WAITING_PARTS", actor=self.current_user, note="Chờ xuất kho vật tư")
            except Exception:
                pass
            append_audit_log(
                "service_order.request_parts",
                self.current_user,
                {"order_id": order_id, "items": created},
            )
            short = ", ".join(f"{x['item_name']} x{x['qty']}" for x in (created or [])[:4])
            if len(created) > 4:
                short += f", ...(+{len(created)-4})"
            QMessageBox.information(self, "Đã tạo yêu cầu vật tư", f"Đã gợi ý vật tư tự động:\n{short}")
        except ValueError as e:
            QMessageBox.warning(self, "Không thể gợi ý vật tư", str(e))
            return
        except Exception as e:
            QMessageBox.warning(self, "Lỗi yêu cầu vật tư", f"Không thể tạo yêu cầu vật tư cho lệnh {order_id}.\nChi tiết: {e}")
            return
        self.btn_wait_parts.setChecked(True)
        self.refresh_data()

    def _mark_parts_exported_selected(self):
        row = self.tbl.currentRow()
        if row < 0:
            QMessageBox.warning(self, "Chưa chọn lệnh", "Vui lòng chọn một lệnh dịch vụ trước khi xác nhận xuất kho.")
            return
        order_id = (self.tbl.item(row, 0).text() if self.tbl.item(row, 0) else "").strip()
        if not order_id:
            QMessageBox.warning(self, "Thiếu mã lệnh", "Không xác định được mã lệnh dịch vụ đang chọn.")
            return
        try:
            changed = mark_materials_exported(order_id, actor=self.current_user)
            if changed:
                try:
                    transition_order_status(order_id, "IN_SERVICE", actor=self.current_user, note="Đã có vật tư, tiếp tục thi công")
                except Exception:
                    pass
                append_audit_log("service_order.parts_exported", self.current_user, {"order_id": order_id})
            else:
                QMessageBox.information(self, "Không có vật tư chờ xuất", f"Lệnh {order_id} chưa có yêu cầu vật tư đang chờ xuất kho.")
        except ValueError as e:
            QMessageBox.warning(self, "Thiếu vật tư / Hết hàng", str(e))
            return
        except Exception as e:
            QMessageBox.warning(self, "Lỗi xuất kho", f"Không thể xác nhận xuất kho cho lệnh {order_id}.\nChi tiết: {e}")
            return
        self.btn_exported.setChecked(True)
        self.refresh_data()
