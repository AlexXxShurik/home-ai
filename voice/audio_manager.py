import time
import numpy as np
import alsaaudio


class AudioManager:
    def __init__(self, device_index: int = None, sample_rate: int = 16000):
        self.device_index = device_index
        self.sample_rate = sample_rate
        self._pcm = None
        self._native_rate = sample_rate

    def open(self, frames_per_buffer: int = 1280):
        self._native_rate = self.sample_rate
        self._pcm = alsaaudio.PCM(
            type=alsaaudio.PCM_CAPTURE,
            mode=alsaaudio.PCM_NORMAL,
            channels=1,
            rate=self._native_rate,
            format=alsaaudio.PCM_FORMAT_S16_LE,
            periodsize=frames_per_buffer,
            device=self.device_name,
        )

    @property
    def effective_rate(self) -> int:
        return self._native_rate

    @property
    def device_name(self) -> str:
        if self.device_index is not None:
            devs = alsaaudio.pcms(alsaaudio.PCM_CAPTURE)
            if self.device_index < len(devs):
                name = devs[self.device_index]
                name = name.replace('hw:', 'plughw:', 1)
                return name
        return 'plughw:CARD=Microphone,DEV=0'

    def read(self, length: int = 1280) -> bytes:
        _length, data = self._pcm.read()
        return data

    def close(self):
        if self._pcm:
            self._pcm.close()


def find_microphone() -> int | None:
    devs = alsaaudio.pcms(alsaaudio.PCM_CAPTURE)
    for i, d in enumerate(devs):
        if 'Microphone' in d:
            return i
    for i, d in enumerate(devs):
        if d not in ('null', 'default'):
            return i
    return 0
