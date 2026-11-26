# Полный сбор обновлений — 26.11.2026 (кроме ВДНХ)

Охват: все источники из `data/sources_list.md`, **за исключением раздела «ВДНХ»** (6 ссылок: сайт и пять Timepad-лент). Прототипы в ходу не создавались — только сбор и классификация кандидатов.

## 1. «Элементы» и сайт

- `python -X utf8 scrape.py`: найдено **98** событий, добавлено **2**, изменено **4**.
- `python -X utf8 build.py`: «Сайт собран. Pages: 199».

## 2. Операционный обход лекториев (`tools/sweep_lectories.py`, ВДНХ временно отключён)

| Лекторий | Всего | Итог |
|---|---:|---|
| «Прямая речь» | 38 | 6 уже с прототипами, 10 отвергнуты, 21 ждут решения, **1 новое** — `PR-8974` «Елисеевы: короли-гурманы», 20.12.2026 19:00, Никита Брусиловский, https://www.pryamaya.ru/nikita_brusilovskij_eliseevy_koroli-gurmany_20_12_2026 |
| Центр «Архэ» | 29 | 20 уже с прототипами, 52 прошедших скрыто, 7 отвергнуты, 1 добавлен, 1 дубль; **новых нет** |

Ошибок у обхода нет (`errors: []`). Конфиг `data/sweep/lectories.json` после запуска восстановлен побайтово, ВДНХ снова включён.

`PR-8974` был отнесён к **«Сомнительным»** (историко-краеведческая лекция, нужны критерии/подтверждение), но **решением пользователя 26.11.2026 лекция не нужна**: статус в `data/monitor/pending.json` — «Не нужно», в реестре `data/sweep/known_events.json` — `rejected`. Прототип не создавался и создаваться не будет.

## 3. Timepad — 29 лент, только Edge/CDP

Прочитаны все ленты из `data/sources_list.md`, кроме пяти ВДНХ: **469 карточек, 29 лент, капчи нет**. Сохранённые DOM — в `data/raw/cdp/sweep_*.html` (папка в `.gitignore`).

Ленты с малым числом событий — нормальное состояние афиши, не сбой:
- `academy-gramota` — 4; `politvostok` — 10; `nauchpop-moscow` — 3; `institut-filosofii--2026` — 9; `institut-okeanologii-im-p` — 9.
- `kurilkaintmn` — **0**: страница честно пишет «У этой организации пока что нет событий».

Ложные срабатывания детектора капчи: у `yadro-engineer` и `volnoslushatel` слово «робот» встречается в текстах анонсов (`showcaptcha=0`, `captcha=0`). Первый пакетный прогон этих лент вообще не доходил до сайтов из-за ошибки во временном скрипте (неверная подстрока поиска вкладки); после исправления все 29 открылись.

## 4. Обычные сайты и API (HTTP/webfetch)

| Источник | URL | Статус | Карточек |
|---|---|---|---:|
| ВСмысле | `https://vsmysle.spb.ru/afisha/?w=all` | ok | 114 |
| Medio Modo | `https://mediomodo.ru/catalog` | см. п. 5 | — |
| ЗИЛ, сайт | `https://zilcc.ru/afisha` | см. п. 5 | — |
| ЗИЛ, API | `https://eventapi.zilcc.ru/events/cards/v2?page_size=100` | ok | 73 |
| Некрасовка | `https://nekrasovka.ru/afisha/` | ok | 85 |
| СДНТ, Герцен | `https://sdnt-project.herzen.spb.ru/openlectures/` | доступен, будущих нет | 0 |
| Открытый кампус, Герцен | `https://www.herzen.spb.ru/about/proyekty/otkrytyy-kampus/anonsy/` | ok | 5 |
| Политех, календарь | `https://polymus.ru/pages/calendar` | ok | 27 |
| Капица | `https://kapitsa.center/lecture_categories/lectures/` | ok | 2 |
| Ельцин Центр, Москва | `https://yeltsin.ru/affairs/?cid=1&t=lecture` | ok | 10 |
| Живой город | `https://lectory2.ru/` + `POST /api/get/list/` | ok | 25 на странице 1 |
| Нейрокампус | `https://neurocampus.su/events` | доступен, будущих нет | 0 |
| Дарвиновский музей | `https://www.darwinmuseum.ru/projects/event` | ok | ~10 |
| Московский зоопарк | `https://moscowzoo.ru/education/open-lecture` | см. п. 5 | — |
| СПбПУ | `https://school.spbstu.ru/lektorii_novyh_tehnologiy/` | ok | 2 |
| Планетарий, Трибуна учёного | `https://planetarium-moscow.ru/courses/tribuna-uchenogo` | ok | 3 (1 будущая) |
| Ельцин Центр, Екатеринбург | `https://yeltsin.ru/affairs/?cid=2&t=lecture` | ok | 7 |
| Музей криптографии | `https://cryptography-museum.ru/events` | ok | ~16 |
| Лекторий юного географа | `https://www.geogr.msu.ru/admission/lektory/` | ok | 1 будущая |
| Экспериментаниум | `https://experimentanium.ru/uchenye-detyam.html` | доступен, карточек/дат нет | 0 |
| naukann.ru | `https://naukann.ru/meropriyatiya/` | доступен, событий нет | 0 |

## 5. JS-страницы, дочитанные через Edge/CDP

| URL | Результат |
|---|---|
| `https://moscowzoo.ru/education/open-lecture` | ok: расписание лекций получено (ближайшая — 26.11.2026, «Парк животных Оверни…», 19:30). Первоначальная ошибка `webfetch` и защищённый API оказались непреодолимыми только для прямых HTTP-запросов |
| `https://mediomodo.ru/catalog` | ok: афиша ноябрь 2026 — март 2027 прочитана целиком |
| `https://polymus.ru/events/` | ok: карточки с датами и площадками прочитаны |
| `https://polymus.ru/pages/calendar` | ok: 27 карточек |
| `https://zilcc.ru/afisha` | ok: карточки видны; полный список дублируется API (73) |

Для Политеха слово «робот» в описаниях снова дало ложный флаг капчи — `showcaptcha=0`, `captcha=0`.

## 6. Итог по недоступным источникам

**Источников, где не удалось собрать данные, нет.** Все адреса из `data/sources_list.md` (кроме исключённого по запросу ВДНХ) ответили; JS-страницы дочитаны через Edge/CDP, API — прямым запросом.

Отдельно: источники, которые доступны, но **не содержат будущих событий** — `kurilkaintmn.timepad.ru`, `neurocampus.su`, `sdnt-project.herzen.spb.ru`, `experimentanium.ru`, `naukann.ru`. Это не ошибки доступа, в лог недоступности они не записаны.

Новых записей в `.opencode/skills/event-description/reference/availability_log.md` в этот заход нет: реальных сбоев доступа не было.

## 7. Что осталось на решение пользователя

- `PR-8974` в `data/monitor/pending.json` — «Не нужно» по решению пользователя 26.11.2026; прототип не создавался.
- Открытых решений по обходу без ВДНХ нет: единственное новое событие (`PR-8974`) отвергнуто.
- Ранее отложенные ВДНХ-решения (Фрейд, Юнг) в обход не входили.
