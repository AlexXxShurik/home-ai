import os
import json
import numpy as np
from vosk import Model, KaldiRecognizer

from audio_manager import AudioManager


class SpeechToText:
    def __init__(self, model_name: str = "vosk-model-small-ru-0.22", audio: AudioManager = None, sample_rate: int = 16000):
        model_path = os.path.expanduser(f"~/.cache/vosk/{model_name}")
        self.model = Model(model_path)
        self.sample_rate = audio.effective_rate if audio else sample_rate
        self.recognizer = KaldiRecognizer(self.model, self.sample_rate)
        self.audio = audio

    def _amplify(self, data: bytes) -> bytes:
        arr = np.frombuffer(data, dtype=np.int16)
        arr = np.clip(arr * 3, -32768, 32767).astype(np.int16)
        return arr.tobytes()

    def transcribe(self, max_duration: float = 10.0) -> str:
        self.recognizer.Reset()
        frames_read = 0
        max_frames = int(max_duration * self.sample_rate / 4000)

        while frames_read < max_frames:
            data = self.audio.read(4000)
            data = self._amplify(data)
            frames_read += 1

            if self.recognizer.AcceptWaveform(data):
                result = json.loads(self.recognizer.Result())
                text = result.get("text", "").strip()
                if text:
                    return text

        result = json.loads(self.recognizer.FinalResult())
        return result.get("text", "").strip()
