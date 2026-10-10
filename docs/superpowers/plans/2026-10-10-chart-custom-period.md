# Свой период графика — план

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** К `/chart` добавляется «Другой» (недели 1–8, месяцы 1–12, годы 1–5) с схлопыванием одинаковых окон в одно название и галочкой на быстром ряду.

**Architecture:** Окно — число недель. `services/chart/period.py` считает границы, название, допустимые длины и метку метрики. Клавиатуры кодируют текущую длину в callback. Сборка принимает недели. Ошибки сборки идут в `chart_errors_total`, удачные картинки — в `chart_builds_total{period}`.

**Tech Stack:** Python 3.13, aiogram 3, prometheus-client, pytest.

## Global Constraints

- Конец окна — сегодня по Москве, границы включительно. Неделя = 7 дней, месяц = 4 недели (28), полгода = 24 недели (168), год = 48 недель (336).
- Название: годы, иначе ровно 24 недели = «Полгода», иначе месяцы, иначе недели. Число только если единиц больше одной.
- Галочка на «Неделя» / «Месяц» / «Полгода», когда название совпало. На «Другой» галочки нет, кнопка остаётся нажимаемой. «Назад» подписан «← Назад».
- «Назад» и смена единицы картинку не трогают. Недопустимая длина не меняет график.
- `chart_errors_total{reason}`: `invalid_span`, `cbr`, `no_data`, `render`.
- `chart_builds_total{period}` только для собранной картинки: `week`, `month`, `half_year`, `year`, `custom`.
- Старые `chart:period:week|month|half_year` = 1, 4, 24 недели.

---

### Task 1: Окно и название

**Files:** Modify `services/chart/period.py`. Test: `tests/unit/test_chart_period.py`.

- [ ] Тесты на окна 7/28/168/336, таблицу названий, склонение, `weeks_for_pick`, `quick_button`, `metric_period`, legacy.
- [ ] Реализация на числе недель. `ChartPeriod` и `PERIOD_DAYS` уходят.

### Task 2: Клавиатуры

**Files:** Modify `bot/keyboards/inline.py`. Test: `tests/unit/test_chart_keyboard.py`.

- [ ] `period_keyboard(weeks)`, `unit_keyboard(weeks)`, `number_keyboard(unit, weeks)` с callback из спецификации.

### Task 3: Метрики и сборка

**Files:** Modify `bot/metrics.py`, `services/chart/build.py`, `services/chart/__init__.py`, `tests/unit/test_metrics.py`. Test: `tests/unit/test_chart_build.py`.

- [ ] `chart_errors_total`. `chart_builds_total` без `result`.
- [ ] `build_chart(currencies, weeks)` пишет метки `cbr` / `no_data` / `render` / период успеха.

### Task 4: Обработчик

**Files:** Modify `bot/handlers/chart.py`.

- [ ] Callback `chart:span`, `chart:other`, `chart:unit`, `chart:pick`, `chart:menu` и старый `chart:period`.
- [ ] Недопустимая длина увеличивает `invalid_span`. Сбой только клавиатуры не шлёт новое фото и не пишет `chart_errors_total`.
