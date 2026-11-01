"""
Digikala Live API Connector.
Fetches real-time price quotes, cleans outliers, extracts verified sellers,
and computes robust statistical indicators.
"""

from typing import Optional, Dict, Any, List
from decimal import Decimal
import urllib.parse
from connectors.base import BaseConnector, ConnectorStatus
from core.money import Money, Currency, calculate_robust_statistics

class DigikalaConnector(BaseConnector):
    def __init__(self):
        super().__init__(name="Digikala", base_url="https://api.digikala.com/v1/search/")

    def search(self, query: str, page: int = 1) -> Dict[str, Any]:
        """
        Executes real-time query against Digikala search API.
        Returns cleaned products, price distribution, and statistical metrics.
        """
        encoded_query = urllib.parse.quote(query)
        url = f"{self.base_url}?q={encoded_query}&page={page}"
        
        resp = self.safe_get(url)
        if not resp or resp.status_code != 200:
            return {
                "status": ConnectorStatus.MANUAL_FALLBACK,
                "query": query,
                "products_count": 0,
                "products": [],
                "statistics": None,
                "notes": f"اتصال زنده به API دیجی‌کالا برقرار نشد (HTTP {resp.status_code if resp else 'Timeout'})"
            }

        try:
            payload = resp.json()
            data = payload.get("data", {})
            raw_products = data.get("products", [])
        except Exception as e:
            return {
                "status": ConnectorStatus.MANUAL_FALLBACK,
                "query": query,
                "products_count": 0,
                "products": [],
                "statistics": None,
                "notes": f"خطا در تجزیه JSON پاسخ دیجی‌کالا: {e}"
            }

        cleaned_products: List[Dict[str, Any]] = []
        valid_prices_toman: List[Decimal] = []

        for p in raw_products:
            # Check availability
            default_variant = p.get("default_variant") or {}
            price_info = default_variant.get("price") or {}
            selling_price_rial = price_info.get("selling_price", 0)
            
            if not selling_price_rial or selling_price_rial <= 0:
                continue  # Out of stock or zero-priced item

            # Convert Rials to Toman
            toman_dec = Decimal(str(selling_price_rial // 10))
            valid_prices_toman.append(toman_dec)

            cleaned_products.append({
                "id": p.get("id"),
                "title_fa": p.get("title_fa", "").strip(),
                "price_toman": int(toman_dec),
                "rrp_price_toman": int(price_info.get("rrp_price", 0) // 10),
                "url": f"https://www.digikala.com/product/dkp-{p.get('id')}",
                "seller_title": default_variant.get("seller", {}).get("title", "فروشنده دیجی‌کالا"),
                "is_active": True,
                "rating": p.get("rating", {}).get("rate", 0),
                "rating_count": p.get("rating", {}).get("count", 0),
            })

        # Calculate robust statistics (IQR outlier filtering)
        stats = None
        if valid_prices_toman:
            stats = calculate_robust_statistics(valid_prices_toman)

        return {
            "status": ConnectorStatus.LIVE_VERIFIED,
            "query": query,
            "products_count": len(cleaned_products),
            "products": cleaned_products,
            "statistics": {
                "count": stats.get("count", 0) if stats else 0,
                "min_toman": int(stats.get("min") or 0) if stats else 0,
                "max_toman": int(stats.get("max") or 0) if stats else 0,
                "median_toman": int(stats.get("median") or 0) if stats else 0,
                "trimmed_mean_toman": int(stats.get("trimmed_mean") or 0) if stats else 0,
                "iqr_toman": int(stats.get("iqr") or 0) if stats else 0,
            } if stats else None,
            "notes": f"استعلام زنده موفق از دیجی‌کالا: {len(cleaned_products)} کالای دارای موجودی و قیمت"
        }
