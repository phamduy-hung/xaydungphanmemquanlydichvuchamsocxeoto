import sys
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                             QTableWidget, QTableWidgetItem, QHeaderView, 
                             QPushButton, QLineEdit, QFrame, QAbstractItemView)
from PyQt5.QtCore import Qt

class POSWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.setObjectName("posRoot")
        layout = QHBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(20)

        # Left: Services & Products Grid (Table format for now)
        left_panel = QVBoxLayout()
        left_panel.setSpacing(15)
        
        lbl_avail = QLabel("📦 DANH MỤC DỊCH VỤ & VẬT TƯ")
        lbl_avail.setObjectName("posTitle")
        left_panel.addWidget(lbl_avail)

        search = QLineEdit()
        search.setPlaceholderText("Gõ để tìm kiếm dịch vụ hoặc sản phẩm...")
        left_panel.addWidget(search)

        self.tbl_items = QTableWidget()
        self.tbl_items.setColumnCount(3)
        self.tbl_items.setHorizontalHeaderLabels(["Dịch vụ / Sản phẩm", "Đơn giá", "Loại"])
        header = self.tbl_items.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.Stretch)
        self.tbl_items.verticalHeader().setVisible(False)
        self.tbl_items.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.tbl_items.setEditTriggers(QAbstractItemView.NoEditTriggers)
        
        # Add some mock items
        items = [
            ("Rửa xe detailing bọt tuyết", "150.000", "Dịch vụ"),
            ("Phủ Ceramic 9H Pro", "4.500.000", "Dịch vụ"),
            ("Vệ sinh dàn lạnh", "300.000", "Dịch vụ"),
            ("Nước hoa xe hơi (Chai)", "650.000", "Sản phẩm"),
            ("Dầu nhớt Castrol 1L", "145.000", "Sản phẩm")
        ]
        self.tbl_items.setRowCount(len(items))
        for r, (name, price, type_) in enumerate(items):
            self.tbl_items.setItem(r, 0, QTableWidgetItem(name))
            self.tbl_items.setItem(r, 1, QTableWidgetItem(price))
            self.tbl_items.setItem(r, 2, QTableWidgetItem(type_))
        
        left_panel.addWidget(self.tbl_items)
        layout.addLayout(left_panel, stretch=2)

        # Right: Cart / Receipt 
        right_panel = QFrame()
        right_panel.setObjectName("posCard")
        right_lay = QVBoxLayout(right_panel)
        right_lay.setContentsMargins(25, 25, 25, 25)
        right_lay.setSpacing(15)

        lbl_cart = QLabel("🗒️ HÓA ĐƠN CHI TIẾT")
        lbl_cart.setObjectName("posTitle")
        right_lay.addWidget(lbl_cart)

        # Customer selection
        cust_box = QFrame()
        cust_lay = QVBoxLayout(cust_box)
        
        lbl_c_title = QLabel("KHÁCH HÀNG")
        lbl_c_title.setObjectName("posSubTitle")
        cust_lay.addWidget(lbl_c_title)

        cust_search = QLineEdit()
        cust_search.setPlaceholderText("SĐT hoặc Tên khách...")
        cust_lay.addWidget(cust_search)
        right_lay.addWidget(cust_box)

        self.tbl_cart = QTableWidget()
        self.tbl_cart.setColumnCount(3)
        self.tbl_cart.setHorizontalHeaderLabels(["Sản phẩm", "SL", "T.Tiền"])
        c_header = self.tbl_cart.horizontalHeader()
        c_header.setSectionResizeMode(QHeaderView.Stretch)
        c_header.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.tbl_cart.verticalHeader().setVisible(False)
        
        # Mock cart
        self.tbl_cart.setRowCount(1)
        self.tbl_cart.setItem(0, 0, QTableWidgetItem("Nước hoa xe hơi"))
        self.tbl_cart.setItem(0, 1, QTableWidgetItem("1"))
        self.tbl_cart.setItem(0, 2, QTableWidgetItem("650.000"))
        right_lay.addWidget(self.tbl_cart)

        # Summary
        sum_lay = QHBoxLayout()
        lbl_total_t = QLabel("TỔNG CỘNG:")
        lbl_total_v = QLabel("650.000 đ")
        lbl_total_t.setObjectName("posSubTitle")
        lbl_total_v.setObjectName("posTotal")
        sum_lay.addWidget(lbl_total_t)
        sum_lay.addStretch()
        sum_lay.addWidget(lbl_total_v)
        right_lay.addLayout(sum_lay)

        btn_pay = QPushButton("THANH TOÁN (F9)")
        btn_pay.setObjectName("btnPay")
        btn_pay.setMinimumHeight(55)
        right_lay.addWidget(btn_pay)

        layout.addWidget(right_panel, stretch=1)
        self._apply_dark_style()

    def _apply_dark_style(self):
        self.setStyleSheet("""
            QWidget#posRoot {
                background: transparent;
                color: #dbeafe;
                font-family: "Segoe UI";
            }
            QLabel#posTitle {
                color: #f8fafc;
                font-size: 18px;
                font-weight: 800;
            }
            QLabel#posSubTitle {
                color: #93c5fd;
                font-weight: 700;
            }
            QLabel#posTotal {
                color: #22d3ee;
                font-size: 20px;
                font-weight: 800;
            }
            QFrame#posCard, QFrame {
                background-color: #111827;
                border: 1px solid #334155;
                border-radius: 12px;
            }
            QLineEdit {
                background-color: #0f172a;
                color: #e2e8f0;
                border: 1px solid #334155;
                border-radius: 8px;
                padding: 8px 10px;
            }
            QLineEdit:focus {
                border: 1px solid #38bdf8;
            }
            QTableWidget {
                background-color: #0f172a;
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
            QPushButton#btnPay {
                background-color: #0ea5e9;
                border: 1px solid #38bdf8;
                color: #f8fafc;
                font-size: 16px;
            }
            QPushButton#btnPay:hover {
                background-color: #0284c7;
            }
        """)
