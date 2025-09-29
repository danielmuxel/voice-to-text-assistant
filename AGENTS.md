# Repository Guidelines

## Project Structure & Module Organization
Core CLI code lives in `src/voice_to_markdown/`. `cli.py` wires the Click interface, `recorder.py` handles microphone capture, and `transcribers.py` hosts backend adapters for faster-whisper and OpenAI. Packaging metadata and entry points are defined in `pyproject.toml`. Generated Markdown transcripts land in `transcripts/`; treat it as runtime output and keep large artifacts out of commits.

## Build, Test, and Development Commands
- `uv sync --extra local` installs core runtime dependencies for offline transcription. Add `--extra api` when working on OpenAI features.
- `uv run voice-to-markdown --backend local --model-size small` runs the CLI with the local backend; adjust flags during manual QA.
- `uv run python -m voice_to_markdown.cli --help` regenerates the option summary when updating the interface.
- `uv run pytest` executes automated tests once `pytest` is added to dev dependencies; pin it in `pyproject.toml` under `[project.optional-dependencies]` or a `dev` extra.

## Coding Style & Naming Conventions
Follow PEP 8 with four-space indentation and keep lines under ~100 characters to match the existing files. Modules and functions use `snake_case`, classes use `PascalCase`, and Click option names stay kebab-cased (e.g., `--model-size`). Type annotations are expected for public functions, and docstrings should focus on intent and side-effects. Prefer `Path` objects for filesystem work and `console.print` for user-facing messages.

## Testing Guidelines
Automated tests live under `tests/`, mirroring the package layout (e.g., `tests/test_cli.py`). Use `pytest` with descriptive `test_<behavior>` function names and isolate audio fixtures in a `tests/fixtures/` directory. New features should include regression coverage for both local and OpenAI transcribers; mock network calls and model downloads to keep the suite fast. Run `uv run pytest` before submitting and include sample CLI outputs in the PR if manual verification is required.

## Commit & Pull Request Guidelines
Write imperative, present-tense commit subjects (`Add whisper batching`) with details in the body when behaviour changes. Squash noisy WIP commits locally. Pull requests should summarise the change, call out new dependencies or environment variables, link tracking issues, and attach CLI transcript snippets or Markdown diffs that prove the behaviour. Request review before merging and wait for tests to pass.

## Security & Configuration Tips
Never commit API keys or raw audio. Load credentials through environment variables (`OPENAI_API_KEY`) and document any new configuration flags in `README.md`. When logging, avoid echoing full file paths or secrets; redact user-specific data in transcripts shared for review.
