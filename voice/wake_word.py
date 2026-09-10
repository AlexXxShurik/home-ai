import logging
import numpy as np
from openwakeword.model import Model

from audio_manager import AudioManager

logger = logging.getLogger(__name__)


class WakeWordDetector:
    def __init__(self, model_path: str, audio: AudioManager, threshold: float = 0.5):
        self.model = Model(wakeword_models=[model_path], inference_framework="onnx")
        self.threshold = threshold
        self.audio = audio
        self.detect_count = 0

    def reset(self):
        self.model.reset()

    def listen(self) -> tuple[bool, float]:
        data = self.audio.read(1280)
        audio = np.frombuffer(data, dtype=np.int16)

        prediction = self.model.predict(audio)
        score = max(prediction.values()) if prediction else 0.0

        return score >= self.threshold, score
