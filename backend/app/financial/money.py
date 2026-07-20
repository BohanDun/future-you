"""Money conversion and rounding helpers."""

from decimal import ROUND_HALF_UP, Decimal, InvalidOperation

type MoneyInput = Decimal | int | float | str
CENT = Decimal("0.01")


def as_decimal(value: MoneyInput, *, name: str = "amount") -> Decimal:
    """Convert user or model input without inheriting binary float error."""
    if isinstance(value, bool):
        raise TypeError(f"{name} must be a number")

    try:
        result = Decimal(str(value))
    except (InvalidOperation, ValueError) as exc:
        raise ValueError(f"{name} must be a valid number") from exc

    if not result.is_finite():
        raise ValueError(f"{name} must be finite")
    return result


def non_negative(value: MoneyInput, *, name: str = "amount") -> Decimal:
    result = as_decimal(value, name=name)
    if result < 0:
        raise ValueError(f"{name} must be non-negative")
    return result


def money(value: MoneyInput) -> Decimal:
    """Round a monetary value to cents using conventional half-up rounding."""
    return as_decimal(value).quantize(CENT, rounding=ROUND_HALF_UP)


def as_float(value: MoneyInput) -> float:
    """Return a two-decimal API-safe number after Decimal calculation."""
    return float(money(value))
