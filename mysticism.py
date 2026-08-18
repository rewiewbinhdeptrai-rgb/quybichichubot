"""
Mysticism Knowledge Engine (mục 18 trong spec).

Flow bắt buộc: Unknown -> Discovered -> Studied -> Understood. Mỗi bước tốn
Spirituality thật (trừ trực tiếp trong DB, không chỉ hiện số trên Embed —
mục 14), và "Understood" có % Risk thật gây Loss of Control (mục 13) qua
EffectEngine — không phải random đơn giản đứng ngoài hệ thống chung.
"""
import random

import database as db
import effects
import loss_of_control
import house as house_engine


class MysticismError(Exception):
    """Lỗi nghiệp vụ (chưa đủ điều kiện, không đủ Spirituality...) — hiển
    thị thẳng cho người chơi, không phải bug."""


def list_catalog(character_id: int):
    """Merge catalog tĩnh + tiến độ Character. stage = 'unknown' nếu Character
    chưa có row (mục 18: Unknown là trạng thái ngầm định, không lưu DB)."""
    catalog = db.list_knowledge_catalog()
    owned = {row["knowledge_id"]: row for row in db.get_character_knowledge(character_id)}
    result = []
    for k in catalog:
        row = owned.get(k["knowledge_id"])
        merged = dict(k)
        merged["stage"] = row["stage"] if row else "unknown"
        result.append(merged)
    return result


def _discounted_cost(character_id: int, base_cost: int) -> int:
    """🔬 Phòng Nghiên cứu (mục 42 mở rộng — house.py) giảm % chi phí
    Spirituality thật. Kẹp tối thiểu 1 để không bao giờ về 0 (Knowledge vẫn
    phải tốn gì đó, không được miễn phí hoàn toàn)."""
    discount = house_engine.research_sp_discount(character_id)
    return max(1, round(base_cost * (100 - discount) / 100))


def _spend_spirituality(character_id: int, cost: int) -> int:
    cost = _discounted_cost(character_id, cost)
    character = db.get_character_by_id(character_id)
    if character["spirituality"] < cost:
        raise MysticismError(f"Không đủ Spirituality (cần {cost}, hiện có {character['spirituality']}).")
    db.set_character_hp_spirituality(character_id, character["hp"], character["spirituality"] - cost)
    return cost


def discover(character_id: int, knowledge_id: str) -> dict:
    k = db.get_knowledge(knowledge_id)
    if k is None:
        raise MysticismError("Kiến thức này chưa khả dụng.")
    if db.get_character_knowledge_row(character_id, knowledge_id):
        raise MysticismError("Bạn đã Phát hiện kiến thức này rồi.")

    _spend_spirituality(character_id, k["discover_cost"])
    db.upsert_character_knowledge(character_id, knowledge_id, "discovered")
    db.log_action(character_id, "knowledge_discover", k["name_en"])
    return k


def study(character_id: int, knowledge_id: str) -> dict:
    k = db.get_knowledge(knowledge_id)
    row = db.get_character_knowledge_row(character_id, knowledge_id)
    if row is None or row["stage"] != "discovered":
        raise MysticismError("Phải Phát hiện kiến thức này trước khi Nghiên cứu.")

    _spend_spirituality(character_id, k["study_cost"])
    db.upsert_character_knowledge(character_id, knowledge_id, "studied")
    db.log_action(character_id, "knowledge_study", k["name_en"])
    return k


def understand(character_id: int, knowledge_id: str) -> dict:
    """Bước sâu nhất — có Risk thật (mục 13, 18: nghiên cứu quá sâu vào
    Huyền bí là một trong các nguồn Loss of Control Risk)."""
    k = db.get_knowledge(knowledge_id)
    row = db.get_character_knowledge_row(character_id, knowledge_id)
    if row is None or row["stage"] != "studied":
        raise MysticismError("Phải Nghiên cứu kiến thức này trước khi Thấu hiểu.")

    _spend_spirituality(character_id, k["understand_cost"])

    risk_triggered = False
    incident = None
    if random.randint(1, 100) <= k["understand_risk"]:
        effects.apply_effect(character_id, "mysticism_overreach", source=f"knowledge:{knowledge_id}")
        risk_triggered = True
        # Trước đây risk_triggered chỉ áp 1 debuff cố định — resolve_incident()
        # (4 tier hậu quả thật của mục 13) chưa từng được gọi ở mốc rủi ro cao
        # này dù docstring engine tự nhận đây là nơi nên gọi. Giờ gọi thật.
        loss_of_control.compute_risk(character_id)
        incident = loss_of_control.resolve_incident(character_id)

    db.upsert_character_knowledge(character_id, knowledge_id, "understood")
    if k["unlock_effect_id"]:
        effects.apply_effect(
            character_id, k["unlock_effect_id"], source=f"knowledge:{knowledge_id}", duration=999999
        )
    db.log_action(character_id, "knowledge_understand", k["name_en"])
    return {"knowledge": k, "risk_triggered": risk_triggered, "incident": incident}
