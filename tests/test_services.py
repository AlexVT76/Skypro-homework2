import json

import pandas as pd
import pytest

from src import services


@pytest.fixture
def df():
    return pd.DataFrame(
        {
            "Дата операции": ["05.05.2020 10:00:00", "15.05.2020 12:00:00", "20.06.2020 12:00:00"],
            "Сумма платежа": [-5000.0, -300.0, -1000.0],
            "Категория": ["Супермаркеты", "Переводы", "Переводы"],
            "Описание": [
                "Пятёрочка +7 (950) 123-45-67",
                "Перевод Сергею З.",
                "Валерий А.",
            ],
        }
    )


@pytest.fixture
def transactions():
    return [
        {"Дата операции": "2021-05-10", "Сумма операции": -1712},
        {"Дата операции": "2021-05-15", "Сумма операции": -75.5},
        {"Дата операции": "2021-06-01", "Сумма операции": -500},
    ]


def test_cashback_categories(df):
    result = json.loads(services.get_cashback_categories(df, 2020, 5))
    assert result == {"Супермаркеты": 50, "Переводы": 3}  # июнь не попал в выборку

def test_investment_bank_limit_50(transactions):
    # 1712 -> 1750 (+38), 75.5 -> 100 (+24.5); июньская трата не учитывается
    assert services.investment_bank("2021-05", transactions, 50) == 62.5


def test_investment_bank_empty_month(transactions):
    assert services.investment_bank("2021-12", transactions, 10) == 0


def test_phone_search_formats(df):
    result = json.loads(services.search_phone_numbers(df))
    assert len(result) == 1
    assert "+7 (950) 123-45-67" in result[0]["description"]


def test_person_transfers(df):
    result = json.loads(services.search_person_transfers(df))
    assert len(result) == 1
    assert result[0]["description"] == "Валерий А."


def test_simple_search_case_insensitive(df):
    result = json.loads(services.simple_search("перевод", df))
    assert len(result) == 2  # и описание «Перевод Сергею З.», и категория «Переводы»
    descriptions = [r["description"] for r in result]
    assert "Перевод Сергею З." in descriptions


def test_simple_search_matches_description_or_category(df):
    # «пятёр» — только в описании первой транзакции
    result = json.loads(services.simple_search("пятёр", df))
    assert len(result) == 1
    assert result[0]["description"] == "Пятёрочка +7 (950) 123-45-67"


def test_simple_search_no_results(df):
    result = json.loads(services.simple_search("несуществующаястрока", df))
    assert result == []
