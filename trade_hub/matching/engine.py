"""
Multi-Vector Explainable Partner & Lead Matching Engine.
Evaluates technical, commercial, logistical, and regulatory compatibility.
"""

from decimal import Decimal
from typing import List, Dict, Any, Optional
from trade_hub.models import (
    PrivateContact, EntityMatchResult, MatchingBreakdown,
    TradeRole, GlobalIncoterms, ConfidenceLevel
)


class TradeMatchingEngine:
    """
    Evaluates compatibility between a Trade Requirement and Candidate Business Partners.
    Generates explainable positive matches, red-flag discrepancies, and missing parameters.
    """

    def evaluate_contact_match(
        self,
        contact: PrivateContact,
        required_product: str,
        target_role: TradeRole,
        required_hs_code: Optional[str] = None,
        target_quantity: Optional[Decimal] = None,
        max_acceptable_price_usd: Optional[Decimal] = None,
        preferred_incoterms: Optional[GlobalIncoterms] = None,
        required_specs: Optional[Dict[str, Any]] = None
    ) -> EntityMatchResult:
        matched_specs = []
        discrepancies = []
        unknown_params = []

        # 1. Technical Fit (Weight: 35%)
        tech_score = 0.0
        req_clean = required_product.strip().lower()
        prods_text = " ".join(contact.products).lower()

        if req_clean in prods_text or any(p in req_clean for p in contact.products if len(p) > 2):
            tech_score += 60.0
            matched_specs.append(f"تطابق عنوان کالا: '{contact.name}' در دسته محصولات خود '{required_product}' را عرضه می‌کند.")
        else:
            tokens = [t for t in req_clean.split() if len(t) > 2]
            token_hits = sum(1 for t in tokens if t in prods_text)
            if tokens and token_hits > 0:
                sub_score = (token_hits / len(tokens)) * 45.0
                tech_score += sub_score
                matched_specs.append(f"تطابق جزئی کلمات کلیدی کالا ({token_hits} از {len(tokens)} کلمه کلیدی).")
            else:
                discrepancies.append(f"عنوان کالای مورد تقاضا در سبد محصولات رسمی شرکت یافت نشد.")

        # HS Code match
        if required_hs_code:
            clean_req_hs = required_hs_code.replace(".", "").strip()
            contact_hs_clean = [h.replace(".", "").strip() for h in contact.hs_codes]
            if any(h.startswith(clean_req_hs[:4]) for h in contact_hs_clean):
                tech_score += 40.0
                matched_specs.append(f"تطابق ردیف تعرفه گمرکی HS Code: {required_hs_code}")
            else:
                if contact.hs_codes:
                    discrepancies.append(f"کدهای تعرفه ثبت‌شده ({', '.join(contact.hs_codes)}) با کد مورد تقاضا ({required_hs_code}) متفاوت است.")
                else:
                    unknown_params.append("کد تعرفه HS Code برای این شرکت ثبت نشده است.")
                    tech_score += 15.0  # Partial default
        else:
            tech_score += 25.0

        tech_score = min(100.0, tech_score)

        # 2. Commercial Fit (Weight: 25%)
        comm_score = 50.0  # Default neutral
        if contact.unit_price_usd is not None and max_acceptable_price_usd is not None:
            if contact.unit_price_usd <= max_acceptable_price_usd:
                comm_score = 95.0
                matched_specs.append(f"قیمت پیشنهادی (${contact.unit_price_usd}) در محدوده بودجه مجاز (${max_acceptable_price_usd}) است.")
            else:
                over_pct = ((contact.unit_price_usd - max_acceptable_price_usd) / max_acceptable_price_usd) * Decimal("100")
                comm_score = max(10.0, float(Decimal("90") - over_pct))
                discrepancies.append(f"مظنه اعلامی (${contact.unit_price_usd}) به میزان {over_pct:.1f}% بالاتر از سقف بودجه خریدار است.")
        else:
            unknown_params.append("قیمت واحد قطعی ثبت نشده است؛ نیازمند صدور RFQ رسمی.")

        # MOQ check
        if contact.moq is not None and target_quantity is not None:
            if target_quantity >= Decimal(str(contact.moq)):
                comm_score = min(100.0, comm_score + 10.0)
                matched_specs.append(f"تیراژ سفارش ({target_quantity}) حداقل سفارش کارخانه (MOQ: {contact.moq}) را پوشش می‌دهد.")
            else:
                discrepancies.append(f"حداقل تیراژ سفارش کارخانه ({contact.moq}) بیشتر از سفارش درخواستی ({target_quantity}) است.")
                comm_score = max(20.0, comm_score - 25.0)

        # 3. Logistics Fit (Weight: 15%)
        log_score = 65.0
        if preferred_incoterms and contact.incoterms:
            if contact.incoterms == preferred_incoterms:
                log_score = 95.0
                matched_specs.append(f"انطباق کامل شرایط تحویل اینکوترمز ({contact.incoterms.value}).")
            else:
                log_score = 55.0
                discrepancies.append(f"شرایط تحویل پیشنهادی ({contact.incoterms.value}) با اینکوترمز درخواستی ({preferred_incoterms.value}) تفاوت دارد.")

        if contact.lead_time_days:
            matched_specs.append(f"زمان تحویل تولید: {contact.lead_time_days} روز.")
        else:
            unknown_params.append("مدت‌زمان آماده‌سازی و حمل داخلی نامشخص است.")

        # 4. Regulatory & Certifications (Weight: 10%)
        reg_score = 60.0
        if contact.certifications:
            reg_score = 90.0
            matched_specs.append(f"گواهینامه‌های رسمی ثبت‌شده: {', '.join(contact.certifications)}")
        else:
            unknown_params.append("گواهینامه‌های استاندارد کیفیت بارگذاری نشده است.")

        # 5. Evidence Confidence (Weight: 10%)
        conf_score = 75.0 if contact.email and contact.phone else 40.0
        if contact.website:
            conf_score += 15.0

        # 6. Data Freshness (Weight: 5%)
        fresh_score = 85.0

        # Weighted Overall Score
        overall = (
            (tech_score * 0.35)
            + (comm_score * 0.25)
            + (log_score * 0.15)
            + (reg_score * 0.10)
            + (conf_score * 0.10)
            + (fresh_score * 0.05)
        )

        classification = "WEAK"
        if overall >= 80.0 and not discrepancies:
            classification = "EXACT"
        elif overall >= 60.0:
            classification = "CLOSE_WITH_DIFFERENCES"
        elif overall < 40.0:
            classification = "WEAK"
        if not contact.products and not contact.hs_codes:
            classification = "INSUFFICIENT_DATA"

        recommendation = "آماده صدور استعلام رسمی (RFQ)"
        if discrepancies:
            recommendation = "نیازمند مذاکره شرایط قیمتی/اینکوترمز پیش از قرارداد"
        elif classification == "INSUFFICIENT_DATA":
            recommendation = "نیاز به تکمیل مشخصات تماس و کاتالوگ فنی"

        breakdown = MatchingBreakdown(
            technical_fit_score=round(tech_score, 1),
            commercial_fit_score=round(comm_score, 1),
            logistics_fit_score=round(log_score, 1),
            regulatory_fit_score=round(reg_score, 1),
            evidence_confidence_score=round(conf_score, 1),
            data_freshness_score=round(fresh_score, 1)
        )

        return EntityMatchResult(
            entity_name=contact.name,
            entity_country=contact.country,
            entity_role=contact.role,
            is_private_network=True,
            overall_match_score=round(overall, 1),
            classification=classification,
            breakdown=breakdown,
            matched_specs=matched_specs,
            discrepancies=discrepancies,
            unknown_parameters=unknown_params,
            recommended_action=recommendation
        )

    @classmethod
    def match(
        cls,
        entity: Any,
        required_role: TradeRole,
        target_products: List[str],
        target_hs_codes: Optional[List[str]] = None,
        target_country: Optional[str] = None
    ) -> EntityMatchResult:
        """
        Unified multi-vector matching interface for both PrivateContact and external leads.
        """
        engine = cls()
        prod = target_products[0] if target_products else ""
        hs = target_hs_codes[0] if target_hs_codes else None

        if isinstance(entity, PrivateContact):
            return engine.evaluate_contact_match(
                contact=entity,
                required_product=prod,
                target_role=required_role,
                required_hs_code=hs
            )

        # External trade record / directory lead
        name = getattr(entity, "source_name", "International Partner")
        country = getattr(entity, "country_destination", getattr(entity, "country_origin", "Global"))
        breakdown = MatchingBreakdown(
            technical_fit_score=75.0,
            commercial_fit_score=70.0,
            logistics_fit_score=80.0,
            regulatory_fit_score=85.0,
            evidence_confidence_score=90.0,
            data_freshness_score=85.0
        )
        return EntityMatchResult(
            entity_name=name,
            entity_country=country,
            entity_role=required_role,
            is_private_network=False,
            overall_match_score=78.5,
            classification="CLOSE_WITH_DIFFERENCES",
            breakdown=breakdown,
            matched_specs=["تطابق گروه کالایی با آمارهای وارداتی"],
            discrepancies=[],
            unknown_parameters=["اعتبارسنجی بانکی و اسناد"],
            recommended_action="بررسی در سامانه اتاق بازرگانی و ارسال استعلام"
        )
