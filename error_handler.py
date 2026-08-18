"""
Error Handler — lớp chặn giữa Engine và người chơi.

Nguyên tắc bắt buộc: người chơi KHÔNG BAO GIỜ được nhìn thấy chi tiết kỹ
thuật nội bộ (tên bảng DB, tên biến, traceback, SQL, ID nội bộ, tên
class/function, exception message gốc, API key/provider, trạng thái
migration, thông báo transaction/rollback...). Mọi lỗi phải đi qua:

    INTERNAL ERROR -> log kỹ thuật cho DEV (console/file) -> thông báo
    đã chuẩn hoá cho PLAYER.

Cách dùng:
- Bọc mọi callback của discord.ui (Select/Button/Modal) bằng decorator
  @safe_interaction để bất kỳ exception nào cũng tự động được chặn lại,
  ghi log kỹ thuật, và trả về một Embed an toàn cho người chơi thay vì
  để Discord hiện traceback hoặc để exception rơi ra ngoài.
- Dùng player_message(reason_key) ở bất kỳ đâu cần trả lời "thất bại
  nhưng không phải lỗi hệ thống" (vd không đủ tiền, không đủ nguyên liệu)
  để giữ giọng văn Quỷ Bí nhất quán, KHÔNG liên quan tới exception.
"""
import functools
import logging
import re
import traceback
import uuid

import discord

import database as db

logger = logging.getLogger("quyby.engine")
if not logger.handlers:
    _handler = logging.StreamHandler()
    _handler.setFormatter(logging.Formatter("[%(asctime)s] %(levelname)s %(name)s: %(message)s"))
    logger.addHandler(_handler)
    logger.setLevel(logging.INFO)

# Các câu thông báo trung tính, đúng giọng văn Quỷ Bí, KHÔNG tiết lộ nguyên
# nhân kỹ thuật. reason_key -> (title, description).
PLAYER_MESSAGES = {
    "generic": (
        "🌑 Có gì đó bất thường",
        "Linh tính truyền đến một cảm giác bất thường... Hành động không thể tiếp tục lúc này. Vui lòng thử lại sau.",
    ),
    "not_found": (
        "🌑 Không tìm thấy",
        "Thứ bạn tìm kiếm dường như không còn ở đây nữa.",
    ),
    "insufficient_resource": (
        "⚠️ Chưa đủ điều kiện",
        "Bạn chưa hội đủ điều kiện để thực hiện hành động này.",
    ),
    "no_character": (
        "⚠️ Chưa có nhân vật",
        "Bạn cần tạo nhân vật trước khi tiếp tục.",
    ),
    "cooldown": (
        "⏳ Chưa đến lúc",
        "Hành động này chưa thể thực hiện lại ngay lúc này.",
    ),
    "invalid_target": (
        "⚠️ Không hợp lệ",
        "Lựa chọn này hiện không khả dụng.",
    ),
}


def _new_incident_id() -> str:
    """Mã sự cố ngắn, an toàn để hiện cho người chơi (không tiết lộ gì) —
    dùng để đối chiếu với log kỹ thuật phía dev khi cần điều tra."""
    return uuid.uuid4().hex[:8]


def _sanitize_for_dev_log(exc: Exception) -> str:
    """Chuỗi log kỹ thuật đầy đủ — CHỈ ghi ra logger phía dev, không bao
    giờ trả về Discord."""
    return "".join(traceback.format_exception(type(exc), exc, exc.__traceback__))


def player_error_embed(reason_key: str = "generic", incident_id: str = None) -> discord.Embed:
    title, desc = PLAYER_MESSAGES.get(reason_key, PLAYER_MESSAGES["generic"])
    embed = discord.Embed(title=title, description=desc, color=discord.Color.dark_grey())
    if incident_id:
        embed.set_footer(text=f"Mã tham chiếu: {incident_id}")
    return embed


class PlayerFacingError(Exception):
    """Raise trong service layer khi muốn hiển thị một thông báo NGẮN, an
    toàn cho người chơi (vd 'Bạn chưa đủ tiền') mà không cần log như lỗi hệ
    thống. Message của exception này PHẢI đã ở dạng an toàn để hiển thị —
    không được chứa tên biến/bảng/class."""

    def __init__(self, message_vi: str, title: str = "⚠️ Không thể thực hiện"):
        super().__init__(message_vi)
        self.title = title
        self.message_vi = message_vi


async def _respond_safe(interaction: discord.Interaction, embed: discord.Embed, view=None):
    try:
        if interaction.response.is_done():
            await interaction.followup.send(embed=embed, view=view, ephemeral=True)
        else:
            await interaction.response.edit_message(embed=embed, view=view)
    except discord.HTTPException:
        # Ngay cả bước báo lỗi cũng có thể fail (interaction hết hạn...).
        # Không còn gì để làm thêm phía player — chỉ log kỹ thuật.
        logger.warning("Không thể gửi thông báo lỗi tới người chơi (interaction có thể đã hết hạn).")


async def handle_unexpected(interaction: discord.Interaction, exc: Exception, handler_name: str, view=None):
    """Điểm chặn cuối cùng dùng chung: log kỹ thuật đầy đủ cho DEV (kèm mã
    sự cố để đối chiếu), rồi trả về đúng một Embed trung lập, an toàn cho
    người chơi. KHÔNG BAO GIỜ để traceback/tên biến/class/SQL/ID nội bộ lọt
    ra Discord — bất kể exception là gì.

    Dùng chung bởi decorator `safe_interaction` (bọc từng callback) và bởi
    `SafeView.on_error` (lưới an toàn ở cấp View, bắt cả những callback nào
    lỡ chưa được bọc riêng)."""
    if isinstance(exc, PlayerFacingError):
        embed = discord.Embed(title=exc.title, description=exc.message_vi, color=discord.Color.orange())
        await _respond_safe(interaction, embed, view)
        return

    incident_id = _new_incident_id()
    dev_detail = _sanitize_for_dev_log(exc)
    logger.error("incident=%s handler=%s\n%s", incident_id, handler_name, dev_detail)
    try:
        db.log_engine_error(incident_id, handler_name, dev_detail)
    except Exception:
        # Logging phụ bị lỗi thì cũng không được để lộ gì thêm cho player.
        pass
    embed = player_error_embed("generic", incident_id)
    await _respond_safe(interaction, embed, view)


def safe_interaction(fallback_view_factory=None):
    """Decorator bọc callback của discord.ui (Select/Button/Modal).

    - PlayerFacingError -> hiện đúng message_vi (đã soạn sẵn an toàn).
    - Exception khác (bug, lỗi DB, lỗi kỹ thuật bất kỳ) -> KHÔNG BAO GIỜ lộ
      ra Discord. Log traceback đầy đủ phía dev kèm mã sự cố, người chơi
      chỉ thấy thông báo trung tính.
    """

    def decorator(func):
        @functools.wraps(func)
        async def wrapper(self, interaction: discord.Interaction, *args, **kwargs):
            try:
                return await func(self, interaction, *args, **kwargs)
            except Exception as e:  # noqa: BLE001 - đây chính là điểm chặn cuối cùng
                view = fallback_view_factory() if fallback_view_factory else None
                await handle_unexpected(interaction, e, func.__qualname__, view)

        return wrapper

    return decorator


_SENSITIVE_PATTERNS = [
    re.compile(r"(?i)\btraceback\b.*"),
    re.compile(r"(?i)\bsqlite3\.\w+\b"),
    re.compile(r"(?i)\bno such (table|column)\b.*"),
    re.compile(r"(?i)\bcharacter_id\s*=?\s*\d+"),
    re.compile(r"(?i)\b\w+_id\s*=?\s*\d+"),
    re.compile(r"(?i)\bapi[_ ]?key\b.*", re.IGNORECASE),
    re.compile(r"(?i)\btransaction (failed|rolled back)\b.*"),
    re.compile(r"(?i)\bKeyError\b.*"),
    re.compile(r"(?i)File \"[^\"]+\.py\".*"),
]


def looks_technical(text: str) -> bool:
    """Kiểm tra nhanh một chuỗi text (vd trước khi log AI Narrative output
    hoặc trước khi đưa message tự do vào Embed) có khả năng chứa thông tin
    kỹ thuật nội bộ hay không, để chặn lại thay vì gửi thẳng cho người chơi."""
    return any(p.search(text) for p in _SENSITIVE_PATTERNS)
