class BaoCaoKho:
    def __init__(self, db):
        self.db = db

    def thong_ke_nhap(self):
        return self.db.execute("""
            SELECT vat_tu_id, SUM(so_luong)
            FROM nhap_kho
            GROUP BY vat_tu_id
        """).fetchall()

    def thong_ke_xuat(self):
        return self.db.execute("""
            SELECT vat_tu_id, SUM(so_luong)
            FROM xuat_kho
            GROUP BY vat_tu_id
        """).fetchall()