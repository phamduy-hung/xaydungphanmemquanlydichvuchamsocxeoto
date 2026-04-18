from modules.kho_vattu.data_store import vattu_list

class QuanLyVatTu:

    def danh_sach(self):
        return vattu_list

    def tim_kiem(self, keyword):
        return [vt for vt in vattu_list if keyword.lower() in vt["ten"].lower()]

    def them(self, ten, loai, don_vi, gia, min_ton):
        new_id = max(v["id"] for v in vattu_list) + 1
        vattu_list.append({
            "id": new_id,
            "ten": ten,
            "loai": loai,
            "don_vi": don_vi,
            "gia": gia,
            "min": min_ton
        })