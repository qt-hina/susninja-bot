import os
import sys
import time
import random
import logging
import threading
import weakref
import asyncio
import concurrent.futures
from collections import defaultdict, deque
from datetime import datetime, timedelta
from typing import Dict, Optional, Set
from http.server import BaseHTTPRequestHandler, HTTPServer
from aiogram import Bot, Dispatcher, F, types
from aiogram.filters import Command
from aiogram.types import (
    BotCommand,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message
)
from aiogram.utils.keyboard import InlineKeyboardBuilder

# Environment variables and config
BOT_TOKEN = os.getenv("BOT_TOKEN", "YOUR_BOT_TOKEN_HERE")
CHANNEL_URL = "https://t.me/WorkGlows"
GROUP_URL = "https://t.me/SoulMeetsHQ"
OWNER_ID = 5290407067
PORT = int(os.environ.get("PORT", 10000))

# Performance configurations
MAX_MESSAGES_PER_CHAT = 1000
MESSAGE_TTL = 3600
CLEANUP_INTERVAL = 300
MAX_MESSAGE_LENGTH = 4096

# Bot data structures
broadcast_mode = set()
broadcast_target = {}
user_ids = set()
group_ids = set()

# Message cache data structures
messages: Dict[int, Dict[int, dict]] = defaultdict(dict)
chat_queues: Dict[int, deque] = defaultdict(lambda: deque(maxlen=MAX_MESSAGES_PER_CHAT))
recent_message_ids: Dict[int, Set[int]] = defaultdict(set)
last_cleanup = time.time()

# Bot messages
WELCOME_MSG = """
💖 <b>Hey {user_mention}, welcome aboard!</b>

💓 I'm your sweet little spy for message edits.

<blockquote>Every time someone edits a message, I catch it 💘</blockquote>

<i>💌 Just add me to your group and I'll take care of the rest!</i>
"""

HELP_MSG_BASIC = """
💖 <b>Hey {user_mention}, need help?</b>

<blockquote>💘 Here's what I can do:
├─ <b>/start</b> – Wake me up   
├─ <b>/help</b> – Show this guide  
└─ <b>/ping</b> – Check if I'm alive</blockquote>  
<blockquote>📖 How I work:
├─ Add me to your group  
├─ Make me admin 
├─ I watch everything quietly  
└─ Someone acts sus? I'll let you know</blockquote>
"""

HELP_MSG_EXPANDED = """
💖 <b>Sus Ninja Manual for {user_mention}</b>

<blockquote><b>📦 Basic Commands:</b>
├─ /start – Wake me up  
├─ /help – This spicy guide  
└─ /ping – Check my heartbeat</blockquote>

<blockquote><b>👥 Group Setup:</b>
├─ Add me to your group  
├─ Make me admin  
├─ I'll quietly watch everything  
└─ Caught? I expose it</blockquote>

<blockquote><b>📖 What I Do:</b>
├─ Catch edited messages  
├─ Remember everything  
└─ React super fast</blockquote>

Need help? Just tap in 💖
"""

GROUP_WELCOME_MSG = """👋 Hey everyone! Thanks for adding me!

I'm now watching your group for sneaky deletes and edits.

Important: Give me admin powers so I can do my magic! 💖

Type /help to see all my naughty tricks!"""

# Bot commands list
BOT_COMMANDS = [
    ("start", "⚔️ Awaken Sus Ninja"),
    ("help", "🥷 Ninja Techniques")
]

# IMAGES LIST
IMAGES = [
    "https://ik.imagekit.io/asadofc/Images1.png",
    "https://ik.imagekit.io/asadofc/Images2.png",
    "https://ik.imagekit.io/asadofc/Images3.png",
    "https://ik.imagekit.io/asadofc/Images4.png",
    "https://ik.imagekit.io/asadofc/Images5.png",
    "https://ik.imagekit.io/asadofc/Images6.png",
    "https://ik.imagekit.io/asadofc/Images7.png",
    "https://ik.imagekit.io/asadofc/Images8.png",
    "https://ik.imagekit.io/asadofc/Images9.png",
    "https://ik.imagekit.io/asadofc/Images10.png",
    "https://ik.imagekit.io/asadofc/Images11.png",
    "https://ik.imagekit.io/asadofc/Images12.png",
    "https://ik.imagekit.io/asadofc/Images13.png",
    "https://ik.imagekit.io/asadofc/Images14.png",
    "https://ik.imagekit.io/asadofc/Images15.png",
    "https://ik.imagekit.io/asadofc/Images16.png",
    "https://ik.imagekit.io/asadofc/Images17.png",
    "https://ik.imagekit.io/asadofc/Images18.png",
    "https://ik.imagekit.io/asadofc/Images19.png",
    "https://ik.imagekit.io/asadofc/Images20.png",
    "https://ik.imagekit.io/asadofc/Images21.png",
    "https://ik.imagekit.io/asadofc/Images22.png",
    "https://ik.imagekit.io/asadofc/Images23.png",
    "https://ik.imagekit.io/asadofc/Images24.png",
    "https://ik.imagekit.io/asadofc/Images25.png",
    "https://ik.imagekit.io/asadofc/Images26.png",
    "https://ik.imagekit.io/asadofc/Images27.png",
    "https://ik.imagekit.io/asadofc/Images28.png",
    "https://ik.imagekit.io/asadofc/Images29.png",
    "https://ik.imagekit.io/asadofc/Images30.png",
    "https://ik.imagekit.io/asadofc/Images31.png",
    "https://ik.imagekit.io/asadofc/Images32.png",
    "https://ik.imagekit.io/asadofc/Images33.png",
    "https://ik.imagekit.io/asadofc/Images34.png",
    "https://ik.imagekit.io/asadofc/Images35.png",
    "https://ik.imagekit.io/asadofc/Images36.png",
    "https://ik.imagekit.io/asadofc/Images37.png",
    "https://ik.imagekit.io/asadofc/Images38.png",
    "https://ik.imagekit.io/asadofc/Images39.png",
    "https://ik.imagekit.io/asadofc/Images40.png"
]

# LOGGING SETUP
class Colors:
    BLUE = '\033[94m'      # INFO/WARNING
    GREEN = '\033[92m'     # DEBUG
    YELLOW = '\033[93m'    # INFO
    RED = '\033[91m'       # ERROR
    RESET = '\033[0m'      # Reset color
    BOLD = '\033[1m'       # Bold text

class ColoredFormatter(logging.Formatter):
    """Custom formatter to add colors to entire log messages"""

    COLORS = {
        'DEBUG': Colors.GREEN,
        'INFO': Colors.YELLOW,
        'WARNING': Colors.BLUE,
        'ERROR': Colors.RED,
    }

    def format(self, record):
        # Get the original formatted message
        original_format = super().format(record)

        # Get color based on log level
        color = self.COLORS.get(record.levelname, Colors.RESET)

        # Apply color to the entire message
        colored_format = f"{color}{original_format}{Colors.RESET}"

        return colored_format

# Configure logging with colors
def setup_colored_logging():
    """Setup colored logging configuration"""
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.INFO)

    # Remove existing handlers
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)

    # Create console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.DEBUG)

    # Create colored formatter with enhanced format
    formatter = ColoredFormatter(
        fmt='%(asctime)s - %(name)s - [%(levelname)s] - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    console_handler.setFormatter(formatter)

    # Add handler to logger
    logger.addHandler(console_handler)

    return logger

# Initialize colored logger
logger = setup_colored_logging()

# Now log the configuration after logger is set up
logger.info(f"🔧 Configuration loaded - Port: {PORT}, Owner ID: {OWNER_ID}")
logger.info(f"⚙️ Performance config - Max messages: {MAX_MESSAGES_PER_CHAT}, TTL: {MESSAGE_TTL}s, Cleanup: {CLEANUP_INTERVAL}s")
logger.info("🗄️ Data structures initialized")
logger.info("📝 Bot messages and commands configured")

# Initialize Bot and Dispatcher at module level
bot = None
dp = Dispatcher()  # Initialize dispatcher here!
active_chats: Set[int] = set()
edit_data_cache = {}

def extract_user_info(msg: Message) -> Dict[str, any]:
    """Extract user and chat information from message"""
    logger.debug("🔍 Extracting user information from message")
    try:
        u = msg.from_user
        c = msg.chat
        info = {
            "user_id": u.id if u else None,
            "username": u.username if u else None,
            "full_name": u.full_name if u else "Unknown",
            "first_name": u.first_name if u else None,
            "last_name": u.last_name if u else None,
            "chat_id": c.id,
            "chat_type": c.type,
            "chat_title": c.title or c.first_name or "",
            "chat_username": f"@{c.username}" if c.username else "No Username",
            "chat_link": f"https://t.me/{c.username}" if c.username else "No Link",
        }
        logger.info(
            f"📑 User info extracted: {info['full_name']} (@{info['username']}) "
            f"[ID: {info['user_id']}] in {info['chat_title']} [{info['chat_id']}] {info['chat_link']}"
        )
        return info
    except Exception as e:
        logger.error(f"❌ Failed to extract user info: {e}")
        return {
            "user_id": None,
            "username": None,
            "full_name": "Unknown",
            "first_name": None,
            "last_name": None,
            "chat_id": msg.chat.id if msg.chat else None,
            "chat_type": msg.chat.type if msg.chat else None,
            "chat_title": "Unknown",
            "chat_username": "No Username",
            "chat_link": "No Link",
        }

def log_with_user_info(level: str, message: str, user_info: Dict[str, any]) -> None:
    """Log message with user information"""
    try:
        user_detail = (
            f"👤 {user_info['full_name']} (@{user_info['username']}) "
            f"[ID: {user_info['user_id']}] | "
            f"💬 {user_info['chat_title']} [{user_info['chat_id']}] "
            f"({user_info['chat_type']}) {user_info['chat_link']}"
        )
        full_message = f"{message} | {user_detail}"

        if level.upper() == "INFO":
            logger.info(full_message)
        elif level.upper() == "DEBUG":
            logger.debug(full_message)
        elif level.upper() == "WARNING":
            logger.warning(full_message)
        elif level.upper() == "ERROR":
            logger.error(full_message)
        else:
            logger.info(full_message)
    except Exception as e:
        logger.error(f"❌ Failed to log with user info: {e}")
        # Fallback to simple logging
        getattr(logger, level.lower(), logger.info)(message)

# HTTP server for deployment
class DummyHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        try:
            logger.debug(f"🌐 HTTP GET request from {self.client_address[0]}")
            self.send_response(200)
            self.send_header('Content-Type', 'text/plain')
            self.end_headers()
            self.wfile.write(b"Sus Ninja Bot is alive and running!")
        except Exception as e:
            logger.error(f"❌ HTTP GET error: {e}")

    def do_HEAD(self):
        try:
            logger.debug(f"🌐 HTTP HEAD request from {self.client_address[0]}")
            self.send_response(200)
            self.send_header('Content-Type', 'text/plain')
            self.end_headers()
        except Exception as e:
            logger.error(f"❌ HTTP HEAD error: {e}")

    def log_message(self, format, *args):
        pass  # Disable HTTP logging

def start_dummy_server():
    # Start HTTP server for deployment
    try:
        logger.info(f"🌐 Starting HTTP server on port {PORT}")
        server = HTTPServer(("0.0.0.0", PORT), DummyHandler)
        logger.info(f"✅ HTTP server successfully started on port {PORT}")
        server.serve_forever()
    except Exception as e:
        logger.error(f"❌ HTTP server critical error: {e}")
        raise

# Message cache functions
def add_message(chat_id: int, message: Message) -> None:
    # Add message to cache
    try:
        logger.debug(f"💾 Adding message {message.message_id} to cache for chat {chat_id}")
        user_info = message.from_user
        msg_data = {
            'message_id': message.message_id,
            'text': message.text or message.caption or "",
            'user_id': user_info.id if user_info else None,
            'username': user_info.username if user_info else None,
            'first_name': user_info.first_name if user_info else None,
            'last_name': user_info.last_name if user_info else None,
            'timestamp': time.time(),
            'date': message.date,
            'reply_to_message_id': message.reply_to_message.message_id if message.reply_to_message else None
        }
        
        messages[chat_id][message.message_id] = msg_data
        recent_message_ids[chat_id].add(message.message_id)
        
        queue = chat_queues[chat_id]
        if len(queue) >= MAX_MESSAGES_PER_CHAT:
            oldest_msg_id = queue.popleft()
            messages[chat_id].pop(oldest_msg_id, None)
            recent_message_ids[chat_id].discard(oldest_msg_id)
            logger.debug(f"🗑️ Removed oldest message {oldest_msg_id} from cache due to size limit")
        
        queue.append(message.message_id)
        logger.info(f"✅ Message {message.message_id} cached successfully for chat {chat_id}")
        
    except Exception as e:
        logger.error(f"❌ Cache add error for message {message.message_id} in chat {chat_id}: {e}")

def get_message(chat_id: int, message_id: int) -> Optional[dict]:
    # Get message from cache
    try:
        logger.debug(f"🔍 Retrieving message {message_id} from cache for chat {chat_id}")
        msg_data = messages.get(chat_id, {}).get(message_id)
        if msg_data:
            logger.debug(f"✅ Message {message_id} found in cache")
        else:
            logger.debug(f"❌ Message {message_id} not found in cache")
        return msg_data
    except Exception as e:
        logger.error(f"❌ Cache retrieval error for message {message_id} in chat {chat_id}: {e}")
        return None

def remove_message(chat_id: int, message_id: int) -> Optional[dict]:
    # Remove message from cache
    try:
        logger.debug(f"🗑️ Removing message {message_id} from cache for chat {chat_id}")
        msg_data = messages.get(chat_id, {}).pop(message_id, None)
        if msg_data:
            try:
                chat_queues[chat_id].remove(message_id)
                logger.debug(f"✅ Message {message_id} removed from queue")
            except ValueError:
                logger.warning(f"⚠️ Message {message_id} not found in queue during removal")
            recent_message_ids[chat_id].discard(message_id)
            logger.info(f"✅ Message {message_id} successfully removed from cache")
        else:
            logger.debug(f"❌ Message {message_id} not found for removal")
        return msg_data
    except Exception as e:
        logger.error(f"❌ Cache removal error for message {message_id} in chat {chat_id}: {e}")
        return None

def cleanup_expired() -> None:
    # Remove expired messages
    global last_cleanup
    current_time = time.time()
    if current_time - last_cleanup < CLEANUP_INTERVAL:
        return
        
    try:
        logger.info("🧹 Starting expired message cleanup")
        total_removed = 0
        
        for chat_id in list(messages.keys()):
            chat_messages = messages[chat_id]
            expired_msg_ids = []
            
            for msg_id, msg_data in chat_messages.items():
                if current_time - msg_data['timestamp'] > MESSAGE_TTL:
                    expired_msg_ids.append(msg_id)
            
            if expired_msg_ids:
                logger.debug(f"🗑️ Found {len(expired_msg_ids)} expired messages in chat {chat_id}")
                for msg_id in expired_msg_ids:
                    chat_messages.pop(msg_id, None)
                    try:
                        chat_queues[chat_id].remove(msg_id)
                    except ValueError:
                        pass
                    recent_message_ids[chat_id].discard(msg_id)
                    total_removed += 1
            
            if not chat_messages:
                logger.debug(f"🧹 Cleaning up empty chat data for {chat_id}")
                del messages[chat_id]
                del chat_queues[chat_id]
                if chat_id in recent_message_ids:
                    del recent_message_ids[chat_id]
        
        last_cleanup = current_time
        logger.info(f"✅ Cleanup completed - Removed {total_removed} expired messages")
            
    except Exception as e:
        logger.error(f"❌ Cleanup error: {e}")

# Handler functions with decorators - NOW dp is initialized!
@dp.message(Command("start"))
async def start_command(message: Message) -> None:
    try:
        user_info = extract_user_info(message)
        log_with_user_info("INFO", "🚀 /start command received", user_info)
        
        if message.from_user:
            user_ids.add(message.from_user.id)
            logger.debug(f"👤 User {message.from_user.id} added to user_ids set")
        
        # Cancel broadcast mode if active
        if message.from_user and message.from_user.id in broadcast_mode:
            broadcast_mode.discard(message.from_user.id)
            if message.from_user.id in broadcast_target:
                del broadcast_target[message.from_user.id]
            logger.info(f"📡 Broadcast mode cancelled for user {message.from_user.id}")
            await message.reply("🌷 Broadcast's off! Spam mission canceled, sweetie! 📡💥", parse_mode="HTML")
            return
        
        # Create user mention
        if message.from_user:
            user_mention = f'<a href="tg://user?id={message.from_user.id}">{message.from_user.full_name}</a>'
            welcome_text = WELCOME_MSG.format(user_mention=user_mention)
        else:
            welcome_text = WELCOME_MSG.format(user_mention="cutie")
        
        # Create keyboard
        builder = InlineKeyboardBuilder()
        builder.row(
            InlineKeyboardButton(text="Updates", url=CHANNEL_URL),
            InlineKeyboardButton(text="Support", url=GROUP_URL)
        )
        
        bot_info = await bot.get_me()
        builder.row(
            InlineKeyboardButton(
                text="Add Me To Your Group", 
                url=f"https://t.me/{bot_info.username}?startgroup=true"
            )
        )
        
        # Get random image
        random_image = random.choice(IMAGES)
        
        await message.reply_photo(
            photo=random_image,
            caption=welcome_text, 
            reply_markup=builder.as_markup(), 
            parse_mode="HTML"
        )
        log_with_user_info("INFO", "✅ /start command completed successfully", user_info)
        
    except Exception as e:
        user_info = extract_user_info(message) if message else {"user_id": "unknown", "full_name": "unknown"}
        log_with_user_info("ERROR", f"❌ Start command error: {e}", user_info)
        try:
            await message.reply("🌷 Oops! My circuits glitched. Try again, please! ⚡")
        except Exception as reply_error:
            logger.error(f"❌ Failed to send error reply: {reply_error}")

@dp.message(Command("help"))
async def help_command(message: Message) -> None:
    try:
        user_info = extract_user_info(message)
        log_with_user_info("INFO", "❓ /help command received", user_info)
        
        if message.from_user:
            user_ids.add(message.from_user.id)
            logger.debug(f"👤 User {message.from_user.id} added to user_ids set")
        
        # Create user mention
        if message.from_user:
            user_mention = f'<a href="tg://user?id={message.from_user.id}">{message.from_user.full_name}</a>'
            help_text = HELP_MSG_BASIC.format(user_mention=user_mention)
        else:
            help_text = HELP_MSG_BASIC.format(user_mention="there cutie")
        
        builder = InlineKeyboardBuilder()
        builder.row(
            InlineKeyboardButton(text="📖 Expand Guide", callback_data="help_expand")
        )
        
        # Get random image
        random_image = random.choice(IMAGES)
        
        await message.reply_photo(
            photo=random_image,
            caption=help_text, 
            reply_markup=builder.as_markup(), 
            parse_mode="HTML"
        )
        log_with_user_info("INFO", "✅ /help command completed successfully", user_info)
        
    except Exception as e:
        user_info = extract_user_info(message) if message else {"user_id": "unknown", "full_name": "unknown"}
        log_with_user_info("ERROR", f"❌ Help command error: {e}", user_info)
        try:
            await message.reply("🌷 Uh oh! Help system crashed! Trying to fix it! 🔧")
        except Exception as reply_error:
            logger.error(f"❌ Failed to send help error reply: {reply_error}")

@dp.message(Command("ping"))
async def ping_command(message: Message) -> None:
    try:
        user_info = extract_user_info(message)
        log_with_user_info("INFO", "🏓 /ping command received", user_info)
        
        if message.from_user:
            user_ids.add(message.from_user.id)
        
        start_time = time.time()
        bot_info = await bot.get_me()
        response_time = round((time.time() - start_time) * 1000, 2)
        
        status_text = f'🏓 <a href="{GROUP_URL}">Pong!</a> {response_time}ms'
        
        await message.reply(status_text, parse_mode="HTML", disable_web_page_preview=True)
        log_with_user_info("INFO", f"✅ /ping command completed - Response time: {response_time}ms", user_info)
        
    except Exception as e:
        user_info = extract_user_info(message) if message else {"user_id": "unknown", "full_name": "unknown"}
        log_with_user_info("ERROR", f"❌ Ping command error: {e}", user_info)
        try:
            await message.reply("🏓 Pong! I'm alive!")
        except Exception as reply_error:
            logger.error(f"❌ Failed to send ping error reply: {reply_error}")

@dp.message(Command("broadcast"))
async def broadcast_command(message: Message) -> None:
    try:
        user_info = extract_user_info(message)
        log_with_user_info("INFO", "📡 /broadcast command received", user_info)
        
        if not message.from_user or message.from_user.id != OWNER_ID:
            log_with_user_info("WARNING", "⛔ Unauthorized broadcast attempt", user_info)
            response = await message.answer("⛔ This command is restricted.")
            return

        user_ids.add(message.from_user.id)

        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text=f"👥 Users ({len(user_ids)})", callback_data="broadcast_users"),
                InlineKeyboardButton(text=f"📢 Groups ({len(group_ids)})", callback_data="broadcast_groups")
            ]
        ])

        response = await message.answer(
            "📣 <b>Choose broadcast target:</b>\n\n"
            f"👥 <b>Users:</b> {len(user_ids)} individual users\n"
            f"📢 <b>Groups:</b> {len(group_ids)} groups\n\n"
            "Select where you want to send your broadcast message:",
            reply_markup=keyboard,
            parse_mode="HTML"
        )
        
        log_with_user_info("INFO", f"✅ Broadcast menu displayed - Users: {len(user_ids)}, Groups: {len(group_ids)}", user_info)
        
    except Exception as e:
        user_info = extract_user_info(message) if message else {"user_id": "unknown", "full_name": "unknown"}
        log_with_user_info("ERROR", f"❌ Broadcast command error: {e}", user_info)
        try:
            await message.reply("🌷 Uh oh! Broadcast system had a meltdown! Hang tight! 📡🔥")
        except Exception as reply_error:
            logger.error(f"❌ Failed to send broadcast error reply: {reply_error}")

@dp.message(F.chat.type == "private")
async def handle_private_message(message: Message) -> None:
    try:
        user_info = extract_user_info(message)
        log_with_user_info("DEBUG", "💌 Private message received", user_info)
        
        # Check broadcast mode first
        if message.from_user and message.from_user.id in broadcast_mode:
            logger.info(f"📡 Processing broadcast message from user {message.from_user.id}")
            target = broadcast_target.get(message.from_user.id, "users")
            target_list = user_ids if target == "users" else group_ids

            success_count = 0
            failed_count = 0

            logger.info(f"📤 Starting broadcast to {len(target_list)} {target}")
            
            for target_id in target_list:
                try:
                    await bot.copy_message(
                        chat_id=target_id,
                        from_chat_id=message.chat.id,
                        message_id=message.message_id
                    )
                    success_count += 1
                    logger.debug(f"✅ Broadcast sent to {target_id}")
                except Exception as broadcast_error:
                    failed_count += 1
                    logger.debug(f"❌ Broadcast failed to {target_id}: {broadcast_error}")

            # Send broadcast summary
            await message.answer(
                f"📊 <b>Broadcast Summary:</b>\n\n"
                f"✅ <b>Sent:</b> {success_count}\n"
                f"❌ <b>Failed:</b> {failed_count}\n"
                f"🎯 <b>Target:</b> {target}\n\n"
                "🔥 Broadcast mode is STILL ACTIVE! Send another message to continue your spam mission or use /start to abort! 📡💥",
                parse_mode="HTML"
            )

            # Remove from broadcast mode
            broadcast_mode.discard(message.from_user.id)
            if message.from_user.id in broadcast_target:
                del broadcast_target[message.from_user.id]

            logger.info(f"📊 Broadcast completed - Success: {success_count}, Failed: {failed_count}")
            return
            
        # Track user ID
        if message.from_user:
            user_ids.add(message.from_user.id)
            logger.debug(f"👤 User {message.from_user.id} tracked in private message")
                
    except Exception as e:
        user_info = extract_user_info(message) if message else {"user_id": "unknown", "full_name": "unknown"}
        log_with_user_info("ERROR", f"❌ Private message handling error: {e}", user_info)

@dp.message(F.content_type.in_({'text', 'photo', 'video', 'document', 'audio', 'voice', 'video_note', 'sticker', 'animation'}))
async def handle_message(message: Message) -> None:
    try:
        user_info = extract_user_info(message)
        log_with_user_info("DEBUG", "📨 Message received", user_info)
        
        # Track user and group IDs
        if message.from_user:
            user_ids.add(message.from_user.id)
            logger.debug(f"👤 User {message.from_user.id} added to tracking")
        
        if message.chat.type in ['group', 'supergroup']:
            group_ids.add(message.chat.id)
            add_message(message.chat.id, message)
            active_chats.add(message.chat.id)
            logger.debug(f"📢 Group {message.chat.id} message cached")
        elif message.chat.type == 'private':
            logger.debug("💌 Private message - skipping cache")
            return
        
        # Periodic cleanup trigger
        total_cached = sum(len(chat_msgs) for chat_msgs in messages.values())
        if total_cached % 100 == 0 and total_cached > 0:
            logger.info(f"🧹 Triggering cleanup - Total cached messages: {total_cached}")
            cleanup_expired()
                
    except Exception as e:
        user_info = extract_user_info(message) if message else {"user_id": "unknown", "full_name": "unknown"}
        log_with_user_info("ERROR", f"❌ Message handling error: {e}", user_info)

@dp.edited_message()
async def handle_edited_message(edited_message: Message) -> None:
    try:
        user_info = extract_user_info(edited_message)
        log_with_user_info("INFO", "📝 Edit detected", user_info)
        
        if edited_message.chat.type not in ['group', 'supergroup']:
            logger.debug("💌 Edit in private chat - ignoring")
            return
        
        chat_id = edited_message.chat.id
        message_id = edited_message.message_id
        
        # Get original message
        original_msg = get_message(chat_id, message_id)
        
        if not original_msg:
            logger.warning(f"⚠️ Original message {message_id} not found in cache - adding current version")
            add_message(chat_id, edited_message)
            return
        
        user = edited_message.from_user
        if not user:
            logger.warning("⚠️ Edit message has no user information")
            return
            
        # Create user mention
        full_name = user.first_name or ""
        if user.last_name:
            full_name += f" {user.last_name}"
        if not full_name:
            full_name = user.username if user.username else "Unknown User"
            
        user_mention = f'<a href="tg://user?id={user.id}">{full_name}</a>'
        
        # Prepare edit notification
        original_text = original_msg.get('text', '')[:400]
        new_text = (edited_message.text or edited_message.caption or '')[:400]
        
        if original_text == new_text:
            logger.debug("📝 Edit detected but text is identical - ignoring")
            return
        
        logger.info(f"📝 Processing edit by {user.full_name} ({user.id}) - Message {message_id}")
        
        # HTML escape function
        def escape_html(text):
            if not text:
                return "(No text)"
            return text.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
        
        original_escaped = escape_html(original_text)
        new_escaped = escape_html(new_text)
        
        edit_notification = f"📝 <b>Message Edited</b> by <b>{user_mention}</b>"
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="👀️", callback_data=f"reveal_edit:{message_id}:{user.id}"),
                InlineKeyboardButton(text="🗑️", callback_data=f"dismiss_edit:{message_id}")
            ]
        ])
        
        # Store edit data for reveal
        edit_data_key = f"edit_{chat_id}_{message_id}"
        edit_data_cache[edit_data_key] = {
            'original': original_escaped,
            'new': new_escaped,
            'editor_id': user.id,
            'editor_mention': user_mention
        }
        
        logger.debug(f"💾 Edit data cached with key: {edit_data_key}")
        
        # Update cache
        add_message(chat_id, edited_message)
        
        # Send notification
        try:
            await bot.send_message(
                chat_id=chat_id,
                text=edit_notification,
                parse_mode="HTML",
                reply_markup=keyboard,
                reply_to_message_id=message_id
            )
            logger.info(f"✅ Edit notification sent for message {message_id}")
        except Exception as send_error:
            logger.warning(f"⚠️ Failed to reply to original message {message_id}: {send_error}")
            try:
                await bot.send_message(
                    chat_id=chat_id,
                    text=edit_notification,
                    parse_mode="HTML",
                    reply_markup=keyboard
                )
                logger.info(f"✅ Edit notification sent without reply for message {message_id}")
            except Exception as fallback_error:
                logger.error(f"❌ Failed to send edit notification: {fallback_error}")
                
    except Exception as e:
        user_info = extract_user_info(edited_message) if edited_message else {"user_id": "unknown", "full_name": "unknown"}
        log_with_user_info("ERROR", f"❌ Edit handling error: {e}", user_info)

@dp.message(F.content_type == 'new_chat_members')
async def handle_new_members(message: Message) -> None:
    try:
        user_info = extract_user_info(message)
        log_with_user_info("INFO", "👥 New members detected", user_info)
        
        if message.chat.type not in ['group', 'supergroup']:
            logger.debug("💌 New member event in private chat - ignoring")
            return
        
        bot_info = await bot.get_me()
        for new_member in message.new_chat_members:
            logger.info(f"👤 New member: {new_member.full_name} ({new_member.id})")
            if new_member.id == bot_info.id:
                logger.info(f"🤖 Bot added to group {message.chat.id} ({message.chat.title})")
                await message.reply(GROUP_WELCOME_MSG, parse_mode="Markdown")
                active_chats.add(message.chat.id)
                logger.info(f"✅ Welcome message sent and chat {message.chat.id} marked as active")
                break
                
    except Exception as e:
        user_info = extract_user_info(message) if message else {"user_id": "unknown", "full_name": "unknown"}
        log_with_user_info("ERROR", f"❌ New members handling error: {e}", user_info)

@dp.callback_query()
async def handle_callback_query(callback_query: types.CallbackQuery) -> None:
    try:
        user_info = {
            "user_id": callback_query.from_user.id,
            "username": callback_query.from_user.username,
            "full_name": callback_query.from_user.full_name,
            "chat_id": callback_query.message.chat.id if callback_query.message else None,
            "chat_type": callback_query.message.chat.type if callback_query.message else None,
            "chat_title": callback_query.message.chat.title if callback_query.message else "Unknown",
            "chat_username": f"@{callback_query.message.chat.username}" if callback_query.message and callback_query.message.chat.username else "No Username",
            "chat_link": f"https://t.me/{callback_query.message.chat.username}" if callback_query.message and callback_query.message.chat.username else "No Link",
        }
        
        log_with_user_info("INFO", f"🔘 Callback query received: {callback_query.data}", user_info)
        
        # Handle help expand/minimize
        if callback_query.data == "help_expand":
            await handle_help_expand(callback_query)
        elif callback_query.data == "help_minimize":
            await handle_help_minimize(callback_query)
        elif callback_query.data.startswith("reveal_edit:"):
            await handle_reveal_edit(callback_query)
        elif callback_query.data.startswith("dismiss_edit:"):
            await handle_dismiss_edit(callback_query)
        elif callback_query.data in ["broadcast_users", "broadcast_groups"]:
            await handle_broadcast_target(callback_query)
        else:
            logger.warning(f"⚠️ Unknown callback data: {callback_query.data}")
            await callback_query.answer()
            
    except Exception as e:
        user_info = {"user_id": callback_query.from_user.id if callback_query.from_user else "unknown", "full_name": "unknown"}
        log_with_user_info("ERROR", f"❌ Callback query error: {e}", user_info)
        try:
            await callback_query.answer("🌷 Oops! Things didn't go as planned!", show_alert=True)
        except Exception as answer_error:
            logger.error(f"❌ Failed to answer callback query: {answer_error}")

async def handle_help_expand(callback_query: types.CallbackQuery) -> None:
    try:
        logger.info(f"📖 Help expand requested by {callback_query.from_user.full_name} ({callback_query.from_user.id})")
        
        if callback_query.from_user:
            user_mention = f'<a href="tg://user?id={callback_query.from_user.id}">{callback_query.from_user.full_name}</a>'
            help_text = HELP_MSG_EXPANDED.format(user_mention=user_mention)
        else:
            help_text = HELP_MSG_EXPANDED.format(user_mention="you!")
        
        builder = InlineKeyboardBuilder()
        builder.row(
            InlineKeyboardButton(text="📖 Minimize Guide", callback_data="help_minimize")
        )
        
        await callback_query.answer()
        if callback_query.message:
            await callback_query.message.edit_caption(
                caption=help_text,
                reply_markup=builder.as_markup(),
                parse_mode="HTML"
            )
            logger.info(f"✅ Help expanded for user {callback_query.from_user.id}")
            
    except Exception as e:
        logger.error(f"❌ Help expand error for user {callback_query.from_user.id if callback_query.from_user else 'unknown'}: {e}")
        try:
            await callback_query.answer("🌷 Uh oh! Help expansion exploded on me! 💥", show_alert=True)
        except Exception as answer_error:
            logger.error(f"❌ Failed to send help expand error: {answer_error}")

async def handle_help_minimize(callback_query: types.CallbackQuery) -> None:
    try:
        logger.info(f"📖 Help minimize requested by {callback_query.from_user.full_name} ({callback_query.from_user.id})")
        
        if callback_query.from_user:
            user_mention = f'<a href="tg://user?id={callback_query.from_user.id}">{callback_query.from_user.full_name}</a>'
            help_text = HELP_MSG_BASIC.format(user_mention=user_mention)
        else:
            help_text = HELP_MSG_BASIC.format(user_mention="there cutie")
        
        builder = InlineKeyboardBuilder()
        builder.row(
            InlineKeyboardButton(text="📖 Expand Guide", callback_data="help_expand")
        )
        
        await callback_query.answer()
        if callback_query.message:
            await callback_query.message.edit_caption(
                caption=help_text,
                reply_markup=builder.as_markup(),
                parse_mode="HTML"
            )
            logger.info(f"✅ Help minimized for user {callback_query.from_user.id}")
            
    except Exception as e:
        logger.error(f"❌ Help minimize error for user {callback_query.from_user.id if callback_query.from_user else 'unknown'}: {e}")
        try:
            await callback_query.answer("🌷 Uh oh! Help minimizer just melted down!", show_alert=True)
        except Exception as answer_error:
            logger.error(f"❌ Failed to send help minimize error: {answer_error}")

async def handle_reveal_edit(callback_query: types.CallbackQuery) -> None:
    try:
        logger.info(f"👀 Edit reveal/hide requested by {callback_query.from_user.full_name} ({callback_query.from_user.id})")
        
        parts = callback_query.data.split(":")
        if len(parts) >= 3:
            message_id = parts[1]
            editor_id = int(parts[2])
            
            # Prevent editor from using buttons
            if callback_query.from_user.id == editor_id:
                logger.warning(f"⚠️ Editor {editor_id} tried to reveal their own edit")
                await callback_query.answer("🌷 Nice try, sweetie! No spying on your mess!", show_alert=True)
                return
            
            chat_id = callback_query.message.chat.id
            edit_data_key = f"edit_{chat_id}_{message_id}"
            
            if edit_data_key in edit_data_cache:
                edit_data = edit_data_cache[edit_data_key]
                
                current_text = callback_query.message.text
                is_revealed = "From:" in current_text and "To:" in current_text
                
                if is_revealed:
                    new_text = f"📝 <b>Message Edited</b> by {edit_data['editor_mention']}"
                    new_button_text = "👀️"
                    action = "hidden"
                else:
                    new_text = (
                        f"📝 <b>Message Edited</b> by {edit_data['editor_mention']}\n\n"
                        f"<b>From:</b> {edit_data['original']}\n\n"
                        f"<b>To:</b> {edit_data['new']}"
                    )
                    new_button_text = "✉️"
                    action = "revealed"
                
                keyboard = InlineKeyboardMarkup(inline_keyboard=[
                    [
                        InlineKeyboardButton(text=new_button_text, callback_data=f"reveal_edit:{message_id}:{editor_id}"),
                        InlineKeyboardButton(text="🗑️", callback_data=f"dismiss_edit:{message_id}")
                    ]
                ])
                
                await callback_query.message.edit_text(
                    new_text,
                    parse_mode="HTML",
                    reply_markup=keyboard
                )
                
                await callback_query.answer(f"✨ Yay! Details {action} just perfectly 💕")
                logger.info(f"✅ Edit details {action} for message {message_id} by user {callback_query.from_user.id}")
            else:
                logger.warning(f"⚠️ Edit data not found for key: {edit_data_key}")
                await callback_query.answer("🌷 Hmm, that edit data poofed away, sweetie!", show_alert=True)
                
    except Exception as e:
        logger.error(f"❌ Reveal edit error for user {callback_query.from_user.id if callback_query.from_user else 'unknown'}: {e}")
        try:
            await callback_query.answer("🌷 Oops! Reveal button got confused!", show_alert=True)
        except Exception as answer_error:
            logger.error(f"❌ Failed to send reveal edit error: {answer_error}")

async def handle_dismiss_edit(callback_query: types.CallbackQuery) -> None:
    try:
        logger.info(f"🗑️ Edit dismiss requested by {callback_query.from_user.full_name} ({callback_query.from_user.id})")
        
        parts = callback_query.data.split(":")
        if len(parts) >= 2:
            message_id = parts[1]
            chat_id = callback_query.message.chat.id
            edit_data_key = f"edit_{chat_id}_{message_id}"
            
            # Check if editor is trying to dismiss
            if edit_data_key in edit_data_cache:
                edit_data = edit_data_cache[edit_data_key]
                editor_id = edit_data.get('editor_id')
                
                if callback_query.from_user.id == editor_id:
                    logger.warning(f"⚠️ Editor {editor_id} tried to dismiss their own edit")
                    await callback_query.answer("🌷 Trying to hide that mess? Not today, sweetie! 🌸", show_alert=True)
                    return
            
            # Check admin status
            try:
                chat_member = await bot.get_chat_member(chat_id, callback_query.from_user.id)
                is_admin = chat_member.status in ['administrator', 'creator']
                logger.debug(f"👤 User {callback_query.from_user.id} admin status: {is_admin} ({chat_member.status})")
                
                if not is_admin:
                    logger.warning(f"⚠️ Non-admin {callback_query.from_user.id} tried to dismiss edit")
                    await callback_query.answer("🌷 Wait up, sweetie! Only admins handle this mess! 🌸", show_alert=True)
                    return
            except Exception as admin_check_error:
                logger.error(f"❌ Admin check error for user {callback_query.from_user.id}: {admin_check_error}")
                await callback_query.answer("🧚‍♀️ Oops! My circuits fluttered away. Try again, darling!", show_alert=True)
                return
            
            # Allow dismiss for admins
            await callback_query.message.delete()
            await callback_query.answer("🌷 Poof! Edit floated away, babe!")
            logger.info(f"✅ Edit notification dismissed by admin {callback_query.from_user.id}")
            
            # Clean up cached data
            if edit_data_key in edit_data_cache:
                del edit_data_cache[edit_data_key]
                logger.debug(f"🧹 Edit data cache cleaned for key: {edit_data_key}")
                
    except Exception as e:
        logger.error(f"❌ Dismiss edit error for user {callback_query.from_user.id if callback_query.from_user else 'unknown'}: {e}")
        try:
            await callback_query.answer("🌷 Oops! Dismiss button malfunctioned!", show_alert=True)
        except Exception as answer_error:
            logger.error(f"❌ Failed to send dismiss edit error: {answer_error}")

async def handle_broadcast_target(callback_query: types.CallbackQuery) -> None:
    try:
        logger.info(f"📡 Broadcast target selection by {callback_query.from_user.full_name} ({callback_query.from_user.id})")
        
        if not callback_query.from_user or callback_query.from_user.id != OWNER_ID:
            logger.warning(f"⚠️ Unauthorized broadcast target selection by {callback_query.from_user.id if callback_query.from_user else 'unknown'}")
            await callback_query.answer("🌷 Not for you, sweetie, sorry!", show_alert=True)
            return
        
        target = "users" if callback_query.data == "broadcast_users" else "groups"
        target_list = user_ids if target == "users" else group_ids
        
        # Enable broadcast mode
        broadcast_mode.add(callback_query.from_user.id)
        broadcast_target[callback_query.from_user.id] = target
        
        logger.info(f"📡 Broadcast mode activated for owner - Target: {target}, Count: {len(target_list)}")
        
        await callback_query.answer(f"🌷 Broadcast's live! Time to stir the pot, {target}! 💥📡")
        
        if callback_query.message:
            await callback_query.message.edit_text(
                f"📣 <b>Broadcast Mode Activated</b>\n\n"
                f"🎯 <b>Target:</b> {target.title()} ({len(target_list)} total)\n\n"
                f"📝 <b>Instructions:</b>\n"
                f"• Send your message in this chat\n"
                f"• It will be broadcast to all {target}\n"
                f"• Use /start to cancel broadcast mode\n\n"
                f"⚡ Ready to broadcast your next message!",
                parse_mode="HTML"
            )
            logger.info("✅ Broadcast mode interface updated")
        
    except Exception as e:
        logger.error(f"❌ Broadcast target selection error for user {callback_query.from_user.id if callback_query.from_user else 'unknown'}: {e}")
        try:
            await callback_query.answer("🌷 Oops! Broadcast selector broke!", show_alert=True)
        except Exception as answer_error:
            logger.error(f"❌ Failed to send broadcast target error: {answer_error}")

async def set_bot_commands() -> None:
    try:
        logger.info("⚙️ Setting bot commands menu")
        
        commands = [
            BotCommand(command=cmd, description=desc)
            for cmd, desc in BOT_COMMANDS
        ]
        
        await bot.set_my_commands(commands)
        logger.info(f"✅ Bot commands set successfully - {len(commands)} commands")
        
    except Exception as e:
        logger.error(f"❌ Failed to set bot commands: {e}")

async def periodic_cleanup() -> None:
    logger.info("🧹 Starting periodic cleanup task")
    
    while True:
        try:
            await asyncio.sleep(CLEANUP_INTERVAL)
            logger.debug("🧹 Running periodic cleanup")
            cleanup_expired()
            
            # Log stats every hour
            total_messages = sum(len(msgs) for msgs in messages.values())
            total_users = len(user_ids)
            total_groups = len(group_ids)
            
            logger.info(
                f"📊 Stats - Active chats: {len(active_chats)}, "
                f"Cached messages: {total_messages}, "
                f"Users: {total_users}, "
                f"Groups: {total_groups}"
            )
            
        except Exception as e:
            logger.error(f"❌ Periodic cleanup error: {e}")
            await asyncio.sleep(60)

async def check_deleted_messages() -> None:
    logger.info("🔍 Starting deleted message checker task")
    
    while True:
        try:
            await asyncio.sleep(60)
            logger.debug("🔍 Checking for deleted messages")
            
            for chat_id in list(active_chats):
                try:
                    current_time = time.time()
                    chat_messages = messages.get(chat_id, {})
                    
                    # Remove old messages from tracking
                    expired_ids = []
                    for msg_id, msg_data in chat_messages.items():
                        if current_time - msg_data['timestamp'] > 7200:  # 2 hours
                            expired_ids.append(msg_id)
                    
                    if expired_ids:
                        logger.debug(f"🧹 Removing {len(expired_ids)} old tracked messages from chat {chat_id}")
                        for msg_id in expired_ids:
                            recent_message_ids[chat_id].discard(msg_id)
                        
                except Exception as chat_error:
                    logger.error(f"❌ Message tracking error for chat {chat_id}: {chat_error}")
                    continue
                    
        except Exception as e:
            logger.error(f"❌ Deletion check error: {e}")
            await asyncio.sleep(300)

async def start_bot_polling() -> None:
    try:
        logger.info("🚀 Starting Sus Ninja Bot polling...")
        bot_info = await bot.get_me()
        logger.info(f"✅ Bot @{bot_info.username} (ID: {bot_info.id}) is running successfully!")
        
        await set_bot_commands()
        logger.info("🎯 Starting polling loop...")
        await dp.start_polling(bot, skip_updates=True)
        
    except Exception as e:
        logger.error(f"❌ Bot polling start error: {e}")
        raise

async def main():
    global bot
    logger.info("🚀 Starting main bot execution")
    
    if not BOT_TOKEN or BOT_TOKEN == "YOUR_BOT_TOKEN_HERE":
        logger.error("❌ BOT_TOKEN not configured - Please set your bot token!")
        return
    
    logger.info("✅ Bot token validation passed")
    
    try:
        # Start HTTP server thread
        logger.info("🌐 Starting HTTP server thread")
        threading.Thread(target=start_dummy_server, daemon=True).start()
        logger.info("✅ HTTP server thread started successfully")
        
        # Initialize bot (dp is already initialized at module level)
        logger.info("🔧 Initializing bot")
        bot = Bot(token=BOT_TOKEN)
        
        # Start background tasks
        logger.info("🔄 Starting background tasks")
        asyncio.create_task(periodic_cleanup())
        asyncio.create_task(check_deleted_messages())
        logger.info("✅ Background tasks started")
        
        logger.info("🎯 Starting bot polling...")
        await start_bot_polling()
        
    except KeyboardInterrupt:
        logger.info("🛑 Bot stopped by user (Ctrl+C)")
    except Exception as e:
        logger.error(f"💥 Bot crashed with critical error: {e}")
        raise

if __name__ == "__main__":
    logger.info("🎬 Bot script started")
    
    try:
        logger.info("⚙️ Configuring asyncio event loop")
        
        # Configure asyncio for performance
        if hasattr(asyncio, 'set_event_loop_policy'):
            if os.name == 'nt':
                logger.info("🖥️ Windows detected - using ProactorEventLoopPolicy")
                asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
            else:
                logger.info("🐧 Unix/Linux detected - applying performance optimizations")
                try:
                    
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    
                    executor = concurrent.futures.ThreadPoolExecutor(max_workers=4)
                    loop.set_default_executor(executor)
                    loop.set_debug(False)
                    
                    logger.info("✅ Asyncio optimizations enabled successfully")
                except Exception as optimization_error:
                    logger.warning(f"⚠️ Using default asyncio policy due to error: {optimization_error}")
        
        logger.info("🚀 Launching main bot function")
        asyncio.run(main())
        
    except KeyboardInterrupt:
        logger.info("✅ Bot shutdown completed gracefully")
    except Exception as critical_error:
        logger.error(f"💀 Critical system error: {critical_error}")
        raise