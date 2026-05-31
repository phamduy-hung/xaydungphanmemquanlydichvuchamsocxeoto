from datetime import datetime, timedelta
import importlib

from PyQt5.QtCore import QDate, Qt
from PyQt5.QtWidgets import (
    QMainWindow,
    QTableWidgetItem,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QComboBox,
    QScrollArea,
    QFileDialog,
    QMessageBox,
    QPushButton,
)
from PyQt5.QtGui import QPainter, QColor, QPen, QFont, QPdfWriter

try:
    from modules.kho_vattu.data_store import nhap_kho_log, xuat_kho_log
except Exception:
    # kho_vattu/data_store.py may be deprecated in MySQL-only mode.
    nhap_kho_log, xuat_kho_log = [], []
from modules.integration_data import get_pos_sales
from modules.rbac_runtime import can_do
from modules.audit_log import append_audit_log
from modules.service_orders import list_orders
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
        # Keep bars readable for long date ranges; scrollbar handled by container.
        min_w = max(720, len(self.labels) * 64)
        self.setMinimumWidth(min_w)
        self.resize(min_w, self.height())
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
        label_step = max(1, int(92 / max(1, bar_space)))
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

            if idx % label_step == 0 or idx == n - 1:
                p.setFont(QFont("Segoe UI", 8))
                short_lbl = lbl[:5] if len(lbl) >= 5 else lbl
                lw = p.fontMetrics().horizontalAdvance(short_lbl)
                p.drawText(x_center - lw // 2, top + chart_h + 16, short_lbl)


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
    def __init__(self, current_role="Quản lý", current_user="system"):
        super().__init__()
        self.current_role = current_role
        self.current_user = current_user
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)
        self._current_headers = []
        self._current_rows = []
        self._apply_dark_style()
        
        self._setup_default_dates()
        self._build_demo_charts()
        self._setup_signals()
        self.show_report_doanh_thu()

    def _setup_default_dates(self):
        today = QDate.currentDate()
        self.ui.date_den_ngay.setDate(today)
        self.ui.date_tu_ngay.setDate(today.addMonths(-1))
        # Force Vietnamese date format: day/month/year.
        self.ui.date_tu_ngay.setDisplayFormat("dd/MM/yyyy")
        self.ui.date_den_ngay.setDisplayFormat("dd/MM/yyyy")
        self.ui.date_tu_ngay.setCalendarPopup(True)
        self.ui.date_den_ngay.setCalendarPopup(True)
        self.cmb_period = QComboBox(self)
        self.cmb_period.setObjectName("cmb_period")
        self.cmb_period.addItems(["Tùy chọn", "Theo kỳ (30 ngày)", "Theo quý", "Theo năm"])
        self.ui.layout_filter.insertWidget(0, self.cmb_period)

    def _setup_signals(self):
        for btn in [self.ui.btn_doanh_thu, self.ui.btn_dich_vu, self.ui.btn_nhan_vien]:
            btn.setCheckable(True)
            btn.setAutoExclusive(True)

        self.ui.btn_doanh_thu.clicked.connect(self.show_report_doanh_thu)
        self.ui.btn_dich_vu.clicked.connect(self.show_report_dich_vu)
        self.ui.btn_nhan_vien.clicked.connect(self.show_report_nhan_vien)
        self.ui.btn_xuat_file_excel.clicked.connect(self.export_excel)
        self.ui.btn_xuat_file_pdf.clicked.connect(self.export_pdf)
        self.ui.date_tu_ngay.dateChanged.connect(self._refresh_active_report)
        self.ui.date_den_ngay.dateChanged.connect(self._refresh_active_report)
        self.cmb_period.currentIndexChanged.connect(self._on_period_changed)
        self._ensure_btn_xem()
        self.ui.btn_doanh_thu.setChecked(True)

    def _on_period_changed(self):
        idx = self.cmb_period.currentIndex()
        today = QDate.currentDate()
        if idx == 1:  # kỳ
            self.ui.date_tu_ngay.setDate(today.addDays(-29))
            self.ui.date_den_ngay.setDate(today)
        elif idx == 2:  # quý
            self.ui.date_tu_ngay.setDate(today.addMonths(-3).addDays(1))
            self.ui.date_den_ngay.setDate(today)
        elif idx == 3:  # năm
            self.ui.date_tu_ngay.setDate(today.addYears(-1).addDays(1))
            self.ui.date_den_ngay.setDate(today)
        self._refresh_active_report()

    def _ensure_btn_xem(self):
        if hasattr(self, "btn_xem_bao_cao"):
            return
        self.btn_xem_bao_cao = QPushButton("Xem")
        self.btn_xem_bao_cao.setObjectName("btn_xem_bao_cao")
        self.btn_xem_bao_cao.clicked.connect(self._refresh_active_report)
        # Place right after "Đến ngày" input for intuitive flow.
        try:
            idx_end_date = self.ui.layout_filter.indexOf(self.ui.date_den_ngay)
            if idx_end_date >= 0:
                self.ui.layout_filter.insertWidget(idx_end_date + 1, self.btn_xem_bao_cao)
            else:
                self.ui.layout_filter.addWidget(self.btn_xem_bao_cao)
        except Exception:
            self.ui.layout_filter.addWidget(self.btn_xem_bao_cao)

    def _refresh_active_report(self):
        if self.ui.btn_dich_vu.isChecked():
            self.show_report_dich_vu()
        elif self.ui.btn_nhan_vien.isChecked():
            self.show_report_nhan_vien()
        else:
            self.show_report_doanh_thu()

    def _selected_period(self):
        start_qdate = self.ui.date_tu_ngay.date()
        end_qdate = self.ui.date_den_ngay.date()
        start_dt = datetime(start_qdate.year(), start_qdate.month(), start_qdate.day(), 0, 0, 0)
        end_dt = datetime(end_qdate.year(), end_qdate.month(), end_qdate.day(), 23, 59, 59)
        if end_dt < start_dt:
            start_dt, end_dt = end_dt, start_dt
        return start_dt, end_dt

    @staticmethod
    def _parse_dt(raw):
        if isinstance(raw, datetime):
            return raw
        text = str(raw or "").strip()
        if not text:
            return None
        for fmt in (
            "%d/%m/%Y %H:%M:%S",
            "%d/%m/%Y %H:%M",
            "%Y-%m-%d %H:%M:%S",
            "%Y-%m-%d %H:%M",
            "%Y-%m-%d",
            "%d/%m/%Y",
        ):
            try:
                return datetime.strptime(text, fmt)
            except Exception:
                pass
        return None

    @staticmethod
    def _fmt_vnd(value):
        return f"{int(value):,}".replace(",", ".")

    @staticmethod
    def _month_key(dt_obj):
        return dt_obj.strftime("%m/%Y")

    def _load_pos_sales_in_period(self, start_dt, end_dt):
        rows = []
        for item in get_pos_sales():
            dt_obj = self._parse_dt(item.get("created_at", ""))
            if not dt_obj:
                continue
            if start_dt <= dt_obj <= end_dt:
                rows.append(dict(item))
        return rows

    def _load_orders_in_period(self, start_dt, end_dt):
        rows = []
        for item in list_orders():
            dt_obj = self._parse_dt(item.get("created_at", ""))
            if not dt_obj:
                continue
            if start_dt <= dt_obj <= end_dt:
                rows.append(dict(item))
        return rows

    def _build_demo_charts(self):
        # Tỷ lệ hiển thị 2 khung biểu đồ: cột 60% - tròn 40%
        self.ui.layout_charts.setStretch(0, 6)
        self.ui.layout_charts.setStretch(1, 4)

        self.bar_chart = ReportBarChartWidget()
        self.pie_chart = ReportDonutChartWidget()

        bar_lay = QVBoxLayout(self.ui.chart_bar_month_placeholder)
        bar_lay.setContentsMargins(0, 0, 0, 0)
        self.bar_scroll = QScrollArea()
        self.bar_scroll.setWidgetResizable(False)
        self.bar_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.bar_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.bar_scroll.setFrameShape(QScrollArea.NoFrame)
        self.bar_scroll.setWidget(self.bar_chart)
        bar_lay.addWidget(self.bar_scroll)
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
                background-color: #090d16;
                color: #e2e8f0;
                font-family: "Segoe UI", "Inter";
            }
            QFrame, QGroupBox {
                background-color: #121824;
                border: 1px solid #27354a;
                border-radius: 10px;
            }
            QGroupBox#group_chart_bar_month,
            QGroupBox#group_chart_pie_revenue {
                border: 1px solid #27354a;
                border-radius: 10px;
                padding-top: 8px;
            }
            QFrame#chart_bar_month_placeholder,
            QFrame#chart_pie_revenue_placeholder {
                border: none;
                background-color: transparent;
            }
            QGroupBox {
                margin-top: 18px;
                padding-top: 8px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                subcontrol-position: top left;
                left: 10px;
                top: -3px;
                padding: 0 8px;
                background-color: #090d16;
                color: #0ea5e9;
                font-weight: 700;
            }
            QLabel {
                color: #e2e8f0;
            }
            #lbl_summary {
                color: #f97316;
                font-weight: 800;
            }
            QDateEdit, QComboBox, QLineEdit {
                background-color: #0c101a;
                color: #f8fafc;
                border: 1px solid #27354a;
                border-radius: 8px;
                padding: 6px 10px;
            }
            QDateEdit:focus, QComboBox:focus, QLineEdit:focus {
                border: 1px solid #f97316;
            }
            QPushButton {
                background-color: #161e2e;
                color: #e2e8f0;
                border: 1px solid #27354a;
                border-radius: 10px;
                font-weight: 700;
                font-size: 13px;
                padding: 9px 14px;
            }
            QPushButton:hover {
                background-color: #f97316;
                border: 1px solid #ff7a22;
                color: #ffffff;
            }
            QPushButton:checked {
                background-color: #ea580c;
                border: 1px solid #f97316;
                color: #ffffff;
            }
            QTableWidget {
                background-color: #0c101a;
                alternate-background-color: #121824;
                color: #e2e8f0;
                border: 1px solid #27354a;
                gridline-color: #1b2336;
                selection-background-color: #0ea5e9;
                selection-color: #ffffff;
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
                border-bottom: 2px solid #27354a;
            }
            QLabel#pieLegendLabel {
                color: #f8fafc;
                font-size: 13px;
                font-weight: 600;
                background-color: #121824;
                border: none;
                padding: 2px 4px;
            }
            QWidget#pieLegendWrap {
                background-color: #121824;
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
        self._current_headers = list(headers)
        self._current_rows = [tuple(r) for r in rows]
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

    def _report_title(self):
        if self.ui.btn_doanh_thu.isChecked():
            return "bao_cao_doanh_thu"
        if self.ui.btn_dich_vu.isChecked():
            return "bao_cao_dich_vu"
        if self.ui.btn_nhan_vien.isChecked():
            return "bao_cao_nhan_vien"
        return "bao_cao_thong_ke"

    def export_excel(self):
        if not can_do(self.current_role, "baocao.export_excel"):
            QMessageBox.warning(self, "Không có quyền", "Vai trò hiện tại không có quyền xuất Excel.")
            return
        if not self._current_headers or not self._current_rows:
            QMessageBox.warning(self, "Khong co du lieu", "Khong co du lieu de xuat Excel.")
            return

        default_name = f"{self._report_title()}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
        path, _ = QFileDialog.getSaveFileName(self, "Xuat file Excel", default_name, "Excel Files (*.xlsx)")
        if not path:
            return

        try:
            openpyxl_mod = importlib.import_module("openpyxl")
            styles_mod = importlib.import_module("openpyxl.styles")
            Workbook = openpyxl_mod.Workbook
            Font = styles_mod.Font
            Alignment = styles_mod.Alignment
        except Exception:
            QMessageBox.warning(
                self,
                "Thieu thu vien",
                "Chua co openpyxl de xuat Excel.\nVui long cai dat: pip install openpyxl",
            )
            return

        try:
            wb = Workbook()
            ws = wb.active
            ws.title = "BaoCao"

            ws.append(self._current_headers)
            for row in self._current_rows:
                ws.append(list(row))

            for cell in ws[1]:
                cell.font = Font(bold=True)
                cell.alignment = Alignment(horizontal="center")

            for column_cells in ws.columns:
                max_len = 0
                col_letter = column_cells[0].column_letter
                for cell in column_cells:
                    max_len = max(max_len, len(str(cell.value or "")))
                ws.column_dimensions[col_letter].width = min(max_len + 3, 45)

            wb.save(path)
            append_audit_log("baocao.export_excel", self.current_user, {"path": path})
            QMessageBox.information(self, "Thanh cong", f"Da xuat Excel:\n{path}")
        except Exception as e:
            QMessageBox.critical(self, "Loi", f"Khong the xuat Excel.\nChi tiet: {e}")

    def export_pdf(self):
        if not can_do(self.current_role, "baocao.export_pdf"):
            QMessageBox.warning(self, "Không có quyền", "Vai trò hiện tại không có quyền xuất PDF.")
            return
        if not self._current_headers or not self._current_rows:
            QMessageBox.warning(self, "Khong co du lieu", "Khong co du lieu de xuat PDF.")
            return

        default_name = f"{self._report_title()}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
        path, _ = QFileDialog.getSaveFileName(self, "Xuat file PDF", default_name, "PDF Files (*.pdf)")
        if not path:
            return

        try:
            writer = QPdfWriter(path)
            writer.setResolution(120)
            writer.setPageSizeMM((210, 297))  # A4

            painter = QPainter(writer)
            painter.setRenderHint(QPainter.Antialiasing)

            margin = 50
            x0, y = margin, margin
            page_w = writer.width() - margin * 2

            painter.setFont(QFont("Segoe UI", 14, QFont.Bold))
            painter.drawText(x0, y + 30, self._report_title().replace("_", " ").upper())
            y += 60

            headers = self._current_headers
            rows = self._current_rows
            cols = len(headers)
            col_w = page_w // max(1, cols)
            row_h = 30

            painter.setFont(QFont("Segoe UI", 9, QFont.Bold))
            for i, h in enumerate(headers):
                rx = x0 + i * col_w
                painter.drawRect(rx, y, col_w, row_h)
                painter.drawText(rx + 4, y + 20, str(h))
            y += row_h

            painter.setFont(QFont("Segoe UI", 9))
            for row in rows:
                if y + row_h > writer.height() - margin:
                    writer.newPage()
                    y = margin
                for i, v in enumerate(row):
                    rx = x0 + i * col_w
                    painter.drawRect(rx, y, col_w, row_h)
                    painter.drawText(rx + 4, y + 20, str(v))
                y += row_h

            painter.end()
            append_audit_log("baocao.export_pdf", self.current_user, {"path": path})
            QMessageBox.information(self, "Thanh cong", f"Da xuat PDF:\n{path}")
        except Exception as e:
            QMessageBox.critical(self, "Loi", f"Khong the xuat PDF.\nChi tiet: {e}")

    def show_report_doanh_thu(self):
        start_dt, end_dt = self._selected_period()
        pos_sales = self._load_pos_sales_in_period(start_dt, end_dt)
        orders = self._load_orders_in_period(start_dt, end_dt)

        pos_revenue = sum(int(x.get("grand_total", 0) or 0) for x in pos_sales)
        status_count = {}
        for item in orders:
            status = item.get("status", "UNKNOWN")
            status_count[status] = status_count.get(status, 0) + 1

        daily_revenue = {}
        for item in pos_sales:
            dt_obj = self._parse_dt(item.get("created_at", ""))
            if not dt_obj:
                continue
            key = dt_obj.strftime("%d/%m/%Y")
            daily_revenue[key] = daily_revenue.get(key, 0) + int(item.get("grand_total", 0) or 0)

        labels = []
        values = []
        cursor = datetime(start_dt.year, start_dt.month, start_dt.day)
        end_day = datetime(end_dt.year, end_dt.month, end_dt.day)
        while cursor <= end_day:
            key = cursor.strftime("%d/%m/%Y")
            labels.append(key)
            values.append(int(daily_revenue.get(key, 0)))
            cursor += timedelta(days=1)

        web_customers = set()
        desk_customers = set()
        for item in orders:
            phone = str(item.get("customer_phone", "")).strip()
            if not phone:
                continue
            if str(item.get("source", "")).strip().lower() == "web":
                web_customers.add(phone)
            else:
                desk_customers.add(phone)

        rows = [
            ("Doanh thu POS (đã thanh toán)", len(pos_sales), self._fmt_vnd(pos_revenue)),
            ("Lệnh nguồn web", sum(1 for x in orders if str(x.get("source", "")).lower() == "web"), "-"),
            ("Lệnh tiếp nhận trực tiếp", sum(1 for x in orders if str(x.get("source", "")).lower() != "web"), "-"),
            ("Khách đặt lịch web (unique)", len(web_customers), "-"),
            ("Khách đến trực tiếp (unique)", len(desk_customers), "-"),
            ("Lệnh đang xử lý", status_count.get("IN_SERVICE", 0), "-"),
            ("Lệnh đã hoàn tất", status_count.get("DONE", 0), "-"),
            ("Lệnh đã thanh toán", status_count.get("PAID", 0), "-"),
        ]
        self._render_table(["Chỉ số", "Số lượng", "Giá trị"], rows)
        self.ui.lbl_summary.setText(
            f"Tổng doanh thu kỳ {start_dt.strftime('%d/%m/%Y')} - {end_dt.strftime('%d/%m/%Y')}: {self._fmt_vnd(pos_revenue)} VND"
        )

        pie_total = len(web_customers) + len(desk_customers)
        if pie_total > 0:
            web_pct = int(round(len(web_customers) * 100 / pie_total))
            desk_pct = max(0, 100 - web_pct)
            pie_segments = [
                ("Khách đặt lịch web", web_pct, "#38bdf8"),
                ("Khách đến trực tiếp", desk_pct, "#10b981"),
            ]
        else:
            pie_segments = [("Chưa có dữ liệu", 100, "#64748b")]
        self._update_demo_charts(labels or ["-"], values or [0], pie_segments)
        self.ui.group_chart_bar_month.setTitle("Biểu đồ cột: Doanh thu thực tế theo ngày")
        self.ui.group_chart_pie_revenue.setTitle("Biểu đồ tròn: Khách web vs trực tiếp")
        self.ui.lbl_chart_bar_month_desc.setText("Doanh thu POS thực tế theo từng ngày trong kỳ lọc (kể cả ngày không có doanh thu).")
        self.ui.lbl_chart_pie_revenue_desc.setText("Tỷ lệ số khách đặt lịch web so với khách đến trực tiếp (unique theo SĐT).")

    def show_report_dich_vu(self):
        start_dt, end_dt = self._selected_period()
        orders = self._load_orders_in_period(start_dt, end_dt)
        counts = {}
        revenues = {}
        for item in orders:
            for svc in item.get("service_items", []) or []:
                name = str(svc.get("service_name", "")).strip()
                if not name:
                    continue
                counts[name] = counts.get(name, 0) + 1
                revenues[name] = revenues.get(name, 0) + int(svc.get("unit_price", 0) or 0)

        ranked = sorted(counts.items(), key=lambda x: (-x[1], x[0]))
        rows = [(name, qty, self._fmt_vnd(revenues.get(name, 0))) for name, qty in ranked]
        self._render_table(["Dịch vụ", "Số lượt", "Doanh thu (VND)"], rows)
        self.ui.lbl_summary.setText(f"Tổng lượt dịch vụ: {sum(counts.values())}")

        top = ranked[:6]
        bar_labels = [x[0][:12] + "..." if len(x[0]) > 12 else x[0] for x in top]
        bar_values = [x[1] for x in top]
        total = sum(x[1] for x in top)
        pie_segments = []
        colors = ["#38bdf8", "#f59e0b", "#10b981", "#a78bfa", "#ef4444", "#22d3ee"]
        if total > 0:
            for idx, (name, qty) in enumerate(top[:3]):
                pct = int(round(qty * 100 / total))
                pie_segments.append((name, pct, colors[idx % len(colors)]))
        else:
            pie_segments = [("Chưa có dữ liệu", 100, "#64748b")]
        self._update_demo_charts(bar_labels or ["-"], bar_values or [0], pie_segments)
        self.ui.group_chart_bar_month.setTitle("Biểu đồ cột: Top dịch vụ theo số lượt")
        self.ui.group_chart_pie_revenue.setTitle("Biểu đồ tròn: Cơ cấu top dịch vụ")
        self.ui.lbl_chart_bar_month_desc.setText("Top dịch vụ theo số lượt phát sinh trong kỳ.")
        self.ui.lbl_chart_pie_revenue_desc.setText("Tỷ trọng các dịch vụ phổ biến nhất trong kỳ.")

    def show_report_nhan_vien(self):
        start_dt, end_dt = self._selected_period()
        orders = self._load_orders_in_period(start_dt, end_dt)

        open_status = {"NEW_WEB", "CHECKED_IN", "QUOTED", "APPROVED", "IN_SERVICE", "WAITING_PARTS"}
        served = {}
        completed = {}
        in_progress = {}
        for item in orders:
            tech = str(item.get("assigned_to", "")).strip() or "Chưa phân công"
            served[tech] = served.get(tech, 0) + 1
            status = str(item.get("status", "")).strip()
            if status in {"DONE", "INVOICED", "PAID", "AFTERCARE"}:
                completed[tech] = completed.get(tech, 0) + 1
            if status in open_status:
                in_progress[tech] = in_progress.get(tech, 0) + 1

        techs = sorted(served.keys(), key=lambda t: (-served[t], t))
        rows = []
        for tech in techs:
            s = served.get(tech, 0)
            c = completed.get(tech, 0)
            eff = int(round(c * 100 / s)) if s > 0 else 0
            rows.append((tech, s, c, in_progress.get(tech, 0), f"{eff}%"))
        self._render_table(["Nhân viên", "Tổng lệnh", "Đã hoàn tất", "Đang xử lý", "Hiệu suất"], rows)
        self.ui.lbl_summary.setText(f"Số nhân viên có dữ liệu: {len(techs)}")

        bar_labels = [x[0] for x in rows][:6]
        bar_values = [x[1] for x in rows][:6]
        top_total = sum(bar_values)
        pie_segments = []
        colors = ["#38bdf8", "#f59e0b", "#10b981", "#a78bfa", "#ef4444", "#22d3ee"]
        if top_total > 0:
            for idx, row in enumerate(rows[:3]):
                pct = int(round(row[1] * 100 / top_total))
                pie_segments.append((row[0], pct, colors[idx % len(colors)]))
        else:
            pie_segments = [("Chưa có dữ liệu", 100, "#64748b")]
        self._update_demo_charts(bar_labels or ["-"], bar_values or [0], pie_segments)
        self.ui.group_chart_bar_month.setTitle("Biểu đồ cột: Khối lượng theo nhân viên")
        self.ui.group_chart_pie_revenue.setTitle("Biểu đồ tròn: Tỷ trọng theo nhân viên")
        self.ui.lbl_chart_bar_month_desc.setText("Số lệnh theo nhân viên trong kỳ lọc.")
        self.ui.lbl_chart_pie_revenue_desc.setText("Tỷ trọng khối lượng xử lý của các nhân viên chính.")
