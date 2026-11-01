"""
سامانه هوشمند واردات از چین به ایران - طراحی فول‌کانواس مینیمال و نئومورفیک
رفع کامل خطوط اضافی، حذف سایدبار مزاحم و یکپارچه‌سازی کامل صفحه مطابق تصویر مرجع
"""

import streamlit as st
import pandas as pd
from config import TradeConfig, CONFIG
from core.agent import ChinaIranImportAgent
from core.report_generator import ReportGenerator
from core.models import ChineseSupplier

# پیکربندی صفحه به صورت تمام‌صفحه بدون سایدبار مزاحم
st.set_page_config(
    page_title="iTrade • سامانه هوشمند واردات از چین",
    page_icon="🇨🇳",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# استایل‌های تمیز، بدون هیچ خط وسط صفحه، کاملاً منطبق بر تصویر مرجع
st.markdown("""
<link href="https://cdn.jsdelivr.net/npm/vazirmatn@33.0.3/Vazirmatn-font-face.css" rel="stylesheet" type="text/css" />
<style>
    /* حذف قطعی تمام المان‌ها، هدرها، فوترها و خط رِسایزر سایدبار */
    #MainMenu, header, footer, 
    div[data-testid="stToolbar"], 
    div[data-testid="stDecoration"], 
    div[data-testid="stStatusWidget"], 
    div[data-testid="stHeader"],
    section[data-testid="stSidebar"],
    div[data-testid="stSidebarCollapseButton"],
    div[data-testid="stSidebarResizer"],
    div[data-baseweb="tab-border"],
    div[data-baseweb="tab-highlight"],
    .stTabs [data-baseweb="tab-border"] {
        display: none !important;
        visibility: hidden !important;
        width: 0 !important;
        height: 0 !important;
        border: none !important;
    }
    
    /* پس‌زمینه سیلور / ابریشمی بسیار نرم و باکلاس مطابق تصویر */
    html, body, .stApp {
        font-family: 'Vazirmatn', -apple-system, BlinkMacSystemFont, sans-serif !important;
        direction: rtl;
        text-align: right;
        background: radial-gradient(circle at 20% 20%, #f4f6fa 0%, #e8edf3 60%, #dfe5ee 100%) !important;
        color: #14171f !important;
        overflow-x: hidden;
    }

    .main .block-container {
        padding: 1.5rem 2rem 3rem 2rem;
        max-width: 1380px;
        margin: 0 auto;
    }

    /* بنر تنظیمات ارزی فوق‌العاده شیک و باریک بالای صفحه به جای سایدبار مزاحم */
    .currency-pill-bar {
        background: rgba(255, 255, 255, 0.7);
        backdrop-filter: blur(20px);
        -webkit-backdrop-filter: blur(20px);
        border: 1px solid rgba(255, 255, 255, 0.9);
        border-radius: 9999px;
        padding: 8px 20px;
        display: flex;
        align-items: center;
        justify-content: space-between;
        margin-bottom: 22px;
        box-shadow: 0 4px 20px rgba(0, 0, 0, 0.02);
    }
    .currency-tag {
        font-size: 13px;
        font-weight: 600;
        color: #475569;
        display: flex;
        align-items: center;
        gap: 6px;
    }
    .currency-val {
        color: #111111;
        font-weight: 800;
    }

    /* تب‌های مونوکروم و مینیمال شبیه عکس (Pills) */
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
        background-color: rgba(255, 255, 255, 0.65);
        backdrop-filter: blur(15px);
        border: 1px solid rgba(255, 255, 255, 0.9);
        border-radius: 9999px;
        padding: 6px;
        margin-bottom: 22px;
        box-shadow: 0 4px 20px rgba(0, 0, 0, 0.02);
        width: fit-content;
    }
    .stTabs [data-baseweb="tab"] {
        border-radius: 9999px;
        padding: 8px 24px;
        background-color: transparent;
        color: #64748b;
        font-weight: 600;
        border: none !important;
        font-size: 14px;
        transition: all 0.2s ease;
    }
    .stTabs [aria-selected="true"] {
        background-color: #111111 !important;
        color: #ffffff !important;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15) !important;
    }

    /* کارت‌های مشکی مات (Dark Matte Cards) مطابق کارت Overall Information تصویر */
    .card-matte-black {
        background: #121316;
        color: #ffffff;
        border-radius: 24px;
        padding: 24px;
        box-shadow: 0 15px 35px rgba(0, 0, 0, 0.14);
        position: relative;
        overflow: hidden;
    }
    .card-matte-black .card-title {
        font-size: 15px;
        font-weight: 600;
        color: #94a3b8;
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 16px;
    }
    .card-matte-black .big-stat {
        font-size: 30px;
        font-weight: 800;
        color: #ffffff;
        line-height: 1.2;
    }
    .card-matte-black .sub-stat {
        font-size: 13px;
        color: #94a3b8;
        margin-top: 4px;
    }

    /* باکس‌های کوچک سفید داخل کارت مشکی (دقیقاً مشابه ۳ باکسی که زیر عکس داخل کارت مشکی است) */
    .mini-stat-grid {
        display: grid;
        grid-template-columns: repeat(3, 1fr);
        gap: 12px;
        margin-top: 22px;
    }
    .mini-stat-card {
        background: #ffffff;
        color: #111111;
        border-radius: 16px;
        padding: 14px 10px;
        text-align: center;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.08);
    }
    .mini-stat-card .val {
        font-size: 16px;
        font-weight: 800;
        color: #111111;
    }
    .mini-stat-card .lbl {
        font-size: 11px;
        font-weight: 600;
        color: #64748b;
        margin-top: 4px;
    }

    /* کارت‌های سفید شیشه‌ای (Light Glass Cards) مطابق کارت‌های Weekly Progress تصویر */
    .card-glass-white {
        background: #ffffff;
        color: #111111;
        border-radius: 24px;
        padding: 24px;
        border: 1px solid rgba(255, 255, 255, 0.9);
        box-shadow: 0 10px 30px rgba(0, 0, 0, 0.035);
        height: 100%;
        display: flex;
        flex-direction: column;
        justify-content: space-between;
    }
    .card-glass-white .card-title {
        font-size: 15px;
        font-weight: 700;
        color: #111111;
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 16px;
    }

    /* رینگ دایره‌ای پیشرفت (مشابه ویجت ۱۲۰٪ سمت راست تصویر) */
    .circle-progress-wrapper {
        text-align: center;
        padding: 10px 0;
    }
    .circle-badge {
        width: 105px;
        height: 105px;
        border-radius: 50%;
        border: 5px solid #111111;
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        margin: 0 auto;
        font-weight: 800;
        font-size: 24px;
        color: #111111;
        background: #f8fafc;
        box-shadow: 0 4px 15px rgba(0, 0, 0, 0.04);
    }
    .circle-badge span {
        font-size: 10px;
        font-weight: 600;
        color: #64748b;
        margin-top: 2px;
    }

    /* ردیف‌های مقایسه مالی */
    .compare-row {
        display: flex;
        justify-content: space-between;
        padding: 9px 0;
        border-bottom: 1px solid #f1f5f9;
        font-size: 13px;
    }
    .compare-row:last-child {
        border-bottom: none;
    }
    .compare-row .lbl {
        color: #64748b;
    }
    .compare-row .val {
        font-weight: 700;
        color: #1e293b;
    }

    /* فیلدهای ورودی استریم‌لیت با گوشه کاملاً گرد و بدون خطوط اضافی */
    input, select, .stTextInput>div>div>input {
        border-radius: 14px !important;
        border: 1px solid #cbd5e1 !important;
        background-color: #ffffff !important;
        color: #0f172a !important;
        font-size: 14px !important;
        padding: 10px 16px !important;
    }
    .stButton>button {
        border-radius: 9999px !important;
        background-color: #111111 !important;
        color: #ffffff !important;
        font-weight: 700 !important;
        padding: 10px 24px !important;
        border: none !important;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1) !important;
    }
</style>
""", unsafe_allow_html=True)

# مقداردهی متغیرهای حالت
if "rmb_rate" not in st.session_state:
    st.session_state.rmb_rate = CONFIG.RMB_TO_TOMAN
if "usd_rate" not in st.session_state:
    st.session_state.usd_rate = CONFIG.USD_TO_TOMAN
if "air_rate" not in st.session_state:
    st.session_state.air_rate = CONFIG.AIR_FREIGHT_USD_PER_KG
if "sea_rate" not in st.session_state:
    st.session_state.sea_rate = CONFIG.SEA_FREIGHT_USD_PER_CBM
if "product_query" not in st.session_state:
    st.session_state.product_query = "ساعت هوشمند"

# ایجاد کانفیگ داینامیک
current_config = TradeConfig(
    RMB_TO_TOMAN=st.session_state.rmb_rate,
    USD_TO_TOMAN=st.session_state.usd_rate,
    AIR_FREIGHT_USD_PER_KG=st.session_state.air_rate,
    SEA_FREIGHT_USD_PER_CBM=st.session_state.sea_rate
)

agent = ChinaIranImportAgent(current_config)
rep_generator = ReportGenerator()

# --- هدر و کادر خلاصه نرخ‌های اقتصادی بالای صفحه (بدون هیچ سایدبار مزاحم) ---
st.markdown(f"""
<div class="currency-pill-bar">
    <div style="display: flex; align-items: center; gap: 8px;">
        <span style="font-size: 18px; font-weight: 900; color: #111111; letter-spacing: -0.5px;">✦ iTrade</span>
        <span style="font-size: 12px; color: #64748b; margin-right: 4px;">سامانه هوشمند واردات کالا از چین</span>
    </div>
    <div style="display: flex; gap: 20px; align-items: center; flex-wrap: wrap;">
        <div class="currency-tag">
            <span>🇨🇳 حواله یوان:</span>
            <span class="currency-val">{st.session_state.rmb_rate:,.0f} تومان</span>
        </div>
        <div class="currency-tag">
            <span>💵 دلار آزاد:</span>
            <span class="currency-val">{st.session_state.usd_rate:,.0f} تومان</span>
        </div>
        <div class="currency-tag">
            <span>✈️ هوایی:</span>
            <span class="currency-val">${st.session_state.air_rate:.1f} / kg</span>
        </div>
        <div class="currency-tag">
            <span>🚢 دریایی:</span>
            <span class="currency-val">${st.session_state.sea_rate:.0f} / CBM</span>
        </div>
    </div>
</div>
""", unsafe_allow_html=True)

# تنظیمات پیشرفته نرخ‌ها در یک کادر کشویی بسیار شیک
with st.expander("⚙️ تغییر نرخ‌های روز ارز و کرایه حمل بین‌المللی"):
    col_t1, col_t2, col_t3, col_t4 = st.columns(4)
    with col_t1:
        st.session_state.rmb_rate = st.number_input("نرخ یوان (تومان):", value=st.session_state.rmb_rate, step=100.0, format="%.0f")
    with col_t2:
        st.session_state.usd_rate = st.number_input("نرخ دلار (تومان):", value=st.session_state.usd_rate, step=500.0, format="%.0f")
    with col_t3:
        st.session_state.air_rate = st.number_input("کرایه هوایی ($/kg):", value=st.session_state.air_rate, step=0.5, format="%.1f")
    with col_t4:
        st.session_state.sea_rate = st.number_input("کرایه دریایی ($/CBM):", value=st.session_state.sea_rate, step=5.0, format="%.0f")

# هدر سلام و جستجو
col_head1, col_head2 = st.columns([3, 1])
with col_head1:
    st.markdown("""
    <div style="margin-bottom: 16px;">
        <h1 style="font-size: 26px; font-weight: 800; color: #111111; margin: 0 0 4px 0;">سلام، واردکننده گرامی! 🇨🇳</h1>
        <p style="font-size: 13px; color: #64748b; margin: 0;">سورسینگ مستقیم از کارخانه‌های چین، پایش قیمت ترب و دیجی‌کالا و محاسبه بهای تمام‌شده گمرک</p>
    </div>
    """, unsafe_allow_html=True)

# تب‌های ناوبری به شکل کپسولی (Pills)
tab1, tab2, tab3, tab4 = st.tabs([
    "داشبورد تحلیلی کالا",
    "رادار فرصت‌های پرسود",
    "ماشین‌حساب گمرک",
    "راهنمای پلتفرم‌ها و سورس"
])

# ==================== تب ۱: داشبورد تحلیلی کالا ====================
with tab1:
    # کپسول‌های دسترسی سریع
    st.markdown("<p style='font-size: 13px; font-weight: 600; color: #64748b; margin-bottom: 8px;'>پیشنهادهای آماده برای تحلیل با یک کلیک:</p>", unsafe_allow_html=True)
    c_p1, c_p2, c_p3, c_p4, c_p5, _ = st.columns([1, 1, 1, 1, 1, 2])
    with c_p1:
        if st.button("⌚ ساعت هوشمند", use_container_width=True):
            st.session_state.product_query = "ساعت هوشمند"
    with c_p2:
        if st.button("🎧 هندزفری نویزکنسلینگ", use_container_width=True):
            st.session_state.product_query = "ایرپاد"
    with c_p3:
        if st.button("🔋 پاوربانک فست‌شارژ", use_container_width=True):
            st.session_state.product_query = "پاوربانک"
    with c_p4:
        if st.button("🪛 دریل شارژی صنعتی", use_container_width=True):
            st.session_state.product_query = "دریل"
    with c_p5:
        if st.button("🛢️ پودر پتروشیمی PVC", use_container_width=True):
            st.session_state.product_query = "پودر PVC"

    # باکس جستجوی مینیمال
    with st.form("search_bar_form"):
        col_s1, col_s2 = st.columns([4, 1])
        with col_s1:
            q_input = st.text_input(
                "نام کالا:",
                value=st.session_state.product_query,
                placeholder="نام کالا را بنویسید (مثلاً: ساعت هوشمند، دریل شارژی، ماساژور، رزین پلیمر...)",
                label_visibility="collapsed"
            )
        with col_s2:
            submitted = st.form_submit_button("+ تحلیل کالا", use_container_width=True)

    # اجرای پردازش و تحلیل
    report = agent.analyze_product(product_query=q_input)
    air = report.air_cost_analysis
    sea = report.sea_cost_analysis
    market = report.iran_market
    best_sup = report.best_supplier

    st.markdown("<div style='height: 10px;'></div>", unsafe_allow_html=True)

    # چیدمان ۳ کارت اصلی بالای صفحه (دقیقاً مشابه ساختار تصویر ارسال‌شده)
    col_card1, col_card2, col_card3 = st.columns([1.3, 1.2, 1.1])

    # کارت ۱: مشکی مات (Overall Information)
    with col_card1:
        st.markdown(f"""
        <div class="card-matte-black">
            <div class="card-title">
                <span>اطلاعات کلی کالا (Overall Information)</span>
                <span style="font-size: 18px;">⋯</span>
            </div>
            <div style="display: flex; justify-content: space-between; align-items: baseline;">
                <div>
                    <div class="big-stat">{sea.net_profit_per_unit_toman:,.0f} ت</div>
                    <div class="sub-stat">سود خالص هر واحد در ایران (حمل دریایی)</div>
                </div>
                <div style="text-align: left;">
                    <div class="big-stat" style="color: #38bdf8;">{sea.roi_percent}%</div>
                    <div class="sub-stat">بازگشت سرمایه (ROI)</div>
                </div>
            </div>
            <!-- ۳ باکس کوچک سفید زیر کارت مشکی دقیقا مطابق تصویر -->
            <div class="mini-stat-grid">
                <div class="mini-stat-card">
                    <div class="val">{air.purchase_price_cny} ¥</div>
                    <div class="lbl">فاکتور چین</div>
                </div>
                <div class="mini-stat-card">
                    <div class="val">{sea.total_landed_cost_toman:,.0f} ت</div>
                    <div class="lbl">بهای تمام‌شده</div>
                </div>
                <div class="mini-stat-card">
                    <div class="val">{market.average_price_toman:,.0f} ت</div>
                    <div class="lbl">فروش در ترب</div>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)

    # کارت ۲: سفید شیشه‌ای (Weekly Progress / مقایسه هوایی و دریایی)
    with col_card2:
        st.markdown(f"""
        <div class="card-glass-white">
            <div class="card-title">
                <span>آنالیز دو روش حمل (Air vs Sea)</span>
                <span style="font-size: 11px; background: #f1f5f9; padding: 4px 10px; border-radius: 9999px; font-weight: 600;">HS: {report.hs_code_estimate}</span>
            </div>
            <div>
                <div class="compare-row">
                    <span class="lbl">کرایه حمل کالا:</span>
                    <span class="val">هوایی {air.international_shipping_toman:,.0f} ت | دریایی {sea.international_shipping_toman:,.0f} ت</span>
                </div>
                <div class="compare-row">
                    <span class="lbl">گمرک + سود بازرگانی:</span>
                    <span class="val">{(sea.customs_duty_toman + sea.commercial_benefit_toman):,.0f} تومان</span>
                </div>
                <div class="compare-row">
                    <span class="lbl">مالیات بر ارزش افزوده (۱۰٪):</span>
                    <span class="val">{sea.vat_toman:,.0f} تومان</span>
                </div>
                <div class="compare-row">
                    <span class="lbl">ترخیص و حمل داخلی:</span>
                    <span class="val">{(sea.clearance_and_brokerage_toman + sea.domestic_logistics_toman):,.0f} تومان</span>
                </div>
                <div class="compare-row" style="background: #f8fafc; padding: 10px; border-radius: 12px; margin-top: 8px;">
                    <span class="lbl" style="font-weight: 700; color: #111111;">سود هر عدد (هوایی vs دریایی):</span>
                    <span class="val" style="color: #111111;">{air.profit_margin_percent}% vs {sea.profit_margin_percent}%</span>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)

    # کارت ۳: سفید شیشه‌ای با نشان دایره‌ای (Month Progress / امتیاز فرصت)
    with col_card3:
        score_val = report.opportunity_score
        st.markdown(f"""
        <div class="card-glass-white">
            <div class="card-title">
                <span>امتیاز فرصت تجاری</span>
                <span style="font-size: 18px;">↗</span>
            </div>
            <div class="circle-progress-wrapper">
                <div class="circle-badge">
                    {score_val}
                    <span>از ۱۰ امتیاز</span>
                </div>
                <div style="font-size: 12px; font-weight: 700; color: #111111; margin-top: 10px;">
                    {sea.profit_margin_percent}% حاشیه سود خالص
                </div>
                <div style="font-size: 11px; color: #64748b;">
                    کشش تقاضا در بازار ایران: عالی
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("<div style='height: 18px;'></div>", unsafe_allow_html=True)

    # ردیف دوم: کارخانه‌های چین و تحلیل بازار در ۲ کارت شکیل سفید
    col_c4, col_c5 = st.columns([1.4, 1.2])

    with col_c4:
        st.markdown("""
        <div class="card-glass-white" style="height: auto;">
            <div class="card-title">
                <span>تامین‌کنندگان منتخب در چین (Verified Suppliers)</span>
                <span style="font-size: 12px; color: #64748b;">1688 • Alibaba • Made-in-China</span>
            </div>
        """, unsafe_allow_html=True)

        for i, s in enumerate(report.suppliers_china[:3], 1):
            st.markdown(f"""
            <div style="padding: 12px 14px; background: #f8fafc; border-radius: 16px; margin-bottom: 10px; display: flex; justify-content: space-between; align-items: center;">
                <div>
                    <div style="font-weight: 800; font-size: 14px; color: #111111;">{i}. {s.name}</div>
                    <div style="font-size: 12px; color: #64748b;">{s.platform} • {s.location}</div>
                </div>
                <div style="text-align: left;">
                    <span style="display: inline-block; background: #111111; color: white; padding: 4px 12px; border-radius: 9999px; font-size: 12px; font-weight: 700;">
                        {s.unit_price_cny} ¥ ({s.unit_price_usd or round(s.unit_price_cny/7.1, 2)} $)
                    </span>
                    <div style="font-size: 11px; color: #64748b; margin-top: 3px;">حداقل سفارش: {s.moq} عدد</div>
                </div>
            </div>
            """, unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)

    with col_c5:
        st.markdown(f"""
        <div class="card-glass-white" style="height: auto;">
            <div class="card-title">
                <span>پایش بازار ایران در ترب و مجوزهای الزامی</span>
                <span style="font-size: 12px; color: #64748b;">Torob & NTSW</span>
            </div>
            <div style="padding: 12px 14px; background: #f8fafc; border-radius: 16px; margin-bottom: 12px;">
                <div style="display: flex; justify-content: space-between; font-size: 13px; margin-bottom: 6px;">
                    <span style="color: #64748b;">کف قیمت بازار:</span>
                    <span style="font-weight: 700; color: #111111;">{market.lowest_price_toman:,.0f} تومان</span>
                </div>
                <div style="display: flex; justify-content: space-between; font-size: 13px; margin-bottom: 6px;">
                    <span style="color: #64748b;">میانگین قیمت فروش:</span>
                    <span style="font-weight: 700; color: #111111;">{market.average_price_toman:,.0f} تومان</span>
                </div>
                <div style="display: flex; justify-content: space-between; font-size: 13px;">
                    <span style="color: #64748b;">تعداد فروشگاه‌های فعال:</span>
                    <span style="font-weight: 700; color: #111111;">{market.active_sellers_count} فروشگاه آنلاین</span>
                </div>
            </div>
            <div style="font-size: 12px; color: #475569; line-height: 1.6;">
        """, unsafe_allow_html=True)

        for note in report.regulatory_notes[:2]:
            st.markdown(f"<p style='margin: 4px 0;'>✔ {note}</p>", unsafe_allow_html=True)

        st.markdown("</div></div>", unsafe_allow_html=True)

    # دکمه دانلود گزارش شکیل دقیقا مشابه دکمه کپسولی Download Report در عکس
    st.markdown("<div style='height: 15px;'></div>", unsafe_allow_html=True)
    html_data = rep_generator.generate_html(report)

    d_col1, d_col2 = st.columns([1, 1])
    with d_col1:
        st.download_button(
            label="📥 دانلود شناسنامه کامل کالا (Download Report - HTML)",
            data=html_data.encode("utf-8"),
            file_name=f"dossier_{q_input}.html",
            mime="text/html",
            use_container_width=True
        )
    with d_col2:
        md_data = rep_generator.generate_markdown(report)
        st.download_button(
            label="📄 دانلود نسخه مارک‌داون (Markdown)",
            data=md_data.encode("utf-8"),
            file_name=f"dossier_{q_input}.md",
            mime="text/markdown",
            use_container_width=True
        )

# ==================== تب ۲: شکار فرصت‌های وارداتی ====================
with tab2:
    st.markdown("""
    <div style="margin-bottom: 18px;">
        <h2 style="font-size: 22px; font-weight: 800; color: #111111; margin: 0 0 4px 0;">🚀 رادار شکار فرصت‌های وارداتی</h2>
        <p style="font-size: 13px; color: #64748b; margin: 0;">پایش کالاهایی که بیشترین سودآوری (آربیتراژ) بین چین و ایران را دارند</p>
    </div>
    """, unsafe_allow_html=True)

    c_cat, c_filter = st.columns([3, 2])
    with c_cat:
        cat_select = st.selectbox(
            "دسته‌بندی بازار:",
            ["گجت‌ها و الکترونیک مصرفی", "ابزارآلات و صنعتی", "لوازم خانه و آشپزخانه", "مواد اولیه و پتروشیمی"]
        )
    with c_filter:
        min_m = st.slider("حداقل حاشیه سود مورد انتظار (%):", 15.0, 50.0, 20.0, step=5.0)

    if st.button("اسکن فرصت‌های پرسود", use_container_width=True):
        opps = agent.find_opportunities(category=cat_select, min_margin_percent=min_m)
        if opps:
            for idx, op in enumerate(opps, 1):
                sea_op = op.sea_cost_analysis
                market_op = op.iran_market
                sup_op = op.best_supplier

                st.markdown(f"""
                <div style="background: #ffffff; border-radius: 20px; padding: 18px 22px; margin-bottom: 12px; box-shadow: 0 6px 20px rgba(0,0,0,0.03); display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 15px;">
                    <div>
                        <div style="font-weight: 800; font-size: 16px; color: #111111;">{idx}. {op.product_name_fa}</div>
                        <div style="font-size: 12px; color: #64748b; margin-top: 3px;">کارخانه چین: {sup_op.name[:30] if sup_op else '-'}</div>
                    </div>
                    <div style="display: flex; gap: 20px; text-align: center;">
                        <div>
                            <div style="font-size: 11px; color: #64748b;">بهای تمام‌شده</div>
                            <div style="font-weight: 800; color: #111111; font-size: 14px;">{sea_op.total_landed_cost_toman:,.0f} ت</div>
                        </div>
                        <div>
                            <div style="font-size: 11px; color: #64748b;">فروش در ترب</div>
                            <div style="font-weight: 800; color: #111111; font-size: 14px;">{market_op.average_price_toman:,.0f} ت</div>
                        </div>
                        <div>
                            <div style="font-size: 11px; color: #64748b;">سود خالص هر عدد</div>
                            <div style="font-weight: 800; color: #111111; font-size: 14px;">{sea_op.net_profit_per_unit_toman:,.0f} ت</div>
                        </div>
                    </div>
                    <div>
                        <span style="background: #111111; color: white; padding: 6px 14px; border-radius: 9999px; font-size: 12px; font-weight: 700;">
                            {sea_op.profit_margin_percent}% سود (ROI {sea_op.roi_percent}%)
                        </span>
                    </div>
                </div>
                """, unsafe_allow_html=True)

# ==================== تب ۳: ماشین‌حساب سریع ====================
with tab3:
    st.markdown("""
    <div style="margin-bottom: 18px;">
        <h2 style="font-size: 22px; font-weight: 800; color: #111111; margin: 0 0 4px 0;">🧮 ماشین‌حساب سریع بهای تمام‌شده و سود</h2>
        <p style="font-size: 13px; color: #64748b; margin: 0;">محاسبه لحظه‌ای قیمت تمام‌شده در انبار ایران بر اساس فاکتور پروفرما</p>
    </div>
    """, unsafe_allow_html=True)

    mc1, mc2, mc3 = st.columns(3)
    with mc1:
        calc_cny = st.number_input("قیمت هر عدد در فاکتور چین (یوان):", value=35.0, step=5.0)
        calc_kg = st.number_input("وزن ناخالص هر عدد (کیلوگرم):", value=0.25, step=0.05)
    with mc2:
        calc_iran_target = st.number_input("قیمت فروش هدف شما در بازار ایران (تومان):", value=1350000, step=50000)
        calc_cbm = st.number_input("حجم هر کارتن (CBM):", value=0.001, step=0.0005)
    with mc3:
        calc_qty = st.number_input("تعداد سفارش در این پارت:", value=200, step=50)

    dummy_sup = ChineseSupplier(
        name="Factory Direct",
        platform="1688",
        product_title="Quick Calculator",
        unit_price_cny=calc_cny,
        weight_kg=calc_kg,
        volume_cbm=calc_cbm,
        moq=calc_qty
    )
    res_s = agent.calculator.calculate_landed_cost(dummy_sup, calc_iran_target, "Sea Freight", batch_quantity=calc_qty)

    st.markdown("<div style='height: 12px;'></div>", unsafe_allow_html=True)
    st.markdown(f"""
    <div class="card-matte-black">
        <div class="card-title">
            <span>نتیجه محاسبات اقتصادی (Landed Cost Result)</span>
            <span style="font-size: 18px;">💰</span>
        </div>
        <div style="display: flex; justify-content: space-between; align-items: baseline;">
            <div>
                <div class="big-stat">{res_s.net_profit_per_unit_toman:,.0f} تومان</div>
                <div class="sub-stat">سود خالص به ازای هر عدد در ایران</div>
            </div>
            <div style="text-align: left;">
                <div class="big-stat" style="color: #38bdf8;">{res_s.total_net_profit_toman:,.0f} تومان</div>
                <div class="sub-stat">سود کل این سفارش ({calc_qty} عددی)</div>
            </div>
        </div>
        <div class="mini-stat-grid">
            <div class="mini-stat-card">
                <div class="val">{res_s.total_landed_cost_toman:,.0f} ت</div>
                <div class="lbl">بهای تمام‌شده هر عدد</div>
            </div>
            <div class="mini-stat-card">
                <div class="val">{res_s.profit_margin_percent}%</div>
                <div class="lbl">حاشیه سود خالص</div>
            </div>
            <div class="mini-stat-card">
                <div class="val">{res_s.roi_percent}%</div>
                <div class="lbl">نرخ بازگشت سرمایه (ROI)</div>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

# ==================== تب ۴: راهنمای سورسینگ و گیت‌هاب ====================
with tab4:
    st.markdown("""
    <div class="card-glass-white">
        <h3 style="font-size: 18px; margin-top: 0; color: #111111;">🇨🇳 راهنمای استراتژیک خرید از چین</h3>
        <p style="font-size: 13px; color: #64748b; line-height: 1.8;">
            • <strong>چرا ۱۶۸۸؟</strong> قیمت‌های 1688.com نرخ واقعی کارخانه‌های داخلی چین است و بین ۲۰ تا ۵۰ درصد ارزان‌تر از علی‌بابا عرضه می‌شود.<br>
            • <strong>فورواردر و کارگو:</strong> برای خرید از ۱۶۸۸ نیازی به کارت بانکی چین نیست؛ شرکت‌های حمل (کارگو) در شهرهای گوانگجو، شنژن و ایوو کالا را تحویل گرفته و در ایران ترخیص می‌کنند.<br>
            • <strong>پتروشیمی و پلیمر:</strong> پلتفرم‌های ChemNet و EChemi مرجع اصلی قیمت‌های تخصصی مواد پلیمری و شیمیایی هستند.
        </p>
        <hr style="border: none; border-top: 1px solid #e2e8f0; margin: 15px 0;">
        <h3 style="font-size: 18px; margin-top: 0; color: #111111;">🛠️ ابزارهای برتر اوپن‌سورس در گیت‌هاب</h3>
        <p style="font-size: 13px; color: #64748b; line-height: 1.8;">
            • <strong>superjack2050/1688-cli:</strong> ابزار خط فرمان برای استخراج مستقیم اطلاعات کارخانه‌ها از ۱۶۸۸.<br>
            • <strong>omkarcloud/alibaba-scraper:</strong> استخراج‌کننده ساختاریافته قیمت‌های پلکانی و مشخصات علی‌بابا.<br>
            • <strong>Carmenliukang/1688_crawler-image_search:</strong> جستجوی معکوس تصویری بر اساس عکس کالا.
        </p>
    </div>
    """, unsafe_allow_html=True)
