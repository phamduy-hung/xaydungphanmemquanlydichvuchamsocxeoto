from PyQt5.QtWidgets import QWidget

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

        self._apply_dark_style()

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
        """)
