
import sys
import requests

from PySide6.QtWidgets import (
    QApplication,
    QMainWindow,
    QStackedWidget,
    QMessageBox,
)

from login_screen import LoginScreen
from register_screen import RegisterScreen
from dashboard_screen import DashboardScreen
from tests_screen import TestsScreen

from srt_screen import SRTScreen
from peripheral_screen import PeripheralScreen
from stroop_screen import StroopScreen
from go_nogo_screen import GoNoGoScreen
from cat_screen import CatScreen
from mot_screen import MOTScreen


API_URL = "https://apexlab-api.onrender.com"


class MainWindow(QMainWindow):

    def __init__(self):
        super().__init__()

        self.setWindowTitle("Athlete Performance App")
        self.resize(1100, 750)

        self.access_token = None
        self.current_user = None

        self.stack = QStackedWidget()
        self.setCentralWidget(self.stack)

        # ساخت صفحات
        self.login_screen = LoginScreen()
        self.register_screen = RegisterScreen()
        self.dashboard_screen = DashboardScreen()
        self.tests_screen = TestsScreen()

        self.srt_screen = SRTScreen()
        self.peripheral_screen = PeripheralScreen()
        self.stroop_screen = StroopScreen()
        self.go_nogo_screen = GoNoGoScreen()
        self.cat_screen = CatScreen()
        self.mot_screen = MOTScreen()

        screens = [
            self.login_screen,
            self.register_screen,
            self.dashboard_screen,
            self.tests_screen,
            self.srt_screen,
            self.peripheral_screen,
            self.stroop_screen,
            self.go_nogo_screen,
            self.cat_screen,
            self.mot_screen,
        ]

        for screen in screens:
            self.stack.addWidget(screen)

        # اتصال ورود
        self.login_screen.login_submitted.connect(
            self.authenticate_user
        )

        self.login_screen.login_success.connect(
            self.open_dashboard
        )

        self.login_screen.register_requested.connect(
            self.open_register
        )

        # اتصال ثبت‌نام
        self.register_screen.registration_submitted.connect(
            self.create_account
        )

        self.register_screen.back_to_login.connect(
            self.open_login
        )

        # اتصال داشبورد
        self.dashboard_screen.logout_requested.connect(
            self.logout
        )

        self.dashboard_screen.tests_requested.connect(
            self.open_tests
        )

        # اتصال آزمون‌ها
        self.tests_screen.back_clicked.connect(
            self.open_dashboard
        )

        self.tests_screen.test_selected.connect(
            self.open_selected_test
        )

        self.srt_screen.back_clicked.connect(self.open_tests)
        self.peripheral_screen.back_clicked.connect(self.open_tests)
        self.stroop_screen.back_clicked.connect(self.open_tests)
        self.go_nogo_screen.back_clicked.connect(self.open_tests)
        self.cat_screen.back_clicked.connect(self.open_tests)
        self.mot_screen.back_clicked.connect(self.open_tests)

        self.open_login()

    # ---------------- LOGIN ----------------

    def authenticate_user(self, username, password):
        try:
            response = requests.post(
                f"{API_URL}/auth/login",
                json={
                    "username": username,
                    "password": password,
                },
                timeout=60,
            )
            print("LOGIN STATUS:", response.status_code)
            try:
                data = response.json()
            except ValueError:
                data = {}

            if response.status_code == 200:
                token = data.get("access_token")

                if not token:
                    self.login_screen.show_login_error(
                        "پاسخ سرور معتبر نیست."
                    )
                    return

                self.access_token = token
                self.current_user = data.get("user", {})

                self.login_screen.show_login_success()
                return

            if response.status_code == 401:
                message = "نام کاربری یا رمز عبور اشتباه است."
            elif response.status_code == 422:
                message = "اطلاعات ورود معتبر نیست."
            else:
                detail = data.get(
                    "detail",
                    "ورود به حساب با خطا مواجه شد."
                )
                message = (
                    detail if isinstance(detail, str)
                    else "اطلاعات ورود معتبر نیست."
                )

            self.login_screen.show_login_error(message)

        except requests.exceptions.Timeout:
            self.login_screen.show_login_error(
                "پاسخ سرور بیش از حد طول کشید."
            )

        except requests.exceptions.ConnectionError:
            self.login_screen.show_login_error(
                "اتصال به سرور برقرار نشد. اینترنت را بررسی کنید."
            )

        except requests.exceptions.RequestException as error:
            print("Login request error:", error)
            self.login_screen.show_login_error(
                "ارتباط با سرور با مشکل مواجه شد."
            )

        except Exception as error:
            print("Login error:", error)
            self.login_screen.show_login_error(
                "خطای غیرمنتظره هنگام ورود رخ داد."
            )

    # ---------------- REGISTER ----------------

    def create_account(self, user_data):
        try:
            response = requests.post(
                f"{API_URL}/auth/register",
                json=user_data,
                timeout=60,
            )

            try:
                data = response.json()
            except ValueError:
                data = {}

            if response.status_code in (200, 201):
                self.register_screen.show_registration_success()

                QMessageBox.information(
                    self,
                    "ثبت‌نام موفق",
                    "حساب کاربری با موفقیت ایجاد شد. "
                    "اکنون می‌توانید وارد شوید."
                )

                self.open_login()
                return

            if response.status_code == 409:
                message = "این نام کاربری قبلاً ثبت شده است."

            elif response.status_code == 422:
                message = (
                    "اطلاعات واردشده معتبر نیست. "
                    "نام، نام خانوادگی، سن و رمز عبور را بررسی کنید."
                )

            else:
                detail = data.get(
                    "detail",
                    "ثبت‌نام با خطا مواجه شد."
                )

                message = (
                    detail if isinstance(detail, str)
                    else "اطلاعات ثبت‌نام معتبر نیست."
                )

            self.register_screen.show_registration_error(message)

        except requests.exceptions.Timeout:
            self.register_screen.show_registration_error(
                "پاسخ سرور بیش از حد طول کشید. دوباره تلاش کنید."
            )

        except requests.exceptions.ConnectionError:
            self.register_screen.show_registration_error(
                "اتصال به سرور برقرار نشد. اینترنت را بررسی کنید."
            )

        except requests.exceptions.RequestException as error:
            print("Registration request error:", error)

            self.register_screen.show_registration_error(
                "ارتباط با سرور با مشکل مواجه شد."
            )

        except Exception as error:
            print("Registration error:", error)

            self.register_screen.show_registration_error(
                "خطای غیرمنتظره هنگام ثبت‌نام رخ داد."
            )

    # ---------------- NAVIGATION ----------------

    def open_login(self):
        self.stack.setCurrentWidget(self.login_screen)

    def open_register(self):
        self.stack.setCurrentWidget(self.register_screen)

    def open_dashboard(self, *args):
        self.stack.setCurrentWidget(self.dashboard_screen)

    def open_tests(self):
        self.stack.setCurrentWidget(self.tests_screen)

    def logout(self):
        self.access_token = None
        self.current_user = None

        self.login_screen.password_input.clear()
        self.open_login()

    def open_selected_test(self, test_name):
        test_name = str(test_name).strip().upper()

        test_screens = {
            "SRT": self.srt_screen,
            "PERIPHERAL": self.peripheral_screen,
            "STROOP": self.stroop_screen,
            "GO_NOGO": self.go_nogo_screen,
            "CAT": self.cat_screen,
            "MOT": self.mot_screen,
        }

        screen = test_screens.get(test_name)

        if screen is not None:
            self.stack.setCurrentWidget(screen)
        else:
            QMessageBox.warning(
                self,
                "آزمون نامعتبر",
                f"شناسه آزمون معتبر نیست: {test_name}"
            )


if __name__ == "__main__":
    app = QApplication(sys.argv)

    window = MainWindow()
    window.show()

    sys.exit(app.exec())
