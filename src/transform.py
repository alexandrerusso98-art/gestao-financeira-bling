"""Transforma os dados brutos (Bling + planilha de precificação) em tabelas para o app.

Uso:
    python -m src.transform

Gera em data/processed/:
    produtos.parquet        produtos ativos e excluídos, com custo e fonte do custo
    vendas_itens.parquet    uma linha por item vendido (sem cancelados), com margens
    pendencias_planilha.csv SKUs repetidos da planilha que não deu para resolver
"""
import json
import unicodedata

import pandas as pd

from src.config import DATA_PROCESSED, DATA_RAW

SITUACAO_CANCELADO = 12

# Despesas variáveis sobre o preço de venda (mesmas da planilha de precificação)
TAXA_CARTAO = 0.07
COMISSAO = 0.05
CUSTO_FIXO = 0.28

ABAS_PLANILHA = [
    "Produtos_Ouro",
    "Produtos_Prata",
    "Produtos_Já_Prontos",
    "ARTFORCE - Produtos_Já_Prontos",
]


def normalizar(texto):
    """Minúsculas, sem acentos e com espaços simples, para comparar nomes e códigos."""
    texto = unicodedata.normalize("NFKD", str(texto)).encode("ascii", "ignore").decode()
    return " ".join(texto.lower().split())


def _ultimo(padrao):
    arquivos = list(DATA_RAW.glob(padrao))
    if not arquivos:
        raise RuntimeError(f"Nenhum arquivo {padrao} em data/raw/. Rode a extração antes.")
    return max(arquivos, key=lambda a: a.stat().st_mtime)


def _ler_json(padrao):
    return json.loads(_ultimo(padrao).read_text(encoding="utf-8"))


# --- Produtos -----------------------------------------------------------------

COLUNAS_PRODUTOS = ["produto_id", "codigo", "nome", "situacao", "preco", "custo_bling", "estoque"]


def montar_produtos(ativos, excluidos):
    registros = [
        {
            "produto_id": p["id"],
            "codigo": (p.get("codigo") or "").strip(),
            "nome": p["nome"],
            "situacao": p.get("situacao"),
            "preco": p.get("preco") or 0.0,
            "custo_bling": p.get("precoCusto") or 0.0,
            "estoque": (p.get("estoque") or {}).get("saldoVirtualTotal", 0),
        }
        for p in ativos + excluidos
    ]
    # Um mesmo id pode aparecer nas duas listas; fica o primeiro (ativo).
    df = pd.DataFrame(registros, columns=COLUNAS_PRODUTOS)
    return df.drop_duplicates("produto_id").reset_index(drop=True)


# --- Planilha de precificação ---------------------------------------------------

def ler_planilha(caminho):
    """Lê as abas de produtos, localizando a linha de cabeçalho pela célula 'SKU'."""
    partes = []
    for aba in ABAS_PLANILHA:
        bruto = pd.read_excel(caminho, sheet_name=aba, header=None)
        linha = bruto.index[bruto.iloc[:, 0].astype(str).str.strip().str.upper() == "SKU"][0]
        df = pd.read_excel(caminho, sheet_name=aba, header=linha)
        df = df[df["SKU"].notna() & (df["SKU"].astype(str).str.strip() != "")]
        partes.append(pd.DataFrame({
            "sku": df["SKU"].astype(str).str.strip().str.upper(),
            "nome_planilha": df["PRODUTO"].astype(str).str.strip(),
            "custo_planilha": pd.to_numeric(df["CUSTO TOTAL (R$)"], errors="coerce"),
            "aba": aba,
        }))
    return pd.concat(partes, ignore_index=True)


def resolver_duplicados(planilha, produtos):
    """Deixa uma linha por SKU.

    Quando o SKU se repete, fica a linha cujo nome confere com o nome do Bling.
    Se nenhuma (ou mais de uma) conferir, o SKU vai para as pendências.
    """
    # Percorre de trás para frente para que os ativos (que vêm primeiro) prevaleçam.
    nomes_bling = {
        cod.upper(): normalizar(nome)
        for cod, nome in zip(produtos["codigo"][::-1], produtos["nome"][::-1]) if cod
    }
    planilha = planilha.assign(
        confere=[normalizar(n) == nomes_bling.get(s) for s, n in zip(planilha["sku"], planilha["nome_planilha"])]
    )
    repetidos = planilha["sku"].duplicated(keep=False)
    unicos = planilha[~repetidos]

    escolhidos, pendentes = [], []
    for _, grupo in planilha[repetidos].groupby("sku"):
        certos = grupo[grupo["confere"]]
        if len(certos) == 1:
            escolhidos.append(certos)
        else:
            pendentes.append(grupo)

    resolvidos = pd.concat([unicos, *escolhidos], ignore_index=True).drop(columns="confere")
    pendencias = (
        pd.concat(pendentes, ignore_index=True).drop(columns="confere")
        if pendentes else planilha.iloc[0:0].drop(columns="confere")
    )
    return resolvidos, pendencias


def aplicar_custos(produtos, planilha):
    """Custo da planilha quando houver; senão, o do Bling; senão, sem custo."""
    custo_planilha = planilha.dropna(subset=["custo_planilha"]).set_index("sku")["custo_planilha"]
    df = produtos.copy()
    df["custo_planilha"] = df["codigo"].str.upper().map(custo_planilha)
    tem_planilha = df["custo_planilha"].notna() & (df["custo_planilha"] > 0)
    tem_bling = df["custo_bling"] > 0
    df["custo_unitario"] = df["custo_planilha"].where(tem_planilha, df["custo_bling"].where(tem_bling))
    df["fonte_custo"] = "sem custo"
    df.loc[tem_bling, "fonte_custo"] = "bling"
    df.loc[tem_planilha, "fonte_custo"] = "planilha"
    return df


# --- Vendas ---------------------------------------------------------------------

def montar_itens(pedidos):
    """Uma linha por item vendido, já com a parte do desconto do pedido."""
    linhas = []
    for p in pedidos:
        if p["situacao"]["id"] == SITUACAO_CANCELADO:
            continue
        total_produtos = p["totalProdutos"]
        desconto = p.get("desconto") or {"valor": 0, "unidade": "REAL"}
        desconto_pedido = (
            total_produtos * desconto["valor"] / 100
            if desconto["unidade"] == "PERCENTUAL" else desconto["valor"]
        )
        for item in p["itens"]:
            # O valor do item já vem com o desconto do item; o campo 'desconto' dele é só informativo.
            bruto = item["quantidade"] * item["valor"]
            rateio = desconto_pedido * bruto / total_produtos if total_produtos else 0.0
            linhas.append({
                "pedido_id": p["id"],
                "numero_pedido": p["numero"],
                "data": p["data"],
                "situacao_id": p["situacao"]["id"],
                "produto_id": item["produto"]["id"],
                "codigo_item": (item.get("codigo") or "").strip(),
                "descricao": item.get("descricao", ""),
                "quantidade": item["quantidade"],
                "preco_unitario": item["valor"],
                "receita": bruto - rateio,
            })
    df = pd.DataFrame(linhas)
    df["data"] = pd.to_datetime(df["data"])
    return df


def calcular_margens(itens, produtos):
    df = itens.merge(
        produtos[["produto_id", "codigo", "nome", "custo_unitario", "fonte_custo"]],
        on="produto_id", how="left",
    )
    df["fonte_custo"] = df["fonte_custo"].fillna("sem custo")
    df["custo_total"] = df["quantidade"] * df["custo_unitario"]
    df["despesas_variaveis"] = df["receita"] * (TAXA_CARTAO + COMISSAO)
    df["margem_contribuicao"] = df["receita"] - df["custo_total"] - df["despesas_variaveis"]
    df["lucro"] = df["margem_contribuicao"] - df["receita"] * CUSTO_FIXO
    return df


def main():
    produtos = montar_produtos(_ler_json("produtos_*.json"), _ler_json("produtos-excluidos_*.json"))
    planilha, pendencias = resolver_duplicados(ler_planilha(_ultimo("*.xlsx")), produtos)
    produtos = aplicar_custos(produtos, planilha)
    vendas = calcular_margens(montar_itens(_ler_json("pedidos-vendas-detalhes.json")), produtos)

    DATA_PROCESSED.mkdir(parents=True, exist_ok=True)
    produtos.to_parquet(DATA_PROCESSED / "produtos.parquet", index=False)
    vendas.to_parquet(DATA_PROCESSED / "vendas_itens.parquet", index=False)
    pendencias.to_csv(DATA_PROCESSED / "pendencias_planilha.csv", index=False, encoding="utf-8-sig")

    receita = vendas["receita"].sum()
    print(f"produtos: {len(produtos)} | itens vendidos: {len(vendas)} | receita R$ {receita:,.2f}")
    for fonte, valor in vendas.groupby("fonte_custo")["receita"].sum().sort_values(ascending=False).items():
        print(f"  receita com custo de {fonte}: {valor / receita:.1%}")
    print(f"pendências da planilha (SKU repetido sem nome conferindo): {pendencias['sku'].nunique()} SKUs")


if __name__ == "__main__":
    main()
