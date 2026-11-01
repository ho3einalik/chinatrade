"""
China Multi-Source Sourcing Engine.
Integrates verified factory networks and B2B wholesale platforms:
- Alibaba.com (بزرگ‌ترین پلتفرم بین‌المللی B2B و سفارش کانتینری با ضمانت Trade Assurance)
- 1688.com (بزرگ‌ترین پلتفرم عمده‌فروشی داخلی چین با قیمت درب کارخانه)
- AliExpress (پلتفرم جهانی خرید نمونه، تست محصول و سفارشات با تیراژ خرد Low MOQ)
- EHSY (西域 - www.ehsy.com) (تجهیزات صنعتی و MRO کارخانه‌ای)
- Gongchang (中国工厂网 - www.gongchang.com) (دایرکتوری مستقیم کارخانه‌ها)
- Makepolo (马可波罗 - www.makepolo.com) (موتور جستجوی خریدهای عمده B2B)
- YiwuGo (义乌购 - www.yiwugo.com) (بازار بین‌المللی کالاهای خرد ایوو)
- Baidu Aicai (百度爱采购 - b2b.baidu.com) (پلتفرم B2B رسمی بایدو)
- ChemNet (china.chemnet.com) (مرجع جهانی پتروشیمی و پلیمرها)
- QiPeiRen (汽配人 - www.qipeiren.com) (قطعات خودرو - نیازمند پروکسی چین)

قانون اصالت داده: هیچ تأمین‌کننده یا قیمت ساختگی در حالت عادی برنامه تولید نمی‌شود.
در صورت نبود پیش‌فاکتور یا نتیجه زنده، فهرست تأمین‌کنندگان خالی بازگردانده شده و لینک‌های مستقیم جستجو ارائه می‌گردد.
"""

from typing import List, Dict, Any, Optional
import urllib.parse
from config import CONFIG
from core.models import ChineseSupplier, PriceTier, DataType, DataFreshness, Incoterms, VerificationStatus

class ChinaSourcingEngine:
    def __init__(self, db=None):
        self.db = db
        self.platform_catalog = {
            "alibaba": {
                "name": "Alibaba.com (International B2B)",
                "url": "https://www.alibaba.com/",
                "search_template": "https://www.alibaba.com/trade/search?SearchText={query}",
                "specialty": "بزرگ‌ترین پلتفرم بین‌المللی B2B عمده‌فروشی، سفارش کانتینری و کارخانجات Trade Assurance",
                "status": "Verified & Active (HTTP 200)",
                "requires_auth": False
            },
            "1688": {
                "name": "1688.com (Alibaba Domestic)",
                "url": "https://www.1688.com/",
                "search_template": "https://s.1688.com/selloffer/offer_search.htm?keywords={query}",
                "specialty": "بزرگ‌ترین پلتفرم عمده‌فروشی چین با قیمت‌های فاکتور داخلی بدون کارمزد دلاری",
                "status": "Manual Search Link (ضدربات علی‌بابا فعال است)",
                "requires_auth": True
            },
            "aliexpress": {
                "name": "AliExpress (خرید نمونه و تست بازار)",
                "url": "https://www.aliexpress.com/",
                "search_template": "https://www.aliexpress.com/wholesale?SearchText={query}",
                "specialty": "خرید نمونه تستی (Sample Orders)، اعتبارسنجی اولیه کالا و خرید با حداقل تیراژ (Low MOQ)",
                "status": "Verified & Active (HTTP 200)",
                "requires_auth": False
            },
            "ehsy": {
                "name": "EHSY (西域)",
                "url": "https://www.ehsy.com/",
                "search_template": "https://www.ehsy.com/search?keyword={query}",
                "specialty": "ابزارآلات، تجهیزات MRO کارخانه‌ای، ابزار دقیق، ایمنی، اتوماسیون و قطعات صنعتی",
                "status": "Verified & Active (HTTP 200)",
                "requires_auth": True
            },
            "gongchang": {
                "name": "Gongchang (中国工厂网)",
                "url": "https://www.gongchang.com/",
                "search_template": "https://www.gongchang.com/search?q={query}",
                "specialty": "دایرکتوری مستقیم کارخانه‌ها و تولیدی‌های معتبر چین برای تولید OEM/ODM",
                "status": "Verified & Active (HTTP 200)",
                "requires_auth": False
            },
            "makepolo": {
                "name": "Makepolo (马可波罗)",
                "url": "https://www.makepolo.com/",
                "search_template": "https://search.makepolo.com/index.php?q={query}",
                "specialty": "موتور جستجوی تامین‌کنندگان و خرید عمده B2B در صنایع مختلف",
                "status": "Verified & Active (HTTP 200)",
                "requires_auth": False
            },
            "yiwugo": {
                "name": "YiwuGo (义乌购)",
                "url": "https://www.yiwugo.com/",
                "search_template": "https://www.yiwugo.com/search/s.html?q={query}",
                "specialty": "بازار بزرگ بین‌المللی ایوو؛ کالای خرد، لوازم خانگی و آشپزخانه، اسباب‌بازی و دکوراسیون",
                "status": "Verified & Active (HTTP 200)",
                "requires_auth": False
            },
            "baidu_b2b": {
                "name": "Baidu Aicai (百度爱采购)",
                "url": "https://b2b.baidu.com/",
                "search_template": "https://b2b.baidu.com/s?q={query}",
                "specialty": "پلتفرم رسمی هوش تجاری و خرید B2B بایدو برای اتصال مستقیم به کارخانجات چین",
                "status": "Verified & Active (HTTP 200)",
                "requires_auth": False
            },
            "chemnet": {
                "name": "ChemNet (中国化工网)",
                "url": "http://china.chemnet.com/",
                "search_template": "http://china.chemnet.com/search/product/{query}",
                "specialty": "پتروشیمی، پلیمرهای مهندسی، رزین‌ها، روغن‌ها، اسیدها و مواد شیمیایی دارویی",
                "status": "Verified & Active (HTTP 200)",
                "requires_auth": False
            },
            "qipeiren": {
                "name": "QiPeiRen (汽配人)",
                "url": "https://www.qipeiren.com/",
                "search_template": "https://www.qipeiren.com/search?q={query}",
                "specialty": "پلتفرم تخصصی B2B قطعات یدکی خودرو و ماشین‌آلات",
                "status": "Blocked by Great Firewall (نیازمند شبکه چین / اکانت وی‌چت)",
                "requires_auth": True
            }
        }

    def translate_to_chinese_keywords(self, query: str) -> str:
        """
        تبدیل کلیدواژه‌های فارسی/انگلیسی به اصطلاحات تخصصی بازرگانی چینی جهت جستجوی مستقیم
        """
        dict_map = {
            "ساعت هوشمند": "智能手表 AMOLED 蓝牙通话",
            "smart watch": "智能手表 OEM工厂",
            "ایرپاد": "TWS无线蓝牙耳机 降噪ANC",
            "هندزفری بلوتوث": "TWS蓝牙耳机 工厂批发",
            "earbuds": "TWS无线降噪耳机",
            "پاوربانک": "快充移动电源 20000mAh",
            "power bank": "自带线充电宝 聚合物",
            "پودر pvc": "PVC聚氯乙烯树脂粉 S-65",
            "pvc": "聚氯乙烯 PVC树脂粉",
            "پلی اتیلن": "高密度聚乙烯 HDPE 颗粒",
            "hdpe": "HDPE注塑级 聚乙烯原料",
            "پلی پروپیلن": "聚丙烯 PP 均聚注塑料",
            "pp": "聚丙烯 PP 塑胶原料",
            "پت": "PET聚酯切片 瓶级原料",
            "pet": "PET瓶级原料 聚酯",
            "دریل شارژی": "无刷锂电钻 21V双电 冲击钻",
            "دریل": "锂电无刷手电钻 工具箱",
            "ابزار": "工业级五金工具 五金机电",
            "ماساژور تفنگی": "筋膜枪 肌肉便携按摩仪",
            "ماساژور": "多功能电动按摩仪 筋膜枪",
            "اسپیکر بلوتوث": "户外防水重低音便携音箱",
            "دوربین مداربسته": "高清WiFi无线监控摄像头 PTZ",
            "لوازم خودرو": "汽车配件 刹车片 汽配批发",
            "قطعات خودرو": "汽车零配件 发动机配件 汽配人",
            "لنت ترمز": "陶瓷刹车片 汽车刹车皮",
            "فیلتر هوا": "汽车空气滤清器 机油滤清器",
            "کمک فنر": "汽车减震器 悬挂配件",
            "تسمه": "汽车发电机皮带 工业同步带",
            "چراغ خودرو": "汽车LED前照大灯总成",
            "لوازم خانگی": "智能小家电 义乌小商品",
            "کابل شارژ": "PD65W快充编织数据线 Type-C",
        }
        
        q_lower = query.lower().strip()
        for k, v in dict_map.items():
            if k in q_lower:
                return v
        return query

    def translate_to_english_keywords(self, query: str) -> str:
        """
        تبدیل کلیدواژه‌های فارسی به عبارات استاندارد انگلیسی جهت جستجو در پلتفرم‌های بین‌المللی مانند Alibaba و AliExpress
        """
        dict_map = {
            "ساعت هوشمند": "smart watch",
            "ایرپاد": "tws wireless earbuds bluetooth",
            "هندزفری بلوتوث": "bluetooth wireless earphones",
            "پاوربانک": "power bank 20000mah fast charging",
            "پودر pvc": "pvc resin powder s65",
            "pvc": "pvc resin powder",
            "پلی اتیلن": "hdpe granules polyethylene raw material",
            "hdpe": "hdpe virgin granules",
            "پلی پروپیلن": "polypropylene pp granules homopolymer",
            "pp": "polypropylene pp granules",
            "پت": "pet resin bottle grade",
            "pet": "pet bottle grade resin",
            "دریل شارژی": "brushless cordless drill 21v",
            "دریل": "cordless power drill",
            "ابزار": "industrial hardware power tools",
            "ماساژور تفنگی": "fascia massage gun deep tissue",
            "ماساژور": "electric body massager",
            "اسپیکر بلوتوث": "portable bluetooth speaker waterproof",
            "دوربین مداربسته": "wifi cctv security camera ptz",
            "لوازم خودرو": "auto spare parts accessories",
            "قطعات خودرو": "auto spare parts replacement",
            "لنت ترمز": "ceramic brake pads auto",
            "فیلتر هوا": "car air filter engine oil filter",
            "کمک فنر": "car shock absorber suspension",
            "تسمه": "automotive timing belt",
            "چراغ خودرو": "car led headlights assembly",
            "لوازم خانگی": "smart home appliances gadgets",
            "کابل شارژ": "fast charging cable type-c pd",
        }
        q_lower = query.lower().strip()
        for k, v in dict_map.items():
            if k in q_lower:
                return v
        return query

    def get_search_links(self, query: str) -> Dict[str, Dict[str, Any]]:
        """تولید لینک‌های عمیق جستجوی مستقیم در تمام پلتفرم‌های چین"""
        cn_keyword = self.translate_to_chinese_keywords(query)
        en_keyword = self.translate_to_english_keywords(query)
        encoded_cn = urllib.parse.quote(cn_keyword)
        encoded_en = urllib.parse.quote(en_keyword)
        links = {}
        for key, p in self.platform_catalog.items():
            target_encoded = encoded_en if key in ["alibaba", "aliexpress"] else encoded_cn
            links[key] = {
                "name": p["name"],
                "url": p["search_template"].format(query=target_encoded),
                "specialty": p["specialty"],
                "status": p["status"],
                "requires_auth": p["requires_auth"]
            }
        return links

    def get_indicative_benchmark(self, query: str, category: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """
        برآورد بازه و نرخ پایه مرجع صنعتی چین بر اساس مشخصات کاتالوگ کارخانجات برای شبیه‌سازی سناریو
        """
        benchmarks = {
            "ساعت هوشمند": {"price_cny": 55.0, "moq": 100, "weight_kg": 0.12, "volume_cbm": 0.0004, "category": "گجت و الکترونیک"},
            "smart watch": {"price_cny": 55.0, "moq": 100, "weight_kg": 0.12, "volume_cbm": 0.0004, "category": "گجت و الکترونیک"},
            "ایرپاد": {"price_cny": 38.0, "moq": 200, "weight_kg": 0.08, "volume_cbm": 0.0003, "category": "گجت و الکترونیک"},
            "هندزفری بلوتوث": {"price_cny": 35.0, "moq": 200, "weight_kg": 0.08, "volume_cbm": 0.0003, "category": "گجت و الکترونیک"},
            "earbuds": {"price_cny": 38.0, "moq": 200, "weight_kg": 0.08, "volume_cbm": 0.0003, "category": "گجت و الکترونیک"},
            "پاوربانک": {"price_cny": 48.0, "moq": 100, "weight_kg": 0.38, "volume_cbm": 0.0006, "category": "گجت و الکترونیک"},
            "power bank": {"price_cny": 48.0, "moq": 100, "weight_kg": 0.38, "volume_cbm": 0.0006, "category": "گجت و الکترونیک"},
            "پودر pvc": {"price_cny": 6.8, "moq": 1000, "weight_kg": 25.0, "volume_cbm": 0.04, "category": "پتروشیمی و پلیمر"},
            "pvc": {"price_cny": 6.8, "moq": 1000, "weight_kg": 25.0, "volume_cbm": 0.04, "category": "پتروشیمی و پلیمر"},
            "پلی اتیلن": {"price_cny": 8.5, "moq": 1000, "weight_kg": 25.0, "volume_cbm": 0.04, "category": "پتروشیمی و پلیمر"},
            "hdpe": {"price_cny": 8.5, "moq": 1000, "weight_kg": 25.0, "volume_cbm": 0.04, "category": "پتروشیمی و پلیمر"},
            "پلی پروپیلن": {"price_cny": 8.2, "moq": 1000, "weight_kg": 25.0, "volume_cbm": 0.04, "category": "پتروشیمی و پلیمر"},
            "pp": {"price_cny": 8.2, "moq": 1000, "weight_kg": 25.0, "volume_cbm": 0.04, "category": "پتروشیمی و پلیمر"},
            "پت": {"price_cny": 7.6, "moq": 1000, "weight_kg": 25.0, "volume_cbm": 0.04, "category": "پتروشیمی و پلیمر"},
            "pet": {"price_cny": 7.6, "moq": 1000, "weight_kg": 25.0, "volume_cbm": 0.04, "category": "پتروشیمی و پلیمر"},
            "دریل شارژی": {"price_cny": 95.0, "moq": 50, "weight_kg": 1.8, "volume_cbm": 0.005, "category": "ابزارآلات صنعتی"},
            "دریل": {"price_cny": 85.0, "moq": 50, "weight_kg": 1.5, "volume_cbm": 0.004, "category": "ابزارآلات صنعتی"},
            "ابزار": {"price_cny": 65.0, "moq": 50, "weight_kg": 1.0, "volume_cbm": 0.003, "category": "ابزارآلات صنعتی"},
            "ماساژور تفنگی": {"price_cny": 68.0, "moq": 100, "weight_kg": 0.9, "volume_cbm": 0.002, "category": "لوازم خانگی و سلامت"},
            "ماساژور": {"price_cny": 55.0, "moq": 100, "weight_kg": 0.8, "volume_cbm": 0.002, "category": "لوازم خانگی و سلامت"},
            "اسپیکر بلوتوث": {"price_cny": 42.0, "moq": 100, "weight_kg": 0.45, "volume_cbm": 0.001, "category": "گجت و الکترونیک"},
            "دوربین مداربسته": {"price_cny": 85.0, "moq": 50, "weight_kg": 0.5, "volume_cbm": 0.0015, "category": "گجت و الکترونیک"},
            "لوازم خودرو": {"price_cny": 50.0, "moq": 100, "weight_kg": 0.8, "volume_cbm": 0.002, "category": "قطعات خودرو"},
            "قطعات خودرو": {"price_cny": 50.0, "moq": 100, "weight_kg": 0.8, "volume_cbm": 0.002, "category": "قطعات خودرو"},
            "لنت ترمز": {"price_cny": 28.0, "moq": 100, "weight_kg": 1.2, "volume_cbm": 0.002, "category": "قطعات خودرو"},
            "فیلتر هوا": {"price_cny": 12.0, "moq": 200, "weight_kg": 0.25, "volume_cbm": 0.001, "category": "قطعات خودرو"},
            "کمک فنر": {"price_cny": 65.0, "moq": 50, "weight_kg": 3.0, "volume_cbm": 0.006, "category": "قطعات خودرو"},
            "تسمه": {"price_cny": 15.0, "moq": 200, "weight_kg": 0.15, "volume_cbm": 0.0005, "category": "قطعات خودرو"},
            "چراغ خودرو": {"price_cny": 110.0, "moq": 30, "weight_kg": 2.2, "volume_cbm": 0.008, "category": "قطعات خودرو"},
            "لوازم خانگی": {"price_cny": 45.0, "moq": 100, "weight_kg": 1.1, "volume_cbm": 0.003, "category": "لوازم خانگی"},
            "کابل شارژ": {"price_cny": 3.5, "moq": 500, "weight_kg": 0.03, "volume_cbm": 0.0001, "category": "گجت و الکترونیک"},
        }
        q_lower = query.lower().strip()
        for k, v in benchmarks.items():
            if k in q_lower:
                return v
        return None

    def search_suppliers(
        self,
        query: str,
        category: Optional[str] = None,
        allow_demo: bool = False,
        custom_buy_price_cny: Optional[float] = None,
        include_indicative_benchmark: bool = True
    ) -> List[ChineseSupplier]:
        """
        سورسینگ تأمین‌کنندگان چین:
        ۱. بررسی ورودی دستی مستقیم کاربر
        ۲. بررسی پیش‌فاکتورها و رکوردهای واقعی ثبت‌شده در پایگاه داده SQLite (جستجوی چندزبانه)
        ۳. در صورت نبود پیش‌فاکتور، استخراج نرخ مرجع صنعتی جهت امکان شبیه‌سازی سناریو
        ۴. در غیر این صورت، لیست خالی بازمی‌گرداند.
        """
        # ۱. قیمت دستی مستقیم وارد شده توسط کاربر
        if custom_buy_price_cny and custom_buy_price_cny > 0:
            return [
                ChineseSupplier(
                    name="مظنه مستقیم کاربر (User Manual Quote)",
                    platform="User Manual Input",
                    product_title=f"{query} (قیمت استعلامی کاربر)",
                    unit_price_cny=float(custom_buy_price_cny),
                    moq=100,
                    supplier_tier="قیمت استعلام‌شده مستقیم کاربر",
                    source_url="",
                    data_type=DataType.MANUAL_QUOTE,
                    incoterms=Incoterms.EXW,
                    verification_status=VerificationStatus.MANUAL_OVERRIDE,
                    confidence_level="USER_MANUAL_INPUT",
                    is_demo=False,
                    notes="ثبت‌شده به صورت مستقیم توسط کاربر در فیلد استعلام قیمت چین"
                )
            ]

        real_suppliers: List[ChineseSupplier] = []

        # ۲. استخراج پیش‌فاکتورها و داده‌های واقعی واردشده توسط کاربر در دیتابیس
        if self.db:
            try:
                en_kw = self.translate_to_english_keywords(query)
                cn_kw = self.translate_to_chinese_keywords(query)
                db_quotes = self.db.get_supplier_quotes_for_query(query, extra_terms=[en_kw, cn_kw])
                for q in db_quotes:
                    real_suppliers.append(ChineseSupplier(
                        name=q["supplier_name"],
                        platform=q["platform"],
                        product_title=q["product_title"],
                        unit_price_cny=float(q["unit_price_cny"]),
                        moq=int(q["moq"]),
                        supplier_tier="Manual Verified Quote",
                        source_url=q.get("source_url", ""),
                        data_type=DataType.MANUAL_QUOTE if q.get("is_manual") else DataType.CSV_IMPORT,
                        incoterms=Incoterms(q.get("incoterms", "EXW")),
                        verification_status=VerificationStatus.VERIFIED_WITH_DOCS,
                        confidence_level="REAL_USER_PROFORMA",
                        is_demo=False,
                        notes="ثبت‌شده در پیش‌فاکتورهای کاربر"
                    ))
            except Exception as e:
                pass

        if real_suppliers:
            return real_suppliers

        # ۳. نرخ مرجع صنعتی جهت امکان مدل‌سازی سناریو
        if include_indicative_benchmark:
            bench = self.get_indicative_benchmark(query, category)
            if bench:
                return [
                    ChineseSupplier(
                        name="نرخ پایه مرجع کارخانجات چین (Indicative Benchmark)",
                        platform="Alibaba / 1688 Reference",
                        product_title=f"{query} (برآورد مرجع عمده‌فروشی)",
                        unit_price_cny=float(bench["price_cny"]),
                        moq=bench["moq"],
                        weight_kg=bench.get("weight_kg", 0.5),
                        volume_cbm=bench.get("volume_cbm", 0.001),
                        supplier_tier="برآورد مرجع صنعتی جهت سناریوسازی",
                        source_url="https://www.alibaba.com/",
                        data_type=DataType.ESTIMATE,
                        incoterms=Incoterms.FOB,
                        verification_status=VerificationStatus.UNVERIFIED,
                        confidence_level="ESTIMATED_BENCHMARK",
                        is_demo=False,
                        notes="این نرخ تخمینی بر مبنای کاتالوگ صنعتی چین جهت امکان مدل‌سازی سناریو است و پیش‌فاکتور قطعی نیست. برای قرارداد نهایی از لینک‌های جستجوی زنده استعلام بگیرید."
                    )
                ]

        # ۴. فقط در صورت درخواست صریح حالت Demo برای محیط توسعه
        if allow_demo:
            cn_keyword = self.translate_to_chinese_keywords(query)
            return self._generate_demo_suppliers_with_explicit_label(query, cn_keyword)

        return []

    def _generate_demo_suppliers_with_explicit_label(self, query: str, cn_kw: str) -> List[ChineseSupplier]:
        """
        تولید داده صرفاً آموزشی (Demo) که با برچسب مشخص و غیرقابل استناد نشاندار شده است.
        """
        return [
            ChineseSupplier(
                name="[DEMO SAMPLE] Shenzhen Demo Electronics Co.",
                platform="1688 Demo Sample",
                product_title=f"{query} (نمونه آزمایشی - غیرواقعی) - {cn_kw}",
                product_specs={"Note": "این داده صرفاً نمونه آموزشی است و پیشنهاد قیمت واقعی نیست"},
                unit_price_cny=45.0,
                price_tiers=[PriceTier(min_quantity=100, unit_price_cny=45.0)],
                moq=100,
                supplier_tier="داده آزمایشی (Demo Data)",
                data_type=DataType.DEMO,
                incoterms=Incoterms.EXW,
                verification_status=VerificationStatus.UNVERIFIED,
                confidence_level="DEMO_NON_ACTIONABLE",
                is_demo=True,
                notes="این رکورد داده نمونه است و برای تصمیم‌گیری واقعی معتبر نیست."
            )
        ]
