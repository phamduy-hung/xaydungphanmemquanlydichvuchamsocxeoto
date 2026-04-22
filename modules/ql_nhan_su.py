import sys
import csv
import importlib
from datetime import date, datetime, timedelta
from pathlib import Path

from PyQt5.QtCore import QDate, Qt
from PyQt5.QtWidgets import (
    QApplication,
    QComboBox,
    QDateEdit,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QHeaderView,
    QHBoxLayout,
    QFileDialog,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from ui.compiled.ui_qlnhansu import Ui_Form as Ui_Form_QLNhanSu
from modules.integration_data import get_pos_sales


class EmployeeDialog(QDialog):
    def __init__(self, parent=None, employee=None):
        super().__init__(parent)
        self.employee = employee or {}
        self.saved_data = None
        self.setWindowTitle("Thêm nhân viên" if not employee else "Sửa thông tin nhân viên")
        self._build_ui()
        self._fill_data()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        form = QFormLayout()

        self.txt_name = QLineEdit()
        self.txt_phone = QLineEdit()
        self.cmb_role = QComboBox()
        self.cmb_role.addItems(["Kỹ thuật", "Lễ tân", "Quản lý"])
        self.date_join = QDateEdit()
        self.date_join.setCalendarPopup(True)
        self.date_join.setDisplayFormat("dd/MM/yyyy")
        self.cmb_status = QComboBox()
        self.cmb_status.addItems(["Đang làm", "Tạm nghỉ"])

        form.addRow("Họ tên:", self.txt_name)
        form.addRow("SĐT:", self.txt_phone)
        form.addRow("Vai trò:", self.cmb_role)
        form.addRow("Ngày vào làm:", self.date_join)
        form.addRow("Trạng thái:", self.cmb_status)
        layout.addLayout(form)

        button_box = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        button_box.accepted.connect(self._on_save)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

    def _fill_data(self):
        if not self.employee:
            self.date_join.setDate(QDate.currentDate())
            return
        self.txt_name.setText(self.employee.get("name", ""))
        self.txt_phone.setText(self.employee.get("phone", ""))
        self.cmb_role.setCurrentText(self.employee.get("role", "Kỹ thuật"))
        try:
            d = datetime.strptime(self.employee.get("join_date", ""), "%d/%m/%Y").date()
            self.date_join.setDate(QDate(d.year, d.month, d.day))
        except Exception:
            self.date_join.setDate(QDate.currentDate())
        self.cmb_status.setCurrentText(self.employee.get("status", "Đang làm"))

    def _on_save(self):
        name = self.txt_name.text().strip()
        phone = self.txt_phone.text().strip()
        if not name or not phone:
            QMessageBox.warning(self, "Thiếu dữ liệu", "Vui lòng nhập Họ tên và SĐT.")
            return
        self.saved_data = {
            "name": name,
            "phone": phone,
            "role": self.cmb_role.currentText(),
            "join_date": self.date_join.date().toString("dd/MM/yyyy"),
            "status": self.cmb_status.currentText(),
        }
        self.accept()


class QuanLyNhanVienWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.ui = Ui_Form_QLNhanSu()
        self.ui.setupUi(self)

        self.employees = []
        self.attendance_records = []
        self.accounts = []
        self.next_employee_id = 1
        self.search_keyword = ""
        self.shift_templates = ["Sáng", "Chiều", "Tối", "Off"]
        self._is_rendering_shifts = False
        self._password_visible = False
        self._editing_permissions = False
        self.permission_matrix = [
            ("Tổng quan/KPI", "Có", "Có", "Xem báo cáo vận hành cơ bản"),
            ("Đặt lịch web", "Có", "Có", "Lễ tân nhận/xử lý lịch đặt từ website"),
            ("Khách hàng (CRM)", "Có", "Có", "Lễ tân cập nhật hồ sơ và lịch sử khách hàng"),
            ("Chăm sóc khách hàng", "Có", "Có", "Lễ tân chăm sóc sau dịch vụ theo kịch bản"),
            ("Bán hàng POS", "Có", "Có", "Lễ tân được tạo đơn, Quản lý toàn quyền"),
            ("Kho & Vật tư", "Có", "Không", "Chỉ Quản lý được chỉnh sửa tồn kho"),
            ("Báo cáo thống kê", "Có", "Không", "Lễ tân không xem báo cáo tài chính"),
            ("Cài đặt hệ thống", "Có", "Không", "Cấu hình hệ thống chỉ cho Quản lý"),
            ("Quản lý nhân sự", "Có", "Không", "Quản lý chấm công, phân ca, RBAC"),
        ]

        self._setup_tables()
        self._apply_dark_style()
        self._seed_demo_data()
        self._setup_defaults()
        self._setup_password_visibility_toggle()
        self._add_permission_edit_buttons()
        self._add_dynamic_commission_refresh_button()
        self._setup_signals()
        self._render_all()

    def _apply_dark_style(self):
        self.setStyleSheet("""
            QWidget {
                background-color: #0b1220;
                color: #dbeafe;
                font-family: "Segoe UI", "Inter";
            }
            QFrame, QGroupBox {
                background-color: #111827;
                border: 1px solid #334155;
                border-radius: 10px;
            }
            QGroupBox {
                margin-top: 14px;
                padding-top: 8px;
            }
            QGroupBox::title {
                color: #93c5fd;
                subcontrol-origin: margin;
                subcontrol-position: top left;
                left: 10px;
                padding: 0 6px;
            }
            QLineEdit, QComboBox, QDateEdit, QTextEdit {
                background-color: #0f172a;
                color: #e2e8f0;
                border: 1px solid #334155;
                border-radius: 8px;
                padding: 6px 8px;
                selection-background-color: #0ea5e9;
                selection-color: #f8fafc;
            }
            QTabWidget::pane {
                border: 1px solid #1f2937;
                background: #0b1220;
            }
            QTabBar::tab {
                background: #111827;
                color: #cbd5e1;
                border: 1px solid #334155;
                border-bottom: none;
                padding: 7px 14px;
                margin-right: 3px;
                border-top-left-radius: 8px;
                border-top-right-radius: 8px;
            }
            QTabBar::tab:selected {
                background: #0ea5e9;
                color: #f8fafc;
                border-color: #38bdf8;
                font-weight: 700;
            }
            QPushButton {
                background-color: #1e293b;
                color: #e2e8f0;
                border: 1px solid #334155;
                border-radius: 10px;
                font-weight: 700;
                font-size: 13px;
                padding: 8px 12px;
            }
            QPushButton:hover {
                background-color: #0ea5e9;
                border: 1px solid #38bdf8;
                color: #f8fafc;
            }
            QPushButton:pressed {
                background-color: #0284c7;
                border-color: #0ea5e9;
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
            QTableWidget::item {
                color: #e2e8f0;
            }
            QHeaderView::section {
                background-color: #1e293b;
                color: #bae6fd;
                border: 0px;
                padding: 8px;
                font-weight: 700;
            }
            QAbstractScrollArea {
                border-radius: 10px;
            }
            QLabel#lbl_title,
            QLabel#label_shift_week,
            QLabel#label_shift_team,
            QLabel#label_rbac_employee,
            QLabel#label_rbac_username,
            QLabel#label_rbac_password,
            QLabel#label_rbac_role,
            QLabel#label_commission_basis,
            QLabel#label_period {
                border: none;
                background: transparent;
                padding: 0;
            }
        """)

    def _setup_password_visibility_toggle(self):
        self.ui.txt_rbac_password.setEchoMode(QLineEdit.Password)
        self.btn_toggle_password = QPushButton("Hiện")
        self.btn_toggle_password.setFixedWidth(56)
        self.btn_toggle_password.clicked.connect(self._toggle_password_visibility)

        old_pwd_widget = self.ui.txt_rbac_password
        row, role = self.ui.formLayout_rbac_account.getWidgetPosition(old_pwd_widget)
        if row < 0:
            return

        self.password_field_container = QWidget(self.ui.grp_rbac_accounts)
        pwd_layout = QHBoxLayout(self.password_field_container)
        pwd_layout.setContentsMargins(0, 0, 0, 0)
        pwd_layout.setSpacing(6)

        old_pwd_widget.setParent(self.password_field_container)
        pwd_layout.addWidget(old_pwd_widget)
        pwd_layout.addWidget(self.btn_toggle_password)

        self.ui.formLayout_rbac_account.setWidget(row, role, self.password_field_container)

    def _toggle_password_visibility(self):
        self._password_visible = not self._password_visible
        if self._password_visible:
            self.ui.txt_rbac_password.setEchoMode(QLineEdit.Normal)
            self.btn_toggle_password.setText("Ẩn")
        else:
            self.ui.txt_rbac_password.setEchoMode(QLineEdit.Password)
            self.btn_toggle_password.setText("Hiện")

    def _setup_tables(self):
        for table in [
            self.ui.tbl_employees,
            self.ui.tbl_attendance,
            self.ui.tbl_commission,
            self.ui.tbl_rbac_permissions,
            self.ui.tbl_accounts,
        ]:
            table.setSelectionBehavior(table.SelectRows)
            table.setSelectionMode(table.SingleSelection)
            table.setEditTriggers(table.NoEditTriggers)
            table.verticalHeader().setVisible(False)
            table.setAlternatingRowColors(True)
            table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)

        self.ui.tbl_shifts.setSelectionBehavior(self.ui.tbl_shifts.SelectItems)
        self.ui.tbl_shifts.setSelectionMode(self.ui.tbl_shifts.SingleSelection)
        self.ui.tbl_shifts.setEditTriggers(
            self.ui.tbl_shifts.DoubleClicked
            | self.ui.tbl_shifts.SelectedClicked
            | self.ui.tbl_shifts.EditKeyPressed
        )
        self.ui.tbl_shifts.verticalHeader().setVisible(False)
        self.ui.tbl_shifts.setAlternatingRowColors(True)
        self.ui.tbl_shifts.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)

    def _add_permission_edit_buttons(self):
        if not hasattr(self.ui, "verticalLayout_permissions"):
            return
        row = QHBoxLayout()
        row.addStretch()
        self.btn_edit_permissions = QPushButton("Sửa quyền hạn")
        self.btn_save_permissions = QPushButton("Lưu quyền hạn")
        self.btn_save_permissions.setEnabled(False)
        self.btn_edit_permissions.clicked.connect(self._toggle_permission_edit_mode)
        self.btn_save_permissions.clicked.connect(self._save_permission_matrix)
        row.addWidget(self.btn_edit_permissions)
        row.addWidget(self.btn_save_permissions)
        self.ui.verticalLayout_permissions.addLayout(row)

    def _setup_defaults(self):
        today = QDate.currentDate()
        self.ui.date_week_start.setDate(today.addDays(-(today.dayOfWeek() - 1)))
        self.ui.date_att_to.setDate(today)
        self.ui.date_att_from.setDate(today.addDays(-6))

    def _setup_signals(self):
        self.ui.btn_search_employee.clicked.connect(self.search_employees)
        self.ui.txt_search_employee.returnPressed.connect(self.search_employees)
        self.ui.btn_add_employee.clicked.connect(self.add_employee)
        self.ui.btn_edit_employee.clicked.connect(self.edit_employee)
        self.ui.btn_delete_employee.clicked.connect(self.toggle_employee_status)
        self.ui.cmb_department_filter.currentIndexChanged.connect(self.render_shift_table)
        self.ui.btn_assign_shift.clicked.connect(self.auto_assign_shift)
        self.ui.btn_save_shift.clicked.connect(self._notify_saved_shift)
        self.ui.tbl_shifts.itemChanged.connect(self._on_shift_item_changed)

        self.ui.btn_load_attendance.clicked.connect(self.render_attendance_table)
        self.ui.btn_export_attendance.clicked.connect(self._notify_export_attendance)

        self.ui.btn_recalc_commission.clicked.connect(self.render_commission_table)
        self.ui.btn_confirm_commission.clicked.connect(self._notify_commission_confirmed)
        self.ui.btn_export_commission.clicked.connect(self._notify_export_commission)
        self.ui.btn_refresh_commission.clicked.connect(self.refresh_commission_tab)

        self.ui.btn_create_account.clicked.connect(self.create_or_update_account)
        self.ui.btn_reset_password.clicked.connect(self.reset_account_password)
        self.ui.btn_lock_account.clicked.connect(self.toggle_account_lock)
        self.ui.cmb_rbac_employee.currentIndexChanged.connect(self._sync_rbac_form_from_account)

    def _seed_demo_data(self):
        self._append_employee("Nguyen Minh Dat", "0902111222", "Kỹ thuật", "10/01/2025", "Đang làm")
        self._append_employee("Tran Bao Ngoc", "0913555444", "Lễ tân", "18/03/2025", "Đang làm")
        self._append_employee("Le Quoc Khanh", "0938222111", "Kỹ thuật", "25/11/2024", "Đang làm")
        self._append_employee("Pham Anh Thu", "0977666111", "Quản lý", "15/07/2023", "Đang làm")

        today = date.today()
        for emp in self.employees:
            for i in range(8):
                work_day = today - timedelta(days=i)
                shift = "Sáng" if i % 2 == 0 else "Chiều"
                hours = 8 if emp["status"] == "Đang làm" else 0
                self.attendance_records.append(
                    {
                        "employee_id": emp["id"],
                        "date": work_day.strftime("%d/%m/%Y"),
                        "shift": shift if hours else "Off",
                        "checkin": "08:00" if shift == "Sáng" and hours else ("13:00" if hours else "-"),
                        "checkout": "12:00" if shift == "Sáng" and hours else ("17:00" if hours else "-"),
                        "hours": hours / 2 if hours else 0,
                        "status": "Đủ công" if hours else "Nghỉ",
                        "note": "",
                    }
                )

        self.accounts = [
            {
                "username": "quanly.thu",
                "employee_id": 4,
                "role": "Quản lý",
                "locked": False,
                "password": "123456",
                "last_login": "20/04/2026 08:12",
            },
            {
                "username": "letan.ngoc",
                "employee_id": 2,
                "role": "Lễ tân",
                "locked": False,
                "password": "123456",
                "last_login": "20/04/2026 07:45",
            },
        ]

    def _append_employee(self, name, phone, role, join_date, status):
        employee = {
            "id": self.next_employee_id,
            "name": name,
            "phone": phone,
            "role": role,
            "join_date": join_date,
            "status": status,
            "shifts": {},
        }
        self.next_employee_id += 1
        self.employees.append(employee)
        return employee

    def _render_all(self):
        self.render_employee_table()
        self.render_shift_table()
        self.render_attendance_table()
        self.render_commission_table()
        self.render_permission_matrix()
        self.render_accounts_table()
        self._populate_rbac_employee_combo()

    def search_employees(self):
        self.search_keyword = self.ui.txt_search_employee.text().strip().lower()
        self.render_employee_table()

    def _filtered_employees(self):
        if not self.search_keyword:
            return list(self.employees)
        result = []
        for emp in self.employees:
            employee_code = f"nv{emp['id']:03d}"
            if (
                self.search_keyword in str(emp["id"]).lower()
                or self.search_keyword in employee_code
                or self.search_keyword in emp["name"].lower()
                or self.search_keyword in emp["phone"].lower()
            ):
                result.append(emp)
        return result

    def render_employee_table(self):
        table = self.ui.tbl_employees
        data = self._filtered_employees()
        table.setRowCount(0)
        for row, emp in enumerate(data):
            table.insertRow(row)
            table.setItem(row, 0, QTableWidgetItem(f"NV{emp['id']:03d}"))
            table.setItem(row, 1, QTableWidgetItem(emp["name"]))
            table.setItem(row, 2, QTableWidgetItem(emp["role"]))
            table.setItem(row, 3, QTableWidgetItem(emp["phone"]))
            table.setItem(row, 4, QTableWidgetItem(emp["join_date"]))
            table.setItem(row, 5, QTableWidgetItem(emp["status"]))

    def add_employee(self):
        dialog = EmployeeDialog(self)
        if dialog.exec_() and dialog.saved_data:
            saved = dialog.saved_data
            self._append_employee(saved["name"], saved["phone"], saved["role"], saved["join_date"], saved["status"])
            self._render_all()

    def _selected_employee(self):
        row = self.ui.tbl_employees.currentRow()
        if row < 0:
            return None
        code_item = self.ui.tbl_employees.item(row, 0)
        if not code_item:
            return None
        try:
            emp_id = int(code_item.text().replace("NV", ""))
        except ValueError:
            return None
        for emp in self.employees:
            if emp["id"] == emp_id:
                return emp
        return None

    def edit_employee(self):
        emp = self._selected_employee()
        if not emp:
            QMessageBox.warning(self, "Chưa chọn nhân viên", "Vui lòng chọn nhân viên để sửa.")
            return
        dialog = EmployeeDialog(self, employee=emp)
        if dialog.exec_() and dialog.saved_data:
            emp.update(dialog.saved_data)
            self._render_all()

    def toggle_employee_status(self):
        emp = self._selected_employee()
        if not emp:
            QMessageBox.warning(self, "Chưa chọn nhân viên", "Vui lòng chọn nhân viên.")
            return
        emp["status"] = "Tạm nghỉ" if emp["status"] == "Đang làm" else "Đang làm"
        self._render_all()

    def _week_dates(self):
        start = self.ui.date_week_start.date().toPyDate()
        return [start + timedelta(days=i) for i in range(7)]

    def _department_matches(self, emp):
        selected = self.ui.cmb_department_filter.currentText()
        if selected == "Tất cả bộ phận":
            return True
        return emp["role"] == selected

    def auto_assign_shift(self):
        dates = self._week_dates()
        for emp in self.employees:
            if not self._department_matches(emp):
                continue
            if emp["status"] != "Đang làm":
                for d in dates:
                    emp["shifts"][d.strftime("%d/%m")] = "Off"
                continue
            for idx, d in enumerate(dates):
                emp["shifts"][d.strftime("%d/%m")] = self.shift_templates[(emp["id"] + idx) % 3]
        self.render_shift_table()

    def render_shift_table(self):
        table = self.ui.tbl_shifts
        self._is_rendering_shifts = True
        table.setRowCount(0)
        week_dates = self._week_dates()
        for row, emp in enumerate([e for e in self.employees if self._department_matches(e)]):
            table.insertRow(row)
            name_item = QTableWidgetItem(emp["name"])
            name_item.setFlags(name_item.flags() & ~Qt.ItemIsEditable)
            table.setItem(row, 0, name_item)
            for col, d in enumerate(week_dates, start=1):
                key = d.strftime("%d/%m")
                table.setItem(row, col, QTableWidgetItem(emp["shifts"].get(key, "-")))
        self._is_rendering_shifts = False

    def _on_shift_item_changed(self, item):
        if self._is_rendering_shifts or not item:
            return
        if item.column() == 0:
            return

        visible_employees = [e for e in self.employees if self._department_matches(e)]
        if item.row() < 0 or item.row() >= len(visible_employees):
            return

        week_dates = self._week_dates()
        col_idx = item.column() - 1
        if col_idx < 0 or col_idx >= len(week_dates):
            return

        employee = visible_employees[item.row()]
        key = week_dates[col_idx].strftime("%d/%m")
        value = (item.text() or "").strip()
        employee["shifts"][key] = value if value else "-"

    def _notify_saved_shift(self):
        QMessageBox.information(self, "Phân ca", "Đã lưu lịch làm việc tuần hiện tại.")

    def render_attendance_table(self):
        table = self.ui.tbl_attendance
        table.setRowCount(0)
        from_d = self.ui.date_att_from.date().toPyDate()
        to_d = self.ui.date_att_to.date().toPyDate()
        for rec in self.attendance_records:
            d = datetime.strptime(rec["date"], "%d/%m/%Y").date()
            if d < from_d or d > to_d:
                continue
            emp = self._employee_by_id(rec["employee_id"])
            if not emp:
                continue
            row = table.rowCount()
            table.insertRow(row)
            table.setItem(row, 0, QTableWidgetItem(f"NV{emp['id']:03d}"))
            table.setItem(row, 1, QTableWidgetItem(emp["name"]))
            table.setItem(row, 2, QTableWidgetItem(rec["date"]))
            table.setItem(row, 3, QTableWidgetItem(rec["shift"]))
            table.setItem(row, 4, QTableWidgetItem(rec["checkin"]))
            table.setItem(row, 5, QTableWidgetItem(rec["checkout"]))
            table.setItem(row, 6, QTableWidgetItem(f"{rec['hours']:.1f}"))
            table.setItem(row, 7, QTableWidgetItem(rec["status"]))
            table.setItem(row, 8, QTableWidgetItem(rec["note"]))

    def _notify_export_attendance(self):
        table = self.ui.tbl_attendance
        if table.rowCount() == 0 or table.columnCount() == 0:
            QMessageBox.warning(self, "Chấm công", "Không có dữ liệu để xuất.")
            return

        from_d = self.ui.date_att_from.date().toString("yyyyMMdd")
        to_d = self.ui.date_att_to.date().toString("yyyyMMdd")
        default_name = f"bao_cao_cham_cong_{from_d}_{to_d}.xlsx"
        save_path, selected_filter = QFileDialog.getSaveFileName(
            self,
            "Xuất báo cáo chấm công",
            default_name,
            "Excel Files (*.xlsx);;CSV Files (*.csv)",
        )
        if not save_path:
            return

        headers, rows = self._collect_table_data(table)
        target_path = Path(save_path)
        try:
            if target_path.suffix.lower() == ".csv" or "CSV" in selected_filter:
                self._export_commission_to_csv(target_path, headers, rows)
                QMessageBox.information(self, "Chấm công", f"Đã xuất CSV:\n{target_path}")
                return

            self._export_commission_to_xlsx(target_path, headers, rows, sheet_name="ChamCong")
            QMessageBox.information(self, "Chấm công", f"Đã xuất Excel:\n{target_path}")
        except ImportError:
            fallback_path = target_path.with_suffix(".csv")
            self._export_commission_to_csv(fallback_path, headers, rows)
            QMessageBox.warning(
                self,
                "Thiếu thư viện openpyxl",
                "Chưa cài openpyxl nên hệ thống đã tự xuất sang CSV.\n"
                f"File: {fallback_path}",
            )
        except Exception as e:
            QMessageBox.critical(self, "Lỗi xuất file", f"Không thể xuất báo cáo chấm công.\nChi tiết: {e}")

    def render_commission_table(self):
        table = self.ui.tbl_commission
        table.setRowCount(0)
        mode = self.ui.cmb_commission_type.currentText()
        pos_sales = get_pos_sales()
        integrated_jobs = sum(len(s.get("items", [])) for s in pos_sales)
        integrated_revenue = sum(int(s.get("grand_total", 0) or 0) for s in pos_sales)
        technicians = [e for e in self.employees if e["role"] == "Kỹ thuật" and e["status"] == "Đang làm"]
        split_jobs = (integrated_jobs // len(technicians)) if technicians else 0
        split_revenue = (integrated_revenue // len(technicians)) if technicians else 0
        for emp in self.employees:
            if emp["role"] != "Kỹ thuật" or emp["status"] != "Đang làm":
                continue
            jobs = 18 + emp["id"] * 3
            revenue = jobs * 180000
            # Liên kết POS -> Nhân sự: phân bổ công việc/doanh thu tích hợp cho KTV.
            jobs += split_jobs
            revenue += split_revenue
            if mode == "Theo khối lượng công việc":
                rate = 6.0
            elif mode == "Theo dịch vụ thực hiện":
                rate = 7.5
            else:
                rate = 8.0
            provisional = revenue * rate / 100
            adjustment = 100000 if jobs >= 20 else 0
            total = provisional + adjustment

            row = table.rowCount()
            table.insertRow(row)
            table.setItem(row, 0, QTableWidgetItem(f"NV{emp['id']:03d}"))
            table.setItem(row, 1, QTableWidgetItem(emp["name"]))
            table.setItem(row, 2, QTableWidgetItem(str(jobs)))
            table.setItem(row, 3, QTableWidgetItem(self._money(revenue)))
            table.setItem(row, 4, QTableWidgetItem(f"{rate:.1f}"))
            table.setItem(row, 5, QTableWidgetItem(self._money(provisional)))
            table.setItem(row, 6, QTableWidgetItem(self._money(adjustment)))
            table.setItem(row, 7, QTableWidgetItem(self._money(total)))

    def _notify_commission_confirmed(self):
        QMessageBox.information(self, "Hoa hồng", "Đã chốt kỳ hoa hồng thành công.")

    def _notify_export_commission(self):
        table = self.ui.tbl_commission
        if table.rowCount() == 0 or table.columnCount() == 0:
            QMessageBox.warning(self, "Hoa hồng", "Không có dữ liệu để xuất.")
            return

        default_name = f"bang_hoa_hong_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
        save_path, selected_filter = QFileDialog.getSaveFileName(
            self,
            "Xuất bảng hoa hồng",
            default_name,
            "Excel Files (*.xlsx);;CSV Files (*.csv)",
        )
        if not save_path:
            return

        headers, rows = self._collect_table_data(table)

        target_path = Path(save_path)
        try:
            # Xuất CSV trực tiếp hoặc fallback khi thiếu openpyxl.
            if target_path.suffix.lower() == ".csv" or "CSV" in selected_filter:
                self._export_commission_to_csv(target_path, headers, rows)
                QMessageBox.information(self, "Hoa hồng", f"Đã xuất CSV:\n{target_path}")
                return

            self._export_commission_to_xlsx(target_path, headers, rows, sheet_name="HoaHong")
            QMessageBox.information(self, "Hoa hồng", f"Đã xuất Excel:\n{target_path}")
        except ImportError:
            fallback_path = target_path.with_suffix(".csv")
            self._export_commission_to_csv(fallback_path, headers, rows)
            QMessageBox.warning(
                self,
                "Thiếu thư viện openpyxl",
                "Chưa cài openpyxl nên hệ thống đã tự xuất sang CSV.\n"
                f"File: {fallback_path}",
            )
        except Exception as e:
            QMessageBox.critical(self, "Lỗi xuất file", f"Không thể xuất bảng hoa hồng.\nChi tiết: {e}")

    def _export_commission_to_csv(self, path: Path, headers, rows):
        with path.open("w", newline="", encoding="utf-8-sig") as f:
            writer = csv.writer(f)
            writer.writerow(headers)
            writer.writerows(rows)

    def _export_commission_to_xlsx(self, path: Path, headers, rows, sheet_name: str = "Sheet1"):
        openpyxl_mod = importlib.import_module("openpyxl")
        styles_mod = importlib.import_module("openpyxl.styles")
        Workbook = openpyxl_mod.Workbook
        Font = styles_mod.Font
        Alignment = styles_mod.Alignment

        wb = Workbook()
        ws = wb.active
        ws.title = sheet_name
        ws.append(headers)
        for row in rows:
            ws.append(row)

        for cell in ws[1]:
            cell.font = Font(bold=True)
            cell.alignment = Alignment(horizontal="center")

        for col_cells in ws.columns:
            col_letter = col_cells[0].column_letter
            max_len = 0
            for cell in col_cells:
                max_len = max(max_len, len(str(cell.value or "")))
            ws.column_dimensions[col_letter].width = min(max_len + 3, 42)

        wb.save(str(path))

    def _collect_table_data(self, table):
        headers = []
        for c in range(table.columnCount()):
            item = table.horizontalHeaderItem(c)
            headers.append(item.text() if item else f"Col {c + 1}")

        rows = []
        for r in range(table.rowCount()):
            row_data = []
            for c in range(table.columnCount()):
                item = table.item(r, c)
                row_data.append(item.text() if item else "")
            rows.append(row_data)
        return headers, rows

    def refresh_commission_tab(self):
        self.ui.cmb_commission_type.setCurrentIndex(0)
        self.ui.cmb_commission_period.setCurrentIndex(0)
        self.render_commission_table()

    def render_permission_matrix(self):
        table = self.ui.tbl_rbac_permissions
        table.setRowCount(0)
        for row, item in enumerate(self.permission_matrix):
            table.insertRow(row)
            for col, value in enumerate(item):
                table.setItem(row, col, QTableWidgetItem(value))
        self._apply_permission_item_flags()

    def _apply_permission_item_flags(self):
        table = self.ui.tbl_rbac_permissions
        for row in range(table.rowCount()):
            for col in range(table.columnCount()):
                item = table.item(row, col)
                if not item:
                    continue
                flags = item.flags() & ~Qt.ItemIsEditable
                if self._editing_permissions and col in (1, 2):
                    flags |= Qt.ItemIsEditable
                item.setFlags(flags)

    def _toggle_permission_edit_mode(self):
        self._editing_permissions = not self._editing_permissions
        self.btn_save_permissions.setEnabled(self._editing_permissions)
        self.btn_edit_permissions.setText("Hủy sửa quyền hạn" if self._editing_permissions else "Sửa quyền hạn")
        self._apply_permission_item_flags()
        if not self._editing_permissions:
            self.render_permission_matrix()

    def _save_permission_matrix(self):
        table = self.ui.tbl_rbac_permissions
        allowed = {"có": "Có", "không": "Không"}
        updated = []
        for row in range(table.rowCount()):
            fn = table.item(row, 0).text() if table.item(row, 0) else ""
            manager_raw = table.item(row, 1).text().strip() if table.item(row, 1) else ""
            receptionist_raw = table.item(row, 2).text().strip() if table.item(row, 2) else ""
            desc = table.item(row, 3).text() if table.item(row, 3) else ""
            manager = allowed.get(manager_raw.lower())
            receptionist = allowed.get(receptionist_raw.lower())
            if manager is None or receptionist is None:
                QMessageBox.warning(
                    self,
                    "Sai định dạng quyền",
                    "Giá trị quyền chỉ được nhập 'Có' hoặc 'Không'.",
                )
                return
            updated.append((fn, manager, receptionist, desc))
        self.permission_matrix = updated
        self._editing_permissions = False
        self.btn_save_permissions.setEnabled(False)
        self.btn_edit_permissions.setText("Sửa quyền hạn")
        self.render_permission_matrix()
        QMessageBox.information(self, "Phân quyền", "Đã cập nhật ma trận quyền hạn.")

    def _populate_rbac_employee_combo(self):
        current_id = self.ui.cmb_rbac_employee.currentData()
        self.ui.cmb_rbac_employee.blockSignals(True)
        self.ui.cmb_rbac_employee.clear()
        for emp in self.employees:
            self.ui.cmb_rbac_employee.addItem(f"NV{emp['id']:03d} - {emp['name']}", emp["id"])
        self.ui.cmb_rbac_employee.blockSignals(False)
        if current_id is not None:
            idx = self.ui.cmb_rbac_employee.findData(current_id)
            if idx >= 0:
                self.ui.cmb_rbac_employee.setCurrentIndex(idx)
        self._sync_rbac_form_from_account()

    def create_or_update_account(self):
        employee_id = self.ui.cmb_rbac_employee.currentData()
        if employee_id is None:
            QMessageBox.warning(self, "Thiếu dữ liệu", "Vui lòng chọn nhân viên.")
            return
        username = self.ui.txt_rbac_username.text().strip()
        password = self.ui.txt_rbac_password.text().strip()
        role = self.ui.cmb_rbac_role.currentText()
        if not username or not password:
            QMessageBox.warning(self, "Thiếu dữ liệu", "Vui lòng nhập tên đăng nhập và mật khẩu.")
            return

        acc = self._account_by_username(username)
        if acc:
            acc.update({"employee_id": employee_id, "role": role, "password": password})
        else:
            self.accounts.append(
                {
                    "username": username,
                    "employee_id": employee_id,
                    "role": role,
                    "locked": False,
                    "password": password,
                    "last_login": "-",
                }
            )

        # Đồng bộ vai trò từ RBAC sang hồ sơ nhân viên để tab Nhân viên & Phân ca cập nhật theo.
        emp = self._employee_by_id(employee_id)
        if emp and role in ("Quản lý", "Lễ tân"):
            emp["role"] = role

        self.render_accounts_table()
        self.render_employee_table()
        self.render_shift_table()
        self._sync_rbac_form_from_account()
        QMessageBox.information(self, "RBAC", "Đã tạo/cập nhật tài khoản.")

    def reset_account_password(self):
        username = self.ui.txt_rbac_username.text().strip()
        if not username:
            QMessageBox.warning(self, "Thiếu dữ liệu", "Nhập tên đăng nhập cần đặt lại mật khẩu.")
            return
        acc = self._account_by_username(username)
        if not acc:
            QMessageBox.warning(self, "Không tìm thấy", "Không có tài khoản tương ứng.")
            return
        acc["password"] = "123456"
        QMessageBox.information(self, "RBAC", "Đã đặt lại mật khẩu mặc định 123456.")

    def toggle_account_lock(self):
        username = self.ui.txt_rbac_username.text().strip()
        if not username:
            QMessageBox.warning(self, "Thiếu dữ liệu", "Nhập tên đăng nhập cần khóa/mở.")
            return
        acc = self._account_by_username(username)
        if not acc:
            QMessageBox.warning(self, "Không tìm thấy", "Không có tài khoản tương ứng.")
            return
        acc["locked"] = not acc["locked"]
        self.render_accounts_table()
        QMessageBox.information(self, "RBAC", "Đã cập nhật trạng thái tài khoản.")

    def render_accounts_table(self):
        table = self.ui.tbl_accounts
        table.setRowCount(0)
        for row, acc in enumerate(self.accounts):
            emp = self._employee_by_id(acc["employee_id"])
            table.insertRow(row)
            table.setItem(row, 0, QTableWidgetItem(acc["username"]))
            table.setItem(row, 1, QTableWidgetItem(emp["name"] if emp else "-"))
            table.setItem(row, 2, QTableWidgetItem(acc["role"]))
            table.setItem(row, 3, QTableWidgetItem("Khóa" if acc["locked"] else "Hoạt động"))
            table.setItem(row, 4, QTableWidgetItem(acc.get("last_login", "-")))

    def _sync_rbac_form_from_account(self):
        employee_id = self.ui.cmb_rbac_employee.currentData()
        if employee_id is None:
            return
        existing = next((a for a in self.accounts if a["employee_id"] == employee_id), None)
        if existing:
            self.ui.txt_rbac_username.setText(existing["username"])
            self.ui.txt_rbac_password.setText(existing["password"])
            self.ui.cmb_rbac_role.setCurrentText(existing["role"])
        else:
            emp = self._employee_by_id(employee_id)
            base_user = (emp["name"].lower().replace(" ", ".") if emp else "user")
            self.ui.txt_rbac_username.setText(base_user)
            self.ui.txt_rbac_password.setText("123456")
            if emp and emp["role"] in ("Quản lý", "Lễ tân"):
                self.ui.cmb_rbac_role.setCurrentText(emp["role"])
            else:
                self.ui.cmb_rbac_role.setCurrentText("Lễ tân")

    def _account_by_username(self, username):
        for acc in self.accounts:
            if acc["username"] == username:
                return acc
        return None

    def _employee_by_id(self, employee_id):
        for emp in self.employees:
            if emp["id"] == employee_id:
                return emp
        return None

    @staticmethod
    def _money(value):
        return f"{int(value):,} đ".replace(",", ".")

    def _add_dynamic_commission_refresh_button(self):
        self.ui.btn_refresh_commission = QPushButton("Làm mới")
        self.ui.horizontalLayout_commission_actions.insertWidget(0, self.ui.btn_refresh_commission)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    w = QuanLyNhanVienWidget()
    w.show()
    sys.exit(app.exec_())
