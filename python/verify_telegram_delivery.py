import os
import time
from dotenv import load_dotenv

from alert.telegram_adapter import TelegramAdapter

def verify():
    load_dotenv()
    
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID")
    
    if not token or not chat_id:
        print("❌ Error: TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID must be set in .env")
        return

    print(f"✅ Bot Token found (starts with {token[:4]}...)")
    print(f"✅ Chat ID found: {chat_id}")
    
    adapter = TelegramAdapter()
    
    payload = {
        "items": [
            {
                "symbol": "HOSE:FPT",
                "total_score": 98,
                "trend_score": 100,
                "momentum_score": 95,
                "mtf_score": 90,
                "trend": "UPTREND"
            },
            {
                "symbol": "HOSE:HPG",
                "total_score": 88,
                "trend_score": 100,
                "momentum_score": 80,
                "mtf_score": 80,
                "trend": "UPTREND"
            }
        ]
    }
    
    msg = adapter.format_scan_result(payload)
    print("\n--- Message to Send ---\n")
    print(msg)
    print("\n-----------------------\n")
    
    print("⏳ Sending message to Telegram...")
    success, retry_after, response = adapter.send_message(chat_id, msg)
    
    if success:
        print("✅ Message delivered successfully!")
    else:
        print(f"❌ Failed to deliver. Response: {response}")
        if retry_after > 0:
            print(f"Rate limited. Retry after {retry_after}s")

if __name__ == "__main__":
    verify()
