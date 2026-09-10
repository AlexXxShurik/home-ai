import os
import json
from vosk import Model, KaldiRecognizer

from audio_manager import AudioManager


class SpeechToText:
    def __init__(self, model_name: str = "vosk-model-small-ru-0.22", audio: AudioManager = None, sample_rate: int = 16000):
        model_path = os.path.expanduser(f"~/.cache/vosk/{model_name}")
        self.model = Model(model_path)
        self.sample_rate = sample_rate
        self.recognizer = KaldiRecognizer(self.model, sample_rate)
        self.audio = audio

    def transcribe(self, max_duration: float = 10.0) -> str:
        self.recognizer.Reset()
        frames_read = 0
        max_frames = int(max_duration * self.sample_rate / 4000)

        while frames_read < max_frames:
            data = self.audio.read(4000)
            frames_read += 1

            if self.recognizer.AcceptWaveform(data):
                result = json.loads(self.recognizer.Result())
                text = result.get("text", "").strip()
                if text:
                    return text

        result = json.loads(self.recognizer.FinalResult())
        return result.get("text", "").strip()
