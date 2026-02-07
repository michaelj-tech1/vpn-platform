import os
import sys
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLineEdit, QPushButton,
                               QLabel, QSizePolicy, QSpacerItem, QMessageBox)
from PySide6.QtGui import QFont, QPixmap, QIcon, QCursor
from PySide6.QtCore import Qt, QPoint, QEvent, Signal

import keyring


class TooltipLabel(QLabel):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAlignment(Qt.AlignCenter)
        self.setWordWrap(True)
        self.setStyleSheet("""
            QLabel {
                color: white;
                padding: 8px;
                background-color: #2a2d34; /* Adjust the color to match your design */
                border: 1px solid #707070; /* Adjust the color to match your design */
                border-radius: 5px;
                font-size: 10px;
            }
        """)
        self.setVisible(False)



class LoginWindow(QMainWindow):
    login_successful = Signal()

    def __init__(self, api_instance, parent=None):
        super().__init__(parent)
        self.api = api_instance
        self.init_ui()
        self.setWindowFlags(Qt.Window | Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.apply_dark_theme_styles()
        self.oldPos = self.pos()
        self.themeButtonTooltip = TooltipLabel(self)


    def init_ui(self):
        self.base_path = self.get_base_path()

        self.setWindowTitle('Login Form')
        self.setGeometry(500, 300, 350, 250)
        self.central_widget = QWidget(self)
        self.setCentralWidget(self.central_widget)
        main_layout = QVBoxLayout(self.central_widget)
        main_layout.setContentsMargins(15, 15, 15, 15)

        self.icon_button = QPushButton()
        icon_pixmap = QPixmap(self.get_image_path('light10.png'))
        self.icon_button.setFixedSize(10, 10)
        self.icon_button.setIcon(QIcon(icon_pixmap))
        self.icon_button.setStyleSheet("background-color: transparent; border: none;")

        self.icon_button.installEventFilter(self)

        self.icon_button.setCursor(QCursor(Qt.PointingHandCursor))
        self.icon_button.clicked.connect(self.toggle_theme)

        icon_width, icon_height = icon_pixmap.size().width(), icon_pixmap.size().height()
        padding_h = (self.icon_button.width() - icon_width) / 2
        padding_v = (self.icon_button.height() - icon_height) / 2

        self.icon_button.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent;
                border: none;
                padding-left: {padding_h}px;
                padding-right: {padding_h}px;
                padding-top: {padding_v}px;
                padding-bottom: {padding_v}px;
            }}
        """)



        header_layout = QHBoxLayout()

        self.minimize_button = QPushButton("−")
        self.minimize_button.setFont(QFont("Arial", 17))
        self.minimize_button.setStyleSheet("background-color: transparent; color: white;border: none; outline: none; padding: 0px;")
        self.minimize_button.clicked.connect(self.showMinimized)
        self.minimize_button.setCursor(QCursor(Qt.PointingHandCursor))
        self.close_button = QPushButton("×")
        self.close_button.setFont(QFont("Arial", 17))
        self.close_button.setStyleSheet("background-color: transparent; color: white; border: none;outline: none; padding: 0px;")
        self.close_button.clicked.connect(self.close)
        self.close_button.setCursor(QCursor(Qt.PointingHandCursor))

        header_layout.addWidget(self.icon_button)

        spacer = QLabel()
        header_layout.setSpacing(0)

        header_layout.addWidget(spacer)
        header_layout.setStretchFactor(spacer, 1)


        header_layout.addWidget(self.minimize_button)

        header_layout.addWidget(self.close_button)
        main_layout.addLayout(header_layout)
        main_layout.setSpacing(10)


        spacer_left = QSpacerItem(40, 20, QSizePolicy.Expanding, QSizePolicy.Minimum)
        spacer_right = QSpacerItem(40, 20, QSizePolicy.Expanding, QSizePolicy.Minimum)

        header_layout = QHBoxLayout()
        header_layout.addItem(spacer_left)
        header_layout.addItem(spacer_right)

        main_layout.addLayout(header_layout)


        self.key_entry = QLineEdit()
        self.key_entry.setPlaceholderText('Enter your License key...')
        self.key_entry.setFont(QFont('Arial', 10))
        key_image = self.get_image_path('key.png').replace('\\', '/')
        self.key_entry.setStyleSheet(f"""
            QLineEdit {{
                background-color: #262626; 
                color: white; 
                border-radius: 15px; 
                padding: 5px;
                padding-left: 40px; /* Adjust padding to avoid text overlaying the image */
                background-image: url({key_image});
                background-repeat: no-repeat; 
                background-position: left center; /* Positions the image to the left-center of the QLineEdit */
            }}
        """)
        self.key_entry.setFixedSize(240, 60)
        main_layout.addWidget(self.key_entry, alignment=Qt.AlignCenter)


        self.login_btn = QPushButton('Submit')
        self.login_btn.setFont(QFont('Arial', 10, QFont.Bold))
        self.login_btn.setStyleSheet("background-color: #4a64ff; color: white; border-radius: 15px; padding: 10px;")
        self.login_btn.setFixedSize(240, 60)
        self.login_btn.clicked.connect(self.on_login_clicked)

        self.login_btn.setCursor(QCursor(Qt.PointingHandCursor))
        main_layout.addWidget(self.login_btn, alignment=Qt.AlignCenter)

        self.footer = QLabel("© 2025 VPN")
        self.footer.setStyleSheet("color: rgba(255, 255, 255, 128); padding: 10px; font-size: 11px;")
        self.footer.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(self.footer)

        header_layout = QHBoxLayout()



        main_layout.addLayout(header_layout)

    def eventFilter(self, watched, event):
        if watched == self.icon_button:
            if event.type() == QEvent.Enter:

                tooltip_text = "Switch to Light Mode" if 'background-color: #1C1A1A;' in self.central_widget.styleSheet() else "Switch to Dark Mode"
                self.themeButtonTooltip.setText(tooltip_text)

                specific_x = 15
                specific_y = 40
                self.themeButtonTooltip.move(specific_x, specific_y)
                self.themeButtonTooltip.show()
            elif event.type() == QEvent.Leave:
                self.themeButtonTooltip.hide()
        return super(LoginWindow, self).eventFilter(watched, event)

    def mousePressEvent(self, event):
        self.oldPos = event.globalPos()

    def mouseMoveEvent(self, event):
        delta = QPoint(event.globalPos() - self.oldPos)
        self.move(self.x() + delta.x(), self.y() + delta.y())
        self.oldPos = event.globalPos()

    def toggle_theme(self):
        if 'background-color: #1C1A1A;' in self.central_widget.styleSheet():
            print("Switching to light theme")
            self.apply_light_theme_styles()
        else:
            print("Switching to dark theme")
            self.apply_dark_theme_styles()

    def apply_light_theme_styles(self):

        self.minimize_button.setStyleSheet("background-color: transparent; color: gray;")
        self.close_button.setStyleSheet("background-color: transparent; color: gray;")

        self.central_widget.setStyleSheet("""
            QWidget {
                background-color: #FFFFFF; /* Light white background */
                color: black;
                border-radius: 10px;
            }
            QLineEdit {
                background-color: #FFFFFF;
                border: 1px solid #CCC;
                border-radius: 5px;
                padding: 5px;
                margin: 10px;
                color: #000;
            }
            QPushButton {
                background-color: #FFFFFF;
                border: 1px solid #DDD;
                border-radius: 5px;
                padding: 5px;
                margin: 10px;
                color: #000;
            }
        """)
        self.icon_button.setIcon(QIcon(QPixmap(self.get_image_path('light17.png'))))

        self.icon_button.setFixedSize(25, 25)

        self.login_btn.setStyleSheet("""
            QPushButton {
                background-color: #A3CEFF; /* Lighter shade of blue */
                color: white; /* White text */
                border-radius: 15px;
                padding: 10px;
                border: 1px solid #8faeff; /* Optional: light blue border to match the background */
                text-align: center;
            }
            QPushButton:hover {
                background-color: #92BFFF; /* A slightly different blue for hover */
            }
            QPushButton:pressed {
                background-color: #7291ff; /* Original color or a bit darker for the pressed state */
            }
        """)

        self.icon_button.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                border: none;
                padding: 5px;
                color: black; /* Text color adjusted for light theme if needed */
            }
        """)
        key2 = self.get_image_path('lightkey2.png').replace('\\', '/')
        self.key_entry.setStyleSheet(f"""
            QLineEdit {{
                background-color: #D4D6D8; 
                color: gray; 
                border-radius: 15px; 
                padding: 5px;
                padding-left: 40px; /* Adjust padding to avoid text overlaying the image */
                background-image: url({key2});
                background-repeat: no-repeat; 
                background-position: left center; /* Positions the image to the left-center of the QLineEdit */
            }}
        """)
    def apply_dark_theme_styles(self):

        self.login_btn.setStyleSheet("background-color: #4a64ff; color: white; border-radius: 15px; padding: 10px;")
        key1 = self.get_image_path('key.png').replace('\\', '/')

        self.key_entry.setStyleSheet(f"""
            QLineEdit {{
                background-color: #262626; 
                color: white; 
                border-radius: 15px; 
                padding: 5px;
                padding-left: 40px; /* Adjust padding to avoid text overlaying the image */
                background-image: url({key1});
                background-repeat: no-repeat; 
                background-position: left center; /* Positions the image to the left-center of the QLineEdit */
            }}
        """)
        self.icon_button.setIcon(QIcon(QPixmap(self.get_image_path('light9.png'))))
        self.icon_button.setFixedSize(25, 25)
        self.central_widget.setStyleSheet("""
            QWidget {
                background-color: #1C1A1A; /* Dark gray background */
                color: white;
                border-radius: 10px;
            }
            QLineEdit {
                background-color: #333;
                border: 1px solid #555;
                border-radius: 5px;
                padding: 5px;
                margin: 10px;
                color: #FFF;
            }
            QPushButton {
                background-color: #1C1C1C;
                border: 1px solid #2D2D2D;
                border-radius: 5px;
                padding: 5px;
                margin: 10px;
                color: #FFF;
            }
        """)
    def on_login_clicked(self):
        license_key = self.key_entry.text().strip()
        if not license_key:
            self.show_error_message("Input Error", "Please enter a key")
            return

        self.verify_license(license_key, prompt_on_fail=True)

    def verify_license(self, license_key, prompt_on_fail=False):
        """Verify the license key with the API.

        Args:
            license_key (str): The license key to verify.
            prompt_on_fail (bool): If True, show the login UI on verification failure.
        """
        result = self.api.license(license_key)
        if result:
            keyring.set_password("VPN", "license_key", license_key)
            self.login_successful.emit()
            self.close()
        else:
            if prompt_on_fail:
                self.show_error_message("Key Error", "Please enter a valid key")

                self.show()

    def check_saved_license_and_login(self):
        """Check for a saved license and validate it; show login if necessary."""
        saved_key = keyring.get_password("VPN", "license_key")
        if saved_key:
            self.verify_license(saved_key, prompt_on_fail=True)
        else:
            self.show()


    def get_base_path(self):
        """Get the base path for the application."""
        if getattr(sys, 'frozen', False):
            return sys._MEIPASS
        else:
            return os.path.dirname(os.path.abspath(__file__))

    def get_image_path(self, image_name):
        """Construct the path to an image resource."""
        return os.path.join(self.base_path, 'ss', image_name)



    def show_error_message(self, title, message):
        """Display an error message with custom styling and no title bar."""
        msgBox = QMessageBox(self)
        msgBox.setWindowTitle(title)
        msgBox.setText(message)
        msgBox.setStyleSheet("""
            QMessageBox {
                color: white;
                padding: 8px;
                background-color: #2a2d34;
                border: 1px solid #707070;
                border-radius: 5px;
                font-size: 14px;
            }
            QMessageBox QLabel {
                color: white;
            }
            QPushButton {
                color: white;
                background-color: #3a3f4b;
                border: none;
                padding: 5px;
                border-radius: 2px;
                min-width: 70px;
            }
            QPushButton:hover {
                background-color: #4a4f5b;
            }
        """)
        msgBox.setWindowFlags(msgBox.windowFlags() | Qt.FramelessWindowHint | Qt.Dialog)
        msgBox.setStandardButtons(QMessageBox.Ok)
        msgBox.exec_()
