"""Cálculos usados pelas telas do app, a partir das tabelas de data/processed/."""
import pandas as pd

from src.config import DATA_PROCESSED

SEM_CUSTO = "sem custo"


def carregar():
    """Lê as tabelas geradas por `python -m src.transform`."""
    vendas = pd.read_parquet(DATA_PROCESSED / "vendas_itens.parquet")
    pendencias_planilha = pd.read_csv(DATA_PROCESSED / "pendencias_planilha.csv")
    return vendas, pendencias_planilha


def filtrar_periodo(vendas, inicio, fim):
    datas = vendas["data"].dt.date
    return vendas[(datas >= inicio) & (datas <= fim)]


def resumo(vendas):
    """Totais do período. Margens consideram só os itens com custo conhecido."""
    com_custo = vendas[vendas["fonte_custo"] != SEM_CUSTO]
    receita = vendas["receita"].sum()
    receita_com_custo = com_custo["receita"].sum()
    mc = com_custo["margem_contribuicao"].sum()
    lucro = com_custo["lucro"].sum()
    return {
        "receita": receita,
        "pedidos": vendas["pedido_id"].nunique(),
        "cobertura_custo": receita_com_custo / receita if receita else 0.0,
        "margem_contribuicao": mc,
        "margem_contribuicao_pct": mc / receita_com_custo if receita_com_custo else 0.0,
        "lucro": lucro,
        "lucro_pct": lucro / receita_com_custo if receita_com_custo else 0.0,
    }


def margem_por_produto(vendas):
    df = (
        vendas.assign(codigo=vendas["codigo"].fillna(vendas["codigo_item"]),
                      nome=vendas["nome"].fillna(vendas["descricao"]))
        .groupby(["codigo", "nome", "fonte_custo"], as_index=False, dropna=False)
        .agg(quantidade=("quantidade", "sum"), receita=("receita", "sum"),
             custo_total=("custo_total", "sum"), margem_contribuicao=("margem_contribuicao", "sum"),
             lucro=("lucro", "sum"))
    )
    sem_custo = df["fonte_custo"] == SEM_CUSTO
    df.loc[sem_custo, ["custo_total", "margem_contribuicao", "lucro"]] = float("nan")
    df["margem_contribuicao_pct"] = df["margem_contribuicao"] / df["receita"].where(df["receita"] > 0)
    df["participacao_receita"] = df["receita"] / df["receita"].sum()
    return df.sort_values("receita", ascending=False, ignore_index=True)


def mais_vendidos_sem_custo(vendas):
    df = margem_por_produto(vendas[vendas["fonte_custo"] == SEM_CUSTO])
    df["participacao_receita"] = df["receita"] / vendas["receita"].sum()
    return df[["codigo", "nome", "quantidade", "receita", "participacao_receita"]]


def custos_suspeitos(vendas):
    """Produtos cujo custo unitário é maior que o preço médio de venda."""
    com_custo = vendas[vendas["fonte_custo"] != SEM_CUSTO]
    df = (
        com_custo.groupby(["codigo", "nome", "fonte_custo"], as_index=False)
        .agg(custo_unitario=("custo_unitario", "first"), quantidade=("quantidade", "sum"),
             receita=("receita", "sum"))
    )
    df["preco_medio"] = df["receita"] / df["quantidade"]
    df = df[(df["receita"] > 0) & (df["custo_unitario"] > df["preco_medio"])]
    return df.sort_values("receita", ascending=False, ignore_index=True)[
        ["codigo", "nome", "fonte_custo", "custo_unitario", "preco_medio", "quantidade"]
    ]
