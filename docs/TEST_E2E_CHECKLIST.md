# CHECKLIST RUNTIME UI MANUAL (PRODUCTION UAT)

Muc tieu: nghiem thu cuoi cung tren giao dien that, xac nhan tung module hoat dong on dinh va lien ket logic.

## Huong dan cham ket qua

- PASS: ket qua thuc te dung 100% voi "Ket qua mong doi".
- FAIL: sai ket qua, loi giao dien, hoac sai luong nghiep vu.
- BLOCKED: khong test duoc do thieu du lieu/moi truong.

## Du lieu test de xai chung

- SDT A: `0901000001`
- SDT B: `0901000002`
- Bien so A: `51A-12345`
- Bien so B: `59G2-88888`
- Ho ten A: `UAT Nguyen Van A`
- Ho ten B: `UAT Tran Thi B`

## Bang checklist (15 case)

| ID | Module | Buoc test UI manual | Ket qua mong doi | Ket qua thuc te | PASS/FAIL | Ghi chu |
|---|---|---|---|---|---|---|
| UAT-01 | Web | Tao 1 booking moi tren web (co ten, sdt, hang xe, dich vu, ngay hen). | Thong bao dat lich thanh cong; booking xuat hien trong danh sach cho xu ly desktop. |  |  |  |
| UAT-02 | Web + Capacity | Thu tao booking thu 11 trong cung 1 ngay hen da full slot. | He thong tu choi va hien thong bao da du cong suat trong ngay. |  |  |  |
| UAT-03 | Dat lich web + Tiep nhan | Trong man hinh Dat lich web, bam "Tiep nhan" 1 booking pending. | Tao service order thanh cong, booking chuyen accepted, CRM nhan du lieu khach. |  |  |  |
| UAT-04 | Tiep nhan xe | Tao 1 lenh truc tiep (desk) moi tu form Tiep nhan xe. | Lenh duoc tao va xuat hien trong bang danh sach lenh. |  |  |  |
| UAT-05 | Tiep nhan + Capacity | Thu tao lenh truc tiep khi da du 10 slot trong ngay. | He thong canh bao "du so xe trong ngay", khong tao lenh moi. |  |  |  |
| UAT-06 | Tiep nhan workflow | Chuyen trang thai lenh: CHECKED_IN -> QUOTED -> APPROVED -> IN_SERVICE -> DONE. | Moi buoc chuyen trang thai hop le, cap nhat bang ngay lap tuc. |  |  |  |
| UAT-07 | Tiep nhan (edit dv) | Bam "Chinh sua dich vu", them/bot dich vu cho lenh dang mo, nhap ly do. | Danh sach dv va tong tien cap nhat dung; co lich su thay doi. |  |  |  |
| UAT-08 | CSKH | Sau khi lenh chuyen DONE, mo CSKH tab nhat ky gui. | Co dong log `service_done` moi trong bang nhat ky thong bao. |  |  |  |
| UAT-09 | POS auto-fill | Sang POS, nhap ten + SDT khach da co lenh chua thanh toan. | Hoa don chi tiet tu dong nap dich vu/san pham lien quan tu Tiep nhan xe. |  |  |  |
| UAT-10 | POS data reset | Trong POS, xoa het ten hoac sdt vua nhap. | Cac dong dich vu tren hoa don chi tiet bien mat (gio hang reset). |  |  |  |
| UAT-11 | POS thanh toan | Thanh toan hoa don (tien mat/chuyen khoan) cho lenh da DONE/INVOICED. | Thanh toan thanh cong; lenh lien quan chuyen PAID; tong tien dung VAT/giam gia. |  |  |  |
| UAT-12 | Hoa don + Bao cao | Mo Quan ly hoa don va Bao cao sau thanh toan POS. | Hoa don moi xuat hien; doanh thu POS xuat hien trong bao cao dung ky loc. |  |  |  |
| UAT-13 | CRM + CSKH lien ket | Sau thanh toan, vao CRM va CSKH kiem tra khach vua giao dich. | Tong chi tieu/diem/hang duoc cap nhat nhat quan giua CRM va CSKH. |  |  |  |
| UAT-14 | Kho vat tu | Test thao tac Kho (xem danh muc vat tu, nhap/xuat co du lieu). | Du lieu kho tai duoc, nghiep vu nhap/xuat khong vo luong chinh. |  |  |  |
| UAT-15 | RBAC + Audit | Dang nhap vai tro Le tan, thu vao Bao cao/Kho/Nhan su/Settings va thu export bao cao. | Quyen bi chan dung theo matrix; thao tac duoc ghi vao Nhat ky he thong. |  |  |  |

## Ket luan nghiem thu

- Tong PASS: `.../15`
- Tong FAIL: `.../15`
- Tong BLOCKED: `.../15`
- Danh gia production-ready:
  - [ ] Dat
  - [ ] Chua dat

## Nguoi xac nhan

- Nguoi test: `........................`
- Ngay test: `.... / .... / ........`
- Chu ky xac nhan: `........................`
