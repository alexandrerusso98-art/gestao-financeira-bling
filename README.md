# Gestão Financeira para Pequenas Empresas

App de gestão financeira para pequenas empresas, com foco em **fluxo de caixa**,
**margem** e **estoque**, a partir de dados extraídos do ERP **Bling**.

> Status: fundação do projeto (sem funcionalidades ainda).

## Estrutura

```
app/              # interface Streamlit
src/              # lógica: integração com o Bling, transformações, cálculos
data/raw/         # dados brutos extraídos (não versionado)
data/processed/   # dados tratados (não versionado)
notebooks/        # exploração e análises
tests/            # testes automatizados
```

## Como rodar

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

## Integração com o Bling (API v3)

1. No Bling, cadastre um aplicativo com o link de redirecionamento
   `http://localhost:8080/callback` e os escopos de leitura necessários.
2. Copie `.env.example` para `.env` e preencha `BLING_CLIENT_ID` e `BLING_CLIENT_SECRET`.
3. Autorize o app (abre o navegador; os tokens ficam em `.bling_tokens.json`, não versionado):
   `python -m src.bling_auth`
4. Extraia os dados para `data/raw/` (todos os recursos, ou um pelo nome):
   `python -m src.extract` ou `python -m src.extract pedidos-vendas`

## Transformação

1. Baixe a planilha de precificação (Arquivo → Fazer download → .xlsx) para `data/raw/`.
2. Gere as tabelas em `data/processed/`:
   `python -m src.transform`

Custo de cada produto: planilha de precificação quando o SKU estiver nela; senão,
o `precoCusto` do Bling; senão, fica "sem custo" (fora do cálculo de margem).
Despesas variáveis: cartão 7%, comissão 5%, custo fixo 28% (em `src/transform.py`).

## App

`streamlit run app/app.py` (abre em http://localhost:8501, acessível só neste computador)

Testes: `python -m pytest`
