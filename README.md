# brijyt-python-util

Shared Python utilities for Brijyt APIs: structured JSON logging, correlation ID context, and Starlette middleware.

## Installation

From Git (recommended: pin to a tag):

```bash
pip install "brijyt-python-util @ git+https://github.com/Brijyt/brijyt-python-util.git@v0.1.0"
```

Or from the main branch:

```bash
pip install "brijyt-python-util @ git+https://github.com/Brijyt/brijyt-python-util.git@main"
```

## Features

- **JSON logging**: Structured logs with `@timestamp`, `level`, `msg`, `method`, `correlationId`, `version`, and optional extra fields.
- **Correlation ID**: Context-local correlation ID via `contextvars`, readable and writable across the request lifecycle.
- **Log context**: Bind extra key-value pairs (e.g. `userId`) that are included in every log line.
- **CorrelationIdMiddleware**: Starlette/FastAPI middleware that reads or generates `X-Correlation-Id` and propagates it in the response.

## Usage

### Logging

Call `configure_logging(api_version)` once at startup, then use `get_logger` in your modules. The logger supports both keyword arguments (like structlog) and format strings.

```python
from brijyt_util import configure_logging, get_logger

configure_logging(api_version="1.0.0")
logger = get_logger(__name__)

logger.info("message", key="value")
logger.error("Error: %s", str(e))
```

Log level is controlled by the `LOG_LEVEL` environment variable (default: `INFO`). Only the `app` logger is configured; third-party loggers (uvicorn, crewai, LiteLLM, etc.) are set to WARNING to reduce noise.

### Correlation ID middleware (FastAPI / Starlette)

Add the middleware so every request gets a correlation ID (from the `X-Correlation-Id` header or a generated UUID) and it is set in the logging context and returned in the response.

```python
from fastapi import FastAPI
from brijyt_util import CorrelationIdMiddleware, configure_logging

app = FastAPI()
configure_logging("1.0.0")
app.add_middleware(CorrelationIdMiddleware)
```

Header name is available as `CORRELATION_ID_HEADER` (`"X-Correlation-Id"`).

### Context and correlation ID

Use context helpers when you need to read or set the correlation ID, or bind extra fields to the log context (e.g. for async or worker code that doesn’t go through the middleware).

```python
from brijyt_util import (
    get_correlation_id,
    set_correlation_id,
    bind_contextvars,
    unbind_contextvars,
    get_log_context,
)

set_correlation_id("req-123")
bind_contextvars(userId="user-456")
ctx = get_log_context()  # {"correlationId": "req-123", "userId": "user-456"}
unbind_contextvars("userId")
```

## Public API

| Export | Description |
|--------|-------------|
| `configure_logging(api_version: str)` | Configure JSON logging for the `app` logger. |
| `get_logger(name: str)` | Return a `LoggerAdapter` for the given module name. |
| `get_correlation_id()` | Return the current correlation ID. |
| `set_correlation_id(correlation_id: str)` | Set the correlation ID for the current context. |
| `bind_contextvars(**kwargs)` | Add key-value pairs to the log context. |
| `unbind_contextvars(*keys)` | Remove keys from the log context. |
| `get_log_context()` | Return current context (correlationId + bound vars). |
| `LoggerAdapter` | Logger with `debug`, `info`, `warning`, `error`, `exception` (msg, *args, **kwargs). |
| `CustomJSONLog` | JSON formatter class (used internally). |
| `CorrelationIdMiddleware` | Starlette middleware for correlation ID. |
| `CORRELATION_ID_HEADER` | `"X-Correlation-Id"`. |

## Requirements

- Python >= 3.11
- [starlette](https://www.starlette.io/)

## Development

```bash
pip install -e ".[dev]"
pytest tests -v
```
