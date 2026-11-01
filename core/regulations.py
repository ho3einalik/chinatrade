"""
Iran Import Regulatory & HS Code Compliance Engine.
Evaluates customs tariff codes, mandatory licensing authorities, FX queues, and trade barriers.
"""

from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field

@dataclass
class HSCodeCandidate:
    code: str
    description_fa: str
    base_tariff_pct: float
    commercial_benefit_pct: float
    vat_pct: float = 10.0
    is_import_banned: bool = False
    priority_group: str = "22"  # گروه کالایی در سامانه جامع تجارت (e.g. 21, 22, 23, 27, 4)

@dataclass
class RegulatoryAssessment:
    product_category: str
    candidate_hs_codes: List[HSCodeCandidate]
    primary_hs_code: str
    mandatory_licenses: List[str]
    is_radio_equipment: bool
    is_medical_or_cosmetic: bool
    is_prohibited_or_restricted: bool
    estimated_fx_queue_days: int
    regulatory_warnings: List[str]
    compliance_steps: List[str]

class ImportRegulationsEngine:
    # Curated HS Code Database for common China-Iran import categories
    HS_CATALOG = {
        "smartwatch": HSCodeCandidate(
            code="8517.62.90",
            description_fa="ساعت‌های هوشمند و دستگاه‌های فرستنده و گیرنده صوت و تصویر و داده",
            base_tariff_pct=4.0,
            commercial_benefit_pct=11.0,
            vat_pct=10.0,
            priority_group="22"
        ),
        "earbuds": HSCodeCandidate(
            code="8518.30.00",
            description_fa="هدفون و گوشی‌های متصل به گوش حتی با میکروفن (TWS و ایرپاد)",
            base_tariff_pct=4.0,
            commercial_benefit_pct=11.0,
            vat_pct=10.0,
            priority_group="22"
        ),
        "powerbank": HSCodeCandidate(
            code="8504.40.90",
            description_fa="مبدل‌های استاتیک و شارژرهای پرتابل (پاوربانک دارای باتری لیتیومی)",
            base_tariff_pct=4.0,
            commercial_benefit_pct=6.0,
            vat_pct=10.0,
            priority_group="22"
        ),
        "drill": HSCodeCandidate(
            code="8467.21.00",
            description_fa="ابزارهای الکترومکانیکی برای کار با دست با موتور خودکار - مته‌ها و دریل‌ها",
            base_tariff_pct=4.0,
            commercial_benefit_pct=1.0,
            vat_pct=10.0,
            priority_group="21"
        ),
        "pvc": HSCodeCandidate(
            code="3904.10.00",
            description_fa="پلی وینیل کلراید (PVC) که با هیچ ماده دیگری مخلوط نشده باشد",
            base_tariff_pct=4.0,
            commercial_benefit_pct=1.0,
            vat_pct=10.0,
            priority_group="21"
        ),
        "camera": HSCodeCandidate(
            code="8525.89.00",
            description_fa="دوربین‌های مداربسته دیجیتال و امنیتی بیسیم",
            base_tariff_pct=4.0,
            commercial_benefit_pct=11.0,
            vat_pct=10.0,
            priority_group="22"
        ),
        "general": HSCodeCandidate(
            code="8479.89.90",
            description_fa="سایر ماشین‌آلات و دستگاه‌ها با کاربرد خاص",
            base_tariff_pct=4.0,
            commercial_benefit_pct=6.0,
            vat_pct=10.0,
            priority_group="22"
        )
    }

    @classmethod
    def analyze_compliance(cls, product_name: str, category: str = "general") -> RegulatoryAssessment:
        p_lower = product_name.lower()
        cat_lower = category.lower()

        # Identify key domain flags
        is_radio = any(k in p_lower or k in cat_lower for k in ["smartwatch", "ساعت", "ایرپاد", "earbuds", "bluetooth", "بلوتوث", "wifi", "وای فای", "دوربین", "بیسیم", "rf"])
        is_med_cosmetic = any(k in p_lower or k in cat_lower for k in ["آرایشی", "پوست", "بهداشتی", "ماساژور", "پزشکی", "دارو", "cosmetic", "medical"])
        is_tool = any(k in p_lower or k in cat_lower for k in ["دریل", "ابزار", "آچار", "drill", "tool"])
        is_polymer = any(k in p_lower or k in cat_lower for k in ["pvc", "hdpe", "pp", "pet", "پلیمر", "پتروشیمی", "رزین"])

        # Select HS candidates
        candidates: List[HSCodeCandidate] = []
        if any(w in p_lower for w in ["ساعت", "smartwatch", "watch", "ultra"]):
            candidates.append(cls.HS_CATALOG["smartwatch"])
        elif any(w in p_lower for w in ["ایرپاد", "هندزفری", "هدفون", "earbuds", "headphone"]):
            candidates.append(cls.HS_CATALOG["earbuds"])
        elif any(w in p_lower for w in ["پاوربانک", "powerbank", "شارژر"]):
            candidates.append(cls.HS_CATALOG["powerbank"])
        elif is_tool:
            candidates.append(cls.HS_CATALOG["drill"])
        elif is_polymer:
            candidates.append(cls.HS_CATALOG["pvc"])
        elif "دوربین" in p_lower or "camera" in p_lower:
            candidates.append(cls.HS_CATALOG["camera"])
        else:
            candidates.append(cls.HS_CATALOG["general"])

        primary = candidates[0]

        licenses: List[str] = [
            "ثبت آماری و پرونده در سامانه جامع تجارت (NTSW)",
            "مجوز ارزی و ثبت سفارش از وزارت صنعت، معدن و تجارت (صمت)"
        ]
        warnings: List[str] = []
        steps: List[str] = []

        if is_radio:
            licenses.append("مجوز تأیید نمونه و انطباق فرکانسی از سازمان تنظیم مقررات و ارتباطات رادیویی (CRA)")
            warnings.append("الزام اخذ تأییدیه استاندارد رادیویی CRA؛ زمان بررسی آزمایشگاه تست تشعشع و باند فرکانسی معمولاً ۱۰ تا ۲۰ روز کاری طول می‌کشد.")

        if is_med_cosmetic:
            licenses.append("مجوز ترخیص و استاندارد فنی سازمان غذا و دارو (TTAC / سامانه بهین یار)")
            warnings.append("کالاهای دارای کاربرد سلامت‌محور مشمول ضوابط سخت‌گیرانه آزمایشگاهی وزارت بهداشت هستند.")

        if is_tool or is_polymer:
            licenses.append("مجوز سازمان ملی استاندارد ایران (استاندارد اجباری ISIRI)")

        # Forex queue estimate
        # Group 21 (raw materials): ~30-45 days, Group 22 (consumer tech): ~60-90 days
        fx_days = 35 if is_polymer or is_tool else 65

        # Compliance roadmap
        steps.append("۱. ثبت پیش‌فاکتور (Proforma Invoice) در سامانه جامع تجارت و دریافت کد ساتا (SATA)")
        steps.append("۲. درخواست تخصیص ارز در سامانه نیما و ورود به صف بانک مرکزی")
        if is_radio:
            steps.append("۳. ارائه نمونه ترخیص موقت به آزمایشگاه آزمون سازمان تنظیم مقررات رادیویی")
        steps.append("۴. بارگذاری اسناد حمل (BL / AWB) و اخذ کد ترخیصیه الکترونیک از کشتیرانی/هوایی")
        steps.append("۵. کوتاژ و اظهار در سامانه EPL گمرک جمهوری اسلامی ایران و پرداخت حقوق ورودی و مالیات ارزش افزوده")

        return RegulatoryAssessment(
            product_category=category,
            candidate_hs_codes=candidates,
            primary_hs_code=primary.code,
            mandatory_licenses=licenses,
            is_radio_equipment=is_radio,
            is_medical_or_cosmetic=is_med_cosmetic,
            is_prohibited_or_restricted=primary.is_import_banned,
            estimated_fx_queue_days=fx_days,
            regulatory_warnings=warnings,
            compliance_steps=steps
        )
