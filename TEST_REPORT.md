# گزارش جامع نتایج و ممیزی آزمون‌های خودکار (TEST_REPORT.md)

این سند ثبت رسمی و مستند نتایج آزمون‌های واحد (Unit)، یکپارچگی (Integration)، امنیت (Security) و تست‌های زنده شبکه (Live Network) ماژول‌های پروژه **iTrade China** است.

---

## ۱. خلاصه نتایج آزمون‌ها
- **تعداد کل تست‌های ثبت‌شده:** ۳۴ تست
- **تعداد تست‌های موفق (Passed):** ۳۴ تست (۱۰۰٪)
- **تعداد تست‌های ردشده (Failed):** ۰
- **محیط اجرا:** Python 3.13.2 روی ویندوز (pytest 8.3.5)
- **پوشش آزمون‌ها:** منطق ریاضی Decimal، اینکوترمز (EXW/FOB/CIF)، عدم کفایت داده‌ها، موتور تطبیق فنی، امنیت SSRF، پایگاه داده SQLite، و تست‌های زنده شبکه.

---

## ۲. ماتریس تفصیلی فایل‌های آزمون

| فایل آزمون | نوع تست | تعداد تست | وضعیت | شرح موارد آزمون‌شده |
| :--- | :---: | :---: | :---: | :--- |
| `tests/test_money.py` | Unit | ۶ | **Pass** | دقت محاسبات اعشاری `Decimal`، تبدیل ارزها، استخراج چارک‌ها و حذف داده‌های پرت با IQR و محاسبه میانه پیراسته |
| `tests/test_matching.py` | Unit | ۵ | **Pass** | تطبیق ساعت هوشمند، مغایرت گرید پتروشیمی (S-65 vs S-70)، ابزار صنعتی ۲۱ ولت براشلس، رفتار در داده ناکافی |
| `tests/test_calculator.py` | Unit | ۶ | **Pass** | وزن حجمی IATA، سناریوهای ۳گانه، سرفصل‌های ۱۴گانه، مقایسه اینکوترمز (EXW > FOB > CIF) و رفتار عدم کفایت داده |
| `tests/test_connectors.py` | Unit / Mock | ۴ | **Pass** | عملکرد قطع مدار Circuit Breaker، لینک‌های عمیق سورس‌های ۹گانه چین، پارسر پیش‌فاکتور دستی و CSV |
| `tests/test_ranking.py` | Unit | ۳ | **Pass** | تفکیک صریح امتیاز فرصت از سطح اطمینان داده، کشف پرچم‌های قرمز تقلب، تطبیق تعرفه HS و CRA |
| `tests/test_e2e.py` | Integration / Security | ۸ | **Pass** | جریان عدم کفایت داده، جریان سناریوهای کامل، دفاع SSRF عمیق با رزولوشن DNS، ثبت قیمت دستی بازار، آپلود CSV و دانلود گزارش‌ها |
| `tests/test_live_sources.py` | Live Network (`@pytest.mark.live`) | ۲ | **Pass** | استعلام واقعی از API دیجی‌کالا و تولید لینک‌های پارامتریک سورس‌های B2B چین |

---

## ۳. خروجی رسمی دستور اجرای Pytest

```text
============================= test session starts =============================
platform win32 -- Python 3.13.2, pytest-8.3.5, pluggy-1.5.0
rootdir: C:\Users\ASUS\OneDrive\Desktop\projs\import
configfile: pytest.ini
testpaths: tests
plugins: anyio-4.9.0, langsmith-0.5.0
collected 34 items

tests\test_calculator.py ......                                          [ 17%]
tests\test_connectors.py ....                                            [ 29%]
tests\test_e2e.py ........                                               [ 52%]
tests\test_live_sources.py ..                                            [ 58%]
tests\test_matching.py .....                                             [ 73%]
tests\test_money.py ......                                               [ 91%]
tests\test_ranking.py ...                                                [100%]

======================== 34 passed, 1 warning in 5.82s ========================
```

---

## ۴. نحوه اجرای تفکیک‌شده تست‌ها

1. **اجرای تمامی تست‌ها (پیش‌فرض):**
   ```bash
   pytest
   ```
2. **اجرای تست‌های ایزوله بدون نیاز به اینترنت (مناسب خط لوله CI/CD):**
   ```bash
   pytest -m "not live"
   ```
3. **اجرای منحصراً تست‌های دارای ارتباط زنده اینترنتی:**
   ```bash
   pytest -m live
   ```
