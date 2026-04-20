import sys
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                             QTableWidget, QTableWidgetItem, QHeaderView, 
                             QPushButton, QLineEdit, QFrame, QAbstractItemView)
from PyQt5.QtCore import Qt

class POSWidget(QWidget):
    def __init__(self):
        super().__init__()
        layout = QHBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(20)

        # Left: Services & Products Grid (Table format for now)
        left_panel = QVBoxLayout()
        left_panel.setSpacing(15)
        
        lbl_avail = QLabel("📦 DANH MỤC DỊCH VỤ & VẬT TƯ")
        lbl_avail.setStyleSheet("color: #0f172a; font-size: 18pt; font-weight: 800;")
        left_panel.addWidget(lbl_avail)

        search = QLineEdit()
        search.setPlaceholderText("Gõ để tìm kiếm dịch vụ hoặc sản phẩm...")
        search.setStyleSheet("padding: 12px; font-size: 11pt; border: 1px solid #cbd5e1; border-radius: 8px; background: #ffffff;")
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
        right_panel.setStyleSheet("""
            QFrame { 
                background: #ffffff; 
                border: 1px solid #e2e8f0; 
                border-radius: 12px; 
            }
        """)
        right_lay = QVBoxLayout(right_panel)
        right_lay.setContentsMargins(25, 25, 25, 25)
        right_lay.setSpacing(15)

        lbl_cart = QLabel("🗒️ HÓA ĐƠN CHI TIẾT")
        lbl_cart.setStyleSheet("border: none; color: #0ea5e9; font-size: 16pt; font-weight: 900;")
        right_lay.addWidget(lbl_cart)

        # Customer selection
        cust_box = QFrame()
        cust_box.setStyleSheet("background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 8px;")
        cust_lay = QVBoxLayout(cust_box)
        
        lbl_c_title = QLabel("KHÁCH HÀNG")
        lbl_c_title.setStyleSheet("border: none; font-size: 8pt; font-weight: 800; color: #64748b;")
        cust_lay.addWidget(lbl_c_title)

        cust_search = QLineEdit()
        cust_search.setPlaceholderText("SĐT hoặc Tên khách...")
        cust_search.setStyleSheet("padding: 5px; font-size: 11pt; border: none; background: transparent;")
        cust_lay.addWidget(cust_search)
        right_lay.addWidget(cust_box)

        self.tbl_cart = QTableWidget()
        self.tbl_cart.setColumnCount(3)
        self.tbl_cart.setHorizontalHeaderLabels(["Sản phẩm", "SL", "T.Tiền"])
        c_header = self.tbl_cart.horizontalHeader()
        c_header.setSectionResizeMode(QHeaderView.Stretch)
        c_header.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.tbl_cart.verticalHeader().setVisible(False)
        self.tbl_cart.setStyleSheet("border: none; border-bottom: 2px dashed #cbd5e1;")
        
        # Mock cart
        self.tbl_cart.setRowCount(1)
        self.tbl_cart.setItem(0, 0, QTableWidgetItem("Nước hoa xe hơi"))
        self.tbl_cart.setItem(0, 1, QTableWidgetItem("1"))
        self.tbl_cart.setItem(0, 2, QTableWidgetItem("650.000"))
        right_lay.addWidget(self.tbl_cart)

        # Summary
        sum_lay = QHBoxLayout()
        lbl_total_t = QLabel("TỔNG CỘNG:")
        lbl_total_t.setStyleSheet("border: none; font-size: 16pt; font-weight: bold; color: #334155;")
        lbl_total_v = QLabel("650.000 đ")
        lbl_total_v.setStyleSheet("border: none; font-size: 20pt; font-weight: 900; color: #10b981;")
        sum_lay.addWidget(lbl_total_t)
        sum_lay.addStretch()
        sum_lay.addWidget(lbl_total_v)
        right_lay.addLayout(sum_lay)

        btn_pay = QPushButton("THANH TOÁN (F9)")
        btn_pay.setMinimumHeight(55)
        btn_pay.setStyleSheet("""
            QPushButton { background-color: #0ea5e9; color: #ffffff; border-radius: 8px; font-size: 16pt; font-weight: 900; }
            QPushButton:hover { background-color: #0284c7; }
        """)
        right_lay.addWidget(btn_pay)

        layout.addWidget(right_panel, stretch=1)
