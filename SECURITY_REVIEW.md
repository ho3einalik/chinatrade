# بازبینی و ممیزی امنیتی سامانه (SECURITY_REVIEW.md)

این سند گزارش ممیزی امنیتی، مدل تهدیدات و تدابیر محافظتی پیاده‌سازی‌شده در نرم‌افزار **iTrade China** است.

---

## ۱. ارزیابی مدل تهدید و تدابیر مقابله (Threat Model & Mitigations)

| نوع تهدید | بردار حمله | مکانیزم دفاعی پیاده‌سازی‌شده | وضعیت |
| :--- | :--- | :--- | :---: |
| **حملات جعل درخواست سمت سرور (SSRF)** | وارد کردن آدرس‌های شبکه داخلی (`127.0.0.1`, `localhost`, `169.254.169.254`, `10.0.0.0/8`, `192.168.0.0/16`) در ورودی جستجو | تابع `validate_safe_url` در `server.py` آدرس‌های لوپ‌بک، پرایوت و متادیتای ابری را قبل از هرگونه درخواست شبکه مسدود و HTTP 400 برمی‌گرداند. | **ایمن** |
| **پیمایش مسیر دایرکتوری (Directory Traversal)** | ارسال نام فایل‌های دستکاری‌شده مانند `../../etc/passwd` در اندپوینت‌های دانلود گزارش | اعمال تابع `os.path.basename` و اعتبارسنجی اسلاگ نام محصول در `server.py` و `core/report_generator.py`. | **ایمن** |
| **تزریق به پایگاه داده (SQL Injection)** | وارد کردن کاراکترهای مخرب در پارامترهای ثبت پیش‌فاکتور یا جستجو | استفاده انحصاری از کوئری‌های پارامتری‌شده (Parameterized Queries) در `core/db.py` با استفاده از `sqlite3`. | **ایمن** |
| **نشت اطلاعات حساس و کلیدهای دسترسی** | کامیت شدن توکن‌ها، رمز عبور دیتابیس یا کلیدهای API در گیت‌هاب | متغیرهای حساس در `.env` ذخیره شده و `.gitignore` مانع از آپلود فایل‌های اعتبارسنجی می‌شود. مقدار پیش‌فرض امن در کد تعبیه شده است. | **ایمن** |
| **محروم‌سازی از سرویس (DoS) و بار بیش‌ازحد** | ارسال درخواست‌های متوالی برای خزش سایت‌های خارجی و مصرف منابع | پیاده‌سازی `CircuitBreaker` در `connectors/base.py` (قطع خودکار مدار پس از ۳ خطای متوالی) و کنترل نرخ درخواست (Rate Limiting حداقل ۵۰۰ میلی‌ثانیه). | **ایمن** |

---

## ۲. کد پیاده‌سازی محافظت SSRF در `server.py`

```python
def validate_safe_url(url: str) -> bool:
    try:
        parsed = urllib.parse.urlparse(url)
        hostname = parsed.hostname
        if not hostname:
            return True

        if hostname.lower() in ("localhost", "127.0.0.1", "0.0.0.0", "::1"):
            return False

        try:
            ip = ipaddress.ip_address(hostname)
            if ip.is_private or ip.is_loopback or ip.is_link_local:
                return False
        except ValueError:
            pass

        return True
    except Exception:
        return False
```

این متد در تست خودکار `tests/test_e2e.py::test_ssrf_protection_blocks_internal_addresses` ارزیابی و صحه‌گذاری شده است.
