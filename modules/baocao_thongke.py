import sys
import os
import pandas as pd
from PyQt5 import QtWidgets, uic, QtCore

# 1. Dữ liệu mẫu để báo cáo có số liệu hiển thị
data_source = [
    {'ngay': '2024-03-01', 'dich_vu': 'Rửa xe', 'doanh_thu': 100000, 'chi_phi': 20000, 'nhan_vien': 'An'},
    {'ngay': '2024-03-05', 'dich_vu': 'Thay nhớt', 'doanh_thu': 600000, 'chi_phi': 400000, 'nhan_vien': 'Bình'},
    {'ngay': '2024-03-10', 'dich_vu': 'Phủ Ceramic', 'doanh_thu': 5000000, 'chi_phi': 2500000, 'nhan_vien': 'An'},
    {'ngay': '2024-03-12', 'dich_vu': 'Rửa xe', 'doanh_thu': 100000, 'chi_phi': 20000, 'nhan_vien': 'Chi'},
    {'ngay': '2024-03-15', 'dich_vu': 'Vệ sinh nội thất', 'doanh_thu': 1500000, 'chi_phi': 500000, 'nhan_vien': 'Bình'},
]

class BaoCaoWindow(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        
        # --- CƠ CHẾ TỰ TÌM FILE .UI ---
        # Lấy đường dẫn đến thư mục chứa file .py đang mở này
        thu_muc_hien_tai = os.path.dirname(os.path.abspath(__file__))
        # Nối tên file .ui vào đường dẫn đó
        duong_dan_ui = os.path.join(thu_muc_hien_tai, 'baocao_thongke.ui')
        
        # Nạp giao diện
        try:
            uic.loadUi(duong_dan_ui, self)
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, "Lỗi nạp UI", f"Không tìm thấy file UI tại:\n{duong_dan_ui}")
            return

        # 2. Xử lý dữ liệu với Pandas
        self.df = pd.DataFrame(data_source)
        self.df['ngay'] = pd.to_datetime(self.df['ngay'])

        # 3. Cài đặt các giá trị mặc định cho UI (Ngày tháng)
        # Lưu ý: Các tên date_tu_ngay, btn_doanh_thu... phải khớp với ObjectName trong Qt Designer
        if hasattr(self, 'date_tu_ngay'):
            self.date_tu_ngay.setDate(QtCore.QDate(2024, 3, 1))
            self.date_den_ngay.setDate(QtCore.QDate.currentDate())

        # 4. Kết nối các nút bấm
        self.btn_doanh_thu.clicked.connect(self.thong_ke_doanh_thu)
        self.btn_dich_vu.clicked.connect(self.thong_ke_dich_vu)
        self.btn_nhan_vien.clicked.connect(self.thong_ke_nhan_vien)

    def display_to_table(self, df_display):
        """Hàm hỗ trợ hiển thị bảng dữ liệu"""
        self.table_report.setRowCount(len(df_display))
        self.table_report.setColumnCount(len(df_display.columns))
        self.table_report.setHorizontalHeaderLabels(df_display.columns)

        for row_idx, row_data in enumerate(df_display.values):
            for col_idx, cell_data in enumerate(row_data):
                val = f"{cell_data:,}" if isinstance(cell_data, (int, float)) else str(cell_data)
                self.table_report.setItem(row_idx, col_idx, QtWidgets.QTableWidgetItem(val))
        self.table_report.resizeColumnsToContents()

    def thong_ke_doanh_thu(self):
        # Lấy ngày từ UI và lọc dữ liệu
        tu = pd.to_datetime(self.date_tu_ngay.date().toPyDate())
        den = pd.to_datetime(self.date_den_ngay.date().toPyDate())
        df_filter = self.df[(self.df['ngay'] >= tu) & (self.df['ngay'] <= den)].copy()
        
        df_filter['loi_nhuan'] = df_filter['doanh_thu'] - df_filter['chi_phi']
        report = df_filter.groupby(df_filter['ngay'].dt.date).agg({
            'doanh_thu': 'sum',
            'loi_nhuan': 'sum'
        }).reset_index()
        report.columns = ['Ngày', 'Doanh thu (VNĐ)', 'Lợi nhuận (VNĐ)']
        
        self.lbl_summary.setText(f"Tổng doanh thu: {report['Doanh thu (VNĐ)'].sum():,} VNĐ")
        self.display_to_table(report)

    def thong_ke_dich_vu(self):
        report = self.df.groupby('dich_vu').agg({
            'dich_vu': 'count',
            'doanh_thu': 'sum'
        }).rename(columns={'dich_vu': 'Số lượt', 'doanh_thu': 'Tổng tiền'}).reset_index()
        self.display_to_table(report.sort_values(by='Số lượt', ascending=False))

    def thong_ke_nhan_vien(self):
        report = self.df.groupby('nhan_vien').agg({
            'dich_vu': 'count',
            'doanh_thu': 'sum'
        }).rename(columns={'dich_vu': 'Số lượt làm', 'doanh_thu': 'Doanh số tạo ra'}).reset_index()
        self.display_to_table(report)

if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    window = BaoCaoWindow()
    window.show()
    sys.exit(app.exec_())