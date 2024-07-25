import sys
import os
import threading
import sqlite3
import secrets
import logging
from PyQt5.QtWidgets import (QApplication, QMainWindow, QVBoxLayout, QHBoxLayout,
                             QWidget, QTextEdit, QPushButton, QLabel, QLineEdit, QMessageBox, QGridLayout)
from PyQt5.QtCore import QTimer, Qt
import hashlib
import asyncio
import database
from server import main as server_main

# Logginställningar
logging.basicConfig(filename='server.log', level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class ServerGUI(QMainWindow):
    def __init__(self):
        super().__init__()
        self.initUI()
        self.check_and_create_admin()
        self.check_and_create_privilege_key()
        self.start_server()

    def initUI(self):
        self.setWindowTitle('Server GUI')
        self.setGeometry(100, 100, 600, 400)

        mainLayout = QVBoxLayout()

        # Timer för att uppdatera loggen
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_log_viewer)
        self.timer.start(1000)  # Uppdatera loggen varje sekund

        # Layout för administratörsinloggning och token
        adminLayout = QGridLayout()
        self.adminUserLabel = QLabel('Login name:')
        self.adminUserInput = QLineEdit(self)
        self.adminUserInput.setReadOnly(True)
        self.adminPassLabel = QLabel('Password:')
        self.adminPassInput = QLineEdit(self)
        self.adminPassInput.setEchoMode(QLineEdit.Password)
        self.adminPassInput.setReadOnly(True)

        self.tokenLabel = QLabel('Server Admin Token:')
        self.tokenDisplay = QLineEdit(self)
        self.tokenDisplay.setReadOnly(True)

        adminLayout.addWidget(self.adminUserLabel, 0, 0)
        adminLayout.addWidget(self.adminUserInput, 0, 1)
        adminLayout.addWidget(self.adminPassLabel, 1, 0)
        adminLayout.addWidget(self.adminPassInput, 1, 1)
        adminLayout.addWidget(self.tokenLabel, 2, 0)
        adminLayout.addWidget(self.tokenDisplay, 2, 1)

        mainLayout.addLayout(adminLayout)

        # TextEdit för att visa loggfilen
        self.logViewer = QTextEdit(self)
        self.logViewer.setReadOnly(True)
        mainLayout.addWidget(self.logViewer)

        # Central widget
        centralWidget = QWidget()
        centralWidget.setLayout(mainLayout)
        self.setCentralWidget(centralWidget)

        self.show()

    def update_log_viewer(self):
        try:
            with open('server.log', 'r') as file:
                lines = file.readlines()
                self.logViewer.setPlainText("".join(lines))
                self.logViewer.verticalScrollBar().setValue(self.logViewer.verticalScrollBar().maximum())
        except Exception as e:
            self.logViewer.setPlainText(f"Error reading log file: {str(e)}")

    def check_and_create_admin(self):
        conn = sqlite3.connect('DB/pyspeak.db')
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM users WHERE is_superadmin=1")
        admin = cursor.fetchone()

        if not admin:
            admin_username = 'admin'
            admin_password = secrets.token_urlsafe(16)
            hashed_password = hashlib.sha256(admin_password.encode()).hexdigest()
            cursor.execute("INSERT INTO users (uid, username, password, role, is_superadmin) VALUES (?, ?, ?, ?, ?)",
                           (secrets.token_hex(16), admin_username, hashed_password, 'superadmin', True))
            conn.commit()
            self.adminUserInput.setText(admin_username)
            self.adminPassInput.setText(admin_password)
        else:
            self.adminUserInput.setText(admin[2])
            self.adminPassInput.setText(admin[3])  # Mask the existing password

        conn.close()

    def check_and_create_privilege_key(self):
        conn = sqlite3.connect('DB/pyspeak.db')
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM server_admin_token")
        token = cursor.fetchone()

        if not token:
            token_key = secrets.token_urlsafe(32)
            cursor.execute("INSERT INTO server_admin_token (token) VALUES (?)", (token_key,))
            conn.commit()
            self.tokenDisplay.setText(token_key)
        else:
            self.tokenDisplay.setText(token[1])

        conn.close()

    def show_token(self):
        self.tokenDisplay.setEchoMode(QLineEdit.Normal)

    def start_server(self):
        self.server_thread = threading.Thread(target=self.run_server)
        self.server_thread.daemon = True
        self.server_thread.start()

    def run_server(self):
        asyncio.run(server_main())

if __name__ == '__main__':
    database.init_db('DB/pyspeak.db')
    app = QApplication(sys.argv)
    ex = ServerGUI()
    sys.exit(app.exec_())
