"""
Potion -> Adaptation -> Acting -> Digestion -> Ritual -> Advancement
(mục 9-12 trong spec).

Đây là engine, KHÔNG phải nơi hiển thị — cogs/menu.py chỉ gọi các hàm ở
đây và render kết quả. Không có đường tắt nào để tự set Sequence: muốn
tăng Sequence bắt buộc phải digestion >= 100 rồi gọi perform_advancement().
"""
import database as db
import effects
import characteristics
import ritual as ritual_engine
import achievements
import ai_narrative
import loss_of_control
from data.acting_actions import get_actions


class ProgressionError(Exception):
    """Lỗi nghiệp vụ (vd: chưa uống Potion, Digestion chưa đủ...) — hiển thị
    thẳng cho người chơi, không phải bug."""


# Câu tĩnh dự phòng (mục 30) cho tường thuật Nghi thức — AI chỉ viết lại
# cho sống động hơn, KHÔNG đổi outcome đã roll xong trong ritual.attempt().
_RITUAL_FALLBACK = {
    "success": "Nghi thức hoàn tất trong im lặng — một luồng sức mạnh mới đã an vị.",
    "interruption": "Nghi thức đứt đoạn giữa chừng, năng lượng tản đi trước khi kịp thành hình.",
    "backlash": "Nghi thức phản chấn dữ dội, một phần tiến triển đã bị cuốn ngược trở lại.",
}


def _ritual_narrative(pathway_id: str, target_sequence: int, outcome: str) -> str:
    fallback = _RITUAL_FALLBACK[outcome]
    prompt = (
        f"Viết 1 câu tường thuật ngắn (không quá 2 câu), giọng văn huyền bí, "
        f"mô tả một Nghi thức tiến cấp Beyonder hướng tới Sequence {target_sequence} "
        f"của Pathway {pathway_id}, với kết quả '{outcome}'. Không thêm chi tiết "
        f"cơ chế (không nói số liệu roll/chance). Câu gốc tham khảo: \"{fallback}\""
    )
    return ai_narrative.generate_line(prompt, fallback=fallback)


def get_state(character: dict):
    """Trả về (progress, potion) hiện tại của Character đang theo Pathway của nó."""
    if not character or not character["pathway_id"]:
        raise ProgressionError("Nhân vật chưa chọn Pathway.")
    progress = db.get_progress(character["character_id"])
    potion = None
    if progress["potion_target_sequence"] is not None:
        potion = db.get_potion(character["pathway_id"], progress["potion_target_sequence"])
    return progress, potion


def start_potion(character: dict):
    """Uống Potion để bắt đầu hướng tới Sequence kế tiếp (current - 1).
    Gây Potion Instability debuff thật (mục 13, 15) — tăng Loss of Control Risk."""
    current_sequence = character["sequence_number"]
    if current_sequence <= 0:
        raise ProgressionError("Nhân vật đã ở Sequence 0 — không còn Potion nào cao hơn.")

    progress = db.get_progress(character["character_id"])
    if progress["status"] != "idle":
        raise ProgressionError("Đang trong quá trình tiêu hóa một Potion khác — không thể uống thêm.")

    target_sequence = current_sequence - 1
    potion = db.get_potion(character["pathway_id"], target_sequence)
    if potion is None:
        raise ProgressionError("Chưa có Ma dược cho Sequence này.")

    # Phải đã Chế tạo (mục 9: Craft trước Drink) — không được uống một Potion
    # mà Character chưa từng sở hữu. Xem potions.craft_potion().
    if not db.consume_potion_stock(character["character_id"], character["pathway_id"], target_sequence):
        raise ProgressionError(
            f"Bạn chưa Chế tạo {potion['name_en']} nào — vào 🧪 Ma dược → Chế tạo trước."
        )

    db.upsert_progress(character["character_id"], target_sequence, 0, "digesting")
    effects.apply_effect(character["character_id"], "potion_instability", source="potion_drink")
    db.log_action(character["character_id"], "drink_potion", potion["name_en"])
    return potion


def perform_acting(character: dict, action_key: str):
    """Thực hiện một Acting Method action -> cộng Digestion thật nếu action
    hợp lệ với Pathway hiện tại (mục 10-11). Cũng tick Effect Engine."""
    progress = db.get_progress(character["character_id"])
    if progress["status"] != "digesting":
        raise ProgressionError("Chưa uống Potion — không có gì để tiêu hóa.")

    actions = get_actions(character["pathway_id"])
    match = next((a for a in actions if a[0] == action_key), None)
    if match is None:
        raise ProgressionError("Hành động này không thuộc Acting Method của Pathway hiện tại.")

    _, label, gain = match
    new_digestion = min(100, progress["digestion"] + gain)
    new_status = "ready" if new_digestion >= 100 else "digesting"

    db.upsert_progress(
        character["character_id"], progress["potion_target_sequence"], new_digestion, new_status
    )

    # Spirituality hồi thật mỗi lượt Acting (mục 14) — trước đây modifier_key
    # "spirituality_regen_flat" chỉ tồn tại trong effect_definitions/artifact
    # (newly_advanced, artifact_pocket_watch_effect, artifact_seal_fragment_side)
    # mà KHÔNG có nơi nào đọc get_modifier_sum() cho key này -> buff/debuff
    # chỉ nằm trên Embed, vi phạm mục 15/51. Đọc trước khi tick() để buff còn
    # active của lượt này vẫn được tính, giống pattern combat.calculate_damage().
    base_regen = 2
    regen_bonus = effects.get_modifier_sum(character["character_id"], "spirituality_regen_flat")
    new_spirituality = max(
        0, min(character["spirituality_max"], round(character["spirituality"] + base_regen + regen_bonus))
    )
    db.set_character_hp_spirituality(character["character_id"], character["hp"], new_spirituality)

    effects.tick(character["character_id"])
    db.log_action(character["character_id"], "acting", f"{label} (+{gain}%)")
    return new_digestion, new_status, label


def perform_advancement(character: dict):
    """Nghi thức tiến cấp (mục 12, 20). Chỉ chạy được khi Digestion == 100%.
    Success chance giờ đến từ ritual.compute_success_chance() (Potion
    stability + Characteristic + Loss of Control Risk — mục 20/21), KHÔNG
    còn là hằng số 85% đứng một mình. Materials Nghi thức (mục 20) bị tiêu
    thụ thật qua ritual.attempt(), dù kết quả thành công hay không.

    Trả về dict: {"success": bool, "new_sequence": int|None, "message": str,
                  "outcome": str, "roll": int, "chance": int}
    """
    progress = db.get_progress(character["character_id"])
    if progress["status"] != "ready":
        raise ProgressionError("Digestion chưa đạt 100% — chưa đủ điều kiện làm Nghi thức.")

    character_id = character["character_id"]
    pathway_id = character["pathway_id"]
    target_sequence = progress["potion_target_sequence"]
    potion = db.get_potion(pathway_id, target_sequence)

    try:
        result = ritual_engine.attempt(character, pathway_id, target_sequence, potion)
    except ritual_engine.RitualError as e:
        raise ProgressionError(str(e))

    outcome = result["outcome"]

    if outcome == "success":
        new_sequence = target_sequence
        db.advance_character_sequence(character_id, new_sequence)
        db.upsert_progress(character_id, None, 0, "idle")
        effects.apply_effect(character_id, "newly_advanced", source="advancement_success")
        db.log_action(character_id, "advancement_success", f"Sequence -> {new_sequence}")
        # mục 21: đạt Sequence mới -> cấp Beyonder Characteristic thật, gắn chết
        # vào đúng (pathway, sequence) này, không phải item rơi ngẫu nhiên.
        gained_characteristic = characteristics.grant_from_advancement(
            character_id, pathway_id, new_sequence
        )
        if new_sequence <= 8:
            achievements.unlock(character_id, "sequence_8")
        if new_sequence <= 5:
            achievements.unlock(character_id, "sequence_5")
        return {
            "success": True,
            "new_sequence": new_sequence,
            "message": (
                f"Nghi thức thành công! (roll {result['roll']} <= {result['chance']}% chance) "
                "Sequence mới đã được ghi nhận."
            ),
            "outcome": outcome,
            "roll": result["roll"],
            "chance": result["chance"],
            "characteristic": gained_characteristic,
            "narrative": _ritual_narrative(pathway_id, target_sequence, outcome),
        }

    if outcome == "interruption":
        # mục 20: gián đoạn — mất vật liệu nhưng Digestion GIỮ NGUYÊN, không
        # có debuff phản chấn (khác Backlash), có thể thử lại ngay.
        db.log_action(character_id, "advancement_interruption", f"roll {result['roll']}/{result['chance']}")
        return {
            "success": False,
            "new_sequence": None,
            "message": (
                f"Nghi thức bị gián đoạn giữa chừng (roll {result['roll']} > {result['chance']}% chance). "
                "Mất vật liệu nhưng Digestion không đổi — có thể chuẩn bị vật liệu và thử lại."
            ),
            "outcome": outcome,
            "roll": result["roll"],
            "chance": result["chance"],
            "narrative": _ritual_narrative(pathway_id, target_sequence, outcome),
        }

    # Backlash (mục 20): mất tiến độ Digestion + debuff thật
    rolled_back = max(0, progress["digestion"] - 30)
    db.upsert_progress(character_id, target_sequence, rolled_back, "digesting")
    effects.apply_effect(character_id, "ritual_backlash", source="advancement_fail")
    db.log_action(character_id, "advancement_backlash", f"digestion -> {rolled_back}")
    # mục 13: "Ritual failure" nằm ngay trong danh sách nguồn Loss of Control
    # Risk của spec — trước đây chỉ compute_risk() (tính số) chạy đâu đó về
    # sau, resolve_incident() (áp hậu quả thật) chưa từng được gọi ở đúng mốc
    # rủi ro cao nhất của cả hệ thống Advancement. Giờ gọi thật ở đây.
    loss_of_control.compute_risk(character_id)
    incident = loss_of_control.resolve_incident(character_id)
    return {
        "success": False,
        "new_sequence": None,
        "message": (
            f"Nghi thức thất bại — phản chấn! (roll {result['roll']} > {result['chance']}% chance) "
            f"Digestion giảm còn {rolled_back}% và nhân vật dính Ritual Backlash."
        ),
        "outcome": outcome,
        "roll": result["roll"],
        "chance": result["chance"],
        "narrative": _ritual_narrative(pathway_id, target_sequence, outcome),
        "incident": incident,
    }
