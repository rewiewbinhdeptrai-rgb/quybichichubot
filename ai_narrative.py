"""
AI Narrative layer (mục 29 trong spec).

Vai trò DUY NHẤT của module này: viết lại một câu thoại/tường thuật cho
mượt hơn, dựa trên nội dung mà Game Engine đã quyết định sẵn (NPC nào,
trust tier nào, câu thoại tĩnh gốc là gì...). Module này KHÔNG có quyền:

    - đổi Trust, HP, tiền, item, Sequence, Digestion...
    - tự bịa nội dung không dựa trên prompt do Engine đưa
    - làm Engine dừng lại nếu API lỗi

Yêu cầu bắt buộc:
    1. Mỗi lần gọi Gemini phải ghi đúng 1 dòng log — "OK" nếu thành công,
       "FAILED" nếu thất bại — và CHỈ ghi vào log server (qua module
       `logging` chuẩn), không bao giờ gửi 2 dòng đó lên Discord.
    2. Người chơi không bao giờ thấy exception, traceback, tên file, tên
       biến, model name, API key hay bất kỳ chi tiết kỹ thuật/nội bộ nào.
       Nếu có lỗi, người chơi chỉ nhận lại `fallback` — coi như AI chưa
       từng được gọi.
"""
import logging

from config import GEMINI_API_KEY, GEMINI_MODEL

log = logging.getLogger("quyby-bot.ai")

_model = None
_unavailable = False  # True nếu thiếu key hoặc import/khởi tạo lỗi 1 lần


def _get_model():
    """Khởi tạo model Gemini một lần duy nhất (lazy). Không bao giờ raise
    ra ngoài — mọi lỗi được nuốt lại thành `_unavailable = True`."""
    global _model, _unavailable

    if _model is not None:
        return _model
    if _unavailable:
        return None
    if not GEMINI_API_KEY:
        _unavailable = True
        return None

    try:
        import google.generativeai as genai

        genai.configure(api_key=GEMINI_API_KEY)
        _model = genai.GenerativeModel(GEMINI_MODEL)
        return _model
    except Exception:
        _unavailable = True
        return None


def generate_line(prompt: str, fallback: str) -> str:
    """
    Sinh MỘT câu thoại/tường thuật ngắn từ Gemini.

    `prompt`   — ngữ cảnh do Engine chuẩn bị sẵn (đã đủ thông tin cần thiết).
    `fallback` — câu thoại tĩnh có sẵn trong Database, dùng khi AI không
                 khả dụng vì bất kỳ lý do gì (thiếu key, mất mạng, hết hạn
                 mức, timeout, response rỗng...).

    Luôn trả về một chuỗi hiển thị được cho người chơi. Không bao giờ raise.
    """
    model = _get_model()
    if model is None:
        log.warning("Gemini narrative call FAILED")
        return fallback

    try:
        response = model.generate_content(prompt)
        text = (getattr(response, "text", None) or "").strip()
        if not text:
            raise ValueError("empty response")
    except Exception:
        log.warning("Gemini narrative call FAILED")
        return fallback

    log.info("Gemini narrative call OK")
    return text
