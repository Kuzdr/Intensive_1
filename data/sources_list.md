# Источники мониторинга (страницы списков/афиш)

> Список **страниц-источников для поиска новых событий** (афиши/списки), а не отдельных карточек. Обновлять вручную при появлении новых страниц. Для каждого источника указаны основной и запасные способы обхода и ссылки на инструкции в репозитории.

## Структура и поля

В таблицах: **Организатор/лента**, **URL страницы-списка**, **Тип**, **Основной способ**, **Запасные способы**, **Инструкции/примечания** (ссылки на файлы правил в репозитории).

---

## Общие правила обхода (из проекта)

- **Любой `timepad.ru` / поддомены Timepad (списки/афиши, карточки при разборе): ОСНОВНОЙ способ — запуск Edge через CDP/скрипты проекта.** Не использовать `webfetch`/прямые HTTP как первый шаг.  
  Инструкции: `AGENTS.md` («Способ получения страниц Timepad…»), `.opencode/skills/update-data/SKILL.md`. Инструменты: `tools/cdp_read.py`, `tools/timepad_parse.py`; кэши `data/raw/cdp/`. Запасные: сохранённые HTML в `data/raw/cdp/`, ручной просмотр в Edge и сохранение. При недоступности: `.opencode/skills/event-description/reference/availability_log.md` (повторы 1 мин → 5 мин).
- **`elementy.ru/events`:** сбор `scrape.py`, разбор карточек `tools/elementy_detail.py`. Инструкции: `AGENTS.md`, `ПАМЯТКА.md`, `update-data` skill. При сбое/пустой афише не затирать `data/events.json`, писать в `availability_log.md`.
- **JS-тяжёлые сайты:** `webfetch` часто только оболочка; основной способ — CDP/ручной просмотр в Edge, кэши `data/raw/`. Инструкции: `AGENTS.md`, `update-data` skill, `availability_log.md` при сбоях.
- **Обычные HTML:** `webfetch` (text/markdown) первой попыткой; запасные — повторы по правилу недоступности (`availability_log.md`, 1→5 мин), кэши/CDP/ручной просмотр. Инструкции: `AGENTS.md`, `update-data` skill.

---

## Элементы (общая афиша)

| Организатор/лента | URL страницы-списка | Тип | Основной способ | Запасные способы | Инструкции/примечания |
|---|---|---|---|---|---|
| Элементы (афиша) | https://elementy.ru/events | HTML (список) | `scrape.py`, `tools/elementy_detail.py` (HTTP) | Повторы по недоступности; `availability_log.md`; не править `data/events.json` при сбое | `AGENTS.md`, `ПАМЯТКА.md`, `.opencode/skills/update-data/SKILL.md`, `.opencode/skills/event-description/reference/availability_log.md` |

---

## Архэ

**Дубли URL событий:** предпочтительно `https://arhe.msk.ru/?p=<ID>` > `https://arhe.msk.ru/?post_type=tribe_events&p=<ID>` (ID может отличаться на 1 — сверять по содержимому) > текстовый `?tribe_events=…` (только если других нет). Склеивать дубли по дате/названию/автору. **Важно:** не ставим курсы целиком, ставим отдельные лекции курсов.

| Организатор/лента | URL страницы-списка | Тип | Основной способ | Запасные способы | Инструкции/примечания |
|---|---|---|---|---|---|
| Архэ (страница) | https://arhe.msk.ru/?page_id=369 | HTML | webfetch / HTTP | Недоступность → `availability_log.md`, повторы 1→5 мин; кэши/CDP | `AGENTS.md`, `.opencode/skills/update-data/SKILL.md` (раздел Архэ) |
| Архэ (лента Tribe Events) | https://arhe.msk.ru/?post_type=tribe_events | HTML | webfetch / HTTP | См. выше | Основная лента сайта Архэ. |
| Архэ (страница) | https://arhe.msk.ru/?page_id=332 | HTML | webfetch / HTTP | См. выше | Страница-список/афиша. |
| Архэ (страница) | https://arhe.msk.ru/?page_id=3466 | HTML | webfetch / HTTP | См. выше | Страница-список/афиша. |
| Архэ (страница) | https://arhe.msk.ru/?page_id=81748 | HTML | webfetch / HTTP | См. выше | Страница-список/афиша. |
| Архэ (страница) | https://arhe.msk.ru/?page_id=32233 | HTML | webfetch / HTTP | См. выше | Страница-список/афиша. |
| Архэ (страница) | https://arhe.msk.ru/?page_id=77150 | HTML | webfetch / HTTP | См. выше | Страница-список/афиша. |
| Архэ (страница) | https://arhe.msk.ru/?page_id=14417 | HTML | webfetch / HTTP | См. выше | Добавлено по запросу. |
| Архэ, Timepad (Москва/общая) | https://arhe-events.timepad.ru/events/ | Timepad (список) | **Edge + CDP** (`tools/cdp_read.py`, `tools/timepad_parse.py`) | Кэши `data/raw/cdp/`, ручной просмотр в Edge | **Timepad — только Edge/CDP.** `AGENTS.md`, `update-data` skill, `availability_log.md` при сбоях. |
| Архэ, Timepad (СПб) | https://tsentr-arhe-v-sankt-peter.timepad.ru/events/ | Timepad (список) | **Edge + CDP** (`tools/cdp_read.py`, `tools/timepad_parse.py`) | Кэши `data/raw/cdp/`, ручной просмотр в Edge | **Timepad — только Edge/CDP.** `AGENTS.md`, `update-data` skill, `availability_log.md`. |

---

## ВДНХ

| Организатор/лента | URL страницы-списка | Тип | Основной способ | Запасные способы | Инструкции/примечания |
|---|---|---|---|---|---|
| ВДНХ (сайт) | https://vdnh.ru/events/ | HTML/JS (SPA) | **Edge/CDP или ручной обход в браузере** (JS обязателен) | Кэши `data/raw/*`; при автоматизации — CDP. `webfetch` даёт только оболочку. | **Важно:** фильтр «Лекции»; подгрузка порциями кнопкой «Показать ещё» (JS). Инструкции: `AGENTS.md`, `.opencode/skills/update-data/SKILL.md`, `availability_log.md` при сбоях. |
| Лекторий ВДНХ (Timepad) | https://lektorij-vdnh.timepad.ru/events/ | Timepad (список) | **Edge + CDP** (`tools/cdp_read.py`, `tools/timepad_parse.py`) | Кэши `data/raw/cdp/`, ручной просмотр в Edge | **Timepad — только Edge/CDP.** `AGENTS.md`, `update-data` skill. |
| Космос и авиация ВДНХ (Timepad) | https://cosmos-vdnh.timepad.ru/events/ | Timepad (список) | **Edge + CDP** (`tools/cdp_read.py`, `tools/timepad_parse.py`) | Кэши `data/raw/cdp/`, ручной просмотр в Edge | **Timepad — только Edge/CDP.** `AGENTS.md`, `update-data` skill. |
| Музей «Слово» (ВДНХ, Timepad) | https://slovo-vdnh.timepad.ru/events/ | Timepad (список) | **Edge + CDP** (`tools/cdp_read.py`, `tools/timepad_parse.py`) | Кэши `data/raw/cdp/`, ручной просмотр в Edge | **Timepad — только Edge/CDP.** `AGENTS.md`, `update-data` skill. |
| Павильон «АТОМ» (ВДНХ, Timepad) | https://atom-lab.timepad.ru/events/ | Timepad (список) | **Edge + CDP** (`tools/cdp_read.py`, `tools/timepad_parse.py`) | Кэши `data/raw/cdp/`, ручной просмотр в Edge | **Timepad — только Edge/CDP.** Добавлено по указанию пользователя. `AGENTS.md`, `update-data` skill. |
| Центр биотехнологий «БИОТЕХ» (ВДНХ, Timepad) | https://muzey-biotekh.timepad.ru/events/ | Timepad (список) | **Edge + CDP** (`tools/cdp_read.py`, `tools/timepad_parse.py`) | Кэши `data/raw/cdp/`, ручной просмотр в Edge | **Timepad — только Edge/CDP.** Добавлено по указанию пользователя. `AGENTS.md`, `update-data` skill. |

---

## КЦ ЗИЛ

| Организатор/лента | URL страницы-списка | Тип | Основной способ | Запасные способы | Инструкции/примечания |
|---|---|---|---|---|---|
| КЦ ЗИЛ (афиша, сайт) | https://zilcc.ru/afisha | HTML | webfetch (text/markdown) | Недоступность → `availability_log.md` (1→5 мин), кэши/CDP/ручной просмотр | Желательно выбирать типы событий «Лекция», «Научное шоу». `AGENTS.md`, `.opencode/skills/update-data/SKILL.md`, `availability_log.md`. |
| КЦ ЗИЛ (Timepad) | https://zilcc.timepad.ru/events/ | Timepad (список) | **Edge + CDP** (`tools/cdp_read.py`, `tools/timepad_parse.py`) | Кэши `data/raw/cdp/`, ручной просмотр в Edge | **Timepad — только Edge/CDP.** `AGENTS.md`, `update-data` skill, `availability_log.md`. |

---

## Medio Modo

| Организатор/лента | URL страницы-списка | Тип | Основной способ | Запасные способы | Инструкции/примечания |
|---|---|---|---|---|---|
| Medio Modo (сайт) | https://mediomodo.ru/catalog | HTML | webfetch первой попыткой | Недоступность → `availability_log.md` (1→5 мин), кэши/CDP/ручной просмотр | Каталог/список событий. Карточки — страницы вида `mediomodo.ru/<slug>`. Инструкции: `AGENTS.md`, `.opencode/skills/update-data/SKILL.md`, `availability_log.md`. |

---

## Прямая речь

| Организатор/лента | URL страницы-списка | Тип | Основной способ | Запасные способы | Инструкции/примечания |
|---|---|---|---|---|---|
| Сайт «Прямая речь» (pryamaya.ru) | https://www.pryamaya.ru/?page=1&dateFrom=&dateTo=&formats%5B%5D=85 | HTML | webfetch первой попыткой | Кэши/ручной просмотр; `availability_log.md` при сбоях | Фильтр по формату (лекции). Карточки событий на pryamaya.ru. Инструкции: `AGENTS.md`, `update-data` skill. |

---

## Проекты Станислава Дробышевского (Фонд науки)

| Организатор/лента | URL страницы-списка | Тип | Основной способ | Запасные способы | Инструкции/примечания |
|---|---|---|---|---|---|
| Фонд науки (Timepad) | https://fondnauk.timepad.ru/events/ | Timepad (список) | **Edge + CDP** (`tools/cdp_read.py`, `tools/timepad_parse.py`) | Кэши `data/raw/cdp/`, ручной просмотр в Edge | **Timepad — только Edge/CDP.** `AGENTS.md`, `update-data` skill, `availability_log.md`. |

---

## Лекторий «Живой город» (lectory2)

| Организатор/лента | URL страницы-списка | Тип | Основной способ | Запасные способы | Инструкции/примечания |
|---|---|---|---|---|---|
| Живой город (сайт) | https://lectory2.ru/ | HTML/JS | webfetch первой попыткой; при JS — CDP/ручной просмотр | Кэши `data/raw/*`, CDP в Edge; `availability_log.md` при сбоях | В данных встречались ссылки вида `lectory2.ru/#lecture_<id>`. Инструкции: `AGENTS.md`, `update-data` skill (правила по Живому городу в AGENTS). |

---

## Neurocampus

| Организатор/лента | URL страницы-списка | Тип | Основной способ | Запасные способы | Инструкции/примечания |
|---|---|---|---|---|---|
| Neurocampus (Timepad) | https://neurocampus.timepad.ru/events/ | Timepad (список) | **Edge + CDP** (`tools/cdp_read.py`, `tools/timepad_parse.py`) | Кэши `data/raw/cdp/`, ручной просмотр в Edge | **Timepad — только Edge/CDP.** `AGENTS.md`, `update-data` skill, `availability_log.md`. |
| Neurocampus (сайт) | https://neurocampus.su/events | HTML | webfetch первой попыткой | Недоступность → `availability_log.md` (1→5 мин), кэши/CDP/ручной просмотр | Карточки `neurocampus.su/tpost/...`. Инструкции: `AGENTS.md`, `update-data` skill. |

---

## Историчка

| Организатор/лента | URL страницы-списка | Тип | Основной способ | Запасные способы | Инструкции/примечания |
|---|---|---|---|---|---|
| Историчка (Timepad) | https://istorichka.timepad.ru/events/ | Timepad (список) | **Edge + CDP** (`tools/cdp_read.py`, `tools/timepad_parse.py`) | Кэши `data/raw/cdp/`, ручной просмотр в Edge | **Timepad — только Edge/CDP.** `AGENTS.md`, `update-data` skill, `availability_log.md`. Сайт Исторички — при необходимости уточнить/добавить. |

---

## РГПУ им. А.И. Герцена (Открытый кампус и проекты)

| Организатор/лента | URL страницы-списка | Тип | Основной способ | Запасные способы | Инструкции/примечания |
|---|---|---|---|---|---|
| Открытый кампус Герценовского университета (анонсы) | https://www.herzen.spb.ru/about/proyekty/otkrytyy-kampus/anonsy/ | HTML | webfetch первой попыткой | Недоступность → `availability_log.md` (1→5 мин), кэши/CDP/ручной просмотр | `AGENTS.md`, `update-data` skill. |
| Открытый кампус (Timepad) | https://terraherz-spb.timepad.ru/events/ | Timepad (список) | **Edge + CDP** (`tools/cdp_read.py`, `tools/timepad_parse.py`) | Кэши `data/raw/cdp/`, ручной просмотр в Edge | **Timepad — только Edge/CDP.** `AGENTS.md`, `update-data` skill, `availability_log.md`. |
| Проект «Современные достижения науки и техники» (Институт физики РГПУ) | https://sdnt-project.herzen.spb.ru/openlectures/ | HTML | webfetch первой попыткой | Недоступность → `availability_log.md`, кэши/CDP/ручной просмотр | `AGENTS.md`, `update-data` skill. |

---

## Некрасовка (ЦУНБ им. Н.А. Некрасова)

| Организатор/лента | URL страницы-списка | Тип | Основной способ | Запасные способы | Инструкции/примечания |
|---|---|---|---|---|---|
| Некрасовка (афиша) | https://nekrasovka.ru/afisha | HTML | webfetch первой попыткой | Недоступность → `availability_log.md` (1→5 мин), кэши/CDP/ручной просмотр | Карточки `nekrasovka.ru/afisha/...`. Инструкции: `AGENTS.md`, `update-data` skill. |

---

## Политехнический музей

| Организатор/лента | URL страницы-списка | Тип | Основной способ | Запасные способы | Инструкции/примечания |
|---|---|---|---|---|---|
| Политех — цикл «Вечерняя школа» | https://polymus.ru/education/cycle/vechernyaya-shkola-politekhnicheskogo-muzeya | HTML | webfetch первой попыткой | Кэши/ручной просмотр; `availability_log.md` при сбоях | Карточки `polymus.ru/events/detail/...`. `AGENTS.md`, `update-data` skill. |
| Политех — календарь/афиша | https://polymus.ru/pages/calendar | HTML | webfetch первой попыткой | Кэши/CDP/ручной просмотр; `availability_log.md` при сбоях | Общий календарь событий. `AGENTS.md`, `update-data` skill, `availability_log.md`. |

---

## Дарвиновский музей

| Организатор/лента | URL страницы-списка | Тип | Основной способ | Запасные способы | Инструкции/примечания |
|---|---|---|---|---|---|
| Дарвиновский музей (сайт, проекты/события) | https://www.darwinmuseum.ru/projects/event | HTML | webfetch первой попыткой | Недоступность → `availability_log.md` (1→5 мин), кэши/CDP/ручной просмотр | Указано пользователем как страница-источник; проверять актуальность раздела. `AGENTS.md`, `update-data` skill. |
| darwinmuseum.timepad.ru | https://darwinmuseum.timepad.ru/events/ | Timepad (список) | **Edge + CDP** (`tools/cdp_read.py`, `tools/timepad_parse.py`) | Кэши `data/raw/cdp/`, ручной просмотр в Edge | **Timepad — только Edge/CDP.** `AGENTS.md`, `update-data` skill, `availability_log.md`. |

---

## Московский зоопарк

| Организатор/лента | URL страницы-списка | Тип | Основной способ | Запасные способы | Инструкции/примечания |
|---|---|---|---|---|---|
| Московский зоопарк (образовательные лекции) | https://moscowzoo.ru/education/open-lecture | HTML | webfetch первой попыткой | Недоступность → `availability_log.md`, кэши/CDP/ручной просмотр | `AGENTS.md`, `update-data` skill. |
| moscowzoo.timepad.ru | https://moscowzoo.timepad.ru/events/ | Timepad (список) | **Edge + CDP** (`tools/cdp_read.py`, `tools/timepad_parse.py`) | Кэши `data/raw/cdp/`, ручной просмотр в Edge | **Timepad — только Edge/CDP.** `AGENTS.md`, `update-data` skill, `availability_log.md`. |

---

## СПбГУ

| Организатор/лента | URL страницы-списка | Тип | Основной способ | Запасные способы | Инструкции/примечания |
|---|---|---|---|---|---|
| СПбГУ (лектории новых технологий, сайт) | https://school.spbstu.ru/lektorii_novyh_tehnologiy/ | HTML | webfetch первой попыткой | Недоступность → `availability_log.md`, кэши/CDP/ручной просмотр | Указано как возможный источник; при необходимости проверять актуальность. `AGENTS.md`, `update-data` skill. |
| spbstuni.timepad.ru | https://spbstuni.timepad.ru/events/ | Timepad (список) | **Edge + CDP** (`tools/cdp_read.py`, `tools/timepad_parse.py`) | Кэши `data/raw/cdp/`, ручной просмотр в Edge | **Timepad — только Edge/CDP.** `AGENTS.md`, `update-data` skill, `availability_log.md`. |

---

## Институт философии РАН

| Организатор/лента | URL страницы-списка | Тип | Основной способ | Запасные способы | Инструкции/примечания |
|---|---|---|---|---|---|
| institut-filosofii--2026.timepad.ru | https://institut-filosofii--2026.timepad.ru/events/ | Timepad (список) | **Edge + CDP** (`tools/cdp_read.py`, `tools/timepad_parse.py`) | Кэши `data/raw/cdp/`, ручной просмотр в Edge | **Timepad — только Edge/CDP.** `AGENTS.md`, `update-data` skill, `availability_log.md`. |

---

## Московский планетарий (разделы)

| Организатор/лента | URL страницы-списка | Тип | Основной способ | Запасные способы | Инструкции/примечания |
|---|---|---|---|---|---|
| Трибуна учёного (курсы) | https://planetarium-moscow.ru/courses/tribuna-uchenogo | HTML | webfetch первой попыткой | Кэши/CDP; `availability_log.md` при сбоях | Пример ленты раздела; при необходимости проверять другие `/courses/...`. `AGENTS.md`, `update-data` skill. |

---

## Лекторий «Вольнослушатель»

| Организатор/лента | URL страницы-списка | Тип | Основной способ | Запасные способы | Инструкции/примечания |
|---|---|---|---|---|---|
| Вольнослушатель (Timepad) | https://volnoslushatel.timepad.ru/events/ | Timepad (список) | **Edge + CDP** (`tools/cdp_read.py`, `tools/timepad_parse.py`) | Кэши `data/raw/cdp/`, ручной просмотр в Edge | **Timepad — только Edge/CDP.** `AGENTS.md`, `.opencode/skills/update-data/SKILL.md`, `availability_log.md`. |

---

## Парк науки ННГУ «Лобачевский Lab»

| Организатор/лента | URL страницы-списка | Тип | Основной способ | Запасные способы | Инструкции/примечания |
|---|---|---|---|---|---|
| Лобачевский Lab (Timepad) | https://lobachevskylab.timepad.ru/events/ | Timepad (список) | **Edge + CDP** (`tools/cdp_read.py`, `tools/timepad_parse.py`) | Кэши `data/raw/cdp/`, ручной просмотр в Edge | **Timepad — только Edge/CDP.** `AGENTS.md`, `update-data` skill. |
| Парк науки ННГУ (сайт, мероприятия) | https://naukann.ru/meropriyatiya/ | HTML | webfetch первой попыткой | Недоступность → `availability_log.md`, кэши/CDP/ручной просмотр | `AGENTS.md`, `update-data` skill, `availability_log.md`. |

---

## Зануда

| Организатор/лента | URL страницы-списка | Тип | Основной способ | Запасные способы | Инструкции/примечания |
|---|---|---|---|---|---|
| Зануда (Timepad) | https://zanuda.timepad.ru/events/ | Timepad (список) | **Edge + CDP** (`tools/cdp_read.py`, `tools/timepad_parse.py`) | Кэши `data/raw/cdp/`, ручной просмотр в Edge | **Timepad — только Edge/CDP.** `AGENTS.md`, `update-data` skill, `availability_log.md`. |

---

## Astrocamp

| Организатор/лента | URL страницы-списка | Тип | Основной способ | Запасные способы | Инструкции/примечания |
|---|---|---|---|---|---|
| Astrocamp (Timepad) | https://astrocamp.timepad.ru/events/ | Timepad (список) | **Edge + CDP** (`tools/cdp_read.py`, `tools/timepad_parse.py`) | Кэши `data/raw/cdp/`, ручной просмотр в Edge | **Timepad — только Edge/CDP.** `AGENTS.md`, `update-data` skill, `availability_log.md`. |

---

## Свидетели научпопа

| Организатор/лента | URL страницы-списка | Тип | Основной способ | Запасные способы | Инструкции/примечания |
|---|---|---|---|---|---|
| Свидетели научпопа (Timepad) | https://nauchpop-moscow.timepad.ru/events/ | Timepad (список) | **Edge + CDP** (`tools/cdp_read.py`, `tools/timepad_parse.py`) | Кэши `data/raw/cdp/`, ручной просмотр в Edge | **Timepad — только Edge/CDP.** `AGENTS.md`, `update-data` skill, `availability_log.md`. |

---

## Технопарк Физтех-лицея им. Капицы

| Организатор/лента | URL страницы-списка | Тип | Основной способ | Запасные способы | Инструкции/примечания |
|---|---|---|---|---|---|
| Капица (сайт, лекции) | https://kapitsa.center/lecture_categories/lectures/ | HTML | webfetch первой попыткой | Недоступность → `availability_log.md`, кэши/CDP/ручной просмотр | `AGENTS.md`, `update-data` skill. |

---

## Курилка Гутенберга

| Организатор/лента | URL страницы-списка | Тип | Основной способ | Запасные способы | Инструкции/примечания |
|---|---|---|---|---|---|
| Курилка Гутенберга (Timepad, основной) | https://kurilka-gutenberga-events.timepad.ru/events/ | Timepad (список) | **Edge + CDP** (`tools/cdp_read.py`, `tools/timepad_parse.py`) | Кэши `data/raw/cdp/`, ручной просмотр в Edge | **Timepad — только Edge/CDP.** `AGENTS.md`, `update-data` skill, `availability_log.md`. |
| Курилка Гутенберга (Timepad, Тюмень/другой) | https://kurilkaintmn.timepad.ru/events/ | Timepad (список) | **Edge + CDP** (`tools/cdp_read.py`, `tools/timepad_parse.py`) | Кэши `data/raw/cdp/`, ручной просмотр в Edge | **Timepad — только Edge/CDP.** `AGENTS.md`, `update-data` skill, `availability_log.md`. |

---

## Ельцин Центр

| Организатор/лента | URL страницы-списка | Тип | Основной способ | Запасные способы | Инструкции/примечания |
|---|---|---|---|---|---|
| Ельцин Центр (Екатеринбург, лекции) | https://yeltsin.ru/affairs/?cid=2&t=lecture | HTML | webfetch первой попыткой | Недоступность → `availability_log.md`, кэши/CDP/ручной просмотр | `AGENTS.md`, `update-data` skill. |
| Ельцин Центр (Москва, лекции) | https://yeltsin.ru/affairs/?cid=1&t=lecture | HTML | webfetch первой попыткой | Недоступность → `availability_log.md`, кэши/CDP/ручной просмотр | Добавлено по запросу (филиал в Москве). `AGENTS.md`, `update-data` skill. |
| Ельцин Центр (Timepad) | https://yeltsin-center.timepad.ru/events/ | Timepad (список) | **Edge + CDP** (`tools/cdp_read.py`, `tools/timepad_parse.py`) | Кэши `data/raw/cdp/`, ручной просмотр в Edge | **Timepad — только Edge/CDP.** `AGENTS.md`, `update-data` skill, `availability_log.md`. |

---

## Музей криптографии

| Организатор/лента | URL страницы-списка | Тип | Основной способ | Запасные способы | Инструкции/примечания |
|---|---|---|---|---|---|
| Музей криптографии (события) | https://cryptography-museum.ru/events | HTML | webfetch первой попыткой | Недоступность → `availability_log.md`, кэши/CDP/ручной просмотр | `AGENTS.md`, `update-data` skill. |

---

## Академия Грамоты

| Организатор/лента | URL страницы-списка | Тип | Основной способ | Запасные способы | Инструкции/примечания |
|---|---|---|---|---|---|
| Академия Грамоты (Timepad) | https://academy-gramota.timepad.ru/events/ | Timepad (список) | **Edge + CDP** (`tools/cdp_read.py`, `tools/timepad_parse.py`) | Кэши `data/raw/cdp/`, ручной просмотр в Edge | **Timepad — только Edge/CDP.** `AGENTS.md`, `update-data` skill, `availability_log.md`. |

---

## Прочие Timepad-ленты (из репозитория)

Для всех `timepad.ru` — **Edge + CDP** (`tools/cdp_read.py`, `tools/timepad_parse.py`), см. общие правила.

| Организатор/лента | URL страницы-списка | Тип | Основной способ | Запасные способы | Инструкции/примечания |
|---|---|---|---|---|---|
| oxta8.timepad.ru | https://oxta8.timepad.ru/events/ | Timepad (список) | **Edge + CDP** (`tools/cdp_read.py`, `tools/timepad_parse.py`) | Кэши `data/raw/cdp/`, ручной просмотр в Edge | **Timepad — только Edge/CDP.** `AGENTS.md`, `update-data` skill, `availability_log.md`. |
| planetalib.timepad.ru | https://planetalib.timepad.ru/events/ | Timepad (список) | **Edge + CDP** (`tools/cdp_read.py`, `tools/timepad_parse.py`) | Кэши `data/raw/cdp/`, ручной просмотр в Edge | **Timepad — только Edge/CDP.** `AGENTS.md`, `update-data` skill, `availability_log.md`. |
| politvostok.timepad.ru | https://politvostok.timepad.ru/events/ | Timepad (список) | **Edge + CDP** (`tools/cdp_read.py`, `tools/timepad_parse.py`) | Кэши `data/raw/cdp/`, ручной просмотр в Edge | **Timepad — только Edge/CDP.** `AGENTS.md`, `update-data` skill, `availability_log.md`. |
| soobshchestvo-vsmysle.timepad.ru | https://soobshchestvo-vsmysle.timepad.ru/events/ | Timepad (список) | **Edge + CDP** (`tools/cdp_read.py`, `tools/timepad_parse.py`) | Кэши `data/raw/cdp/`, ручной просмотр в Edge | **Timepad — только Edge/CDP.** `AGENTS.md`, `update-data` skill, `availability_log.md`. |
| spitsbergen.timepad.ru | https://spitsbergen.timepad.ru/events/ | Timepad (список) | **Edge + CDP** (`tools/cdp_read.py`, `tools/timepad_parse.py`) | Кэши `data/raw/cdp/`, ручной просмотр в Edge | **Timepad — только Edge/CDP.** `AGENTS.md`, `update-data` skill, `availability_log.md`. |
| yadro-engineer.timepad.ru | https://yadro-engineer.timepad.ru/events/ | Timepad (список) | **Edge + CDP** (`tools/cdp_read.py`, `tools/timepad_parse.py`) | Кэши `data/raw/cdp/`, ручной просмотр в Edge | **Timepad — только Edge/CDP.** `AGENTS.md`, `update-data` skill, `availability_log.md`. |
| your-sector-of-space.timepad.ru | https://your-sector-of-space.timepad.ru/events/ | Timepad (список) | **Edge + CDP** (`tools/cdp_read.py`, `tools/timepad_parse.py`) | Кэши `data/raw/cdp/`, ручной просмотр в Edge | **Timepad — только Edge/CDP.** `AGENTS.md`, `update-data` skill, `availability_log.md`. |
| zaobiblio.timepad.ru | https://zaobiblio.timepad.ru/events/ | Timepad (список) | **Edge + CDP** (`tools/cdp_read.py`, `tools/timepad_parse.py`) | Кэши `data/raw/cdp/`, ручной просмотр в Edge | **Timepad — только Edge/CDP.** `AGENTS.md`, `update-data` skill, `availability_log.md`. |

---

## Как добавлять новые источники

1. Добавлять **только страницы-списки/афиши** (или явно помеченные ленты), не отдельные карточки событий, если иное не оговорено. **Группировать по организатору** (даже если источник один).
2. Для любых URL с доменом `timepad.ru` / поддоменами Timepad: основной способ **Edge + CDP** (`tools/cdp_read.py`, `tools/timepad_parse.py`), в примечаниях указывать ссылки: `AGENTS.md`, `.opencode/skills/update-data/SKILL.md`, `.opencode/skills/event-description/reference/availability_log.md`.
3. Для нестандартного обхода (JS, капча, API) — кратко описать и указать инструменты/кэши (`data/raw/`, `data/raw/cdp/`).
4. При недоступности: действовать по `AGENTS.md`, писать в `.opencode/skills/event-description/reference/availability_log.md`, повторы 1 мин → 5 мин, при необходимости дополнять `notes` прототипа.