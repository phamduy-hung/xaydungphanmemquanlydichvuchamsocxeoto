import sys
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                             QPushButton, QFrame, QFormLayout, QLineEdit, 
                             QComboBox, QCheckBox, QScrollArea)
from PyQt5.QtCore import Qt

class SettingsWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.setObjectName("settingsRoot")
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(30, 30, 30, 30)

        lbl_title = QLabel("CÀI ĐẶT HỆ THỐNG")
        main_layout.addWidget(lbl_title)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)

        container = QWidget()
        container.setObjectName("settingsContainer")
        lay = QVBoxLayout(container)
        lay.setSpacing(25)

        lay.addWidget(self._make_section("1. Chỉnh sửa Thông tin cửa hàng", self._form_store_info()))
        lay.addWidget(self._make_section("2. Kết nối API & Website", self._form_api()))
        lay.addWidget(self._make_section("3. Tích hợp thanh toán & Hóa đơn", self._form_payment()))

        lay.addStretch()
        scroll.setWidget(container)
        main_layout.addWidget(scroll)

        # Save Action
        b_lay = QHBoxLayout()
        b_lay.addStretch()
        btn_save = QPushButton("LƯU CÀI ĐẶT")
        btn_save.setObjectName("btnSaveSettings")
        btn_save.setMinimumHeight(45)
        btn_save.setMinimumWidth(200)
        b_lay.addWidget(btn_save)
        main_layout.addLayout(b_lay)
        self._apply_dark_style()

    def _make_section(self, title, content_widget):
        frame = QFrame()
        frame.setObjectName("settingsSection")
        flay = QVBoxLayout(frame)
        flay.setContentsMargins(20, 20, 20, 20)

        lbl = QLabel(title)
        lbl.setObjectName("settingsSectionTitle")
        flay.addWidget(lbl)

        flay.addWidget(content_widget)
        return frame

    def _form_store_info(self):
        w = QWidget()
        f = QFormLayout(w)
        f.setSpacing(15)
        
        t1 = QLineEdit("ProCare TPHCM")
        t2 = QLineEdit("Số 123 Đường Sài Gòn, Quận 1, TPHCM")
        t3 = QLineEdit("0999 888 777")
        
        f.addRow(self._lbl("Tên Trung Tâm:"), t1)
        f.addRow(self._lbl("Địa Chỉ:"), t2)
        f.addRow(self._lbl("Hotline:"), t3)
        return w

    def _form_api(self):
        w = QWidget()
        f = QFormLayout(w)
        f.setSpacing(15)
        
        t1 = QLineEdit("http://localhost:8765/api")
        t2 = QLineEdit("sk_prod_123456789xxxx")
        cb = QCheckBox("Bật đồng bộ Web Bookings Tự Động")
        cb.setChecked(True)
        f.addRow(self._lbl("Endpoint Website:"), t1)
        f.addRow(self._lbl("API Key (Bảo mật):"), t2)
        f.addRow(self._lbl("Đồng bộ:"), cb)
        return w
        
    def _form_payment(self):
        w = QWidget()
        f = QFormLayout(w)
        f.setSpacing(15)

        c = QComboBox()
        c.addItems(["Khổ giấy 80mm", "Khổ giấy 58mm", "Khổ A4"])
        t = QLineEdit("10%")
        
        f.addRow(self._lbl("Máy In Hóa Đơn:"), c)
        f.addRow(self._lbl("Mặc định Thuế VAT:"), t)
        return w

    def _lbl(self, text):
        l = QLabel(text)
        l.setObjectName("settingsLabel")
        return l

    def _apply_dark_style(self):
        self.setStyleSheet("""
            QWidget#settingsRoot {
                background: transparent;
                color: #dbeafe;
                font-family: "Segoe UI", "Inter";
            }
            QScrollArea {
                border: none;
                background: transparent;
            }
            QScrollArea QWidget#qt_scrollarea_viewport {
                background-color: #0b1220;
            }
            QWidget#settingsContainer {
                background-color: #0b1220;
            }
            QFrame#settingsSection {
                background-color: #111827;
                border: 1px solid #334155;
                border-radius: 12px;
            }
            QLabel#settingsSectionTitle {
                color: #93c5fd;
                font-size: 14px;
                font-weight: 800;
            }
            QLabel#settingsLabel {
                color: #cbd5e1;
                font-weight: 600;
            }
            QLineEdit, QComboBox {
                background-color: #0f172a;
                color: #e2e8f0;
                border: 1px solid #334155;
                border-radius: 8px;
                padding: 7px 10px;
            }
            QLineEdit:focus, QComboBox:focus {
                border: 1px solid #38bdf8;
            }
            QCheckBox {
                color: #cbd5e1;
            }
            QPushButton#btnSaveSettings {
                background-color: #0ea5e9;
                color: #f8fafc;
                border: 1px solid #38bdf8;
                border-radius: 10px;
                font-weight: 700;
                font-size: 13px;
                padding: 8px 14px;
            }
            QPushButton#btnSaveSettings:hover {
                background-color: #0284c7;
            }
        """)
