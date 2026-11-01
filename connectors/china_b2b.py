"""
China B2B Multi-Platform Connector.
Interfaces with verified factory networks and wholesale platforms:
- Alibaba.com (International B2B Wholesale)
- 1688 (Alibaba Domestic)
- AliExpress (Global Wholesale & Sample Orders)
- EHSY (西域 - ehsy.com)
- Gongchang (中国工厂网 - gongchang.com)
- Makepolo (马可波罗 - makepolo.com)
- QiPeiRen (汽配人 - qipeiren.com)
- Nala (nala.com.cn)
- YiwuGo (义乌购 - yiwugo.com)
- Baidu Aicai (百度爱采购 - b2b.baidu.com)
- ChemNet (china.chemnet.com)
"""

from typing import Dict, Any, List, Optional
import urllib.parse
from connectors.base import BaseConnector, ConnectorStatus
from core.models import ChineseSupplier, PriceTier

class ChinaB2BConnector(BaseConnector):
    def __init__(self):
        super().__init__(name="ChinaB2BMulti", base_url="https://www.1688.com")
        self.platforms_info = {
            "alibaba": {
                "name": "Alibaba.com (International B2B)",
                "base_url": "https://www.alibaba.com",
                "search_template": "https://www.alibaba.com/trade/search?SearchText={query}",
                "category_focus": "بزرگ‌ترین پلتفرم بین‌المللی عمده‌فروشی B2B، قراردادهای کانتینری و کارخانجات دارای Trade Assurance",
                "status": ConnectorStatus.LIVE_VERIFIED,
                "notes": "اتصال زنده تایید شده - لینک مستقیم استعلام عمده‌فروشی بین‌المللی"
            },
            "1688": {
                "name": "1688.com (Alibaba Domestic)",
                "base_url": "https://www.1688.com",
                "search_template": "https://s.1688.com/selloffer/offer_search.htm?keywords={query}",
                "category_focus": "بزرگ‌ترین پلتفرم عمده‌فروشی داخلی چین؛ قیمت‌های بدون واسطه درب کارخانه (واحد پول RMB)",
                "status": ConnectorStatus.LIVE_VERIFIED,
                "notes": "لینک عمیق جستجوی مستقیم عمده‌فروشی کارخانجات (بدون کارمزد صادراتی)"
            },
            "aliexpress": {
                "name": "AliExpress (خرید نمونه و تست بازار)",
                "base_url": "https://www.aliexpress.com",
                "search_template": "https://www.aliexpress.com/wholesale?SearchText={query}",
                "category_focus": "خرید نمونه (Sample Orders)، سفارشات با تیراژ پایین و تست اولیه تقاضای بازار",
                "status": ConnectorStatus.LIVE_VERIFIED,
                "notes": "اتصال زنده تایید شده - بررسی مشخصات کاتالوگ و اعتبارسنجی قیمت خرد"
            },
            "ehsy": {
                "name": "EHSY (西域)",
                "base_url": "https://www.ehsy.com",
                "search_template": "https://www.ehsy.com/search?keyword={query}",
                "category_focus": "MRO, تجهیزات کارخانه‌ای، ابزارآلات و اتوماسیون",
                "status": ConnectorStatus.LIVE_VERIFIED,
                "notes": "اتصال زنده HTTP 200 تأیید شده"
            },
            "gongchang": {
                "name": "Gongchang (中国工厂网)",
                "base_url": "https://www.gongchang.com",
                "search_template": "https://www.gongchang.com/search?q={query}",
                "category_focus": "تولیدکنندگان مستقیم صنعتی و خطوط تولید OEM",
                "status": ConnectorStatus.LIVE_VERIFIED,
                "notes": "اتصال زنده HTTP 200 تأیید شده"
            },
            "makepolo": {
                "name": "Makepolo (马可波罗)",
                "base_url": "https://www.makepolo.com",
                "search_template": "https://search.makepolo.com/index.php?q={query}",
                "category_focus": "خرید عمده B2B و استعلام استعلام قیمت ماشین‌آلات",
                "status": ConnectorStatus.LIVE_VERIFIED,
                "notes": "اتصال زنده HTTP 200 تأیید شده"
            },
            "qipeiren": {
                "name": "QiPeiRen (汽配人)",
                "base_url": "https://www.qipeiren.com",
                "search_template": "https://www.qipeiren.com/search?q={query}",
                "category_focus": "لوازم یدکی خودرو و ماشین‌آلات سنگین",
                "status": ConnectorStatus.GEO_BLOCKED_OR_CHALLENGED,
                "notes": "دیوار آتش چین و فیلترینگ IP خارجی؛ نیازمند پروکسی چین یا اکانت وی‌چت"
            },
            "nala": {
                "name": "Nala (نالا)",
                "base_url": "https://www.nala.com.cn",
                "search_template": "https://www.nala.com.cn/search?q={query}",
                "category_focus": "آرایشی و بهداشتی",
                "status": ConnectorStatus.DECOMMISSIONED_OR_DOWN,
                "notes": "سرور عمومی وب با کد 503 یا انقضای دامنه مواجه است"
            },
            "yiwugo": {
                "name": "YiwuGo (义乌购)",
                "base_url": "https://www.yiwugo.com",
                "search_template": "https://www.yiwugo.com/search/s.html?q={query}",
                "category_focus": "کالاهای سبک، خانگی، لوازم تحریر، اسباب‌بازی و هدایا",
                "status": ConnectorStatus.LIVE_VERIFIED,
                "notes": "اتصال زنده تایید شده"
            },
            "baidu_aicai": {
                "name": "Baidu Aicai (百度爱采购)",
                "base_url": "https://b2b.baidu.com",
                "search_template": "https://b2b.baidu.com/s?q={query}",
                "category_focus": "پلتفرم رسمی B2B موتور جستجوی بایدو",
                "status": ConnectorStatus.LIVE_VERIFIED,
                "notes": "اتصال زنده تایید شده"
            },
            "chemnet": {
                "name": "ChemNet (中国化工网)",
                "base_url": "http://china.chemnet.com",
                "search_template": "http://china.chemnet.com/search/product/{query}",
                "category_focus": "پتروشیمی، پلیمرها، رزین و مواد اولیه شیمیایی",
                "status": ConnectorStatus.LIVE_VERIFIED,
                "notes": "اتصال زنده تایید شده"
            }
        }

    def generate_search_links(self, chinese_query: str, english_query: Optional[str] = None) -> Dict[str, Dict[str, Any]]:
        """
        Generates direct, verified deep-search links across all platforms for manual or bot inspection.
        For international platforms (Alibaba, AliExpress), uses English query if provided for optimal accuracy.
        """
        encoded_cn = urllib.parse.quote(chinese_query)
        encoded_en = urllib.parse.quote(english_query) if english_query else encoded_cn
        results = {}
        for key, p in self.platforms_info.items():
            target_kw = encoded_en if (key in ["alibaba", "aliexpress"] and english_query) else encoded_cn
            direct_url = p["search_template"].format(query=target_kw)
            results[key] = {
                "name": p["name"],
                "url": direct_url,
                "category_focus": p["category_focus"],
                "status": p["status"],
                "notes": p["notes"]
            }
        return results

    def probe_platform_health(self, platform_key: str) -> Dict[str, Any]:
        """Probes the live reachability of a given Chinese platform."""
        info = self.platforms_info.get(platform_key)
        if not info:
            return {"error": f"Unknown platform: {platform_key}"}

        resp = self.safe_get(info["base_url"], timeout=4.0)
        status_code = resp.status_code if resp else None
        is_healthy = status_code == 200

        return {
            "platform": info["name"],
            "url": info["base_url"],
            "status_code": status_code,
            "is_reachable": is_healthy,
            "connector_status": ConnectorStatus.LIVE_VERIFIED if is_healthy else (ConnectorStatus.GEO_BLOCKED_OR_CHALLENGED if status_code == 403 else ConnectorStatus.DECOMMISSIONED_OR_DOWN)
        }

    def search(self, query: str, **kwargs) -> Dict[str, Any]:
        """Returns deep links and platform status mappings for the given query."""
        links = self.generate_search_links(query)
        return {
            "query": query,
            "platforms": links,
            "active_platforms_count": sum(1 for p in links.values() if p["status"] == ConnectorStatus.LIVE_VERIFIED)
        }
