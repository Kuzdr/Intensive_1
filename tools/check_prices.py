# -*- coding: utf-8 -*-
r"""Проверка цен: валюта цены должна соответствовать стране события.

    python -X utf8 tools\check_prices.py

Правило пользователя 15.10.2026: если цена не в рублях, она должна быть в
валюте страны, где проходит событие. Скрипт читает `data/events.json`, для
каждого события определяет ожидаемую валюту по полям `city`/`place`
(незнакомое место = Россия, рубль) и сверяет с валютой итоговой цены.

Пример ошибки, которую ловит проверка: событие в Санкт-Петербурге, а цена
вышла «2 USD» — потому что в прозе аннотации стоял оборот «бюджет $ 2 млрд».

Скрипт НЕ имеет побочных эффектов (ничего не пишет), возвращает 1 при
найденных проблемах — годится для прогона в конвейере.
"""
import importlib.util
import os
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)


def load_scrape():
    spec = importlib.util.spec_from_file_location(
        "scrape", os.path.join(ROOT, "scrape.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def main():
    scrape = load_scrape()
    fp = os.path.join(ROOT, "data", "events.json")
    if not os.path.exists(fp):
        print("Нет data/events.json — нечего проверять.")
        return 0
    events = scrape.load_old_events()
    problems = scrape.check_price_country(events)
    if problems:
        print("=== ПРОВЕРКА ЦЕН: найдены несоответствия (валюта ≠ стране) ===")
        for p in problems:
            print("  " + p)
        print("РЕЗУЛЬТАТ: %d проблем(ы) — исправить." % len(problems))
        return 1
    print("Проверка цен: OK (%d событий, несоответствий нет)." % len(events))
    return 0


if __name__ == "__main__":
    sys.exit(main())
