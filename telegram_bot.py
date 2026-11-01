"""
Telegram Bot Interface for China-to-Iran Import Intelligence & Arbitrage Agent.
Provides mobile-friendly access to sourcing data, price analysis, and landed costs.

Run:
  python telegram_bot.py
Requires:
  TELEGRAM_BOT_TOKEN in config.py or environment variable.
"""

import os
import sys
import asyncio
from config import CONFIG
from core.agent import ChinaIranImportAgent
from core.report_generator import ReportGenerator

# Ensure UTF-8
if sys.stdout.encoding.lower() != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

agent = ChinaIranImportAgent()
rep_gen = ReportGenerator()

async def start_command(update, context):
    welcome_text = """
👋 **سلام به ربات دستیار هوشمند واردات از چین به ایران خوش آمدید!** 🇨🇳 ➡️ 🇮🇷

من به شما و واردکنندگان کمک می‌کنم تا:
۱. قیمت واقعی کارخانه‌های چین (1688، علی‌بابا، Made-in-China، ChemNet) را پیدا کنید.
۲. قیمت‌های فروش همان کالا در بازار ایران (ترب، دیجی‌کالا، بازار آزاد) را پایش کنید.
۳. بهای تمام‌شده گمرکی، کرایه حمل هوایی/دریایی و سود خالص را دقیق محاسبه کنید.
۴. فرصت‌های طلایی و کالاهای پرسود را شکار کنید.

📌 **راهنمای دستورات:**
🔍 `نام کالا` (مثلاً: `ساعت هوشمند` یا `پودر PVC`)
🚀 `/scan` : مشاهده فرصت‌های پرسود در گجت‌ها و پتروشیمی
🧮 `/calc 35 1400000` : محاسبه سریع (قیمت به یوان + قیمت فروش در ایران)
    """
    await update.message.reply_text(welcome_text, parse_mode="Markdown")

async def scan_command(update, context):
    await update.message.reply_text("⏳ در حال اسکن بازار چین و ایران برای یافتن پرسودترین کالاها...")
    opps = agent.find_opportunities("گجت‌ها و الکترونیک مصرفی", min_margin_percent=25.0)

    lines = ["💎 **فرصت‌های برتر واردات (گجت‌ها و الکترونیک):**\n"]
    for i, opp in enumerate(opps[:5], 1):
        sea = opp.sea_cost_analysis
        market = opp.iran_market
        lines.append(
            f"{i}. **{opp.product_name_fa}**\n"
            f"   🏷️ بهای تمام‌شده دریایی: {sea.total_landed_cost_toman:,} ت\n"
            f"   🛒 فروش در بازار ایران: {market.average_price_toman:,} ت\n"
            f"   📈 حاشیه سود: {sea.profit_margin_percent}% | بازگشت سرمایه: {sea.roi_percent}%\n"
            f"   ⭐ امتیاز فرصت: {opp.opportunity_score}/10\n"
        )
    lines.append("برای دریافت شناسنامه هر کالا، نام آن را بفرستید.")
    await update.message.reply_text("\n".join(lines), parse_mode="Markdown")

async def analyze_message(update, context):
    query = update.message.text.strip()
    if query.startswith("/"):
        return

    await update.message.reply_text(f"🔍 در حال استعلام کارخانه‌های چین و تحلیل بازار ایران برای: «{query}»...")

    report = agent.analyze_product(query)
    air = report.air_cost_analysis
    sea = report.sea_cost_analysis
    market = report.iran_market
    best_sup = report.best_supplier

    msg = f"""
🇨🇳 **شناسنامه تحلیل واردات: {report.product_name_fa}**
⭐ **امتیاز جذابیت فرصت:** {report.opportunity_score} از ۱۰
🏷️ **کد تعرفه تخمینی (HS Code):** `{report.hs_code_estimate}`

🏭 **کارخانه منتخب در چین:**
• نام: {best_sup.name if best_sup else 'کارخانه معتبر'}
• پلتفرم: {best_sup.platform if best_sup else '1688.com'}
• قیمت فاکتور: {best_sup.unit_price_cny if best_sup else '-'} یوان ({best_sup.unit_price_usd or '-'} دلار)
• حداقل سفارش (MOQ): {best_sup.moq if best_sup else 100} واحد
• محل کارخانه: {best_sup.location if best_sup else 'چین'}

🇮🇷 **قیمت در بازار ایران (ترب و دیجی‌کالا):**
• کف قیمت: {market.lowest_price_toman:,} تومان
• میانگین فروش: {market.average_price_toman:,} تومان
• سقف قیمت: {market.highest_price_toman:,} تومان

💰 **آنالیز بهای تمام‌شده و سود در ایران:**
✈️ **روش حمل هوایی (Air Cargo):**
• بهای تمام‌شده هر عدد: {air.total_landed_cost_toman:,} تومان
• سود خالص هر عدد: {air.net_profit_per_unit_toman:,} تومان
• حاشیه سود: {air.profit_margin_percent}% (ROI: {air.roi_percent}%)

🚢 **روش حمل دریایی (Sea Freight):**
• بهای تمام‌شده هر عدد: {sea.total_landed_cost_toman:,} تومان
• سود خالص هر عدد: {sea.net_profit_per_unit_toman:,} تومان
• حاشیه سود: {sea.profit_margin_percent}% (ROI: {sea.roi_percent}%)

💡 **توصیه استراتژیک:**
{report.recommendation_summary}
    """
    await update.message.reply_text(msg, parse_mode="Markdown")

def main():
    token = CONFIG.TELEGRAM_BOT_TOKEN or os.getenv("TELEGRAM_BOT_TOKEN")
    if not token:
        print("[!] برای راه‌اندازی ربات تلگرام، توکن ربات را در فایل config.py یا متغیر TELEGRAM_BOT_TOKEN ست کنید.")
        print("    نمونه: set TELEGRAM_BOT_TOKEN=123456:ABC-DEF...")
        return

    from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters
    print("[*] ربات تلگرام دستیار واردات در حال راه‌اندازی است...")
    app = ApplicationBuilder().token(token).build()

    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("scan", scan_command))
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), analyze_message))

    app.run_polling()

if __name__ == "__main__":
    main()
