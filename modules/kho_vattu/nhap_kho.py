from database.models import get_product_by_id, update_product_stock, insert_inventory_transaction


class NhapKho:

    def nhap(self, product_id, so_luong, reason='Nhập kho', reference_no=''):
        try:
            product = get_product_by_id(product_id)
            if not product:
                raise ValueError("Product not found")

            new_stock = product["current_stock"] + so_luong
            update_product_stock(product_id, new_stock)
            insert_inventory_transaction(product_id, 'IN', so_luong, reason, reference_no)
        except Exception as e:
            print(f"Error importing stock: {e}")
            raise