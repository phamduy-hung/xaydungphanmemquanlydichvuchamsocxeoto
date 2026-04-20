
from __future__ import annotations

import json
import re
import sys
import uuid
from datetime import date, datetime, timedelta
from pathlib import Path

from PyQt5.QtCore import Qt, QDate
from PyQt5.QtWidgets import (
    QDialog,
    QMessageBox,
    QTableWidgetItem,
    QWidget,
)

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from ui.compiled.ui_chamsocKH import Ui_Form as Ui_ChamSocKHForm
from ui.compiled.ui_them_sua_voucher import Ui_Form as Ui_ThemSuaVoucherForm

DATA_DIR = PROJECT_ROOT / "data"
DATA_FILE = DATA_DIR / "cham_soc_kh_marketing.json"

TIER_DONG = "Đồng"
TIER_BAC = "Bạc"
TIER_VANG = "Vàng"
TIER_VIP = "VIP"

CHIET_KHAU = {TIER_DONG: 1, TIER_BAC: 3, TIER_VANG: 5, TIER_VIP: 8}

LOAI_PERCENT = "percent"
LOAI_AMOUNT = "amount"


def _today_iso() -> str:
    return date.today().isoformat()


def _parse_iso(s: str | None) -> date | None:
    if not s:
        return None
    try:
        return date.fromisoformat(str(s)[:10])
    except ValueError:
        return None


def tinh_hang_theo_diem(
    diem: int,
    nguong_dong: int,
    nguong_bac: int,
    nguong_vang: int,
    nguong_vip: int,
) -> str:
    if diem >= nguong_vip:
        return TIER_VIP
    if diem >= nguong_vang:
        return TIER_VANG
    if diem >= nguong_bac:
        return TIER_BAC
    return TIER_DONG


def diem_tu_thanh_toan(so_tien_vnd: int, diem_moi_1trieu: int) -> int:
    return int(so_tien_vnd // 1_000_000) * int(diem_moi_1trieu)


def diem_can_len_hang_tiep(
    diem: int,
    nguong_bac: int,
    nguong_vang: int,
    nguong_vip: int,
) -> str:
    hang = tinh_hang_theo_diem(diem, 0, nguong_bac, nguong_vang, nguong_vip)
    if hang == TIER_VIP:
        return "—"
    targets = []
    if diem < nguong_bac:
        targets.append(nguong_bac)
    if diem < nguong_vang:
        targets.append(nguong_vang)
    if diem < nguong_vip:
        targets.append(nguong_vip)
    if not targets:
        return "—"
    nxt = min(x for x in targets if x > diem)
    return str(max(0, nxt - diem))


def _fmt_money(n: int) -> str:
    return f"{int(n):,}".replace(",", ".") + " đ"


def voucher_trang_thai(v: dict) -> str:
    t = date.today()
    bd = _parse_iso(v.get("ngay_bd"))
    kt = _parse_iso(v.get("ngay_kt"))
    if not bd or not kt:
        return "Không xác định"
    if t < bd:
        return "Chưa bắt đầu"
    if t > kt:
        return "Đã hết hạn"
    return "Đang áp dụng"


def voucher_hinh_thuc_text(v: dict) -> str:
    return "Giảm %" if v.get("loai") == LOAI_PERCENT else "Giảm tiền"


def voucher_gia_tri_hien_thi(v: dict) -> str:
    gt = int(v.get("gia_tri", 0))
    if v.get("loai") == LOAI_PERCENT:
        return f"{gt}%"
    return _fmt_money(gt)


class ChamSocMarketingStore:
    def __init__(self) -> None:
        self.data: dict = {}

    def load(self) -> None:
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        if not DATA_FILE.is_file():
            self._default_data()
            self.save()
            return
        try:
            raw = json.loads(DATA_FILE.read_text(encoding="utf-8"))
            if isinstance(raw, dict):
                self.data = raw
                self._migrate_vouchers()
        except (json.JSONDecodeError, OSError):
            self._default_data()
        self.save()

    def _default_data(self) -> None:
        self.data = {
            "loyalty": {
                "diem_moi_1trieu": 10,
                "nguong_dong": 0,
                "nguong_bac": 500,
                "nguong_vang": 1500,
                "nguong_vip": 5000,
                "khach": [
                    {
                        "id": "1",
                        "ten": "Nguyễn Văn A",
                        "sdt": "0901122334",
                        "diem": 120,
                        "hang": TIER_DONG,
                        "chiet_khau": 1,
                    },
                    {
                        "id": "2",
                        "ten": "Trần Thị B",
                        "sdt": "0988777666",
                        "diem": 5200,
                        "hang": TIER_VIP,
                        "chiet_khau": 8,
                    },
                ],
            },
            "vouchers": [],
            "thong_bao": {"sms": True, "zalo": False, "email": False, "mau_cam_on": "", "mau_sinh_nhat": ""},
            "nhat_ky_gui": [],
            "nhac_lich": [],
            "phan_hoi": [],
        }
        self._migrate_vouchers()
        self._seed_demo_voucher()

    def _seed_demo_voucher(self) -> None:
        if self.data.get("vouchers"):
            return
        t = date.today()
        self.data["vouchers"] = [
            {
                "id": str(uuid.uuid4()),
                "ma": "TET2026",
                "ten_chuong_trinh": "Khuyến mãi Tết",
                "loai": LOAI_PERCENT,
                "gia_tri": 10,
                "ngay_bd": t.isoformat(),
                "ngay_kt": t.replace(month=12, day=31).isoformat(),
                "ghi_chu": "Áp dụng toàn bộ dịch vụ",
            }
        ]

    def _migrate_vouchers(self) -> None:
        for v in self.data.get("vouchers", []):
            if "loai" not in v:
                v["loai"] = LOAI_PERCENT
                v["gia_tri"] = int(v.pop("giam_percent", v.get("gia_tri", 10)))
            if "ten_chuong_trinh" not in v:
                v["ten_chuong_trinh"] = v.get("ma", "Voucher")
            het = v.get("het_han") or v.get("ngay_kt")
            if het and "ngay_kt" not in v:
                v["ngay_kt"] = str(het)[:10]
            if "ngay_bd" not in v:
                v["ngay_bd"] = _today_iso()
            if "ghi_chu" not in v:
                v["ghi_chu"] = ""
            v.pop("het_han", None)
            v.pop("con_lai", None)

    def save(self) -> None:
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        DATA_FILE.write_text(json.dumps(self.data, ensure_ascii=False, indent=2), encoding="utf-8")

    def cap_nhat_khach_sau_diem(self, kh: dict, loy: dict) -> None:
        hang = tinh_hang_theo_diem(
            int(kh["diem"]),
            int(loy["nguong_dong"]),
            int(loy["nguong_bac"]),
            int(loy["nguong_vang"]),
            int(loy["nguong_vip"]),
        )
        kh["hang"] = hang
        kh["chiet_khau"] = CHIET_KHAU.get(hang, 1)


_store_singleton: ChamSocMarketingStore | None = None


def get_store() -> ChamSocMarketingStore:
    global _store_singleton
    if _store_singleton is None:
        _store_singleton = ChamSocMarketingStore()
        _store_singleton.load()
    return _store_singleton


def ghi_nhan_thanh_toan_tich_hop(ma_khach_hang: str, so_tien_vnd: int, ten_khach_hang: str = "", sdt: str = "") -> dict | None:
    store = get_store()
    loy = store.data["loyalty"]
    diem_cong = diem_tu_thanh_toan(so_tien_vnd, int(loy["diem_moi_1trieu"]))
    kh = None
    for row in loy["khach"]:
        if str(row["id"]) == str(ma_khach_hang):
            kh = row
            break
    if kh is None:
        kh = {
            "id": str(ma_khach_hang),
            "ten": ten_khach_hang or f"Khách #{ma_khach_hang}",
            "sdt": sdt or "",
            "diem": 0,
            "hang": TIER_DONG,
            "chiet_khau": 1,
        }
        loy["khach"].append(kh)
    kh["diem"] = int(kh["diem"]) + diem_cong
    if ten_khach_hang:
        kh["ten"] = ten_khach_hang
    if sdt:
        kh["sdt"] = sdt
    store.cap_nhat_khach_sau_diem(kh, loy)

    tb = store.data["thong_bao"]
    noi_dung = (tb.get("mau_cam_on") or "Cảm ơn {ten}! Hóa đơn: {link_hd}").replace("{ten}", kh["ten"]).replace(
        "{ma_hd}", f"HD-{datetime.now().strftime('%Y%m%d%H%M')}"
    ).replace("{link_hd}", "https://hoadon.example.com/x")
    store.data["nhat_ky_gui"].insert(
        0,
        {
            "thoi_gian": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "kenh": _kenh_hien_thi(tb),
            "tom_tat": noi_dung[:200],
        },
    )
    store.save()
    return {"khach": kh, "diem_cong": diem_cong}


def _kenh_hien_thi(tb: dict) -> str:
    k = []
    if tb.get("sms"):
        k.append("SMS")
    if tb.get("zalo"):
        k.append("Zalo")
    if tb.get("email"):
        k.append("Email")
    return ", ".join(k) if k else "(chưa bật)"


def _parse_gia_tri_txt(s: str) -> int:
    s = re.sub(r"[^\d]", "", s.strip())
    return int(s) if s else 0


class ThemSuaVoucherDialog(QDialog):
    """Dialog dùng ui_them_sua_voucher.ui — thêm hoặc sửa voucher."""

    def __init__(self, parent=None, voucher: dict | None = None, ma_da_co: set | None = None):
        super().__init__(parent)
        self._voucher_id = voucher.get("id") if voucher else None
        self._ma_da_co = ma_da_co or set()
        self._result: dict | None = None

        self.ui = Ui_ThemSuaVoucherForm()
        self.ui.setupUi(self)
        self._apply_dark_style()
        self.ui.dat_ngay_bd.setCalendarPopup(True)
        self.ui.dat_ngay_kt.setCalendarPopup(True)

        if voucher:
            self._dien_form(voucher)
        else:
            d = QDate.currentDate()
            self.ui.dat_ngay_bd.setDate(d)
            self.ui.dat_ngay_kt.setDate(d.addMonths(1))

        self.ui.btn_luu_voucher.clicked.connect(self._on_luu)
        self.ui.btn_huy_bo.clicked.connect(self.reject)

    def _dien_form(self, v: dict) -> None:
        self.ui.txt_ma_voucher.setText(v.get("ma", ""))
        self.ui.txt_ten_voucher.setText(v.get("ten_chuong_trinh", ""))
        idx = 0 if v.get("loai") == LOAI_PERCENT else 1
        self.ui.cmb_loai_khuyenmai.setCurrentIndex(idx)
        gt = int(v.get("gia_tri", 0))
        self.ui.txt_gia_tri.setText(str(gt))
        bd = _parse_iso(v.get("ngay_bd"))
        kt = _parse_iso(v.get("ngay_kt"))
        if bd:
            self.ui.dat_ngay_bd.setDate(QDate(bd.year, bd.month, bd.day))
        if kt:
            self.ui.dat_ngay_kt.setDate(QDate(kt.year, kt.month, kt.day))
        self.ui.txt_mota_voucher.setPlainText(v.get("ghi_chu", ""))

    def _on_luu(self) -> None:
        ma = self.ui.txt_ma_voucher.text().strip().upper()
        ten = self.ui.txt_ten_voucher.text().strip()
        if not ma or not ten:
            QMessageBox.warning(self, "Thiếu dữ liệu", "Nhập mã và tên chương trình.")
            return

        mas = set(self._ma_da_co)
        if self._voucher_id:
            for x in get_store().data.get("vouchers", []):
                if x.get("id") == self._voucher_id:
                    mas.discard(str(x.get("ma", "")).upper())
                    break
        if ma in mas:
            QMessageBox.warning(self, "Trùng mã", "Mã voucher này đã tồn tại.")
            return

        loai = LOAI_PERCENT if self.ui.cmb_loai_khuyenmai.currentIndex() == 0 else LOAI_AMOUNT
        gt = _parse_gia_tri_txt(self.ui.txt_gia_tri.text())
        if loai == LOAI_PERCENT and (gt < 1 or gt > 100):
            QMessageBox.warning(self, "Sai giá trị", "Phần trăm giảm phải từ 1 đến 100.")
            return
        if loai == LOAI_AMOUNT and gt < 1:
            QMessageBox.warning(self, "Sai giá trị", "Nhập số tiền giảm (VNĐ) hợp lệ.")
            return

        bd = self.ui.dat_ngay_bd.date().toPyDate()
        kt = self.ui.dat_ngay_kt.date().toPyDate()
        if bd > kt:
            QMessageBox.warning(self, "Ngày không hợp lệ", "Ngày bắt đầu phải trước hoặc bằng ngày kết thúc.")
            return

        self._result = {
            "id": self._voucher_id or str(uuid.uuid4()),
            "ma": ma,
            "ten_chuong_trinh": ten,
            "loai": loai,
            "gia_tri": gt,
            "ngay_bd": bd.isoformat(),
            "ngay_kt": kt.isoformat(),
            "ghi_chu": self.ui.txt_mota_voucher.toPlainText().strip(),
        }
        self.accept()

    def lay_du_lieu(self) -> dict | None:
        return self._result

    def _apply_dark_style(self) -> None:
        self.setStyleSheet("""
            QDialog {
                background-color: #111827;
                color: #dbeafe;
                font-family: "Segoe UI", "Inter";
            }
            QLabel {
                color: #dbeafe;
                font-weight: 600;
            }
            QLineEdit, QTextEdit, QDateEdit, QComboBox {
                background-color: #ffffff;
                color: #111827;
                border: 1px solid #cbd5e1;
                border-radius: 8px;
                padding: 6px 8px;
            }
            QPushButton {
                background-color: #1e293b;
                color: #e2e8f0;
                border: 1px solid #334155;
                border-radius: 10px;
                font-weight: 700;
                font-size: 13px;
                padding: 9px 14px;
            }
            QPushButton:hover {
                background-color: #0ea5e9;
                border: 1px solid #0ea5e9;
                color: #f8fafc;
            }
        """)


class ChamSocKhachHangVaMarketingWindow(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self.ui = Ui_ChamSocKHForm()
        self.ui.setupUi(self)
        self._apply_dark_style()
        # QSpinBox mặc định trong Designer thường max=99 — mở rộng ngưỡng điểm
        for sp in (
            self.ui.spn_diem,
            self.ui.spn_dong,
            self.ui.spn_bac,
            self.ui.spn_vang,
            self.ui.spn_vip,
        ):
            sp.setRange(0, 9_999_999)

        self.store = get_store()

        self.ui.spn_tien.setMinimum(1000)
        self.ui.spn_tien.setMaximum(999_999_999)
        self.ui.spn_tien.setSingleStep(100_000)
        self.ui.spn_tien.setValue(2_000_000)

        self._noi_rules = False
        self._nap_loyalty_rules()
        self._nap_thong_bao()
        self._wire_signals()
        self._refresh_tich_diem()
        self._refresh_vouchers()
        self._refresh_nhac_lich()
        self._refresh_log_thong_bao()
        self._refresh_phan_hoi()
        self._noi_rules = False

    def _apply_dark_style(self) -> None:
        self.setStyleSheet("""
            QWidget {
                background-color: #0b1220;
                color: #dbeafe;
                font-family: "Segoe UI";
            }
            QGroupBox {
                background-color: #111827;
                border: 1px solid #334155;
                border-radius: 10px;
                margin-top: 8px;
            }
            QGroupBox::title {
                color: #93c5fd;
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 4px;
                font-weight: 700;
            }
            QTabWidget::pane {
                border: 1px solid #334155;
                border-radius: 10px;
                background: #111827;
            }
            QTabBar::tab {
                background: #1e293b;
                color: #cbd5e1;
                padding: 8px 14px;
                border-top-left-radius: 8px;
                border-top-right-radius: 8px;
                margin-right: 3px;
            }
            QTabBar::tab:selected {
                background: #0ea5e9;
                color: #f8fafc;
            }
            QLineEdit, QTextEdit, QDateEdit, QComboBox, QSpinBox {
                background-color: #0f172a;
                color: #e2e8f0;
                border: 1px solid #334155;
                border-radius: 8px;
                padding: 6px 8px;
            }
            QLineEdit:focus, QTextEdit:focus, QDateEdit:focus, QComboBox:focus, QSpinBox:focus {
                border: 1px solid #38bdf8;
            }
            QPushButton {
                background-color: #1e293b;
                color: #e2e8f0;
                border: 1px solid #334155;
                border-radius: 10px;
                font-weight: 700;
                font-size: 13px;
                padding: 9px 12px;
            }
            QPushButton:hover {
                background-color: #0ea5e9;
                border: 1px solid #38bdf8;
                color: #f8fafc;
            }
            QCheckBox {
                color: #dbeafe;
            }
            QTableWidget {
                background-color: #0f172a;
                color: #e2e8f0;
                border: 1px solid #334155;
                gridline-color: #1f2937;
                selection-background-color: #0ea5e9;
            }
            QHeaderView::section {
                background-color: #1e293b;
                color: #bae6fd;
                border: 0px;
                padding: 8px;
                font-weight: 700;
            }
        """)

    def _nap_loyalty_rules(self) -> None:
        loy = self.store.data["loyalty"]
        self._noi_rules = True
        self.ui.spn_diem.setValue(int(loy.get("diem_moi_1trieu", 10)))
        self.ui.spn_dong.setValue(int(loy.get("nguong_dong", 0)))
        self.ui.spn_bac.setValue(int(loy.get("nguong_bac", 500)))
        self.ui.spn_vang.setValue(int(loy.get("nguong_vang", 1500)))
        self.ui.spn_vip.setValue(int(loy.get("nguong_vip", 5000)))
        self._noi_rules = False

    def _nap_thong_bao(self) -> None:
        tb = self.store.data["thong_bao"]
        self.ui.chk_kenh_sms.setChecked(bool(tb.get("sms", True)))
        self.ui.chk_kenh_zalo.setChecked(bool(tb.get("zalo")))
        self.ui.chk_kenh_email.setChecked(bool(tb.get("email")))
        self.ui.txt_mau_camon.setPlainText(
            tb.get("mau_cam_on") or "Cảm ơn {ten}! Hóa đơn điện tử: {link_hd} (Mã: {ma_hd})"
        )
        self.ui.txt_mau_sinhnhat.setPlainText(
            tb.get("mau_sinh_nhat") or "Chúc mừng sinh nhật {ten}! Mã: {ma_giam} — hết hạn {ngay_het_han}."
        )

    def _wire_signals(self) -> None:
        self.ui.btn_ghinhan.clicked.connect(self._on_ghi_nhan_tt)
        for sp in (
            self.ui.spn_diem,
            self.ui.spn_dong,
            self.ui.spn_bac,
            self.ui.spn_vang,
            self.ui.spn_vip,
        ):
            sp.valueChanged.connect(self._on_loyalty_rules_changed)

        self.ui.btn_cauhinh_chietkhau.clicked.connect(self._on_tim_thanhvien)
        self.ui.btn_them_voucher.clicked.connect(self._on_them_voucher)
        self.ui.btn_sua_voucher.clicked.connect(self._on_sua_voucher)
        self.ui.btn_xoa_voucher.clicked.connect(self._on_xoa_voucher)
        self.ui.btn_timkiem_voucher.clicked.connect(self._refresh_vouchers)

        self.ui.btn_luu_cauhinh_thongbao.clicked.connect(self._on_luu_thong_bao)
        self.ui.btn_mophong_gui.clicked.connect(self._on_mo_phong_gui)
        self.ui.btn_them_quytac_nhac.clicked.connect(self._on_them_nhac)

        self.ui.btn_xacnhan.clicked.connect(self._on_ghi_phan_hoi)
        self.ui.btn_danhdau.clicked.connect(self._on_danh_dau_goi)

    def _loyalty_dict(self) -> dict:
        return self.store.data["loyalty"]

    def _on_loyalty_rules_changed(self) -> None:
        if self._noi_rules:
            return
        loy = self._loyalty_dict()
        loy["diem_moi_1trieu"] = self.ui.spn_diem.value()
        loy["nguong_dong"] = self.ui.spn_dong.value()
        loy["nguong_bac"] = self.ui.spn_bac.value()
        loy["nguong_vang"] = self.ui.spn_vang.value()
        loy["nguong_vip"] = self.ui.spn_vip.value()
        for kh in loy["khach"]:
            self.store.cap_nhat_khach_sau_diem(kh, loy)
        self.store.save()
        self._refresh_tich_diem()

    def _on_ghi_nhan_tt(self) -> None:
        self._on_loyalty_rules_changed()
        ma = self.ui.txt_nhapmakh.text().strip()
        if not ma:
            QMessageBox.warning(self, "Thiếu dữ liệu", "Nhập mã khách hàng.")
            return
        tien = int(self.ui.spn_tien.value())
        res = ghi_nhan_thanh_toan_tich_hop(ma, tien)
        if res:
            QMessageBox.information(
                self,
                "Đã ghi nhận",
                f"Cộng {res['diem_cong']} điểm. Hạng: {res['khach']['hang']} "
                f"(chiết khấu {res['khach']['chiet_khau']}%).",
            )
        self._refresh_tich_diem()
        self._refresh_log_thong_bao()

    def _on_tim_thanhvien(self) -> None:
        self._refresh_tich_diem()

    def _refresh_tich_diem(self) -> None:
        loy = self._loyalty_dict()
        kw = self.ui.txt_timkiem_thanhvien.text().strip().lower()
        rows = []
        for kh in loy["khach"]:
            blob = f"{kh.get('ten','')} {kh.get('sdt','')} {kh.get('id','')}".lower()
            if kw and kw not in blob:
                continue
            diem = int(kh["diem"])
            need = diem_can_len_hang_tiep(
                diem,
                int(loy["nguong_bac"]),
                int(loy["nguong_vang"]),
                int(loy["nguong_vip"]),
            )
            rows.append(
                [
                    str(kh["id"]),
                    kh.get("ten", ""),
                    kh.get("sdt", ""),
                    str(diem),
                    kh.get("hang", ""),
                    str(kh.get("chiet_khau", 0)),
                    need,
                ]
            )

        t = self.ui.tbl_tichdiem
        t.setRowCount(len(rows))
        for i, row in enumerate(rows):
            for j, val in enumerate(row):
                t.setItem(i, j, QTableWidgetItem(val))
        t.resizeColumnsToContents()

    def _ma_voucher_hien_tai(self) -> set[str]:
        return {str(v.get("ma", "")).upper() for v in self.store.data.get("vouchers", [])}

    def _on_them_voucher(self) -> None:
        dlg = ThemSuaVoucherDialog(self, voucher=None, ma_da_co=self._ma_voucher_hien_tai())
        if dlg.exec_() != QDialog.Accepted:
            return
        data = dlg.lay_du_lieu()
        if not data:
            return
        self.store.data.setdefault("vouchers", []).append(data)
        self.store.save()
        self._refresh_vouchers()

    def _on_sua_voucher(self) -> None:
        r = self.ui.tbl_khuyenmai.currentRow()
        if r < 0:
            QMessageBox.information(self, "Chọn dòng", "Chọn một khuyến mãi trong bảng để sửa.")
            return
        it = self.ui.tbl_khuyenmai.item(r, 0)
        vid = it.data(Qt.UserRole) if it else None
        v = next((x for x in self.store.data.get("vouchers", []) if x.get("id") == vid), None)
        if not v:
            QMessageBox.warning(self, "Lỗi", "Không tìm thấy dữ liệu voucher.")
            return
        dlg = ThemSuaVoucherDialog(self, voucher=v, ma_da_co=self._ma_voucher_hien_tai())
        if dlg.exec_() != QDialog.Accepted:
            return
        data = dlg.lay_du_lieu()
        if not data:
            return
        for i, x in enumerate(self.store.data["vouchers"]):
            if x.get("id") == data["id"]:
                self.store.data["vouchers"][i] = data
                break
        self.store.save()
        self._refresh_vouchers()

    def _on_xoa_voucher(self) -> None:
        r = self.ui.tbl_khuyenmai.currentRow()
        if r < 0:
            QMessageBox.information(self, "Chọn dòng", "Chọn một khuyến mãi để xóa.")
            return
        it = self.ui.tbl_khuyenmai.item(r, 0)
        vid = it.data(Qt.UserRole) if it else None
        if not vid:
            return
        if QMessageBox.question(self, "Xác nhận", "Xóa voucher này?", QMessageBox.Yes | QMessageBox.No) != QMessageBox.Yes:
            return
        self.store.data["vouchers"] = [x for x in self.store.data["vouchers"] if x.get("id") != vid]
        self.store.save()
        self._refresh_vouchers()

    def _voucher_pass_filter(self, v: dict) -> bool:
        kw = self.ui.txt_timkiem_voucher.text().strip().lower()
        if kw:
            hay = f"{v.get('ma','')} {v.get('ten_chuong_trinh','')}".lower()
            if kw not in hay:
                return False
        tt = voucher_trang_thai(v)
        loc = self.ui.cmb_loc_trangthai_voucher.currentIndex()
        if loc == 1:
            return tt == "Đang áp dụng"
        if loc == 2:
            return tt in ("Đã hết hạn", "Chưa bắt đầu") or tt == "Không xác định"
        return True

    def _refresh_vouchers(self) -> None:
        vos = [v for v in self.store.data.get("vouchers", []) if self._voucher_pass_filter(v)]
        t = self.ui.tbl_khuyenmai
        t.setRowCount(len(vos))
        for i, v in enumerate(vos):
            vals = [
                v.get("ma", ""),
                v.get("ten_chuong_trinh", ""),
                voucher_hinh_thuc_text(v),
                voucher_gia_tri_hien_thi(v),
                v.get("ngay_bd", "")[:10],
                v.get("ngay_kt", "")[:10],
                voucher_trang_thai(v),
            ]
            for j, val in enumerate(vals):
                cell = QTableWidgetItem(val)
                if j == 0:
                    cell.setData(Qt.UserRole, v.get("id"))
                t.setItem(i, j, cell)
        t.resizeColumnsToContents()

    def _on_luu_thong_bao(self) -> None:
        self.store.data["thong_bao"] = {
            "sms": self.ui.chk_kenh_sms.isChecked(),
            "zalo": self.ui.chk_kenh_zalo.isChecked(),
            "email": self.ui.chk_kenh_email.isChecked(),
            "mau_cam_on": self.ui.txt_mau_camon.toPlainText().strip(),
            "mau_sinh_nhat": self.ui.txt_mau_sinhnhat.toPlainText().strip(),
        }
        self.store.save()
        QMessageBox.information(self, "Đã lưu", "Đã lưu cấu hình thông báo.")

    def _on_mo_phong_gui(self) -> None:
        self.store.data["thong_bao"].update(
            {
                "sms": self.ui.chk_kenh_sms.isChecked(),
                "zalo": self.ui.chk_kenh_zalo.isChecked(),
                "email": self.ui.chk_kenh_email.isChecked(),
                "mau_cam_on": self.ui.txt_mau_camon.toPlainText().strip(),
                "mau_sinh_nhat": self.ui.txt_mau_sinhnhat.toPlainText().strip(),
            }
        )
        tb = self.store.data["thong_bao"]
        noi = (
            (tb.get("mau_cam_on") or "Cảm ơn {ten}")
            .replace("{ten}", "Khách mẫu")
            .replace("{ma_hd}", "HD-DEMO")
            .replace("{link_hd}", "https://hoadon.example.com/demo")
        )
        self.store.data.setdefault("nhat_ky_gui", []).insert(
            0,
            {
                "thoi_gian": datetime.now().strftime("%Y-%m-%d %H:%M"),
                "kenh": _kenh_hien_thi(tb),
                "tom_tat": noi[:200],
            },
        )
        self.store.save()
        self._refresh_log_thong_bao()

    def _refresh_log_thong_bao(self) -> None:
        rows = self.store.data.get("nhat_ky_gui", [])[:200]
        t = self.ui.tbl_mophong_thongbao
        if t.columnCount() > 3:
            t.setColumnCount(3)
            t.setHorizontalHeaderLabels(["Thời gian", "Kênh", "Tóm tắt nội dung"])
        t.setRowCount(len(rows))
        for i, r in enumerate(rows):
            tom = r.get("tom_tat", "") or ""
            loai = (r.get("loai") or "").strip()
            if loai and loai not in tom:
                tom = f"[{loai}] {tom}".strip()
            t.setItem(i, 0, QTableWidgetItem(r.get("thoi_gian", "")))
            t.setItem(i, 1, QTableWidgetItem(r.get("kenh", "")))
            t.setItem(i, 2, QTableWidgetItem(tom))
        t.resizeColumnsToContents()

    def _on_them_nhac(self) -> None:
        dv = self.ui.txt_tendichvu_nhac.text().strip()
        if not dv:
            QMessageBox.warning(self, "Thiếu dữ liệu", "Nhập tên dịch vụ nhắc lịch.")
            return
        thang = int(self.ui.spn_thang_nhac.value())
        self.store.data.setdefault("nhac_lich", []).append(
            {
                "id": str(uuid.uuid4()),
                "dich_vu": dv,
                "sau_thang": thang,
                "ngay_tao": _today_iso(),
            }
        )
        self.store.save()
        self._refresh_nhac_lich()
        self.ui.txt_tendichvu_nhac.clear()

    def _refresh_nhac_lich(self) -> None:
        rows = self.store.data.get("nhac_lich", [])
        t = self.ui.tbl_quytac_nhaclich
        if t.columnCount() < 3:
            t.setColumnCount(3)
            t.setHorizontalHeaderLabels(["Dịch vụ", "Nhắc sau (tháng)", "Ngày tạo"])
        t.setRowCount(len(rows))
        for i, r in enumerate(rows):
            t.setItem(i, 0, QTableWidgetItem(r.get("dich_vu", "")))
            t.setItem(i, 1, QTableWidgetItem(str(r.get("sau_thang", ""))))
            t.setItem(i, 2, QTableWidgetItem(r.get("ngay_tao", "")))
        t.resizeColumnsToContents()

    def _on_ghi_phan_hoi(self) -> None:
        ten = self.ui.txt_tenkhach.text().strip()
        loai = self.ui.cmb_loai.currentText().strip()
        nd = self.ui.txt_noidung.toPlainText().strip()
        if not ten or not nd:
            QMessageBox.warning(self, "Thiếu dữ liệu", "Nhập tên và nội dung.")
            return
        self.store.data.setdefault("phan_hoi", []).append(
            {
                "id": str(uuid.uuid4()),
                "ten_kh": ten,
                "loai": loai,
                "noi_dung": nd,
                "ngay_ghi": _today_iso(),
                "ngay_dich_vu": _today_iso(),
                "da_goi_tham": False,
            }
        )
        self.store.save()
        self._refresh_phan_hoi()
        self.ui.txt_noidung.clear()

    def _refresh_phan_hoi(self) -> None:
        rows = self.store.data.get("phan_hoi", [])
        t = self.ui.tbl_phanhoi
        if t.columnCount() < 6:
            t.setColumnCount(6)
        t.setRowCount(len(rows))
        for i, r in enumerate(rows):
            ngay_dv = _parse_iso(r.get("ngay_dich_vu"))
            hen = (ngay_dv + timedelta(days=3)).isoformat() if ngay_dv else ""
            trang = "Đã gọi" if r.get("da_goi_tham") else "Chờ gọi"
            vals = [
                r.get("ngay_ghi", ""),
                r.get("ten_kh", ""),
                r.get("loai", ""),
                r.get("noi_dung", ""),
                hen,
                trang,
            ]
            for j, val in enumerate(vals):
                t.setItem(i, j, QTableWidgetItem(val))
        t.resizeColumnsToContents()

    def _on_danh_dau_goi(self) -> None:
        r = self.ui.tbl_phanhoi.currentRow()
        ph = self.store.data.get("phan_hoi", [])
        if r < 0 or r >= len(ph):
            QMessageBox.information(self, "Chọn dòng", "Chọn một phản hồi trong bảng.")
            return
        ph[r]["da_goi_tham"] = True
        self.store.save()
        self._refresh_phan_hoi()


if __name__ == "__main__":
    from PyQt5.QtWidgets import QApplication

    app = QApplication(sys.argv)
    w = ChamSocKhachHangVaMarketingWindow()
    w.setWindowTitle("Chăm sóc khách hàng")
    w.resize(1100, 750)
    w.show()
    sys.exit(app.exec_())
