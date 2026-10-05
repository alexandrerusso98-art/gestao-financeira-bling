import pandas as pd
import pytest

from src.transform import (
    aplicar_custos,
    calcular_margens,
    montar_itens,
    montar_produtos,
    normalizar,
    resolver_duplicados,
)


def produto(id_, codigo, nome, custo=0.0, situacao="A"):
    return {"id": id_, "codigo": codigo, "nome": nome, "situacao": situacao,
            "preco": 100.0, "precoCusto": custo, "estoque": {"saldoVirtualTotal": 1}}


def pedido(id_, itens, situacao=9, desconto=None):
    return {
        "id": id_, "numero": id_, "data": "2026-09-01", "situacao": {"id": situacao},
        "totalProdutos": sum(i["quantidade"] * i["valor"] for i in itens),
        "desconto": desconto or {"valor": 0, "unidade": "REAL"},
        "itens": itens,
    }


def item(produto_id, quantidade, valor, codigo="X"):
    return {"produto": {"id": produto_id}, "codigo": codigo, "descricao": "", "quantidade": quantidade, "valor": valor}


def test_normalizar_ignora_acento_caixa_e_espacos():
    assert normalizar("  Choker  Elos Geométricos Prata") == normalizar("choker elos geometricos prata")


def test_montar_produtos_prefere_ativo_quando_id_repete():
    df = montar_produtos([produto(1, "A1", "Ativo")], [produto(1, "A1", "Excluido", situacao="E")])
    assert df["nome"].tolist() == ["Ativo"]


def test_resolver_duplicados_usa_nome_do_bling():
    produtos = montar_produtos([produto(1, "COLP2031", "Choker Zig Zag Prata")], [])
    planilha = pd.DataFrame({
        "sku": ["COLP2031", "COLP2031", "UNICO"],
        "nome_planilha": ["Choker Grume Prata", "Choker  Zig Zag Prata", "Outro"],
        "custo_planilha": [10.0, 20.0, 5.0],
        "aba": ["Prata"] * 3,
    })

    resolvidos, pendencias = resolver_duplicados(planilha, produtos)

    assert resolvidos.set_index("sku")["custo_planilha"].to_dict() == {"COLP2031": 20.0, "UNICO": 5.0}
    assert pendencias.empty


def test_resolver_duplicados_manda_para_pendencias_quando_nenhum_nome_confere():
    produtos = montar_produtos([], [])
    planilha = pd.DataFrame({
        "sku": ["COLD2028", "COLD2028"], "nome_planilha": ["A", "B"],
        "custo_planilha": [1.0, 2.0], "aba": ["Ouro"] * 2,
    })

    resolvidos, pendencias = resolver_duplicados(planilha, produtos)

    assert resolvidos.empty
    assert len(pendencias) == 2


def test_aplicar_custos_prioriza_planilha_depois_bling():
    produtos = montar_produtos(
        [produto(1, "P1", "a", custo=10), produto(2, "P2", "b", custo=10), produto(3, "P3", "c", custo=0)], []
    )
    planilha = pd.DataFrame({"sku": ["P1"], "nome_planilha": ["a"], "custo_planilha": [25.0], "aba": ["x"]})

    df = aplicar_custos(produtos, planilha).set_index("codigo")

    assert df.loc["P1", ["custo_unitario", "fonte_custo"]].tolist() == [25.0, "planilha"]
    assert df.loc["P2", ["custo_unitario", "fonte_custo"]].tolist() == [10.0, "bling"]
    assert df.loc["P3", "fonte_custo"] == "sem custo"
    assert pd.isna(df.loc["P3", "custo_unitario"])


def test_montar_itens_ignora_cancelados_e_rateia_desconto_do_pedido():
    pedidos = [
        pedido(1, [item(10, 1, 100.0), item(11, 1, 300.0)], desconto={"valor": 10, "unidade": "PERCENTUAL"}),
        pedido(2, [item(10, 1, 999.0)], situacao=12),
    ]

    df = montar_itens(pedidos)

    assert df["pedido_id"].unique().tolist() == [1]
    assert df["receita"].tolist() == pytest.approx([90.0, 270.0])


def test_calcular_margens():
    produtos = aplicar_custos(
        montar_produtos([produto(10, "P", "p", custo=30)], []),
        pd.DataFrame(columns=["sku", "nome_planilha", "custo_planilha", "aba"]),
    )
    itens = montar_itens([pedido(1, [item(10, 2, 100.0)])])

    linha = calcular_margens(itens, produtos).iloc[0]

    assert linha["custo_total"] == pytest.approx(60.0)
    assert linha["margem_contribuicao"] == pytest.approx(200 - 60 - 200 * 0.12)
    assert linha["lucro"] == pytest.approx(200 - 60 - 200 * 0.40)
