"""Microphone recording utilities."""
from __future__ import annotations

import queue
import sys
import tempfile
import threading
from pathlib import Path
from typing import Optional

import click
import numpy as np


class RecordingError(RuntimeError):
    """Raised when audio could not be captured from the microphone."""


class AudioRecorder:
    """Records audio from the default system microphone."""

    def __init__(self, sample_rate: int = 16_000, channels: int = 1) -> None:
        self.sample_rate = sample_rate
        self.channels = channels

    def record_to_file(self, destination: Optional[Path] = None) -> Path:
        """Capture microphone input until the user stops with SPACE.

        Returns the path to a temporary WAV file containing the audio samples.
        """

        try:
            import sounddevice as sd  # type: ignore
            import soundfile as sf  # type: ignore
        except ImportError as exc:  # pragma: no cover - optional dependency
            raise RecordingError(
                "sounddevice and soundfile must be installed. Run 'pip install voice-to-text-assistant'."
            ) from exc

        audio_queue: "queue.Queue[np.ndarray]" = queue.Queue()

        def callback(indata: np.ndarray, frames: int, time, status) -> None:  # type: ignore[override]
            if status:  # pragma: no cover - passthrough info from PortAudio
                print(f"Audio callback status: {status}", file=sys.stderr)
            audio_queue.put(indata.copy())

        print('[READY] Press SPACE to start recording (CTRL+C to cancel).')

        try:
            while True:
                key = click.getchar()
                if key == " ":
                    break
        except KeyboardInterrupt as exc:
            raise RecordingError("Recording cancelled before start.") from exc

        stop_event = threading.Event()
        cancel_event = threading.Event()

        def wait_for_stop() -> None:
            try:
                while True:
                    key = click.getchar()
                    if key == " ":
                        stop_event.set()
                        break
            except KeyboardInterrupt:
                cancel_event.set()
                stop_event.set()

        print('[REC] Recording... Press SPACE to stop (CTRL+C to cancel).')

        frames: list[np.ndarray] = []
        listener = threading.Thread(target=wait_for_stop, daemon=True)
        try:
            with sd.InputStream(
                samplerate=self.sample_rate,
                channels=self.channels,
                dtype="float32",
                callback=callback,
            ):
                listener.start()
                while not stop_event.is_set():
                    try:
                        frames.append(audio_queue.get(timeout=0.1))
                    except queue.Empty:
                        continue
        except KeyboardInterrupt:
            cancel_event.set()
            stop_event.set()
        except Exception as exc:  # pragma: no cover - pass-through from sounddevice
            raise RecordingError(f"Microphone recording failed: {exc}") from exc

        while True:
            try:
                frames.append(audio_queue.get_nowait())
            except queue.Empty:
                break

        if not frames:
            raise RecordingError("No audio captured before stop; please try again.")

        if cancel_event.is_set():
            print('[STOP] Recording stopped (CTRL+C).')
        else:
            print('[STOP] Recording stopped.')

        audio = np.concatenate(frames, axis=0)

        if destination is None:
            temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".wav")
            destination_path = Path(temp_file.name)
            temp_file.close()
        else:
            destination_path = destination

        sf.write(destination_path, audio, self.sample_rate)
        return destination_path


__all__ = ["AudioRecorder", "RecordingError"]
