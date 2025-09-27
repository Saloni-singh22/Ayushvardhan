import jwt
import pytest
from datetime import datetime, timedelta, timezone

from fastapi import Depends, FastAPI, HTTPException
from fastapi.testclient import TestClient
from starlette.requests import Request
from starlette.responses import Response

from app.core.config import settings
from app.middlewares.auth_middleware import AuthMiddleware, require_auth


def _build_test_app() -> FastAPI:
    app = FastAPI()
    app.add_middleware(AuthMiddleware)

    @app.get("/protected")
    async def protected_route(user=Depends(require_auth)):
        return {"abha": user.get("abha_number"), "debug": user.get("debug")}

    @app.get("/api/v1/enhanced-mapping/analytics")
    async def exempt_route():
        return {"ok": True}

    return app


@pytest.fixture(autouse=True)
def restore_settings():
    original_debug = settings.debug
    original_secret = settings.jwt_secret_key
    try:
        yield
    finally:
        settings.debug = original_debug
        settings.jwt_secret_key = original_secret


def _make_token(abha_number: str) -> str:
    settings.jwt_secret_key = "x" * 64
    payload = {
        "sub": abha_number,
        "exp": datetime.now(timezone.utc) + timedelta(hours=1),
    }
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def test_exempt_route_bypasses_authentication():
    app = _build_test_app()
    client = TestClient(app, raise_server_exceptions=False)

    response = client.get("/api/v1/enhanced-mapping/analytics")

    assert response.status_code == 200
    assert response.json() == {"ok": True}


@pytest.mark.asyncio
async def test_protected_route_requires_token_when_not_debug():
    settings.debug = False
    middleware = AuthMiddleware(app=lambda scope: None)

    scope = {
        "type": "http",
        "http_version": "1.1",
        "method": "GET",
        "scheme": "http",
        "path": "/protected",
        "headers": [],
        "query_string": b"",
        "root_path": "",
        "server": ("testserver", 80),
        "client": ("testclient", 12345),
    }

    async def receive():
        return {"type": "http.request", "body": b"", "more_body": False}

    request = Request(scope, receive)

    async def call_next(_: Request) -> Response:
        return Response("ok")

    with pytest.raises(HTTPException) as exc:
        await middleware.dispatch(request, call_next)

    assert exc.value.status_code == 401
    assert exc.value.detail == "Authorization header required"


def test_protected_route_accepts_valid_token():
    settings.debug = False
    abha_number = "12345678901234"
    token = _make_token(abha_number)

    app = _build_test_app()
    client = TestClient(app, raise_server_exceptions=False)

    response = client.get("/protected", headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 200
    body = response.json()
    assert body["abha"] == abha_number
    assert body["debug"] is None


def test_debug_mode_allows_missing_token():
    settings.debug = True
    app = _build_test_app()
    client = TestClient(app, raise_server_exceptions=False)

    response = client.get("/protected")

    assert response.status_code == 200
    body = response.json()
    assert body["abha"] == "debug_user"
    assert body["debug"] is True