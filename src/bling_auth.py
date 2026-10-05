"""Autenticação OAuth 2.0 com a API v3 do Bling.

Rode uma vez para autorizar o app (e de novo se ficar 30 dias sem uso):
    python -m src.bling_auth
"""
import json
import secrets
import time
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import parse_qs, urlencode, urlparse

import requests

from src.config import TOKENS_FILE, get_env

AUTHORIZE_URL = "https://www.bling.com.br/Api/v3/oauth/authorize"
TOKEN_URL = "https://api.bling.com.br/Api/v3/oauth/token"
EXPIRY_MARGIN = 300  # renova o token 5 minutos antes de expirar


def _request_token(data):
    """Pede tokens ao Bling e salva em disco junto com o horário de expiração."""
    resp = requests.post(
        TOKEN_URL,
        data=data,
        auth=(get_env("BLING_CLIENT_ID"), get_env("BLING_CLIENT_SECRET")),
        timeout=30,
    )
    if not resp.ok:
        raise RuntimeError(f"Erro ao obter token ({resp.status_code}): {resp.text}")
    tokens = resp.json()
    tokens["expires_at"] = time.time() + tokens["expires_in"]
    TOKENS_FILE.write_text(json.dumps(tokens, indent=2), encoding="utf-8")
    return tokens


def _load_tokens():
    if not TOKENS_FILE.exists():
        raise RuntimeError("Nenhum token salvo. Rode antes: python -m src.bling_auth")
    return json.loads(TOKENS_FILE.read_text(encoding="utf-8"))


def refresh_access_token():
    """Força a renovação usando o refresh token e devolve o novo access token."""
    tokens = _load_tokens()
    tokens = _request_token({"grant_type": "refresh_token", "refresh_token": tokens["refresh_token"]})
    return tokens["access_token"]


def get_access_token():
    """Devolve um access token válido, renovando se estiver perto de expirar."""
    tokens = _load_tokens()
    if time.time() > tokens["expires_at"] - EXPIRY_MARGIN:
        return refresh_access_token()
    return tokens["access_token"]


def authorize():
    """Abre o navegador para autorizar o app e captura o código no redirecionamento."""
    redirect = urlparse(get_env("BLING_REDIRECT_URI"))
    state = secrets.token_urlsafe(16)
    result = {}

    class CallbackHandler(BaseHTTPRequestHandler):
        def do_GET(self):
            query = parse_qs(urlparse(self.path).query)
            result.update({key: values[0] for key, values in query.items()})
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write("<h3>Pronto! Pode fechar esta aba e voltar ao terminal.</h3>".encode())

        def log_message(self, *args):
            pass

    server = HTTPServer((redirect.hostname, redirect.port or 80), CallbackHandler)
    url = AUTHORIZE_URL + "?" + urlencode(
        {"response_type": "code", "client_id": get_env("BLING_CLIENT_ID"), "state": state}
    )
    print("Abrindo o navegador para autorizar o app no Bling...")
    print(f"Se não abrir sozinho, acesse:\n{url}\n")
    webbrowser.open(url)

    while "code" not in result and "error" not in result:
        server.handle_request()
    server.server_close()

    if "error" in result:
        raise RuntimeError(f"Autorização negada: {result}")
    if result.get("state") != state:
        raise RuntimeError("Parâmetro state não confere; autorização descartada por segurança.")

    _request_token({"grant_type": "authorization_code", "code": result["code"]})
    print(f"Autorizado! Tokens salvos em {TOKENS_FILE.name}.")


if __name__ == "__main__":
    authorize()
