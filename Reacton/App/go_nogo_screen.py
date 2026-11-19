import sys
import csv
import random
from pathlib import Path
from datetime import datetime

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QPushButton, QMessageBox
)
from PySide6.QtCore import Qt, QProcess, Signal


# =========================================================
# Paths
# =========================================================

# Expected structure:
# PythonProject/
#   .venv_psychopy/
#   Reacton/
#     App/
#       Main.py
#       go_nogo_screen.py

PROJECT_ROOT = Path(__file__).resolve().parents[2]
PSYCHOPY_PYTHON = (
    PROJECT_ROOT / ".venv_psychopy" / "Scripts" / "python.exe"
)


# =========================================================
# Protocol
# =========================================================

PRACTICE_GO = 11
PRACTICE_NOGO = 4

MAIN_GO = 19
MAIN_NOGO = 6

FIXATION_MIN = 0.8
FIXATION_MAX = 1.5

STIMULUS_DURATION = 0.5
RESPONSE_WINDOW = 1.0


# =========================================================
# Trial schedule
# =========================================================

def create_schedule(go_count, nogo_count):
    """Create a randomized schedule with no more than 3 No-Go trials in a row."""
    schedule = ["GO"] * go_count + ["NOGO"] * nogo_count

    while True:
        random.shuffle(schedule)
        consecutive_nogo = 0
        valid = True

        for trial_type in schedule:
            if trial_type == "NOGO":
                consecutive_nogo += 1
            else:
                consecutive_nogo = 0

            if consecutive_nogo > 3:
                valid = False
                break

        if valid:
            return schedule


def save_results(results, output_file):
    if not results:
        return

    fieldnames = [
        "phase",
        "trial",
        "stimulus",
        "fixation_duration_s",
        "response_key",
        "response_rt_ms",
        "anticipatory_response",
        "correct",
        "omission_error",
        "commission_error",
        "correct_rejection",
        "reaction_time_valid",
    ]

    with open(output_file, "w", newline="", encoding="utf-8-sig") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(results)


# =========================================================
# PsychoPy task process
# =========================================================

def run_go_nogo():
    from psychopy import visual, core, monitors
    from psychopy.hardware import keyboard

    print("GO_NOGO_STARTED", flush=True)

    output_dir = Path(__file__).resolve().parent / "results"
    output_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = output_dir / f"go_nogo_{timestamp}.csv"

    results = []
    completed = False
    win = None

    try:
        monitor = monitors.Monitor("GoNoGoMonitor")
        monitor.setWidth(53)
        monitor.setDistance(60)
        monitor.setSizePix((1920, 1080))

        win = visual.Window(
            fullscr=True,
            screen=0,
            monitor=monitor,
            units="pix",
            color=(-0.65, -0.65, -0.65),
            colorSpace="rgb",
            waitBlanking=True,
        )

        kb = keyboard.Keyboard()

        fixation = visual.TextStim(
            win, text="+", color="gray", height=55
        )

        green_circle = visual.Circle(
            win,
            radius=65,
            fillColor="green",
            lineColor="green",
            colorSpace="named",
        )

        red_circle = visual.Circle(
            win,
            radius=65,
            fillColor="red",
            lineColor="red",
            colorSpace="named",
        )

        blank = visual.TextStim(win, text="", color="white")

        message = visual.TextStim(
            win,
            text="",
            color="white",
            height=30,
            wrapWidth=1100,
        )

        feedback = visual.TextStim(
            win,
            text="",
            color="white",
            height=35,
            pos=(0, -180),
        )

        def wait_for_start():
            kb.clearEvents()

            while True:
                keys = kb.getKeys(
                    keyList=["space", "escape"],
                    waitRelease=True,
                    clear=True,
                )

                for key in keys:
                    if key.name == "escape":
                        return False
                    if key.name == "space":
                        return True

                core.wait(0.005)

        def show_message(text):
            message.text = text
            message.draw()
            win.flip()

        def run_trial(phase, trial_number, trial_type):
            fixation_duration = random.uniform(
                FIXATION_MIN, FIXATION_MAX
            )
            anticipatory = False

            # Fixation period. A space press here is recorded as anticipatory.
            kb.clearEvents()
            fixation_clock = core.Clock()
            fixation.draw()
            win.flip()
            fixation_clock.reset()

            while fixation_clock.getTime() < fixation_duration:
                keys = kb.getKeys(
                    keyList=["space", "escape"],
                    waitRelease=True,
                    clear=True,
                )

                for key in keys:
                    if key.name == "escape":
                        raise KeyboardInterrupt
                    if key.name == "space":
                        anticipatory = True

                core.wait(0.002)

            # Discard any residual fixation-period events before stimulus onset.
            kb.clearEvents()

            stimulus = green_circle if trial_type == "GO" else red_circle
            stimulus.draw()
            win.callOnFlip(kb.clock.reset)
            win.flip()

            response_key = None
            response_rt = None
            stimulus_removed = False

            # Stimulus is visible for 500 ms; response collection continues
            # until the 1000-ms response deadline.
            while kb.clock.getTime() < RESPONSE_WINDOW:
                elapsed = kb.clock.getTime()

                if elapsed >= STIMULUS_DURATION and not stimulus_removed:
                    blank.draw()
                    win.flip()
                    stimulus_removed = True

                keys = kb.getKeys(
                    keyList=["space", "escape"],
                    waitRelease=True,
                    clear=True,
                )

                for key in keys:
                    if key.name == "escape":
                        raise KeyboardInterrupt

                    if response_key is None:
                        response_key = key.name
                        response_rt = key.rt * 1000 if key.rt is not None else None

                core.wait(0.001)

            # Score the trial.
            omission = False
            commission = False
            correct_rejection = False
            correct = False

            if trial_type == "GO":
                if response_key is None:
                    omission = True
                else:
                    correct = True
            else:
                if response_key is not None:
                    commission = True
                else:
                    correct_rejection = True
                    correct = True

            results.append({
                "phase": phase,
                "trial": trial_number,
                "stimulus": trial_type,
                "fixation_duration_s": round(fixation_duration, 3),
                "response_key": response_key,
                "response_rt_ms": (
                    round(response_rt, 2)
                    if response_rt is not None else ""
                ),
                "anticipatory_response": anticipatory,
                "correct": correct,
                "omission_error": omission,
                "commission_error": commission,
                "correct_rejection": correct_rejection,
                "reaction_time_valid": (
                    phase == "MAIN"
                    and trial_type == "GO"
                    and response_key is not None
                    and response_rt is not None
                    and not anticipatory
                ),
            })

            # Feedback is provided only during practice.
            if phase == "PRACTICE":
                if anticipatory:
                    feedback.text = "Too early!"
                elif omission:
                    feedback.text = "Too slow!"
                elif commission:
                    feedback.text = "Incorrect response!"
                else:
                    feedback.text = "Correct!"

                blank.draw()
                feedback.draw()
                win.flip()
                core.wait(0.4)
            else:
                blank.draw()
                win.flip()
                core.wait(0.25)

        # Instructions
        show_message(
            "GO / NO-GO TASK\n\n"
            "GREEN CIRCLE = PRESS SPACE\n\n"
            "RED CIRCLE = DO NOT PRESS\n\n"
            "Respond as quickly and accurately as possible.\n\n"
            "Press SPACE to begin."
        )

        if not wait_for_start():
            raise KeyboardInterrupt

        # Practice: 15 trials (11 Go, 4 No-Go).
        show_message(
            "PRACTICE\n\n"
            "15 practice trials\n\n"
            "Press SPACE to begin."
        )

        if not wait_for_start():
            raise KeyboardInterrupt

        practice_schedule = create_schedule(
            PRACTICE_GO, PRACTICE_NOGO
        )

        for index, trial_type in enumerate(practice_schedule, start=1):
            run_trial("PRACTICE", index, trial_type)

        # Main: 25 trials (19 Go, 6 No-Go).
        show_message(
            "MAIN TEST\n\n"
            "The practice is complete.\n\n"
            "The main test contains 25 trials.\n\n"
            "No feedback will be provided.\n\n"
            "Press SPACE when you are ready."
        )

        if not wait_for_start():
            raise KeyboardInterrupt

        main_schedule = create_schedule(MAIN_GO, MAIN_NOGO)

        for index, trial_type in enumerate(main_schedule, start=1):
            run_trial("MAIN", index, trial_type)

        completed = True

    except KeyboardInterrupt:
        completed = False

    finally:
        save_results(results, output_file)

        if win is not None:
            try:
                main_results = [
                    row for row in results if row["phase"] == "MAIN"
                ]

                if main_results:
                    go_trials = [
                        row for row in main_results
                        if row["stimulus"] == "GO"
                    ]
                    nogo_trials = [
                        row for row in main_results
                        if row["stimulus"] == "NOGO"
                    ]

                    go_correct = sum(
                        bool(row["correct"]) for row in go_trials
                    )
                    omission_errors = sum(
                        bool(row["omission_error"]) for row in go_trials
                    )
                    commission_errors = sum(
                        bool(row["commission_error"]) for row in nogo_trials
                    )
                    correct_rejections = sum(
                        bool(row["correct_rejection"]) for row in nogo_trials
                    )
                    anticipatory_count = sum(
                        bool(row["anticipatory_response"])
                        for row in main_results
                    )

                    valid_rt = [
                        row["response_rt_ms"]
                        for row in go_trials
                        if row["reaction_time_valid"]
                        and row["response_rt_ms"] != ""
                    ]
                    mean_rt = (
                        sum(valid_rt) / len(valid_rt)
                        if valid_rt else None
                    )

                    summary_lines = [
                        "GO / NO-GO RESULTS",
                        "",
                        "STATUS: " + (
                            "COMPLETED" if completed else "STOPPED"
                        ),
                        "",
                        f"Completed main trials: {len(main_results)} / 25",
                        f"Correct Go responses: {go_correct}",
                        f"Omission errors: {omission_errors}",
                        f"Commission errors: {commission_errors}",
                        f"Correct rejections: {correct_rejections}",
                        f"Anticipatory trials: {anticipatory_count}",
                    ]

                    if mean_rt is not None:
                        summary_lines.append(
                            f"Mean correct Go RT: {mean_rt:.1f} ms"
                        )

                    summary_lines.extend([
                        "",
                        "CSV results saved to:",
                        str(output_file),
                        "",
                        "Press ESC to close.",
                    ])

                    show_message("\n".join(summary_lines))
                    kb.clearEvents()

                    while True:
                        keys = kb.getKeys(
                            keyList=["escape"],
                            waitRelease=True,
                            clear=True,
                        )
                        if keys:
                            break
                        core.wait(0.01)

            finally:
                win.close()

    if completed:
        print("GO_NOGO_COMPLETED", flush=True)
    else:
        print("GO_NOGO_STOPPED", flush=True)


# =========================================================
# PySide6 screen
# =========================================================

class GoNoGoScreen(QWidget):
    back_clicked = Signal()

    def __init__(self):
        super().__init__()
        self.process = None
        self.process_output = ""
        self.create_ui()

    def create_ui(self):
        self.setLayoutDirection(Qt.LayoutDirection.RightToLeft)

        self.setStyleSheet("""
            QWidget {
                background-color: #f4f6f9;
                font-family: Tahoma;
                color: #202938;
            }
            QLabel { color: #202938; }
            QPushButton {
                background-color: #3478f6;
                color: white;
                border: none;
                border-radius: 10px;
                padding: 14px;
                font-size: 15px;
            }
            QPushButton:hover { background-color: #2463d8; }
            QPushButton:disabled { background-color: #aab7cc; }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(50, 40, 50, 40)
        layout.setSpacing(20)

        title = QLabel("آزمون مهار پاسخ (Go / No-Go)")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet("font-size: 24px; font-weight: bold;")

        description = QLabel(
            "این آزمون توانایی مهار پاسخ‌های حرکتی "
            "و کنترل بازداری شناختی را ارزیابی می‌کند."
        )
        description.setAlignment(Qt.AlignmentFlag.AlignCenter)
        description.setWordWrap(True)

        protocol = QLabel(
            "۱۵ کوشش تمرینی\n"
            "۲۵ کوشش اصلی\n"
            "محرک سبز: فشردن Space\n"
            "محرک قرمز: عدم پاسخ"
        )
        protocol.setAlignment(Qt.AlignmentFlag.AlignCenter)
        protocol.setStyleSheet("""
            font-size: 16px;
            background-color: white;
            border: 1px solid #d9dee7;
            border-radius: 12px;
            padding: 22px;
        """)

        self.start_button = QPushButton("شروع آزمون")
        self.start_button.setMinimumHeight(55)
        self.start_button.clicked.connect(self.start_task)

        self.back_button = QPushButton("بازگشت به فهرست آزمون‌ها")
        self.back_button.setMinimumHeight(45)
        self.back_button.clicked.connect(self.back_clicked.emit)

        layout.addStretch()
        layout.addWidget(title)
        layout.addWidget(description)
        layout.addWidget(protocol)
        layout.addSpacing(20)
        layout.addWidget(self.start_button)
        layout.addWidget(self.back_button)
        layout.addStretch()

    def start_task(self):
        if self.process is not None:
            return

        if not PSYCHOPY_PYTHON.exists():
            QMessageBox.critical(
                self,
                "خطای اجرا",
                "فایل پایتون محیط PsychoPy پیدا نشد:\n"
                f"{PSYCHOPY_PYTHON}\n\n"
                "مسیر محیط .venv_psychopy را بررسی کن."
            )
            return

        self.process_output = ""
        self.start_button.setEnabled(False)
        self.back_button.setEnabled(False)
        self.start_button.setText("آزمون در حال اجرا است...")

        self.process = QProcess(self)
        self.process.readyReadStandardOutput.connect(self.read_output)
        self.process.readyReadStandardError.connect(self.read_output)
        self.process.finished.connect(self.task_finished)
        self.process.errorOccurred.connect(self.task_error)

        self.process.start(
            str(PSYCHOPY_PYTHON),
            ["-u", str(Path(__file__).resolve()), "--run-task"],
        )

    def read_output(self):
        if self.process is None:
            return

        stdout = bytes(
            self.process.readAllStandardOutput()
        ).decode("utf-8", errors="replace")

        stderr = bytes(
            self.process.readAllStandardError()
        ).decode("utf-8", errors="replace")

        self.process_output += stdout + stderr

    def restore_buttons(self):
        self.start_button.setEnabled(True)
        self.back_button.setEnabled(True)
        self.start_button.setText("شروع آزمون")

    def task_finished(self, exit_code, exit_status):
        self.read_output()
        output = self.process_output

        self.restore_buttons()
        self.process = None

        if exit_code != 0:
            QMessageBox.critical(
                self,
                "خطای آزمون",
                f"Exit code: {exit_code}\n\n{output[-4000:]}"
            )
        elif "GO_NOGO_COMPLETED" in output:
            QMessageBox.information(
                self,
                "پایان آزمون",
                "آزمون Go/No-Go با موفقیت کامل شد.\n"
                "فایل نتایج در پوشه results ذخیره شده است."
            )
        elif "GO_NOGO_STARTED" not in output:
            QMessageBox.critical(
                self,
                "آزمون اجرا نشد",
                output[-4000:] or "No output received."
            )
        else:
            QMessageBox.warning(
                self,
                "آزمون کامل نشد",
                "فرایند اجرا شد اما آزمون کامل نشده است.\n\n"
                f"{output[-4000:]}"
            )

    def task_error(self, error):
        self.read_output()
        output = self.process_output

        self.restore_buttons()
        self.process = None

        QMessageBox.critical(
            self,
            "خطای اجرای PsychoPy",
            f"{error}\n\n{output[-3000:]}"
        )


if __name__ == "__main__":
    if "--run-task" in sys.argv:
        run_go_nogo()
