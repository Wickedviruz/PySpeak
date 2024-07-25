import asyncio
import json
import threading
import pyaudio
import websockets
import webbrowser
import sqlite3
import uuid
from datetime import datetime, timedelta
from audio import AudioThread

#PyQt imports
from PyQt5.QtMultimedia import QMediaPlayer,QMediaContent
from PyQt5.QtWidgets import QMainWindow, QVBoxLayout, QHBoxLayout, QWidget, QListWidget, QListWidgetItem, QPushButton, QTextEdit, QLineEdit, QAction, QSplitter, QDialog
from PyQt5.QtGui import QIcon
from PyQt5.QtCore import Qt, QUrl

#Local imports
from dialogs import (
    ConnectDialog,
    ManageBookmarksDialog, 
    ConnectionInfoDialog, 
    SettingsDialog, 
    PasswordDialog, 
    ChangelogDialog, 
    AboutPySpeak, 
    AboutPyQT, 
    IdentitiesDialog, 
    UsePrivilegeKey,
    PyLicense)
from settings import load_bookmarks, save_bookmarks, load_default_identity, db_file

class VoiceChatClient(QMainWindow):
    def __init__(self):
        super().__init__()
        self.initUI()
        self.websocket = None
        self.server_name = None
        self.current_username = None
        self.connection_info_dialog = None
        self.connection_start_time = None 
        self.ping = 0
        self.load_bookmarks_from_db()
        self.refresh_bookmarks_menu()
        self.current_identity = load_default_identity()
        self.changelog_file = 'changelog.txt'
        self.PyLicense = 'assets/Pylicense.ini'
        self.pyqt5_infoFile = 'assets/pyqt5_info.ini'
        self.pySpeak_infoFile = 'assets/pySpeak_info.ini'

        self.pyaudio_instance = pyaudio.PyAudio()
        self.stream = None
        self.mic_muted = False
        self.speaker_muted = False
        self.audio_stream = None
        self.audio_thread = None
        self.lock = threading.Lock()

        self.media_player = QMediaPlayer()

        # Initialize statistics
        self.statistics = {
            "total": {"packets_transferred": 0, "bytes_transferred": 0, "bandwidth_last_second": 0, "bandwidth_last_minute": 0, "file_transfer_bandwidth": 0},
            "speech": {"packets_transferred": 0, "bytes_transferred": 0, "bandwidth_last_second": 0, "bandwidth_last_minute": 0},
            "keep_alive": {"packets_transferred": 0, "bytes_transferred": 0, "bandwidth_last_second": 0, "bandwidth_last_minute": 0},
            "control": {"packets_transferred": 0, "bytes_transferred": 0, "bandwidth_last_second": 0, "bandwidth_last_minute": 0},
            "quota": {"bytes_transferred": 0, "bandwidth_last_second": 0, "bandwidth_last_minute": 0},
        }

    def initUI(self):
        self.setWindowTitle('PySpeak Client')
        self.setWindowIcon(QIcon('assets/img/icon.png'))
        self.setGeometry(100, 100, 500, 600)

        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        main_layout = QVBoxLayout()
        central_widget.setLayout(main_layout)

        menubar = self.menuBar()

        connectionsMenu = menubar.addMenu('Connections')
        self.bookmarksMenu = self.menuBar().addMenu('Bookmarks')
        selfMenu = menubar.addMenu('Self')
        permissionsMenu = menubar.addMenu('Permissions')
        toolsMenu = menubar.addMenu('Tools')
        helpMenu = menubar.addMenu('Help')

        connectAction = QAction(QIcon('assets/img/default_colored_2014/connect.svg'), 'Connect', self)
        connectAction.triggered.connect(self.show_connect_dialog)
        connectionsMenu.addAction(connectAction)

        disconnectAction = QAction(QIcon('assets/img/default_colored_2014/disconnect.svg'), 'Disconnect', self)
        disconnectAction.triggered.connect(lambda: asyncio.ensure_future(self.disconnect_from_server()))
        connectionsMenu.addAction(disconnectAction)
        connectionsMenu.addSeparator()

        quitAction = QAction(QIcon('assets/img/default_colored_2014/close_button.svg'), 'Quit', self)
        quitAction.triggered.connect(self.close)
        connectionsMenu.addAction(quitAction)

        captureProfileAction = QAction(QIcon('assets/img/default_colored_2014/close_button.svg'),'Capture profile', self)
        selfMenu.addAction(captureProfileAction)

        playbackProfileAction = QAction(QIcon('assets/img/default_colored_2014/close_button.svg'),'Playback profile', self)
        selfMenu.addAction(playbackProfileAction)

        soundPackAction = QAction(QIcon('assets/img/default_colored_2014/sound-pack.svg'),'Sound pack', self)
        selfMenu.addAction(soundPackAction)
        selfMenu.addSeparator()

        muteMicrophoneAction = QAction(QIcon('assets/img/default_colored_2014/close_button.svg'),'Mute microphone', self)
        selfMenu.addAction(muteMicrophoneAction)

        muteSpeakerAction = QAction(QIcon('assets/img/default_colored_2014/close_button.svg'),'Mute speakers/headphones', self)
        selfMenu.addAction(muteSpeakerAction)
        selfMenu.addSeparator()

        connectionInfoAction = QAction(QIcon('assets/img/default_colored_2014/server_log.svg'),'Connection info', self)
        connectionInfoAction.triggered.connect(self.show_connection_info_dialog)
        selfMenu.addAction(connectionInfoAction)

        # Disable the connection info action initially
        connectionInfoAction.setEnabled(False)
        self.connectionInfoAction = connectionInfoAction

        serverGroupsAction = QAction(QIcon('assets/img/default_colored_2014/server_log.svg'),'Server groups', self)
        permissionsMenu.addAction(serverGroupsAction)

        channelGroupsAction = QAction(QIcon('assets/img/default_colored_2014/server_log.svg'),'Channel groups', self)
        permissionsMenu.addAction(channelGroupsAction)
        permissionsMenu.addSeparator()

        privilegeKeyAction = QAction(QIcon('assets/img/default_colored_2014/token.svg'),'Privilege Key', self)
        permissionsMenu.addAction(privilegeKeyAction)

        usePrivilegeKeyAction = QAction(QIcon('assets/img/default_colored_2014/token_use.svg'),'Use Privilege Key', self)
        usePrivilegeKeyAction.triggered.connect(self.show_UsePrivilegeKey_dialog)
        permissionsMenu.addAction(usePrivilegeKeyAction)
        
        identitiesAction = QAction(QIcon('assets/img/default_colored_2014/settings.svg'), 'Identities', self)
        identitiesAction.triggered.connect(self.show_identities_dialog)
        toolsMenu.addAction(identitiesAction)
        toolsMenu.addSeparator()

        settingsAction = QAction(QIcon('assets/img/default_colored_2014/settings.svg'), 'Options', self)
        settingsAction.triggered.connect(self.show_settings_dialog)
        toolsMenu.addAction(settingsAction)

        aboutPySpeakAction = QAction(QIcon('assets/img/default_colored_2014/about.svg'), 'About PySpeak', self)
        aboutPySpeakAction.triggered.connect(self.show_aboutPySpeak_dialog)
        helpMenu.addAction(aboutPySpeakAction)

        aboutPyQtAction = QAction(QIcon('assets/img/default_colored_2014/about.svg'), 'About PyQt', self)
        aboutPyQtAction.triggered.connect(self.show_aboutPyQT_dialog)
        helpMenu.addAction(aboutPyQtAction)
        helpMenu.addSeparator()

        pySpeakWebsiteAction = QAction(QIcon('assets/img/default_colored_2014/weblist.svg'), 'Visit PySpeak website', self)
        pySpeakWebsiteAction.triggered.connect(self.open_website)
        helpMenu.addAction(pySpeakWebsiteAction)
        helpMenu.addSeparator()

        changelogAction = QAction(QIcon('assets/img/default_colored_2014/changelog.svg'), 'View changelog', self)
        changelogAction.triggered.connect(self.show_changelog_dialog)
        helpMenu.addAction(changelogAction)

        licenseAction = QAction(QIcon('assets/img/default_colored_2014/changelog.svg'), 'View license', self)
        licenseAction.triggered.connect(self.show_PyLicense_dialog)
        helpMenu.addAction(licenseAction)

        splitter_top = QSplitter()
        main_layout.addWidget(splitter_top)

        self.roomList = QListWidget()
        self.roomList.itemClicked.connect(self.switch_room)
        splitter_top.addWidget(self.roomList)

        self.userInfo = QListWidget()
        splitter_top.addWidget(self.userInfo)

        splitter_top.setStretchFactor(0, 1)
        splitter_top.setStretchFactor(1, 1)
        splitter_top.setSizes([self.width() // 2, self.width() // 2])

        button_layout = QHBoxLayout()

        self.muteMicButton = QPushButton()
        self.muteMicButton.setCheckable(True)
        self.muteMicButton.setIcon(QIcon('assets/img/default_colored_2014/capture.svg'))
        self.muteMicButton.clicked.connect(self.toggle_mic)

        self.muteSpeakerButton = QPushButton()
        self.muteSpeakerButton.setCheckable(True)
        self.muteSpeakerButton.setIcon(QIcon('assets/img/default_colored_2014/volume.svg'))
        self.muteSpeakerButton.clicked.connect(self.toggle_speaker)

        button_layout.addWidget(self.muteMicButton)
        button_layout.addWidget(self.muteSpeakerButton)
        main_layout.addLayout(button_layout)

        splitter_bottom = QSplitter()
        splitter_bottom.setOrientation(Qt.Vertical)
        main_layout.addWidget(splitter_bottom)

        splitter_bottom.addWidget(splitter_top)

        self.console = QTextEdit()
        self.console.setReadOnly(True)
        splitter_bottom.addWidget(self.console)

        message_input_widget = QWidget()
        message_input_layout = QHBoxLayout()
        message_input_widget.setLayout(message_input_layout)
        self.messageInput = QLineEdit()
        message_input_layout.addWidget(self.messageInput)
        self.sendButton = QPushButton('Send')
        self.sendButton.clicked.connect(self.send_message)
        message_input_layout.addWidget(self.sendButton)
        main_layout.addWidget(message_input_widget)

        splitter_bottom.setStretchFactor(0, 3)
        splitter_bottom.setStretchFactor(1, 1)

    #Mute/unmute section on client
    def toggle_mic(self):
        if self.muteMicButton.isChecked():
            self.mute_mic()
            self.muteMicButton.setIcon(QIcon('assets/img/default_colored_2014/input_muted.svg'))
            self.play_sound('assets/sound/mic_muted.mp3')
        else:
            self.unmute_mic()
            self.muteMicButton.setIcon(QIcon('assets/img/default_colored_2014/capture.svg'))
            self.play_sound('assets/sound/mic_activated.mp3')

    def mute_mic(self):
        if self.audio_thread is not None:
            self.audio_thread.mute_mic()
        self.log_message("Microphone muted")

    def unmute_mic(self):
        if self.audio_thread is not None:
            self.audio_thread.unmute_mic()
        self.log_message("Microphone unmuted")

    def toggle_speaker(self):
        if self.muteSpeakerButton.isChecked():
            self.mute_speaker()
            self.muteSpeakerButton.setIcon(QIcon('assets/img/default_colored_2014/output_muted.svg'))
            self.play_sound('assets/sound/sound_muted.mp3')
        else:
            self.unmute_speaker()
            self.muteSpeakerButton.setIcon(QIcon('assets/img/default_colored_2014/volume.svg'))
            self.play_sound('assets/sound/sound_resumed.mp3')

    def mute_speaker(self):
        self.speaker_muted = True
        self.log_message("Speaker muted")

    def unmute_speaker(self):
        self.speaker_muted = False
        self.log_message("Speaker unmuted")

    def reset_audio_stream(self):
        if self.audio_stream is not None:
            try:
                self.audio_stream.close()
            except OSError as e:
                print(f"Error closing stream: {e}")
        try:
            self.audio_stream = self.pyaudio_instance.open(format=pyaudio.paInt16,
                                                           channels=1,
                                                           rate=44100,
                                                           output=True)
        except OSError as e:
            print(f"Error opening stream: {e}")

    def play_audio(self, audio_data):
        if not self.speaker_muted and self.audio_stream is not None:
            try:
                self.audio_stream.write(audio_data)
            except OSError as e:
                if e.errno == -9983:  # Stream is stopped
                    self.reset_audio_stream()
                    try:
                        self.audio_stream.write(audio_data)
                    except OSError as inner_e:
                        print(f"Error writing to stream: {inner_e}")

    def start_audio_stream(self):
        self.audio_thread = AudioThread(self.websocket, asyncio.get_event_loop())
        self.audio_thread.start()

    def stop_audio_stream(self):
        if self.audio_thread:
            self.audio_thread.stop()
            self.audio_thread = None

    def play_sound(self, sound_file):
        self.media_player.setMedia(QMediaContent(QUrl.fromLocalFile(sound_file)))
        self.media_player.play()

    #Connect dialog for connecting to a server
    def show_connect_dialog(self):
        dialog = ConnectDialog()
        if dialog.exec_() == QDialog.Accepted:
            server_address, password, name = dialog.get_connection_info()
            uid = self.get_uid_for_user(name)  # Hämta UID för användaren
            asyncio.ensure_future(self.connect_to_server(server_address, password, name, uid))

    #Bookmarks management
    def show_manage_bookmarks_dialog(self):
        dialog = ManageBookmarksDialog(self.bookmarks, self.save_bookmarks_to_db)
        if dialog.exec_():
            self.refresh_bookmarks_menu()

    def load_bookmarks_from_db(self):
        try:
            self.bookmarks = load_bookmarks()  # Load bookmarks from the database
        except Exception as e:
            print(f"Failed to load bookmarks: {str(e)}")
            self.bookmarks = []

    def save_bookmarks_to_db(self):
        try:
            save_bookmarks(self.bookmarks)  # Save bookmarks to the database
        except Exception as e:
            print(f"Failed to save bookmarks: {str(e)}")

    def refresh_bookmarks_menu(self):
        self.bookmarksMenu.clear()  # Clear existing menu items

        # Add fixed menu items
        addBookmarkAction = QAction(QIcon('assets/img/default_colored_2014/bookmark_add.svg'), 'Add Bookmark', self)
        addBookmarkAction.triggered.connect(self.add_bookmark)
        self.bookmarksMenu.addAction(addBookmarkAction)

        manageBookmarksAction = QAction(QIcon('assets/img/default_colored_2014/bookmark_manager.svg'), 'Manage Bookmarks', self)
        manageBookmarksAction.triggered.connect(self.show_manage_bookmarks_dialog)
        self.bookmarksMenu.addAction(manageBookmarksAction)
        self.bookmarksMenu.addSeparator()

        # Dynamically add bookmarks
        for bookmark in self.bookmarks:
            action = QAction(QIcon('assets/img/default_colored_2014/server_green.svg'), bookmark['name'], self)
            action.triggered.connect(lambda checked, b=bookmark: self.connect_to_bookmark(b))
            self.bookmarksMenu.addAction(action)

        self.update_bookmark_actions()

    def update_bookmark_actions(self):
        actions = self.bookmarksMenu.actions()
        if self.websocket:
            actions[0].setEnabled(True)
        else:
            actions[0].setEnabled(False) 

    def connect_to_bookmark(self, bookmark):
        print(f"Connecting to {bookmark['name']} at {bookmark['address']}")
        uid = self.get_uid_for_user(bookmark['nickname'])  # Hämta UID för användaren i bokmärket
        asyncio.ensure_future(self.connect_to_server(bookmark['address'], bookmark['password'], bookmark['nickname'], uid))


    def add_bookmark(self):
        if self.websocket:
            current_server = {
                "name": self.server_name,
                "address": self.websocket.remote_address[0],
                "password": "",  # Lägg till logik för att hantera lösenord om nödvändigt
                "nickname": self.current_username
            }
            self.bookmarks.append(current_server)
            self.save_bookmarks_to_db()
            self.refresh_bookmarks_menu()

    #To show connection window
    def show_connection_info_dialog(self):
        if self.connection_info_dialog is None:
            self.connection_info_dialog = ConnectionInfoDialog(self, self.get_connection_info)
        self.connection_info_dialog.show()
        self.connection_info_dialog.raise_()
        self.connection_info_dialog.activateWindow()

    #To show Identities window
    def show_identities_dialog(self):
        dialog = IdentitiesDialog(self)
        dialog.exec_()

    #To show settings window
    def show_settings_dialog(self):
        dialog = SettingsDialog(self)
        dialog.exec_()

    #Show use PrivilegeKey window
    def show_UsePrivilegeKey_dialog(self):
        dialog = UsePrivilegeKey()
        if dialog.exec_() == QDialog.Accepted:
            usePrivilegeKey  = dialog.get_use_privilege_key()

    #Opens the website for Pyspeak
    def open_website(self):
        webbrowser.open('https://www.aftonbladet.se')

    # Show about PySpeak dialog
    def show_aboutPySpeak_dialog(self):
        dialog = AboutPySpeak(self.pySpeak_infoFile, self)
        dialog.exec_()

    # Show about PyLicens dialog
    def show_PyLicense_dialog(self):
        dialog = PyLicense(self.PyLicense, self)
        dialog.exec_()

    # Show about PyQt dialog
    def show_aboutPyQT_dialog(self):
        dialog = AboutPyQT(self.pyqt5_infoFile, self)
        dialog.exec_()

    # Show changelog dialog
    def show_changelog_dialog(self):
        dialog = ChangelogDialog(self.changelog_file, self)
        dialog.exec_()

    #Server connections
    async def connect_to_server(self, server_address, password, name, uid):
        try:
            self.log_message(f"Trying to connect to server on {server_address}")
            self.websocket = await websockets.connect(f'ws://{server_address}')
            await self.websocket.send(json.dumps({'type': 'join', 'username': name, 'password': password, 'uid': uid}))
            self.log_message(f"Connected to {server_address} as {name}")
            self.current_username = name
            self.current_uid = uid  # Spara UID
            self.connection_start_time = datetime.now()
            self.ping = 0
            self.connectionInfoAction.setEnabled(True)
            self.update_bookmark_actions()
            self.play_sound('assets/sound/connected.mp3')

            asyncio.ensure_future(self.receive_messages())
        except Exception as e:
            self.log_message(f"Failed to connect: {str(e)}")

    async def disconnect_from_server(self):
        if self.websocket:
            await self.websocket.close()
            self.websocket = None
            self.connectionInfoAction.setEnabled(False)
            self.log_message("Disconnected from server")
            self.play_sound('assets/sound/disconnected.mp3')
            self.update_bookmark_actions()
            self.roomList.clear()
            self.userInfo.clear()

    async def receive_messages(self):
        try:
            async for message in self.websocket:
                if isinstance(message, bytes):
                    self.play_audio(message)
                    self.update_statistics("speech", len(message))
                else:
                    data = json.loads(message)
                    if data['type'] == 'info':
                        self.log_message(data['message'])
                    elif data['type'] == 'message':
                        self.log_message(f"{data['username']}: {data['message']}")
                    elif data['type'] == 'room_update':
                        self.update_room_members(data['members'])
                    elif data['type'] == 'room_list':
                        self.update_room_list(data)
                    elif data['type'] == 'error':
                        self.log_message(f"Error: {data['message']}")
                    elif data['type'] == 'talking':
                        self.update_talking_status(data['username'], data['status'])
                    elif data['type'] == 'ping':
                        self.ping = data['ping']
                    elif data['type'] == 'switched_room':
                        self.log_message(data['message'])
                        self.stop_audio_stream()  # Stop the current audio stream
                        self.start_audio_stream()  # Start a new audio stream for the new room
                        self.play_sound('assets/sound/channel_switched.mp3')
                    self.update_statistics(data['type'], len(message))
        except websockets.ConnectionClosed:
            self.play_sound('assets/sound/connection_lost.mp3')
            self.log_message("Connection closed")

    def get_uid_for_user(self, nickname):
        conn = sqlite3.connect(db_file)
        cursor = conn.cursor()
        cursor.execute("SELECT uid FROM identities WHERE nickname=?", (nickname,))
        row = cursor.fetchone()
        if row:
            uid = row[0]
        else:
            uid = str(uuid.uuid4())
            cursor.execute('''
                INSERT INTO identities (identity_name, nickname, uid)
                VALUES (?, ?, ?)
            ''', (nickname, nickname, uid))
            conn.commit()
        conn.close()
        return uid

    def get_connection_info(self):
        if self.websocket:
            connection_time = str(timedelta(seconds=int((datetime.now() - self.connection_start_time).total_seconds())))
            return {
                "client_name": self.current_username or "",
                "connection_time": connection_time or "",
                "idle_time": connection_time,  # Assuming no separate idle tracking for now
                "ping": f"{self.ping} ms ± 0.6",  # Replace 0.6 with actual jitter if available
                "client_address":  self.websocket.remote_address[0] if self.websocket.remote_address else "",  # Replace with actual client address
                "total": {
                    "packet_loss": "0.00",  # Replace with actual value
                    "packets_transferred": self.statistics["total"]["packets_transferred"],
                    "bytes_transferred": f"{self.statistics['total']['bytes_transferred'] / 1024:.2f} KiB",
                    "bandwidth_last_second": f"{self.statistics['total']['bandwidth_last_second']} Bytes/s",
                    "bandwidth_last_minute": f"{self.statistics['total']['bandwidth_last_minute']} Bytes/s",
                    "file_transfer_bandwidth": f"{self.statistics['total']['file_transfer_bandwidth']} Bytes/s"
                },
                "speech": {
                    "packets_transferred": self.statistics["speech"]["packets_transferred"],
                    "bytes_transferred": f"{self.statistics['speech']['bytes_transferred'] / 1024:.2f} KiB",
                    "bandwidth_last_second": f"{self.statistics['speech']['bandwidth_last_second']} Bytes/s",
                    "bandwidth_last_minute": f"{self.statistics['speech']['bandwidth_last_minute']} Bytes/s"
                },
                "keep_alive": {
                    "packets_transferred": self.statistics["keep_alive"]["packets_transferred"],
                    "bytes_transferred": f"{self.statistics['keep_alive']['bytes_transferred'] / 1024:.2f} KiB",
                    "bandwidth_last_second": f"{self.statistics['keep_alive']['bandwidth_last_second']} Bytes/s",
                    "bandwidth_last_minute": f"{self.statistics['keep_alive']['bandwidth_last_minute']} Bytes/s"
                },
                "control": {
                    "packets_transferred": self.statistics["control"]["packets_transferred"],
                    "bytes_transferred": f"{self.statistics['control']['bytes_transferred'] / 1024:.2f} KiB",
                    "bandwidth_last_second": f"{self.statistics['control']['bandwidth_last_second']} Bytes/s",
                    "bandwidth_last_minute": f"{self.statistics['control']['bandwidth_last_minute']} Bytes/s"
                },
                "quota": {
                    "bytes_transferred": f"{self.statistics['quota']['bytes_transferred'] / 1024:.2f} KiB",
                    "bandwidth_last_second": f"{self.statistics['quota']['bandwidth_last_second']} Bytes/s",
                    "bandwidth_last_minute": f"{self.statistics['quota']['bandwidth_last_minute']} Bytes/s"
                }
            }
        return {}

    def update_statistics(self, message_type, packet_size):
        """Update statistics based on the message type and packet size."""
        self.statistics["total"]["packets_transferred"] += 1
        self.statistics["total"]["bytes_transferred"] += packet_size
        if message_type in self.statistics:
            self.statistics[message_type]["packets_transferred"] += 1
            self.statistics[message_type]["bytes_transferred"] += packet_size

    def update_talking_status(self, username, is_talking):
        for i in range(self.userInfo.count()):
            item = self.userInfo.item(i)
            if item.text().strip() == username:
                icon = QIcon('assets/img/talking_icon.png') if is_talking else QIcon('assets/img/nottalking_icon.png')
                item.setIcon(icon)
                break

    #Updates rooms and members
    def update_room_members(self, members):
        self.userInfo.clear()
        for member in members:
            item = QListWidgetItem(member['username'])
            item.setIcon(QIcon('assets/img/default_colored_2014/player_off.svg'))
            self.userInfo.addItem(item)

    def update_room_list(self, data):
        self.room_list = data['rooms']
        self.server_name = data.get('server_name', 'Unknown Server')
        self.user_info = data.get('user_info', {})
        self.roomList.clear()

        # Lägg till servernamn högst upp
        server_item = QListWidgetItem(self.server_name)
        server_item.setIcon(QIcon('assets/img/default_colored_2014/server_green.svg'))
        server_item.setFlags(server_item.flags() & ~Qt.ItemIsSelectable)
        self.roomList.addItem(server_item)

        for room, room_data in self.room_list.items():
            room_icon = QIcon('assets/img/default_colored_2014/channel_yellow.svg') if room_data['password'] else QIcon('assets/img/default_colored_2014/channel_green.svg')
            room_item = QListWidgetItem(f"  {room}")
            room_item.setIcon(room_icon)
            self.roomList.addItem(room_item)
            for user in room_data['members']:
                user_item = QListWidgetItem(f"    {user}")
                user_item.setIcon(QIcon('assets/img/default_colored_2014/player_off.svg'))
                self.roomList.addItem(user_item)

    def switch_room(self, item):
        room_name = item.text().strip()
        current_usernames = [self.current_username] + [user_item.text().strip() for user_item in self.userInfo.findItems(self.current_username, Qt.MatchExactly)]
        if room_name in current_usernames:
            return

        if room_name == self.server_name:
            return

        room_data = self.room_list.get(room_name, None)
        if room_data and room_data['password']:
            dialog = PasswordDialog(room_name)
            if dialog.exec_() == QDialog.Accepted:
                password = dialog.get_password()
                asyncio.ensure_future(self.websocket.send(json.dumps({'type': 'switch_room', 'new_room': room_name, 'room_password': password})))
        else:
            asyncio.ensure_future(self.websocket.send(json.dumps({'type': 'switch_room', 'new_room': room_name})))

    #Message sender
    def send_message(self, name):
        message = self.messageInput.text()
        if message and self.websocket:
            asyncio.ensure_future(self.websocket.send(json.dumps({'type': 'message', 'message': message, 'username': name})))
            self.messageInput.clear()

    #log messages
    def log_message(self, message):
        timestamp = datetime.now().strftime('%H:%M:%S')
        self.console.append(f"{timestamp} - {message}")
