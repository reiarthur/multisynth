# Error Handling and Troubleshooting

`multisynth` uses typed exceptions so application code can handle failures intentionally. All exceptions inherit from `MultisynthError`.

## Exception hierarchy

```
MultisynthError
├── ConfigurationError
│   └── MissingCredentialError
├── UnsupportedProviderError
├── UnsupportedModelError
├── InvalidParameterError
├── IncompatibleParameterError
├── PricingUnavailableError
├── ProviderTimeoutError
├── JobFailedError
├── TemporaryDownloadError
└── InvalidProviderResponseError
```

## Exception descriptions

- `MultisynthError` — base class for all library exceptions. Catch this to handle any multisynth failure generically.
- `ConfigurationError` — base class for credential and configuration problems. Catch this when you want to handle any setup error without caring about the specific subtype.
- `MissingCredentialError` — the selected provider was called without the required environment variables or explicit credentials. Exposes `.provider` (canonical provider name) and `.env_vars` (tuple of variable names that must be set).
- `UnsupportedProviderError` — the provider name or alias is unknown.
- `UnsupportedModelError` — the requested model is not supported by the adapter contract.
- `InvalidParameterError` — one input value is invalid on its own (e.g., out of range, wrong type).
- `IncompatibleParameterError` — two or more inputs are individually valid but cannot be used together.
- `PricingUnavailableError` — the exact USD cost cannot be computed for the selected provider/model pair. The operation still succeeds; only `cost_usd` is unavailable.
- `ProviderTimeoutError` — the HTTP request or long-running job polling timed out.
- `JobFailedError` — a long-running provider job (video generation, transcription, etc.) completed in a failed state.
- `TemporaryDownloadError` — the provider returned a temporary download URL for a result asset, and that URL could not be fetched safely (network error, expiry, etc.).
- `InvalidProviderResponseError` — the provider returned a response shape that the adapter cannot parse. Usually indicates a provider API change or an unexpected error payload.

## Missing credentials

```python
from multisynth.exceptions import MissingCredentialError
from multisynth.text import generate

try:
    generate(provider="openai", instructions="Write one sentence.")
except MissingCredentialError as exc:
    print(exc.provider)   # "openai"
    print(exc.env_vars)   # ("OPENAI_API_KEY",)
```

A `MissingCredentialError` for one provider does **not** affect other providers. Package imports and unrelated operations remain fully usable.

## Configuration errors (generic catch)

`MissingCredentialError` is a subclass of `ConfigurationError`. Catch `ConfigurationError` when you want to handle any credential or setup failure without caring about the specific type:

```python
from multisynth.exceptions import ConfigurationError
from multisynth.text import generate

try:
    generate(provider="openai", instructions="Write one sentence.")
except ConfigurationError as exc:
    print(f"Configuration problem: {exc}")
```

## Unsupported provider or model

```python
from multisynth.exceptions import UnsupportedModelError, UnsupportedProviderError
from multisynth.text import generate

try:
    generate(provider="unknown-provider", instructions="Hello.")
except UnsupportedProviderError as exc:
    print(f"Unknown provider: {exc}")

try:
    generate(provider="openai", instructions="Hello.", model="gpt-99-ultra")
except UnsupportedModelError as exc:
    print(f"Unsupported model: {exc}")
```

## Long-running job failures

```python
from multisynth.exceptions import JobFailedError, ProviderTimeoutError
from multisynth.video import generate

try:
    result = generate(
        provider="runway",
        prompt="A slow pan across a canyon",
        output_path="out.mp4",
    )
except ProviderTimeoutError:
    print("The video job timed out. Increase `job_timeout_seconds` or retry later.")
except JobFailedError as exc:
    print(f"The video job failed on the provider side: {exc}")
```

## Pricing unavailable

`PricingUnavailableError` is raised only when pricing information is explicitly requested and cannot be computed. For text generation, `cost_usd` in the result is always populated — if pricing data is missing for the model, the library raises this error instead of returning a silent zero.

```python
from multisynth.exceptions import PricingUnavailableError
from multisynth.text import generate

try:
    result = generate(provider="openai", instructions="Hello.", model="gpt-99-ultra")
    print(result.cost_usd)
except PricingUnavailableError:
    print("No pricing data available for this model.")
```

## Best practice

- Catch `MissingCredentialError` near application startup or before user-triggered actions.
- Catch `UnsupportedProviderError` and `UnsupportedModelError` to validate configuration at boot time.
- Log `InvalidProviderResponseError` with the provider name and request metadata — it may indicate a provider API change.
- Do not retry unconditionally. The library already retries known transient network failures. Only wrap retries around `ProviderTimeoutError` or `JobFailedError` when your use case justifies it.
- For video and other long-running operations, tune `job_timeout_seconds` to match your provider's typical generation time rather than catching `ProviderTimeoutError` and retrying blindly.
