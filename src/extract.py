"""Extrai recursos do Bling e salva o JSON bruto em data/raw/.

Uso:
    python -m src.extract                      # todos os recursos, período padrão
    python -m src.extract pedidos-vendas       # um recurso
    python -m src.extract contas-pagar --inicio 2025-01-01 --fim 2025-12-31
"""
import argparse
import json
from datetime import date, timedelta

from src.bling_client import BlingClient
from src.config import DATA_RAW

MESES_PASSADOS = 12  # período padrão: últimos 12 meses...
DIAS_FUTUROS_CONTAS = 180  # ...e, para contas, vencimentos dos próximos 6 meses

# nome -> caminho na API, parâmetros fixos e (opcional) nomes dos filtros de data
RECURSOS = {
    "produtos": {"path": "produtos"},
    "categorias": {"path": "categorias/receitas-despesas"},
    "contas-financeiras": {"path": "contas-contabeis"},
    "formas-pagamento": {"path": "formas-pagamentos"},
    "pedidos-vendas": {
        "path": "pedidos/vendas",
        "datas": ("dataInicial", "dataFinal"),
    },
    "contas-receber": {
        "path": "contas/receber",
        "params": {"tipoFiltroData": "V"},  # filtra por data de vencimento
        "datas": ("dataInicial", "dataFinal"),
        "futuro": True,
    },
    "contas-pagar": {
        "path": "contas/pagar",
        "datas": ("dataVencimentoInicial", "dataVencimentoFinal"),
        "futuro": True,
    },
}


def janelas_mensais(inicio, fim):
    """Divide [inicio, fim] em períodos de no máximo um mês (o Bling recusa mais de 1 ano)."""
    janelas = []
    atual = inicio
    while atual <= fim:
        proximo_mes = (atual.replace(day=1) + timedelta(days=32)).replace(day=1)
        janelas.append((atual, min(proximo_mes - timedelta(days=1), fim)))
        atual = proximo_mes
    return janelas


def inicio_padrao(hoje):
    ano, mes = divmod(hoje.year * 12 + hoje.month - 1 - MESES_PASSADOS, 12)
    return date(ano, mes + 1, 1)


def extrair(client, nome, inicio=None, fim=None):
    recurso = RECURSOS[nome]
    params = recurso.get("params", {})

    if "datas" not in recurso:
        registros = client.get_all(recurso["path"], params)
    else:
        hoje = date.today()
        inicio = inicio or inicio_padrao(hoje)
        fim = fim or hoje + timedelta(days=DIAS_FUTUROS_CONTAS if recurso.get("futuro") else 0)
        campo_ini, campo_fim = recurso["datas"]
        por_id = {}
        for ini, fi in janelas_mensais(inicio, fim):
            filtro = {**params, campo_ini: ini.isoformat(), campo_fim: fi.isoformat()}
            for registro in client.get_all(recurso["path"], filtro):
                por_id[registro["id"]] = registro
        registros = list(por_id.values())
        print(f"  período {inicio} a {fim}")

    DATA_RAW.mkdir(parents=True, exist_ok=True)
    out = DATA_RAW / f"{nome}_{date.today():%Y%m%d}.json"
    out.write_text(json.dumps(registros, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"  {len(registros)} registros -> {out.relative_to(DATA_RAW.parent.parent)}")


def main():
    parser = argparse.ArgumentParser(description="Extrai dados do Bling para data/raw/.")
    parser.add_argument("recursos", nargs="*", help=f"padrão: todos ({', '.join(RECURSOS)})")
    parser.add_argument("--inicio", type=date.fromisoformat, help="AAAA-MM-DD")
    parser.add_argument("--fim", type=date.fromisoformat, help="AAAA-MM-DD")
    args = parser.parse_args()
    invalidos = set(args.recursos) - set(RECURSOS)
    if invalidos:
        parser.error(f"recurso desconhecido: {', '.join(invalidos)}. Opções: {', '.join(RECURSOS)}")

    client = BlingClient()
    for nome in args.recursos or RECURSOS:
        print(f"{nome}:")
        extrair(client, nome, args.inicio, args.fim)


if __name__ == "__main__":
    main()
