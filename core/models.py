"""
Pydantic Data models for China-to-Iran Import Intelligence & Arbitrage Agent.
"""

from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field

class PriceTier(BaseModel):
    min_quantity: int = Field(..., description="حداقل تعداد برای این پله قیمتی")
    unit_price_cny: float = Field(..., description="قیمت هر واحد به یوان")
    unit_price_usd: Optional[float] = None

class ChineseSupplier(BaseModel):
    name: str = Field(..., description="نام کارخانه یا تامین‌کننده")
    platform: str = Field(..., description="پلتفرم سورسینگ: 1688, EHSY, Gongchang, Makepolo, QiPeiRen, Alibaba, ChemNet, YiwuGo, Baidu B2B")
    product_title: str = Field(..., description="عنوان محصول در سایت چینی")
    product_specs: Dict[str, Any] = Field(default_factory=dict, description="مشخصات فنی و پکیجینگ")
    unit_price_cny: float = Field(..., description="پایین‌ترین یا مناسب‌ترین قیمت به یوان")
    unit_price_usd: Optional[float] = None
    price_tiers: List[PriceTier] = Field(default_factory=list, description="پلکان قیمت بر اساس تیراژ")
    moq: int = Field(default=1, description="حداقل تیراژ سفارش (MOQ)")
    supplier_tier: str = Field(default="Verified Factory", description="رتبه و نشان اعتبار تامین‌کننده")
    years_active: int = Field(default=3, description="سابقه فعالیت کارخانه به سال")
    location: str = Field(default="Guangdong, China", description="شهر و استان محل استقرار کارخانه")
    certifications: List[str] = Field(default_factory=list, description="گواهی‌های بین‌المللی: CE, RoHS, ISO9001")
    lead_time_days: int = Field(default=10, description="مدت زمان تولید و تحویل")
    weight_kg: float = Field(default=0.2, description="وزن ناخالص هر واحد (کیلوگرم)")
    volume_cbm: float = Field(default=0.001, description="حجم هر واحد (متر مکعب)")
    source_url: str = Field(default="", description="لینک به صفحه کارخانه/محصول")

class IranMarketChannel(BaseModel):
    name: str = Field(..., description="نام کانال فروش: دیجی‌کالا، ترب، ایمالز، باسلام، فروشگاه‌های تخصصی، دیوار")
    price_toman: float = Field(..., description="قیمت تخمینی یا زنده در این کانال")
    price_label: str = Field(default="", description="توضیح نوع قیمت: کف قیمت، تک‌فروشی، عمده")
    url: str = Field(default="", description="لینک جستجو یا کالا")
    is_live: bool = Field(default=False, description="آیا استعلام زنده انجام شده است")

class IranMarketPrice(BaseModel):
    platform: str = Field(..., description="پلتفرم ایرانی: ترب، دیجی‌کالا، ایمالز، باسلام، دیوار، بازار عمده")
    title_fa: str = Field(..., description="نام کالا در بازار ایران")
    lowest_price_toman: float = Field(..., description="پایین‌ترین قیمت فروش در بازار (تومان)")
    average_price_toman: float = Field(..., description="میانگین قیمت فروش (تومان)")
    highest_price_toman: float = Field(..., description="بالاترین قیمت فروش (تومان)")
    active_sellers_count: int = Field(default=1, description="تعداد فروشندگان فعال")
    sales_velocity_score: int = Field(default=7, description="امتیاز تخمینی سرعت فروش و تقاضا از 10")
    source_url: str = Field(default="", description="لینک به صفحه محصول در ترب یا دیجی‌کالا")
    channels: List[IranMarketChannel] = Field(default_factory=list, description="تفکیک قیمت در کانال‌های مختلف فروش ایران")
    sample_products: List[Dict[str, Any]] = Field(default_factory=list, description="نمونه کالاهای یافت‌شده در بازار")

class LandedCostBreakdown(BaseModel):
    # مقادیر به ازای هر واحد
    purchase_price_cny: float
    purchase_price_toman: float
    shipping_method: str = Field(default="Air Cargo", description="روش حمل: Air Cargo یا Sea Freight")
    international_shipping_toman: float
    customs_duty_toman: float
    commercial_benefit_toman: float
    vat_toman: float
    clearance_and_brokerage_toman: float
    domestic_logistics_toman: float
    total_landed_cost_toman: float = Field(..., description="بهای تمام‌شده کل در انبار ایران (تومان)")
    
    # تحلیل سودآوری در ایران
    target_selling_price_toman: float = Field(..., description="قیمت هدف فروش در ایران")
    net_profit_per_unit_toman: float = Field(..., description="سود خالص هر واحد")
    profit_margin_percent: float = Field(..., description="حاشیه سود خالص (درصد)")
    roi_percent: float = Field(..., description="نرخ بازگشت سرمایه (ROI %)")
    break_even_price_toman: float = Field(..., description="حداقل قیمت فروش بدون ضرر")
    
    # برای کل بچ سفارش
    batch_quantity: int = Field(default=500, description="تعداد کل سفارش در این پارت")
    total_investment_toman: float = 0.0
    total_net_profit_toman: float = 0.0

class ImportOpportunityReport(BaseModel):
    product_name_fa: str = Field(..., description="نام فارسی کالا")
    product_name_en: str = Field(..., description="نام انگلیسی کالا")
    category: str = Field(..., description="دسته‌بندی (گجت، پتروشیمی، خودرو، ابزار، خانگی)")
    hs_code_estimate: str = Field(default="8517.62.90", description="کد تعرفه تخمینی گمرکی HS Code")
    regulatory_notes: List[str] = Field(default_factory=list, description="مجوزهای الزامی: صمت، استاندارد، بهداشت")
    
    suppliers_china: List[ChineseSupplier] = Field(default_factory=list, description="تامین‌کنندگان منتخب چین")
    best_supplier: Optional[ChineseSupplier] = None
    
    iran_market: Optional[IranMarketPrice] = None
    
    air_cost_analysis: Optional[LandedCostBreakdown] = None
    sea_cost_analysis: Optional[LandedCostBreakdown] = None
    
    opportunity_score: float = Field(default=8.5, description="امتیاز جذابیت فرصت واردات از 10")
    recommendation_summary: str = Field(default="", description="خلاصه توصیه بازرگانی و استراتژی ورود")
