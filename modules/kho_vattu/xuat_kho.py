from modules.kho_vattu.data_store import ton_kho, xuat_kho_log

class XuatKho:

    def xuat(self, vat_tu_id, so_luong):
        if ton_kho.get(vat_tu_id, 0) < so_luong:
            print("❌ Không đủ hàng!")
            return

        ton_kho[vat_tu_id] -= so_luong

        xuat_kho_log.append({
            "vat_tu_id": vat_tu_id,
            "so_luong": so_luong
        })