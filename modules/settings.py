import json
from pathlib import Path

from PyQt5.QtWidgets import QWidget, QMessageBox, QFileDialog

from ui.compiled.ui_settings import Ui_Form as Ui_Form_Settings


class SettingsWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.ui = Ui_Form_Settings()
        self.ui.setupUi(self)

        self.setObjectName("settingsRoot")
        self.ui.settingsContainer.setObjectName("settingsContainer")

        # Map object names for section/card styling compatibility.
        self.ui.settingsSection_store.setObjectName("settingsSection")
        self.ui.settingsSection_api.setObjectName("settingsSection")
        self.ui.settingsSection_payment.setObjectName("settingsSection")

        # Map label names for unified typography styling.
        self.ui.settingsSectionTitle_store.setObjectName("settingsSectionTitle")
        self.ui.settingsSectionTitle_api.setObjectName("settingsSectionTitle")
        self.ui.settingsSectionTitle_payment.setObjectName("settingsSectionTitle")

        self.ui.settingsLabel_store_name.setObjectName("settingsLabel")
        self.ui.settingsLabel_store_addr.setObjectName("settingsLabel")
        self.ui.settingsLabel_store_hotline.setObjectName("settingsLabel")
        self.ui.settingsLabel_api_endpoint.setObjectName("settingsLabel")
        self.ui.settingsLabel_api_key.setObjectName("settingsLabel")
        self.ui.settingsLabel_sync.setObjectName("settingsLabel")
        self.ui.settingsLabel_printer.setObjectName("settingsLabel")
        self.ui.settingsLabel_vat.setObjectName("settingsLabel")
        self.ui.settingsLabel_bank_name.setObjectName("settingsLabel")
        self.ui.settingsLabel_bank_account_number.setObjectName("settingsLabel")
        self.ui.settingsLabel_bank_account_name.setObjectName("settingsLabel")
        self.ui.settingsLabel_bank_transfer_note.setObjectName("settingsLabel")
        self.ui.settingsLabel_qr_payload.setObjectName("settingsLabel")
        self.ui.settingsLabel_qr_image.setObjectName("settingsLabel")
        self.ui.btn_browse_qr_image.setObjectName("btnSecondary")

        self.settings_path = Path("data/system_settings.json")
        self.ui.btnSaveSettings.clicked.connect(self._save_settings)
        self.ui.btn_browse_qr_image.clicked.connect(self._browse_qr_image)
        self._load_settings()

        self._apply_dark_style()

    def _load_settings(self):
        if not self.settings_path.exists():
            return
        try:
            payload = json.loads(self.settings_path.read_text(encoding="utf-8"))
        except Exception:
            return
        self.ui.txt_store_name.setText(payload.get("store_name", self.ui.txt_store_name.text()))
        self.ui.txt_store_address.setText(payload.get("store_address", self.ui.txt_store_address.text()))
        self.ui.txt_store_hotline.setText(payload.get("store_hotline", self.ui.txt_store_hotline.text()))
        self.ui.txt_api_endpoint.setText(payload.get("api_endpoint", self.ui.txt_api_endpoint.text()))
        self.ui.txt_api_key.setText(payload.get("api_key", self.ui.txt_api_key.text()))
        self.ui.chk_sync.setChecked(bool(payload.get("sync_enabled", self.ui.chk_sync.isChecked())))
        vat_value = payload.get("default_vat")
        if vat_value is not None:
            self.ui.txt_default_vat.setText(str(vat_value))
        self.ui.txt_bank_name.setText(payload.get("bank_name", self.ui.txt_bank_name.text()))
        self.ui.txt_bank_account_number.setText(
            payload.get("bank_account_number", self.ui.txt_bank_account_number.text())
        )
        self.ui.txt_bank_account_name.setText(
            payload.get("bank_account_name", self.ui.txt_bank_account_name.text())
        )
        self.ui.txt_bank_transfer_note.setText(
            payload.get("bank_transfer_note", self.ui.txt_bank_transfer_note.text())
        )
        self.ui.txt_qr_payload.setText(payload.get("qr_payload", self.ui.txt_qr_payload.text()))
        self.ui.txt_qr_image_path.setText(payload.get("qr_image_path", self.ui.txt_qr_image_path.text()))

    def _browse_qr_image(self):
        selected, _ = QFileDialog.getOpenFileName(
            self,
            "Chọn ảnh QR thanh toán",
            "",
            "Image Files (*.png *.jpg *.jpeg *.webp)",
        )
        if selected:
            self.ui.txt_qr_image_path.setText(selected)

    def _save_settings(self):
        payload = {
            "store_name": self.ui.txt_store_name.text().strip(),
            "store_address": self.ui.txt_store_address.text().strip(),
            "store_hotline": self.ui.txt_store_hotline.text().strip(),
            "api_endpoint": self.ui.txt_api_endpoint.text().strip(),
            "api_key": self.ui.txt_api_key.text().strip(),
            "sync_enabled": self.ui.chk_sync.isChecked(),
            "invoice_printer": self.ui.cmb_invoice_printer.currentText(),
            "default_vat": self.ui.txt_default_vat.text().strip(),
            "bank_name": self.ui.txt_bank_name.text().strip(),
            "bank_account_number": self.ui.txt_bank_account_number.text().strip(),
            "bank_account_name": self.ui.txt_bank_account_name.text().strip(),
            "bank_transfer_note": self.ui.txt_bank_transfer_note.text().strip(),
            "qr_payload": self.ui.txt_qr_payload.text().strip(),
            "qr_image_path": self.ui.txt_qr_image_path.text().strip(),
        }
        self.settings_path.parent.mkdir(parents=True, exist_ok=True)
        self.settings_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        QMessageBox.information(self, "Cài đặt hệ thống", "Đã lưu thông tin thanh toán và cài đặt.")

    def _apply_dark_style(self):
        self.setStyleSheet("""
            QWidget#settingsRoot {
                background: transparent;
                color: #dbeafe;
                font-family: "Segoe UI", "Inter";
            }
            QScrollArea {
                border: none;
                background: transparent;
            }
            QScrollArea QWidget#qt_scrollarea_viewport {
                background-color: #0b1220;
            }
            QWidget#settingsContainer {
                background-color: #0b1220;
            }
            QFrame#settingsSection {
                background-color: #111827;
                border: 1px solid #334155;
                border-radius: 12px;
            }
            QLabel#settingsSectionTitle {
                color: #93c5fd;
                font-size: 14px;
                font-weight: 800;
            }
            QLabel#settingsLabel {
                color: #cbd5e1;
                font-weight: 600;
            }
            QLineEdit, QComboBox {
                background-color: #0f172a;
                color: #e2e8f0;
                border: 1px solid #334155;
                border-radius: 8px;
                padding: 7px 10px;
            }
            QLineEdit:focus, QComboBox:focus {
                border: 1px solid #38bdf8;
            }
            QCheckBox {
                color: #cbd5e1;
            }
            QPushButton#btnSaveSettings {
                background-color: #0ea5e9;
                color: #f8fafc;
                border: 1px solid #38bdf8;
                border-radius: 10px;
                font-weight: 700;
                font-size: 13px;
                padding: 8px 14px;
            }
            QPushButton#btnSaveSettings:hover {
                background-color: #0284c7;
            }
            QPushButton#btnSecondary {
                background-color: #1e293b;
                color: #e2e8f0;
                border: 1px solid #334155;
                border-radius: 8px;
                font-weight: 700;
                padding: 7px 12px;
                min-width: 96px;
            }
            QPushButton#btnSecondary:hover {
                background-color: #0ea5e9;
                border: 1px solid #38bdf8;
                color: #f8fafc;
            }
        """)
