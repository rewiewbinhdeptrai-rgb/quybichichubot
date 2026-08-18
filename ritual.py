"""
Ritual Engine (mục 20 trong spec).

Trước đây progression.perform_advancement() roll một tỉ lệ 85% CỐ ĐỊNH,
không liên quan gì tới Potion/Characteristic/Materials — đúng kiểu "admin-like
UI tự tăng Sequence" mà mục 12 cấm. File này thay bằng:

    Potion stability + Beyonder Characteristic stability (mục 21)
    + Materials có đủ hay không (mục 20)
    ↓
    Success chance thật (không còn hằng số 85%)
    ↓
    Roll -> Success / Interruption / Backlash (mục 20: Ritual Result)

progression.py CHỈ được gọi ritual.attempt() rồi xử lý kết quả (đổi Sequence,
cấp Characteristic, ...) — không tự roll random ở đó nữa.
"""
import random

import database as db
import house as house_engine


class RitualError(Exception):
    """Lỗi nghiệp vụ (thiếu vật liệu Nghi thức...) — hiển thị thẳng cho
    người chơi, không phải bug."""


def get_materials(pathway_id: str, target_sequence: int):
    return db.get_ritual_materials(pathway_id, target_sequence)


def compute_success_chance(character: dict, potion: dict) -> int:
    """Base = potion['stability'] (độ ổn định công thức, mục 9). Cộng thêm
    bonus nhỏ từ Beyonder Characteristic đang sở hữu (mục 21: Stability của
    Characteristic góp phần ổn định Nghi thức tiến cấp tiếp theo — mục 49:
    hệ thống phải đồng bộ với nhau, không phải hai module tách biệt hoàn
    toàn). Trừ đi loss_of_control_risk hiện tại của Character (mục 13: nguy
    cơ mất kiểm soát cao thì Nghi thức càng bất ổn). Kẹp trong khoảng 5-95 —
    không bao giờ chắc chắn 100% thành công hay chắc chắn thất bại."""
    base = potion["stability"]

    characteristics = db.list_character_characteristics(character["character_id"])
    stored = [c for c in characteristics if c["state"] == "stored"]
    characteristic_bonus = 0
    if stored:
        avg_stability = sum(c["stability"] for c in stored) / len(stored)
        characteristic_bonus = round(avg_stability * 0.1)

    risk_penalty = character.get("loss_of_control_risk", 0) or 0

    # 🕯️ Phòng Nghi thức (mục 42 mở rộng — house.py) cộng thêm điểm % thành
    # công thật, không phải chỉ hiện khác trên Embed.
    room_bonus = house_engine.ritual_success_bonus(character["character_id"])

    chance = base + characteristic_bonus + room_bonus - risk_penalty
    return max(5, min(95, round(chance)))


def attempt(character: dict, pathway_id: str, target_sequence: int, potion: dict) -> dict:
    """Thực hiện 1 lần Nghi thức: kiểm tra + tiêu thụ Materials (atomic), roll
    theo success chance thật, trả về outcome. KHÔNG tự đổi Sequence ở đây —
    progression.py mới là nơi cập nhật state Character sau khi có kết quả.

    Trả về dict: {"outcome": "success"|"interruption"|"backlash",
                  "roll": int, "chance": int, "materials": list}
    """
    character_id = character["character_id"]
    materials = get_materials(pathway_id, target_sequence)
    if not materials:
        raise RitualError("Chưa có vật liệu Nghi thức cho Sequence này.")

    consumed = db.consume_ritual_materials_transaction(character_id, materials)
    if not consumed:
        missing = ", ".join(
            f"{m['name_en']} x{m['quantity']}" for m in materials
        )
        raise RitualError(f"Không đủ vật liệu Nghi thức trong Túi đồ. Cần: {missing}")

    chance = compute_success_chance(character, potion)
    roll = random.randint(1, 100)

    if roll <= chance:
        outcome = "success"
    elif roll <= chance + 10:
        # Interruption (mục 20): Nghi thức bị gián đoạn giữa chừng — mất vật
        # liệu nhưng KHÔNG có phản chấn, tiến độ Digestion giữ nguyên.
        outcome = "interruption"
    else:
        outcome = "backlash"

    db.log_ritual(character_id, pathway_id, target_sequence, outcome, roll, chance)
    return {"outcome": outcome, "roll": roll, "chance": chance, "materials": materials}
