"""
Cấu hình chung cho bot. Đọc từ biến môi trường / file .env
"""
import os
from dotenv import load_dotenv

load_dotenv()

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
DEV_GUILD_ID = os.getenv("DEV_GUILD_ID") or None
DB_PATH = os.getenv("DB_PATH", "quyby.db")

# Gemini API key cho lớp AI Narrative (mục 29 trong spec) — CHỈ dùng để
# diễn đạt câu chữ, không có quyền quyết định trạng thái game. Nếu để
# trống, engine tự dùng câu thoại tĩnh có sẵn, game vẫn chạy bình thường.
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY") or None
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-1.5-flash")

if DEV_GUILD_ID is not None:
    DEV_GUILD_ID = int(DEV_GUILD_ID)

# Ngôn ngữ mặc định cho user mới
DEFAULT_LANGUAGE = "vi"

# Icon dùng thống nhất toàn bộ UI (mục 54 trong tài liệu spec)
ICONS = {
    "character": "👤",
    "pathway": "🧬",
    "sequence": "🔢",
    "characteristic": "🧿",
    "potion": "🧪",
    "acting": "🎭",
    "digestion": "📖",
    "ability": "✨",
    "spirituality": "🧠",
    "loss_of_control": "☠️",
    "mysticism": "🔮",
    "divination": "🃏",
    "ritual": "📜",
    "artifact": "🕯️",
    "world": "🌍",
    "city": "🏙️",
    "location": "📍",
    "investigation": "🔍",
    "event": "🌑",
    "npc": "👤",
    "church": "⛪",
    "faction": "🏛️",
    "guild": "🛡️",
    "tarot": "🃏",
    "party": "👥",
    "trade": "🤝",
    "contract": "📜",
    "bounty": "☠️",
    "quest": "📜",
    "combat": "⚔️",
    "pvp": "🏟️",
    "pve": "👹",
    "boss": "👑",
    "dungeon": "🏰",
    "economy": "💰",
    "shop": "🛒",
    "market": "🏪",
    "auction": "🔨",
    "black_market": "🕶️",
    "mental_state": "🧠",
    "history": "📜",
    "inventory": "🎒",
    "house": "🏠",
    "achievement": "🏆",
    "ranking": "📊",
    "season": "🗓️",
    "settings": "⚙️",
    "language": "🌐",
    "back": "⬅️",
    "next": "➡️",
    "locked": "🔒",
    "hp": "❤️",
}
