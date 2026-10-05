import pytest

from src import bling_client
from src.bling_client import PAGE_LIMIT, BlingClient


class FakeResponse:
    def __init__(self, status_code, payload=None):
        self.status_code = status_code
        self.ok = status_code < 400
        self.text = ""
        self._payload = payload or {}

    def json(self):
        return self._payload


class FakeSession:
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []

    def get(self, url, params=None, headers=None, timeout=None):
        self.calls.append({"url": url, "params": params, "headers": headers})
        return self.responses.pop(0)


@pytest.fixture
def make_client(monkeypatch):
    monkeypatch.setattr(bling_client, "get_access_token", lambda: "token-1")
    monkeypatch.setattr(bling_client, "refresh_access_token", lambda: "token-2")
    monkeypatch.setattr(bling_client, "MIN_INTERVAL", 0)
    monkeypatch.setattr(bling_client.time, "sleep", lambda seconds: None)

    def _make(responses):
        client = BlingClient()
        client.session = FakeSession(responses)
        return client

    return _make


def test_get_all_percorre_paginas_ate_pagina_incompleta(make_client):
    client = make_client([
        FakeResponse(200, {"data": [{"id": i} for i in range(PAGE_LIMIT)]}),
        FakeResponse(200, {"data": [{"id": "a"}, {"id": "b"}]}),
    ])

    records = client.get_all("produtos")

    assert len(records) == PAGE_LIMIT + 2
    assert [call["params"]["pagina"] for call in client.session.calls] == [1, 2]


def test_renova_token_quando_recebe_401(make_client):
    client = make_client([FakeResponse(401), FakeResponse(200, {"data": []})])

    client.get("produtos")

    assert client.session.calls[1]["headers"]["Authorization"] == "Bearer token-2"


def test_tenta_de_novo_quando_recebe_429(make_client):
    client = make_client([FakeResponse(429), FakeResponse(200, {"data": [{"id": 1}]})])

    assert client.get("produtos") == {"data": [{"id": 1}]}


def test_erro_http_vira_excecao(make_client):
    client = make_client([FakeResponse(400)])

    with pytest.raises(RuntimeError, match="Erro 400"):
        client.get("produtos")
