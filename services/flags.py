"""Currency code to country flag helpers."""

# ISO 4217 -> ISO 3166-1 alpha-2 (or EU) used for flag emoji.
# Covers the Bank of Russia daily list; unknown codes get no flag.
_CURRENCY_COUNTRY: dict[str, str] = {
    "AED": "AE",
    "AMD": "AM",
    "AUD": "AU",
    "AZN": "AZ",
    "BDT": "BD",
    "BGN": "BG",
    "BHD": "BH",
    "BOB": "BO",
    "BRL": "BR",
    "BYN": "BY",
    "CAD": "CA",
    "CHF": "CH",
    "CNY": "CN",
    "CUP": "CU",
    "CZK": "CZ",
    "DKK": "DK",
    "DZD": "DZ",
    "EGP": "EG",
    "ETB": "ET",
    "EUR": "EU",
    "GBP": "GB",
    "GEL": "GE",
    "HKD": "HK",
    "HUF": "HU",
    "IDR": "ID",
    "INR": "IN",
    "IRR": "IR",
    "JPY": "JP",
    "KGS": "KG",
    "KRW": "KR",
    "KZT": "KZ",
    "MDL": "MD",
    "MMK": "MM",
    "MNT": "MN",
    "NGN": "NG",
    "NOK": "NO",
    "NZD": "NZ",
    "OMR": "OM",
    "PLN": "PL",
    "QAR": "QA",
    "RON": "RO",
    "RSD": "RS",
    "RUB": "RU",
    "SAR": "SA",
    "SEK": "SE",
    "SGD": "SG",
    "THB": "TH",
    "TJS": "TJ",
    "TMT": "TM",
    "TRY": "TR",
    "UAH": "UA",
    "USD": "US",
    "UZS": "UZ",
    "VND": "VN",
    "XDR": "",  # IMF SDR - no country flag
    "ZAR": "ZA",
}


def country_flag(country_code: str) -> str:
    """Build a flag emoji from a 2-letter country/region code."""
    code = country_code.strip().upper()
    if len(code) != 2 or not code.isalpha():
        return ""
    return "".join(chr(0x1F1E6 + ord(c) - ord("A")) for c in code)


def currency_flag(currency_code: str) -> str:
    """Return a flag emoji for an ISO currency code, or empty string."""
    country = _CURRENCY_COUNTRY.get(currency_code.upper(), "")
    if not country:
        return ""
    return country_flag(country)


def currency_label(code: str, name: str) -> str:
    """Label like '🇺🇸 USD - Доллар США' (flag omitted when unknown)."""
    flag = currency_flag(code)
    prefix = f"{flag} " if flag else ""
    return f"{prefix}{code} - {name}"
