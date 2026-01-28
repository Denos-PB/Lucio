import os
import time
import wave
import tempfile
from dataclasses import dataclass

import numpy as np
import requests

import pvporcupine
import pyaudio

from faster_whisper import WhisperModel
from dotenv import load_dotenv

load_dotenv()

@dataclass
class Config:
    api_url: str = "http://127.0.0.1:8000/run"
    hotword: str = "lucio"
    sample_rate: int = 16000
    channels: int = 1
    record_seconds: int = 30
    silence_timeout_sec: float = 1.2
    whisper_model: str = "small"

def post_to_agent(api_url: str, prompt: str) -> dict:
    r = requests.post(api_url, json={"prompt": prompt}, timeout=600)
    r.raise_for_status()
    return r.json()

def save_wav(path:str, pcm16: bytes, sample_rate: int, channels: int = 1):
    with wave.open(path, "wb") as wf:
        wf.setnchannels(channels)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(pcm16)

def rms_int16(pcm: np.ndarray) -> float:
    if pcm.size == 0:
        return 0.0
    x = pcm.astype(np.float32)
    return float(np.sqrt(np.mean(x * x)))

def main():
    access_key = os.environ.get("PICOVOICE_ACCESS_KEY")
    if not access_key:
        raise RuntimeError("Missing PICOVOICE_ACCESS_KEY env var")

    cfg = Config()

    porcupine = pvporcupine.create(
        access_key=access_key,
        keyword_paths=["backend/resources/keywords/lucio_en_windows.ppn"],
    )

    pa = pyaudio.PyAudio()
    stream = pa.open(
        rate=porcupine.sample_rate,
        channels=1,
        format=pyaudio.paInt16,
        input=True,
        frames_per_buffer=porcupine.frame_length,
    )

    whisper = WhisperModel(cfg.whisper_model, device="cpu", compute_type="int8")

    print("Listener started. Say 'Lucio' to wake me up.")
    try:
        while True:
            pcm = stream.read(porcupine.frame_length, exception_on_overflow=False)
            frame = np.frombuffer(pcm, dtype=np.int16)

            keyword_index = porcupine.process(list(frame))
            if keyword_index < 0:
                continue

            print("Wake word detected. Listening for request...")

            recorded = bytearray()
            last_voice_time = time.time()

            start_time = time.time()
            while True:
                pcm2 = stream.read(porcupine.frame_length, exception_on_overflow=False)
                frame2 = np.frombuffer(pcm2, dtype=np.int16)
                recorded.extend(pcm2)

                energy = rms_int16(frame2)
                if energy > 300:
                    last_voice_time = time.time()
                if time.time() - start_time >= cfg.record_seconds:
                    break
                if time.time() - last_voice_time >= cfg.silence_timeout_sec:
                    break

            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
                wav_path = f.name
            save_wav(wav_path, bytes(recorded), cfg.sample_rate, cfg.channels)

            segments, info = whisper.transcribe(wav_path, language=None)
            text = " ".join(seg.text.strip() for seg in segments).strip()

            try:
                os.remove(wav_path)
            except OSError:
                pass

            if not text:
                print("No speech detected. Say 'Lucio' again.")
                continue

            print("Heard:", text)

            try:
                result = post_to_agent(cfg.api_url, text)
                print("Agent status:", result.get("status"))
                print("PDF:", result.get("pdf_file_path"))
                if result.get("errors"):
                    print("Errors:", result.get("errors"))
            except Exception as e:
                print("Failed calling agent:", e)

            time.sleep(0.5)

    finally:
        stream.stop_stream()
        stream.close()
        pa.terminate()
        porcupine.delete()


if __name__ == "__main__":
    main()