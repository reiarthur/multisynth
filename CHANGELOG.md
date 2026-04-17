# Changelog

All notable changes to this project will be documented in this file.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).
Versions follow [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [0.1.0] — 2026-04-16

### Added

#### Text generation
- `multisynth.text.generate` / `generate_async` — synchronous and async text generation with a single provider call.
- `multisynth.text.batch_generate` / `batch_generate_async` — run multiple requests to the same provider concurrently.
- Providers: `openai`, `groq`, `together`, `fireworks`, `deepseek`, `openrouter`, `xai`, `mistral`, `anthropic`, `google`, `cohere`, `perplexity`.
- Support for sampling controls (`temperature`, `top_p`, `seed`), tool use, structured output (`response_format`), reasoning (`reasoning_effort`, `thinking`), and multimodal inputs (`input_images`).

#### Audio — transcription
- `multisynth.audio.transcribe` / `transcribe_async` — transcribe audio to text with word-level timings and speaker diarization.
- Result includes `.text`, `.words` (`WordTiming`), `.speaker_segments` (`SpeakerSegment`), and `.metadata`.
- Providers: `deepgram`, `assemblyai`, `speechmatics`, `revai`.

#### Audio — speech synthesis
- `multisynth.audio.synthesize` / `synthesize_async` — synthesize spoken audio from text.
- Result includes `.audio_base64`, `.words`, and `.metadata`.
- Providers: `cartesia`, `azure`, `hume`, `elevenlabs`, `murf`.

#### Audio — music generation
- `multisynth.audio.compose` / `compose_async` — generate instrumental music from a text prompt with optional duration control.
- Result includes `.audio_base64` and `.metadata`.
- Providers: `google`, `elevenlabs`, `stability`, `beatoven`, `loudly`.

#### Image generation
- `multisynth.image.generate` / `generate_async` — generate an image from a text prompt.
- Providers: `openai`, `google`, `bfl`, `ideogram`, `stability`, `hedra`.

#### Image transformation
- `multisynth.image.transform` / `transform_async` — transform an input image guided by a prompt, with optional `strength` and `negative_prompt`.
- Providers: `openai`, `google`, `bfl`, `ideogram`, `stability`.

#### Image editing
- `multisynth.image.edit` / `edit_async` — edit an image with an optional mask for inpainting.
- Providers: `openai`, `google`, `bfl`, `ideogram`, `stability`.

#### Video generation
- `multisynth.video.generate` / `generate_async` — generate a video from a prompt, image, or audio. Routes automatically to the `without_audio` or `with_audio` registry depending on whether `audio` is supplied.
- Video files are written directly to `output_path` on the local filesystem.
- Providers (without audio): `runway`, `luma`, `fal`, `hedra`.
- Providers (with audio): `google`, `heygen`, `did`, `hedra`.

#### Lip sync
- `multisynth.video.lipsync` / `lipsync_async` — animate a still image or avatar portrait with a supplied audio track.
- Providers: `heygen`, `did`, `hedra`.

#### Stateful client
- `multisynth.Multisynth` — optional stateful client that shares credentials and request defaults (`timeout_seconds`, `job_timeout_seconds`, `max_retries`) across all modality helpers.

#### Core infrastructure
- Typed exception hierarchy (`MultisynthError`, `ConfigurationError`, `MissingCredentialError`, and nine specialised subclasses).
- Lazy credential resolution: explicit `credentials={...}` first, then environment variables.
- Flexible provider alias system (e.g., `"gemini"` → `"google"`, `"flux"` → `"bfl"`, `"runwayml"` → `"runway"`).
- Unified async HTTP client with configurable retry and exponential backoff.
- Polling helper for long-running provider jobs.
- Pricing calculation for text generation (where pricing data is available).
- Pydantic v2 models for all public request and result types.
- `py.typed` marker for PEP 561 type-checking support.
- Full test suite covering all modalities with fake adapters and integration-style configuration tests.
