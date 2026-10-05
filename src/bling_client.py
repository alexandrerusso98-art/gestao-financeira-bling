"""Cliente HTTP para a API v3 do Bling: autenticação, limite de requisições e paginação."""
import time

import requests

from src.bling_auth import get_access_token, refresh_access_token

BASE_URL = "https://api.bling.com.br/Api/v3"
MIN_INTERVAL = 0.35  # limite do Bling: 3 requisições por segundo
PAGE_LIMIT = 100
MAX_ATTEMPTS = 5


class BlingClient:
    def __init__(self):
        self.session = requests.Session()
        self._token = get_access_token()
        self._last_request = 0.0

    def get(self, path, params=None):
        refreshed = False
        for attempt in range(MAX_ATTEMPTS):
            wait = MIN_INTERVAL - (time.monotonic() - self._last_request)
            if wait > 0:
                time.sleep(wait)
            self._last_request = time.monotonic()

            resp = self.session.get(
                f"{BASE_URL}/{path.lstrip('/')}",
                params=params,
                headers={"Authorization": f"Bearer {self._token}"},
                timeout=30,
            )
            if resp.status_code == 401 and not refreshed:
                self._token = refresh_access_token()
                refreshed = True
                continue
            if resp.status_code == 429:
                time.sleep(2 ** attempt)
                continue
            if not resp.ok:
                raise RuntimeError(f"Erro {resp.status_code} em GET {path}: {resp.text}")
            return resp.json()
        raise RuntimeError(f"GET {path} falhou após {MAX_ATTEMPTS} tentativas.")

    def get_all(self, path, params=None):
        """Percorre todas as páginas de uma listagem e devolve os registros juntos."""
        records = []
        page = 1
        while True:
            data = self.get(path, {**(params or {}), "pagina": page, "limite": PAGE_LIMIT})["data"]
            records.extend(data)
            if len(data) < PAGE_LIMIT:
                return records
            page += 1
