from database.models import (
    load_products, get_product_by_id, get_product_by_code,
    insert_product, update_product, delete_product
)


class QuanLyVatTu:

    def danh_sach(self):
        try:
            products = load_products()
            if not products:
                return []
            # Convert to old format for compatibility
            return [{
                "id": p["id"],
                "ma": str(p.get("product_code") or "").strip() or f"VT{int(p['id']):03d}",
                "ten": p["name"],
                "loai": p["category"],
                "don_vi": p["unit"],
                "gia": float(p["price"]),
                "min": p["min_stock"],
                "ton": int(p.get("current_stock") or 0),
            } for p in products]
        except Exception as e:
            print(f"Error loading products: {e}")
            return []

    def tim_kiem(self, keyword):
        try:
            products = load_products()
            if not products:
                return []
            filtered = [
                p for p in products
                if keyword.lower() in p["name"].lower()
                or keyword.lower() in str(p.get("product_code") or "").lower()
            ]
            return [{
                "id": p["id"],
                "ma": str(p.get("product_code") or "").strip() or f"VT{int(p['id']):03d}",
                "ten": p["name"],
                "loai": p["category"],
                "don_vi": p["unit"],
                "gia": float(p["price"]),
                "min": p["min_stock"],
                "ton": int(p.get("current_stock") or 0),
            } for p in filtered]
        except Exception as e:
            print(f"Error searching products: {e}")
            return []

    def them(self, ten, loai, don_vi, gia, min_ton):
        try:
            # Generate product code
            products = load_products()
            next_code = f"VT{len(products) + 1:03d}"
            product_id = insert_product(next_code, ten, loai, don_vi, gia, min_ton)
            return product_id
        except Exception as e:
            print(f"Error adding product: {e}")
            raise

    def sua(self, product_id, ten, loai, don_vi, gia, min_ton):
        try:
            product = get_product_by_id(product_id)
            if not product:
                raise ValueError("Product not found")
            update_product(product_id, product["product_code"], ten, loai, don_vi, gia, min_ton)
        except Exception as e:
            print(f"Error updating product: {e}")
            raise

    def xoa(self, product_id):
        try:
            product = get_product_by_id(product_id)
            if not product:
                raise ValueError("Product not found")
            delete_product(product_id)
        except Exception as e:
            print(f"Error deleting product: {e}")
            raise

    def lay_theo_id(self, product_id):
        try:
            product = get_product_by_id(product_id)
            if not product:
                return None
            return {
                "id": product["id"],
                "ma": str(product.get("product_code") or "").strip() or f"VT{int(product['id']):03d}",
                "ten": product["name"],
                "loai": product["category"],
                "don_vi": product["unit"],
                "gia": float(product["price"]),
                "min": product["min_stock"],
                "ton": int(product.get("current_stock") or 0),
            }
        except Exception as e:
            print(f"Error getting product by id: {e}")
            return None