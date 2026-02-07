import os
import subprocess
import sys
import time
from functools import partial
from pathlib import Path

from PySide6.QtCore import Signal

import paramiko
from PySide6 import QtCore
from PySide6.QtCore import QByteArray, QBuffer, QIODevice, QEvent
from PySide6.QtWidgets import (QHBoxLayout, QPushButton, QLabel,
                               QLineEdit, QListWidget, QGraphicsDropShadowEffect, QListWidgetItem, QSpacerItem,
                               QSizePolicy, QScrollArea, QGridLayout, QMessageBox, QInputDialog, QRadioButton)
from PySide6.QtCore import Qt, QSize, QRectF, QTimer, QPointF, QPoint
from PySide6.QtGui import QPainter, QPainterPath, QPen, QColor, QCursor
from PySide6.QtWidgets import QApplication, QMainWindow, QWidget, QVBoxLayout, QListWidget, QListWidgetItem
from PySide6.QtGui import QIcon, QFont, QPixmap
from PySide6.QtCore import Qt

import sys
import flagpy as fp


class CustomPowerButton(QPushButton):
    connectionChanged = Signal(bool)

    def __init__(self, parent=None):

        super().__init__(parent)
        self.setFixedSize(100, 100)
        self.setCursor(QCursor(Qt.PointingHandCursor))

        self.setStyleSheet("background-color: transparent;")
        self.icon_color = QColor("#3265E4")
        self.clicked_color = QColor("#008000")
        self.disconnected_color = QColor("#3265E4")

        self.shadow = QGraphicsDropShadowEffect(self)
        self.shadow.setBlurRadius(50)
        self.shadow.setOffset(0, 0)
        self.setGraphicsEffect(self.shadow)

        self.connected_shadow_color = QColor("#32CD32")
        self.disconnected_shadow_color = QColor("#3265E4")

        self.shadow.setColor(self.disconnected_shadow_color)

        self.connectionChanged.connect(self.update_color)


        self.timer = QTimer(self)
        self.timer.timeout.connect(self.on_timeout)
        self.transition_steps = 20
        self.current_step = 0
        self.animating = False
        self.connectionChanged.connect(self.update_color)



    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        center_point = QPointF(self.width() / 2, self.height() / 2)
        outer_radius = min(self.width(), self.height()) / 2

        painter.setBrush(QColor(20, 19, 20))
        painter.setPen(Qt.NoPen)
        painter.drawEllipse(center_point, outer_radius, outer_radius)

        icon_pen = QPen(self.icon_color, 5)
        icon_pen.setCapStyle(Qt.RoundCap)
        painter.setPen(icon_pen)
        vertical_line_length = outer_radius *1
        line_offset = 25
        painter.drawLine(
            QPointF(center_point.x(), center_point.y() - vertical_line_length / 2),
            QPointF(center_point.x(), center_point.y() + vertical_line_length / 2 - line_offset)
        )

        arc_rect = QRectF(center_point.x() - outer_radius / 2, center_point.y() - outer_radius / 2,
                          outer_radius, outer_radius)
        start_angle = 135 * 16
        span_angle = 270 * 16
        painter.drawArc(arc_rect, start_angle, span_angle)


    def update_color(self, connected):
        if connected:
            self.icon_color = self.clicked_color
            self.shadow.setColor(self.connected_shadow_color)
        else:
            self.icon_color = self.disconnected_color
            self.shadow.setColor(self.disconnected_shadow_color)
        self.repaint()



    def on_click(self):

        self.icon_color = self.clicked_color if self.isConnected else self.disconnected_color
        self.toggle_vpn_signal.emit(self.isConnected)

        time.sleep(3)
        self.repaint()

    def emit_connect_signal(self):
        pass

    def emit_disconnect_signal(self):
        pass

    def on_timeout(self):
        self.current_step += 1
        progress = self.current_step / self.transition_steps
        if progress >= 1.0:
            progress = 1.0
            self.timer.stop()
            self.animating = False

        r = int(
            self.start_color.red()
            + (self.end_color.red() - self.start_color.red()) * progress
        )
        g = int(
            self.start_color.green()
            + (self.end_color.green() - self.start_color.green()) * progress
        )
        b = int(
            self.start_color.blue()
            + (self.end_color.blue() - self.start_color.blue()) * progress
        )

        self.icon_color = QColor(r, g, b)
        self.circle_color = QColor(r, g, b)
        self.repaint()

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


class FramelessWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.theme = "dark"


        self.setWindowTitle('VPN')

        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        self.setAttribute(Qt.WA_TranslucentBackground)

        self.setGeometry(100, 100, 650, 500)

        self.centralWidget = QWidget(self)
        self.centralWidget.setObjectName("centralWidget")
        self.centralWidget.setStyleSheet(
            "QWidget#centralWidget { background-color: #1C1A1A; border-radius: 15px; }"
        )
        self.setCentralWidget(self.centralWidget)

        self.mainLayout = QHBoxLayout(self.centralWidget)
        self.mainLayout.setContentsMargins(0, 0, 0, 0)

        self.base_path = self.get_base_path()

        sidebarContainer = QWidget()
        sidebarContainerLayout = QVBoxLayout(sidebarContainer)
        sidebarContainerLayout.setContentsMargins(0, 0, 0, 0)
        sidebarContainerLayout.setSpacing(0)
        sidebarContainer.setStyleSheet("background-color: transparent;")

        self.sidebar = QWidget()
        self.sidebarLayout = QVBoxLayout(self.sidebar)
        self.sidebarLayout.setContentsMargins(0, 0, 0, 0)

        self.sidebar.setFixedWidth(250)
        self.sidebar.setStyleSheet("background-color: #101010; color: white; border-radius: 10px;")
        sidebarContainerLayout.addWidget(self.sidebar)

        self.mainLayout.addWidget(sidebarContainer, alignment=Qt.AlignLeft)

        self.logoLabel = QLabel()
        self.logoLabel.setText("VPN\nClient")
        self.logoLabel.setFixedHeight(100)
        self.logoLabel.setAlignment(Qt.AlignCenter)
        self.logoLabel.setStyleSheet("""
            color: white;
            font-size: 22px;
            font-weight: 700;
            line-height: 1.1;
            border-bottom: 1px solid #2a2d34;
        """)
        self.sidebarLayout.addWidget(self.logoLabel)

        self.menuItems = [
            QPushButton(QIcon(self.get_image_path('globe.png')), " Full VPN"),
            QPushButton(QIcon(self.get_image_path('help.png')), " FAQ"),
            QPushButton("Reset Connection")
        ]

        self.commonStyle = """
            QPushButton { color: white; padding: 15px; border: none; text-align: left; font-size: 16px; }
            QPushButton:hover { background-color: #4a64ff; }
            QPushButton:checked {
                border-right: 4px solid #3265E4; 
                background-color: transparent; /* No background color change */
                background-image: linear-gradient(to right, transparent 90%, #3265E4 90%, #3265E4 100%);  /* Creates a vertical line that matches the border */
                border-top-right-radius: -4px;  /* Wraps the border around the top-right corner */
                border-bottom-right-radius: -4px;  /* Wraps the border around the bottom-right corner */
            }
        """

        for btn in self.menuItems:
            btn.setCheckable(True)
            btn.setStyleSheet(self.commonStyle)
            btn.setCursor(QCursor(Qt.PointingHandCursor))

            self.sidebarLayout.addWidget(btn)
            btn.clicked.connect(partial(self.update_button_selection, btn))

        self.resetButtonTooltip = TooltipLabel(self)
        self.resetButtonTooltip.setText(
            "You will only need to click on 'Reset Connection' if you are switching from Full VPN to DNS")

        faqResetLayout = QVBoxLayout()
        faqButton = self.menuItems[-2]
        resetButton = self.menuItems[-1]
        resetButton.installEventFilter(self)

        faqResetLayout.addWidget(faqButton)
        faqResetLayout.addWidget(resetButton)
        faqButton.setStyleSheet(self.commonStyle)
        resetButton.setIcon(QIcon(self.get_image_path('resetconnection.png')))
        resetButton.setIconSize(QSize(23, 23))
        resetButton.setStyleSheet("""
            QPushButton { color: white; padding: 5px 25px; margin: 5px; border: 2px solid #5d1e1e; text-align: center; font-size: 14px; background-color: #5d1e1e; border-radius: 7px; }
        """)
        self.sidebarLayout.addLayout(faqResetLayout)

        resetButton = next((btn for btn in self.menuItems if btn.text() == "Reset Connection"), None)

        if resetButton:
            resetButton.clicked.disconnect()
            resetButton.clicked.connect(self.resetVpnConnection)

        self.footer = QLabel("© 2025 VPN")
        self.footer.setStyleSheet("color: rgba(255, 255, 255, 128); margin-top: 5px; padding: 10px; font-size: 11px;")
        self.footer.setMaximumHeight(50)
        self.footer.setAlignment(Qt.AlignCenter)
        self.sidebarLayout.addWidget(self.footer)

        self.mainContent = QWidget()
        self.mainContentLayout = QVBoxLayout(self.mainContent)
        self.mainContentLayout.setAlignment(Qt.AlignCenter)
        self.mainLayout.addWidget(self.mainContent, 1)

        self.powerButton = CustomPowerButton()
        self.mainContentLayout.addWidget(self.powerButton, 0, Qt.AlignCenter)
        self.powerButton.update_color(True)
        self.consoleVpnSetupRadio = QRadioButton("Console Support", self.mainContent)
        self.consoleVpnSetupRadio.move(150, 160)
        self.consoleVpnSetupRadio.setCursor(QCursor(Qt.PointingHandCursor))

        self.consoleVpnSetupRadio.setStyleSheet("""
            QRadioButton {
                color: white;
                font-size: 10px;
                background-color: transparent;
            }
            QRadioButton::indicator {
                width: 10px;
                height: 10px;
                border: 2px solid #3265E4;
                
            }
            QRadioButton::indicator:checked {
                background-color: #4a64ff;
                border-radius: 15px;  # Ensure the colored fill is also round

            }
        """)
        self.consoleVpnSetupRadio.setVisible(False)
        self.consoleVpnSetupRadio.toggled.connect(self.handleConsoleVpnSetup, QtCore.Qt.DirectConnection)

        self.searchBox = QLineEdit()
        self.searchBox.setMaximumWidth(275)
        self.searchBox.setPlaceholderText("Search...")
        search_image_path = self.get_image_path('search.png').replace('\\', '/')

        self.searchBox.setStyleSheet(f"""
            QLineEdit {{
                padding-left: 33px; /* Adjusted to move text further to the right */
                padding-top: 10px;
                padding-bottom: 10px;
                border: 1px solid #333;
                border-radius: 20px;
                background-color: #262626;
                color: white;
                font-size: 14px;
                background-image: url({search_image_path});
                background-repeat: no-repeat;
                background-position: center left; /* Keeps the icon on the left */
            }}
        """)
        self.mainContentLayout.addWidget(self.searchBox)
        self.searchBox.textChanged.connect(self.filter_countries)


        self.countryList = QListWidget(self)
        self.countryList.setMaximumHeight(250)
        self.countryList.setMaximumWidth(275)

        desired_icon_size = 40
        self.countryList.setIconSize(QSize(desired_icon_size, desired_icon_size))

        countries = [
            "South Africa", "Netherlands", "Australia", "Canada",
            "Chile", "Germany", "India", "Israel", "Japan", "Mexico",
            "Poland", "Singapore", "South Korea", "Spain", "Sweden",
            "United Kingdom", "USA Miami", "USA Chicago", "USA Los Angeles"
        ]



        for country in countries:
            try:

                if country == "Netherlands":
                    flag_country = "The Netherlands"
                elif country in ["USA Miami", "USA Chicago", "USA Los Angeles"]:
                    flag_country = "The United States"
                elif country == "United Kingdom":
                    flag_country = "The United Kingdom"
                else:
                    flag_country = country



                pil_img = fp.get_flag_img(flag_country)

                byte_array = QByteArray()
                buffer = QBuffer(byte_array)
                buffer.open(QIODevice.WriteOnly)
                pil_img.save(buffer, 'PNG')
                pixmap = QPixmap()
                pixmap.loadFromData(byte_array)

                scaled_pixmap = pixmap.scaled(desired_icon_size, desired_icon_size,
                                              Qt.KeepAspectRatio, Qt.SmoothTransformation)

                x = (desired_icon_size - scaled_pixmap.width()) / 2
                y = (desired_icon_size - scaled_pixmap.height()) / 2

                circle_pixmap = QPixmap(desired_icon_size, desired_icon_size)
                circle_pixmap.fill(Qt.transparent)

                painter = QPainter(circle_pixmap)
                painter.setRenderHint(QPainter.Antialiasing)

                clip_path = QPainterPath()
                clip_path.addEllipse(0, 0, desired_icon_size, desired_icon_size)
                painter.setClipPath(clip_path)

                painter.drawPixmap(x, y, scaled_pixmap)
                painter.end()

                icon = QIcon(circle_pixmap)
                item = QListWidgetItem(icon, country)
                item.setFont(QFont("Arial", 12, QFont.Bold))
                self.countryList.addItem(item)
            except Exception as e:
                print(f"Error processing {country}: {e}")

        self.countryList.setStyleSheet("""
            QListWidget {
                background-color: #262626; /* Dark background */
                border-radius: 20px;
                padding: 20px; /* Adjusted padding for consistency */
                border: 1px solid #333; /* Subtle border */
                color: white; /* Text color */
                font-size: 14px;
                outline: none; /* Removes the dotted border around selected item */
            }
            QListWidget::item {
                border-bottom: 2px solid #707070; /* Darker gray border for separation */
                margin-left: 2px; /* Slight margin for visual separation from the edge */
                padding: 5px; /* Padding for the item, adjusted for visual consistency */
                color: #DDDDDD; /* Default item text color for better contrast */
            }
            QListWidget::item:selected, QListWidget::item:selected:active {
                border-left: 4px solid #4a64ff; /* Vibrant left border for selected item */
                background-color: transparent; /* Keeping the background unchanged */
                color: white; /* Bright text color for selected item */
                margin-left: 0px; /* Align the border with the list edge */
                padding-left: 6px; /* Adjust padding to compensate for the left border */
            }
            QListWidget::item:hover {
                background-color: #3a60cf; /* Lighter blue hover effect */
                color: #FFFFFF; /* Hover makes text brighter */
            }

        """)

        self.mainContentLayout.addWidget(self.countryList)
        self.countryList.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOn)
        self.countryList.verticalScrollBar().setStyleSheet("""
            QScrollBar:vertical {
                border: none;
                background-color: #262626; /* Adjusted to a more subtle background color */
                width: 8px; /* Slightly thinner for a sleeker look */
                margin: 10px 0 10px 0;
                border-radius: 4px;
            }
            QScrollBar::handle:vertical {
                background-color: #4a64ff; /* Vibrant color for better visibility */
                min-height: 60px;
                border-radius: 4px;
                border: 2px solid #2a2d34; /* Border to distinguish the handle from the track */
            }
            QScrollBar::handle:vertical:hover {
                background-color: #262626; /* Lighter shade on hover for interactivity */
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0px; /* Removing the up and down buttons for a cleaner look */
            }
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
                background: none;
            }
        """)

        faq_questions_answers = [
            ("Q: What is Full VPN?", "A: It functions as a normal vpn for privacy and routes all traffic."),
            ("Q: What is Reset button for?", "A: You only need to use that when switching from Full VPN to DNS"),
        ]
        self.faqScrollArea = QScrollArea()
        self.faqContent = QWidget()
        self.faqLayout = QGridLayout(self.faqContent)

        faqBubbleStyle = """
        QLabel {
            background-color: #2a2d34; /* Lighter gray for the bubble background */
            color: #FFFFFF;
            border-radius: 10px;
            padding: 15px;
            margin: 5px;
            border-bottom: 3px solid #4a64ff; /* Blue line under each bubble */
        }
        """

        faqScrollAreaStyle = """
        QScrollBar:vertical {
            border: none;
            background-color: transparent; /* Making the scrollbar background transparent */
            width: 8px; /* Slightly thinner for a sleeker look */
            margin: 10px 0 10px 0;
            border-radius: 4px;
        }
        QScrollBar::handle:vertical {
            background-color: #4a64ff; /* Vibrant color for better visibility */
            min-height: 60px;
            border-radius: 4px;
            border: 2px solid #2a2d34; /* Border to distinguish the handle from the track */
        }
        QScrollBar::handle:vertical:hover {
            background-color: #262626; /* Lighter shade on hover for interactivity */
        }
        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
            height: 0px; /* Removing the up and down buttons for a cleaner look */
        }
        QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
            background: none; /* Ensure no background for the scroll action area */
        }
        """

        self.faqScrollArea.setStyleSheet(faqScrollAreaStyle)

        for i, (question, answer) in enumerate(faq_questions_answers):
            faqBubble = QLabel(f"{question}\n{answer}")
            faqBubble.setStyleSheet(faqBubbleStyle)
            faqBubble.setWordWrap(True)
            row = i // 2
            col = i % 2
            self.faqLayout.addWidget(faqBubble, row, col)

        self.faqScrollArea.setWidget(self.faqContent)
        self.faqScrollArea.setMaximumHeight(400)
        self.faqScrollArea.setMaximumWidth(400)
        faqContentAndAreaStyle = """
        QWidget, QScrollArea {
            background-color: transparent; /* Dark gray background */
            border: transparent; /* Transparent border */
        }
        """
        self.faqContent.setStyleSheet(faqContentAndAreaStyle)
        self.faqScrollArea.setStyleSheet(faqScrollAreaStyle + faqContentAndAreaStyle)
        self.faqScrollArea.setWidgetResizable(True)
        self.faqScrollArea.setVisible(False)

        self.mainContentLayout.addWidget(self.faqScrollArea)

        self.mainContentLayout.addWidget(self.faqScrollArea)


        titleBarWidget = QWidget(self)
        titleBarWidget.setObjectName("titleBarWidget")
        titleBarLayout = QHBoxLayout(titleBarWidget)
        titleBarLayout.setContentsMargins(0, 0, 0, 0)
        titleBarWidget.setMaximumHeight(100)
        titleBarLayout.addStretch(1)
        self.themeToggleButton = QPushButton()
        self.themeToggleButton.setFixedSize(40, 40)
        self.themeToggleButton.setCursor(QCursor(Qt.PointingHandCursor))
        self.themeToggleButton.setStyleSheet("QPushButton { background-color: transparent; border: transparent; }")
        self.themeToggleButton.setIcon(QIcon(QPixmap(self.get_image_path('light5.png'))))

        self.themeButtonTooltip = TooltipLabel(self)
        self.themeButtonTooltip.setText("Switch to Light Mode")
        self.themeToggleButton.installEventFilter(self)

        self.themeToggleButton.clicked.connect(self.toggle_theme)
        titleBarLayout.addWidget(self.themeToggleButton)

        titleBarLayout.addSpacing(290)

        self.minimizeButton = QPushButton("−", self)
        self.minimizeButton.setFont(QFont("Arial", 20))
        self.minimizeButton.setFixedSize(30, 30)
        self.minimizeButton.setStyleSheet("QPushButton { background-color: transparent; color: white; border: none; }")
        self.minimizeButton.setCursor(QCursor(Qt.PointingHandCursor))
        self.minimizeButton.clicked.connect(self.showMinimized)

        self.closeButton = QPushButton("×", self)
        self.closeButton.setFont(QFont("Arial", 20))
        self.closeButton.setFixedSize(30, 30)
        self.closeButton.setStyleSheet("QPushButton { background-color: transparent; color: white; border: none; }")
        self.closeButton.setCursor(QCursor(Qt.PointingHandCursor))
        self.closeButton.clicked.connect(self.close)

        titleBarLayout.addWidget(self.minimizeButton)
        titleBarLayout.addWidget(self.closeButton)

        titleBarWidget.setLayout(titleBarLayout)
        titleBarWidget.setFixedHeight(30)
        titleBarWidget.resize(self.width(), 30)

        def resizeEvent(self, event):
            super(FramelessWindow, self).resizeEvent(event)
            titleBarWidget.resize(self.width(), 30)
        self.oldPos = self.pos()
        self.menuItems[0].click()

    def eventFilter(self, watched, event):
        if watched == self.menuItems[-1]:
            if event.type() == QEvent.Enter:
                button_rect = watched.geometry()
                tooltip_width = self.resetButtonTooltip.sizeHint().width()
                tooltip_height = self.resetButtonTooltip.sizeHint().height()
                tooltip_x = button_rect.x() + (button_rect.width() - tooltip_width) // 2
                tooltip_y = button_rect.y() + button_rect.height() + 10  # 10 pixels below the button
                self.resetButtonTooltip.setGeometry(tooltip_x, tooltip_y, tooltip_width, tooltip_height)
                self.resetButtonTooltip.setVisible(True)
            elif event.type() == QEvent.Leave:
                self.resetButtonTooltip.setVisible(False)

        elif watched == self.themeToggleButton:
            if event.type() == QEvent.Enter:
                tooltip_text = "Switch to Dark Mode" if self.theme == "light" else "Switch to Light Mode"
                self.themeButtonTooltip.setText(tooltip_text)


                specific_x = 240
                specific_y = 40

                self.themeButtonTooltip.move(specific_x, specific_y)
                self.themeButtonTooltip.show()
                return True
            elif event.type() == QEvent.Leave:
                self.themeButtonTooltip.hide()
                return True

        return super(FramelessWindow, self).eventFilter(watched, event)

    def get_base_path(self):
        if getattr(sys, 'frozen', False):
            return Path(sys._MEIPASS)
        return Path(__file__).resolve().parents[2]  # <-- project root

    def get_image_path(self, image_name):
        return str(self.base_path / "ss" / image_name)

    def modify_firewall(self,server_ip, username, password, action, client_ip):
        """
        Connect to the server via SSH and modify firewall rules with a specific comment for easy management.

        :param server_ip: IP address of the Ubuntu server
        :param username: SSH username
        :param password: SSH password
        :param action: 'allow' to add an IP, 'deny' to remove an IP
        :param client_ip: IP address to allow or deny
        """
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

        try:
            client.connect(server_ip, username=username, password=password)

            if action == 'allow':
                command = f"sudo iptables -I INPUT -s {client_ip} -p udp --dport 53 -j ACCEPT -m comment --comment 'dynamic_ip'"
                command += f"; sudo iptables -I INPUT -s {client_ip} -p tcp --dport 53 -j ACCEPT -m comment --comment 'dynamic_ip'"
            elif action == 'deny':
                command = f"sudo iptables -D INPUT -s {client_ip} -p udp --dport 53 -j ACCEPT -m comment --comment 'dynamic_ip'"
                command += f"; sudo iptables -D INPUT -s {client_ip} -p tcp --dport 53 -j ACCEPT -m comment --comment 'dynamic_ip'"
            else:
                return "Invalid action specified"

            stdin, stdout, stderr = client.exec_command(command)
            print("Command executed:", command)
            print("Output:", stdout.read().decode())
            print("Errors:", stderr.read().decode())

            client.exec_command("sudo iptables-save > /etc/iptables/rules.v4")

        finally:
            client.close()

    def closeEvent(self, event):
        try:
            subprocess.call("taskkill /F /IM openvpn.exe", shell=True)
            print("VPN process terminated successfully.")
        except Exception as e:
            print("Failed to terminate VPN process:", e)
        super().closeEvent(event)



    def filter_countries(self, search_text):
        for index in range(self.countryList.count()):
            item = self.countryList.item(index)
            item.setHidden(search_text.lower() not in item.text().lower())

    def switch_content(self, content_name):
        self.faqScrollArea.setVisible(False)
        self.powerButton.setVisible(False)
        self.searchBox.setVisible(False)
        self.countryList.setVisible(False)
        self.consoleVpnSetupRadio.setVisible(False)

        if content_name == "FAQ":
            self.faqScrollArea.setVisible(True)

        elif content_name == "Full VPN":
            self.powerButton.setVisible(True)
            self.searchBox.setVisible(True)
            self.countryList.setVisible(True)

    def toggle_theme(self):
        if self.theme == "dark":
            self.theme = "light"
            self.themeToggleButton.setIcon(QIcon(QPixmap(self.get_image_path('light8.png'))))
            self.apply_light_theme_styles()
        else:
            self.theme = "dark"
            self.themeToggleButton.setIcon(QIcon(QPixmap(self.get_image_path('light9.png'))))
            self.apply_dark_theme_styles()


    def update_button_selection(self, selected_button):
        for btn in self.menuItems:
            btn.setChecked(btn == selected_button)
            if btn == selected_button:
                self.switch_content(selected_button.text().strip())


    def apply_light_theme_styles(self):

        self.consoleVpnSetupRadio.setStyleSheet("""
            QRadioButton {
                color: black;
                font-size: 16px;
                background-color: transparent;
            }
            QRadioButton::indicator {
                width: 20px;
                height: 20px;
                border: 2px solid #4a64ff;
            }
            QRadioButton::indicator:checked {
                background-color: #4a64ff;
            }
        """)
        self.footer.setStyleSheet("""
            QLabel {
                color: #000000; /* Black text for visibility in light mode */
                padding: 10px;
                font-size: 11px;
                border: none; /* Removes all borders */
                border-top: 1px solid #CCCCCC; /* Apply only top border */
            }
        """)
        self.centralWidget.setStyleSheet(
            "QWidget#centralWidget { background-color: #FFFFFF; border-radius: 15px; }"
        )
        self.setStyleSheet("""
            QPushButton { background-color: #E0E0E0; border: 1px solid #AEAEAE; color: #000000; }
            QLineEdit { background-color: #FFFFFF; color: #000000; border: 1px solid #AEAEAE; border-radius: 20px; }
            QListWidget { background-color: #FFFFFF; color: #000000; border-radius: 20px; }
        """)
        self.sidebar.setStyleSheet("""
            background-color: #FFFFFF; /* Lighter gray background for the sidebar */
            color: #000000; /* Black text for visibility */
            border-right: 1px solid #CCCCCC; /* Solid light gray right border */
            padding-right: 1px; /* Offset for right border, to prevent it from being overlapped */
            border-radius: 10px

        """)
        self.consoleVpnSetupRadio.setStyleSheet("""
            QRadioButton {
                color: black;
                font-size: 10px;
                background-color: transparent;
            }
            QRadioButton::indicator {
                width: 10px;
                height: 10px;
                border: 2px solid #3265E4;

            }
            QRadioButton::indicator:checked {
                background-color: #4a64ff;
                border-radius: 15px;  # Ensure the colored fill is also round

            }
        """)

        self.commonStyle = """
            QPushButton { 
                color: #000000; 
                padding: 15px; 
                text-align: left; 
                font-size: 16px; 
                background-color: transparent; /* Make sure buttons don't overlap the sidebar's border */
                border: none; /* No borders on buttons */
            }
            QPushButton:hover { 
                background-color: #D0D0D0; /* Slightly darker on hover */
            }
            QPushButton:checked {
                background-color: #E0E0E0;  /* Light background on selected */
                background-image: linear-gradient(to right, transparent 90%, #3265E4 90%, #3265E4 100%); /* Creates a vertical line that matches the border */
                border-right: 4px solid #3265E4; /* Solid right border */
                border-top-right-radius: -4px; /* Consistent with rounded corners if needed */
                border-bottom-right-radius: -4px; /* Consistent with rounded corners if needed */
            }
        """


        full_vpn_icon = QIcon(self.get_image_path('home.png'))

        faq_icon = QIcon(self.get_image_path('home.png'))

        for btn in self.menuItems:
            if "Full VPN" in btn.text():
                btn.setIcon(full_vpn_icon)
            elif "FAQ" in btn.text():
                btn.setIcon(faq_icon)
        for btn in self.menuItems[:-1]:
            btn.setStyleSheet(self.commonStyle)
        self.countryList.verticalScrollBar().setStyleSheet("""
            QScrollBar:vertical {
                border: none;
                background-color: #FFFFFF; /* Adjusted to a more subtle background color */
                width: 8px; /* Slightly thinner for a sleeker look */
                margin: 10px 0 10px 0;
                border-radius: 4px;
            }
            QScrollBar::handle:vertical {
                background-color: #4a64ff; /* Vibrant color for better visibility */
                min-height: 60px;
                border-radius: 4px;
                border: 2px solid #2a2d34; /* Border to distinguish the handle from the track */
            }
            QScrollBar::handle:vertical:hover {
                background-color: #262626; /* Lighter shade on hover for interactivity */
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0px; /* Removing the up and down buttons for a cleaner look */
            }
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
                background: none;
            }
        """)


        self.countryList.setStyleSheet("""
            QListWidget {
                background-color: #FFFFFF;
                border-radius: 20px;
                padding: 20px;
                border: 1px solid #333;
                color: black;
                font-size: 14px;
                outline: none;
            }
            QListWidget::item {
                border-bottom: 2px solid #707070;
                margin-left: 2px;
                padding: 5px;
                color: #DDDDDD;
            }
            QListWidget::item:selected, QListWidget::item:selected:active {
                border-left: 4px solid #4a64ff;
                background-color: transparent;
                color: black;
                margin-left: 0px;
                padding-left: 6px;
            }

        """)

        self.closeButton.setStyleSheet("QPushButton { background-color: transparent; color: gray; border: none; }")

        self.footer.setStyleSheet("color: rgba(128, 128, 128, 255); margin-top: 5px; padding: 10px; font-size: 11px;")
        search_image_path1 = self.get_image_path('search1.png').replace('\\', '/')
        print("Formatted Image Path:", search_image_path1)

        self.searchBox.setStyleSheet(f"""
            QLineEdit {{
                padding-left: 33px; /* Adjusted to move text further to the right */
                padding-top: 10px;
                padding-bottom: 10px;
                border: 1px solid #333;
                border-radius: 20px;
                background-color: #FFFFFF;
                color: gray;
                font-size: 14px;
                background-image: url({search_image_path1});
                background-repeat: no-repeat;
                background-position: center left; /* Keeps the icon on the left */
            }}
        """)

    def apply_dark_theme_styles(self):

        self.consoleVpnSetupRadio.setStyleSheet("""
            QRadioButton {
                color: white;
                font-size: 10px;
                background-color: transparent;
            }
            QRadioButton::indicator {
                width: 10px;
                height: 10px;
                border: 2px solid #3265E4;

            }
            QRadioButton::indicator:checked {
                background-color: #4a64ff;
                border-radius: 15px;  # Ensure the colored fill is also round

            }
        """)
        self.update()


        self.centralWidget.setStyleSheet(
            "QWidget#centralWidget { background-color: #1C1A1A; border-radius: 15px; }"
        )

        self.sidebar.setStyleSheet("background-color: #101010; color: white; border-radius: 10px;")

        commonStyle = """
            QPushButton { color: white; padding: 15px; border: none; text-align: left; font-size: 16px; }
            QPushButton:hover { background-color: #4a64ff; }
            QPushButton:checked {
                border-right: 4px solid #3265E4; 
                background-color: transparent; /* No background color change */
                background-image: linear-gradient(to right, transparent 90%, #3265E4 90%, #3265E4 100%);  /* Creates a vertical line that matches the border */
                border-top-right-radius: -4px;  /* Wraps the border around the top-right corner */
                border-bottom-right-radius: -4px;  /* Wraps the border around the bottom-right corner */
            }
        """

        full_vpn_icon = QIcon(self.get_image_path('home.png'))
        faq_icon = QIcon(self.get_image_path('home.png'))

        for btn in self.menuItems:
            if "Full VPN" in btn.text():
                btn.setIcon(full_vpn_icon)
            elif "FAQ" in btn.text():
                btn.setIcon(faq_icon)
        for btn in self.menuItems[:-1]:
            btn.setStyleSheet(commonStyle)


        resetButton = self.menuItems[-1]
        resetButton.setStyleSheet("""
            QPushButton {
                color: white;
                padding: 5px 25px;
                margin: 5px;
                border: 2px solid #5d1e1e;
                text-align: center;
                font-size: 14px;
                background-color: #5d1e1e;
                border-radius: 7px;
            }
        """)
        self.minimizeButton.setStyleSheet("QPushButton { background-color: transparent; color: white; border: none; }")

        self.closeButton.setStyleSheet("QPushButton { background-color: transparent; color: white; border: none; }")
        search_image_path1 = self.get_image_path('search.png').replace('\\', '/')
        print("Formatted Image Path:", search_image_path1)

        self.searchBox.setStyleSheet(f"""
            QLineEdit {{
                padding-left: 33px;
                padding-top: 10px;
                padding-bottom: 10px;
                border: 1px solid #333;
                border-radius: 20px;
                background-color: #262626;
                color: white;
                font-size: 14px;
                background-image: url({search_image_path1});
                background-repeat: no-repeat;
                background-position: center left;
            }}
        """)

        self.countryList.verticalScrollBar().setStyleSheet("""
            QScrollBar:vertical {
                border: none;
                background-color: #262626; /* Adjusted to a more subtle background color */
                width: 8px; /* Slightly thinner for a sleeker look */
                margin: 10px 0 10px 0;
                border-radius: 4px;
            }
            QScrollBar::handle:vertical {
                background-color: #4a64ff; /* Vibrant color for better visibility */
                min-height: 60px;
                border-radius: 4px;
                border: 2px solid #2a2d34; /* Border to distinguish the handle from the track */
            }
            QScrollBar::handle:vertical:hover {
                background-color: #262626; /* Lighter shade on hover for interactivity */
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0px; /* Removing the up and down buttons for a cleaner look */
            }
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
                background: none;
            }
        """)
        self.countryList.setStyleSheet("""
            QListWidget {
                background-color: #262626;
                border-radius: 20px;
                padding: 20px;
                border: 1px solid #333;
                color: white;
                font-size: 14px;
                outline: none;
            }
            QListWidget::item {
                border-bottom: 2px solid #707070;
                margin-left: 2px;
                padding: 5px;
                color: #DDDDDD;
            }
            QListWidget::item:selected, QListWidget::item:selected:active {
                border-left: 4px solid #4a64ff;
                background-color: transparent;
                color: white;
                margin-left: 0px;
                padding-left: 6px;
            }
            QListWidget::item:hover {
                background-color: #3a60cf;
                color: #FFFFFF;
            }
        """)

        self.update()

    def handleConsoleVpnSetup(self, checked):
        print(f"Radio button checked state changed: {checked}")
        if checked:
            QApplication.processEvents()
            msgBox = QMessageBox(self)
            msgBox.setWindowTitle("Confirm Setup")
            msgBox.setText("Are you sure you want to set up console VPN?")
            msgBox.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
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
            msgBox.setWindowFlags(msgBox.windowFlags() | QtCore.Qt.FramelessWindowHint)
            msgBox.move(self.geometry().center() - msgBox.rect().center())
            result = msgBox.exec_()

            print(f"Message box result: {result}")
            if result == QMessageBox.Yes:
                print("User confirmed Yes")
                self.setupConsoleVpn()
            else:
                print("User cancelled the setup")
                self.consoleVpnSetupRadio.setChecked(False)
    def setupConsoleVpn(self):
        print("Setting up console VPN...")

        countryDialog = QInputDialog(self)
        countryDialog.setWindowTitle("Select Country")
        countryDialog.setLabelText("Choose a country:")
        countryDialog.setComboBoxItems(["Australia", "Brazil", "India", "Israel", "Singapore"])
        countryDialog.setModal(True)

        countryDialog.setStyleSheet("""
            QInputDialog QLabel {  /* Styling labels specifically in QInputDialog */
                color: white;
                font-size: 11px; /* Slightly larger font for better readability */
            }
            QInputDialog {
                color: white;
                background-color: #2a2d34; /* Dark gray background */
                font-size: 11px; /* Uniform font size for the dialog */
                border: 1px solid #707070;
                border-radius: 5px;
            }
            QComboBox, QComboBox QAbstractItemView {
                background-color: #3a3f4b; /* Gray background for the dropdown to match the combo box */
                color: white;
                border: 1px solid #707070; /* Subtle border */
                border-radius: 5px;
                selection-background-color: #4a4f5b; /* Darker gray for selected items */
                selection-color: white;
            }
            QComboBox::drop-down {
                subcontrol-origin: padding;
                subcontrol-position: top right;
                width: 20px; /* Proper width for the arrow button */
                border-left: 1px solid #707070; /* Subtle left border for the drop-down arrow */
                border-radius: 5px; /* Rounded corners */
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
            /* Additional focus style removal */
            QComboBox:focus, QPushButton:focus, QLineEdit:focus, QInputDialog:focus, QComboBox QAbstractItemView:focus {
                outline: none;
                border-style: none; /* Remove any border style set by focus */
            }
            /* Make sure to remove the focus outline on all focusable elements */
            *:focus {
                outline: none;
                border-style: none; /* Strongly insist on no border styles on focus */
            }
        """)
        countryDialog.setWindowFlags(QtCore.Qt.FramelessWindowHint | QtCore.Qt.WindowStaysOnTopHint)

        ok = countryDialog.exec_()
        country = countryDialog.textValue()
        print(f"Dialog closed with OK status: {ok}, Selected country: {countryDialog.textValue()}")

        if ok and country:
            print("Proceeding with selected country setup...")

            selected_ip = ips.get(country, "No IP Found")

            dnsBox = QMessageBox()
            dnsBox.setWindowTitle("DNS Setup")
            dnsBox.setText(f"Please set primary server: {selected_ip} \n\nin console settings and click OK when done.")

            dnsBox.setStyleSheet("""
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
            dnsBox.setWindowFlags(QtCore.Qt.FramelessWindowHint | QtCore.Qt.WindowStaysOnTopHint)

            dnsBox.show()
            QApplication.processEvents()

            mainCenter = self.frameGeometry().center()
            dialogCenter = dnsBox.frameGeometry()
            dialogCenter.moveCenter(mainCenter)
            dnsBox.move(dialogCenter.topLeft())

            dnsBox.exec_()

            ipDialog = QInputDialog(self)
            ipDialog.setWindowTitle("Enter IP")
            ipDialog.setLabelText("Enter IP to authorize access")
            ipDialog.setStyleSheet("""
                                QInputDialog {
                                    color: white;
                                    background-color: #2a2d34; /* Dark gray */
                                    font-size: 10px;
                                    border: 1px solid #707070;
                                    border-radius: 5px;
                                }
                                QInputDialog QLineEdit {  /* Targeting QLineEdit specifically in QInputDialog */
                                    background-color: #3a3f4b; /* Light gray */
                                    color: white; /* Explicitly setting color again */
                                    border: 1px solid #555;
                                    padding: 4px;
                                    border-radius: 2px;
                                }
                                QInputDialog QLabel {  /* Targeting QLabel specifically in QInputDialog */
                                    color: white; /* Set text color for the label */
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

            ipDialog.setWindowFlags(QtCore.Qt.FramelessWindowHint | QtCore.Qt.WindowStaysOnTopHint)


            while True:
                ipDialog = QInputDialog(self)
                ipDialog.setWindowTitle("Enter IP")
                ipDialog.setLabelText("Enter IP to authorize access")
                ipDialog.setStyleSheet("""
                                    QInputDialog {
                                        color: white;
                                        background-color: #2a2d34; /* Dark gray */
                                        font-size: 10px;
                                        border: 1px solid #707070;
                                        border-radius: 5px;
                                    }
                                    QInputDialog QLineEdit {  /* Targeting QLineEdit specifically in QInputDialog */
                                        background-color: #3a3f4b; /* Light gray */
                                        color: white; /* Explicitly setting color again */
                                        border: 1px solid #555;
                                        padding: 4px;
                                        border-radius: 2px;
                                    }
                                    QInputDialog QLabel {  /* Targeting QLabel specifically in QInputDialog */
                                        color: white; /* Set text color for the label */
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
                style = """
                    QMessageBox {
                        color: white;
                        background-color: #2a2d34;
                        font-size: 12px;
                        border: 1px solid #707070;
                        border-radius: 5px;
                    }
                    QPushButton {
                        color: white;
                        background-color: #3a3f4b;
                        border: none;
                        padding: 6px;
                        border-radius: 2px;
                        font-size: 10px;
                    }
                    QPushButton:hover {
                        background-color: #4a4f5b;
                    }
                """

                ipDialog.setWindowFlags(QtCore.Qt.FramelessWindowHint | QtCore.Qt.WindowStaysOnTopHint)
                ok = ipDialog.exec_()
                ip = ipDialog.textValue()
                if ok:
                    if ip.strip():
                        match country:
                            case "Australia":
                                print("Aus selected")
                            case "Brazil":
                                print("Brazil selected")
                            case "India":
                                print("India selected")
                            case "Israel":
                                print("Israel selected")
                            case "Singapore":
                                print("Sing selected")

                        self.showMessage("Activation", "Console VPN is activated.", style)
                        break
                    else:
                        self.showMessage("Invalid Input", "Please enter a valid IP address.", style,
                                         QMessageBox.Warning)
                else:
                    self.showMessage("Cancelled", "Connection cancelled.", style, QMessageBox.Warning)
                    break

    def showMessage(self, title, message, style, icon=QMessageBox.NoIcon):
        msgBox = QMessageBox(self)
        msgBox.setWindowTitle(title)
        msgBox.setText(message)
        msgBox.setIcon(icon)
        msgBox.setStyleSheet(style + """
            QMessageBox QLabel {
                color: white;  /* Explicitly setting text color for labels */
            }
        """)
        msgBox.setWindowFlags(msgBox.windowFlags() | Qt.FramelessWindowHint)

        x = self.x() + (self.width() - msgBox.width()) // 2
        y = self.y() + (self.height() - msgBox.height()) // 2
        msgBox.move(x, y)

        msgBox.exec_()

    def mousePressEvent(self, event):
        self.oldPos = event.globalPos()

    def mouseMoveEvent(self, event):
        delta = QPoint(event.globalPos() - self.oldPos)
        self.move(self.x() + delta.x(), self.y() + delta.y())
        self.oldPos = event.globalPos()

    def resetVpnConnection(self):
        try:
            subprocess.call("route -f", shell=True)
        except Exception as e:
            print(str(e))


    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        path = QPainterPath()
        path.addRoundedRect(self.rect(), 15, 15)
        painter.fillPath(path, self.centralWidget.palette().brush(self.centralWidget.backgroundRole()))

