"""Tela de margem e pendências de cadastro.

Uso:
    streamlit run app/app.py
"""
import sys
from pathlib import Path

import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))  # permite importar src/

from src import analise  # noqa: E402

st.set_page_config(page_title="Gestão Financeira", layout="wide")


def reais(valor, casas=2):
    # "\$" evita que o Streamlit interprete o texto entre dois cifrões como fórmula matemática.
    texto = f"{valor:,.{casas}f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return f"R\\$ {texto}"


def reais_compacto(valor):
    if abs(valor) >= 1_000_000:
        return reais(valor / 1_000_000, 1) + " mi"
    if abs(valor) >= 1_000:
        return reais(valor / 1_000, 1) + " mil"
    return reais(valor)


def pct(valor):
    return f"{valor:.1%}".replace(".", ",")


@st.cache_data
def carregar():
    return analise.carregar()


try:
    vendas, pendencias_planilha = carregar()
except FileNotFoundError:
    st.error("Tabelas não encontradas. Rode `python -m src.extract` e depois `python -m src.transform`.")
    st.stop()

# --- Filtro de período ----------------------------------------------------------
menor, maior = vendas["data"].min().date(), vendas["data"].max().date()
with st.sidebar:
    st.header("Período")
    periodo = st.date_input("Datas dos pedidos", (menor, maior), min_value=menor, max_value=maior,
                            format="DD/MM/YYYY")
if len(periodo) != 2:
    st.info("Escolha a data final do período.")
    st.stop()
filtradas = analise.filtrar_periodo(vendas, *periodo)
if filtradas.empty:
    st.warning("Nenhuma venda no período escolhido.")
    st.stop()

# --- Indicadores ----------------------------------------------------------------
st.title("Margem")
r = analise.resumo(filtradas)

col1, col2, col3 = st.columns(3)
col1.metric("Receita", reais_compacto(r["receita"]), help=reais(r["receita"]))
col2.metric("Pedidos", f"{r['pedidos']:,}".replace(",", "."))
col3.metric("Receita com custo conhecido", pct(r["cobertura_custo"]))

col1, col2, col3 = st.columns(3)
col1.metric("Margem de contribuição", pct(r["margem_contribuicao_pct"]), help=reais(r["margem_contribuicao"]))
col2.metric("Lucro (após custo fixo)", pct(r["lucro_pct"]), help=reais(r["lucro"]))
col3.caption(
    f"Sobre a receita com custo conhecido: margem de contribuição de {reais(r['margem_contribuicao'])} "
    f"e lucro de {reais(r['lucro'])}."
)

if r["cobertura_custo"] < 0.8:
    st.warning(
        f"Só {pct(r['cobertura_custo'])} da receita tem custo cadastrado. As margens acima consideram "
        "apenas esses itens e podem não representar o negócio todo. Veja a aba **Pendências**."
    )
st.caption(
    "Margem de contribuição = receita − custo − cartão (7%) − comissão (5%). "
    "Lucro = margem de contribuição − custo fixo (28%). "
    "Custo: planilha de precificação quando houver; senão, o custo do Bling."
)

# --- Abas -----------------------------------------------------------------------
aba_produtos, aba_pendencias = st.tabs(["Margem por produto", "Pendências de cadastro"])

with aba_produtos:
    st.dataframe(
        analise.margem_por_produto(filtradas),
        hide_index=True,
        width="stretch",
        column_config={
            "codigo": "Código", "nome": "Produto", "fonte_custo": "Fonte do custo",
            "quantidade": "Qtd.",
            "receita": st.column_config.NumberColumn("Receita", format="R$ %.2f"),
            "custo_total": st.column_config.NumberColumn("Custo", format="R$ %.2f"),
            "margem_contribuicao": st.column_config.NumberColumn("Margem contrib.", format="R$ %.2f"),
            "lucro": st.column_config.NumberColumn("Lucro", format="R$ %.2f"),
            "margem_contribuicao_pct": st.column_config.NumberColumn("Margem contrib. %", format="percent"),
            "participacao_receita": st.column_config.NumberColumn("% da receita", format="percent"),
        },
    )

with aba_pendencias:
    st.subheader("Mais vendidos sem custo")
    st.caption("Cadastrar o custo destes produtos (na planilha ou no Bling) é o que mais melhora a análise.")
    st.dataframe(
        analise.mais_vendidos_sem_custo(filtradas),
        hide_index=True,
        width="stretch",
        column_config={
            "codigo": "Código", "nome": "Produto", "quantidade": "Qtd.",
            "receita": st.column_config.NumberColumn("Receita", format="R$ %.2f"),
            "participacao_receita": st.column_config.NumberColumn("% da receita total", format="percent"),
        },
    )

    st.subheader("Custo maior que o preço de venda")
    st.caption("Geralmente é o preço de venda digitado no campo de custo.")
    st.dataframe(
        analise.custos_suspeitos(filtradas),
        hide_index=True,
        width="stretch",
        column_config={
            "codigo": "Código", "nome": "Produto", "fonte_custo": "Fonte do custo", "quantidade": "Qtd.",
            "custo_unitario": st.column_config.NumberColumn("Custo unitário", format="R$ %.2f"),
            "preco_medio": st.column_config.NumberColumn("Preço médio de venda", format="R$ %.2f"),
        },
    )

    st.subheader("SKUs repetidos na planilha")
    st.caption("O mesmo SKU aparece para produtos diferentes e nenhum nome confere com o Bling.")
    st.dataframe(
        pendencias_planilha,
        hide_index=True,
        width="stretch",
        column_config={
            "sku": "SKU", "nome_planilha": "Produto na planilha", "aba": "Aba",
            "custo_planilha": st.column_config.NumberColumn("Custo", format="R$ %.2f"),
        },
    )
