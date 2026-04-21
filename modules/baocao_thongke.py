from PyQt5.QtCore import QDate, Qt
from PyQt5.QtWidgets import QMainWindow, QTableWidgetItem, QWidget, QVBoxLayout, QHBoxLayout, QLabel
from PyQt5.QtGui import QPainter, QColor, QPen, QFont

from modules.kho_vattu.data_store import nhap_kho_log, xuat_kho_log
from ui.compiled.ui_baocao_thongke import Ui_MainWindow

class BaoCaoKho:
    def tong_nhap(self):
        result = {}
        for item in nhap_kho_log:
            result[item["vat_tu_id"]] = result.get(item["vat_tu_id"], 0) + item["so_luong"]
        return result

    def tong_xuat(self):
        result = {}
        for item in xuat_kho_log:
            result[item["vat_tu_id"]] = result.get(item["vat_tu_id"], 0) + item["so_luong"]
        return result


class ReportBarChartWidget(QWidget):
    def __init__(self, labels=None, values=None, parent=None):
        super().__init__(parent)
        self.labels = labels or []
        self.values = values or []
        self.setMinimumHeight(210)

    def set_data(self, labels, values):
        self.labels = labels
        self.values = values
        self.update()

    def paintEvent(self, event):
        super().paintEvent(event)
        if not self.labels or not self.values:
            return

        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        w, h = self.width(), self.height()
        left, top, right, bottom = 40, 14, 10, 32
        chart_w = max(10, w - left - right)
        chart_h = max(10, h - top - bottom)

        axis_c = QColor("#64748b")
        grid_c = QColor("#334155")
        text_c = QColor("#cbd5e1")
        bar_c = QColor("#38bdf8")

        p.setPen(QPen(axis_c, 1))
        p.drawLine(left, top + chart_h, left + chart_w, top + chart_h)
        p.drawLine(left, top, left, top + chart_h)

        max_v = max(self.values) if self.values else 1
        max_tick = ((max_v + 9) // 10) * 10
        steps = 4
        p.setFont(QFont("Segoe UI", 8))
        for i in range(steps + 1):
            y = top + int(chart_h - chart_h * i / steps)
            val = int(max_tick * i / steps)
            p.setPen(QPen(grid_c, 1))
            p.drawLine(left, y, left + chart_w, y)
            p.setPen(QPen(text_c))
            p.drawText(4, y + 4, str(val))

        n = len(self.values)
        bar_space = chart_w / max(1, n)
        bar_w = max(8, int(bar_space * 0.58))
        for idx, (lbl, val) in enumerate(zip(self.labels, self.values)):
            x_center = left + int((idx + 0.5) * bar_space)
            bar_h = int((val / max_tick) * chart_h) if max_tick else 0
            x = x_center - bar_w // 2
            y = top + chart_h - bar_h
            p.setPen(Qt.NoPen)
            p.setBrush(bar_c)
            p.drawRoundedRect(x, y, bar_w, bar_h, 3, 3)

            p.setPen(QPen(text_c))
            p.setFont(QFont("Segoe UI", 8, QFont.Bold))
            t = str(val)
            tw = p.fontMetrics().horizontalAdvance(t)
            p.drawText(x_center - tw // 2, y - 4, t)

            p.setFont(QFont("Segoe UI", 8))
            lw = p.fontMetrics().horizontalAdvance(lbl)
            p.drawText(x_center - lw // 2, top + chart_h + 16, lbl)


class ReportDonutChartWidget(QWidget):
    def __init__(self, segments=None, parent=None):
        super().__init__(parent)
        self.segments = segments or []
        self.setMinimumHeight(210)

    def set_data(self, segments):
        self.segments = segments
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
        size = max(120, min(w, h) - 28)
        x = (w - size) // 2
        y = (h - size) // 2

        start = 90 * 16
        for _, v, color in self.segments:
            span = int(-360 * 16 * (v / total))
            p.setPen(QPen(QColor("#0f172a"), 1))
            p.setBrush(QColor(color))
            p.drawPie(x, y, size, size, start, span)
            start += span

        inner = int(size * 0.56)
        ix = x + (size - inner) // 2
        iy = y + (size - inner) // 2
        p.setPen(Qt.NoPen)
        p.setBrush(QColor("#111827"))
        p.drawEllipse(ix, iy, inner, inner)


class BaoCaoWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)
        self._apply_dark_style()
        
        self._setup_default_dates()
        self._build_demo_charts()
        self._setup_signals()
        self.show_report_doanh_thu()

    def _setup_default_dates(self):
        today = QDate.currentDate()
        self.ui.date_den_ngay.setDate(today)
        self.ui.date_tu_ngay.setDate(today.addMonths(-1))

    def _setup_signals(self):
        for btn in [self.ui.btn_doanh_thu, self.ui.btn_dich_vu, self.ui.btn_nhan_vien]:
            btn.setCheckable(True)
            btn.setAutoExclusive(True)

        self.ui.btn_doanh_thu.clicked.connect(self.show_report_doanh_thu)
        self.ui.btn_dich_vu.clicked.connect(self.show_report_dich_vu)
        self.ui.btn_nhan_vien.clicked.connect(self.show_report_nhan_vien)
        self.ui.btn_doanh_thu.setChecked(True)

    def _build_demo_charts(self):
        # Tỷ lệ hiển thị 2 khung biểu đồ: cột 60% - tròn 40%
        self.ui.layout_charts.setStretch(0, 6)
        self.ui.layout_charts.setStretch(1, 4)

        self.bar_chart = ReportBarChartWidget()
        self.pie_chart = ReportDonutChartWidget()

        bar_lay = QVBoxLayout(self.ui.chart_bar_month_placeholder)
        bar_lay.setContentsMargins(0, 0, 0, 0)
        bar_lay.addWidget(self.bar_chart)
        bar_lay.setStretch(0, 1)

        pie_lay = QVBoxLayout(self.ui.chart_pie_revenue_placeholder)
        pie_lay.setContentsMargins(0, 0, 0, 0)
        pie_row = QHBoxLayout()
        pie_row.setContentsMargins(0, 0, 0, 0)
        pie_row.setSpacing(12)
        pie_row.addWidget(self.pie_chart, 6)

        legend_wrap = QWidget()
        legend_wrap.setObjectName("pieLegendWrap")
        legend_lay = QVBoxLayout(legend_wrap)
        legend_lay.setContentsMargins(0, 6, 0, 0)
        legend_lay.setSpacing(8)
        legend_lay.addStretch()
        self.lbl_pie_legend_1 = QLabel()
        self.lbl_pie_legend_2 = QLabel()
        self.lbl_pie_legend_3 = QLabel()
        for w in (self.lbl_pie_legend_1, self.lbl_pie_legend_2, self.lbl_pie_legend_3):
            w.setObjectName("pieLegendLabel")
            w.setAlignment(Qt.AlignCenter)
            legend_lay.addWidget(w)
        legend_lay.addStretch()
        pie_row.addWidget(legend_wrap, 4)
        pie_row.setStretch(0, 6)
        pie_row.setStretch(1, 4)
        pie_lay.addLayout(pie_row)

    def _update_demo_charts(self, bar_labels, bar_values, pie_segments):
        self.bar_chart.set_data(bar_labels, bar_values)
        self.pie_chart.set_data(pie_segments)
        legend_widgets = [self.lbl_pie_legend_1, self.lbl_pie_legend_2, self.lbl_pie_legend_3]
        for idx, lbl in enumerate(legend_widgets):
            if idx < len(pie_segments):
                name, value, color = pie_segments[idx]
                lbl.setText(f'<span style="color:{color};">●</span>  {name}: {value}%')
            else:
                lbl.setText("")

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
            QGroupBox#group_chart_bar_month,
            QGroupBox#group_chart_pie_revenue {
                border: 1px solid #334155;
                border-radius: 10px;
                padding-top: 8px;
            }
            QFrame#chart_bar_month_placeholder,
            QFrame#chart_pie_revenue_placeholder {
                border: none;
            }
            QGroupBox {
                margin-top: 12px;
                padding-top: 8px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                subcontrol-position: top left;
                left: 10px;
                top: -1px;
                padding: 0 6px;
                color: #93c5fd;
                font-weight: 700;
            }
            QLabel {
                color: #dbeafe;
            }
            #lbl_summary {
                color: #22d3ee;
                font-weight: 800;
            }
            QDateEdit, QComboBox, QLineEdit {
                background-color: #0f172a;
                color: #e2e8f0;
                border: 1px solid #334155;
                border-radius: 8px;
                padding: 6px 10px;
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
            QPushButton:checked {
                background-color: #0284c7;
                border: 1px solid #38bdf8;
                color: #f8fafc;
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
            QHeaderView::section {
                background-color: #1e293b;
                color: #bae6fd;
                border: 0px;
                padding: 8px;
                font-weight: 700;
            }
            QLabel#pieLegendLabel {
                color: #f8fafc;
                font-size: 13px;
                font-weight: 600;
                background-color: #111827;
                border: none;
                padding: 2px 4px;
            }
            QWidget#pieLegendWrap {
                background-color: #111827;
                border: none;
            }
            QLabel#lbl_chart_bar_month_desc,
            QLabel#lbl_chart_pie_revenue_desc {
                border: none;
                background: transparent;
                color: #cbd5e1;
            }
        """)

    def _render_table(self, headers, rows):
        table = self.ui.table_report
        table.clear()
        table.setColumnCount(len(headers))
        table.setHorizontalHeaderLabels(headers)
        table.setRowCount(len(rows))
        
        # Make the table fill horizontally and hide vertical headers (row indices)
        from PyQt5.QtWidgets import QHeaderView, QAbstractItemView
        table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        table.verticalHeader().setVisible(False)
        table.setSelectionBehavior(QAbstractItemView.SelectRows)
        table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        table.setAlternatingRowColors(True)

        for row_idx, row_data in enumerate(rows):
            for col_idx, value in enumerate(row_data):
                table.setItem(row_idx, col_idx, QTableWidgetItem(str(value)))
        table.resizeColumnsToContents()

    def show_report_doanh_thu(self):
        rows = [
            ("Rửa xe + hút bụi", 120, "18.000.000"),
            ("Phủ ceramic", 34, "22.100.000"),
            ("Bảo dưỡng tổng quát", 15, "19.500.000"),
        ]
        self._render_table(["Dịch vụ", "Số lượt", "Doanh thu (VND)"], rows)
        self.ui.lbl_summary.setText("Tổng doanh thu: 59.600.000 VND")
        self._update_demo_charts(
            ["T1", "T2", "T3", "T4", "T5", "T6"],
            [42, 55, 61, 58, 75, 69],
            [("Rửa xe", 35, "#38bdf8"), ("Ceramic", 30, "#f59e0b"), ("Bảo dưỡng", 20, "#10b981"), ("Khác", 15, "#a78bfa")],
        )

    def show_report_dich_vu(self):
        rows = [
            ("Rửa xe + hút bụi", 120),
            ("Phủ ceramic", 34),
            ("Vệ sinh khoang máy", 21),
            ("Đánh bóng đèn pha", 17),
        ]
        self._render_table(["Dịch vụ", "Số lượt"], rows)
        self.ui.lbl_summary.setText("Tổng lượt dịch vụ: 192")
        self._update_demo_charts(
            ["Top1", "Top2", "Top3", "Top4", "Top5"],
            [120, 34, 21, 17, 14],
            [("Rửa xe", 45, "#38bdf8"), ("Ceramic", 25, "#f59e0b"), ("Khoang máy", 18, "#10b981"), ("Khác", 12, "#a78bfa")],
        )

    def show_report_nhan_vien(self):
        rows = [
            ("Minh", 58, "97%"),
            ("Đạt", 47, "94%"),
            ("Phúc", 45, "92%"),
            ("Khánh", 42, "90%"),
        ]
        self._render_table(["Nhân viên", "Số xe phục vụ", "Hiệu suất"], rows)
        self.ui.lbl_summary.setText("Số nhân viên có dữ liệu: 4")
        self._update_demo_charts(
            ["Minh", "Đạt", "Phúc", "Khánh"],
            [58, 47, 45, 42],
            [("Nhóm A", 40, "#38bdf8"), ("Nhóm B", 33, "#f59e0b"), ("Nhóm C", 27, "#10b981")],
        )