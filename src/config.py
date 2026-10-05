"""Configuração do projeto: caminhos e variáveis do .env."""
import os
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")

DATA_RAW = ROOT / "data" / "raw"
DATA_PROCESSED = ROOT / "data" / "processed"
TOKENS_FILE = ROOT / ".bling_tokens.json"


def get_env(name):
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"Variável {name} não definida no .env (veja .env.example).")
    return value
