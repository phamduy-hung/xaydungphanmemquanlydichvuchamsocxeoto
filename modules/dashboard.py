from datetime import date, timedelta
import math

from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                            QFrame, QPushButton)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QPainter, QColor, QPen, QFont
from ui.compiled.ui_dashboard import Ui_Form as Ui_Form_Dashboard

from database.connection import ensure_mysql_ready
from database.models import fetch_dashboard_snapshot
from utils.animated_stack import HoverCardFrame


class SimpleBarChartWidget(QWidget):
    def __init__(self, labels, values, parent=None):
        super().__init__(parent)
        self.labels = labels or []
        self.values = values or []
        self.setMinimumHeight(220)

    def set_data(self, labels, values):
        self.labels = labels or []
        self.values = values or []
        self.update()

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
        grid_color = QColor("#222e44")
        text_color = QColor("#cbd5e1")
        bar_color = QColor("#0ea5e9")

        # Axes
        p.setPen(QPen(axis_color, 1))
        p.drawLine(left, top + chart_h, left + chart_w, top + chart_h)   # X
        p.drawLine(left, top, left, top + chart_h)                        # Y

        vals = [float(v) for v in self.values] if self.values else []
        max_v = max(vals) if vals else 0.0
        steps = 4
        if max_v <= 0:
            max_tick = 1.0
        else:
            pow10 = 10 ** math.floor(math.log10(max(max_v, 1e-9)))
            step = max(pow10 / 5.0, 1.0)
            max_tick = math.ceil(max_v / step) * step
            max_tick = max(max_tick, 1.0)

        # Y ticks + grid
        p.setFont(QFont("Segoe UI", 8))
        for i in range(steps + 1):
            y = top + int(chart_h - (chart_h * i / steps))
            val = max_tick * i / steps
            p.setPen(QPen(grid_color, 1))
            p.drawLine(left, y, left + chart_w, y)
            p.setPen(QPen(text_color))
            if val >= 1_000_000:
                txt = f"{val/1_000_000:.1f}M"
            elif val >= 1000:
                txt = f"{int(val/1000)}k"
            else:
                txt = f"{int(round(val))}"
            p.drawText(4, y + 4, txt)

        # Bars + X labels
        n = len(self.values)
        bar_space = chart_w / max(1, n)
        bar_w = max(8, int(bar_space * 0.58))

        for idx, (lbl, val) in enumerate(zip(self.labels, self.values)):
            x_center = left + int((idx + 0.5) * bar_space)
            fv = float(val)
            bar_h = int((fv / max_tick) * chart_h) if max_tick else 0
            x = x_center - bar_w // 2
            y = top + chart_h - bar_h

            p.setPen(Qt.NoPen)
            p.setBrush(bar_color)
            p.drawRoundedRect(x, y, bar_w, bar_h, 3, 3)

            p.setPen(QPen(text_color))
            p.setFont(QFont("Segoe UI", 8, QFont.Bold))
            if fv >= 1_000_000:
                value_text = f"{fv/1_000_000:.1f}M"
            elif fv >= 1000:
                value_text = f"{int(round(fv/1000))}k"
            else:
                value_text = f"{int(round(fv))}"
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

    def set_segments(self, segments):
        self.segments = segments or []
        self.update()

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
        p.setBrush(QColor("#121824"))
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

        self._stat_value_labels = []
        self._stat_sub_labels = []
        self._bar_chart = None
        self._bar_desc = None
        self._pie_chart = None
        self._pie_legend_lay = None

        stat_specs = [
            ("Doanh thu hôm nay", "#10b981"),
            ("Lệnh đang xử lý", "#0ea5e9"),
            ("Đặt lịch web (hôm nay)", "#f59e0b"),
            ("Khách CRM mới (hôm nay)", "#8b5cf6"),
        ]
        for title, color in stat_specs:
            card, lbl_v, lbl_s = self._make_stat_card(title, "…", color, "…")
            self.ui.layout_stat_cards.addWidget(card)
            self._stat_value_labels.append(lbl_v)
            self._stat_sub_labels.append(lbl_s)
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

        quick_lay = QHBoxLayout()
        quick_lay.setSpacing(16)
        quick_lay.addWidget(self._make_quick_bar_card())
        quick_lay.addWidget(self._make_quick_pie_card())
        quick_lay.addStretch()
        self.ui.layout_quick_charts.addLayout(quick_lay)

        self._apply_dark_style()
        self.refresh_data()

    def refresh_data(self):
        """Tải KPI và biểu đồ từ MySQL (hóa đơn paid, lệnh dịch vụ, web_bookings, customers)."""
        try:
            ensure_mysql_ready()
            d = fetch_dashboard_snapshot()
        except Exception as exc:
            err = str(exc).strip() or type(exc).__name__
            err_short = err if len(err) <= 240 else (err[:237] + "…")
            for lbl in self._stat_value_labels:
                lbl.setText("—")
            self._stat_sub_labels[0].setWordWrap(True)
            self._stat_sub_labels[0].setText(f"Lỗi: {err_short}")
            self._stat_sub_labels[0].setToolTip(err)
            for i in range(1, 4):
                self._stat_sub_labels[i].setWordWrap(True)
                self._stat_sub_labels[i].setText("Không tải KPI — cùng nguyên nhân thẻ Doanh thu.")
                self._stat_sub_labels[i].setToolTip(err)
            if self._bar_chart:
                self._bar_chart.set_data([], [])
            if self._pie_chart:
                self._pie_chart.set_segments([])
            self._rebuild_pie_legend(0, 0, 0, 0, 0)
            if self._bar_desc:
                self._bar_desc.setWordWrap(True)
                self._bar_desc.setText(
                    f"Lỗi kết nối/query: {err_short}\n\n"
                    "Gợi ý: bật dịch vụ MySQL; tạo database và import mysql_schema_seed.sql; "
                    "kiểm tra file .env (DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASS); "
                    "DB_ENABLED=1. Chạy app từ thư mục gốc project để đọc đúng .env."
                )
            return

        rev_today = d["revenue_today"]
        pct = d["revenue_change_pct"]
        if pct is None:
            rev_sub = "So với hôm qua: chưa có dữ liệu"
        elif d["revenue_yesterday"] <= 0 and rev_today <= 0:
            rev_sub = "So với hôm qua: không phát sinh"
        else:
            arrow = "↑" if pct >= 0 else "↓"
            rev_sub = f"{arrow} {abs(pct):.1f}% so với hôm qua"

        self._stat_value_labels[0].setText(self._fmt_vnd(rev_today))
        self._stat_sub_labels[0].setText(rev_sub)

        pipe = d["pipeline_orders"]
        owe = d["orders_awaiting_payment"]
        self._stat_value_labels[1].setText(str(pipe))
        self._stat_sub_labels[1].setText(f"{owe} lệnh chờ thanh toán (DONE/INVOICED)" if owe else "Không có lệnh chờ thanh toán")

        wb_t = d["web_bookings_today"]
        wb_p = d["web_bookings_pending"]
        self._stat_value_labels[2].setText(str(wb_t))
        self._stat_sub_labels[2].setText(f"{wb_p} đơn web đang chờ duyệt")

        nc = d["new_customers_today"]
        nc_w = d["new_customers_week"]
        self._stat_value_labels[3].setText(str(nc))
        self._stat_sub_labels[3].setText(f"Tuần này (từ T2): {nc_w} khách mới")

        if self._bar_chart:
            self._bar_chart.set_data(d["bar_labels"], d["bar_values"])
        if self._bar_desc:
            self._bar_desc.setText(
                "Tổng total_amount hóa đơn trạng thái paid theo ngày tạo (MySQL invoices)."
            )

        pie_new, pie_run, pie_end, pie_cancel, pie_other = d["pie_counts"]
        all_seg = [
            ("Tiếp nhận / báo giá", pie_new, "#0ea5e9"),
            ("Đang thực hiện", pie_run, "#f59e0b"),
            ("Hoàn tất / thanh toán", pie_end, "#10b981"),
            ("Đã hủy", pie_cancel, "#64748b"),
            ("Trạng thái khác", pie_other, "#a78bfa"),
        ]
        seg_donut = [(a, b, c) for a, b, c in all_seg if b > 0]
        if self._pie_chart:
            self._pie_chart.set_segments(seg_donut)
        self._rebuild_pie_legend(pie_new, pie_run, pie_end, pie_cancel, pie_other)

    @staticmethod
    def _fmt_vnd(n):
        try:
            x = int(round(float(n)))
            return f"{x:,} đ".replace(",", ".")
        except Exception:
            return "—"

    def _rebuild_pie_legend(self, pie_new, pie_run, pie_end, pie_cancel, pie_other):
        if not self._pie_legend_lay:
            return
        while self._pie_legend_lay.count():
            item = self._pie_legend_lay.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()
        total = pie_new + pie_run + pie_end + pie_cancel + pie_other
        if total == 0:
            empty = QLabel("Chưa có lệnh dịch vụ tạo trong ngày hôm nay (MySQL service_orders).")
            empty.setObjectName("quickChartDesc")
            empty.setWordWrap(True)
            self._pie_legend_lay.addWidget(empty)
            return
        specs = [
            ("Tiếp nhận / báo giá", pie_new, "#0ea5e9"),
            ("Đang thực hiện", pie_run, "#f59e0b"),
            ("Hoàn tất / thanh toán", pie_end, "#10b981"),
            ("Đã hủy", pie_cancel, "#64748b"),
            ("Trạng thái khác", pie_other, "#a78bfa"),
        ]
        for name, cnt, color in specs:
            if cnt <= 0:
                continue
            pct_txt = f"{100.0 * cnt / total:.0f}%"
            row = QHBoxLayout()
            dot = QLabel("●")
            dot.setStyleSheet(f"color: {color}; font-size: 14px;")
            lbl = QLabel(f"{name}: {cnt} ({pct_txt})")
            lbl.setObjectName("quickPieLabel")
            row.addWidget(dot)
            row.addWidget(lbl)
            row.addStretch()
            wrap = QWidget()
            wl = QVBoxLayout(wrap)
            wl.setContentsMargins(0, 0, 0, 0)
            wl.addLayout(row)
            self._pie_legend_lay.addWidget(wrap)

    def _make_stat_card(self, title, value, color, sub):
        card = HoverCardFrame()
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

        return card, lbl_v, lbl_s

    def _make_action_btn(self, text, brand_color):
        b = QPushButton(text)
        b.setMinimumHeight(45)
        b.setMinimumWidth(200)
        b.setProperty("brandColor", brand_color)
        return b

    def _make_quick_bar_card(self):
        card = HoverCardFrame()
        card.setObjectName("quickChartCard")
        card.setMinimumWidth(480)
        lay = QVBoxLayout(card)
        lay.setContentsMargins(16, 14, 16, 14)
        lay.setSpacing(8)

        title = QLabel("Doanh thu 7 ngày gần nhất (hóa đơn đã thanh toán)")
        title.setObjectName("quickChartTitle")
        lay.addWidget(title)

        start_day = date.today() - timedelta(days=6)
        labels = [(start_day + timedelta(days=i)).strftime("%d/%m") for i in range(7)]
        chart = SimpleBarChartWidget(labels, [0] * 7)
        self._bar_chart = chart
        lay.addWidget(chart)

        desc = QLabel("Đang tải dữ liệu từ MySQL…")
        desc.setWordWrap(True)
        desc.setObjectName("quickChartDesc")
        lay.addWidget(desc)
        self._bar_desc = desc
        return card

    def _make_quick_pie_card(self):
        card = HoverCardFrame()
        card.setObjectName("quickChartCard")
        card.setMinimumWidth(360)
        lay = QVBoxLayout(card)
        lay.setContentsMargins(16, 14, 16, 14)
        lay.setSpacing(8)

        title = QLabel("Lệnh dịch vụ tạo trong ngày (theo trạng thái)")
        title.setObjectName("quickChartTitle")
        lay.addWidget(title)

        chart = SimpleDonutChartWidget([])
        self._pie_chart = chart
        lay.addWidget(chart)

        legend_container = QWidget()
        legend_lay = QVBoxLayout(legend_container)
        legend_lay.setContentsMargins(0, 0, 0, 0)
        legend_lay.setSpacing(4)
        lay.addWidget(legend_container)
        self._pie_legend_lay = legend_lay

        return card

    def _apply_dark_style(self):
        self.setStyleSheet("""
            QWidget#dashboardRoot {
                background: transparent;
                color: #e2e8f0;
                font-family: "Segoe UI", "Inter";
            }
            QLabel#dashboardTitle {
                color: #f8fafc;
                font-size: 30px;
                font-weight: 800;
            }
            QLabel#dashboardSubTitle {
                color: #0ea5e9;
                font-size: 16px;
                font-weight: 700;
            }
            QFrame#quickChartCard {
                background-color: #121824;
                border: 1px solid #222e44;
                border-radius: 12px;
            }
            QLabel#quickChartTitle {
                color: #0ea5e9;
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
                background-color: #121824;
                border: 1px solid #222e44;
                border-radius: 12px;
            }
            QFrame#cardFrame QLabel#cardTitle {
                color: #cbd5e1;
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
                color: #94a3b8;
                font-size: 12px;
                font-weight: 500;
            }
            QPushButton {
                background-color: #161e2e;
                color: #e2e8f0;
                border: 1px solid #27354a;
                border-radius: 8px;
                font-weight: 700;
                font-size: 13px;
                padding: 9px 14px;
            }
            QPushButton:hover {
                background-color: #f97316;
                border: 1px solid #ff7a22;
                color: #ffffff;
            }
        """)
