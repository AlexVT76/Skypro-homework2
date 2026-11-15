
import json
import math
import re
from typing import Any, Dict, List

import pandas as pd


PHONE_PATTERN = r"(?:\+7|8)[\s\-()]*\d{3}[\s\-()]*\d{2,3}[\s\-]*\d{2}[\s\-]*\d{2}"


INDIVIDUAL_TRANSFER_PATTERN = r"^[А-ЯЁ][а-яё]+\s[А-ЯЁ]\.$"


def _to_json(data: Any) -> str:
    """Сериализует данные в JSON-строку (единый формат ответов сервиса)."""
    return json.dumps(data, ensure_ascii=False, indent=2)


def get_cashback_categories(data: pd.DataFrame, year: int, month: int) -> str:
    """Анализ выгодности категорий повышенного кешбэка за указанный месяц."""
    df = data.copy()
    df["Дата операции"] = pd.to_datetime(df["Дата операции"], dayfirst=True)
    month_df = df[(df["Дата операции"].dt.year == year) & (df["Дата операции"].dt.month == month)]
    spending = month_df[month_df["Сумма платежа"] < 0]

    by_category = spending.groupby("Категория")["Сумма платежа"].sum().abs()
    cashback = {category: int(round(amount / 100)) for category, amount in by_category.items()}
    return _to_json(cashback)


def investment_bank(month: str, transactions: List[Dict[str, Any]], limit: int) -> float:
    """Считает сумму, которую удалось бы отложить в «Инвесткопилку» за месяц."""
    expenses_in_month = list(
        filter(
            lambda t: t["Дата операции"][:7] == month
            and isinstance(t["Сумма операции"], (int, float))
            and t["Сумма операции"] < 0,
            transactions,
        )
    )
    total = sum(
        math.ceil(abs(t["Сумма операции"]) / limit) * limit - abs(t["Сумма операции"])
        for t in expenses_in_month
    )
    return round(float(total), 2)


def simple_search(search_string: str, data: pd.DataFrame) -> str:
    """Ищет транзакции по подстроке в описании или категории (без учёта регистра)."""
    df = data.copy()
    df["Дата операции"] = pd.to_datetime(df["Дата операции"], dayfirst=True)

    text = df["Описание"].fillna("").astype(str) + " " + df["Категория"].fillna("").astype(str)
    mask = text.map(lambda s: search_string.lower() in s.lower())

    found = list(
        map(
            lambda row: {
                "date": row["Дата операции"].strftime("%d.%m.%Y"),
                "amount": round(abs(row["Сумма платежа"]), 2),
                "category": row["Категория"],
                "description": row["Описание"],
            },
            df[mask].to_dict("records"),
        )
    )
    return _to_json(found)


def search_phone_numbers(data: pd.DataFrame) -> str:
    """Возвращает JSON со всеми транзакциями, содержащими мобильные номера в описании."""
    df = data.copy()
    df["Дата операции"] = pd.to_datetime(df["Дата операции"], dayfirst=True)

    mask = df["Описание"].fillna("").astype(str).map(lambda s: re.search(PHONE_PATTERN, s) is not None)

    found = list(
        map(
            lambda row: {
                "date": row["Дата операции"].strftime("%d.%m.%Y"),
                "amount": round(abs(row["Сумма платежа"]), 2),
                "category": row["Категория"],
                "description": row["Описание"],
            },
            df[mask].to_dict("records"),
        )
    )
    return _to_json(found)


def search_person_transfers(data: pd.DataFrame) -> str:
    """Возвращает JSON с переводами физлицам: категория «Переводы»,
    в описании — имя и первая буква фамилии с точкой («Валерий А.»)."""
    df = data.copy()
    df["Дата операции"] = pd.to_datetime(df["Дата операции"], dayfirst=True)

    mask = (df["Категория"] == "Переводы") & df["Описание"].fillna("").astype(str).map(
        lambda s: re.search(INDIVIDUAL_TRANSFER_PATTERN, s.strip()) is not None
    )

    found = list(
        map(
            lambda row: {
                "date": row["Дата операции"].strftime("%d.%m.%Y"),
                "amount": round(abs(row["Сумма платежа"]), 2),
                "category": row["Категория"],
                "description": row["Описание"],
            },
            df[mask].to_dict("records"),
        )
    )
    return _to_json(found)
