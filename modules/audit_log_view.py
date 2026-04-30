import csv
from pathlib import Path

from PyQt5.QtWidgets import (
    QFileDialog,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from modules.audit_log import load_audit_logs


class AuditLogViewWidget(QWidget):
    def __init__(self):
        super().__init__()
        self._build_ui()
        self._apply_style()
        self.refresh_data()

    def _build_ui(self):
        root = QVBoxLayout(self)
        title = QLabel("NHẬT KÝ HỆ THỐNG")
        title.setObjectName("auditTitle")
        root.addWidget(title)

        filters = QHBoxLayout()
        self.txt_actor = QLineEdit()
        self.txt_actor.setPlaceholderText("Lọc theo người thao tác...")
        self.txt_action = QLineEdit()
        self.txt_action.setPlaceholderText("Lọc theo hành động...")
        self.btn_filter = QPushButton("Lọc")
        self.btn_filter.clicked.connect(self.apply_filters)
        filters.addWidget(self.txt_actor)
        filters.addWidget(self.txt_action)
        filters.addWidget(self.btn_filter)
        root.addLayout(filters)

        row = QHBoxLayout()
        row.addStretch()
        self.btn_refresh = QPushButton("Làm mới")
        self.btn_export = QPushButton("Xuất CSV")
        self.btn_refresh.clicked.connect(self.refresh_data)
        self.btn_export.clicked.connect(self.export_csv)
        row.addWidget(self.btn_refresh)
        row.addWidget(self.btn_export)
        root.addLayout(row)

        self.tbl = QTableWidget()
        self.tbl.setColumnCount(4)
        self.tbl.setHorizontalHeaderLabels(["Thời gian", "Người thực hiện", "Hành động", "Chi tiết"])
        self.tbl.verticalHeader().setVisible(False)
        self.tbl.setAlternatingRowColors(True)
        header = self.tbl.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.Stretch)
        root.addWidget(self.tbl)

    def _apply_style(self):
        self.setStyleSheet(
            """
            QWidget { background: transparent; color: #dbeafe; }
            QLabel#auditTitle { color: #f8fafc; font-size: 18px; font-weight: 800; border: none; }
            QLineEdit { background:#0f172a; color:#e2e8f0; border:1px solid #334155; border-radius:8px; padding:6px; }
            QTableWidget {
                background:#0f172a;
                alternate-background-color:#111b31;
                color:#e2e8f0;
                border:1px solid #334155;
                gridline-color:#1f2937;
                selection-background-color:#0ea5e9;
                selection-color:#f8fafc;
            }
            QTableWidget::item {
                background-color:#0f172a;
                color:#e2e8f0;
            }
            QTableWidget::item:alternate {
                background-color:#111b31;
                color:#e2e8f0;
            }
            QHeaderView::section { background:#1e293b; color:#bae6fd; border:0; padding:7px; font-weight:700; }
            QPushButton { background:#1e293b; color:#e2e8f0; border:1px solid #334155; border-radius:10px; padding:8px; }
            """
        )

    def refresh_data(self):
        self._all_logs = list(reversed(load_audit_logs()))
        self.apply_filters()

    def apply_filters(self):
        logs = list(getattr(self, "_all_logs", []))
        actor_key = (self.txt_actor.text() or "").strip().lower()
        action_key = (self.txt_action.text() or "").strip().lower()
        if actor_key:
            logs = [x for x in logs if actor_key in str(x.get("actor", "")).lower()]
        if action_key:
            logs = [x for x in logs if action_key in str(x.get("action", "")).lower()]
        self._shown_logs = logs
        self.tbl.setRowCount(0)
        for row, log in enumerate(logs):
            self.tbl.insertRow(row)
            self.tbl.setItem(row, 0, QTableWidgetItem(str(log.get("at", "-"))))
            self.tbl.setItem(row, 1, QTableWidgetItem(str(log.get("actor", "-"))))
            self.tbl.setItem(row, 2, QTableWidgetItem(str(log.get("action", "-"))))
            self.tbl.setItem(row, 3, QTableWidgetItem(str(log.get("detail", {}))))

    def export_csv(self):
        logs = list(getattr(self, "_shown_logs", []))
        if not logs:
            return
        save_path, _ = QFileDialog.getSaveFileName(
            self, "Xuất nhật ký hệ thống", "nhat_ky_he_thong.csv", "CSV Files (*.csv)"
        )
        if not save_path:
            return
        path = Path(save_path)
        with path.open("w", newline="", encoding="utf-8-sig") as f:
            writer = csv.writer(f)
            writer.writerow(["Thời gian", "Người thực hiện", "Hành động", "Chi tiết"])
            for row in logs:
                writer.writerow(
                    [
                        str(row.get("at", "-")),
                        str(row.get("actor", "-")),
                        str(row.get("action", "-")),
                        str(row.get("detail", {})),
                    ]
                )
