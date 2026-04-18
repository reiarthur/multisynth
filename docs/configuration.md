# Configuration

`easy-ai-api` resolves credentials lazily:

1. values passed through `credentials={...}`
2. environment variables from the current process

The library does not load `.env` files automatically. That keeps imports side-effect free and makes runtime behavior explicit in production, CI, and server environments.

## Recommended setup flow

1. Copy `.env.example` to `.env` in your application repository.
2. Fill only the variables for providers you actually use.
3. Export them into the process that runs your Python code.

## Shell example

```bash
cp .env.example .env
export OPENAI_API_KEY="sk-..."
export IDEOGRAM_API_KEY="..."
```

## Using python-dotenv in your application

```python
from dotenv import load_dotenv

load_dotenv()
```

Use `python-dotenv` in the application entrypoint, not inside the library itself.

## Explicit credentials per call

```python
from easy_ai_api.text import generate

result = generate(
    provider="openai",
    instructions="Write one sentence about rain.",
    credentials={"OPENAI_API_KEY": "sk-..."},
)
```

## Client-wide shared credentials

```python
from easy_ai_api import EasyAiApi

client = EasyAiApi(
    credentials={"OPENAI_API_KEY": "sk-..."},
    timeout_seconds=90,
    max_retries=4,
)
```
