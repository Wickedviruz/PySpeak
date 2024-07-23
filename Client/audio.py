import pyaudio
import numpy as np
import collections
import asyncio
import json
from PyQt5.QtCore import QThread

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
        self.loop = loop
        self.talking_threshold = 500
        self.silence_threshold = 300
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
