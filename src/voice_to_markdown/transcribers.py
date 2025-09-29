"""Transcription backends for the voice-to-markdown assistant."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List, Optional, Protocol


class TranscriptionError(RuntimeError):
    """Base error raised when a transcription backend fails."""


@dataclass
class TranscriptSegment:
    start: float
    end: float
    text: str
    language: Optional[str] = None


@dataclass
class TranscriptionResult:
    text: str
    segments: List[TranscriptSegment]
    detected_language: Optional[str] = None
    backend: Optional[str] = None


class Transcriber(Protocol):
    def transcribe(self, audio_path: Path, language: Optional[str] = None) -> TranscriptionResult:
        ...


class LocalWhisperTranscriber:
    """Offline transcription powered by faster-whisper."""

    def __init__(
        self,
        model_size: str = "small",
        device: Optional[str] = None,
        compute_type: str = "int8",
    ) -> None:
        try:
            from faster_whisper import WhisperModel  # type: ignore
        except ImportError as exc:  # pragma: no cover - optional dependency
            raise TranscriptionError(
                "faster-whisper is not installed. Install with 'pip install voice-to-text-assistant[local]'"
            ) from exc

        self._model_size = model_size
        self._device = device or "auto"
        self._compute_type = compute_type
        self._model = WhisperModel(
            model_size,
            device=self._device,
            compute_type=compute_type,
        )

    def transcribe(self, audio_path: Path, language: Optional[str] = None) -> TranscriptionResult:
        segments_iter, info = self._model.transcribe(
            str(audio_path),
            beam_size=5,
            language=language,
            vad_filter=True,
        )

        segments = _segments_from_iterable(segments_iter)
        text = " ".join(segment.text.strip() for segment in segments).strip()
        detected_language = getattr(info, "language", None)
        return TranscriptionResult(
            text=text,
            segments=segments,
            detected_language=detected_language,
            backend=f"faster-whisper/{self._model_size}",
        )


class OpenAITranscriber:
    """Cloud transcription using OpenAI's Audio API."""

    def __init__(self, model: str = "gpt-4o-mini-transcribe", api_key: Optional[str] = None) -> None:
        try:
            from openai import OpenAI  # type: ignore
        except ImportError as exc:  # pragma: no cover - optional dependency
            raise TranscriptionError(
                "openai is not installed. Install with 'pip install voice-to-text-assistant[api]'"
            ) from exc

        key = api_key or _get_env("OPENAI_API_KEY")
        if not key:
            raise TranscriptionError(
                "OpenAI API key not configured. Set the OPENAI_API_KEY environment variable."
            )

        self._model = model
        self._client = OpenAI(api_key=key)

    def transcribe(self, audio_path: Path, language: Optional[str] = None) -> TranscriptionResult:
        from openai.types.audio import Transcription  # type: ignore

        with audio_path.open("rb") as audio_file:
            response: Transcription = self._client.audio.transcriptions.create(
                model=self._model,
                file=audio_file,
                language=language,
                temperature=0,
                response_format="verbose_json",
            )

        segments = [
            TranscriptSegment(
                start=getattr(segment, "start", 0.0) or 0.0,
                end=getattr(segment, "end", 0.0) or 0.0,
                text=getattr(segment, "text", ""),
                language=getattr(segment, "language", None),
            )
            for segment in getattr(response, "segments", []) or []
        ]
        text = getattr(response, "text", "").strip()
        detected_language = getattr(response, "language", None)
        return TranscriptionResult(
            text=text,
            segments=segments,
            detected_language=detected_language,
            backend=f"openai/{self._model}",
        )


def _get_env(var_name: str) -> Optional[str]:
    import os

    return os.environ.get(var_name)


def _segments_from_iterable(segments: Iterable) -> List[TranscriptSegment]:
    collected: List[TranscriptSegment] = []
    for raw in segments:
        start = float(getattr(raw, "start", 0.0) or 0.0)
        end = float(getattr(raw, "end", 0.0) or 0.0)
        text = getattr(raw, "text", "").strip()
        language = getattr(raw, "language", None)
        collected.append(TranscriptSegment(start=start, end=end, text=text, language=language))
    return collected


__all__ = [
    "Transcriber",
    "TranscriptionError",
    "TranscriptionResult",
    "TranscriptSegment",
    "LocalWhisperTranscriber",
    "OpenAITranscriber",
]
