
import subprocess
import tempfile
import threading
import os
import keyring
from PySide6.QtCore import Qt, QObject, QCoreApplication
import sys
from PySide6.QtWidgets import QApplication, QMessageBox
from core.monitor import SecurityMonitor
from ui.login_ui import LoginWindow
from ui.api import keyauthapp
from ui.main_ui import FramelessWindow
from ctypes import windll


class Main:
    def __init__(self, window):
        self.window = window
        self.vpn_process = None
        self.setup_connections()
        print("Application initialized.")

    def setup_connections(self):
        self.window.powerButton.clicked.connect(self.on_power_button_click)
        print("Connections set up.")

    def on_power_button_click(self):
        print("Power button clicked.")
        if self.vpn_process and self.vpn_process.poll() is None:
            self.stop_vpn()
        else:
            self.start_vpn_connection()

    def start_vpn_connection(self):
        current_item = self.window.countryList.currentItem()
        if not current_item:
            self.show_message_box("Selection Required", "Please select a country before connecting.")
            print("No country selected.")
            return

        country = current_item.text()
        mode = self.get_selected_mode()
        if mode:
            print(f"Selected mode: {mode}")
        else:
            print("No mode selected.")

        config = self.get_vpn_config(country, mode)
        if config:
            self.start_vpn(config)
        else:
            self.show_message_box("Configuration Error", f"No configuration found for {country} with mode {mode}")
            print("Configuration not found for:", country, "with mode:", mode)

    def stop_vpn(self):
        if self.vpn_process:
            self.vpn_process.terminate()
            self.vpn_process = None
            self.window.powerButton.connectionChanged.emit(False)
            print("VPN connection terminated.")

    def start_vpn(self, config_contents):
        openvpn_exe_path = self.find_openvpn_path()
        if not openvpn_exe_path:
            print("Error: openvpn.exe not found.")
            return

        with tempfile.NamedTemporaryFile(delete=False, mode='w+', suffix='.ovpn') as config_file:
            config_file.write(config_contents)
            config_file.flush()
            config_file_path = config_file.name

        command = [openvpn_exe_path, "--config", config_file_path]
        print(f"Executing command: {command}")

        creation_flags = subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
        self.vpn_process = subprocess.Popen(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            creationflags=creation_flags
        )

        threading.Thread(target=self.monitor_vpn, args=(config_file_path,)).start()

    def monitor_vpn(self, config_filename):
        initialization_completed = False
        try:
            while True:
                if self.vpn_process is None or self.vpn_process.poll() is not None:
                    break

                output = self.vpn_process.stdout.readline()
                if "Initialization Sequence Completed" in output:
                    initialization_completed = True
                    self.window.powerButton.connectionChanged.emit(True)
                    print("Initialization Sequence Completed. Deleting config file...")
                    break

                if output == '':
                    break

                if output:
                    print(output.strip())

        finally:
            if initialization_completed:
                try:
                    os.unlink(config_filename)
                    print("Config file deleted.")
                except FileNotFoundError as e:
                    print(f"Error deleting config file: {e}")
            else:
                self.show_vpn_error_message()
    def show_vpn_error_message(self):
        self.show_message_box("VPN Connection Error",
                                "Error connecting to VPN. Please restart your PC and try again. "
                                "If the issue persists, please contact EZVPN support.")

    def find_openvpn_path(self):
        if getattr(sys, 'frozen', False):
            base_path = sys._MEIPASS
        else:
            base_path = os.path.dirname(os.path.abspath(__file__))

        search_paths = [
            os.path.join(base_path, "OpenVPN", "bin"),
            "C:\\Program Files\\OpenVPN\\bin",
            os.path.join(base_path, "OpenVPN")
        ]

        for path in search_paths:
            openvpn_exe_path = os.path.join(path, "openvpn.exe")
            if os.path.exists(openvpn_exe_path):
                return openvpn_exe_path

        return None
    def get_selected_mode(self):
        for button in self.window.menuItems:
            if button.isChecked() and button.text().strip() in ["Bot Lobby", "Full VPN"]:
                return button.text().strip()
        return None  # Return None if no mode is selected

    def get_vpn_config(self, country, mode):
        config_mapping = {
            "South Africa": {"Bot Lobby": africa, "Full VPN": africa_all},
            "Netherlands": {"Bot Lobby": amsterdam, "Full VPN": amsterdam_all},
            "Australia": {"Bot Lobby": australia, "Full VPN": australia_all},
            "Canada": {"Bot Lobby": canada, "Full VPN": canada_all},
            "Chile": {"Bot Lobby": chile, "Full VPN": chile_all},
            "Germany": {"Bot Lobby": germany, "Full VPN": germany_all},
            "India": {"Bot Lobby": india, "Full VPN": india_all},
            "Israel": {"Bot Lobby": israel, "Full VPN": israel_all},
            "Japan": {"Bot Lobby": japan, "Full VPN": japan_all},
            "Mexico": {"Bot Lobby": mexico, "Full VPN": mexico_all},
            "Poland": {"Bot Lobby": poland, "Full VPN": poland_all},
            "Singapore": {"Bot Lobby": singapore, "Full VPN": singapore_all},
            "South Korea": {"Bot Lobby": korea, "Full VPN": south_korea_all},
            "Spain": {"Bot Lobby": spain, "Full VPN": spain_all},
            "Sweden": {"Bot Lobby": sweden, "Full VPN": sweden_all},
            "United Kingdom": {"Bot Lobby": united_kingdom, "Full VPN": united_kingdom_all},
            "USA Miami": {"Bot Lobby": usa_miami, "Full VPN": usa_miami_all},
            "USA Chicago": {"Bot Lobby": chicago_usa, "Full VPN": chicago_usa_all},
            "USA Los Angeles": {"Bot Lobby": la_usa, "Full VPN": la_usa_all}
        }
        return config_mapping.get(country, {}).get(mode)


    def show(self):
        self.window.show()
    def show_message_box(self, title, message):
        msgBox = QMessageBox(self.window)
        msgBox.setWindowTitle(title)
        msgBox.setText(message)
        msgBox.setWindowFlags(msgBox.windowFlags() | Qt.FramelessWindowHint | Qt.Dialog)
        msgBox.setStyleSheet("""
            QMessageBox {
                color: white;
                padding: 8px;
                background-color: #2a2d34;
                border: 1px solid #707070;
                border-radius: 5px;
                font-size: 14px;
            }
            QMessageBox QLabel {  /* More specific to target labels within the message box */
                color: white;  /* Explicitly setting text color again for any labels */
            }
            QPushButton {
                color: white;
                background-color: #3a3f4b; /* Consistent with the combo box */
                border: none;
                padding: 5px;
                border-radius: 2px;
                min-width: 70px; /* Ensures buttons are not too small */
            }
            QPushButton:hover {
                background-color: #4a4f5b; /* Slightly lighter gray for hover */
                border: none;
            }
        """)
        msgBox.setStandardButtons(QMessageBox.Ok)
        msgBox.exec_()


class OneTimeKeyChecker(QObject):
    def __init__(self, keyauthapp):
        super().__init__()
        self.keyauthapp = keyauthapp
        if not self.check_saved_license_and_login():
            QCoreApplication.quit()

    def check_saved_license_and_login(self):
        saved_key = keyring.get_password("VPN", "license_key")
        if saved_key:
            return self.verify_license(saved_key)
        return False

    def verify_license(self, license_key):
        result = self.keyauthapp.license(license_key)
        if result:
            keyring.set_password("VPN", "license_key", license_key)
            return True
        return False


def is_admin():
    try:
        return windll.shell32.IsUserAnAdmin()
    except:
        return False

def main():
    app = QApplication(sys.argv)

    if not is_admin():
        msgBox = QMessageBox()

        msgBox.setText("VPN must be run as an administrator.")
        msgBox.setWindowFlags(msgBox.windowFlags() | Qt.FramelessWindowHint | Qt.Dialog)
        msgBox.setStyleSheet("""
            QMessageBox {
                color: white;
                padding: 8px;
                background-color: #2a2d34;
                border: 1px solid #707070;
                border-radius: 5px;
                font-size: 14px;
            }
            QMessageBox QLabel {  /* More specific to target labels within the message box */
                color: white;  /* Explicitly setting text color again for any labels */
            }
            QPushButton {
                color: white;
                background-color: #3a3f4b; /* Consistent with the combo box */
                border: none;
                padding: 5px;
                border-radius: 2px;
                min-width: 70px; /* Ensures buttons are not too small */
            }
            QPushButton:hover {
                background-color: #4a4f5b; /* Slightly lighter gray for hover */
                border: none;
            }
        """)
        msgBox.setStandardButtons(QMessageBox.Ok)
        msgBox.exec()
        sys.exit()

    monitor = SecurityMonitor()
    monitor.run_security_check()

    login_window = LoginWindow(api_instance=keyauthapp)
    window = FramelessWindow()
    main_app = Main(window)
    monitor = SecurityMonitor()
    monitor.run_security_check()
    # login_window.login_successful.connect(main_app.show)
    # one_time_key_checker = OneTimeKeyChecker(keyauthapp)
    # one_time_key_checker.check_saved_license_and_login()
    #
    # login_window.check_saved_license_and_login()
    main_app.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()

