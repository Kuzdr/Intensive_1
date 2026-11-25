# Источники мониторинга (страницы списков/афиш)

> Список **страниц-источников для поиска новых событий** (афиши/списки), а не отдельных карточек. Обновлять вручную при появлении новых страниц. Для каждого источника указаны основной и запасные способы обхода и ссылки на инструкции в репозитории.

## Структура и поля (для расширения)

В таблицах используются поля: **Организатор/лента**, **URL страницы-списка**, **Тип**, **Основной способ**, **Запасные способы**, **Инструкции/примечания** (сюда можно добавлять ссылки на файлы правил, например `AGENTS.md`, `.opencode/skills/update-data/SKILL.md`, `.opencode/skills/event-description/reference/availability_log.md`).

---

## Общие правила обхода (из проекта)

- **Любой `timepad.ru` / поддомены Timepad (списки/афиши, карточки при разборе): ОСНОВНОЙ способ — запуск Edge через CDP/скрипты проекта.** Не использовать `webfetch`/прямые HTTP как первый шаг. Инструменты: `tools/cdp_read.py` (снятие HTML/контента через CDP), `tools/timepad_parse.py` (разбор карточек из сохранённых данных). Кэши: `data/raw/cdp/` (если есть). Запасные: сохранённые HTML в `data/raw/cdp/`, ручной просмотр в Edge и сохранение для разбора. См. также `AGENTS.md` (раздел «Способ получения страниц Timepad…») и `.opencode/skills/update-data/SKILL.md`.
- **`elementy.ru/events` (общая афиша):** основной сбор — `scrape.py`, разбор карточек — `tools/elementy_detail.py` (HTTP). При ошибках/пустой афише — правило недоступности: сообщить пользователю, записать в `.opencode/skills/event-description/reference/availability_log.md` (повторы 1 мин → 5 мин), не затирать `data/events.json` при сбое. См. `AGENTS.md`, `ПАМЯТКА.md`.
- **JS-тяжёлые сайты (часть `vdnh.ru` и др.):** `webfetch` может вернуть только навигацию. Запасные: кэши в `data/raw/`, CDP/ручной просмотр в Edge. При недоступности — лог в `availability_log.md`.
- **Обычные HTML-сайты:** `webfetch` (text/markdown) первой попыткой; при ошибках — повторы по правилу недоступности, затем кэши/CDP/ручной просмотр. Проблемы доступа фиксировать в `.opencode/skills/event-description/reference/availability_log.md` при необходимости.

---

## Элементы (общая афиша)

| Организатор/лента | URL страницы-списка | Тип | Основной способ | Запасные способы | Инструкции/примечания |
|---|---|---|---|---|---|
| Элементы (афиша) | https://elementy.ru/events | HTML (список) | `scrape.py`, `tools/elementy_detail.py` (HTTP) | Повторы по правилу недоступности; лог `availability_log.md`. При сбое не править `data/events.json`. | См. `AGENTS.md`, `ПАМЯТКА.md`, `update-data` skill. |

---

## Архэ

**Дубли URL событий:** одни и те же события могут встречаться в разных форматах; склеивать дубли по смыслу (дата/название/автор). Предпочтительно: (1) `https://arhe.msk.ru/?p=<ID>`; (2) `https://arhe.msk.ru/?post_type=tribe_events&p=<ID>` (ID может отличаться на 1 — сверять по содержимому); (3) текстовый `https://arhe.msk.ru/?tribe_events=…` — только при отсутствии других.

| Организатор/лента | URL страницы-списка | Тип | Основной способ | Запасные способы | Инструкции/примечания |
|---|---|---|---|---|---|
| Архэ (страница) | https://arhe.msk.ru/?page_id=369 | HTML | webfetch / HTTP | Повторы при недоступности; кэши/CDP/ручной просмотр | См. `update-data` skill (раздел Архэ), `AGENTS.md`. |
| Архэ (лента Tribe Events) | https://arhe.msk.ru/?post_type=tribe_events | HTML | webfetch / HTTP | Повторы при недоступности; кэши/CDP | Основная лента сайта Архэ. |
| Архэ (страница) | https://arhe.msk.ru/?page_id=332 | HTML | webfetch / HTTP | Повторы при недоступности; кэши/CDP | Страница-список/афиша. |
| Архэ (страница) | https://arhe.msk.ru/?page_id=3466 | HTML | webfetch / HTTP | Повторы при недоступности; кэши/CDP | Страница-список/афиша. |
| Архэ (страница) | https://arhe.msk.ru/?page_id=81748 | HTML | webfetch / HTTP | Повторы при недоступности; кэши/CDP | Страница-список/афиша. |
| Архэ (страница) | https://arhe.msk.ru/?page_id=32233 | HTML | webfetch / HTTP | Повторы при недоступности; кэши/CDP | Страница-список/афиша. |
| Архэ (страница) | https://arhe.msk.ru/?page_id=77150 | HTML | webfetch / HTTP | Повторы при недоступности; кэши/CDP | Страница-список/афиша. |
| Архэ (страница) | https://arhe.msk.ru/?page_id=14417 | HTML | webfetch / HTTP | Повторы при недоступности; кэши/CDP | Добавлено по запросу. |
| Архэ, Timepad (Москва/общая лента) | https://arhe-events.timepad.ru/events/ | Timepad (список) | **Edge + CDP** (`tools/cdp_read.py`, `tools/timepad_parse.py`) | Кэши `data/raw/cdp/`; ручной просмотр в Edge + сохранение | **Timepad — только Edge/CDP.** См. `AGENTS.md`, `update-data` skill. |
| Архэ, Timepad (СПб) | https://tsentr-arhe-v-sankt-peter.timepad.ru/events/ | Timepad (список) | **Edge + CDP** (`tools/cdp_read.py`, `tools/timepad_parse.py`) | Кэши `data/raw/cdp/`; ручной просмотр в Edge + сохранение | **Timepad — только Edge/CDP.** См. `AGENTS.md`, `update-data` skill. |

---

## ВДНХ

| Организатор/лента | URL страницы-списка | Тип | Основной способ | Запасные способы | Инструкции/примечания |
|---|---|---|---|---|---|
| ВДНХ (сайт) | https://vdnh.ru/events/ | HTML/JS (SPA/динамика) | **CDP/ручной просмотр в Edge** (JS обязателен) | Кэши `data/raw/*`, повторный обход после ручного прогона/сохранения | **Важно:** применять фильтр «Лекции»; события подгружаются порциями — нужно итеративно нажимать «Показать ещё» (всё через JS). `webfetch` обычно даёт только оболочку. См. `AGENTS.md`, `update-data` skill, при проблемах — `availability_log.md`. |
| Лекторий ВДНХ (Timepad) | https://lektorij-vdnh.timepad.ru/events/ | Timepad (список) | **Edge + CDP** (`tools/cdp_read.py`, `tools/timepad_parse.py`) | Кэши `data/raw/cdp/`, ручной просмотр в Edge | **Timepad — только Edge/CDP.** |
| Космос и авиация ВДНХ (Timepad) | https://cosmos-vdnh.timepad.ru/events/ | Timepad (список) | **Edge + CDP** (`tools/cdp_read.py`, `tools/timepad_parse.py`) | Кэши `data/raw/cdp/`, ручной просмотр в Edge | **Timepad — только Edge/CDP.** |
| Музей «Слово» (ВДНХ, Timepad) | https://slovo-vdnh.timepad.ru/events/ | Timepad (список) | **Edge + CDP** (`tools/cdp_read.py`, `tools/timepad_parse.py`) | Кэши `data/raw/cdp/`, ручной просмотр в Edge | **Timepad — только Edge/CDP.** Выявлено по прототипам/данным. |
| Павильон «АТОМ» (ВДНХ, Timepad) | https://atom-lab.timepad.ru/events/ | Timepad (список) | **Edge + CDP** (`tools/cdp_read.py`, `tools/timepad_parse.py`) | Кэши `data/raw/cdp/`, ручной просмотр в Edge | **Timepad — только Edge/CDP.** Добавлено по указанию пользователя. |
| Центр биотехнологий «БИОТЕХ» (ВДНХ, Timepad) | https://muzey-biotekh.timepad.ru/events/ | Timepad (список) | **Edge + CDP** (`tools/cdp_read.py`, `tools/timepad_parse.py`) | Кэши `data/raw/cdp/`, ручной просмотр в Edge | **Timepad — только Edge/CDP.** Добавлено по указанию пользователя. |

> При появлении других Timepad-поддоменов ВДНХ добавлять строки с пометкой «Timepad — только Edge/CDP».

---

## Timepad-ленты других организаторов (из репозитория)

Ниже — страницы списков `*/events/` на Timepad, найденные по ссылкам в `data/events.json` и прототипах. Для **всех** этих URL основной способ — **запуск Edge через CDP** (`tools/cdp_read.py`, `tools/timepad_parse.py`), без `webfetch` как первого шага.

| Организатор/лента (по домену) | URL страницы-списка | Тип | Основной способ | Запасные способы | Инструкции/примечания |
|---|---|---|---|---|---|
| darwinmuseum.timepad.ru | https://darwinmuseum.timepad.ru/events/ | Timepad (список) | **Edge + CDP** (`tools/cdp_read.py`, `tools/timepad_parse.py`) | Кэши `data/raw/cdp/`, ручной просмотр в Edge | Timepad — только Edge/CDP. См. `update-data` skill. |
| fondnauk.timepad.ru | https://fondnauk.timepad.ru/events/ | Timepad (список) | **Edge + CDP** (`tools/cdp_read.py`, `tools/timepad_parse.py`) | Кэши `data/raw/cdp/`, ручной просмотр в Edge | Timepad — только Edge/CDP. |
| institut-filosofii--2026.timepad.ru | https://institut-filosofii--2026.timepad.ru/events/ | Timepad (список) | **Edge + CDP** (`tools/cdp_read.py`, `tools/timepad_parse.py`) | Кэши `data/raw/cdp/`, ручной просмотр в Edge | Timepad — только Edge/CDP. |
| istorichka.timepad.ru | https://istorichka.timepad.ru/events/ | Timepad (список) | **Edge + CDP** (`tools/cdp_read.py`, `tools/timepad_parse.py`) | Кэши `data/raw/cdp/`, ручной просмотр в Edge | Timepad — только Edge/CDP. |
| moscowzoo.timepad.ru | https://moscowzoo.timepad.ru/events/ | Timepad (список) | **Edge + CDP** (`tools/cdp_read.py`, `tools/timepad_parse.py`) | Кэши `data/raw/cdp/`, ручной просмотр в Edge | Timepad — только Edge/CDP. |
| neurocampus.timepad.ru | https://neurocampus.timepad.ru/events/ | Timepad (список) | **Edge + CDP** (`tools/cdp_read.py`, `tools/timepad_parse.py`) | Кэши `data/raw/cdp/`, ручной просмотр в Edge | Timepad — только Edge/CDP. |
| oxta8.timepad.ru | https://oxta8.timepad.ru/events/ | Timepad (список) | **Edge + CDP** (`tools/cdp_read.py`, `tools/timepad_parse.py`) | Кэши `data/raw/cdp/`, ручной просмотр в Edge | Timepad — только Edge/CDP. |
| planetalib.timepad.ru | https://planetalib.timepad.ru/events/ | Timepad (список) | **Edge + CDP** (`tools/cdp_read.py`, `tools/timepad_parse.py`) | Кэши `data/raw/cdp/`, ручной просмотр в Edge | Timepad — только Edge/CDP. |
| politvostok.timepad.ru | https://politvostok.timepad.ru/events/ | Timepad (список) | **Edge + CDP** (`tools/cdp_read.py`, `tools/timepad_parse.py`) | Кэши `data/raw/cdp/`, ручной просмотр в Edge | Timepad — только Edge/CDP. |
| soobshchestvo-vsmysle.timepad.ru | https://soobshchestvo-vsmysle.timepad.ru/events/ | Timepad (список) | **Edge + CDP** (`tools/cdp_read.py`, `tools/timepad_parse.py`) | Кэши `data/raw/cdp/`, ручной просмотр в Edge | Timepad — только Edge/CDP. |
| spbstuni.timepad.ru | https://spbstuni.timepad.ru/events/ | Timepad (список) | **Edge + CDP** (`tools/cdp_read.py`, `tools/timepad_parse.py`) | Кэши `data/raw/cdp/`, ручной просмотр в Edge | Timepad — только Edge/CDP. |
| spitsbergen.timepad.ru | https://spitsbergen.timepad.ru/events/ | Timepad (список) | **Edge + CDP** (`tools/cdp_read.py`, `tools/timepad_parse.py`) | Кэши `data/raw/cdp/`, ручной просмотр в Edge | Timepad — только Edge/CDP. |
| yadro-engineer.timepad.ru | https://yadro-engineer.timepad.ru/events/ | Timepad (список) | **Edge + CDP** (`tools/cdp_read.py`, `tools/timepad_parse.py`) | Кэши `data/raw/cdp/`, ручной просмотр в Edge | Timepad — только Edge/CDP. |
| your-sector-of-space.timepad.ru | https://your-sector-of-space.timepad.ru/events/ | Timepad (список) | **Edge + CDP** (`tools/cdp_read.py`, `tools/timepad_parse.py`) | Кэши `data/raw/cdp/`, ручной просмотр в Edge | Timepad — только Edge/CDP. |
| zaobiblio.timepad.ru | https://zaobiblio.timepad.ru/events/ | Timepad (список) | **Edge + CDP** (`tools/cdp_read.py`, `tools/timepad_parse.py`) | Кэши `data/raw/cdp/`, ручной просмотр в Edge | Timepad — только Edge/CDP. |
| zilcc.timepad.ru | https://zilcc.timepad.ru/events/ | Timepad (список) | **Edge + CDP** (`tools/cdp_read.py`, `tools/timepad_parse.py`) | Кэши `data/raw/cdp/`, ручной просмотр в Edge | Timepad — только Edge/CDP. |

---

## Прочие страницы-списки (не Timepad), встречающиеся в данных/прототипах

Ниже — отдельные URL-списки/афиши организаторов, которые встречались в репозитории. При появлении новых — добавлять сюда по тому же шаблону, указывая инструкции в колонке «Инструкции/примечания» (`AGENTS.md`, `.opencode/skills/update-data/SKILL.md`, `availability_log.md`).

| Организатор/лента | URL страницы-списка | Тип | Основной способ | Запасные способы | Инструкции/примечания |
|---|---|---|---|---|---|
| ZIL Cultural Center (ZILCC) | https://zilcc.ru/afisha | HTML | webfetch (text/markdown) первой попыткой | Повторы по правилу недоступности; кэши/CDP/ручной просмотр | См. `update-data` skill, `AGENTS.md`, `availability_log.md` при ошибках. |
| Московский планетарий (курсы/афиша) | https://planetarium-moscow.ru/courses/tribuna-uchenogo | HTML | webfetch первой попыткой | Повторы/кэши/CDP при блокировках | Раздел «Трибуна учёного» (пример страницы-ленты). Проверять другие разделы курсов при необходимости. См. `AGENTS.md`. |
| Политехнический музей — цикл «Вечерняя школа Политехнического музея» | https://polymus.ru/education/cycle/vechernyaya-shkola-politekhnicheskogo-muzeya | HTML | webfetch первой попыткой | Кэши/ручной просмотр | Страница цикла (список анонсов цикла). Карточки событий — `polymus.ru/events/detail/...`. См. `AGENTS.md`. |
| Лекторий юного географа (МГУ, справочно) | https://www.geogr.msu.ru/admission/lektory/ | HTML | webfetch первой попыткой | Повторы/кэши | Справочная страница лектория; актуальные анонсы часто в прототипах/других источниках. См. карточку лектория в `reference/lectories.md`. |

---

## Как добавлять новые источники

1. Добавлять **только страницы-списки/афиши** (или явно помеченные ленты), не отдельные карточки событий, если иное не оговорено.
2. Для любых URL с доменом `timepad.ru` / поддоменами Timepad: в столбце «Основной способ» указывать **Edge + CDP** (`tools/cdp_read.py`, `tools/timepad_parse.py`), в «Инструкции/примечания» — ссылку на `AGENTS.md` и/или `update-data` skill.
3. Для нестандартного обхода (капча, JS, API и т.п.) — кратко описать способ и дать ссылку на скрипт/инструкцию в репозитории.
4. При недоступности источника действовать по `AGENTS.md`: уведомить пользователя, писать в `availability_log.md`, повторять 1 мин → 5 мин, при необходимости дополнять `notes` прототипа.