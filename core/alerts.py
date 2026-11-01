"""
Price & Profit Alerting Engine.
Monitors arbitrage spreads and fires alerts when net profitability or market margins exceed threshold.
"""

from typing import List, Dict, Any
from core.db import Database

class AlertEngine:
    def __init__(self, db: Database):
        self.db = db

    def check_alerts(self, current_product: str, current_profit_toman: float) -> List[Dict[str, Any]]:
        """
        Checks whether current profit triggers any active alerts.
        Returns triggered alerts list.
        """
        active_alerts = self.db.get_active_alerts()
        triggered = []

        curr_prod_clean = current_product.lower()
        for alert in active_alerts:
            target = alert["target_product"].lower()
            if target in curr_prod_clean or curr_prod_clean in target:
                if current_profit_toman >= alert["threshold_profit_toman"]:
                    triggered.append({
                        "alert_id": alert["id"],
                        "target_product": alert["target_product"],
                        "user_contact": alert["user_contact"],
                        "threshold_profit": alert["threshold_profit_toman"],
                        "achieved_profit": current_profit_toman,
                        "message_fa": f"هشدار سودآوری: سود هر واحد {current_product} به {current_profit_toman:,.0f} تومان رسید (بیشتر از آستانه {alert['threshold_profit_toman']:,.0f} تومان)!"
                    })

        return triggered
