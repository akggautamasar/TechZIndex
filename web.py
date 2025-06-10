# web.py
import os
from streamer import media_streamer
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, FileResponse, RedirectResponse, Response
from bot import get_image, get_posts, rm_cache
from html_gen import posts_html # Assuming html_gen.py exists
from pyrogram.client import Client
from config import API_ID, API_HASH, BOT_TOKEN, STRING_SESSION, HOME_PAGE_REDIRECT, BASE_URL, OWNER_ID, ADMINS
from pyrogram import filters
from pyrogram.types import Message
import logging

# --- Logging Setup ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# --- Pyrogram Client Initialization (using values from config.py) ---
# IMPORTANT: These clients will be initialized when the web.py module loads.
# Ensure all required environment variables are set in Koyeb.
try:
    user = Client(
        "userbot",
        api_id=API_ID,
        api_hash=API_HASH,
        session_string=STRING_SESSION,
        # It's good practice to provide a workdir if your session files are
        # to be stored in a specific location for persistent deployments.
        # For ephemeral serverless, this might not be strictly necessary,
        # but for stateful clients, it is.
        # workdir="./sessions/userbot_sessions"
    )
    logger.info("Userbot client initialized.")
except Exception as e:
    logger.error(f"Error initializing userbot client: {e}")
    # You might want to exit or raise an error if this is critical for startup
    # For now, let it proceed to see if bot client can start.

try:
    bot = Client(
        "techzindexbot",
        api_id=API_ID,
        api_hash=API_HASH,
        bot_token=BOT_TOKEN,
        # workdir="./sessions/bot_sessions"
    )
    logger.info("Bot client initialized.")
except Exception as e:
    logger.error(f"Error initializing bot client: {e}")
    # If bot client fails, the web app might still run but commands won't work.

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
    # Exit or raise an error if templates are critical for the app to function.
    HOME_HTML = "<h1>Error: Home template not found</h1>"
    STREAM_HTML = "<h1>Error: Stream template not found</h1>"


# --- FastAPI Startup/Shutdown Events ---
@app.on_event("startup")
async def startup_event():
    """
    Connects the Pyrogram clients when the FastAPI application starts up.
    """
    logger.info("Starting TG Clients...")
    try:
        if bot:
            await bot.start()
            logger.info("Bot client started.")
        if user:
            await user.start()
            logger.info("Userbot client started.")
    except Exception as e:
        logger.error(f"Failed to start one or more Pyrogram clients: {e}")
        # Depending on criticality, you might want to exit or log a critical error.
    logger.info("========================================")
    logger.info("TechZIndex Started Successfully")
    logger.info("Made By TechZBots | TechShreyash")
    logger.info("========================================")

@app.on_event("shutdown")
async def shutdown_event():
    """
    Stops the Pyrogram clients gracefully when the FastAPI application shuts down.
    """
    logger.info("Stopping TG Clients...")
    try:
        if bot and bot.is_connected:
            await bot.stop()
            logger.info("Bot client stopped.")
        if user and user.is_connected:
            await user.stop()
            logger.info("Userbot client stopped.")
    except Exception as e:
        logger.error(f"Error stopping one or more Pyrogram clients: {e}")
    logger.info("TG Clients Stopped.")


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
async def channel(channel_username: str):
    """
    Displays posts for a given Telegram channel username.
    """
    try:
        posts = await get_posts(user, str(channel_username).lower())
        phtml = posts_html(posts, channel_username)
        return HTMLResponse(
            HOME_HTML.replace("POSTS", phtml).replace("CHANNEL_ID", channel_username)
        )
    except Exception as e:
        logger.error(f"Error serving channel {channel_username}: {e}")
        return HTMLResponse(f"<h1>Error loading channel: {e}</h1>", status_code=500)


@app.get("/api/posts/{channel}/{page}")
async def get_posts_api(channel: str, page: int = 1):
    """
    API endpoint to fetch posts from a Telegram channel.
    """
    try:
        posts = await get_posts(user, str(channel).lower(), page)
        phtml = posts_html(posts, channel)
        return {"html": phtml}
    except Exception as e:
        logger.error(f"Error fetching posts API for channel {channel}, page {page}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch posts: {e}")


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
async def get_thumb(channel: str, message_id: int):
    """
    Serves video thumbnail images.
    """
    try:
        img_path = await get_image(bot, message_id, channel)
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
    """
    return await media_streamer(bot, channel, message_id, request)


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
