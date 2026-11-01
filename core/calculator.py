"""
Landed Cost and Arbitrage Calculator for importing goods from China to Iran.
Accurately models CIF values, customs tariffs, commercial benefits, 10% VAT,
international freight (Air vs Sea), brokerage fees, and ROI.
"""

from typing import Optional
from config import CONFIG, TradeConfig
from core.models import ChineseSupplier, LandedCostBreakdown

class ImportProfitCalculator:
    def __init__(self, config: Optional[TradeConfig] = None):
        self.config = config or CONFIG

    def calculate_landed_cost(
        self,
        supplier: ChineseSupplier,
        target_iran_price_toman: float,
        shipping_method: str = "Air Cargo",
        customs_tariff_pct: Optional[float] = None,
        commercial_benefit_pct: Optional[float] = None,
        batch_quantity: Optional[int] = None,
    ) -> LandedCostBreakdown:
        """
        محاسبه دقیق بهای تمام‌شده و سودآوری بر اساس قوانین گمرکی و حمل ایران
        """
        qty = batch_quantity if batch_quantity is not None else max(supplier.moq, 100)
        
        # 1. تعیین قیمت بر اساس تیراژ پله‌ای
        unit_cny = supplier.unit_price_cny
        if supplier.price_tiers:
            for tier in sorted(supplier.price_tiers, key=lambda x: x.min_quantity, reverse=True):
                if qty >= tier.min_quantity:
                    unit_cny = tier.unit_price_cny
                    break

        purchase_price_toman = unit_cny * self.config.RMB_TO_TOMAN

        # 2. هزینه حمل بین‌المللی (هوایی یا دریایی)
        method = shipping_method.lower()
        if "sea" in method or "دریایی" in method:
            # حمل دریایی بر اساس CBM
            cbm = max(supplier.volume_cbm, 0.0005)
            sea_cost_usd = cbm * self.config.SEA_FREIGHT_USD_PER_CBM
            shipping_toman = sea_cost_usd * self.config.USD_TO_TOMAN
            active_shipping_method = "Sea Freight (LCL/FCL)"
        else:
            # حمل هوایی کارگو بر اساس وزن (یا وزن حجمی)
            # وزن حجمی = (حجم * 167)
            volumetric_weight = supplier.volume_cbm * 167.0
            billable_weight = max(supplier.weight_kg, volumetric_weight, 0.05)
            air_cost_usd = billable_weight * self.config.AIR_FREIGHT_USD_PER_KG
            shipping_toman = air_cost_usd * self.config.USD_TO_TOMAN
            active_shipping_method = "Air Cargo (Express/Standard)"

        # 3. محاسبه ارزش CIF در گمرک (ارزش کالا + کرایه حمل + بیمه 0.5%)
        insurance_toman = purchase_price_toman * 0.005
        cif_toman = purchase_price_toman + shipping_toman + insurance_toman

        # 4. حقوق و عوارض گمرکی ایران
        tariff_rate = (
            customs_tariff_pct
            if customs_tariff_pct is not None
            else self.config.DEFAULT_CUSTOMS_TARIFF_PERCENT
        ) / 100.0
        
        benefit_rate = (
            commercial_benefit_pct
            if commercial_benefit_pct is not None
            else self.config.DEFAULT_COMMERCIAL_BENEFIT_PERCENT
        ) / 100.0

        customs_duty_toman = cif_toman * tariff_rate
        commercial_benefit_toman = cif_toman * benefit_rate

        # 5. مالیات بر ارزش افزوده (۱۰ درصد از مجموع CIF + حقوق گمرکی + سود بازرگانی)
        taxable_base = cif_toman + customs_duty_toman + commercial_benefit_toman
        vat_toman = taxable_base * (self.config.VAT_PERCENT / 100.0)

        # 6. هزینه‌های جانبی: ترخیص، انبارداری، استاندارد، ثبت سفارش، حمل داخلی
        brokerage_toman = cif_toman * (self.config.CLEARANCE_BROKERAGE_PERCENT / 100.0)
        domestic_logistics_toman = cif_toman * (self.config.DOMESTIC_LOGISTICS_PERCENT / 100.0)

        # 7. بهای تمام‌شده نهایی در انبار ایران (به ازای هر واحد)
        total_landed_cost_toman = (
            purchase_price_toman
            + shipping_toman
            + customs_duty_toman
            + commercial_benefit_toman
            + vat_toman
            + brokerage_toman
            + domestic_logistics_toman
        )

        # 8. محاسبه سودآوری و بازگشت سرمایه (ROI)
        net_profit_per_unit = target_iran_price_toman - total_landed_cost_toman
        profit_margin_pct = (net_profit_per_unit / target_iran_price_toman) * 100.0 if target_iran_price_toman > 0 else 0.0
        roi_pct = (net_profit_per_unit / total_landed_cost_toman) * 100.0 if total_landed_cost_toman > 0 else 0.0

        # برای کل پارت سفارش
        total_investment = total_landed_cost_toman * qty
        total_profit = net_profit_per_unit * qty

        return LandedCostBreakdown(
            purchase_price_cny=unit_cny,
            purchase_price_toman=round(purchase_price_toman),
            shipping_method=active_shipping_method,
            international_shipping_toman=round(shipping_toman),
            customs_duty_toman=round(customs_duty_toman),
            commercial_benefit_toman=round(commercial_benefit_toman),
            vat_toman=round(vat_toman),
            clearance_and_brokerage_toman=round(brokerage_toman),
            domestic_logistics_toman=round(domestic_logistics_toman),
            total_landed_cost_toman=round(total_landed_cost_toman),
            target_selling_price_toman=round(target_iran_price_toman),
            net_profit_per_unit_toman=round(net_profit_per_unit),
            profit_margin_percent=round(profit_margin_pct, 1),
            roi_percent=round(roi_pct, 1),
            break_even_price_toman=round(total_landed_cost_toman),
            batch_quantity=qty,
            total_investment_toman=round(total_investment),
            total_net_profit_toman=round(total_profit),
        )
