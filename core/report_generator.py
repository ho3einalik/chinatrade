"""
Report Generator for China-to-Iran Import Intelligence & Arbitrage Agent.
Produces executive-ready Markdown dossiers and interactive HTML reports.
"""

import os
from typing import Optional
from core.models import ImportOpportunityReport

class ReportGenerator:
    def __init__(self, output_dir: str = "reports"):
        self.output_dir = output_dir
        os.makedirs(self.output_dir, exist_ok=True)

    def generate_markdown(self, report: ImportOpportunityReport) -> str:
        """تولید گزارش متنی با فرمت حرفه‌ای مارک‌داون"""
        best_sup = report.best_supplier
        air = report.air_cost_analysis
        sea = report.sea_cost_analysis
        market = report.iran_market

        md = []
        md.append(f"# 🇨🇳🇮🇷 شناسنامه جامع تحلیل واردات کالا: {report.product_name_fa}")
        md.append(f"**عنوان بین‌المللی کالا:** `{report.product_name_en}`")
        md.append(f"**دسته‌بندی:** `{report.category}` | **کد تعرفه گمرکی (HS Code تخمینی):** `{report.hs_code_estimate}`")
        md.append(f"**امتیاز فرصت تجاری (Opportunity Score):** ⭐ **{report.opportunity_score} / 10**")
        md.append("\n---\n")

        # خلاصه تصمیم‌گیری
        md.append("### 🎯 خلاصه ارزیابی و استراتژی ورود به بازار")
        md.append(f"> {report.recommendation_summary}\n")

        # جدول مقایسه مالی هوایی و دریایی
        md.append("### 💰 مقایسه سودآوری و بهای تمام‌شده نهایی (هوایی vs دریایی)")
        md.append("| شاخص مالی و بازرگانی | روش حمل هوایی (Air Cargo) | روش حمل دریایی (Sea Freight) |")
        md.append("| :--- | :--- | :--- |")
        if air and sea:
            md.append(f"| **قیمت خرید فاکتور کارخانه** | {air.purchase_price_cny} ¥ ({air.purchase_price_toman:,} تومان) | {sea.purchase_price_cny} ¥ ({sea.purchase_price_toman:,} تومان) |")
            md.append(f"| **کرایه حمل بین‌المللی** | {air.international_shipping_toman:,} تومان | {sea.international_shipping_toman:,} تومان |")
            md.append(f"| **حقوق گمرکی و سود بازرگانی** | {(air.customs_duty_toman + air.commercial_benefit_toman):,} تومان | {(sea.customs_duty_toman + sea.commercial_benefit_toman):,} تومان |")
            md.append(f"| **مالیات ارزش افزوده (۱۰٪)** | {air.vat_toman:,} تومان | {sea.vat_toman:,} تومان |")
            md.append(f"| **هزینه ترخیص، استاندارد و حمل داخلی** | {(air.clearance_and_brokerage_toman + air.domestic_logistics_toman):,} تومان | {(sea.clearance_and_brokerage_toman + sea.domestic_logistics_toman):,} تومان |")
            md.append(f"| 🏷️ **بهای تمام‌شده هر واحد در ایران** | **{air.total_landed_cost_toman:,} تومان** | **{sea.total_landed_cost_toman:,} تومان** |")
            md.append(f"| 🛒 **قیمت فروش هدف در بازار ایران** | **{air.target_selling_price_toman:,} تومان** | **{sea.target_selling_price_toman:,} تومان** |")
            md.append(f"| 💵 **سود خالص هر عدد** | **{air.net_profit_per_unit_toman:,} تومان** | **{sea.net_profit_per_unit_toman:,} تومان** |")
            md.append(f"| 📈 **حاشیه سود خالص (Margin)** | **{air.profit_margin_percent}%** | **{sea.profit_margin_percent}%** |")
            md.append(f"| 🚀 **نرخ بازگشت سرمایه (ROI)** | **{air.roi_percent}%** | **{sea.roi_percent}%** |")
            md.append(f"| 📦 **سود کل یک پارت ({air.batch_quantity} عددی)** | **{air.total_net_profit_toman:,} تومان** | **{sea.total_net_profit_toman:,} تومان** |")
        md.append("\n---\n")

        # وضعیت بازار ایران
        md.append("### 🇮🇷 تحلیل بازار و رقبای داخلی در ایران (دیجی‌کالا، ترب، ایمالز، باسلام، فروشگاه‌های تخصصی و دیوار)")
        if market:
            md.append(f"- **پلتفرم‌های پایش‌شده:** {market.platform}")
            md.append(f"- **کف قیمت بازار (ارزان‌ترین فروشگاه):** {market.lowest_price_toman:,.0f} تومان")
            md.append(f"- **میانگین قیمت فروش فعلی:** {market.average_price_toman:,.0f} تومان")
            md.append(f"- **سقف قیمت بازار:** {market.highest_price_toman:,.0f} تومان")
            md.append(f"- **تعداد فروشندگان فعال:** {market.active_sellers_count} فروشگاه")
            md.append(f"- **شاخص کشش تقاضا:** {market.sales_velocity_score} از ۱۰")
            
            if market.channels:
                md.append("\n#### 🏬 تفکیک قیمت در کانال‌های توزیع ایران:")
                md.append("| کانال فروش | قیمت تخمینی (تومان) | وضعیت و نوع قیمت |")
                md.append("| :--- | :--- | :--- |")
                for ch in market.channels:
                    md.append(f"| **{ch.name}** | {ch.price_toman:,.0f} تومان | {ch.price_label} |")
                md.append("")
            
            md.append(f"- **لینک استعلام بازار:** [مشاهده در ترب]({market.source_url})")
        md.append("\n---\n")

        # کارخانه‌های شناسایی‌شده در چین
        md.append("### 🇨🇳 کارخانه‌ها و تامین‌کنندگان منتخب در چین")
        for idx, sup in enumerate(report.suppliers_china, 1):
            md.append(f"#### {idx}. {sup.name} ({sup.platform})")
            md.append(f"- **قیمت پایه:** {sup.unit_price_cny} یوان ({sup.unit_price_usd or round(sup.unit_price_cny/7.1, 2)} دلار)")
            md.append(f"- **حداقل سفارش (MOQ):** {sup.moq} واحد | **زمان تولید:** {sup.lead_time_days} روز")
            md.append(f"- **محل استقرار کارخانه:** {sup.location}")
            md.append(f"- **اعتبار و گواهینامه‌ها:** {sup.supplier_tier} | {', '.join(sup.certifications) if sup.certifications else 'Verified'}")
            if sup.price_tiers:
                tier_str = " | ".join([f"تیراژ {t.min_quantity}+: {t.unit_price_cny}¥" for t in sup.price_tiers])
                md.append(f"- **پله‌های قیمتی تیراژ:** {tier_str}")
            if sup.product_specs:
                spec_str = "، ".join([f"{k}: {v}" for k, v in list(sup.product_specs.items())[:3]])
                md.append(f"- **مشخصات فنی کلیدی:** {spec_str}")
            md.append("")

        # الزامات قانونی و گمرکی
        md.append("### 📋 چک‌لیست رگولاتوری، گمرک و ثبت سفارش")
        for note in report.regulatory_notes:
            md.append(f"- ✅ {note}")

        return "\n".join(md)

    def generate_html(self, report: ImportOpportunityReport) -> str:
        """تولید گزارش شکیل تعاملی به زبان فارسی با طراحی مدرن و راست‌چین"""
        best_sup = report.best_supplier
        air = report.air_cost_analysis
        sea = report.sea_cost_analysis
        market = report.iran_market

        air_cost = f"{air.total_landed_cost_toman:,.0f}" if air else "-"
        air_profit = f"{air.net_profit_per_unit_toman:,.0f}" if air else "-"
        air_roi = f"{air.roi_percent}%" if air else "-"
        air_margin = f"{air.profit_margin_percent}%" if air else "-"
        air_buy_cny = f"{air.purchase_price_cny}" if air else "-"
        air_buy_toman = f"{air.purchase_price_toman:,.0f}" if air else "-"
        air_shipping = f"{air.international_shipping_toman:,.0f}" if air else "-"
        air_customs = f"{(air.customs_duty_toman + air.commercial_benefit_toman):,.0f}" if air else "-"
        air_vat = f"{air.vat_toman:,.0f}" if air else "-"
        air_clearance = f"{(air.clearance_and_brokerage_toman + air.domestic_logistics_toman):,.0f}" if air else "-"
        air_batch_qty = air.batch_quantity if air else 500
        air_batch_profit = f"{air.total_net_profit_toman:,.0f}" if air else "-"

        sea_cost = f"{sea.total_landed_cost_toman:,.0f}" if sea else "-"
        sea_profit = f"{sea.net_profit_per_unit_toman:,.0f}" if sea else "-"
        sea_margin = f"{sea.profit_margin_percent}%" if sea else "-"
        sea_buy_cny = f"{sea.purchase_price_cny}" if sea else "-"
        sea_buy_toman = f"{sea.purchase_price_toman:,.0f}" if sea else "-"
        sea_shipping = f"{sea.international_shipping_toman:,.0f}" if sea else "-"
        sea_customs = f"{(sea.customs_duty_toman + sea.commercial_benefit_toman):,.0f}" if sea else "-"
        sea_vat = f"{sea.vat_toman:,.0f}" if sea else "-"
        sea_clearance = f"{(sea.clearance_and_brokerage_toman + sea.domestic_logistics_toman):,.0f}" if sea else "-"
        sea_batch_profit = f"{sea.total_net_profit_toman:,.0f}" if sea else "-"

        market_avg = f"{market.average_price_toman:,.0f}" if market else "-"
        market_low = f"{market.lowest_price_toman:,.0f}" if market else "-"
        market_high = f"{market.highest_price_toman:,.0f}" if market else "-"
        market_sellers = market.active_sellers_count if market else 1

        html = f"""<!DOCTYPE html>
<html lang="fa" dir="rtl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>شناسنامه تحلیل واردات: {report.product_name_fa}</title>
    <link href="https://cdn.jsdelivr.net/npm/vazirmatn@33.0.3/Vazirmatn-font-face.css" rel="stylesheet" type="text/css" />
    <style>
        body {{
            font-family: 'Vazirmatn', sans-serif;
            background-color: #0f172a;
            color: #e2e8f0;
            margin: 0;
            padding: 30px 20px;
        }}
        .container {{
            max-width: 1100px;
            margin: 0 auto;
        }}
        .header-card {{
            background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%);
            border: 1px solid #334155;
            border-radius: 16px;
            padding: 30px;
            margin-bottom: 25px;
            box-shadow: 0 10px 25px rgba(0,0,0,0.3);
            display: flex;
            justify-content: space-between;
            align-items: center;
            flex-wrap: wrap;
            gap: 20px;
        }}
        .header-title h1 {{
            margin: 0 0 10px 0;
            font-size: 26px;
            color: #38bdf8;
        }}
        .header-title p {{
            margin: 5px 0;
            color: #94a3b8;
            font-size: 14px;
        }}
        .score-badge {{
            background: linear-gradient(135deg, #059669 0%, #10b981 100%);
            color: white;
            padding: 15px 25px;
            border-radius: 12px;
            text-align: center;
        }}
        .score-badge .score-val {{
            font-size: 32px;
            font-weight: 800;
        }}
        .score-badge .score-label {{
            font-size: 12px;
            text-transform: uppercase;
        }}
        .kpi-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
            gap: 15px;
            margin-bottom: 25px;
        }}
        .kpi-card {{
            background-color: #1e293b;
            border: 1px solid #334155;
            border-radius: 12px;
            padding: 20px;
            text-align: right;
        }}
        .kpi-card .kpi-label {{
            color: #94a3b8;
            font-size: 13px;
            margin-bottom: 8px;
        }}
        .kpi-card .kpi-value {{
            font-size: 22px;
            font-weight: bold;
            color: #f8fafc;
        }}
        .kpi-card.green .kpi-value {{ color: #34d399; }}
        .kpi-card.blue .kpi-value {{ color: #38bdf8; }}
        .kpi-card.amber .kpi-value {{ color: #fbbf24; }}
        
        .section-card {{
            background-color: #1e293b;
            border: 1px solid #334155;
            border-radius: 14px;
            padding: 25px;
            margin-bottom: 25px;
        }}
        .section-card h2 {{
            margin-top: 0;
            font-size: 19px;
            color: #38bdf8;
            border-bottom: 1px solid #334155;
            padding-bottom: 12px;
            margin-bottom: 20px;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            margin: 15px 0;
            font-size: 14px;
        }}
        th, td {{
            padding: 12px 16px;
            text-align: right;
            border-bottom: 1px solid #334155;
        }}
        th {{
            background-color: #0f172a;
            color: #94a3b8;
            font-weight: 600;
        }}
        tr:hover {{
            background-color: #273549;
        }}
        .badge {{
            display: inline-block;
            padding: 4px 10px;
            border-radius: 6px;
            font-size: 12px;
            font-weight: 600;
        }}
        .badge-green {{ background-color: rgba(16, 185, 129, 0.2); color: #34d399; }}
        .badge-blue {{ background-color: rgba(56, 189, 248, 0.2); color: #38bdf8; }}
        .tag-list {{
            display: flex;
            gap: 8px;
            flex-wrap: wrap;
            margin-top: 5px;
        }}
        .checklist-item {{
            display: flex;
            align-items: center;
            gap: 10px;
            margin-bottom: 12px;
            color: #cbd5e1;
        }}
        .checklist-icon {{
            color: #10b981;
            font-size: 18px;
        }}
        .btn {{
            background-color: #2563eb;
            color: white;
            padding: 8px 16px;
            border-radius: 8px;
            text-decoration: none;
            font-size: 13px;
            display: inline-block;
        }}
    </style>
</head>
<body>
    <div class="container">
        <!-- هدر و امتیاز فرصت -->
        <div class="header-card">
            <div class="header-title">
                <h1>🇨🇳🇮🇷 شناسنامه جامع واردات: {report.product_name_fa}</h1>
                <p><strong>نام انگلیسی / کارخانه:</strong> {report.product_name_en}</p>
                <p><strong>دسته‌بندی:</strong> {report.category} | <strong>کد تعرفه گمرکی (HS Code):</strong> {report.hs_code_estimate}</p>
            </div>
            <div class="score-badge">
                <div class="score-val">{report.opportunity_score}</div>
                <div class="score-label">امتیاز جذابیت واردات از ۱۰</div>
            </div>
        </div>

        <!-- کارت‌های KPI کلیدی -->
        <div class="kpi-grid">
            <div class="kpi-card blue">
                <div class="kpi-label">بهای تمام‌شده هر عدد در ایران (هوایی)</div>
                <div class="kpi-value">{air_cost} تومان</div>
            </div>
            <div class="kpi-card amber">
                <div class="kpi-label">قیمت فروش در بازار ایران (ترب)</div>
                <div class="kpi-value">{market_avg} تومان</div>
            </div>
            <div class="kpi-card green">
                <div class="kpi-label">سود خالص هر عدد (هوایی)</div>
                <div class="kpi-value">{air_profit} تومان</div>
            </div>
            <div class="kpi-card green">
                <div class="kpi-label">نرخ بازگشت سرمایه (ROI)</div>
                <div class="kpi-value">{air_roi} (مارجین: {air_margin})</div>
            </div>
        </div>

        <!-- جدول مقایسه کامل هوایی و دریایی -->
        <div class="section-card">
            <h2>📊 آنالیز بهای تمام‌شده و سودآوری در ایران (Air vs Sea)</h2>
            <table>
                <thead>
                    <tr>
                        <th>آیتم هزینه / شاخص</th>
                        <th>روش حمل هوایی (Air Cargo)</th>
                        <th>روش حمل دریایی (Sea Freight)</th>
                    </tr>
                </thead>
                <tbody>
                    <tr>
                        <td>قیمت خرید فاکتور چین</td>
                        <td>{air_buy_cny} ¥ ({air_buy_toman} تومان)</td>
                        <td>{sea_buy_cny} ¥ ({sea_buy_toman} تومان)</td>
                    </tr>
                    <tr>
                        <td>کرایه حمل بین‌المللی تا ایران</td>
                        <td>{air_shipping} تومان</td>
                        <td>{sea_shipping} تومان</td>
                    </tr>
                    <tr>
                        <td>حقوق گمرکی و سود بازرگانی</td>
                        <td>{air_customs} تومان</td>
                        <td>{sea_customs} تومان</td>
                    </tr>
                    <tr>
                        <td>مالیات بر ارزش افزوده (۱۰٪)</td>
                        <td>{air_vat} تومان</td>
                        <td>{sea_vat} تومان</td>
                    </tr>
                    <tr>
                        <td>ترخیص، استاندارد و حمل داخلی</td>
                        <td>{air_clearance} تومان</td>
                        <td>{sea_clearance} تومان</td>
                    </tr>
                    <tr style="background-color: rgba(56, 189, 248, 0.1); font-weight: bold;">
                        <td>بهای تمام‌شده کل در انبار ایران</td>
                        <td style="color: #38bdf8;">{air_cost} تومان</td>
                        <td style="color: #38bdf8;">{sea_cost} تومان</td>
                    </tr>
                    <tr style="background-color: rgba(16, 185, 129, 0.1); font-weight: bold;">
                        <td>سود خالص هر واحد</td>
                        <td style="color: #34d399;">{air_profit} تومان ({air_margin} مارجین)</td>
                        <td style="color: #34d399;">{sea_profit} تومان ({sea_margin} مارجین)</td>
                    </tr>
                    <tr>
                        <td>سود کل یک پارت ({air_batch_qty} عددی)</td>
                        <td>{air_batch_profit} تومان</td>
                        <td>{sea_batch_profit} تومان</td>
                    </tr>
                </tbody>
            </table>
        </div>

        <!-- کارخانه‌های چین -->
        <div class="section-card">
            <h2>🏭 کارخانه‌ها و تامین‌کنندگان معتبر شناسایی‌شده در چین</h2>
            <table>
                <thead>
                    <tr>
                        <th>نام کارخانه و پلتفرم</th>
                        <th>قیمت هر واحد</th>
                        <th>حداقل سفارش (MOQ)</th>
                        <th>محل کارخانه و استان</th>
                        <th>اعتبارسنجی و گواهینامه‌ها</th>
                    </tr>
                </thead>
                <tbody>"""

        for sup in report.suppliers_china:
            html += f"""
                    <tr>
                        <td><strong>{sup.name}</strong><br><span style="color: #94a3b8; font-size: 12px;">{sup.platform}</span></td>
                        <td><span class="badge badge-green">{sup.unit_price_cny} ¥ ({sup.unit_price_usd or round(sup.unit_price_cny/7.1, 2)} $)</span></td>
                        <td>{sup.moq} واحد</td>
                        <td>{sup.location}</td>
                        <td>{sup.supplier_tier}</td>
                    </tr>"""

        html += f"""
                </tbody>
            </table>
        </div>

        <!-- بازار ایران و الزامات قانونی -->
        <div class="section-card">
            <h2>📋 وضعیت بازار داخلی و مجوزهای الزامی گمرک</h2>
            <div style="margin-bottom: 20px;">
                <p><strong>پایش قیمت در بازار داخلی:</strong> کف قیمت {market_low} ت | میانگین {market_avg} ت | سقف {market_high} ت ({market_sellers} فروشنده فعال در ترب)</p>
            </div>
            <div class="checklist">"""

        for note in report.regulatory_notes:
            html += f"""
                <div class="checklist-item">
                    <span class="checklist-icon">✔</span>
                    <span>{note}</span>
                </div>"""

        html += f"""
            </div>
        </div>
    </div>
</body>
</html>"""
        return html

    def generate_csv(self, report: ImportOpportunityReport) -> str:
        """تولید خروجی جدولی CSV شامل مقایسه هزینه‌ها و تأمین‌کنندگان"""
        import io
        import csv
        
        output = io.StringIO()
        writer = csv.writer(output)
        
        # Section 1: Summary
        writer.writerow(["شاخص", "مقدار"])
        writer.writerow(["نام فارسی کالا", report.product_name_fa])
        writer.writerow(["نام انگلیسی کالا", report.product_name_en])
        writer.writerow(["دسته‌بندی", report.category])
        writer.writerow(["کد تعرفه HS", report.hs_code_estimate])
        writer.writerow(["امتیاز فرصت تجاری", report.opportunity_score])
        writer.writerow([])

        # Section 2: Economics
        writer.writerow(["شاخص مالی (تومان)", "حمل هوایی (Air)", "حمل دریایی (Sea)"])
        air = report.air_cost_analysis
        sea = report.sea_cost_analysis
        if air and sea:
            writer.writerow(["بهای خرید کارخانه (تومان)", air.purchase_price_toman, sea.purchase_price_toman])
            writer.writerow(["کرایه حمل بین‌المللی", air.international_shipping_toman, sea.international_shipping_toman])
            writer.writerow(["حقوق و سود بازرگانی", air.customs_duty_toman + air.commercial_benefit_toman, sea.customs_duty_toman + sea.commercial_benefit_toman])
            writer.writerow(["مالیات بر ارزش افزوده (۱۰٪)", air.vat_toman, sea.vat_toman])
            writer.writerow(["ترخیص و حمل داخلی", air.clearance_and_brokerage_toman + air.domestic_logistics_toman, sea.clearance_and_brokerage_toman + sea.domestic_logistics_toman])
            writer.writerow(["بهای تمام‌شده هر واحد", air.total_landed_cost_toman, sea.total_landed_cost_toman])
            writer.writerow(["قیمت فروش هدف در ایران", air.target_selling_price_toman, sea.target_selling_price_toman])
            writer.writerow(["سود خالص هر واحد", air.net_profit_per_unit_toman, sea.net_profit_per_unit_toman])
            writer.writerow(["حاشیه سود خالص (Margin %)", f"{air.profit_margin_percent}%", f"{sea.profit_margin_percent}%"])
            writer.writerow(["بازده سرمایه (ROI %)", f"{air.roi_percent}%", f"{sea.roi_percent}%"])
        writer.writerow([])

        # Section 3: Suppliers
        writer.writerow(["نام تأمین‌کننده", "پلتفرم", "قیمت (یوان)", "MOQ", "محل استقرار", "رتبه اعتبار"])
        for s in report.suppliers_china:
            writer.writerow([s.name, s.platform, s.unit_price_cny, s.moq, s.location, s.supplier_tier])

        return output.getvalue()

    def save_reports(self, report: ImportOpportunityReport, filename_prefix: Optional[str] = None) -> tuple[str, str, str]:
        """ذخیره گزارش در سه فرمت مارک‌داون، HTML و CSV با نام فایل امن"""
        import time
        # ساخت نام فایل تمیز و ایمن برای سیستم‌عامل
        slug = "".join(c if (c.isalnum() and ord(c) < 128) else "_" for c in report.product_name_en)
        slug = slug.strip("_")[:30] or "item"
        timestamp = int(time.time())
        prefix = filename_prefix or f"dossier_{slug}_{timestamp}"
        
        md_path = os.path.join(self.output_dir, f"{prefix}.md")
        html_path = os.path.join(self.output_dir, f"{prefix}.html")
        csv_path = os.path.join(self.output_dir, f"{prefix}.csv")

        md_content = self.generate_markdown(report)
        html_content = self.generate_html(report)
        csv_content = self.generate_csv(report)

        with open(md_path, "w", encoding="utf-8") as f:
            f.write(md_content)

        with open(html_path, "w", encoding="utf-8") as f:
            f.write(html_content)

        with open(csv_path, "w", encoding="utf-8") as f:
            f.write(csv_content)

        return md_path, html_path, csv_path
