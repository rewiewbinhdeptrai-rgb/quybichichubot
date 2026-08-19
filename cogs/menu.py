"""
Discord UI — hệ thống /menu gộp, phân tầng (mục 52-65 trong spec).

Nguyên tắc:
- Một cửa vào duy nhất: /menu
- Menu chính chỉ chứa nhóm lớn (~10-12 option)
- Chọn nhóm -> mở submenu -> chọn chức năng cụ thể
- Riêng "Con đường": chọn Pathway -> chọn Sequence -> chi tiết
  Sequence chưa đạt hiển thị khóa 🔒, không cho bypass advancement.
- Engine (database.py) là nguồn sự thật; view chỉ đọc/hiển thị.
"""
import re

import discord
from discord import app_commands
from discord.ext import commands

import database as db
import effects
import progression as prog
import potions as potions_engine
import characteristics as char_engine
import ritual as ritual_engine
import artifacts as artifact_engine
import mysticism as mysticism_engine
import divination as divination_engine
import world as world_engine
import world_event
import npc as npc_engine
import investigation as investigation_engine
import quest as quest_engine
import combat
import pvp
import dungeon
import inventory as inv
import faction as faction_engine
import tarot as tarot_engine
import party as party_engine
import economy as economy_engine
import house as house_engine
import achievements as achievements_engine
import guild as guild_engine
import auction as auction_engine
import black_market as black_market_engine
import loss_of_control
import error_handler
from config import ICONS, DB_PATH
import i18n
import os

# Lệnh /download_data chỉ được đăng ký trong server của bot và chỉ admin
# này mới gọi được — không liên quan gameplay, chỉ phục vụ vận hành/backup.
BOT_HOME_GUILD_ID = 1530517263046934569
DATA_ADMIN_USER_ID = 1530490044098285711

MAIN_CATEGORIES = [
    ("character", "Nhân vật", "Hồ sơ, chỉ số, trạng thái.", ICONS["character"]),
    ("pathway", "Con đường", "Pathway, Sequence, tiến cấp.", ICONS["pathway"]),
    ("ability", "Năng lực", "Abilities, Passive, kỹ năng.", ICONS["ability"]),
    ("mysticism", "Huyền bí", "Mysticism, Divination, Ritual, Knowledge.", ICONS["mysticism"]),
    ("inventory", "Tài sản", "Inventory, Potion, Artifact, Equipment.", ICONS["inventory"]),
    ("combat", "Chiến đấu", "PvP, PvE, Dungeon, Boss.", ICONS["combat"]),
    ("world", "Thế giới", "World, City, Location, NPC, Investigation, Event.", ICONS["world"]),
    ("faction", "Tổ chức", "Church, Faction, Tarot, Party.", ICONS["faction"]),
    ("economy", "Giao dịch", "Economy, Market, Auction, Trade, Contract, Bounty.", ICONS["economy"]),
    ("house", "Đời sống", "House, Achievement, Ranking.", ICONS["house"]),
    ("settings", "Cài đặt", "Language, notification, UI settings.", ICONS["settings"]),
]

# Các nhóm menu chính chưa có Engine thật đứng sau (routing rơi vào nhánh
# else trong MainMenuSelect.callback -> build_stub_embed). "ability" đã có
# Engine thật (xem build_ability_menu_embed) nên không còn nằm trong danh
# sách này.
STUB_CATEGORIES = set()


class SafeView(discord.ui.View):
    """Base cho MỌI View trong bot.

    Đây là lưới an toàn cấp cuối: nếu một item (Select/Button) trong View
    ném ra exception mà bản thân callback đó chưa tự bọc bằng
    @error_handler.safe_interaction, discord.py sẽ gọi on_error() này thay
    vì để lỗi rơi ra ngoài. Người chơi luôn chỉ thấy một Embed trung lập,
    không bao giờ thấy traceback/tên biến/ID nội bộ; log kỹ thuật đầy đủ
    vẫn được ghi lại phía dev.

    interaction_check(): /menu KHÔNG gửi ephemeral (mục 52 — menu cần ở lại
    kênh để người khác thấy Character đang làm gì), nên message của View này
    hiển thị công khai cho cả kênh. Không có check nào trước đây -> BẤT KỲ
    ai trong kênh cũng bấm được nút/Select trên menu của người khác (đổi
    Character, tấn công hộ, uống Potion hộ, chấp nhận PvP hộ...). Sửa bằng
    cách so khớp interaction.user với người đã tạo ra Interaction gốc sinh
    ra Message này (Discord lưu lại qua message.interaction_metadata — hoặc
    message.interaction ở bản discord.py cũ hơn), áp dụng chung một lần cho
    toàn bộ ~180 View/Select/Button kế thừa SafeView, không cần sửa từng
    class con. Message không gắn với Interaction nào (vd Embed do task nền
    tự gửi) thì không xác định được chủ sở hữu — cho qua (fail open), không
    đổi hành vi cũ trong các trường hợp đó."""

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        message = interaction.message
        owner = None
        if message is not None:
            meta = getattr(message, "interaction_metadata", None)
            if meta is not None:
                owner = meta.user
            else:
                legacy = getattr(message, "interaction", None)
                owner = legacy.user if legacy is not None else None
        if owner is not None and interaction.user.id != owner.id:
            await interaction.response.send_message(
                "🔒 Đây không phải menu của bạn — dùng lệnh `/menu` để mở menu riêng của bạn.",
                ephemeral=True,
            )
            return False
        return True

    async def on_error(self, interaction: discord.Interaction, error: Exception, item) -> None:
        await error_handler.handle_unexpected(interaction, error, item.__class__.__qualname__)


# ---------------------------------------------------------------------------
# Embeds
# ---------------------------------------------------------------------------

def build_character_embed(character: dict) -> discord.Embed:
    embed = discord.Embed(title="🌑 QUỶ BÍ", color=discord.Color.dark_purple())

    if character is None:
        embed.description = (
            "Bạn chưa có nhân vật nào.\n"
            "Bấm **Tạo nhân vật** bên dưới để bắt đầu."
        )
        return embed

    lang = i18n.user_lang(character["user_id"])
    pathway = db.get_pathway(character["pathway_id"]) if character["pathway_id"] else None
    seq_name = None
    if pathway:
        seqs = {s["sequence_number"]: s["name_vi"] for s in db.list_sequences(pathway["pathway_id"])}
        seq_name = seqs.get(character["sequence_number"])

    embed.add_field(name=f"{ICONS['character']} Nhân vật", value=character["name"], inline=False)

    if pathway:
        pathway_line = f"{pathway['icon']} {pathway['name_vi']}"
        seq_line = f"Sequence {character['sequence_number']}" + (f" — {seq_name}" if seq_name else "")
    else:
        pathway_line = "Chưa chọn"
        seq_line = "—"

    embed.add_field(name=f"{ICONS['pathway']} {i18n.t('character.pathway', lang)}", value=pathway_line, inline=True)
    embed.add_field(name=f"{ICONS['sequence']} {i18n.t('character.sequence', lang)}", value=seq_line, inline=True)
    embed.add_field(
        name=f"{ICONS['spirituality']} {i18n.t('character.spirituality', lang)}",
        value=f"{character['spirituality']} / {character['spirituality_max']}",
        inline=True,
    )
    embed.add_field(
        name=f"{ICONS['hp']} {i18n.t('character.hp', lang)}",
        value=f"{character['hp']} / {character['hp_max']}",
        inline=True,
    )
    # mục 13 mở rộng: Risk giờ được loss_of_control.compute_risk() tính từ nhiều
    # yếu tố thật (Spirituality/Mental State/HP/Potion/Characteristic/Sequence/
    # Effect) mỗi lần hồ sơ được mở, KHÔNG còn là một con số tĩnh trên Character.
    risk_result = loss_of_control.compute_risk(character["character_id"])
    embed.add_field(
        name=f"{ICONS['loss_of_control']} {i18n.t('character.loss_of_control_risk', lang)}",
        value=f"{risk_result['total']}%",
        inline=True,
    )
    embed.add_field(
        name=f"{ICONS['mental_state']} {i18n.t('character.mental_state', lang)}",
        value=f"{character.get('mental_state', 100)} / 100",
        inline=True,
    )
    embed.add_field(name=f"💰 {i18n.t('character.money', lang)}", value=f"{character['money']:,} Bảng", inline=True)
    current_location = world_engine.get_current_location(character)
    location_line = current_location["name_en"] if current_location else "Chưa xác định"
    embed.add_field(name=f"{ICONS['location']} {i18n.t('character.location', lang)}", value=location_line, inline=True)
    return embed


def build_stub_embed(title: str, icon: str) -> discord.Embed:
    embed = discord.Embed(
        title=f"{icon} {title}",
        description="🚧 Tính năng này đang được phát triển và sẽ sớm ra mắt.",
        color=discord.Color.dark_grey(),
    )
    return embed


def build_ability_menu_embed(character: dict) -> discord.Embed:
    """✨ Năng lực — danh sách Ability THẬT mà nhân vật đã mở khóa (mục 17).
    Không còn stub: dữ liệu lấy trực tiếp từ bảng abilities (220 dòng,
    22 Pathway x 10 Sequence — xem data/abilities_seed.py)."""
    icon = ICONS["ability"]
    if character is None or not character.get("pathway_id"):
        embed = discord.Embed(
            title=f"{icon} Năng lực",
            description="Bạn chưa chọn Pathway — vào 🧬 Con đường trước.",
            color=discord.Color.dark_grey(),
        )
        return embed

    pathway = db.get_pathway(character["pathway_id"])
    abilities = db.list_unlocked_abilities(character["pathway_id"], character["sequence_number"])

    embed = discord.Embed(
        title=f"{icon} NĂNG LỰC — {pathway['name_vi']}",
        description=f"Sequence hiện tại: {character['sequence_number']}. "
                     f"Đã mở khóa {len(abilities)} Ability (Sequence đã đi qua trở lên).",
        color=discord.Color.purple(),
    )
    if not abilities:
        embed.add_field(name="—", value="Chưa có Ability nào mở khóa.", inline=False)
    else:
        for a in abilities:
            embed.add_field(
                name=f"Sequence {a['sequence_number']} — {a['name_vi']}",
                value=f"Cost: {a['cost']} Spirituality · Damage x{a['damage_multiplier']}",
                inline=False,
            )
    return embed


class AbilityMenuView(SafeView):
    def __init__(self):
        super().__init__(timeout=180)
        self.add_item(BackButton(MainMenuView))


# ---------------------------------------------------------------------------
# Shared UI pieces
# ---------------------------------------------------------------------------

class BackButton(discord.ui.Button):
    def __init__(self, target_view_factory):
        super().__init__(label="Quay lại", emoji=ICONS["back"], style=discord.ButtonStyle.secondary, row=4)
        self._target_view_factory = target_view_factory

    async def callback(self, interaction: discord.Interaction):
        view = self._target_view_factory()
        character = db.get_character(str(interaction.user.id))
        await interaction.response.edit_message(embed=build_character_embed(character), view=view)


class MainMenuSelect(discord.ui.Select):
    def __init__(self, lang: str = None):
        lang = lang or i18n.DEFAULT_LANG
        options = [
            discord.SelectOption(
                label=i18n.t(f"main_menu.{key}", lang, default=label), description=desc[:100], emoji=icon, value=key,
            )
            for key, label, desc, icon in MAIN_CATEGORIES
        ]
        super().__init__(
            placeholder=f"📖 {i18n.t('main_menu.placeholder', lang)}",
            min_values=1,
            max_values=1,
            options=options,
            row=0,
        )

    @error_handler.safe_interaction(lambda: MainMenuView())
    async def callback(self, interaction: discord.Interaction):
        key = self.values[0]
        user_id = str(interaction.user.id)
        character = db.get_character(user_id)
        lang = i18n.user_lang(user_id)

        if key == "character":
            embed = build_character_embed(character)
            await interaction.response.edit_message(embed=embed, view=CharacterMenuView())
        elif key == "pathway":
            embed = build_character_embed(character)
            await interaction.response.edit_message(embed=embed, view=PathwaySelectView())
        elif key == "settings":
            embed = build_character_embed(character)
            await interaction.response.edit_message(embed=embed, view=SettingsView())
        elif key == "inventory":
            embed = build_character_embed(character)
            await interaction.response.edit_message(embed=embed, view=InventoryMenuView())
        elif key == "combat":
            embed = build_character_embed(character)
            await interaction.response.edit_message(embed=embed, view=CombatMenuView(lang))
        elif key == "mysticism":
            embed = build_character_embed(character)
            await interaction.response.edit_message(embed=embed, view=MysticismMenuView(lang))
        elif key == "world":
            embed = build_world_overview_embed(character)
            await interaction.response.edit_message(embed=embed, view=WorldMenuView(lang))
        elif key == "ability":
            embed = build_ability_menu_embed(character)
            await interaction.response.edit_message(embed=embed, view=AbilityMenuView())
        elif key == "faction":
            embed = build_faction_hub_embed(character)
            await interaction.response.edit_message(embed=embed, view=FactionMenuView())
        elif key == "economy":
            embed = build_economy_hub_embed(character)
            await interaction.response.edit_message(embed=embed, view=EconomyMenuView())
        elif key == "house":
            embed = build_house_hub_embed(character)
            lang = i18n.user_lang(character["user_id"]) if character else None
            await interaction.response.edit_message(embed=embed, view=HouseMenuView(lang))
        else:
            label = next(l for k, l, d, i in MAIN_CATEGORIES if k == key)
            icon = next(i for k, l, d, i in MAIN_CATEGORIES if k == key)
            await interaction.response.edit_message(
                embed=build_stub_embed(label, icon),
                view=SimpleBackView(MainMenuView),
            )


class MainMenuView(SafeView):
    def __init__(self, lang: str = None):
        super().__init__(timeout=180)
        self.add_item(MainMenuSelect(lang))


class SimpleBackView(SafeView):
    """View chỉ có nút Quay lại — dùng cho submenu chưa triển khai."""

    def __init__(self, target_view_factory):
        super().__init__(timeout=180)
        self.add_item(BackButton(target_view_factory))


# ---------------------------------------------------------------------------
# 👤 Nhân vật submenu (mục 64)
# ---------------------------------------------------------------------------

class CharacterMenuSelect(discord.ui.Select):
    OPTIONS = [
        ("profile", "Hồ sơ", "👤"),
        ("stats", "Chỉ số", "📊"),
        ("status", "Trạng thái", "🧠"),
        ("characteristics", "Beyonder Characteristic", ICONS["characteristic"]),
        ("history", "Lịch sử", "📜"),
        ("achievements", "Thành tựu", "🏆"),
        ("switch", "Đổi nhân vật", "🔀"),
    ]
    STUB_KEYS = {"stats", "status", "history", "achievements"}

    def __init__(self):
        options = [
            discord.SelectOption(label=label, value=key, emoji=icon)
            for key, label, icon in self.OPTIONS
        ]
        super().__init__(placeholder="👤 Chọn chức năng", options=options, row=0)

    async def callback(self, interaction: discord.Interaction):
        character = db.get_character(str(interaction.user.id))
        key = self.values[0]
        if key == "profile":
            embed = build_character_embed(character)
            await interaction.response.edit_message(embed=embed, view=CharacterMenuView())
        elif key == "characteristics":
            embed, view = build_characteristics_view(character)
            await interaction.response.edit_message(embed=embed, view=view)
        elif key == "stats":
            embed = build_stats_embed(character)
            await interaction.response.edit_message(embed=embed, view=CharacterMenuView())
        elif key == "status":
            embed = build_status_embed(character)
            await interaction.response.edit_message(embed=embed, view=CharacterMenuView())
        elif key == "history":
            embed = build_history_embed(character)
            await interaction.response.edit_message(embed=embed, view=CharacterMenuView())
        elif key == "achievements":
            embed = build_achievements_embed(character)
            await interaction.response.edit_message(embed=embed, view=CharacterMenuView())
        elif key == "switch":
            embed, view = build_switch_character_view(str(interaction.user.id))
            await interaction.response.edit_message(embed=embed, view=view)
        else:
            label = next(l for k, l, i in self.OPTIONS if k == key)
            icon = next(i for k, l, i in self.OPTIONS if k == key)
            embed = build_stub_embed(label, icon)
            await interaction.response.edit_message(embed=embed, view=CharacterMenuView())


def build_switch_character_view(user_id: str):
    """🔀 Đổi nhân vật (mục 3, mục 33 báo cáo trước) — liệt kê MỌI Character
    của user, đánh dấu Character đang active. Đổi active_character_id là
    nguồn sự thật duy nhất mà get_character() đọc, nên chọn xong ở đây thì
    toàn hệ thống (Combat/Party/House/Inventory...) đồng bộ ngay lập tức."""
    characters = db.list_characters(user_id)
    embed = discord.Embed(title="🔀 ĐỔI NHÂN VẬT", color=discord.Color.dark_purple())
    if not characters:
        embed.description = "Bạn chưa có Character nào."
    else:
        lines = []
        for c in characters:
            mark = "▶️ " if c["is_active"] else "• "
            lines.append(f"{mark}**{c['name']}** — Lv.{c['level']} · Sequence {c['sequence_number']}")
        embed.description = "\n".join(lines)
    view = SwitchCharacterView(characters)
    return embed, view


class SwitchCharacterSelect(discord.ui.Select):
    def __init__(self, characters: list):
        options = [
            discord.SelectOption(
                label=f"{c['name']} (Lv.{c['level']})",
                value=str(c["character_id"]),
                emoji="▶️" if c["is_active"] else "👤",
                default=c["is_active"],
            )
            for c in characters
        ]
        super().__init__(placeholder="Chọn Character để chơi", options=options, row=0)

    async def callback(self, interaction: discord.Interaction):
        user_id = str(interaction.user.id)
        ok = db.switch_active_character(user_id, int(self.values[0]))
        if not ok:
            await interaction.response.send_message("Không thể đổi sang Character này.", ephemeral=True)
            return
        character = db.get_character(user_id)
        embed = build_character_embed(character)
        await interaction.response.edit_message(embed=embed, view=MainMenuView())


class SwitchCharacterView(SafeView):
    def __init__(self, characters: list):
        super().__init__(timeout=180)
        if characters:
            self.add_item(SwitchCharacterSelect(characters))
        self.add_item(CreateCharacterButton())
        self.add_item(BackButton(CharacterMenuView))


class CreateCharacterButton(discord.ui.Button):
    def __init__(self):
        super().__init__(label="Tạo nhân vật mới", emoji="👤", style=discord.ButtonStyle.success, row=1)

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.send_modal(CreateCharacterModal())


def build_stats_embed(character: dict) -> discord.Embed:
    """📊 Chỉ số — số liệu Engine thật (Level/EXP/HP/Spirituality/Money/
    Digestion), không phải hồ sơ tóm tắt như build_character_embed."""
    icon = "📊"
    if character is None:
        return build_stub_embed("Chỉ số", icon)

    progress = db.get_progress(character["character_id"])
    embed = discord.Embed(title=f"{icon} CHỈ SỐ — {character['name']}", color=discord.Color.blue())
    embed.add_field(name="Level", value=str(character["level"]), inline=True)
    embed.add_field(name="EXP", value=f"{character['exp']:,}", inline=True)
    embed.add_field(name=f"{ICONS['hp']} HP", value=f"{character['hp']} / {character['hp_max']}", inline=True)
    embed.add_field(
        name=f"{ICONS['spirituality']} Spirituality",
        value=f"{character['spirituality']} / {character['spirituality_max']}",
        inline=True,
    )
    embed.add_field(name="💰 Tiền", value=f"{character['money']:,} Bảng", inline=True)
    embed.add_field(name="📍 Location", value=character["location"], inline=True)
    if progress["potion_target_sequence"] is not None:
        embed.add_field(
            name="📖 Digestion",
            value=f"{progress['digestion']}% ({progress['status']})",
            inline=True,
        )
    return embed


def build_status_embed(character: dict) -> discord.Embed:
    """🧠 Trạng thái — Mental State + breakdown Loss of Control Risk tính
    thật từ loss_of_control.compute_risk() (mục 13), cùng buff/debuff đang
    có hiệu lực từ EffectEngine (mục 15-16), không phải số tĩnh."""
    icon = "🧠"
    if character is None:
        return build_stub_embed("Trạng thái", icon)

    risk = loss_of_control.compute_risk(character["character_id"])
    embed = discord.Embed(title=f"{icon} TRẠNG THÁI — {character['name']}", color=discord.Color.dark_gold())
    embed.add_field(name="🧠 Mental State", value=f"{character.get('mental_state', 100)} / 100", inline=True)
    embed.add_field(name="☠️ Loss of Control Risk", value=f"{risk['total']}%", inline=True)

    breakdown_lines = [
        f"• {factor}: +{value}%"
        for factor, value in risk["breakdown"].items()
        if value
    ]
    if breakdown_lines:
        embed.add_field(name="Nguồn Risk", value="\n".join(breakdown_lines), inline=False)

    active_effects = db.list_character_effects(character["character_id"])
    if active_effects:
        lines = [
            f"• {e['name_en']} ({e['modifier_key']} {e['modifier_value']:+}) — còn {e['duration']} lượt"
            for e in active_effects
        ]
        embed.add_field(name="Buff/Debuff đang có hiệu lực", value="\n".join(lines), inline=False)
    else:
        embed.add_field(name="Buff/Debuff đang có hiệu lực", value="Không có.", inline=False)
    return embed


def build_history_embed(character: dict) -> discord.Embed:
    """📜 Lịch sử — lấy trực tiếp từ action_log (mục 28), tối đa 15 dòng gần
    nhất, không phải danh sách dựng sẵn."""
    icon = "📜"
    if character is None:
        return build_stub_embed("Lịch sử", icon)

    entries = db.list_action_log(character["character_id"], limit=15)
    embed = discord.Embed(title=f"{icon} LỊCH SỬ — {character['name']}", color=discord.Color.greyple())
    if not entries:
        embed.description = "Chưa có hành động nào được ghi lại."
        return embed

    lines = []
    for e in entries:
        detail = f" — {e['detail']}" if e["detail"] else ""
        lines.append(f"`{e['created_at']}` **{e['action']}**{detail}")
    embed.description = "\n".join(lines)
    return embed


def build_achievements_embed(character: dict) -> discord.Embed:
    """🏆 Thành tựu — đối chiếu character_achievements thật (mục 45), hiện
    cả đã mở khoá lẫn còn khoá thay vì chỉ danh sách tên suông."""
    icon = "🏆"
    if character is None:
        return build_stub_embed("Thành tựu", icon)

    unlocked = achievements_engine.list_unlocked(character["character_id"])
    locked = achievements_engine.list_locked(character["character_id"])
    embed = discord.Embed(title=f"{icon} THÀNH TỰU — {character['name']}", color=discord.Color.gold())
    embed.add_field(
        name=f"Đã mở khoá ({len(unlocked)})",
        value="\n".join(f"✅ {a['name_vi']}" for a in unlocked) or "Chưa có.",
        inline=False,
    )
    locked_preview = locked[:10]
    remaining = len(locked) - len(locked_preview)
    locked_text = "\n".join(f"🔒 {a['name_vi']}" for a in locked_preview) or "Đã mở khoá hết!"
    if remaining > 0:
        locked_text += f"\n… và {remaining} thành tựu khác."
    embed.add_field(name=f"Chưa mở khoá ({len(locked)})", value=locked_text, inline=False)
    return embed


class CharacterMenuView(SafeView):
    def __init__(self):
        super().__init__(timeout=180)
        self.add_item(CharacterMenuSelect())
        self.add_item(BackButton(MainMenuView))


# ---------------------------------------------------------------------------
# 🧿 Beyonder Characteristic (mục 21) — Ownership / Consumption thật
# ---------------------------------------------------------------------------

def build_characteristics_view(character: dict):
    icon = ICONS["characteristic"]
    if character is None:
        embed = build_stub_embed("Beyonder Characteristic", icon)
        return embed, SimpleBackView(CharacterMenuView)

    owned = char_engine.list_owned(character["character_id"])
    embed = discord.Embed(title=f"{icon} BEYONDER CHARACTERISTIC", color=discord.Color.dark_teal())
    if not owned:
        embed.description = (
            "Chưa sở hữu Characteristic nào — hoàn thành Nghi thức tiến cấp "
            "(🧪 Ma dược) để nhận Characteristic gắn với Sequence vừa đạt được."
        )
    else:
        for c in owned:
            state_label = "🟢 Đang giữ" if c["state"] == "stored" else "⚪ Đã tiêu thụ"
            embed.add_field(
                name=f"{c['name_vi']} (Sequence {c['sequence_number']})",
                value=f"Stability: {c['stability']}% | {state_label} | Nguồn: {c['source']}",
                inline=False,
            )
    return embed, CharacteristicsView(character, owned)


class ConsumeCharacteristicSelect(discord.ui.Select):
    def __init__(self, owned: list):
        stored = [c for c in owned if c["state"] == "stored"]
        options = [
            discord.SelectOption(
                label=f"{c['name_vi']} (Sequence {c['sequence_number']})",
                value=str(c["id"]),
                description=f"Stability {c['stability']}% — Tiêu thụ để +5 Spirituality tối đa",
            )
            for c in stored
        ]
        super().__init__(placeholder="🧿 Tiêu thụ Characteristic", options=options, row=0)

    async def callback(self, interaction: discord.Interaction):
        character = db.get_character(str(interaction.user.id))
        try:
            result = char_engine.consume(character["character_id"], int(self.values[0]))
        except char_engine.CharacteristicError as e:
            await interaction.response.send_message(f"⚠️ {e}", ephemeral=True)
            return

        character = db.get_character(str(interaction.user.id))
        embed, view = build_characteristics_view(character)
        embed.add_field(
            name="Kết quả tiêu thụ",
            value=(
                f"✅ Đã tiêu thụ {result['characteristic']['name_vi']} — "
                f"Spirituality tối đa: {result['spirituality_max']}"
            ),
            inline=False,
        )
        await interaction.response.edit_message(embed=embed, view=view)


class CharacteristicsView(SafeView):
    def __init__(self, character: dict, owned: list):
        super().__init__(timeout=180)
        if any(c["state"] == "stored" for c in owned):
            self.add_item(ConsumeCharacteristicSelect(owned))
        self.add_item(BackButton(CharacterMenuView))


# ---------------------------------------------------------------------------
# 🧬 Con đường: Pathway -> Sequence (mục 54-56)
# ---------------------------------------------------------------------------

class PathwaySelect(discord.ui.Select):
    def __init__(self):
        pathways = db.list_pathways()
        options = [
            discord.SelectOption(
                label=p["name_vi"], value=p["pathway_id"],
                description=f"Title: {p['title_vi']}", emoji=p["icon"],
            )
            for p in pathways
        ]
        super().__init__(placeholder="🧬 Chọn Pathway", options=options, row=0)

    async def callback(self, interaction: discord.Interaction):
        pathway_id = self.values[0]
        pathway = db.get_pathway(pathway_id)
        character = db.get_character(str(interaction.user.id))

        if character and character.get("pathway_id") == pathway_id:
            current_sequence = character["sequence_number"]
        else:
            # Chưa đi theo Pathway này -> chỉ Sequence 9 là "điểm vào", còn lại khóa
            current_sequence = 9

        embed = discord.Embed(
            title=f"{pathway['icon']} {pathway['name_vi'].upper()} PATHWAY",
            description=f"Title: **{pathway['title_vi']}**\nSequence 9 → 0",
            color=discord.Color.dark_purple(),
        )
        view = SequenceSelectView(pathway_id, current_sequence)
        if character and character.get("pathway_id") is None:
            view.add_item(ChoosePathwayButton(pathway_id))
        await interaction.response.edit_message(embed=embed, view=view)


class PathwaySelectView(SafeView):
    def __init__(self):
        super().__init__(timeout=180)
        self.add_item(PathwaySelect())
        self.add_item(BackButton(MainMenuView))


class ChoosePathwayButton(discord.ui.Button):
    """Chỉ hiện khi Character CHƯA có Pathway nào — đây là lựa chọn ban đầu
    (mục 6), khác với Advancement (mục 12) vốn phải qua Potion/Digestion/Ritual."""

    def __init__(self, pathway_id: str):
        super().__init__(label="Nhận Pathway này (Sequence 9)", emoji="🧬", style=discord.ButtonStyle.success, row=1)
        self.pathway_id = pathway_id

    async def callback(self, interaction: discord.Interaction):
        character = db.get_character(str(interaction.user.id))
        if character is None:
            await interaction.response.send_message("Bạn chưa có nhân vật.", ephemeral=True)
            return
        if character["pathway_id"] is not None:
            await interaction.response.send_message(
                "Nhân vật đã có Pathway rồi — không thể đổi trực tiếp.", ephemeral=True
            )
            return
        db.set_character_pathway(character["character_id"], self.pathway_id, 9)
        character = db.get_character(str(interaction.user.id))
        embed = build_character_embed(character)
        await interaction.response.edit_message(embed=embed, view=SequenceSelectView(self.pathway_id, 9))


class SequenceSelect(discord.ui.Select):
    """Chỉ hiển thị thông tin. Sequence chưa đạt bị khóa — không có cách
    nào từ đây để tự set Sequence (mục 12, 54): chọn ô khóa chỉ hiện thông báo."""

    def __init__(self, pathway_id: str, current_sequence: int | None):
        sequences = db.list_sequences(pathway_id)
        options = []
        for s in sequences:
            unlocked = current_sequence is not None and s["sequence_number"] >= current_sequence
            label = f"{s['sequence_number']} — {s['name_vi']}"
            emoji = None if unlocked else "🔒"
            options.append(
                discord.SelectOption(
                    label=label,
                    value=str(s["sequence_number"]),
                    description="Đã đạt" if unlocked else "Chưa đạt — bị khóa",
                    emoji=emoji,
                )
            )
        super().__init__(placeholder="🔢 Chọn Sequence", options=options, row=0)
        self.pathway_id = pathway_id
        self.current_sequence = current_sequence

    async def callback(self, interaction: discord.Interaction):
        chosen = int(self.values[0])
        pathway = db.get_pathway(self.pathway_id)
        sequences = {s["sequence_number"]: s["name_vi"] for s in db.list_sequences(self.pathway_id)}

        unlocked = self.current_sequence is not None and chosen >= self.current_sequence
        if not unlocked:
            embed = discord.Embed(
                title=f"🔒 Sequence {chosen} — {sequences[chosen]}",
                description=(
                    "Nhân vật chưa đạt tới Sequence này.\n"
                    "Tiến cấp phải đi qua: Potion → Adaptation → Acting → "
                    "Digestion → Nghi thức → Tiến cấp."
                ),
                color=discord.Color.dark_grey(),
            )
        else:
            embed = discord.Embed(
                title=f"🔢 SEQUENCE {chosen} — {sequences[chosen]}",
                color=discord.Color.purple(),
            )
            embed.add_field(name=f"{ICONS['pathway']} Pathway", value=pathway["name_vi"], inline=True)

            character = db.get_character(str(interaction.user.id))
            is_current = (
                character and character["pathway_id"] == self.pathway_id
                and character["sequence_number"] == chosen
            )
            if is_current:
                # Đây là Sequence CHÍNH nhân vật đang đứng -> hiện tiến độ Digestion thật
                progress, potion = prog.get_state(character)
                potion_next = db.get_potion(self.pathway_id, chosen - 1) if chosen > 0 else None
                embed.add_field(
                    name=f"{ICONS['potion']} Potion đang dùng",
                    value=potion["name_vi"] if potion else "Chưa uống",
                    inline=True,
                )
                bar = "█" * (progress["digestion"] // 10) + "░" * (10 - progress["digestion"] // 10)
                embed.add_field(
                    name=f"{ICONS['digestion']} Digestion",
                    value=f"{progress['digestion']}%\n{bar}",
                    inline=True,
                )
                embed.set_footer(text="Vào 🎒 Tài sản → 🧪 Ma dược để Uống Potion / Thực hành / Làm Nghi thức.")
            else:
                embed.add_field(name=f"{ICONS['potion']} Potion", value=f"{sequences[chosen]} Potion", inline=True)
                embed.add_field(name=f"{ICONS['digestion']} Digestion", value="—", inline=True)
            ability = db.get_ability(f"{self.pathway_id}_{chosen}")
            if ability:
                embed.add_field(
                    name=f"{ICONS['ability']} Ability",
                    value=(
                        f"**{ability['name_vi']}**\n"
                        f"Cost: {ability['cost']} Spirituality · "
                        f"Damage x{ability['damage_multiplier']}"
                    ),
                    inline=False,
                )
            else:
                embed.add_field(name=f"{ICONS['ability']} Abilities", value="Chưa có Ability nào ở Sequence này.", inline=False)

        await interaction.response.edit_message(
            embed=embed, view=SequenceSelectView(self.pathway_id, self.current_sequence)
        )


class SequenceSelectView(SafeView):
    def __init__(self, pathway_id: str, current_sequence: int):
        super().__init__(timeout=180)
        self.add_item(SequenceSelect(pathway_id, current_sequence))
        self.add_item(BackButton(PathwaySelectView))


# ---------------------------------------------------------------------------
# 🎒 Tài sản (mục 59)
# ---------------------------------------------------------------------------

class InventoryMenuSelect(discord.ui.Select):
    OPTIONS = [
        ("bag", "Túi đồ", "🎒"),
        ("potion", "Ma dược", "🧪"),
        ("artifact", "Vật phẩm thần kỳ", "🕯️"),
        ("characteristic", "Beyonder Characteristic", "🧬"),
        ("equipment", "Trang bị", "⚔️"),
    ]

    def __init__(self):
        options = [
            discord.SelectOption(label=label, value=key, emoji=icon)
            for key, label, icon in self.OPTIONS
        ]
        super().__init__(placeholder="🎒 Chọn chức năng", options=options, row=0)

    async def callback(self, interaction: discord.Interaction):
        key = self.values[0]
        character = db.get_character(str(interaction.user.id))

        if key == "potion":
            embed, view = build_potion_view(character)
            await interaction.response.edit_message(embed=embed, view=view)
            return
        if key == "bag":
            embed, view = build_bag_view(character)
            await interaction.response.edit_message(embed=embed, view=view)
            return
        if key == "equipment":
            embed, view = build_equipment_view(character)
            await interaction.response.edit_message(embed=embed, view=view)
            return
        if key == "artifact":
            embed, view = build_artifact_list_view(character)
            await interaction.response.edit_message(embed=embed, view=view)
            return

        label = next(l for k, l, i in self.OPTIONS if k == key)
        icon = next(i for k, l, i in self.OPTIONS if k == key)
        await interaction.response.edit_message(
            embed=build_stub_embed(label, icon), view=InventoryMenuView()
        )


class InventoryMenuView(SafeView):
    def __init__(self):
        super().__init__(timeout=180)
        self.add_item(InventoryMenuSelect())
        self.add_item(BackButton(MainMenuView))


# ---------------------------------------------------------------------------
# 🕯️ Vật phẩm thần kỳ — Sealed Artifact (mục 22): Inspect/Experiment thật,
# Effect/Side Effect đi qua EffectEngine, không có số liệu hiển thị giả.
# ---------------------------------------------------------------------------

def build_artifact_list_view(character: dict):
    icon = ICONS["artifact"]
    if character is None:
        return build_stub_embed("Vật phẩm thần kỳ", icon), SimpleBackView(InventoryMenuView)

    owned = artifact_engine.list_owned(character["character_id"])
    embed = discord.Embed(title=f"{icon} VẬT PHẨM THẦN KỲ", color=discord.Color.dark_purple())
    if not owned:
        embed.description = "Bạn chưa sở hữu Sealed Artifact nào."
    else:
        for o in owned:
            known = [s for s in o["discovered_stages"].split(",") if s]
            uses = "Vô hạn" if o["uses_remaining"] == -1 else str(o["uses_remaining"])
            embed.add_field(
                name=f"{o['name_vi']} (#{o['id']}) — {'★' * o['risk_stars']}",
                value=f"Grade: {o['grade']} | Đã khám phá: {len(known)}/3 | Lượt dùng còn: {uses}",
                inline=False,
            )
    return embed, ArtifactListView(character, owned)


class ArtifactSelect(discord.ui.Select):
    def __init__(self, owned: list):
        options = [
            discord.SelectOption(
                label=f"{o['name_vi']} (#{o['id']})",
                value=str(o["id"]),
                description=f"{o['grade']} · {'★' * o['risk_stars']}"[:100],
            )
            for o in owned
        ]
        super().__init__(placeholder="🕯️ Chọn Vật phẩm thần kỳ", options=options, row=0)

    async def callback(self, interaction: discord.Interaction):
        character = db.get_character(str(interaction.user.id))
        ca_id = int(self.values[0])
        embed, view = build_artifact_detail_view(character, ca_id)
        await interaction.response.edit_message(embed=embed, view=view)


class ArtifactListView(SafeView):
    def __init__(self, character: dict, owned: list):
        super().__init__(timeout=180)
        if owned:
            self.add_item(ArtifactSelect(owned))
        self.add_item(BackButton(InventoryMenuView))


def build_artifact_detail_view(character: dict, character_artifact_id: int):
    ca = db.get_character_artifact(character_artifact_id)
    artifact = db.get_artifact(ca["artifact_id"])
    known = {s for s in ca["discovered_stages"].split(",") if s}
    rules = artifact_engine.get_rules_text(artifact["artifact_id"])

    embed = discord.Embed(title=f"{ICONS['artifact']} {artifact['name_en']}", color=discord.Color.dark_purple())
    if not known:
        embed.description = f"❓ {artifact['inspect_hint']}"
    embed.add_field(name="Grade", value=artifact["grade"].capitalize(), inline=True)
    embed.add_field(name="Risk", value="★" * artifact["risk_stars"], inline=True)
    uses = "Vô hạn" if ca["uses_remaining"] == -1 else str(ca["uses_remaining"])
    embed.add_field(name="Lượt dùng còn lại", value=uses, inline=True)
    embed.add_field(name="Sealing Method", value=artifact["sealing_method"], inline=False)
    for stage, label in (("effect", "🔹 Effect"), ("rule", "📏 Rule"), ("side_effect", "⚠️ Side Effect")):
        value = rules.get(stage, "—") if stage in known else "❓ Chưa khám phá — Inspect hoặc Experiment để biết thêm."
        embed.add_field(name=label, value=value, inline=False)

    return embed, ArtifactDetailView(character, character_artifact_id)


class InspectButton(discord.ui.Button):
    def __init__(self, character_artifact_id: int):
        super().__init__(label="Quan sát", emoji="🔍", style=discord.ButtonStyle.secondary, row=0)
        self.character_artifact_id = character_artifact_id

    async def callback(self, interaction: discord.Interaction):
        character = db.get_character(str(interaction.user.id))
        try:
            result = artifact_engine.inspect(character["character_id"], self.character_artifact_id)
        except artifact_engine.ArtifactError as e:
            await interaction.response.send_message(f"⚠️ {e}", ephemeral=True)
            return
        embed, view = build_artifact_detail_view(character, self.character_artifact_id)
        if result["stage"] is None:
            embed.add_field(name="Kết quả", value="Bạn đã biết hết mọi thứ có thể Quan sát được.", inline=False)
        else:
            embed.add_field(name="Kết quả", value=f"✅ Vừa khám phá thêm: **{result['stage']}**", inline=False)
        await interaction.response.edit_message(embed=embed, view=view)


class ExperimentButton(discord.ui.Button):
    def __init__(self, character_artifact_id: int):
        super().__init__(label="Thực nghiệm", emoji="⚗️", style=discord.ButtonStyle.danger, row=0)
        self.character_artifact_id = character_artifact_id

    async def callback(self, interaction: discord.Interaction):
        character = db.get_character(str(interaction.user.id))
        try:
            result = artifact_engine.experiment(character["character_id"], self.character_artifact_id)
        except artifact_engine.ArtifactError as e:
            await interaction.response.send_message(f"⚠️ {e}", ephemeral=True)
            return
        embed, view = build_artifact_detail_view(character, self.character_artifact_id)
        note = "⚠️ Side Effect đã kích hoạt!" if result["side_effect_triggered"] else "Không có Side Effect lần này."
        embed.add_field(name="Kết quả", value=f"✅ Đã áp dụng Effect thật lên nhân vật. {note}", inline=False)
        await interaction.response.edit_message(embed=embed, view=view)


class ArtifactDetailView(SafeView):
    def __init__(self, character: dict, character_artifact_id: int):
        super().__init__(timeout=180)
        self.add_item(InspectButton(character_artifact_id))
        self.add_item(ExperimentButton(character_artifact_id))
        self.add_item(BackButton(InventoryMenuView))


# ---------------------------------------------------------------------------
# 🎒 Túi đồ — dùng Consumable thật (mục 59)
# ---------------------------------------------------------------------------

def build_bag_view(character: dict):
    items = inv.list_inventory(character["character_id"]) if character else []
    embed = discord.Embed(title=f"{ICONS['inventory']} TÚI ĐỒ", color=discord.Color.dark_gold())
    if not items:
        embed.description = "Túi đồ trống."
    else:
        lines = []
        for it in items:
            tag = {"consumable": "🧪", "equipment": "⚔️", "material": "🔹"}.get(it["type"], "•")
            lines.append(f"{tag} **{it['name_vi']}** ×{it['quantity']} — {it['description']}")
        embed.description = "\n".join(lines)
    return embed, BagActionsView(character, items)


class UseItemSelect(discord.ui.Select):
    def __init__(self, consumables: list):
        options = [
            discord.SelectOption(label=f"{it['name_vi']} (×{it['quantity']})", value=it["item_id"])
            for it in consumables
        ]
        super().__init__(placeholder="🧪 Dùng vật phẩm", options=options, row=0)

    async def callback(self, interaction: discord.Interaction):
        character = db.get_character(str(interaction.user.id))
        try:
            item, new_hp, new_sp = inv.use_item(character, self.values[0])
        except inv.InventoryError as e:
            await interaction.response.send_message(f"⚠️ {e}", ephemeral=True)
            return
        character = db.get_character(str(interaction.user.id))
        embed, view = build_bag_view(character)
        embed.add_field(
            name="Kết quả",
            value=f"✅ Đã dùng {item['name_vi']}. HP: {new_hp}/{character['hp_max']} · "
                  f"Spirituality: {new_sp}/{character['spirituality_max']}",
            inline=False,
        )
        await interaction.response.edit_message(embed=embed, view=view)


class BagActionsView(SafeView):
    def __init__(self, character: dict, items: list):
        super().__init__(timeout=180)
        consumables = [it for it in items if it["type"] == "consumable"]
        if consumables:
            self.add_item(UseItemSelect(consumables))
        self.add_item(BackButton(InventoryMenuView))


# ---------------------------------------------------------------------------
# ⚔️ Trang bị — equip/unequip thật qua EffectEngine (mục 59)
# ---------------------------------------------------------------------------

def build_equipment_view(character: dict):
    equipped = inv.get_equipped_items(character)
    embed = discord.Embed(title="⚔️ TRANG BỊ", color=discord.Color.dark_gold())
    for slot in ("weapon", "armor"):
        item = equipped.get(slot)
        label = "Vũ khí" if slot == "weapon" else "Giáp"
        embed.add_field(
            name=label,
            value=f"{item['name_vi']} ({item['modifier_key']} {item['modifier_value']:+g}%)" if item else "Trống",
            inline=True,
        )
    return embed, EquipmentActionsView(character, equipped)


class EquipSelect(discord.ui.Select):
    def __init__(self, equippable: list):
        options = [
            discord.SelectOption(label=f"{it['name_vi']} ({it['equip_slot']})", value=it["item_id"])
            for it in equippable
        ]
        super().__init__(placeholder="⚔️ Trang bị vật phẩm", options=options, row=0)

    async def callback(self, interaction: discord.Interaction):
        character = db.get_character(str(interaction.user.id))
        try:
            item = inv.equip_item(character, self.values[0])
        except inv.InventoryError as e:
            await interaction.response.send_message(f"⚠️ {e}", ephemeral=True)
            return
        character = db.get_character(str(interaction.user.id))
        embed, view = build_equipment_view(character)
        embed.add_field(name="Kết quả", value=f"✅ Đã trang bị {item['name_vi']}.", inline=False)
        await interaction.response.edit_message(embed=embed, view=view)


class UnequipButton(discord.ui.Button):
    def __init__(self, slot: str, label: str):
        super().__init__(label=f"Gỡ {label}", style=discord.ButtonStyle.secondary, row=1)
        self.slot = slot

    async def callback(self, interaction: discord.Interaction):
        character = db.get_character(str(interaction.user.id))
        try:
            inv.unequip_item(character, self.slot)
        except inv.InventoryError as e:
            await interaction.response.send_message(f"⚠️ {e}", ephemeral=True)
            return
        character = db.get_character(str(interaction.user.id))
        embed, view = build_equipment_view(character)
        await interaction.response.edit_message(embed=embed, view=view)


class EquipmentActionsView(SafeView):
    def __init__(self, character: dict, equipped: dict):
        super().__init__(timeout=180)
        items = inv.list_inventory(character["character_id"])
        equipped_item_ids = {item["item_id"] for item in equipped.values() if item}
        equippable = [
            it for it in items
            if it["type"] == "equipment" and it["item_id"] not in equipped_item_ids
        ]
        if equippable:
            self.add_item(EquipSelect(equippable))
        if "weapon" in equipped:
            self.add_item(UnequipButton("weapon", "Vũ khí"))
        if "armor" in equipped:
            self.add_item(UnequipButton("armor", "Giáp"))
        self.add_item(BackButton(InventoryMenuView))


def build_potion_view(character: dict):
    """Dựng embed + view thật cho 🧪 Ma dược, dựa trên progression.py."""
    if character is None or character["pathway_id"] is None:
        embed = discord.Embed(
            title=f"{ICONS['potion']} MA DƯỢC",
            description="Nhân vật cần có Pathway trước (vào 🧬 Con đường).",
            color=discord.Color.dark_grey(),
        )
        return embed, PotionActionsView(character, progress=None)

    progress, potion = prog.get_state(character)
    pathway = db.get_pathway(character["pathway_id"])

    embed = discord.Embed(title=f"{ICONS['potion']} MA DƯỢC", color=discord.Color.purple())
    embed.add_field(name="Pathway", value=f"{pathway['icon']} {pathway['name_vi']}", inline=True)
    embed.add_field(name="Sequence hiện tại", value=str(character["sequence_number"]), inline=True)
    embed.add_field(
        name="Potion đang dùng",
        value=potion["name_vi"] if potion else "Chưa uống (idle)",
        inline=False,
    )
    bar = "█" * (progress["digestion"] // 10) + "░" * (10 - progress["digestion"] // 10)
    embed.add_field(name=f"{ICONS['digestion']} Digestion", value=f"{progress['digestion']}%\n{bar}", inline=False)

    if progress["status"] == "idle" and character["sequence_number"] > 0:
        target_sequence = character["sequence_number"] - 1
        target_potion = db.get_potion(character["pathway_id"], target_sequence)
        stock = potions_engine.get_stock(character, target_sequence)
        recipe = db.get_potion_recipe(character["pathway_id"], target_sequence)
        recipe_lines = [
            f"• {r['name_vi']} x{r['quantity']} (có: {db.get_inventory_quantity(character['character_id'], r['item_id'])})"
            for r in recipe
        ]
        embed.add_field(
            name=f"🧪 Công thức: {target_potion['name_vi'] if target_potion else '???'}",
            value=(
                "\n".join(recipe_lines) if recipe_lines else "Chưa có công thức."
            ) + f"\n\nĐang sở hữu: {stock} | Tỉ lệ hỏng khi Chế tạo: {target_potion['craft_risk']}%"
            if target_potion else "Chưa có dữ liệu.",
            inline=False,
        )

    if progress["status"] == "ready" and potion:
        materials = ritual_engine.get_materials(character["pathway_id"], progress["potion_target_sequence"])
        material_lines = [
            f"• {m['name_vi']} x{m['quantity']} (có: {db.get_inventory_quantity(character['character_id'], m['item_id'])})"
            for m in materials
        ]
        chance = ritual_engine.compute_success_chance(character, potion)
        embed.add_field(
            name=f"{ICONS['ritual']} Vật liệu Nghi thức",
            value=(
                ("\n".join(material_lines) if material_lines else "Chưa có dữ liệu vật liệu.")
                + f"\n\nTỉ lệ thành công ước tính: **{chance}%** "
                "(Potion stability + Characteristic − Loss of Control Risk)"
            ),
            inline=False,
        )

    active_effects = effects.list_active_effects(character["character_id"])
    if active_effects:
        lines = [f"{'🟢' if e['type']=='buff' else '🔴'} {e['name_en']} ({e['duration']} lượt)" for e in active_effects]
        embed.add_field(name="Hiệu ứng đang active", value="\n".join(lines), inline=False)

    return embed, PotionActionsView(character, progress)


class CraftPotionButton(discord.ui.Button):
    def __init__(self):
        super().__init__(label="Chế tạo", emoji="⚗️", style=discord.ButtonStyle.secondary, row=1)

    async def callback(self, interaction: discord.Interaction):
        character = db.get_character(str(interaction.user.id))
        target_sequence = character["sequence_number"] - 1
        try:
            result = potions_engine.craft_potion(character, target_sequence)
        except potions_engine.CraftError as e:
            await interaction.response.send_message(f"⚠️ {e}", ephemeral=True)
            return

        character = db.get_character(str(interaction.user.id))
        embed, view = build_potion_view(character)
        if result["success"]:
            note = f"✅ Chế tạo thành công: {result['potion']['name_vi']}"
        else:
            note = (
                f"☠️ Chế tạo thất bại — {result['potion']['name_vi']} hỏng, "
                "mất nguyên liệu và dính Potion Instability."
            )
        embed.add_field(name="Kết quả Chế tạo", value=note, inline=False)
        await interaction.response.edit_message(embed=embed, view=view)


class DrinkPotionButton(discord.ui.Button):
    def __init__(self):
        super().__init__(label="Uống Potion", emoji="🧪", style=discord.ButtonStyle.primary, row=1)

    async def callback(self, interaction: discord.Interaction):
        character = db.get_character(str(interaction.user.id))
        try:
            prog.start_potion(character)
        except prog.ProgressionError as e:
            await interaction.response.send_message(f"⚠️ {e}", ephemeral=True)
            return
        character = db.get_character(str(interaction.user.id))
        embed, view = build_potion_view(character)
        await interaction.response.edit_message(embed=embed, view=view)


class ActingActionSelect(discord.ui.Select):
    def __init__(self, pathway_id: str):
        from data.acting_actions import get_actions

        actions = get_actions(pathway_id)
        options = [
            discord.SelectOption(label=f"{label} (+{gain}%)", value=key)
            for key, label, gain in actions
        ]
        super().__init__(placeholder="🎭 Thực hành Acting Method", options=options, row=2)

    async def callback(self, interaction: discord.Interaction):
        character = db.get_character(str(interaction.user.id))
        try:
            new_digestion, status, label = prog.perform_acting(character, self.values[0])
        except prog.ProgressionError as e:
            await interaction.response.send_message(f"⚠️ {e}", ephemeral=True)
            return

        character = db.get_character(str(interaction.user.id))
        embed, view = build_potion_view(character)
        note = f"✅ {label}: Digestion +{new_digestion}%"
        if status == "ready":
            note += "\n🔔 Digestion đã đạt 100% — có thể làm Nghi thức tiến cấp!"
        embed.add_field(name="Kết quả", value=note, inline=False)
        await interaction.response.edit_message(embed=embed, view=view)


class AdvancementButton(discord.ui.Button):
    def __init__(self):
        super().__init__(label="Làm Nghi thức tiến cấp", emoji="📜", style=discord.ButtonStyle.danger, row=1)

    async def callback(self, interaction: discord.Interaction):
        character = db.get_character(str(interaction.user.id))
        try:
            result = prog.perform_advancement(character)
        except prog.ProgressionError as e:
            await interaction.response.send_message(f"⚠️ {e}", ephemeral=True)
            return

        character = db.get_character(str(interaction.user.id))
        embed, view = build_potion_view(character)
        color_note = "✅" if result["success"] else "☠️"
        embed.add_field(name="Kết quả Nghi thức", value=f"{color_note} {result['message']}", inline=False)
        if result["success"]:
            embed.add_field(name="Sequence mới", value=str(result["new_sequence"]), inline=False)
            gained = result.get("characteristic")
            if gained:
                embed.add_field(
                    name=f"{ICONS['characteristic']} Beyonder Characteristic mới",
                    value=gained["name_vi"],
                    inline=False,
                )
        incident = result.get("incident")
        if incident:
            embed.add_field(
                name=f"☠️ Mất kiểm soát ({incident['severity_label_vi']})",
                value="\n".join(incident["effects"]),
                inline=False,
            )
        embed.add_field(name="📖 Diễn giải", value=result["narrative"], inline=False)
        await interaction.response.edit_message(embed=embed, view=view)


class PotionActionsView(SafeView):
    def __init__(self, character: dict, progress: dict | None):
        super().__init__(timeout=180)
        if character and character.get("pathway_id") and progress is not None:
            if progress["status"] == "idle":
                self.add_item(CraftPotionButton())
                self.add_item(DrinkPotionButton())
            elif progress["status"] == "digesting":
                self.add_item(ActingActionSelect(character["pathway_id"]))
            elif progress["status"] == "ready":
                self.add_item(AdvancementButton())
        self.add_item(BackButton(InventoryMenuView))


# ---------------------------------------------------------------------------
# ⚔️ Chiến đấu — PvE thật (mục 25, 60)
# ---------------------------------------------------------------------------

class CombatMenuSelect(discord.ui.Select):
    OPTIONS = [
        ("pve", "pve", "PvE", "👹"),
        ("pvp", "pvp", "PvP", "🏟️"),
        ("dungeon", "dungeon", "Dungeon", "🏰"),
        ("boss", "boss", "Boss", "👑"),
        ("arena", "arena", "Arena", "🏆"),
    ]

    def __init__(self, lang: str = None):
        self.lang = lang
        options = [
            discord.SelectOption(label=i18n.t(f"combat_menu.{i18n_key}", lang, default=l), value=k, emoji=i)
            for k, i18n_key, l, i in self.OPTIONS
        ]
        super().__init__(
            placeholder=f"⚔️ {i18n.t('combat_menu.placeholder', lang)}", options=options, row=0,
        )

    async def callback(self, interaction: discord.Interaction):
        key = self.values[0]
        lang = self.lang or i18n.user_lang(str(interaction.user.id))
        if key == "pve":
            embed = discord.Embed(
                title=f"👹 {i18n.t('combat_menu.pve_title', lang)}",
                description=i18n.t("combat_menu.pve_description", lang),
                color=discord.Color.dark_red(),
            )
            await interaction.response.edit_message(embed=embed, view=MonsterSelectView())
            return
        if key == "pvp":
            character = db.get_character(str(interaction.user.id))
            if character is None:
                await interaction.response.send_message(f"⚠️ {i18n.t('common.no_character', lang)}", ephemeral=True)
                return
            embed, view = build_pvp_hub(character)
            await interaction.response.edit_message(embed=embed, view=view)
            return
        if key == "dungeon":
            character = db.get_character(str(interaction.user.id))
            if character is None:
                await interaction.response.send_message(f"⚠️ {i18n.t('common.no_character', lang)}", ephemeral=True)
                return
            embed, view = build_dungeon_hub(character)
            await interaction.response.edit_message(embed=embed, view=view)
            return
        label = i18n.t(f"combat_menu.{next(ik for k, ik, l, i in self.OPTIONS if k == key)}", lang,
                        default=next(l for k, ik, l, i in self.OPTIONS if k == key))
        icon = next(i for k, ik, l, i in self.OPTIONS if k == key)
        await interaction.response.edit_message(embed=build_stub_embed(label, icon), view=CombatMenuView(lang))


class CombatMenuView(SafeView):
    def __init__(self, lang: str = None):
        super().__init__(timeout=180)
        self.add_item(CombatMenuSelect(lang))
        self.add_item(BackButton(MainMenuView))



class MonsterSelect(discord.ui.Select):
    def __init__(self):
        monsters = db.list_monsters()
        options = [
            discord.SelectOption(
                label=m["name_en"], value=m["monster_id"],
                description=f"HP {m['hp']} · ATK {m['attack']} · Thưởng {m['reward_money']} Bảng",
                emoji="👹",
            )
            for m in monsters
        ]
        super().__init__(placeholder="👹 Chọn Monster", options=options, row=0)

    async def callback(self, interaction: discord.Interaction):
        character = db.get_character(str(interaction.user.id))
        if character is None:
            await interaction.response.send_message("Bạn chưa có nhân vật.", ephemeral=True)
            return
        try:
            session, monster = combat.start_pve(character, self.values[0])
        except combat.CombatError as e:
            await interaction.response.send_message(f"⚠️ {e}", ephemeral=True)
            return
        embed = build_combat_embed(character, session, monster)
        await interaction.response.edit_message(embed=embed, view=CombatActionsView(character))


class MonsterSelectView(SafeView):
    def __init__(self):
        super().__init__(timeout=180)
        self.add_item(MonsterSelect())
        self.add_item(BackButton(CombatMenuView))


def build_combat_embed(character: dict, session: dict, monster: dict, last_result: dict = None) -> discord.Embed:
    embed = discord.Embed(title=f"⚔️ {monster['name_en']}", color=discord.Color.dark_red())
    p_bar_len = 10
    p_filled = max(0, round(session["player_hp"] / character["hp_max"] * p_bar_len))
    m_filled = max(0, round(session["monster_hp"] / monster["hp"] * p_bar_len))
    embed.add_field(
        name=f"{ICONS['hp']} Bạn",
        value=f"{session['player_hp']} / {character['hp_max']}\n" + "🟩" * p_filled + "⬛" * (p_bar_len - p_filled),
        inline=True,
    )
    embed.add_field(
        name=f"👹 {monster['name_en']}",
        value=f"{session['monster_hp']} / {monster['hp']}\n" + "🟥" * m_filled + "⬛" * (p_bar_len - m_filled),
        inline=True,
    )
    active = effects.list_active_effects(character["character_id"])
    if active:
        embed.add_field(
            name="Hiệu ứng",
            value="\n".join(f"{'🟢' if e['type']=='buff' else '🔴'} {e['name_en']}" for e in active),
            inline=False,
        )
    if last_result:
        lines = [f"**{last_result['action_label']}**"]
        if last_result.get("player_dealt"):
            lines.append(f"Bạn gây {last_result['player_dealt']} sát thương.")
        if last_result.get("counter_damage"):
            lines.append(f"{monster['name_en']} phản đòn {last_result['counter_damage']} sát thương.")
        if last_result["status"] == "victory":
            lines.append(f"🏆 Thắng! +{last_result['reward_money']} Bảng, +{last_result['reward_exp']} EXP.")
            if last_result.get("party_rewarded_count"):
                lines.append(f"👥 {last_result['party_rewarded_count']} đồng đội cùng địa điểm đã nhận chia sẻ thưởng.")
        elif last_result["status"] == "defeat":
            lines.append(f"☠️ Thua trận! Tiền phạt {last_result['money_penalty']} Bảng, HP về 1.")
        elif last_result["status"] == "fled":
            lines.append("🏃 Rút lui thành công.")
        embed.add_field(name="Kết quả lượt", value="\n".join(lines), inline=False)
    return embed


class AttackButton(discord.ui.Button):
    def __init__(self):
        super().__init__(label="Tấn công", emoji="⚔️", style=discord.ButtonStyle.danger, row=1)

    async def callback(self, interaction: discord.Interaction):
        character = db.get_character(str(interaction.user.id))
        session = db.get_active_combat_session(character["character_id"])
        if session is None:
            await interaction.response.send_message("Không có trận nào đang diễn ra.", ephemeral=True)
            return
        monster = db.get_monster(session["monster_id"])
        result = combat.perform_attack(character, session)
        await _render_combat_turn(interaction, result, monster)


class DefendButton(discord.ui.Button):
    def __init__(self):
        super().__init__(label="Phòng thủ", emoji="🛡️", style=discord.ButtonStyle.secondary, row=1)

    async def callback(self, interaction: discord.Interaction):
        character = db.get_character(str(interaction.user.id))
        session = db.get_active_combat_session(character["character_id"])
        if session is None:
            await interaction.response.send_message("Không có trận nào đang diễn ra.", ephemeral=True)
            return
        monster = db.get_monster(session["monster_id"])
        result = combat.perform_defend(character, session)
        await _render_combat_turn(interaction, result, monster)


class FleeButton(discord.ui.Button):
    def __init__(self):
        super().__init__(label="Rút lui", emoji="🏃", style=discord.ButtonStyle.secondary, row=1)

    async def callback(self, interaction: discord.Interaction):
        character = db.get_character(str(interaction.user.id))
        session = db.get_active_combat_session(character["character_id"])
        if session is None:
            await interaction.response.send_message("Không có trận nào đang diễn ra.", ephemeral=True)
            return
        monster = db.get_monster(session["monster_id"])
        result = combat.perform_flee(character, session)
        await _render_combat_turn(interaction, result, monster)


class AbilitySelect(discord.ui.Select):
    def __init__(self, pathway_id: str, current_sequence: int):
        abilities = db.list_unlocked_abilities(pathway_id, current_sequence)
        if not abilities:
            abilities_options = [discord.SelectOption(label="Chưa có Ability nào mở khóa", value="none")]
        else:
            abilities_options = [
                discord.SelectOption(
                    label=f"{a['name_vi']} (Spirituality {a['cost']})",
                    value=a["ability_id"],
                )
                for a in abilities
            ]
        super().__init__(placeholder="✨ Dùng Ability", options=abilities_options, row=2)

    async def callback(self, interaction: discord.Interaction):
        if self.values[0] == "none":
            await interaction.response.send_message("Chưa có Ability nào để dùng.", ephemeral=True)
            return
        character = db.get_character(str(interaction.user.id))
        session = db.get_active_combat_session(character["character_id"])
        if session is None:
            await interaction.response.send_message("Không có trận nào đang diễn ra.", ephemeral=True)
            return
        monster = db.get_monster(session["monster_id"])
        try:
            result = combat.perform_ability(character, session, self.values[0])
        except combat.CombatError as e:
            await interaction.response.send_message(f"⚠️ {e}", ephemeral=True)
            return
        await _render_combat_turn(interaction, result, monster)


async def _render_combat_turn(interaction: discord.Interaction, result: dict, monster: dict):
    character = db.get_character(str(interaction.user.id))
    if result["status"] == "ongoing":
        session = db.get_active_combat_session(character["character_id"])
        embed = build_combat_embed(character, session, monster, last_result=result)
        await interaction.response.edit_message(embed=embed, view=CombatActionsView(character))
    else:
        fake_session = {"player_hp": result["player_hp"], "monster_hp": result.get("monster_hp", 0)}
        embed = build_combat_embed(character, fake_session, monster, last_result=result)
        await interaction.response.edit_message(embed=embed, view=SimpleBackView(CombatMenuView))


class CombatActionsView(SafeView):
    def __init__(self, character: dict):
        super().__init__(timeout=180)
        self.add_item(AttackButton())
        self.add_item(DefendButton())
        self.add_item(FleeButton())
        if character.get("pathway_id"):
            self.add_item(AbilitySelect(character["pathway_id"], character["sequence_number"]))


# ---------------------------------------------------------------------------
# 🏰 Dungeon (mục 26) — procedural theo phòng, tái dùng CombatActionsView
# ---------------------------------------------------------------------------

def build_dungeon_hub(character: dict):
    icon = ICONS["dungeon"]
    run = dungeon.get_progress(character["character_id"])
    if run:
        return build_dungeon_room_embed_from_run(character, run)

    dungeons = dungeon.list_dungeons()
    embed = discord.Embed(title=f"{icon} DUNGEON", color=discord.Color.dark_purple())
    embed.description = "Chọn một Dungeon để khám phá. Mỗi phòng có thể là Chiến đấu, Kho báu, hoặc Cạm bẫy."
    for d in dungeons:
        embed.add_field(
            name=f"{d['name_vi']} ({d['room_count']} phòng)",
            value=f"{d['description_vi'][:150]}\nThưởng khi hạ Boss: {d['reward_money']:,} Bảng, {d['reward_exp']:,} EXP",
            inline=False,
        )
    return embed, DungeonSelectView(dungeons)


def build_dungeon_room_embed_from_run(character: dict, run: dict):
    """Người chơi có run active nhưng không có combat session đang chờ (vd
    vừa quay lại menu sau một phòng Event) — hiện trạng thái + nút tiếp tục."""
    session = db.get_active_combat_session(character["character_id"])
    if session and session.get("dungeon_run_id") == run["run_id"]:
        monster = db.get_monster(session["monster_id"])
        embed = build_combat_embed(character, session, monster)
        embed.set_footer(text=f"🏰 {run['dungeon']['name_vi']} — Phòng {run['current_room'] + 1}/{run['total_rooms']}")
        return embed, DungeonCombatActionsView(character)

    icon = ICONS["dungeon"]
    embed = discord.Embed(title=f"{icon} {run['dungeon']['name_vi']}", color=discord.Color.dark_purple())
    embed.description = f"Phòng {run['current_room'] + 1}/{run['total_rooms']}"
    if run["events"]:
        lines = [f"#{e['room_index'] + 1} — {e['result_vi']}" for e in run["events"][-5:]]
        embed.add_field(name="Diễn biến gần đây", value="\n".join(lines), inline=False)
    return embed, DungeonContinueView()


class DungeonSelect(discord.ui.Select):
    def __init__(self, dungeons: list):
        options = [
            discord.SelectOption(label=d["name_vi"], value=d["dungeon_id"], description=d["name_en"][:100])
            for d in dungeons
        ]
        super().__init__(placeholder=f"{ICONS['dungeon']} Chọn Dungeon", options=options, row=0)

    @error_handler.safe_interaction(lambda: CombatMenuView())
    async def callback(self, interaction: discord.Interaction):
        character = db.get_character(str(interaction.user.id))
        try:
            room = dungeon.enter_dungeon(character, self.values[0])
        except dungeon.DungeonError as e:
            await interaction.response.send_message(f"⚠️ {e}", ephemeral=True)
            return
        await _render_dungeon_room(interaction, room)


class DungeonSelectView(SafeView):
    def __init__(self, dungeons: list):
        super().__init__(timeout=180)
        self.add_item(DungeonSelect(dungeons))
        self.add_item(BackButton(CombatMenuView))


class DungeonContinueButton(discord.ui.Button):
    def __init__(self):
        super().__init__(label="Tiến vào phòng tiếp theo", emoji="🚪", style=discord.ButtonStyle.primary, row=1)

    @error_handler.safe_interaction(lambda: CombatMenuView())
    async def callback(self, interaction: discord.Interaction):
        character = db.get_character(str(interaction.user.id))
        try:
            room = dungeon.continue_run(character)
        except dungeon.DungeonError as e:
            await interaction.response.send_message(f"⚠️ {e}", ephemeral=True)
            return
        await _render_dungeon_room(interaction, room)


class DungeonContinueView(SafeView):
    def __init__(self):
        super().__init__(timeout=180)
        self.add_item(DungeonContinueButton())
        self.add_item(BackButton(CombatMenuView))


async def _render_dungeon_room(interaction: discord.Interaction, room: dict):
    character = db.get_character(str(interaction.user.id))
    if room["kind"] == "combat":
        embed = build_combat_embed(character, room["session"], room["monster"])
        title = "👑 PHÒNG BOSS" if room["room_type"] == "boss" else f"Phòng {room['room_index'] + 1}/{room['total_rooms']}"
        embed.set_footer(text=f"🏰 {title}")
        await interaction.response.edit_message(embed=embed, view=DungeonCombatActionsView(character))
        return

    icon = "🎁" if room["room_type"] == "treasure" else ("⚠️" if room["room_type"] == "trap" else "🔍")
    embed = discord.Embed(title=f"{icon} {room['name_vi']}", color=discord.Color.dark_purple())
    lines = []
    if room["money_delta"]:
        lines.append(f"{'+' if room['money_delta'] >= 0 else ''}{room['money_delta']:,} Bảng")
    if room["hp_delta"]:
        lines.append(f"{'+' if room['hp_delta'] >= 0 else ''}{room['hp_delta']} HP")
    embed.description = "\n".join(lines) if lines else "Không có gì xảy ra."
    embed.set_footer(text=f"Phòng {room['room_index'] + 1}/{room['total_rooms']}")
    await interaction.response.edit_message(embed=embed, view=DungeonContinueView())


async def _render_dungeon_combat_turn(interaction: discord.Interaction, result: dict, monster: dict):
    character = db.get_character(str(interaction.user.id))
    if result["status"] == "ongoing":
        session = db.get_active_combat_session(character["character_id"])
        embed = build_combat_embed(character, session, monster, last_result=result)
        await interaction.response.edit_message(embed=embed, view=DungeonCombatActionsView(character))
        return

    dungeon_result = result.get("dungeon_result") or {}
    status = dungeon_result.get("dungeon_status")
    fake_session = {"player_hp": result["player_hp"], "monster_hp": result.get("monster_hp", 0)}
    embed = build_combat_embed(character, fake_session, monster, last_result=result)

    if status == "cleared":
        d = dungeon_result["dungeon"]
        embed.add_field(
            name="🏆 DUNGEON HOÀN THÀNH",
            value=f"**{d['name_vi']}** — Thưởng tổng: {d['reward_money']:,} Bảng, {d['reward_exp']:,} EXP"
                  + (f", nhận được {d['reward_item_id']}" if d.get("reward_item_id") else ""),
            inline=False,
        )
        await interaction.response.edit_message(embed=embed, view=SimpleBackView(CombatMenuView))
    elif status == "room_cleared":
        embed.add_field(name="✅ Đã dọn sạch phòng", value="Bạn có thể tiến vào phòng tiếp theo.", inline=False)
        await interaction.response.edit_message(embed=embed, view=DungeonContinueView())
    else:
        embed.add_field(name="☠️ DUNGEON THẤT BẠI", value="Lượt khám phá Dungeon này đã kết thúc.", inline=False)
        await interaction.response.edit_message(embed=embed, view=SimpleBackView(CombatMenuView))


class DungeonAttackButton(discord.ui.Button):
    def __init__(self):
        super().__init__(label="Tấn công", emoji="⚔️", style=discord.ButtonStyle.danger, row=1)

    @error_handler.safe_interaction(lambda: CombatMenuView())
    async def callback(self, interaction: discord.Interaction):
        character = db.get_character(str(interaction.user.id))
        session = db.get_active_combat_session(character["character_id"])
        if session is None:
            await interaction.response.send_message("Không có trận nào đang diễn ra.", ephemeral=True)
            return
        monster = db.get_monster(session["monster_id"])
        result = combat.perform_attack(character, session)
        await _render_dungeon_combat_turn(interaction, result, monster)


class DungeonDefendButton(discord.ui.Button):
    def __init__(self):
        super().__init__(label="Phòng thủ", emoji="🛡️", style=discord.ButtonStyle.secondary, row=1)

    @error_handler.safe_interaction(lambda: CombatMenuView())
    async def callback(self, interaction: discord.Interaction):
        character = db.get_character(str(interaction.user.id))
        session = db.get_active_combat_session(character["character_id"])
        if session is None:
            await interaction.response.send_message("Không có trận nào đang diễn ra.", ephemeral=True)
            return
        monster = db.get_monster(session["monster_id"])
        result = combat.perform_defend(character, session)
        await _render_dungeon_combat_turn(interaction, result, monster)


class DungeonFleeButton(discord.ui.Button):
    def __init__(self):
        super().__init__(label="Rút lui", emoji="🏃", style=discord.ButtonStyle.secondary, row=1)

    @error_handler.safe_interaction(lambda: CombatMenuView())
    async def callback(self, interaction: discord.Interaction):
        character = db.get_character(str(interaction.user.id))
        session = db.get_active_combat_session(character["character_id"])
        if session is None:
            await interaction.response.send_message("Không có trận nào đang diễn ra.", ephemeral=True)
            return
        monster = db.get_monster(session["monster_id"])
        result = combat.perform_flee(character, session)
        await _render_dungeon_combat_turn(interaction, result, monster)


class DungeonAbilitySelect(discord.ui.Select):
    def __init__(self, pathway_id: str, current_sequence: int):
        abilities = db.list_unlocked_abilities(pathway_id, current_sequence)
        if not abilities:
            abilities_options = [discord.SelectOption(label="Chưa có Ability nào mở khóa", value="none")]
        else:
            abilities_options = [
                discord.SelectOption(label=f"{a['name_vi']} (Spirituality {a['cost']})", value=a["ability_id"])
                for a in abilities
            ]
        super().__init__(placeholder="✨ Dùng Ability", options=abilities_options, row=2)

    @error_handler.safe_interaction(lambda: CombatMenuView())
    async def callback(self, interaction: discord.Interaction):
        if self.values[0] == "none":
            await interaction.response.send_message("Chưa có Ability nào để dùng.", ephemeral=True)
            return
        character = db.get_character(str(interaction.user.id))
        session = db.get_active_combat_session(character["character_id"])
        if session is None:
            await interaction.response.send_message("Không có trận nào đang diễn ra.", ephemeral=True)
            return
        monster = db.get_monster(session["monster_id"])
        try:
            result = combat.perform_ability(character, session, self.values[0])
        except combat.CombatError as e:
            await interaction.response.send_message(f"⚠️ {e}", ephemeral=True)
            return
        await _render_dungeon_combat_turn(interaction, result, monster)


class DungeonCombatActionsView(SafeView):
    def __init__(self, character: dict):
        super().__init__(timeout=180)
        self.add_item(DungeonAttackButton())
        self.add_item(DungeonDefendButton())
        self.add_item(DungeonFleeButton())
        if character.get("pathway_id"):
            self.add_item(DungeonAbilitySelect(character["pathway_id"], character["sequence_number"]))


# ---------------------------------------------------------------------------
# 🏟️ PvP thật (mục 24, 60) — luân phiên lượt giữa 2 Character
# ---------------------------------------------------------------------------

def build_pvp_hub(character: dict):
    """Hub PvP: hiện trận đang active, lời thách đấu đến/đi, hoặc nút thách đấu mới."""
    character_id = character["character_id"]

    active = pvp.get_active_session(character_id)
    if active:
        opponent_id = active["opponent_id"] if character_id == active["challenger_id"] else active["challenger_id"]
        opponent = db.get_character_by_id(opponent_id)
        embed = build_pvp_embed(character, active, opponent)
        return embed, PvPActionsView(character, active)

    incoming = pvp.get_incoming_challenge(character_id)
    if incoming:
        challenger = db.get_character_by_id(incoming["challenger_id"])
        embed = discord.Embed(
            title="🏟️ LỜI THÁCH ĐẤU",
            description=f"**{challenger['name']}** (Lv.{challenger['level']}) đã thách đấu bạn.\n"
                        f"Cược: {pvp.WAGER} Bảng (bên thua mất cho bên thắng).",
            color=discord.Color.orange(),
        )
        return embed, PvPIncomingView(incoming)

    outgoing = pvp.get_outgoing_challenge(character_id)
    if outgoing:
        opponent = db.get_character_by_id(outgoing["opponent_id"])
        embed = discord.Embed(
            title="🏟️ ĐANG CHỜ ĐỐI THỦ",
            description=f"Đã gửi lời thách đấu tới **{opponent['name']}**. Đợi họ chấp nhận.",
            color=discord.Color.orange(),
        )
        return embed, SimpleBackView(CombatMenuView)

    embed = discord.Embed(
        title="🏟️ PVP",
        description=f"Chọn một người chơi khác trong server để thách đấu.\n"
                    f"Cược mỗi trận: {pvp.WAGER} Bảng.",
        color=discord.Color.dark_red(),
    )
    return embed, PvPChallengeView()


def build_pvp_embed(character: dict, session: dict, opponent: dict, last_result: dict = None) -> discord.Embed:
    character_id = character["character_id"]
    self_hp = session["challenger_hp"] if character_id == session["challenger_id"] else session["opponent_hp"]
    opp_hp = session["opponent_hp"] if character_id == session["challenger_id"] else session["challenger_hp"]

    embed = discord.Embed(title=f"🏟️ {character['name']} vs {opponent['name']}", color=discord.Color.dark_red())
    bar_len = 10
    self_filled = max(0, round(self_hp / character["hp_max"] * bar_len))
    opp_filled = max(0, round(opp_hp / max(1, opponent["hp_max"]) * bar_len))
    embed.add_field(
        name=f"{ICONS['hp']} Bạn ({character['name']})",
        value=f"{self_hp} / {character['hp_max']}\n" + "🟩" * self_filled + "⬛" * (bar_len - self_filled),
        inline=True,
    )
    embed.add_field(
        name=f"⚔️ {opponent['name']}",
        value=f"{opp_hp} / {opponent['hp_max']}\n" + "🟥" * opp_filled + "⬛" * (bar_len - opp_filled),
        inline=True,
    )
    if session.get("turn_character_id") is not None:
        turn_name = character["name"] if session["turn_character_id"] == character_id else opponent["name"]
        embed.add_field(name="Lượt hiện tại", value=f"🎯 {turn_name}", inline=False)

    active = effects.list_active_effects(character_id)
    if active:
        embed.add_field(
            name="Hiệu ứng của bạn",
            value="\n".join(f"{'🟢' if e['type']=='buff' else '🔴'} {e['name_en']}" for e in active),
            inline=False,
        )
    if last_result:
        lines = [f"**{last_result['action_label']}**"]
        if last_result.get("dealt"):
            lines.append(f"Gây {last_result['dealt']} sát thương.")
        if last_result["status"] == "victory":
            lines.append(f"🏆 Thắng! +{last_result['wager']} Bảng từ đối thủ.")
        elif last_result["status"] == "defeat":
            lines.append(f"☠️ Thua trận! Mất {last_result['wager']} Bảng, HP về 1.")
        elif last_result["status"] == "fled":
            lines.append(f"🏃 Rút lui — xử thua, mất {last_result['wager']} Bảng.")
        embed.add_field(name="Kết quả lượt", value="\n".join(lines), inline=False)
    return embed


class PvPChallengeSelect(discord.ui.UserSelect):
    def __init__(self):
        super().__init__(placeholder="🏟️ Chọn người chơi để thách đấu", row=0)

    async def callback(self, interaction: discord.Interaction):
        challenger = db.get_character(str(interaction.user.id))
        target_user = self.values[0]
        opponent = db.get_character(str(target_user.id))
        if opponent is None:
            await interaction.response.send_message("Người chơi này chưa có nhân vật.", ephemeral=True)
            return
        try:
            pvp.challenge(challenger, opponent)
        except pvp.PvPError as e:
            await interaction.response.send_message(f"⚠️ {e}", ephemeral=True)
            return
        embed, view = build_pvp_hub(challenger)
        await interaction.response.edit_message(embed=embed, view=view)


class PvPChallengeView(SafeView):
    def __init__(self):
        super().__init__(timeout=180)
        self.add_item(PvPChallengeSelect())
        self.add_item(BackButton(CombatMenuView))


class PvPIncomingView(SafeView):
    def __init__(self, session: dict):
        super().__init__(timeout=180)
        self.session = session

    @discord.ui.button(label="Chấp nhận", emoji="✅", style=discord.ButtonStyle.success, row=0)
    async def accept(self, interaction: discord.Interaction, button: discord.ui.Button):
        character = db.get_character(str(interaction.user.id))
        try:
            session, challenger = pvp.accept(character)
        except pvp.PvPError as e:
            await interaction.response.send_message(f"⚠️ {e}", ephemeral=True)
            return
        embed = build_pvp_embed(character, session, challenger)
        await interaction.response.edit_message(embed=embed, view=PvPActionsView(character, session))

    @discord.ui.button(label="Từ chối", emoji="❌", style=discord.ButtonStyle.secondary, row=0)
    async def decline(self, interaction: discord.Interaction, button: discord.ui.Button):
        character = db.get_character(str(interaction.user.id))
        try:
            pvp.decline(character)
        except pvp.PvPError as e:
            await interaction.response.send_message(f"⚠️ {e}", ephemeral=True)
            return
        embed = discord.Embed(description="Đã từ chối lời thách đấu.", color=discord.Color.greyple())
        await interaction.response.edit_message(embed=embed, view=SimpleBackView(CombatMenuView))


async def _render_pvp_turn(interaction: discord.Interaction, result: dict, opponent: dict):
    character = db.get_character(str(interaction.user.id))
    if result["status"] == "ongoing":
        session = db.get_active_pvp_session(character["character_id"])
        embed = build_pvp_embed(character, session, opponent, last_result=result)
        await interaction.response.edit_message(embed=embed, view=PvPActionsView(character, session))
    else:
        fake_session = {
            "challenger_hp": result["self_hp"], "opponent_hp": result["opponent_hp"],
            "challenger_id": character["character_id"], "opponent_id": opponent["character_id"],
        }
        embed = build_pvp_embed(character, fake_session, opponent, last_result=result)
        await interaction.response.edit_message(embed=embed, view=SimpleBackView(CombatMenuView))


class PvPAttackButton(discord.ui.Button):
    def __init__(self):
        super().__init__(label="Tấn công", emoji="⚔️", style=discord.ButtonStyle.danger, row=1)

    async def callback(self, interaction: discord.Interaction):
        character = db.get_character(str(interaction.user.id))
        session = db.get_active_pvp_session(character["character_id"])
        if session is None:
            await interaction.response.send_message("Không có trận PvP nào đang diễn ra.", ephemeral=True)
            return
        opponent_id = session["opponent_id"] if character["character_id"] == session["challenger_id"] else session["challenger_id"]
        opponent = db.get_character_by_id(opponent_id)
        try:
            result = pvp.perform_attack(character, session)
        except pvp.PvPError as e:
            await interaction.response.send_message(f"⚠️ {e}", ephemeral=True)
            return
        await _render_pvp_turn(interaction, result, opponent)


class PvPDefendButton(discord.ui.Button):
    def __init__(self):
        super().__init__(label="Phòng thủ", emoji="🛡️", style=discord.ButtonStyle.secondary, row=1)

    async def callback(self, interaction: discord.Interaction):
        character = db.get_character(str(interaction.user.id))
        session = db.get_active_pvp_session(character["character_id"])
        if session is None:
            await interaction.response.send_message("Không có trận PvP nào đang diễn ra.", ephemeral=True)
            return
        opponent_id = session["opponent_id"] if character["character_id"] == session["challenger_id"] else session["challenger_id"]
        opponent = db.get_character_by_id(opponent_id)
        try:
            result = pvp.perform_defend(character, session)
        except pvp.PvPError as e:
            await interaction.response.send_message(f"⚠️ {e}", ephemeral=True)
            return
        await _render_pvp_turn(interaction, result, opponent)


class PvPFleeButton(discord.ui.Button):
    def __init__(self):
        super().__init__(label="Rút lui", emoji="🏃", style=discord.ButtonStyle.secondary, row=1)

    async def callback(self, interaction: discord.Interaction):
        character = db.get_character(str(interaction.user.id))
        session = db.get_active_pvp_session(character["character_id"])
        if session is None:
            await interaction.response.send_message("Không có trận PvP nào đang diễn ra.", ephemeral=True)
            return
        opponent_id = session["opponent_id"] if character["character_id"] == session["challenger_id"] else session["challenger_id"]
        opponent = db.get_character_by_id(opponent_id)
        try:
            result = pvp.perform_flee(character, session)
        except pvp.PvPError as e:
            await interaction.response.send_message(f"⚠️ {e}", ephemeral=True)
            return
        await _render_pvp_turn(interaction, result, opponent)


class PvPAbilitySelect(discord.ui.Select):
    def __init__(self, pathway_id: str, current_sequence: int):
        abilities = db.list_unlocked_abilities(pathway_id, current_sequence)
        if not abilities:
            abilities_options = [discord.SelectOption(label="Chưa có Ability nào mở khóa", value="none")]
        else:
            abilities_options = [
                discord.SelectOption(
                    label=f"{a['name_vi']} (Spirituality {a['cost']})",
                    value=a["ability_id"],
                )
                for a in abilities
            ]
        super().__init__(placeholder="✨ Dùng Ability", options=abilities_options, row=2)

    async def callback(self, interaction: discord.Interaction):
        if self.values[0] == "none":
            await interaction.response.send_message("Chưa có Ability nào để dùng.", ephemeral=True)
            return
        character = db.get_character(str(interaction.user.id))
        session = db.get_active_pvp_session(character["character_id"])
        if session is None:
            await interaction.response.send_message("Không có trận PvP nào đang diễn ra.", ephemeral=True)
            return
        opponent_id = session["opponent_id"] if character["character_id"] == session["challenger_id"] else session["challenger_id"]
        opponent = db.get_character_by_id(opponent_id)
        try:
            result = pvp.perform_ability(character, session, self.values[0])
        except pvp.PvPError as e:
            await interaction.response.send_message(f"⚠️ {e}", ephemeral=True)
            return
        await _render_pvp_turn(interaction, result, opponent)


class PvPActionsView(SafeView):
    def __init__(self, character: dict, session: dict):
        super().__init__(timeout=180)
        self.add_item(PvPAttackButton())
        self.add_item(PvPDefendButton())
        self.add_item(PvPFleeButton())
        if character.get("pathway_id"):
            self.add_item(PvPAbilitySelect(character["pathway_id"], character["sequence_number"]))


# ---------------------------------------------------------------------------
# 🔮 Huyền bí — Mysticism Knowledge (mục 18) + Divination (mục 19)
# ---------------------------------------------------------------------------

class MysticismMenuSelect(discord.ui.Select):
    OPTIONS = [
        ("knowledge", "knowledge", "Kiến thức", ICONS["mysticism"]),
        ("divination", "divination", "Bói toán", ICONS["divination"]),
    ]

    def __init__(self, lang: str = None):
        self.lang = lang
        options = [
            discord.SelectOption(label=i18n.t(f"mysticism_menu.{i18n_key}", lang, default=label), value=key, emoji=icon)
            for key, i18n_key, label, icon in self.OPTIONS
        ]
        super().__init__(placeholder=f"🔮 {i18n.t('mysticism_menu.placeholder', lang)}", options=options, row=0)

    async def callback(self, interaction: discord.Interaction):
        character = db.get_character(str(interaction.user.id))
        key = self.values[0]
        if key == "knowledge":
            embed, view = build_knowledge_view(character)
        else:
            embed, view = build_divination_view(character)
        await interaction.response.edit_message(embed=embed, view=view)


class MysticismMenuView(SafeView):
    def __init__(self, lang: str = None):
        super().__init__(timeout=180)
        self.add_item(MysticismMenuSelect(lang))
        self.add_item(BackButton(MainMenuView))


def build_knowledge_view(character: dict):
    icon = ICONS["mysticism"]
    lang = i18n.user_lang(character["user_id"]) if character else None
    if character is None:
        return build_stub_embed(i18n.t("mysticism_menu.knowledge_title", lang, default="Kiến thức Huyền bí"), icon), SimpleBackView(MysticismMenuView)

    catalog = mysticism_engine.list_catalog(character["character_id"])
    embed = discord.Embed(title=f"{icon} {i18n.t('mysticism_menu.knowledge_title', lang)}", color=discord.Color.dark_blue())
    embed.description = i18n.t("mysticism_menu.knowledge_description", lang)
    for k in catalog:
        stage_label = i18n.t(f"mysticism_menu.stage_{k['stage']}", lang)
        embed.add_field(
            name=f"{k['name_en']} ({k['category']})",
            value=i18n.t(
                "mysticism_menu.knowledge_field_value", lang,
                stage=stage_label, discover_cost=k["discover_cost"],
                study_cost=k["study_cost"], understand_cost=k["understand_cost"],
                understand_risk=k["understand_risk"],
            ),
            inline=False,
        )
    return embed, KnowledgeActionsView(character, catalog, lang)


class KnowledgeSelect(discord.ui.Select):
    def __init__(self, catalog: list, lang: str = None):
        self.lang = lang
        options = [
            discord.SelectOption(
                label=k["name_en"],
                value=k["knowledge_id"],
                description=i18n.t(f"mysticism_menu.stage_{k['stage']}", lang)[:100],
            )
            for k in catalog
            if k["stage"] != "understood"
        ]
        super().__init__(placeholder=f"🔮 {i18n.t('mysticism_menu.knowledge_select_placeholder', lang)}", options=options, row=0)

    async def callback(self, interaction: discord.Interaction):
        character = db.get_character(str(interaction.user.id))
        lang = self.lang or i18n.user_lang(str(interaction.user.id))
        knowledge_id = self.values[0]
        row = db.get_character_knowledge_row(character["character_id"], knowledge_id)
        stage = row["stage"] if row else "unknown"

        try:
            if stage == "unknown":
                k = mysticism_engine.discover(character["character_id"], knowledge_id)
                message = i18n.t("mysticism_menu.discover_result", lang, name=k["name_en"])
            elif stage == "discovered":
                k = mysticism_engine.study(character["character_id"], knowledge_id)
                message = i18n.t("mysticism_menu.study_result", lang, name=k["name_en"])
            elif stage == "studied":
                result = mysticism_engine.understand(character["character_id"], knowledge_id)
                message = i18n.t("mysticism_menu.understand_result", lang, name=result["knowledge"]["name_en"])
                if result["risk_triggered"]:
                    message += i18n.t("mysticism_menu.understand_risk_warning", lang)
                    incident = result.get("incident")
                    if incident:
                        message += (
                            f"\n☠️ Mất kiểm soát ({incident['severity_label_vi']}): "
                            + ", ".join(incident["effects"])
                        )
            else:
                message = i18n.t("mysticism_menu.already_understood", lang)
        except mysticism_engine.MysticismError as e:
            await interaction.response.send_message(f"⚠️ {e}", ephemeral=True)
            return

        character = db.get_character(str(interaction.user.id))
        embed, view = build_knowledge_view(character)
        embed.add_field(name=i18n.t("common.result", lang), value=message, inline=False)
        await interaction.response.edit_message(embed=embed, view=view)


class KnowledgeActionsView(SafeView):
    def __init__(self, character: dict, catalog: list, lang: str = None):
        super().__init__(timeout=180)
        self.add_item(KnowledgeSelect(catalog, lang))
        self.add_item(BackButton(MysticismMenuView))


def build_divination_view(character: dict):
    icon = ICONS["divination"]
    lang = i18n.user_lang(character["user_id"]) if character else None
    if character is None:
        return build_stub_embed(i18n.t("mysticism_menu.divination_title", lang, default="Bói toán"), icon), SimpleBackView(MysticismMenuView)

    methods = divination_engine.list_methods()
    embed = discord.Embed(title=f"{icon} {i18n.t('mysticism_menu.divination_title', lang)}", color=discord.Color.dark_blue())
    embed.description = f"{ICONS['spirituality']} Spirituality: {character['spirituality']}/{character['spirituality_max']}"
    for m in methods:
        embed.add_field(
            name=m["name_en"],
            value=i18n.t(
                "mysticism_menu.divination_field_value", lang,
                cost=m["spirituality_cost"], accuracy=m["base_accuracy"], stars="★" * m["risk_stars"],
            ),
            inline=False,
        )
    return embed, DivinationActionsView(character, methods, lang)


class DivinationMethodSelect(discord.ui.Select):
    def __init__(self, methods: list, lang: str = None):
        self.lang = lang
        options = [
            discord.SelectOption(
                label=m["name_en"],
                value=m["method_id"],
                description=f"{m['spirituality_cost']} SP · {m['base_accuracy']}% accuracy"[:100],
            )
            for m in methods
        ]
        super().__init__(placeholder=f"🃏 {i18n.t('mysticism_menu.divination_select_placeholder', lang)}", options=options, row=0)

    async def callback(self, interaction: discord.Interaction):
        character = db.get_character(str(interaction.user.id))
        lang = self.lang or i18n.user_lang(str(interaction.user.id))
        try:
            result = divination_engine.perform(character, self.values[0])
        except divination_engine.DivinationError as e:
            await interaction.response.send_message(f"⚠️ {e}", ephemeral=True)
            return

        tier_label = i18n.t(f"mysticism_menu.tier_{result['tier']}", lang)

        character = db.get_character(str(interaction.user.id))
        embed, view = build_divination_view(character)
        embed.add_field(
            name=i18n.t("common.result", lang),
            value=i18n.t(
                "mysticism_menu.divination_result", lang,
                method=result["method"]["name_en"], tier=tier_label,
                roll=result["roll"], accuracy=result["accuracy"],
            ),
            inline=False,
        )
        if result["tier"] == "ominous":
            incident = result.get("incident")
            if incident:
                embed.add_field(
                    name=f"☠️ Mất kiểm soát ({incident['severity_label_vi']})",
                    value="Dính debuff Divination Backlash.\n" + "\n".join(incident["effects"]),
                    inline=False,
                )
            else:
                embed.add_field(name="⚠️ Phản chấn", value="Dính debuff Divination Backlash.", inline=False)
        embed.add_field(name="📖 Diễn giải", value=result["narrative"], inline=False)
        await interaction.response.edit_message(embed=embed, view=view)


class DivinationActionsView(SafeView):
    def __init__(self, character: dict, methods: list, lang: str = None):
        super().__init__(timeout=180)
        self.add_item(DivinationMethodSelect(methods, lang))
        self.add_item(BackButton(MysticismMenuView))


# ---------------------------------------------------------------------------
# 🌍 Thế giới — City + Location thật (mục 31-32)
# ---------------------------------------------------------------------------

def build_world_overview_embed(character: dict) -> discord.Embed:
    icon = ICONS["world"]
    embed = discord.Embed(title=f"{icon} THẾ GIỚI", color=discord.Color.dark_teal())
    if character is None:
        embed.description = "Bạn chưa có nhân vật nào."
        return embed

    location = world_engine.get_current_location(character)
    if location is None:
        embed.description = "Chưa xác định vị trí của nhân vật."
        return embed

    city = db.get_city(location["city_id"])
    embed.add_field(
        name=f"{ICONS['location']} Vị trí hiện tại",
        value=f"{location['name_en']} — {city['name_en']}",
        inline=False,
    )
    embed.add_field(name="Mô tả", value=location["description_vi"], inline=False)
    embed.add_field(
        name=f"{ICONS['city']} {city['name_en']}",
        value=(
            f"Kinh tế: {city['economy']} | Tội phạm: {city['crime']} | "
            f"Hoạt động huyền bí: {city['mystical_activity']} | "
            f"Ảnh hưởng Giáo hội: {city['church_influence']}"
        ),
        inline=False,
    )
    return embed


class WorldMenuSelect(discord.ui.Select):
    OPTIONS = [
        ("cities", "cities", "Thành phố", ICONS["city"]),
        ("travel", "travel", "Di chuyển", ICONS["world"]),
        ("npc", "npc", "NPC", ICONS["npc"]),
        ("investigation", "investigation", "Điều tra", ICONS["investigation"]),
        ("quest", "quest", "Nhiệm vụ", ICONS["quest"]),
        ("event", "event", "Sự kiện", ICONS["event"]),
        ("history", "history", "Biên niên sử", ICONS["history"]),
    ]

    def __init__(self, lang: str = None):
        self.lang = lang
        options = [
            discord.SelectOption(label=i18n.t(f"world_menu.{i18n_key}", lang, default=label), value=key, emoji=icon)
            for key, i18n_key, label, icon in self.OPTIONS
        ]
        super().__init__(placeholder=f"🌍 {i18n.t('world_menu.placeholder', lang)}", options=options, row=0)

    @error_handler.safe_interaction(lambda: WorldMenuView())
    async def callback(self, interaction: discord.Interaction):
        character = db.get_character(str(interaction.user.id))
        key = self.values[0]
        if key == "cities":
            embed, view = build_cities_view(character)
        elif key == "npc":
            embed, view = build_npc_list_view(character)
        elif key == "investigation":
            embed, view = build_investigation_list_view(character)
        elif key == "quest":
            embed, view = build_quest_list_view(character)
        elif key == "event":
            embed, view = build_world_event_hub(character)
        elif key == "history":
            embed, view = build_world_history_view(character)
        else:
            embed, view = build_travel_city_view(character)
        await interaction.response.edit_message(embed=embed, view=view)


class WorldMenuView(SafeView):
    def __init__(self, lang: str = None):
        super().__init__(timeout=180)
        self.add_item(WorldMenuSelect(lang))
        self.add_item(BackButton(MainMenuView))


def build_cities_view(character: dict):
    icon = ICONS["city"]
    lang = i18n.user_lang(character["user_id"]) if character else None
    if character is None:
        return build_stub_embed(i18n.t("world_menu.cities_title", lang, default="Thành phố"), icon), SimpleBackView(WorldMenuView)

    cities = world_engine.list_cities()
    current_location = world_engine.get_current_location(character)
    current_city_id = current_location["city_id"] if current_location else None

    embed = discord.Embed(title=f"{icon} {i18n.t('world_menu.cities_title', lang)}", color=discord.Color.dark_teal())
    for c in cities:
        marker = i18n.t("world_menu.current_marker", lang) if c["city_id"] == current_city_id else ""
        embed.add_field(
            name=f"{c['name_en']}{marker}",
            value=i18n.t(
                "world_menu.city_field_value", lang,
                description=c["description_vi"], economy=c["economy"], crime=c["crime"],
                mystical=c["mystical_activity"], church=c["church_influence"], cost=c["travel_cost"],
            ),
            inline=False,
        )
    return embed, SimpleBackView(WorldMenuView)


def build_travel_city_view(character: dict):
    icon = ICONS["world"]
    lang = i18n.user_lang(character["user_id"]) if character else None
    if character is None:
        return build_stub_embed(i18n.t("world_menu.travel", lang, default="Di chuyển"), icon), SimpleBackView(WorldMenuView)

    cities = world_engine.list_cities()
    embed = discord.Embed(title=f"{icon} {i18n.t('world_menu.travel_title', lang)}", color=discord.Color.dark_teal())
    embed.description = i18n.t("world_menu.travel_description", lang)
    return embed, TravelCitySelectView(cities, lang)


class TravelCitySelect(discord.ui.Select):
    def __init__(self, cities: list, lang: str = None):
        self.lang = lang
        options = [
            discord.SelectOption(
                label=c["name_en"], value=c["city_id"],
                description=i18n.t("world_menu.travel_cost_description", lang, cost=c["travel_cost"])[:100],
            )
            for c in cities
        ]
        super().__init__(placeholder=f"🏙️ {i18n.t('world_menu.travel_city_select_placeholder', lang)}", options=options, row=0)

    async def callback(self, interaction: discord.Interaction):
        character = db.get_character(str(interaction.user.id))
        embed, view = build_travel_location_view(character, self.values[0])
        await interaction.response.edit_message(embed=embed, view=view)


class TravelCitySelectView(SafeView):
    def __init__(self, cities: list, lang: str = None):
        super().__init__(timeout=180)
        self.add_item(TravelCitySelect(cities, lang))
        self.add_item(BackButton(WorldMenuView))


def build_travel_location_view(character: dict, city_id: str):
    icon = ICONS["location"]
    lang = i18n.user_lang(character["user_id"])
    city = db.get_city(city_id)
    locations = world_engine.list_locations(city_id)

    current_location = world_engine.get_current_location(character)
    cost = 0
    if not current_location or current_location["city_id"] != city_id:
        cost = city["travel_cost"]

    embed = discord.Embed(
        title=f"{icon} {i18n.t('world_menu.travel_location_title', lang, city=city['name_en'])}",
        color=discord.Color.dark_teal(),
    )
    embed.description = (
        i18n.t("world_menu.travel_location_cost_line", lang, city=city["name_en"], cost=cost) if cost
        else i18n.t("world_menu.travel_location_free_line", lang, city=city["name_en"])
    )
    return embed, TravelLocationSelectView(locations, lang)


class TravelLocationSelect(discord.ui.Select):
    def __init__(self, locations: list, lang: str = None):
        self.lang = lang
        options = [
            discord.SelectOption(
                label=l["name_en"], value=l["location_id"],
                description=l["description_vi"][:100],
            )
            for l in locations
        ]
        super().__init__(placeholder=f"📍 {i18n.t('world_menu.travel_location_select_placeholder', lang)}", options=options, row=0)

    @error_handler.safe_interaction(lambda: WorldMenuView())
    async def callback(self, interaction: discord.Interaction):
        character = db.get_character(str(interaction.user.id))
        lang = self.lang or i18n.user_lang(str(interaction.user.id))
        try:
            result = world_engine.travel(character["character_id"], self.values[0])
        except world_engine.WorldError as e:
            await interaction.response.send_message(f"⚠️ {e}", ephemeral=True)
            return

        character = db.get_character(str(interaction.user.id))
        embed = build_world_overview_embed(character)
        cost_note = (
            i18n.t("world_menu.travel_cost_note", lang, cost=result["cost"]) if result["cost"]
            else i18n.t("world_menu.travel_free_note", lang)
        )
        embed.add_field(
            name=i18n.t("common.result", lang),
            value=i18n.t("world_menu.travel_result", lang, location=result["location"]["name_en"], cost_note=cost_note),
            inline=False,
        )
        if result.get("triggered_event"):
            ev = result["triggered_event"]
            embed.add_field(
                name=i18n.t("world_menu.event_field_name", lang, name=ev["name_vi"]),
                value=ev.get("narrative", ev["description_vi"])[:300],
                inline=False,
            )
        await interaction.response.edit_message(embed=embed, view=WorldMenuView(lang))


class TravelLocationSelectView(SafeView):
    def __init__(self, locations: list, lang: str = None):
        super().__init__(timeout=180)
        self.add_item(TravelLocationSelect(locations, lang))
        self.add_item(BackButton(WorldMenuView))


# ---------------------------------------------------------------------------
# 🌑 World Event (mục 47) — tác động thật lên City, Player có thể can thiệp
# ---------------------------------------------------------------------------

def build_world_event_hub(character: dict):
    icon = ICONS["event"]
    events = world_event.list_active()
    embed = discord.Embed(title=f"{icon} SỰ KIỆN THẾ GIỚI", color=discord.Color.dark_red())
    if not events:
        embed.description = "Hiện không có Sự kiện nào đang diễn ra. Sự kiện có thể tự phát sinh khi Di chuyển."
        return embed, SimpleBackView(WorldMenuView)

    for e in events:
        deltas = []
        if e["economy_delta"]:
            deltas.append(f"Kinh tế {'+' if e['economy_delta']>=0 else ''}{e['economy_delta']}")
        if e["crime_delta"]:
            deltas.append(f"Tội phạm {'+' if e['crime_delta']>=0 else ''}{e['crime_delta']}")
        if e["mystical_delta"]:
            deltas.append(f"Huyền bí {'+' if e['mystical_delta']>=0 else ''}{e['mystical_delta']}")
        embed.add_field(
            name=f"#{e['event_id']} {e['name_vi']} — {e['city_name']}",
            value=f"{e['description_vi'][:150]}\n{' · '.join(deltas)}",
            inline=False,
        )
    return embed, WorldEventActionsView(events)


class ContributeEventSelect(discord.ui.Select):
    def __init__(self, events: list):
        from data.world_events_seed import CONTRIBUTION_COST_MONEY
        options = [
            discord.SelectOption(
                label=f"#{e['event_id']} {e['name_vi']} ({e['city_name']})",
                value=str(e["event_id"]),
                description=f"Tốn {CONTRIBUTION_COST_MONEY} Bảng để can thiệp"[:100],
            )
            for e in events
        ]
        super().__init__(placeholder=f"{ICONS['event']} Can thiệp dẹp Sự kiện", options=options, row=0)

    @error_handler.safe_interaction(lambda: WorldMenuView())
    async def callback(self, interaction: discord.Interaction):
        character = db.get_character(str(interaction.user.id))
        try:
            outcome = world_event.contribute(character["character_id"], int(self.values[0]))
        except world_event.WorldEventError as e:
            await interaction.response.send_message(f"⚠️ {e}", ephemeral=True)
            return
        character = db.get_character(str(interaction.user.id))
        embed, view = build_world_event_hub(character)
        if outcome["resolved"]:
            message = "✅ Sự kiện đã được dẹp yên hoàn toàn! Thành phố trở lại trạng thái bình thường."
        else:
            message = f"Đã đóng góp. Tiến độ: {outcome['total_contribution']}/{outcome['threshold']}."
        embed.add_field(name="Kết quả", value=message, inline=False)
        await interaction.response.edit_message(embed=embed, view=view)


class WorldEventActionsView(SafeView):
    def __init__(self, events: list):
        super().__init__(timeout=180)
        self.add_item(ContributeEventSelect(events))
        self.add_item(BackButton(WorldMenuView))


# ---------------------------------------------------------------------------
# 👤 NPC — Trust + Memory thật, gắn với Location hiện tại (mục 28)
# ---------------------------------------------------------------------------

TRUST_TIER_LABEL_VI = {
    "stranger": "Người lạ",
    "acquaintance": "Quen biết",
    "trusted": "Tin tưởng",
}


def build_npc_list_view(character: dict):
    icon = ICONS["npc"]
    if character is None:
        return build_stub_embed("NPC", icon), SimpleBackView(WorldMenuView)

    location = world_engine.get_current_location(character)
    npcs = npc_engine.list_npcs_here(character)

    embed = discord.Embed(title=f"{icon} NPC — {location['name_en'] if location else '?'}", color=discord.Color.dark_gold())
    if not npcs:
        embed.description = "Không có NPC nào ở Location này. Hãy Di chuyển tới nơi khác."
        return embed, SimpleBackView(WorldMenuView)

    for n in npcs:
        rel = npc_engine.get_relationship(character["character_id"], n["npc_id"])
        embed.add_field(
            name=f"{n['name_en']} ({n['role']})",
            value=f"{n['description_vi']}\nTrust: {rel['trust']}/100 — {TRUST_TIER_LABEL_VI[rel['tier']]}",
            inline=False,
        )
    return embed, NPCSelectView(npcs)


class NPCSelect(discord.ui.Select):
    def __init__(self, npcs: list):
        options = [
            discord.SelectOption(label=n["name_en"], value=n["npc_id"], description=n["role"][:100])
            for n in npcs
        ]
        super().__init__(placeholder="👤 Chọn NPC", options=options, row=0)

    async def callback(self, interaction: discord.Interaction):
        character = db.get_character(str(interaction.user.id))
        embed, view = build_npc_detail_view(character, self.values[0])
        await interaction.response.edit_message(embed=embed, view=view)


class NPCSelectView(SafeView):
    def __init__(self, npcs: list):
        super().__init__(timeout=180)
        self.add_item(NPCSelect(npcs))
        self.add_item(BackButton(WorldMenuView))


def build_npc_detail_view(character: dict, npc_id: str):
    icon = ICONS["npc"]
    npc = db.get_npc(npc_id)
    rel = npc_engine.get_relationship(character["character_id"], npc_id)

    embed = discord.Embed(title=f"{icon} {npc['name_en']}", color=discord.Color.dark_gold())
    embed.description = npc["description_vi"]
    embed.add_field(
        name="Trust",
        value=f"{rel['trust']}/100 — {TRUST_TIER_LABEL_VI[rel['tier']]} ({rel['interactions']} lần tương tác)",
        inline=False,
    )
    inventory = db.list_inventory(character["character_id"])
    return embed, NPCDetailActionsView(npc, inventory)


class TalkButton(discord.ui.Button):
    def __init__(self, npc_id: str):
        super().__init__(label="Trò chuyện", emoji="💬", style=discord.ButtonStyle.primary, row=0)
        self._npc_id = npc_id

    async def callback(self, interaction: discord.Interaction):
        character = db.get_character(str(interaction.user.id))
        try:
            result = npc_engine.talk(character["character_id"], character, self._npc_id)
        except npc_engine.NPCError as e:
            await interaction.response.send_message(f"⚠️ {e}", ephemeral=True)
            return

        embed, view = build_npc_detail_view(character, self._npc_id)
        embed.add_field(name=f"{result['npc']['name_en']} nói", value=result["line"], inline=False)
        if result.get("dangerous_event"):
            embed.add_field(
                name="⚠️ Bất ổn",
                value=f"{result['npc']['name_en']} đang cảnh giác vì \"{result['dangerous_event']}\" — Trust tăng chậm hơn.",
                inline=False,
            )
        await interaction.response.edit_message(embed=embed, view=view)


class GiftItemSelect(discord.ui.Select):
    def __init__(self, npc_id: str, inventory: list):
        self._npc_id = npc_id
        options = [
            discord.SelectOption(label=f"{i['name_vi']} (x{i['quantity']})", value=i["item_id"])
            for i in inventory
        ] or [discord.SelectOption(label="Túi đồ trống", value="__empty__")]
        super().__init__(placeholder="🎁 Chọn quà để tặng", options=options, row=1)

    async def callback(self, interaction: discord.Interaction):
        if self.values[0] == "__empty__":
            await interaction.response.send_message("⚠️ Túi đồ của bạn đang trống.", ephemeral=True)
            return
        character = db.get_character(str(interaction.user.id))
        try:
            result = npc_engine.give_gift(character["character_id"], character, self._npc_id, self.values[0])
        except npc_engine.NPCError as e:
            await interaction.response.send_message(f"⚠️ {e}", ephemeral=True)
            return

        embed, view = build_npc_detail_view(character, self._npc_id)
        favorite_note = " 💖 Đúng món họ thích!" if result["is_favorite"] else ""
        embed.add_field(
            name="Kết quả",
            value=f"✅ Đã tặng **{result['item']['name_vi']}**. Trust +{result['trust_gain']}.{favorite_note}",
            inline=False,
        )
        if result.get("dangerous_event"):
            embed.add_field(
                name="⚠️ Bất ổn",
                value=f"{result['npc']['name_en']} đang cảnh giác vì \"{result['dangerous_event']}\" — Trust tăng chậm hơn.",
                inline=False,
            )
        await interaction.response.edit_message(embed=embed, view=view)


class NPCDetailActionsView(SafeView):
    def __init__(self, npc: dict, inventory: list):
        super().__init__(timeout=180)
        self.add_item(TalkButton(npc["npc_id"]))
        self.add_item(GiftItemSelect(npc["npc_id"], inventory))
        self.add_item(BackButton(WorldMenuView))


# ---------------------------------------------------------------------------
# 🔍 Điều tra — Observe/Clue/Resolution thật, gắn với Location hiện tại (mục 27)
# ---------------------------------------------------------------------------

INVESTIGATION_STATUS_LABEL_VI = {
    "not_started": "Chưa bắt đầu",
    "active": "Đang điều tra",
    "resolved_success": "✅ Đã kết luận đúng",
    "resolved_failed": "☠️ Đã kết luận sai",
}


def build_investigation_list_view(character: dict):
    icon = ICONS["investigation"]
    if character is None:
        return build_stub_embed("Điều tra", icon), SimpleBackView(WorldMenuView)

    location = world_engine.get_current_location(character)
    investigations = investigation_engine.list_at_location(character["location_id"])

    embed = discord.Embed(
        title=f"{icon} ĐIỀU TRA — {location['name_en'] if location else '?'}",
        color=discord.Color.dark_purple(),
    )
    if not investigations:
        embed.description = "Không có vụ việc nào cần điều tra ở đây. Hãy Di chuyển tới nơi khác."
        return embed, SimpleBackView(WorldMenuView)

    embed.description = "Chọn một vụ việc để xem chi tiết."
    for inv in investigations:
        ci = db.get_character_investigation(character["character_id"], inv["investigation_id"])
        status = ci["status"] if ci else "not_started"
        embed.add_field(
            name=inv["name_en"],
            value=f"{INVESTIGATION_STATUS_LABEL_VI[status]}",
            inline=True,
        )
    return embed, InvestigationSelectView(investigations, character["character_id"])


class InvestigationSelect(discord.ui.Select):
    def __init__(self, investigations: list, character_id: int):
        options = []
        for inv in investigations:
            ci = db.get_character_investigation(character_id, inv["investigation_id"])
            status = ci["status"] if ci else "not_started"
            options.append(
                discord.SelectOption(
                    label=inv["name_en"], value=inv["investigation_id"],
                    description=INVESTIGATION_STATUS_LABEL_VI[status][:100],
                )
            )
        super().__init__(placeholder="🔍 Chọn vụ việc", options=options, row=0)

    async def callback(self, interaction: discord.Interaction):
        character = db.get_character(str(interaction.user.id))
        embed, view = build_investigation_detail_view(character, self.values[0])
        await interaction.response.edit_message(embed=embed, view=view)


class InvestigationSelectView(SafeView):
    def __init__(self, investigations: list, character_id: int):
        super().__init__(timeout=180)
        self.add_item(InvestigationSelect(investigations, character_id))
        self.add_item(BackButton(WorldMenuView))


def build_investigation_detail_view(character: dict, investigation_id: str):
    icon = ICONS["investigation"]
    investigation = investigation_engine.get_investigation(investigation_id)
    progress = investigation_engine.get_progress(character["character_id"], investigation_id)

    embed = discord.Embed(title=f"{icon} {investigation['name_en']}", color=discord.Color.dark_purple())
    embed.description = investigation["description_vi"]

    if progress["status"] == "not_started":
        embed.add_field(name="Trạng thái", value="Chưa bắt đầu điều tra.", inline=False)
    else:
        found_texts = [c["text_vi"] for c in progress["clues"] if c["clue_id"] in progress["found_ids"]]
        clue_display = "\n".join(f"• {t}" for t in found_texts) if found_texts else "Chưa tìm ra manh mối nào — hãy Quan sát."
        embed.add_field(
            name=f"Manh mối ({progress['found_count']}/{progress['total_count']})",
            value=clue_display[:1024],
            inline=False,
        )
        embed.add_field(name="Trạng thái", value=INVESTIGATION_STATUS_LABEL_VI[progress["status"]], inline=False)

    return embed, InvestigationDetailView(investigation_id, progress["status"])


class InvestigationStartButton(discord.ui.Button):
    def __init__(self):
        super().__init__(label="Bắt đầu điều tra", emoji="🔍", style=discord.ButtonStyle.primary, row=1)

    async def callback(self, interaction: discord.Interaction):
        character = db.get_character(str(interaction.user.id))
        investigation_id = self.view.investigation_id
        try:
            investigation_engine.start(character, investigation_id)
        except investigation_engine.InvestigationError as e:
            await interaction.response.send_message(f"⚠️ {e}", ephemeral=True)
            return
        character = db.get_character(str(interaction.user.id))
        embed, view = build_investigation_detail_view(character, investigation_id)
        await interaction.response.edit_message(embed=embed, view=view)


class InvestigationObserveButton(discord.ui.Button):
    def __init__(self):
        super().__init__(label="Quan sát", emoji="🔎", style=discord.ButtonStyle.secondary, row=1)

    async def callback(self, interaction: discord.Interaction):
        character = db.get_character(str(interaction.user.id))
        investigation_id = self.view.investigation_id
        try:
            clue, found = investigation_engine.observe(character, investigation_id)
        except investigation_engine.InvestigationError as e:
            await interaction.response.send_message(f"⚠️ {e}", ephemeral=True)
            return
        character = db.get_character(str(interaction.user.id))
        embed, view = build_investigation_detail_view(character, investigation_id)
        note = f"🔎 Tìm thấy manh mối mới: {clue['text_vi']}" if found else "🔎 Không phát hiện gì đáng chú ý lần này."
        embed.add_field(name="Kết quả Quan sát", value=note, inline=False)
        await interaction.response.edit_message(embed=embed, view=view)


class InvestigationResolveButton(discord.ui.Button):
    def __init__(self):
        super().__init__(label="Phân tích & Kết luận", emoji="🧩", style=discord.ButtonStyle.danger, row=2)

    async def callback(self, interaction: discord.Interaction):
        character = db.get_character(str(interaction.user.id))
        investigation_id = self.view.investigation_id
        try:
            result = investigation_engine.resolve(character, investigation_id)
        except investigation_engine.InvestigationError as e:
            await interaction.response.send_message(f"⚠️ {e}", ephemeral=True)
            return
        character = db.get_character(str(interaction.user.id))
        embed, view = build_investigation_detail_view(character, investigation_id)
        if result["success"]:
            note = (
                f"✅ Kết luận chính xác! Thưởng: {result['reward']['money']} Bảng, "
                f"{result['reward']['exp']} EXP"
            )
        else:
            note = "☠️ Kết luận sai — vụ việc khép lại trong bí ẩn."
        embed.add_field(name="Kết quả", value=note, inline=False)
        await interaction.response.edit_message(embed=embed, view=view)


class InvestigationDetailView(SafeView):
    def __init__(self, investigation_id: str, status: str):
        super().__init__(timeout=180)
        self.investigation_id = investigation_id
        if status == "not_started":
            self.add_item(InvestigationStartButton())
        elif status == "active":
            self.add_item(InvestigationObserveButton())
            self.add_item(InvestigationResolveButton())
        self.add_item(BackButton(WorldMenuView))


# ---------------------------------------------------------------------------
# 📜 Quest — tuyến tính, nhiều Objective, tiến độ đến từ gameplay thật
# (mục 43 trong spec; KHÁC Investigation ở trên và KHÁC Contract/Bounty).
# ---------------------------------------------------------------------------

QUEST_STATUS_LABEL_VI = {
    "LOCKED": f"{ICONS['locked']} Chưa mở khóa",
    "AVAILABLE": "🟢 Có thể nhận",
    "ACTIVE": "🟡 Đang thực hiện",
    "COMPLETED": "✅ Đã hoàn thành",
    "FAILED": "☠️ Thất bại",
    "EXPIRED": "⌛ Hết hạn",
}


def build_world_history_view(character: dict):
    icon = ICONS["history"]
    embed = discord.Embed(title=f"{icon} BIÊN NIÊN SỬ THẾ GIỚI", color=discord.Color.dark_grey())
    stability = db.get_world_state("global_stability", "70")
    embed.description = f"🌍 Ổn định toàn cục: {stability}/100"
    entries = db.list_world_history(10)
    if not entries:
        embed.add_field(name="—", value="Chưa có sự kiện lớn nào được ghi nhận.", inline=False)
    for e in entries:
        embed.add_field(name=f"[{e['category']}] {e['created_at']}", value=e["summary_vi"], inline=False)
    return embed, SimpleBackView(WorldMenuView)


def build_quest_list_view(character: dict):
    icon = ICONS["quest"]
    if character is None:
        return build_stub_embed("Nhiệm vụ", icon), SimpleBackView(WorldMenuView)

    quests = quest_engine.list_quests(character)
    embed = discord.Embed(title=f"{icon} NHIỆM VỤ", color=discord.Color.dark_gold())
    embed.description = "Chọn một nhiệm vụ để xem chi tiết và mục tiêu."
    for q in quests:
        embed.add_field(
            name=f"{q['name_vi']} ({q['category']})",
            value=QUEST_STATUS_LABEL_VI[q["status"]],
            inline=True,
        )
    return embed, QuestSelectView(quests)


class QuestSelect(discord.ui.Select):
    def __init__(self, quests: list):
        # Chỉ cho chọn quest không LOCKED — quest LOCKED hiển thị ở embed
        # danh sách để người chơi biết còn tồn tại, nhưng không bấm được
        # vào xem chi tiết (tránh lộ nội dung chưa mở khóa).
        selectable = [q for q in quests if q["status"] != "LOCKED"]
        options = [
            discord.SelectOption(
                label=q["name_vi"][:100], value=q["quest_id"],
                description=QUEST_STATUS_LABEL_VI[q["status"]][:100],
            )
            for q in selectable
        ] or [discord.SelectOption(label="Chưa có nhiệm vụ khả dụng", value="_none")]
        super().__init__(placeholder="📜 Chọn nhiệm vụ", options=options, row=0)

    async def callback(self, interaction: discord.Interaction):
        if self.values[0] == "_none":
            await interaction.response.defer()
            return
        character = db.get_character(str(interaction.user.id))
        embed, view = build_quest_detail_view(character, self.values[0])
        await interaction.response.edit_message(embed=embed, view=view)


class QuestSelectView(SafeView):
    def __init__(self, quests: list):
        super().__init__(timeout=180)
        self.add_item(QuestSelect(quests))
        self.add_item(BackButton(WorldMenuView))


def build_quest_detail_view(character: dict, quest_id: str):
    icon = ICONS["quest"]
    progress = quest_engine.get_progress(character["character_id"], quest_id)
    q = progress["quest"]
    status = progress["status"] or "AVAILABLE"

    embed = discord.Embed(title=f"{icon} {q['name_vi']}", color=discord.Color.dark_gold())
    embed.description = q["description_vi"]
    embed.add_field(name="Trạng thái", value=QUEST_STATUS_LABEL_VI[status], inline=False)

    if status in ("ACTIVE", "COMPLETED"):
        lines = []
        for obj in progress["objectives"]:
            mark = "✅" if obj["completed_at"] else "▫️"
            lines.append(f"{mark} {obj['description_vi']} ({obj['progress_count']}/{obj['target_count']})")
        embed.add_field(name="Mục tiêu", value="\n".join(lines) or "—", inline=False)

    reward_lines = [f"{q['reward_money']} Bảng", f"{q['reward_exp']} EXP"]
    if q["reward_item_id"]:
        item = db.get_item(q["reward_item_id"])
        reward_lines.append(item["name_vi"] if item else q["reward_item_id"])
    embed.add_field(name="Phần thưởng", value=" · ".join(reward_lines), inline=False)

    return embed, QuestDetailView(quest_id, status)


class QuestStartButton(discord.ui.Button):
    def __init__(self):
        super().__init__(label="Nhận nhiệm vụ", emoji="📜", style=discord.ButtonStyle.primary, row=1)

    async def callback(self, interaction: discord.Interaction):
        character = db.get_character(str(interaction.user.id))
        quest_id = self.view.quest_id
        try:
            quest_engine.start(character, quest_id)
        except quest_engine.QuestError as e:
            await interaction.response.send_message(f"⚠️ {e}", ephemeral=True)
            return
        character = db.get_character(str(interaction.user.id))
        embed, view = build_quest_detail_view(character, quest_id)
        await interaction.response.edit_message(embed=embed, view=view)


class QuestCompleteButton(discord.ui.Button):
    def __init__(self):
        super().__init__(label="Hoàn thành & Nhận thưởng", emoji="🏁", style=discord.ButtonStyle.success, row=1)

    async def callback(self, interaction: discord.Interaction):
        character = db.get_character(str(interaction.user.id))
        quest_id = self.view.quest_id
        try:
            quest_engine.complete(character, quest_id)
        except quest_engine.QuestError as e:
            await interaction.response.send_message(f"⚠️ {e}", ephemeral=True)
            return
        character = db.get_character(str(interaction.user.id))
        embed, view = build_quest_detail_view(character, quest_id)
        embed.add_field(name="Kết quả", value="✅ Đã hoàn thành nhiệm vụ và nhận thưởng!", inline=False)
        await interaction.response.edit_message(embed=embed, view=view)


class QuestDetailView(SafeView):
    def __init__(self, quest_id: str, status: str):
        super().__init__(timeout=180)
        self.quest_id = quest_id
        if status == "AVAILABLE":
            self.add_item(QuestStartButton())
        elif status == "ACTIVE":
            self.add_item(QuestCompleteButton())
        self.add_item(BackButton(WorldMenuView))


# ---------------------------------------------------------------------------
# ⚙️ Cài đặt — ngôn ngữ (mục 65-66)
# ---------------------------------------------------------------------------

class LanguageSelect(discord.ui.Select):
    def __init__(self):
        options = [
            discord.SelectOption(label="Tiếng Việt", value="vi", emoji="🇻🇳"),
            discord.SelectOption(label="English", value="en", emoji="🇬🇧"),
        ]
        super().__init__(placeholder="🌐 Chọn ngôn ngữ", options=options, row=0)

    async def callback(self, interaction: discord.Interaction):
        db.set_user_language(str(interaction.user.id), self.values[0])
        confirm = i18n.t(f"settings.language_changed_{self.values[0]}", self.values[0])
        embed = discord.Embed(description=f"✅ {confirm}", color=discord.Color.green())
        await interaction.response.edit_message(embed=embed, view=SettingsView())


class SettingsView(SafeView):
    def __init__(self):
        super().__init__(timeout=180)
        self.add_item(LanguageSelect())
        self.add_item(BackButton(MainMenuView))


# ---------------------------------------------------------------------------
# 🏛️ Tổ chức — Church / Faction / Tarot / Party (mục 33-36, 59)
# ---------------------------------------------------------------------------

def build_faction_hub_embed(character: dict) -> discord.Embed:
    icon = ICONS["faction"]
    embed = discord.Embed(title=f"{icon} TỔ CHỨC", color=discord.Color.dark_purple())
    if character is None:
        embed.description = "Bạn chưa có nhân vật."
        return embed
    membership = faction_engine.get_membership(character["character_id"])
    church = membership["church"]
    fac = membership["faction"]
    tarot_membership = tarot_engine.get_membership(character["character_id"])
    party = party_engine.get_party(character["character_id"])

    embed.add_field(
        name=f"{ICONS['church']} Nhà Thờ",
        value=(f"{church['name_vi']} (Danh tiếng: {church['reputation']})" if church else "Chưa gia nhập"),
        inline=False,
    )
    embed.add_field(
        name=f"{ICONS['faction']} Faction",
        value=(f"{fac['name_vi']} (Danh tiếng: {fac['reputation']})" if fac else "Chưa gia nhập"),
        inline=False,
    )
    embed.add_field(
        name=f"{ICONS['tarot']} Tarot Club",
        value=(f"Mật danh: **{tarot_membership['tarot_seat']}**" if tarot_membership else "Chưa gia nhập"),
        inline=False,
    )
    embed.add_field(
        name=f"{ICONS['party']} Đội nhóm",
        value=(f"{len(party['members'])}/{party_engine.db.MAX_PARTY_SIZE} thành viên" if party else "Chưa có đội"),
        inline=False,
    )
    return embed


class FactionMenuSelect(discord.ui.Select):
    OPTIONS = [
        ("church", "Nhà Thờ", ICONS["church"]),
        ("faction", "Faction", ICONS["faction"]),
        ("guild", "Guild", ICONS["guild"]),
        ("tarot", "Tarot Club", ICONS["tarot"]),
        ("party", "Đội nhóm", ICONS["party"]),
    ]

    def __init__(self):
        options = [discord.SelectOption(label=l, value=k, emoji=i) for k, l, i in self.OPTIONS]
        super().__init__(placeholder="🏛️ Chọn chức năng", options=options, row=0)

    @error_handler.safe_interaction(lambda: FactionMenuView())
    async def callback(self, interaction: discord.Interaction):
        character = db.get_character(str(interaction.user.id))
        key = self.values[0]
        if key == "church":
            embed, view = build_church_view(character)
        elif key == "faction":
            embed, view = build_faction_list_view(character)
        elif key == "guild":
            embed, view = build_guild_hub_view(character)
        elif key == "tarot":
            embed, view = build_tarot_view(character)
        else:
            embed, view = build_party_view(character)
        await interaction.response.edit_message(embed=embed, view=view)


class FactionMenuView(SafeView):
    def __init__(self):
        super().__init__(timeout=180)
        self.add_item(FactionMenuSelect())
        self.add_item(BackButton(MainMenuView))


def build_church_view(character: dict):
    icon = ICONS["church"]
    churches = faction_engine.list_churches()
    current = faction_engine.get_membership(character["character_id"])["church"]
    embed = discord.Embed(title=f"{icon} CÁC NHÀ THỜ CHÍNH THỐNG", color=discord.Color.gold())
    embed.description = (
        f"Hiện tại: **{current['name_vi']}**" if current else "Bạn chưa gia nhập Nhà Thờ nào."
    )
    for c in churches:
        embed.add_field(name=f"{c['name_vi']} ({c['name_en']})", value=c["description_vi"][:200], inline=False)
    return embed, ChurchActionsView(churches, bool(current))


class JoinChurchSelect(discord.ui.Select):
    def __init__(self, churches: list):
        options = [
            discord.SelectOption(label=c["name_vi"], value=c["church_id"], description=c["name_en"][:100])
            for c in churches
        ]
        super().__init__(placeholder=f"{ICONS['church']} Gia nhập Nhà Thờ", options=options, row=0)

    @error_handler.safe_interaction(lambda: FactionMenuView())
    async def callback(self, interaction: discord.Interaction):
        character = db.get_character(str(interaction.user.id))
        try:
            church = faction_engine.join_church(character["character_id"], self.values[0])
            message = f"✅ Đã gia nhập **{church['name_vi']}**."
        except faction_engine.FactionError as e:
            await interaction.response.send_message(f"⚠️ {e}", ephemeral=True)
            return
        character = db.get_character(str(interaction.user.id))
        embed, view = build_church_view(character)
        embed.add_field(name="Kết quả", value=message, inline=False)
        await interaction.response.edit_message(embed=embed, view=view)


class LeaveChurchButton(discord.ui.Button):
    def __init__(self):
        super().__init__(label="Rời Nhà Thờ", emoji="🚪", style=discord.ButtonStyle.danger, row=1)

    @error_handler.safe_interaction(lambda: FactionMenuView())
    async def callback(self, interaction: discord.Interaction):
        character = db.get_character(str(interaction.user.id))
        try:
            faction_engine.leave_church(character["character_id"])
        except faction_engine.FactionError as e:
            await interaction.response.send_message(f"⚠️ {e}", ephemeral=True)
            return
        character = db.get_character(str(interaction.user.id))
        embed, view = build_church_view(character)
        await interaction.response.edit_message(embed=embed, view=view)


class ChurchActionsView(SafeView):
    def __init__(self, churches: list, has_current: bool):
        super().__init__(timeout=180)
        self.add_item(JoinChurchSelect(churches))
        if has_current:
            self.add_item(LeaveChurchButton())
            self.add_item(DonateButton())
            self.add_item(MissionListButton())
        self.add_item(BackButton(FactionMenuView))


def build_faction_list_view(character: dict):
    icon = ICONS["faction"]
    factions = faction_engine.list_factions()
    current = faction_engine.get_membership(character["character_id"])["faction"]
    embed = discord.Embed(title=f"{icon} CÁC FACTION", color=discord.Color.dark_teal())
    embed.description = (
        f"Hiện tại: **{current['name_vi']}**" if current else "Bạn chưa gia nhập Faction nào."
    )
    for f in factions:
        embed.add_field(name=f"{f['name_vi']} ({f['name_en']})", value=f["description_vi"][:200], inline=False)
    return embed, FactionActionsView(factions, bool(current))


class JoinFactionSelect(discord.ui.Select):
    def __init__(self, factions: list):
        options = [
            discord.SelectOption(label=f["name_vi"], value=f["faction_id"], description=f["name_en"][:100])
            for f in factions
        ]
        super().__init__(placeholder=f"{ICONS['faction']} Gia nhập Faction", options=options, row=0)

    @error_handler.safe_interaction(lambda: FactionMenuView())
    async def callback(self, interaction: discord.Interaction):
        character = db.get_character(str(interaction.user.id))
        try:
            faction = faction_engine.join_faction(character["character_id"], self.values[0])
            message = f"✅ Đã gia nhập **{faction['name_vi']}**."
        except faction_engine.FactionError as e:
            await interaction.response.send_message(f"⚠️ {e}", ephemeral=True)
            return
        character = db.get_character(str(interaction.user.id))
        embed, view = build_faction_list_view(character)
        embed.add_field(name="Kết quả", value=message, inline=False)
        await interaction.response.edit_message(embed=embed, view=view)


class LeaveFactionButton(discord.ui.Button):
    def __init__(self):
        super().__init__(label="Rời Faction", emoji="🚪", style=discord.ButtonStyle.danger, row=1)

    @error_handler.safe_interaction(lambda: FactionMenuView())
    async def callback(self, interaction: discord.Interaction):
        character = db.get_character(str(interaction.user.id))
        try:
            faction_engine.leave_faction(character["character_id"])
        except faction_engine.FactionError as e:
            await interaction.response.send_message(f"⚠️ {e}", ephemeral=True)
            return
        character = db.get_character(str(interaction.user.id))
        embed, view = build_faction_list_view(character)
        await interaction.response.edit_message(embed=embed, view=view)


class DonateModal(discord.ui.Modal, title="Quyên góp"):
    """mục 33-34: Donate -> Reputation thật qua faction_engine.donate(),
    KHÔNG chỉ hiện số Bảng bị trừ mà không đổi gì (mục 15/51)."""
    amount = discord.ui.TextInput(label="Số Bảng muốn quyên góp", max_length=10)

    @error_handler.safe_interaction(lambda: FactionMenuView())
    async def on_submit(self, interaction: discord.Interaction):
        character = db.get_character(str(interaction.user.id))
        try:
            amount = int(str(self.amount))
        except ValueError:
            await interaction.response.send_message("⚠️ Số Bảng phải là số nguyên.", ephemeral=True)
            return
        try:
            result = faction_engine.donate(character["character_id"], amount)
        except faction_engine.FactionError as e:
            await interaction.response.send_message(f"⚠️ {e}", ephemeral=True)
            return
        character = db.get_character(str(interaction.user.id))
        org_embed, view = (
            build_church_view(character) if result["is_church"] else build_faction_list_view(character)
        )
        org_embed.add_field(
            name="Kết quả",
            value=(
                f"✅ Quyên góp thành công (+{result['gained']} Reputation).\n"
                f"Reputation hiện tại: **{result['reputation']}** ({result['rank']})"
            ),
            inline=False,
        )
        await interaction.response.edit_message(embed=org_embed, view=view)


class DonateButton(discord.ui.Button):
    def __init__(self):
        super().__init__(label="Quyên góp", emoji="💰", style=discord.ButtonStyle.secondary, row=2)

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.send_modal(DonateModal())


def build_mission_list_embed(character: dict):
    """mục 33-34: danh sách Mission thật của Church/Faction hiện tại — Rank
    thấp bị khoá rõ ràng, kill_progress lấy từ combat thật, không phải
    thanh tiến độ giả."""
    icon = ICONS["faction"]
    missions = faction_engine.list_missions(character["character_id"])
    embed = discord.Embed(title=f"{icon} MISSION", color=discord.Color.dark_gold())
    if not missions:
        embed.description = "Tổ chức của bạn hiện chưa có Mission nào."
        return embed, missions

    for m in missions:
        monster = db.get_monster(m["monster_id"])
        monster_name = monster["name_en"] if monster else m["monster_id"]
        if m["claimed"]:
            status = "✅ Đã nhận thưởng"
        elif not m["unlocked"]:
            status = f"🔒 Cần Reputation >= {m['min_reputation']}"
        elif m["accepted"]:
            status = f"⏳ Tiến độ: {m['kill_progress']}/{m['required_kills']}"
        else:
            status = "🆕 Có thể nhận"
        embed.add_field(
            name=m["name_vi"],
            value=(
                f"Săn: {monster_name} x{m['required_kills']}\n"
                f"Thưởng: {m['reward_money']} Bảng, {m['reward_exp']} EXP, "
                f"{m['reward_reputation']} Reputation\n"
                f"Trạng thái: {status}"
            ),
            inline=False,
        )
    return embed, missions


class MissionAcceptSelect(discord.ui.Select):
    def __init__(self, missions: list):
        acceptable = [m for m in missions if m["unlocked"] and not m["accepted"]]
        options = [
            discord.SelectOption(label=m["name_vi"], value=m["mission_id"])
            for m in acceptable
        ] or [discord.SelectOption(label="(Không có Mission khả dụng)", value="_none")]
        super().__init__(placeholder="🆕 Nhận Mission", options=options, row=0, disabled=not acceptable)

    @error_handler.safe_interaction(lambda: FactionMenuView())
    async def callback(self, interaction: discord.Interaction):
        character = db.get_character(str(interaction.user.id))
        try:
            faction_engine.accept_mission(character["character_id"], self.values[0])
        except faction_engine.FactionError as e:
            await interaction.response.send_message(f"⚠️ {e}", ephemeral=True)
            return
        character = db.get_character(str(interaction.user.id))
        embed, missions = build_mission_list_embed(character)
        embed.add_field(name="Kết quả", value="✅ Đã nhận Mission.", inline=False)
        await interaction.response.edit_message(embed=embed, view=MissionListView(missions))


class MissionClaimSelect(discord.ui.Select):
    def __init__(self, missions: list):
        claimable = [m for m in missions if m["accepted"] and not m["claimed"]
                     and m["kill_progress"] >= m["required_kills"]]
        options = [
            discord.SelectOption(label=m["name_vi"], value=m["mission_id"])
            for m in claimable
        ] or [discord.SelectOption(label="(Chưa có Mission hoàn thành)", value="_none")]
        super().__init__(placeholder="🎁 Nhận thưởng Mission", options=options, row=1, disabled=not claimable)

    @error_handler.safe_interaction(lambda: FactionMenuView())
    async def callback(self, interaction: discord.Interaction):
        character = db.get_character(str(interaction.user.id))
        try:
            faction_engine.claim_mission(character["character_id"], self.values[0])
        except faction_engine.FactionError as e:
            await interaction.response.send_message(f"⚠️ {e}", ephemeral=True)
            return
        character = db.get_character(str(interaction.user.id))
        embed, missions = build_mission_list_embed(character)
        embed.add_field(name="Kết quả", value="✅ Đã nhận thưởng.", inline=False)
        await interaction.response.edit_message(embed=embed, view=MissionListView(missions))


class MissionListView(SafeView):
    def __init__(self, missions: list):
        super().__init__(timeout=180)
        self.add_item(MissionAcceptSelect(missions))
        self.add_item(MissionClaimSelect(missions))
        self.add_item(BackButton(FactionMenuView))


class MissionListButton(discord.ui.Button):
    def __init__(self):
        super().__init__(label="Mission", emoji="📜", style=discord.ButtonStyle.primary, row=2)

    @error_handler.safe_interaction(lambda: FactionMenuView())
    async def callback(self, interaction: discord.Interaction):
        character = db.get_character(str(interaction.user.id))
        try:
            embed, missions = build_mission_list_embed(character)
        except faction_engine.FactionError as e:
            await interaction.response.send_message(f"⚠️ {e}", ephemeral=True)
            return
        await interaction.response.edit_message(embed=embed, view=MissionListView(missions))


class FactionActionsView(SafeView):
    def __init__(self, factions: list, has_current: bool):
        super().__init__(timeout=180)
        self.add_item(JoinFactionSelect(factions))
        if has_current:
            self.add_item(LeaveFactionButton())
            self.add_item(DonateButton())
            self.add_item(MissionListButton())
        self.add_item(BackButton(FactionMenuView))


def build_tarot_view(character: dict):
    icon = ICONS["tarot"]
    membership = tarot_engine.get_membership(character["character_id"])
    embed = discord.Embed(title=f"{icon} TAROT CLUB", color=discord.Color.dark_magenta())
    embed.description = tarot_engine.description()
    if membership:
        embed.add_field(name="Mật danh của bạn", value=f"**{membership['tarot_seat']}**", inline=False)
        meetings = tarot_engine.list_meetings()
        if meetings:
            lines = [f"#{m['meeting_id']} — {m['topic_vi']} (triệu tập bởi {m['called_by_seat']})" for m in meetings[:5]]
            embed.add_field(name="Hội nghị gần đây", value="\n".join(lines), inline=False)
        else:
            embed.add_field(name="Hội nghị", value="Chưa có hội nghị nào được triệu tập.", inline=False)
    else:
        remaining = len(tarot_engine.available_seats())
        embed.add_field(name="Trạng thái", value=f"Bạn chưa gia nhập. Còn {remaining} mật danh trống.", inline=False)
    return embed, TarotActionsView(bool(membership), meetings if membership else [])


class JoinTarotButton(discord.ui.Button):
    def __init__(self):
        super().__init__(label="Xin gia nhập", emoji="🃏", style=discord.ButtonStyle.primary, row=1)

    @error_handler.safe_interaction(lambda: FactionMenuView())
    async def callback(self, interaction: discord.Interaction):
        character = db.get_character(str(interaction.user.id))
        try:
            seat = tarot_engine.request_join(character["character_id"])
            message = f"✅ Bạn đã được cấp mật danh **{seat}**."
        except tarot_engine.TarotError as e:
            await interaction.response.send_message(f"⚠️ {e}", ephemeral=True)
            return
        character = db.get_character(str(interaction.user.id))
        embed, view = build_tarot_view(character)
        embed.add_field(name="Kết quả", value=message, inline=False)
        await interaction.response.edit_message(embed=embed, view=view)


class LeaveTarotButton(discord.ui.Button):
    def __init__(self):
        super().__init__(label="Rời Tarot Club", emoji="🚪", style=discord.ButtonStyle.danger, row=1)

    @error_handler.safe_interaction(lambda: FactionMenuView())
    async def callback(self, interaction: discord.Interaction):
        character = db.get_character(str(interaction.user.id))
        try:
            tarot_engine.leave(character["character_id"])
        except tarot_engine.TarotError as e:
            await interaction.response.send_message(f"⚠️ {e}", ephemeral=True)
            return
        character = db.get_character(str(interaction.user.id))
        embed, view = build_tarot_view(character)
        await interaction.response.edit_message(embed=embed, view=view)


class CallTarotMeetingModal(discord.ui.Modal, title="Triệu tập hội nghị Tarot"):
    topic = discord.ui.TextInput(label="Chủ đề", max_length=200, placeholder="Vd: Trao đổi thông tin về...")

    @error_handler.safe_interaction(lambda: FactionMenuView())
    async def on_submit(self, interaction: discord.Interaction):
        character = db.get_character(str(interaction.user.id))
        try:
            tarot_engine.call_meeting(character["character_id"], str(self.topic))
        except tarot_engine.TarotError as e:
            await interaction.response.send_message(f"⚠️ {e}", ephemeral=True)
            return
        character = db.get_character(str(interaction.user.id))
        embed, view = build_tarot_view(character)
        await interaction.response.edit_message(embed=embed, view=view)


class CallTarotMeetingButton(discord.ui.Button):
    def __init__(self):
        super().__init__(label="Triệu tập hội nghị", emoji="📜", style=discord.ButtonStyle.secondary, row=1)

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.send_modal(CallTarotMeetingModal())


class TarotActionsView(SafeView):
    def __init__(self, is_member: bool, meetings: list = None):
        super().__init__(timeout=180)
        if is_member:
            self.add_item(CallTarotMeetingButton())
            self.add_item(LeaveTarotButton())
            # mục 35: tarot.post_message()/list_messages() có sẵn trong engine
            # + DB (tarot_messages) nhưng trước đây chưa từng nối vào UI —
            # Character Identity != Tarot Identity vẫn được giữ đúng nguyên
            # tắc (chỉ hiện tarot_seat, không bao giờ hiện tên thật).
            self.add_item(OpenMeetingSelect(meetings or []))
        else:
            self.add_item(JoinTarotButton())
        self.add_item(BackButton(FactionMenuView))


def build_tarot_meeting_view(character: dict, meeting_id: int):
    membership = tarot_engine.get_membership(character["character_id"])
    meeting = next((m for m in tarot_engine.list_meetings() if m["meeting_id"] == meeting_id), None)
    icon = ICONS["tarot"]
    embed = discord.Embed(title=f"{icon} HỘI NGHỊ #{meeting_id}", color=discord.Color.dark_magenta())
    if meeting is None:
        embed.description = "Hội nghị này không còn tồn tại."
        return embed, SimpleBackView(FactionMenuView)
    embed.description = f"Chủ đề: **{meeting['topic_vi']}**\nTriệu tập bởi: {meeting['called_by_seat']}"
    messages = tarot_engine.list_messages(meeting_id)
    if messages:
        lines = [f"**{m['from_seat']}**: {m['content_vi']}" for m in messages[-10:]]
        embed.add_field(name="Thông điệp (10 gần nhất)", value="\n".join(lines)[:1024], inline=False)
    else:
        embed.add_field(name="Thông điệp", value="Chưa có thông điệp nào.", inline=False)
    embed.set_footer(text=f"Bạn đang gửi với mật danh {membership['tarot_seat']}")
    return embed, TarotMeetingView(meeting_id)


class OpenMeetingSelect(discord.ui.Select):
    def __init__(self, meetings: list):
        options = [
            discord.SelectOption(label=f"#{m['meeting_id']} {m['topic_vi'][:80]}", value=str(m["meeting_id"]))
            for m in meetings[:20]
        ] or [discord.SelectOption(label="(Chưa có hội nghị nào)", value="_none")]
        super().__init__(placeholder="📖 Mở hội nghị", options=options, row=2, disabled=not meetings)

    @error_handler.safe_interaction(lambda: FactionMenuView())
    async def callback(self, interaction: discord.Interaction):
        character = db.get_character(str(interaction.user.id))
        embed, view = build_tarot_meeting_view(character, int(self.values[0]))
        await interaction.response.edit_message(embed=embed, view=view)


class PostTarotMessageModal(discord.ui.Modal, title="Gửi thông điệp ẩn danh"):
    content = discord.ui.TextInput(label="Nội dung", max_length=500, style=discord.TextStyle.paragraph)

    def __init__(self, meeting_id: int):
        super().__init__()
        self.meeting_id = meeting_id

    @error_handler.safe_interaction(lambda: FactionMenuView())
    async def on_submit(self, interaction: discord.Interaction):
        character = db.get_character(str(interaction.user.id))
        try:
            tarot_engine.post_message(character["character_id"], self.meeting_id, str(self.content))
        except tarot_engine.TarotError as e:
            await interaction.response.send_message(f"⚠️ {e}", ephemeral=True)
            return
        embed, view = build_tarot_meeting_view(character, self.meeting_id)
        await interaction.response.edit_message(embed=embed, view=view)


class PostTarotMessageButton(discord.ui.Button):
    def __init__(self, meeting_id: int):
        super().__init__(label="Gửi thông điệp", emoji="✉️", style=discord.ButtonStyle.primary, row=0)
        self.meeting_id = meeting_id

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.send_modal(PostTarotMessageModal(self.meeting_id))


class TarotMeetingView(SafeView):
    def __init__(self, meeting_id: int):
        super().__init__(timeout=180)
        self.add_item(PostTarotMessageButton(meeting_id))
        self.add_item(BackButton(FactionMenuView))


def build_party_view(character: dict):
    icon = ICONS["party"]
    party = party_engine.get_party(character["character_id"])
    embed = discord.Embed(title=f"{icon} ĐỘI NHÓM", color=discord.Color.green())
    if party:
        lines = [f"{'👑' if m['role'] == 'leader' else '•'} {m['name']} (Lv{m['level']}, Seq {m['sequence_number']})" for m in party["members"]]
        embed.description = "\n".join(lines)
        embed.set_footer(text=f"{len(party['members'])}/{party_engine.db.MAX_PARTY_SIZE} thành viên")
    else:
        embed.description = "Bạn chưa ở trong Đội nhóm nào."
    return embed, PartyActionsView(bool(party))


class CreatePartyButton(discord.ui.Button):
    def __init__(self):
        super().__init__(label="Tạo đội", emoji="👥", style=discord.ButtonStyle.primary, row=1)

    @error_handler.safe_interaction(lambda: FactionMenuView())
    async def callback(self, interaction: discord.Interaction):
        character = db.get_character(str(interaction.user.id))
        try:
            party_engine.create_party(character["character_id"])
        except party_engine.PartyError as e:
            await interaction.response.send_message(f"⚠️ {e}", ephemeral=True)
            return
        character = db.get_character(str(interaction.user.id))
        embed, view = build_party_view(character)
        await interaction.response.edit_message(embed=embed, view=view)


class InvitePartySelect(discord.ui.UserSelect):
    def __init__(self):
        super().__init__(placeholder=f"{ICONS['party']} Mời người chơi vào đội", row=1)

    @error_handler.safe_interaction(lambda: FactionMenuView())
    async def callback(self, interaction: discord.Interaction):
        character = db.get_character(str(interaction.user.id))
        target = db.get_character(str(self.values[0].id))
        if target is None:
            await interaction.response.send_message("Người chơi này chưa có nhân vật.", ephemeral=True)
            return
        party = party_engine.get_party(character["character_id"])
        try:
            party_engine.join_party(target["character_id"], party["party_id"])
            message = f"✅ Đã mời **{target['name']}** vào đội."
        except party_engine.PartyError as e:
            await interaction.response.send_message(f"⚠️ {e}", ephemeral=True)
            return
        character = db.get_character(str(interaction.user.id))
        embed, view = build_party_view(character)
        embed.add_field(name="Kết quả", value=message, inline=False)
        await interaction.response.edit_message(embed=embed, view=view)


class LeavePartyButton(discord.ui.Button):
    def __init__(self):
        super().__init__(label="Rời đội", emoji="🚪", style=discord.ButtonStyle.danger, row=2)

    @error_handler.safe_interaction(lambda: FactionMenuView())
    async def callback(self, interaction: discord.Interaction):
        character = db.get_character(str(interaction.user.id))
        try:
            party_engine.leave_party(character["character_id"])
        except party_engine.PartyError as e:
            await interaction.response.send_message(f"⚠️ {e}", ephemeral=True)
            return
        character = db.get_character(str(interaction.user.id))
        embed, view = build_party_view(character)
        await interaction.response.edit_message(embed=embed, view=view)


class PartyActionsView(SafeView):
    def __init__(self, has_party: bool):
        super().__init__(timeout=180)
        if has_party:
            self.add_item(InvitePartySelect())
            self.add_item(LeavePartyButton())
        else:
            self.add_item(CreatePartyButton())
        self.add_item(BackButton(FactionMenuView))


# ---------------------------------------------------------------------------
# 🛡️ Guild — Player-created (mục 34 mở rộng)
# ---------------------------------------------------------------------------

def build_guild_hub_view(character: dict):
    icon = ICONS["guild"]
    if character is None:
        return build_stub_embed("Guild", icon), SimpleBackView(FactionMenuView)

    my_guild = guild_engine.get_my_guild(character["character_id"])
    if my_guild is None:
        guilds = guild_engine.list_guilds()
        embed = discord.Embed(title=f"{icon} GUILD", color=discord.Color.dark_blue())
        embed.description = (
            f"Bạn chưa thuộc Guild nào. Lập Guild mới tốn "
            f"{guild_engine.GUILD_FOUNDING_COST:,} Bảng."
        )
        if not guilds:
            embed.add_field(name="—", value="Chưa có Guild nào được lập.", inline=False)
        for g in guilds[:10]:
            embed.add_field(
                name=g["name"],
                value=f"Quỹ: {g['treasury']:,} Bảng · Thành viên: {g['member_count']}",
                inline=False,
            )
        return embed, GuildBrowseView()

    embed = discord.Embed(title=f"{icon} {my_guild['name']}", color=discord.Color.dark_blue())
    embed.description = my_guild["description_vi"] or "—"
    embed.add_field(name="Cấp bậc của bạn", value=GUILD_RANK_LABEL_VI.get(my_guild["rank"], my_guild["rank"]), inline=True)
    embed.add_field(name="Quỹ Guild", value=f"{my_guild['treasury']:,} Bảng", inline=True)
    members = guild_engine.get_members(my_guild["guild_id"])
    embed.add_field(name="Thành viên", value=str(len(members)), inline=True)

    war = guild_engine.get_active_war(my_guild["guild_id"])
    if war:
        atk = db.get_guild(war["attacker_guild_id"])
        dfd = db.get_guild(war["defender_guild_id"])
        embed.add_field(
            name="⚔️ Guild War đang diễn ra",
            value=(
                f"{atk['name']} ({war['attacker_score']}) vs {dfd['name']} ({war['defender_score']}) "
                f"— thắng {war['win_threshold']} điểm để kết thúc"
            ),
            inline=False,
        )

    member_lines = [
        f"{GUILD_RANK_LABEL_VI.get(m['rank'], m['rank'])} — {m['character_name']}" for m in members[:10]
    ]
    embed.add_field(name="Danh sách (tối đa 10)", value="\n".join(member_lines) or "—", inline=False)

    return embed, GuildDetailView(my_guild, character["character_id"])


GUILD_RANK_LABEL_VI = {"leader": "👑 Leader", "officer": "🎖️ Officer", "member": "Thành viên"}


class GuildCreateModal(discord.ui.Modal, title="Lập Guild mới"):
    name = discord.ui.TextInput(label="Tên Guild", max_length=40)
    description = discord.ui.TextInput(
        label="Mô tả", max_length=200, required=False, style=discord.TextStyle.paragraph
    )

    @error_handler.safe_interaction(lambda: FactionMenuView())
    async def on_submit(self, interaction: discord.Interaction):
        character = db.get_character(str(interaction.user.id))
        try:
            guild_engine.create_guild(character["character_id"], str(self.name), str(self.description or ""))
        except guild_engine.GuildError as e:
            await interaction.response.send_message(f"⚠️ {e}", ephemeral=True)
            return
        character = db.get_character(str(interaction.user.id))
        embed, view = build_guild_hub_view(character)
        embed.add_field(name="Kết quả", value="✅ Đã lập Guild.", inline=False)
        await interaction.response.edit_message(embed=embed, view=view)


class GuildCreateButton(discord.ui.Button):
    def __init__(self):
        super().__init__(label="Lập Guild", emoji="🛡️", style=discord.ButtonStyle.primary, row=1)

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.send_modal(GuildCreateModal())


class GuildBrowseView(SafeView):
    def __init__(self):
        super().__init__(timeout=180)
        self.add_item(GuildCreateButton())
        self.add_item(BackButton(FactionMenuView))


class GuildDepositModal(discord.ui.Modal, title="Nộp quỹ Guild"):
    amount = discord.ui.TextInput(label="Số Bảng muốn nộp", max_length=10)

    @error_handler.safe_interaction(lambda: FactionMenuView())
    async def on_submit(self, interaction: discord.Interaction):
        character = db.get_character(str(interaction.user.id))
        try:
            amount = int(str(self.amount))
        except ValueError:
            await interaction.response.send_message("⚠️ Số Bảng phải là số nguyên.", ephemeral=True)
            return
        try:
            guild_engine.deposit(character["character_id"], amount)
        except guild_engine.GuildError as e:
            await interaction.response.send_message(f"⚠️ {e}", ephemeral=True)
            return
        character = db.get_character(str(interaction.user.id))
        embed, view = build_guild_hub_view(character)
        embed.add_field(name="Kết quả", value="✅ Đã nộp quỹ.", inline=False)
        await interaction.response.edit_message(embed=embed, view=view)


class GuildDepositButton(discord.ui.Button):
    def __init__(self):
        super().__init__(label="Nộp quỹ", emoji="💰", style=discord.ButtonStyle.secondary, row=1)

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.send_modal(GuildDepositModal())


class GuildWithdrawModal(discord.ui.Modal, title="Rút quỹ Guild"):
    amount = discord.ui.TextInput(label="Số Bảng muốn rút", max_length=10)

    @error_handler.safe_interaction(lambda: FactionMenuView())
    async def on_submit(self, interaction: discord.Interaction):
        character = db.get_character(str(interaction.user.id))
        try:
            amount = int(str(self.amount))
        except ValueError:
            await interaction.response.send_message("⚠️ Số Bảng phải là số nguyên.", ephemeral=True)
            return
        try:
            guild_engine.withdraw(character["character_id"], amount)
        except guild_engine.GuildError as e:
            await interaction.response.send_message(f"⚠️ {e}", ephemeral=True)
            return
        character = db.get_character(str(interaction.user.id))
        embed, view = build_guild_hub_view(character)
        embed.add_field(name="Kết quả", value="✅ Đã rút quỹ.", inline=False)
        await interaction.response.edit_message(embed=embed, view=view)


class GuildWithdrawButton(discord.ui.Button):
    def __init__(self):
        super().__init__(label="Rút quỹ", emoji="💸", style=discord.ButtonStyle.secondary, row=1)

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.send_modal(GuildWithdrawModal())


class GuildRecruitSelect(discord.ui.UserSelect):
    def __init__(self):
        super().__init__(placeholder="🛡️ Tuyển thành viên (chọn user Discord)", row=2)

    @error_handler.safe_interaction(lambda: FactionMenuView())
    async def callback(self, interaction: discord.Interaction):
        character = db.get_character(str(interaction.user.id))
        target = db.get_character(str(self.values[0].id))
        if target is None:
            await interaction.response.send_message("⚠️ Người này chưa có nhân vật.", ephemeral=True)
            return
        try:
            guild_engine.recruit_member(character["character_id"], target["character_id"])
        except guild_engine.GuildError as e:
            await interaction.response.send_message(f"⚠️ {e}", ephemeral=True)
            return
        character = db.get_character(str(interaction.user.id))
        embed, view = build_guild_hub_view(character)
        embed.add_field(name="Kết quả", value=f"✅ Đã tuyển {target['name']} vào Guild.", inline=False)
        await interaction.response.edit_message(embed=embed, view=view)


class GuildLeaveButton(discord.ui.Button):
    def __init__(self):
        super().__init__(label="Rời Guild", emoji="🚪", style=discord.ButtonStyle.danger, row=3)

    async def callback(self, interaction: discord.Interaction):
        character = db.get_character(str(interaction.user.id))
        try:
            guild_engine.leave_guild(character["character_id"])
        except guild_engine.GuildError as e:
            await interaction.response.send_message(f"⚠️ {e}", ephemeral=True)
            return
        character = db.get_character(str(interaction.user.id))
        embed, view = build_guild_hub_view(character)
        embed.add_field(name="Kết quả", value="✅ Đã rời Guild.", inline=False)
        await interaction.response.edit_message(embed=embed, view=view)


class GuildDisbandButton(discord.ui.Button):
    def __init__(self):
        super().__init__(label="Giải tán Guild", emoji="💥", style=discord.ButtonStyle.danger, row=4)

    async def callback(self, interaction: discord.Interaction):
        character = db.get_character(str(interaction.user.id))
        try:
            guild_engine.disband_guild(character["character_id"])
        except guild_engine.GuildError as e:
            await interaction.response.send_message(f"⚠️ {e}", ephemeral=True)
            return
        character = db.get_character(str(interaction.user.id))
        embed, view = build_guild_hub_view(character)
        embed.add_field(name="Kết quả", value="✅ Đã giải tán Guild.", inline=False)
        await interaction.response.edit_message(embed=embed, view=view)


class GuildDeclareWarSelect(discord.ui.Select):
    def __init__(self, my_guild_id: int):
        others = [g for g in guild_engine.list_guilds() if g["guild_id"] != my_guild_id]
        options = [
            discord.SelectOption(label=g["name"][:100], value=str(g["guild_id"]))
            for g in others
        ] or [discord.SelectOption(label="Không có Guild nào khác", value="_none")]
        super().__init__(placeholder="⚔️ Tuyên chiến với Guild", options=options, row=3)

    @error_handler.safe_interaction(lambda: FactionMenuView())
    async def callback(self, interaction: discord.Interaction):
        if self.values[0] == "_none":
            await interaction.response.defer()
            return
        character = db.get_character(str(interaction.user.id))
        try:
            guild_engine.declare_war(character["character_id"], int(self.values[0]))
        except guild_engine.GuildError as e:
            await interaction.response.send_message(f"⚠️ {e}", ephemeral=True)
            return
        character = db.get_character(str(interaction.user.id))
        embed, view = build_guild_hub_view(character)
        embed.add_field(name="Kết quả", value="⚔️ Đã tuyên chiến!", inline=False)
        await interaction.response.edit_message(embed=embed, view=view)


class GuildKickSelect(discord.ui.Select):
    def __init__(self, kicker_character_id: int, members: list):
        kickable = [m for m in members if m["character_id"] != kicker_character_id and m["rank"] != "leader"]
        options = [
            discord.SelectOption(label=m["character_name"], value=str(m["character_id"]))
            for m in kickable
        ] or [discord.SelectOption(label="(Không có thành viên để kick)", value="_none")]
        super().__init__(placeholder="🥾 Kick thành viên", options=options, row=0, disabled=not kickable)

    @error_handler.safe_interaction(lambda: FactionMenuView())
    async def callback(self, interaction: discord.Interaction):
        character = db.get_character(str(interaction.user.id))
        try:
            guild_engine.kick_member(character["character_id"], int(self.values[0]))
        except guild_engine.GuildError as e:
            await interaction.response.send_message(f"⚠️ {e}", ephemeral=True)
            return
        character = db.get_character(str(interaction.user.id))
        embed, view = build_guild_hub_view(character)
        embed.add_field(name="Kết quả", value="✅ Đã kick thành viên khỏi Guild.", inline=False)
        await interaction.response.edit_message(embed=embed, view=view)


class GuildDetailView(SafeView):
    def __init__(self, my_guild: dict, viewer_character_id: int):
        super().__init__(timeout=180)
        rank = my_guild["rank"]
        self.add_item(GuildDepositButton())
        if rank in ("leader", "officer"):
            self.add_item(GuildWithdrawButton())
            self.add_item(GuildRecruitSelect())
            # mục 34 mở rộng: guild.kick_member() có sẵn trong engine + DB
            # nhưng trước đây chưa từng nối vào UI — Leader/Officer không có
            # cách nào loại bỏ thành viên gây rối.
            members = guild_engine.get_members(my_guild["guild_id"])
            self.add_item(GuildKickSelect(viewer_character_id, members))
        if rank == "leader":
            self.add_item(GuildDeclareWarSelect(my_guild["guild_id"]))
            self.add_item(GuildDisbandButton())
        else:
            self.add_item(GuildLeaveButton())
        self.add_item(BackButton(FactionMenuView))


# ---------------------------------------------------------------------------
# 💰 Giao dịch — Market / Trade / Contract / Bounty (mục 37-40, 59)
# ---------------------------------------------------------------------------

def build_economy_hub_embed(character: dict) -> discord.Embed:
    icon = ICONS["economy"]
    embed = discord.Embed(title=f"{icon} GIAO DỊCH", color=discord.Color.dark_gold())
    if character is None:
        embed.description = "Bạn chưa có nhân vật."
        return embed
    embed.description = f"💰 {character['money']:,} Bảng"
    return embed


class EconomyMenuSelect(discord.ui.Select):
    OPTIONS = [
        ("market", "Chợ", ICONS["market"]),
        ("black_market", "Chợ đen", ICONS["black_market"]),
        ("auction", "Đấu giá", ICONS["auction"]),
        ("trade", "Trade trực tiếp", ICONS["trade"]),
        ("contract", "Khế ước", ICONS["contract"]),
        ("bounty", "Truy nã", ICONS["bounty"]),
    ]

    def __init__(self):
        options = [discord.SelectOption(label=l, value=k, emoji=i) for k, l, i in self.OPTIONS]
        super().__init__(placeholder="💰 Chọn chức năng", options=options, row=0)

    @error_handler.safe_interaction(lambda: EconomyMenuView())
    async def callback(self, interaction: discord.Interaction):
        character = db.get_character(str(interaction.user.id))
        key = self.values[0]
        if key == "market":
            embed, view = build_market_view(character)
        elif key == "black_market":
            embed, view = build_black_market_view(character)
        elif key == "auction":
            embed, view = build_auction_view(character)
        elif key == "trade":
            embed, view = build_trade_view(character)
        elif key == "contract":
            embed, view = build_contract_view(character)
        else:
            embed, view = build_bounty_view(character)
        await interaction.response.edit_message(embed=embed, view=view)


class EconomyMenuView(SafeView):
    def __init__(self):
        super().__init__(timeout=180)
        self.add_item(EconomyMenuSelect())
        self.add_item(BackButton(MainMenuView))


def build_market_view(character: dict):
    icon = ICONS["market"]
    listings = economy_engine.list_market(15)
    embed = discord.Embed(title=f"{icon} CHỢ", color=discord.Color.orange())
    embed.description = f"💰 {character['money']:,} Bảng"
    if not listings:
        embed.add_field(name="—", value="Chợ hiện không có ai rao bán.", inline=False)
    for l in listings:
        embed.add_field(
            name=f"#{l['listing_id']} — {l['name_vi']} ×{l['quantity']}",
            value=f"Giá: {l['price_per_unit']:,}/cái (tổng {l['price_per_unit']*l['quantity']:,} Bảng) · Người bán: {l['seller_name']}",
            inline=False,
        )
    return embed, MarketActionsView(listings)


class BuyListingSelect(discord.ui.Select):
    def __init__(self, listings: list):
        options = [
            discord.SelectOption(
                label=f"#{l['listing_id']} {l['name_vi']} ×{l['quantity']}",
                value=str(l["listing_id"]),
                description=f"{l['price_per_unit']*l['quantity']:,} Bảng"[:100],
            )
            for l in listings
        ]
        super().__init__(placeholder=f"{ICONS['market']} Mua vật phẩm", options=options, row=0)

    @error_handler.safe_interaction(lambda: EconomyMenuView())
    async def callback(self, interaction: discord.Interaction):
        character = db.get_character(str(interaction.user.id))
        try:
            listing = economy_engine.buy_from_market(character["character_id"], int(self.values[0]))
            message = f"✅ Đã mua **{listing['name_vi']}** ×{listing['quantity']}."
        except economy_engine.EconomyError as e:
            await interaction.response.send_message(f"⚠️ {e}", ephemeral=True)
            return
        character = db.get_character(str(interaction.user.id))
        embed, view = build_market_view(character)
        embed.add_field(name="Kết quả", value=message, inline=False)
        await interaction.response.edit_message(embed=embed, view=view)


class SellItemModal(discord.ui.Modal, title="Rao bán vật phẩm"):
    quantity = discord.ui.TextInput(label="Số lượng", max_length=6, default="1")
    price = discord.ui.TextInput(label="Giá mỗi cái (Bảng)", max_length=10)

    def __init__(self, item_id: str, item_name: str):
        super().__init__()
        self.item_id = item_id
        self.title = f"Rao bán: {item_name}"[:45]

    @error_handler.safe_interaction(lambda: EconomyMenuView())
    async def on_submit(self, interaction: discord.Interaction):
        character = db.get_character(str(interaction.user.id))
        try:
            qty = int(str(self.quantity))
            unit_price = int(str(self.price))
        except ValueError:
            await interaction.response.send_message("⚠️ Số lượng và giá phải là số nguyên.", ephemeral=True)
            return
        try:
            economy_engine.sell_on_market(character["character_id"], self.item_id, qty, unit_price)
            message = "✅ Đã đăng tin rao bán."
        except economy_engine.EconomyError as e:
            await interaction.response.send_message(f"⚠️ {e}", ephemeral=True)
            return
        character = db.get_character(str(interaction.user.id))
        embed, view = build_market_view(character)
        embed.add_field(name="Kết quả", value=message, inline=False)
        await interaction.response.edit_message(embed=embed, view=view)


class SellItemPickSelect(discord.ui.Select):
    """Người chơi chọn vật phẩm từ chính Túi đồ của mình — không cần biết
    hay gõ mã item_id kỹ thuật."""

    def __init__(self, items: list):
        options = [
            discord.SelectOption(label=f"{it['name_vi']} (×{it['quantity']})", value=it["item_id"])
            for it in items
        ]
        super().__init__(placeholder="🏪 Chọn vật phẩm cần rao bán", options=options, row=0)
        self._items_by_id = {it["item_id"]: it for it in items}

    @error_handler.safe_interaction(lambda: EconomyMenuView())
    async def callback(self, interaction: discord.Interaction):
        item = self._items_by_id[self.values[0]]
        await interaction.response.send_modal(SellItemModal(item["item_id"], item["name_vi"]))


class SellItemPickView(SafeView):
    def __init__(self, items: list):
        super().__init__(timeout=180)
        self.add_item(SellItemPickSelect(items))
        self.add_item(BackButton(EconomyMenuView))


class SellItemButton(discord.ui.Button):
    def __init__(self):
        super().__init__(label="Rao bán", emoji="🏪", style=discord.ButtonStyle.primary, row=1)

    @error_handler.safe_interaction(lambda: EconomyMenuView())
    async def callback(self, interaction: discord.Interaction):
        character = db.get_character(str(interaction.user.id))
        items = [it for it in inv.list_inventory(character["character_id"]) if it["quantity"] > 0]
        if not items:
            await interaction.response.send_message("⚠️ Bạn không có vật phẩm nào để rao bán.", ephemeral=True)
            return
        embed = discord.Embed(
            title=f"{ICONS['market']} Rao bán vật phẩm",
            description="Chọn vật phẩm từ Túi đồ bên dưới.",
            color=discord.Color.orange(),
        )
        await interaction.response.edit_message(embed=embed, view=SellItemPickView(items))


class MarketActionsView(SafeView):
    def __init__(self, listings: list):
        super().__init__(timeout=180)
        if listings:
            self.add_item(BuyListingSelect(listings))
        self.add_item(SellItemButton())
        self.add_item(MyListingsButton())
        self.add_item(BackButton(EconomyMenuView))


class CancelListingSelect(discord.ui.Select):
    def __init__(self, my_listings: list):
        options = [
            discord.SelectOption(
                label=f"#{l['listing_id']} {l['name_vi']} ×{l['quantity']}", value=str(l["listing_id"])
            )
            for l in my_listings
        ] or [discord.SelectOption(label="(Bạn chưa rao bán gì)", value="_none")]
        super().__init__(placeholder="❌ Huỷ tin rao bán", options=options, row=0, disabled=not my_listings)

    @error_handler.safe_interaction(lambda: EconomyMenuView())
    async def callback(self, interaction: discord.Interaction):
        character = db.get_character(str(interaction.user.id))
        try:
            economy_engine.cancel_listing(character["character_id"], int(self.values[0]))
        except economy_engine.EconomyError as e:
            await interaction.response.send_message(f"⚠️ {e}", ephemeral=True)
            return
        character = db.get_character(str(interaction.user.id))
        embed, view = build_market_view(character)
        embed.add_field(name="Kết quả", value="✅ Đã huỷ tin rao bán — vật phẩm về lại Túi đồ.", inline=False)
        await interaction.response.edit_message(embed=embed, view=view)


class MyListingsView(SafeView):
    def __init__(self, my_listings: list):
        super().__init__(timeout=180)
        self.add_item(CancelListingSelect(my_listings))
        self.add_item(BackButton(EconomyMenuView))


class MyListingsButton(discord.ui.Button):
    def __init__(self):
        super().__init__(label="Tin rao bán của tôi", emoji="🗂️", style=discord.ButtonStyle.secondary, row=2)

    @error_handler.safe_interaction(lambda: EconomyMenuView())
    async def callback(self, interaction: discord.Interaction):
        character = db.get_character(str(interaction.user.id))
        # mục 38: economy.cancel_listing() có sẵn trong engine + DB nhưng
        # trước đây chưa từng nối vào menu.py — người bán không có cách nào
        # rút lại tin rao bán của mình. list_market() không lọc theo seller
        # riêng ở tầng DB, nên lọc thẳng tại đây (đơn giản hơn thêm 1 hàm DB
        # mới chỉ để phục vụ đúng 1 màn hình).
        all_listings = economy_engine.list_market(limit=100)
        my_listings = [l for l in all_listings if l["seller_character_id"] == character["character_id"]]
        icon = ICONS["market"]
        embed = discord.Embed(title=f"{icon} TIN RAO BÁN CỦA TÔI", color=discord.Color.orange())
        if not my_listings:
            embed.description = "Bạn hiện không có tin rao bán nào."
        for l in my_listings:
            embed.add_field(
                name=f"#{l['listing_id']} — {l['name_vi']} ×{l['quantity']}",
                value=f"Giá: {l['price_per_unit']:,}/cái (tổng {l['price_per_unit']*l['quantity']:,} Bảng)",
                inline=False,
            )
        await interaction.response.edit_message(embed=embed, view=MyListingsView(my_listings))


# ---------------------------------------------------------------------------
# 🕶️ Chợ đen (mục 41) — giá cố định như Chợ, nhưng mỗi listing có risk_type
# thật (scam/trap/wanted) roll ngay khi mua, KHÔNG chỉ hiển thị cảnh báo suông.
# ---------------------------------------------------------------------------

def build_black_market_view(character: dict):
    lang = i18n.user_lang(character["user_id"])
    icon = ICONS["black_market"]
    listings = black_market_engine.browse_catalog()
    embed = discord.Embed(
        title=f"{icon} {i18n.t('black_market.title', lang).replace(icon + ' ', '')}",
        description=(
            f"💰 {character['money']:,} Bảng\n"
            f"{i18n.t('black_market.description', lang)}"
        ),
        color=discord.Color.dark_grey(),
    )
    if not listings:
        embed.add_field(name="—", value=i18n.t("black_market.no_listings", lang), inline=False)
    for l in listings:
        category_label = i18n.t(f"black_market.category.{l['category']}", lang, default=l["category"])
        risk_label = i18n.t(f"black_market.risk.{l['risk_type']}", lang, default=l["risk_type"])
        embed.add_field(
            name=f"{l['listing_id']} — {category_label}",
            value=(
                f"Giá: {l['price']:,} Bảng · ⚠️ {risk_label}"
                + (f" ({l['risk_chance']}%)" if l["risk_type"] != "none" else "")
                + f"\n{l['description_vi']}"
            ),
            inline=False,
        )
    return embed, BlackMarketActionsView(listings, lang)


class BlackMarketBuySelect(discord.ui.Select):
    def __init__(self, listings: list, lang: str = None):
        options = [
            discord.SelectOption(
                label=f"{l['listing_id']} — {l['price']:,} Bảng",
                value=l["listing_id"],
                description=i18n.t(f"black_market.risk.{l['risk_type']}", lang, default=l["risk_type"])[:100],
            )
            for l in listings
        ]
        super().__init__(
            placeholder=f"{ICONS['black_market']} {i18n.t('black_market.buy_placeholder', lang)}",
            options=options, row=0,
        )

    @error_handler.safe_interaction(lambda: EconomyMenuView())
    async def callback(self, interaction: discord.Interaction):
        character = db.get_character(str(interaction.user.id))
        lang = i18n.user_lang(character["user_id"])
        try:
            result = black_market_engine.buy(character["character_id"], self.values[0], lang)
        except black_market_engine.BlackMarketError as e:
            await interaction.response.send_message(f"⚠️ {e}", ephemeral=True)
            return
        character = db.get_character(str(interaction.user.id))
        embed, view = build_black_market_view(character)
        outcome_icon = {"success": "✅", "scam": "🎭", "trap": "💥", "wanted": "☠️"}.get(result["outcome"], "ℹ️")
        embed.add_field(
            name=f"{outcome_icon} {i18n.t('black_market.result_label', lang)}",
            value=result["detail"], inline=False,
        )
        await interaction.response.edit_message(embed=embed, view=view)


class BlackMarketActionsView(SafeView):
    def __init__(self, listings: list, lang: str = None):
        super().__init__(timeout=180)
        if listings:
            self.add_item(BlackMarketBuySelect(listings, lang))
        self.add_item(BlackMarketHistoryButton())
        self.add_item(BackButton(EconomyMenuView))


class BlackMarketHistoryButton(discord.ui.Button):
    def __init__(self):
        super().__init__(label="Lịch sử giao dịch", emoji="🗒️", style=discord.ButtonStyle.secondary, row=1)

    @error_handler.safe_interaction(lambda: EconomyMenuView())
    async def callback(self, interaction: discord.Interaction):
        character = db.get_character(str(interaction.user.id))
        # mục 41: black_market.history() có sẵn trong engine + DB
        # (black_market_purchase_log) nhưng trước đây chưa từng nối vào UI.
        entries = black_market_engine.history(character["character_id"])
        icon = ICONS["black_market"]
        embed = discord.Embed(title=f"{icon} LỊCH SỬ CHỢ ĐEN", color=discord.Color.dark_grey())
        if not entries:
            embed.description = "Bạn chưa có giao dịch Chợ Đen nào."
        outcome_icon = {"success": "✅", "scam": "🎭", "trap": "💥", "wanted": "☠️"}
        for e in entries[:15]:
            icon_e = outcome_icon.get(e["outcome"], "ℹ️")
            embed.add_field(
                name=f"{icon_e} {e['listing_id']} — {e['created_at']}",
                value=f"Kết quả: {e['outcome']} · Tốn: {e['money_spent']:,} Bảng",
                inline=False,
            )
        await interaction.response.edit_message(embed=embed, view=SimpleBackView(EconomyMenuView))


# ---------------------------------------------------------------------------
# 🔨 Đấu giá (mục 41) — bidding thật, khác Chợ (giá cố định)
# ---------------------------------------------------------------------------

def build_auction_view(character: dict):
    icon = ICONS["auction"]
    auctions = auction_engine.list_active(15)
    embed = discord.Embed(title=f"{icon} ĐẤU GIÁ", color=discord.Color.dark_orange())
    embed.description = f"💰 {character['money']:,} Bảng"
    if not auctions:
        embed.add_field(name="—", value="Hiện không có phiên đấu giá nào.", inline=False)
    for a in auctions:
        bidder = " · Đang có người ra giá" if a["highest_bidder_character_id"] else " · Chưa có ai ra giá"
        embed.add_field(
            name=f"#{a['auction_id']} — {a['name_vi']} ×{a['quantity']}",
            value=(
                f"Giá hiện tại: {a['current_price']:,} Bảng · Kết thúc: {a['ends_at']} · "
                f"Người bán: {a['seller_name']}{bidder}"
            ),
            inline=False,
        )
    return embed, AuctionActionsView(auctions)


class BidAuctionSelect(discord.ui.Select):
    def __init__(self, auctions: list):
        options = [
            discord.SelectOption(
                label=f"#{a['auction_id']} {a['name_vi']} ×{a['quantity']}",
                value=str(a["auction_id"]),
                description=f"Giá hiện tại {a['current_price']:,} Bảng"[:100],
            )
            for a in auctions
        ] or [discord.SelectOption(label="Chưa có phiên nào", value="_none")]
        super().__init__(placeholder=f"{ICONS['auction']} Chọn phiên để ra giá", options=options, row=0)

    async def callback(self, interaction: discord.Interaction):
        if self.values[0] == "_none":
            await interaction.response.defer()
            return
        await interaction.response.send_modal(PlaceBidModal(int(self.values[0])))


class PlaceBidModal(discord.ui.Modal, title="Ra giá đấu giá"):
    amount = discord.ui.TextInput(label="Số Bảng muốn ra giá", max_length=10)

    def __init__(self, auction_id: int):
        super().__init__()
        self.auction_id = auction_id

    @error_handler.safe_interaction(lambda: EconomyMenuView())
    async def on_submit(self, interaction: discord.Interaction):
        character = db.get_character(str(interaction.user.id))
        try:
            amount = int(str(self.amount))
        except ValueError:
            await interaction.response.send_message("⚠️ Số Bảng phải là số nguyên.", ephemeral=True)
            return
        try:
            auction_engine.place_bid(character["character_id"], self.auction_id, amount)
            message = "✅ Đã ra giá thành công."
        except auction_engine.AuctionError as e:
            await interaction.response.send_message(f"⚠️ {e}", ephemeral=True)
            return
        character = db.get_character(str(interaction.user.id))
        embed, view = build_auction_view(character)
        embed.add_field(name="Kết quả", value=message, inline=False)
        await interaction.response.edit_message(embed=embed, view=view)


class CreateAuctionModal(discord.ui.Modal, title="Đăng phiên đấu giá"):
    quantity = discord.ui.TextInput(label="Số lượng", max_length=6, default="1")
    starting_price = discord.ui.TextInput(label="Giá khởi điểm (Bảng)", max_length=10)
    duration_hours = discord.ui.TextInput(label="Thời hạn (giờ, 1-72)", max_length=3, default="24")

    def __init__(self, item_id: str, item_name: str):
        super().__init__()
        self.item_id = item_id
        self.title = f"Đấu giá: {item_name}"[:45]

    @error_handler.safe_interaction(lambda: EconomyMenuView())
    async def on_submit(self, interaction: discord.Interaction):
        character = db.get_character(str(interaction.user.id))
        try:
            qty = int(str(self.quantity))
            price = int(str(self.starting_price))
            hours = int(str(self.duration_hours))
        except ValueError:
            await interaction.response.send_message("⚠️ Số lượng, giá và thời hạn phải là số nguyên.", ephemeral=True)
            return
        try:
            auction_engine.create_auction(character["character_id"], self.item_id, qty, price, hours)
            message = "✅ Đã đăng phiên đấu giá."
        except auction_engine.AuctionError as e:
            await interaction.response.send_message(f"⚠️ {e}", ephemeral=True)
            return
        character = db.get_character(str(interaction.user.id))
        embed, view = build_auction_view(character)
        embed.add_field(name="Kết quả", value=message, inline=False)
        await interaction.response.edit_message(embed=embed, view=view)


class CreateAuctionPickSelect(discord.ui.Select):
    """Người chơi chọn vật phẩm từ Túi đồ để đấu giá — không gõ item_id."""

    def __init__(self, items: list):
        options = [
            discord.SelectOption(label=f"{it['name_vi']} (×{it['quantity']})", value=it["item_id"])
            for it in items
        ]
        super().__init__(placeholder="🔨 Chọn vật phẩm cần đấu giá", options=options, row=0)
        self._items_by_id = {it["item_id"]: it for it in items}

    @error_handler.safe_interaction(lambda: EconomyMenuView())
    async def callback(self, interaction: discord.Interaction):
        item = self._items_by_id[self.values[0]]
        await interaction.response.send_modal(CreateAuctionModal(item["item_id"], item["name_vi"]))


class CreateAuctionPickView(SafeView):
    def __init__(self, items: list):
        super().__init__(timeout=180)
        self.add_item(CreateAuctionPickSelect(items))
        self.add_item(BackButton(EconomyMenuView))


class CreateAuctionButton(discord.ui.Button):
    def __init__(self):
        super().__init__(label="Đăng phiên đấu giá", emoji="🔨", style=discord.ButtonStyle.primary, row=1)

    @error_handler.safe_interaction(lambda: EconomyMenuView())
    async def callback(self, interaction: discord.Interaction):
        character = db.get_character(str(interaction.user.id))
        items = [it for it in inv.list_inventory(character["character_id"]) if it["quantity"] > 0]
        if not items:
            await interaction.response.send_message("⚠️ Bạn không có vật phẩm nào để đấu giá.", ephemeral=True)
            return
        embed = discord.Embed(
            title=f"{ICONS['auction']} Đăng phiên đấu giá",
            description="Chọn vật phẩm từ Túi đồ bên dưới.",
            color=discord.Color.dark_orange(),
        )
        await interaction.response.edit_message(embed=embed, view=CreateAuctionPickView(items))


class AuctionActionsView(SafeView):
    def __init__(self, auctions: list):
        super().__init__(timeout=180)
        if auctions:
            self.add_item(BidAuctionSelect(auctions))
        self.add_item(CreateAuctionButton())
        self.add_item(MyAuctionsButton())
        self.add_item(BackButton(EconomyMenuView))


class CancelAuctionSelect(discord.ui.Select):
    def __init__(self, my_auctions: list):
        cancellable = [a for a in my_auctions if a["highest_bidder_character_id"] is None]
        options = [
            discord.SelectOption(label=f"#{a['auction_id']} {a['name_vi']} ×{a['quantity']}", value=str(a["auction_id"]))
            for a in cancellable
        ] or [discord.SelectOption(label="(Không có phiên có thể huỷ)", value="_none")]
        super().__init__(placeholder="❌ Huỷ phiên đấu giá", options=options, row=0, disabled=not cancellable)

    @error_handler.safe_interaction(lambda: EconomyMenuView())
    async def callback(self, interaction: discord.Interaction):
        character = db.get_character(str(interaction.user.id))
        try:
            auction_engine.cancel_auction(character["character_id"], int(self.values[0]))
        except auction_engine.AuctionError as e:
            await interaction.response.send_message(f"⚠️ {e}", ephemeral=True)
            return
        character = db.get_character(str(interaction.user.id))
        embed, view = build_auction_view(character)
        embed.add_field(name="Kết quả", value="✅ Đã huỷ phiên — vật phẩm về lại Túi đồ.", inline=False)
        await interaction.response.edit_message(embed=embed, view=view)


class MyAuctionsView(SafeView):
    def __init__(self, my_auctions: list):
        super().__init__(timeout=180)
        self.add_item(CancelAuctionSelect(my_auctions))
        self.add_item(BackButton(EconomyMenuView))


class MyAuctionsButton(discord.ui.Button):
    def __init__(self):
        super().__init__(label="Phiên của tôi", emoji="🗂️", style=discord.ButtonStyle.secondary, row=2)

    @error_handler.safe_interaction(lambda: EconomyMenuView())
    async def callback(self, interaction: discord.Interaction):
        character = db.get_character(str(interaction.user.id))
        # mục 41: auction.cancel_auction() có sẵn nhưng chưa từng nối vào UI —
        # người đăng không có cách nào rút lại phiên chưa ai ra giá.
        all_auctions = auction_engine.list_active(limit=100)
        my_auctions = [a for a in all_auctions if a["seller_character_id"] == character["character_id"]]
        icon = ICONS["auction"]
        embed = discord.Embed(title=f"{icon} PHIÊN ĐẤU GIÁ CỦA TÔI", color=discord.Color.dark_orange())
        if not my_auctions:
            embed.description = "Bạn hiện không có phiên đấu giá nào."
        for a in my_auctions:
            bidder = "Đang có người ra giá (không huỷ được)" if a["highest_bidder_character_id"] else "Chưa có ai ra giá"
            embed.add_field(
                name=f"#{a['auction_id']} — {a['name_vi']} ×{a['quantity']}",
                value=f"Giá hiện tại: {a['current_price']:,} Bảng · {bidder}",
                inline=False,
            )
        await interaction.response.edit_message(embed=embed, view=MyAuctionsView(my_auctions))


def build_trade_view(character: dict):
    icon = ICONS["trade"]
    history = economy_engine.trade_history(character["character_id"])
    embed = discord.Embed(title=f"{icon} TRADE TRỰC TIẾP", color=discord.Color.blue())
    embed.description = "Chọn người chơi để giao dịch trực tiếp 1-đổi-1 (an toàn, đồng bộ hai chiều)."
    if history:
        lines = [f"{h['kind']} · {h['quantity'] or ''} {h['item_id'] or ''} · {h['money_amount']:,} Bảng" for h in history[:5]]
        embed.add_field(name="Lịch sử gần đây", value="\n".join(lines), inline=False)
    return embed, TradeActionsView()


class TradePartnerSelect(discord.ui.UserSelect):
    def __init__(self):
        super().__init__(placeholder=f"{ICONS['trade']} Chọn người chơi", row=0)

    @error_handler.safe_interaction(lambda: EconomyMenuView())
    async def callback(self, interaction: discord.Interaction):
        target = db.get_character(str(self.values[0].id))
        if target is None:
            await interaction.response.send_message("Người chơi này chưa có nhân vật.", ephemeral=True)
            return
        character = db.get_character(str(interaction.user.id))
        items = [it for it in inv.list_inventory(character["character_id"]) if it["quantity"] > 0]
        if not items:
            await interaction.response.send_message("⚠️ Bạn không có vật phẩm nào để giao dịch.", ephemeral=True)
            return
        embed = discord.Embed(
            title=f"{ICONS['trade']} Giao dịch với {target['name']}",
            description="Chọn vật phẩm từ Túi đồ bên dưới.",
            color=discord.Color.blue(),
        )
        await interaction.response.edit_message(
            embed=embed, view=DirectTradeItemPickView(target["character_id"], target["name"], items)
        )


class DirectTradeModal(discord.ui.Modal, title="Giao dịch trực tiếp"):
    quantity = discord.ui.TextInput(label="Số lượng", max_length=6, default="1")
    price = discord.ui.TextInput(label="Giá (Bảng, đối phương sẽ trả)", max_length=10)

    def __init__(self, target_character_id: int, target_name: str, item_id: str, item_name: str):
        super().__init__()
        self.target_character_id = target_character_id
        self.item_id = item_id
        self.title = f"Bán {item_name} cho {target_name}"[:45]

    @error_handler.safe_interaction(lambda: EconomyMenuView())
    async def on_submit(self, interaction: discord.Interaction):
        character = db.get_character(str(interaction.user.id))
        try:
            qty = int(str(self.quantity))
            amount = int(str(self.price))
        except ValueError:
            await interaction.response.send_message("⚠️ Số lượng và giá phải là số nguyên.", ephemeral=True)
            return
        try:
            economy_engine.direct_trade(
                character["character_id"], self.target_character_id, self.item_id, qty, amount
            )
            message = "✅ Giao dịch thành công."
        except economy_engine.EconomyError as e:
            await interaction.response.send_message(f"⚠️ {e}", ephemeral=True)
            return
        character = db.get_character(str(interaction.user.id))
        embed, view = build_trade_view(character)
        embed.add_field(name="Kết quả", value=message, inline=False)
        await interaction.response.edit_message(embed=embed, view=view)


class DirectTradeItemPickSelect(discord.ui.Select):
    """Người chơi chọn vật phẩm từ Túi đồ để bán trực tiếp — không gõ item_id."""

    def __init__(self, target_character_id: int, target_name: str, items: list):
        options = [
            discord.SelectOption(label=f"{it['name_vi']} (×{it['quantity']})", value=it["item_id"])
            for it in items
        ]
        super().__init__(placeholder="🤝 Chọn vật phẩm cần bán", options=options, row=0)
        self._items_by_id = {it["item_id"]: it for it in items}
        self.target_character_id = target_character_id
        self.target_name = target_name

    @error_handler.safe_interaction(lambda: EconomyMenuView())
    async def callback(self, interaction: discord.Interaction):
        item = self._items_by_id[self.values[0]]
        await interaction.response.send_modal(
            DirectTradeModal(self.target_character_id, self.target_name, item["item_id"], item["name_vi"])
        )


class DirectTradeItemPickView(SafeView):
    def __init__(self, target_character_id: int, target_name: str, items: list):
        super().__init__(timeout=180)
        self.add_item(DirectTradeItemPickSelect(target_character_id, target_name, items))
        self.add_item(BackButton(EconomyMenuView))


class TradeActionsView(SafeView):
    def __init__(self):
        super().__init__(timeout=180)
        self.add_item(TradePartnerSelect())
        self.add_item(BackButton(EconomyMenuView))


def build_contract_view(character: dict):
    icon = ICONS["contract"]
    contracts = economy_engine.list_open_contracts()
    embed = discord.Embed(title=f"{icon} KHẾ ƯỚC", color=discord.Color.dark_orange())
    if not contracts:
        embed.description = "Hiện không có Khế ước nào đang mở."
    for c in contracts:
        embed.add_field(
            name=f"#{c['contract_id']} — {c['task_vi']}",
            value=f"Thưởng: {c['reward_money']:,} Bảng",
            inline=False,
        )
    return embed, ContractActionsView(contracts)


class AcceptContractSelect(discord.ui.Select):
    def __init__(self, contracts: list):
        options = [
            discord.SelectOption(label=f"#{c['contract_id']} {c['task_vi'][:80]}", value=str(c["contract_id"]))
            for c in contracts
        ]
        super().__init__(placeholder=f"{ICONS['contract']} Nhận Khế ước", options=options, row=0)

    @error_handler.safe_interaction(lambda: EconomyMenuView())
    async def callback(self, interaction: discord.Interaction):
        character = db.get_character(str(interaction.user.id))
        try:
            economy_engine.accept_contract(character["character_id"], int(self.values[0]))
            message = "✅ Đã nhận Khế ước."
        except economy_engine.EconomyError as e:
            await interaction.response.send_message(f"⚠️ {e}", ephemeral=True)
            return
        character = db.get_character(str(interaction.user.id))
        embed, view = build_contract_view(character)
        embed.add_field(name="Kết quả", value=message, inline=False)
        await interaction.response.edit_message(embed=embed, view=view)


class PostContractModal(discord.ui.Modal, title="Đăng Khế ước"):
    task = discord.ui.TextInput(label="Nhiệm vụ", max_length=200)
    reward = discord.ui.TextInput(label="Phần thưởng (Bảng)", max_length=10)

    @error_handler.safe_interaction(lambda: EconomyMenuView())
    async def on_submit(self, interaction: discord.Interaction):
        character = db.get_character(str(interaction.user.id))
        try:
            reward = int(str(self.reward))
        except ValueError:
            await interaction.response.send_message("⚠️ Phần thưởng phải là số nguyên.", ephemeral=True)
            return
        try:
            economy_engine.post_contract(character["character_id"], str(self.task), reward)
            message = "✅ Đã đăng Khế ước (tiền thưởng đã được ký quỹ)."
        except economy_engine.EconomyError as e:
            await interaction.response.send_message(f"⚠️ {e}", ephemeral=True)
            return
        character = db.get_character(str(interaction.user.id))
        embed, view = build_contract_view(character)
        embed.add_field(name="Kết quả", value=message, inline=False)
        await interaction.response.edit_message(embed=embed, view=view)


class PostContractButton(discord.ui.Button):
    def __init__(self):
        super().__init__(label="Đăng Khế ước", emoji="📜", style=discord.ButtonStyle.primary, row=1)

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.send_modal(PostContractModal())


class ContractActionsView(SafeView):
    def __init__(self, contracts: list):
        super().__init__(timeout=180)
        if contracts:
            self.add_item(AcceptContractSelect(contracts))
        self.add_item(PostContractButton())
        self.add_item(MyContractsButton())
        self.add_item(BackButton(EconomyMenuView))


STATUS_LABEL_VI = {
    "open": "🟢 Đang mở",
    "in_progress": "⏳ Đang thực hiện",
    "completed": "✅ Hoàn tất",
    "cancelled": "❌ Đã huỷ",
}


def build_my_contracts_view(character: dict):
    """mục 39: economy.my_contracts()/complete_contract()/cancel_contract()
    đã có sẵn trong engine nhưng trước đây chưa từng được gọi trong menu.py —
    người đăng Khế ước không có cách nào Xác nhận hoàn thành hay Huỷ trong
    UI. Giờ có view riêng cho việc này."""
    character_id = character["character_id"]
    icon = ICONS["contract"]
    contracts = economy_engine.my_contracts(character_id)
    embed = discord.Embed(title=f"{icon} KHẾ ƯỚC CỦA TÔI", color=discord.Color.dark_orange())
    if not contracts:
        embed.description = "Bạn chưa đăng hay nhận Khế ước nào."
    for c in contracts:
        role = "Người đăng" if c["issuer_character_id"] == character_id else "Người nhận"
        embed.add_field(
            name=f"#{c['contract_id']} — {c['task_vi']}",
            value=(
                f"Thưởng: {c['reward_money']:,} Bảng | Vai trò: {role}\n"
                f"Trạng thái: {STATUS_LABEL_VI.get(c['status'], c['status'])}"
            ),
            inline=False,
        )
    return embed, contracts


class CompleteContractSelect(discord.ui.Select):
    def __init__(self, contracts: list):
        completable = [c for c in contracts if c["status"] == "in_progress"]
        options = [
            discord.SelectOption(label=f"#{c['contract_id']} {c['task_vi'][:80]}", value=str(c["contract_id"]))
            for c in completable
        ] or [discord.SelectOption(label="(Không có Khế ước chờ xác nhận)", value="_none")]
        super().__init__(placeholder="✅ Xác nhận hoàn thành", options=options, row=0, disabled=not completable)

    @error_handler.safe_interaction(lambda: EconomyMenuView())
    async def callback(self, interaction: discord.Interaction):
        character = db.get_character(str(interaction.user.id))
        try:
            economy_engine.complete_contract(character["character_id"], int(self.values[0]))
        except economy_engine.EconomyError as e:
            await interaction.response.send_message(f"⚠️ {e}", ephemeral=True)
            return
        character = db.get_character(str(interaction.user.id))
        embed, contracts = build_my_contracts_view(character)
        embed.add_field(name="Kết quả", value="✅ Đã xác nhận hoàn thành — thưởng đã chuyển.", inline=False)
        await interaction.response.edit_message(embed=embed, view=MyContractsView(contracts))


class CancelContractSelect(discord.ui.Select):
    def __init__(self, contracts: list):
        cancellable = [c for c in contracts if c["status"] == "open"]
        options = [
            discord.SelectOption(label=f"#{c['contract_id']} {c['task_vi'][:80]}", value=str(c["contract_id"]))
            for c in cancellable
        ] or [discord.SelectOption(label="(Không có Khế ước có thể huỷ)", value="_none")]
        super().__init__(placeholder="❌ Huỷ Khế ước", options=options, row=1, disabled=not cancellable)

    @error_handler.safe_interaction(lambda: EconomyMenuView())
    async def callback(self, interaction: discord.Interaction):
        character = db.get_character(str(interaction.user.id))
        try:
            economy_engine.cancel_contract(character["character_id"], int(self.values[0]))
        except economy_engine.EconomyError as e:
            await interaction.response.send_message(f"⚠️ {e}", ephemeral=True)
            return
        character = db.get_character(str(interaction.user.id))
        embed, contracts = build_my_contracts_view(character)
        embed.add_field(name="Kết quả", value="✅ Đã huỷ — tiền ký quỹ đã hoàn lại.", inline=False)
        await interaction.response.edit_message(embed=embed, view=MyContractsView(contracts))


class MyContractsView(SafeView):
    def __init__(self, contracts: list):
        super().__init__(timeout=180)
        self.add_item(CompleteContractSelect(contracts))
        self.add_item(CancelContractSelect(contracts))
        self.add_item(BackButton(EconomyMenuView))


class MyContractsButton(discord.ui.Button):
    def __init__(self):
        super().__init__(label="Khế ước của tôi", emoji="🗂️", style=discord.ButtonStyle.secondary, row=2)

    @error_handler.safe_interaction(lambda: EconomyMenuView())
    async def callback(self, interaction: discord.Interaction):
        character = db.get_character(str(interaction.user.id))
        embed, contracts = build_my_contracts_view(character)
        await interaction.response.edit_message(embed=embed, view=MyContractsView(contracts))


def build_bounty_view(character: dict):
    icon = ICONS["bounty"]
    bounties = economy_engine.list_active_bounties()
    embed = discord.Embed(title=f"{icon} TRUY NÃ", color=discord.Color.dark_red())
    if not bounties:
        embed.description = "Hiện không có lệnh Truy nã nào."
    for b in bounties:
        embed.add_field(
            name=f"#{b['bounty_id']} — {b['target_name']}",
            value=f"Tội danh: {b['crime_vi']} · Thưởng: {b['reward_money']:,} Bảng",
            inline=False,
        )
    return embed, BountyActionsView(bounties)


class ClaimBountySelect(discord.ui.Select):
    def __init__(self, bounties: list):
        options = [
            discord.SelectOption(label=f"#{b['bounty_id']} {b['target_name']}", value=str(b["bounty_id"]))
            for b in bounties
        ]
        super().__init__(placeholder=f"{ICONS['bounty']} Nhận thưởng (đã hạ mục tiêu)", options=options, row=0)

    @error_handler.safe_interaction(lambda: EconomyMenuView())
    async def callback(self, interaction: discord.Interaction):
        character = db.get_character(str(interaction.user.id))
        try:
            economy_engine.claim_bounty(character["character_id"], int(self.values[0]))
            message = "✅ Đã nhận thưởng Truy nã."
        except economy_engine.EconomyError as e:
            await interaction.response.send_message(f"⚠️ {e}", ephemeral=True)
            return
        character = db.get_character(str(interaction.user.id))
        embed, view = build_bounty_view(character)
        embed.add_field(name="Kết quả", value=message, inline=False)
        await interaction.response.edit_message(embed=embed, view=view)


class PostBountyModal(discord.ui.Modal, title="Treo thưởng Truy nã"):
    crime = discord.ui.TextInput(label="Tội danh", max_length=200)
    reward = discord.ui.TextInput(label="Phần thưởng (Bảng)", max_length=10)

    def __init__(self, target_character_id: int, target_name: str):
        super().__init__()
        self.target_character_id = target_character_id
        self.title = f"Treo thưởng: {target_name}"[:45]

    @error_handler.safe_interaction(lambda: EconomyMenuView())
    async def on_submit(self, interaction: discord.Interaction):
        character = db.get_character(str(interaction.user.id))
        try:
            reward = int(str(self.reward))
        except ValueError:
            await interaction.response.send_message("⚠️ Phần thưởng phải là số nguyên.", ephemeral=True)
            return
        try:
            economy_engine.post_bounty(character["character_id"], self.target_character_id, str(self.crime), reward)
            message = "✅ Đã treo thưởng Truy nã."
        except economy_engine.EconomyError as e:
            await interaction.response.send_message(f"⚠️ {e}", ephemeral=True)
            return
        character = db.get_character(str(interaction.user.id))
        embed, view = build_bounty_view(character)
        embed.add_field(name="Kết quả", value=message, inline=False)
        await interaction.response.edit_message(embed=embed, view=view)


class BountyTargetSelect(discord.ui.UserSelect):
    def __init__(self):
        super().__init__(placeholder=f"{ICONS['bounty']} Chọn mục tiêu", row=0)

    @error_handler.safe_interaction(lambda: EconomyMenuView())
    async def callback(self, interaction: discord.Interaction):
        target = db.get_character(str(self.values[0].id))
        if target is None:
            await interaction.response.send_message("Người chơi này chưa có nhân vật.", ephemeral=True)
            return
        await interaction.response.send_modal(PostBountyModal(target["character_id"], target["name"]))


class BountyTargetPickView(SafeView):
    def __init__(self):
        super().__init__(timeout=180)
        self.add_item(BountyTargetSelect())
        self.add_item(BackButton(EconomyMenuView))


class PostBountyButton(discord.ui.Button):
    def __init__(self):
        super().__init__(label="Treo thưởng", emoji="☠️", style=discord.ButtonStyle.danger, row=1)

    async def callback(self, interaction: discord.Interaction):
        embed = discord.Embed(
            title=f"{ICONS['bounty']} Treo thưởng Truy nã",
            description="Chọn mục tiêu bên dưới.",
            color=discord.Color.dark_red(),
        )
        await interaction.response.edit_message(embed=embed, view=BountyTargetPickView())


class BountyActionsView(SafeView):
    def __init__(self, bounties: list):
        super().__init__(timeout=180)
        if bounties:
            self.add_item(ClaimBountySelect(bounties))
        self.add_item(PostBountyButton())
        self.add_item(BackButton(EconomyMenuView))


# ---------------------------------------------------------------------------
# 🏠 Đời sống — House / Achievement / Ranking (mục 42, 45-46, 59)
# ---------------------------------------------------------------------------

def build_house_hub_embed(character: dict) -> discord.Embed:
    icon = ICONS["house"]
    lang = i18n.user_lang(character["user_id"]) if character else None
    embed = discord.Embed(title=f"{icon} {i18n.t('house.hub_title', lang)}", color=discord.Color.dark_green())
    if character is None:
        embed.description = i18n.t("common.no_character", lang)
        return embed
    embed.description = i18n.t("house.hub_description", lang)
    return embed


class HouseMenuSelect(discord.ui.Select):
    OPTIONS = [
        ("house", "option_house", ICONS["house"]),
        ("rooms", "option_rooms", "🔬"),
        ("achievement", "option_achievement", ICONS["achievement"]),
        ("ranking", "option_ranking", ICONS["ranking"]),
        ("season", "option_season", ICONS["season"]),
    ]

    def __init__(self, lang: str = None):
        self.lang = lang
        lang = lang or i18n.DEFAULT_LANG
        options = [
            discord.SelectOption(label=i18n.t(f"house.{i18n_key}", lang), value=k, emoji=i)
            for k, i18n_key, i in self.OPTIONS
        ]
        super().__init__(placeholder=f"🏠 {i18n.t('house.hub_placeholder', lang)}", options=options, row=0)

    @error_handler.safe_interaction(lambda: HouseMenuView())
    async def callback(self, interaction: discord.Interaction):
        character = db.get_character(str(interaction.user.id))
        key = self.values[0]
        if key == "house":
            embed, view = build_house_storage_view(character)
        elif key == "rooms":
            embed, view = build_house_rooms_view(character)
        elif key == "achievement":
            embed, view = build_achievement_view(character)
        elif key == "season":
            embed, view = build_season_history_view(character)
        else:
            embed, view = build_ranking_view(character)
        await interaction.response.edit_message(embed=embed, view=view)


class HouseMenuView(SafeView):
    def __init__(self, lang: str = None):
        super().__init__(timeout=180)
        self.add_item(HouseMenuSelect(lang))
        self.add_item(BackButton(MainMenuView))


def build_house_storage_view(character: dict):
    icon = ICONS["house"]
    lang = i18n.user_lang(character["user_id"])
    house = house_engine.get_house(character["character_id"])
    embed = discord.Embed(title=f"{icon} {i18n.t('house.storage_title', lang)}", color=discord.Color.dark_green())
    embed.description = i18n.t(
        "house.storage_description", lang, tier=house["tier"], slots=house["storage_slots"]
    )
    if house["storage"]:
        lines = [f"{s['name_vi']} ×{s['quantity']}" for s in house["storage"]]
        embed.add_field(name=i18n.t("house.storage_field", lang), value="\n".join(lines), inline=False)
    else:
        embed.add_field(name=i18n.t("house.storage_field", lang), value=i18n.t("house.storage_empty", lang), inline=False)
    return embed, HouseStorageActionsView(lang)


class StoreItemModal(discord.ui.Modal):
    def __init__(self, item_id: str, item_name: str, lang: str = None):
        self.lang = lang or i18n.DEFAULT_LANG
        super().__init__(title=f"{i18n.t('house.store_modal_title', self.lang)}: {item_name}"[:45])
        self.item_id = item_id
        self.quantity = discord.ui.TextInput(label=i18n.t("house.quantity_label", self.lang), max_length=6, default="1")
        self.add_item(self.quantity)

    @error_handler.safe_interaction(lambda: HouseMenuView())
    async def on_submit(self, interaction: discord.Interaction):
        character = db.get_character(str(interaction.user.id))
        lang = self.lang or i18n.user_lang(str(interaction.user.id))
        try:
            qty = int(str(self.quantity))
        except ValueError:
            await interaction.response.send_message(f"⚠️ {i18n.t('house.quantity_not_integer', lang)}", ephemeral=True)
            return
        try:
            house_engine.store_item(character["character_id"], self.item_id, qty)
            message = f"✅ {i18n.t('house.store_success', lang)}"
        except house_engine.HouseError as e:
            await interaction.response.send_message(f"⚠️ {e}", ephemeral=True)
            return
        character = db.get_character(str(interaction.user.id))
        embed, view = build_house_storage_view(character)
        embed.add_field(name=i18n.t("common.result", lang), value=message, inline=False)
        await interaction.response.edit_message(embed=embed, view=view)


class WithdrawItemModal(discord.ui.Modal):
    def __init__(self, item_id: str, item_name: str, lang: str = None):
        self.lang = lang or i18n.DEFAULT_LANG
        super().__init__(title=f"{i18n.t('house.withdraw_modal_title', self.lang)}: {item_name}"[:45])
        self.item_id = item_id
        self.quantity = discord.ui.TextInput(label=i18n.t("house.quantity_label", self.lang), max_length=6, default="1")
        self.add_item(self.quantity)

    @error_handler.safe_interaction(lambda: HouseMenuView())
    async def on_submit(self, interaction: discord.Interaction):
        character = db.get_character(str(interaction.user.id))
        lang = self.lang or i18n.user_lang(str(interaction.user.id))
        try:
            qty = int(str(self.quantity))
        except ValueError:
            await interaction.response.send_message(f"⚠️ {i18n.t('house.quantity_not_integer', lang)}", ephemeral=True)
            return
        try:
            house_engine.withdraw_item(character["character_id"], self.item_id, qty)
            message = f"✅ {i18n.t('house.withdraw_success', lang)}"
        except house_engine.HouseError as e:
            await interaction.response.send_message(f"⚠️ {e}", ephemeral=True)
            return
        character = db.get_character(str(interaction.user.id))
        embed, view = build_house_storage_view(character)
        embed.add_field(name=i18n.t("common.result", lang), value=message, inline=False)
        await interaction.response.edit_message(embed=embed, view=view)


class StoreItemPickSelect(discord.ui.Select):
    """Chọn vật phẩm từ Túi đồ để cất vào kho — không gõ mã item_id."""

    def __init__(self, items: list, lang: str = None):
        self.lang = lang or i18n.DEFAULT_LANG
        options = [
            discord.SelectOption(label=f"{it['name_vi']} (×{it['quantity']})", value=it["item_id"])
            for it in items
        ]
        super().__init__(placeholder=i18n.t("house.store_pick_placeholder", self.lang), options=options, row=0)
        self._items_by_id = {it["item_id"]: it for it in items}

    @error_handler.safe_interaction(lambda: HouseMenuView())
    async def callback(self, interaction: discord.Interaction):
        item = self._items_by_id[self.values[0]]
        await interaction.response.send_modal(StoreItemModal(item["item_id"], item["name_vi"], self.lang))


class WithdrawItemPickSelect(discord.ui.Select):
    """Chọn vật phẩm từ Kho để lấy ra — không gõ mã item_id."""

    def __init__(self, items: list, lang: str = None):
        self.lang = lang or i18n.DEFAULT_LANG
        options = [
            discord.SelectOption(label=f"{it['name_vi']} (×{it['quantity']})", value=it["item_id"])
            for it in items
        ]
        super().__init__(placeholder=i18n.t("house.withdraw_pick_placeholder", self.lang), options=options, row=0)
        self._items_by_id = {it["item_id"]: it for it in items}

    @error_handler.safe_interaction(lambda: HouseMenuView())
    async def callback(self, interaction: discord.Interaction):
        item = self._items_by_id[self.values[0]]
        await interaction.response.send_modal(WithdrawItemModal(item["item_id"], item["name_vi"], self.lang))


class StoreItemPickView(SafeView):
    def __init__(self, items: list, lang: str = None):
        super().__init__(timeout=180)
        self.add_item(StoreItemPickSelect(items, lang))
        self.add_item(BackButton(HouseMenuView))


class WithdrawItemPickView(SafeView):
    def __init__(self, items: list, lang: str = None):
        super().__init__(timeout=180)
        self.add_item(WithdrawItemPickSelect(items, lang))
        self.add_item(BackButton(HouseMenuView))


class StoreItemButton(discord.ui.Button):
    def __init__(self, lang: str = None):
        self.lang = lang
        super().__init__(label=i18n.t("house.store_button", lang), emoji="📥", style=discord.ButtonStyle.primary, row=1)

    @error_handler.safe_interaction(lambda: HouseMenuView())
    async def callback(self, interaction: discord.Interaction):
        lang = self.lang or i18n.DEFAULT_LANG
        character = db.get_character(str(interaction.user.id))
        items = [it for it in inv.list_inventory(character["character_id"]) if it["quantity"] > 0]
        if not items:
            await interaction.response.send_message(i18n.t("house.no_items_to_store", lang), ephemeral=True)
            return
        embed = discord.Embed(title=i18n.t("house.store_modal_title", lang), color=discord.Color.dark_green())
        await interaction.response.edit_message(embed=embed, view=StoreItemPickView(items, lang))


class WithdrawItemButton(discord.ui.Button):
    def __init__(self, lang: str = None):
        self.lang = lang
        super().__init__(label=i18n.t("house.withdraw_button", lang), emoji="📤", style=discord.ButtonStyle.secondary, row=1)

    @error_handler.safe_interaction(lambda: HouseMenuView())
    async def callback(self, interaction: discord.Interaction):
        lang = self.lang or i18n.DEFAULT_LANG
        character = db.get_character(str(interaction.user.id))
        house = house_engine.get_house(character["character_id"])
        items = [it for it in house["storage"] if it["quantity"] > 0]
        if not items:
            await interaction.response.send_message(i18n.t("house.no_items_to_withdraw", lang), ephemeral=True)
            return
        embed = discord.Embed(title=i18n.t("house.withdraw_modal_title", lang), color=discord.Color.dark_green())
        await interaction.response.edit_message(embed=embed, view=WithdrawItemPickView(items, lang))


class RoomsShortcutButton(discord.ui.Button):
    def __init__(self, lang: str = None):
        self.lang = lang
        super().__init__(label=i18n.t("house.rooms_button", lang), emoji="🔬", style=discord.ButtonStyle.secondary, row=2)

    @error_handler.safe_interaction(lambda: HouseMenuView())
    async def callback(self, interaction: discord.Interaction):
        character = db.get_character(str(interaction.user.id))
        embed, view = build_house_rooms_view(character)
        await interaction.response.edit_message(embed=embed, view=view)


class UpgradeTierButton(discord.ui.Button):
    def __init__(self, lang: str = None):
        self.lang = lang
        super().__init__(label=i18n.t("house.upgrade_tier_button", lang), emoji="🏗️", style=discord.ButtonStyle.success, row=2)

    @error_handler.safe_interaction(lambda: HouseMenuView())
    async def callback(self, interaction: discord.Interaction):
        character = db.get_character(str(interaction.user.id))
        lang = self.lang or i18n.user_lang(str(interaction.user.id))
        try:
            result = house_engine.upgrade_tier(character["character_id"])
            message = f"✅ {i18n.t('house.upgrade_tier_success', lang, tier=result['new_tier'], slots=result['slot_increase'])}"
        except house_engine.HouseError as e:
            await interaction.response.send_message(f"⚠️ {e}", ephemeral=True)
            return
        character = db.get_character(str(interaction.user.id))
        embed, view = build_house_storage_view(character)
        embed.add_field(name=i18n.t("common.result", lang), value=message, inline=False)
        await interaction.response.edit_message(embed=embed, view=view)


class HouseStorageActionsView(SafeView):
    def __init__(self, lang: str = None):
        super().__init__(timeout=180)
        self.add_item(StoreItemButton(lang))
        self.add_item(WithdrawItemButton(lang))
        self.add_item(RoomsShortcutButton(lang))
        self.add_item(UpgradeTierButton(lang))
        self.add_item(BackButton(HouseMenuView))


# ---------------------------------------------------------------------------
# 🏠 Phòng chức năng (Rooms) — mục 42 mở rộng: 4 phòng nâng cấp độc lập, mỗi
# phòng cho bonus cơ học thật ở engine liên quan (xem house.py).
# ---------------------------------------------------------------------------

_ROOM_ICONS = {"research": "🔬", "potion": "🧪", "ritual": "🕯️", "artifact": "🗝️"}
_ROOM_BONUS_GETTERS = {
    "research": house_engine.research_sp_discount,
    "potion": house_engine.potion_risk_reduction,
    "ritual": house_engine.ritual_success_bonus,
    "artifact": house_engine.artifact_side_effect_reduction,
}


def build_house_rooms_view(character: dict):
    icon = ICONS["house"]
    lang = i18n.user_lang(character["user_id"])
    character_id = character["character_id"]
    rooms = house_engine.get_rooms(character_id)
    embed = discord.Embed(title=f"{icon} {i18n.t('house.rooms_title', lang)}", color=discord.Color.dark_green())
    embed.description = i18n.t("house.rooms_description", lang, max_level=house_engine.MAX_ROOM_LEVEL)
    for room_type in house_engine.ROOM_TYPES:
        level = rooms[room_type]
        bonus = _ROOM_BONUS_GETTERS[room_type](character_id)
        name = f"{i18n.t(f'house.room_{room_type}', lang)}"
        desc = i18n.t(f"house.room_{room_type}_desc", lang, bonus=bonus)
        if level >= house_engine.MAX_ROOM_LEVEL:
            status = i18n.t("house.room_maxed_line", lang, level=level, max_level=house_engine.MAX_ROOM_LEVEL)
        else:
            cost = house_engine.room_upgrade_cost(level)
            status = i18n.t("house.room_level_line", lang, level=level, max_level=house_engine.MAX_ROOM_LEVEL, cost=f"{cost:,}")
        embed.add_field(name=name, value=f"{desc}\n{status}", inline=False)
    return embed, HouseRoomsActionsView(lang)


class UpgradeRoomSelect(discord.ui.Select):
    def __init__(self, lang: str = None):
        self.lang = lang
        lang = lang or i18n.DEFAULT_LANG
        options = [
            discord.SelectOption(label=i18n.t(f"house.room_{rt}", lang), value=rt, emoji=_ROOM_ICONS[rt])
            for rt in house_engine.ROOM_TYPES
        ]
        super().__init__(placeholder=i18n.t("house.upgrade_room_placeholder", lang), options=options, row=0)

    @error_handler.safe_interaction(lambda: HouseMenuView())
    async def callback(self, interaction: discord.Interaction):
        character = db.get_character(str(interaction.user.id))
        lang = self.lang or i18n.user_lang(str(interaction.user.id))
        room_type = self.values[0]
        try:
            result = house_engine.upgrade_room(character["character_id"], room_type)
            room_label = i18n.t(f"house.room_{room_type}", lang)
            message = f"✅ {i18n.t('house.upgrade_room_success', lang, room=room_label, level=result['new_level'])}"
        except house_engine.HouseError as e:
            await interaction.response.send_message(f"⚠️ {e}", ephemeral=True)
            return
        character = db.get_character(str(interaction.user.id))
        embed, view = build_house_rooms_view(character)
        embed.add_field(name=i18n.t("common.result", lang), value=message, inline=False)
        await interaction.response.edit_message(embed=embed, view=view)


class HouseRoomsActionsView(SafeView):
    def __init__(self, lang: str = None):
        super().__init__(timeout=180)
        self.add_item(UpgradeRoomSelect(lang))
        self.add_item(BackButton(HouseMenuView))


def build_achievement_view(character: dict):
    icon = ICONS["achievement"]
    unlocked = achievements_engine.list_unlocked(character["character_id"])
    locked = achievements_engine.list_locked(character["character_id"])
    embed = discord.Embed(title=f"{icon} THÀNH TỰU", color=discord.Color.yellow())
    embed.description = f"Đã mở khoá {len(unlocked)}/{len(unlocked) + len(locked)}."
    for a in unlocked:
        embed.add_field(name=f"✅ {a['name_vi']}", value=a["description_vi"], inline=False)
    for a in locked[:10]:
        embed.add_field(name=f"🔒 {a['name_vi']}", value=a["description_vi"], inline=False)
    return embed, SimpleBackView(HouseMenuView)


def build_ranking_view(character: dict):
    icon = ICONS["ranking"]
    season = db.get_active_season()
    season_label = season["name_vi"] if season else "—"
    embed = discord.Embed(
        title=f"{icon} BẢNG XẾP HẠNG",
        description=f"Vĩnh viễn (Level/Tiền/Sequence/Thành tựu) + theo {ICONS['season']} **{season_label}** (PvP/Dungeon/Truy nã/Guild).",
        color=discord.Color.blurple(),
    )
    # Vĩnh viễn (mục 44 — Character progression không reset qua Season)
    for field, (_, label) in db.RANKING_FIELDS.items():
        top = achievements_engine.get_ranking(field, 5)
        lines = [f"{i+1}. {row['name']} — {row[db.RANKING_FIELDS[field][0]]:,}" for i, row in enumerate(top)]
        embed.add_field(name=label, value="\n".join(lines) if lines else "—", inline=False)
    # Theo Season đang active + Guild (mục 46: PvP/Dungeon/Bounty/Achievement/Guild)
    for category, (label, _, _) in db.SEASON_RANKING_CATEGORIES.items():
        top = db.get_live_ranking(category, 5)
        lines = [f"{i+1}. {row['name']} — {row['value']:,}" for i, row in enumerate(top)]
        embed.add_field(name=label, value="\n".join(lines) if lines else "—", inline=False)
    return embed, RankingActionsView()


class ViewSeasonHistoryButton(discord.ui.Button):
    def __init__(self):
        super().__init__(label="Lịch sử Mùa", emoji=ICONS["season"], style=discord.ButtonStyle.secondary)

    @error_handler.safe_interaction(lambda: HouseMenuView())
    async def callback(self, interaction: discord.Interaction):
        character = db.get_character(str(interaction.user.id))
        embed, view = build_season_history_view(character)
        await interaction.response.edit_message(embed=embed, view=view)


class RankingActionsView(SafeView):
    def __init__(self):
        super().__init__(timeout=180)
        self.add_item(ViewSeasonHistoryButton())
        self.add_item(BackButton(HouseMenuView))


def build_season_history_view(character: dict):
    icon = ICONS["season"]
    seasons = db.list_seasons(10)
    embed = discord.Embed(title=f"{icon} LỊCH SỬ MÙA", color=discord.Color.dark_gold())
    if not seasons:
        embed.description = "Chưa có Mùa nào."
        return embed, SimpleBackView(HouseMenuView)

    active = next((s for s in seasons if s["status"] == "active"), None)
    if active:
        embed.add_field(
            name=f"🟢 {active['name_vi']} (đang diễn ra)",
            value=f"Bắt đầu: {active['started_at']}",
            inline=False,
        )

    ended = [s for s in seasons if s["status"] == "ended"]
    if not ended:
        embed.add_field(name="Mùa đã kết thúc", value="Chưa có Mùa nào kết thúc.", inline=False)
        return embed, SimpleBackView(HouseMenuView)

    latest = ended[0]
    embed.add_field(
        name=f"🏁 {latest['name_vi']} (kết thúc {latest['ended_at']})",
        value="Top 3 mỗi bảng xếp hạng khi Mùa này chốt:",
        inline=False,
    )
    for category, label in db.ALL_RANKING_CATEGORIES.items():
        snap = db.list_season_ranking_snapshot(latest["season_id"], category, 3)
        lines = [f"{row['rank']}. {row['character_name']} — {row['value']:,}" for row in snap]
        embed.add_field(name=label, value="\n".join(lines) if lines else "—", inline=True)

    if len(ended) > 1:
        older = ", ".join(s["name_vi"] for s in ended[1:])
        embed.set_footer(text=f"Mùa cũ hơn: {older}")

    return embed, SimpleBackView(HouseMenuView)


# ---------------------------------------------------------------------------
# Tạo nhân vật (Modal — mục 57)

# ---------------------------------------------------------------------------

class CreateCharacterModal(discord.ui.Modal, title="Tạo nhân vật"):
    name = discord.ui.TextInput(label="Tên nhân vật", max_length=32, placeholder="Vd: Hoàng")

    async def on_submit(self, interaction: discord.Interaction):
        character = db.create_character(str(interaction.user.id), str(self.name))
        embed = build_character_embed(character)
        await interaction.response.edit_message(embed=embed, view=MainMenuView())


class NoCharacterView(SafeView):
    def __init__(self):
        super().__init__(timeout=180)

    @discord.ui.button(label="Tạo nhân vật", emoji="👤", style=discord.ButtonStyle.primary)
    async def create(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(CreateCharacterModal())


# ---------------------------------------------------------------------------
# 📖 Hướng dẫn chơi (/huong_dan) — 3 trang, dành cho người chơi mới
# ---------------------------------------------------------------------------

GUIDE_PAGES = [
    {
        "title": "📖 Hướng dẫn 1 — Nhập môn",
        "color": discord.Color.dark_purple(),
        "fields": [
            (
                "👤 Tạo nhân vật",
                "Gõ lệnh `/menu` lần đầu tiên, bấm **Tạo nhân vật** và đặt tên. "
                "Mỗi tài khoản Discord chỉ có 1 nhân vật.",
            ),
            (
                f"{ICONS['pathway']} Con đường (Pathway)",
                "Vào mục **Con đường** trong `/menu` để chọn hướng phát triển cho nhân vật. "
                "Mỗi Con đường có 9-10 **Sequence** (cấp bậc), đi từ số lớn xuống số nhỏ — "
                "Sequence càng thấp thì càng mạnh.",
            ),
            (
                f"{ICONS['spirituality']} Chỉ số cơ bản",
                f"{ICONS['spirituality']} Tinh Thần (Spirituality): dùng để thi triển Năng lực.\n"
                f"{ICONS['hp']} Sinh Lực (HP): về 0 sẽ gục trong chiến đấu.\n"
                f"{ICONS['loss_of_control']} Nguy cơ mất kiểm soát: càng cao càng dễ gặp sự cố bất ngờ — "
                "giữ Tinh Thần và trạng thái tâm lý ổn định để hạ chỉ số này.",
            ),
            (
                "➡️ Tiếp theo",
                "Dùng `/huong_dan trang:2` để xem cách chiến đấu và tăng sức mạnh.",
            ),
        ],
    },
    {
        "title": "📖 Hướng dẫn 2 — Sức mạnh & Sinh tồn",
        "color": discord.Color.purple(),
        "fields": [
            (
                f"{ICONS['ability']} Năng lực",
                "Mỗi Sequence trên Con đường mở khóa một Năng lực mới. Xem danh sách "
                "và chi phí Tinh Thần trong mục **Năng lực**.",
            ),
            (
                f"{ICONS['mysticism']} Huyền bí",
                f"{ICONS['divination']} Bói toán (Tarot), {ICONS['ritual']} Nghi thức (Ritual) và Tri thức "
                "(Knowledge) giúp nhân vật hiểu thêm về thế giới và mở thêm lựa chọn hành động.",
            ),
            (
                f"{ICONS['inventory']} Tài sản",
                f"{ICONS['potion']} Potion, {ICONS['artifact']} Artifact và trang bị được quản lý trong mục "
                "**Tài sản**. Một số Potion cần chế tạo trước khi dùng.",
            ),
            (
                f"{ICONS['combat']} Chiến đấu",
                f"{ICONS['pve']} Đánh quái, {ICONS['pvp']} đấu người chơi khác, hoặc vào "
                f"{ICONS['dungeon']} Dungeon theo nhóm. Có thể **Phòng thủ** hoặc **Rút lui** khi bất lợi.",
            ),
            (
                "➡️ Tiếp theo",
                "Dùng `/huong_dan trang:3` để xem về thế giới, tổ chức và giao dịch.",
            ),
        ],
    },
    {
        "title": "📖 Hướng dẫn 3 — Thế giới & Xã hội",
        "color": discord.Color.blue(),
        "fields": [
            (
                f"{ICONS['world']} Thế giới",
                f"Di chuyển giữa {ICONS['city']} Thành phố, khám phá {ICONS['location']} Địa điểm, gặp "
                f"{ICONS['npc']} NPC, thực hiện {ICONS['investigation']} Điều tra và theo dõi "
                f"{ICONS['event']} Sự kiện đang diễn ra.",
            ),
            (
                f"{ICONS['faction']} Tổ chức & đồng đội",
                f"Tham gia {ICONS['church']} Giáo hội hoặc {ICONS['faction']} Tổ chức, lập "
                f"{ICONS['party']} Nhóm để cùng phiêu lưu.",
            ),
            (
                f"{ICONS['economy']} Giao dịch",
                f"Mua bán tại {ICONS['market']} Chợ, đấu giá ở {ICONS['auction']} Auction, hoặc thăm dò "
                f"{ICONS['black_market']} Chợ đen (rủi ro cao hơn, cẩn thận khi giao dịch).",
            ),
            (
                f"{ICONS['house']} Đời sống",
                "Xây dựng và nâng cấp Nhà riêng, theo dõi Thành tựu và Bảng xếp hạng theo Mùa "
                "trong mục **Đời sống**.",
            ),
            (
                "✅ Xong rồi!",
                "Quay lại trang bất kỳ bằng `/huong_dan trang:1` (hoặc 2, 3). Mở `/menu` để bắt đầu chơi.",
            ),
        ],
    },
]


def build_guide_embed(page: int) -> discord.Embed:
    page = max(1, min(page, len(GUIDE_PAGES)))
    data = GUIDE_PAGES[page - 1]
    embed = discord.Embed(title=data["title"], color=data["color"])
    for name, value in data["fields"]:
        embed.add_field(name=name, value=value, inline=False)
    embed.set_footer(text=f"Trang {page}/{len(GUIDE_PAGES)}")
    return embed


class GuideView(SafeView):
    """View điều hướng 3 trang hướng dẫn bằng nút bấm — không cần gõ lại lệnh."""

    def __init__(self, page: int = 1):
        super().__init__(timeout=180)
        self.page = max(1, min(page, len(GUIDE_PAGES)))
        self._sync_buttons()

    def _sync_buttons(self):
        self.previous_page.disabled = self.page <= 1
        self.next_page.disabled = self.page >= len(GUIDE_PAGES)

    @discord.ui.button(label="Trang trước", emoji="⬅️", style=discord.ButtonStyle.secondary, row=0)
    async def previous_page(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.page -= 1
        self._sync_buttons()
        await interaction.response.edit_message(embed=build_guide_embed(self.page), view=self)

    @discord.ui.button(label="Trang sau", emoji="➡️", style=discord.ButtonStyle.secondary, row=0)
    async def next_page(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.page += 1
        self._sync_buttons()
        await interaction.response.edit_message(embed=build_guide_embed(self.page), view=self)

    @discord.ui.button(label="Mở menu", emoji=ICONS["character"], style=discord.ButtonStyle.primary, row=1)
    async def open_menu(self, interaction: discord.Interaction, button: discord.ui.Button):
        user_id = str(interaction.user.id)
        user = db.get_or_create_user(user_id)
        lang = user.get("language") or i18n.DEFAULT_LANG
        character = db.get_character(user_id)
        embed = build_character_embed(character)
        view = MainMenuView(lang) if character else NoCharacterView()
        await interaction.response.edit_message(embed=embed, view=view)


# ---------------------------------------------------------------------------
# Hướng dẫn người chơi mới (đọc trực tiếp từ docs/NEW_PLAYER_GUIDE.md)
# ---------------------------------------------------------------------------

GUIDE_DOC_PATH = os.path.join(os.path.dirname(__file__), "..", "docs", "NEW_PLAYER_GUIDE.md")
GUIDE_DOC_PAGE_BUDGET = 3500  # ký tự tối đa mỗi trang embed (Discord giới hạn description 4096)


def _load_guide_doc_pages() -> list:
    """Đọc docs/NEW_PLAYER_GUIDE.md, tách theo từng mục "## ..." và gộp lại
    thành các trang sao cho không vượt giới hạn ký tự của embed Discord.
    Đọc trực tiếp từ file nên nội dung /huongdan luôn khớp với tài liệu gốc,
    không cần đồng bộ tay khi tài liệu thay đổi."""
    if not os.path.exists(GUIDE_DOC_PATH):
        return []

    with open(GUIDE_DOC_PATH, "r", encoding="utf-8") as f:
        raw = f.read()

    # Bỏ các dòng "---" (horizontal rule) để không lẫn vào nội dung trang.
    raw = re.sub(r"(?m)^---\s*$\n?", "", raw)

    sections = [s.strip("\n") for s in re.split(r"(?m)^(?=## )", raw) if s.strip()]

    pages = []
    current = ""
    for section in sections:
        candidate = f"{current}\n\n{section}" if current else section
        if current and len(candidate) > GUIDE_DOC_PAGE_BUDGET:
            pages.append(current)
            current = section
        else:
            current = candidate
    if current:
        pages.append(current)

    return pages


GUIDE_DOC_PAGES = _load_guide_doc_pages()


def build_guide_doc_embed(page: int) -> discord.Embed:
    page = max(1, min(page, len(GUIDE_DOC_PAGES)))
    embed = discord.Embed(
        title="📘 Hướng dẫn người chơi mới",
        description=GUIDE_DOC_PAGES[page - 1],
        color=discord.Color.dark_purple(),
    )
    embed.set_footer(text=f"Trang {page}/{len(GUIDE_DOC_PAGES)}")
    return embed


class GuideDocView(SafeView):
    """View điều hướng nhiều trang cho nội dung docs/NEW_PLAYER_GUIDE.md."""

    def __init__(self, page: int = 1):
        super().__init__(timeout=180)
        self.page = max(1, min(page, len(GUIDE_DOC_PAGES)))
        self._sync_buttons()

    def _sync_buttons(self):
        self.previous_page.disabled = self.page <= 1
        self.next_page.disabled = self.page >= len(GUIDE_DOC_PAGES)

    @discord.ui.button(label="Trang trước", emoji="⬅️", style=discord.ButtonStyle.secondary, row=0)
    async def previous_page(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.page -= 1
        self._sync_buttons()
        await interaction.response.edit_message(embed=build_guide_doc_embed(self.page), view=self)

    @discord.ui.button(label="Trang sau", emoji="➡️", style=discord.ButtonStyle.secondary, row=0)
    async def next_page(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.page += 1
        self._sync_buttons()
        await interaction.response.edit_message(embed=build_guide_doc_embed(self.page), view=self)


# ---------------------------------------------------------------------------
# Cog
# ---------------------------------------------------------------------------

class MenuCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="huong_dan", description="Xem hướng dẫn chơi Quỷ Bí (3 trang)")
    @app_commands.describe(trang="Trang hướng dẫn muốn xem: 1, 2 hoặc 3 (mặc định 1)")
    @app_commands.choices(trang=[
        app_commands.Choice(name="1 — Nhập môn", value=1),
        app_commands.Choice(name="2 — Sức mạnh & Sinh tồn", value=2),
        app_commands.Choice(name="3 — Thế giới & Xã hội", value=3),
    ])
    async def huong_dan(self, interaction: discord.Interaction, trang: app_commands.Choice[int] = None):
        page = trang.value if trang else 1
        embed = build_guide_embed(page)
        view = GuideView(page)
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

    @app_commands.command(name="huongdan", description="Xem nội dung Hướng dẫn người chơi mới (New Player Guide)")
    async def huongdan(self, interaction: discord.Interaction):
        if not GUIDE_DOC_PAGES:
            embed = error_handler.player_error_embed("not_found")
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        embed = build_guide_doc_embed(1)
        view = GuideDocView(1)
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

    @app_commands.command(name="menu", description="Mở giao diện chính của Quỷ Bí")
    async def menu(self, interaction: discord.Interaction):
        user_id = str(interaction.user.id)
        user = db.get_or_create_user(user_id)
        lang = user.get("language") or i18n.DEFAULT_LANG
        character = db.get_character(user_id)

        embed = build_character_embed(character)
        view = MainMenuView(lang) if character else NoCharacterView()
        await interaction.response.send_message(embed=embed, view=view)

    @app_commands.command(name="end_season", description="[Admin] Chốt Mùa hiện tại, chụp Ranking, mở Mùa mới")
    @app_commands.describe(new_season_name="Tên Mùa mới, vd: 'Mùa 2'")
    @app_commands.default_permissions(administrator=True)
    async def end_season(self, interaction: discord.Interaction, new_season_name: str):
        current = db.get_active_season()
        new_season_id = db.end_season_transaction(new_season_name)
        if new_season_id is None:
            await interaction.response.send_message("Không có Mùa nào đang hoạt động để chốt.", ephemeral=True)
            return
        icon = ICONS["ranking"]
        embed = discord.Embed(
            title=f"{icon} MÙA MỚI BẮT ĐẦU",
            description=f"'{current['name_vi']}' đã kết thúc, Ranking đã được chụp lại.\n"
                         f"Mùa mới: **{new_season_name}**",
            color=discord.Color.gold(),
        )
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="download_data", description="[Admin] Tải file dữ liệu hiện tại của bot")
    @app_commands.guilds(discord.Object(id=BOT_HOME_GUILD_ID))
    @app_commands.default_permissions(administrator=True)
    async def download_data(self, interaction: discord.Interaction):
        # Giới hạn cứng: chỉ đúng tài khoản admin này mới thực sự dùng được,
        # kể cả nếu ai khác trong server cũng có quyền Administrator.
        if interaction.user.id != DATA_ADMIN_USER_ID:
            embed = error_handler.player_error_embed("invalid_target")
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        if not os.path.exists(DB_PATH):
            embed = error_handler.player_error_embed("not_found")
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        await interaction.response.send_message(
            content="📦 File dữ liệu hiện tại của bot:",
            file=discord.File(DB_PATH),
            ephemeral=True,
        )


async def setup(bot: commands.Bot):
    await bot.add_cog(MenuCog(bot))
