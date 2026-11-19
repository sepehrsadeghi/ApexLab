import sys
import csv
import random
from pathlib import Path
from datetime import datetime

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QPushButton,
    QMessageBox
)
from PySide6.QtCore import Qt, QProcess, Signal


# =========================================================
# Project paths
# =========================================================

def find_project_root():
    exe = Path(sys.executable).resolve()

    for parent in exe.parents:
        if parent.name.lower() in {".venv", ".venv_psychopy"}:
            return parent.parent

    candidates = [Path.cwd(), *Path(__file__).resolve().parents]

    for candidate in candidates:
        psychopy_exe = (
            candidate / ".venv_psychopy" / "Scripts" / "python.exe"
        )
        if psychopy_exe.exists():
            return candidate

    return Path(__file__).resolve().parent


PROJECT_ROOT = find_project_root()

PSYCHOPY_PYTHON = (
    PROJECT_ROOT
    / ".venv_psychopy"
    / "Scripts"
    / "python.exe"
)


# =========================================================
# SRTT protocol
# =========================================================

SEQUENCE = [1, 3, 2, 4, 1, 4, 2, 3, 4, 1, 3, 2]

BLOCK_COUNT = 6
TRIALS_PER_BLOCK = 120

RANDOM_BLOCK = 5

RSI_SECONDS = 0.300

KEY_TO_POSITION = {
    "s": 1,
    "d": 2,
    "f": 3,
    "j": 4
}

POSITIONS = {
    1: (-6, 0),
    2: (-2, 0),
    3: (2, 0),
    4: (6, 0)
}


# =========================================================
# Generate targets
# =========================================================

def create_block_targets(block_number):

    if block_number == RANDOM_BLOCK:
        return [
            random.randint(1, 4)
            for _ in range(TRIALS_PER_BLOCK)
        ]

    repetitions = TRIALS_PER_BLOCK // len(SEQUENCE)

    return SEQUENCE * repetitions


# =========================================================
# Save CSV
# =========================================================

def save_results(results, output_file):

    if not results:
        return

    fieldnames = [
        "block_number",
        "block_type",
        "trial_in_block",
        "global_trial",
        "sequence_position",
        "target_position",
        "expected_key",
        "first_response_key",
        "first_response_correct",
        "first_response_rt_ms",
        "correct_response_rt_ms",
        "correction_attempts",
        "rsi_ms"
    ]

    with open(
        output_file,
        "w",
        newline="",
        encoding="utf-8-sig"
    ) as file:

        writer = csv.DictWriter(
            file,
            fieldnames=fieldnames
        )

        writer.writeheader()
        writer.writerows(results)


# =========================================================
# PsychoPy task
# =========================================================

def run_srtt_task():

    from psychopy import visual, core, monitors
    from psychopy.hardware import keyboard

    output_dir = Path(__file__).resolve().parent / "results"
    output_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    output_file = output_dir / f"srtt_{timestamp}.csv"

    results = []
    completed = False

    win = None

    try:

        # -------------------------------------------------
        # Monitor and window
        # -------------------------------------------------

        monitor = monitors.Monitor("SRTT_Monitor")
        monitor.setWidth(53)
        monitor.setDistance(60)
        monitor.setSizePix((1920, 1080))

        win = visual.Window(
            fullscr=True,
            screen=0,
            monitor=monitor,
            units="deg",
            color=(-0.65, -0.65, -0.65),
            colorSpace="rgb",
            waitBlanking=True
        )

        kb = keyboard.Keyboard()

        # -------------------------------------------------
        # Stimuli
        # -------------------------------------------------

        boxes = {}

        for position, coordinates in POSITIONS.items():

            boxes[position] = visual.Rect(win,
                width=2.0,
                height=2.0,
                pos=coordinates,
                fillColor=(-0.15, -0.15, -0.15),
                lineColor="white",
                lineWidth=3,
                colorSpace="rgb"
            )

        fixation = visual.TextStim(
            win,
            text="+",
            color="white",
            height=0.7,
            pos=(0, -3)
        )

        instruction = visual.TextStim(
            win,
            text=(
                "SERIAL REACTION TIME TASK\n\n"
                "Four boxes will appear on the screen.\n\n"
                "Press the matching key as quickly as possible:\n\n"
                "S = Position 1       D = Position 2\n"
                "F = Position 3       J = Position 4\n\n"
                "If you press a wrong key, keep responding\n"
                "until you press the correct key.\n\n"
                "The sequence is not shown to you.\n\n"
                "Press SPACE to start."
            ),
            color="white",
            height=0.55,
            wrapWidth=22
        )

        status = visual.TextStim(
            win,
            text="",
            color="white",
            height=0.55,
            pos=(0, 5)
        )

        feedback = visual.TextStim(
            win,
            text="",
            color="red",
            height=0.6,
            pos=(0, -4)
        )

        # -------------------------------------------------
        # Drawing functions
        # -------------------------------------------------

        def draw_boxes(active_position=None, error=False):

            for position, box in boxes.items():

                if position == active_position:

                    box.fillColor = (0.1, 0.75, 0.25)

                    if error:
                        box.lineColor = "red"
                    else:
                        box.lineColor = "white"

                else:

                    box.fillColor = (-0.15, -0.15, -0.15)
                    box.lineColor = "white"

                box.draw()

            fixation.draw()

        def wait_for_space():

            kb.clearEvents()

            while True:

                pressed = kb.getKeys(
                    keyList=["space", "escape"],
                    waitRelease=True,
                    clear=True
                )

                for key in pressed:

                    if key.name == "escape":
                        return False

                    if key.name == "space":
                        return True

                core.wait(0.005)

        # -------------------------------------------------
        # Initial instruction
        # -------------------------------------------------

        instruction.draw()
        win.flip()

        if not wait_for_space():
            raise KeyboardInterrupt

        global_trial = 0

        # -------------------------------------------------
        # Six blocks
        # -------------------------------------------------

        for block_number in range(1, BLOCK_COUNT + 1):

            block_type = (
                "random"
                if block_number == RANDOM_BLOCK
                else "sequence"
            )

            targets = create_block_targets(block_number)

            if block_number == 1:

                message = (
                    "BLOCK 1 OF 6\n\n"
                    "The test is starting.\n\n"
                    "Press SPACE to continue."
                )

            else:

                message = (
                    f"BLOCK {block_number} OF {BLOCK_COUNT}\n\n"
                    "Take a short rest.\n\n"
                    "Press SPACE when you are ready."
                )

            block_instruction = visual.TextStim(
                win,
                text=message,
                color="white",
                height=0.7,
                wrapWidth=20
            )

            block_instruction.draw()
            win.flip()

            if not wait_for_space():
                raise KeyboardInterrupt

            # -------------------------------------------------
            # 120 trials per block
            # -------------------------------------------------

            for trial_in_block, target_position in enumerate(
                targets,
                start=1
            ):

                global_trial += 1

                expected_key = next(
                    key
                    for key, position in KEY_TO_POSITION.items()
                    if position == target_position
                )

                if block_type == "sequence":

                    sequence_position = (
                        (trial_in_block - 1) % len(SEQUENCE)
                    ) + 1

                else:

                    sequence_position = None

                status.text = (
                    f"BLOCK {block_number}/{BLOCK_COUNT}    "
                    f"TRIAL {trial_in_block}/{TRIALS_PER_BLOCK}"
                )

                # Inter-trial preparation

                draw_boxes()
                status.draw()
                win.flip()

                core.wait(0.25)

                # Start reaction-time clock

                kb.clearEvents()

                draw_boxes(active_position=target_position)
                status.draw()

                win.callOnFlip(kb.clock.reset)
                win.flip()

                first_response_key = None
                first_response_rt = None
                correct_response_rt = None

                correction_attempts = 0

                # Wait for the correct response

                while correct_response_rt is None:

                    pressed = kb.getKeys(
                        keyList=[
                            "s", "d", "f", "j", "escape"
                        ],
                        waitRelease=True,
                        clear=True
                    )

                    if not pressed:
                        core.wait(0.001)
                        continue

                    key = pressed[0]

                    if key.name == "escape":
                        raise KeyboardInterrupt

                    response_key = key.name
                    response_time = key.rt * 1000

                    if first_response_key is None:

                        first_response_key = response_key
                        first_response_rt = response_time

                    if KEY_TO_POSITION[response_key] == target_position:

                        correct_response_rt = response_time

                    else:

                        correction_attempts += 1

                        draw_boxes(
                            active_position=target_position,
                            error=True
                        )

                        status.draw()

                        feedback.text = "Incorrect key"
                        feedback.draw()

                        win.flip()

                        core.wait(0.12)

                        feedback.text = ""

                        draw_boxes(
                            active_position=target_position
                        )

                        status.draw()
                        win.flip()

                # First response accuracy

                first_response_correct = (
                    first_response_key == expected_key
                )

                # Save trial

                results.append({

                    "block_number": block_number,

                    "block_type": block_type,

                    "trial_in_block": trial_in_block,

                    "global_trial": global_trial,

                    "sequence_position": sequence_position,

                    "target_position": target_position,

                    "expected_key": expected_key,

                    "first_response_key": first_response_key,

                    "first_response_correct": first_response_correct,

                    "first_response_rt_ms": round(
                        first_response_rt, 2
                    ),

                    "correct_response_rt_ms": round(
                        correct_response_rt, 2
                    ),

                    "correction_attempts": correction_attempts,

                    "rsi_ms": RSI_SECONDS * 1000

                })

                # End of trial

                draw_boxes()
                status.draw()
                win.flip()

                core.wait(RSI_SECONDS)

        completed = (
            global_trial == BLOCK_COUNT * TRIALS_PER_BLOCK
        )

    except KeyboardInterrupt:

        completed = False

    finally:

        # Save data even if the test was interrupted

        save_results(results, output_file)

        if win is not None:

            if results:

                first_correct = [
                    row for row in results
                    if row["first_response_correct"]
                ]

                if first_correct:

                    mean_rt = sum(
                        row["first_response_rt_ms"]
                        for row in first_correct
                    ) / len(first_correct)

                else:

                    mean_rt = None

                total_errors = sum(
                    row["correction_attempts"]
                    for row in results
                )

                lines = [
                    "SRTT FINISHED" if completed else "SRTT STOPPED",
                    "",
                    f"Completed trials: {len(results)}",
                    f"First-response correct: {len(first_correct)}",
                    f"Correction errors: {total_errors}",
                ]

                if mean_rt is not None:

                    lines.append(
                        f"Mean first correct RT: {mean_rt:.1f} ms"
                    )

                lines.extend([
                    "",
                    "Data saved to:",
                    str(output_file),
                    "",
                    "Press ESC to exit."
                ])

                final_text = visual.TextStim(
                    win,
                    text="\n".join(lines),
                    color="white",
                    height=0.55,
                    wrapWidth=22
                )

                final_text.draw()
                win.flip()

                kb.clearEvents()

                while True:

                    pressed = kb.getKeys(
                        keyList=["escape"],
                        waitRelease=True,
                        clear=True
                    )

                    if pressed:
                        break

                    core.wait(0.01)

            win.close()


# =========================================================
# PySide6 screen
# =========================================================

class SRTTScreen(QWidget):

    back_clicked = Signal()

    def __init__(self):
        super().__init__()

        self.process = None

        self.create_ui()

    def create_ui(self):

        self.setLayoutDirection(
            Qt.LayoutDirection.RightToLeft
        )

        self.setStyleSheet("""
            QWidget {
                background-color: #f4f6f9;
                font-family: Tahoma;
                color: #202938;
            }

            QLabel {
                color: #202938;
            }

            QPushButton {
                background-color: #3478f6;
                color: white;
                border: none;
                border-radius: 10px;
                padding: 14px;
                font-size: 15px;
            }

            QPushButton:hover {
                background-color: #2463d8;
            }

            QPushButton:disabled {
                background-color: #aab7cc;
            }
        """)

        layout = QVBoxLayout(self)

        layout.setContentsMargins(50, 40, 50, 40)
        layout.setSpacing(20)

        title = QLabel(
            "آزمون یادگیری توالی واکنش (SRTT)"
        )

        title.setAlignment(Qt.AlignmentFlag.AlignCenter)

        title.setStyleSheet("""
            font-size: 24px;
            font-weight: bold;
        """)

        description = QLabel(
            "در این آزمون، سرعت واکنش و یادگیری توالی حرکتی "
            "با استفاده از چهار محرک دیداری ارزیابی می‌شود."
        )

        description.setAlignment(Qt.AlignmentFlag.AlignCenter)
        description.setWordWrap(True)

        description.setStyleSheet("""
            font-size: 15px;
            color: #667085;
        """)

        protocol = QLabel(
            "تعداد بلوک‌ها: ۶\n"
            "تعداد کوشش در هر بلوک: ۱۲۰\n"
            "بلوک پنجم: تصادفی\n"
            "کلیدهای پاسخ: S ،D ،F ،J"
        )

        protocol.setAlignment(Qt.AlignmentFlag.AlignCenter)

        protocol.setStyleSheet("""
            font-size: 15px;
            background-color: white;
            border: 1px solid #d9dee7;
            border-radius: 12px;
            padding: 20px;
        """)

        self.start_button = QPushButton(
            "شروع آزمون"
        )

        self.start_button.setMinimumHeight(55)
        self.start_button.clicked.connect(self.start_task)

        self.back_button = QPushButton(
            "بازگشت به آزمون‌ها"
        )

        self.back_button.setMinimumHeight(45)

        self.back_button.setStyleSheet("""
            QPushButton {
                background-color: #667085;
            }
            QPushButton:hover {
                background-color: #475467;
            }
        """)

        self.back_button.clicked.connect(
            self.back_clicked.emit
        )

        layout.addStretch()
        layout.addWidget(title)
        layout.addWidget(description)
        layout.addWidget(protocol)
        layout.addSpacing(20)
        layout.addWidget(self.start_button)
        layout.addWidget(self.back_button)
        layout.addStretch()

    def start_task(self):

        if not PSYCHOPY_PYTHON.exists():

            QMessageBox.critical(
                self,
                "خطای اجرا",
                "مفسر پایتون محیط PsychoPy پیدا نشد.\n\n"
                f"مسیر بررسی‌شده:\n{PSYCHOPY_PYTHON}"
            )

            return

        self.start_button.setEnabled(False)
        self.start_button.setText("آزمون در حال اجرا است...")

        self.process = QProcess(self)

        self.process.finished.connect(
            self.task_finished
        )

        self.process.errorOccurred.connect(
            self.task_error
        )

        self.process.start(
            str(PSYCHOPY_PYTHON),
            [
                str(Path(__file__).resolve()),
                "--run-task"
            ]
        )

    def task_finished(self, exit_code, exit_status):

        self.start_button.setEnabled(True)
        self.start_button.setText("شروع آزمون")

        if exit_code == 0:

            QMessageBox.information(
                self,
                "پایان آزمون",
                "فرایند اجرای آزمون پایان یافت.\n"
                "در صورت ثبت پاسخ‌ها، فایل CSV در پوشه results ذخیره شده است."
            )

        else:

            QMessageBox.warning(
                self,
                "خطای اجرای آزمون",
                f"آزمون با کد خروج {exit_code} متوقف شد.\n"
                "برای بررسی جزئیات، خطاهای کنسول را بررسی کن."
            )

        self.process = None

    def task_error(self, error):

        self.start_button.setEnabled(True)
        self.start_button.setText("شروع آزمون")

        QMessageBox.critical(
            self,
            "خطای اجرای PsychoPy",
            "اجرای فرایند آزمون با مشکل مواجه شد.\n"
            f"جزئیات: {error}"
        )

        self.process = None


# =======================================