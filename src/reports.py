
from datetime import datetime
from typing import Any

import pandas as pd

DATE_FORMAT = "%Y-%m-%d %H:%M:%S"
WEEKDAY_NAMES = ["Понедельник", "Вторник", "Среда", "Четверг", "Пятница", "Суббота", "Воскресенье"]


def _get_period(df: pd.DataFrame, end: datetime, months: int = 3) -> pd.DataFrame:
    """Фильтрует траты за последние `months` месяцев до даты end включительно."""
    df = df.copy()
    df["Дата операции"] = pd.to_datetime(df["Дата операции"], format="%d.%m.%Y %H:%M:%S")
    start = end - pd.DateOffset(months=months)
    spending = df[(df["Сумма платежа"] < 0) & (df["Дата операции"] >= start) & (df["Дата операции"] <= end)]
    return spending


def spending_by_category(operations: pd.DataFrame, category: str, date_str: str) -> dict[str, Any]:
    """Сумма трат по категории за последние 3 месяца от входящей даты."""
    end = datetime.strptime(date_str, DATE_FORMAT)
    spending = _get_period(operations, end)
    total = spending.loc[spending["Категория"] == category, "Сумма платежа"].abs().sum()
    return {"category": category, "total_amount": round(float(total), 2)}


def spending_by_weekday(operations: pd.DataFrame, date_str: str) -> dict[str, Any]:
    """Средняя сумма трат для каждого дня недели за последние 3 месяца."""
    end = datetime.strptime(date_str, DATE_FORMAT)
    spending = _get_period(operations, end)
    if spending.empty:
        return {}
    weeks = max(1, spending["Дата операции"].dt.to_period("W").nunique())
    totals = spending.groupby(spending["Дата операции"].dt.dayofweek)["Сумма платежа"].sum().abs()
    return {WEEKDAY_NAMES[day]: round(float(amount) / weeks, 2) for day, amount in totals.items()}


def spending_workday_weekend(operations: pd.DataFrame, date_str: str) -> dict[str, Any]:
    """Средняя сумма трат в рабочий день и в выходной за последние 3 месяца."""
    end = datetime.strptime(date_str, DATE_FORMAT)
    spending = _get_period(operations, end)
    if spending.empty:
        return {}
    weekday = spending["Дата операции"].dt.dayofweek
    work_total = spending.loc[weekday < 5, "Сумма платежа"].abs().sum()
    weekend_total = spending.loc[weekday >= 5, "Сумма платежа"].abs().sum()
    work_days = spending.loc[weekday < 5, "Дата операции"].dt.to_period("D").nunique()
    weekend_days = spending.loc[weekday >= 5, "Дата операции"].dt.to_period("D").nunique()
    return {
        "workday": round(float(work_total) / max(1, work_days), 2),
        "weekend": round(float(weekend_total) / max(1, weekend_days), 2),
    }
