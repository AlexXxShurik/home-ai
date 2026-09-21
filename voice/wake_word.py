import logging
import numpy as np
from openwakeword.model import Model

from audio_manager import AudioManager

logger = logging.getLogger(__name__)


def _downsample(data: bytes, from_rate: int, to_rate: int) -> bytes:
    if from_rate == to_rate:
        return data
    audio = np.frombuffer(data, dtype=np.int16)
    ratio = from_rate // to_rate
    if ratio > 1:
        audio = audio[::ratio]
    return audio.tobytes()


class WakeWordDetector:
    def __init__(self, model_path: str, audio: AudioManager, threshold: float = 0.5):
        try:
            self.model = Model(wakeword_models=[model_path], inference_framework="onnx")
        except TypeError:
            self.model = Model(wakeword_model_paths=[model_path])
        self.threshold = threshold
        self.audio = audio
        self.detect_count = 0

    def reset(self):
        self.model.reset()

    def listen(self) -> tuple[bool, float]:
        data = self.audio.read(1280)
        if not data or len(data) < 800:
            return False, 0.0
        data = _downsample(data, self.audio.effective_rate, 16000)
        audio = np.frombuffer(data, dtype=np.int16)
        if len(audio) < 400:
            return False, 0.0
        audio = np.clip(audio * 5, -32768, 32767).astype(np.int16)

        prediction = self.model.predict(audio)
        score = max(prediction.values()) if prediction else 0.0

        return score >= self.threshold, score
