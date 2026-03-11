"""Unit tests for brijyt_util.middleware."""

import uuid
from unittest.mock import patch

from fastapi import FastAPI
from starlette.testclient import TestClient

from brijyt_util import CORRELATION_ID_HEADER, CorrelationIdMiddleware


class TestCorrelationIdMiddleware:
    def test_correlation_id_header_constant(self):
        assert CORRELATION_ID_HEADER == "X-Correlation-Id"

    def test_middleware_generates_correlation_id_when_missing(self):
        app = FastAPI()
        app.add_middleware(CorrelationIdMiddleware)

        @app.get("/test")
        async def test_endpoint():
            return {"message": "test"}

        client = TestClient(app)
        response = client.get("/test")
        assert response.status_code == 200
        assert CORRELATION_ID_HEADER in response.headers
        correlation_id = response.headers[CORRELATION_ID_HEADER]
        uuid.UUID(correlation_id)

    def test_middleware_preserves_existing_correlation_id(self):
        app = FastAPI()
        app.add_middleware(CorrelationIdMiddleware)

        @app.get("/test")
        async def test_endpoint():
            return {"message": "test"}

        client = TestClient(app)
        existing_correlation_id = str(uuid.uuid4())
        headers = {CORRELATION_ID_HEADER: existing_correlation_id}
        response = client.get("/test", headers=headers)
        assert response.status_code == 200
        assert response.headers[CORRELATION_ID_HEADER] == existing_correlation_id

    @patch("brijyt_util.middleware.set_correlation_id")
    def test_middleware_sets_correlation_id(self, mock_set_correlation_id):
        app = FastAPI()
        app.add_middleware(CorrelationIdMiddleware)

        @app.get("/test")
        async def test_endpoint():
            return {"ok": True}

        client = TestClient(app)
        correlation_id = str(uuid.uuid4())
        response = client.get("/test", headers={CORRELATION_ID_HEADER: correlation_id})
        assert response.status_code == 200
        mock_set_correlation_id.assert_called_once_with(correlation_id)

    def test_middleware_generates_id_when_header_empty(self):
        app = FastAPI()
        app.add_middleware(CorrelationIdMiddleware)

        @app.get("/test")
        async def test_endpoint():
            return {}

        client = TestClient(app)
        response = client.get("/test", headers={CORRELATION_ID_HEADER: ""})
        assert response.status_code == 200
        cid = response.headers[CORRELATION_ID_HEADER]
        assert cid != ""
        uuid.UUID(cid)
