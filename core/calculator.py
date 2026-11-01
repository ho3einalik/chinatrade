"""
Landed Cost and Arbitrage Calculator for importing goods from China to Iran.
Implements exact Decimal-based monetary arithmetic, 3-scenario profit modeling
(Optimistic, Realistic, Pessimistic), full line-item attribution, volumetric weight,
dated regulatory rule versions, Incoterms adjustments, and break-even unit analysis.

قانون اصالت داده: در صورت نبود داده قیمت تأمین‌کننده یا قیمت بازار، به جای تولید اعداد فرضی،
وضعیت insufficient_data اعلام می‌گردد.
"""

from decimal import Decimal, ROUND_HALF_UP
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, field

from config import CONFIG, TradeConfig
from core.models import ChineseSupplier, LandedCostBreakdown, Incoterms

# Regulatory & Tariff rule version metadata
RULE_VERSION = "IR-CUSTOMS-1403-1404-V2"
RULE_DATE = "2026-03"
RULE_REFERENCE = "کتاب مقررات صادرات و واردات و احکام بودجه ۱۴۰۳-۱۴۰۴ (تخمینی تا زمان بررسی کتاب تعرفه قطعی کالا)"

@dataclass
class CostLineItem:
    category: str  # origin, freight, customs, clearance, logistics, financing, risk
    name_fa: str
    name_en: str
    amount_toman: Decimal
    percentage_of_total: Decimal
    notes: str = ""

@dataclass
class ScenarioResult:
    scenario_type: str  # optimistic, realistic, pessimistic
    scenario_title_fa: str
    exchange_rate_usd_toman: Decimal
    exchange_rate_rmb_toman: Decimal
    target_selling_price_toman: Decimal
    landed_cost_unit_toman: Decimal
    net_profit_unit_toman: Decimal
    margin_percent: Decimal
    markup_percent: Decimal
    roi_percent: Decimal
    break_even_price_toman: Decimal
    break_even_units: int
    total_investment_toman: Decimal
    total_net_profit_toman: Decimal
    line_items: List[CostLineItem] = field(default_factory=list)

@dataclass
class ComprehensiveLandedCostResult:
    rule_version: str
    rule_date: str
    batch_quantity: int
    shipping_method: str
    chargeable_weight_kg: Decimal
    volume_cbm: Decimal
    incoterms: str
    is_sufficient_data: bool
    data_notes: str
    
    # 3 Scenarios
    realistic: Optional[ScenarioResult]
    optimistic: Optional[ScenarioResult]
    pessimistic: Optional[ScenarioResult]
    
    # Sensitivity Summary
    fx_sensitivity_10pct_impact_toman: Decimal
    freight_sensitivity_20pct_impact_toman: Decimal

    def to_legacy_breakdown(self) -> LandedCostBreakdown:
        if not self.is_sufficient_data or not self.realistic:
            return LandedCostBreakdown(
                purchase_price_cny=0.0,
                purchase_price_toman=0.0,
                shipping_method=self.shipping_method,
                international_shipping_toman=0.0,
                customs_duty_toman=0.0,
                commercial_benefit_toman=0.0,
                vat_toman=0.0,
                clearance_and_brokerage_toman=0.0,
                domestic_logistics_toman=0.0,
                total_landed_cost_toman=0.0,
                target_selling_price_toman=0.0,
                net_profit_per_unit_toman=0.0,
                profit_margin_percent=0.0,
                roi_percent=0.0,
                break_even_price_toman=0.0,
                batch_quantity=self.batch_quantity,
                total_investment_toman=0.0,
                total_net_profit_toman=0.0
            )

        r = self.realistic
        purchase_item = next((i for i in r.line_items if i.category == "origin"), None)
        freight_item = next((i for i in r.line_items if i.category == "freight"), None)
        duty_item = next((i for i in r.line_items if i.name_en == "customs_duty"), None)
        benefit_item = next((i for i in r.line_items if i.name_en == "commercial_benefit"), None)
        vat_item = next((i for i in r.line_items if i.name_en == "vat"), None)
        clearance_item = next((i for i in r.line_items if i.category == "clearance"), None)
        logistics_item = next((i for i in r.line_items if i.category == "logistics"), None)

        return LandedCostBreakdown(
            purchase_price_cny=float(r.line_items[0].amount_toman / (r.exchange_rate_rmb_toman or Decimal(1))) if r.line_items else 0.0,
            purchase_price_toman=float(purchase_item.amount_toman) if purchase_item else 0.0,
            shipping_method=self.shipping_method,
            international_shipping_toman=float(freight_item.amount_toman) if freight_item else 0.0,
            customs_duty_toman=float(duty_item.amount_toman) if duty_item else 0.0,
            commercial_benefit_toman=float(benefit_item.amount_toman) if benefit_item else 0.0,
            vat_toman=float(vat_item.amount_toman) if vat_item else 0.0,
            clearance_and_brokerage_toman=float(clearance_item.amount_toman) if clearance_item else 0.0,
            domestic_logistics_toman=float(logistics_item.amount_toman) if logistics_item else 0.0,
            total_landed_cost_toman=float(r.landed_cost_unit_toman),
            target_selling_price_toman=float(r.target_selling_price_toman),
            net_profit_per_unit_toman=float(r.net_profit_unit_toman),
            profit_margin_percent=float(r.margin_percent),
            roi_percent=float(r.roi_percent),
            break_even_price_toman=float(r.break_even_price_toman),
            batch_quantity=self.batch_quantity,
            total_investment_toman=float(r.total_investment_toman),
            total_net_profit_toman=float(r.total_net_profit_toman)
        )

class ImportProfitCalculator:
    """
    High-precision Import Landed Cost & Profitability Calculator.
    All calculations are performed using pure Decimal arithmetic.
    """
    def __init__(self, config: Optional[TradeConfig] = None):
        self.config = config or CONFIG
        self.rule_version = RULE_VERSION
        self.rule_date = RULE_DATE

    @staticmethod
    def calculate_volumetric_weight(length_cm: float, width_cm: float, height_cm: float, divisor: int = 5000) -> Decimal:
        vol_cm3 = Decimal(str(length_cm)) * Decimal(str(width_cm)) * Decimal(str(height_cm))
        return (vol_cm3 / Decimal(str(divisor))).quantize(Decimal("0.001"), rounding=ROUND_HALF_UP)

    def calculate_chargeable_weight(
        self,
        actual_weight_kg: float,
        volume_cbm: float,
        shipping_method: str = "Air Cargo"
    ) -> Decimal:
        act_kg = Decimal(str(max(actual_weight_kg, 0.01)))
        cbm = Decimal(str(max(volume_cbm, 0.0001)))

        method_lower = shipping_method.lower()
        if "sea" in method_lower or "دریایی" in method_lower:
            weight_cbm_equiv = act_kg / Decimal("1000")
            return max(cbm, weight_cbm_equiv)
        else:
            volumetric_kg = (cbm * Decimal("167")).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            return max(act_kg, volumetric_kg)

    def compute_single_scenario(
        self,
        supplier: ChineseSupplier,
        target_iran_price_toman: Decimal,
        batch_qty: int,
        shipping_method: str,
        usd_rate: Decimal,
        rmb_rate: Decimal,
        air_usd_per_kg: Decimal,
        sea_usd_per_cbm: Decimal,
        tariff_pct: Decimal,
        benefit_pct: Decimal,
        vat_pct: Decimal,
        brokerage_pct: Decimal,
        domestic_logistics_pct: Decimal,
        remittance_fee_pct: Decimal,
        inspection_usd: Decimal,
        financing_months: int,
        annual_cost_of_capital_pct: Decimal,
        defect_scrap_rate_pct: Decimal,
        marketplace_fee_pct: Decimal,
        demurrage_reserve_toman: Decimal,
        scenario_type: str,
        scenario_title_fa: str,
        incoterms: Optional[Incoterms] = None
    ) -> ScenarioResult:
        # 1. Determine unit purchase in CNY
        unit_cny = Decimal(str(supplier.unit_price_cny))
        if supplier.price_tiers:
            for tier in sorted(supplier.price_tiers, key=lambda x: x.min_quantity, reverse=True):
                if batch_qty >= tier.min_quantity:
                    unit_cny = Decimal(str(tier.unit_price_cny))
                    break

        unit_purchase_toman = (unit_cny * rmb_rate).quantize(Decimal("1"), rounding=ROUND_HALF_UP)
        remittance_toman = (unit_purchase_toman * (remittance_fee_pct / Decimal("100"))).quantize(Decimal("1"), rounding=ROUND_HALF_UP)

        # Pre-shipment QC
        inspection_total_toman = inspection_usd * usd_rate
        inspection_unit_toman = (inspection_total_toman / Decimal(str(batch_qty))).quantize(Decimal("1"), rounding=ROUND_HALF_UP)

        # 2. International Freight & Origin Handling (Respect Incoterms)
        actual_incoterms = incoterms or (supplier.incoterms if hasattr(supplier, "incoterms") else Incoterms.EXW)
        is_sea = "sea" in shipping_method.lower() or "دریایی" in shipping_method.lower()
        
        # Origin handling for EXW terms (China domestic haulage + export customs)
        if actual_incoterms == Incoterms.EXW:
            unit_origin_handling_toman = (unit_purchase_toman * Decimal("0.02")).quantize(Decimal("1"), rounding=ROUND_HALF_UP)
        else:
            unit_origin_handling_toman = Decimal("0")

        if actual_incoterms == Incoterms.CIF:
            # CIF already includes international freight and insurance
            unit_freight_toman = Decimal("0")
            unit_insurance_toman = Decimal("0")
            c_and_f_toman = unit_purchase_toman
            cif_toman = unit_purchase_toman
        else:
            if is_sea:
                cbm = Decimal(str(max(supplier.volume_cbm, 0.0005)))
                freight_usd = cbm * sea_usd_per_cbm
                unit_freight_toman = (freight_usd * usd_rate).quantize(Decimal("1"), rounding=ROUND_HALF_UP)
            else:
                chargeable_kg = self.calculate_chargeable_weight(supplier.weight_kg, supplier.volume_cbm, shipping_method)
                freight_usd = chargeable_kg * air_usd_per_kg
                unit_freight_toman = (freight_usd * usd_rate).quantize(Decimal("1"), rounding=ROUND_HALF_UP)

            c_and_f_toman = unit_purchase_toman + unit_origin_handling_toman + unit_freight_toman
            unit_insurance_toman = (c_and_f_toman * Decimal("0.005")).quantize(Decimal("1"), rounding=ROUND_HALF_UP)
            cif_toman = c_and_f_toman + unit_insurance_toman

        # 3. Customs Duties & Taxes
        unit_customs_duty_toman = (cif_toman * (tariff_pct / Decimal("100"))).quantize(Decimal("1"), rounding=ROUND_HALF_UP)
        unit_commercial_benefit_toman = (cif_toman * (benefit_pct / Decimal("100"))).quantize(Decimal("1"), rounding=ROUND_HALF_UP)

        taxable_base = cif_toman + unit_customs_duty_toman + unit_commercial_benefit_toman
        unit_vat_toman = (taxable_base * (vat_pct / Decimal("100"))).quantize(Decimal("1"), rounding=ROUND_HALF_UP)

        # 4. Clearance, Demurrage & Destination Logistics
        unit_brokerage_toman = (cif_toman * (brokerage_pct / Decimal("100"))).quantize(Decimal("1"), rounding=ROUND_HALF_UP)
        unit_demurrage_toman = (demurrage_reserve_toman / Decimal(str(batch_qty))).quantize(Decimal("1"), rounding=ROUND_HALF_UP)
        unit_dest_logistics_toman = (cif_toman * (domestic_logistics_pct / Decimal("100"))).quantize(Decimal("1"), rounding=ROUND_HALF_UP)

        direct_landed_cost_toman = (
            unit_purchase_toman
            + unit_origin_handling_toman
            + remittance_toman
            + inspection_unit_toman
            + unit_freight_toman
            + unit_insurance_toman
            + unit_customs_duty_toman
            + unit_commercial_benefit_toman
            + unit_vat_toman
            + unit_brokerage_toman
            + unit_demurrage_toman
            + unit_dest_logistics_toman
        )

        # 5. Financing & Risk
        monthly_capital_rate = (annual_cost_of_capital_pct / Decimal("100")) / Decimal("12")
        unit_financing_cost_toman = (direct_landed_cost_toman * monthly_capital_rate * Decimal(str(financing_months))).quantize(Decimal("1"), rounding=ROUND_HALF_UP)
        unit_scrap_reserve_toman = (direct_landed_cost_toman * (defect_scrap_rate_pct / Decimal("100"))).quantize(Decimal("1"), rounding=ROUND_HALF_UP)

        total_landed_cost_toman = direct_landed_cost_toman + unit_financing_cost_toman + unit_scrap_reserve_toman

        # 6. Sales Commission & Net Profit
        unit_sales_commission_toman = (target_iran_price_toman * (marketplace_fee_pct / Decimal("100"))).quantize(Decimal("1"), rounding=ROUND_HALF_UP)
        effective_net_revenue_unit = target_iran_price_toman - unit_sales_commission_toman
        net_profit_unit_toman = effective_net_revenue_unit - total_landed_cost_toman

        margin_percent = Decimal("0.0")
        if target_iran_price_toman > Decimal("0"):
            margin_percent = ((net_profit_unit_toman / target_iran_price_toman) * Decimal("100")).quantize(Decimal("0.1"), rounding=ROUND_HALF_UP)

        markup_percent = Decimal("0.0")
        if total_landed_cost_toman > Decimal("0"):
            markup_percent = ((net_profit_unit_toman / total_landed_cost_toman) * Decimal("100")).quantize(Decimal("0.1"), rounding=ROUND_HALF_UP)

        roi_percent = markup_percent

        comm_ratio = Decimal("1") - (marketplace_fee_pct / Decimal("100"))
        break_even_price_toman = (total_landed_cost_toman / comm_ratio).quantize(Decimal("1"), rounding=ROUND_HALF_UP) if comm_ratio > Decimal("0") else total_landed_cost_toman

        total_investment_toman = total_landed_cost_toman * Decimal(str(batch_qty))
        total_net_profit_toman = net_profit_unit_toman * Decimal(str(batch_qty))

        fixed_batch_overhead = inspection_total_toman + demurrage_reserve_toman
        contribution_margin_per_unit = effective_net_revenue_unit - (unit_purchase_toman + unit_origin_handling_toman + remittance_toman + unit_freight_toman + unit_customs_duty_toman + unit_commercial_benefit_toman + unit_vat_toman)
        if contribution_margin_per_unit > Decimal("0"):
            break_even_units = int((fixed_batch_overhead / contribution_margin_per_unit).quantize(Decimal("1"), rounding=ROUND_HALF_UP))
            break_even_units = max(1, min(break_even_units, batch_qty))
        else:
            break_even_units = batch_qty

        tot = total_landed_cost_toman if total_landed_cost_toman > Decimal("0") else Decimal("1")
        line_items = [
            CostLineItem("origin", "خرید کالا از کارخانه چین", "purchase_price", unit_purchase_toman, ((unit_purchase_toman / tot) * Decimal("100")).quantize(Decimal("0.1"))),
            CostLineItem("origin", "حمل مبدأ و ترخیص صادراتی چین (EXW)", "china_origin_handling", unit_origin_handling_toman, ((unit_origin_handling_toman / tot) * Decimal("100")).quantize(Decimal("0.1"))),
            CostLineItem("origin", "کارمزد صرافی و حواله ارزی", "remittance_fee", remittance_toman, ((remittance_toman / tot) * Decimal("100")).quantize(Decimal("0.1"))),
            CostLineItem("origin", "بازرسی کالا قبل از بارگیری (QC)", "inspection_fee", inspection_unit_toman, ((inspection_unit_toman / tot) * Decimal("100")).quantize(Decimal("0.1"))),
            CostLineItem("freight", "کرایه حمل بین‌المللی", "international_freight", unit_freight_toman, ((unit_freight_toman / tot) * Decimal("100")).quantize(Decimal("0.1"))),
            CostLineItem("freight", "بیمه باربری بین‌المللی", "cargo_insurance", unit_insurance_toman, ((unit_insurance_toman / tot) * Decimal("100")).quantize(Decimal("0.1"))),
            CostLineItem("customs", "حقوق گمرکی", "customs_duty", unit_customs_duty_toman, ((unit_customs_duty_toman / tot) * Decimal("100")).quantize(Decimal("0.1"))),
            CostLineItem("customs", "سود بازرگانی", "commercial_benefit", unit_commercial_benefit_toman, ((unit_commercial_benefit_toman / tot) * Decimal("100")).quantize(Decimal("0.1"))),
            CostLineItem("customs", "مالیات بر ارزش افزوده (۱۰٪)", "vat", unit_vat_toman, ((unit_vat_toman / tot) * Decimal("100")).quantize(Decimal("0.1"))),
            CostLineItem("clearance", "ترخیص و کارگزاری گمرک", "clearance_brokerage", unit_brokerage_toman, ((unit_brokerage_toman / tot) * Decimal("100")).quantize(Decimal("0.1"))),
            CostLineItem("clearance", "ذخیره انبارداری و دموراژ", "demurrage_reserve", unit_demurrage_toman, ((unit_demurrage_toman / tot) * Decimal("100")).quantize(Decimal("0.1"))),
            CostLineItem("logistics", "حمل داخلی از گمرک تا انبار مقصد", "domestic_logistics", unit_dest_logistics_toman, ((unit_dest_logistics_toman / tot) * Decimal("100")).quantize(Decimal("0.1"))),
            CostLineItem("financing", "هزینه خواب سرمایه", "financing_cost", unit_financing_cost_toman, ((unit_financing_cost_toman / tot) * Decimal("100")).quantize(Decimal("0.1"))),
            CostLineItem("risk", "ذخیره ضایعات و مرجوعی", "defect_scrap_reserve", unit_scrap_reserve_toman, ((unit_scrap_reserve_toman / tot) * Decimal("100")).quantize(Decimal("0.1")))
        ]

        return ScenarioResult(
            scenario_type=scenario_type,
            scenario_title_fa=scenario_title_fa,
            exchange_rate_usd_toman=usd_rate,
            exchange_rate_rmb_toman=rmb_rate,
            target_selling_price_toman=target_iran_price_toman,
            landed_cost_unit_toman=total_landed_cost_toman,
            net_profit_unit_toman=net_profit_unit_toman,
            margin_percent=margin_percent,
            markup_percent=markup_percent,
            roi_percent=roi_percent,
            break_even_price_toman=break_even_price_toman,
            break_even_units=break_even_units,
            total_investment_toman=total_investment_toman,
            total_net_profit_toman=total_net_profit_toman,
            line_items=line_items
        )

    def calculate_landed_cost_scenarios(
        self,
        supplier: Optional[ChineseSupplier],
        target_iran_price_toman: Optional[float],
        shipping_method: str = "Air Cargo",
        incoterms: Optional[Incoterms] = None,
        customs_tariff_pct: Optional[float] = None,
        commercial_benefit_pct: Optional[float] = None,
        batch_quantity: Optional[int] = None,
        financing_months: int = 3,
        defect_scrap_rate_pct: float = 2.0,
        marketplace_fee_pct: float = 4.0
    ) -> ComprehensiveLandedCostResult:
        """
        Runs complete 3-scenario calculation.
        اگر تأمین‌کننده یا قیمت بازار موجود نباشد، وضعیت is_sufficient_data=False برمی‌گرداند.
        """
        effective_incoterms = incoterms or (supplier.incoterms if supplier and hasattr(supplier, "incoterms") else Incoterms.EXW)

        # شرط اصالت داده: در صورت عدم وجود داده، از تولید سود ساختگی جلوگیری می‌شود
        if not supplier or target_iran_price_toman is None or target_iran_price_toman <= 0 or supplier.unit_price_cny <= 0:
            return ComprehensiveLandedCostResult(
                rule_version=self.rule_version,
                rule_date=self.rule_date,
                batch_quantity=batch_quantity or 100,
                shipping_method=shipping_method,
                chargeable_weight_kg=Decimal("0"),
                volume_cbm=Decimal("0"),
                incoterms=effective_incoterms.value if hasattr(effective_incoterms, "value") else str(effective_incoterms),
                is_sufficient_data=False,
                data_notes="داده‌های لازم (قیمت تأمین‌کننده یا قیمت فروش در ایران) ناکافی است. هیچ سود یا هزینه‌ای محاسبه نشد.",
                realistic=None,
                optimistic=None,
                pessimistic=None,
                fx_sensitivity_10pct_impact_toman=Decimal("0"),
                freight_sensitivity_20pct_impact_toman=Decimal("0")
            )

        qty = batch_quantity if batch_quantity is not None else max(supplier.moq, 100)
        target_price = Decimal(str(round(target_iran_price_toman)))
        
        base_usd = Decimal(str(self.config.USD_TO_TOMAN))
        base_rmb = Decimal(str(self.config.RMB_TO_TOMAN))
        air_usd = Decimal(str(self.config.AIR_FREIGHT_USD_PER_KG))
        sea_usd = Decimal(str(self.config.SEA_FREIGHT_USD_PER_CBM))
        tariff = Decimal(str(customs_tariff_pct if customs_tariff_pct is not None else self.config.DEFAULT_CUSTOMS_TARIFF_PERCENT))
        benefit = Decimal(str(commercial_benefit_pct if commercial_benefit_pct is not None else self.config.DEFAULT_COMMERCIAL_BENEFIT_PERCENT))
        vat = Decimal(str(self.config.VAT_PERCENT))
        brokerage = Decimal(str(self.config.CLEARANCE_BROKERAGE_PERCENT))
        logistics = Decimal(str(self.config.DOMESTIC_LOGISTICS_PERCENT))
        remittance = Decimal("1.5")
        inspection_usd = Decimal("150")
        cost_of_capital = Decimal("24.0")

        realistic = self.compute_single_scenario(
            supplier=supplier,
            target_iran_price_toman=target_price,
            batch_qty=qty,
            shipping_method=shipping_method,
            usd_rate=base_usd,
            rmb_rate=base_rmb,
            air_usd_per_kg=air_usd,
            sea_usd_per_cbm=sea_usd,
            tariff_pct=tariff,
            benefit_pct=benefit,
            vat_pct=vat,
            brokerage_pct=brokerage,
            domestic_logistics_pct=logistics,
            remittance_fee_pct=remittance,
            inspection_usd=inspection_usd,
            financing_months=financing_months,
            annual_cost_of_capital_pct=cost_of_capital,
            defect_scrap_rate_pct=Decimal(str(defect_scrap_rate_pct)),
            marketplace_fee_pct=Decimal(str(marketplace_fee_pct)),
            demurrage_reserve_toman=Decimal("5000000"),
            scenario_type="realistic",
            scenario_title_fa="حالت واقع‌بینانه (Realistic)",
            incoterms=effective_incoterms
        )

        opt_usd = (base_usd * Decimal("0.96")).quantize(Decimal("1"))
        opt_rmb = (base_rmb * Decimal("0.96")).quantize(Decimal("1"))
        opt_price = (target_price * Decimal("1.05")).quantize(Decimal("1"))
        optimistic = self.compute_single_scenario(
            supplier=supplier,
            target_iran_price_toman=opt_price,
            batch_qty=qty,
            shipping_method=shipping_method,
            usd_rate=opt_usd,
            rmb_rate=opt_rmb,
            air_usd_per_kg=(air_usd * Decimal("0.95")),
            sea_usd_per_cbm=(sea_usd * Decimal("0.95")),
            tariff_pct=tariff,
            benefit_pct=benefit,
            vat_pct=vat,
            brokerage_pct=(brokerage * Decimal("0.9")),
            domestic_logistics_pct=logistics,
            remittance_fee_pct=Decimal("1.0"),
            inspection_usd=Decimal("100"),
            financing_months=max(1, financing_months - 1),
            annual_cost_of_capital_pct=cost_of_capital,
            defect_scrap_rate_pct=Decimal("1.0"),
            marketplace_fee_pct=Decimal(str(marketplace_fee_pct)),
            demurrage_reserve_toman=Decimal("2000000"),
            scenario_type="optimistic",
            scenario_title_fa="حالت خوش‌بینانه (Optimistic)",
            incoterms=effective_incoterms
        )

        pess_usd = (base_usd * Decimal("1.10")).quantize(Decimal("1"))
        pess_rmb = (base_rmb * Decimal("1.10")).quantize(Decimal("1"))
        pess_price = (target_price * Decimal("0.92")).quantize(Decimal("1"))
        pessimistic = self.compute_single_scenario(
            supplier=supplier,
            target_iran_price_toman=pess_price,
            batch_qty=qty,
            shipping_method=shipping_method,
            usd_rate=pess_usd,
            rmb_rate=pess_rmb,
            air_usd_per_kg=(air_usd * Decimal("1.20")),
            sea_usd_per_cbm=(sea_usd * Decimal("1.20")),
            tariff_pct=tariff,
            benefit_pct=benefit,
            vat_pct=vat,
            brokerage_pct=(brokerage * Decimal("1.25")),
            domestic_logistics_pct=(logistics * Decimal("1.15")),
            remittance_fee_pct=Decimal("2.0"),
            inspection_usd=Decimal("200"),
            financing_months=financing_months + 2,
            annual_cost_of_capital_pct=cost_of_capital,
            defect_scrap_rate_pct=Decimal("4.0"),
            marketplace_fee_pct=Decimal(str(marketplace_fee_pct)),
            demurrage_reserve_toman=Decimal("15000000"),
            scenario_type="pessimistic",
            scenario_title_fa="حالت بدبینانه (Pessimistic)",
            incoterms=effective_incoterms
        )

        fx_impact = (realistic.landed_cost_unit_toman * Decimal("0.085")).quantize(Decimal("1"))
        freight_impact = (realistic.line_items[3].amount_toman * Decimal("0.20")).quantize(Decimal("1"))
        chargeable_kg = self.calculate_chargeable_weight(supplier.weight_kg, supplier.volume_cbm, shipping_method)
        cbm = Decimal(str(supplier.volume_cbm)).quantize(Decimal("0.0001"))

        return ComprehensiveLandedCostResult(
            rule_version=self.rule_version,
            rule_date=self.rule_date,
            batch_quantity=qty,
            shipping_method=shipping_method,
            chargeable_weight_kg=chargeable_kg,
            volume_cbm=cbm,
            incoterms=effective_incoterms.value if hasattr(effective_incoterms, "value") else str(effective_incoterms),
            is_sufficient_data=True,
            data_notes="محاسبه کامل بر مبنای قیمت واقعی و نرخ‌های پیکربندی‌شده",
            realistic=realistic,
            optimistic=optimistic,
            pessimistic=pessimistic,
            fx_sensitivity_10pct_impact_toman=fx_impact,
            freight_sensitivity_20pct_impact_toman=freight_impact
        )

    def calculate_landed_cost(
        self,
        supplier: Optional[ChineseSupplier],
        target_iran_price_toman: Optional[float],
        shipping_method: str = "Air Cargo",
        customs_tariff_pct: Optional[float] = None,
        commercial_benefit_pct: Optional[float] = None,
        batch_quantity: Optional[int] = None,
    ) -> LandedCostBreakdown:
        comp = self.calculate_landed_cost_scenarios(
            supplier=supplier,
            target_iran_price_toman=target_iran_price_toman,
            shipping_method=shipping_method,
            customs_tariff_pct=customs_tariff_pct,
            commercial_benefit_pct=commercial_benefit_pct,
            batch_quantity=batch_quantity
        )
        return comp.to_legacy_breakdown()
