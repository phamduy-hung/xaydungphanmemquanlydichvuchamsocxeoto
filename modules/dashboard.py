from datetime import date, timedelta
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                            QFrame, QPushButton)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QPainter, QColor, QPen, QFont
from ui.compiled.ui_dashboard import Ui_Form as Ui_Form_Dashboard


class SimpleBarChartWidget(QWidget):
    def __init__(self, labels, values, parent=None):
        super().__init__(parent)
        self.labels = labels
        self.values = values
        self.setMinimumHeight(220)

    def paintEvent(self, event):
        super().paintEvent(event)
        if not self.labels or not self.values:
            return

        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)

        w = self.width()
        h = self.height()
        left, top, right, bottom = 42, 14, 12, 32
        chart_w = max(10, w - left - right)
        chart_h = max(10, h - top - bottom)

        axis_color = QColor("#64748b")
        grid_color = QColor("#334155")
        text_color = QColor("#cbd5e1")
        bar_color = QColor("#34d399")

        # Axes
        p.setPen(QPen(axis_color, 1))
        p.drawLine(left, top + chart_h, left + chart_w, top + chart_h)   # X
        p.drawLine(left, top, left, top + chart_h)                        # Y

        max_v = max(self.values) if self.values else 1
        max_tick = ((max_v + 9) // 10) * 10
        steps = 4

        # Y ticks + grid
        p.setFont(QFont("Segoe UI", 8))
        for i in range(steps + 1):
            y = top + int(chart_h - (chart_h * i / steps))
            val = int(max_tick * i / steps)
            p.setPen(QPen(grid_color, 1))
            p.drawLine(left, y, left + chart_w, y)
            p.setPen(QPen(text_color))
            p.drawText(4, y + 4, f"{val}")

        # Bars + X labels
        n = len(self.values)
        bar_space = chart_w / max(1, n)
        bar_w = max(8, int(bar_space * 0.58))

        for idx, (lbl, val) in enumerate(zip(self.labels, self.values)):
            x_center = left + int((idx + 0.5) * bar_space)
            bar_h = int((val / max_tick) * chart_h) if max_tick else 0
            x = x_center - bar_w // 2
            y = top + chart_h - bar_h

            p.setPen(Qt.NoPen)
            p.setBrush(bar_color)
            p.drawRoundedRect(x, y, bar_w, bar_h, 3, 3)

            p.setPen(QPen(text_color))
            p.setFont(QFont("Segoe UI", 8, QFont.Bold))
            value_text = f"{val}"
            value_w = p.fontMetrics().horizontalAdvance(value_text)
            p.drawText(x_center - value_w // 2, y - 4, value_text)

            p.setFont(QFont("Segoe UI", 8))
            label_w = p.fontMetrics().horizontalAdvance(lbl)
            p.drawText(x_center - label_w // 2, top + chart_h + 16, lbl)


class SimpleDonutChartWidget(QWidget):
    def __init__(self, segments, parent=None):
        super().__init__(parent)
        self.segments = segments  # [(name, value, color_hex)]
        self.setMinimumHeight(220)

    def paintEvent(self, event):
        super().paintEvent(event)
        if not self.segments:
            return
        total = sum(v for _, v, _ in self.segments)
        if total <= 0:
            return

        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)

        w, h = self.width(), self.height()
        size = min(w, h) - 36
        size = max(120, size)
        x = (w - size) // 2
        y = (h - size) // 2

        start_angle = 90 * 16
        for _, value, color in self.segments:
            span = int(-360 * 16 * (value / total))
            p.setPen(QPen(QColor("#0f172a"), 1))
            p.setBrush(QColor(color))
            p.drawPie(x, y, size, size, start_angle, span)
            start_angle += span

        # inner hole
        inner = int(size * 0.56)
        ix = x + (size - inner) // 2
        iy = y + (size - inner) // 2
        p.setPen(Qt.NoPen)
        p.setBrush(QColor("#111827"))
        p.drawEllipse(ix, iy, inner, inner)

class DashboardWidget(QWidget):
    go_to_pos = pyqtSignal()
    go_to_kho = pyqtSignal()
    go_to_cskh = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.ui = Ui_Form_Dashboard()
        self.ui.setupUi(self)
        self.setObjectName("dashboardRoot")
        self.ui.lbl_dashboard_title.setObjectName("dashboardTitle")
        self.ui.lbl_action_title.setObjectName("dashboardSubTitle")
        self.ui.lbl_quick_title.setObjectName("dashboardSubTitle")

        # Stat cards row
        self.ui.layout_stat_cards.addWidget(
            self._make_stat_card("Doanh thu hôm nay", "18.540.000 đ", "#10b981", "↑ 12% so với hôm qua")
        )
        self.ui.layout_stat_cards.addWidget(
            self._make_stat_card("Xe đang xử lý", "8", "#0ea5e9", "3 xe sắp hoàn thiện")
        )
        self.ui.layout_stat_cards.addWidget(
            self._make_stat_card("Lịch hẹn mới", "14", "#f59e0b", "2 đơn chờ tiếp nhận")
        )
        self.ui.layout_stat_cards.addWidget(
            self._make_stat_card("Khách hàng mới", "5", "#8b5cf6", "Tăng 2% tuần này")
        )
        self.ui.layout_stat_cards.addStretch()

        # Quick actions
        actions_lay = self.ui.layout_action_buttons
        
        btn1 = self._make_action_btn("Tạo Hóa Đơn Mới", "#10b981")
        btn2 = self._make_action_btn("Nhập Vật Tư", "#0ea5e9")
        btn3 = self._make_action_btn("Gửi Thông Báo Tới Khách", "#6366f1")
        btn1.clicked.connect(self.go_to_pos.emit)
        btn2.clicked.connect(self.go_to_kho.emit)
        btn3.clicked.connect(self.go_to_cskh.emit)
        
        actions_lay.addWidget(btn1)
        actions_lay.addWidget(btn2)
        actions_lay.addWidget(btn3)
        actions_lay.addStretch()

        # Lightweight charts for quick snapshot (no heavy chart engine).
        quick_lay = QHBoxLayout()
        quick_lay.setSpacing(16)
        quick_lay.addWidget(self._make_quick_bar_card())
        quick_lay.addWidget(self._make_quick_pie_card())
        quick_lay.addStretch()
        self.ui.layout_quick_charts.addLayout(quick_lay)

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

    def _make_quick_bar_card(self):
        card = QFrame()
        card.setObjectName("quickChartCard")
        card.setMinimumWidth(480)
        lay = QVBoxLayout(card)
        lay.setContentsMargins(16, 14, 16, 14)
        lay.setSpacing(8)

        title = QLabel("Doanh thu 7 ngày gần nhất")
        title.setObjectName("quickChartTitle")
        lay.addWidget(title)

        start_day = date.today() - timedelta(days=6)
        labels = [(start_day + timedelta(days=i)).strftime("%d/%m") for i in range(7)]
        values = [32, 38, 62, 51, 52, 53, 43]
        chart = SimpleBarChartWidget(labels, values)
        lay.addWidget(chart)

        desc = QLabel("Biểu đồ cột thể hiện doanh số theo thời gian; trục X là mốc thời gian, trục Y là giá trị doanh số.")
        desc.setWordWrap(True)
        desc.setObjectName("quickChartDesc")
        lay.addWidget(desc)
        return card

    def _make_quick_pie_card(self):
        card = QFrame()
        card.setObjectName("quickChartCard")
        card.setMinimumWidth(360)
        lay = QVBoxLayout(card)
        lay.setContentsMargins(16, 14, 16, 14)
        lay.setSpacing(8)

        title = QLabel("Cơ cấu đơn hôm nay")
        title.setObjectName("quickChartTitle")
        lay.addWidget(title)

        segments = [
            ("Đơn mới", "40%", "#0ea5e9"),
            ("Đang xử lý", "35%", "#f59e0b"),
            ("Hoàn tất", "25%", "#10b981"),
        ]
        chart = SimpleDonutChartWidget(
            [
                ("Đơn mới", 40, "#0ea5e9"),
                ("Đang xử lý", 35, "#f59e0b"),
                ("Hoàn tất", 25, "#10b981"),
            ]
        )
        lay.addWidget(chart)

        for name, pct, color in segments:
            row = QHBoxLayout()
            dot = QLabel("●")
            dot.setStyleSheet(f"color: {color}; font-size: 14px;")
            lbl = QLabel(f"{name}: {pct}")
            lbl.setObjectName("quickPieLabel")
            row.addWidget(dot)
            row.addWidget(lbl)
            row.addStretch()
            lay.addLayout(row)

        # desc = QLabel("Cơ cấu đơn hôm nay gồm: đơn mới 40%, đang xử lý 35%, hoàn tất 25%.")
        # desc.setWordWrap(True)
        # desc.setObjectName("quickChartDesc")
        # lay.addWidget(desc)
        return card

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
            QFrame#quickChartCard {
                background-color: #111827;
                border: 1px solid #334155;
                border-radius: 12px;
            }
            QLabel#quickChartTitle {
                color: #93c5fd;
                font-size: 13px;
                font-weight: 700;
            }
            QLabel#quickPieLabel {
                color: #f8fafc;
                font-size: 13px;
                font-weight: 600;
            }
            QLabel#quickChartDesc {
                color: #cbd5e1;
                font-size: 12px;
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
