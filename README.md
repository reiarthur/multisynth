# multisynth

[![PyPI version](https://img.shields.io/pypi/v/multisynth.svg)](https://pypi.org/project/multisynth/)
[![Python versions](https://img.shields.io/pypi/pyversions/multisynth.svg)](https://pypi.org/project/multisynth/)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

`multisynth` is a typed, multimodal Python library that wraps multiple AI providers behind a single public API for:

- **Text generation** — chat, instructions, reasoning, tool use, batch
- **Speech transcription** — audio to text with word timings and speaker diarization
- **Speech synthesis** — text to spoken audio
- **Music generation** — text prompt to instrumental audio
- **Image generation** — text to image
- **Image transformation** — prompt + input image to new image
- **Image editing** — inpainting with optional mask
- **Video generation** — text/image/audio to video
- **Lip sync** — animate a face image with an audio track

All operations are available in synchronous and asynchronous variants. Provider names are resolved through a flexible alias system, so `"gemini"`, `"google"`, and `"google-ai"` all map to the same adapter.

## Requirements

- Python 3.12 or higher
- Dependencies installed automatically: `httpx`, `pydantic`, `Pillow`

## Install

```bash
pip install multisynth
```

For local development (includes test and lint tools):

```bash
pip install -e ".[dev]"
```

## Checking the version

```python
import multisynth

print(multisynth.__version__)
```

## Configuration

Credentials are resolved lazily, in this order:

1. Explicit `credentials={...}` values passed to a call or to `Multisynth(...)`.
2. Environment variables from the current process.

`multisynth` does **not** auto-load `.env` files, keeping imports side-effect free.

### Environment variable setup

```bash
cp .env.example .env
# Edit .env and fill only the providers you plan to use
export OPENAI_API_KEY="sk-..."
export GOOGLE_API_KEY="..."
```

If your application uses `python-dotenv`, load it in the application entrypoint — not inside the library:

```python
from dotenv import load_dotenv

load_dotenv()
```

See [`docs/configuration.md`](docs/configuration.md) for full details and per-call credential override patterns.

---

## Quickstart

### Text generation

```python
from multisynth.text import generate

result = generate(
    provider="openai",
    instructions="Write a short slogan about rain in one sentence.",
    credentials={"OPENAI_API_KEY": "sk-..."},
)

print(result.text)
print(result.cost_usd)
```

### Speech transcription

```python
from multisynth.audio import transcribe

result = transcribe(
    provider="deepgram",
    audio="/path/to/recording.mp3",
    credentials={"DEEPGRAM_API_KEY": "..."},
)

print(result.text)

for word in result.words:
    print(word.text, word.start_seconds, word.end_seconds)

for segment in result.speaker_segments:
    print(segment.speaker, segment.text)
```

### Speech synthesis

```python
from multisynth.audio import synthesize

result = synthesize(
    provider="elevenlabs",
    text="Hello, this is a test of text-to-speech synthesis.",
    credentials={"ELEVENLABS_API_KEY": "..."},
)

import base64
audio_bytes = base64.b64decode(result.audio_base64)
with open("output.mp3", "wb") as f:
    f.write(audio_bytes)
```

### Music generation

```python
from multisynth.audio import compose

result = compose(
    provider="stability",
    prompt="Upbeat lo-fi hip-hop, 80 BPM, mellow piano and drums",
    duration_seconds=30,
    credentials={"STABILITY_API_KEY": "..."},
)

import base64
audio_bytes = base64.b64decode(result.audio_base64)
with open("music.mp3", "wb") as f:
    f.write(audio_bytes)
```

### Image generation

```python
from multisynth.image import generate

result = generate(
    provider="openai",
    prompt="A cinematic lighthouse in a storm, dramatic lighting",
    credentials={"OPENAI_API_KEY": "sk-..."},
)

import base64
image_bytes = base64.b64decode(result.image_base64)
with open("output.png", "wb") as f:
    f.write(image_bytes)
```

### Image transformation

Takes an existing image and transforms it according to a prompt.

```python
from multisynth.image import transform

result = transform(
    provider="stability",
    prompt="Turn this photo into a watercolor painting",
    image="/path/to/photo.jpg",
    strength=0.75,
    credentials={"STABILITY_API_KEY": "..."},
)

import base64
image_bytes = base64.b64decode(result.image_base64)
with open("transformed.png", "wb") as f:
    f.write(image_bytes)
```

### Image editing

Edits specific regions of an image using a prompt. Pass a `mask` to limit edits to the masked area.

```python
from multisynth.image import edit

result = edit(
    provider="openai",
    prompt="Replace the sky with a dramatic sunset",
    image="/path/to/photo.png",
    mask="/path/to/mask.png",  # white areas are edited, black areas are preserved
    credentials={"OPENAI_API_KEY": "sk-..."},
)

import base64
image_bytes = base64.b64decode(result.image_base64)
with open("edited.png", "wb") as f:
    f.write(image_bytes)
```

### Video generation

Video files are written directly to a local path. Long-running jobs are polled until completion.

```python
from multisynth.video import generate

result = generate(
    provider="runway",
    prompt="A slow pan across a misty mountain valley at dawn",
    output_path="output.mp4",
    credentials={"RUNWAYML_API_SECRET": "..."},
)

print(result.output_path)  # pathlib.Path to the written file
```

To generate a video driven by both a reference image and an audio track:

```python
from multisynth.video import generate

result = generate(
    provider="heygen",
    image="/path/to/avatar.jpg",
    audio="/path/to/voiceover.mp3",
    output_path="avatar_video.mp4",
    credentials={"HEYGEN_API_KEY": "..."},
)
```

### Lip sync

Animate a still image or avatar portrait using a supplied audio track.

```python
from multisynth.video import lipsync

result = lipsync(
    provider="heygen",
    image="/path/to/face.jpg",
    audio="/path/to/speech.mp3",
    output_path="lipsync.mp4",
    credentials={"HEYGEN_API_KEY": "..."},
)

print(result.output_path)
```

---

## Stateful client

Use `Multisynth` to share credentials and default settings across many calls:

```python
from multisynth import Multisynth

client = Multisynth(
    credentials={"OPENAI_API_KEY": "sk-..."},
    timeout_seconds=90,
    job_timeout_seconds=900,
    max_retries=4,
)

text_result = client.text.generate(
    provider="openai",
    instructions="Summarize this in 3 bullets.",
    context={"topic": "multimodal AI libraries"},
)

image_result = client.image.generate(
    provider="openai",
    prompt="Abstract geometric art in blue and gold",
)
```

---

## Async example

Every helper has an `_async` variant. Combine them with `asyncio.gather` for concurrent requests:

```python
import asyncio

from multisynth.image import generate_async
from multisynth.text import generate_async as text_generate_async


async def main() -> None:
    text_task = text_generate_async(
        provider="openai",
        instructions="Write a one-sentence product description for a smart umbrella.",
        credentials={"OPENAI_API_KEY": "sk-..."},
    )
    image_task = generate_async(
        provider="openai",
        prompt="A smart umbrella with solar panels and an LED display",
        credentials={"OPENAI_API_KEY": "sk-..."},
    )

    text_result, image_result = await asyncio.gather(text_task, image_task)
    print(text_result.text)
    print(image_result.image_base64[:32])


asyncio.run(main())
```

---

## Public API

### `multisynth.text`

```python
from multisynth.text import batch_generate, batch_generate_async, generate, generate_async
from multisynth.models import TextGenerationRequest, TextGenerationResult
```

| Function | Description |
|---|---|
| `generate(provider, instructions, ...)` | Generate text from a single prompt. |
| `generate_async(...)` | Async variant. |
| `batch_generate(requests, ...)` | Run multiple requests to the same provider concurrently. |
| `batch_generate_async(...)` | Async variant. |

### `multisynth.audio`

```python
from multisynth.audio import (
    compose, compose_async,
    synthesize, synthesize_async,
    transcribe, transcribe_async,
)
from multisynth.models import (
    MusicGenerationRequest, MusicGenerationResult,
    SpeechSynthesisRequest, SpeechSynthesisResult,
    SpeechTranscriptionRequest, SpeechTranscriptionResult,
)
```

| Function | Description |
|---|---|
| `transcribe(provider, audio, ...)` | Transcribe audio to text with word timings and speaker diarization. |
| `synthesize(provider, text, ...)` | Synthesize speech audio from text. |
| `compose(provider, prompt, ...)` | Generate instrumental music from a text prompt. |

### `multisynth.image`

```python
from multisynth.image import (
    edit, edit_async,
    generate, generate_async,
    transform, transform_async,
)
from multisynth.models import (
    ImageEditRequest,
    ImageGenerationRequest,
    ImageResult,
    ImageTransformationRequest,
)
```

| Function | Description |
|---|---|
| `generate(provider, prompt, ...)` | Generate an image from a text prompt. |
| `transform(provider, prompt, image, ...)` | Transform an input image guided by a prompt. |
| `edit(provider, prompt, image, ...)` | Edit an image region with an optional mask. |

### `multisynth.video`

```python
from multisynth.video import generate, generate_async, lipsync, lipsync_async
from multisynth.models import LipSyncRequest, VideoGenerationRequest, VideoResult
```

| Function | Description |
|---|---|
| `generate(provider, output_path, ...)` | Generate a video. Accepts optional `prompt`, `image`, and `audio`. |
| `lipsync(provider, image, audio, output_path, ...)` | Animate a face image with a supplied audio track. |

### Exceptions

```python
from multisynth.exceptions import (
    ConfigurationError,
    IncompatibleParameterError,
    InvalidParameterError,
    InvalidProviderResponseError,
    JobFailedError,
    MissingCredentialError,
    MultisynthError,
    PricingUnavailableError,
    ProviderTimeoutError,
    TemporaryDownloadError,
    UnsupportedModelError,
    UnsupportedProviderError,
)
```

See [`docs/errors.md`](docs/errors.md) for descriptions and handling patterns.

---

## Provider matrix

### Text

| Provider | Env var |
|---|---|
| `openai` | `OPENAI_API_KEY` |
| `groq` | `GROQ_API_KEY` |
| `together` | `TOGETHER_API_KEY` |
| `fireworks` | `FIREWORKS_API_KEY` |
| `deepseek` | `DEEPSEEK_API_KEY` |
| `openrouter` | `OPENROUTER_API_KEY` |
| `xai` | `XAI_API_KEY` |
| `mistral` | `MISTRAL_API_KEY` |
| `anthropic` | `ANTHROPIC_API_KEY` |
| `google` | `GOOGLE_API_KEY` |
| `cohere` | `COHERE_API_KEY` |
| `perplexity` | `PERPLEXITY_API_KEY` |

### Audio — transcription

| Provider | Env var |
|---|---|
| `deepgram` | `DEEPGRAM_API_KEY` |
| `assemblyai` | `ASSEMBLYAI_API_KEY` |
| `speechmatics` | `SPEECHMATICS_API_KEY` |
| `revai` | `REVAI_API_KEY` |

### Audio — synthesis

| Provider | Env var |
|---|---|
| `cartesia` | `CARTESIA_API_KEY` |
| `azure` | `AZURE_SPEECH_API_KEY`, `AZURE_SPEECH_REGION` |
| `hume` | `HUME_API_KEY` |
| `elevenlabs` | `ELEVENLABS_API_KEY` |
| `murf` | `MURF_API_KEY` |

### Audio — music

| Provider | Env var |
|---|---|
| `google` | `GOOGLE_API_KEY` |
| `elevenlabs` | `ELEVENLABS_API_KEY` |
| `stability` | `STABILITY_API_KEY` |
| `beatoven` | `BEATOVEN_API_KEY` |
| `loudly` | `LOUDLY_API_KEY` |

### Image — generate

| Provider | Env var |
|---|---|
| `openai` | `OPENAI_API_KEY` |
| `google` | `GOOGLE_API_KEY` |
| `bfl` | `BFL_API_KEY` |
| `ideogram` | `IDEOGRAM_API_KEY` |
| `stability` | `STABILITY_API_KEY` |
| `hedra` | `HEDRA_API_KEY` |

### Image — transform

| Provider | Env var |
|---|---|
| `openai` | `OPENAI_API_KEY` |
| `google` | `GOOGLE_API_KEY` |
| `bfl` | `BFL_API_KEY` |
| `ideogram` | `IDEOGRAM_API_KEY` |
| `stability` | `STABILITY_API_KEY` |

### Image — edit

| Provider | Env var |
|---|---|
| `openai` | `OPENAI_API_KEY` |
| `google` | `GOOGLE_API_KEY` |
| `bfl` | `BFL_API_KEY` |
| `ideogram` | `IDEOGRAM_API_KEY` |
| `stability` | `STABILITY_API_KEY` |

### Video — generate without audio

| Provider | Env var |
|---|---|
| `runway` | `RUNWAYML_API_SECRET` |
| `luma` | `LUMA_API_KEY` |
| `fal` | `FAL_KEY` |
| `hedra` | `HEDRA_API_KEY` |

### Video — generate with audio

| Provider | Env var |
|---|---|
| `google` | `GOOGLE_API_KEY` |
| `heygen` | `HEYGEN_API_KEY` |
| `did` | `DID_API_KEY` |
| `hedra` | `HEDRA_API_KEY` |

### Video — lip sync

| Provider | Env var |
|---|---|
| `heygen` | `HEYGEN_API_KEY` |
| `did` | `DID_API_KEY` |
| `hedra` | `HEDRA_API_KEY` |

---

## Error handling

`multisynth` uses typed exceptions so your code can handle failures intentionally.

```python
from multisynth.exceptions import MissingCredentialError, UnsupportedProviderError
from multisynth.text import generate

try:
    result = generate(provider="openai", instructions="Write one sentence.")
except MissingCredentialError as exc:
    # exc.provider — the canonical provider name
    # exc.env_vars — tuple of env var names that must be set
    print(f"Missing credentials for {exc.provider}: {exc.env_vars}")
except UnsupportedProviderError as exc:
    print(f"Unknown provider: {exc}")
```

A `MissingCredentialError` for one provider does **not** affect other providers. Package imports and unrelated operations remain fully usable.

See [`docs/errors.md`](docs/errors.md) for the full exception hierarchy and handling recommendations.

---

## Provider aliases

Many providers accept common aliases:

| Alias | Resolves to |
|---|---|
| `gemini`, `google-ai`, `imagen`, `veo`, `lyria` | `google` |
| `flux`, `black-forest-labs` | `bfl` |
| `mistralai` | `mistral` |
| `runwayml`, `runway-ml` | `runway` |
| `lumalabs`, `luma-dream-machine` | `luma` |
| `hey-gen` | `heygen` |
| `d-id` | `did` |
| `eleven-labs` | `elevenlabs` |
| `assembly-ai` | `assemblyai` |
| `pplx` | `perplexity` |

---

## Additional docs

- [`docs/configuration.md`](docs/configuration.md) — credential resolution, python-dotenv integration, per-call overrides
- [`docs/providers.md`](docs/providers.md) — complete credential tables for every provider and operation
- [`docs/errors.md`](docs/errors.md) — exception hierarchy, handling patterns, retry guidance

## Contributing

See [`CONTRIBUTING.md`](CONTRIBUTING.md) for development setup, running tests, and the release process.
