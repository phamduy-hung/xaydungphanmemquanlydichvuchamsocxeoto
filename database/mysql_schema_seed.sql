-- MySQL 8+ schema for xaydungphanmemquanlydichvuchamsocxeoto
-- Import:
--   mysql -u root -p < database/mysql_schema_seed.sql

CREATE DATABASE IF NOT EXISTS car_care_management
  CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;

USE car_care_management;

SET NAMES utf8mb4;
SET FOREIGN_KEY_CHECKS = 0;

DROP TABLE IF EXISTS customer_care_feedback;
DROP TABLE IF EXISTS customer_care_vouchers;
DROP TABLE IF EXISTS cskh_feedback;
DROP TABLE IF EXISTS cskh_reminders;
DROP TABLE IF EXISTS cskh_message_logs;
DROP TABLE IF EXISTS cskh_settings;
DROP TABLE IF EXISTS integration_events;
DROP TABLE IF EXISTS invoice_items;
DROP TABLE IF EXISTS invoices;
DROP TABLE IF EXISTS crm_service_history;
DROP TABLE IF EXISTS service_order_history;
DROP TABLE IF EXISTS service_order_material_requests;
DROP TABLE IF EXISTS service_order_services;
DROP TABLE IF EXISTS service_orders;
DROP TABLE IF EXISTS service_material_bom;
DROP TABLE IF EXISTS web_bookings;
DROP TABLE IF EXISTS customers;
DROP TABLE IF EXISTS rbac_section_permissions;
DROP TABLE IF EXISTS audit_logs;
DROP TABLE IF EXISTS hr_shift_cells;
DROP TABLE IF EXISTS hr_employees;
DROP TABLE IF EXISTS system_settings;
DROP TABLE IF EXISTS users;

SET FOREIGN_KEY_CHECKS = 1;

CREATE TABLE users (
  id BIGINT AUTO_INCREMENT PRIMARY KEY,
  username VARCHAR(50) NOT NULL UNIQUE,
  password_plain VARCHAR(255) NOT NULL,
  role VARCHAR(30) NOT NULL,
  is_active TINYINT(1) NOT NULL DEFAULT 1,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB;

CREATE TABLE system_settings (
  id BIGINT AUTO_INCREMENT PRIMARY KEY,
  store_name VARCHAR(120) NOT NULL,
  store_address VARCHAR(255) NOT NULL,
  store_hotline VARCHAR(30) NOT NULL,
  api_endpoint VARCHAR(255) NOT NULL,
  api_key VARCHAR(255) NOT NULL,
  sync_enabled TINYINT(1) NOT NULL DEFAULT 1,
  invoice_printer VARCHAR(80) NOT NULL,
  default_vat DECIMAL(5,2) NOT NULL DEFAULT 10.00,
  bank_name VARCHAR(120) NOT NULL,
  bank_account_number VARCHAR(60) NOT NULL,
  bank_account_name VARCHAR(120) NOT NULL,
  bank_transfer_note VARCHAR(255) NOT NULL,
  qr_payload TEXT,
  qr_image_path VARCHAR(255) DEFAULT '',
  updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB;

CREATE TABLE rbac_section_permissions (
  id BIGINT AUTO_INCREMENT PRIMARY KEY,
  role_name VARCHAR(30) NOT NULL,
  section_key VARCHAR(50) NOT NULL,
  can_access TINYINT(1) NOT NULL DEFAULT 0,
  UNIQUE KEY uk_role_section (role_name, section_key)
) ENGINE=InnoDB;

CREATE TABLE audit_logs (
  id BIGINT AUTO_INCREMENT PRIMARY KEY,
  at_time DATETIME NOT NULL,
  actor VARCHAR(80) NOT NULL,
  action_key VARCHAR(120) NOT NULL,
  detail_json JSON NULL,
  INDEX idx_audit_time (at_time),
  INDEX idx_audit_actor (actor),
  INDEX idx_audit_action (action_key)
) ENGINE=InnoDB;

-- Nhân sự / KTV: nguồn duy nhất cho combobox phân công kỹ thuật viên (Tiếp nhận, web, cân bằng tải).
CREATE TABLE hr_employees (
  id BIGINT AUTO_INCREMENT PRIMARY KEY,
  full_name VARCHAR(120) NOT NULL,
  phone VARCHAR(20) NOT NULL,
  role VARCHAR(30) NOT NULL,
  join_date VARCHAR(20) NOT NULL DEFAULT '',
  status VARCHAR(30) NOT NULL DEFAULT 'Đang làm',
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  UNIQUE KEY uk_hr_phone (phone),
  INDEX idx_hr_role_status (role, status)
) ENGINE=InnoDB;

CREATE TABLE hr_shift_cells (
  id BIGINT AUTO_INCREMENT PRIMARY KEY,
  employee_id BIGINT NOT NULL,
  shift_date DATE NOT NULL,
  shift_value VARCHAR(40) NOT NULL DEFAULT '-',
  updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  UNIQUE KEY uk_hr_shift_emp_day (employee_id, shift_date),
  INDEX idx_hr_shift_date (shift_date),
  CONSTRAINT fk_hr_shift_employee FOREIGN KEY (employee_id) REFERENCES hr_employees (id) ON DELETE CASCADE
) ENGINE=InnoDB;

CREATE TABLE customers (
  id BIGINT AUTO_INCREMENT PRIMARY KEY,
  customer_code VARCHAR(20) NOT NULL UNIQUE,
  full_name VARCHAR(120) NOT NULL,
  phone VARCHAR(20) NOT NULL UNIQUE,
  vehicle_plate VARCHAR(20) DEFAULT '',
  points INT NOT NULL DEFAULT 0,
  tier VARCHAR(20) NOT NULL DEFAULT 'Đồng',
  discount_percent DECIMAL(5,2) NOT NULL DEFAULT 0.00,
  total_spent DECIMAL(14,2) NOT NULL DEFAULT 0.00,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB;

CREATE TABLE crm_service_history (
  id BIGINT AUTO_INCREMENT PRIMARY KEY,
  customer_id BIGINT NOT NULL,
  service_date DATE NULL,
  car_model VARCHAR(100) DEFAULT '',
  plate_no VARCHAR(20) DEFAULT '',
  service_name VARCHAR(255) NOT NULL,
  amount DECIMAL(14,2) NOT NULL DEFAULT 0.00,
  technician VARCHAR(80) DEFAULT '',
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (customer_id) REFERENCES customers(id) ON DELETE CASCADE
) ENGINE=InnoDB;

CREATE TABLE integration_events (
  id BIGINT AUTO_INCREMENT PRIMARY KEY,
  event_type VARCHAR(30) NOT NULL,
  payload_json JSON NOT NULL,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  INDEX idx_inte_type_time (event_type, created_at)
) ENGINE=InnoDB;

CREATE TABLE web_bookings (
  id BIGINT AUTO_INCREMENT PRIMARY KEY,
  booking_code VARCHAR(30) NOT NULL UNIQUE,
  customer_name VARCHAR(120) NOT NULL,
  phone VARCHAR(20) NOT NULL,
  plate VARCHAR(20) DEFAULT '',
  service_name VARCHAR(120) NOT NULL,
  appointment_date DATE NULL,
  appointment_time VARCHAR(20) DEFAULT '',
  notes VARCHAR(255) DEFAULT '',
  status VARCHAR(20) NOT NULL DEFAULT 'PENDING',
  source VARCHAR(20) NOT NULL DEFAULT 'web',
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB;

CREATE TABLE service_orders (
  id BIGINT AUTO_INCREMENT PRIMARY KEY,
  order_no VARCHAR(30) NOT NULL UNIQUE,
  created_at DATETIME NOT NULL,
  service_date DATE NULL,
  status VARCHAR(20) NOT NULL,
  customer_name VARCHAR(120) NOT NULL,
  customer_phone VARCHAR(20) NOT NULL,
  plate VARCHAR(20) DEFAULT '',
  source VARCHAR(20) NOT NULL DEFAULT 'desk',
  assigned_to VARCHAR(80) DEFAULT '',
  invoice_no VARCHAR(30) DEFAULT '',
  INDEX idx_so_phone (customer_phone),
  INDEX idx_so_status (status),
  INDEX idx_so_service_day (service_date)
) ENGINE=InnoDB;

CREATE TABLE service_order_services (
  id BIGINT AUTO_INCREMENT PRIMARY KEY,
  order_no VARCHAR(30) NOT NULL,
  service_name VARCHAR(120) NOT NULL,
  qty INT NOT NULL DEFAULT 1,
  unit_price DECIMAL(14,2) NOT NULL DEFAULT 0.00,
  FOREIGN KEY (order_no) REFERENCES service_orders(order_no) ON DELETE CASCADE
) ENGINE=InnoDB;

CREATE TABLE service_order_material_requests (
  id BIGINT AUTO_INCREMENT PRIMARY KEY,
  order_no VARCHAR(30) NOT NULL,
  item_name VARCHAR(120) NOT NULL,
  qty INT NOT NULL DEFAULT 1,
  requested_at DATETIME NOT NULL,
  exported TINYINT(1) NOT NULL DEFAULT 0,
  exported_at DATETIME NULL,
  FOREIGN KEY (order_no) REFERENCES service_orders(order_no) ON DELETE CASCADE
) ENGINE=InnoDB;

CREATE TABLE service_order_history (
  id BIGINT AUTO_INCREMENT PRIMARY KEY,
  order_no VARCHAR(30) NOT NULL,
  at_time DATETIME NOT NULL,
  from_status VARCHAR(20) NOT NULL,
  to_status VARCHAR(20) NOT NULL,
  actor VARCHAR(80) NOT NULL,
  note_text VARCHAR(255) DEFAULT '',
  FOREIGN KEY (order_no) REFERENCES service_orders(order_no) ON DELETE CASCADE,
  INDEX idx_soh_order (order_no, at_time)
) ENGINE=InnoDB;

CREATE TABLE invoices (
  id BIGINT AUTO_INCREMENT PRIMARY KEY,
  invoice_no VARCHAR(30) NOT NULL UNIQUE,
  created_at DATETIME NOT NULL,
  customer_name VARCHAR(120) NOT NULL,
  customer_phone VARCHAR(20) NOT NULL,
  subtotal DECIMAL(14,2) NOT NULL DEFAULT 0.00,
  discount_type VARCHAR(20) DEFAULT 'none',
  discount_value DECIMAL(14,2) NOT NULL DEFAULT 0.00,
  vat_percent DECIMAL(5,2) NOT NULL DEFAULT 10.00,
  vat_amount DECIMAL(14,2) NOT NULL DEFAULT 0.00,
  total_amount DECIMAL(14,2) NOT NULL DEFAULT 0.00,
  payment_method VARCHAR(30) NOT NULL DEFAULT 'bank',
  status VARCHAR(20) NOT NULL DEFAULT 'paid',
  linked_order_no VARCHAR(30) DEFAULT '',
  INDEX idx_invoice_phone (customer_phone),
  INDEX idx_invoice_status (status)
) ENGINE=InnoDB;

CREATE TABLE invoice_items (
  id BIGINT AUTO_INCREMENT PRIMARY KEY,
  invoice_no VARCHAR(30) NOT NULL,
  item_name VARCHAR(120) NOT NULL,
  item_type VARCHAR(20) NOT NULL DEFAULT 'service',
  qty INT NOT NULL DEFAULT 1,
  unit_price DECIMAL(14,2) NOT NULL DEFAULT 0.00,
  line_total DECIMAL(14,2) NOT NULL DEFAULT 0.00,
  FOREIGN KEY (invoice_no) REFERENCES invoices(invoice_no) ON DELETE CASCADE
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS products (
  id BIGINT AUTO_INCREMENT PRIMARY KEY,
  product_code VARCHAR(20) NOT NULL UNIQUE,
  name VARCHAR(120) NOT NULL,
  category VARCHAR(50) NOT NULL,
  unit VARCHAR(20) NOT NULL,
  price DECIMAL(14,2) NOT NULL DEFAULT 0.00,
  min_stock INT NOT NULL DEFAULT 0,
  current_stock INT NOT NULL DEFAULT 0,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS service_catalog (
  id BIGINT AUTO_INCREMENT PRIMARY KEY,
  service_code VARCHAR(30) NOT NULL UNIQUE,
  service_name VARCHAR(120) NOT NULL UNIQUE,
  price DECIMAL(14,2) NOT NULL DEFAULT 0.00,
  is_active TINYINT(1) NOT NULL DEFAULT 1,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB;

-- Định mức vật tư theo dịch vụ (BOM): dịch vụ = tổng hợp các mặt hàng trong kho × số lượng.
CREATE TABLE IF NOT EXISTS service_material_bom (
  id BIGINT AUTO_INCREMENT PRIMARY KEY,
  service_catalog_id BIGINT NOT NULL,
  product_id BIGINT NOT NULL,
  qty INT NOT NULL DEFAULT 1,
  note VARCHAR(160) DEFAULT '',
  UNIQUE KEY uk_svc_product (service_catalog_id, product_id),
  CONSTRAINT fk_bom_catalog FOREIGN KEY (service_catalog_id) REFERENCES service_catalog(id) ON DELETE CASCADE,
  CONSTRAINT fk_bom_product FOREIGN KEY (product_id) REFERENCES products(id) ON DELETE CASCADE,
  INDEX idx_bom_service (service_catalog_id),
  INDEX idx_bom_product (product_id)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS inventory_transactions (
  id BIGINT AUTO_INCREMENT PRIMARY KEY,
  product_id BIGINT NOT NULL,
  transaction_type VARCHAR(20) NOT NULL, -- 'IN' or 'OUT'
  quantity INT NOT NULL,
  reason VARCHAR(100) DEFAULT '',
  reference_no VARCHAR(30) DEFAULT '', -- invoice_no or purchase_order
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (product_id) REFERENCES products(id) ON DELETE CASCADE,
  INDEX idx_trans_product (product_id),
  INDEX idx_trans_type (transaction_type),
  INDEX idx_trans_created (created_at)
) ENGINE=InnoDB;

CREATE TABLE customer_care_vouchers (
  id BIGINT AUTO_INCREMENT PRIMARY KEY,
  voucher_code VARCHAR(40) NOT NULL UNIQUE,
  campaign_name VARCHAR(120) NOT NULL,
  voucher_type VARCHAR(20) NOT NULL,
  voucher_value DECIMAL(10,2) NOT NULL,
  start_date DATE NOT NULL,
  end_date DATE NOT NULL,
  note_text VARCHAR(255) DEFAULT ''
) ENGINE=InnoDB;

CREATE TABLE customer_care_feedback (
  id BIGINT AUTO_INCREMENT PRIMARY KEY,
  customer_phone VARCHAR(20) NOT NULL,
  feedback_text VARCHAR(500) NOT NULL,
  level_text VARCHAR(20) NOT NULL DEFAULT 'normal',
  created_at DATETIME NOT NULL,
  created_by VARCHAR(80) NOT NULL DEFAULT 'system'
) ENGINE=InnoDB;

CREATE TABLE cskh_settings (
  id BIGINT AUTO_INCREMENT PRIMARY KEY,
  diem_moi_1trieu INT NOT NULL DEFAULT 10,
  nguong_dong INT NOT NULL DEFAULT 0,
  nguong_bac INT NOT NULL DEFAULT 500,
  nguong_vang INT NOT NULL DEFAULT 1500,
  nguong_vip INT NOT NULL DEFAULT 5000,
  sms TINYINT(1) NOT NULL DEFAULT 1,
  zalo TINYINT(1) NOT NULL DEFAULT 0,
  email TINYINT(1) NOT NULL DEFAULT 0,
  mau_cam_on TEXT,
  mau_sinh_nhat TEXT,
  updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB;

CREATE TABLE cskh_message_logs (
  id BIGINT AUTO_INCREMENT PRIMARY KEY,
  sent_at DATETIME NOT NULL,
  channel_text VARCHAR(80) NOT NULL,
  summary_text VARCHAR(500) NOT NULL,
  message_type VARCHAR(40) DEFAULT '',
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB;

CREATE TABLE cskh_reminders (
  id BIGINT AUTO_INCREMENT PRIMARY KEY,
  reminder_uid VARCHAR(64) NOT NULL UNIQUE,
  service_name VARCHAR(120) NOT NULL,
  remind_after_months INT NOT NULL DEFAULT 3,
  created_date DATE NOT NULL
) ENGINE=InnoDB;

CREATE TABLE cskh_feedback (
  id BIGINT AUTO_INCREMENT PRIMARY KEY,
  feedback_uid VARCHAR(64) NOT NULL UNIQUE,
  customer_name VARCHAR(120) NOT NULL,
  feedback_type VARCHAR(40) NOT NULL,
  feedback_text VARCHAR(500) NOT NULL,
  created_date DATE NOT NULL,
  service_date DATE NOT NULL,
  called TINYINT(1) NOT NULL DEFAULT 0
) ENGINE=InnoDB;

-- ==========================================================
-- Sample data (>= 10 rows across important modules)
-- ==========================================================

INSERT INTO users (username, password_plain, role) VALUES
('admin', '123456', 'Quản lý'),
('letan', '123456', 'Lễ tân'),
('admin1', '123456', 'Quản lý');

INSERT INTO hr_employees (full_name, phone, role, join_date, status) VALUES
('Nguyen Minh Dat', '0902111222', 'Kỹ thuật', '10/01/2025', 'Đang làm'),
('Tran Bao Ngoc', '0913555444', 'Lễ tân', '18/03/2025', 'Đang làm'),
('Le Quoc Khanh', '0938222111', 'Kỹ thuật', '25/11/2024', 'Đang làm'),
('Pham Anh Thu', '0977666111', 'Quản lý', '15/07/2023', 'Đang làm'),
('Pham Van Phuc', '0966333444', 'Kỹ thuật', '01/02/2025', 'Đang làm');

INSERT INTO system_settings (
  store_name, store_address, store_hotline, api_endpoint, api_key, sync_enabled,
  invoice_printer, default_vat, bank_name, bank_account_number, bank_account_name,
  bank_transfer_note, qr_payload, qr_image_path
) VALUES (
  'ProCare TPHCM',
  'Số 123 Đường Sài Gòn, Quận 1, TPHCM',
  '0999 888 777',
  'http://localhost:8765/api',
  'sk_prod_123456789xxxx',
  1,
  'Khổ giấy 80mm',
  10.00,
  'MB Bank',
  '999999999',
  'CONG TY PROCARE',
  'Thanh toan hoa don',
  'PROCARE_QR',
  ''
);

INSERT INTO rbac_section_permissions (role_name, section_key, can_access) VALUES
('Quản lý', 'dashboard', 1),
('Quản lý', 'web', 1),
('Quản lý', 'crm', 1),
('Quản lý', 'cskh', 1),
('Quản lý', 'pos', 1),
('Quản lý', 'kho', 1),
('Quản lý', 'baocao', 1),
('Quản lý', 'settings', 1),
('Quản lý', 'nhansu', 1),
('Quản lý', 'tiepnhan', 1),
('Quản lý', 'hoadon', 1),
('Quản lý', 'audit', 1),
('Lễ tân', 'dashboard', 1),
('Lễ tân', 'web', 1),
('Lễ tân', 'crm', 1),
('Lễ tân', 'cskh', 1),
('Lễ tân', 'pos', 1),
('Lễ tân', 'kho', 0),
('Lễ tân', 'baocao', 0),
('Lễ tân', 'settings', 0),
('Lễ tân', 'nhansu', 0),
('Lễ tân', 'tiepnhan', 0),
('Lễ tân', 'hoadon', 0),
('Lễ tân', 'audit', 0);

INSERT INTO customers (customer_code, full_name, phone, vehicle_plate, points, tier, discount_percent, total_spent) VALUES
('KH001', 'Nguyễn Văn A', '0901122334', '51A-12345', 120, 'Đồng', 1.00, 2500000.00),
('KH002', 'Trần Thị B', '0988777666', '59K1-45678', 5200, 'VIP', 8.00, 55200000.00),
('KH003', 'Lê Quốc Khánh', '0938222111', '43A-99999', 780, 'Bạc', 3.00, 8600000.00),
('KH004', 'Phạm Anh Thu', '0977666111', '30F-88888', 1650, 'Vàng', 5.00, 19200000.00),
('KH005', 'Hoàng Minh Châu', '0913555444', '29A-123456', 50, 'Đồng', 0.00, 980000.00);

INSERT INTO products (product_code, name, category, unit, price, min_stock, current_stock) VALUES
('VT001', 'Dầu nhớt Castrol GTX 5W-30', 'Dung dịch', 'Lít', 120000.00, 20, 50),
('VT002', 'Nước rửa kính Meguiar', 'Dung dịch', 'Chai', 50000.00, 10, 5),
('VT003', 'Lọc gió Toyota Camry', 'Phụ tùng', 'Cái', 150000.00, 5, 2),
('VT004', 'Dầu phanh DOT 4', 'Dung dịch', 'Lít', 80000.00, 15, 25),
('VT005', 'Bọt rửa xe cao áp', 'Dung dịch', 'Chai', 30000.00, 20, 30),
('VT006', 'Vệ sinh nội thất Meguiar', 'Dung dịch', 'Chai', 250000.00, 5, 8),
('VT007', 'Lốp xe Michelin 205/55R16', 'Phụ tùng', 'Cái', 2500000.00, 2, 4),
('VT008', 'Ắc quy 12V 60Ah', 'Phụ tùng', 'Cái', 800000.00, 3, 6),
('VT009', 'Dung dịch làm mát', 'Dung dịch', 'Lít', 60000.00, 10, 12),
('VT010', 'Chổi lau kính', 'Công cụ', 'Cái', 20000.00, 10, 15),
('VT011', 'Khăn microfiber đa năng ProCare', 'Dụng cụ', 'Cái', 35000.00, 15, 40),
('VT012', 'Dung dịch đánh bóng Sonax Cut', 'Dung dịch', 'Chai', 285000.00, 5, 12),
('VT013', 'Nano ceramic coating Sonax', 'Dung dịch', 'Chai', 920000.00, 3, 8),
('VT014', 'Tẩy gầm & khoang máy ProCare', 'Dung dịch', 'Chai', 195000.00, 5, 14)
ON DUPLICATE KEY UPDATE
  name=VALUES(name),
  category=VALUES(category),
  unit=VALUES(unit),
  price=VALUES(price),
  min_stock=VALUES(min_stock),
  current_stock=VALUES(current_stock);

INSERT INTO service_catalog (service_code, service_name, price, is_active) VALUES
('DV-RUA-THUONG', 'Rửa xe thường', 120000.00, 1),
('DV-RUA-HUT-BUI', 'Rửa xe + hút bụi', 180000.00, 1),
('DV-DANH-BONG', 'Đánh bóng', 450000.00, 1),
('DV-CERAMIC-NHANH', 'Phủ ceramic nhanh', 1200000.00, 1),
('DV-CERAMIC-CAO-CAP', 'Phủ ceramic cao cấp', 2500000.00, 1),
('DV-VE-SINH-NOI-THAT', 'Vệ sinh nội thất', 350000.00, 1),
('DV-VE-SINH-KHOANG-MAY', 'Vệ sinh khoang máy', 300000.00, 1),
('DV-BAO-DUONG-TONG-QUAT', 'Bảo dưỡng tổng quát', 900000.00, 1),
('DV-THAY-DAU-MAY', 'Thay dầu máy', 550000.00, 1),
('DV-SUA-CHUA-DIEN', 'Sửa chữa điện', 700000.00, 1),
('DV-RUA-XE', 'Rửa xe', 120000.00, 1),
('DV-PHU-CERAMIC', 'Phủ ceramic', 1500000.00, 1)
ON DUPLICATE KEY UPDATE
  service_code=VALUES(service_code),
  service_name=VALUES(service_name),
  price=VALUES(price),
  is_active=VALUES(is_active);

-- Định mức vật tư (BOM): bảng service_material_bom — dữ liệu mẫu được nạp khi chạy app
-- (database.models.seed_service_material_bom_defaults) để đồng bộ với mã nguồn.

INSERT INTO web_bookings (booking_code, customer_name, phone, plate, service_name, appointment_date, appointment_time, notes, status, source) VALUES
('WB20260505001', 'Nguyễn Văn A', '0901122334', '51A-12345', 'Rửa xe', '2026-05-05', '09:30', 'Khách đến đúng giờ', 'ACCEPTED', 'web'),
('WB20260505002', 'Trần Thị B', '0988777666', '59K1-45678', 'Đánh bóng', '2026-05-05', '10:00', '', 'PENDING', 'web'),
('WB20260505003', 'Lê Quốc Khánh', '0938222111', '43A-99999', 'Phủ ceramic', '2026-05-06', '14:00', 'Gọi trước 15 phút', 'PENDING', 'web');

INSERT INTO service_orders (order_no, created_at, status, customer_name, customer_phone, plate, source, assigned_to, invoice_no) VALUES
('SO20260505093001', '2026-05-05 09:30:00', 'DONE', 'Nguyễn Văn A', '0901122334', '51A-12345', 'web', 'NV001', 'INV20260505001'),
('SO20260505101502', '2026-05-05 10:15:00', 'IN_SERVICE', 'Trần Thị B', '0988777666', '59K1-45678', 'desk', 'NV003', ''),
('SO20260505113003', '2026-05-05 11:30:00', 'CHECKED_IN', 'Hoàng Minh Châu', '0913555444', '29A-123456', 'desk', '', '');

INSERT INTO service_order_services (order_no, service_name, qty, unit_price) VALUES
('SO20260505093001', 'Rửa xe', 1, 120000.00),
('SO20260505093001', 'Vệ sinh nội thất', 1, 300000.00),
('SO20260505101502', 'Đánh bóng', 1, 850000.00),
('SO20260505113003', 'Rửa xe', 1, 120000.00);

INSERT INTO service_order_material_requests (order_no, item_name, qty, requested_at, exported, exported_at) VALUES
('SO20260505101502', 'Dung dịch đánh bóng', 1, '2026-05-05 10:20:00', 1, '2026-05-05 10:35:00'),
('SO20260505113003', 'Bọt rửa xe', 1, '2026-05-05 11:35:00', 0, NULL);

INSERT INTO service_order_history (order_no, at_time, from_status, to_status, actor, note_text) VALUES
('SO20260505093001', '2026-05-05 09:30:00', '-', 'CHECKED_IN', 'admin', 'Tạo lệnh dịch vụ'),
('SO20260505093001', '2026-05-05 09:35:00', 'CHECKED_IN', 'IN_SERVICE', 'admin', 'Bắt đầu thực hiện'),
('SO20260505093001', '2026-05-05 10:10:00', 'IN_SERVICE', 'DONE', 'admin', 'Hoàn tất dịch vụ'),
('SO20260505101502', '2026-05-05 10:15:00', '-', 'CHECKED_IN', 'admin', 'Tạo lệnh dịch vụ');

INSERT INTO invoices (
  invoice_no, created_at, customer_name, customer_phone, subtotal, discount_type, discount_value,
  vat_percent, vat_amount, total_amount, payment_method, status, linked_order_no
) VALUES
('INV20260505001', '2026-05-05 10:15:00', 'Nguyễn Văn A', '0901122334', 420000.00, 'percent', 5.00, 10.00, 39900.00, 458850.00, 'bank', 'paid', 'SO20260505093001'),
('INV20260504002', '2026-05-04 16:40:00', 'Phạm Anh Thu', '0977666111', 1200000.00, 'none', 0.00, 10.00, 120000.00, 1320000.00, 'cash', 'paid', '');

INSERT INTO invoice_items (invoice_no, item_name, item_type, qty, unit_price, line_total) VALUES
('INV20260505001', 'Rửa xe', 'service', 1, 120000.00, 120000.00),
('INV20260505001', 'Vệ sinh nội thất', 'service', 1, 300000.00, 300000.00),
('INV20260504002', 'Phủ ceramic 5 năm', 'service', 1, 1200000.00, 1200000.00);

INSERT INTO customer_care_vouchers (voucher_code, campaign_name, voucher_type, voucher_value, start_date, end_date, note_text) VALUES
('TET2026', 'Khuyến mãi Tết', 'percent', 10, '2026-04-20', '2026-12-31', 'Áp dụng toàn bộ dịch vụ'),
('VIP50K', 'Ưu đãi khách VIP', 'fixed', 50000, '2026-05-01', '2026-08-31', 'Giảm 50k cho hóa đơn từ 500k');

INSERT INTO customer_care_feedback (customer_phone, feedback_text, level_text, created_at, created_by) VALUES
('0901122334', 'Dịch vụ tốt, nhân viên nhiệt tình', 'good', '2026-05-05 12:00:00', 'letan'),
('0988777666', 'Mong muốn đợi xe nhanh hơn', 'normal', '2026-05-05 12:20:00', 'letan');

INSERT INTO crm_service_history (customer_id, service_date, car_model, plate_no, service_name, amount, technician) VALUES
(1, '2026-04-10', 'Toyota', '51A-12345', 'Rửa xe + hút bụi', 150000, 'Minh'),
(1, '2026-04-15', 'Toyota', '51A-12345', 'Phủ ceramic nhanh', 200000, 'Dat'),
(2, '2026-03-28', 'Mercedes', '59G2-88991', 'Bảo dưỡng tổng quát', 1250000, 'Khanh');

INSERT INTO integration_events (event_type, payload_json, created_at) VALUES
('pos_sale', JSON_OBJECT('invoice_no','INV20260505001','customer_phone','0901122334','total_amount',458850), '2026-05-05 10:16:00'),
('web_accept', JSON_OBJECT('booking_code','WB20260505001','customer_phone','0901122334'), '2026-05-05 09:31:00');

INSERT INTO cskh_settings (
  diem_moi_1trieu, nguong_dong, nguong_bac, nguong_vang, nguong_vip,
  sms, zalo, email, mau_cam_on, mau_sinh_nhat
) VALUES (
  10, 0, 500, 1500, 5000,
  1, 0, 0,
  'Cảm ơn {ten}! Hóa đơn điện tử: {link_hd} (Mã: {ma_hd})',
  'Chúc mừng sinh nhật {ten}! Mã: {ma_giam} — hết hạn {ngay_het_han}.'
);

INSERT INTO cskh_message_logs (sent_at, channel_text, summary_text, message_type) VALUES
('2026-05-05 12:45:00', 'SMS', 'Cảm ơn Nguyễn Văn A đã sử dụng dịch vụ.', 'cam_on'),
('2026-05-05 13:10:00', 'SMS, Zalo', 'Nhắc lịch bảo dưỡng cho khách VIP.', 'nhac_lich');

INSERT INTO cskh_reminders (reminder_uid, service_name, remind_after_months, created_date) VALUES
('RMD-001', 'Thay nhớt', 3, '2026-05-01'),
('RMD-002', 'Vệ sinh nội thất', 2, '2026-05-01');

INSERT INTO cskh_feedback (feedback_uid, customer_name, feedback_type, feedback_text, created_date, service_date, called) VALUES
('FDB-001', 'Nguyễn Văn A', 'Hài lòng', 'Dịch vụ nhanh, nhân viên nhiệt tình', '2026-05-05', '2026-05-04', 0),
('FDB-002', 'Trần Thị B', 'Góp ý', 'Khu chờ nên có thêm nước uống', '2026-05-05', '2026-05-05', 1);

INSERT INTO audit_logs (at_time, actor, action_key, detail_json) VALUES
('2026-05-05 09:00:00', 'admin', 'auth.login_success', JSON_OBJECT('role', 'Quản lý')),
('2026-05-05 09:30:00', 'admin', 'service_order.create', JSON_OBJECT('order_no', 'SO20260505093001')),
('2026-05-05 10:16:00', 'admin', 'pos.checkout', JSON_OBJECT('invoice_no', 'INV20260505001')),
('2026-05-05 10:20:00', 'admin', 'invoice.update_status', JSON_OBJECT('invoice_no', 'INV20260505001', 'to', 'paid')),
('2026-05-05 12:30:00', 'admin', 'auth.logout', JSON_OBJECT('role', 'Quản lý'));

-- Quick verification queries
-- SELECT COUNT(*) AS users_count FROM users;
-- SELECT COUNT(*) AS customers_count FROM customers;
-- SELECT COUNT(*) AS service_orders_count FROM service_orders;
-- SELECT COUNT(*) AS invoices_count FROM invoices;
-- SELECT COUNT(*) AS audit_count FROM audit_logs;
