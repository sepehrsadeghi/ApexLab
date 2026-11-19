import sys
import csv
import random
import statistics
import time
import wave
import struct
import re
from pathlib import Path
from datetime import datetime

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QPushButton, QMessageBox,
    QFrame, QComboBox, QHBoxLayout
)
from PySide6.QtCore import Qt, QProcess, Signal


def find_project_root():
    exe = Path(sys.executable).resolve()
    for parent in exe.parents:
        if parent.name.lower() in {".venv", ".venv_psychopy"}:
            return parent.parent
    candidates = [Path.cwd(), *Path(__file__).resolve().parents]
    for candidate in candidates:
        if (candidate / ".venv_psychopy" / "Scripts" / "python.exe").exists():
            return candidate
    return Path.cwd()


PROJECT_ROOT = find_project_root()
PSYCHOPY_PYTHON = PROJECT_ROOT / ".venv_psychopy" / "Scripts" / "python.exe"

COLORS = {
    "قرمز": {"rgb": (1, -1, -1), "key": "d"},
    "سبز": {"rgb": (-1, 1, -1), "key": "f"},
    "آبی": {"rgb": (-1, -1, 1), "key": "j"},
    "زرد": {"rgb": (1, 1, -1), "key": "k"},
}
KEY_TO_COLOR = {v["key"]: k for k, v in COLORS.items()}
PRACTICE_TRIALS = 12
TRIALS_PER_CONDITION = 5
MAX_RESPONSE_SECONDS = 1.5
MIN_ISI_SECONDS = 1.0
MAX_ISI_SECONDS = 2.0
VOICE_SAMPLE_RATE = 16000


def shape_persian(text):
    import arabic_reshaper
    from bidi.algorithm import get_display
    return get_display(arabic_reshaper.reshape(str(text)))


def build_trials():
    """۱۵ نوبت اصلی: ۵ نوبت در هر یک از سه وضعیت استروپ."""
    names = list(COLORS)
    trials = []

    # هم‌راستا: پنج نمونه با توزیع رنگی تا حد ممکن متوازن
    congruent_colors = names * ((TRIALS_PER_CONDITION + len(names) - 1) // len(names))
    random.shuffle(congruent_colors)
    for color in congruent_colors[:TRIALS_PER_CONDITION]:
        trials.append({"condition": "congruent", "word": color, "ink_color": color})

    # ناهم‌راستا: انتخاب پنج زوج متفاوت؛ رنگ واژه و جوهر هرگز یکسان نیستند
    incongruent_pairs = [
        (word, ink) for word in names for ink in names if word != ink
    ]
    for word, ink in random.sample(incongruent_pairs, TRIALS_PER_CONDITION):
        trials.append({"condition": "incongruent", "word": word, "ink_color": ink})

    # خنثی: پنج محرک با رنگ جوهر متوازن تا حد ممکن
    neutral_colors = names * ((TRIALS_PER_CONDITION + len(names) - 1) // len(names))
    random.shuffle(neutral_colors)
    for color in neutral_colors[:TRIALS_PER_CONDITION]:
        trials.append({"condition": "neutral", "word": "XXXX", "ink_color": color})

    random.shuffle(trials)
    return trials


def build_practice_trials():
    names = list(COLORS)
    trials = []
    for condition in ("congruent", "incongruent", "neutral"):
        for i in range(4):
            ink = names[i]
            if condition == "congruent":
                word = ink
            elif condition == "neutral":
                word = "XXXX"
            else:
                word = names[(i + 1) % len(names)]
            trials.append({"condition": condition, "word": word, "ink_color": ink})
    random.shuffle(trials)
    return trials


def normalize_color_text(text):
    text = str(text).strip().replace("‌", "").replace(" ", "")
    text = re.sub(r"[^\wآ-ی]", "", text)
    aliases = {
        "قرمز": "قرمز", "سرخ": "قرمز",
        "سبز": "سبز",
        "آبی": "آبی", "ابی": "آبی",
        "زرد": "زرد",
    }
    for token, color in aliases.items():
        if token in text:
            return color
    return None


def save_wav(path, audio, sample_rate):
    import numpy as np
    audio = np.asarray(audio, dtype=np.float32).reshape(-1)
    audio = np.clip(audio, -1.0, 1.0)
    pcm = (audio * 32767).astype("<i2")
    with wave.open(str(path), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(pcm.tobytes())


def detect_voice_onset(audio, sample_rate, noise_rms):
    import numpy as np
    x = np.asarray(audio, dtype=np.float32).reshape(-1)
    frame = max(1, int(sample_rate * 0.01))  # پنجره‌های ۱۰ میلی‌ثانیه‌ای
    threshold = max(0.012, noise_rms * 3.0)
    consecutive_needed = 2
    consecutive = 0
    for start in range(0, len(x) - frame + 1, frame):
        chunk = x[start:start + frame]
        rms = float(np.sqrt(np.mean(chunk * chunk)))
        if rms >= threshold:
            consecutive += 1
            if consecutive >= consecutive_needed:
                onset_sample = start - (consecutive_needed - 1) * frame
                return max(0, onset_sample) / sample_rate * 1000.0
        else:
            consecutive = 0
    return None


def transcribe_audio_files(audio_paths):
    """تشخیص واژه‌های فارسی پس از پایان تکلیف؛ به اینترنت نیاز دارد."""
    import speech_recognition as sr
    recognizer = sr.Recognizer()
    recognized = []
    for audio_path in audio_paths:
        try:
            with sr.AudioFile(str(audio_path)) as source:
                audio = recognizer.record(source)
            text = recognizer.recognize_google(audio, language="fa-IR")
            recognized.append(normalize_color_text(text))
        except Exception:
            recognized.append(None)
    return recognized


def run_stroop_task(mode):
    from psychopy import visual, core, monitors
    from psychopy.hardware import keyboard
    import numpy as np

    if mode == "voice":
        try:
            import sounddevice as sd
            import speech_recognition  # noqa: F401
        except ImportError as exc:
            raise RuntimeError(
                "برای حالت صوتی، در محیط .venv_psychopy این بسته‌ها را نصب کنید:\n"
                "python -m pip install sounddevice SpeechRecognition"
            ) from exc

    try:
        shape_persian("آزمون")
    except ImportError as exc:
        raise RuntimeError(
            "برای نمایش فارسی، arabic-reshaper و python-bidi را در محیط .venv_psychopy نصب کنید."
        ) from exc

    app_dir = PROJECT_ROOT / "Reacton" / "App"
    if not app_dir.exists():
        app_dir = Path(__file__).resolve().parent
    output_dir = app_dir / "results"
    output_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    csv_path = output_dir / f"stroop_{mode}_{stamp}.csv"
    audio_dir = output_dir / f"stroop_audio_{stamp}"
    if mode == "voice":
        audio_dir.mkdir(parents=True, exist_ok=True)

    monitor = monitors.Monitor("StroopMonitor")
    monitor.setWidth(53)
    monitor.setDistance(60)
    monitor.setSizePix((1920, 1080))

    win = visual.Window(
        fullscr=True, screen=0, monitor=monitor, units="height",
        color=(-0.35, -0.35, -0.35), colorSpace="rgb",
        waitBlanking=True
    )
    kb = keyboard.Keyboard()
    fixation = visual.TextStim(win, text="+", color="white", height=0.055)
    stimulus = visual.TextStim(
        win, text="", color="white", height=0.095,
        font="Tahoma", wrapWidth=0.8
    )
    message = visual.TextStim(
        win, text="", color="white", height=0.035,
        font="Tahoma", wrapWidth=1.5
    )

    def show(text):
        message.text = shape_persian(text)
        message.draw()
        win.flip()

    def wait_space():
        while True:
            keys = kb.getKeys(keyList=["space", "escape"], waitRelease=False, clear=True)
            if any(k.name == "escape" for k in keys):
                return False
            if any(k.name == "space" for k in keys):
                return True
            core.wait(0.005)

    def capture_voice_trial():
        # ضبط کل پنجره پاسخ؛ شروع گفتار از روی انرژی صوتی تخمین زده می‌شود.
        # این زمان باید با میکروفون/کارت صدای مورد استفاده کالیبره شود.
        duration = MAX_RESPONSE_SECONDS
        recording = sd.rec(
            int(duration * VOICE_SAMPLE_RATE),
            samplerate=VOICE_SAMPLE_RATE,
            channels=1,
            dtype="float32"
        )
        sd.wait()
        onset_ms = detect_voice_onset(recording, VOICE_SAMPLE_RATE, noise_rms)
        return recording, onset_ms

    try:
        mode_text = "پاسخ صوتی: نام رنگ جوهر را با صدای واضح بگویید." if mode == "voice" else (
            "پاسخ صفحه‌کلید: D قرمز | F سبز | J آبی | K زرد"
        )
        show(
            "آزمون استروپ رنگ ـ واژه\n\n"
            "در هر نوبت فقط رنگ جوهر را اعلام کنید، نه معنی واژه را.\n\n"
            + mode_text +
            "\n\n۱۲ نوبت تمرینی و ۱۵ نوبت اصلی (۵ نوبت در هر وضعیت).\n"
            "برای شروع کلید فاصله را فشار دهید؛ برای خروج ESC."
        )
        if not wait_space():
            return

        noise_rms = 0.0
        if mode == "voice":
            show("لطفاً در سکوت بمانید؛ میکروفون در حال سنجش صدای محیط است.")
            noise_sample = sd.rec(
                int(0.5 * VOICE_SAMPLE_RATE),
                samplerate=VOICE_SAMPLE_RATE,
                channels=1,
                dtype="float32"
            )
            sd.wait()
            noise_rms = float(np.sqrt(np.mean(np.asarray(noise_sample) ** 2)))

            # بررسی میکروفون پیش از تمرین اصلی؛ فایل این بخش ذخیره نمی‌شود.
            while True:
                show(
                    "آزمایش میکروفون\n\n"
                    "پس از فشردن SPACE، جمله زیر را با صدای معمولی بگویید:\n"
                    "قرمز، سبز، آبی، زرد\n\n"
                    "ضبط به مدت ۳ ثانیه انجام می‌شود."
                )
                if not wait_space():
                    return

                show("در حال ضبط صدا... لطفاً صحبت کنید.")
                mic_sample = sd.rec(
                    int(3.0 * VOICE_SAMPLE_RATE),
                    samplerate=VOICE_SAMPLE_RATE,
                    channels=1,
                    dtype="float32"
                )
                sd.wait()
                mic_sample = np.asarray(mic_sample, dtype=np.float32).reshape(-1)
                mic_rms = float(np.sqrt(np.mean(mic_sample ** 2))) if mic_sample.size else 0.0
                mic_peak = float(np.max(np.abs(mic_sample))) if mic_sample.size else 0.0
                clipping_percent = float(np.mean(np.abs(mic_sample) >= 0.99) * 100) if mic_sample.size else 0.0

                try:
                    show("ضبط تمام شد؛ در حال پخش صدای ضبط‌شده...")
                    sd.play(mic_sample, VOICE_SAMPLE_RATE)
                    sd.wait()
                except Exception as exc:
                    raise RuntimeError(
                        "ضبط انجام شد، اما پخش صدای آزمایشی ممکن نشد. خروجی صدا و بلندگو را بررسی کنید."
                    ) from exc

                if mic_rms < 0.003:
                    quality_text = "صدای ضبط‌شده بسیار ضعیف است؛ میکروفون، مجوز دسترسی و فاصله از میکروفون را بررسی کنید."
                elif clipping_percent > 1.0 or mic_peak >= 0.999:
                    quality_text = "صدا دریافت شده، اما احتمالاً بیش از حد بلند و دچار بریدگی است؛ کمی از میکروفون فاصله بگیرید."
                else:
                    quality_text = "سطح صدای ضبط‌شده مناسب به نظر می‌رسد. واضح بودن تلفظ را نیز با گوش‌دادن بررسی کنید."

                show(
                    "نتیجه آزمایش میکروفون\n\n"
                    f"شدت متوسط صدا (RMS): {mic_rms:.4f}\n"
                    f"بیشینه دامنه صدا: {mic_peak:.3f}\n"
                    f"نمونه‌های احتمالاً بریده‌شده: {clipping_percent:.2f}%\n\n"
                    + quality_text +
                    "\n\nبرای ضبط دوباره R را فشار دهید.\n"
                    "برای تأیید میکروفون و ادامه، SPACE را فشار دهید.\n"
                    "برای خروج ESC را فشار دهید."
                )
                while True:
                    check_keys = kb.getKeys(
                        keyList=["r", "space", "escape"],
                        waitRelease=False,
                        clear=True
                    )
                    if any(k.name == "escape" for k in check_keys):
                        return
                    if any(k.name == "r" for k in check_keys):
                        break
                    if any(k.name == "space" for k in check_keys):
                        check_keys = None
                        break
                    core.wait(0.01)
                if check_keys is None:
                    break

        # تمرین؛ داده‌های تمرین وارد تحلیل اصلی نمی‌شوند.
        for idx, trial in enumerate(build_practice_trials(), start=1):
            fixation.draw()
            win.flip()
            core.wait(random.uniform(MIN_ISI_SECONDS, MAX_ISI_SECONDS))
            stimulus.text = shape_persian(trial["word"])
            stimulus.color = COLORS[trial["ink_color"]]["rgb"]
            stimulus.draw()
            win.flip()
            if mode == "keyboard":
                kb.clock.reset()
                response = None
                while kb.clock.getTime() < MAX_RESPONSE_SECONDS:
                    keys = kb.getKeys(keyList=["d", "f", "j", "k", "escape"], waitRelease=False, clear=True)
                    if keys:
                        if keys[0].name == "escape":
                            return
                        response = keys[0].name
                        break
                    core.wait(0.001)
            else:
                _, _ = capture_voice_trial()
            fixation.draw()
            win.flip()
            core.wait(0.25)

        show(
            "تمرین پایان یافت.\n"
            "بخش اصلی آزمون آغاز می‌شود؛ در این بخش بازخوردی نمایش داده نمی‌شود.\n\n"
            "برای شروع کلید فاصله را فشار دهید."
        )
        if not wait_space():
            return

        trials = build_trials()
        results = []
        audio_paths = []
        for trial_no, trial in enumerate(trials, start=1):
            fixation.draw()
            win.flip()
            isi = random.uniform(MIN_ISI_SECONDS, MAX_ISI_SECONDS)
            core.wait(isi)

            stimulus.text = shape_persian(trial["word"])
            stimulus.color = COLORS[trial["ink_color"]]["rgb"]
            kb.clearEvents()
            stimulus.draw()
            onset_time = win.flip()

            response_key = None
            response_color = None
            rt_ms = None
            audio_path = None

            if mode == "keyboard":
                kb.clock.reset()
                # reset روی فریم بعدی برای نزدیک‌شدن مبدأ زمان به شروع محرک
                win.callOnFlip(kb.clock.reset)
                while kb.clock.getTime() < MAX_RESPONSE_SECONDS:
                    keys = kb.getKeys(
                        keyList=["d", "f", "j", "k", "escape"],
                        waitRelease=False, clear=True
                    )
                    if keys:
                        key = keys[0]
                        if key.name == "escape":
                            return
                        response_key = key.name
                        response_color = KEY_TO_COLOR.get(response_key)
                        rt_ms = key.rt * 1000.0
                        break
                    core.wait(0.001)
            else:
                audio, rt_ms = capture_voice_trial()
                audio_path = audio_dir / f"trial_{trial_no:03d}.wav"
                save_wav(audio_path, audio, VOICE_SAMPLE_RATE)
                audio_paths.append(audio_path)

            stimulus_correct = response_color == trial["ink_color"] if mode == "keyboard" else None
            results.append({
                "trial_number": trial_no,
                "condition": trial["condition"],
                "word": trial["word"],
                "ink_color": trial["ink_color"],
                "response_mode": mode,
                "response_color": response_color,
                "response_key": response_key,
                "reaction_time_ms": round(rt_ms, 2) if rt_ms is not None else None,
                "correct": stimulus_correct,
                "no_response": rt_ms is None,
                "isi_ms": round(isi * 1000, 2),
                "audio_file": str(audio_path) if audio_path else "",
                "stimulus_onset_psychopy": onset_time,
            })
            fixation.draw()
            win.flip()

        if mode == "voice":
            show("آزمون به پایان رسید.\nدر حال تشخیص پاسخ‌های صوتی؛ لطفاً منتظر بمانید.")
            spoken_colors = transcribe_audio_files(audio_paths)
            for row, spoken in zip(results, spoken_colors):
                row["response_color"] = spoken
                row["correct"] = spoken == row["ink_color"] if spoken is not None else False
                row["no_response"] = row["reaction_time_ms"] is None
        else:
            spoken_colors = None

        fields = [
            "trial_number", "condition", "word", "ink_color",
            "response_mode", "response_color", "response_key",
            "reaction_time_ms", "correct", "no_response",
            "isi_ms", "audio_file", "stimulus_onset_psychopy"
        ]
        with open(csv_path, "w", newline="", encoding="utf-8-sig") as f:
            writer = csv.DictWriter(f, fieldnames=fields)
            writer.writeheader()
            writer.writerows(results)

        summaries = []
        for condition in ("congruent", "neutral", "incongruent"):
            subset = [r for r in results if r["condition"] == condition]
            valid = [r for r in subset if r["correct"] and r["reaction_time_ms"] is not None]
            times = [r["reaction_time_ms"] for r in valid]
            accuracy = (sum(bool(r["correct"]) for r in subset) / len(subset) * 100) if subset else 0
            summaries.append({
                "condition": condition,
                "accuracy": accuracy,
                "mean": statistics.mean(times) if times else None,
                "median": statistics.median(times) if times else None,
                "count": len(subset),
            })

        by_condition = {x["condition"]: x for x in summaries}
        inc = by_condition["incongruent"]["mean"]
        neu = by_condition["neutral"]["mean"]
        con = by_condition["congruent"]["mean"]
        interference = inc - neu if inc is not None and neu is not None else None
        facilitation = neu - con if neu is not None and con is not None else None

        # محاسبه تعداد پاسخ‌های درست، غلط و بدون پاسخ
        correct_count = sum(
            1 for r in results
            if r["correct"] is True and not r["no_response"]
        )

        no_response_count = sum(
            1 for r in results
            if r["no_response"] is True
        )

        wrong_count = len(results) - correct_count - no_response_count

        # نمایش نتیجه ساده به ورزشکار
        lines = [
            "آزمون استروپ پایان یافت",
            "",
            f"تعداد پاسخ‌های درست: {correct_count}",
            f"تعداد پاسخ‌های غلط: {wrong_count}",
            f"تعداد پاسخ‌های بدون پاسخ: {no_response_count}",
            "",
            "برای خروج ESC را فشار دهید."
        ]

        show("\n".join(lines))

        while True:
            if kb.getKeys(
                    keyList=["escape"],
                    waitRelease=False,
                    clear=True
            ):
                break

            core.wait(0.01)
        while True:
            if kb.getKeys(keyList=["escape"], waitRelease=False, clear=True):
                break
            core.wait(0.01)
    finally:
        win.close()
        core.quit()


class StroopScreen(QWidget):
    back_clicked = Signal()

    def __init__(self):
        super().__init__()
        self.process = None
        self.create_ui()

    def create_ui(self):
        self.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(35, 30, 35, 30)
        layout.setSpacing(16)

        title = QLabel("آزمون استروپ رنگ ـ واژه")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet("font-size: 24px; font-weight: bold;")
        layout.addWidget(title)

        description = QLabel(
            "در هر نوبت فقط رنگ جوهر واژه را مشخص کنید و به معنی واژه توجه نکنید. "
            "آزمون شامل وضعیت‌های هم‌راستا، ناهم‌راستا و خنثی است."
        )
        description.setWordWrap(True)
        description.setAlignment(Qt.AlignmentFlag.AlignCenter)
        description.setStyleSheet("font-size: 15px; color: #444;")
        layout.addWidget(description)

        mode_row = QHBoxLayout()
        mode_label = QLabel("روش پاسخ‌دهی:")
        self.mode_combo = QComboBox()
        self.mode_combo.addItem("پاسخ با صفحه‌کلید", "keyboard")
        self.mode_combo.addItem("پاسخ صوتی با میکروفون", "voice")
        mode_row.addWidget(mode_label)
        mode_row.addWidget(self.mode_combo, 1)
        layout.addLayout(mode_row)

        guide = QFrame()
        guide_layout = QVBoxLayout(guide)
        guide_layout.addWidget(QLabel("صفحه‌کلید: D قرمز | F سبز | J آبی | K زرد"))
        guide_layout.addWidget(QLabel("حالت صوتی: نام رنگ جوهر را واضح و با صدای معمولی بیان کنید."))
        guide_layout.addWidget(QLabel("۱۲ نوبت تمرینی + ۱۵ نوبت اصلی (۵ نوبت در هر وضعیت)؛ مهلت پاسخ ۱۵۰۰ میلی‌ثانیه."))
        guide_layout.addWidget(QLabel("تشخیص گفتار فارسی پس از پایان آزمون انجام می‌شود و به اینترنت نیاز دارد."))
        layout.addWidget(guide)

        self.start_button = QPushButton("شروع آزمون استروپ")
        self.start_button.setMinimumHeight(48)
        self.start_button.clicked.connect(self.start_test)
        layout.addWidget(self.start_button)

        self.back_button = QPushButton("بازگشت به فهرست آزمون‌ها")
        self.back_button.setMinimumHeight(42)
        self.back_button.clicked.connect(self.back_clicked.emit)
        layout.addWidget(self.back_button)
        layout.addStretch()

    def start_test(self):
        if not PSYCHOPY_PYTHON.exists():
            QMessageBox.critical(self, "خطا", f"مفسر Python پیدا نشد:\n{PSYCHOPY_PYTHON}")
            return
        mode = self.mode_combo.currentData()
        self.start_button.setEnabled(False)
        self.back_button.setEnabled(False)
        self.mode_combo.setEnabled(False)

        self.process = QProcess(self)
        self.process.finished.connect(self.test_finished)
        self.process.errorOccurred.connect(self.process_error)
        self.process.setProgram(str(PSYCHOPY_PYTHON))
        self.process.setArguments([str(Path(__file__).resolve()), "--run-task", mode])
        self.process.start()
        if not self.process.waitForStarted(5000):
            self.restore_controls()
            QMessageBox.critical(self, "خطا", "اجرای آزمون آغاز نشد.")

    def restore_controls(self):
        self.start_button.setEnabled(True)
        self.back_button.setEnabled(True)
        self.mode_combo.setEnabled(True)

    def test_finished(self, exit_code, exit_status):
        error_text = bytes(self.process.readAllStandardError()).decode("utf-8", errors="replace") if self.process else ""
        self.restore_controls()
        if exit_code != 0:
            QMessageBox.critical(self, "خطا در آزمون", error_text[-4000:] or "اجرای آزمون با خطا متوقف شد.")
        else:
            QMessageBox.information(
                self, "پایان آزمون",
                "فرایند آزمون پایان یافت. در صورت تکمیل آزمون، فایل CSV در پوشه App/results ذخیره شده است."
            )

    def process_error(self, error):
        self.restore_controls()
        QMessageBox.critical(self, "خطای اجرای آزمون", "فرایند اجرای PsychoPy با مشکل مواجه شد.")


if __name__ == "__main__" and len(sys.argv) >= 3 and sys.argv[1] == "--run-task":
    run_stroop_task(sys.argv[2])
