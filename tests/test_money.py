import pytest
from decimal import Decimal
from core.money import Money, Currency, to_decimal, quantize_money, calculate_robust_statistics

def test_decimal_safety_and_no_float_binary_leakage():
    # 0.1 + 0.2 in standard IEEE 754 float is 0.30000000000000004
    d1 = to_decimal(0.1)
    d2 = to_decimal(0.2)
    assert d1 + d2 == Decimal("0.3")

def test_money_addition_and_subtraction():
    m1 = Money("150000", Currency.IRT)
    m2 = Money("50000", Currency.IRT)
    res = m1 + m2
    assert res.amount == Decimal("200000")
    assert res.currency == Currency.IRT
    assert (m1 - m2).amount == Decimal("100000")

def test_money_mismatched_currency_error():
    m_irt = Money("1000", Currency.IRT)
    m_usd = Money("10", Currency.USD)
    with pytest.raises(TypeError):
        _ = m_irt + m_usd

def test_money_to_toman_conversion():
    rates = {
        Currency.CNY: Decimal("14200"),
        Currency.USD: Decimal("102000")
    }
    cny_money = Money("48.50", Currency.CNY)
    toman_money = cny_money.to_toman(rates)
    # 48.50 * 14200 = 688,700 IRT
    assert toman_money.amount == Decimal("688700")
    assert toman_money.currency == Currency.IRT

def test_money_rial_to_toman():
    rial_money = Money("10000000", Currency.IRR) # 10 Million Rials
    toman_money = rial_money.to_toman({})
    assert toman_money.amount == Decimal("1000000") # 1 Million Tomans

def test_calculate_robust_statistics():
    # Prices with two severe outliers: 100 (fake cheap scam) and 50,000,000 (erroneous price anchor)
    prices = [
        Decimal("100"), # Outlier
        Decimal("1200000"),
        Decimal("1250000"),
        Decimal("1300000"),
        Decimal("1350000"),
        Decimal("1400000"),
        Decimal("1450000"),
        Decimal("1500000"),
        Decimal("50000000") # Outlier
    ]
    stats = calculate_robust_statistics(prices)
    assert stats["count"] == 9
    assert stats["median"] == Decimal("1350000")
    # Trimmed mean should remove or bound the extreme outliers and give a realistic average ~1.3M
    assert Decimal("1250000") <= stats["trimmed_mean"] <= Decimal("1450000")
