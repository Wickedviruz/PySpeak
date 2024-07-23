import pyaudio
import wave
import json
import numpy as np
from settings import load_settings_from_db, save_settings_to_db
from PyQt5.QtCore import Qt, QThread
from PyQt5.QtGui import QIcon, QPainter
from PyQt5.QtWidgets import ( 
    QWidget, 
    QVBoxLayout, 
    QHBoxLayout, 
    QPushButton, 
    QLineEdit, 
    QSlider, 
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


class ConnectDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
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
    def __init__(self, bookmarks, save_func, parent=None):
        super().__init__(parent)
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

        save_settings_to_db(settings)
        self.accept()

    def load_settings(self):
        try:
            settings = load_settings_from_db()
            
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
        except Exception as e:
            print(f"Failed to load settings: {str(e)}")

class PasswordDialog(QDialog):
    def __init__(self, room_name, parent=None):
        super().__init__(parent)
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
