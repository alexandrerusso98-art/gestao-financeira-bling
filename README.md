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

Credenciais (ex.: token da API do Bling) ficam em um arquivo `.env`, que não é versionado.
