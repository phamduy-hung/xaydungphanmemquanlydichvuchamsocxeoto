from datetime import datetime
import re
import unicodedata

from PyQt5.QtCore import QTimer
from PyQt5.QtGui import QColor
from PyQt5.QtWidgets import (
    QCheckBox,
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
    def __init__(self, current_user="system", current_role="Quản lý"):
        super().__init__()
        self.current_user = current_user
        self.current_role = current_role
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
        self.btn_clear_search.setObjectName("btn_clear_search")
        self.btn_clear_search.clicked.connect(lambda: self.txt_search.setText(""))
        self.chk_show_cancelled = QCheckBox("Hiển thị lệnh đã hủy")
        self.chk_show_cancelled.setChecked(False)
        self.chk_show_cancelled.stateChanged.connect(self._on_search_text_changed)
        search_row.addWidget(self.txt_search)
        search_row.addWidget(self.btn_clear_search)
        search_row.addWidget(self.chk_show_cancelled)
        root.addLayout(search_row)

        form = QHBoxLayout()
        self.txt_customer = QLineEdit()
        self.txt_customer.setPlaceholderText("Khách hàng")
        self.txt_phone = QLineEdit()
        self.txt_phone.setPlaceholderText("SĐT")
        self.txt_phone.textChanged.connect(self._on_phone_text_changed)
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
        self.btn_auto_tech.setObjectName("btn_auto_tech")
        self.btn_auto_tech.setCheckable(True)
        self.btn_auto_tech.clicked.connect(self._auto_assign_technician_for_input)
        self.btn_add = QPushButton("Tạo lệnh")
        self.btn_add.setObjectName("btnIntakeAdd")
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
        self.btn_checkin = QPushButton("Nhận xe vào xưởng")
        self.btn_checkin.setObjectName("btn_checkin_order")
        self.btn_quote = QPushButton("Đánh dấu Đã báo giá")
        self.btn_approve = QPushButton("Đánh dấu Đã duyệt")
        self.btn_done = QPushButton("Đánh dấu Hoàn tất")
        self.btn_edit_services = QPushButton("Chỉnh sửa dịch vụ")
        self.btn_wait_parts = QPushButton("Yêu cầu vật tư")
        self.btn_exported = QPushButton("Xác nhận xuất kho")
        self.btn_cancel = QPushButton("Hủy lệnh")
        self.btn_cancel.setObjectName("btn_cancel_order")
        for b in (self.btn_checkin, self.btn_quote, self.btn_approve, self.btn_done, self.btn_edit_services, self.btn_wait_parts, self.btn_exported, self.btn_cancel):
            b.setCheckable(True)
        self.btn_checkin.clicked.connect(lambda: self._transition_selected("CHECKED_IN"))
        self.btn_quote.clicked.connect(lambda: self._transition_selected("QUOTED"))
        self.btn_approve.clicked.connect(lambda: self._transition_selected("APPROVED"))
        self.btn_done.clicked.connect(lambda: self._transition_selected("DONE"))
        self.btn_edit_services.clicked.connect(self._edit_services_for_selected)
        self.btn_wait_parts.clicked.connect(self._request_parts_for_selected)
        self.btn_exported.clicked.connect(self._mark_parts_exported_selected)
        self.btn_cancel.clicked.connect(self._cancel_selected_order)
        action.addWidget(self.btn_checkin)
        action.addWidget(self.btn_quote)
        action.addWidget(self.btn_approve)
        action.addWidget(self.btn_edit_services)
        action.addWidget(self.btn_wait_parts)
        action.addWidget(self.btn_exported)
        action.addWidget(self.btn_done)
        action.addWidget(self.btn_cancel)
        action.addStretch()
        root.addLayout(action)

        self.tbl = QTableWidget()
        self.tbl.setColumnCount(12)
        self.tbl.setHorizontalHeaderLabels(
            ["Mã lệnh", "Nguồn", "Thời gian tạo", "Khách hàng", "SĐT", "Hãng xe", "Biển số", "Dịch vụ", "Tổng giá thành", "KTV phụ trách", "Trạng thái", "Vật tư"]
        )
        self.tbl.verticalHeader().setVisible(False)
        self.tbl.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.tbl.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.tbl.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.tbl.horizontalHeader().setSectionResizeMode(3, QHeaderView.Stretch)
        self.tbl.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeToContents)
        self.tbl.horizontalHeader().setSectionResizeMode(5, QHeaderView.ResizeToContents)
        self.tbl.horizontalHeader().setSectionResizeMode(6, QHeaderView.ResizeToContents)
        self.tbl.horizontalHeader().setSectionResizeMode(7, QHeaderView.Stretch)
        self.tbl.horizontalHeader().setSectionResizeMode(8, QHeaderView.ResizeToContents)
        self.tbl.horizontalHeader().setSectionResizeMode(9, QHeaderView.ResizeToContents)
        self.tbl.horizontalHeader().setSectionResizeMode(10, QHeaderView.ResizeToContents)
        self.tbl.horizontalHeader().setSectionResizeMode(11, QHeaderView.Stretch)
        self.tbl.itemSelectionChanged.connect(self._remember_current_selection)
        root.addWidget(self.tbl)

    def _apply_style(self):
        self.setStyleSheet(
            """
            QWidget { background: transparent; color: #e2e8f0; font-family: "Segoe UI", "Inter"; }
            QLabel#orderTitle { color: #f8fafc; font-size: 20px; font-weight: 800; border: none; padding-bottom: 5px; }
            QLineEdit { background:#0c101a; color:#f8fafc; border:1px solid #27354a; border-radius:8px; padding:7px 10px; }
            QLineEdit:focus { border:1px solid #0ea5e9; }
            QComboBox { background:#0c101a; color:#f8fafc; border:1px solid #27354a; border-radius:8px; padding:6px 10px; }
            QComboBox:focus { border:1px solid #0ea5e9; }
            QComboBox QAbstractItemView {
                background:#0c101a;
                color:#f8fafc;
                border:1px solid #27354a;
                selection-background-color:#0ea5e9;
                selection-color:#f8fafc;
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
                background-color: #0ea5e9;
                border: 1px solid #38bdf8;
                color: #ffffff;
            }
            QPushButton#btnIntakeAdd {
                background-color: #f97316;
                color: #ffffff;
                border: 1px solid #ff7a22;
            }
            QPushButton#btnIntakeAdd:hover {
                background-color: #ea580c;
                border: 1px solid #f97316;
            }
            QPushButton:checked {
                background-color: #0ea5e9;
                color: #ffffff;
                border: 1px solid #38bdf8;
            }
            QPushButton#btnIntakeAdd:checked {
                background-color: #10b981;
                border: 1px solid #34d399;
            }
            QPushButton#btn_cancel_order {
                background-color: #311c1c;
                color: #ef4444;
                border: 1px solid #7f1d1d;
            }
            QPushButton#btn_cancel_order:hover {
                background-color: #7f1d1d;
                color: #fca5a5;
                border: 1px solid #b91c1c;
            }
            QPushButton#btn_checkin_order {
                background-color: #1e1b4b;
                color: #818cf8;
                border: 1px solid #3730a3;
            }
            QPushButton#btn_checkin_order:hover {
                background-color: #3730a3;
                color: #e0e7ff;
                border: 1px solid #4338ca;
            }
            QTableWidget {
                background-color: #0c101a;
                alternate-background-color: #121824;
                color: #e2e8f0;
                border: 1px solid #222e44;
                gridline-color: #1b2336;
                selection-background-color: #0ea5e9;
                selection-color: #f8fafc;
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
                border-bottom: 2px solid #222e44;
            }
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
        """Chọn một dòng trong dropdown: hỗ trợ chọn nhiều dịch vụ, nối tiếp vào dịch vụ trước bằng dấu +."""
        chosen = str(chosen or "").strip()
        if not chosen:
            return
        if self._service_combo_guard:
            return
        self._service_combo_guard = True
        try:
            current_text = str(self._service_input_cache or "").strip()
            if current_text:
                # Tránh trùng lặp: tách các phần đã có theo các dấu phân tách (+ , ; / |)
                import re
                parts = [p.strip() for p in re.split(r"[+,;/|]", current_text)]
                if chosen not in parts:
                    new_text = f"{current_text} + {chosen}"
                else:
                    new_text = current_text
            else:
                new_text = chosen
            self.cmb_service.setCurrentText(new_text)
            self._service_input_cache = new_text
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
        
        text_norm = self._normalize_text(raw)
        if not text_norm:
            return []
            
        # Lấy danh sách dịch vụ đang hoạt động
        active_services = list(self._service_price_map.keys())
        if not active_services:
            try:
                rows = load_service_catalog(active_only=True)
                active_services = [str(x.get("service_name", "")).strip() for x in rows if str(x.get("service_name", "")).strip()]
            except Exception:
                active_services = []
                
        # Sắp xếp dịch vụ theo độ dài đã chuẩn hóa giảm dần để ưu tiên khớp dịch vụ dài trước (như "rửa xe + hút bụi" trước "rửa xe")
        sorted_services = sorted(
            [s for s in active_services if s.strip()],
            key=lambda x: len(self._normalize_text(x)),
            reverse=True
        )
        
        # Thử khớp hoàn toàn trước
        for svc in sorted_services:
            if self._normalize_text(svc) == text_norm:
                return [svc]
                
        # Thử tìm kiếm dịch vụ con trong chuỗi
        results = []
        remaining = text_norm
        for svc in sorted_services:
            svc_norm = self._normalize_text(svc)
            if not svc_norm:
                continue
            pattern = rf"\b{re.escape(svc_norm)}\b"
            match = re.search(pattern, remaining)
            if match:
                results.append(svc)
                start, end = match.span()
                remaining = remaining[:start] + " " * (end - start) + remaining[end:]
                
        if results:
            return results
            
        # Fallback tự động tách theo ký tự phân tách nếu không khớp mẫu danh mục nào
        parts = re.split(r"[+,;/|]", raw)
        res = []
        for p in parts:
            token = str(p or "").strip()
            if token:
                res.append(self._match_service_name(token))
        return [x for x in res if x]

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
            row = self.tbl.currentRow()
            if row >= 0:
                status_item = self.tbl.item(row, 10)
                if status_item:
                    self._update_button_states_for_status(status_item.text().strip())
        else:
            self._update_button_states_for_status("")

    def _update_button_states_for_status(self, status):
        # 1. Reset check status
        for b in (self.btn_checkin, self.btn_quote, self.btn_approve, self.btn_done):
            b.setChecked(False)

        # 2. Highlight active state button
        mapping = {
            "CHECKED_IN": self.btn_checkin,
            "QUOTED": self.btn_quote,
            "APPROVED": self.btn_approve,
            "DONE": self.btn_done
        }
        if status in mapping:
            mapping[status].setChecked(True)

        # 3. Handle default disabled state if no order is selected
        if not status:
            for b in (self.btn_checkin, self.btn_quote, self.btn_approve, self.btn_done, self.btn_cancel, self.btn_edit_services, self.btn_wait_parts, self.btn_exported):
                b.setEnabled(False)
            return

        # 4. Enable/disable dynamically based on state machine rules
        from modules.service_orders import ALLOWED_TRANSITIONS
        allowed = ALLOWED_TRANSITIONS.get(status, set())

        self.btn_checkin.setEnabled("CHECKED_IN" in allowed)
        self.btn_quote.setEnabled("QUOTED" in allowed)
        self.btn_approve.setEnabled("APPROVED" in allowed)
        self.btn_done.setEnabled("DONE" in allowed or status == "IN_SERVICE")
        self.btn_cancel.setEnabled("CANCELLED" in allowed)
        
        self.btn_edit_services.setEnabled(status not in ("PAID", "AFTERCARE", "CANCELLED"))
        self.btn_wait_parts.setEnabled("WAITING_PARTS" in allowed or status in ("APPROVED", "IN_SERVICE"))
        self.btn_exported.setEnabled(status == "WAITING_PARTS")

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

    def _on_phone_text_changed(self):
        phone = self.txt_phone.text().strip()
        if len(phone) >= 9:
            try:
                from database.connection import fetch_one
                row = fetch_one(
                    """
                    SELECT c.full_name, c.vehicle_plate, v.car_model
                    FROM customers c
                    LEFT JOIN crm_customer_vehicles v ON v.customer_id = c.id
                    WHERE c.phone = %s
                    ORDER BY v.id DESC
                    LIMIT 1
                    """,
                    (phone,)
                )
                if row:
                    current_cust = self.txt_customer.text().strip()
                    if not current_cust or current_cust == "Khách lẻ":
                        self.txt_customer.setText(str(row.get("full_name") or ""))
                    if not self.txt_plate.text().strip():
                        self.txt_plate.setText(str(row.get("vehicle_plate") or ""))
                    if not self.txt_car_model.text().strip() and row.get("car_model"):
                        self.txt_car_model.setText(str(row.get("car_model") or ""))
            except Exception:
                pass

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
        row_idx = 0
        for it in data:
            status = it.get("status", "")
            is_cancelled = (status == "CANCELLED")
            if is_cancelled and not self.chk_show_cancelled.isChecked():
                continue

            self.tbl.insertRow(row_idx)
            self.tbl.setItem(row_idx, 0, QTableWidgetItem(str(it.get("order_id", "-"))))
            self.tbl.setItem(row_idx, 1, QTableWidgetItem(str(it.get("source", "-"))))
            self.tbl.setItem(row_idx, 2, QTableWidgetItem(str(it.get("created_at", ""))))
            self.tbl.setItem(row_idx, 3, QTableWidgetItem(str(it.get("customer_name", ""))))
            self.tbl.setItem(row_idx, 4, QTableWidgetItem(str(it.get("customer_phone", ""))))
            self.tbl.setItem(row_idx, 5, QTableWidgetItem(str(it.get("car_model", ""))))
            self.tbl.setItem(row_idx, 6, QTableWidgetItem(str(it.get("plate", ""))))
            services = it.get("services", []) or []
            self.tbl.setItem(row_idx, 7, QTableWidgetItem(", ".join(services)))
            total_price = int(it.get("service_total") or 0)
            if total_price <= 0:
                service_items = it.get("service_items", []) or []
                if service_items:
                    total_price = sum(int(x.get("unit_price") or 0) for x in service_items)
            if total_price <= 0:
                total_price = self._calc_order_total_from_services(services)
            self.tbl.setItem(row_idx, 8, QTableWidgetItem(self._format_vnd(total_price) if total_price > 0 else "Chưa báo giá"))
            self.tbl.setItem(row_idx, 9, QTableWidgetItem(str(it.get("assigned_to", ""))))
            self.tbl.setItem(row_idx, 10, QTableWidgetItem(str(status)))
            parts = it.get("material_requests", []) or []
            pending = sum(1 for x in parts if not x.get("exported"))
            exported = sum(1 for x in parts if x.get("exported"))
            self.tbl.setItem(row_idx, 11, QTableWidgetItem(f"chờ: {pending} | đã xuất: {exported}"))

            if is_cancelled:
                for col in range(12):
                    item = self.tbl.item(row_idx, col)
                    if item:
                        item.setForeground(QColor("#64748b"))
            row_idx += 1
        self._restore_selection(preferred_order_id)
        if self.tbl.currentRow() < 0:
            self._update_button_states_for_status("")

    def create_manual_order(self):
        customer = (self.txt_customer.text() or "").strip() or "Khách lẻ"
        phone = (self.txt_phone.text() or "").strip()
        if (not customer or customer == "Khách lẻ") and phone:
            try:
                from database.connection import fetch_one
                row = fetch_one("SELECT full_name FROM customers WHERE phone=%s LIMIT 1", (phone,))
                if row and row.get("full_name"):
                    customer = str(row["full_name"])
                    self.txt_customer.setText(customer)
            except Exception:
                pass
        plate = (self.txt_plate.text() or "").strip()
        car_model = (self.txt_car_model.text() or "").strip()

        # Validate SĐT nếu có điền
        if phone:
            clean_sdt = re.sub(r"[\s\-]", "", phone)
            if not re.match(r"^(0|84)[35789]\d{8}$", clean_sdt):
                QMessageBox.warning(self, "Sai định dạng", "Số điện thoại không hợp lệ (phải bắt đầu bằng 0 hoặc 84 và có 10 chữ số).")
                return

        # Validate Biển số nếu có điền
        if plate:
            clean_plate = re.sub(r"[\s\-.]", "", plate)
            if not re.match(r"^[a-zA-Z0-9]{4,15}$", clean_plate):
                QMessageBox.warning(self, "Sai định dạng", "Biển số xe không hợp lệ (chỉ gồm chữ và số, từ 4-15 ký tự).")
                return

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
        except Exception as e:
            QMessageBox.warning(self, "Không thể tạo lệnh", f"Không thể tạo lệnh dịch vụ.\nChi tiết: {e}")
            return
        append_audit_log(
            "service_order.create",
            self.current_user,
            {"customer_phone": phone, "plate": plate, "car_model": car_model, "assigned_to": technician},
        )
        self.btn_add.setChecked(True)
        self.btn_add.setText("Đã tạo lệnh")
        QTimer.singleShot(2000, lambda: (self.btn_add.setChecked(False), self.btn_add.setText("Tạo lệnh")))
        self.btn_auto_tech.setChecked(False)
        self.btn_auto_tech.setText("Tự phân công KTV")
        self.txt_customer.setText("")
        self.txt_phone.setText("")
        self.txt_plate.setText("")
        self.txt_car_model.setText("")
        self.cmb_service.setCurrentText("")
        self.cmb_technician.setCurrentText("")
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
        except Exception as e:
            QMessageBox.warning(
                self,
                "Lỗi chuyển trạng thái",
                f"Không thể chuyển trạng thái lệnh {order_id}.\nChi tiết: {e}"
            )
            self.refresh_data()
            return
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

    def _prompt_cancellation_reason(self, order_id):
        dlg = QDialog(self)
        dlg.setWindowTitle("Hủy lệnh dịch vụ")
        dlg.setMinimumWidth(380)
        dlg.setStyleSheet(self.styleSheet())
        
        layout = QVBoxLayout(dlg)
        
        lbl = QLabel(f"Bạn có chắc chắn muốn hủy lệnh <b>{order_id}</b> không?")
        lbl.setStyleSheet("color: #f1f5f9; font-size: 13px;")
        layout.addWidget(lbl)
        
        lbl_hint = QLabel("Nhập lý do hủy lệnh (bắt buộc):")
        lbl_hint.setStyleSheet("color: #94a3b8; font-size: 12px;")
        layout.addWidget(lbl_hint)
        
        txt_reason = QLineEdit()
        txt_reason.setPlaceholderText("Ví dụ: Khách đổi ý, trùng lịch...")
        layout.addWidget(txt_reason)
        
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        layout.addWidget(buttons)
        
        buttons.accepted.connect(dlg.accept)
        buttons.rejected.connect(dlg.reject)
        
        if dlg.exec_() == QDialog.Accepted:
            reason = txt_reason.text().strip()
            if not reason:
                QMessageBox.warning(self, "Thiếu thông tin", "Bạn phải nhập lý do để hủy lệnh.")
                return None
            return reason
        return None

    def _cancel_selected_order(self):
        self.btn_cancel.setChecked(False)
        row = self.tbl.currentRow()
        if row < 0:
            QMessageBox.warning(self, "Chưa chọn lệnh", "Vui lòng chọn một lệnh dịch vụ muốn hủy.")
            return
        order_id = (self.tbl.item(row, 0).text() if self.tbl.item(row, 0) else "").strip()
        if not order_id:
            return
            
        order = get_order(order_id)
        if not order:
            return
            
        status = order.get("status", "")
        from modules.service_orders import ALLOWED_TRANSITIONS
        allowed = ALLOWED_TRANSITIONS.get(status, set())
        if "CANCELLED" not in allowed:
            QMessageBox.warning(
                self, 
                "Không thể hủy lệnh", 
                f"Lệnh ở trạng thái '{status}' không thể hủy. Chỉ có thể hủy lệnh chưa thanh toán."
            )
            return
            
        reason = self._prompt_cancellation_reason(order_id)
        if not reason:
            return
            
        try:
            transition_order_status(order_id, "CANCELLED", actor=self.current_user, note=reason)
            append_audit_log(
                "service_order.cancel", 
                self.current_user, 
                {"order_id": order_id, "reason": reason}
            )
            QMessageBox.information(self, "Thành công", f"Đã hủy lệnh {order_id} thành công.")
            self.refresh_data()
        except Exception as e:
            QMessageBox.warning(self, "Lỗi", f"Không thể hủy lệnh.\nChi tiết: {e}")

