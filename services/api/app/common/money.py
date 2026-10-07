"""Currency helpers. Amounts are always `Decimal`; never floats (docs/ARCHITECTURE.md §9)."""

# Currencies offered as a home/trip currency. Must be ISO 4217 codes the FX provider supports;
# extend deliberately (the web app renders this list).
SUPPORTED_CURRENCIES: tuple[str, ...] = (
    "USD", "EUR", "GBP", "JPY", "CAD", "AUD", "NZD", "CHF", "CNY", "HKD",
    "SGD", "KRW", "INR", "NPR", "THB", "MYR", "IDR", "PHP", "VND", "TWD",
    "AED", "SAR", "TRY", "ZAR", "BRL", "MXN", "ARS", "CLP", "SEK", "NOK",
    "DKK", "PLN", "CZK", "HUF", "ISK", "ILS", "EGP", "MAD",
)  # fmt: skip
SUPPORTED_CURRENCY_SET = frozenset(SUPPORTED_CURRENCIES)
