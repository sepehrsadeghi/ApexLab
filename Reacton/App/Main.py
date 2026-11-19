import sys
from pathlib import Path

import requests

from PySide6.QtWidgets import (
    QApplication, QMainWindow, QStackedWidget, QMessageBox
)
from PySide6.QtGui import QIcon

from login_screen import LoginScreen
from register_screen import RegisterScreen
from dashboard_screen import DashboardScreen
from tests_screen import TestsScreen
from srt_screen import SRTScreen
from peripheral_screen import PeripheralScreen


API_URL = "http://127.0.0.1:8001"


class SportReactionApp(QMainWindow):

    def __init__(self):
        super().__init__()

        self.base_dir = Path(__file__).resolve().parent
        self.assets_dir = self.base_dir / "assets"

        self.setWindowTitle("ApexLab")
        self.setMinimumSize(1100, 700)
        self.setWindowIcon(QIcon(str(self.assets_dir / "apexlab_icon.png")))

        self.current_user = None

        self.stack = QStackedWidget()
        self.setCentralWidget(self.stack)

        self.login_screen = LoginScreen()
        self.register_screen = RegisterScreen()
        self.tests_screen = TestsScreen()
        self.srt_screen = SRTScreen()
        self.peripheral_screen = PeripheralScreen()
        self.dashboard_screen = None

        for screen in (
            self.login_screen,
            self.register_screen,
            self.tests_screen,
            self.srt_screen,
            self.peripheral_screen,
        ):
            self.stack.addWidget(screen)

        self.login_screen.login_submitted.connect(self.handle_login)
        self.login_screen.register_clicked.connect(self.show_register)

        self.register_screen.registration_submitted.connect(
            self.handle_registration
        )
        self.register_screen.back_to_login.connect(self.show_login)

        self.tests_screen.back_clicked.connect(self.open_dashboard)
        self.tests_screen.test_selected.connect(self.open_selected_test)
        self.srt_screen.back_clicked.connect(self.open_tests)
        self.peripheral_screen.back_clicked.connect(self.open_tests)

        self.show_login()

    def show_login(self):
        self.stack.setCurrentWidget(self.login_screen)

    def show_register(self):
        self.stack.setCurrentWidget(self.register_screen)

    def handle_registration(self, user_data):

        payload = {
            "first_name": user_data["first_name"],
            "last_name": user_data["last_name"],
            "username": user_data["username"],
            "password": user_data["password"],
            "gender": user_data["gender"]
        }

        try:
            response = requests.post(
                f"{API_URL}/auth/register",
                json=payload,
                timeout=15
            )

            if response.status_code == 409:
                QMessageBox.warning(
                    self, "ثبت‌نام ناموفق",
                    "این نام کاربری قبلاً ثبت شده است."
                )
                return

            response.raise_for_status()

            QMessageBox.information(
                self, "ثبت‌نام موفق",
                "حساب کاربری با موفقیت ایجاد شد."
            )

            self.login_screen.username_input.setText(
                user_data["username"]
            )
            self.login_screen.password_input.clear()
            self.show_login()

        except requests.exceptions.ConnectionError:
            QMessageBox.critical(
                self, "خطای اتصال",
                "ارتباط با سرور برقرار نشد. "
                "مطمئن شوید بک‌اند در حال اجراست."
            )

        except requests.exceptions.Timeout:
            QMessageBox.warning(
                self, "پایان زمان انتظار",
                "سرور در زمان مشخص‌شده پاسخ نداد."
            )

        except requests.exceptions.HTTPError:
            try:
                message = response.json().get(
                    "detail", "اطلاعات ثبت‌نام معتبر نیست."
                )
            except ValueError:
                message = "خطا در ثبت‌نام."

            QMessageBox.warning(self, "خطای ثبت‌نام", str(message))

        except Exception as error:
            QMessageBox.critical(
                self, "خطای غیرمنتظره", str(error)
            )

    def handle_login(self, username, password):

        payload = {
            "username": username.strip(),
            "password": password
        }

        try:
            response = requests.post(
                f"{API_URL}/auth/login",
                json=payload,
                timeout=15
            )

            if response.status_code == 401:
                QMessageBox.warning(
                    self, "خطای ورود",
                    "نام کاربری یا رمز عبور اشتباه است."
                )
                return

            response.raise_for_status()

            data = response.json()
            user = data["user"]

            # هماهنگ‌سازی اطلاعات دریافتی با داشبورد
            self.current_user = {
                **user,
                "full_name": (
                    user["first_name"] + " " + user["last_name"]
                )
            }

            self.login_screen.password_input.clear()
            self.open_dashboard()

        except requests.exceptions.ConnectionError:
            QMessageBox.critical(
                self, "خطای اتصال",
                "ارتباط با سرور برقرار نشد. "
                "مطمئن شوید بک‌اند در حال اجراست."
            )

        except requests.exceptions.Timeout:
            QMessageBox.warning(
                self, "پایان زمان انتظار",
                "سرور در زمان مشخص‌شده پاسخ نداد."
            )

        except requests.exceptions.HTTPError:
            QMessageBox.warning(
                self, "خطای ورود",
                "در ورود به حساب مشکلی رخ داد."
            )

        except Exception as error:
            QMessageBox.critical(
                self, "خطای غیرمنتظره", str(error)
            )

    def open_dashboard(self):

        if self.current_user is None:
            self.show_login()
            return

        if self.dashboard_screen is not None:
            self.stack.removeWidget(self.dashboard_screen)
            self.dashboard_screen.deleteLater()

        self.dashboard_screen = DashboardScreen(self.current_user)
        self.stack.addWidget(self.dashboard_screen)

        self.dashboard_screen.new_test_clicked.connect(self.open_tests)
        self.dashboard_screen.logout_clicked.connect(self.logout)

        self.stack.setCurrentWidget(self.dashboard_screen)

    def logout(self):
        self.current_user = None
        self.login_screen.password_input.clear()
        self.show_login()

    def open_tests(self):
        self.stack.setCurrentWidget(self.tests_screen)

    def open_selected_test(self, test_name):

        if test_name == "SRT":
            self.stack.setCurrentWidget(self.srt_screen)

        elif test_name == "PERIPHERAL":
            self.stack.setCurrentWidget(self.peripheral_screen)

        else:
            QMessageBox.warning(
                self, "خطا",
                "آزمون انتخاب‌شده معتبر نیست."
            )

    def closeEvent(self, event):
        event.accept()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = SportReactionApp()
    window.show()
    sys.exit(app.exec())