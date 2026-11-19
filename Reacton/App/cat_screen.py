import sys
import csv
import random
import statistics
from pathlib import Path
from datetime import datetime

from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QPushButton, QMessageBox
from PySide6.QtCore import Qt, QProcess, Signal


def find_project_root():
    app_file = Path(__file__).resolve()
    candidates = [app_file.parents[2], Path.cwd(), *app_file.parents]
    for candidate in candidates:
        if (candidate / ".venv_psychopy" / "Scripts" / "python.exe").exists():
            return candidate
    return app_file.parents[2]


PROJECT_ROOT = find_project_root()
PSYCHOPY_PYTHON = PROJECT_ROOT / ".venv_psychopy" / "Scripts" / "python.exe"

PRACTICE_COUNTS = {"SLOW": 3, "MEDIUM": 3, "FAST": 4}
MAIN_COUNTS = {"SLOW": 10, "MEDIUM": 10, "FAST": 10}
OCCLUSION_FRACTION = 0.70
LATE_RESPONSE_WINDOW_S = 1.50
SPEED_WIDTH_RATES = {"SLOW": 0.35, "MEDIUM": 0.45, "FAST": 0.60}
TARGET_TOLERANCE_MS = 50.0


def make_speed_schedule(counts):
    schedule = [condition for condition, count in counts.items() for _ in range(count)]
    while True:
        random.shuffle(schedule)
        if not any(schedule[i] == schedule[i - 1] == schedule[i - 2]
                   for i in range(2, len(schedule))):
            return schedule


def save_results(rows, output_path):
    if not rows:
        return
    fields = [
        "phase", "trial", "speed_condition", "speed_px_per_s",
        "track_distance_px", "occlusion_fraction", "occlusion_time_ms",
        "actual_target_time_ms", "response_time_ms", "signed_error_ms",
        "absolute_error_ms", "response_class", "valid_timing_response"
    ]
    with open(output_path, "w", newline="", encoding="utf-8-sig") as file:
        writer = csv.DictWriter(file, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def calculate_summary(rows):
    valid = [r for r in rows if r["phase"] == "MAIN" and r["valid_timing_response"]]
    errors = [float(r["signed_error_ms"]) for r in valid]
    absolute = [float(r["absolute_error_ms"]) for r in valid]
    result = {
        "valid_count": len(valid),
        "premature_count": sum(r["phase"] == "MAIN" and r["response_class"] == "PREMATURE_VISIBLE" for r in rows),
        "omission_count": sum(r["phase"] == "MAIN" and r["response_class"] == "NO_RESPONSE" for r in rows),
        "early_count": sum(e < -TARGET_TOLERANCE_MS for e in errors),
        "late_count": sum(e > TARGET_TOLERANCE_MS for e in errors),
        "on_target_count": sum(abs(e) <= TARGET_TOLERANCE_MS for e in errors),
        "mean_signed_error": statistics.mean(errors) if errors else None,
        "mean_absolute_error": statistics.mean(absolute) if absolute else None,
        "variable_error": statistics.pstdev(errors) if len(errors) >= 2 else None,
        "by_speed": {},
    }
    for condition in ("SLOW", "MEDIUM", "FAST"):
        values = [float(r["absolute_error_ms"]) for r in valid if r["speed_condition"] == condition]
        result["by_speed"][condition] = {
            "n": len(values),
            "mean_absolute_error": statistics.mean(values) if values else None,
        }
    return result


def run_cat_task():
    from psychopy import visual, core
    from psychopy.hardware import keyboard

    print("CAT_STARTED", flush=True)
    output_dir = Path(__file__).resolve().parent / "results"
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f"cat_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    rows, completed, win = [], False, None

    try:
        win = visual.Window(fullscr=True, screen=0, units="pix",
                            color=(-0.72, -0.72, -0.72), colorSpace="rgb",
                            waitBlanking=True)
        kb = keyboard.Keyboard()
        width, height = win.size
        x_start, x_target = -0.40 * width, 0.40 * width
        distance = x_target - x_start
        x_occlusion = x_start + OCCLUSION_FRACTION * distance

        ball = visual.Circle(win, radius=max(13, int(width * 0.010)),
                             fillColor=(1, 0.75, -0.1), lineColor=(1, 0.75, -0.1),
                             colorSpace="rgb", pos=(x_start, 0))
        lane = visual.Line(win, start=(x_start, 0), end=(x_target, 0),
                           lineColor="white", lineWidth=3)
        start_marker = visual.Line(win, start=(x_start, -45), end=(x_start, 45),
                                   lineColor="white", lineWidth=4)
        target_line = visual.Line(win, start=(x_target, -85), end=(x_target, 85),
                                  lineColor=(0.1, 1, 0.1), lineWidth=7, colorSpace="rgb")
        occlusion_panel = visual.Rect(
            win, width=0.25 * distance, height=125,
            pos=(x_start + 0.825 * distance, 0),
            fillColor=(-0.45, -0.45, -0.45), lineColor=(-0.45, -0.45, -0.45),
            colorSpace="rgb"
        )
        header = visual.TextStim(win, text="COINCIDENCE-ANTICIPATION TIMING",
                                 color="white", height=max(22, int(height * 0.035)),
                                 pos=(0, 0.34 * height))
        instruction = visual.TextStim(win, text="", color="white",
                                      height=max(20, int(height * 0.027)),
                                      wrapWidth=width * 0.86, pos=(0, -0.30 * height))
        feedback = visual.TextStim(win, text="", color="white",
                                   height=max(24, int(height * 0.035)),
                                   wrapWidth=width * 0.85, pos=(0, -0.22 * height))
        trial_clock = core.Clock()

        def draw_track(show_ball=False, ball_x=None):
            lane.draw()
            start_marker.draw()
            occlusion_panel.draw()
            target_line.draw()
            if show_ball and ball_x is not None:
                ball.pos = (ball_x, 0)
                ball.draw()
            header.draw()

        def show_text(message):
            instruction.text = message
            instruction.draw()
            win.flip()

        def wait_for_space():
            kb.clearEvents()
            while True:
                keys = kb.getKeys(keyList=["space", "escape"], waitRelease=True, clear=True)
                for key in keys:
                    if key.name == "escape":
                        return False
                    if key.name == "space":
                        return True
                core.wait(0.002)

        def run_trial(phase, trial_number, condition):
            speed = width * SPEED_WIDTH_RATES[condition]
            target_time = distance / speed
            occlusion_time = target_time * OCCLUSION_FRACTION
            show_text(
                f"{phase} TRIAL {trial_number}\n\nWatch the moving ball.\n"
                "Press SPACE when you think it reaches the green target line.\n\n"
                "Press SPACE to start the ball."
            )
            if not wait_for_space():
                raise KeyboardInterrupt

            kb.clearEvents()
            draw_track(show_ball=True, ball_x=x_start)
            win.callOnFlip(kb.clock.reset)
            win.callOnFlip(trial_clock.reset)
            win.flip()

            response_time = None
            deadline = target_time + LATE_RESPONSE_WINDOW_S
            while trial_clock.getTime() < deadline:
                elapsed = trial_clock.getTime()
                if elapsed < occlusion_time:
                    draw_track(True, x_start + speed * elapsed)
                else:
                    draw_track(False)
                win.flip()
                keys = kb.getKeys(keyList=["space", "escape"], waitRelease=False, clear=True)
                for key in keys:
                    if key.name == "escape":
                        raise KeyboardInterrupt
                    if key.name == "space" and response_time is None:
                        response_time = float(key.rt) if key.rt is not None else float(trial_clock.getTime())
                core.wait(0.001)

            signed_error = absolute_error = ""
            valid_response = False
            if response_time is None:
                response_class = "NO_RESPONSE"
            elif response_time < occlusion_time:
                response_class = "PREMATURE_VISIBLE"
            else:
                error = (response_time - target_time) * 1000.0
                signed_error, absolute_error = round(error, 2), round(abs(error), 2)
                valid_response = True
                if error < -TARGET_TOLERANCE_MS:
                    response_class = "EARLY"
                elif error > TARGET_TOLERANCE_MS:
                    response_class = "LATE"
                else:
                    response_class = "ON_TARGET"

            rows.append({
                "phase": phase, "trial": trial_number,
                "speed_condition": condition, "speed_px_per_s": round(speed, 2),
                "track_distance_px": round(distance, 2),
                "occlusion_fraction": OCCLUSION_FRACTION,
                "occlusion_time_ms": round(occlusion_time * 1000, 2),
                "actual_target_time_ms": round(target_time * 1000, 2),
                "response_time_ms": round(response_time * 1000, 2) if response_time is not None else "",
                "signed_error_ms": signed_error, "absolute_error_ms": absolute_error,
                "response_class": response_class,
                "valid_timing_response": valid_response,
            })

            if phase == "PRACTICE":
                if response_class == "PREMATURE_VISIBLE":
                    feedback.text = "Too early: the ball was still visible."
                elif response_class == "NO_RESPONSE":
                    feedback.text = "No response recorded."
                elif response_class == "EARLY":
                    feedback.text = f"Early by {abs(float(signed_error)):.0f} ms"
                elif response_class == "LATE":
                    feedback.text = f"Late by {float(signed_error):.0f} ms"
                else:
                    feedback.text = "Very close to the target time!"
                draw_track(False)
                feedback.draw()
                win.flip()
                core.wait(0.65)
            else:
                draw_track(False)
                win.flip()
                core.wait(0.25)

        show_text(
            "COINCIDENCE-ANTICIPATION TIMING TEST\n\n"
            "A ball moves from left to right and disappears before the green target line.\n"
            "Estimate when it would reach the line and press SPACE at that moment.\n\n"
            "Each trial starts with SPACE. Press SPACE again to indicate your estimate.\n"
            "Press ESC at any time to stop.\n\nPress SPACE to continue."
        )
        if not wait_for_space():
            raise KeyboardInterrupt

        show_text("PRACTICE BLOCK\n\n10 practice trials with feedback.\n\nPress SPACE to begin.")
        if not wait_for_space():
            raise KeyboardInterrupt
        for i, condition in enumerate(make_speed_schedule(PRACTICE_COUNTS), 1):
            run_trial("PRACTICE", i, condition)

        show_text("MAIN TEST\n\n30 trials: 10 slow, 10 medium, 10 fast.\n"
                  "No feedback will be provided.\n\nPress SPACE when ready.")
        if not wait_for_space():
            raise KeyboardInterrupt
        for i, condition in enumerate(make_speed_schedule(MAIN_COUNTS), 1):
            run_trial("MAIN", i, condition)
        completed = True

    except KeyboardInterrupt:
        completed = False
    finally:
        save_results(rows, output_path)
        if win is not None:
            try:
                if rows:
                    s = calculate_summary(rows)
                    lines = [
                        "CAT RESULTS", "", f"Status: {'COMPLETED' if completed else 'STOPPED'}",
                        f"Main trials recorded: {sum(r['phase'] == 'MAIN' for r in rows)} / 30",
                        f"Valid timing responses: {s['valid_count']}",
                        f"Premature responses: {s['premature_count']}",
                        f"No responses: {s['omission_count']}",
                        f"Early / late / near-target: {s['early_count']} / {s['late_count']} / {s['on_target_count']}",
                    ]
                    if s["mean_absolute_error"] is not None:
                        lines.append(f"Mean absolute error: {s['mean_absolute_error']:.1f} ms")
                    if s["mean_signed_error"] is not None:
                        lines.append(f"Constant error (signed mean): {s['mean_signed_error']:.1f} ms")
                    if s["variable_error"] is not None:
                        lines.append(f"Variable error (SD): {s['variable_error']:.1f} ms")
                    for condition in ("SLOW", "MEDIUM", "FAST"):
                        item = s["by_speed"][condition]
                        value = f"{item['mean_absolute_error']:.1f} ms" if item["mean_absolute_error"] is not None else "N/A"
                        lines.append(f"{condition}: n={item['n']}, mean absolute error={value}")
                    lines.extend(["", "CSV saved to:", str(output_path), "", "Press ESC to close."])
                    show_text("\n".join(lines))
                    kb.clearEvents()
                    while True:
                        keys = kb.getKeys(keyList=["escape"], waitRelease=True, clear=True)
                        if keys:
                            break
                        core.wait(0.01)
            finally:
                win.close()

    print("CAT_COMPLETED" if completed else "CAT_STOPPED", flush=True)


class CATScreen(QWidget):
    back_clicked = Signal()

    def __init__(self):
        super().__init__()
        self.process = None
        self.process_output = ""
        self.create_ui()

    def create_ui(self):
        self.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        self.setStyleSheet("""
            QWidget { background-color: #f4f6f9; font-family: Tahoma; color: #202938; }
            QLabel { color: #202938; }
            QPushButton { background-color: #3478f6; color: white; border: none;
                border-radius: 10px; padding: 14px; font-size: 15px; }
            QPushButton:hover { background-color: #2463d8; }
            QPushButton:disabled { background-color: #aab7cc; }
        """)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(50, 40, 50, 40)
        layout.setSpacing(20)

        title = QLabel("آزمون پیش‌بینی زمان رسیدن (CAT)")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet("font-size: 24px; font-weight: bold;")
        description = QLabel(
            "این آزمون توانایی پیش‌بینی زمان رسیدن یک شیء متحرک و هماهنگ‌کردن "
            "پاسخ با لحظه برخورد را ارزیابی می‌کند."
        )
        description.setAlignment(Qt.AlignmentFlag.AlignCenter)
        description.setWordWrap(True)
        protocol = QLabel(
            "۱۰ کوشش تمرینی با بازخورد\n۳۰ کوشش اصلی بدون بازخورد\n"
            "سه سطح سرعت: کند، متوسط و سریع\nپنهان‌شدن توپ پس از طی ۷۰٪ مسیر\n"
            "ثبت خطای زمانی و ذخیره نتایج در CSV"
        )
        protocol.setAlignment(Qt.AlignmentFlag.AlignCenter)
        protocol.setStyleSheet("font-size: 16px; background-color: white; border: 1px solid #d9dee7; border-radius: 12px; padding: 22px;")

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
            QMessageBox.critical(self, "خطای اجرا",
                "فایل پایتون محیط PsychoPy پیدا نشد:\n"
                f"{PSYCHOPY_PYTHON}\n\nوجود پوشه .venv_psychopy در ریشه پروژه را بررسی کن.")
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
        self.process.start(str(PSYCHOPY_PYTHON), ["-u", str(Path(__file__).resolve()), "--run-task"])

    def read_output(self):
        if self.process is None:
            return
        stdout = bytes(self.process.readAllStandardOutput()).decode("utf-8", errors="replace")
        stderr = bytes(self.process.readAllStandardError()).decode("utf-8", errors="replace")
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
            QMessageBox.critical(self, "خطای آزمون", f"Exit code: {exit_code}\n\n{output[-4000:]}")
        elif "CAT_COMPLETED" in output:
            QMessageBox.information(self, "پایان آزمون", "آزمون CAT با موفقیت کامل شد.\nفایل نتایج در پوشه results ذخیره شده است.")
        elif "CAT_STARTED" not in output:
            QMessageBox.critical(self, "آزمون اجرا نشد", output[-4000:] or "No output received.")
        else:
            QMessageBox.warning(self, "آزمون کامل نشد", "فرایند اجرا شد اما آزمون کامل نشده است.\n\n" + output[-4000:])

    def task_error(self, error):
        self.read_output()
        output = self.process_output
        self.restore_buttons()
        self.process = None
        QMessageBox.critical(self, "خطای اجرای PsychoPy", f"{error}\n\n{output[-3000:]}")


if __name__ == "__main__" and "--run-task" in sys.argv:
    run_cat_task()
