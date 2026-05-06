from database.models import load_products, get_low_stock_products


class TonKho:

    def xem_ton(self):
        try:
            products = load_products()
            if not products:
                return []
            result = []
            for p in products:
                result.append((p["name"], p["current_stock"]))
            return result
        except Exception as e:
            print(f"Error getting stock levels: {e}")
            return []

    def canh_bao_ton_thap(self):
        try:
            low_stock = get_low_stock_products()
            if not low_stock:
                return []
            warning = []
            for p in low_stock:
                warning.append((p["name"], p["current_stock"], p["min_stock"]))
            return warning
        except Exception as e:
            print(f"Error getting low stock warnings: {e}")
            return []