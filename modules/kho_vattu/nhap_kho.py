from modules.kho_vattu.data_store import ton_kho, nhap_kho_log

class NhapKho:

    def nhap(self, vat_tu_id, so_luong):
        ton_kho[vat_tu_id] = ton_kho.get(vat_tu_id, 0) + so_luong

        nhap_kho_log.append({
            "vat_tu_id": vat_tu_id,
            "so_luong": so_luong
        })