import sys
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                             QGridLayout, QFrame, QPushButton)
from PyQt5.QtCore import Qt

class DashboardWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.setObjectName("dashboardRoot")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(25)

        # Header Title
        lbl_title = QLabel("TỔNG QUAN HOẠT ĐỘNG")
        lbl_title.setObjectName("dashboardTitle")
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
        lbl_action.setObjectName("dashboardSubTitle")
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
        self._apply_dark_style()

    def _make_stat_card(self, title, value, color, sub):
        card = QFrame()
        card.setObjectName("cardFrame")
        card.setFixedSize(300, 165)
        clay = QVBoxLayout(card)
        clay.setContentsMargins(0, 0, 0, 16)
        clay.setSpacing(10)

        accent = QFrame()
        accent.setObjectName("cardAccent")
        accent.setFixedHeight(4)
        accent.setStyleSheet(f"QFrame#cardAccent {{ background-color: {color}; border: none; }}")
        clay.addWidget(accent)

        inner = QVBoxLayout()
        inner.setContentsMargins(18, 10, 18, 0)
        inner.setSpacing(8)

        lbl_t = QLabel(title.upper())
        lbl_t.setObjectName("cardTitle")
        lbl_v = QLabel(value)
        lbl_v.setObjectName("cardValue")
        lbl_s = QLabel(sub)
        lbl_s.setObjectName("cardSub")

        inner.addWidget(lbl_t)
        inner.addWidget(lbl_v)
        inner.addStretch()
        inner.addWidget(lbl_s)
        clay.addLayout(inner)

        return card

    def _make_action_btn(self, text, brand_color):
        b = QPushButton(text)
        b.setMinimumHeight(45)
        b.setMinimumWidth(200)
        b.setProperty("brandColor", brand_color)
        return b

    def _apply_dark_style(self):
        self.setStyleSheet("""
            QWidget#dashboardRoot {
                background: transparent;
                color: #dbeafe;
                font-family: "Segoe UI";
            }
            QLabel#dashboardTitle {
                color: #f8fafc;
                font-size: 30px;
                font-weight: 800;
            }
            QLabel#dashboardSubTitle {
                color: #93c5fd;
                font-size: 16px;
                font-weight: 700;
            }
            QFrame#cardFrame {
                background-color: #111827;
                border: 1px solid #334155;
                border-radius: 12px;
            }
            QFrame#cardFrame QLabel#cardTitle {
                color: #93c5fd;
                font-size: 11px;
                font-weight: 700;
                letter-spacing: 0.5px;
            }
            QFrame#cardFrame QLabel#cardValue {
                color: #f8fafc;
                font-size: 28px;
                font-weight: 800;
            }
            QFrame#cardFrame QLabel#cardSub {
                color: #cbd5e1;
                font-size: 12px;
                font-weight: 500;
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
        """)
