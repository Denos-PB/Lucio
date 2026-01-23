import base64
import threading
import time
from PIL import ImageGrab
import io
from typing import Callable, Optional

class ScreenStreamer:
    def __init__(self, interval: float = 1.0):
        self.interval = interval
        self.is_streaming = False
        self.thread: Optional[threading.Thread] = None
        self.latest_frame: Optional[str] = None
        self.callback: Optional[Callable] = None

    def capture_screen(self) -> str:
        screenshot = ImageGrab.grab()
        buffered = io.BytesIO()
        screenshot.save(buffered, format="png")
        img_base64 = base64.b64encode(buffered.getvalue()).decode()
        return img_base64

    def start_streaming(self, callback: Optional[Callable] = None):
        if self.is_streaming:
            return
        
        self.is_streaming = True
        self.callback = callback
        self.thread = threading.Thread(target=self._stream_loop, daemon=True)
        self.thread.start()

    def _stream_loop(self):
        while self.is_streaming:
            try:
                self.latest_frame = self.capture_screen()

                if self.callback:
                    self.callback(self.latest_frame)

                time.sleep(self.interval)

            except Exception as e:
                print(f"Streaming error: {e}")
                break

    def stop_streaming(self):
        self.is_streaming = False
        if self.thread:
            self.thread.join(timeout=2)

    def get_latest_frame(self) -> Optional[str]:
        return self.latest_frame

screen_streamer = ScreenStreamer(interval=1.0)

def start_screen_stream(interval: float = 1.0):
    screen_streamer.interval = interval
    screen_streamer.start_streaming()

def stop_screen_stream():
    screen_streamer.stop_streaming()

def get_current_screen() -> Optional[str]:
    return screen_streamer.get_latest_frame()