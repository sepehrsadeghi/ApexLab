from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QPushButton
from PySide6.QtCore import Qt, Signal


class TestsScreen(QWidget):
    back_clicked = Signal()
    test_selected = Signal(str)

    def __init__(self):
        super().__init__()
        self.create_ui()

    def create_ui(self):
        self.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        self.setStyleSheet("""
            QWidget { background-color: #f4f6f9; font-family: Tahoma; }
            QLabel { color: #202938; }
            QPushButton { background-color: #ffffff; color: #202938;
                border: 1px solid #d9dee7; border-radius: 12px;
                padding: 16px; font-size: 15px; text-align: right; }
            QPushButton:hover { background-color: #eaf1ff; border: 1px solid #3478f6; }
            QPushButton#backButton { background-color: #3478f6; color: white;
                text-align: center; padding: 12px; }
        """)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(40, 28, 40, 28)
        layout.setSpacing(12)
        title = QLabel("آزمون‌های ارزیابی ورزشکار")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet("font-size: 24px; font-weight: bold;")
        description = QLabel("آزمون موردنظر خود را برای اجرا انتخاب کنید.")
        description.setAlignment(Qt.AlignmentFlag.AlignCenter)
        description.setStyleSheet("font-size: 14px; color: #667085;")
        layout.addWidget(title)
        layout.addWidget(description)

        items = [
            ("آزمون اول: سرعت واکنش ساده (SRT)\nاندازه‌گیری زمان واکنش به یک محرک دیداری", "SRT"),
            ("آزمون دوم: سرعت واکنش دید محیطی\nتشخیص محرک‌های دیداری در چهار جهت اطراف نقطه تثبیت", "PERIPHERAL"),
            ("آزمون سوم: استروپ رنگ ـ واژه (Stroop)\nارزیابی کنترل بازداری و تداخل شناختی", "STROOP"),
            ("آزمون چهارم: مهار پاسخ (Go / No-Go)\nارزیابی کنترل بازداری و توانایی مهار پاسخ حرکتی", "GO_NOGO"),
            ("آزمون پنجم: پیش‌بینی زمان رسیدن (CAT)\nارزیابی پیش‌بینی زمان برخورد و هماهنگی پاسخ با لحظه هدف", "CAT"),
        ]
        for label, code in items:
            button = QPushButton(label)
            button.setMinimumHeight(72)
            button.clicked.connect(lambda checked=False, test_code=code: self.test_selected.emit(test_code))
            layout.addWidget(button)
        layout.addStretch()
        back = QPushButton("بازگشت به داشبورد")
        back.setObjectName("backButton")
        back.clicked.connect(self.back_clicked.emit)
        layout.addWidget(back)
