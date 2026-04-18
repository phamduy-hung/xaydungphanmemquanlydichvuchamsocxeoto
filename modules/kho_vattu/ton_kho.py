from modules.kho_vattu.data_store import ton_kho, vattu_list

class TonKho:

    def xem_ton(self):
        result = []
        for vt in vattu_list:
            so_luong = ton_kho.get(vt["id"], 0)
            result.append((vt["ten"], so_luong))
        return result

    def canh_bao_ton_thap(self):
        warning = []
        for vt in vattu_list:
            so_luong = ton_kho.get(vt["id"], 0)
            if so_luong < vt["min"]:
                warning.append((vt["ten"], so_luong, vt["min"]))
        return warning