"""Тесты для views.py: main_page и events_page."""

import json
from datetime import datetime

import pandas as pd
import pytest

from src import utils, views


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
            "Сумма платежа": [-1000.0, -250.5, -300.0, 500.0],  # последняя — доход
            "Категория": [
                "Супермаркеты",
                "Транспорт",
                "Наличные",  # cash
                "Супермаркеты",  # доход
            ],
            "Описание": [
                "Пятёрочка",
                "Яндекс.Такси",
                "Снятие наличных",
                "Возврат",
            ],
        }
    )


@pytest.fixture
def mock_settings(monkeypatch):
    """Подменяет read_user_settings на возврат фиксированных настроек."""

    def fake_read(*args, **kwargs):
        return {"user_currencies": ["USD", "EUR"], "user_stocks": ["AAPL", "MSFT"]}

    monkeypatch.setattr(utils, "read_user_settings", fake_read)


def test_main_page_structure(sample_df, mock_settings):
    dt_str = "2020-05-20 12:30:00"
    result_json = views.main_page(dt_str, sample_df)
    result = json.loads(result_json)

    assert isinstance(result, dict)
    assert set(result.keys()) == {"greeting", "cards", "top_transactions", "currency_rates", "stock_prices"}

    # Приветствие
    dt = datetime.strptime(dt_str, "%Y-%m-%d %H:%M:%S")
    assert result["greeting"] == utils.get_greeting(dt)

    # Карты
    month_df = utils.filter_operations_by_date(sample_df, dt)
    expected_cards = utils.get_card_stats(month_df)
    assert result["cards"] == expected_cards

    # Топ-5
    expected_top = utils.get_top_transactions(month_df)
    assert result["top_transactions"] == expected_top

    # Курсы и акции: проверяем, что они не пустые (т.к. mock_settings подменил настройки)
    assert len(result["currency_rates"]) > 0
    assert len(result["stock_prices"]) > 0


def test_main_page_empty_transactions(mock_settings):
    empty_df = pd.DataFrame(columns=["Дата операции", "Номер карты", "Сумма платежа", "Категория", "Описание"])
    result_json = views.main_page("2020-05-20 12:30:00", empty_df)
    result = json.loads(result_json)

    assert result["cards"] == []
    assert result["top_transactions"] == []
    # курсы и акции всё ещё могут быть, если API вернёт — это нормально


def test_main_page_no_settings(monkeypatch):
    """Проверяем, что отсутствие настроек не ломает функцию (возвращает пустые списки)."""

    def fake_read(*args, **kwargs):
        return {}

    monkeypatch.setattr(utils, "read_user_settings", fake_read)
    sample_df = pd.DataFrame(
        {
            "Дата операции": ["01.05.2020 10:00:00"],
            "Номер карты": ["*7197"],
            "Сумма платежа": [-100.0],
            "Категория": ["Супермаркеты"],
            "Описание": ["Пятёрочка"],
        }
    )
    result_json = views.main_page("2020-05-20 12:30:00", sample_df)
    result = json.loads(result_json)

    assert result["currency_rates"] == []
    assert result["stock_prices"] == []


def test_events_page_structure(sample_df, mock_settings):
    dt_str = "2020-05-20 12:30:00"
    result_json = views.events_page(dt_str, sample_df)
    result = json.loads(result_json)

    assert isinstance(result, dict)
    assert set(result.keys()) == {
        "expenses",
        "income",
        "transfers_and_cash",
        "currency_rates",
        "stock_prices",
    }

    dt = datetime.strptime(dt_str, "%Y-%m-%d %H:%M:%S")
    month_df = utils.filter_operations_by_date(sample_df, dt)

    cash_mask = month_df["Категория"].isin(utils.CASH_CATEGORIES)
    expenses = month_df[(month_df["Сумма платежа"] < 0) & ~cash_mask]
    income = month_df[month_df["Сумма платежа"] > 0]
    transfers_cash = month_df[cash_mask & (month_df["Сумма платежа"] < 0)]

    assert result["expenses"] == utils.get_category_groups(expenses)
    assert result["income"] == utils.get_category_groups(income, top_n=7)
    assert result["transfers_and_cash"] == utils.get_category_groups(transfers_cash, top_n=999)


def test_events_page_cash_categories_separated(sample_df, mock_settings):
    """Убеждаемся, что «Наличные» не попадают в expenses, а уходят в transfers_and_cash."""
    dt_str = "2020-05-20 12:30:00"
    result_json = views.events_page(dt_str, sample_df)
    result = json.loads(result_json)

    expense_cats = {item["category"] for item in result["expenses"]}
    cash_cats = {item["category"] for item in result["transfers_and_cash"]}

    # В sample_df категория «Наличные» должна быть только в transfers_and_cash
    assert "Наличные" not in expense_cats
    assert "Наличные" in cash_cats


def test_events_page_income_only(mock_settings):
    """Тестируем случай, когда есть только доходы — расходы и переводы должны быть пустыми."""
    df = pd.DataFrame(
        {
            "Дата операции": ["01.05.2020 10:00:00"],
            "Номер карты": ["*7197"],
            "Сумма платежа": [500.0],
            "Категория": ["Возврат"],
            "Описание": ["Возврат средств"],
        }
    )
    result_json = views.events_page("2020-05-20 12:30:00", df)
    result = json.loads(result_json)

    assert result["expenses"] == []
    assert result["transfers_and_cash"] == []
    assert len(result["income"]) == 1


def test_events_page_invalid_datetime_format():
    """Невалитная строка даты должна вызывать понятную ошибку (ValueError)."""
    sample_df = pd.DataFrame(
        {
            "Дата операции": ["01.05.2020 10:00:00"],
            "Номер карты": ["*7197"],
            "Сумма платежа": [-100.0],
            "Категория": ["Супермаркеты"],
            "Описание": ["Пятёрочка"],
        }
    )
    with pytest.raises(ValueError):
        views.events_page("некорректная дата", sample_df)


def test_views_return_valid_json_string(sample_df, mock_settings):
    """Обе функции возвращают валидный JSON (не выбрасывают ошибок при loads)."""
    main_json = views.main_page("2020-05-20 12:30:00", sample_df)
    events_json = views.events_page("2020-05-20 12:30:00", sample_df)

    assert json.loads(main_json) is not None
    assert json.loads(events_json) is not None
