import os
import time
import shutil
import mimetypes
import asyncio
import logging
import random
import re
import requests
import psutil
import subprocess
import math
import json
from threading import Thread
from collections import deque
from shlex import quote
from urllib.parse import urlparse, unquote, parse_qs
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from pyrogram.errors import FloodWait, MessageNotModified, MessageIdInvalid
from dotenv import load_dotenv
from flask import Flask
from auth import add_authorized_user, remove_authorized_user, is_authorized, AUTHORIZED_USERS, AUTHORIZED_USERS_FILE
from auth import BOT_OWNER_ID, get_authorized_users
from effect import send_effect_message  # ✅ Reusable import

# Load environment variables
load_dotenv()
API_ID = int(os.getenv("API_ID", "27400429"))
API_HASH = os.getenv("API_HASH", "e4585a30e42079fef123da0c70b5e5a6")
BOT_TOKEN = os.getenv("BOT_TOKEN", "8106093607:AAE3MW6Hz6Q1tmukuM_y-gsppRIC-Gixg4M")
BOT_OWNER_ID = int(os.getenv("BOT_OWNER_ID", "1056173503"))

# Channel button link 🖇️ 
WD_ZONE_NAME = os.getenv("WD_ZONE_NAME", "💧𝐖𝐃 𝐙𝐎𝐍𝐄 ™💦")
WD_ZONE_URL = os.getenv("WD_ZONE_URL", "https://t.me/Opleech_WD")
PHOTO_URL = os.getenv("PHOTO_URL", "https://i.ibb.co/j9n6nZxD/Op-log.png")
CHANNEL_NAME = os.getenv("CHANNEL_NAME", "⚡❍⊱❁ 𝐖𝐃 𝐙𝐎𝐍𝐄 ™")
CHANNEL_URL = os.getenv("CHANNEL_URL", "https://t.me/Opleech_WD")
WELCOME_URL = os.getenv("WELCOME_URL", "https://i.ibb.co/j9n6nZxD/Op-log.png")
BRAND_NOOR = os.getenv("BRAND_NOOR", "❍⊱❁ 𝐖𝐃 𝐙𝐎𝐍𝐄 ™")
BRAND_NAME = os.getenv("BRAND_NAME", "WD ZONE")

FANCY_TITLES = [
    "❛❛Jahaan shabd ruk jaate hain, wahi se khaamoshi bolti hai...❜❜",
    "❛❛Khush raho, main to ab khaamoshi ka aadi ho gaya hoon.❜❜",
    "❛❛Sab kuch badal jaata hai, bas yaadein reh jaati hain…❜❜",
    "❛❛Chot tab hi lagti hai, jab umeed hoti hai…❜❜",
    "❛❛Chup rehne ki bhi apni ek takleef hoti hai…❜❜"
]

# Validate environment variables
if not all([API_ID, API_HASH, BOT_TOKEN]):
    raise ValueError("Missing required environment variables")

# Initialize Pyrogram client
bot = Client("torrent_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# Constants
DOWNLOAD_DIR = "downloads"
MAX_SIZE = 1900 * 1024 * 1024  # 1.9GB Telegram upload limit
MAX_CONCURRENT_DOWNLOADS = 2
TIMEOUT = 1800  # 30 minutes

# Regex patterns for valid links
MAGNET_REGEX = r"^magnet:\?xt=urn:btih:([a-zA-Z0-9]+)"
TORRENT_REGEX = r"^https?://.*\.torrent(\?.*)?$"

# ✅ Improved Logging setup
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler()]
)
op_logger = logging.getLogger("op_logger")

# Add file logging handler
file_handler = logging.FileHandler('bot.log')
file_handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
op_logger.addHandler(file_handler)
op_logger.setLevel(logging.INFO)

# Initialize Flask app
flask_app = Flask(__name__)
@flask_app.route('/')
def home():
    return "Bot is running ✅"

# Start Flask server in a separate thread
Thread(target=lambda: flask_app.run(host="0.0.0.0", port=8080), daemon=True).start()

# Utility functions
def human_readable_size(size, decimal_places=2):
    for unit in ["B", "KiB", "MiB", "GiB", "TiB"]:
        if size < 1024.0:
            break
        size /= 1024.0
    return f"{size:.{decimal_places}f} {unit}"

def progress_bar(percentage, bar_length=20):
    filled = int(round(bar_length * percentage / 100))
    empty = bar_length - filled
    return "█" * filled + "░" * empty

async def safe_edit_message(message, text):
    try:
        await message.edit_text(text)
        return True
    except (FloodWait, MessageNotModified, MessageIdInvalid):
        return True
    except Exception as e:
        op_logger.error(f"Error editing message: {str(e)}")
        return False

def split_large_file(file_path, chunk_size=MAX_SIZE):
    part_num = 1
    output_files = []
    base_name = os.path.basename(file_path)
    
    with open(file_path, 'rb') as f:
        while True:
            chunk = f.read(chunk_size)
            if not chunk:
                break
            part_name = f"{base_name}.part{part_num:03d}"
            part_path = os.path.join(os.path.dirname(file_path), part_name)
            with open(part_path, 'wb') as p:
                p.write(chunk)
            output_files.append(part_path)
            part_num += 1
    
    return output_files

def clean_directory(directory):
    try:
        if os.path.exists(directory):
            shutil.rmtree(directory)
        return True
    except Exception as e:
        op_logger.error(f"Error cleaning directory: {str(e)}")
        return False

def extract_thumbnail(video_path):
    try:
        brand_name = os.getenv("BRAND_NAME") or "WOODcraft"
        text_escaped = quote(brand_name)  # Safely escape special characters
        thumbnail_path = os.path.join(os.path.dirname(video_path), "thumbnail.jpg")
        font_path = os.path.join(os.path.dirname(__file__), "wood.ttf")

        cmd = [
            "ffmpeg", "-ss", "00:00:10",
            "-i", video_path,
            "-vframes", "1",
            "-vf", f"drawtext=fontfile='{font_path}':text={text_escaped}:fontcolor=white:fontsize=40:x=(w-text_w)/2:y=h-text_h-30",
            "-q:v", "2",
            thumbnail_path
        ]

        subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=30)
        return thumbnail_path if os.path.exists(thumbnail_path) else None
    except Exception as e:
        op_logger.error(f"Thumbnail extraction failed: {str(e)}")
        return None

def get_duration(file_path):
    try:
        cmd = [
            "ffprobe", "-v", "error",
            "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1",
            file_path
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        return int(float(result.stdout.strip()))
    except Exception:
        return 0

def sanitize_filename(filename):
    return re.sub(r'[\\/*?:"<>|]', "_", filename)

def get_magnet_name(magnet_link):
    try:
        magnet_link = magnet_link.strip().replace(' ', '%20')
        if not magnet_link.startswith("magnet:?xt=urn:btih:"):
            return "Invalid Magnet Link"
        
        params = parse_qs(urlparse(magnet_link).query)
        if 'dn' in params:
            return unquote(params['dn'][0])
        
        # Extract info hash
        xt = params.get('xt', [''])[0]
        if 'urn:btih:' in xt:
            btih = xt.split('urn:btih:')[-1]
            return f"Torrent-{btih[:8].upper()}"
        return "Unknown"
    except Exception:
        return "Unknown-Torrent"

def kill_aria_processes():
    for proc in psutil.process_iter(['name']):
        if proc.info['name'] == 'aria2c':
            try:
                proc.kill()
            except:
                pass

def time_formatter(seconds: float) -> str:
    minutes, seconds = divmod(seconds, 60)
    hours, minutes = divmod(minutes, 60)
    return f"{int(hours)}h {int(minutes)}m {int(seconds)}s"

# ✅ First Button Layout
keyboard = InlineKeyboardMarkup([
    [InlineKeyboardButton(WD_ZONE_NAME, url=WD_ZONE_URL)]
])

# User session management
user_queues = {}
user_messages = {}
active_downloads = {}
user_active_tasks = {}

# ✅ Updated start handler with photo and HTML formatting
@bot.on_message(filters.command("start") & (filters.private | filters.group))
async def start_handler(client, message):
    chat_id = message.chat.id
    photo_url = WELCOME_URL
    title = random.choice(FANCY_TITLES)
    
    # HTML formatted caption
    caption = (
        f"<pre>🌟 𝗧𝗼𝗿𝗿𝗲𝗻𝘁 𝗗𝗼𝘄𝗻𝗹𝗼𝗮𝗱𝗲𝗿 𝗕𝗼𝘁! 🌟</pre>\n\n"
        f"<b>{title}</b>\n\n"
    
        "📤 <b>How to use:</b>\n"
        "Just send me magnet links or .torrent files\n"
        "I'll <b>download & upload</b> them for you!\n\n"
    
        "✨ <b>Key Features:</b>\n"
        "🔁 Unlimited Torrent + Magnet support\n"
        "📊 Real-time progress updates\n"
        "🧹 Auto cleanup after upload\n\n"
    
        "⚙️ <b>Technical Specifications:</b>\n"
        "• <b>Max File Size:</b> <code>1.9 GB</code>\n"
        "• <b>Auto Cleanup:</b> ✅ <code>Enabled</code>\n"
        "• <b>Access:</b> Authorized users only\n\n"
    
        "<b>🆔 Version:</b> <code>v1.0.2</code>"
    )

    reply_markup = {
        "inline_keyboard": [
            [{"text": CHANNEL_NAME, "url": CHANNEL_URL}]
        ]
    }

    # ✅ Send photo with effect using async
    await send_effect_message(
        chat_id, 
        text=caption,
        photo_url=photo_url,
        reply_markup=reply_markup,
        op_logger=op_logger
    )
        
async def run_aria2c(command, msg, start_time, torrent_name):
    kill_aria_processes()
    user_id = msg.chat.id
    msg_id = msg.id

    process = await asyncio.create_subprocess_exec(
        *command,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.STDOUT
    )
    
    progress_regex = re.compile(
        r'\[#\w+\s+([\d.]+\w*)/([\d.]+\w*)\((\d+)%\)\s+.*DL:([\d.]+\w*).*ETA:(\w+)\]'
    )
    last_update = time.time()
    last_reported_percent = -1

    while True:
        if user_id in active_downloads and active_downloads[user_id] != msg_id:
            process.terminate()
            return False

        elapsed = time.time() - start_time
        if elapsed > TIMEOUT:
            process.terminate()
            await safe_edit_message(msg, "❌ Download timed out after 30 minutes!")
            return False

        try:
            line = await asyncio.wait_for(process.stdout.readline(), 1.0)
        except asyncio.TimeoutError:
            if process.returncode is not None:
                break
            continue

        if not line:
            if process.returncode is not None:
                break
            continue

        line = line.decode().strip()
        op_logger.debug(f"aria2c: {line}")

        if "Download complete:" in line:
            return True

        match = progress_regex.search(line)
        if match:
            downloaded = match.group(1)
            total = match.group(2)
            percentage = int(match.group(3))
            speed = match.group(4)
            eta = match.group(5)

            if time.time() - last_update > 5 or percentage == 100:
                bar = progress_bar(percentage)
                status = (
                    f"╭━◝━━━━━━━━━━━━◜━╮\n"
                    f"⚡ {BRAND_NOOR}\n"
                    f"╰━◞━━━━━━━━━━━━◟━╯\n\n"
                    f"📤 **Downloading...**\n"
                    f"🪺 Torrent: `{torrent_name}`\n"
                    f"📦 Progress: {downloaded}/{total} ({percentage}%)\n"
                    f"🔸 {bar} 🔸\n"
                    f"🚀 Speed: {speed} | ⏳ ETA: {eta}\n"
                    f"✨❍⭕️━━━━━━━━━━━━━━━⭕️❍✨"

                )
                await safe_edit_message(msg, status)
                last_update = time.time()
                last_reported_percent = percentage

    return await process.wait() == 0

async def process_torrent(user_id, link, msg):
    timestamp = int(time.time())
    USER_DIR = os.path.join(DOWNLOAD_DIR, f"user_{user_id}_{timestamp}")
    os.makedirs(USER_DIR, exist_ok=True)

    extra_trackers = [
        "udp://tracker.openbittorrent.com:80",
        "udp://tracker.opentrackr.org:1337",
        "udp://9.rarbg.me:2710",
        "udp://9.rarbg.to:2710",
        "udp://tracker.tiny-vps.com:6969",
        "udp://open.demonii.com:1337/announce",
        "udp://tracker.internetwarriors.net:1337",
        "udp://tracker.leechers-paradise.org:6969/announce",
        "udp://exodus.desync.com:6969",
        "udp://tracker.moeking.me:6969",
        "udp://tracker.dler.org:6969",
        "udp://tracker.filemail.com:6969",
        "udp://public.popcorn-tracker.org:6969",
        "udp://explodie.org:6969",
        "udp://tracker.torrent.eu.org:451",
        "udp://tracker.cyberia.is:6969",
        "udp://p4p.arenabg.com:1337",
        "udp://tracker.bt4g.com:6969/announce",
        "udp://tracker4.itzmx.com:2710/announce",
        "udp://tracker.ccc.de:80",
        "udp://denis.stalker.upeer.me:6969/announce"
	"udp://tracker.opentrackr.org:1337/announce"
	"udp://tracker.dler.org:6969/announce"
	"udp://exodus.desync.com:6969/announce"
	"udp://open.stealth.si:80/announce"
	"udp://tracker.moeking.me:6969/announce"
	"udp://tracker.openbittorrent.com:1337/announce"
	"udp://p4p.arenabg.com:1337/announce"
	"udp://open.demonii.com:1337/announce"
	"udp://tracker.torrent.eu.org:451/announce"
	"udp://tracker.bittor.pw:1337/announce"
	"udp://explodie.org:6969/announce"
	"udp://tracker.filemail.com:6969/announce"
	"udp://tracker.tiny-vps.com:6969/announce"
	"udp://public.popcorn-tracker.org:6969/announce"
    ]

    start_time = time.time()
    torrent_file_path = None
    torrent_name = "Unknown"

    try:
        # Handle magnet links
        if link.startswith("magnet:?"):
            torrent_name = get_magnet_name(link)
            await safe_edit_message(msg, f"🔗 Magnet link detected: {torrent_name}\n📥 Starting download...")
            download_link = link
        
        # Handle .torrent URLs
        elif link.lower().endswith('.torrent') or '.torrent' in link.lower():
            try:
                await safe_edit_message(msg, "📥 Downloading torrent file...")
                response = requests.get(link, headers={'User-Agent': 'Mozilla/5.0'}, timeout=30)
                response.raise_for_status()
                
                # Extract filename
                if "content-disposition" in response.headers:
                    fname = re.findall(r'filename\*?=[\'"]?(?:UTF-\d[\'"]*)?([^;\'"]+)', 
                                      response.headers["content-disposition"], 
                                      re.IGNORECASE)
                    filename = unquote(fname[0]) if fname else os.path.basename(urlparse(link).path)
                else:
                    filename = os.path.basename(urlparse(link).path)
                
                if not filename.lower().endswith('.torrent'):
                    filename += '.torrent'
                
                filename = sanitize_filename(filename)
                torrent_name = filename.replace('.torrent', '')
                torrent_file_path = os.path.join(USER_DIR, filename)
                
                with open(torrent_file_path, 'wb') as f:
                    f.write(response.content)
                
                download_link = torrent_file_path
                await safe_edit_message(msg, f"📥 Torrent file downloaded: {torrent_name}\n🚀 Starting content download...")
            except Exception as e:
                await safe_edit_message(msg, f"❌ Torrent download failed: {str(e)}")
                return False
        else:
            await safe_edit_message(msg, "❌ Invalid torrent or magnet link!")
            return False

        cmd = [
            "aria2c",
            "--console-log-level=info",
            "--enable-color=false",
            "--console-log-level=notice",
            "--log-level=warn",
            "--allow-overwrite=true",
            "--check-certificate=false",
            "--auto-file-renaming=true",
            "--allow-overwrite=true",
            "--file-allocation=none",
            "--enable-dht=true",
            "--bt-enable-lpd=true",
            "--bt-save-metadata=true",
            "--seed-time=0",
            "--max-connection-per-server=16",
            "--bt-tracker=" + ",".join(extra_trackers),
            "--split=16",
            "--max-concurrent-downloads=5",
            "--file-allocation=none",
            "--summary-interval=1",
            "--dir=" + USER_DIR,
            download_link
        ]

        op_logger.info(f"Starting download: {' '.join(cmd)}")
        download_success = await run_aria2c(cmd, msg, start_time, torrent_name)
        
        if not download_success:
            await safe_edit_message(msg, "❌ Download failed or canceled")
            return False
            
        # Find downloaded files
        files = []
        for root, _, filenames in os.walk(USER_DIR):
            for filename in filenames:
                filepath = os.path.join(root, filename)
                if (os.path.exists(filepath) and 
                    os.path.getsize(filepath) > 0 and
                    not filename.endswith(('.aria2', '.tmp'))):
                    files.append(filepath)
        
        if not files:
            await safe_edit_message(msg, "❌ No files found after download")
            return False

        await safe_edit_message(msg, f"📁 Found {len(files)} files. Starting uploads...")
        
        for filepath in files:
            filename = os.path.basename(filepath)
            size = os.path.getsize(filepath)

            if size < 1024:  # Skip empty files
                continue

            if size > MAX_SIZE:
                await safe_edit_message(msg, f"⚠️ Splitting large file: {filename}")
                file_parts = split_large_file(filepath)
                os.remove(filepath)
            else:
                file_parts = [filepath]

            total_parts = len(file_parts)
            for part_index, part in enumerate(file_parts, 1):
                part_name = os.path.basename(part)
                part_size = os.path.getsize(part)
                
                await safe_edit_message(
                    msg,
                    f"╭━◝━━━━━━━━━━━━◜━╮\n"
                    f"⚡ {BRAND_NOOR}\n"
                    f"╰━◞━━━━━━━━━━━━◟━╯\n\n"
                    f"📤 **Uploading...**\n"
                    f"📁 File: `{filename}`\n"
                    f"🔸 Part: `{part_index}/{total_parts}`\n"
                    f"📦 Size: `{human_readable_size(part_size)}`\n"
                    f"✨❍⭕️━━━━━━━━━━━━━━━⭕️❍✨"
                )
                
                mime, _ = mimetypes.guess_type(part)
                
                try:
                    if mime and mime.startswith("video"):
                        thumbnail = extract_thumbnail(part)
                        duration = get_duration(part)
                        
                        await msg.reply_video(
                            video=part,
                            caption=f"🎬 {filename}",
                            reply_markup=keyboard,
                            supports_streaming=True,
                            duration=duration,
                            thumb=thumbnail or None,
                            progress=create_upload_callback(msg, part_name)
                        )
                        
                        if thumbnail and os.path.exists(thumbnail):
                            os.remove(thumbnail)
                    else:
                        await msg.reply_document(
                            document=part,
                            caption=f"📦 {filename}",
                            reply_markup=keyboard,
                            progress=create_upload_callback(msg, part_name)
                        )
                except Exception as e:
                    op_logger.error(f"Upload failed: {e}")
                    await safe_edit_message(msg, f"❌ Upload failed: {str(e)}")
                finally:
                    if os.path.exists(part):
                        os.remove(part)
        return True
    except Exception as e:
        op_logger.error(f"Processing error: {str(e)}")
        await safe_edit_message(msg, f"❌ Processing error: {str(e)}")
        return False
    finally:
        clean_directory(USER_DIR)

def create_upload_callback(msg, part_name):
    last_reported = 0
    
    async def callback(current, total):
        nonlocal last_reported
        if total == 0:
            return
            
        percent = math.floor(current * 100 / total)
        current_time = time.time()
        
        if percent == 100 or current_time - last_reported > 5:
            text = (
                f"╭━◝━━━━━━━━━━━━◜━╮\n"
                f"⚡ {BRAND_NOOR}\n"
                f"╰━◞━━━━━━━━━━━━◟━╯\n\n"
                f"📤 **Uploading...**\n"
                f"📁 File: `{part_name}`\n"
                f"📊 Progress: {human_readable_size(current)} / {human_readable_size(total)}\n"
                f"🔸 {progress_bar(percent)} 🔸\n"
                f"✨❍⭕️━━━━━━━━━━━━━━━⭕️❍✨"
            )
            await safe_edit_message(msg, text)
            last_reported = current_time
    
    return callback

async def process_user_queue(user_id):
    while user_queues.get(user_id) and user_queues[user_id]:
        link = user_queues[user_id][0]
        try:
            # Create processing message
            msg = await bot.send_message(user_id, "🔄 Processing started...")
            user_messages[user_id] = msg
            active_downloads[user_id] = msg.id

            # Process torrent
            success = await process_torrent(user_id, link, msg)
            
            if not success:
                await safe_edit_message(msg, "❌ Processing failed")
            else:
                try:
                    await msg.delete()
                except:
                    pass

        except Exception as e:
            op_logger.error(f"Queue processing error: {str(e)}")
            if user_id in user_messages:
                await safe_edit_message(user_messages[user_id], f"❌ Error: {str(e)}")
        finally:
            # Cleanup queue
            if user_queues.get(user_id):
                user_queues[user_id].popleft()
                
                if not user_queues[user_id]:
                    del user_queues[user_id]
                    if user_id in user_messages:
                        del user_messages[user_id]
                    if user_id in active_downloads:
                        del active_downloads[user_id]

        # Rate limiting
        await asyncio.sleep(1)

    # Cleanup after queue is empty
    if user_id in user_active_tasks:
        user_active_tasks[user_id] -= 1
        if user_active_tasks[user_id] <= 0:
            del user_active_tasks[user_id]
            
# ✅ Add user command (BOT_OWNER_ID চেক সহ)
@bot.on_message(filters.command("adduser"))
async def add_user_cmd(client, message):
    if message.from_user.id != BOT_OWNER_ID:
        return await message.reply("🚫 You cannot run this command.")

    try:
        op_logger.info("Adduser command triggered")
        args = message.text.split()

        if len(args) < 2:
            return await message.reply("❌ Use: /adduser <user_id>")

        try:
            new_id = int(args[1])
        except ValueError:
            return await message.reply("❌ Invalid user ID! Enter a number.")

        result = add_authorized_user(new_id)

        if result:
            await message.reply(f"✅ User `{new_id}` Added!")

            # ✅ ইউজারকে নোটিফাই করা হচ্ছে
            try:
                await client.send_message(new_id, "✅ You've been added to the authorized user list.")
                op_logger.info(f"Notified user {new_id}")
            except Exception as e:
                op_logger.warning(f"Couldn't message user {new_id}: {e}")

        else:
            await message.reply(f"ℹ️ User `{new_id}` It was already added.")
    except Exception as e:
        op_logger.exception("Error in adduser")
        await message.reply(f"❌ ত্রুটি: {str(e)}")

# ✅ Remove user command (BOT_OWNER_ID চেক সহ)
@bot.on_message(filters.command("removeuser"))
async def remove_user_cmd(client, message):
    if message.from_user.id != BOT_OWNER_ID:
        return await message.reply("🚫 You cannot run this command.")

    try:
        op_logger.info("Removeuser command triggered")
        args = message.text.split()

        if len(args) < 2:
            return await message.reply("❌ Use: /removeuser <user_id>")

        try:
            uid = int(args[1])
        except ValueError:
            return await message.reply("❌ Invalid user ID! Enter a number.")

        result = remove_authorized_user(uid)

        if result:
            await message.reply(f"❎ User `{uid}` Who has moved!")
        else:
            await message.reply(f"⚠️ User `{uid}` was not allowed.")
    except Exception as e:
        op_logger.exception("Error in removeuser")
        await message.reply(f"❌ ত্রুটি: {str(e)}")

# ✅ Userlist command (Plain text formatting)
@bot.on_message(filters.command("userlist"))
async def list_users(client, message):
    if message.from_user.id != BOT_OWNER_ID:
        op_logger.warning(f"Unauthorized /userlist access attempt by: {message.from_user.id}")
        return await message.reply("🚫 You cannot run this command.")

    op_logger.info(f"/userlist command triggered by: {message.from_user.id}")

    try:
        users = get_authorized_users()
        op_logger.info(f"AUTHORIZED_USERS inside /userlist: {users}")

        if not users:
            op_logger.warning("User list is empty!")
            return await message.reply("⚠️ There are no authorized users.")

        # ✅ Plain টেক্সটে সুন্দর ডিজাইন
        text = "👤 **Authorized User List:**\n"
        text += "═══════════════════════\n"

        for i, uid in enumerate(users, start=1):
            try:
                user = await client.get_users(uid)
                name = user.first_name or "No name"
                op_logger.info(f"User #{i}: {name} ({uid})")
                text += f"🔹 {i}. {name}\n🆔 {uid}\n\n"
            except Exception as e:
                name = "Name not found (❗Hasn't started the bot)"
                op_logger.warning(f"User ID {uid} fetch failed: {str(e)}")
                text += f"🔹 {i}. {name}\n🆔 {uid}\n\n"

        text += "═══════════════════════"

        # ✅ Inline button
        developer = InlineKeyboardMarkup([
            [InlineKeyboardButton("👤 𝐃𝐞𝐯𝐞𝐥𝐨𝐩𝐞𝐫 👤", url="https://t.me/Farooq_is_king")]
        ])

        # ✅ Try sending with image
        try:
            await message.reply_photo(
                photo=PHOTO_URL,
                caption=text,
                reply_markup=developer
            )
        except Exception as e:
            op_logger.warning(f"Couldn't send photo: {e}")
            await message.reply(
                text=text,
                reply_markup=developer,
                disable_web_page_preview=True
            )

        op_logger.info("/userlist executed successfully.")

    except Exception as e:
        op_logger.exception(f"❌ Error in /userlist command: {str(e)}")
        await message.reply(f"❌ Error: {str(e)}")
        
# ✅ Permission check: সবশেষে রাখুন
@bot.on_message((filters.private | filters.group) & filters.text)
async def message_handler(client: Client, message: Message):
    if not is_authorized(message.from_user.id):
        await message.reply("🚫 You are not authorized to use this bot.")
        return
    
    user_id = message.from_user.id
    text = message.text.strip()

    is_magnet = re.match(MAGNET_REGEX, text, re.IGNORECASE)
    is_torrent = re.match(TORRENT_REGEX, text, re.IGNORECASE)

    if not (is_magnet or is_torrent):
        return

    if user_id not in user_queues:
        user_queues[user_id] = deque()
    if user_id not in user_active_tasks:
        user_active_tasks[user_id] = 0

    user_queues[user_id].append(text)
    position = len(user_queues[user_id])

    if position > 1 or user_active_tasks[user_id] >= MAX_CONCURRENT_DOWNLOADS:
        msg = await message.reply(f"📥 Added to queue. Position: {position}")
        user_messages[user_id] = msg
    else:
        user_active_tasks[user_id] += 1
        asyncio.create_task(process_user_queue(user_id))

        
# Periodic cleanup
async def cleanup_scheduler():
    while True:
        try:
            if os.path.exists(DOWNLOAD_DIR):
                for entry in os.listdir(DOWNLOAD_DIR):
                    path = os.path.join(DOWNLOAD_DIR, entry)
                    if os.path.isdir(path):
                        # Delete directories older than 1 hour
                        if time.time() - os.path.getmtime(path) > 3600:
                            clean_directory(path)
        except Exception as e:
            op_logger.error(f"Cleanup error: {str(e)}")
        await asyncio.sleep(3600)

# Start the bot
if __name__ == "__main__":
    op_logger.info("🚀 Starting Torrent Downloader Bot...")
    os.makedirs(DOWNLOAD_DIR, exist_ok=True)
    
    # Log the authorized users file path
    op_logger.info(f"Authorized users file: {AUTHORIZED_USERS_FILE}")
    op_logger.info(f"Initial authorized users: {AUTHORIZED_USERS}")
    
    # Create background tasks
    loop = asyncio.get_event_loop()
    loop.create_task(cleanup_scheduler())
    
    # Start the bot
    bot.run()
