import sys
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                             QPushButton, QFrame, QFormLayout, QLineEdit, 
                             QComboBox, QCheckBox, QScrollArea)
from PyQt5.QtCore import Qt

class SettingsWidget(QWidget):
    def __init__(self):
        super().__init__()
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(30, 30, 30, 30)

        lbl_title = QLabel("CÀI ĐẶT HỆ THỐNG")
        lbl_title.setStyleSheet("color: #0f172a; font-size: 22pt; font-weight: 900;")
        main_layout.addWidget(lbl_title)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")

        container = QWidget()
        container.setStyleSheet("background: transparent;")
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
        btn_save.setMinimumHeight(45)
        btn_save.setMinimumWidth(200)
        btn_save.setStyleSheet("""
            QPushButton { background-color: #10b981; color: #ffffff; border-radius: 8px; font-weight: bold; font-size: 11pt; }
            QPushButton:hover { background-color: #34d399; }
        """)
        b_lay.addWidget(btn_save)
        main_layout.addLayout(b_lay)

    def _make_section(self, title, content_widget):
        frame = QFrame()
        frame.setStyleSheet("QFrame { background: #ffffff; border: 1px solid #e2e8f0; border-radius: 12px; }")
        flay = QVBoxLayout(frame)
        flay.setContentsMargins(20, 20, 20, 20)

        lbl = QLabel(title)
        lbl.setStyleSheet("border: none; color: #0ea5e9; font-weight: bold; font-size: 14pt; margin-bottom: 10px;")
        flay.addWidget(lbl)
        
        content_widget.setStyleSheet("border: none;")
        flay.addWidget(content_widget)
        return frame

    def _form_store_info(self):
        w = QWidget()
        f = QFormLayout(w)
        f.setSpacing(15)
        
        t1 = QLineEdit("ProCare TPHCM")
        t2 = QLineEdit("Số 123 Đường Sài Gòn, Quận 1, TPHCM")
        t3 = QLineEdit("0999 888 777")
        
        for t in (t1, t2, t3):
            t.setStyleSheet("border: 1px solid #cbd5e1; border-radius: 6px; padding: 8px; font-size: 11pt;")

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
        cb.setStyleSheet("font-size: 11pt; color: #334155;")

        for t in (t1, t2):
            t.setStyleSheet("border: 1px solid #cbd5e1; border-radius: 6px; padding: 8px; font-size: 11pt;")

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
        c.setStyleSheet("border: 1px solid #cbd5e1; border-radius: 6px; padding: 8px; font-size: 11pt;")
        
        t = QLineEdit("10%")
        t.setStyleSheet("border: 1px solid #cbd5e1; border-radius: 6px; padding: 8px; font-size: 11pt; width: 100px;")
        
        f.addRow(self._lbl("Máy In Hóa Đơn:"), c)
        f.addRow(self._lbl("Mặc định Thuế VAT:"), t)
        return w

    def _lbl(self, text):
        l = QLabel(text)
        l.setStyleSheet("color: #475569; font-weight: bold; font-size: 11pt;")
        return l
