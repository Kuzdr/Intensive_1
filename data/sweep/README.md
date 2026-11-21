# Регулярные обходы лекториев

Два файла в этой папке можно редактировать прямо в блокноте — это обычный JSON.

## 1. `lectories.json` — список лекториев и источников

Каждый лекторий — отдельный объект:

- `key` — короткий латинский идентификатор (`pryamaya`, `arhe`, …);
- `name` — название, как показывать в отчёте;
- `enabled` — `true`, если лекторий нужно проверять при обходе;
- `collector` — имя сборщика: `pryamaya`, `arhe` или пустая строка;
- `sources` — массив источников (`kind`, `url`, `note`);
- `criteria` — напоминание, что берём, а что нет;
- `reference` — путь к подробной карточке лектория в навыке.

Если `collector` пуст, лекторий всё равно хранится в списке, но при обходе
пропускается — пока для него не написан сборщик. Ссылки при этом не теряются.

## 2. `known_events.json` — реестр известных событий

События сгруппированы по `key` лектория. У каждого события:

- `key` — устойчивый идентификатор (`PR-<id лекции>` у «Прямой речи»,
  `TP-<id Timepad>` у «Архэ»); смена заголовка не меняет ключ;
- `date`, `time`, `title`, `subtitle`, `author`, `url` — что нашли;
- `status` — один из:
  - `candidate` — найдено, решение ещё не принято;
  - `added` — добавлено в прототип/на сайт;
  - `on_elementy` — уже опубликовано на «Элементах»;
  - `rejected` — отвергнуто (причина в `note`);
  - `duplicate` — дубль опубликованного (ID в `note`);
- `note`, `first_seen`, `last_seen`, `updated` — служебные поля.

## Команды

```bat
python -X utf8 tools\sweep_lectories.py --list
python -X utf8 tools\sweep_lectories.py
python -X utf8 tools\sweep_lectories.py --lectory pryamaya
python -X utf8 tools\sweep_lectories.py --refresh
python -X utf8 tools\sweep_lectories.py --bootstrap
python -X utf8 tools\sweep_lectories.py --mark PR-8935 --mark-status added --note "прототип создан"
python -X utf8 tools\sweep_lectories.py --mark PR-8935 --mark-status rejected --note "игра, не лекция"
python -X utf8 tools\sweep_lectories.py --json report.json
```

- Обычный запуск печатает **НОВОЕ** (чего нет в реестре) и сводку по
  известным статусам. Сам реестр не меняется.
- `--bootstrap` один раз добавляет все найденные события в реестр со статусом
  из источника. Повторный запуск ничего не дублирует.
- `--mark` меняет статус одной записи (или создаёт её, если ключа ещё нет).
- `--refresh` обновляет кэш «Архэ» (`data/raw/arhe_calendar.json`).
- Если источник недоступен, обход пишет причину в
  `.opencode/skills/event-description/reference/availability_log.md` и
  продолжает остальные лектории; реестр не портится.
