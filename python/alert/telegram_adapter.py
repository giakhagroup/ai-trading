import os
import requests
from typing import Tuple, Dict, Any

class TelegramAdapter:
    def __init__(self):
        # Security: Fetch from environment variable
        self.bot_token = os.environ.get("TELEGRAM_BOT_TOKEN")
        self.base_url = f"https://api.telegram.org/bot{self.bot_token}"

    def send_message(self, chat_id: str, text: str, parse_mode: str = "HTML") -> Tuple[bool, int, Dict[str, Any]]:
        """
        Returns (success, retry_after, response_json)
        retry_after is the number of seconds to wait if rate-limited (HTTP 429)
        """
        if not self.bot_token:
            # Mock success if no token is configured for local testing
            return True, 0, {"mock": True}

        url = f"{self.base_url}/sendMessage"
        payload = {
            "chat_id": chat_id,
            "text": text,
            "parse_mode": parse_mode
        }
        
        try:
            response = requests.post(url, json=payload, timeout=10)
            
            if response.status_code == 200:
                return True, 0, response.json()
            elif response.status_code == 429:
                # Rate limited
                data = response.json()
                retry_after = data.get("parameters", {}).get("retry_after", 5)
                return False, retry_after, data
            else:
                return False, 0, {"error": response.text, "status_code": response.status_code}
                
        except requests.RequestException as e:
            return False, 0, {"error": str(e)}

    @staticmethod
    def format_scan_result(payload: dict) -> str:
        """Format AlertEvent payload into a Telegram-friendly HTML message."""
        items = payload.get("items", [])
        if not items:
            return "<i>No data available</i>"

        import datetime
        now_str = datetime.datetime.now().strftime("%H:%M")
        
        msg = f"🚨 <b>AI Trading Alert</b>\n"
        msg += f"{now_str} — VN30\n\n"
        
        for idx, item in enumerate(items, 1):
            symbol = item.get("symbol", "").replace("HOSE:", "")
            score = item.get("total_score", 0)
            trend = item.get("trend", "UNKNOWN")
            
            trend_score = item.get("trend_score", 0)
            mom_score = item.get("momentum_score", 0)
            mtf_score = item.get("mtf_score", 0)
            
            msg += f"{idx}. {symbol}  Score {score}  {trend}\n"
            msg += f"   Trend {trend_score} | Momentum {mom_score} | MTF {mtf_score}\n\n"
            
        return msg.strip()
