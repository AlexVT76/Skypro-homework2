
import json
from datetime import datetime
from typing import Any
from pathlib import Path

import pandas as pd
import requests
from dotenv import load_dotenv

load_dotenv()

USER_SETTINGS_PATH = "user_settings.json"
CURRENCY_API_URL = "https://open.er-api.com/v6/latest/USD"
STOCKS_API_URL = "https://query1.finance.yahoo.com/v8/finance/chart"

CASH_CATEGORIES = ["Наличные", "Переводы"]

BASE_DIR = Path(__file__).resolve().parent.parent

def read_user_settings(path: str = USER_SETTINGS_PATH) -> dict[str, Any]:
    """Читает пользовательские настройки (валюты и акции)."""
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {"user_currencies": [], "user_stocks": []}


def read_operations(path: str | None = None) -> pd.DataFrame:
    """Читает выписку из Excel-файла; по умолчанию — data/operations.xls в корне проекта."""
    file_path = Path(path) if path else BASE_DIR / "data" / "operations.xls"
    return pd.read_excel(file_path)


def get_greeting(dt: datetime) -> str:
    """Возвращает приветствие по временным интервалам:
    06:00–11:59 — утро, 12:00–17:59 — день, 18:00–22:59 — вечер, 23:00–05:59 — ночь."""
    hour = dt.hour
    if hour < 6:
        return "Доброй ночи"
    if hour < 12:
        return "Доброе утро"
    if hour < 18:
        return "Добрый день"
    if hour < 23:
        return "Добрый вечер"
    return "Доброй ночи"


def filter_operations_by_date(df: pd.DataFrame, dt: datetime) -> pd.DataFrame:
    """Оставляет транзакции с начала месяца по входящую дату включительно."""
    df = df.copy()
    df["Дата операции"] = pd.to_datetime(df["Дата операции"], format="%d.%m.%Y %H:%M:%S")
    start = dt.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    mask = (df["Дата операции"] >= start) & (df["Дата операции"] <= dt)
    return df.loc[mask]


def get_card_stats(df: pd.DataFrame) -> list[dict[str, Any]]:
    """Расходы и кешбэк по каждой карте."""
    if df.empty:
        return []
    spending = df[df["Сумма платежа"] < 0].copy()
    spending["last_digits"] = spending["Номер карты"].astype(str).str[-4:]
    result = []
    for card, group in spending.groupby("last_digits"):
        total = round(abs(group["Сумма платежа"].sum()), 2)
        result.append(
            {"last_digits": card, "total_spent": total, "cashback": round(total / 100, 2)}
        )
    return result



def get_top_transactions(df: pd.DataFrame, n: int = 5) -> list[dict[str, Any]]:
    """Возвращает n самых крупных транзакций-расходов, отсортированных по убыванию суммы."""
    if df.empty:
        return []
    spending = df[df["Сумма платежа"] < 0].copy()
    top = spending.nsmallest(n, "Сумма платежа")
    result = []
    for _, row in top.iterrows():
        result.append(
            {
                "date": pd.to_datetime(row["Дата операции"]).strftime("%d.%m.%Y"),
                "amount": abs(round(float(row["Сумма платежа"]), 2)),
                "category": row["Категория"],
                "description": row["Описание"],
            }
        )
    return result



def get_category_groups(df: pd.DataFrame, top_n: int = 7) -> list[dict[str, Any]]:
    """Группирует транзакции по категориям: топ-N категорий, остальные — в «Остальное».
    Суммы округляются до целых."""
    if df.empty:
        return []
    groups = df.groupby("Категория")["Сумма платежа"].sum().abs().sort_values(ascending=False)
    rounded = groups.round().astype(int)
    result = [{"category": cat, "amount": int(amount)} for cat, amount in rounded.head(top_n).items()]
    rest = int(rounded.iloc[top_n:].sum())
    if rest > 0:
        result.append({"category": "Остальное", "amount": rest})
    return result


def get_currency_rates(currencies: list[str]) -> list[dict[str, Any]]:
    """Получает курсы валют к рублю через открытый API."""
    result = []
    try:
        response = requests.get(CURRENCY_API_URL, timeout=10)
        response.raise_for_status()
        data = response.json()
    except requests.RequestException:
        return result
    rub_rate = data.get("rates", {}).get("RUB")
    if not rub_rate:
        return result
    for code in currencies:
        rate = data.get("rates", {}).get(code)
        if rate:
            result.append({"currency": code, "rate": round(rub_rate / rate, 2)})
    return result


def get_stock_prices(stocks: list[str]) -> list[dict[str, Any]]:
    """Получает цены акций через Yahoo Finance. """
    headers = {"User-Agent": "Mozilla/5.0"}
    result = []
    for symbol in stocks:
        try:
            response = requests.get(
                f"{STOCKS_API_URL}/{symbol}",
                params={"interval": "1d", "range": "1d"},
                headers=headers,
                timeout=10,
            )
            response.raise_for_status()
            meta = response.json()["chart"]["result"][0]["meta"]
            price = meta.get("regularMarketPrice")
            if price is not None:
                result.append({"stock": symbol, "price": round(float(price), 2)})
        except (requests.RequestException, KeyError, IndexError):
            pass
    return result
