import re
from pathlib import Path

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QMessageBox, QCheckBox, QFrame
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QPixmap


class LoginScreen(QWidget):
    login_submitted = Signal(str, str)
    register_clicked = Signal()

    def __init__(self):
        super().__init__()
        self.assets_dir = Path(__file__).resolve().parent / "assets"
        self.create_ui()

    def create_ui(self):
        self.setLayoutDirection(Qt.LayoutDirection.RightToLeft)

        background = QLabel(self)
        background.setObjectName("background")
        background.setGeometry(self.rect())
        pixmap = QPixmap(str(self.assets_dir / "auth_background.png"))
        if not pixmap.isNull():
            background.setPixmap(pixmap)
            background.setScaledContents(True)
        background.lower()
        self.background_label = background

        root = QVBoxLayout(self)
        root.setContentsMargins(30, 30, 30, 30)
        root.addStretch()

        card = QFrame()
        card.setObjectName("authCard")
        card.setMaximumWidth(470)
        card.setMinimumWidth(380)
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(38, 34, 38, 34)
        card_layout.setSpacing(15)

        title = QLabel("ApexLab")
        title.setObjectName("brandTitle")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)

        subtitle = QLabel("ورود به حساب کاربری")
        subtitle.setObjectName("subtitle")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.username_input = QLineEdit()
        self.username_input.setPlaceholderText("نام کاربری انگلیسی")
        self.username_input.setMinimumHeight(48)
        self.username_input.setMaxLength(20)
        self.username_input.setLayoutDirection(Qt.LayoutDirection.LeftToRight)
        self.username_input.setAlignment(Qt.AlignmentFlag.AlignLeft)
        self.username_input.setPlaceholderText("Username")

        self.password_input = QLineEdit()
        self.password_input.setPlaceholderText("رمز عبور")
        self.password_input.setMinimumHeight(48)
        self.password_input.setEchoMode(QLineEdit.EchoMode.Password)

        self.show_password = QCheckBox("نمایش رمز عبور")
        self.show_password.setCursor(Qt.CursorShape.PointingHandCursor)
        self.show_password.toggled.connect(self.toggle_password_visibility)

        login_button = QPushButton("ورود")
        login_button.setObjectName("primaryButton")
        login_button.setMinimumHeight(48)
        login_button.setCursor(Qt.CursorShape.PointingHandCursor)
        login_button.clicked.connect(self.submit_login)

        register_row = QHBoxLayout()
        register_text = QLabel("حساب کاربری ندارید؟")
        register_text.setObjectName("helperText")
        register_button = QPushButton("ثبت‌نام")
        register_button.setObjectName("textButton")
        register_button.setCursor(Qt.CursorShape.PointingHandCursor)
        register_button.clicked.connect(self.register_clicked.emit)
        register_row.addStretch()
        register_row.addWidget(register_text)
        register_row.addWidget(register_button)
        register_row.addStretch()

        card_layout.addWidget(title)
        card_layout.addWidget(subtitle)
        card_layout.addSpacing(12)
        card_layout.addWidget(self.username_input)
        card_layout.addWidget(self.password_input)
        card_layout.addWidget(self.show_password)
        card_layout.addSpacing(4)
        card_layout.addWidget(login_button)
        card_layout.addSpacing(5)
        card_layout.addLayout(register_row)

        root.addWidget(card, alignment=Qt.AlignmentFlag.AlignHCenter)
        root.addStretch()

        self.setStyleSheet("""
            QWidget {
                font-family: Tahoma;
                color: #F4F8FF;
            }
            QLabel#background { border: none; }
            QFrame#authCard {
                background-color: rgba(3, 14, 38, 218);
                border: 1px solid rgba(40, 190, 255, 150);
                border-radius: 22px;
            }
            QLabel#brandTitle {
                color: #FFFFFF;
                font-family: Arial;
                font-size: 34px;
                font-weight: 900;
                letter-spacing: 2px;
            }
            QLabel#subtitle {
                color: #B9DDF8;
                font-size: 15px;
            }
            QLabel#helperText { color: #D7E8F8; font-size: 12px; }
            QLineEdit {
                background-color: rgba(11, 34, 68, 225);
                border: 1px solid #276A9E;
                border-radius: 10px;
                padding: 10px 13px;
                color: white;
                font-size: 14px;
                selection-background-color: #06B6D4;
            }
            QLineEdit:focus { border: 2px solid #12CFF4; }
            QCheckBox { color: #D5EAFE; spacing: 8px; font-size: 12px; }
            QCheckBox::indicator {
                width: 17px; height: 17px;
                border: 1px solid #53BFEA;
                border-radius: 4px;
                background: rgba(5, 28, 58, 230);
            }
            QCheckBox::indicator:checked {
                background: #06B6D4;
                border: 1px solid #06B6D4;
            }
            QPushButton#primaryButton {
                background-color: #087FC4;
                color: white;
                border: 1px solid #28D8F4;
                border-radius: 10px;
                font-size: 15px;
                font-weight: bold;
            }
            QPushButton#primaryButton:hover { background-color: #06A6D9; }
            QPushButton#textButton {
                background: transparent;
                color: #32D8F4;
                border: none;
                font-size: 13px;
                font-weight: bold;
                padding: 5px;
            }
            QPushButton#textButton:hover { color: white; }
        """)

    def resizeEvent(self, event):
        if hasattr(self, "background_label"):
            self.background_label.setGeometry(self.rect())
        super().resizeEvent(event)

    def toggle_password_visibility(self, visible):
        self.password_input.setEchoMode(
            QLineEdit.EchoMode.Normal if visible
            else QLineEdit.EchoMode.Password
        )

    def submit_login(self):
        username = self.username_input.text().strip()
        password = self.password_input.text()

        if not username or not password:
            QMessageBox.warning(
                self, "خطا", "نام کاربری و رمز عبور را وارد کنید."
            )
            return

        if not re.fullmatch(r"[A-Za-z][A-Za-z0-9_]{2,19}", username):
            QMessageBox.warning(
                self, "نام کاربری نامعتبر",
                "نام کاربری باید با حروف انگلیسی شروع شود و فقط شامل "
                "حروف انگلیسی، اعداد و زیرخط باشد (۳ تا ۲۰ کاراکتر)."
            )
            return

        self.login_submitted.emit(username, password)
