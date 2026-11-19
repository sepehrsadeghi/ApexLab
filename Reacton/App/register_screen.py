import re
from pathlib import Path

from PySide6.QtWidgets import (
    QWidget, QLabel, QLineEdit, QPushButton, QVBoxLayout,
    QHBoxLayout, QMessageBox, QFrame, QCheckBox, QComboBox
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QPixmap


class RegisterScreen(QWidget):
    back_to_login = Signal()
    registration_submitted = Signal(dict)

    def __init__(self):
        super().__init__()
        self.assets_dir = Path(__file__).resolve().parent / "assets"
        self.create_ui()

    def create_ui(self):
        self.setLayoutDirection(Qt.LayoutDirection.RightToLeft)

        self.background_label = QLabel(self)
        self.background_label.setObjectName("background")
        pixmap = QPixmap(str(self.assets_dir / "auth_background.png"))
        if not pixmap.isNull():
            self.background_label.setPixmap(pixmap)
            self.background_label.setScaledContents(True)
        self.background_label.lower()

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(28, 24, 28, 24)
        main_layout.addStretch()

        card = QFrame()
        card.setObjectName("registerCard")
        card.setMaximumWidth(500)
        card.setMinimumWidth(390)

        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(38, 30, 38, 30)
        card_layout.setSpacing(12)

        title = QLabel("ایجاد حساب کاربری")
        title.setStyleSheet("font-size: 23px; font-weight: bold; color: white;")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)

        subtitle = QLabel("برای استفاده از ApexLab اطلاعات خود را وارد کنید")
        subtitle.setStyleSheet("font-size: 11px; color: #B9DDF8;")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.full_name_input = QLineEdit()
        self.full_name_input.setPlaceholderText("نام و نام خانوادگی")
        self.full_name_input.setMinimumHeight(45)

        self.username_input = QLineEdit()
        self.username_input.setPlaceholderText("نام کاربری انگلیسی (Username)")
        self.username_input.setMinimumHeight(45)
        self.username_input.setMaxLength(20)
        self.username_input.setLayoutDirection(Qt.LayoutDirection.LeftToRight)
        self.username_input.setAlignment(Qt.AlignmentFlag.AlignLeft)

        # انتخاب جنسیت
        self.gender_input = QComboBox()
        self.gender_input.addItem("انتخاب جنسیت", "")
        self.gender_input.addItem("مرد", "male")
        self.gender_input.addItem("زن", "female")
        self.gender_input.setMinimumHeight(45)

        self.password_input = QLineEdit()
        self.password_input.setPlaceholderText("رمز عبور")
        self.password_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.password_input.setMinimumHeight(45)

        self.confirm_password_input = QLineEdit()
        self.confirm_password_input.setPlaceholderText("تکرار رمز عبور")
        self.confirm_password_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.confirm_password_input.setMinimumHeight(45)

        self.show_password = QCheckBox("نمایش رمزهای عبور")
        self.show_password.setCursor(Qt.CursorShape.PointingHandCursor)
        self.show_password.toggled.connect(self.toggle_password_visibility)

        register_button = QPushButton("ایجاد حساب")
        register_button.setObjectName("primaryButton")
        register_button.setMinimumHeight(48)
        register_button.setCursor(Qt.CursorShape.PointingHandCursor)
        register_button.clicked.connect(self.register_user)

        back_row = QHBoxLayout()
        back_text = QLabel("قبلاً حساب کاربری ساخته‌اید؟")
        back_text.setStyleSheet("color: #D7E8F8; font-size: 12px;")

        back_button = QPushButton("ورود به حساب")
        back_button.setObjectName("textButton")
        back_button.setCursor(Qt.CursorShape.PointingHandCursor)
        back_button.clicked.connect(self.back_to_login.emit)

        back_row.addStretch()
        back_row.addWidget(back_text)
        back_row.addWidget(back_button)
        back_row.addStretch()

        for widget in (
            title, subtitle, self.full_name_input,
            self.username_input, self.gender_input,
            self.password_input, self.confirm_password_input,
            self.show_password, register_button
        ):
            card_layout.addWidget(widget)

        card_layout.addLayout(back_row)

        main_layout.addWidget(card, alignment=Qt.AlignmentFlag.AlignHCenter)
        main_layout.addStretch()

        self.setStyleSheet("""
            QWidget { font-family: Tahoma; color: #F4F8FF; }
            QLabel#background { border: none; }
            QFrame#registerCard {
                background-color: rgba(3, 14, 38, 220);
                border: 1px solid rgba(40, 190, 255, 150);
                border-radius: 22px;
            }
            QLineEdit, QComboBox {
                background-color: rgba(11, 34, 68, 225);
                border: 1px solid #276A9E;
                border-radius: 9px;
                padding: 9px 12px;
                color: white;
                font-size: 13px;
            }
            QLineEdit:focus, QComboBox:focus {
                border: 2px solid #12CFF4;
            }
            QComboBox QAbstractItemView {
                background-color: #0B2244;
                color: white;
                selection-background-color: #087FC4;
            }
            QCheckBox { color: #D5EAFE; spacing: 8px; font-size: 12px; }
            QCheckBox::indicator {
                width: 17px; height: 17px;
                border: 1px solid #53BFEA;
                border-radius: 4px;
                background: rgba(5, 28, 58, 230);
            }
            QCheckBox::indicator:checked { background: #06B6D4; }
            QPushButton#primaryButton {
                background-color: #087FC4;
                color: white;
                border: 1px solid #28D8F4;
                border-radius: 10px;
                font-size: 14px;
                font-weight: bold;
            }
            QPushButton#primaryButton:hover { background-color: #06A6D9; }
            QPushButton#textButton {
                background: transparent; color: #32D8F4;
                border: none; font-size: 12px; font-weight: bold;
            }
            QPushButton#textButton:hover { color: white; }
        """)

    def resizeEvent(self, event):
        if hasattr(self, "background_label"):
            self.background_label.setGeometry(self.rect())
        super().resizeEvent(event)

    def toggle_password_visibility(self, visible):
        mode = (
            QLineEdit.EchoMode.Normal if visible
            else QLineEdit.EchoMode.Password
        )
        self.password_input.setEchoMode(mode)
        self.confirm_password_input.setEchoMode(mode)

    def register_user(self):
        full_name = self.full_name_input.text().strip()
        username = self.username_input.text().strip()
        password = self.password_input.text()
        confirm_password = self.confirm_password_input.text()
        gender = self.gender_input.currentData()

        if len(full_name.split()) < 2:
            QMessageBox.warning(
                self, "خطا",
                "لطفاً نام و نام خانوادگی را وارد کنید."
            )
            return

        if not re.fullmatch(r"[A-Za-z][A-Za-z0-9_]{2,19}", username):
            QMessageBox.warning(
                self, "نام کاربری نامعتبر",
                "نام کاربری باید با حروف انگلیسی شروع شود و فقط شامل "
                "حروف انگلیسی، اعداد و زیرخط باشد (۳ تا ۲۰ کاراکتر)."
            )
            return

        if not gender:
            QMessageBox.warning(
                self, "خطا", "لطفاً جنسیت خود را انتخاب کنید."
            )
            return

        if len(password) < 8:
            QMessageBox.warning(
                self, "خطا", "رمز عبور باید حداقل ۸ کاراکتر داشته باشد."
            )
            return

        if password != confirm_password:
            QMessageBox.warning(
                self, "خطا", "رمز عبور و تکرار آن یکسان نیستند."
            )
            return

        name_parts = full_name.split(maxsplit=1)

        user_data = {
            "full_name": full_name,
            "first_name": name_parts[0],
            "last_name": name_parts[1],
            "username": username.lower(),
            "password": password,
            "gender": gender
        }

        self.registration_submitted.emit(user_data)