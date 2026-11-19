import random
import time

from PySide6.QtWidgets import (
    QWidget, QLabel, QPushButton,
    QVBoxLayout, QHBoxLayout, QMessageBox
)

from PySide6.QtCore import Qt, QTimer, Signal


class SRTScreen(QWidget):

    back_clicked = Signal()

    def __init__(self):
        super().__init__()

        self.setLayoutDirection(
            Qt.LayoutDirection.RightToLeft
        )

        self.total_trials = 20
        self.current_trial = 0

        self.reaction_times = []
        self.false_starts = []

        self.state = "ready"
        self.stimulus_start_time = None

        self.timer = QTimer(self)
        self.timer.setSingleShot(True)
        self.timer.timeout.connect(
            self.show_stimulus
        )

        self.feedback_timer = QTimer(self)
        self.feedback_timer.setSingleShot(True)
        self.feedback_timer.timeout.connect(
            self.start_next_trial
        )

        self.create_ui()

    def create_ui(self):

        main_layout = QVBoxLayout(self)

        main_layout.setContentsMargins(
            40, 30, 40, 30
        )

        main_layout.setSpacing(20)

        header_layout = QHBoxLayout()

        title = QLabel("آزمون واکنش ساده")

        title.setStyleSheet("""
            font-size: 25px;
            font-weight: bold;
            color: #17365D;
        """)

        back_button = QPushButton("بازگشت")

        back_button.clicked.connect(
            self.go_back
        )

        header_layout.addWidget(title)
        header_layout.addStretch()
        header_layout.addWidget(back_button)

        main_layout.addLayout(header_layout)

        self.instruction_label = QLabel(
            "برای شروع آزمون، دکمه شروع را بزنید.\n"
            "به محض مشاهده محرک سبزرنگ، کلید Space را فشار دهید."
        )

        self.instruction_label.setAlignment(
            Qt.AlignmentFlag.AlignCenter
        )

        self.instruction_label.setWordWrap(True)

        self.instruction_label.setStyleSheet("""
            font-size: 16px;
            color: #444444;
        """)

        main_layout.addWidget(
            self.instruction_label
        )

        self.stimulus_label = QLabel("آماده‌اید؟")

        self.stimulus_label.setAlignment(
            Qt.AlignmentFlag.AlignCenter
        )

        self.stimulus_label.setMinimumHeight(280)

        self.stimulus_label.setStyleSheet("""
            background-color: #E5EAF0;
            color: #17365D;
            font-size: 30px;
            font-weight: bold;
            border-radius: 15px;
        """)

        main_layout.addWidget(
            self.stimulus_label
        )

        self.progress_label = QLabel(
            "نوبت ۰ از ۲۰"
        )

        self.progress_label.setAlignment(
            Qt.AlignmentFlag.AlignCenter
        )

        main_layout.addWidget(
            self.progress_label
        )

        self.start_button = QPushButton(
            "شروع آزمون"
        )

        self.start_button.setMinimumHeight(45)

        self.start_button.clicked.connect(
            self.start_test
        )

        main_layout.addWidget(
            self.start_button
        )

        main_layout.addStretch()

    # START TEST

    def start_test(self):

        self.timer.stop()
        self.feedback_timer.stop()

        self.current_trial = 0

        self.reaction_times = []
        self.false_starts = []

        self.state = "waiting"

        self.start_button.setEnabled(False)

        self.instruction_label.setText(
            "منتظر محرک سبزرنگ باشید."
        )

        self.start_next_trial()

        self.setFocus()

    # NEXT TRIAL

    def start_next_trial(self):

        if self.state == "finished" or self.state == "ready":
            return

        if self.current_trial >= self.total_trials:

            self.finish_test()
            return

        self.current_trial += 1

        self.state = "waiting"

        self.progress_label.setText(
            f"نوبت {self.current_trial} از {self.total_trials}"
        )

        self.stimulus_label.setText(
            "منتظر بمانید...")

        self.stimulus_label.setStyleSheet("""
            background-color: #E5EAF0;
            color: #17365D;
            font-size: 28px;
            font-weight: bold;
            border-radius: 15px;
        """)

        delay = random.randint(1500, 4000)

        self.timer.start(delay)

    # SHOW STIMULUS

    def show_stimulus(self):

        if self.state != "waiting":
            return

        self.state = "stimulus"

        self.stimulus_label.setText("اکنون!")

        self.stimulus_label.setStyleSheet("""
            background-color: #20A464;
            color: white;
            font-size: 42px;
            font-weight: bold;
            border-radius: 15px;
        """)

        self.stimulus_start_time = (
            time.perf_counter_ns()
        )

        self.setFocus()

    # KEYBOARD INPUT

    def keyPressEvent(self, event):

        if event.key() != Qt.Key.Key_Space:
            super().keyPressEvent(event)
            return

        if self.state == "waiting":

            self.timer.stop()

            self.false_starts.append(
                self.current_trial
            )

            self.state = "feedback"

            self.stimulus_label.setText(
                "زودتر از موعد پاسخ دادید!"
            )

            self.stimulus_label.setStyleSheet("""
                background-color: #D9534F;
                color: white;
                font-size: 25px;
                font-weight: bold;
                border-radius: 15px;
            """)

            self.feedback_timer.start(800)

        elif self.state == "stimulus":

            response_time = time.perf_counter_ns()

            reaction_time = (
                response_time - self.stimulus_start_time
            ) / 1_000_000

            self.reaction_times.append(
                reaction_time
            )

            self.state = "feedback"

            self.stimulus_label.setText(
                f"{reaction_time:.1f} میلی‌ثانیه"
            )

            self.stimulus_label.setStyleSheet("""
                background-color: #DCEFE5;
                color: #176B43;
                font-size: 30px;
                font-weight: bold;
                border-radius: 15px;
            """)

            self.feedback_timer.start(800)

    # FINISH TEST

    def finish_test(self):

        self.state = "finished"

        self.stimulus_label.setText(
            "آزمون به پایان رسید"
        )

        self.stimulus_label.setStyleSheet("""
            background-color: #E5EAF0;
            color: #17365D;
            font-size: 30px;
            font-weight: bold;
            border-radius: 15px;
        """)

        self.instruction_label.setText(
            "نتیجه ارزیابی شما آماده است."
        )

        self.start_button.setText(
            "اجرای مجدد آزمون"
        )

        self.start_button.setEnabled(True)

        if self.reaction_times:

            average_time = (
                sum(self.reaction_times)
                / len(self.reaction_times)
            )

            fastest_time = min(
                self.reaction_times
            )

            slowest_time = max(
                self.reaction_times
            )

            result = (
                f"تعداد نوبت‌ها: {self.total_trials}\n"
                f"پاسخ‌های معتبر: {len(self.reaction_times)}\n"
                f"واکنش‌های زودهنگام: {len(self.false_starts)}\n\n"
                f"میانگین زمان واکنش: {average_time:.1f} ms\n"
                f"سریع‌ترین واکنش: {fastest_time:.1f} ms\n"
                f"کندترین واکنش: {slowest_time:.1f} ms"
            )

        else:

            result = (
                "هیچ پاسخ معتبری ثبت نشده است.\n"
                f"واکنش‌های زودهنگام: {len(self.false_starts)}"
            )

        QMessageBox.information(
            self,
            "نتیجه آزمون SRT",
            result
        )

        self.progress_label.setText(
            "آزمون کامل شد."
        )

    # BACK

    def go_back(self):

        self.timer.stop()
        self.feedback_timer.stop()

        self.state = "ready"

        self.back_clicked.emit()