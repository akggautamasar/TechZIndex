# web.py
import os
import asyncio
from streamer import media_streamer # Assuming streamer.py exists
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import HTMLResponse, FileResponse, RedirectResponse, Response
from bot import get_image, get_posts, rm_cache # Corrected import for get_posts (now takes client)
from html_gen import posts_html # Assuming html_gen.py exists
from pyrogram.client import Client
# Import specific variables from config.py
from config import API_ID, API_HASH, BOT_TOKEN, HOME_PAGE_REDIRECT, BASE_URL, OWNER_ID, ADMINS
from pyrogram import filters
from pyrogram.types import Message
import logging

# --- Logging Setup ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# --- Pyrogram Bot Client Initialization ---
# Only one client (bot) is initialized now.
# This relies on BOT_TOKEN, API_ID, API_HASH from environment variables via config.py
try:
    bot = Client(
        "techzindexbot",
        api_id=API_ID,
        api_hash=API_HASH,
        bot_token=BOT_TOKEN,
    )
    logger.info("Pyrogram bot client initialized.")
except Exception as e:
    logger.critical(f"CRITICAL ERROR: Failed to initialize Pyrogram bot client: {e}")
    # Consider exiting or making the app unhealthy if bot client is critical for the app.

app = FastAPI(docs_url=None, redoc_url=None)

# --- Template Loading ---
# Ensure 'templates' directory exists in your project root
try:
    with open("templates/home.html", "r") as f:
        HOME_HTML = f.read()
    with open("templates/stream.html", "r") as f:
        STREAM_HTML = f.read()
except FileNotFoundError as e:
    logger.critical(f"Template file not found: {e}. Please ensure 'templates/' directory and files exist.")
    # Fallback HTML for critical errors
    HOME_HTML = "<h1>Error: Home template not found</h1><p>Please check your deployment files.</p>"
    STREAM_HTML = "<h1>Error: Stream template not found</h1><p>Please check your deployment files.</p>"

# --- FastAPI Startup/Shutdown Events ---
@app.on_event("startup")
async def startup_event():
    """
    Connects the Pyrogram bot client when the FastAPI application starts up.
    """
    logger.info("Starting TG Bot Client...")
    try:
        if bot: # Check if bot client was successfully initialized
            await bot.start()
            logger.info("Bot client started successfully.")
    except Exception as e:
        logger.error(f"Failed to start Pyrogram bot client: {e}")
        # The app might still run but telegram features will be broken.
    logger.info("========================================")
    logger.info("TechZIndex Started Successfully")
    logger.info("Made By TechZBots | TechShreyash")
    logger.info("========================================")

    # Ensure directories for cache and downloads exist
    os.makedirs("cache", exist_ok=True)
    os.makedirs("downloads", exist_ok=True)


@app.on_event("shutdown")
async def shutdown_event():
    """
    Stops the Pyrogram bot client gracefully when the FastAPI application shuts down.
    """
    logger.info("Stopping TG Bot Client...")
    try:
        if bot and bot.is_connected: # Check if bot client is connected before stopping
            await bot.stop()
            logger.info("Bot client stopped.")
    except Exception as e:
        logger.error(f"Error stopping Pyrogram bot client: {e}")
    logger.info("TG Bot Client Stopped.")


# --- Web Endpoints ---

@app.get("/")
async def home_redirect():
    """
    Redirects to the configured HOME_PAGE_REDIRECT URL.
    This also serves as a basic health check for Koyeb, as a redirect implies
    the server is running.
    """
    return RedirectResponse(HOME_PAGE_REDIRECT)


@app.get("/channel/{channel}")
async def channel_page(channel_username: str): # Renamed for clarity, original was 'channel'
    """
    Displays posts for a given Telegram channel username.
    Now uses the 'bot' client to fetch posts.
    """
    try:
        # Pass the 'bot' client to get_posts
        posts = await get_posts(bot, str(channel_username).lower())
        phtml = posts_html(posts, channel_username)
        return HTMLResponse(
            HOME_HTML.replace("POSTS", phtml).replace("CHANNEL_ID", channel_username)
        )
    except Exception as e:
        logger.error(f"Error serving channel page for {channel_username}: {e}")
        return HTMLResponse(f"<h1>Error loading channel: {e}</h1><p>Ensure bot is admin in channel and permissions are correct.</p>", status_code=500)


@app.get("/api/posts/{channel}/{page}")
async def get_posts_api(channel: str, page: int = 1):
    """
    API endpoint to fetch posts from a Telegram channel.
    Now uses the 'bot' client to fetch posts.
    """
    try:
        # Pass the 'bot' client to get_posts
        posts = await get_posts(bot, str(channel).lower(), page)
        phtml = posts_html(posts, channel)
        return {"html": phtml}
    except Exception as e:
        logger.error(f"Error fetching posts API for channel {channel}, page {page}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch posts: {e}. Check bot permissions.")


@app.get("/static/{file}")
async def static_files(file: str):
    """
    Serves static files from the 'static' directory.
    Ensure 'static' directory exists in your project root.
    """
    file_path = f"static/{file}"
    if os.path.exists(file_path):
        return FileResponse(file_path)
    else:
        logger.warning(f"Static file not found: {file_path}")
        raise HTTPException(status_code=404, detail="Static file not found")


@app.get("/api/thumb/{channel}/{id}")
async def get_thumb_endpoint(channel: str, message_id: int): # Renamed for clarity
    """
    Serves video thumbnail images.
    Uses the 'bot' client to get images.
    """
    try:
        img_path = await get_image(bot, message_id, channel) # Pass the 'bot' client
        if img_path and os.path.exists(img_path):
            return FileResponse(img_path, media_type="image/jpeg")
        else:
            logger.warning(f"Image not found for channel {channel}, ID {message_id}")
            raise HTTPException(status_code=404, detail="Image not found or could not be downloaded.")
    except Exception as e:
        logger.error(f"Error getting thumbnail for channel {channel}, ID {message_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get thumbnail: {e}")


# --- Streamer Endpoints ---
@app.get("/stream/{channel}/{id}")
async def stream_page(channel: str, message_id: int):
    """
    Renders the stream page for a given video.
    """
    return HTMLResponse(
        STREAM_HTML.replace("URL", f"{BASE_URL}/api/stream/{channel}/{message_id}")
    )


@app.get("/api/stream/{channel}/{id}")
async def stream_api(channel: str, message_id: int, request: Request):
    """
    Handles streaming media from Telegram.
    Uses the 'bot' client for streaming.
    """
    return await media_streamer(bot, channel, message_id, request) # Pass the 'bot' client


# --- Bot Commands (handled by Pyrogram client) ---
# These functions will be run by the 'bot' Pyrogram client when messages are received.
@bot.on_message(filters.command("start"))
async def start_cmd(_, msg: Message):
    logger.info(f"Received /start from {msg.from_user.id}")
    await msg.reply_text(
        "TechZIndex Up and Running\n\n/clean_cache to clean website cache\n/help to know how to use this bot\n\nMade By @TechZBots | @TechZBots_Support"
    )

@bot.on_message(filters.command("help"))
async def help_cmd(_, msg: Message):
    logger.info(f"Received /help from {msg.from_user.id}")
    await msg.reply_text(
        f"""
**How to use this bot?**

1. Add me to your channel as admin
2. Your channel must be public
3. Now open this link domain/channel/<your channel username>

Ex : http://index.techzbots.live/channel/autoairinganimes

Contact [Owner](tg://user?id={OWNER_ID}) To Get domain of website
Owner Id : {OWNER_ID}"""
    )

@bot.on_message(filters.command("clean_cache"))
async def clean_cache_cmd(_, msg: Message):
    logger.info(f"Received /clean_cache from {msg.from_user.id}")
    if msg.from_user.id in ADMINS:
        x = msg.text.split(" ")
        if len(x) == 2:
            rm_cache(x[1])
        else:
            rm_cache()
        await msg.reply_text("Cache cleaned")
    else:
        await msg.reply_text(
            f"You are not my owner\n\nContact [Owner](tg://user?id={OWNER_ID}) If You Want To Update Your Site\n\nRead : https://t.me/TechZBots/524"
        )
