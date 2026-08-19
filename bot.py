"""
Entry point cho bot Quỷ Bí.

Chạy:
    pip install -r requirements.txt
    cp .env.example .env   # rồi điền DISCORD_TOKEN
    python bot.py
"""
import asyncio
import logging

import discord
from discord import app_commands
from discord.ext import commands

from config import DISCORD_TOKEN, DEV_GUILD_ID
import database as db
import error_handler
from cogs.menu import BOT_HOME_GUILD_ID

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("quyby-bot")

INTENTS = discord.Intents.default()
# Bật message_content: cần cho lệnh dạng text ".huongdan" (commands.command)
# đọc được nội dung tin nhắn. Các lệnh còn lại vẫn dùng slash command +
# component nên không phụ thuộc intent này.
INTENTS.message_content = True


class QuyBiBot(commands.Bot):
    def __init__(self):
        # Prefix "." cho lệnh text (hiện chỉ có .huongdan) — tách biệt với
        # slash command "/" để không bị lẫn vào danh sách autocomplete
        # slash command chung của server (có thể trùng tên với bot khác).
        super().__init__(command_prefix=".", intents=INTENTS)

    async def setup_hook(self):
        db.init_db()
        await self.load_extension("cogs.menu")

        # Lưới an toàn cấp cuối cho slash command: nếu một lệnh ném ra lỗi
        # chưa được xử lý riêng, người chơi vẫn chỉ thấy một Embed trung
        # lập thay vì "Ứng dụng không phản hồi" hoặc bất kỳ chi tiết kỹ
        # thuật nào. Log đầy đủ vẫn được ghi phía dev.
        async def on_tree_error(interaction: discord.Interaction, error: app_commands.AppCommandError):
            command_name = interaction.command.qualified_name if interaction.command else "unknown_command"
            await error_handler.handle_unexpected(interaction, error, command_name)

        self.tree.on_error = on_tree_error

        if DEV_GUILD_ID:
            guild = discord.Object(id=DEV_GUILD_ID)
            self.tree.copy_global_to(guild=guild)
            synced = await self.tree.sync(guild=guild)
            log.info("Đã đồng bộ %d slash command tới guild dev.", len(synced))
        else:
            synced = await self.tree.sync()
            log.info("Đã đồng bộ %d slash command global (có thể mất tới 1h để hiện).", len(synced))

        # /download_data chỉ gắn với server chính của bot (xem
        # BOT_HOME_GUILD_ID trong cogs/menu.py) nên cần sync riêng cho guild
        # đó — không nằm trong global sync/copy_global_to ở trên.
        home_guild = discord.Object(id=BOT_HOME_GUILD_ID)
        home_synced = await self.tree.sync(guild=home_guild)
        log.info("Đã đồng bộ %d slash command riêng cho guild chính của bot.", len(home_synced))

    async def on_ready(self):
        log.info("Đăng nhập với tên %s (ID: %s)", self.user, self.user.id)


async def main():
    if not DISCORD_TOKEN:
        raise SystemExit("Chưa cấu hình DISCORD_TOKEN — sao chép .env.example thành .env và điền token.")

    bot = QuyBiBot()
    async with bot:
        await bot.start(DISCORD_TOKEN)


if __name__ == "__main__":
    asyncio.run(main())
