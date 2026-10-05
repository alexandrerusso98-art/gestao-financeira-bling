"""Extrai um recurso do Bling e salva o JSON bruto em data/raw/.

Uso:
    python -m src.extract produtos
"""
import json
import sys
from datetime import date

from src.bling_client import BlingClient
from src.config import DATA_RAW


def extract(path):
    records = BlingClient().get_all(path)
    DATA_RAW.mkdir(parents=True, exist_ok=True)
    out = DATA_RAW / f"{path.replace('/', '_')}_{date.today():%Y%m%d}.json"
    out.write_text(json.dumps(records, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"{len(records)} registros salvos em {out.relative_to(DATA_RAW.parent.parent)}")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit("Uso: python -m src.extract <recurso>   (ex.: produtos)")
    extract(sys.argv[1])
