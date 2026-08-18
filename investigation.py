"""
Investigation Engine (mục 27 trong spec).

Flow: Event -> Observe -> Clue -> Analyze -> Hypothesis -> Investigate ->
Resolution. KHÔNG phải quest tuyến tính "bấm nút nhận thưởng":

    Observe (mỗi lần chỉ find_chance% tìm ra Clue tiếp theo)
    ↓
    Clue được lưu thật vào character_clues (mục 27: "Clue phải được lưu")
    ↓
    Khi đã tìm đủ min_clue_ratio% Clue -> có thể Resolve
    ↓
    Resolve: success chance tăng theo tỉ lệ Clue (đặc biệt Key Clue) đã tìm —
    không phải hằng số. Roll thật, có thể "Hiểu sai" (mục 27: người chơi có
    thể bỏ sót clue, hiểu sai, hoặc phát hiện bí mật).

reward money/exp đi qua db.apply_combat_result() — dùng lại đúng 1 hàm ghi
Tiền/EXP có sẵn trong hệ thống (mục 49: không update rời rạc từng nơi), giữ
nguyên HP hiện tại của Character.
"""
import random

import database as db
import achievements


class InvestigationError(Exception):
    """Lỗi nghiệp vụ (chưa bắt đầu, chưa đủ Clue để Resolve...) — hiển thị
    thẳng cho người chơi, không phải bug."""


def list_at_location(location_id: str):
    return db.list_investigations_at_location(location_id)


def get_investigation(investigation_id: str):
    return db.get_investigation(investigation_id)


def get_progress(character_id: int, investigation_id: str):
    """Trả về dict tiến độ thật: found/total clue, found/total key clue,
    status hiện tại ('not_started' nếu chưa Bắt đầu)."""
    clues = db.list_investigation_clues(investigation_id)
    found_ids = db.list_found_clue_ids(character_id, investigation_id)
    character_investigation = db.get_character_investigation(character_id, investigation_id)

    key_clues = [c for c in clues if c["is_key_clue"]]
    found_key = [c for c in key_clues if c["clue_id"] in found_ids]

    return {
        "status": character_investigation["status"] if character_investigation else "not_started",
        "clues": clues,
        "found_ids": found_ids,
        "found_count": len(found_ids),
        "total_count": len(clues),
        "found_key_count": len(found_key),
        "total_key_count": len(key_clues),
    }


def start(character: dict, investigation_id: str):
    investigation = db.get_investigation(investigation_id)
    if investigation is None:
        raise InvestigationError("Vụ việc này không tồn tại.")

    existing = db.get_character_investigation(character["character_id"], investigation_id)
    if existing is not None:
        raise InvestigationError("Bạn đã bắt đầu điều tra vụ việc này rồi.")

    db.start_character_investigation(character["character_id"], investigation_id)
    db.log_action(character["character_id"], "investigation_start", investigation["name_en"])
    return investigation


def observe(character: dict, investigation_id: str):
    """Một lần Quan sát: nhắm vào Clue chưa tìm ra có order_index nhỏ nhất,
    roll theo find_chance% của đúng Clue đó. Trả về (clue|None, found: bool).
    Vẫn tốn 1 lượt Quan sát dù có tìm ra Clue hay không — không auto-nhặt hết."""
    character_id = character["character_id"]
    character_investigation = db.get_character_investigation(character_id, investigation_id)
    if character_investigation is None or character_investigation["status"] != "active":
        raise InvestigationError("Bạn chưa bắt đầu điều tra vụ việc này.")

    clues = db.list_investigation_clues(investigation_id)
    found_ids = db.list_found_clue_ids(character_id, investigation_id)
    remaining = [c for c in clues if c["clue_id"] not in found_ids]
    if not remaining:
        raise InvestigationError("Bạn đã tìm ra mọi manh mối tại đây — có thể Phân tích để Kết luận.")

    target = remaining[0]
    roll = random.randint(1, 100)
    found = roll <= target["find_chance"]

    if found:
        db.add_found_clue(character_id, investigation_id, target["clue_id"])
        db.log_action(character_id, "investigation_observe", f"found:{target['clue_id']}")
    else:
        db.log_action(character_id, "investigation_observe", f"missed:{target['clue_id']}")

    return target, found


def compute_resolution_chance(progress: dict) -> int:
    """Success chance = 30 nền + tỉ lệ Clue thường tìm được + bonus riêng cho
    Key Clue (nặng hơn vì Key Clue mang thông tin quyết định). Kẹp 10-95 —
    không bao giờ chắc chắn Hiểu đúng hay chắc chắn Hiểu sai."""
    total = progress["total_count"] or 1
    normal_found = progress["found_count"] - progress["found_key_count"]
    normal_total = max(1, total - progress["total_key_count"])

    base = 30
    normal_ratio_bonus = round((normal_found / normal_total) * 30)
    key_ratio_bonus = 0
    if progress["total_key_count"]:
        key_ratio_bonus = round((progress["found_key_count"] / progress["total_key_count"]) * 40)

    chance = base + normal_ratio_bonus + key_ratio_bonus
    return max(10, min(95, chance))


def resolve(character: dict, investigation_id: str):
    """Phân tích + Kết luận (Analyze -> Hypothesis -> Resolution). Chỉ chạy
    được khi đã tìm đủ min_clue_ratio% Clue. Trả về dict:
    {"success": bool, "roll": int, "chance": int, "reward": dict|None}"""
    character_id = character["character_id"]
    investigation = db.get_investigation(investigation_id)
    if investigation is None:
        raise InvestigationError("Vụ việc này không tồn tại.")

    progress = get_progress(character_id, investigation_id)
    if progress["status"] != "active":
        raise InvestigationError("Bạn chưa bắt đầu điều tra, hoặc vụ việc này đã có Kết luận.")

    found_ratio = round((progress["found_count"] / (progress["total_count"] or 1)) * 100)
    if found_ratio < investigation["min_clue_ratio"]:
        raise InvestigationError(
            f"Chưa đủ manh mối để Kết luận — cần ít nhất {investigation['min_clue_ratio']}% "
            f"(hiện có {found_ratio}%). Hãy Quan sát thêm."
        )

    chance = compute_resolution_chance(progress)
    roll = random.randint(1, 100)
    success = roll <= chance

    reward = None
    if success:
        db.resolve_character_investigation(character_id, investigation_id, "resolved_success")
        db.apply_combat_result(
            character_id, character["hp"], investigation["reward_money"], investigation["reward_exp"]
        )
        achievements.unlock(character_id, "first_investigation")
        if investigation["reward_item_id"]:
            db.add_inventory_item(character_id, investigation["reward_item_id"], 1)
        db.log_action(character_id, "investigation_resolve_success", investigation["name_en"])
        reward = {
            "money": investigation["reward_money"],
            "exp": investigation["reward_exp"],
            "item_id": investigation["reward_item_id"],
        }
    else:
        # Hiểu sai (mục 27): vụ việc đóng lại KHÔNG thưởng — không cho phép
        # Resolve lại vô hạn tới khi đúng, để mỗi lần Kết luận thật sự có giá.
        db.resolve_character_investigation(character_id, investigation_id, "resolved_failed")
        db.log_action(character_id, "investigation_resolve_failed", investigation["name_en"])

    return {"success": success, "roll": roll, "chance": chance, "reward": reward}
