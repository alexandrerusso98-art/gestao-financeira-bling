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
4. Extraia um recurso para `data/raw/`:
   `python -m src.extract produtos`

Testes: `python -m pytest`
