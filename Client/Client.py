#Massive import system
import sys
import wave
import asyncio
import json
import websockets
import qasync
import pyaudio
import collections
import numpy as np
import webbrowser
import threading
from datetime import datetime
from PyQt5.QtMultimedia import QSound
from PyQt5.QtMultimedia import QMediaPlayer, QMediaContent
from PyQt5.QtCore import Qt, QThread, QUrl
from PyQt5.QtGui import QIcon, QPainter
from PyQt5.QtWidgets import ( 
    QApplication,
    QMainWindow,
    QWidget, 
    QVBoxLayout, 
    QHBoxLayout, 
    QPushButton, 
    QLineEdit, 
    QSlider, 
    QAction, 
    QSplitter, 
    QTextEdit, 
    QListWidget, 
    QListWidgetItem, 
    QDialog, 
    QFormLayout, 
    QComboBox,
    QStackedWidget,
    QGroupBox,
    QCheckBox,
    QRadioButton,
    QDialogButtonBox,
    QStyleOptionSlider,
    QStyle,
    QLabel)

#Main classes for dialogs, threads and mainwindow
class ConnectDialog(QDialog):
    def __init__(self):
        super().__init__()
        self.initUI()

    def initUI(self):
        self.setWindowTitle('Connect to Server')
        self.setGeometry(100, 100, 300, 100)

        layout = QFormLayout()

        self.serverInput = QLineEdit(self)
        self.serverInput.setPlaceholderText('Server Address')
        layout.addRow('Server Address:', self.serverInput)

        self.passwordInput = QLineEdit(self)
        self.passwordInput.setPlaceholderText('Server Password (Optional)')
        self.passwordInput.setEchoMode(QLineEdit.Password)
        layout.addRow('Password:', self.passwordInput)

        self.nameInput = QLineEdit(self)
        self.nameInput.setPlaceholderText('Your Name')
        layout.addRow('Name:', self.nameInput)

        self.connectButton = QPushButton('Connect', self)
        self.connectButton.clicked.connect(self.accept)
        layout.addWidget(self.connectButton)

        self.setLayout(layout)

    def get_connection_info(self):
        return self.serverInput.text(), self.passwordInput.text(), self.nameInput.text()

class ManageBookmarksDialog(QDialog):
    def __init__(self, bookmarks, save_func):
        super().__init__()
        self.bookmarks = bookmarks
        self.save_func = save_func
        self.initUI()

    def initUI(self):
        self.setWindowTitle('Manage Bookmarks')
        self.setGeometry(100, 100, 600, 400)
        
        mainLayout = QHBoxLayout(self)
        
        # Left side: List of saved servers
        self.serverList = QListWidget()
        self.serverList.currentItemChanged.connect(self.load_selected_bookmark)
        mainLayout.addWidget(self.serverList, 1)
        
        # Right side: Form to edit details
        formLayout = QFormLayout()
        self.nameInput = QLineEdit()
        self.addressInput = QLineEdit()
        self.passwordInput = QLineEdit()
        self.passwordInput.setEchoMode(QLineEdit.Password)
        self.nicknameInput = QLineEdit()

        formLayout.addRow("Server Name:", self.nameInput)
        formLayout.addRow("Server Address:", self.addressInput)
        formLayout.addRow("Password (Optional):", self.passwordInput)
        formLayout.addRow("Nickname:", self.nicknameInput)

        self.saveButton = QPushButton("Save")
        self.saveButton.clicked.connect(self.save_current_bookmark)
        self.deleteButton = QPushButton("Delete")
        self.deleteButton.clicked.connect(self.delete_current_bookmark)
        buttonsLayout = QHBoxLayout()
        buttonsLayout.addWidget(self.saveButton)
        buttonsLayout.addWidget(self.deleteButton)
        formLayout.addRow(buttonsLayout)

        formContainer = QWidget()
        formContainer.setLayout(formLayout)
        mainLayout.addWidget(formContainer, 2)

        self.setLayout(mainLayout)
        self.load_bookmarks()

    def load_bookmarks(self):
        self.serverList.clear()
        for bookmark in self.bookmarks:
            item = QListWidgetItem(bookmark['name'])
            self.serverList.addItem(item)

    def load_selected_bookmark(self, current, previous):
        if current is not None:
            data = self.bookmarks[self.serverList.row(current)]
            self.nameInput.setText(data['name'])
            self.addressInput.setText(data['address'])
            self.passwordInput.setText(data['password'])
            self.nicknameInput.setText(data['nickname'])

    def save_current_bookmark(self):
        index = self.serverList.currentRow()
        if index == -1:  # No item selected, this is a new bookmark
            index = len(self.bookmarks)
            self.bookmarks.append({})
            self.serverList.addItem(self.nameInput.text())

        data = {
            'name': self.nameInput.text(),
            'address': self.addressInput.text(),
            'password': self.passwordInput.text(),
            'nickname': self.nicknameInput.text()
        }
        self.bookmarks[index] = data
        self.serverList.item(index).setText(data['name'])
        self.save_func()

    def delete_current_bookmark(self):
        index = self.serverList.currentRow()
        if index != -1:
            del self.bookmarks[index]
            self.serverList.takeItem(index)
            self.save_func()

class CustomSlider(QSlider):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setTickPosition(QSlider.TicksBelow)
        self.setTickInterval(10)
        self.setSingleStep(1)
        self.setPageStep(10)

    def paintEvent(self, event):
        super().paintEvent(event)
        painter = QPainter(self)
        option = QStyleOptionSlider()
        self.initStyleOption(option)
        self.style().drawComplexControl(QStyle.CC_Slider, option, painter, self)
        for tick in range(self.minimum(), self.maximum() + 1, self.tickInterval()):
            self.drawTick(painter, tick)

    def drawTick(self, painter, tick):
        rect = self.geometry()
        spacing = (rect.width() - 20) / (self.maximum() - self.minimum())
        x = 10 + (tick - self.minimum()) * spacing
        x = int(x)
        painter.drawLine(x, rect.height() - 20, x, rect.height() - 10)
        painter.drawText(x - 10, rect.height(), 20, 20, Qt.AlignCenter, str(tick))

class AudioTestThread(QThread):
    def __init__(self, stream_in, stream_out, parent=None):
        super().__init__(parent)
        self.stream_in = stream_in
        self.stream_out = stream_out
        self.running = True

    def run(self):
        while self.running:
            data = self.stream_in.read(1024)
            self.stream_out.write(data)

    def stop(self):
        self.running = False
        self.wait()

class SettingsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Settings")
        self.setGeometry(100, 100, 800, 600)
        self.settings_file = 'settings.json'
        self.initUI()
        self.load_settings()
        self.pyaudio_instance = pyaudio.PyAudio()
        self.is_testing = False
        self.stream_in = None
        self.stream_out = None
        self.audio_test_thread = None

    def initUI(self):
        main_layout = QVBoxLayout(self)

        # Main layout split into left (categories) and right (settings pages)
        content_layout = QHBoxLayout()

        # Left side: List of settings categories
        self.category_list = QListWidget()
        content_layout.addWidget(self.category_list, 1)

        playback_item = QListWidgetItem("Playback")
        playback_item.setIcon(QIcon('assets/img/speaker.png'))
        self.category_list.addItem(playback_item)

        capture_item = QListWidgetItem("Capture")
        capture_item.setIcon(QIcon('assets/img/microphone.png'))
        self.category_list.addItem(capture_item)

        # Right side: Stack of settings pages
        self.settings_stack = QStackedWidget()

        # Playback settings
        self.playback_page = self.create_playback_page()
        self.settings_stack.addWidget(self.playback_page)

        # Capture settings
        self.capture_page = self.create_capture_page()
        self.settings_stack.addWidget(self.capture_page)

        # Add more pages as needed...

        content_layout.addWidget(self.settings_stack, 3)

        # Connect list selection to stack widget
        self.category_list.currentRowChanged.connect(self.settings_stack.setCurrentIndex)

        main_layout.addLayout(content_layout)

        # OK and Cancel buttons
        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(self.save_settings)
        button_box.rejected.connect(self.reject)
        main_layout.addWidget(button_box)

        self.setLayout(main_layout)

    def create_playback_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)

        form_layout = QFormLayout()

        self.playback_mode_combo = QComboBox()
        self.playback_mode_combo.addItems(["Automatically use best mode", "Manual selection"])
        form_layout.addRow("Playback Mode:", self.playback_mode_combo)

        self.playback_device_combo = QComboBox()
        self.populate_audio_devices(self.playback_device_combo, input=False)
        form_layout.addRow("Playback Device:", self.playback_device_combo)

        layout.addLayout(form_layout)

        # Sliders
        self.volume_adjustment_slider = QSlider(Qt.Horizontal)
        self.volume_adjustment_slider.setRange(-40, 20)
        self.volume_adjustment_slider.setValue(0)
        form_layout.addRow("Voice Volume Adjustment:", self.volume_adjustment_slider)

        self.sound_pack_volume_slider = QSlider(Qt.Horizontal)
        self.sound_pack_volume_slider.setRange(-40, 20)
        form_layout.addRow("Sound Pack Volume:", self.sound_pack_volume_slider)

        layout.addLayout(form_layout)

        # Play test sound button
        play_test_sound_button = QPushButton("Play Test Sound")
        play_test_sound_button.clicked.connect(self.play_test_sound)
        layout.addWidget(play_test_sound_button)

        # Options checkboxes
        options_group = QGroupBox("Options")
        options_layout = QVBoxLayout()

        self.auto_volume_checkbox = QCheckBox("Automatic voice volume leveling")
        self.mic_clicks_checkbox = QCheckBox("Own client plays mic clicks")
        options_layout.addWidget(self.auto_volume_checkbox)
        options_layout.addWidget(self.mic_clicks_checkbox)

        options_group.setLayout(options_layout)
        layout.addWidget(options_group)

        # Mono sound expansion radio buttons
        mono_expansion_group = QGroupBox("Mono Sound Expansion")
        mono_expansion_layout = QVBoxLayout()
        self.mono_stereo_radio = QRadioButton("Mono to stereo")
        self.mono_center_radio = QRadioButton("Mono to center speaker (if available)")
        self.mono_surround_radio = QRadioButton("Mono to surround (if available)")
        mono_expansion_layout.addWidget(self.mono_stereo_radio)
        mono_expansion_layout.addWidget(self.mono_center_radio)
        mono_expansion_layout.addWidget(self.mono_surround_radio)
        mono_expansion_group.setLayout(mono_expansion_layout)

        layout.addWidget(mono_expansion_group)
        layout.addStretch()

        return page

    def create_capture_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)

        form_layout = QFormLayout()

        # Capture mode
        self.capture_mode_combo = QComboBox()
        self.capture_mode_combo.addItems(["Automatically use best mode", "Manual selection"])
        form_layout.addRow("Capture Mode:", self.capture_mode_combo)

        # Capture device
        self.capture_device_combo = QComboBox()
        self.populate_audio_devices(self.capture_device_combo, input=True)
        form_layout.addRow("Capture Device:", self.capture_device_combo)

        layout.addLayout(form_layout)

        # Activation section
        activation_group = QGroupBox("Activation")
        activation_layout = QVBoxLayout()

        self.push_to_talk_radio = QRadioButton("Push-To-Talk")
        push_to_talk_layout = QHBoxLayout()
        push_to_talk_layout.addWidget(self.push_to_talk_radio)
        self.hotkey_button = QPushButton("No Hotkey Assigned")
        push_to_talk_layout.addWidget(self.hotkey_button)
        activation_layout.addLayout(push_to_talk_layout)

        self.continuous_transmission_radio = QRadioButton("Continuous Transmission")
        activation_layout.addWidget(self.continuous_transmission_radio)

        self.vad_radio = QRadioButton("Voice Activity Detection")
        vad_layout = QHBoxLayout()
        vad_layout.addWidget(self.vad_radio)
        self.vad_mode_combo = QComboBox()
        self.vad_mode_combo.addItems(["Volume Gate"])
        vad_layout.addWidget(self.vad_mode_combo)
        activation_layout.addLayout(vad_layout)

        # VAD Test Section
        vad_test_layout = QVBoxLayout()
        self.vad_slider = CustomSlider(Qt.Horizontal)
        self.vad_slider.setRange(-50, 50)
        self.vad_slider.setValue(0)
        vad_test_layout.addWidget(self.vad_slider)

        self.begin_test_button = QPushButton("Begin Test")
        self.begin_test_button.clicked.connect(self.begin_test)
        vad_test_layout.addWidget(self.begin_test_button)

        activation_layout.addLayout(vad_test_layout)

        activation_group.setLayout(activation_layout)
        layout.addWidget(activation_group)

        # Digital Signal Processing section
        dsp_group = QGroupBox("Digital Signal Processing")
        dsp_layout = QVBoxLayout()

        self.typing_att_checkbox = QCheckBox("Typing attenuation")
        dsp_layout.addWidget(self.typing_att_checkbox)

        self.remove_noise_checkbox = QCheckBox("Remove background noise")
        self.remove_noise_checkbox.setChecked(True)
        dsp_layout.addWidget(self.remove_noise_checkbox)

        self.echo_cancel_checkbox = QCheckBox("Echo cancellation")
        self.echo_cancel_checkbox.setChecked(True)
        dsp_layout.addWidget(self.echo_cancel_checkbox)

        self.echo_reduction_checkbox = QCheckBox("Echo reduction (Ducking)")
        dsp_layout.addWidget(self.echo_reduction_checkbox)

        dsp_group.setLayout(dsp_layout)
        layout.addWidget(dsp_group)

        layout.addStretch()

        return page

    def populate_audio_devices(self, combo_box, input=True):
        p = pyaudio.PyAudio()
        info = p.get_host_api_info_by_index(0)
        num_devices = info.get('deviceCount')

        for i in range(0, num_devices):
            device_info = p.get_device_info_by_host_api_device_index(0, i)
            if input and device_info.get('maxInputChannels') > 0:
                combo_box.addItem(device_info.get('name'))
            elif not input and device_info.get('maxOutputChannels') > 0:
                combo_box.addItem(device_info.get('name'))

        p.terminate()

    def play_test_sound(self):
        wf = wave.open("assets/sound/test_sound.wav", 'rb')
        channels = wf.getnchannels()

        # Open a PyAudio stream using the selected playback device
        playback_device_index = self.playback_device_combo.currentIndex()

        try:
            device_info = self.pyaudio_instance.get_device_info_by_index(playback_device_index)
            max_output_channels = device_info.get('maxOutputChannels', 1)
            channels = min(channels, max_output_channels)

            stream = self.pyaudio_instance.open(format=self.pyaudio_instance.get_format_from_width(wf.getsampwidth()),
                                                channels=channels,
                                                rate=wf.getframerate(),
                                                output=True,
                                                output_device_index=playback_device_index)
        except OSError as e:
            print(f"Error opening stream: {e}")
            return

        # Read data in chunks and play
        data = wf.readframes(1024)
        while data:
            adjusted_data = self.adjust_volume(data)
            stream.write(adjusted_data)
            data = wf.readframes(1024)

        # Stop and close the stream
        stream.stop_stream()
        stream.close()

    def adjust_volume(self, data):
        volume_db = self.volume_adjustment_slider.value()
        volume_factor = 10 ** (volume_db / 20.0)

        # Convert byte data to numpy array, adjust volume, and convert back to bytes
        audio_data = np.frombuffer(data, dtype=np.int16)
        audio_data = (audio_data * volume_factor).astype(np.int16)
        return audio_data.tobytes()
    
    def begin_test(self):
        if self.is_testing:
            self.stop_test()
            self.begin_test_button.setText("Begin Test")  # Update button text
        else:
            capture_device_index = self.capture_device_combo.currentIndex()
            playback_device_index = self.playback_device_combo.currentIndex()

            try:
                capture_device_info = self.pyaudio_instance.get_device_info_by_index(capture_device_index)
                max_input_channels = capture_device_info.get('maxInputChannels', 1)

                playback_device_info = self.pyaudio_instance.get_device_info_by_index(playback_device_index)
                max_output_channels = playback_device_info.get('maxOutputChannels', 1)

                self.stream_in = self.pyaudio_instance.open(format=pyaudio.paInt16,
                                                            channels=min(1, max_input_channels),
                                                            rate=44100,
                                                            input=True,
                                                            input_device_index=capture_device_index,
                                                            frames_per_buffer=1024)

                self.stream_out = self.pyaudio_instance.open(format=pyaudio.paInt16,
                                                            channels=min(1, max_output_channels),
                                                            rate=44100,
                                                            output=True,
                                                            output_device_index=playback_device_index,
                                                            frames_per_buffer=1024)
            except OSError as e:
                print(f"Error opening stream: {e}")
                return

            self.is_testing = True
            self.audio_test_thread = AudioTestThread(self.stream_in, self.stream_out)
            self.audio_test_thread.start()
            self.begin_test_button.setText("Stop Test") 

    def stop_test(self):
        if self.audio_test_thread is not None:
            self.audio_test_thread.stop()
            self.audio_test_thread = None
        self.is_testing = False
        if hasattr(self, 'stream_in') and self.stream_in is not None:
            self.stream_in.stop_stream()
            self.stream_in.close()
        if hasattr(self, 'stream_out') and self.stream_out is not None:
            self.stream_out.stop_stream()
            self.stream_out.close()

    def save_settings(self):
        settings = {
            "playback_mode": self.playback_mode_combo.currentText(),
            "playback_device": self.playback_device_combo.currentText(),
            "volume_adjustment": self.volume_adjustment_slider.value(),
            "sound_pack_volume": self.sound_pack_volume_slider.value(),
            "auto_volume": self.auto_volume_checkbox.isChecked(),
            "mic_clicks": self.mic_clicks_checkbox.isChecked(),
            "mono_stereo": self.mono_stereo_radio.isChecked(),
            "mono_center": self.mono_center_radio.isChecked(),
            "mono_surround": self.mono_surround_radio.isChecked(),
            "capture_mode": self.capture_mode_combo.currentText(),
            "capture_device": self.capture_device_combo.currentText(),
            "push_to_talk": self.push_to_talk_radio.isChecked(),
            "continuous_transmission": self.continuous_transmission_radio.isChecked(),
            "vad": self.vad_radio.isChecked(),
            "vad_mode": self.vad_mode_combo.currentText(),
            "vad_level": self.vad_slider.value(),
            "typing_att": self.typing_att_checkbox.isChecked(),
            "remove_noise": self.remove_noise_checkbox.isChecked(),
            "echo_cancel": self.echo_cancel_checkbox.isChecked(),
            "echo_reduction": self.echo_reduction_checkbox.isChecked()
        }

        with open(self.settings_file, 'w') as file:
            json.dump(settings, file, indent=4)

        self.accept()

    def load_settings(self):
        try:
            with open(self.settings_file, 'r') as file:
                settings = json.load(file)

                self.playback_mode_combo.setCurrentText(settings.get("playback_mode", "Automatically use best mode"))
                self.playback_device_combo.setCurrentText(settings.get("playback_device", "Default"))
                self.volume_adjustment_slider.setValue(settings.get("volume_adjustment", 0))
                self.sound_pack_volume_slider.setValue(settings.get("sound_pack_volume", 0))
                self.auto_volume_checkbox.setChecked(settings.get("auto_volume", False))
                self.mic_clicks_checkbox.setChecked(settings.get("mic_clicks", False))
                self.mono_stereo_radio.setChecked(settings.get("mono_stereo", True))
                self.mono_center_radio.setChecked(settings.get("mono_center", False))
                self.mono_surround_radio.setChecked(settings.get("mono_surround", False))
                self.capture_mode_combo.setCurrentText(settings.get("capture_mode", "Automatically use best mode"))
                self.capture_device_combo.setCurrentText(settings.get("capture_device", "Default"))
                self.push_to_talk_radio.setChecked(settings.get("push_to_talk", False))
                self.continuous_transmission_radio.setChecked(settings.get("continuous_transmission", False))
                self.vad_radio.setChecked(settings.get("vad", False))
                self.vad_mode_combo.setCurrentText(settings.get("vad_mode", "Volume Gate"))
                self.vad_slider.setValue(settings.get("vad_level", 0))
                self.typing_att_checkbox.setChecked(settings.get("typing_att", False))
                self.remove_noise_checkbox.setChecked(settings.get("remove_noise", True))
                self.echo_cancel_checkbox.setChecked(settings.get("echo_cancel", True))
                self.echo_reduction_checkbox.setChecked(settings.get("echo_reduction", False))
        except FileNotFoundError:
            print("Settings file not found. A new one will be created.")
            self.settings = {}
            self.save_settings_to_file()  # Create the file immediately if not found
        except json.JSONDecodeError as e:
            print(f"Failed to load settings due to JSON decoding error: {str(e)}")
            self.settings = {}

    def save_settings_to_file(self):
        try:
            # Ensure the file is created if it doesn't exist and open for writing
            with open(self.settings_file, 'w') as file:
                json.dump(self.settings, file, indent=4)
        except IOError as e:
            print(f"Failed to save settings: {str(e)}")

class PasswordDialog(QDialog):
    def __init__(self, room_name):
        super().__init__()
        self.room_name = room_name
        self.initUI()

    def initUI(self):
        self.setWindowTitle(f'Enter Password for {self.room_name}')
        self.setGeometry(100, 100, 300, 100)

        layout = QFormLayout()

        self.passwordInput = QLineEdit(self)
        self.passwordInput.setEchoMode(QLineEdit.Password)
        layout.addRow('Password:', self.passwordInput)

        self.submitButton = QPushButton('Submit', self)
        self.submitButton.clicked.connect(self.accept)
        layout.addWidget(self.submitButton)

        self.setLayout(layout)

    def get_password(self):
        return self.passwordInput.text()

class ChangelogDialog(QDialog):
    def __init__(self, changelog_file, parent=None):
        super().__init__(parent)
        self.changelog_file = changelog_file
        self.initUI()

    def initUI(self):
        self.setWindowTitle('Changelog')
        self.setGeometry(100, 100, 675, 500)

        layout = QVBoxLayout()

        # QTextEdit för att visa changelog-innehållet
        self.textEdit = QTextEdit(self)
        self.textEdit.setReadOnly(True)
        self.textEdit.setLineWrapMode(QTextEdit.NoWrap)  # Disable word wrap
        self.textEdit.setFontFamily("Courier")  # Use a fixed-width font
        layout.addWidget(self.textEdit)

        # Läsa och visa changelog.txt-innehållet
        with open(self.changelog_file, 'r') as file:
            self.textEdit.setPlainText(file.read())

        # Stäng-knapp
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        self.closeButton = QPushButton('Close', self)
        self.closeButton.setFixedSize(60, 25)
        self.closeButton.clicked.connect(self.accept)
        button_layout.addWidget(self.closeButton)

        layout.addLayout(button_layout)
        self.setLayout(layout)

class AboutPySpeak(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.initUI()

    def initUI(self):
        self.setWindowTitle('About PySpeak')
        self.setGeometry(100, 100, 300, 100)

        layout = QFormLayout()

        about_text = QLabel("PySpeak\nVersion: 1.0.0\nDeveloped by: Johan Ivarsson")
        layout.addRow(about_text)

        self.setLayout(layout)

class AboutPyQT(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.initUI()

    def initUI(self):
        self.setWindowTitle('About PyQt')
        self.setGeometry(100, 100, 300, 100)

        layout = QFormLayout()

        about_text = QLabel("PYQT")
        layout.addRow(about_text)

        self.setLayout(layout)

#AudioThread, thread for voice channels
class AudioThread(QThread):
    def __init__(self, websocket, loop):
        super().__init__()
        self.websocket = websocket
        self.pyaudio_instance = pyaudio.PyAudio()
        self.stream = self.pyaudio_instance.open(format=pyaudio.paInt16,
                                                 channels=1,
                                                 rate=44100,
                                                 input=True,
                                                 frames_per_buffer=1024)
        self.running = True
        self.loop = loop  # Save the event loop reference
        self.talking_threshold = 500  # Adjust this value based on your environment
        self.silence_threshold = 300  # Number of consecutive silent frames to consider stop talking
        self.silent_frames = collections.deque(maxlen=self.silence_threshold)
        self.mic_muted = False

    def run(self):
        talking = False
        while self.running:
            if not self.mic_muted:
                data = self.stream.read(1024)
                audio_level = np.frombuffer(data, dtype=np.int16).max()
                self.silent_frames.append(audio_level < self.talking_threshold)

                if not talking and not any(self.silent_frames):
                    talking = True
                    asyncio.run_coroutine_threadsafe(self.websocket.send(json.dumps({'type': 'talking', 'status': True})), self.loop)

                if talking and all(self.silent_frames):
                    talking = False
                    asyncio.run_coroutine_threadsafe(self.websocket.send(json.dumps({'type': 'talking', 'status': False})), self.loop)

                asyncio.run_coroutine_threadsafe(self.websocket.send(data), self.loop)

    def mute_mic(self):
        self.mic_muted = True

    def unmute_mic(self):
        self.mic_muted = False

    def stop(self):
        self.running = False
        self.wait()
        self.stream.stop_stream()
        self.stream.close()
        self.pyaudio_instance.terminate()

#Main window class
class VoiceChatClient(QMainWindow):
    def __init__(self):
        super().__init__()
        self.initUI()
        self.websocket = None
        self.server_name = None
        self.current_username = None
        self.load_bookmarks_from_file()
        self.refresh_bookmarks_menu()
        self.changelog_file = 'changelog.txt'

        # Initialize PyAudio
        self.pyaudio_instance = pyaudio.PyAudio()
        self.stream = None
        self.mic_muted = False
        self.speaker_muted = False
        self.audio_stream = None
        self.audio_thread = None
        self.lock = threading.Lock()

        # Initialize QMediaPlayer
        self.media_player = QMediaPlayer()

    def initUI(self):
        self.setWindowTitle('PySpeak Client')
        self.setWindowIcon(QIcon('assets/img/icon.png'))
        self.setGeometry(100, 100, 500, 600)

        # Create central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        main_layout = QVBoxLayout()
        central_widget.setLayout(main_layout)

        # Create menu bar
        menubar = self.menuBar()

        connectionsMenu = menubar.addMenu('Connections')
        self.bookmarksMenu = self.menuBar().addMenu('Bookmarks')
        selfMenu = menubar.addMenu('Self')
        permissionsMenu = menubar.addMenu('Permissions')
        toolsMenu = menubar.addMenu('Tools')
        helpMenu = menubar.addMenu('Help')

        # Add actions to Connections menu
        connectAction = QAction(QIcon('assets/img/default_colored_2014/connect.svg'),'Connect', self)
        connectAction.triggered.connect(self.show_connect_dialog)
        connectionsMenu.addAction(connectAction)

        disconnectAction = QAction(QIcon('assets/img/default_colored_2014/disconnect.svg'),'Disconnect', self)
        disconnectAction.triggered.connect(lambda: asyncio.ensure_future(self.disconnect_from_server()))
        connectionsMenu.addAction(disconnectAction)
        connectionsMenu.addSeparator()

        quitAction = QAction(QIcon('assets/img/default_colored_2014/close_button.svg'),'Quit', self)
        quitAction.triggered.connect(self.close)
        connectionsMenu.addAction(quitAction)

        # Add actions to Self menu
        changeNameAction = QAction('Change Name', self)
        selfMenu.addAction(changeNameAction)

        # Add actions to Permissions menu
        viewPermissionsAction = QAction('View Permissions', self)
        permissionsMenu.addAction(viewPermissionsAction)

        # Add actions to Tools menu
        settingsAction = QAction(QIcon('assets/img/default_colored_2014/settings.svg'),'Settings', self)
        settingsAction.triggered.connect(self.show_settings_dialog)
        toolsMenu.addAction(settingsAction)

        # Add actions to Help menu
        aboutPySpeakAction = QAction(QIcon('assets/img/default_colored_2014/about.svg'),'About PySpeak', self)
        aboutPySpeakAction.triggered.connect(self.show_aboutPySpeak_dialog)
        helpMenu.addAction(aboutPySpeakAction)

        aboutPyQtAction = QAction(QIcon('assets/img/default_colored_2014/about.svg'),'About PyQt', self)
        aboutPyQtAction.triggered.connect(self.show_aboutPyQT_dialog)
        helpMenu.addAction(aboutPyQtAction)
        helpMenu.addSeparator()

        pySpeakWebsiteAction = QAction(QIcon('assets/img/default_colored_2014/weblist.svg'),'Visit PySpeak website', self)
        pySpeakWebsiteAction.triggered.connect(self.open_website)
        helpMenu.addAction(pySpeakWebsiteAction)
        helpMenu.addSeparator()

        changelogAction = QAction(QIcon('assets/img/default_colored_2014/changelog.svg'),'View changelog', self)
        changelogAction.triggered.connect(self.show_changelog_dialog)
        helpMenu.addAction(changelogAction)

        licenseAction = QAction(QIcon('assets/img/default_colored_2014/changelog.svg'),'View license', self)
        helpMenu.addAction(licenseAction)

        # Create splitter for room list and user info
        splitter_top = QSplitter()
        main_layout.addWidget(splitter_top)

        # Room list
        self.roomList = QListWidget()
        self.roomList.itemClicked.connect(self.switch_room)
        splitter_top.addWidget(self.roomList)

        # User info
        self.userInfo = QListWidget()
        splitter_top.addWidget(self.userInfo)

        splitter_top.setStretchFactor(0, 1)
        splitter_top.setStretchFactor(1, 1)
        splitter_top.setSizes([self.width() // 2, self.width() // 2])

        # Add mute/unmute buttons with icons
        button_layout = QHBoxLayout()

        # Mute/Unmute Mic Button
        self.muteMicButton = QPushButton()
        self.muteMicButton.setCheckable(True)
        self.muteMicButton.setIcon(QIcon('assets/img/default_colored_2014/capture.svg'))
        self.muteMicButton.clicked.connect(self.toggle_mic)

        # Mute/Unmute Speaker Button
        self.muteSpeakerButton = QPushButton()
        self.muteSpeakerButton.setCheckable(True)
        self.muteSpeakerButton.setIcon(QIcon('assets/img/default_colored_2014/volume.svg'))
        self.muteSpeakerButton.clicked.connect(self.toggle_speaker)

        button_layout.addWidget(self.muteMicButton)
        button_layout.addWidget(self.muteSpeakerButton)
        main_layout.addLayout(button_layout)

        # Create splitter for bottom layout
        splitter_bottom = QSplitter()
        splitter_bottom.setOrientation(Qt.Vertical)
        main_layout.addWidget(splitter_bottom)

        # Top part of bottom layout (splitter_top)
        splitter_bottom.addWidget(splitter_top)

        # Console
        self.console = QTextEdit()
        self.console.setReadOnly(True)
        splitter_bottom.addWidget(self.console)

        # Message input layout
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
            self.play_sound('assets/sound/mic_muted.wav')
        else:
            self.unmute_mic()
            self.muteMicButton.setIcon(QIcon('assets/img/default_colored_2014/capture.svg'))
            self.play_sound('assets/sound/mic_activated.wav')

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
            self.play_sound('assets/sound/sound_muted.wav')
        else:
            self.unmute_speaker()
            self.muteSpeakerButton.setIcon(QIcon('assets/img/default_colored_2014/volume.svg'))
            self.play_sound('assets/sound/sound_resumed.wav')

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

    async def receive_messages(self):
        try:
            async for message in self.websocket:
                if isinstance(message, bytes):
                    self.play_audio(message)
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
        except websockets.ConnectionClosed:
            self.log_message("Connection closed")

    def play_sound(self, sound_file):
        self.media_player.setMedia(QMediaContent(QUrl.fromLocalFile(sound_file)))
        self.media_player.play()

    #Connect dialog for connecting to a server
    def show_connect_dialog(self):
        dialog = ConnectDialog()
        if dialog.exec_() == QDialog.Accepted:
            server_address, password, name = dialog.get_connection_info()
            self.current_username = name
            asyncio.ensure_future(self.connect_to_server(server_address, password, name))

    #Bookmarks management
    def show_manage_bookmarks_dialog(self):
        dialog = ManageBookmarksDialog(self.bookmarks, self.save_bookmarks_to_file)
        if dialog.exec_():
            self.refresh_bookmarks_menu()

    def load_bookmarks_from_file(self):
        try:
            # Open the file in read mode or create it if it doesn't exist
            with open('bookmarks.json', 'r') as file:
                self.bookmarks = json.load(file)
        except FileNotFoundError:
            print("Bookmarks file not found. A new one will be created.")
            self.bookmarks = []
            self.save_bookmarks_to_file()  # Create the file immediately if not found
        except json.JSONDecodeError as e:
            # Handle cases where the file is corrupted and cannot be parsed
            print(f"Failed to load bookmarks due to JSON decoding error: {str(e)}")
            self.bookmarks = []

    def save_bookmarks_to_file(self):
        try:
            # Ensure the file is created if it doesn't exist and open for writing
            with open('bookmarks.json', 'w') as file:
                json.dump(self.bookmarks, file)
        except IOError as e:
            print(f"Failed to save bookmarks: {str(e)}")

    def refresh_bookmarks_menu(self):
        self.bookmarksMenu.clear()  # Clear existing menu items

        # Add fixed menu items
        addBookmarkAction = QAction(QIcon('assets/img/default_colored_2014/bookmark_add.svg'),'Add Bookmark', self)
        addBookmarkAction.triggered.connect(lambda: self.show_manage_bookmarks_dialog())
        self.bookmarksMenu.addAction(addBookmarkAction)

        manageBookmarksAction = QAction(QIcon('assets/img/default_colored_2014/bookmark_manager.svg'),'Manage Bookmarks', self)
        manageBookmarksAction.triggered.connect(self.show_manage_bookmarks_dialog)
        self.bookmarksMenu.addAction(manageBookmarksAction)
        self.bookmarksMenu.addSeparator()

        # Dynamically add bookmarks
        for bookmark in self.bookmarks:
            action = QAction(QIcon('assets/img/default_colored_2014/server_green.svg'),bookmark['name'], self)
            action.triggered.connect(lambda checked, b=bookmark: self.connect_to_bookmark(b))
            self.bookmarksMenu.addAction(action)

    def connect_to_bookmark(self, bookmark):
        print(f"Connecting to {bookmark['name']} at {bookmark['address']}")
        asyncio.ensure_future(self.connect_to_server(bookmark['address'], bookmark['password'], bookmark['nickname']))

    #To show settings window
    def show_settings_dialog(self):
        dialog = SettingsDialog(self)
        dialog.exec_()

    #Opens the website for Pyspeak
    def open_website(self):
        webbrowser.open('https://www.aftonbladet.se')

    # Show about PyQt dialog
    def show_aboutPySpeak_dialog(self):
        dialog = AboutPySpeak(self)
        dialog.exec_()

    # Show about PyQt dialog
    def show_aboutPyQT_dialog(self):
        dialog = AboutPyQT(self)
        dialog.exec_()

    # Show changelog dialog
    def show_changelog_dialog(self):
        dialog = ChangelogDialog(self.changelog_file, self)
        dialog.exec_()

    #Server connections
    async def connect_to_server(self, server_address, password, name):
        try:
            self.log_message(f"trying to connect to server on {server_address}")
            self.websocket = await websockets.connect(f'ws://{server_address}')
            await self.websocket.send(json.dumps({'type': 'join', 'username': name, 'password': password}))
            self.log_message(f"Connected to {server_address} as {name}")
            self.current_username = name
            self.play_sound('assets/sound/connected.wav')

            asyncio.ensure_future(self.receive_messages())
        except Exception as e:
            self.log_message(f"Failed to connect: {str(e)}")

    async def disconnect_from_server(self):
        if self.websocket:
            await self.websocket.close()
            self.websocket = None
            self.log_message("Disconnected from server")
            self.play_sound('assets/sound/disconnected.wav')
            self.roomList.clear()
            self.userInfo.clear()

    def update_talking_status(self, username, is_talking):
        for i in range(self.userInfo.count()):
            item = self.userInfo.item(i)
            if item.text().strip() == username:
                icon = QIcon('assets/img/talking_icon.png') if is_talking else QIcon('assets/img/nottalking_icon.png')
                item.setIcon(icon)
                break

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
            # Kontrollera om rummet är lösenordsskyddat
            room_icon = QIcon('assets/img/default_colored_2014/channel_yellow.svg') if room_data['password'] else QIcon('assets/img/default_colored_2014/channel_green.svg')

            # Lägg till rumsnamn indenterat ett steg
            room_item = QListWidgetItem(f"  {room}")
            room_item.setIcon(room_icon)
            self.roomList.addItem(room_item)
            for user in room_data['members']:
                # Lägg till användarnamn indenterat ytterligare ett steg
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
                self.stop_audio_stream()  # Stop the current audio stream
                self.start_audio_stream()  # Start a new audio stream for the new room
                self.play_sound('assets/sound/channel_switched.wav')
        else:
            asyncio.ensure_future(self.websocket.send(json.dumps({'type': 'switch_room', 'new_room': room_name})))
            self.stop_audio_stream()  # Stop the current audio stream
            self.start_audio_stream()
            self.play_sound('assets/sound/channel_switched.wav')

    def send_message(self, name):
        message = self.messageInput.text()
        if message and self.websocket:
            asyncio.ensure_future(self.websocket.send(json.dumps({'type': 'message', 'message': message, 'username': name})))
            self.messageInput.clear()

    def log_message(self, message):
        timestamp = datetime.now().strftime('%H:%M:%S')
        self.console.append(f"{timestamp} - {message}")

#Running of main application
if __name__ == '__main__':
    app = QApplication(sys.argv)
    app.setWindowIcon(QIcon('assets/img/icon.png'))
    loop = qasync.QEventLoop(app)
    asyncio.set_event_loop(loop)

    client = VoiceChatClient()
    client.show()
    print('Starting client')
    loop.run_forever()
