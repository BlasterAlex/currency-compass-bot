from services.flags import currency_flag, currency_label


def test_currency_flag_png_exists():
    from pathlib import Path

    root = Path(__file__).resolve().parents[2] / "assets" / "flags"
    assert (root / "us.png").is_file()
    assert (root / "uz.png").is_file()


def test_currency_flag_usd():
    assert currency_flag("USD") == "🇺🇸"


def test_currency_flag_eur():
    assert currency_flag("EUR") == "🇪🇺"


def test_currency_flag_uzs():
    assert currency_flag("UZS") == "🇺🇿"


def test_currency_flag_xdr_empty():
    assert currency_flag("XDR") == ""


def test_currency_label():
    assert currency_label("USD", "Доллар США") == "🇺🇸 USD - Доллар США"
