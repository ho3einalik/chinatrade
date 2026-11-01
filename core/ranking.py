"""
Multi-Factor Opportunity Ranking & Data Confidence Engine.
Strictly separates Opportunity Commercial Attractiveness from Data Confidence.
"""

from decimal import Decimal
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from core.matching import MatchClassification

@dataclass
class OpportunityScoreBreakdown:
    opportunity_score: float         # 0.0 to 10.0
    data_confidence_score: float     # 0.0 to 100.0 %
    profitability_score: float       # 0.0 to 10.0 (ROI & Net Margin)
    demand_velocity_score: float     # 0.0 to 10.0 (Sales velocity & turnover)
    competition_score: float         # 0.0 to 10.0 (Competitive headroom)
    supplier_reliability_score: float# 0.0 to 10.0 (Years active, certs, MOQ)
    regulatory_risk_score: float     # 0.0 to 10.0 (10 = low barrier, 0 = high risk/ban)
    
    recommendation_verdict: str      # توصیه سرمایه‌گذاری
    risk_summary: List[str]
    positive_drivers: List[str]

class OpportunityRankingEngine:
    """
    Ranks import viability by evaluating economics, market liquidity, and supplier risk
    while strictly accounting for data confidence to prevent misleading scores.
    """

    @classmethod
    def evaluate(
        cls,
        net_margin_pct: float,
        roi_pct: float,
        sales_velocity_score: int,  # 1 to 10
        active_sellers_count: int,
        supplier_years: int,
        supplier_has_certs: bool,
        has_radio_or_health_barrier: bool,
        is_live_iran_data: bool,
        match_classification: MatchClassification,
        iran_sample_count: int
    ) -> OpportunityScoreBreakdown:
        positives: List[str] = []
        risks: List[str] = []

        # 1. Profitability Score (Weight: 35%)
        # Benchmarks: ROI >= 60% and Margin >= 25% is ideal in Iran's inflationary context
        if roi_pct >= 80.0:
            profit_score = 10.0
            positives.append(f"بازده سرمایه استثنایی ({roi_pct:.1f}% ROI)")
        elif roi_pct >= 50.0:
            profit_score = 8.5
            positives.append(f"سودآوری مطلوب و توجیه‌پذیر ({roi_pct:.1f}% ROI)")
        elif roi_pct >= 25.0:
            profit_score = 6.5
            positives.append(f"سودآوری متوسط ({roi_pct:.1f}% ROI)")
        elif roi_pct > 0.0:
            profit_score = 4.0
            risks.append(f"حاشیه سود ناچیز ({roi_pct:.1f}% ROI)؛ ریسک نوسان نرخ ارز را پوشش نمی‌دهد")
        else:
            profit_score = 1.0
            risks.append("طرح غیراقتصادی و دارای زیان ناخالص")

        # 2. Demand Velocity Score (Weight: 20%)
        velocity_clamped = min(max(sales_velocity_score, 1), 10)
        demand_score = float(velocity_clamped)
        if demand_score >= 8.0:
            positives.append("کشش تقاضای بالا و نقدشوندگی سریع در بازار ایران")
        elif demand_score <= 4.0:
            risks.append("سرعت فروش پایین و رکود احتمالی در چرخش انبار")

        # 3. Competition Score (Weight: 15%)
        # Too many sellers (> 20) = price war, 3-10 sellers = healthy established market
        if active_sellers_count <= 2:
            comp_score = 7.5
            positives.append("رقابت کم و فضای مستعد قیمت‌گذاری در بازار")
        elif active_sellers_count <= 10:
            comp_score = 8.5
            positives.append("تعادل مطلوب بین عمق بازار و تعداد رقبای فعال")
        elif active_sellers_count <= 25:
            comp_score = 6.0
            risks.append(f"تعداد بالای فروشندگان ({active_sellers_count} رقیب)؛ احتمال رقابت منفی قیمت")
        else:
            comp_score = 4.0
            risks.append(f"بازار اشباع و پرچگال ({active_sellers_count} فروشنده) با جنگ قیمتی شدید")

        # 4. Supplier Reliability Score (Weight: 15%)
        supp_score = 5.0
        if supplier_years >= 5:
            supp_score += 3.0
            positives.append(f"تأمین‌کننده باسابقه و تثبیت‌شده ({supplier_years} سال فعالیت کارخانه‌ای)")
        elif supplier_years >= 2:
            supp_score += 1.5
        else:
            supp_score -= 1.0
            risks.append("سابقه فعالیت تأمین‌کننده کمتر از ۲ سال است")

        if supplier_has_certs:
            supp_score += 2.0
            positives.append("دارای گواهینامه‌های بین‌المللی کیفی (CE / ISO / RoHS)")
        else:
            supp_score -= 1.0

        supp_score = min(max(supp_score, 1.0), 10.0)

        # 5. Regulatory Risk Score (Weight: 15%)
        if has_radio_or_health_barrier:
            reg_score = 5.0
            risks.append("نیازمند مجوزهای تخصصی (تنظیم مقررات رادیویی یا غذا و دارو) و فرآیند ترخیص طولانی‌تر")
        else:
            reg_score = 9.0
            positives.append("فرآیند استاندارد ثبت سفارش بدون مجوزهای مانع‌ساز خاص")

        # Composite Opportunity Score (Weighted Average)
        raw_opp_score = (
            (profit_score * 0.35) +
            (demand_score * 0.20) +
            (comp_score * 0.15) +
            (supp_score * 0.15) +
            (reg_score * 0.15)
        )
        opportunity_score = round(raw_opp_score, 1)

        # 6. Data Confidence Score (0% to 100%)
        conf_pts = 0.0
        if is_live_iran_data:
            conf_pts += 35.0
        else:
            conf_pts += 15.0

        if match_classification == MatchClassification.EXACT:
            conf_pts += 35.0
        elif match_classification == MatchClassification.CLOSE_WITH_DIFFERENCES:
            conf_pts += 25.0
        elif match_classification == MatchClassification.WEAK:
            conf_pts += 10.0
        else: # INSUFFICIENT_DATA
            conf_pts += 5.0

        if iran_sample_count >= 5:
            conf_pts += 20.0
        elif iran_sample_count >= 1:
            conf_pts += 10.0

        if supplier_years > 0:
            conf_pts += 10.0

        confidence_score = round(min(conf_pts, 100.0), 1)

        # Formulate Investment Verdict
        if opportunity_score >= 8.0 and confidence_score >= 70.0:
            verdict = "فرصت طلایی واردات (اقدام به سفارش نمونه و استعلام PI قطعی)"
        elif opportunity_score >= 6.5:
            verdict = "فرصت با جذابیت خوب (نیازمند اعتبارسنجی نهایی نمونه و مذاکره قیمت)"
        elif opportunity_score >= 5.0:
            verdict = "فرصت مشروط / حاشیه‌ای (نیازمند کاهش قیمت خرید چین یا روش حمل ارزان‌تر)"
        else:
            verdict = "توصیه نمی‌شود (ریسک بالا یا عدم توجیه اقتصادی)"

        return OpportunityScoreBreakdown(
            opportunity_score=opportunity_score,
            data_confidence_score=confidence_score,
            profitability_score=round(profit_score, 1),
            demand_velocity_score=round(demand_score, 1),
            competition_score=round(comp_score, 1),
            supplier_reliability_score=round(supp_score, 1),
            regulatory_risk_score=round(reg_score, 1),
            recommendation_verdict=verdict,
            risk_summary=risks,
            positive_drivers=positives
        )
