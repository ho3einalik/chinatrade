"""
Supplier Verification & Risk Assessment Engine.
Audits Chinese factory credentials, spots fraud red flags, and evaluates trade safety.
"""

from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field
from core.models import ChineseSupplier

@dataclass
class SupplierAuditResult:
    supplier_name: str
    risk_level: str  # LOW, MEDIUM, HIGH, CRITICAL
    risk_level_fa: str
    safety_score: float  # 0.0 to 10.0
    is_factory: bool     # True = Manufacturer, False = Trading Middleman
    red_flags: List[str] = field(default_factory=list)
    positive_signals: List[str] = field(default_factory=list)
    actionable_recommendations: List[str] = field(default_factory=list)

class SupplierVerificationEngine:
    @classmethod
    def audit_supplier(cls, supplier: ChineseSupplier, category: str = "general") -> SupplierAuditResult:
        red_flags: List[str] = []
        positive_signals: List[str] = []
        recommendations: List[str] = []
        points = 7.0  # Base score

        cat_lower = category.lower()
        is_elec = any(k in cat_lower for k in ["الکترونیک", "گجت", "ساعت", "صدا", "شارژ", "electronics", "gadget"])
        is_chem = any(k in cat_lower for k in ["شیمیایی", "پتروشیمی", "رزین", "chemical", "polymer"])

        # 1. Company Name & Business Nature
        name_lower = supplier.name.lower()
        if any(w in name_lower for w in ["trading", "commercial", "import & export", "بازرگانی", "واسطه"]):
            is_factory = False
            points -= 1.0
            red_flags.append("ماهیت شرکت بازرگانی/واسطه‌ای (Trading Company) است و تولیدکننده مستقیم نیست")
            recommendations.append("مذاکره برای حذف کارمزد واسطه یا جستجوی کارخانه مادر در 1688")
        elif any(w in name_lower for w in ["technology", "industry", "manufacturing", "factory", "electronics", "plastic"]):
            is_factory = True
            points += 1.5
            positive_signals.append("ماهیت حقوقی تولیدکننده صنعتی و دارای خطوط مونتاژ")
        else:
            is_factory = True

        # 2. Years Active & Longevity
        if supplier.years_active >= 8:
            points += 2.0
            positive_signals.append(f"سابقه طولانی و تثبیت‌شده در صنعت چین ({supplier.years_active} سال فعالیت مستمر)")
        elif supplier.years_active >= 3:
            points += 1.0
            positive_signals.append(f"سابقه فعالیت قابل قبول ({supplier.years_active} سال)")
        elif supplier.years_active <= 1:
            points -= 2.5
            red_flags.append("شرکت نوپا با سابقه کمتر از ۱ سال؛ ریسک عدم تحویل یا کیفیت ناپایدار")
            recommendations.append("عدم پرداخت مستقیم به حساب شخصی فروشنده؛ فقط از طریق ضمانت رسمی پلتفرم (Trade Assurance / 1688 Danbao)")

        # 3. Certifications Audit
        if is_elec:
            has_ce_rohs = any(c.upper() in ["CE", "ROHS", "FCC"] for c in supplier.certifications)
            if has_ce_rohs:
                points += 1.5
                positive_signals.append(f"دارای استانداردهای صادراتی الزامی: {', '.join(supplier.certifications)}")
            else:
                points -= 1.0
                red_flags.append("عدم ثبت گواهینامه CE/RoHS برای تجهیزات الکترونیکی در پروفایل")
                recommendations.append("درخواست استعلام تصویر گواهی CE و انطباق با تست ریپورت معتبر LVD/EMC قبل از ثبت سفارش")

        # 4. Pricing sanity check
        if supplier.unit_price_cny <= 1.0 and is_elec:
            points -= 3.0
            red_flags.append(f"قیمت غیرعادی و مشکوک ({supplier.unit_price_cny} یوان) برای محصول الکترونیکی؛ احتمال قطعه یدکی یا کلاهبرداری")
            recommendations.append("بررسی دقیق مشخصات فنی؛ قیمت ممکن است مربوط به اکسسوری جانبی باشد نه محصول کامل")

        # 5. Location Check
        loc = supplier.location.lower()
        if any(prov in loc for prov in ["guangdong", "shenzhen", "dongguan", "zhejiang", "yiwu", "ningbo", "jiangsu", "shandong"]):
            positive_signals.append(f"مستقر در قطب صنعتی تخصصی چین ({supplier.location})")
        
        # 6. Safety recommendations
        recommendations.append("سفارش حتمی حداقل یک عدد نمونه واقعی (Sample) جهت تست فیزیکی و آزمایشگاه قبل از تولید انبوه")
        recommendations.append("الزام درج بند بازرسی شخص ثالث (Pre-shipment Inspection توسط SGS/Cotecna) در قرارداد یا پیش‌فاکتور (PI)")

        # Final score clamp
        safety_score = round(min(max(points, 1.0), 10.0), 1)

        if safety_score >= 8.0 and not red_flags:
            risk_level = "LOW"
            risk_level_fa = "ریسک پایین (تأمین‌کننده معتبر و استاندارد)"
        elif safety_score >= 6.0:
            risk_level = "MEDIUM"
            risk_level_fa = "ریسک متوسط (نیازمند بررسی نمونه و شرایط پرداخت امن)"
        elif safety_score >= 4.0:
            risk_level = "HIGH"
            risk_level_fa = "ریسک بالا (نیازمند بازرسی فیزیکی و احتیاط مضاعف)"
        else:
            risk_level = "CRITICAL"
            risk_level_fa = "ریسک بحرانی (معامله با این تأمین‌کننده توصیه نمی‌شود)"

        return SupplierAuditResult(
            supplier_name=supplier.name,
            risk_level=risk_level,
            risk_level_fa=risk_level_fa,
            safety_score=safety_score,
            is_factory=is_factory,
            red_flags=red_flags,
            positive_signals=positive_signals,
            actionable_recommendations=recommendations
        )
