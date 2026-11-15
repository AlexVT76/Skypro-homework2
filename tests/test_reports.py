from datetime import datetime

import pandas as pd
import pytest

from src import reports


@pytest.fixture
def df():
    return pd.DataFrame(
        {
            "Дата операции": [
                "12.05.2020 10:00:00",  # вторник
                "13.05.2020 12:00:00",  # среда
                "16.05.2020 12:00:00",  # суббота
            ],
            "Сумма платежа": [-1000.0, -2000.0, -500.0],
            "Категория": ["Супермаркеты", "Супермаркеты", "Развлечения"],
        }
    )


def test_spending_by_category(df):
    result = reports.spending_by_category(df, "Супермаркеты", "2020-06-01 00:00:00")
    assert result == {"category": "Супермаркеты", "total_amount": 3000.0}


def test_spending_workday_weekend(df):
    result = reports.spending_workday_weekend(df, "2020-06-01 00:00:00")
    assert result["weekend"] == 500.0
    assert result["workday"] == 1500.0
