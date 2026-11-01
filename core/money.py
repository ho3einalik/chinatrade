"""
Precision Monetary and Currency Arithmetic Module.
Uses Python Decimal for exact financial accounting, preventing IEEE 754 floating-point
rounding inaccuracies. Explicitly distinguishes between Iranian Rial (IRR) and Toman (IRT).
"""

from decimal import Decimal, ROUND_HALF_UP, InvalidOperation
from enum import Enum
from typing import Union, Dict, Any, Optional

class Currency(str, Enum):
    IRT = "IRT"  # Iranian Toman (تومان) - 1 IRT = 10 IRR
    IRR = "IRR"  # Iranian Rial (ریال)
    CNY = "CNY"  # Chinese Yuan Renminbi (یوان چین - ¥)
    USD = "USD"  # US Dollar ($)
    AED = "AED"  # UAE Dirham (درهم امارات)
    EUR = "EUR"  # Euro (€)

def to_decimal(val: Union[Decimal, int, float, str, None], default: str = "0.00") -> Decimal:
    """Safely converts input to Decimal with high precision."""
    if val is None:
        return Decimal(default)
    if isinstance(val, Decimal):
        return val
    try:
        # Stringify to avoid float precision binary leakage (e.g. 0.1 -> 0.1000000000000000055511151231257827021181583404541015625)
        return Decimal(str(val).strip().replace(",", ""))
    except (InvalidOperation, ValueError):
        return Decimal(default)

def quantize_money(amount: Decimal, decimals: int = 2) -> Decimal:
    """Rounds a Decimal value to the specified number of decimal places using ROUND_HALF_UP."""
    fmt = "1." + ("0" * decimals) if decimals > 0 else "1"
    return amount.quantize(Decimal(fmt), rounding=ROUND_HALF_UP)

class Money:
    """Immutable monetary representation binding an exact Decimal amount to a Currency."""
    __slots__ = ("_amount", "_currency")

    def __init__(self, amount: Union[Decimal, int, float, str], currency: Union[Currency, str] = Currency.IRT):
        self._amount = quantize_money(to_decimal(amount), decimals=2 if str(currency) not in ("IRR", "IRT") else 0)
        self._currency = Currency(currency) if isinstance(currency, str) else currency

    @property
    def amount(self) -> Decimal:
        return self._amount

    @property
    def currency(self) -> Currency:
        return self._currency

    def to_toman(self, exchange_rates: Dict[Currency, Decimal]) -> "Money":
        """Converts any currency into Iranian Toman (IRT) using provided exchange rates."""
        if self._currency == Currency.IRT:
            return self
        if self._currency == Currency.IRR:
            # 10 Rials = 1 Toman
            return Money(self._amount / Decimal("10"), Currency.IRT)

        rate = exchange_rates.get(self._currency)
        if not rate or rate <= 0:
            raise ValueError(f"Exchange rate for {self._currency.value} to IRT is missing or non-positive.")

        toman_val = self._amount * to_decimal(rate)
        return Money(quantize_money(toman_val, decimals=0), Currency.IRT)

    def to_rial(self, exchange_rates: Optional[Dict[Currency, Decimal]] = None) -> "Money":
        """Converts to Iranian Rial (IRR)."""
        if self._currency == Currency.IRR:
            return self
        if self._currency == Currency.IRT:
            return Money(self._amount * Decimal("10"), Currency.IRR)
        toman = self.to_toman(exchange_rates or {})
        return Money(toman.amount * Decimal("10"), Currency.IRR)

    def __repr__(self) -> str:
        return f"Money({self._amount}, {self._currency.value})"

    def __str__(self) -> str:
        if self._currency in (Currency.IRT, Currency.IRR):
            return f"{self._amount:,.0f} {self._currency.value}"
        return f"{self._amount:,.2f} {self._currency.value}"

    def __eq__(self, other: Any) -> bool:
        if not isinstance(other, Money):
            return False
        return self._amount == other._amount and self._currency == other._currency

    def __lt__(self, other: "Money") -> bool:
        if self._currency != other._currency:
            raise TypeError(f"Cannot compare {self._currency} directly with {other._currency}; convert first.")
        return self._amount < other._amount

    def __le__(self, other: "Money") -> bool:
        return self < other or self == other

    def __gt__(self, other: "Money") -> bool:
        return not (self <= other)

    def __ge__(self, other: "Money") -> bool:
        return not (self < other)

    def __add__(self, other: "Money") -> "Money":
        if self._currency != other._currency:
            raise TypeError(f"Cannot add {self._currency} to {other._currency}; convert currencies first.")
        return Money(self._amount + other._amount, self._currency)

    def __sub__(self, other: "Money") -> "Money":
        if self._currency != other._currency:
            raise TypeError(f"Cannot subtract {other._currency} from {self._currency}; convert currencies first.")
        return Money(self._amount - other._amount, self._currency)

    def __mul__(self, scalar: Union[Decimal, int, float, str]) -> "Money":
        dec_scalar = to_decimal(scalar)
        return Money(self._amount * dec_scalar, self._currency)

    def __truediv__(self, scalar: Union[Decimal, int, float, str]) -> "Money":
        dec_scalar = to_decimal(scalar)
        if dec_scalar == 0:
            raise ZeroDivisionError("Cannot divide Money by zero.")
        return Money(self._amount / dec_scalar, self._currency)


def calculate_robust_statistics(prices: list[Decimal]) -> Dict[str, Optional[Decimal]]:
    """
    Computes robust descriptive price metrics (Median, Trimmed Mean, IQR, Min, Max)
    resilient against fraudulent low bids, artificial high anchors, and duplicate scrapers.
    """
    if not prices:
        return {
            "count": 0,
            "min": None,
            "max": None,
            "median": None,
            "trimmed_mean": None,
            "iqr": None
        }

    sorted_p = sorted([to_decimal(p) for p in prices])
    n = len(sorted_p)

    # Median
    if n % 2 == 1:
        median = sorted_p[n // 2]
    else:
        median = (sorted_p[n // 2 - 1] + sorted_p[n // 2]) / Decimal("2")

    # Quartiles
    q1 = sorted_p[n // 4]
    q3 = sorted_p[(3 * n) // 4]
    iqr = q3 - q1

    # Filter extreme outliers using 1.5 * IQR bounds if enough samples exist
    if n >= 5 and iqr > 0:
        lower_bound = max(Decimal("0"), q1 - (Decimal("1.5") * iqr))
        upper_bound = q3 + (Decimal("1.5") * iqr)
        filtered = [p for p in sorted_p if lower_bound <= p <= upper_bound]
        if not filtered:
            filtered = sorted_p
    else:
        filtered = sorted_p

    # Trimmed Mean (10% trim each end if n >= 6, else simple arithmetic mean of filtered)
    if len(filtered) >= 6:
        trim_count = max(1, len(filtered) // 10)
        trimmed_subset = filtered[trim_count:-trim_count]
        trimmed_mean = sum(trimmed_subset) / Decimal(str(len(trimmed_subset)))
    else:
        trimmed_mean = sum(filtered) / Decimal(str(len(filtered)))

    return {
        "count": n,
        "min": quantize_money(sorted_p[0], 0),
        "max": quantize_money(sorted_p[-1], 0),
        "median": quantize_money(median, 0),
        "trimmed_mean": quantize_money(trimmed_mean, 0),
        "iqr": quantize_money(iqr, 0)
    }
