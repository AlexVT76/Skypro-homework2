

from src import reports, services, utils, views


def main() -> None:
    operations = utils.read_operations()
    print("1 — Главная, 2 — События, 3 — Кешбэк по категориям, "
          "4 — Простой поиск, 5 — Поиск по телефонам, "
          "6 — Траты по категории, 7 — По дням недели, 8 — Рабочий/выходной")
    choice = input("Выберите функцию: ")

    if choice in ("1", "2"):
        dt = input("Дата и время (YYYY-MM-DD HH:MM:SS): ")
        print(views.main_page(dt, operations) if choice == "1" else views.events_page(dt, operations))
    elif choice == "3":
        year, month = int(input("Год: ")), int(input("Месяц (1-12): "))
        print(services.get_cashback_categories(operations, year, month))

    elif choice == "4":
        print(services.simple_search(input("Что искать: "), operations))
    elif choice == "5":
        print(services.search_phone_numbers(operations))
    elif choice == "6":
        print(reports.spending_by_category(operations, input("Категория: "), input("Дата (YYYY-MM-DD HH:MM:SS): ")))
    elif choice == "7":
        print(reports.spending_by_weekday(operations, input("Дата (YYYY-MM-DD HH:MM:SS): ")))
    elif choice == "8":
        print(reports.spending_workday_weekend(operations, input("Дата (YYYY-MM-DD HH:MM:SS): ")))


if __name__ == "__main__":
    main()
