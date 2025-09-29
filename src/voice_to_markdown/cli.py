"""Command line interface for the voice-to-markdown assistant."""
from __future__ import annotations

import datetime as dt
import textwrap
from pathlib import Path
from typing import Optional

import click
from rich.console import Console

from .recorder import AudioRecorder, RecordingError
from .transcribers import (
    LocalWhisperTranscriber,
    OpenAITranscriber,
    TranscriptionError,
    TranscriptionResult,
)

console = Console()


@click.command()
@click.option(
    "--backend",
    type=click.Choice(["local", "openai"], case_sensitive=False),
    default="local",
    show_default=True,
    help="Choose between offline (local) and cloud (openai) transcription.",
)
@click.option(
    "--language",
    type=str,
    default=None,
    help="Force a language code (e.g. 'de' or 'en') instead of automatic detection.",
)
@click.option(
    "--output-dir",
    type=click.Path(path_type=Path),
    default=Path("transcripts"),
    help="Directory where markdown transcripts are stored.",
)
@click.option(
    "--input-file",
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
    default=None,
    help="Path to an existing audio file (skip live recording).",
)
@click.option(
    "--model-size",
    type=str,
    default="small",
    show_default=True,
    help="Local faster-whisper model size (tiny, base, small, medium).",
)
@click.option(
    "--device",
    type=str,
    default=None,
    help="Device override for faster-whisper (e.g. 'cuda', 'cpu').",
)
@click.option(
    "--compute-type",
    type=str,
    default="int8",
    show_default=True,
    help="faster-whisper compute type (int8, int8_float16, float16, float32).",
)
@click.option(
    "--openai-model",
    type=str,
    default="gpt-4o-mini-transcribe",
    show_default=True,
    help="Model name to use with the OpenAI backend.",
)
@click.option(
    "--openai-api-key",
    type=str,
    default=None,
    envvar="OPENAI_API_KEY",
    help="Explicit API key for OpenAI backend (defaults to env var).",
)
@click.option(
    "--no-segments",
    is_flag=True,
    help="Do not include per-segment timing details in the markdown output.",
)
def main(
    backend: str,
    language: Optional[str],
    output_dir: Path,
    input_file: Optional[Path],
    model_size: str,
    device: Optional[str],
    compute_type: str,
    openai_model: str,
    openai_api_key: Optional[str],
    no_segments: bool,
) -> None:
    """Record speech in German or English and save a markdown transcript."""

    output_dir.mkdir(parents=True, exist_ok=True)

    include_segments = not no_segments

    if input_file is not None:
        _transcribe_and_display(
            backend=backend,
            audio_path=input_file,
            language=language,
            model_size=model_size,
            device=device,
            compute_type=compute_type,
            openai_model=openai_model,
            openai_api_key=openai_api_key,
            output_dir=output_dir,
            include_segments=include_segments,
        )
        return

    recorder = AudioRecorder()

    console.print("[bold cyan]Interactive recording session started.[/bold cyan]")
    console.print("Press SPACE to capture a note. Use CTRL+C at the prompt to exit.")

    try:
        while True:
            temp_audio: Optional[Path] = None
            try:
                temp_audio = recorder.record_to_file()
            except RecordingError as exc:
                message = str(exc)
                if message == "Recording cancelled before start.":
                    console.print("[yellow]Recording session cancelled. Goodbye![/yellow]")
                    return
                console.print(f"[bold red]Recording failed:[/bold red] {message}")
                if "please try again" in message.lower():
                    continue
                raise SystemExit(1) from exc

            try:
                _transcribe_and_display(
                    backend=backend,
                    audio_path=temp_audio,
                    language=language,
                    model_size=model_size,
                    device=device,
                    compute_type=compute_type,
                    openai_model=openai_model,
                    openai_api_key=openai_api_key,
                    output_dir=output_dir,
                    include_segments=include_segments,
                )
            finally:
                if temp_audio and temp_audio.exists():
                    temp_audio.unlink(missing_ok=True)

            console.print("\n[dim]Press SPACE to record another note or CTRL+C to exit.[/dim]\n")
    except KeyboardInterrupt:
        console.print("\n[yellow]Recording session ended by user.[/yellow]")


def _run_transcription(
    *,
    backend: str,
    audio_path: Path,
    language: Optional[str],
    model_size: str,
    device: Optional[str],
    compute_type: str,
    openai_model: str,
    openai_api_key: Optional[str],
) -> TranscriptionResult:
    backend_normalized = backend.lower()
    if backend_normalized == "local":
        transcriber = LocalWhisperTranscriber(
            model_size=model_size,
            device=device,
            compute_type=compute_type,
        )
    elif backend_normalized == "openai":
        transcriber = OpenAITranscriber(model=openai_model, api_key=openai_api_key)
    else:  # pragma: no cover - guarded by click.Choice
        raise TranscriptionError(f"Unknown backend '{backend}'.")

    return transcriber.transcribe(audio_path=audio_path, language=language)


def _render_markdown(
    result: TranscriptionResult,
    *,
    target_language: Optional[str],
    include_segments: bool = True,
) -> str:
    header = dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    lines = [
        f"# Voice Note {header}",
        "",
        "## Metadata",
        f"- Backend: {result.backend}",
        f"- Requested language: {target_language or 'auto'}",
        f"- Detected language: {result.detected_language or 'unknown'}",
        f"- Transcript length (chars): {len(result.text)}",
        "",
        "## Transcript",
        "",
        result.text.strip(),
        "",
    ]

    if include_segments and result.segments:
        lines.extend(["## Timeline", ""])
        for segment in result.segments:
            start = _format_seconds(segment.start)
            end = _format_seconds(segment.end)
            snippet = segment.text.strip()
            if segment.language:
                lines.append(f"- `{start} -> {end}` ({segment.language}) {snippet}")
            else:
                lines.append(f"- `{start} -> {end}` {snippet}")
        lines.append("")

    return "\n".join(lines).strip() + "\n"


def _transcribe_and_display(
    *,
    backend: str,
    audio_path: Path,
    language: Optional[str],
    model_size: str,
    device: Optional[str],
    compute_type: str,
    openai_model: str,
    openai_api_key: Optional[str],
    output_dir: Path,
    include_segments: bool,
) -> None:
    try:
        transcription = _run_transcription(
            backend=backend,
            audio_path=audio_path,
            language=language,
            model_size=model_size,
            device=device,
            compute_type=compute_type,
            openai_model=openai_model,
            openai_api_key=openai_api_key,
        )
    except TranscriptionError as exc:
        console.print(f"[bold red]Transcription failed:[/bold red] {exc}")
        raise SystemExit(2) from exc

    timestamp = dt.datetime.now().strftime("%Y%m%d-%H%M%S")
    output_path = output_dir / f"transcript-{timestamp}.md"
    markdown = _render_markdown(
        transcription,
        target_language=language,
        include_segments=include_segments,
    )
    output_path.write_text(markdown, encoding="utf-8")

    console.print("[bold green]Transcription complete![/bold green]")
    console.print(f"Saved markdown transcript to [underline]{output_path}[/underline].")
    console.print(
        textwrap.dedent(
            f"""
            Backend: {transcription.backend}
            Requested language: {language or 'auto'}
            Detected language: {transcription.detected_language or 'unknown'}
            """
        ).strip()
    )

    console.print("\n[bold]Transcript[/bold]")
    transcript_text = transcription.text.strip()
    if transcript_text:
        console.print(transcript_text)
    else:
        console.print("[dim]No transcript text returned.[/dim]")


def _format_seconds(value: float) -> str:
    total_seconds = max(0.0, float(value))
    minutes, seconds = divmod(total_seconds, 60)
    return f"{int(minutes):02d}:{seconds:05.2f}"


__all__ = ["main"]
