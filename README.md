# Voice to Markdown Assistant

A small command-line assistant that captures spoken input in German or English, transcribes it, and stores the result in a Markdown file. Choose between an offline, open-source model (faster-whisper) or a hosted API model (OpenAI) for higher quality.

## Features
- Live microphone capture or existing audio file transcription
- Offline transcription via `faster-whisper` (tiny, base, small, medium models)
- Hosted API transcription via OpenAI's `gpt-4o-mini-transcribe` (or any compatible model)
- Markdown output with metadata, transcript text, and optional per-segment timestamps
- Console summary describing the backend, language, and output location

## Getting Started

### Prerequisites
- Python 3.10+
- Microphone access (for live recording)
- `portaudio` libraries for `sounddevice` (installed via your system package manager if missing)

### Installation (uv)
Use [uv](https://github.com/astral-sh/uv) to manage dependencies and virtual environments:

```bash
uv sync --extra local                # offline transcription only
uv sync --extra local --extra api    # offline + OpenAI backend
```

Run the CLI with uv to avoid activating the environment manually:

```bash
uv run voice-to-markdown --backend local --model-size small
```

### Alternative Installation (pip)
If you prefer a traditional virtual environment:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[local]"        # offline transcription only
pip install -e ".[local,api]"    # both offline and OpenAI backends
```

The first run of the local backend downloads the selected Whisper model. Smaller models (`tiny`, `base`) are faster; larger models (`small`, `medium`) are more accurate but require more RAM and time.

### Recording from the Microphone
```bash
voice-to-markdown --backend local --model-size small
```

- Press `SPACE` to start recording, then press `SPACE` again to stop.
- Use `CTRL+C` at any point to cancel the capture.
- The transcript text is printed in the console once transcription finishes.
- The session stays open—press `SPACE` again to record a new note or `CTRL+C` to exit.
- The transcript is saved in `transcripts/transcript-<timestamp>.md`.
- By default the language is auto-detected. Force German or English with `--language de` or `--language en`.

### Transcribing an Existing Audio File
```bash
voice-to-markdown --input-file path/to/audio.wav --backend local
```

Any format readable by `soundfile` can be used (WAV, FLAC, OGG, etc.).

### Using the OpenAI Backend
```bash
export OPENAI_API_KEY=sk-your-key
voice-to-markdown --backend openai --openai-model gpt-4o-mini-transcribe
```

Supply `--openai-api-key` on the command line if you prefer not to use environment variables. Larger models such as `gpt-4o-transcribe` offer higher quality but cost more.

### Markdown Output
The generated Markdown file contains:
- Metadata with backend, requested language, detected language, and character count
- The full transcript under `## Transcript`
- An optional `## Timeline` section with per-segment timestamps (omit with `--no-segments`)

## Troubleshooting
- **Microphone access denied**: Check OS permissions and ensure no other app is using the device.
- **`faster-whisper` import error**: Install extras via `pip install -e ".[local]"` and confirm Python can download the model files on first use.
- **OpenAI authentication errors**: Verify `OPENAI_API_KEY` and that your account has access to the requested model.
- **PortAudio backend issues on macOS/Linux**: Install system packages (`brew install portaudio` or `apt install libportaudio2`).

## Roadmap Ideas
- Add VAD-based auto-stop recording
- Provide Docker packaging for easier setup
- Support additional transcription providers (e.g. Deepgram, AssemblyAI)
