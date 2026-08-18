"""
Potion Crafting Engine (mục 9: Recipe -> Ingredients -> Craft -> Potion).

Tách riêng khỏi progression.py: progression.py chỉ lo Drink -> Adaptation ->
Acting -> Digestion -> Advancement (một Potion ĐÃ có sẵn trong kho). File này
lo bước TRƯỚC đó — biến nguyên liệu trong Inventory thành một Potion sở hữu
được (character_potions), đúng flow mục 9 chứ không phải Potion "tự nhiên có"
chỉ vì dữ liệu tĩnh tồn tại.
"""
import random

import database as db
import effects
import house as house_engine


class CraftError(Exception):
    """Lỗi nghiệp vụ (thiếu nguyên liệu, chưa có công thức...) — hiển thị
    thẳng cho người chơi, không phải bug."""


def get_recipe(pathway_id: str, target_sequence: int):
    recipe = db.get_potion_recipe(pathway_id, target_sequence)
    if not recipe:
        raise CraftError("Chưa có công thức cho Ma dược này.")
    return recipe


def craft_potion(character: dict, target_sequence: int):
    """Chế tạo 1 Potion hướng tới target_sequence. Trừ TOÀN BỘ nguyên liệu dù
    thành công hay thất bại (mục 9: Potion failure — nguyên liệu vẫn mất khi
    hỏng, không phải chỉ khi thành công). Tỉ lệ thất bại lấy từ
    potions.craft_risk (dữ liệu tĩnh, không phải AI random tự nghĩ).

    Trả về dict: {"success": bool, "recipe": list, "potion": dict}
    """
    character_id = character["character_id"]
    pathway_id = character["pathway_id"]
    if pathway_id is None:
        raise CraftError("Nhân vật chưa chọn Pathway.")

    potion = db.get_potion(pathway_id, target_sequence)
    if potion is None:
        raise CraftError("Chưa có Ma dược cho Sequence này.")

    recipe = get_recipe(pathway_id, target_sequence)

    # 🧪 Phòng Luyện dược (mục 42 mở rộng — house.py) giảm craft_risk thật,
    # không chỉ hiện số khác trên Embed. Kẹp tối thiểu 5% để không bao giờ
    # thành "chắc chắn không hỏng" (đúng tinh thần mục 20 về Potion failure).
    effective_risk = max(5, potion["craft_risk"] - house_engine.potion_risk_reduction(character_id))
    success = random.randint(1, 100) > effective_risk
    ok = db.craft_potion_transaction(character_id, pathway_id, target_sequence, recipe, success)
    if not ok:
        raise CraftError("Không đủ nguyên liệu trong Túi đồ để Chế tạo Potion này.")

    if success:
        db.log_action(character_id, "craft_potion_success", potion["name_en"])
    else:
        # Thất bại thật (mục 9/20: Potion failure/Backlash) — mất nguyên liệu, không
        # ra Potion, và gây một debuff nhẹ thay vì im lặng trừ đồ không hậu quả gì.
        effects.apply_effect(character_id, "potion_instability", source="craft_failure")
        db.log_action(character_id, "craft_potion_fail", potion["name_en"])

    return {"success": success, "recipe": recipe, "potion": potion}


def get_stock(character: dict, target_sequence: int) -> int:
    if character["pathway_id"] is None:
        return 0
    return db.get_potion_stock(character["character_id"], character["pathway_id"], target_sequence)
