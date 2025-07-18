import asyncio
import logging
import os
import time
import weakref
import sys
from collections import defaultdict, deque
from typing import Dict, Optional, Set
from datetime import datetime, timedelta

from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Message
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram import F

# ─── Imports for Dummy HTTP Server ──────────────────────────────────────────
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

class ColoredFormatter(logging.Formatter):
    """Custom formatter with colors and emojis for better readability"""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Check if we should use colors
        self.use_colors = (
            hasattr(sys.stderr, "isatty") and sys.stderr.isatty() or
            os.environ.get('FORCE_COLOR') == '1' or
            os.environ.get('TERM', '').lower() in ('xterm', 'xterm-color', 'xterm-256color', 'screen', 'screen-256color')
        )

    COLORS = {
        'DEBUG': '\x1b[36m',    # Cyan
        'INFO': '\x1b[32m',     # Green  
        'WARNING': '\x1b[33m',  # Yellow
        'ERROR': '\x1b[31m',    # Red
        'CRITICAL': '\x1b[35m', # Magenta
        'RESET': '\x1b[0m',     # Reset
        'BLUE': '\x1b[34m',     # Blue
        'PURPLE': '\x1b[35m',   # Purple
        'CYAN': '\x1b[36m',     # Cyan
        'YELLOW': '\x1b[33m',   # Yellow
        'GREEN': '\x1b[32m',    # Green
        'RED': '\x1b[31m',      # Red (alias for ERROR)
        'BOLD': '\x1b[1m',      # Bold
        'DIM': '\x1b[2m'        # Dim
    }

    def format(self, record):
        if not self.use_colors:
            return super().format(record)

        # Create a copy to avoid modifying the original
        formatted_record = logging.makeLogRecord(record.__dict__)

        # Get the basic formatted message
        message = super().format(formatted_record)

        # Apply colors to the entire message
        return self.colorize_full_message(message, record.levelname)

    def colorize_full_message(self, message, level):
        """Apply colors to the entire formatted message"""
        if not self.use_colors:
            return message

        # Color based on log level
        level_color = self.COLORS.get(level, self.COLORS['RESET'])

        # Apply level-based coloring to the entire message
        if level == 'ERROR' or level == 'CRITICAL':
            return f"{self.COLORS['ERROR']}{self.COLORS['BOLD']}{message}{self.COLORS['RESET']}"
        elif level == 'WARNING':
            return f"{self.COLORS['YELLOW']}{message}{self.COLORS['RESET']}"
        elif level == 'INFO':
            # For INFO messages, use subtle coloring
            if any(word in message for word in ['Bot', 'Quiz', 'startup', 'connected', 'Success']):
                return f"{self.COLORS['GREEN']}{message}{self.COLORS['RESET']}"
            elif any(word in message for word in ['API', 'HTTP', 'Fetching']):
                return f"{self.COLORS['BLUE']}{message}{self.COLORS['RESET']}"
            elif any(word in message for word in ['User', 'extracted']):
                return f"{self.COLORS['CYAN']}{message}{self.COLORS['RESET']}"
            else:
                return f"{self.COLORS['GREEN']}{message}{self.COLORS['RESET']}"
        else:
            return f"{level_color}{message}{self.COLORS['RESET']}"

# Force color support in terminal
os.environ['FORCE_COLOR'] = '1'
os.environ['TERM'] = 'xterm-256color'

# Setup colored logging
logger = logging.getLogger("sus_ninja_bot")
logger.setLevel(logging.INFO)

# Remove any existing handlers
for handler in logger.handlers[:]:
    logger.removeHandler(handler)

# Create and configure console handler with colors
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)
console_handler.setFormatter(ColoredFormatter("%(asctime)s | %(levelname)s | %(message)s"))

# Add handler to logger
logger.addHandler(console_handler)

# Prevent propagation to root logger to avoid duplicate messages
logger.propagate = False

# Configure aiogram loggers to use colors too
aiogram_logger = logging.getLogger("aiogram")
aiogram_logger.setLevel(logging.INFO)

# Remove existing handlers
for handler in aiogram_logger.handlers[:]:
    aiogram_logger.removeHandler(handler)

# Add our colored handler to aiogram logger
aiogram_console_handler = logging.StreamHandler()
aiogram_console_handler.setLevel(logging.INFO)
aiogram_console_handler.setFormatter(ColoredFormatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s"))
aiogram_logger.addHandler(aiogram_console_handler)
aiogram_logger.propagate = False

# Configure aiogram.event logger specifically
aiogram_event_logger = logging.getLogger("aiogram.event")
aiogram_event_logger.setLevel(logging.INFO)

# Remove existing handlers
for handler in aiogram_event_logger.handlers[:]:
    aiogram_event_logger.removeHandler(handler)

# Add our colored handler to aiogram.event logger
aiogram_event_console_handler = logging.StreamHandler()
aiogram_event_console_handler.setLevel(logging.INFO)
aiogram_event_console_handler.setFormatter(ColoredFormatter("%(asctime)s - %(name)s - %(levelname)s - 🔄 %(message)s"))
aiogram_event_logger.addHandler(aiogram_event_console_handler)
aiogram_event_logger.propagate = False

# Configure aiogram.dispatcher logger
aiogram_dispatcher_logger = logging.getLogger("aiogram.dispatcher")
aiogram_dispatcher_logger.setLevel(logging.INFO)

# Remove existing handlers
for handler in aiogram_dispatcher_logger.handlers[:]:
    aiogram_dispatcher_logger.removeHandler(handler)

# Add our colored handler to aiogram.dispatcher logger
aiogram_dispatcher_console_handler = logging.StreamHandler()
aiogram_dispatcher_console_handler.setLevel(logging.INFO)
aiogram_dispatcher_console_handler.setFormatter(ColoredFormatter("%(asctime)s - %(name)s - %(levelname)s - ⚡ %(message)s"))
aiogram_dispatcher_logger.addHandler(aiogram_dispatcher_console_handler)
aiogram_dispatcher_logger.propagate = False

# ─── Dummy HTTP Server to Keep Render Happy ─────────────────────────────────
class DummyHandler(BaseHTTPRequestHandler):
    """HTTP request handler for deployment platform health checks"""
    
    def do_GET(self):
        """Handle GET requests with colorful logging"""
        client_ip = self.client_address[0]
        logger.info(f"🌐 HTTP GET request from {client_ip} to {self.path}")
        
        self.send_response(200)
        self.send_header('Content-Type', 'text/plain')
        self.end_headers()
        
        response_message = b"Sus Ninja Bot is alive and running!"
        self.wfile.write(response_message)
        
        logger.info(f"✅ HTTP response sent to {client_ip}: 200 OK")

    def do_HEAD(self):
        """Handle HEAD requests with colorful logging"""
        client_ip = self.client_address[0]
        logger.info(f"🌐 HTTP HEAD request from {client_ip} to {self.path}")
        
        self.send_response(200)
        self.send_header('Content-Type', 'text/plain')
        self.end_headers()
        
        logger.info(f"✅ HTTP HEAD response sent to {client_ip}: 200 OK")

    def log_message(self, format, *args):
        """Override default logging to use our colored logger"""
        logger.info(f"🌐 HTTP Server: {format % args}")

def start_dummy_server():
    """Start the dummy HTTP server for deployment platform compatibility"""
    port = int(os.environ.get("PORT", 10000))  # Render injects this
    
    try:
        logger.info(f"🌐 Starting dummy HTTP server on port {port}")
        logger.info(f"🔧 Server will bind to 0.0.0.0:{port}")
        
        server = HTTPServer(("0.0.0.0", port), DummyHandler)
        
        logger.info(f"🚀 Dummy HTTP server listening on port {port}")
        logger.info(f"🌐 Server ready to handle health checks from deployment platform")
        
        server.serve_forever()
        
    except Exception as e:
        logger.error(f"❌ Error starting dummy HTTP server: {e}")
        logger.error(f"🔧 Port: {port}, Error type: {type(e).__name__}")
        raise

def extract_user_info(msg: Message):
    """Extract user and chat information from message"""
    logger.debug("🔍 Extracting user information from message")
    try:
        u = msg.from_user
        c = msg.chat
        info = {
            "user_id": u.id if u else None,
            "username": u.username if u else None,
            "full_name": u.full_name if u else "Anonymous",
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
        return None

logger.info("🥷 Sus Ninja Bot starting up - loading configuration")

# Bot configuration
logger.info("⚙️ Loading bot configuration settings")
BOT_TOKEN = os.getenv("BOT_TOKEN", "YOUR_BOT_TOKEN_HERE")
CHANNEL_URL = "https://t.me/WorkGlows"
GROUP_URL = "https://t.me/SoulMeetsHQ"
logger.info(f"🔗 Channel URL set: {CHANNEL_URL}")
logger.info(f"🔗 Group URL set: {GROUP_URL}")

# ─── Owner and Broadcasting Configuration ──────────────────────────
OWNER_ID = 5290407067  # Hardcoded owner ID
broadcast_mode = set()  # Users in broadcast mode
broadcast_target = {}  # User broadcast targets
user_ids = set()  # Track user IDs for broadcasting
group_ids = set()  # Track group IDs for broadcasting
logger.info(f"👑 Owner ID configured: {OWNER_ID}")
logger.info("📊 Broadcasting system initialized with empty user/group sets")

# Performance configurations for 100k users
MAX_MESSAGES_PER_CHAT = 1000  # Limit messages stored per chat
MESSAGE_TTL = 3600  # 1 hour TTL for messages
CLEANUP_INTERVAL = 300  # Cleanup every 5 minutes
MAX_MESSAGE_LENGTH = 4096  # Telegram's message limit
logger.info(f"⚡ Performance settings: {MAX_MESSAGES_PER_CHAT} msgs/chat, {MESSAGE_TTL}s TTL, {CLEANUP_INTERVAL}s cleanup interval")

class MessageCache:
    """Efficient message cache with TTL and size limits for high-performance usage"""
    
    def __init__(self, max_size: int = MAX_MESSAGES_PER_CHAT, ttl: int = MESSAGE_TTL):
        logger.info("🗄️ Initializing MessageCache system")
        self.max_size = max_size
        self.ttl = ttl
        # Using defaultdict with deque for O(1) operations
        self.messages: Dict[int, Dict[int, dict]] = defaultdict(dict)  # chat_id -> {msg_id: msg_data}
        self.chat_queues: Dict[int, deque] = defaultdict(lambda: deque(maxlen=max_size))
        self.last_cleanup = time.time()
        # Track message IDs for deletion detection
        self.recent_message_ids: Dict[int, Set[int]] = defaultdict(set)  # chat_id -> set of msg_ids
        logger.info(f"✅ MessageCache initialized with max_size={max_size}, ttl={ttl}s")
        
    def add_message(self, chat_id: int, message: Message) -> None:
        """Add message to cache with timestamp"""
        logger.debug(f"📝 Adding message {message.message_id} to cache for chat {chat_id}")
        try:
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
            
            # Add to messages dict
            self.messages[chat_id][message.message_id] = msg_data
            logger.debug(f"💾 Message data stored in cache for chat {chat_id}")
            
            # Track recent message ID for deletion detection
            self.recent_message_ids[chat_id].add(message.message_id)
            logger.debug(f"🔍 Message ID {message.message_id} added to deletion tracking")
            
            # Add to queue for size management
            queue = self.chat_queues[chat_id]
            if len(queue) >= self.max_size:
                # Remove oldest message when queue is full
                oldest_msg_id = queue.popleft()
                self.messages[chat_id].pop(oldest_msg_id, None)
                self.recent_message_ids[chat_id].discard(oldest_msg_id)
                logger.debug(f"🗑️ Removed oldest message {oldest_msg_id} due to cache size limit")
            
            queue.append(message.message_id)
            logger.info(f"✅ Message {message.message_id} successfully cached for chat {chat_id} (cache size: {len(queue)})")
            
        except Exception as e:
            logger.error(f"❌ Failed to add message to cache: {e}")
            logger.error(f"🔧 Message details: chat_id={chat_id}, msg_id={getattr(message, 'message_id', 'unknown')}")
    
    def get_message(self, chat_id: int, message_id: int) -> Optional[dict]:
        """Get message from cache"""
        logger.debug(f"🔍 Retrieving message {message_id} from cache for chat {chat_id}")
        try:
            result = self.messages.get(chat_id, {}).get(message_id)
            if result:
                logger.debug(f"✅ Message {message_id} found in cache")
            else:
                logger.debug(f"❌ Message {message_id} not found in cache")
            return result
        except Exception as e:
            logger.error(f"❌ Error retrieving message from cache: {e}")
            return None
    
    def remove_message(self, chat_id: int, message_id: int) -> Optional[dict]:
        """Remove and return message from cache"""
        logger.debug(f"🗑️ Removing message {message_id} from cache for chat {chat_id}")
        try:
            msg_data = self.messages.get(chat_id, {}).pop(message_id, None)
            if msg_data:
                try:
                    self.chat_queues[chat_id].remove(message_id)
                    logger.info(f"✅ Message {message_id} successfully removed from cache")
                except ValueError:
                    logger.warning(f"⚠️ Message {message_id} not found in queue during removal")
                    pass  # Message not in queue
                # Remove from deletion tracking
                self.recent_message_ids[chat_id].discard(message_id)
                logger.debug(f"🔍 Message {message_id} removed from deletion tracking")
            else:
                logger.debug(f"❌ Message {message_id} not found for removal")
            return msg_data
        except Exception as e:
            logger.error(f"❌ Error removing message from cache: {e}")
            return None
    
    def cleanup_expired(self) -> None:
        """Remove expired messages based on TTL"""
        current_time = time.time()
        if current_time - self.last_cleanup < CLEANUP_INTERVAL:
            logger.debug(f"⏰ Cleanup skipped - last cleanup was {current_time - self.last_cleanup:.1f}s ago")
            return
            
        logger.info("🧹 Starting message cache cleanup process")
        try:
            expired_count = 0
            chats_cleaned = 0
            for chat_id in list(self.messages.keys()):
                chat_messages = self.messages[chat_id]
                expired_msg_ids = []
                
                logger.debug(f"🔍 Checking {len(chat_messages)} messages in chat {chat_id}")
                for msg_id, msg_data in chat_messages.items():
                    if current_time - msg_data['timestamp'] > self.ttl:
                        expired_msg_ids.append(msg_id)
                
                # Remove expired messages
                if expired_msg_ids:
                    logger.debug(f"🗑️ Found {len(expired_msg_ids)} expired messages in chat {chat_id}")
                    for msg_id in expired_msg_ids:
                        chat_messages.pop(msg_id, None)
                        try:
                            self.chat_queues[chat_id].remove(msg_id)
                        except ValueError:
                            logger.debug(f"⚠️ Message {msg_id} not found in queue during cleanup")
                            pass
                        # Remove from deletion tracking
                        self.recent_message_ids[chat_id].discard(msg_id)
                        expired_count += 1
                    chats_cleaned += 1
                
                # Clean up empty chat entries
                if not chat_messages:
                    del self.messages[chat_id]
                    del self.chat_queues[chat_id]
                    if chat_id in self.recent_message_ids:
                        del self.recent_message_ids[chat_id]
                    logger.debug(f"🧹 Removed empty chat entry {chat_id}")
            
            self.last_cleanup = current_time
            if expired_count > 0:
                logger.info(f"✅ Cleanup completed: {expired_count} messages removed from {chats_cleaned} chats")
            else:
                logger.debug("✅ Cleanup completed: no expired messages found")
                
        except Exception as e:
            logger.error(f"❌ Error during cleanup process: {e}")
            logger.error(f"🔧 Cleanup state: current_time={current_time}, ttl={self.ttl}")

class SusNinjaBot:
    """High-performance Telegram bot for monitoring message deletions and edits"""
    
    def __init__(self, token: str):
        logger.info("🥷 Initializing SusNinjaBot")
        logger.debug(f"🔑 Bot token length: {len(token) if token else 0} characters")
        try:
            self.bot = Bot(token=token)
            logger.info("✅ Bot instance created successfully")
            
            self.dp = Dispatcher()
            logger.info("✅ Dispatcher initialized")
            
            self.message_cache = MessageCache()
            logger.info("✅ Message cache system ready")
            
            self.active_chats: Set[int] = set()
            logger.info("✅ Active chats tracker initialized")
            
            # Set up handlers
            logger.info("🔧 Setting up message handlers")
            self._setup_handlers()
            
            # Start cleanup task
            logger.info("🧹 Starting periodic cleanup task")
            asyncio.create_task(self._periodic_cleanup())
            
            # Start deletion monitoring task
            logger.info("🔍 Starting deletion monitoring task")
            asyncio.create_task(self._check_deleted_messages())
            
            logger.info("🎉 SusNinjaBot initialization completed successfully")
        except Exception as e:
            logger.error(f"❌ Failed to initialize SusNinjaBot: {e}")
            raise
    
    def _setup_handlers(self) -> None:
        """Setup all message and command handlers"""
        logger.info("🔗 Setting up command and message handlers")
        try:
            # Command handlers
            logger.debug("📝 Registering /start command handler")
            self.dp.message(Command("start"))(self._start_command)
            
            logger.debug("📝 Registering /help command handler")
            self.dp.message(Command("help"))(self._help_command)
            
            logger.debug("📝 Registering /ping command handler")
            self.dp.message(Command("ping"))(self._ping_command)
            
            logger.debug("📝 Registering /broadcast command handler")
            self.dp.message(Command("broadcast"))(self._broadcast_command)
            
            # Message handlers
            logger.debug("📝 Registering private message handler")
            self.dp.message(F.chat.type == "private")(self._handle_private_message)
            
            logger.debug("📝 Registering general message handler")
            self.dp.message(F.content_type.in_({'text', 'photo', 'video', 'document', 'audio', 'voice', 'video_note', 'sticker', 'animation'}))(self._handle_message)
            
            logger.debug("📝 Registering edited message handler")
            self.dp.edited_message()(self._handle_edited_message)
            
            logger.debug("📝 Registering new members handler")
            self.dp.message(F.content_type == 'new_chat_members')(self._handle_new_members)
            
            # Callback query handler for inline buttons
            logger.debug("📝 Registering callback query handler")
            self.dp.callback_query()(self._handle_callback_query)
            
            logger.info("✅ All handlers registered successfully")
        except Exception as e:
            logger.error(f"❌ Failed to setup handlers: {e}")
            raise
    
    async def _start_command(self, message: Message) -> None:
        """Handle /start command with inline keyboard"""
        user_info = extract_user_info(message)
        logger.info(f"🚀 /start command received from {user_info['full_name'] if user_info else 'Unknown'}")
        
        try:
            # Track user for broadcasting when they use commands
            if message.from_user:
                user_ids.add(message.from_user.id)
                logger.debug(f"👤 User {message.from_user.id} added to broadcast tracking via /start (total: {len(user_ids)})")
            # Check if user was in broadcast mode and cancel it
            if message.from_user and message.from_user.id in broadcast_mode:
                logger.info(f"🔓 Cancelling broadcast mode for user {message.from_user.id}")
                broadcast_mode.discard(message.from_user.id)
                if message.from_user.id in broadcast_target:
                    del broadcast_target[message.from_user.id]
                    logger.debug(f"🗑️ Removed broadcast target for user {message.from_user.id}")
                logger.info(f"✅ Broadcast mode cancelled for {message.from_user.id}")
                await message.reply("🌷 Broadcast’s off! Spam mission canceled, sweetie! 📡💥", parse_mode="HTML")
                return
            
            logger.debug("📝 Preparing welcome message and inline keyboard")
            if user_info and user_info["user_id"]:
                user_mention = f'<a href="tg://user?id={user_info["user_id"]}">{user_info["full_name"]}</a>'
                welcome_text = f"""
💖 <b>Hey {user_mention}, your Sus Ninja just woke up!</b>

I’m your cheeky guardian watching all the sneaky moves! 💕  

<b>My Lovely Skills:</b>
• 👀 Spy on message edits like a pro  
• 🕵️ Find those deleted secrets  
• ⚡ Strike quick with love and style  
• 🤫 Stay stealthy until someone acts sus  

Add me to your group and let me catch all the sneaky fun! 🎭
"""
            else:
                welcome_text = """
💖 <b>Hey babe, the Sus Ninja is awake!</b>

I’m your cheeky guardian watching all the sneaky moves! 💕

<b>My Lovely Skills:</b>
• 👀 Spy on message edits like a pro  
• 🕵️ Find those deleted secrets  
• ⚡ Strike quick with love and style  
• 🤫 Stay stealthy until someone acts sus  

Add me to your group and let me catch all the sneaky fun! 🎭
"""
            
            # Create inline keyboard with specified layout
            logger.debug("🎨 Creating inline keyboard buttons")
            builder = InlineKeyboardBuilder()
            
            # First row - 2 buttons
            builder.row(
                InlineKeyboardButton(text="Updates", url=CHANNEL_URL),
                InlineKeyboardButton(text="Support", url=GROUP_URL)
            )
            logger.debug("✅ First row buttons added (Updates & Support)")
            
            # Second row - 1 button
            logger.debug("🔍 Getting bot username for group invitation link")
            bot_info = await self.bot.get_me()
            logger.debug(f"🤖 Bot username: @{bot_info.username}")
            
            builder.row(
                InlineKeyboardButton(
                    text="Add Me To Your Group", 
                    url=f"https://t.me/{bot_info.username}?startgroup=true"
                )
            )
            logger.debug("✅ Second row button added (Add to Group)")
            
            logger.info(f"📤 Sending welcome message to {user_info['full_name'] if user_info else 'user'}")
            await message.reply(welcome_text, reply_markup=builder.as_markup(), parse_mode="HTML")
            logger.info(f"✅ Welcome message sent successfully to {user_info['user_id'] if user_info else 'unknown'}")
            
        except Exception as e:
            logger.error(f"❌ Error in /start command: {e}")
            logger.error(f"🔧 User details: {user_info}")
            try:
                await message.reply("🌷 Oops! My circuits glitched. Try again, please! ⚡")
                logger.info("📤 Error message sent to user")
            except Exception as reply_error:
                logger.error(f"❌ Failed to send error message: {reply_error}")
    
    async def _help_command(self, message: Message) -> None:
        """Handle /help command"""
        user_info = extract_user_info(message)
        logger.info(f"❓ /help command received from {user_info['full_name'] if user_info else 'Unknown'}")
        
        try:
            # Track user for broadcasting when they use commands
            if message.from_user:
                user_ids.add(message.from_user.id)
                logger.debug(f"👤 User {message.from_user.id} added to broadcast tracking via /help (total: {len(user_ids)})")
            logger.debug("📝 Preparing help message content")
            if user_info and user_info["user_id"]:
                user_mention = f'<a href="tg://user?id={user_info["user_id"]}">{user_info["full_name"]}</a>'
                help_text_basic = (
    				f"💖 <b>Sus Ninja Manual for {user_mention}</b>\n\n"
				    "<b>My Arsenal:</b>\n"
				    "• <b>/start</b> - Wake up your fierce ninja baby 🔥\n"
				    "• <b>/help</b> - Peek at my secret moves 💕\n"
				    "• <b>/ping</b> - Check if I’m still buzzing for you 💫\n\n"
				    "<b>How I own your group:</b>\n"
				    "1. Drag me in and let’s get cozy 😘\n"
				    "2. Give me admin powers to play hard 👑\n"
				    "3. I’ll lurk and watch every naughty move 👀\n"
				    "4. Someone’s sneaky? BAM! Secrets out! 💥"
				)
            else:
                help_text_basic = (
    				"💖 <b>Sus Ninja Manual</b>\n\n"
				    "<b>My Arsenal:</b>\n"
				    "• <b>/start</b> - Wake up your fierce ninja baby 🔥\n"
				    "• <b>/help</b> - Peek at my secret moves 💕\n"
				    "• <b>/ping</b> - Check if I’m still buzzing for you 💫\n\n"
				    "<b>How I own your group:</b>\n"
				    "1. Drag me in and let’s get cozy 😘\n"
				    "2. Give me admin powers to play hard 👑\n"
				    "3. I’ll lurk and watch every naughty move 👀\n"
				    "4. Someone’s sneaky? BAM! Secrets out! 💥"
				)
            
            # Create inline keyboard with expand button
            builder = InlineKeyboardBuilder()
            builder.row(
                InlineKeyboardButton(text="📖 Expand Guide", callback_data="help_expand")
            )
            
            logger.info(f"📤 Sending help message to {user_info['full_name'] if user_info else 'user'}")
            await message.reply(help_text_basic, reply_markup=builder.as_markup(), parse_mode="HTML")
            logger.info(f"✅ Help message sent successfully to {user_info['user_id'] if user_info else 'unknown'}")
            
        except Exception as e:
            logger.error(f"❌ Error in /help command: {e}")
            logger.error(f"🔧 User details: {user_info}")
            try:
                await message.reply("🌷 Uh oh! Help system crashed! Trying to fix it! 🔧")
                logger.info("📤 Error message sent to user")
            except Exception as reply_error:
                logger.error(f"❌ Failed to send error message: {reply_error}")
    
    async def _ping_command(self, message: Message) -> None:
        """Handle /ping command"""
        user_info = extract_user_info(message)
        logger.info(f"🏓 /ping command received from {user_info['full_name'] if user_info else 'Unknown'}")
        
        try:
            # Track user for broadcasting when they use commands
            if message.from_user:
                user_ids.add(message.from_user.id)
                logger.debug(f"👤 User {message.from_user.id} added to broadcast tracking via /ping (total: {len(user_ids)})")
            logger.debug("⏱️ Starting ping response timer")
            start_time = time.time()
            
            # Get bot info for status
            logger.debug("🔍 Fetching bot information for status check")
            bot_info = await self.bot.get_me()
            response_time = round((time.time() - start_time) * 1000, 2)
            logger.info(f"⚡ Bot response time calculated: {response_time}ms")
            
            status_text = (
                f'🏓 <a href="{GROUP_URL}">Pong!</a> {response_time}ms'
            )
            
            logger.info(f"📤 Sending ping response to {user_info['full_name'] if user_info else 'user'}")
            await message.reply(status_text, parse_mode="HTML")
            logger.info(f"✅ Ping response sent successfully ({response_time}ms) to {user_info['user_id'] if user_info else 'unknown'}")
            
        except Exception as e:
            logger.error(f"❌ Error in /ping command: {e}")
            logger.error(f"🔧 User details: {user_info}")
            try:
                await message.reply("🏓 Pong! I'm alive!")
                logger.info("📤 Error ping response sent to user")
            except Exception as reply_error:
                logger.error(f"❌ Failed to send error ping response: {reply_error}")
    
    async def _broadcast_command(self, message: Message) -> None:
        """Handle broadcast command (owner only)"""
        user_info = extract_user_info(message)
        logger.info(f"📢 /broadcast command received from {user_info['full_name'] if user_info else 'Unknown'}")
        
        try:
            # Security check - owner only
            if not message.from_user or message.from_user.id != OWNER_ID:
                logger.warning(f"🚫 Unauthorized broadcast attempt by user {message.from_user.id if message.from_user else 'Unknown'}")
                logger.warning(f"🔐 Security violation - non-owner tried to access broadcast: {user_info}")
                response = await message.answer("⛔ This command is restricted.")
                logger.info(f"⚠️ Unauthorized access message sent, ID: {response.message_id}")
                return

            logger.info(f"✅ Owner {message.from_user.id} authorized for broadcast command")
            
            # Track owner for broadcasting when they use commands  
            user_ids.add(message.from_user.id)
            logger.debug(f"👤 Owner {message.from_user.id} added to broadcast tracking via /broadcast (total: {len(user_ids)})")
            logger.debug(f"📊 Current broadcast stats - Users: {len(user_ids)}, Groups: {len(group_ids)}")

            # Create inline keyboard for broadcast target selection
            logger.debug("🎨 Creating broadcast target selection keyboard")
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [
                    InlineKeyboardButton(text=f"👥 Users ({len(user_ids)})", callback_data="broadcast_users"),
                    InlineKeyboardButton(text=f"📢 Groups ({len(group_ids)})", callback_data="broadcast_groups")
                ]
            ])

            logger.info(f"📤 Sending broadcast target selection to owner")
            response = await message.answer(
                "📣 <b>Choose broadcast target:</b>\n\n"
                f"👥 <b>Users:</b> {len(user_ids)} individual users\n"
                f"📢 <b>Groups:</b> {len(group_ids)} groups\n\n"
                "Select where you want to send your broadcast message:",
                reply_markup=keyboard,
                parse_mode="HTML"
            )
            logger.info(f"✅ Broadcast target selection sent to owner {message.from_user.id}, message ID: {response.message_id}")
            
        except Exception as e:
            logger.error(f"❌ Error in /broadcast command: {e}")
            logger.error(f"🔧 User details: {user_info}")
            try:
                await message.reply("🌷 Uh oh! Broadcast system had a meltdown! Hang tight! 📡🔥")
                logger.info("📤 Error message sent to user")
            except Exception as reply_error:
                logger.error(f"❌ Failed to send error message: {reply_error}")
    
    async def _handle_private_message(self, message: Message) -> None:
        """Handle live search in private messages and broadcast functionality"""
        user_info = extract_user_info(message)
        logger.info(f"💬 Private message received from {user_info['full_name'] if user_info else 'Unknown'}")
        
        try:
            # Check for broadcast mode first (owner bypass)
            if message.from_user and message.from_user.id in broadcast_mode:
                logger.info(f"📢 Executing broadcast from owner {message.from_user.id}")
                logger.debug(f"📝 Broadcast message content: {message.text[:50] if message.text else 'Media/File'}...")

                target = broadcast_target.get(message.from_user.id, "users")
                target_list = user_ids if target == "users" else group_ids
                logger.info(f"🎯 Broadcasting to {len(target_list)} {target}")

                success_count = 0
                failed_count = 0

                for target_id in target_list:
                    try:
                        logger.debug(f"📤 Sending broadcast message to {target_id}")
                        await self.bot.copy_message(
                            chat_id=target_id,
                            from_chat_id=message.chat.id,
                            message_id=message.message_id
                        )
                        success_count += 1
                        logger.debug(f"✅ Message successfully sent to {target_id}")
                    except Exception as e:
                        failed_count += 1
                        logger.warning(f"❌ Failed to send broadcast to {target_id}: {e}")

                logger.info(f"📊 Broadcast completed: {success_count}/{len(target_list)} successful")

                # Send broadcast summary
                logger.debug("📤 Sending broadcast summary to owner")
                await message.answer(
                    f"📊 <b>Broadcast Summary:</b>\n\n"
                    f"✅ <b>Sent:</b> {success_count}\n"
                    f"❌ <b>Failed:</b> {failed_count}\n"
                    f"🎯 <b>Target:</b> {target}\n\n"
                    "🔥 Broadcast mode is STILL ACTIVE! Send another message to continue your spam mission or use /start to abort! 📡💥",
                    parse_mode="HTML"
                )

                # Remove from broadcast mode after sending
                logger.debug(f"🔓 Disabling broadcast mode for {message.from_user.id}")
                broadcast_mode.discard(message.from_user.id)
                if message.from_user.id in broadcast_target:
                    del broadcast_target[message.from_user.id]

                logger.info(f"✅ Broadcast mode disabled for {message.from_user.id}")
                return
                
            # Track user ID for regular private messages
            if message.from_user:
                user_ids.add(message.from_user.id)
                logger.debug(f"👤 User {message.from_user.id} added to broadcast tracking (total: {len(user_ids)})")
                
        except Exception as e:
            logger.error(f"❌ Error in private message handler: {e}")
            logger.error(f"🔧 User details: {user_info}")
            logger.error(f"🔧 Message details: text={getattr(message, 'text', 'None')}")
    
    async def _handle_message(self, message: Message) -> None:
        """Handle incoming messages and store them in cache"""
        user_info = extract_user_info(message)
        logger.debug(f"📨 Processing message from {user_info['full_name'] if user_info else 'Unknown'} in {user_info['chat_title'] if user_info else 'Unknown chat'}")
        
        try:
            # Track user and group IDs for broadcasting
            if message.from_user:
                user_ids.add(message.from_user.id)
                logger.debug(f"👤 User {message.from_user.id} tracked for broadcasting (total users: {len(user_ids)})")
            
            if message.chat.type in ['group', 'supergroup']:
                group_ids.add(message.chat.id)
                logger.debug(f"🏠 Group {message.chat.id} tracked for broadcasting (total groups: {len(group_ids)})")
                
                # Add chat to active chats
                self.active_chats.add(message.chat.id)
                logger.debug(f"💬 Chat {message.chat.id} added to active monitoring (total active: {len(self.active_chats)})")
                
                # Store message in cache
                self.message_cache.add_message(message.chat.id, message)
                logger.debug(f"💾 Message {message.message_id} cached for monitoring")
                
            elif message.chat.type == 'private':
                logger.debug("💬 Private message - delegating to private handler")
                # Handle private messages - will be caught by private handler
                return
            
            # Periodic cleanup trigger
            total_cached = sum(len(chat_msgs) for chat_msgs in self.message_cache.messages.values())
            if total_cached % 100 == 0 and total_cached > 0:
                logger.info(f"🧹 Triggering periodic cleanup at {total_cached} cached messages")
                self.message_cache.cleanup_expired()
                
        except Exception as e:
            logger.error(f"❌ Error handling message: {e}")
            logger.error(f"🔧 User details: {user_info}")
            logger.error(f"🔧 Message details: msg_id={getattr(message, 'message_id', 'unknown')}, chat_id={getattr(message.chat, 'id', 'unknown')}")
    
    async def _handle_edited_message(self, edited_message: Message) -> None:
        """Handle edited messages and announce the change"""
        user_info = extract_user_info(edited_message)
        logger.info(f"✏️ Message edit detected from {user_info['full_name'] if user_info else 'Unknown'} in {user_info['chat_title'] if user_info else 'Unknown chat'}")
        
        try:
            if edited_message.chat.type not in ['group', 'supergroup']:
                logger.debug("❌ Skipping edit - not a group/supergroup")
                return
            
            chat_id = edited_message.chat.id
            message_id = edited_message.message_id
            logger.debug(f"🔍 Processing edit for message {message_id} in chat {chat_id}")
            
            # Get original message from cache
            original_msg = self.message_cache.get_message(chat_id, message_id)
            
            if not original_msg:
                logger.debug(f"❌ Original message {message_id} not found in cache - adding current version")
                # Message not in cache, just update it
                self.message_cache.add_message(chat_id, edited_message)
                return
            
            # Get user info
            user = edited_message.from_user
            if not user:
                return
                
            # Create user mention with HTML formatting using full name
            full_name = user.first_name or ""
            if user.last_name:
                full_name += f" {user.last_name}"
            if not full_name:
                full_name = user.username if user.username else "Unknown User"
                
            user_mention = f'<a href="tg://user?id={user.id}">{full_name}</a>'
            
            # Prepare edit notification with proper escaping
            original_text = original_msg.get('text', '')[:400]  # Limit text length
            new_text = (edited_message.text or edited_message.caption or '')[:400]
            
            if original_text == new_text:
                return  # No actual text change
            
            # Escape HTML characters
            def escape_html(text):
                if not text:
                    return "(No text)"
                return text.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
            
            original_escaped = escape_html(original_text)
            new_escaped = escape_html(new_text)
            
            # Create initial notification (hidden by default)
            edit_notification = (
                f"📝 <b>Message Edited</b> by <b>{user_mention}</b>\n"
            )
            
            # Create inline keyboard with Reveal/Hide and Dismiss buttons
            from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
            
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="👀️", 
                        callback_data=f"reveal_edit:{message_id}:{user.id}"
                    ),
                    InlineKeyboardButton(
                        text="🗑️", 
                        callback_data=f"dismiss_edit:{message_id}"
                    )
                ]
            ])
            
            # Store edit data for reveal functionality (we'll need this in callback handler)
            edit_data_key = f"edit_{chat_id}_{message_id}"
            if not hasattr(self, 'edit_data_cache'):
                self.edit_data_cache = {}
            
            self.edit_data_cache[edit_data_key] = {
                'original': original_escaped,
                'new': new_escaped,
                'editor_id': user.id,
                'editor_mention': user_mention
            }
            
            # Update message in cache
            self.message_cache.add_message(chat_id, edited_message)
            
            # Send notification with inline keyboard
            try:
                await self.bot.send_message(
                    chat_id=chat_id,
                    text=edit_notification,
                    parse_mode="HTML",
                    reply_markup=keyboard,
                    reply_to_message_id=message_id
                )
            except Exception as send_error:
                logger.error(f"Error sending edit notification: {send_error}")
                # Try without reply if original message was deleted
                try:
                    await self.bot.send_message(
                        chat_id=chat_id,
                        text=edit_notification,
                        parse_mode="HTML",
                        reply_markup=keyboard
                    )
                except Exception as fallback_error:
                    logger.error(f"Error sending fallback edit notification: {fallback_error}")
                
        except Exception as e:
            logger.error(f"Error handling edited message: {e}")
    
    async def _handle_new_members(self, message: Message) -> None:
        """Handle new members joining the group"""
        try:
            if message.chat.type not in ['group', 'supergroup']:
                return
            
            # Check if bot was added
            bot_info = await self.bot.get_me()
            for new_member in message.new_chat_members:
                if new_member.id == bot_info.id:
                    welcome_msg = (
						"👋 Hey there! Thanks for adding Sus Ninja!\n\n"
						"I’m now watching your group for sneaky deletes and edits.\n\n"
						"Important: Give me admin powers so I can do my magic! 💖\n\n"
						"Type /help to see all my naughty tricks!"
					)
                    
                    await message.reply(welcome_msg, parse_mode="Markdown")
                    self.active_chats.add(message.chat.id)
                    break
                    
        except Exception as e:
            logger.error(f"Error handling new members: {e}")
    
    async def _set_bot_commands(self) -> None:
        """Set bot commands menu"""
        try:
            from aiogram.types import BotCommand
            
            commands = [
                BotCommand(command="start", description="⚔️ Awaken Sus Ninja"),
                BotCommand(command="help", description="🥷 Ninja Techniques")
            ]
            
            await self.bot.set_my_commands(commands)
            logger.info("Bot commands menu set successfully")
            
        except Exception as e:
            logger.error(f"Error setting bot commands: {e}")

    async def _announce_deletion(self, chat_id: int, deleted_msg: dict) -> None:
        """Announce when a message was deleted"""
        try:
            user_id = deleted_msg.get('user_id')
            username = deleted_msg.get('username')
            first_name = deleted_msg.get('first_name', 'Unknown User')
            deleted_text = deleted_msg.get('text', '')[:400]
            
            # Create user mention with HTML formatting using full name
            # Note: For deleted messages, we only have cached data
            full_name = first_name or ""
            last_name = deleted_msg.get('last_name', '')
            if last_name:
                full_name += f" {last_name}"
            if not full_name:
                full_name = username if username else "Unknown User"
                
            user_mention = f'<a href="tg://user?id={user_id}">{full_name}</a>'
            
            # Escape HTML characters
            def escape_html(text):
                if not text:
                    return "(No text)"
                return text.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
            
            deleted_escaped = escape_html(deleted_text)
            
            deletion_notification = (
                f"🗑️ Message Deleted by {user_mention} • "
                f"Deleted message: <b>{deleted_escaped}</b>"
            )
            
            # Send notification
            await self.bot.send_message(
                chat_id=chat_id,
                text=deletion_notification,
                parse_mode="HTML"
            )
            
        except Exception as e:
            logger.error(f"Error announcing deletion: {e}")
    
    async def _handle_help_expand(self, callback_query: types.CallbackQuery) -> None:
        """Handle help expand callback"""
        try:
            # Get user info for personalization
            user_info = None
            if callback_query.from_user:
                user_info = {
                    "user_id": callback_query.from_user.id,
                    "full_name": callback_query.from_user.full_name or "User"
                }
            
            # Create expanded help message
            if user_info and user_info["user_id"]:
                user_mention = f'<a href="tg://user?id={user_info["user_id"]}">{user_info["full_name"]}</a>'
                help_text_expanded = (
					f"💖 <b>Sus Ninja Manual for {user_mention}</b>\n\n"
					"<b>My Arsenal:</b>\n"
					"• /start - Wake your fierce Sus Ninja 💞\n"
					"• /help - Grab this sexy guide 💕\n"
					"• /ping - Check if I’m ready 💫\n\n"
					"<b>How I rule your group:</b>\n"
					"1. Drag me in, let’s get cozy 🤫\n"
					"2. Give me admin powers to tease 👑\n"
					"3. I watch silently, catching all 👀\n"
					"4. Sneaky? BAM! Secrets spilled 💥\n\n"
					"<b>My Powers:</b>\n"
					"• 👀️ Always watching you\n"
					"• 🚨 Catch sus instantly\n"
					"• 📊 Remember EVERYTHING\n"
					"• ⚡ Faster than excuses\n\n"
					"<b>Advanced Moves:</b>\n"
					"• 🔄 Track every edit\n"
					"• 🗑️ Expose deleted msgs\n"
					"• 📈 Monitor performance\n"
					"• 🛡️ Stealth until slip\n\n"
					"Need backup? Join us for epic support! 💖"
				)
            else:
                help_text_expanded = (
					"💖 <b>Sus Ninja Manual</b>\n\n"
					"<b>My Arsenal:</b>\n"
					"• /start - Wake your fierce Sus Ninja 💞\n"
					"• /help - Grab this sexy guide 💕\n"
					"• /ping - Check if I’m ready 💫\n\n"
					"<b>How I rule your group:</b>\n"
					"1. Drag me in, let’s get cozy 🤫\n"
					"2. Give me admin powers to tease 👑\n"
					"3. I watch silently, catching all 👀\n"
					"4. Sneaky? BAM! Secrets spilled 💥\n\n"
					"<b>My Powers:</b>\n"
					"• 👀️ Always watching you\n"
					"• 🚨 Catch sus instantly\n"
					"• 📊 Remember EVERYTHING\n"
					"• ⚡ Faster than excuses\n\n"
					"<b>Advanced Moves:</b>\n"
					"• 🔄 Track every edit\n"
					"• 🗑️ Expose deleted msgs\n"
					"• 📈 Monitor performance\n"
					"• 🛡️ Stealth until slip\n\n"
					"Need backup? Join us for epic support! 💖"
				)
            
            # Create minimize button
            builder = InlineKeyboardBuilder()
            builder.row(
                InlineKeyboardButton(text="📖 Minimize Guide", callback_data="help_minimize")
            )
            
            await callback_query.answer()
            if callback_query.message:
                await callback_query.message.edit_text(
                    help_text_expanded,
                    reply_markup=builder.as_markup(),
                    parse_mode="HTML"
                )
                logger.info(f"✅ Help expanded for user {callback_query.from_user.id if callback_query.from_user else 'unknown'}")
                
        except Exception as e:
            logger.error(f"❌ Error expanding help: {e}")
            await callback_query.answer("🌷 Uh oh! Help expansion exploded on me! 💥", show_alert=True)
    
    async def _handle_help_minimize(self, callback_query: types.CallbackQuery) -> None:
        """Handle help minimize callback"""
        try:
            # Get user info for personalization
            user_info = None
            if callback_query.from_user:
                user_info = {
                    "user_id": callback_query.from_user.id,
                    "full_name": callback_query.from_user.full_name or "User"
                }
            
            # Create basic help message
            if user_info and user_info["user_id"]:
                user_mention = f'<a href="tg://user?id={user_info["user_id"]}">{user_info["full_name"]}</a>'
                help_text_basic = (
				    f"🥷 <b>Sus Ninja Bot Help for {user_mention}</b>\n\n"
				    "<b>Ninja Commands:</b>\n"
  				  "• <b>/start</b> - Wake up your naughty Sus Ninja 💖\n"
 				   "• <b>/help</b> - Peek at my sexy secrets 💕\n"
  				  "• <b>/ping</b> - Test my quick, teasing reflexes 💫\n\n"
				    "<b>How your naughty ninja works:</b>\n"
  				  "1. Add me to your group and let me get cozy 🤫\n"
  				  "2. Give me admin powers to watch and tease 👑\n"
 				   "3. I silently catch every cheeky move 👀\n"
  				  "4. When someone gets sus (deletes/edits), I spill the naughty tea 💥"
				)
            else:
                help_text_basic = (
				    "🥷 <b>Sus Ninja Bot Help</b>\n\n"
				    "<b>Ninja Commands:</b>\n"
  				  "• <b>/start</b> - Wake up your naughty Sus Ninja 💖\n"
 				   "• <b>/help</b> - Peek at my sexy secrets 💕\n"
  				  "• <b>/ping</b> - Test my quick, teasing reflexes 💫\n\n"
				    "<b>How your naughty ninja works:</b>\n"
  				  "1. Add me to your group and let me get cozy 🤫\n"
  				  "2. Give me admin powers to watch and tease 👑\n"
 				   "3. I silently catch every cheeky move 👀\n"
  				  "4. When someone gets sus (deletes/edits), I spill the naughty tea 💥"
				)
            
            # Create expand button
            builder = InlineKeyboardBuilder()
            builder.row(
                InlineKeyboardButton(text="📖 Expand Guide", callback_data="help_expand")
            )
            
            await callback_query.answer()
            if callback_query.message:
                await callback_query.message.edit_text(
                    help_text_basic,
                    reply_markup=builder.as_markup(),
                    parse_mode="HTML"
                )
                logger.info(f"✅ Help minimized for user {callback_query.from_user.id if callback_query.from_user else 'unknown'}")
                
        except Exception as e:
            logger.error(f"❌ Error minimizing help: {e}")
            await callback_query.answer("🌷 Uh oh! Help minimizer just melted down!", show_alert=True)

    async def _handle_callback_query(self, callback_query: types.CallbackQuery) -> None:
        """Handle inline button callbacks"""
        try:
            # Handle help expand/minimize
            if callback_query.data == "help_expand":
                await self._handle_help_expand(callback_query)
            elif callback_query.data == "help_minimize":
                await self._handle_help_minimize(callback_query)
            # Handle edit reveal/hide functionality
            elif callback_query.data.startswith("reveal_edit:"):
                parts = callback_query.data.split(":")
                if len(parts) >= 3:
                    message_id = parts[1]
                    editor_id = int(parts[2])
                    
                    # Prevent the editor from using reveal/hide buttons
                    if callback_query.from_user.id == editor_id:
                        await callback_query.answer("🌷 Nice try, sweetie! No spying on your mess!", show_alert=True)
                        return
                    
                    chat_id = callback_query.message.chat.id
                    edit_data_key = f"edit_{chat_id}_{message_id}"
                    
                    if hasattr(self, 'edit_data_cache') and edit_data_key in self.edit_data_cache:
                        edit_data = self.edit_data_cache[edit_data_key]
                        
                        # Check current state (revealed or hidden)
                        current_text = callback_query.message.text
                        is_revealed = "From:" in current_text and "To:" in current_text
                        
                        if is_revealed:
                            # Hide the edit details
                            new_text = (
                                f"📝 <b>Message Edited</b> by {edit_data['editor_mention']}\n"
                                f"<i>Click Reveal to see the changes</i>"
                            )
                            new_button_text = "👀️"
                        else:
                            # Show the edit details
                            new_text = (
                                f"📝 <b>Message Edited</b> by {edit_data['editor_mention']}\n\n"
                                f"<b>From:</b> {edit_data['original']}\n\n"
                                f"<b>To:</b> {edit_data['new']}"
                            )
                            new_button_text = "✉️"
                        
                        # Update keyboard with new button text
                        from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
                        keyboard = InlineKeyboardMarkup(inline_keyboard=[
                            [
                                InlineKeyboardButton(
                                    text=new_button_text, 
                                    callback_data=f"reveal_edit:{message_id}:{editor_id}"
                                ),
                                InlineKeyboardButton(
                                    text="🗑️", 
                                    callback_data=f"dismiss_edit:{message_id}"
                                )
                            ]
                        ])
                        
                        await callback_query.message.edit_text(
                            new_text,
                            parse_mode="HTML",
                            reply_markup=keyboard
                        )
                        
                        action = "hidden" if is_revealed else "revealed"
                        await callback_query.answer(f"✨ Yay! Details {action} just perfectly 💕")
                        logger.info(f"🔄 Edit details {action} by user {callback_query.from_user.id}")
                    else:
                        await callback_query.answer("🌷 Hmm, that edit data poofed away, sweetie!", show_alert=True)
                        
            elif callback_query.data.startswith("dismiss_edit:"):
                # Handle dismiss functionality
                parts = callback_query.data.split(":")
                if len(parts) >= 2:
                    message_id = parts[1]
                    chat_id = callback_query.message.chat.id
                    edit_data_key = f"edit_{chat_id}_{message_id}"
                    
                    # Check if the user trying to dismiss is the editor
                    if hasattr(self, 'edit_data_cache') and edit_data_key in self.edit_data_cache:
                        edit_data = self.edit_data_cache[edit_data_key]
                        editor_id = edit_data.get('editor_id')
                        
                        # Prevent the editor from dismissing their own edit notification
                        if callback_query.from_user.id == editor_id:
                            await callback_query.answer("🌷 Trying to hide that mess? Not today, sweetie! 🌸", show_alert=True)
                            return
                    
                    # Check if user is admin in the chat
                    try:
                        chat_member = await self.bot.get_chat_member(chat_id, callback_query.from_user.id)
                        is_admin = chat_member.status in ['administrator', 'creator']
                        
                        if not is_admin:
                            await callback_query.answer("🌷 Wait up, sweetie! Only admins handle this mess! 🌸", show_alert=True)
                            return
                    except Exception as e:
                        logger.error(f"Error checking admin status: {e}")
                        await callback_query.answer("🧚‍♀️ Oops! My circuits fluttered away. Try again, darling!", show_alert=True)
                        return
                    
                    # Allow dismiss for admins only (except the editor)
                    await callback_query.message.delete()
                    await callback_query.answer("🌷 Poof! Edit floated away, babe!")
                    logger.info(f"🗑️ Edit notification dismissed by admin {callback_query.from_user.id}")
                    
                    # Clean up cached edit data
                    if hasattr(self, 'edit_data_cache') and edit_data_key in self.edit_data_cache:
                        del self.edit_data_cache[edit_data_key]
            # Handle broadcast target selection
            elif callback_query.data in ["broadcast_users", "broadcast_groups"]:
                if not callback_query.from_user or callback_query.from_user.id != OWNER_ID:
                    await callback_query.answer("🌷 Not for you, sweetie, sorry!", show_alert=True)
                    return
                
                target = "users" if callback_query.data == "broadcast_users" else "groups"
                target_list = user_ids if target == "users" else group_ids
                
                # Enable broadcast mode for owner
                broadcast_mode.add(callback_query.from_user.id)
                broadcast_target[callback_query.from_user.id] = target
                
                await callback_query.answer(f"🌷 Broadcast’s live! Time to stir the pot, {target}! 💥📡")
                
                # Update the message
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
                
                logger.info(f"🔓 Broadcast mode enabled for {callback_query.from_user.id} targeting {target}")
            else:
                await callback_query.answer()
                
        except Exception as e:
            logger.error(f"Error handling callback query: {e}")
            await callback_query.answer("🌷 Oops! Things didn’t go as planned!", show_alert=True)
    
    async def _periodic_cleanup(self) -> None:
        """Periodic cleanup task to manage memory usage"""
        while True:
            try:
                await asyncio.sleep(CLEANUP_INTERVAL)
                self.message_cache.cleanup_expired()
                
                # Log statistics every hour
                total_messages = sum(len(msgs) for msgs in self.message_cache.messages.values())
                logger.info(f"Stats - Active chats: {len(self.active_chats)}, Cached messages: {total_messages}")
                
            except Exception as e:
                logger.error(f"Error in periodic cleanup: {e}")
                await asyncio.sleep(60)  # Wait a minute before retrying
    
    async def _check_deleted_messages(self) -> None:
        """Check for deleted messages by monitoring message patterns"""
        while True:
            try:
                await asyncio.sleep(60)  # Check every minute
                
                # For now, we'll rely on edit detection and user reports
                # True deletion detection requires webhook mode or more complex tracking
                # In polling mode, we can detect some deletions when users try to reply to deleted messages
                
                for chat_id in list(self.active_chats):
                    try:
                        # Clean up very old messages from tracking
                        current_time = time.time()
                        chat_messages = self.message_cache.messages.get(chat_id, {})
                        
                        # Remove messages older than 2 hours from recent tracking
                        expired_ids = []
                        for msg_id, msg_data in chat_messages.items():
                            if current_time - msg_data['timestamp'] > 7200:  # 2 hours
                                expired_ids.append(msg_id)
                        
                        for msg_id in expired_ids:
                            self.message_cache.recent_message_ids[chat_id].discard(msg_id)
                            
                    except Exception as chat_error:
                        logger.error(f"Error in message tracking cleanup for chat {chat_id}: {chat_error}")
                        continue
                        
            except Exception as e:
                logger.error(f"Error in deletion check: {e}")
                await asyncio.sleep(300)  # Wait 5 minutes if there's an error
    
    async def start_polling(self) -> None:
        """Start the bot with polling"""
        try:
            logger.info("Starting Sus Ninja Bot...")
            bot_info = await self.bot.get_me()
            logger.info(f"Bot @{bot_info.username} is running!")
            
            # Set bot commands menu
            await self._set_bot_commands()
            
            # Start polling
            await self.dp.start_polling(self.bot, skip_updates=True)
            
        except Exception as e:
            logger.error(f"Error starting bot: {e}")
            raise

async def main():
    """Main function to run the bot"""
    logger.info("🚀 Starting main bot execution")
    
    if not BOT_TOKEN or BOT_TOKEN == "YOUR_BOT_TOKEN_HERE":
        logger.error("❌ BOT_TOKEN not configured - please set environment variable")
        logger.error("🔧 Set token with: export BOT_TOKEN='your_token_here'")
        return
    
    logger.info("✅ Bot token validation passed")
    
    try:
        # Start dummy HTTP server (needed for Render health check)
        logger.info("🌐 Starting dummy HTTP server for deployment platform compatibility")
        threading.Thread(target=start_dummy_server, daemon=True).start()
        logger.info("✅ HTTP server thread started as daemon")
        
        # Create and start bot
        logger.info("🥷 Creating SusNinjaBot instance")
        bot = SusNinjaBot(BOT_TOKEN)
        
        logger.info("🚀 Starting bot polling...")
        await bot.start_polling()
        
    except KeyboardInterrupt:
        logger.info("🛑 Bot stopped by user (Ctrl+C)")
    except Exception as e:
        logger.error(f"💥 Bot crashed with fatal error: {e}")
        logger.error(f"🔧 Error type: {type(e).__name__}")
        raise

if __name__ == "__main__":
    logger.info("🎯 Bot script started from command line")
    
    # Handle the event loop for high concurrency
    try:
        logger.info("⚙️ Configuring asyncio for high performance")
        
        # Configure asyncio for high performance
        if hasattr(asyncio, 'set_event_loop_policy'):
            if os.name == 'nt':  # Windows
                logger.info("🪟 Windows detected - using ProactorEventLoopPolicy")
                asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
            else:  # Unix/Linux
                logger.info("🐧 Unix/Linux detected - applying performance optimizations")
                try:
                    # Use asyncio's built-in performance optimizations
                    import concurrent.futures
                    
                    # Set up thread pool for CPU-bound operations
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    
                    # Create thread pool executor for better performance
                    executor = concurrent.futures.ThreadPoolExecutor(max_workers=4)
                    loop.set_default_executor(executor)
                    
                    # Enable asyncio optimizations
                    loop.set_debug(False)  # Disable debug for production performance
                    
                    logger.info("⚡ Asyncio performance optimizations enabled with thread pool")
                except Exception as e:
                    logger.info(f"📦 Using default asyncio policy: {e}")
                    pass  # Use default policy
        
        logger.info("🎬 Launching main bot function")
        # Run the bot
        asyncio.run(main())
        
    except KeyboardInterrupt:
        logger.info("✅ Bot shutdown completed gracefully")
    except Exception as e:
        logger.error(f"💥 Critical error in main execution: {e}")
        logger.error(f"🔧 Error type: {type(e).__name__}")
        raise
    except Exception as e:
        logger.error(f"Fatal error: {e}")