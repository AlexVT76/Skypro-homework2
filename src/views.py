
import json
from datetime import datetime
from typing import Any

import pandas as pd

from src import utils


def main_page(datetime_str: str, operations: pd.DataFrame) -> str:
    """JSON-ответ для страницы «Главная»: приветствие, карты, топ-5 транзакций, курсы и акции."""
    dt = datetime.strptime(datetime_str, "%Y-%m-%d %H:%M:%S")
    settings = utils.read_user_settings()
    month_df = utils.filter_operations_by_date(operations, dt)

    result: dict[str, Any] = {
        "greeting": utils.get_greeting(dt),
        "cards": utils.get_card_stats(month_df),
        "top_transactions": utils.get_top_transactions(month_df),
        "currency_rates": utils.get_currency_rates(settings.get("user_currencies", [])),
        "stock_prices": utils.get_stock_prices(settings.get("user_stocks", [])),
    }
    return json.dumps(result, ensure_ascii=False, indent=2)


def events_page(datetime_str: str, operations: pd.DataFrame) -> str:
    """JSON-ответ для страницы «События»: расходы и поступления по категориям,
    переводы и наличные отдельным блоком, курсы валют и акции."""
    dt = datetime.strptime(datetime_str, "%Y-%m-%d %H:%M:%S")
    settings = utils.read_user_settings()
    month_df = utils.filter_operations_by_date(operations, dt)

    cash_mask = month_df["Категория"].isin(utils.CASH_CATEGORIES)
    expenses = month_df[(month_df["Сумма платежа"] < 0) & ~cash_mask]
    income = month_df[month_df["Сумма платежа"] > 0]
    transfers_cash = month_df[cash_mask & (month_df["Сумма платежа"] < 0)]

    result: dict[str, Any] = {
        "expenses": utils.get_category_groups(expenses),
        "income": utils.get_category_groups(income, top_n=7),
        "transfers_and_cash": utils.get_category_groups(transfers_cash, top_n=999),
        "currency_rates": utils.get_currency_rates(settings.get("user_currencies", [])),
        "stock_prices": utils.get_stock_prices(settings.get("user_stocks", [])),
    }
    return json.dumps(result, ensure_ascii=False, indent=2)
