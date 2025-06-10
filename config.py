# config.py
import os

# --- Mandatory Environment Variables ---
# Get your API_ID and API_HASH from https://my.telegram.org/
# BOT_TOKEN from @BotFather on Telegram

API_ID = int(os.getenv("API_ID", "0")) # Provide a default '0' for type conversion safety if not set
API_HASH = os.getenv("API_HASH", "YOUR_DEFAULT_API_HASH") # Replace with a sensible default or leave blank for safety
BOT_TOKEN = os.getenv("BOT_TOKEN", "YOUR_DEFAULT_BOT_TOKEN") # Replace with a sensible default or leave blank for safety

# --- Other Configuration Variables ---
HOME_PAGE_REDIRECT = os.getenv("HOME_PAGE_REDIRECT", "https://example.com/default_redirect")
BASE_URL = os.getenv("BASE_URL", "https://your-koyeb-app-domain.koyeb.app") # Your Koyeb app's domain
OWNER_ID = int(os.getenv("OWNER_ID", "0")) # Your Telegram User ID
ADMINS = list(map(int, os.getenv("ADMINS", f"{OWNER_ID}").split(','))) # Comma-separated list of admin IDs
# Example: ADMINS = [12345, 67890] if ADMINS env var is "12345,67890"

# --- Remove any input() calls from this file! ---
