import os
import requests

BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")


def send_message(text: str):
    """Sends a plain-text message. Telegram messages max out at 4096
    chars, so very large digests get split into chunks automatically."""
    if not BOT_TOKEN or not CHAT_ID:
        print("[ERROR] Telegram credentials not properly set -- cannot send message.")
        print("---- MESSAGE THAT WOULD HAVE BEEN SENT ----")
        print(text)
        return

    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"

    for chunk in _split_message(text):
        try:
            response = requests.post(url, json={
                "chat_id": CHAT_ID,
                "text": chunk,
                "parse_mode": "HTML",
                "disable_web_page_preview": False,
            }, timeout=15)
            response.raise_for_status()
        except requests.RequestException as e:
            print(f"[ERROR] Failed to send the Telegram message: {e}")


def _split_message(text: str, limit: int = 4000) -> list[str]:
    """Splits long text into chunks under Telegram's message limit."""
    if len(text) <= limit:
        return [text]

    chunks = []
    while text:
        chunks.append(text[:limit])
        text = text[limit:]
    return chunks
