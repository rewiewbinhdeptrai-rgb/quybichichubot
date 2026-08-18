"""
Localization loader (mục 60-61 trong spec).

users.language đã tồn tại từ trước (mục 65-66), nhưng chưa có nơi nào thực sự
đọc file locales/*.json — mọi text trong cogs/menu.py vẫn hardcode tiếng Việt.
File này là lớp nền: load locales/vi.json + locales/en.json một lần, cung cấp
t(key, lang) tra cứu có fallback về tiếng Việt (ngôn ngữ mặc định — mục 60)
rồi về chính key nếu vẫn thiếu, để không bao giờ vỡ UI vì thiếu bản dịch.

TRẠNG THÁI: đã bọc đủ các string CHUNG (menu chính, nút bấm dùng lại nhiều
nơi, Chợ đen, Loss of Control, Cài đặt, House — kho/Phòng chức năng/Nâng
Tier). Phần lớn embed chi tiết khác trong cogs/menu.py (4900+ dòng) vẫn
hardcode tiếng Việt trực tiếp — đây là công việc tách dần từng module, không
làm một lần để tránh phá vỡ UI đang chạy được.
Muốn thêm bản dịch cho module khác: thêm key mới vào CẢ HAI file JSON rồi gọi
i18n.t("key.moi", lang) tại nơi cần, theo đúng mẫu đã dùng trong LanguageSelect
và MainMenuSelect.
"""
import json
from pathlib import Path
from functools import lru_cache

LOCALES_DIR = Path(__file__).parent / "locales"
DEFAULT_LANG = "vi"


@lru_cache(maxsize=None)
def _load(lang: str) -> dict:
    path = LOCALES_DIR / f"{lang}.json"
    if not path.exists():
        return {}
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def t(key: str, lang: str = None, default: str = None, **kwargs) -> str:
    """Tra cứu 'a.b.c' theo key lồng nhau trong JSON. Fallback: lang đã chọn
    -> DEFAULT_LANG -> default (nếu truyền vào) -> chính key (không bao giờ
    raise, không bao giờ để UI hiện chuỗi rỗng)."""
    lang = lang or DEFAULT_LANG
    for candidate_lang in (lang, DEFAULT_LANG):
        data = _load(candidate_lang)
        node = data
        found = True
        for part in key.split("."):
            if isinstance(node, dict) and part in node:
                node = node[part]
            else:
                found = False
                break
        if found and isinstance(node, str):
            try:
                return node.format(**kwargs) if kwargs else node
            except (KeyError, IndexError):
                return node
    return default if default is not None else key


def user_lang(user_id: str) -> str:
    """Đọc users.language đã có sẵn trong database.py (mục 65-66)."""
    import database as db
    user = db.get_or_create_user(user_id)
    return (user or {}).get("language") or DEFAULT_LANG
