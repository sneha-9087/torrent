# effect.py ✅ Full async implementation
import os
import random
import aiohttp
import asyncio
from dotenv import load_dotenv

load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN", "8106093607:AAE3MW6Hz6Q1tmukuM_y-gsppRIC-Gixg4M")

# ✅ Only effects that work without Telegram Premium
EFFECT_IDS = [
    5046509860389126442,  # 🎉 Celebration
    5104841245755180586,  # 🔥 Fire
]

async def send_effect_message(
    chat_id: int, 
    text: str, 
    photo_url: str = None, 
    reply_markup: dict = None, 
    op_logger=None
):
    """
    Async Telegram message sender with visual effects
    """
    if not BOT_TOKEN:
        if op_logger: 
            op_logger.error("BOT_TOKEN not set.")
        return

    effect_id = random.choice(EFFECT_IDS)
    method = "sendPhoto" if photo_url else "sendMessage"
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/{method}"
    
    payload = {
        "chat_id": chat_id,
        "parse_mode": "HTML",
        "message_effect_id": effect_id,
    }

    # Add text/caption based on message type
    if photo_url:
        payload["photo"] = photo_url
        payload["caption"] = text
    else:
        payload["text"] = text

    if reply_markup:
        payload["reply_markup"] = reply_markup

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload) as response:
                data = await response.json()
                
                if op_logger:
                    if data.get("ok"):
                        media_type = "photo" if photo_url else "text"
                        op_logger.info(f"✅ Effect {effect_id} sent with {media_type}")
                    else:
                        error_desc = data.get('description', 'Unknown error')
                        op_logger.error(f"❌ Telegram API Error: {error_desc}")
    except Exception as e:
        if op_logger: 
            op_logger.error(f"❌ Request failed: {str(e)}")


