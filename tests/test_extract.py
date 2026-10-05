from datetime import date

from src.extract import inicio_padrao, janelas_mensais


def test_janelas_mensais_cobrem_o_periodo_sem_buracos():
    janelas = janelas_mensais(date(2025, 11, 15), date(2026, 2, 10))

    assert janelas == [
        (date(2025, 11, 15), date(2025, 11, 30)),
        (date(2025, 12, 1), date(2025, 12, 31)),
        (date(2026, 1, 1), date(2026, 1, 31)),
        (date(2026, 2, 1), date(2026, 2, 10)),
    ]


def test_janelas_mensais_trata_fevereiro_bissexto():
    assert janelas_mensais(date(2028, 2, 1), date(2028, 3, 5))[0] == (date(2028, 2, 1), date(2028, 2, 29))


def test_inicio_padrao_volta_12_meses_ate_o_dia_1():
    assert inicio_padrao(date(2026, 10, 5)) == date(2025, 10, 1)
    assert inicio_padrao(date(2026, 1, 20)) == date(2025, 1, 1)
