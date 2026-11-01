"""
Core AI Import Intelligence & Arbitrage Agent for China-to-Iran Trade.
Orchestrates Chinese factory sourcing, Iranian market benchmarking, landed cost math,
regulatory risk assessment, and executive opportunity discovery.
"""

from typing import List, Optional, Dict, Any
from config import CONFIG, TradeConfig
from core.models import ImportOpportunityReport, ChineseSupplier, IranMarketPrice
from core.china_sourcing import ChinaSourcingEngine
from core.iran_market import IranMarketEngine
from core.calculator import ImportProfitCalculator

class ChinaIranImportAgent:
    def __init__(self, config: Optional[TradeConfig] = None):
        self.config = config or CONFIG
        self.sourcing_engine = ChinaSourcingEngine()
        self.market_engine = IranMarketEngine()
        self.calculator = ImportProfitCalculator(self.config)

    def analyze_product(
        self,
        product_query: str,
        category: Optional[str] = None,
        custom_target_iran_price: Optional[float] = None,
        batch_quantity: Optional[int] = None
    ) -> ImportOpportunityReport:
        """
        تحلیل جامع ۳۶۰ درجه یک کالا:
        ۱. یافتن کارخانه‌ها و قیمت‌های چین در ۱۶۸۸، علی‌بابا، Made-in-China، ChemNet
        ۲. استخراج قیمت‌های رقبا در بازار ایران (ترب، دیجی‌کالا، بازار آزاد)
        ۳. محاسبه بهای تمام‌شده گمرکی، هوایی، دریایی و سود خالص
        ۴. تعیین HS Code و مجوزهای الزامی گمرک
        ۵. ارزیابی ریسک و امتیاز فرصت تجاری
        """
        # ۱. استخراج تامین‌کنندگان چین
        suppliers = self.sourcing_engine.search_suppliers(product_query, category)
        best_supplier = suppliers[0] if suppliers else None

        # ۲. استخراج قیمت در بازار ایران
        iran_market = self.market_engine.analyze_iran_market(product_query, custom_target_iran_price)

        # تعیین قیمت فروش هدف (معمولاً میانگین بازار یا کمی کمتر برای رقابت‌پذیری بالا)
        target_sell_price = custom_target_iran_price or iran_market.average_price_toman

        # ۳. محاسبات دقیق مالی (هوایی و دریایی)
        air_analysis = None
        sea_analysis = None

        if best_supplier:
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

        # ۴. تخمین کد تعرفه گمرکی (HS Code) و الزامات رگولاتوری
        hs_code, regulations, detected_category = self._determine_customs_and_regulations(product_query)

        # ۵. محاسبه امتیاز جذابیت فرصت (Opportunity Score) از ۱۰
        opp_score = self._calculate_opportunity_score(air_analysis, sea_analysis, iran_market)

        # ۶. خلاصه استراتژیک برای واردکننده
        summary = self._generate_recommendation_summary(
            product_query, best_supplier, air_analysis, sea_analysis, iran_market, opp_score
        )

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
            recommendation_summary=summary
        )

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
