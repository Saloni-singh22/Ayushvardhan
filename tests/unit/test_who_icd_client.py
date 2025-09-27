import asyncio

import httpx
import pytest

from app.services.who_icd_client import WHOICD11TM2Client


class DummyAuthService:
    async def get_authenticated_headers(self):
        return {"Authorization": "Bearer test"}


@pytest.fixture(autouse=True)
def no_sleep(monkeypatch):
    async def immediate_sleep(*args, **kwargs):
        return None

    monkeypatch.setattr(asyncio, "sleep", immediate_sleep)


def _client() -> WHOICD11TM2Client:
    client = WHOICD11TM2Client()
    client.auth_service = DummyAuthService()
    client._min_request_interval = 0
    client.max_retries = 3
    client.retry_backoff_factor = 0.1
    return client


@pytest.mark.asyncio
async def test_rate_limited_request_retries_and_succeeds(monkeypatch):
    client = _client()

    attempts = 0

    async def fake_request(self, method, url, headers=None, **kwargs):
        nonlocal attempts
        attempts += 1
        if attempts < 3:
            raise httpx.RequestError("boom", request=httpx.Request(method, url))
        request = httpx.Request(method, url)
        return httpx.Response(200, request=request, json={"ok": True})

    monkeypatch.setattr(httpx.AsyncClient, "request", fake_request, raising=False)

    response = await client._rate_limited_request("GET", "https://example.com")

    assert attempts == 3
    assert response.status_code == 200
    assert response.json() == {"ok": True}


@pytest.mark.asyncio
async def test_rate_limited_request_exhausts_retries(monkeypatch):
    client = _client()

    attempts = 0

    async def fake_request(self, method, url, headers=None, **kwargs):
        nonlocal attempts
        attempts += 1
        raise httpx.RequestError("boom", request=httpx.Request(method, url))

    monkeypatch.setattr(httpx.AsyncClient, "request", fake_request, raising=False)

    with pytest.raises(httpx.RequestError):
        await client._rate_limited_request("GET", "https://example.org")

    assert attempts == client.max_retries