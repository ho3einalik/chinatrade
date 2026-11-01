"""
Global Trade Cost & Landed Profit Calculator.
Calculates end-to-end landed cost, export profitability, duty/VAT impact,
and break-even thresholds for arbitrary Origin-Destination country pairs using Decimal precision.
"""

from decimal import Decimal, ROUND_HALF_UP
from typing import Optional, Dict, Any, List
from trade_hub.models import (
    GlobalIncoterms,
    TradeDirection,
    GlobalTradeCalculationResult,
    GlobalTradeCostLineItem,
)


class GlobalTradeCostCalculator:
    """
    Arbitrary-route, multi-Incoterm landed cost and export profitability engine.
    Uses pure Decimal arithmetic for financial fidelity.
    """

    DEFAULT_FX_USD_IRR = Decimal("850000")  # Market baseline reference rate

    # Default regional freight benchmarks (USD per metric ton / standard container unit equivalent)
    DEFAULT_FREIGHT_RATES: Dict[str, Decimal] = {
        # Road transit corridors
        "Iran_Iraq": Decimal("45.00"),          # Trucking via Mehran/Shalamcheh
        "Iran_Turkey": Decimal("75.00"),        # Trucking via Bazargan
        "Iran_UAE": Decimal("55.00"),           # Sea barge / Ro-Ro Bandar Abbas - Sharjah
        "Iran_Armenia": Decimal("65.00"),       # Nordooz border
        "Iran_Russia": Decimal("110.00"),       # Anzali/Astrakhan or rail
        "Iran_Afghanistan": Decimal("50.00"),   # Dogharoun
        "Iran_Oman": Decimal("60.00"),          # Bandar Abbas - Sohar
        
        # Deep sea intercontinental corridors (per ton estimate)
        "China_Iran": Decimal("95.00"),
        "China_Iraq": Decimal("105.00"),
        "China_UAE": Decimal("85.00"),
        "India_Iran": Decimal("60.00"),
        "Germany_Iran": Decimal("140.00"),
        "Default_Road": Decimal("60.00"),
        "Default_Sea": Decimal("80.00"),
    }

    @classmethod
    def calculate(
        cls,
        origin_country: str,
        destination_country: str,
        incoterms: GlobalIncoterms,
        trade_direction: TradeDirection,
        batch_quantity: Decimal,
        purchase_cost_per_unit_usd: Decimal,
        target_selling_price_per_unit_usd: Optional[Decimal] = None,
        unit_name: str = "Tons",
        fx_rate_usd_irr: Optional[Decimal] = None,
        freight_per_unit_usd: Optional[Decimal] = None,
        insurance_pct: Decimal = Decimal("0.005"),     # 0.5% cargo insurance
        customs_tariff_pct: Decimal = Decimal("0.05"),  # 5% default tariff
        vat_tax_pct: Decimal = Decimal("0.09"),         # 9% default VAT
        origin_handling_per_unit_usd: Optional[Decimal] = None,
        destination_clearance_per_unit_usd: Optional[Decimal] = None,
        financing_interest_pct: Decimal = Decimal("0.02"), # 2% cost of capital during transit
        scrap_reserve_pct: Decimal = Decimal("0.01"),       # 1% allowance for damages/loss
    ) -> GlobalTradeCalculationResult:
        """
        Executes comprehensive landed cost calculation.
        """
        fx_rate = fx_rate_usd_irr or cls.DEFAULT_FX_USD_IRR
        qty = Decimal(str(batch_quantity))
        if qty <= Decimal("0"):
            qty = Decimal("1")

        unit_purchase = Decimal(str(purchase_cost_per_unit_usd))
        batch_purchase = (unit_purchase * qty).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

        # Determine corridor key
        orig_clean = origin_country.strip().capitalize()
        dest_clean = destination_country.strip().capitalize()
        corridor_key = f"{orig_clean}_{dest_clean}"
        
        # Estimate freight if not provided
        if freight_per_unit_usd is not None:
            unit_freight = Decimal(str(freight_per_unit_usd))
        elif corridor_key in cls.DEFAULT_FREIGHT_RATES:
            unit_freight = cls.DEFAULT_FREIGHT_RATES[corridor_key]
        else:
            unit_freight = cls.DEFAULT_FREIGHT_RATES["Default_Road"]

        # Incoterms responsibility adjustments
        # EXW: Buyer pays everything from origin factory
        # FOB/FCA: Seller brings to ship/carrier; Buyer pays ocean freight + import
        # CFR/CPT: Seller pays freight; Buyer pays insurance + import
        # CIF/CIP: Seller pays freight + insurance; Buyer pays import
        # DAP: Seller pays up to destination unloaded point; Buyer pays import duty/VAT
        # DDP: Seller pays all duties, taxes, and delivery to buyer's door

        if origin_handling_per_unit_usd is not None:
            unit_origin_handling = Decimal(str(origin_handling_per_unit_usd))
        else:
            unit_origin_handling = Decimal("10.00") if incoterms in [GlobalIncoterms.EXW, GlobalIncoterms.FCA] else Decimal("0.00")

        # Freight component
        if incoterms in [GlobalIncoterms.EXW, GlobalIncoterms.FCA, GlobalIncoterms.FAS, GlobalIncoterms.FOB]:
            applicable_freight_unit = unit_freight
        elif incoterms in [GlobalIncoterms.CFR, GlobalIncoterms.CIF, GlobalIncoterms.CPT, GlobalIncoterms.CIP, GlobalIncoterms.DAP, GlobalIncoterms.DDP]:
            # Freight is already bundled in purchase price if quoted CIF/DDP, but if user is buyer modeling landed cost from FOB supplier, freight is added
            applicable_freight_unit = Decimal("0.00")
        else:
            applicable_freight_unit = unit_freight

        # Insurance component
        if incoterms in [GlobalIncoterms.CIF, GlobalIncoterms.CIP, GlobalIncoterms.DDP]:
            unit_insurance = Decimal("0.00")
        else:
            unit_insurance = ((unit_purchase + applicable_freight_unit) * insurance_pct).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

        # Customs valuation base (CIF value in destination customs law)
        cif_customs_base_unit = unit_purchase + unit_origin_handling + applicable_freight_unit + unit_insurance

        # Destination customs duty & VAT
        if incoterms == GlobalIncoterms.DDP:
            # Under DDP, duty and taxes are prepaid by seller in price
            unit_customs_duty = Decimal("0.00")
            unit_vat = Decimal("0.00")
        else:
            unit_customs_duty = (cif_customs_base_unit * customs_tariff_pct).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            unit_vat = ((cif_customs_base_unit + unit_customs_duty) * vat_tax_pct).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

        # Destination clearance, port handling & inland delivery
        if destination_clearance_per_unit_usd is not None:
            unit_dest_clearance = Decimal(str(destination_clearance_per_unit_usd))
        else:
            unit_dest_clearance = Decimal("15.00") if incoterms != GlobalIncoterms.DDP else Decimal("0.00")

        # Financial cost of capital during transit + Scrap reserve
        unit_financing = (cif_customs_base_unit * financing_interest_pct).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        unit_scrap = (unit_purchase * scrap_reserve_pct).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

        # Total landed cost per unit
        total_landed_unit = (
            unit_purchase
            + unit_origin_handling
            + applicable_freight_unit
            + unit_insurance
            + unit_customs_duty
            + unit_vat
            + unit_dest_clearance
            + unit_financing
            + unit_scrap
        ).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

        total_landed_batch = (total_landed_unit * qty).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

        # Revenue and Profitability metrics
        if target_selling_price_per_unit_usd is not None and Decimal(str(target_selling_price_per_unit_usd)) > Decimal("0"):
            target_sell_unit = Decimal(str(target_selling_price_per_unit_usd))
        else:
            # Default standard benchmark margin: 18% over landed cost
            target_sell_unit = (total_landed_unit * Decimal("1.18")).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

        gross_revenue_batch = (target_sell_unit * qty).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        net_profit_unit = (target_sell_unit - total_landed_unit).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        total_net_profit_batch = (net_profit_unit * qty).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

        # Margins & Ratios
        profit_margin_pct = (
            ((net_profit_unit / target_sell_unit) * Decimal("100")).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            if target_sell_unit > Decimal("0") else Decimal("0.00")
        )
        markup_roi_pct = (
            ((total_net_profit_batch / total_landed_batch) * Decimal("100")).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            if total_landed_batch > Decimal("0") else Decimal("0.00")
        )

        # Break-even thresholds
        break_even_price = total_landed_unit
        break_even_units = (
            (total_landed_batch / target_sell_unit).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            if target_sell_unit > Decimal("0") else qty
        )

        # Build detailed line items
        line_items: List[GlobalTradeCostLineItem] = []
        raw_items = [
            ("origin", "بهای خرید مبدا", "Base Purchase Cost", unit_purchase * qty),
            ("origin", "هزینه ترخیص صادراتی و بارگیری مبدا", "Origin Handling & Export Clearance", unit_origin_handling * qty),
            ("freight", "حمل و ترانزیت بین‌المللی", "International Freight", applicable_freight_unit * qty),
            ("insurance", "بیمه باربری بین‌المللی", "Cargo Insurance", unit_insurance * qty),
            ("customs", "حقوق و عوارض گمرک مقصد", "Destination Customs Tariff", unit_customs_duty * qty),
            ("customs", "مالیات بر ارزش افزوده گمرکی", "Destination VAT & Taxes", unit_vat * qty),
            ("clearance", "ترخیص، تخلیه، THC و ترابری داخلی مقصد", "Destination THC & Inland Delivery", unit_dest_clearance * qty),
            ("financing", "هزینه خواب سرمایه و مالی", "Financing & Capital Cost", unit_financing * qty),
            ("risk", "ذخیره ضایعات و کسری بار", "Scrap & Wastage Reserve", unit_scrap * qty),
        ]

        for cat, name_fa, name_en, amt_usd in raw_items:
            amt_usd_dec = amt_usd.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            amt_irr = (amt_usd_dec * fx_rate).quantize(Decimal("1"), rounding=ROUND_HALF_UP)
            pct = (
                ((amt_usd_dec / total_landed_batch) * Decimal("100")).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
                if total_landed_batch > Decimal("0") else Decimal("0.00")
            )
            line_items.append(
                GlobalTradeCostLineItem(
                    category=cat,
                    name_fa=name_fa,
                    name_en=name_en,
                    amount_usd=amt_usd_dec,
                    amount_irr=amt_irr,
                    percentage_of_total=pct
                )
            )

        # Sensitivity Analysis:
        # 1. 10% FX volatility impact on landed cost in IRR
        sensitivity_fx_10pct = (total_landed_batch * (fx_rate * Decimal("0.10"))).quantize(Decimal("1"), rounding=ROUND_HALF_UP)
        # 2. 20% freight cost increase impact in USD
        freight_impact_usd = (applicable_freight_unit * qty * Decimal("0.20")).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

        assumptions = (
            f"محاسبه بر اساس اینکوترمز {incoterms.value} از {origin_country} به {destination_country} "
            f"با نرخ ارز مبنا {fx_rate:,.0f} ریال/دلار انجام شد. نرخ تعرفه گمرکی {(customs_tariff_pct*100):.1f}% و مالیات ارزش افزوده {(vat_tax_pct*100):.1f}% لحاظ گردید."
        )

        return GlobalTradeCalculationResult(
            origin_country=origin_country,
            destination_country=destination_country,
            incoterms=incoterms,
            trade_direction=trade_direction,
            batch_quantity=qty,
            unit_name=unit_name,
            currency_used="USD",
            fx_rate_usd_irr=fx_rate,
            purchase_cost_per_unit_usd=unit_purchase,
            total_landed_cost_per_unit_usd=total_landed_unit,
            total_landed_cost_batch_usd=total_landed_batch,
            target_selling_price_per_unit_usd=target_sell_unit,
            gross_revenue_batch_usd=gross_revenue_batch,
            net_profit_per_unit_usd=net_profit_unit,
            total_net_profit_batch_usd=total_net_profit_batch,
            profit_margin_pct=profit_margin_pct,
            markup_roi_pct=markup_roi_pct,
            break_even_selling_price_usd=break_even_price,
            break_even_units=break_even_units,
            line_items=line_items,
            sensitivity_fx_10pct_usd=sensitivity_fx_10pct,
            sensitivity_freight_20pct_usd=freight_impact_usd,
            is_sufficient_data=True,
            assumptions_notes=assumptions
        )
