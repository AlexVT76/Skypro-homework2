"""Тесты вспомогательных функций: приветствие, фильтрация, агрегаты, настройки, API."""
import json
from datetime import datetime

import pandas as pd
import pytest
import requests

from src import utils


# ---------- Фикстура: согласованные данные за май и июнь 2020 ----------

@pytest.fixture
def sample_df():
    return pd.DataFrame(
        {
            "Дата операции": [
                "01.05.2020 10:00:00",
                "15.05.2020 12:00:00",
                "20.05.2020 12:00:00",
                "10.06.2020 12:00:00",
            ],
            "Номер карты": ["*7197", "*7197", "*4556", "*4556"],
            "Сумма платежа": [-1000.0, -250.5, -300.0, -500.0],
            "Категория": ["Супермаркеты", "Транспорт", "Рестораны", "Супермаркеты"],
            "Описание": ["Пятёрочка", "Яндекс.Такси", "Ресторан", "Магнит"],
        }
    )


# ---------- Приветствие: границы интервалов ----------

@pytest.mark.parametrize(
    "hour, expected",
    [
        (0, "Доброй ночи"),
        (5, "Доброй ночи"),
        (6, "Доброе утро"),
        (11, "Доброе утро"),
        (12, "Добрый день"),
        (17, "Добрый день"),
        (18, "Добрый вечер"),
        (22, "Добрый вечер"),
        (23, "Доброй ночи"),
    ],
)
def test_get_greeting(hour, expected):
    assert utils.get_greeting(datetime(2024, 1, 1, hour, 0)) == expected


def test_get_greeting_boundaries():
    assert utils.get_greeting(datetime(2024, 1, 1, 5, 59)) == "Доброй ночи"
    assert utils.get_greeting(datetime(2024, 1, 1, 6, 0)) == "Доброе утро"
    assert utils.get_greeting(datetime(2024, 1, 1, 11, 59)) == "Доброе утро"
    assert utils.get_greeting(datetime(2024, 1, 1, 12, 0)) == "Добрый день"
    assert utils.get_greeting(datetime(2024, 1, 1, 17, 59)) == "Добрый день"
    assert utils.get_greeting(datetime(2024, 1, 1, 18, 0)) == "Добрый вечер"
    assert utils.get_greeting(datetime(2024, 1, 1, 22, 59)) == "Добрый вечер"
    assert utils.get_greeting(datetime(2024, 1, 1, 23, 0)) == "Доброй ночи"


# ---------- Фильтрация: начало месяца — входящая дата включительно ----------

def test_filter_operations_by_date(sample_df):
    # Конец дня 20 мая: все три майские транзакции, июньская исключена
    filtered = utils.filter_operations_by_date(sample_df, datetime(2020, 5, 20, 23, 59, 59))
    assert len(filtered) == 3


def test_filter_operations_by_date_includes_end_of_day(sample_df):
    filtered = utils.filter_operations_by_date(sample_df, datetime(2020, 5, 20, 23, 59, 59))
    assert len(filtered) == 3


def test_filter_operations_by_date_start_of_month(sample_df):
    # Конец первого дня месяца: только транзакция от 01.05 10:00
    filtered = utils.filter_operations_by_date(sample_df, datetime(2020, 5, 1, 23, 59, 59))
    assert len(filtered) == 1
    assert filtered["Дата операции"].iloc[0] == pd.Timestamp("2020-05-01 10:00:00")


def test_filter_operations_by_date_midnight_excludes_later_same_day(sample_df):
    # Граница в полночь 01.05: транзакция 01.05 10:00 ещё «не наступила»
    filtered = utils.filter_operations_by_date(sample_df, datetime(2020, 5, 1, 0, 0, 0))
    assert len(filtered) == 0


def test_filter_does_not_mutate_original(sample_df):
    utils.filter_operations_by_date(sample_df, datetime(2020, 5, 20, 23, 59, 59))
    assert sample_df["Дата операции"].iloc[0] == "01.05.2020 10:00:00"


# ---------- Карты: расходы и кешбэк ----------

def test_get_card_stats(sample_df):
    filtered = utils.filter_operations_by_date(sample_df, datetime(2020, 5, 20, 23, 59, 59))
    stats = utils.get_card_stats(filtered)
    by_card = {item["last_digits"]: item for item in stats}
    assert by_card["7197"]["total_spent"] == 1250.5
    assert by_card["7197"]["cashback"] == 12.5  # 1250.5 / 100, float-округление даёт 12.5
    assert by_card["4556"]["total_spent"] == 300.0
    assert by_card["4556"]["cashback"] == 3.0


def test_get_card_stats_ignores_income(sample_df):
    sample_df.loc[0, "Сумма платежа"] = 1000.0  # поступление, не расход
    filtered = utils.filter_operations_by_date(sample_df, datetime(2020, 5, 20, 23, 59, 59))
    by_card = {item["last_digits"]: item for item in utils.get_card_stats(filtered)}
    assert by_card["7197"]["total_spent"] == 250.5


def test_get_card_stats_empty():
    empty = pd.DataFrame(columns=["Дата операции", "Номер карты", "Сумма платежа"])
    assert utils.get_card_stats(empty) == []


# ---------- Топ-5 транзакций ----------

def test_get_top_transactions_sorted_descending(sample_df):
    filtered = utils.filter_operations_by_date(sample_df, datetime(2020, 5, 20, 23, 59, 59))
    top = utils.get_top_transactions(filtered)
    assert len(top) == 3
    amounts = [t["amount"] for t in top]
    assert amounts == sorted(amounts, reverse=True)
    assert top[0]["amount"] == 1000.0


def test_get_top_transactions_limited_to_five():
    rows = {
        "Дата операции": [f"0{i}.05.2020 10:00:00" for i in range(1, 8)],
        "Сумма платежа": [-i * 100 for i in range(7, 0, -1)],
        "Категория": ["А"] * 7,
        "Описание": [f"Трата {i}" for i in range(7)],
        "Номер карты": ["*1111"] * 7,
    }
    top = utils.get_top_transactions(pd.DataFrame(rows))
    assert len(top) == 5
    assert top[0]["amount"] == 700.0  # самая крупная трата первая


def test_get_top_transactions_fields_and_date_format(sample_df):
    filtered = utils.filter_operations_by_date(sample_df, datetime(2020, 5, 20, 23, 59, 59))
    top = utils.get_top_transactions(filtered)
    for t in top:
        assert set(t.keys()) == {"date", "amount", "category", "description"}
        assert len(t["date"].split(".")) == 3  # формат dd.mm.yyyy


def test_get_top_transactions_empty():
    empty = pd.DataFrame(columns=["Дата операции", "Сумма платежа", "Категория", "Описание"])
    assert utils.get_top_transactions(empty) == []


# ---------- Категории: топ-N + «Остальное» ----------

def test_get_category_groups_top_n(sample_df):
    filtered = utils.filter_operations_by_date(sample_df, datetime(2020, 5, 20, 23, 59, 59))
    groups = utils.get_category_groups(filtered, top_n=2)
    assert groups == [
        {"category": "Супермаркеты", "amount": 1000},
        {"category": "Рестораны", "amount": 300},
        {"category": "Остальное", "amount": 250},
    ]


def test_get_category_groups_rest_category():
    rows = {
        "Дата операции": [f"0{i % 9 + 1}.05.2020 10:00:00" for i in range(10)],
        "Сумма платежа": [-100.0 * (i + 1) for i in range(10)],
        "Категория": [f"Категория {i}" for i in range(10)],
    }
    groups = utils.get_category_groups(pd.DataFrame(rows), top_n=7)
    assert len(groups) == 8  # 7 категорий + «Остальное»
    # Топ-7 покрывает суммы 1000..400; остаток: 300 + 200 + 100 = 600
    assert groups[-1] == {"category": "Остальное", "amount": 600}
    assert all(isinstance(g["amount"], int) for g in groups)


def test_get_category_groups_empty():
    assert utils.get_category_groups(pd.DataFrame(columns=["Категория", "Сумма платежа"])) == []


# ---------- Настройки пользователя ----------

def test_read_user_settings_valid(tmp_path):
    path = tmp_path / "settings.json"
    path.write_text(json.dumps({"user_currencies": ["USD"], "user_stocks": ["AAPL"]}), encoding="utf-8")
    assert utils.read_user_settings(str(path)) == {"user_currencies": ["USD"], "user_stocks": ["AAPL"]}


def test_read_user_settings_missing_file():
    result = utils.read_user_settings("nonexistent.json")
    assert result == {"user_currencies": [], "user_stocks": []}


# ---------- Курс валют (API заглушается через monkeypatch) ----------

def test_get_currency_rates_ok(monkeypatch):
    class FakeResponse:
        def raise_for_status(self):
            pass

        def json(self):
            return {"rates": {"RUB": 92.5, "USD": 0.0111, "EUR": 0.0101}}

    monkeypatch.setattr(requests, "get", lambda *a, **kw: FakeResponse())
    result = utils.get_currency_rates(["USD", "EUR"])
    by_code = {item["currency"]: item["rate"] for item in result}
    assert by_code["USD"] == round(92.5 / 0.0111, 2)
    assert by_code["EUR"] == round(92.5 / 0.0101, 2)
    assert all(item["rate"] > 0 for item in result)


def test_get_currency_rates_api_error(monkeypatch):
    def fail(*a, **kw):
        raise requests.RequestException("нет сети")

    monkeypatch.setattr(requests, "get", fail)
    assert utils.get_currency_rates(["USD"]) == []


def test_get_currency_rates_no_rub(monkeypatch):
    class FakeResponse:
        def raise_for_status(self):
            pass

        def json(self):
            return {"rates": {"USD": 1.0}}

    monkeypatch.setattr(requests, "get", lambda *a, **kw: FakeResponse())
    assert utils.get_currency_rates(["USD"]) == []


def test_get_currency_rates_unknown_currency(monkeypatch):
    class FakeResponse:
        def raise_for_status(self):
            pass

        def json(self):
            return {"rates": {"RUB": 92.5}}

    monkeypatch.setattr(requests, "get", lambda *a, **kw: FakeResponse())
    assert utils.get_currency_rates(["XXX"]) == []


# ---------- Цены акций (API заглушается) ----------

@pytest.fixture
def fake_stock_api(monkeypatch):
    def fake_get(url, *args, **kwargs):
        symbol = url.rsplit("/", maxsplit=1)[-1]

        class FakeResponse:
            def raise_for_status(self):
                pass

            def json(self):
                if symbol == "BAD":
                    raise requests.RequestException("сервис недоступен")
                return {"chart": {"result": [{"meta": {"regularMarketPrice": 150.25}}]}}

        return FakeResponse()

    monkeypatch.setattr(requests, "get", fake_get)


def test_get_stock_prices_ok(fake_stock_api):
    result = utils.get_stock_prices(["AAPL", "MSFT"])
    assert result == [
        {"stock": "AAPL", "price": 150.25},
        {"stock": "MSFT", "price": 150.25},
    ]


def test_get_stock_prices_one_fails_others_ok(fake_stock_api):
    result = utils.get_stock_prices(["BAD", "AAPL", "TSLA"])
    assert len(result) == 2  # ошибка по одной акции не прерывает остальные
    assert {item["stock"] for item in result} == {"AAPL", "TSLA"}


def test_get_stock_prices_all_fail(monkeypatch):
    def fail(*a, **kw):
        raise requests.RequestException("нет сети")

    monkeypatch.setattr(requests, "get", fail)
    assert utils.get_stock_prices(["AAPL"]) == []
