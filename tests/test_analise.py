import pandas as pd
import pytest

from src import analise


def vendas(*linhas):
    colunas = ["pedido_id", "data", "codigo", "codigo_item", "nome", "descricao", "fonte_custo",
               "quantidade", "receita", "custo_unitario", "custo_total", "margem_contribuicao", "lucro"]
    df = pd.DataFrame(linhas, columns=colunas)
    df["data"] = pd.to_datetime(df["data"])
    return df


V = vendas(
    (1, "2026-09-01", "A", "A", "Prod A", "", "planilha", 2, 200.0, 40.0, 80.0, 96.0, 40.0),
    (1, "2026-09-01", "B", "B", "Prod B", "", "sem custo", 1, 300.0, None, None, None, None),
    (2, "2026-09-10", "C", "C", "Prod C", "", "bling", 1, 50.0, 80.0, 80.0, -36.0, -50.0),
)


def test_resumo_calcula_margem_so_sobre_itens_com_custo():
    r = analise.resumo(V)

    assert r["receita"] == 550
    assert r["pedidos"] == 2
    assert r["cobertura_custo"] == pytest.approx(250 / 550)
    assert r["margem_contribuicao_pct"] == pytest.approx(60 / 250)


def test_margem_por_produto_ordena_por_receita_e_deixa_sem_custo_vazio():
    df = analise.margem_por_produto(V)

    assert df["codigo"].tolist() == ["B", "A", "C"]
    assert pd.isna(df.loc[0, "margem_contribuicao"])
    assert df.loc[1, "margem_contribuicao_pct"] == pytest.approx(0.48)


def test_mais_vendidos_sem_custo_usa_receita_total_como_base():
    df = analise.mais_vendidos_sem_custo(V)

    assert df["codigo"].tolist() == ["B"]
    assert df.loc[0, "participacao_receita"] == pytest.approx(300 / 550)


def test_custos_suspeitos_pega_custo_maior_que_preco():
    assert analise.custos_suspeitos(V)["codigo"].tolist() == ["C"]


def test_filtrar_periodo_inclui_as_pontas():
    df = analise.filtrar_periodo(V, pd.Timestamp("2026-09-01").date(), pd.Timestamp("2026-09-01").date())
    assert df["pedido_id"].unique().tolist() == [1]
