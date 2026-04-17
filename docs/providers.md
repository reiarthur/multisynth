# Provider Credentials

The tables below describe the public provider matrix and the environment variables each provider requires.

## Text generation

| Provider | Env vars |
| --- | --- |
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

## Audio

### Transcription

| Provider | Env vars |
| --- | --- |
| `deepgram` | `DEEPGRAM_API_KEY` |
| `assemblyai` | `ASSEMBLYAI_API_KEY` |
| `speechmatics` | `SPEECHMATICS_API_KEY` |
| `revai` | `REVAI_API_KEY` |

### Speech synthesis

| Provider | Env vars |
| --- | --- |
| `cartesia` | `CARTESIA_API_KEY` |
| `azure` | `AZURE_SPEECH_API_KEY`, `AZURE_SPEECH_REGION` |
| `hume` | `HUME_API_KEY` |
| `elevenlabs` | `ELEVENLABS_API_KEY` |
| `murf` | `MURF_API_KEY` |

### Music generation

| Provider | Env vars |
| --- | --- |
| `google` | `GOOGLE_API_KEY` |
| `elevenlabs` | `ELEVENLABS_API_KEY` |
| `stability` | `STABILITY_API_KEY` |
| `beatoven` | `BEATOVEN_API_KEY` |
| `loudly` | `LOUDLY_API_KEY` |

## Image

### Generate

| Provider | Env vars |
| --- | --- |
| `openai` | `OPENAI_API_KEY` |
| `google` | `GOOGLE_API_KEY` |
| `bfl` | `BFL_API_KEY` |
| `ideogram` | `IDEOGRAM_API_KEY` |
| `stability` | `STABILITY_API_KEY` |
| `hedra` | `HEDRA_API_KEY` |

### Transform

| Provider | Env vars |
| --- | --- |
| `openai` | `OPENAI_API_KEY` |
| `google` | `GOOGLE_API_KEY` |
| `bfl` | `BFL_API_KEY` |
| `ideogram` | `IDEOGRAM_API_KEY` |
| `stability` | `STABILITY_API_KEY` |

### Edit

| Provider | Env vars |
| --- | --- |
| `openai` | `OPENAI_API_KEY` |
| `google` | `GOOGLE_API_KEY` |
| `bfl` | `BFL_API_KEY` |
| `ideogram` | `IDEOGRAM_API_KEY` |
| `stability` | `STABILITY_API_KEY` |

## Video

### Generate without audio

| Provider | Env vars |
| --- | --- |
| `runway` | `RUNWAYML_API_SECRET` |
| `luma` | `LUMA_API_KEY` |
| `fal` | `FAL_KEY` |
| `hedra` | `HEDRA_API_KEY` |

### Generate with audio

| Provider | Env vars |
| --- | --- |
| `google` | `GOOGLE_API_KEY` |
| `heygen` | `HEYGEN_API_KEY` |
| `did` | `DID_API_KEY` |
| `hedra` | `HEDRA_API_KEY` |

### Lip sync

| Provider | Env vars |
| --- | --- |
| `heygen` | `HEYGEN_API_KEY` |
| `did` | `DID_API_KEY` |
| `hedra` | `HEDRA_API_KEY` |
