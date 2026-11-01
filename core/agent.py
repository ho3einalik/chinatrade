"""
Core AI Import Intelligence & Arbitrage Agent for China-to-Iran Trade.
Orchestrates Chinese factory sourcing, Iranian market benchmarking, landed cost math,
regulatory risk assessment, and executive opportunity discovery.
"""

from typing import List, Optional, Dict, Any
from config import CONFIG, TradeConfig
from core.models import (
    ImportOpportunityReport,
    ChineseSupplier,
    IranMarketPrice,
    DataProvenanceBreakdown,
    ComponentStatus,
    DataType,
    VerificationStatus
)
from core.china_sourcing import ChinaSourcingEngine
from core.iran_market import IranMarketEngine
from core.calculator import ImportProfitCalculator, ComprehensiveLandedCostResult
from core.matching import ProductMatchingEngine, MatchExplanation
from core.verification import SupplierVerificationEngine, SupplierAuditResult
from core.regulations import ImportRegulationsEngine, RegulatoryAssessment
from core.ranking import OpportunityRankingEngine, OpportunityScoreBreakdown
from connectors.china_b2b import ChinaB2BConnector
from core.db import Database
from core.alerts import AlertEngine

class ChinaIranImportAgent:
    def __init__(self, config: Optional[TradeConfig] = None):
        self.config = config or CONFIG
        self.db = Database()
        self.sourcing_engine = ChinaSourcingEngine(self.db)
        self.market_engine = IranMarketEngine(self.db)
        self.calculator = ImportProfitCalculator(self.config)
        self.matching_engine = ProductMatchingEngine()
        self.b2b_connector = ChinaB2BConnector()
        self.alert_engine = AlertEngine(self.db)

    def analyze_product(
        self,
        product_query: str,
        category: Optional[str] = None,
        custom_target_iran_price: Optional[float] = None,
        batch_quantity: Optional[int] = None,
        allow_demo: bool = False,
        custom_buy_price_cny: Optional[float] = None,
        include_indicative_benchmark: bool = True
    ) -> ImportOpportunityReport:
        """
        تحلیل جامع ۳۶۰ درجه یک کالا:
        ۱. یافتن کارخانه‌ها و قیمت‌های چین در ۱۶۸۸، علی‌بابا، Made-in-China، ChemNet
        ۲. استخراج قیمت‌های رقبا در بازار ایران (ترب، دیجی‌کالا، بازار آزاد)
        ۳. محاسبه بهای تمام‌شده گمرکی، هوایی، دریایی و سود خالص
        ۴. تعیین HS Code و مجوزهای الزامی گمرک
        ۵. ارزیابی ریسک و شناسنامه تفکیک‌شده داده‌ها
        """
        # ۱. استخراج تامین‌کنندگان چین (پیش‌فاکتور قطعی، ورودی دستی کاربر، یا نرخ مرجع صنعتی)
        suppliers = self.sourcing_engine.search_suppliers(
            product_query,
            category,
            allow_demo=allow_demo,
            custom_buy_price_cny=custom_buy_price_cny,
            include_indicative_benchmark=include_indicative_benchmark
        )
        best_supplier = suppliers[0] if suppliers else None

        # ۲. استخراج قیمت در بازار ایران (استعلام زنده دیجی‌کالا یا قیمت دستی)
        iran_market = self.market_engine.analyze_iran_market(product_query, custom_target_iran_price)

        # تعیین قیمت فروش هدف (در صورت عدم دسترسی: None)
        target_sell_price = custom_target_iran_price or (iran_market.average_price_toman if iran_market else None)

        # ۳. تخمین کد تعرفه گمرکی (HS Code) و الزامات رگولاتوری
        hs_code, regulations, detected_category = self._determine_customs_and_regulations(product_query)

        # ۴. شناسنامه تفکیک‌شده وضعیت مؤلفه‌های داده (Data Provenance Breakdown)
        missing_reqs: List[str] = []
        
        # الف) وضعیت قیمت تأمین‌کننده چین
        if best_supplier:
            if best_supplier.data_type in (DataType.MANUAL_QUOTE, DataType.CSV_IMPORT) and best_supplier.verification_status != VerificationStatus.MANUAL_OVERRIDE:
                supp_status = ComponentStatus.REAL_VERIFIED
                supp_source = f"پیش‌فاکتور رسمی ثبت‌شده ({best_supplier.name} - {best_supplier.platform})"
            elif best_supplier.verification_status == VerificationStatus.MANUAL_OVERRIDE:
                supp_status = ComponentStatus.USER_MANUAL
                supp_source = "قیمت ورودی مستقیم کاربر در استعلام"
            elif best_supplier.data_type == DataType.ESTIMATE:
                supp_status = ComponentStatus.ESTIMATED
                supp_source = "نرخ مرجع صنعتی کاتالوگ چین (شبیه‌سازی سناریو)"
                missing_reqs.append("پیش‌فاکتور قطعی کارخانه چین ثبت نشده است (محاسبه بر مبنای نرخ مرجع صنعتی انجام شد).")
            else:
                supp_status = ComponentStatus.ESTIMATED
                supp_source = "داده نمونه آموزشی (Demo)"
        else:
            supp_status = ComponentStatus.UNAVAILABLE
            supp_source = "قیمت خرید چین ناموجود"
            missing_reqs.append("هیچ قیمتی برای خرید از چین یافت نشد. قیمت را از لینک‌های زنده استعلام کرده و در ماشین‌حساب وارد کنید.")

        # ب) وضعیت قیمت بازار ایران
        if custom_target_iran_price and custom_target_iran_price > 0:
            market_status = ComponentStatus.USER_MANUAL
            market_source = "قیمت هدف واردشده توسط کاربر"
        elif iran_market and iran_market.status == "available" and iran_market.average_price_toman:
            market_status = ComponentStatus.REAL_VERIFIED
            market_source = f"استعلام زنده API دیجی‌کالا ({iran_market.active_sellers_count} کالا)"
        else:
            market_status = ComponentStatus.UNAVAILABLE
            market_source = "استعلام زنده نتیجه‌ای نداشت"
            missing_reqs.append("قیمت فروش کالا در بازار ایران ناموجود است. قیمت فروش هدف را وارد کنید.")

        # تشخیص امکان سود قطعی در برابر شبیه‌سازی سناریو
        is_definite = (supp_status in (ComponentStatus.REAL_VERIFIED, ComponentStatus.USER_MANUAL)) and \
                      (market_status in (ComponentStatus.REAL_VERIFIED, ComponentStatus.USER_MANUAL))
        is_simulation = not is_definite

        # ۵. محاسبات دقیق مالی (هوایی و دریایی)
        air_analysis = None
        sea_analysis = None
        is_insufficient = False

        if best_supplier and target_sell_price and target_sell_price > 0:
            calc_mode = "DEFINITE_CONTRACT" if is_definite else "SCENARIO_SIMULATION"
            is_insufficient = False
            air_analysis = self.calculator.calculate_landed_cost(
                supplier=best_supplier,
                target_iran_price_toman=target_sell_price,
                shipping_method="Air Cargo",
                batch_quantity=batch_quantity or best_supplier.moq
            )
            sea_analysis = self.calculator.calculate_landed_cost(
                supplier=best_supplier,
                target_iran_price_toman=target_sell_price,
                shipping_method="Sea Freight",
                batch_quantity=batch_quantity or max(best_supplier.moq * 2, 500)
            )
        else:
            calc_mode = "DISCOVERY_ONLY"
            is_insufficient = True

        data_prov = DataProvenanceBreakdown(
            supplier_price_status=supp_status.value,
            supplier_price_source=supp_source,
            supplier_price_value=best_supplier.unit_price_cny if best_supplier else None,
            supplier_currency="CNY",
            iran_market_status=market_status.value,
            iran_market_source=market_source,
            iran_market_value_toman=target_sell_price,
            iran_sellers_count=iran_market.active_sellers_count if iran_market else 0,
            shipping_cost_status="ESTIMATED",
            shipping_cost_source="نرخ‌نامه مرجع لجستیک هوایی (IATA) و کانتینری (CBM)",
            customs_tariff_status="REAL_VERIFIED",
            customs_tariff_source="کتاب رسمی مقررات صادرات و واردات سال جاری",
            hs_code=hs_code,
            is_definite_profit_ready=is_definite,
            missing_for_definite=missing_reqs,
            calculation_mode=calc_mode
        )

        # ۶. محاسبه امتیاز جذابیت فرصت و توصیه بازرگانی
        if not is_insufficient:
            opp_score = self._calculate_opportunity_score(air_analysis, sea_analysis, iran_market)
            summary = self._generate_recommendation_summary(
                product_query, best_supplier, air_analysis, sea_analysis, iran_market, opp_score
            )
            if is_simulation:
                summary += " [توجه: این سناریو بر اساس نرخ مرجع صنعتی چین شبیه‌سازی شده و پیش‌فاکتور قطعی کارخانه نیست]."
        else:
            opp_score = 1.0
            summary = "مشخصات فنی، کد تعرفه گمرکی و لینک‌های تأمین‌کنندگان شناسایی شدند. به دلیل نبود هم‌زمان قیمت خرید و فروش، محاسبه سود به ورود قیمت در ماشین‌حساب سناریو موکول شد."

        return ImportOpportunityReport(
            product_name_fa=product_query,
            product_name_en=best_supplier.product_title if best_supplier else product_query,
            category=category or detected_category,
            hs_code_estimate=hs_code,
            regulatory_notes=regulations,
            suppliers_china=suppliers,
            best_supplier=best_supplier,
            iran_market=iran_market,
            air_cost_analysis=air_analysis,
            sea_cost_analysis=sea_analysis,
            opportunity_score=opp_score,
            recommendation_summary=summary,
            insufficient_data=is_insufficient,
            data_provenance=data_prov,
            is_simulation=is_simulation,
            definite_profit_calculable=is_definite,
            missing_requirements=missing_reqs
        )

    def analyze_product_comprehensive(
        self,
        product_query: str,
        category: Optional[str] = None,
        custom_target_iran_price: Optional[float] = None,
        batch_quantity: Optional[int] = None,
        allow_demo: bool = False,
        custom_buy_price_cny: Optional[float] = None,
        include_indicative_benchmark: bool = True
    ) -> Dict[str, Any]:
        """
        تحلیل ۳۶۰ درجه و تمام‌عیار با سناریوهای ۳گانه، امتیاز تطبیق، ارزیابی ریسک و ثبت در دیتابیس
        """
        # 1. Base report
        report = self.analyze_product(
            product_query,
            category,
            custom_target_iran_price,
            batch_quantity,
            allow_demo=allow_demo,
            custom_buy_price_cny=custom_buy_price_cny,
            include_indicative_benchmark=include_indicative_benchmark
        )
        best_sup = report.best_supplier
        cat = report.category
        target_price = custom_target_iran_price or (report.iran_market.average_price_toman if report.iran_market else None)

        # 2. 3-Scenario Landed Cost Calculations (Air & Sea)
        air_scenarios = None
        sea_scenarios = None
        if best_sup and target_price and target_price > 0:
            air_scenarios = self.calculator.calculate_landed_cost_scenarios(
                supplier=best_sup,
                target_iran_price_toman=target_price,
                shipping_method="Air Cargo",
                batch_quantity=batch_quantity or best_sup.moq
            )
            sea_scenarios = self.calculator.calculate_landed_cost_scenarios(
                supplier=best_sup,
                target_iran_price_toman=target_price,
                shipping_method="Sea Freight",
                batch_quantity=batch_quantity or max(best_sup.moq * 2, 500)
            )

        # 3. Product Matching Engine Evaluation with real Iranian specs extraction
        matching_res = None
        if best_sup and report.iran_market:
            iran_specs_dict = {}
            if report.iran_market.sample_products:
                sp = report.iran_market.sample_products[0]
                sp_title = sp.get("title") or sp.get("title_fa") or ""
                extracted = self.matching_engine.extract_specs_from_text(f"{report.iran_market.title_fa} {sp_title}", cat)
                iran_specs_dict = {
                    "model": extracted.model,
                    "capacity_mah": extracted.capacity_mah,
                    "voltage_volts": extracted.voltage_volts,
                    "power_watts": extracted.power_watts,
                    "grade": extracted.grade,
                    "key_features": extracted.key_features
                }

            matching_res = self.matching_engine.compare_products(
                iran_title=report.iran_market.title_fa,
                iran_specs_dict=iran_specs_dict,
                china_title=best_sup.product_title,
                china_specs_dict=best_sup.product_specs,
                category=cat
            )

        # 4. Supplier Risk Audit
        supplier_audit = None
        if best_sup:
            supplier_audit = SupplierVerificationEngine.audit_supplier(best_sup, category=cat)

        # 5. Regulatory & HS Code Assessment
        reg_assessment = ImportRegulationsEngine.analyze_compliance(product_query, category=cat)

        # 6. Multi-Factor Opportunity & Data Confidence Decoupling
        from core.matching import MatchClassification
        match_cls = matching_res.classification if matching_res else MatchClassification.INSUFFICIENT_DATA
        sample_count = len(report.iran_market.sample_products) if (report.iran_market and report.iran_market.sample_products) else (1 if report.iran_market and report.iran_market.average_price_toman else 0)
        
        best_roi = float(air_scenarios.realistic.roi_percent if air_scenarios and air_scenarios.realistic else 0.0)
        best_margin = float(air_scenarios.realistic.margin_percent if air_scenarios and air_scenarios.realistic else 0.0)
        if sea_scenarios and sea_scenarios.realistic and float(sea_scenarios.realistic.roi_percent) > best_roi:
            best_roi = float(sea_scenarios.realistic.roi_percent)
            best_margin = float(sea_scenarios.realistic.margin_percent)

        opp_eval = OpportunityRankingEngine.evaluate(
            net_margin_pct=best_margin,
            roi_pct=best_roi,
            sales_velocity_score=report.iran_market.sales_velocity_score if report.iran_market else 5,
            active_sellers_count=report.iran_market.active_sellers_count if report.iran_market else 0,
            supplier_years=best_sup.years_active if best_sup else 0,
            supplier_has_certs=bool(best_sup.certifications) if best_sup else False,
            has_radio_or_health_barrier=reg_assessment.is_radio_equipment or reg_assessment.is_medical_or_cosmetic,
            is_live_iran_data=any(c.is_live for c in (report.iran_market.channels if report.iran_market else [])),
            match_classification=match_cls,
            iran_sample_count=sample_count
        )

        # 7. Chinese B2B Search Links (Including Alibaba, 1688, AliExpress)
        chinese_kw = self.sourcing_engine.translate_to_chinese_keywords(product_query)
        english_kw = self.sourcing_engine.translate_to_english_keywords(product_query)
        b2b_links = self.b2b_connector.generate_search_links(chinese_kw, english_kw)

        # Helper serializer for scenarios
        def serialize_scenario_res(scen_obj: Optional[ComprehensiveLandedCostResult]):
            if not scen_obj or not scen_obj.is_sufficient_data:
                return {
                    "is_sufficient_data": False,
                    "data_notes": scen_obj.data_notes if scen_obj else "داده‌ها ناکافی است",
                    "realistic": None,
                    "optimistic": None,
                    "pessimistic": None
                }
            def scen_dict(s):
                if not s:
                    return None
                return {
                    "scenario_type": s.scenario_type,
                    "title_fa": s.scenario_title_fa,
                    "usd_rate": int(s.exchange_rate_usd_toman),
                    "rmb_rate": int(s.exchange_rate_rmb_toman),
                    "target_selling_price_toman": int(s.target_selling_price_toman),
                    "landed_cost_unit_toman": int(s.landed_cost_unit_toman),
                    "net_profit_unit_toman": int(s.net_profit_unit_toman),
                    "margin_percent": float(s.margin_percent),
                    "markup_percent": float(s.markup_percent),
                    "roi_percent": float(s.roi_percent),
                    "break_even_price_toman": int(s.break_even_price_toman),
                    "break_even_units": s.break_even_units,
                    "total_investment_toman": int(s.total_investment_toman),
                    "total_net_profit_toman": int(s.total_net_profit_toman),
                    "line_items": [
                        {
                            "category": item.category,
                            "name_fa": item.name_fa,
                            "amount_toman": int(item.amount_toman),
                            "percentage": float(item.percentage_of_total)
                        } for item in s.line_items
                    ]
                }
            return {
                "rule_version": scen_obj.rule_version,
                "rule_date": scen_obj.rule_date,
                "batch_quantity": scen_obj.batch_quantity,
                "shipping_method": scen_obj.shipping_method,
                "chargeable_weight_kg": float(scen_obj.chargeable_weight_kg),
                "volume_cbm": float(scen_obj.volume_cbm),
                "incoterms": scen_obj.incoterms,
                "is_sufficient_data": True,
                "data_notes": scen_obj.data_notes,
                "realistic": scen_dict(scen_obj.realistic),
                "optimistic": scen_dict(scen_obj.optimistic),
                "pessimistic": scen_dict(scen_obj.pessimistic),
                "fx_sensitivity_10pct_impact_toman": int(scen_obj.fx_sensitivity_10pct_impact_toman),
                "freight_sensitivity_20pct_impact_toman": int(scen_obj.freight_sensitivity_20pct_impact_toman)
            }

        full_result = {
            "query": product_query,
            "category": cat,
            "insufficient_data": report.insufficient_data,
            "is_simulation": report.is_simulation,
            "definite_profit_calculable": report.definite_profit_calculable,
            "missing_requirements": report.missing_requirements,
            "data_provenance": report.data_provenance.model_dump() if report.data_provenance else None,
            "report": report.model_dump(),
            "chinese_keyword": chinese_kw,
            "b2b_platforms": b2b_links,
            "air_scenarios": serialize_scenario_res(air_scenarios),
            "sea_scenarios": serialize_scenario_res(sea_scenarios),
            "matching": {
                "score": matching_res.score if matching_res else 0.0,
                "classification": matching_res.classification.value if matching_res else "INSUFFICIENT_DATA",
                "pros": matching_res.pros if matching_res else [],
                "cons": matching_res.cons if matching_res else [],
                "missing_attributes": matching_res.missing_critical_attributes if matching_res else ["هیچ داده تطبیقی استخراج نشد"],
                "is_conditional": matching_res.is_conditional if matching_res else True
            } if matching_res else None,
            "supplier_audit": {
                "name": supplier_audit.supplier_name if supplier_audit else "",
                "risk_level": supplier_audit.risk_level if supplier_audit else "UNVERIFIED",
                "risk_level_fa": supplier_audit.risk_level_fa if supplier_audit else "تأمین‌کننده ثبت نشده است",
                "safety_score": supplier_audit.safety_score if supplier_audit else 0.0,
                "is_factory": supplier_audit.is_factory if supplier_audit else False,
                "red_flags": supplier_audit.red_flags if supplier_audit else [],
                "positive_signals": supplier_audit.positive_signals if supplier_audit else [],
                "recommendations": supplier_audit.actionable_recommendations if supplier_audit else []
            } if supplier_audit else None,
            "regulations": {
                "primary_hs_code": reg_assessment.primary_hs_code,
                "candidate_hs_codes": [
                    {
                        "code": c.code,
                        "description_fa": c.description_fa,
                        "tariff_pct": c.base_tariff_pct,
                        "benefit_pct": c.commercial_benefit_pct,
                        "vat_pct": c.vat_pct,
                        "priority_group": c.priority_group
                    } for c in reg_assessment.candidate_hs_codes
                ],
                "mandatory_licenses": reg_assessment.mandatory_licenses,
                "is_radio_equipment": reg_assessment.is_radio_equipment,
                "is_medical_or_cosmetic": reg_assessment.is_medical_or_cosmetic,
                "estimated_fx_queue_days": reg_assessment.estimated_fx_queue_days,
                "warnings": reg_assessment.regulatory_warnings,
                "steps": reg_assessment.compliance_steps
            },
            "opportunity_evaluation": {
                "opportunity_score": opp_eval.opportunity_score,
                "data_confidence_score": opp_eval.data_confidence_score,
                "profitability_score": opp_eval.profitability_score,
                "demand_velocity_score": opp_eval.demand_velocity_score,
                "competition_score": opp_eval.competition_score,
                "supplier_reliability_score": opp_eval.supplier_reliability_score,
                "regulatory_risk_score": opp_eval.regulatory_risk_score,
                "verdict": opp_eval.recommendation_verdict,
                "risks": opp_eval.risk_summary,
                "positives": opp_eval.positive_drivers
            }
        }

        # 9. Persistence & Snapshots
        snapshot_id = self.db.save_search_and_snapshot(
            query=product_query,
            category=cat,
            report_dict=full_result,
            rule_version=air_scenarios.rule_version if air_scenarios else "IR-CUSTOMS-1403"
        )
        full_result["snapshot_id"] = snapshot_id

        # 10. Check triggered alerts
        current_net_profit = float(air_scenarios.realistic.net_profit_unit_toman if (air_scenarios and air_scenarios.realistic) else 0.0)
        triggered = self.alert_engine.check_alerts(product_query, current_net_profit)
        full_result["triggered_alerts"] = triggered

        return full_result

        # 8. Assemble full structured result
        full_result = {
            "query": product_query,
            "category": cat,
            "report": report.model_dump(),
            "chinese_keyword": chinese_kw,
            "b2b_platforms": b2b_links,
            "air_scenarios": serialize_scenario_res(air_scenarios),
            "sea_scenarios": serialize_scenario_res(sea_scenarios),
            "matching": {
                "score": matching_res.score if matching_res else 50.0,
                "classification": matching_res.classification.value if matching_res else "INSUFFICIENT_DATA",
                "pros": matching_res.pros if matching_res else [],
                "cons": matching_res.cons if matching_res else [],
                "missing_attributes": matching_res.missing_critical_attributes if matching_res else [],
                "is_conditional": matching_res.is_conditional if matching_res else True
            } if matching_res else None,
            "supplier_audit": {
                "name": supplier_audit.supplier_name if supplier_audit else "",
                "risk_level": supplier_audit.risk_level if supplier_audit else "MEDIUM",
                "risk_level_fa": supplier_audit.risk_level_fa if supplier_audit else "",
                "safety_score": supplier_audit.safety_score if supplier_audit else 6.0,
                "is_factory": supplier_audit.is_factory if supplier_audit else True,
                "red_flags": supplier_audit.red_flags if supplier_audit else [],
                "positive_signals": supplier_audit.positive_signals if supplier_audit else [],
                "recommendations": supplier_audit.actionable_recommendations if supplier_audit else []
            } if supplier_audit else None,
            "regulations": {
                "primary_hs_code": reg_assessment.primary_hs_code,
                "candidate_hs_codes": [
                    {
                        "code": c.code,
                        "description_fa": c.description_fa,
                        "tariff_pct": c.base_tariff_pct,
                        "benefit_pct": c.commercial_benefit_pct,
                        "vat_pct": c.vat_pct,
                        "priority_group": c.priority_group
                    } for c in reg_assessment.candidate_hs_codes
                ],
                "mandatory_licenses": reg_assessment.mandatory_licenses,
                "is_radio_equipment": reg_assessment.is_radio_equipment,
                "is_medical_or_cosmetic": reg_assessment.is_medical_or_cosmetic,
                "estimated_fx_queue_days": reg_assessment.estimated_fx_queue_days,
                "warnings": reg_assessment.regulatory_warnings,
                "steps": reg_assessment.compliance_steps
            },
            "opportunity_evaluation": {
                "opportunity_score": opp_eval.opportunity_score,
                "data_confidence_score": opp_eval.data_confidence_score,
                "profitability_score": opp_eval.profitability_score,
                "demand_velocity_score": opp_eval.demand_velocity_score,
                "competition_score": opp_eval.competition_score,
                "supplier_reliability_score": opp_eval.supplier_reliability_score,
                "regulatory_risk_score": opp_eval.regulatory_risk_score,
                "verdict": opp_eval.recommendation_verdict,
                "risks": opp_eval.risk_summary,
                "positives": opp_eval.positive_drivers
            }
        }

        # 9. Persistence & Snapshots
        snapshot_id = self.db.save_search_and_snapshot(
            query=product_query,
            category=cat,
            report_dict=full_result,
            rule_version=air_scenarios.rule_version if air_scenarios else "IR-CUSTOMS-1403"
        )
        full_result["snapshot_id"] = snapshot_id

        # 10. Check triggered alerts
        current_net_profit = float(air_scenarios.realistic.net_profit_unit_toman if air_scenarios else 0.0)
        triggered = self.alert_engine.check_alerts(product_query, current_net_profit)
        full_result["triggered_alerts"] = triggered

        return full_result

    def find_opportunities(
        self,
        category: str = "گجت‌ها و الکترونیک مصرفی",
        min_margin_percent: float = 30.0,
        max_budget_toman: Optional[float] = None
    ) -> List[ImportOpportunityReport]:
        """
        موتور خودکار شکار فرصت‌های وارداتی پرسود در یک دسته‌بندی مشخص
        """
        opportunity_catalogue = {
            "گجت‌ها و الکترونیک مصرفی": [
                "ساعت هوشمند",
                "ایرپاد بلوتوثی نویزکنسلینگ",
                "پاوربانک فست شارژ 20000",
                "ماساژور تفنگی شارژی",
                "اسپیکر بلوتوث ضدآب",
                "دوربین مداربسته وای‌فای خانگی"
            ],
            "مواد اولیه و پتروشیمی": [
                "پودر PVC گرید S65",
                "پلی اتیلن سنگین HDPE",
                "پلی پروپیلن PP نساجی و تزریقی",
                "گرانول PET بطری"
            ],
            "ابزارآلات و صنعتی": [
                "دریل شارژی براشلس ۲۱ ولت",
                "تراز لیزری ۳۶۰ درجه نور سبز",
                "کارواش شارژی سیار پرتابل",
                "مینی فرز دیمردار صنعتی"
            ],
            "لوازم خانه و آشپزخانه": [
                "فندک پلاسما الکتریکی ضد باد",
                "مخلوط‌کن و شیکر شارژی اسموتی",
                "ترازو دیجیتال آشپزخانه دقیق",
                "چراغ خواب سنسوردار هوشمند"
            ]
        }

        # اگر دسته‌بندی وجود نداشت، دسته‌بندی اول را به عنوان پیش‌فرض قرار می‌دهیم
        items_to_scan = opportunity_catalogue.get(category, opportunity_catalogue["گجت‌ها و الکترونیک مصرفی"])
        
        results: List[ImportOpportunityReport] = []
        for item in items_to_scan:
            report = self.analyze_product(item, category=category)
            # فیلتر بر اساس حداقل حاشیه سود (هوایی یا دریایی)
            best_margin = max(
                (report.air_cost_analysis.profit_margin_percent if report.air_cost_analysis else 0),
                (report.sea_cost_analysis.profit_margin_percent if report.sea_cost_analysis else 0)
            )
            if best_margin >= min_margin_percent:
                if max_budget_toman:
                    invest = report.air_cost_analysis.total_investment_toman if report.air_cost_analysis else 0
                    if invest <= max_budget_toman:
                        results.append(report)
                else:
                    results.append(report)

        # مرتب‌سازی بر اساس امتیاز فرصت
        results.sort(key=lambda r: r.opportunity_score, reverse=True)
        return results

    def _determine_customs_and_regulations(self, query: str):
        """تعیین HS Code و مجوزهای سامانه جامع تجارت، استاندارد و صمت"""
        q = query.lower()
        if any(w in q for w in ["pvc", "hdpe", "pp", "pet", "پلیمر", "پتروشیمی", "رزین"]):
            return (
                "3904.10.00",
                [
                    "نیاز به ثبت سفارش در سامانه جامع تجارت (NTSW)",
                    "نیاز به تاییدیه آنالیز آزمایشگاهی و COA کارخانه مبدا",
                    "ترخیص عموماً از گمرک شهید رجایی بندرعباس یا گمرک منطقه ویژه بوشهر",
                    "معمولاً حمل به صورت دریایی FCL (کانتینر ۲۰ یا ۴۰ فوت) به صورت پالت و کیسه ۲۵ کیلویی"
                ],
                "مواد اولیه و پتروشیمی"
            )
        elif any(w in q for w in ["ساعت", "ایرپاد", "هندزفری", "اسپیکر", "شارژر", "دوربین"]):
            return (
                "8517.62.90",
                [
                    "کالای با فناوری رادیویی/بلوتوث: نیاز به تاییدیه سازمان تنظیم مقررات و ارتباطات رادیویی (CRA)",
                    "ارزیابی استاندارد اجباری باتری‌های لیتیوم-یون (استاندارد ایمنی باتری و MSDS)",
                    "حمل پیشنهادی: کارگو هوایی از گوانگجو یا شنژن به فرودگاه امام یا ترانزیت دبی",
                    "ثبت سفارش تخصیص ارز نیمایی یا ارز حاصل از صادرات خود"
                ],
                "گجت‌ها و الکترونیک مصرفی"
            )
        elif any(w in q for w in ["دریل", "ابزار", "کارواش", "فرز"]):
            return (
                "8467.21.00",
                [
                    "کد تعرفه ماشین‌آلات برقی دستی و موتوری با موتور برقی مستقل",
                    "نیاز به گواهی استاندارد ملی ایران (ISIRI) در گمرک ورودی",
                    "ارائه تاییدیه تست ایمنی الکتریکی CE و گواهی مبدا (Certificate of Origin)"
                ],
                "ابزارآلات و صنعتی"
            )
        else:
            return (
                "8543.70.90",
                [
                    "بررسی در کتاب مقررات صادرات و واردات سال جاری",
                    "استعلام شناسه کالا و ثبت در سامانه جامع انبارها پس از ترخیص"
                ],
                "کالاهای عمومی و مصرفی"
            )

    def _calculate_opportunity_score(
        self,
        air_calc: Optional[Any],
        sea_calc: Optional[Any],
        iran_market: Optional[IranMarketPrice]
    ) -> float:
        """محاسبه نمره الگوریتمی جذابیت واردات بین ۱ تا ۱۰"""
        score = 5.0
        # انتخاب بهترین حاشیه سود
        best_margin = 0.0
        best_roi = 0.0
        if air_calc:
            best_margin = max(best_margin, air_calc.profit_margin_percent)
            best_roi = max(best_roi, air_calc.roi_percent)
        if sea_calc:
            best_margin = max(best_margin, sea_calc.profit_margin_percent)
            best_roi = max(best_roi, sea_calc.roi_percent)

        # افزایش نمره بر اساس حاشیه سود
        if best_margin >= 50:
            score += 2.5
        elif best_margin >= 35:
            score += 2.0
        elif best_margin >= 20:
            score += 1.0

        # افزایش نمره بر اساس ROI
        if best_roi >= 80:
            score += 1.5
        elif best_roi >= 40:
            score += 1.0

        # فاکتور تقاضای بازار در ترب
        if iran_market and iran_market.sales_velocity_score >= 8:
            score += 1.0

        return min(round(score, 1), 9.8)

    def _generate_recommendation_summary(
        self, query: str, supplier, air, sea, market, score
    ) -> str:
        """نگارش توصیه تحلیلی هوشمند برای تصمیم‌گیری واردکننده"""
        if not supplier or not market:
            return "داده‌های کافی برای تحلیل جامع استخراج نشد."

        sea_roi = sea.roi_percent if sea else 0
        air_roi = air.roi_percent if air else 0

        best_method = "دریایی (به دلیل کاهش چشمگیر کرایه حمل و افزایش بازگشت سرمایه)" if sea_roi > air_roi + 15 else "هوایی (برای تست سریع بازار و دوره گردش سرمایه ۱۰ روزه)"

        return (
            f"کالای «{query}» با امتیاز فرصت {score} از ۱۰ ارزیابی می‌شود. "
            f"تامین مستقیم از کارخانه {supplier.name} در {supplier.location} "
            f"امکان ورود به بازار با حاشیه سود بین {min(air.profit_margin_percent if air else 0, sea.profit_margin_percent if sea else 0)}% "
            f"تا {max(air.profit_margin_percent if air else 0, sea.profit_margin_percent if sea else 0)}% را فراهم می‌سازد. "
            f"روش حمل پیشنهادی اولیه: {best_method}."
        )
