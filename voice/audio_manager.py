import pyaudio


class AudioManager:
    def __init__(self, device_index: int = None, sample_rate: int = 16000):
        self.pa = pyaudio.PyAudio()
        self.device_index = device_index
        self.sample_rate = sample_rate
        self.stream = None

    def open(self, frames_per_buffer: int = 1280):
        self.stream = self.pa.open(
            format=pyaudio.paInt16,
            channels=1,
            rate=self.sample_rate,
            input=True,
            input_device_index=self.device_index,
            frames_per_buffer=frames_per_buffer,
        )

    def read(self, length: int) -> bytes:
        return self.stream.read(length, exception_on_overflow=False)

    def close(self):
        if self.stream:
            self.stream.stop_stream()
            self.stream.close()
        self.pa.terminate()
