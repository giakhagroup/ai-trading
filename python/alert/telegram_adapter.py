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
    def format_scan_result(result: dict) -> str:
        """Format ScanResult into a Telegram-friendly HTML message."""
        symbol = result.get("symbol", "N/A")
        score = result.get("score", 0)
        trend = result.get("trend", "UNKNOWN")
        rvol = result.get("rvol", 0)
        matched = result.get("matched_criteria", [])
        
        icon = "🟢" if trend == "UPTREND" else "🔴" if trend == "DOWNTREND" else "⚪"
        
        msg = f"<b>{icon} AI TRADING ALERT | {symbol}</b>\n\n"
        msg += f"<b>Score:</b> {score}/100\n"
        msg += f"<b>Trend:</b> {trend}\n"
        msg += f"<b>RVOL:</b> {rvol}x\n"
        
        if matched:
            msg += f"<b>Criteria:</b> {', '.join(matched)}\n"
            
        correlation_id = result.get("correlation_id")
        if correlation_id:
            msg += f"\n<i>#Trace: {correlation_id}</i>"
            
        return msg
