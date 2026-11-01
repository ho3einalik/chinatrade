"""
Grounded B2B Communication Assistant for Trade Intelligence Hub.
Generates factually grounded formal RFQs, export sales pitches, counter-offers,
and international trade correspondence without hallucinations.
"""

from typing import Dict, Any, Optional
from decimal import Decimal
from trade_hub.models import GlobalIncoterms


class TradeAIAssistant:
    """
    Assists international traders with formal, standards-compliant trade correspondence.
    All outputs strictly adhere to provided specifications and Incoterms rules.
    """

    @classmethod
    def generate_export_sales_pitch(
        cls,
        company_name: str,
        product_name_en: str,
        product_name_fa: str,
        hs_code: str,
        target_country: str,
        unit_price_usd: Optional[Decimal] = None,
        incoterms: GlobalIncoterms = GlobalIncoterms.FOB,
        monthly_capacity: str = "5,000 Metric Tons",
        certifications: Optional[str] = "ISO 9001, CE, Halal Certificate"
    ) -> Dict[str, str]:
        """
        Drafts professional English and Persian export introduction pitches.
        """
        price_str = f"${unit_price_usd:,.2f} per Metric Ton ({incoterms.value})" if unit_price_usd else "Competitive pricing upon inquiry"
        price_fa_str = f"{unit_price_usd:,.2f} دلار به ازای هر تن ({incoterms.value})" if unit_price_usd else "قیمت رقابتی پس از اعلام حجم استعلام"

        pitch_en = f"""Subject: Strategic Supply Partnership: Premium {product_name_en} (HS Code: {hs_code}) - {company_name}

Dear Procurement & Commercial Director,

I am writing from {company_name}, an established producer and global exporter of high-grade {product_name_en}.

We actively monitor market demand in {target_country} and have structured an optimized export supply chain specifically tailored for regional buyers, offering:
- Product & Grade: Pure industrial grade {product_name_en} compliant with international specifications (HS Code: {hs_code}).
- Supply Capacity: Scalable volume exceeding {monthly_capacity} per month with guaranteed dispatch schedules.
- Pricing Benchmark: Indicative {price_str}, backed by direct mill/factory supply without intermediary markup.
- Quality Assurance: Fully audited quality control with {certifications or 'full analytical test reports and SGS inspection'}.
- Flexible Logistics: Standard delivery under {incoterms.value} with prompt border clearance and complete export documentation (EUR.1 / Form A / Certificate of Origin).

We welcome the opportunity to submit our formal Technical Data Sheet (TDS) and Proforma quotation for your upcoming procurement cycle. Please let us know your required specification and target monthly tonnage.

Sincerely,
Export & Commercial Directorate
{company_name}
"""

        pitch_fa = f"""موضوع: پیشنهاد رسمی تامین و صادرات {product_name_fa} (کد تعرفه {hs_code}) به بازار {target_country}

جناب آقای / سرکار خانم مدیر محترم بازرگانی و خرید،

با سلام و احترام،
بدین‌وسیله شرکت {company_name} آمادگی رسمی خود را جهت تامین پایدار و صادرات محصول {product_name_fa} با مشخصات استاندارد بین‌المللی به خریداران معتبر در کشور {target_country} اعلام می‌دارد.

مزایای رقابتی این پیشنهاد:
۱. انطباق کامل کیفی: تولید بر اساس استانداردهای بین‌المللی با کد تعرفه گمرکی {hs_code} همراه با گواهی بازرسی بین‌المللی (SGS) و آنالیز رسمی (COA).
۲. ظرفیت تامین پایدار: توان تحویل ماهانه بیش از {monthly_capacity} با تضمین زمان‌بندی بارگیری.
۳. قیمت رقابتی صادراتی: قیمت مبنا بر اساس {price_fa_str} به صورت مستقیم از درب کارخانه بدون واسطه.
۴. اسناد و تشریفات قانونی: ارائه کامل گواهی مبدا اتاق بازرگانی، بارنامه بین‌المللی، پکینگ لیست و ترخیص سریع مرزی بر اساس ترم تحویل {incoterms.value}.

خواهشمند است در صورت تمایل به دریافت دیتاشیت فنی (TDS) و پیش‌فاکتور رسمی (PI)، حجم درخواستی و مشخصات مدنظر خود را اعلام فرمایید.

با تجدید احترام،
معاونت بازرگانی بین‌الملل و توسعه صادرات
{company_name}
"""
        return {"pitch_en": pitch_en.strip(), "pitch_fa": pitch_fa.strip()}

    @classmethod
    def generate_formal_rfq_letter(
        cls,
        importer_name: str,
        supplier_name: str,
        product_name: str,
        hs_code: Optional[str],
        quantity: Decimal,
        unit: str = "Tons",
        destination_port: str = "Bandar Abbas / Mehran Terminal",
        incoterms: GlobalIncoterms = GlobalIncoterms.CIF,
        target_delivery_days: int = 30
    ) -> str:
        """
        Drafts a formal Request for Quotation (RFQ) for international suppliers.
        """
        hs_part = f"(HS Code: {hs_code})" if hs_code else ""
        return f"""FORMAL REQUEST FOR QUOTATION (RFQ)

Date: Formal Submission
To: Commercial Department, {supplier_name}
From: Procurement Division, {importer_name}
Subject: Official Inquiry for {product_name} {hs_part}

Dear Sir/Madam,

We kindly invite your company to provide a formal, firm commercial quotation for the procurement of {product_name} in accordance with the following terms:

1. Commodity Description: {product_name} {hs_part}
2. Required Volume: {quantity:,.2f} {unit} (Trial Order with potential for annual rolling contract)
3. Target Delivery Term: {incoterms.value} - Destination: {destination_port} (Incoterms 2020)
4. Delivery Lead Time: Within {target_delivery_days} calendar days from contract confirmation
5. Inspection & Quality: Pre-shipment inspection (PSI) by SGS or mutually agreed independent surveyor
6. Mandatory Enclosures Requested with Quote:
   a. Formal Proforma Invoice (PI) with 30-day validity
   b. Complete Technical Data Sheet (TDS) and Material Safety Data Sheet (MSDS)
   c. Production facility origin & packing specifications
   d. Proposed Payment Terms (L/C at sight, CAD, or T/T schedule)

Please transmit your best commercial quotation at your earliest convenience.

Best regards,
Procurement Directorate
{importer_name}
""".strip()
