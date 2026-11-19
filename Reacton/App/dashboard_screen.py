from pathlib import Path

from PySide6.QtWidgets import (
    QWidget, QLabel, QPushButton, QVBoxLayout, QHBoxLayout,
    QGridLayout, QFrame, QMenu, QMessageBox, QGraphicsDropShadowEffect
)
from PySide6.QtCore import Qt, Signal, QPropertyAnimation, QEasingCurve
from PySide6.QtGui import QFont, QPixmap, QColor


class HoverCard(QFrame):
    """کارت شیشه‌ای با افکت درخشش و بالا آمدن هنگام قرارگیری موس."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("dashboardCard")
        self.setMouseTracking(True)
        self.shadow = QGraphicsDropShadowEffect(self)
        self.shadow.setBlurRadius(12)
        self.shadow.setOffset(0, 3)
        self.shadow.setColor(QColor(0, 160, 255, 70))
        self.setGraphicsEffect(self.shadow)
        self.shadow_animation = QPropertyAnimation(self.shadow, b"blurRadius", self)
        self.shadow_animation.setDuration(180)
        self.shadow_animation.setEasingCurve(QEasingCurve.Type.OutCubic)

    def enterEvent(self, event):
        self.shadow_animation.stop()
        self.shadow_animation.setStartValue(self.shadow.blurRadius())
        self.shadow_animation.setEndValue(30)
        self.shadow_animation.start()
        self.setStyleSheet("""
            QFrame#dashboardCard {
                background-color: rgba(5, 48, 88, 205);
                border: 1px solid #23D5F5;
                border-radius: 18px;
            }
        """)
        super().enterEvent(event)

    def leaveEvent(self, event):
        self.shadow_animation.stop()
        self.shadow_animation.setStartValue(self.shadow.blurRadius())
        self.shadow_animation.setEndValue(12)
        self.shadow_animation.start()
        self.setStyleSheet("""
            QFrame#dashboardCard {
                background-color: rgba(4, 24, 55, 178);
                border: 1px solid rgba(62, 177, 235, 125);
                border-radius: 18px;
            }
        """)
        super().leaveEvent(event)


class DashboardScreen(QWidget):
    new_test_clicked = Signal()
    continue_test_clicked = Signal()
    logout_clicked = Signal()

    def __init__(self, user_data=None):
        super().__init__()
        self.user_data = user_data or {}
        self.assets_dir = Path(__file__).resolve().parent / "assets"
        self.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        self.create_ui()

    def create_ui(self):
        self.background_label = QLabel(self)
        self.background_label.setObjectName("dashboardBackground")
        pixmap = QPixmap(str(self.assets_dir / "dashboard_background.png"))
        if not pixmap.isNull():
            self.background_label.setPixmap(pixmap)
            self.background_label.setScaledContents(True)
        self.background_label.lower()

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(42, 28, 42, 28)
        main_layout.setSpacing(20)

        header = QHBoxLayout()
        header.setSpacing(12)

        # در چیدمان راست‌به‌چپ، اولین دکمه در سمت راست قرار می‌گیرد.
        home_button = QPushButton("A")
        home_button.setObjectName("homeButton")
        home_button.setToolTip("صفحه اصلی")
        home_button.setCursor(Qt.CursorShape.PointingHandCursor)
        home_button.clicked.connect(lambda: self.show_home_message())

        brand = QLabel("ApexLab")
        brand.setObjectName("dashboardBrand")
        brand.setAlignment(Qt.AlignmentFlag.AlignCenter)

        menu_button = QPushButton("☰")
        menu_button.setObjectName("menuButton")
        menu_button.setToolTip("منو")
        menu_button.setCursor(Qt.CursorShape.PointingHandCursor)
        menu_button.clicked.connect(self.show_menu)

        header.addWidget(home_button)
        header.addStretch()
        header.addWidget(brand)
        header.addStretch()
        header.addWidget(menu_button)
        main_layout.addLayout(header)

        full_name = self.user_data.get("full_name", "ورزشکار")
        welcome = QLabel(f"سلام {full_name}، به ApexLab خوش آمدید")
        welcome.setObjectName("welcomeTitle")
        welcome.setAlignment(Qt.AlignmentFlag.AlignCenter)

        description = QLabel(
            "سامانه ارزیابی عملکرد شناختی و سنجش سرعت واکنش ورزشکاران"
        )
        description.setObjectName("welcomeDescription")
        description.setAlignment(Qt.AlignmentFlag.AlignCenter)
        description.setWordWrap(True)

        main_layout.addSpacing(28)
        main_layout.addWidget(welcome)
        main_layout.addWidget(description)
        main_layout.addSpacing(24)

        cards_layout = QGridLayout()
        cards_layout.setSpacing(22)

        new_card, new_button = self.create_card(
            "آزمون جدید",
            "شروع یک ارزیابی جدید و مشاهده فهرست آزمون‌های قابل اجرا",
            "شروع آزمون"
        )
        new_button.clicked.connect(self.new_test_clicked.emit)

        continue_card, continue_button = self.create_card(
            "ادامه آزمون",
            "ادامه ارزیابی‌هایی که قبلاً آغاز کرده‌اید",
            "ادامه"
        )
        continue_button.setEnabled(False)
        continue_button.setToolTip("قابلیت ادامه آزمون در نسخه فعلی فعال نیست.")

        cards_layout.addWidget(new_card, 0, 0)
        cards_layout.addWidget(continue_card, 0, 1)
        main_layout.addLayout(cards_layout)

        status_card = HoverCard()
        status_layout = QVBoxLayout(status_card)
        status_layout.setContentsMargins(24, 20, 24, 20)
        status_title = QLabel("وضعیت ارزیابی‌ها")
        status_title.setObjectName("cardTitle")
        status_description = QLabel(
            "هنوز ارزیابی‌ای برای این حساب کاربری ثبت نشده است."
        )
        status_description.setObjectName("cardDescription")
        status_description.setWordWrap(True)
        status_layout.addWidget(status_title)
        status_layout.addWidget(status_description)
        main_layout.addWidget(status_card)

        main_layout.addStretch()

        footer = QLabel("APEXLAB  |  Cognitive & Sports Performance Assessment")
        footer.setObjectName("footer")
        footer.setAlignment(Qt.AlignmentFlag.AlignCenter)
        main_layout.addWidget(footer)

        self.setStyleSheet("""
            QWidget { font-family: Tahoma; color: #F4F8FF; }
            QLabel#dashboardBackground { border: none; }
            QLabel#dashboardBrand {
                color: white; font-family: Arial; font-size: 30px;
                font-weight: 900; letter-spacing: 3px;
                background: transparent;
            }
            QLabel#welcomeTitle {
                color: white; font-size: 23px; font-weight: bold;
                background: transparent;
            }
            QLabel#welcomeDescription {
                color: #C5E5FA; font-size: 12px;
                background: transparent;
            }
            QLabel#cardTitle {
                color: #FFFFFF; font-size: 17px; font-weight: bold;
                background: transparent;
            }
            QLabel#cardDescription {
                color: #C7DFF2; font-size: 11px;
                background: transparent;
            }
            QLabel#footer {
                color: rgba(220, 240, 255, 175);
                font-size: 9px; background: transparent;
            }
            QPushButton {
                background-color: #087FC4; color: white;
                border: 1px solid #28CFF0; border-radius: 9px;
                padding: 10px 16px; font-size: 12px; font-weight: bold;
            }
            QPushButton:hover { background-color: #06A6D9; }
            QPushButton:disabled {
                background-color: rgba(65, 92, 120, 190);
                color: #B8C8D8; border-color: rgba(150, 180, 205, 90);
            }
            QPushButton#homeButton {
                min-width: 44px; min-height: 44px;
                font-family: Arial; font-size: 20px; font-weight: 900;
                border-radius: 22px; background-color: rgba(0, 130, 205, 210);
            }
            QPushButton#menuButton {
                min-width: 48px; min-height: 44px;
                font-size: 24px; border-radius: 10px;
                background-color: rgba(4, 30, 68, 190);
            }
            QFrame#dashboardCard {
                background-color: rgba(4, 24, 55, 178);
                border: 1px solid rgba(62, 177, 235, 125);
                border-radius: 18px;
            }
        """)

    def resizeEvent(self, event):
        if hasattr(self, "background_label"):
            self.background_label.setGeometry(self.rect())
        super().resizeEvent(event)

    def create_card(self, title_text, description_text, button_text):
        card = HoverCard()
        card.setMinimumHeight(205)
        layout = QVBoxLayout(card)
        layout.setContentsMargins(23, 22, 23, 22)
        layout.setSpacing(13)

        title = QLabel(title_text)
        title.setObjectName("cardTitle")
        description = QLabel(description_text)
        description.setObjectName("cardDescription")
        description.setWordWrap(True)

        button = QPushButton(button_text)
        button.setMinimumHeight(43)
        button.setCursor(Qt.CursorShape.PointingHandCursor)

        layout.addWidget(title)
        layout.addWidget(description)
        layout.addStretch()
        layout.addWidget(button)
        return card, button

    def show_home_message(self):
        # در حال حاضر داشبورد همان صفحه اصلی پس از ورود است.
        # کلیک روی A کاربر را به بالای صفحه اصلی هدایت می‌کند.
        self.layout().setAlignment(Qt.AlignmentFlag.AlignTop)

    def show_menu(self):
        menu = QMenu(self)
        menu.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        menu.setStyleSheet("""
            QMenu {
                background-color: #071B3A; color: white;
                border: 1px solid #159ACB; padding: 6px;
            }
            QMenu::item { padding: 9px 24px; }
            QMenu::item:selected { background-color: #087FC4; }
        """)
        account_action = menu.addAction("حساب کاربری")
        settings_action = menu.addAction("تنظیمات")
        about_action = menu.addAction("درباره ApexLab")
        menu.addSeparator()
        logout_action = menu.addAction("خروج از حساب")
        selected = menu.exec(self.mapToGlobal(self.rect().topRight()))

        if selected == account_action:
            QMessageBox.information(
                self, "حساب کاربری",
                f"نام: {self.user_data.get('full_name', '-')}\n"
                f"نام کاربری: {self.user_data.get('username', '-')}"
            )
        elif selected == settings_action:
            QMessageBox.information(
                self, "تنظیمات",
                "بخش تنظیمات در نسخه بعدی تکمیل خواهد شد."
            )
        elif selected == about_action:
            QMessageBox.about(
                self, "درباره ApexLab",
                "ApexLab\nسامانه ارزیابی عملکرد شناختی و سنجش واکنش ورزشکاران"
            )
        elif selected == logout_action:
            self.logout_clicked.emit()
