from database.models import get_inventory_transactions


class BaoCaoKho:
    def __init__(self, db=None):
        self.db = db

    def thong_ke_nhap(self):
        try:
            transactions = get_inventory_transactions()
            if not transactions:
                return []
            in_transactions = [t for t in transactions if t['transaction_type'] == 'IN']
            summary = {}
            for t in in_transactions:
                pid = t['product_id']
                summary[pid] = summary.get(pid, 0) + t['quantity']
            return list(summary.items())
        except Exception as e:
            print(f"Error getting import statistics: {e}")
            return []

    def thong_ke_xuat(self):
        try:
            transactions = get_inventory_transactions()
            if not transactions:
                return []
            out_transactions = [t for t in transactions if t['transaction_type'] == 'OUT']
            summary = {}
            for t in out_transactions:
                pid = t['product_id']
                summary[pid] = summary.get(pid, 0) + t['quantity']
            return list(summary.items())
        except Exception as e:
            print(f"Error getting export statistics: {e}")
            return []