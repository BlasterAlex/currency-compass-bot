from bot.keyboards.inline import number_keyboard, period_keyboard, unit_keyboard


def _flat(markup) -> list[tuple[str, str]]:
    return [(button.text, button.callback_data) for row in markup.inline_keyboard for button in row]


def test_period_keyboard_marks_quick_button():
    assert _flat(period_keyboard(1)) == [
        ("✓ Неделя", "noop"),
        ("Месяц", "chart:span:4"),
        ("Полгода", "chart:span:24"),
        ("Другой", "chart:other:1"),
    ]
    assert _flat(period_keyboard(4))[1] == ("✓ Месяц", "noop")
    assert _flat(period_keyboard(24))[2] == ("✓ Полгода", "noop")


def test_period_keyboard_custom_stays_pressable():
    buttons = _flat(period_keyboard(2))
    assert buttons[0] == ("Неделя", "chart:span:1")
    assert buttons[3] == ("Другой", "chart:other:2")
    assert _flat(period_keyboard(48))[3] == ("Другой", "chart:other:48")


def test_unit_keyboard_has_no_checks():
    assert _flat(unit_keyboard(4)) == [
        ("Недели", "chart:unit:week:4"),
        ("Месяцы", "chart:unit:month:4"),
        ("Годы", "chart:unit:year:4"),
        ("← Назад", "chart:menu:4"),
    ]


def test_number_keyboard_marks_matching_count():
    weeks = _flat(number_keyboard("week", 4))
    assert ("✓ 4", "chart:menu:4") in weeks
    assert ("2", "chart:pick:week:2") in weeks
    assert weeks[-1] == ("← Назад", "chart:other:4")

    months = _flat(number_keyboard("month", 4))
    assert ("✓ 1", "chart:menu:4") in months
    assert ("3", "chart:pick:month:3") in months
    assert all(not text.startswith("✓") or text == "✓ 1" for text, _ in months)

    years = _flat(number_keyboard("year", 2))
    assert all(not text.startswith("✓") for text, _ in years[:-1])
    assert ("1", "chart:pick:year:1") in years
    assert len([text for text, _ in years if text != "← Назад"]) == 5
