"""
CLI Interface for China-to-Iran Import Intelligence & Arbitrage Agent.
Run commands:
  python cli.py analyze "ساعت هوشمند"
  python cli.py analyze "پودر PVC"
  python cli.py scan "گجت‌ها و الکترونیک مصرفی"
  python cli.py scan "مواد اولیه و پتروشیمی"
  python cli.py calc --price-cny 48 --iran-price 1750000 --weight 0.2
"""

import sys
import io

# Ensure UTF-8 output on Windows consoles
if sys.stdout.encoding.lower() != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

import argparse
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.markdown import Markdown

from config import CONFIG
from core.agent import ChinaIranImportAgent
from core.report_generator import ReportGenerator
from core.models import ChineseSupplier

console = Console()

def print_banner():
    banner = """
    ╔══════════════════════════════════════════════════════════════════╗
    ║   🇨🇳 ➡️ 🇮🇷  China-to-Iran Import Intelligence & Arbitrage Agent ║
    ║   سیستم هوشمند سورسینگ از کارخانه‌های چین، بازار ایران و آربیتراژ  ║
    ╚══════════════════════════════════════════════════════════════════╝
    """
    console.print(f"[bold cyan]{banner}[/bold cyan]")

def handle_analyze(args):
    print_banner()
    agent = ChinaIranImportAgent()
    rep_gen = ReportGenerator()

    console.print(f"[bold yellow]🔍 در حال پردازش سورسینگ چین و پایش بازار ایران برای:[/bold yellow] [bold white]«{args.product}»[/bold white]...\n")

    report = agent.analyze_product(
        product_query=args.product,
        category=args.category,
        custom_target_iran_price=args.target_price,
        batch_quantity=args.quantity
    )

    # 1. کارت خلاصه فرصت
    summary_text = (
        f"[bold]دسته‌بندی:[/bold] {report.category} | [bold]کد تعرفه HS Code:[/bold] {report.hs_code_estimate}\n"
        f"[bold]امتیاز جذابیت واردات:[/bold] [bold green]{report.opportunity_score} / 10[/bold green]\n"
        f"[bold]توصیه استراتژیک:[/bold] {report.recommendation_summary}"
    )
    console.print(Panel(summary_text, title=f"🎯 شناسنامه فرصت: {report.product_name_fa}", border_style="cyan"))

    # 2. جدول کارخانه‌های چین
    sup_table = Table(title="🏭 کارخانه‌ها و تامین‌کنندگان منتخب چین (1688 / Alibaba / ChemNet)", border_style="blue")
    sup_table.add_column("ردیف", style="dim", width=6)
    sup_table.add_column("نام کارخانه و پلتفرم", style="bold white")
    sup_table.add_column("قیمت پایه (یوان / دلار)", style="green")
    sup_table.add_column("حداقل سفارش (MOQ)", style="yellow")
    sup_table.add_column("محل استقرار کارخانه", style="cyan")
    sup_table.add_column("اعتبار و رتبه", style="magenta")

    for i, s in enumerate(report.suppliers_china, 1):
        sup_table.add_row(
            str(i),
            f"{s.name}\n[dim]{s.platform}[/dim]",
            f"{s.unit_price_cny} ¥ ({s.unit_price_usd or round(s.unit_price_cny/7.1, 2)} $)",
            f"{s.moq} عدد",
            s.location,
            s.supplier_tier
        )
    console.print(sup_table)
    console.print("")

    # 3. جدول مقایسه مالی بهای تمام‌شده و سودآوری در ایران
    air = report.air_cost_analysis
    sea = report.sea_cost_analysis
    fin_table = Table(title="💰 مقایسه اقتصادی بهای تمام‌شده و سود در بازار ایران (Air vs Sea)", border_style="green")
    fin_table.add_column("شاخص مالی / آیتم هزینه", style="bold")
    fin_table.add_column("حمل هوایی (Air Cargo)", style="cyan")
    fin_table.add_column("حمل دریایی (Sea Freight)", style="blue")

    if air and sea:
        fin_table.add_row("قیمت خرید فاکتور چین", f"{air.purchase_price_toman:,} ت", f"{sea.purchase_price_toman:,} ت")
        fin_table.add_row("کرایه حمل بین‌المللی", f"{air.international_shipping_toman:,} ت", f"{sea.international_shipping_toman:,} ت")
        fin_table.add_row("حقوق گمرکی و سود بازرگانی", f"{(air.customs_duty_toman + air.commercial_benefit_toman):,} ت", f"{(sea.customs_duty_toman + sea.commercial_benefit_toman):,} ت")
        fin_table.add_row("مالیات بر ارزش افزوده (۱۰٪)", f"{air.vat_toman:,} ت", f"{sea.vat_toman:,} ت")
        fin_table.add_row("ترخیص، انبارداری و حمل داخلی", f"{(air.clearance_and_brokerage_toman + air.domestic_logistics_toman):,} ت", f"{(sea.clearance_and_brokerage_toman + sea.domestic_logistics_toman):,} ت")
        fin_table.add_row("[bold yellow]بهای تمام‌شده هر واحد در ایران[/bold yellow]", f"[bold yellow]{air.total_landed_cost_toman:,} ت[/bold yellow]", f"[bold yellow]{sea.total_landed_cost_toman:,} ت[/bold yellow]")
        fin_table.add_row("قیمت فروش هدف در بازار ایران (ترب)", f"{air.target_selling_price_toman:,} ت", f"{sea.target_selling_price_toman:,} ت")
        fin_table.add_row("[bold green]سود خالص هر واحد[/bold green]", f"[bold green]{air.net_profit_per_unit_toman:,} ت[/bold green]", f"[bold green]{sea.net_profit_per_unit_toman:,} ت[/bold green]")
        fin_table.add_row("[bold magenta]حاشیه سود خالص (Margin)[/bold magenta]", f"[bold magenta]{air.profit_margin_percent}%[/bold magenta]", f"[bold magenta]{sea.profit_margin_percent}%[/bold magenta]")
        fin_table.add_row("[bold red]نرخ بازگشت سرمایه (ROI)[/bold red]", f"[bold red]{air.roi_percent}%[/bold red]", f"[bold red]{sea.roi_percent}%[/bold red]")
        fin_table.add_row(f"سود کل پارت ({air.batch_quantity} عددی)", f"[bold green]{air.total_net_profit_toman:,} ت[/bold green]", f"[bold green]{sea.total_net_profit_toman:,} ت[/bold green]")
    console.print(fin_table)

    # 4. ذخیره گزارشات
    md_file, html_file = rep_gen.save_reports(report)
    console.print(f"\n[bold green]✔ گزارش جامع با موفقیت ذخیره شد:[/bold green]")
    console.print(f"  📄 فرمت مارک‌داون: [cyan]{md_file}[/cyan]")
    console.print(f"  🌐 فرمت وب تعاملی HTML: [cyan]{html_file}[/cyan]\n")

def handle_scan(args):
    print_banner()
    agent = ChinaIranImportAgent()
    console.print(f"[bold yellow]🚀 در حال پویش بازار چین و ایران برای یافتن بهترین فرصت‌های:[/bold yellow] [bold cyan]«{args.category}»[/bold cyan]...\n")

    opportunities = agent.find_opportunities(category=args.category, min_margin_percent=args.min_margin)

    opp_table = Table(title=f"💎 فرصت‌های طلایی واردات در حوزه {args.category}", border_style="gold1")
    opp_table.add_column("رتبه", style="dim", width=5)
    opp_table.add_column("نام کالا", style="bold white")
    opp_table.add_column("تامین‌کننده چین", style="cyan")
    opp_table.add_column("بهای تمام‌شده (ایران)", style="yellow")
    opp_table.add_column("فروش در بازار ایران", style="white")
    opp_table.add_column("حاشیه سود", style="bold green")
    opp_table.add_column("ROI %", style="bold red")
    opp_table.add_column("امتیاز", style="bold magenta")

    for i, opp in enumerate(opportunities, 1):
        air = opp.air_cost_analysis
        market = opp.iran_market
        sup = opp.best_supplier
        opp_table.add_row(
            str(i),
            opp.product_name_fa,
            sup.name[:25] if sup else "-",
            f"{air.total_landed_cost_toman:,} ت" if air else "-",
            f"{market.average_price_toman:,} ت" if market else "-",
            f"{air.profit_margin_percent}%" if air else "-",
            f"{air.roi_percent}%" if air else "-",
            f"⭐ {opp.opportunity_score}"
        )

    console.print(opp_table)
    console.print(f"\n[green]تعداد {len(opportunities)} کالای پرسود شناسایی شد. برای مشاهده شناسنامه هر کدام دستور زیر را اجرا کنید:[/green]")
    if opportunities:
        sample = opportunities[0].product_name_fa
        console.print(f"[white]python cli.py analyze \"{sample}\"[/white]\n")

def main():
    parser = argparse.ArgumentParser(description="China-to-Iran Import Intelligence & Arbitrage Agent")
    subparsers = parser.add_subparsers(dest="command", help="دستورات در دسترس")

    # analyze
    analyze_parser = subparsers.add_parser("analyze", help="تحلیل جامع یک محصول مشخص")
    analyze_parser.add_argument("product", type=str, help="نام کالا (مثلا: ساعت هوشمند، پودر PVC)")
    analyze_parser.add_argument("--category", type=str, default=None, help="دسته‌بندی کالا")
    analyze_parser.add_argument("--target-price", type=float, default=None, help="قیمت فروش هدف در ایران (تومان)")
    analyze_parser.add_argument("--quantity", type=int, default=None, help="تعداد سفارش در یک پارت")

    # scan
    scan_parser = subparsers.add_parser("scan", help="شکار فرصت‌های پرسود در یک دسته‌بندی")
    scan_parser.add_argument("category", type=str, default="گجت‌ها و الکترونیک مصرفی", nargs="?", help="نام دسته‌بندی")
    scan_parser.add_argument("--min-margin", type=float, default=30.0, help="حداقل حاشیه سود درصد (پیش‌فرض: 30%)")

    args = parser.parse_args()

    if args.command == "analyze":
        handle_analyze(args)
    elif args.command == "scan":
        handle_scan(args)
    else:
        print_banner()
        parser.print_help()

if __name__ == "__main__":
    main()
