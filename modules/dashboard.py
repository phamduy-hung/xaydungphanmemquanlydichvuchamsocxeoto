import sys
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                             QGridLayout, QFrame, QPushButton)
from PyQt5.QtCore import Qt

class DashboardWidget(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(25)

        # Header Title
        lbl_title = QLabel("TỔNG QUAN HOẠT ĐỘNG")
        lbl_title.setStyleSheet("color: #0f172a; font-size: 22pt; font-weight: 900; letter-spacing: -0.5px;")
        layout.addWidget(lbl_title)

        # Stat cards row
        grid = QHBoxLayout()
        grid.setSpacing(25)

        grid.addWidget(self._make_stat_card("Doanh thu hôm nay", "18.540.000 đ", "#10b981", "↑ 12% so với hôm qua"))
        grid.addWidget(self._make_stat_card("Xe đang xử lý", "8", "#0ea5e9", "3 xe sắp hoàn thiện"))
        grid.addWidget(self._make_stat_card("Lịch hẹn mới", "14", "#f59e0b", "2 đơn chờ tiếp nhận"))
        grid.addWidget(self._make_stat_card("Khách hàng mới", "5", "#8b5cf6", "Tăng 2% tuần này"))
        grid.addStretch()

        layout.addLayout(grid)

        # Quick actions
        lbl_action = QLabel("Thao tác nhanh")
        lbl_action.setStyleSheet("color: #475569; font-size: 14pt; font-weight: bold; margin-top: 10px;")
        layout.addWidget(lbl_action)

        actions_lay = QHBoxLayout()
        actions_lay.setSpacing(15)
        
        btn1 = self._make_action_btn("Tạo Hóa Đơn Mới", "#10b981")
        btn2 = self._make_action_btn("Nhập Vật Tư", "#0ea5e9")
        btn3 = self._make_action_btn("Gửi Thông Báo Tới Khách", "#6366f1")
        
        actions_lay.addWidget(btn1)
        actions_lay.addWidget(btn2)
        actions_lay.addWidget(btn3)
        actions_lay.addStretch()

        layout.addLayout(actions_lay)
        layout.addStretch()

    def _make_stat_card(self, title, value, color, sub):
        card = QFrame()
        card.setObjectName("cardFrame")
        card.setGraphicsEffect(None) # Potential shadow if I want but CSS is safer
        card.setFixedSize(280, 160)
        clay = QVBoxLayout(card)
        clay.setContentsMargins(25, 25, 25, 25)
        clay.setSpacing(10)

        lbl_t = QLabel(title.upper())
        lbl_t.setStyleSheet(f"color: {color}; font-size: 10pt; font-weight: 800; border: none;")
        
        lbl_v = QLabel(value)
        lbl_v.setStyleSheet(f"color: #0f172a; font-size: 26pt; font-weight: 900; border: none;")
        
        lbl_s = QLabel(sub)
        lbl_s.setStyleSheet("color: #64748b; font-size: 10pt; border: none;")

        clay.addWidget(lbl_t)
        clay.addWidget(lbl_v)
        clay.addStretch()
        clay.addWidget(lbl_s)

        # Colorful left accent
        card.setStyleSheet(f"""
            QFrame#cardFrame {{
                background-color: #ffffff;
                border: 1px solid #e2e8f0;
                border-radius: 12px;
                border-left: 6px solid {color};
            }}
        """)
        return card

    def _make_action_btn(self, text, brand_color):
        b = QPushButton(text)
        b.setMinimumHeight(45)
        b.setMinimumWidth(200)
        b.setStyleSheet(f"""
            QPushButton {{
                background-color: #ffffff;
                color: {brand_color};
                border: 1px solid {brand_color};
                border-radius: 8px;
                font-weight: bold;
                font-size: 11pt;
            }}
            QPushButton:hover {{
                background-color: {brand_color};
                color: #ffffff;
            }}
        """)
        return b
