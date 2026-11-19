import sys
import csv
import cv2
import numpy as np
import time
import random
import statistics
import mediapipe as mp
mp_pose = mp.solutions.pose
P = mp_pose.PoseLandmark
from pathlib import Path
from datetime import datetime

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel,
    QPushButton, QMessageBox
)
from PySide6.QtCore import Qt, QProcess, Signal


# =====================================================
# تنظیمات آزمون
# =====================================================

MAIN_TOTAL_TRIALS = 25
CATCH_TRIALS = 1

PRACTICE_TRIALS = 5

STIMULUS_DURATION = 0.350
MIN_FOREPERIOD = 0.0
MAX_FOREPERIOD = 0.0
RESPONSE_WINDOW = 2.0
NO_RESPONSE_WINDOW = 0.8
POST_RETURN_DELAY = 0.5

FOOT_MOVEMENT_THRESHOLD = 0.16
TORSO_MOVEMENT_THRESHOLD = 0.12

RETURN_TIMEOUT = 10.0
NEUTRAL_STABLE_TIME = 0.8
NEUTRAL_FRAME_MOVEMENT = 0.05

CALIBRATION_STABLE_TIME = 1.5
CALIBRATION_MAX_TIME = 60

DIRECTIONS = ["LEFT", "RIGHT", "UP", "DOWN"]

WINDOW_NAME = "ApexLab - Movement Reaction Test"

# MediaPipe Pose landmark enum

# =====================================================
# ابزارهای تصویری و تشخیص بدن
# =====================================================

def get_pose(pose, frame):

    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    return pose.process(rgb)


def get_landmarks(result):

    if not result.pose_landmarks:
        return None

    return result.pose_landmarks.landmark


def landmark_visible(landmarks, index, threshold=0.50):

    return landmarks[index].visibility >= threshold


def check_body_visibility(landmarks):
    """Check visibility of the key body landmarks."""
    if landmarks is None:
        return False

    required = (
        P.LEFT_SHOULDER, P.RIGHT_SHOULDER,
        P.LEFT_HIP, P.RIGHT_HIP,
        P.LEFT_KNEE, P.RIGHT_KNEE,
        P.LEFT_ANKLE, P.RIGHT_ANKLE,
    )

    return all(landmarks[p.value].visibility >= 0.50 for p in required)


def get_body_values(landmarks):

    left_shoulder = landmarks[P.LEFT_SHOULDER]
    right_shoulder = landmarks[P.RIGHT_SHOULDER]

    left_hip = landmarks[P.LEFT_HIP]
    right_hip = landmarks[P.RIGHT_HIP]

    left_ankle = landmarks[P.LEFT_ANKLE]
    right_ankle = landmarks[P.RIGHT_ANKLE]

    shoulder_width = abs(
        left_shoulder.x - right_shoulder.x
    )

    if shoulder_width < 0.05:
        return None

    shoulder_center = (
        left_shoulder.x + right_shoulder.x
    ) / 2

    hip_center = (
        left_hip.x + right_hip.x
    ) / 2

    body_center = (
        shoulder_center + hip_center
    ) / 2

    return {
        "left_ankle": left_ankle.x,
        "right_ankle": right_ankle.x,
        "shoulder_width": shoulder_width,
        "torso": shoulder_center - hip_center,
        "center": body_center,
        "shoulder_center": shoulder_center,
        "hip_center": hip_center,
    }


def average_baseline(samples):

    keys = samples[0].keys()

    return {
        key: statistics.mean(
            sample[key] for sample in samples
        )
        for key in keys
    }


# =====================================================
# بررسی وضعیت اولیه کاربر
# =====================================================

def evaluate_posture(landmarks, frame):

    height, width = frame.shape[:2]

    if landmarks is None:

        return {
            "color": (0, 0, 255),
            "status": "BODY NOT DETECTED",
            "guide": "Stand in front of the camera"
        }

    if not check_body_visibility(landmarks):

        return {
            "color": (0, 0, 255),
            "status": "BODY NOT FULLY VISIBLE",
            "guide": "Show your full body and both feet"
        }

    values = get_body_values(landmarks)

    if values is None:

        return {
            "color": (0, 0, 255),
            "status": "POSITION NOT DETECTED",
            "guide": "Adjust your position"
        }

    # محدوده بدن در تصویر
    visible_points = [
        landmarks[P.NOSE],
        landmarks[P.LEFT_SHOULDER],
        landmarks[P.RIGHT_SHOULDER],
        landmarks[P.LEFT_HIP],
        landmarks[P.RIGHT_HIP],
        landmarks[P.LEFT_ANKLE],
        landmarks[P.RIGHT_ANKLE],
    ]

    min_x = min(point.x for point in visible_points)
    max_x = max(point.x for point in visible_points)

    min_y = min(point.y for point in visible_points)
    max_y = max(point.y for point in visible_points)

    # فاصله از لبه تصویر
    if (
        min_x < 0.015
        or max_x > 0.985
        or min_y < 0.01
        or max_y > 0.99
    ):

        return {
            "color": (0, 0, 255),
            "status": "BODY OUT OF FRAME",
            "guide": "Move slightly away from camera"
        }

    # مرکز بدن باید نزدیک مرکز تصویر باشد
    center_error = abs(values["center"] - 0.5)

    if center_error > 0.20:

        return {
            "color": (0, 165, 255),
            "status": "ADJUST YOUR POSITION",
            "guide": "Move to the center of the screen"
        }

    # بررسی کج بودن بالاتنه
    torso_error = abs(values["torso"]) / values["shoulder_width"]

    if torso_error > 0.35:

        return {
            "color": (0, 165, 255),
            "status": "BODY NOT STRAIGHT",
            "guide": "Stand straight"
        }

    return {
        "color": (0, 255, 0),
        "status": "GOOD POSITION",
        "guide": "Stand still"
    }


# =====================================================
# رسم اسکلت بدن
# =====================================================

def draw_skeleton(frame, landmarks, color, mirrored=False):

    if landmarks is None:
        return

    height, width = frame.shape[:2]

    connections = mp_pose.POSE_CONNECTIONS

    for start, end in connections:

        point_a = landmarks[start]
        point_b = landmarks[end]

        if (
            point_a.visibility < 0.35
            or point_b.visibility < 0.35
        ):
            continue

        x1 = int((1.0 - point_a.x if mirrored else point_a.x) * width)
        y1 = int(point_a.y * height)

        x2 = int((1.0 - point_b.x if mirrored else point_b.x) * width)
        y2 = int(point_b.y * height)

        cv2.line(
            frame,
            (x1, y1),
            (x2, y2),
            color,
            4,
            cv2.LINE_AA
        )

    for point in landmarks:

        if point.visibility < 0.35:
            continue

        x = int((1.0 - point.x if mirrored else point.x) * width)
        y = int(point.y * height)

        cv2.circle(
            frame,
            (x, y),
            5,
            color,
            -1,
            cv2.LINE_AA
        )


def show_test_screen(direction=None):
    """Display a plain black test screen with an optional arrow only."""
    display = np.zeros((720, 1280, 3), dtype="uint8")
    if direction:
        draw_arrow(display, direction)
    cv2.imshow(WINDOW_NAME, display)
    return cv2.waitKey(1) & 0xFF


# =====================================================
# متن و رابط دوربین
# =====================================================

def draw_text(
    frame,
    text,
    position,
    color=(255, 255, 255),
    scale=0.7,
    thickness=2
):

    cv2.putText(
        frame,
        text,
        position,
        cv2.FONT_HERSHEY_SIMPLEX,
        scale,
        color,
        thickness,
        cv2.LINE_AA
    )


def draw_arrow(frame, direction):

    height, width = frame.shape[:2]

    center = (width // 2, height // 2)

    length = 110

    offsets = {
        "LEFT": (-length, 0),
        "RIGHT": (length, 0),
        "UP": (0, -length),
        "DOWN": (0, length),
    }

    if direction not in offsets:
        return

    dx, dy = offsets[direction]

    end = (
        center[0] + dx,
        center[1] + dy
    )

    cv2.arrowedLine(
        frame,
        center,
        end,
        (0, 255, 255),
        12,
        cv2.LINE_AA,
        tipLength=0.35
    )


def draw_camera_screen(
    frame,
    landmarks=None,
    color=(0, 255, 0),
    status="",
    guide="",
    direction=None,
    trial_text=""
):

    display = cv2.flip(frame.copy(), 1)

    if landmarks is not None:
        draw_skeleton(display, landmarks, color, mirrored=True)

    height, width = display.shape[:2]

    # نوار بالای تصویر
    cv2.rectangle(
        display,
        (0, 0),
        (width, 110),
        (15, 20, 35),
        -1
    )
    draw_text(
        display,
        "ApexLab",
        (30, 40),
        (255, 255, 255),
        0.8
    )

    draw_text(
        display,
        status,
        (30, 78),
        color,
        0.75
    )

    draw_text(
        display,
        guide,
        (30, height - 55),
        (255, 255, 255),
        0.65
    )

    if trial_text:

        draw_text(
            display,
            trial_text,
            (width - 300, 45),
            (255, 255, 255),
            0.7
        )

    if direction:

        draw_arrow(display, direction)

    cv2.imshow(WINDOW_NAME, display)

    return cv2.waitKey(1) & 0xFF


# =====================================================
# تشخیص حرکت پا و تنه
# =====================================================

def detect_movement(current, baseline):

    width = baseline["shoulder_width"]

    left_dx = (
        current["left_ankle"]
        - baseline["left_ankle"]
    ) / width

    right_dx = (
        current["right_ankle"]
        - baseline["right_ankle"]
    ) / width

    torso_dx = (
        current["torso"]
        - baseline["torso"]
    ) / width

    # در تصویر خام:
    # حرکت پای چپ فرد به سمت چپ بدن
    # معمولاً در جهت مثبت محور x تصویر است.

    left_step = left_dx > FOOT_MOVEMENT_THRESHOLD

    right_step = right_dx < -FOOT_MOVEMENT_THRESHOLD

    if left_step and not right_step:

        movement = "LEFT"

    elif right_step and not left_step:

        movement = "RIGHT"

    elif left_step and right_step:

        if abs(left_dx) >= abs(right_dx):
            movement = "LEFT"
        else:
            movement = "RIGHT"

    else:

        movement = None

    if torso_dx > TORSO_MOVEMENT_THRESHOLD:
        torso_direction = "LEFT"

    elif torso_dx < -TORSO_MOVEMENT_THRESHOLD:
        torso_direction = "RIGHT"

    else:
        torso_direction = None

    return {
        "movement": movement,
        "left_dx": left_dx,
        "right_dx": right_dx,
        "torso_dx": torso_dx,
        "torso_direction": torso_direction
    }


def is_neutral(current, baseline):

    width = baseline["shoulder_width"]

    left_delta = abs(
        current["left_ankle"]
        - baseline["left_ankle"]
    ) / width

    right_delta = abs(
        current["right_ankle"]
        - baseline["right_ankle"]
    ) / width

    torso_delta = abs(
        current["torso"]
        - baseline["torso"]
    ) / width

    return (
        left_delta < 0.10
        and right_delta < 0.10
        and torso_delta < 0.15
    )


# =====================================================
# دریافت فریم و نمایش وضعیت
# =====================================================

def read_and_draw(
    camera,
    pose,
    direction=None,
    trial_text="",
    guide_override=None
):

    ret, frame = camera.read()

    if not ret:
        return None, None, None, -1

    result = get_pose(pose, frame)

    landmarks = get_landmarks(result)

    posture = evaluate_posture(
        landmarks,
        frame
    )

    guide = (
        guide_override
        if guide_override
        else posture["guide"]
    )

    key = draw_camera_screen(
        frame,
        landmarks,
        posture["color"],
        posture["status"],
        guide,
        direction,
        trial_text
    )

    values = None

    if landmarks is not None and check_body_visibility(landmarks):

        values = get_body_values(landmarks)

    return frame, landmarks, values, key


# =====================================================
# کالیبراسیون خودکار
# =====================================================

def automatic_calibration(camera, pose):

    start_time = time.perf_counter()

    stable_start = None

    samples = []

    previous_values = None

    while time.perf_counter() - start_time < CALIBRATION_MAX_TIME:

        frame, landmarks, values, key = read_and_draw(
            camera,
            pose,
            guide_override="Stand straight and remain still"
        )

        if frame is None:
            continue

        if key == 27:
            return None

        if values is None:
            stable_start = None
            samples.clear()
            previous_values = None
            continue

        posture = evaluate_posture(
            landmarks,
            frame
        )

        if posture["color"] != (0, 255, 0):

            stable_start = None
            samples.clear()
            previous_values = None

            continue

        if previous_values is not None:

            movement = (
                abs(values["left_ankle"] - previous_values["left_ankle"])
                + abs(values["right_ankle"] - previous_values["right_ankle"])
                + abs(values["center"] - previous_values["center"])
            )

            if movement > 0.035:

                stable_start = None
                samples.clear()

        if stable_start is None:

            stable_start = time.perf_counter()
            samples = []

        samples.append(values)

        previous_values = values

        elapsed = time.perf_counter() - stable_start

        if elapsed >= CALIBRATION_STABLE_TIME and len(samples) >= 15:

            baseline = average_baseline(samples)

            # پیام موفقیت
            for _ in range(25):

                frame, landmarks, values, key = read_and_draw(
                    camera,
                    pose,
                    guide_override="Calibration completed!"
                )

                if key == 27:
                    return None

            return baseline

    raise RuntimeError(
        "کالیبراسیون انجام نشد. لطفاً در مقابل دوربین صاف و ثابت بایستید."
    )


# =====================================================
# شمارش معکوس
# =====================================================

def countdown(camera, pose):

    for number in range(5, 0, -1):
        start = time.perf_counter()

        while time.perf_counter() - start < 1:
            display = np.zeros((720, 1280, 3), dtype="uint8")
            draw_text(
                display, str(number), (610, 380),
                (0, 255, 255), 3, 7
            )
            cv2.imshow(WINDOW_NAME, display)
            if cv2.waitKey(1) & 0xFF == 27:
                return False

    return True


# =====================================================
# اجرای یک کوشش
# =====================================================

def run_trial(
    camera, pose, baseline, direction, trial_number, total_trials,
    trial_type="TARGET", practice=False
):

    foreperiod = random.uniform(MIN_FOREPERIOD, MAX_FOREPERIOD)
    wait_start = time.perf_counter()

    # فاصله تصادفی؛ صفحه در تمام مدت کاملاً سیاه است.
    while time.perf_counter() - wait_start < foreperiod:
        key = show_test_screen()
        if key == 27:
            return None
        # دریافت فریم برای حفظ جریان دوربین، بدون نمایش تصویر آن
        camera.grab()

    arrow = direction if trial_type == "TARGET" else None

    # شروع زمان واکنش دقیقاً هم‌زمان با آغاز محرک
    onset_time = time.perf_counter()
    response = None
    reaction_time = None
    detected_frames = 0
    detected_direction = None
    torso_direction = None
    target_displacement = None
    support_displacement = None

    trial_response_window = (
        NO_RESPONSE_WINDOW
        if direction in ("UP", "DOWN") and trial_type == "TARGET"
        else RESPONSE_WINDOW
    )

    while time.perf_counter() - onset_time < trial_response_window:
        ret, frame = camera.read()
        if not ret:
            continue

        result = get_pose(pose, frame)
        landmarks = get_landmarks(result)
        elapsed = time.perf_counter() - onset_time

        # فقط در مدت تعیین‌شده محرک، پیکان نمایش داده می‌شود.
        visible_arrow = arrow if elapsed < STIMULUS_DURATION else None
        key = show_test_screen(visible_arrow)
        if key == 27:
            return None

        if landmarks is None or not check_body_visibility(landmarks):
            continue

        current = get_body_values(landmarks)
        if current is None:
            continue

        movement_data = detect_movement(current, baseline)
        movement = movement_data["movement"]

        if movement_data["torso_direction"]:
            torso_direction = movement_data["torso_direction"]

        if movement is not None:
            if movement == detected_direction:
                detected_frames += 1
            else:
                detected_direction = movement
                detected_frames = 1
        else:
            detected_direction = None
            detected_frames = 0

        if detected_frames >= 2:
            response = detected_direction
            reaction_time = (time.perf_counter() - onset_time) * 1000

            if direction == "LEFT":
                target_displacement = movement_data["left_dx"]
                support_displacement = movement_data["right_dx"]
            elif direction == "RIGHT":
                target_displacement = movement_data["right_dx"]
                support_displacement = movement_data["left_dx"]
            break

    if trial_type == "CATCH":
        correct = response is None
    elif direction in ("LEFT", "RIGHT"):
        support_foot_stable = (
            support_displacement is not None
            and abs(support_displacement) <= 0.10
        )
        correct = response == direction and support_foot_stable
    else:
        correct = response is None

    return {
        "trial_number": trial_number,
        "trial_type": trial_type,
        "target_direction": direction,
        "detected_direction": response,
        "reaction_time_ms": reaction_time,
        "correct": correct,
        "torso_direction": torso_direction,
        "target_leg_displacement": target_displacement,
        "support_leg_displacement": support_displacement,
        "foreperiod_ms": round(foreperiod * 1000, 2),
        "practice": practice
    }


# =====================================================
# انتظار برای برگشت به وضعیت اولیه
# =====================================================

def wait_for_neutral(camera, pose, baseline=None):
    """Wait for a stable, upright posture and recalibrate its position.

    The user may return to a slightly different location; only uprightness
    and short-term stability are required. The returned baseline is used
    for the next trial so movement is measured from the new neutral stance.
    """
    start = time.perf_counter()
    stable_start = None
    previous_values = None
    samples = []

    while time.perf_counter() - start < RETURN_TIMEOUT:
        ret, frame = camera.read()
        if not ret:
            show_test_screen()
            continue

        landmarks = get_landmarks(get_pose(pose, frame))
        values = None
        upright = False

        if landmarks is not None and check_body_visibility(landmarks):
            values = get_body_values(landmarks)
            if values is not None:
                torso_error = abs(values["torso"]) / values["shoulder_width"]
                upright = torso_error <= 0.35

        # بازگشت به وضعیت آماده فقط با ثبات بدن و صاف بودن تنه سنجیده می‌شود؛
        # لازم نیست مختصات پاها دقیقاً با محل کالیبراسیون اول یکسان باشد.
        if not upright or values is None:
            stable_start = None
            previous_values = None
            samples.clear()
        else:
            movement = 0.0
            if previous_values is not None:
                movement = (
                    abs(values["left_ankle"] - previous_values["left_ankle"])
                    + abs(values["right_ankle"] - previous_values["right_ankle"])
                    + abs(values["center"] - previous_values["center"])
                    + abs(values["torso"] - previous_values["torso"])
                )

            if previous_values is None or movement > NEUTRAL_FRAME_MOVEMENT:
                stable_start = time.perf_counter()
                samples = [values]
            else:
                samples.append(values)

            previous_values = values
            if (
                stable_start is not None
                and time.perf_counter() - stable_start >= NEUTRAL_STABLE_TIME
                and len(samples) >= 15
            ):
                return average_baseline(samples)

        key = show_test_screen()
        if key == 27:
            return None

    return None


# =====================================================
# بازخورد تمرین
# =====================================================

def show_feedback(camera, pose, correct, response):
    """Show practice feedback on a black screen; main trials never call this."""
    if correct:
        message = "CORRECT"
        color = (0, 255, 0)
    elif response is None:
        message = "NO RESPONSE"
        color = (0, 0, 255)
    else:
        message = "WRONG DIRECTION"
        color = (0, 0, 255)

    start = time.perf_counter()
    while time.perf_counter() - start < 0.8:
        camera.grab()
        display = np.zeros((720, 1280, 3), dtype="uint8")
        draw_text(display, message, (420, 380), color, 1.1, 3)
        cv2.imshow(WINDOW_NAME, display)
        if cv2.waitKey(1) & 0xFF == 27:
            return False
    return True


# =====================================================
# ذخیره نتایج
# =====================================================

def save_results(results):

    output_dir = (
        Path(__file__).resolve().parent / "results"
    )

    output_dir.mkdir(exist_ok=True)

    timestamp = datetime.now().strftime(
        "%Y%m%d_%H%M%S"
    )

    output_file = output_dir / (
        f"movement_reaction_{timestamp}.csv"
    )

    fieldnames = [
        "trial_number",
        "trial_type",
        "target_direction",
        "detected_direction",
        "reaction_time_ms",
        "correct",
        "torso_direction",
        "target_leg_displacement",
        "support_leg_displacement",
        "foreperiod_ms",
        "practice"
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

    return output_file


# =====================================================
# اجرای کل آزمون
# =====================================================

def run_peripheral_task():

    camera = cv2.VideoCapture(0)

    if not camera.isOpened():

        raise RuntimeError(
            "دوربین قابل دسترسی نیست."
        )

    camera.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
    camera.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)

    pose = mp_pose.Pose(
        static_image_mode=False,
        model_complexity=1,
        smooth_landmarks=True,
        min_detection_confidence=0.5,
        min_tracking_confidence=0.5
    )

    results = []

    try:

        cv2.namedWindow(
            WINDOW_NAME,
            cv2.WINDOW_NORMAL
        )

        cv2.setWindowProperty(
            WINDOW_NAME,
            cv2.WND_PROP_FULLSCREEN,
            cv2.WINDOW_FULLSCREEN
        )

        # ---------------------------------
        # مرحله اول: آماده‌سازی و کالیبراسیون
        # ---------------------------------

        baseline = automatic_calibration(
            camera,
            pose
        )

        if baseline is None:
            return

        # ---------------------------------
        # مرحله دوم: آزمون تمرینی
        # ---------------------------------

        practice_directions = [
            "LEFT",
            "RIGHT",
            "UP",
            "DOWN",
            "LEFT"
        ]

        random.shuffle(practice_directions)

        for index, direction in enumerate(
            practice_directions,
            start=1
        ):

            trial = run_trial(
                camera,
                pose,
                baseline,
                direction,
                index,
                PRACTICE_TRIALS,
                practice=True
            )

            if trial is None:
                return

            if not show_feedback(
                camera, pose, trial["correct"], trial["detected_direction"]
            ):
                return

            new_baseline = wait_for_neutral(camera, pose, baseline)
            if new_baseline is None:
                return
            baseline = new_baseline
            # پس از بازگشت به وضعیت صاف و پایدار، نیم ثانیه مکث.
            delay_start = time.perf_counter()
            while time.perf_counter() - delay_start < POST_RETURN_DELAY:
                if show_test_screen() == 27:
                    return

        # ---------------------------------
        # مرحله سوم: شمارش معکوس
        # ---------------------------------

        if not countdown(camera, pose):
            return

        # ---------------------------------
        # مرحله چهارم: آزمون اصلی
        # ---------------------------------

        # دقیقاً ۲۵ کوشش: شش بار از هر جهت و یک کوشش Catch.
        # ترتیب همه کوشش‌ها کاملاً تصادفی است.
        trials = []

        for direction in DIRECTIONS:
            for _ in range(6):
                trials.append({
                    "type": "TARGET",
                    "direction": direction
                })

        for _ in range(CATCH_TRIALS):
            trials.append({
                "type": "CATCH",
                "direction": None
            })

        random.shuffle(trials)

        total_trials = len(trials)

        for index, item in enumerate(trials, start=1):

            direction = item["direction"]

            trial = run_trial(
                camera,
                pose,
                baseline,
                direction,
                index,
                total_trials,
                trial_type=item["type"]
            )

            if trial is None:
                break

            results.append(trial)

            # در آزمون اصلی بازخورد درست/غلط نشان داده نمی‌شود.
            # در فلش‌های بالا/پایین، اگر کاربر در ۸۰۰ میلی‌ثانیه
            # حرکتی نداشته باشد، همان ایستادن ثابت برای رفتن به بعدی کافی است.
            if direction in ("UP", "DOWN") and trial["detected_direction"] is None:
                new_baseline = baseline
            else:
                new_baseline = wait_for_neutral(camera, pose, baseline)

            if new_baseline is None:
                raise RuntimeError(
                    "وضعیت بدن پایدار و صاف تشخیص داده نشد. آزمون متوقف شد."
                )

            baseline = new_baseline
            # کوشش بعدی ۵۰۰ میلی‌ثانیه پس از آماده‌شدن کاربر آغاز می‌شود.
            delay_start = time.perf_counter()
            while time.perf_counter() - delay_start < POST_RETURN_DELAY:
                if show_test_screen() == 27:
                    break

        if not results:
            return

        output_file = save_results(results)

        # ---------------------------------
        # محاسبه نتایج
        # ---------------------------------

        correct_results = [
            r for r in results
            if r["correct"]
            and r["target_direction"] in ("LEFT", "RIGHT")
            and r["reaction_time_ms"] is not None
        ]

        reaction_times = [
            r["reaction_time_ms"]
            for r in correct_results
        ]

        mean_rt = (
            statistics.mean(reaction_times)
            if reaction_times
            else None
        )

        median_rt = (
            statistics.median(reaction_times)
            if reaction_times
            else None
        )

        correct_count = sum(
            1 for r in results
            if r["correct"]
        )

        wrong_count = sum(
            1 for r in results
            if r["detected_direction"] is not None
            and r["correct"] is False
        )

        summary = [
            "TEST COMPLETED",
            f"Total trials: {len(results)}",
            f"Correct trials: {correct_count}",
            f"Wrong responses: {wrong_count}"
        ]

        if mean_rt is not None:

            summary.extend([
                f"Mean RT: {mean_rt:.1f} ms",
                f"Median RT: {median_rt:.1f} ms"
            ])

        summary.append(
            f"Saved: {output_file.name}"
        )

        while True:

            display = np.zeros((720, 1280, 3), dtype="uint8")

            y = 100

            for line in summary:

                draw_text(
                    display,
                    line,
                    (40, y),
                    (255, 255, 255),
                    0.7
                )

                y += 45

            cv2.imshow(WINDOW_NAME, display)

            if cv2.waitKey(10) & 0xFF == 27:
                break

    finally:

        pose.close()
        camera.release()
        cv2.destroyAllWindows()


# =====================================================
# صفحه آزمون در برنامه اصلی
# =====================================================

class PeripheralScreen(QWidget):

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
            QWidget {background-color: #07152d;
                color: white;
                font-family: Arial;
            }

            QLabel {
                color: white;
            }

            QPushButton {
                background-color: #087ee8;
                color: white;
                border: none;
                border-radius: 10px;
                padding: 13px;
                font-size: 15px;
                font-weight: bold;
            }

            QPushButton:hover {
                background-color: #00b9e8;
            }

            QPushButton:disabled {
                background-color: #555b66;
            }
        """)

        layout = QVBoxLayout(self)

        layout.setContentsMargins(40, 35, 40, 35)
        layout.setSpacing(20)

        title = QLabel(
            "آزمون دوم: واکنش حرکتی جانبی"
        )

        title.setAlignment(Qt.AlignCenter)

        title.setStyleSheet("""
            font-size: 25px;
            font-weight: bold;
            color: #20c9ff;
        """)

        description = QLabel(
            "در این آزمون با مشاهده فلش چپ یا راست، "
            "پای متناظر را به طرفین حرکت دهید و به وضعیت اولیه برگردید.\n"
            "در برابر فلش بالا و پایین بدون حرکت بمانید.\n"
            "ابتدا وضعیت بدن شما با دوربین بررسی و کالیبره می‌شود؛ "
            "سپس آزمون تمرینی و اصلی به‌صورت خودکار اجرا می‌شوند."
        )

        description.setAlignment(Qt.AlignCenter)
        description.setWordWrap(True)

        description.setStyleSheet(
            "font-size: 16px;"
        )

        layout.addWidget(title)
        layout.addWidget(description)

        self.status_label = QLabel(
            "برای شروع، دکمه زیر را انتخاب کنید."
        )

        self.status_label.setAlignment(Qt.AlignCenter)

        layout.addWidget(self.status_label)

        self.start_button = QPushButton(
            "شروع و کالیبراسیون خودکار"
        )

        self.start_button.setMinimumHeight(52)

        self.start_button.clicked.connect(
            self.start_test
        )

        layout.addWidget(self.start_button)

        self.back_button = QPushButton(
            "بازگشت"
        )

        self.back_button.setMinimumHeight(45)

        self.back_button.clicked.connect(
            self.go_back
        )

        layout.addWidget(self.back_button)

        layout.addStretch()

    def start_test(self):

        self.start_button.setEnabled(False)
        self.back_button.setEnabled(False)

        self.status_label.setText(
            "در حال راه‌اندازی دوربین..."
        )

        self.process = QProcess(self)

        self.process.finished.connect(
            self.test_finished
        )

        self.process.errorOccurred.connect(
            self.process_error
        )

        script_path = str(
            Path(__file__).resolve()
        )

        self.process.start(
            sys.executable,
            [script_path, "--run-task"]
        )

        if not self.process.waitForStarted(5000):

            self.start_button.setEnabled(True)
            self.back_button.setEnabled(True)

            self.status_label.setText(
                "اجرای آزمون آغاز نشد."
            )

            QMessageBox.critical(
                self,
                "خطا",
                "اجرای آزمون آغاز نشد."
            )

    def test_finished(self, exit_code, exit_status):

        self.start_button.setEnabled(True)
        self.back_button.setEnabled(True)

        if exit_code == 0:

            self.status_label.setText(
                "آزمون پایان یافت."
            )

            QMessageBox.information(
                self,
                "پایان آزمون",
                "آزمون پایان یافت. اطلاعات در پوشه results ذخیره شد."
            )

        else:

            error_text = ""

            if self.process:

                error_text = bytes(
                    self.process.readAllStandardError()
                ).decode(
                    "utf-8",
                    errors="replace"
                )

            self.status_label.setText("اجرای آزمون با خطا متوقف شد."
            )

            QMessageBox.critical(
                self,
                "خطا در آزمون",
                error_text[-2500:] or
                "اجرای آزمون با خطا متوقف شد."
            )

    def process_error(self, error):

        self.start_button.setEnabled(True)
        self.back_button.setEnabled(True)

        self.status_label.setText(
            "خطا در اجرای آزمون."
        )

    def go_back(self):

        if (
            self.process
            and self.process.state() != QProcess.NotRunning
        ):

            self.process.kill()
            self.process.waitForFinished(2000)

        self.back_clicked.emit()


if __name__ == "__main__":

    if (
        len(sys.argv) > 1
        and sys.argv[1] == "--run-task"
    ):

        run_peripheral_task()