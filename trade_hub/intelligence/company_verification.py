"""
Company Verification & Counterparty Risk Assessment Engine for Trade Intelligence Hub.
Performs corporate identity verification, domain legitimacy checks, and red-flag audits.
"""

from typing import Dict, Any, List, Optional
from trade_hub.models import PrivateContact, VerificationStatus


class CompanyVerificationEngine:
    """
    Evaluates trustworthiness and corporate risk profile of international counterparties.
    """

    PUBLIC_FREE_EMAIL_DOMAINS = {
        "gmail.com", "yahoo.com", "hotmail.com", "outlook.com",
        "163.com", "126.com", "qq.com", "mail.ru", "yandex.ru"
    }

    HIGH_RISK_TERMS = [
        "offshore", "anonymous", "shell", "crypto only", "personal account",
        "no invoice", "western union", "third party transfer"
    ]

    @classmethod
    def evaluate_contact(cls, contact: PrivateContact) -> Dict[str, Any]:
        """
        Conducts a multi-point risk and verification audit of a private contact or counterparty.
        """
        score = 60  # Baseline neutral
        alerts: List[str] = []
        positive_factors: List[str] = []
        required_documents: List[str] = []

        # 1. Official Web Domain & Corporate Email Check
        email_clean = (contact.email or "").strip().lower()
        website_clean = (contact.website or "").strip().lower()

        if email_clean:
            domain = email_clean.split("@")[-1] if "@" in email_clean else ""
            if domain in cls.PUBLIC_FREE_EMAIL_DOMAINS:
                score -= 15
                alerts.append(f"ایمیل تجاری غیررسمی ({domain}). برای معاملات بین‌المللی ایمیل اختصاصی دامنه شرکت الزامی است.")
            elif website_clean and domain in website_clean:
                score += 15
                positive_factors.append(f"تطابق کامل دامنه ایمیل سازمانی با وب‌سایت رسمی شرکت ({domain}).")
            else:
                score += 5
                positive_factors.append("استفاده از دامنه ایمیل اختصاصی.")
        else:
            score -= 10
            alerts.append("عدم ثبت ایمیل رسمی برای طرف تجاری.")

        # 2. Physical Address & Location
        if contact.address and len(contact.address.strip()) > 10:
            score += 10
            positive_factors.append("ثبت آدرس فیزیکی دقیق دفتر یا کارخانه.")
        else:
            score -= 5
            alerts.append("آدرس فیزیکی کامل دفتر مرکزی ثبت نشده است.")

        # 3. Certifications & Quality Standards
        if contact.certifications:
            score += 15
            positive_factors.append(f"دارای گواهینامه‌های کیفی معتبر: {', '.join(contact.certifications)}.")
        else:
            required_documents.append("درخواست گواهینامه‌های کیفیت (مانند ISO، استاندارد ملی یا گواهی حلال)")

        # 4. Payment Terms Risk Audit
        pt_lower = (contact.payment_terms or "").lower()
        if "l/c" in pt_lower or "letter of credit" in pt_lower or "اعتبار اسنادی" in pt_lower:
            score += 10
            positive_factors.append("پذیرش اعتبار اسنادی (Letter of Credit) جهت تضمین بانکی تعهدات.")
        elif "100% advance" in pt_lower or "پیش پرداخت ۱۰۰" in pt_lower:
            score -= 20
            alerts.append("ریسک مالی: شرط پرداخت ۱۰۰٪ پیش‌پرداخت بدون ضمانت‌نامه بانکی پیشنهاد شده است.")
        elif "cad" in pt_lower or "cash against documents" in pt_lower:
            score += 5
            positive_factors.append("روش پرداخت وصولی اسنادی (CAD).")

        # 5. Sanctions & Red-flag terms scan
        combined_text = f"{contact.name} {contact.private_notes} {contact.payment_terms}".lower()
        for term in cls.HIGH_RISK_TERMS:
            if term in combined_text:
                score -= 30
                alerts.append(f"هشدار امنیتی: واژه پرریسک شناسایی شد: '{term}'.")

        # 6. Standard Trade Document Requirements
        required_documents.extend([
            "اساسنامه و روزنامه رسمی شرکت (Certificate of Incorporation)",
            "گواهی ثبت مالیاتی / شناسه ملی اقتصادی (Tax Registration ID)",
            "کارت بازرگانی یا گواهی عضویت در اتاق بازرگانی کشور مبدا",
            "گواهی استاندارد کالا و آنالیز آزمایشگاهی (CoA / Test Report)"
        ])

        # Final classification
        score = max(0, min(100, score))
        if score >= 80:
            status = VerificationStatus.OFFICIAL_VERIFIED
        elif score >= 60:
            status = VerificationStatus.PRELIMINARY_MATCH
        elif score >= 40:
            status = VerificationStatus.NEEDS_REVIEW
        elif any("هشدار امنیتی" in a for a in alerts):
            status = VerificationStatus.RED_FLAG
        else:
            status = VerificationStatus.INSUFFICIENT_DATA

        return {
            "entity_name": contact.name,
            "country": contact.country,
            "verification_score": score,
            "status": status,
            "positive_factors": positive_factors,
            "alerts": alerts,
            "required_documents": required_documents,
            "is_cleared_for_negotiation": score >= 50 and status != VerificationStatus.RED_FLAG
        }
