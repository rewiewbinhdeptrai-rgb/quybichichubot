"""House Engine (mục 42 mở rộng) — kho lưu trữ riêng tách biệt Inventory
mang theo người, cộng 4 Phòng chức năng nâng cấp độc lập và Tier nhà tổng
thể. Chuyển đồ giữa hai kho, nâng cấp phòng, và nâng Tier đều là transaction
atomic thật (xem database.py) — không có trường hợp trừ tiền mà không lên
cấp, hoặc lên cấp mà không trừ tiền.

4 Phòng chức năng cho bonus cơ học THẬT ở đúng engine liên quan, không phải
chỉ số trang trí trên Embed (đúng tinh thần mục 15/51 — mọi buff phải đi qua
số liệu thật):
- 🔬 Phòng Nghiên cứu (research) -> giảm % Spirituality cần cho Mysticism
  Knowledge (mysticism.py).
- 🧪 Phòng Luyện dược (potion)   -> giảm % craft_risk khi Chế tạo Potion
  (potions.py).
- 🕯️ Phòng Nghi thức (ritual)    -> cộng thêm điểm % tỉ lệ thành công Ritual
  (ritual.py).
- 🗝️ Phòng Cổ vật (artifact)     -> giảm % tỉ lệ kích hoạt Side Effect khi
  Experiment Sealed Artifact (artifacts.py).

Mỗi phòng tối đa MAX_ROOM_LEVEL, Tier nhà tối đa MAX_TIER. Đây là hệ thống
sink tiền hợp lệ trong game (mục 37: Economy cần có nơi tiêu tiền lâu dài
ngoài Market/Contract).
"""
import database as db

ROOM_TYPES = ("research", "potion", "ritual", "artifact")
MAX_ROOM_LEVEL = 5
MAX_TIER = 5

# Bonus mỗi level, tính theo % (điểm phần trăm) — kẹp lại ở nơi tiêu thụ để
# không bao giờ vượt quá giới hạn hợp lý (vd risk không thể âm).
_ROOM_BONUS_PER_LEVEL = {
    "research": 5,   # -5%/level chi phí Spirituality cho Mysticism
    "potion": 3,      # -3%/level craft_risk khi Chế tạo Potion
    "ritual": 3,      # +3%/level tỉ lệ thành công Ritual
    "artifact": 5,    # -5%/level tỉ lệ Side Effect khi Experiment Artifact
}


class HouseError(Exception):
    """Lỗi nghiệp vụ hiển thị thẳng cho người chơi."""


def get_house(character_id: int):
    house = db.get_or_create_house(character_id)
    house["storage"] = db.list_house_storage(character_id)
    house["rooms"] = db.get_house_rooms(character_id)
    return house


def store_item(character_id: int, item_id: str, quantity: int):
    if quantity <= 0:
        raise HouseError("Số lượng phải lớn hơn 0.")
    ok = db.store_item_in_house_transaction(character_id, item_id, quantity)
    if not ok:
        raise HouseError("Bạn không có đủ số lượng vật phẩm này trong túi.")


def withdraw_item(character_id: int, item_id: str, quantity: int):
    if quantity <= 0:
        raise HouseError("Số lượng phải lớn hơn 0.")
    ok = db.withdraw_item_from_house_transaction(character_id, item_id, quantity)
    if not ok:
        raise HouseError("Kho của bạn không có đủ số lượng vật phẩm này.")


# ---------- Phòng chức năng (Rooms) ----------

def room_upgrade_cost(current_level: int) -> int:
    """Công thức chi phí tăng dần — cấp sau luôn đắt hơn cấp trước, giữ vai
    trò money sink dài hạn thay vì có thể max hết trong 1-2 giao dịch."""
    return 500 * (current_level + 1)


def get_rooms(character_id: int) -> dict:
    return db.get_house_rooms(character_id)


def upgrade_room(character_id: int, room_type: str) -> dict:
    if room_type not in ROOM_TYPES:
        raise HouseError("Phòng chức năng này không tồn tại.")
    current_level = db.get_house_room_level(character_id, room_type)
    if current_level >= MAX_ROOM_LEVEL:
        raise HouseError(f"Phòng này đã đạt cấp tối đa ({MAX_ROOM_LEVEL}).")
    cost = room_upgrade_cost(current_level)
    ok = db.upgrade_house_room_transaction(character_id, room_type, cost, MAX_ROOM_LEVEL)
    if not ok:
        raise HouseError(f"Bạn không đủ {cost:,} Bảng để nâng cấp phòng này.")
    return {"room_type": room_type, "new_level": current_level + 1, "cost": cost}


# ---------- Tier nhà (Storage) ----------

def tier_upgrade_cost(current_tier: int) -> int:
    return 2000 * current_tier


def tier_slot_bonus() -> int:
    return 10


def upgrade_tier(character_id: int) -> dict:
    house = db.get_or_create_house(character_id)
    current_tier = house["tier"]
    if current_tier >= MAX_TIER:
        raise HouseError(f"Nhà đã đạt Tier tối đa ({MAX_TIER}).")
    cost = tier_upgrade_cost(current_tier)
    slot_increase = tier_slot_bonus()
    ok = db.upgrade_house_tier_transaction(character_id, cost, slot_increase, MAX_TIER)
    if not ok:
        raise HouseError(f"Bạn không đủ {cost:,} Bảng để nâng Tier nhà.")
    return {"new_tier": current_tier + 1, "cost": cost, "slot_increase": slot_increase}


# ---------- Bonus getters — dùng ở các engine khác (potions/mysticism/ritual/artifacts) ----------

def research_sp_discount(character_id: int) -> int:
    """% giảm chi phí Spirituality cho Mysticism Knowledge, kẹp 0-60%."""
    level = db.get_house_room_level(character_id, "research")
    return min(60, level * _ROOM_BONUS_PER_LEVEL["research"])


def potion_risk_reduction(character_id: int) -> int:
    """% điểm giảm craft_risk khi Chế tạo Potion, kẹp 0-40 điểm."""
    level = db.get_house_room_level(character_id, "potion")
    return min(40, level * _ROOM_BONUS_PER_LEVEL["potion"])


def ritual_success_bonus(character_id: int) -> int:
    """% điểm cộng thêm vào tỉ lệ thành công Ritual, kẹp 0-30 điểm."""
    level = db.get_house_room_level(character_id, "ritual")
    return min(30, level * _ROOM_BONUS_PER_LEVEL["ritual"])


def artifact_side_effect_reduction(character_id: int) -> int:
    """% điểm giảm tỉ lệ kích hoạt Side Effect khi Experiment, kẹp 0-60 điểm."""
    level = db.get_house_room_level(character_id, "artifact")
    return min(60, level * _ROOM_BONUS_PER_LEVEL["artifact"])
