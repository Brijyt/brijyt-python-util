# brijyt-python-util

Shared Python utilities for Brijyt APIs: JSON logging, correlation ID context, and Starlette middleware.

## Installation

```bash
pip install brijyt-python-util
```

Or from Git:

```
brijyt-python-util @ git+https://github.com/Brijyt/brijyt-python-util.git@main
```

Pin to a tag when available: `@v0.1.0`

## Usage

### Logging

```python
from brijyt_util import configure_logging, get_logger

configure_logging(api_version="1.0.0")
logger = get_logger(__name__)
logger.info("message", key="value")
```

### Correlation ID middleware (FastAPI / Starlette)

```python
from fastapi import FastAPI
from brijyt_util import CorrelationIdMiddleware, configure_logging

app = FastAPI()
configure_logging("1.0.0")
app.add_middleware(CorrelationIdMiddleware)
```

### Context and correlation ID

```python
from brijyt_util import get_correlation_id, set_correlation_id, bind_contextvars, get_log_context

set_correlation_id("req-123")
bind_contextvars(userId="user-456")
ctx = get_log_context()  # {"correlationId": "req-123", "userId": "user-456"}
```

## Requirements

- Python >= 3.11
- starlette
