import sys
from pathlib import Path
from datetime import datetime

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
from modules.rbac_runtime import can_do
from modules.audit_log import append_audit_log
from modules.service_orders import find_latest_order_by_phone, get_order
from database.connection import ensure_mysql_ready, execute, fetch_all, fetch_one

# Phân loại khớp bộ lọc trên ui_qlkhachhang (comboBox)
CLASS_NEW = "Khách mới"
CLASS_RETURN = "Khách quay lại"
CLASS_VIP = "Khách VIP"
TIER_DONG = "Đồng"
TIER_BAC = "Bạc"
TIER_VANG = "Vàng"
TIER_VIP = "VIP"
DISCOUNT_BY_TIER = {TIER_DONG: 1, TIER_BAC: 3, TIER_VANG: 5, TIER_VIP: 8}


def _tier_from_points(points: int, rules: dict) -> str:
    p = int(points or 0)
    if p >= int(rules.get("nguong_vip", 5000)):
        return TIER_VIP
    if p >= int(rules.get("nguong_vang", 1500)):
        return TIER_VANG
    if p >= int(rules.get("nguong_bac", 500)):
        return TIER_BAC
    return TIER_DONG


def _crm_class_from_tier(tier: str, points: int) -> str:
    if str(tier or "").strip() == TIER_VIP:
        return CLASS_VIP
    return CLASS_RETURN if int(points or 0) > 0 else CLASS_NEW


def _apply_loyalty_rule(customer: dict, rules: dict):
    points = int(customer.get("diem", 0) or 0)
    tier = _tier_from_points(points, rules)
    
    # Tự động nâng cấp lên VIP nếu tổng chi tiêu vượt quá 50 triệu VNĐ
    tong_chi_tieu = int(customer.get("tong_chi_tieu", 0) or 0)
    if tong_chi_tieu > 50000000:
        tier = TIER_VIP
        
    customer["hang_thanh_vien"] = tier
    customer["chiet_khau"] = int(DISCOUNT_BY_TIER.get(tier, 1))
    customer["phan_loai"] = _crm_class_from_tier(tier, points)
    if tong_chi_tieu > 50000000:
        customer["phan_loai"] = CLASS_VIP


def _to_mysql_date(value: str):
    text = str(value or "").strip()
    if not text:
        return None
    for fmt in ("%Y-%m-%d", "%d/%m/%Y"):
        try:
            return datetime.strptime(text, fmt).strftime("%Y-%m-%d")
        except Exception:
            continue
    return None


class AddCustomerDialog(QDialog):
    """Thêm KH: không chọn phân loại; luôn là Khách mới (theo yêu cầu)."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.ui = Ui_Dialog_ThemKhachHang()
        self.ui.setupUi(self)
        
        # Chèn động trường Email vào vị trí thứ 8 và 9 của formLayout (trước Ghi chú)
        from PyQt5.QtWidgets import QLabel, QLineEdit
        self.lbl_email = QLabel("Email:")
        self.txt_email = QLineEdit()
        self.txt_email.setObjectName("txt_email")
        self.ui.formLayout.insertRow(8, self.lbl_email)
        self.ui.formLayout.insertRow(9, self.txt_email)
        
        self._apply_input_text_dark_style()
        self.saved_customer_data = None
        self.setWindowTitle("Thêm khách hàng mới")
        self._setup_signals()

    def _apply_input_text_dark_style(self):
        self.setStyleSheet("""
            QDialog {
                background-color: #090d16;
                color: #e2e8f0;
            }
            QLabel {
                color: #cbd5e1;
                font-weight: 600;
                font-size: 13px;
            }
            QLineEdit, QTextEdit, QComboBox {
                background-color: #0c101a;
                color: #f8fafc;
                border: 1px solid #27354a;
                border-radius: 8px;
                padding: 6px 10px;
                font-size: 13px;
            }
            QLineEdit:focus, QTextEdit:focus, QComboBox:focus {
                border: 1px solid #f97316;
            }
            QPushButton {
                background-color: #161e2e;
                color: #e2e8f0;
                border: 1px solid #27354a;
                border-radius: 8px;
                font-weight: 700;
                font-size: 13px;
                padding: 8px 14px;
            }
            QPushButton:hover {
                background-color: #f97316;
                border: 1px solid #ff7a22;
                color: #ffffff;
            }
        """)

    def _setup_signals(self):
        self.ui.btn_save.clicked.connect(self._save_data)
        self.ui.btn_cancel.clicked.connect(self.reject)

    def _save_data(self):
        import re
        ten = self.ui.txt_name.text().strip()
        sdt = self.ui.txt_phone.text().strip()
        hang_xe = self.ui.txt_hangxe.text().strip()
        bien_so = self.ui.txt_plate.text().strip()
        email = self.txt_email.text().strip()
        ghi_chu = self.ui.txt_note.toPlainText().strip()

        if not ten or not sdt:
            QMessageBox.warning(self, "Thiếu dữ liệu", "Vui lòng nhập Tên khách hàng và Số điện thoại.")
            return

        # Validate SĐT
        clean_sdt = re.sub(r"[\s\-]", "", sdt)
        if not re.match(r"^(0|84)[35789]\d{8}$", clean_sdt):
            QMessageBox.warning(self, "Sai định dạng", "Số điện thoại không hợp lệ (phải bắt đầu bằng 0 hoặc 84 và có 10 chữ số).")
            return

        # Validate Email
        if email and not re.match(r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$", email):
            QMessageBox.warning(self, "Sai định dạng", "Email không đúng định dạng (ví dụ: example@gmail.com).")
            return

        # Validate Biển số xe
        if bien_so:
            clean_plate = re.sub(r"[\s\-.]", "", bien_so)
            if not re.match(r"^[a-zA-Z0-9]{4,15}$", clean_plate):
                QMessageBox.warning(self, "Sai định dạng", "Biển số xe không hợp lệ (chỉ gồm chữ và số, từ 4-15 ký tự).")
                return

        self.saved_customer_data = {
            "ten": ten,
            "sdt": sdt,
            "hang_xe": hang_xe,
            "bien_so": bien_so,
            "email": email,
            "phan_loai": CLASS_NEW,
            "tong_chi_tieu": 0,
            "ghi_chu": ghi_chu,
        }
        self.accept()


class EditCustomerDialog(QDialog):
    """Sửa thông tin khách; hạng CRM sẽ tự đồng bộ theo điểm từ CSKH."""

    def __init__(self, parent=None, customer_data=None):
        super().__init__(parent)
        self.ui = Ui_Dialog_SuaThongTinKH()
        self.ui.setupUi(self)
        
        # Chèn động trường Email vào vị trí thứ 10 và 11 của formLayout (trước Ghi chú)
        from PyQt5.QtWidgets import QLabel, QLineEdit
        self.lbl_email = QLabel("Email:")
        self.txt_email = QLineEdit()
        self.txt_email.setObjectName("txt_email")
        self.ui.formLayout.insertRow(10, self.lbl_email)
        self.ui.formLayout.insertRow(11, self.txt_email)
        
        self._apply_input_text_dark_style()
        self.customer_data = customer_data or {}
        self.saved_customer_data = None
        self.setWindowTitle("Sửa thông tin khách hàng")
        self._setup_classification_combo()
        self._fill_old_data()
        self._setup_signals()

    def _apply_input_text_dark_style(self):
        self.setStyleSheet("""
            QDialog {
                background-color: #090d16;
                color: #e2e8f0;
            }
            QLabel {
                color: #cbd5e1;
                font-weight: 600;
                font-size: 13px;
            }
            QLineEdit, QTextEdit, QComboBox {
                background-color: #0c101a;
                color: #f8fafc;
                border: 1px solid #27354a;
                border-radius: 8px;
                padding: 6px 10px;
                font-size: 13px;
            }
            QLineEdit:focus, QTextEdit:focus, QComboBox:focus {
                border: 1px solid #f97316;
            }
            QPushButton {
                background-color: #161e2e;
                color: #e2e8f0;
                border: 1px solid #27354a;
                border-radius: 8px;
                font-weight: 700;
                font-size: 13px;
                padding: 8px 14px;
            }
            QPushButton:hover {
                background-color: #f97316;
                border: 1px solid #ff7a22;
                color: #ffffff;
            }
        """)

    def _setup_classification_combo(self):
        """Phân loại CRM đồng bộ tự động theo điểm -> chỉ hiển thị để tham khảo."""
        cb = self.ui.comboBox
        cb.blockSignals(True)
        cb.clear()
        cb.addItem(CLASS_NEW)
        cb.addItem(CLASS_RETURN)
        cb.addItem(CLASS_VIP)
        cb.setEnabled(False)
        cb.blockSignals(False)

    def _set_combo_from_phan_loai(self):
        raw = self.customer_data.get("phan_loai", CLASS_NEW)
        cb = self.ui.comboBox
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
        self.txt_email.setText(self.customer_data.get("email", ""))
        self.ui.txt_note.setPlainText(self.customer_data.get("ghi_chu", ""))
        self._set_combo_from_phan_loai()

    def _save_data(self):
        import re
        ten = self.ui.txt_name.text().strip()
        sdt = self.ui.txt_phone.text().strip()
        hang_xe = self.ui.txt_hangxe.text().strip()
        bien_so = self.ui.txt_plate.text().strip()
        email = self.txt_email.text().strip()
        ghi_chu = self.ui.txt_note.toPlainText().strip()
        spending = int(self.customer_data.get("tong_chi_tieu", 0))

        if not ten or not sdt:
            QMessageBox.warning(self, "Thiếu dữ liệu", "Vui lòng nhập Tên khách hàng và Số điện thoại.")
            return

        # Validate SĐT
        clean_sdt = re.sub(r"[\s\-]", "", sdt)
        if not re.match(r"^(0|84)[35789]\d{8}$", clean_sdt):
            QMessageBox.warning(self, "Sai định dạng", "Số điện thoại không hợp lệ (phải bắt đầu bằng 0 hoặc 84 và có 10 chữ số).")
            return

        # Validate Email
        if email and not re.match(r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$", email):
            QMessageBox.warning(self, "Sai định dạng", "Email không đúng định dạng (ví dụ: example@gmail.com).")
            return

        # Validate Biển số xe
        if bien_so:
            clean_plate = re.sub(r"[\s\-.]", "", bien_so)
            if not re.match(r"^[a-zA-Z0-9]{4,15}$", clean_plate):
                QMessageBox.warning(self, "Sai định dạng", "Biển số xe không hợp lệ (chỉ gồm chữ và số, từ 4-15 ký tự).")
                return

        self.saved_customer_data = {
            "id": self.customer_data.get("id"),
            "ten": ten,
            "sdt": sdt,
            "hang_xe": hang_xe,
            "bien_so": bien_so,
            "email": email,
            "phan_loai": self.customer_data.get("phan_loai", CLASS_NEW),
            "diem": int(self.customer_data.get("diem", 0)),
            "hang_thanh_vien": self.customer_data.get("hang_thanh_vien", TIER_DONG),
            "chiet_khau": int(self.customer_data.get("chiet_khau", 1)),
            "tong_chi_tieu": spending,
            "ghi_chu": ghi_chu,
        }
        self.accept()


class CustomerManagerWidget(QWidget):
    def __init__(self, current_role="Quản lý", current_user="system"):
        super().__init__()
        self.current_role = current_role
        self.current_user = current_user
        self.ui = Ui_Form_QLKhachHang()
        self.ui.setupUi(self)

        self.customers = []
        self.service_history_map = {}
        self.next_customer_id = 1
        self.search_keyword = ""
        self.loyalty_rules = self._load_loyalty_rules()

        self._setup_tables()
        self._apply_dark_style()
        self._load_or_seed_data()
        self._setup_signals()
        self.refresh_customer_table()

    def _load_or_seed_data(self):
        ensure_mysql_ready()
        self._ensure_vehicle_table()
        self.loyalty_rules = self._load_loyalty_rules()
        if self._load_from_mysql():
            return
        self._seed_demo_data()
        self._save_all_to_mysql()

    def _ensure_vehicle_table(self):
        execute(
            """
            CREATE TABLE IF NOT EXISTS crm_customer_vehicles (
                id BIGINT AUTO_INCREMENT PRIMARY KEY,
                customer_id BIGINT NOT NULL,
                car_model VARCHAR(100) NOT NULL DEFAULT '',
                plate_no VARCHAR(20) NOT NULL DEFAULT '',
                UNIQUE KEY uk_customer_vehicle (customer_id, car_model, plate_no),
                INDEX idx_customer_vehicles (customer_id),
                FOREIGN KEY (customer_id) REFERENCES customers(id) ON DELETE CASCADE
            ) ENGINE=InnoDB
            """
        )

    def refresh_from_database(self):
        selected_id = self._get_selected_customer_id()
        self.loyalty_rules = self._load_loyalty_rules()
        self._load_from_mysql()
        self.refresh_customer_table()
        if selected_id is not None:
            self._select_customer_by_id(selected_id)

    def _load_loyalty_rules(self):
        try:
            rows = fetch_all(
                """
                SELECT diem_moi_1trieu, nguong_bac, nguong_vang, nguong_vip
                FROM cskh_settings
                ORDER BY id DESC
                LIMIT 1
                """
            )
            if rows:
                r = rows[0]
                return {
                    "diem_moi_1trieu": int(r.get("diem_moi_1trieu") or 10),
                    "nguong_bac": int(r.get("nguong_bac") or 500),
                    "nguong_vang": int(r.get("nguong_vang") or 1500),
                    "nguong_vip": int(r.get("nguong_vip") or 5000),
                }
        except Exception:
            pass
        return {"diem_moi_1trieu": 10, "nguong_bac": 500, "nguong_vang": 1500, "nguong_vip": 5000}

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
        customer_table.setColumnCount(8)
        customer_table.setHorizontalHeaderLabels([
            "Mã khách hàng",
            "Tên khách hàng",
            "Số điện thoại",
            "Email",
            "Hãng xe",
            "Biển số xe",
            "Phân loại",
            "Tổng chi tiêu"
        ])
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
        
        # Thêm bộ lọc ngày vào panel lịch sử dịch vụ bên phải
        from PyQt5.QtWidgets import QHBoxLayout, QComboBox, QLabel, QDateEdit
        from PyQt5.QtCore import QDate
        
        self.date_filter_layout = QHBoxLayout()
        self.date_filter_layout.setContentsMargins(0, 5, 0, 5)
        self.date_filter_layout.setSpacing(8)
        
        self.cmb_date_preset = QComboBox()
        self.cmb_date_preset.addItems(["Tất cả", "Hôm qua", "7 ngày trước", "1 tháng trước"])
        self.cmb_date_preset.setFixedWidth(130)
        self.cmb_date_preset.currentIndexChanged.connect(self._on_date_preset_changed)
        
        self.lbl_from = QLabel("Từ:")
        self.lbl_from.setObjectName("lbl_from")
        self.date_from = QDateEdit()
        self.date_from.setCalendarPopup(True)
        self.date_from.setDisplayFormat("dd/MM/yyyy")
        self.date_from.setFixedWidth(120)
        self.date_from.setDate(QDate.currentDate().addDays(-7))
        self.date_from.dateChanged.connect(self._on_date_changed)
        
        self.lbl_to = QLabel("Đến:")
        self.lbl_to.setObjectName("lbl_to")
        self.date_to = QDateEdit()
        self.date_to.setCalendarPopup(True)
        self.date_to.setDisplayFormat("dd/MM/yyyy")
        self.date_to.setFixedWidth(120)
        self.date_to.setDate(QDate.currentDate())
        self.date_to.dateChanged.connect(self._on_date_changed)
        
        self.date_filter_layout.addWidget(self.cmb_date_preset)
        self.date_filter_layout.addWidget(self.lbl_from)
        self.date_filter_layout.addWidget(self.date_from)
        self.date_filter_layout.addWidget(self.lbl_to)
        self.date_filter_layout.addWidget(self.date_to)
        self.date_filter_layout.addStretch(1) # Đẩy bộ lọc về bên trái để giao diện gọn gàng hơn
        
        # Chèn layout này vào verticalLayout_2 (sau label_3 và trước tbl_history)
        self.ui.verticalLayout_2.insertLayout(2, self.date_filter_layout)
        
        # Trạng thái ban đầu của bộ lọc
        self._updating_date_presets = False
        self._on_date_preset_changed()

    def _apply_dark_style(self):
        self.setStyleSheet("""
            QWidget {
                background-color: #090d16;
                color: #e2e8f0;
                font-family: "Segoe UI", "Inter";
            }
            QGroupBox {
                background-color: #121824;
                border: 1px solid #222e44;
                border-radius: 12px;
                margin-top: 8px;
            }
            QGroupBox::title {
                color: #0ea5e9;
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 4px;
                font-weight: 700;
            }
            QLineEdit, QComboBox, QDateEdit, QTextEdit {
                background-color: #0c101a;
                color: #f8fafc;
                border: 1px solid #27354a;
                border-radius: 8px;
                padding: 6px 10px;
            }
            QLineEdit:focus, QComboBox:focus, QDateEdit:focus, QTextEdit:focus {
                border: 1px solid #f97316;
            }
            QLabel#lbl_from, QLabel#lbl_to {
                background-color: transparent;
                color: #94a3b8;
                font-weight: bold;
                font-size: 13px;
                margin-left: 5px;
            }
            QDateEdit::drop-down {
                border: none;
                width: 20px;
            }
            QDateEdit::down-arrow {
                image: url("C:/Users/LENOVO/OneDrive/Documents/xaydungphanmemquanlydichvuchamsocxeoto/assets/icons/muiten.png");
                width: 10px;
                height: 10px;
            }
            QCalendarWidget QWidget {
                background-color: #0c101a;
                color: #e2e8f0;
            }
            QCalendarWidget QAbstractItemView:enabled {
                color: #e2e8f0;
                background-color: #0c101a;
                selection-background-color: #f97316;
                selection-color: #ffffff;
            }
            QCalendarWidget QAbstractItemView:disabled {
                color: #4b5563;
            }
            QCalendarWidget QNavigationBar {
                background-color: #1e293b;
            }
            QPushButton {
                background-color: #161e2e;
                color: #e2e8f0;
                border: 1px solid #27354a;
                border-radius: 8px;
                font-weight: 700;
                font-size: 13px;
                padding: 9px 12px;
            }
            QPushButton:hover {
                background-color: #0ea5e9;
                border: 1px solid #38bdf8;
                color: #f8fafc;
            }
            QPushButton#btn_themKH {
                background-color: #f97316;
                color: #ffffff;
                border: 1px solid #ff7a22;
            }
            QPushButton#btn_themKH:hover {
                background-color: #ea580c;
                border: 1px solid #f97316;
            }
            QPushButton#btn_xoaKH:hover {
                background-color: #ef4444;
                border: 1px solid #f87171;
                color: #ffffff;
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
            "email": data.get("email", ""),
            "phan_loai": data.get("phan_loai", CLASS_NEW),
            "diem": int(data.get("diem", 0)),
            "hang_thanh_vien": data.get("hang_thanh_vien", TIER_DONG),
            "chiet_khau": int(data.get("chiet_khau", 1)),
            "tong_chi_tieu": int(data.get("tong_chi_tieu", 0)),
            "ghi_chu": data.get("ghi_chu", ""),
        }
        _apply_loyalty_rule(customer, self.loyalty_rules)
        self.customers.append(customer)
        self.next_customer_id += 1
        return customer

    @staticmethod
    def _split_multi_values(text: str):
        raw = str(text or "").strip()
        if not raw:
            return []
        parts = []
        for chunk in raw.replace(";", ",").split(","):
            val = chunk.strip()
            if val and val not in parts:
                parts.append(val)
        return parts

    @staticmethod
    def _merge_vehicle_field(existing: str, new_value: str) -> str:
        values = CustomerManagerWidget._split_multi_values(existing)
        value = str(new_value or "").strip()
        if value and value not in values:
            values.append(value)
        return ", ".join(values)

    @staticmethod
    def _first_plate_for_customers_table(raw_plate: str):
        plates = CustomerManagerWidget._split_multi_values(raw_plate)
        if plates:
            return plates[0][:20]
        return str(raw_plate or "").strip()[:20]

    def _ensure_email_column(self):
        try:
            col = fetch_one(
                """
                SELECT COLUMN_NAME
                FROM information_schema.COLUMNS
                WHERE TABLE_SCHEMA = DATABASE()
                  AND TABLE_NAME = 'customers'
                  AND COLUMN_NAME = 'email'
                LIMIT 1
                """
            )
            if not col:
                execute("ALTER TABLE customers ADD COLUMN email VARCHAR(100) DEFAULT ''")
        except Exception as e:
            print("Warning: _ensure_email_column failed:", e)

    def _load_from_mysql(self):
        try:
            self._ensure_vehicle_table()
            self._ensure_email_column()
            rows = fetch_all(
                """
                SELECT id, full_name, phone, vehicle_plate, email, points, tier, discount_percent, total_spent
                FROM customers
                ORDER BY id ASC
                """
            )
            self.customers = []
            self.service_history_map = {}
            max_id = 0
            for r in rows:
                cid = int(r.get("id") or 0)
                max_id = max(max_id, cid)
                customer = {
                    "id": cid,
                    "ten": r.get("full_name", ""),
                    "sdt": r.get("phone", ""),
                    "hang_xe": "",
                    "bien_so": r.get("vehicle_plate", ""),
                    "email": r.get("email", ""),
                    "diem": int(r.get("points") or 0),
                    "hang_thanh_vien": r.get("tier", TIER_DONG),
                    "chiet_khau": int(float(r.get("discount_percent") or 1)),
                    "phan_loai": CLASS_NEW,
                    "tong_chi_tieu": int(float(r.get("total_spent") or 0)),
                    "ghi_chu": "",
                }
                _apply_loyalty_rule(customer, self.loyalty_rules)
                self.customers.append(customer)
            self.next_customer_id = max_id + 1 if max_id else 1

            vehicle_rows = fetch_all(
                """
                SELECT customer_id, car_model, plate_no
                FROM crm_customer_vehicles
                ORDER BY id ASC
                """
            )
            vehicle_map = {}
            plate_map = {}
            for v in vehicle_rows:
                cid = int(v.get("customer_id") or 0)
                if cid <= 0:
                    continue
                cm = str(v.get("car_model", "")).strip()
                pn = str(v.get("plate_no", "")).strip()
                if cm:
                    vehicle_map.setdefault(cid, [])
                    if cm not in vehicle_map[cid]:
                        vehicle_map[cid].append(cm)
                if pn:
                    plate_map.setdefault(cid, [])
                    if pn not in plate_map[cid]:
                        plate_map[cid].append(pn)
            for customer in self.customers:
                cid = int(customer["id"])
                if vehicle_map.get(cid):
                    customer["hang_xe"] = ", ".join(vehicle_map[cid])
                if plate_map.get(cid):
                    customer["bien_so"] = ", ".join(plate_map[cid])

            history_rows = fetch_all(
                """
                SELECT customer_id, service_date, car_model, plate_no, service_name, amount, technician
                FROM crm_service_history
                ORDER BY id ASC
                """
            )
            for h in history_rows:
                cid = int(h.get("customer_id") or 0)
                if cid <= 0:
                    continue
                self.service_history_map.setdefault(cid, []).append(
                    {
                        "ngay": h["service_date"].strftime("%Y-%m-%d") if h.get("service_date") else "",
                        "hang_xe": h.get("car_model", ""),
                        "bien_so": h.get("plate_no", ""),
                        "dich_vu": h.get("service_name", ""),
                        "tong_tien": int(float(h.get("amount") or 0)),
                        "ktv": h.get("technician", ""),
                    }
                )

            # Tính toán lại tổng chi tiêu tích lũy và điểm số dựa trên toàn bộ lịch sử dịch vụ
            for customer in self.customers:
                cid = int(customer["id"])
                histories = self.service_history_map.get(cid, [])
                if histories:
                    customer["tong_chi_tieu"] = sum(h["tong_tien"] for h in histories)
                    # Phục hồi điểm tích lũy tối thiểu từ lịch sử hóa đơn (đề phòng bị ghi đè bằng 0)
                    calculated_points = sum((h["tong_tien"] // 1000000) * int(self.loyalty_rules.get("diem_moi_1trieu", 10)) for h in histories)
                    customer["diem"] = max(customer.get("diem", 0), calculated_points)
                else:
                    customer["tong_chi_tieu"] = 0
                _apply_loyalty_rule(customer, self.loyalty_rules)

            return bool(self.customers)
        except Exception:
            return False

    def _save_all_to_mysql(self):
        ensure_mysql_ready()
        self._ensure_vehicle_table()
        self._ensure_email_column()
        execute("DELETE FROM crm_service_history")
        execute("DELETE FROM crm_customer_vehicles")
        execute("DELETE FROM customers")
        for c in self.customers:
            execute(
                """
                INSERT INTO customers(id, customer_code, full_name, phone, vehicle_plate, email, points, tier, discount_percent, total_spent)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    int(c["id"]),
                    f"KH{int(c['id']):03d}",
                    c.get("ten", ""),
                    c.get("sdt", ""),
                    self._first_plate_for_customers_table(c.get("bien_so", "")),
                    c.get("email", ""),
                    int(c.get("diem", 0)),
                    c.get("hang_thanh_vien", TIER_DONG),
                    float(c.get("chiet_khau", 1)),
                    float(c.get("tong_chi_tieu", 0)),
                ),
            )
            brands = self._split_multi_values(c.get("hang_xe", ""))
            plates = self._split_multi_values(c.get("bien_so", ""))
            if not brands and c.get("hang_xe", "").strip():
                brands = [c.get("hang_xe", "").strip()]
            if not plates and c.get("bien_so", "").strip():
                plates = [c.get("bien_so", "").strip()]
            if not brands and not plates:
                continue

            # Ghép cặp thông minh sử dụng lịch sử làm dịch vụ
            history_rows = self.service_history_map.get(int(c["id"]), [])
            history_plate_map = {}
            for h in history_rows:
                h_plate = str(h.get("bien_so", "")).strip()
                h_brand = str(h.get("hang_xe", "")).strip()
                if h_plate and h_brand:
                    history_plate_map[h_plate] = h_brand

            paired_vehicles = []
            used_brands = set()

            for plate in plates:
                if plate in history_plate_map:
                    brand = history_plate_map[plate]
                    paired_vehicles.append((brand, plate))
                    if brand in brands:
                        used_brands.add(brand)
                else:
                    paired_vehicles.append((None, plate))

            leftover_brands = [b for b in brands if b not in used_brands]
            leftover_idx = 0
            for i, (brand, plate) in enumerate(paired_vehicles):
                if brand is None:
                    if leftover_idx < len(leftover_brands):
                        paired_vehicles[i] = (leftover_brands[leftover_idx], plate)
                        leftover_idx += 1
                    else:
                        paired_vehicles[i] = ("", plate)

            while leftover_idx < len(leftover_brands):
                paired_vehicles.append((leftover_brands[leftover_idx], ""))
                leftover_idx += 1

            if not paired_vehicles:
                max_len = max(len(brands), len(plates), 1)
                for idx in range(max_len):
                    brand = brands[idx] if idx < len(brands) else ""
                    plate = plates[idx] if idx < len(plates) else ""
                    paired_vehicles.append((brand, plate))

            for brand, plate in paired_vehicles:
                execute(
                    """
                    INSERT INTO crm_customer_vehicles(customer_id, car_model, plate_no)
                    VALUES (%s, %s, %s)
                    """,
                    (
                        int(c["id"]),
                        brand,
                        plate,
                    ),
                )
        for cid, rows in self.service_history_map.items():
            for h in rows:
                execute(
                    """
                    INSERT INTO crm_service_history(customer_id, service_date, car_model, plate_no, service_name, amount, technician)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                    """,
                    (
                        int(cid),
                        _to_mysql_date(h.get("ngay", "")),
                        h.get("hang_xe", ""),
                        h.get("bien_so", ""),
                        h.get("dich_vu", ""),
                        float(h.get("tong_tien", 0)),
                        h.get("ktv", ""),
                    ),
                )

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
            table.setItem(row, 3, QTableWidgetItem(customer.get("email", "")))
            table.setItem(row, 4, QTableWidgetItem(customer.get("hang_xe", "")))
            table.setItem(row, 5, QTableWidgetItem(customer["bien_so"]))
            table.setItem(row, 6, QTableWidgetItem(customer["phan_loai"]))
            table.setItem(row, 7, QTableWidgetItem(self._format_currency(customer["tong_chi_tieu"])))

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
        if not can_do(self.current_role, "crm.create"):
            QMessageBox.warning(self, "Không có quyền", "Vai trò hiện tại không có quyền thêm khách hàng.")
            return
        dialog = AddCustomerDialog(self)
        if dialog.exec_() and dialog.saved_customer_data:
            new_customer = self._append_customer(dialog.saved_customer_data)
            self.service_history_map.setdefault(new_customer["id"], [])
            self._save_all_to_mysql()
            self.refresh_customer_table()
            append_audit_log("crm.create_customer", self.current_user, {"customer_id": new_customer["id"]})

    def open_edit_dialog(self):
        if not can_do(self.current_role, "crm.edit"):
            QMessageBox.warning(self, "Không có quyền", "Vai trò hiện tại không có quyền sửa khách hàng.")
            return
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
            _apply_loyalty_rule(updated, self.loyalty_rules)
            self.customers[customer_index] = updated
            self._save_all_to_mysql()
            self.refresh_customer_table()
            self._select_customer_by_id(customer_id)
            append_audit_log("crm.edit_customer", self.current_user, {"customer_id": customer_id})

    def delete_customer(self):
        if not can_do(self.current_role, "crm.delete"):
            QMessageBox.warning(self, "Không có quyền", "Vai trò hiện tại không có quyền xóa khách hàng.")
            return
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
        self._save_all_to_mysql()
        self.refresh_customer_table()
        append_audit_log("crm.delete_customer", self.current_user, {"customer_id": customer_id})

    def _select_customer_by_id(self, customer_id):
        table = self.ui.tbl_customers
        for row in range(table.rowCount()):
            item = table.item(row, 0)
            if item and item.text() == str(customer_id):
                table.selectRow(row)
                return

    def _on_date_preset_changed(self):
        from PyQt5.QtCore import QDate
        preset = self.cmb_date_preset.currentText()
        today = QDate.currentDate()
        
        self._updating_date_presets = True
        
        if preset == "Hôm qua":
            yesterday = today.addDays(-1)
            self.date_from.setDate(yesterday)
            self.date_to.setDate(yesterday)
        elif preset == "7 ngày trước":
            self.date_from.setDate(today.addDays(-7))
            self.date_to.setDate(today)
        elif preset == "1 tháng trước":
            self.date_from.setDate(today.addMonths(-1))
            self.date_to.setDate(today)
            
        self._updating_date_presets = False
        self.refresh_history_for_selected()

    def _on_date_changed(self):
        if getattr(self, "_updating_date_presets", False):
            return
        
        # Khi người dùng tự tay thay đổi ngày, bỏ chọn preset (setCurrentIndex(-1))
        self.cmb_date_preset.blockSignals(True)
        self.cmb_date_preset.setCurrentIndex(-1)
        self.cmb_date_preset.blockSignals(False)
        self.refresh_history_for_selected()

    def refresh_history_for_selected(self):
        customer_id = self._get_selected_customer_id()
        if customer_id is not None:
            self._render_history(customer_id)

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

        # Áp dụng bộ lọc ngày
        preset = self.cmb_date_preset.currentText()
        filtered_histories = []
        
        for h in histories:
            h_date_str = str(h.get("ngay", "")).strip()
            if not h_date_str:
                if preset == "Tất cả":
                    filtered_histories.append(h)
                continue
            
            try:
                h_date = None
                for fmt in ("%Y-%m-%d", "%d/%m/%Y"):
                    try:
                        h_date = datetime.strptime(h_date_str, fmt).date()
                        break
                    except Exception:
                        continue
                if not h_date:
                    if preset == "Tất cả":
                        filtered_histories.append(h)
                    continue
            except Exception:
                if preset == "Tất cả":
                    filtered_histories.append(h)
                continue
                
            if preset != "Tất cả":
                from_date = self.date_from.date().toPyDate()
                to_date = self.date_to.date().toPyDate()
                if not (from_date <= h_date <= to_date):
                    continue
            
            filtered_histories.append(h)

        for row, history in enumerate(filtered_histories):
            table.insertRow(row)
            table.setItem(row, 0, QTableWidgetItem(history["ngay"]))
            table.setItem(row, 1, QTableWidgetItem(history.get("hang_xe", "")))
            table.setItem(row, 2, QTableWidgetItem(history["bien_so"]))
            table.setItem(row, 3, QTableWidgetItem(history["dich_vu"]))
            table.setItem(row, 4, QTableWidgetItem(self._format_currency(history["tong_tien"])))
            table.setItem(row, 5, QTableWidgetItem(history["ktv"]))

    def record_pos_invoice(
        self,
        customer_name,
        customer_phone,
        total_amount,
        line_items,
        created_at,
        related_order_no=None,
    ):
        self.loyalty_rules = self._load_loyalty_rules()
        customer_phone = (customer_phone or "").strip()
        customer_name = (customer_name or "").strip() or "Khách lẻ"
        total_amount = int(total_amount or 0)
        if total_amount <= 0:
            return

        customer = None
        if customer_phone and customer_phone != "-":
            for c in self.customers:
                if c.get("sdt", "").strip() == customer_phone:
                    customer = c
                    break

        if customer is None:
            customer = self._append_customer(
                {
                    "ten": customer_name,
                    "sdt": customer_phone if customer_phone and customer_phone != "-" else "",
                    "hang_xe": "",
                    "bien_so": "",
                    "email": "",
                    "phan_loai": CLASS_NEW,
                    "diem": 0,
                    "hang_thanh_vien": TIER_DONG,
                    "chiet_khau": 1,
                    "tong_chi_tieu": 0,
                    "ghi_chu": "Tự động tạo từ hóa đơn POS.",
                }
            )
            self.service_history_map.setdefault(customer["id"], [])

        customer["tong_chi_tieu"] = int(customer.get("tong_chi_tieu", 0)) + total_amount
        customer["diem"] = int(customer.get("diem", 0)) + (
            (total_amount // 1_000_000) * int(self.loyalty_rules.get("diem_moi_1trieu", 10))
        )
        _apply_loyalty_rule(customer, self.loyalty_rules)

        technician_name = "POS"
        order_for_vehicle = None
        try:
            ro = str(related_order_no or "").strip()
            if ro:
                order_for_vehicle = get_order(ro)
            if not order_for_vehicle and customer_phone and customer_phone != "-":
                order_for_vehicle = find_latest_order_by_phone(
                    customer_phone,
                    statuses={"DONE", "INVOICED", "PAID", "AFTERCARE"},
                )
            if not order_for_vehicle and customer_phone and customer_phone != "-":
                order_for_vehicle = find_latest_order_by_phone(customer_phone)
            assigned_to = str((order_for_vehicle or {}).get("assigned_to", "")).strip()
            if assigned_to:
                technician_name = assigned_to
        except Exception:
            technician_name = "POS"
            order_for_vehicle = None

        car_model = str((order_for_vehicle or {}).get("car_model", "")).strip()
        plate = str((order_for_vehicle or {}).get("plate", "")).strip()
        if car_model:
            customer["hang_xe"] = self._merge_vehicle_field(customer.get("hang_xe", ""), car_model)
        if plate:
            customer["bien_so"] = self._merge_vehicle_field(customer.get("bien_so", ""), plate)

        service_text = ", ".join(str(it.get("name", "")) for it in (line_items or []) if it.get("name"))
        self.service_history_map.setdefault(customer["id"], []).append(
            {
                "ngay": created_at.split(" ")[0] if created_at else datetime.now().strftime("%d/%m/%Y"),
                "hang_xe": car_model or customer.get("hang_xe", ""),
                "bien_so": plate or customer.get("bien_so", ""),
                "dich_vu": service_text or "Hóa đơn POS",
                "tong_tien": total_amount,
                "ktv": technician_name,
            }
        )
        self._save_all_to_mysql()
        self.refresh_customer_table()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = CustomerManagerWidget()
    window.show()
    sys.exit(app.exec_())
