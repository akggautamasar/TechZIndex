# config.py
import os

# --- Mandatory Environment Variables ---
# Get your API_ID and API_HASH from https://my.telegram.org/
# BOT_TOKEN from @BotFather on Telegram
# STRING_SESSION: Generated from a Pyrogram userbot (see steps above)

API_ID = int(os.getenv("API_ID", "0"))
API_HASH = os.getenv("API_HASH", "YOUR_DEFAULT_API_HASH")
BOT_TOKEN = os.getenv("BOT_TOKEN", "YOUR_DEFAULT_BOT_TOKEN")
STRING_SESSION = os.getenv("STRING_SESSION", "") # MUST be set in Koyeb

# --- Other Configuration Variables ---
HOME_PAGE_REDIRECT = os.getenv("HOME_PAGE_REDIRECT", "https://example.com/default_redirect")
BASE_URL = os.getenv("BASE_URL", "https://your-koyeb-app-domain.koyeb.app")
OWNER_ID = int(os.getenv("OWNER_ID", "0"))
ADMINS = list(map(int, os.getenv("ADMINS", f"{OWNER_ID}").split(',')))
