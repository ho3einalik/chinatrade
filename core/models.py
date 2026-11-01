"""
Pydantic Data models for China-to-Iran Import Intelligence & Arbitrage Agent.
Includes strict data provenance, data types, freshness, Incoterms, and verification metadata.
"""

from enum import Enum
from typing import List, Optional, Dict, Any
from datetime import datetime, timezone
from pydantic import BaseModel, Field

class DataType(str, Enum):
    LIVE_API = "live_api"
    LIVE_SCRAPE = "live_scrape"
    MANUAL_QUOTE = "manual_quote"
    CSV_IMPORT = "csv_import"
    ESTIMATE = "estimate"
    DEMO = "demo"

class DataFreshness(str, Enum):
    FRESH = "fresh"          # استعلام تازه (کمتر از ۲۴ ساعت)
    STALE = "stale"          # قدیمی‌تر از آستانه استاندارد (نیازمند استعلام مجدد)
    EXPIRED = "expired"      # منقضی‌شده و غیرقابل استناد
    UNAVAILABLE = "unavailable" # در دسترس نیست

class Incoterms(str, Enum):
    EXW = "EXW"  # تحویل درب کارخانه در چین
    FOB = "FOB"  # تحویل روی عرشه کشتی/فرودگاه در مبدأ چین
    CIF = "CIF"  # تحویل با احتساب کرایه و بیمه تا گمرک مقصد ایران
    DDP = "DDP"  # تحویل در انبار مقصد با ترخیص قطعی
    UNKNOWN = "UNKNOWN"

class VerificationStatus(str, Enum):
    VERIFIED_WITH_DOCS = "verified_with_docs" # تأییدشده با مدارک رسمی و پیش‌فاکتور
    UNVERIFIED = "unverified"                 # تأییدنشده (صرفاً پروفایل عمومی)
    INCOMPLETE = "incomplete"                 # اطلاعات ناقص
    WARNING = "warning"                       # دارای پرچم قرمز و هشدار ریسک
    MANUAL_OVERRIDE = "manual_override"       # واردشده دستی توسط کاربر

class ComponentStatus(str, Enum):
    REAL_VERIFIED = "REAL_VERIFIED"     # استعلام زنده یا پیش‌فاکتور واقعی
    USER_MANUAL = "USER_MANUAL"         # قیمت واردشده توسط کاربر
    ESTIMATED = "ESTIMATED"             # تخمینی بر اساس الگوها و مراجع صنعتی
    UNAVAILABLE = "UNAVAILABLE"         # ناموجود

class DataProvenanceBreakdown(BaseModel):
    supplier_price_status: str = Field(default="UNAVAILABLE", description="وضعیت قیمت تأمین‌کننده: REAL_VERIFIED, USER_MANUAL, ESTIMATED, UNAVAILABLE")
    supplier_price_source: str = Field(default="نامشخص", description="منبع قیمت تأمین‌کننده")
    supplier_price_value: Optional[float] = None
    supplier_currency: str = "CNY"
    
    iran_market_status: str = Field(default="UNAVAILABLE", description="وضعیت قیمت بازار ایران: REAL_VERIFIED, USER_MANUAL, ESTIMATED, UNAVAILABLE")
    iran_market_source: str = Field(default="نامشخص", description="منبع قیمت بازار ایران")
    iran_market_value_toman: Optional[float] = None
    iran_sellers_count: int = 0
    
    shipping_cost_status: str = Field(default="ESTIMATED", description="وضعیت کرایه حمل: ESTIMATED, REAL_VERIFIED")
    shipping_cost_source: str = Field(default="نرخ‌نامه مرجع لجستیک هوایی و کانتینری", description="منبع محاسبه کرایه حمل")
    
    customs_tariff_status: str = Field(default="REAL_VERIFIED", description="وضعیت تعرفه گمرکی: REAL_VERIFIED")
    customs_tariff_source: str = Field(default="کتاب مقررات صادرات و واردات سال جاری", description="منبع تعرفه و ضوابط ورود")
    hs_code: str = Field(default="نامشخص", description="کد تعرفه HS")
    
    last_updated_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat(), description="زمان آخرین به‌روزرسانی")
    
    is_definite_profit_ready: bool = Field(default=False, description="آیا داده‌های قطعی برای سود قرارداد آماده است")
    missing_for_definite: List[str] = Field(default_factory=list, description="اقلام کمبود برای محاسبه سود قطعی")
    calculation_mode: str = Field(default="SCENARIO_SIMULATION", description="حالت محاسبه: DEFINITE_CONTRACT, SCENARIO_SIMULATION, DISCOVERY_ONLY")

class PriceTier(BaseModel):
    min_quantity: int = Field(..., description="حداقل تعداد برای این پله قیمتی")
    unit_price_cny: float = Field(..., description="قیمت هر واحد به یوان")
    unit_price_usd: Optional[float] = None

class ChineseSupplier(BaseModel):
    name: str = Field(..., description="نام کارخانه یا تامین‌کننده")
    platform: str = Field(..., description="پلتفرم سورسینگ: Alibaba, 1688, AliExpress, EHSY, Gongchang, Makepolo, QiPeiRen, ChemNet, YiwuGo, Baidu B2B, Manual")
    product_title: str = Field(..., description="عنوان محصول در سایت چینی")
    product_specs: Dict[str, Any] = Field(default_factory=dict, description="مشخصات فنی و پکیجینگ")
    unit_price_cny: float = Field(..., description="پایین‌ترین یا مناسب‌ترین قیمت به یوان")
    unit_price_usd: Optional[float] = None
    price_tiers: List[PriceTier] = Field(default_factory=list, description="پلکان قیمت بر اساس تیراژ")
    moq: int = Field(default=1, description="حداقل تیراژ سفارش (MOQ)")
    supplier_tier: str = Field(default="Unverified Profile", description="رتبه و نشان اعتبار تامین‌کننده")
    years_active: int = Field(default=1, description="سابقه فعالیت کارخانه به سال")
    location: str = Field(default="China", description="شهر و استان محل استقرار کارخانه")
    certifications: List[str] = Field(default_factory=list, description="گواهی‌های بین‌المللی: CE, RoHS, ISO9001")
    lead_time_days: int = Field(default=10, description="مدت زمان تولید و تحویل")
    weight_kg: float = Field(default=0.2, description="وزن ناخالص هر واحد (کیلوگرم)")
    volume_cbm: float = Field(default=0.001, description="حجم هر واحد (متر مکعب)")
    source_url: str = Field(default="", description="لینک به صفحه کارخانه/محصول یا پیش‌فاکتور")
    
    # --- Provenance & Data Quality Metadata ---
    data_type: DataType = Field(default=DataType.MANUAL_QUOTE, description="نوع داده: live_api, manual_quote, csv_import, demo, estimate")
    incoterms: Incoterms = Field(default=Incoterms.EXW, description="شرایط تحویل: EXW, FOB, CIF")
    fetch_time_utc: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat(), description="زمان ثبت داده به UTC")
    freshness: DataFreshness = Field(default=DataFreshness.FRESH, description="وضعیت تازگی داده")
    verification_status: VerificationStatus = Field(default=VerificationStatus.UNVERIFIED, description="وضعیت اعتبارسنجی مدارک")
    confidence_level: str = Field(default="UNVERIFIED", description="سطح اطمینان داده")
    is_demo: bool = Field(default=False, description="آیا داده صرفاً نمونه آموزشی است")
    notes: str = Field(default="", description="یادداشت‌های اصالت داده و منبع")

class IranMarketChannel(BaseModel):
    name: str = Field(..., description="نام کانال فروش: دیجی‌کالا، ترب، ایمالز، باسلام، فروشگاه‌های تخصصی، دیوار")
    price_toman: Optional[float] = Field(default=None, description="قیمت در این کانال (در صورت نبود داده زنده یا دستی: None)")
    price_label: str = Field(default="", description="توضیح نوع قیمت: کف قیمت، تک‌فروشی، عمده")
    url: str = Field(default="", description="لینک جستجو یا کالا")
    is_live: bool = Field(default=False, description="آیا استعلام زنده موفق از این کانال انجام شده است")
    data_type: DataType = Field(default=DataType.ESTIMATE, description="نوع داده")
    channel_type: str = Field(default="search_link", description="نوع کانال: live_api, search_link, manual_entry")
    fetch_time_utc: Optional[str] = None

class IranMarketPrice(BaseModel):
    platform: str = Field(..., description="پلتفرم ایرانی: ترب، دیجی‌کالا، ایمالز، باسلام، دیوار، بازار عمده")
    title_fa: str = Field(..., description="نام کالا در بازار ایران")
    lowest_price_toman: Optional[float] = Field(default=None, description="پایین‌ترین قیمت فروش در بازار (تومان)")
    average_price_toman: Optional[float] = Field(default=None, description="میانگین قیمت فروش (تومان)")
    highest_price_toman: Optional[float] = Field(default=None, description="بالاترین قیمت فروش (تومان)")
    active_sellers_count: int = Field(default=0, description="تعداد فروشندگان فعال")
    sales_velocity_score: int = Field(default=5, description="امتیاز تخمینی سرعت فروش و تقاضا از 10")
    source_url: str = Field(default="", description="لینک به صفحه محصول در ترب یا دیجی‌کالا")
    channels: List[IranMarketChannel] = Field(default_factory=list, description="تفکیک قیمت در کانال‌های مختلف فروش ایران")
    sample_products: List[Dict[str, Any]] = Field(default_factory=list, description="نمونه کالاهای یافت‌شده در بازار")
    status: str = Field(default="available", description="وضعیت داده: available, unavailable, no_results, insufficient_data")
    data_type: DataType = Field(default=DataType.LIVE_API, description="نوع داده بازار ایران")
    freshness: DataFreshness = Field(default=DataFreshness.FRESH, description="وضعیت تازگی داده")
    fetch_time_utc: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat(), description="زمان دریافت داده")

class LandedCostBreakdown(BaseModel):
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
    
    target_selling_price_toman: float = Field(..., description="قیمت هدف فروش در ایران")
    net_profit_per_unit_toman: float = Field(..., description="سود خالص هر واحد")
    profit_margin_percent: float = Field(..., description="حاشیه سود خالص (درصد)")
    roi_percent: float = Field(..., description="نرخ بازگشت سرمایه (ROI %)")
    break_even_price_toman: float = Field(..., description="حداقل قیمت فروش بدون ضرر")
    
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
    
    opportunity_score: float = Field(default=5.0, description="امتیاز جذابیت فرصت تجاری از 10")
    recommendation_summary: str = Field(default="", description="خلاصه توصیه بازرگانی و استراتژی ورود")
    insufficient_data: bool = Field(default=False, description="آیا داده‌های واقعی برای تحلیل کامل ناکافی است")
    data_provenance: Optional[DataProvenanceBreakdown] = Field(default=None, description="شناسنامه تفکیک‌شده اصالت و وضعیت مؤلفه‌های داده")
    is_simulation: bool = Field(default=False, description="آیا محاسبات سناریوی شبیه‌سازی است")
    definite_profit_calculable: bool = Field(default=False, description="آیا سود قطعی قرارداد قابل محاسبه است")
    missing_requirements: List[str] = Field(default_factory=list, description="موارد لازم جهت محاسبه سود قطعی")
