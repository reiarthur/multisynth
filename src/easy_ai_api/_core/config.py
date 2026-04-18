"""Configuração estática do pacote e metadados de providers.

Última atualização: 2026-04-18
"""

from __future__ import annotations

from decimal import Decimal

from .provider_catalog import KNOWN_CREDENTIAL_ENV_VARS as _KNOWN_CREDENTIAL_ENV_VARS

VERSION = "0.2.0"
USER_AGENT = f"easy-ai-api/{VERSION}"

DEFAULT_TIMEOUT_SECONDS = 60.0
DEFAULT_DOWNLOAD_TIMEOUT_SECONDS = 180.0
DEFAULT_JOB_TIMEOUT_SECONDS = 900.0
DEFAULT_INITIAL_POLL_SECONDS = 1.5
DEFAULT_MAX_POLL_SECONDS = 20.0
DEFAULT_RETRIES = 3
DEFAULT_INITIAL_BACKOFF_SECONDS = 0.8
DEFAULT_BACKOFF_MULTIPLIER = 2.0
DEFAULT_MAX_BACKOFF_SECONDS = 12.0
DEFAULT_BATCH_CONCURRENCY = 5

TOKEN_SCALE = Decimal("1000000")
COST_QUANTIZE = Decimal("0.0000001")

RUNWAY_API_VERSION = "2024-11-06"

BASE_URL_OPENAI = "https://api.openai.com/v1"
BASE_URL_GROQ = "https://api.groq.com/openai/v1"
BASE_URL_TOGETHER = "https://api.together.xyz/v1"
BASE_URL_FIREWORKS = "https://api.fireworks.ai/inference/v1"
BASE_URL_DEEPSEEK = "https://api.deepseek.com"
BASE_URL_OPENROUTER = "https://openrouter.ai/api/v1"
BASE_URL_XAI = "https://api.x.ai/v1"
BASE_URL_MISTRAL = "https://api.mistral.ai/v1"
BASE_URL_ANTHROPIC = "https://api.anthropic.com/v1"
BASE_URL_GOOGLE = "https://generativelanguage.googleapis.com/v1beta"
BASE_URL_COHERE = "https://api.cohere.com/v2"
BASE_URL_PERPLEXITY = "https://api.perplexity.ai"
BASE_URL_IDEOGRAM = "https://api.ideogram.ai"
BASE_URL_STABILITY = "https://api.stability.ai"
BASE_URL_BFL = "https://api.bfl.ai/v1"
BASE_URL_DEEPGRAM = "https://api.deepgram.com/v1"
BASE_URL_ASSEMBLYAI = "https://api.assemblyai.com/v2"
BASE_URL_SPEECHMATICS = "https://asr.api.speechmatics.com/v2"
BASE_URL_REVAI = "https://api.rev.ai/speechtotext/v1"
BASE_URL_CARTESIA = "https://api.cartesia.ai"
BASE_URL_HUME = "https://api.hume.ai/v0"
BASE_URL_ELEVENLABS = "https://api.elevenlabs.io/v1"
BASE_URL_MURF = "https://api.murf.ai/v1"
BASE_URL_BEATOVEN = "https://public-api.beatoven.ai"
BASE_URL_LOUDLY = "https://soundtracks.loudly.com"
BASE_URL_RUNWAY = "https://api.dev.runwayml.com/v1"
BASE_URL_LUMA = "https://api.lumalabs.ai/dream-machine/v1"
BASE_URL_FAL = "https://queue.fal.run"
BASE_URL_DEEPINFRA = "https://api.deepinfra.com/v1/openai"
BASE_URL_HUGGINGFACE = "https://router.huggingface.co/v1"
BASE_URL_REPLICATE = "https://api.replicate.com/v1"
BASE_URL_EDENAI = "https://api.edenai.run/v2"
BASE_URL_HEYGEN = "https://api.heygen.com/v2"
BASE_URL_DID = "https://api.d-id.com"
BASE_URL_HEDRA = "https://api.hedra.com/web-app/public"

KNOWN_CREDENTIAL_ENV_VARS = _KNOWN_CREDENTIAL_ENV_VARS
