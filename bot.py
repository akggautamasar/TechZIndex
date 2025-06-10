# bot.py
from pyrogram.client import Client
from pyrogram.types import Message
import os
import json
import logging

logger = logging.getLogger(__name__)

# --- Cache Management Functions ---

def rm_cache(channel=None):
    logger.info("Cleaning Cache...")
    global image_cache
    image_cache = {}

    downloads_path = "downloads"
    if os.path.exists(downloads_path):
        for file_name in os.listdir(downloads_path):
            file_path = os.path.join(downloads_path, file_name)
            try:
                if os.path.isfile(file_path):
                    os.remove(file_path)
                    logger.info(f"Removed download: {file_path}")
            except Exception as e:
                logger.error(f"Error removing download {file_path}: {e}")
    else:
        logger.warning(f"Downloads directory not found: {downloads_path}")

    cache_path = "cache"
    if os.path.exists(cache_path):
        for file_name in os.listdir(cache_path):
            file_path = os.path.join(cache_path, file_name)
            try:
                if file_name.endswith(".json"):
                    if channel:
                        if file_name.startswith(channel):
                            os.remove(file_path)
                            logger.info(f"Removed cache file: {file_path}")
                    else:
                        os.remove(file_path)
                        logger.info(f"Removed cache file: {file_path}")
            except Exception as e:
                logger.error(f"Error removing cache file {file_path}: {e}")
    else:
        logger.warning(f"Cache directory not found: {cache_path}")


def get_cache(channel, page):
    cache_file_path = f"cache/{channel}-{page}.json"
    if os.path.exists(cache_file_path):
        try:
            with open(cache_file_path, "r") as f:
                logger.info(f"Loading cache from {cache_file_path}")
                return json.load(f)["posts"]
        except (json.JSONDecodeError, KeyError) as e:
            logger.error(f"Error reading cache file {cache_file_path}: {e}")
            return None
    else:
        return None


def save_cache(channel, cache, page):
    cache_dir = "cache"
    if not os.path.exists(cache_dir):
        os.makedirs(cache_dir)

    cache_file_path = f"{cache_dir}/{channel}-{page}.json"
    try:
        with open(cache_file_path, "w") as f:
            json.dump(cache, f)
            logger.info(f"Saved cache to {cache_file_path}")
    except Exception as e:
        logger.error(f"Error saving cache to {cache_file_path}: {e}")


# --- Pyrogram Interaction Functions ---

async def get_posts(client: Client, channel: str, page: int = 1):
    """
    Fetches posts from a Telegram channel using the provided Pyrogram client.
    Caches the results.
    """
    page = int(page)
    cache = get_cache(channel, page)
    if cache:
        logger.info(f"Returning posts from cache for channel {channel}, page {page}")
        return cache
    else:
        logger.info(f"Fetching posts from Telegram for channel {channel} (ID/Username: {channel}), page {page}")
        posts = []
        try:
            # Attempt to fetch history
            logger.info(f"Calling client.get_chat_history for channel: {channel}, limit: 50, offset: {(page - 1) * 50}")
            async for post in client.get_chat_history(
                chat_id=channel, limit=50, offset=(page - 1) * 50
            ):
                post: Message
                if post.video and post.video.thumbs:
                    file_name = post.video.file_name or post.caption or post.video.file_id
                    title = " ".join(str(file_name).split(".")[:-1]) if isinstance(file_name, str) else str(file_name)
                    title = title[:200].strip()
                    posts.append({"msg-id": post.id, "title": title})
                elif post.caption and post.media:
                    title = post.caption[:200].strip()
                    posts.append({"msg-id": post.id, "title": title})
            
            logger.info(f"Successfully fetched {len(posts)} posts for channel {channel}.")

        except Exception as e:
            logger.error(f"Error getting chat history for channel {channel}: {e}", exc_info=True) # exc_info=True prints traceback
            # If there's an error fetching, return empty list or raise
            return []

        save_cache(channel, {"posts": posts}, page)
        return posts


image_cache = {}


async def get_image(bot_client: Client, file_id_or_message_id: int, channel: str):
    """
    Downloads and caches a video thumbnail from a Telegram message.
    'file_id_or_message_id' can be a message ID or a file ID.
    """
    global image_cache

    cache_key = f"{channel}-{file_id_or_message_id}"
    cache = image_cache.get(cache_key)
    if cache:
        logger.info(f"Returning image from in-memory cache: {cache_key}")
        return cache
    else:
        logger.info(f"Downloading image from Telegram: {cache_key}")
        download_path = None
        downloads_dir = "downloads"
        os.makedirs(downloads_dir, exist_ok=True) # Ensure downloads directory exists

        try:
            if isinstance(file_id_or_message_id, int):
                msg = await bot_client.get_messages(channel, file_id_or_message_id)
                if msg and msg.video and msg.video.thumbs:
                    download_path = await bot_client.download_media(
                        str(msg.video.thumbs[0].file_id),
                        file_name=os.path.join(downloads_dir, cache_key)
                    )
                else:
                    logger.warning(f"No video or thumbnail found for message ID {file_id_or_message_id} in {channel}")
            else:
                download_path = await bot_client.download_media(
                    str(file_id_or_message_id),
                    file_name=os.path.join(downloads_dir, cache_key)
                )

            if download_path:
                image_cache[cache_key] = download_path
                return download_path
            else:
                return None

        except Exception as e:
            logger.error(f"Error downloading image {cache_key}: {e}", exc_info=True)
            return None
