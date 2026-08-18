"""
Sealed Artifact Engine (mục 22 trong spec).

Artifact không chỉ là "ATK +500": mỗi Artifact có Effect/Rule/Side Effect
riêng, đi qua EffectEngine thật (effects.py) khi Experiment — không có buff
nào chỉ hiện trên Embed mà không đổi số liệu (mục 15, 51).

Gameplay: Unknown -> Inspect -> Experiment -> Discover Rule (mục 22).
- inspect(): miễn phí, không giới hạn số lần gọi, mỗi lần tiết lộ đúng 1
  stage kế tiếp theo thứ tự cố định effect -> rule -> side_effect.
- experiment(): tốn 1 lượt sử dụng (usage_limit), áp Effect thật, có %
  Risk kích hoạt Side Effect, và tự động mở khóa toàn bộ 3 stage cùng lúc
  (trải nghiệm trực tiếp dạy cho người chơi biết Artifact hoạt động ra sao).
"""
import random

import database as db
import effects
import house as house_engine

STAGE_ORDER = ["effect", "rule", "side_effect"]


class ArtifactError(Exception):
    """Lỗi nghiệp vụ (không sở hữu, hết lượt sử dụng...) — hiển thị thẳng
    cho người chơi, không phải bug."""


def list_owned(character_id: int):
    return db.list_character_artifacts(character_id)


def get_rules_text(artifact_id: str) -> dict:
    return {r["stage"]: r["text_vi"] for r in db.get_artifact_rules(artifact_id)}


def _ensure_owned(character_id: int, character_artifact_id: int) -> dict:
    ca = db.get_character_artifact(character_artifact_id)
    if ca is None or ca["character_id"] != character_id:
        raise ArtifactError("Bạn không sở hữu Vật phẩm thần kỳ này.")
    return ca


def inspect(character_id: int, character_artifact_id: int) -> dict:
    """Quan sát Artifact — miễn phí, luôn mở khóa đúng 1 stage kế tiếp.
    Trả về {"stage": str|None, "text": str|None} — stage=None nghĩa là đã
    biết hết cả 3 stage rồi, không còn gì để Inspect thêm."""
    ca = _ensure_owned(character_id, character_artifact_id)

    known = {s for s in ca["discovered_stages"].split(",") if s}
    next_stage = next((s for s in STAGE_ORDER if s not in known), None)
    if next_stage is None:
        return {"stage": None, "text": None}

    known.add(next_stage)
    db.update_artifact_discovery(character_artifact_id, ",".join(known))
    rules = get_rules_text(ca["artifact_id"])
    db.log_artifact_history(character_id, ca["artifact_id"], "inspect", side_effect_triggered=False)
    return {"stage": next_stage, "text": rules.get(next_stage, "")}


def experiment(character_id: int, character_artifact_id: int) -> dict:
    """Kích hoạt thật Artifact (mục 22: Experiment). Áp Effect chính qua
    EffectEngine luôn luôn; roll risk_stars*10% để Side Effect có kích hoạt
    hay không. Trải nghiệm này tự mở khóa toàn bộ 3 stage."""
    ca = _ensure_owned(character_id, character_artifact_id)
    if ca["uses_remaining"] == 0:
        raise ArtifactError("Vật phẩm thần kỳ này đã hết lượt sử dụng.")

    artifact = db.get_artifact(ca["artifact_id"])
    if not db.consume_artifact_use(character_artifact_id):
        raise ArtifactError("Không thể sử dụng Vật phẩm thần kỳ lúc này.")

    effects.apply_effect(character_id, artifact["effect_id"], source=f"artifact:{artifact['artifact_id']}")

    # 🗝️ Phòng Cổ vật (mục 42 mở rộng — house.py) giảm % kích hoạt Side
    # Effect thật. Kẹp tối thiểu 5% để Experiment không bao giờ hoàn toàn an
    # toàn (đúng tinh thần mục 22: rủi ro luôn tồn tại khi thao túng Artifact).
    effective_side_chance = max(
        5, artifact["side_effect_chance"] - house_engine.artifact_side_effect_reduction(character_id)
    )

    side_triggered = False
    if artifact["side_effect_id"] and random.randint(1, 100) <= effective_side_chance:
        effects.apply_effect(character_id, artifact["side_effect_id"], source=f"artifact:{artifact['artifact_id']}")
        side_triggered = True

    db.update_artifact_discovery(character_artifact_id, ",".join(STAGE_ORDER))
    db.log_artifact_history(character_id, artifact["artifact_id"], "experiment", side_triggered)
    db.log_action(character_id, "artifact_experiment", artifact["name_en"])

    updated = db.get_character_artifact(character_artifact_id)
    return {"artifact": artifact, "side_effect_triggered": side_triggered, "artifact_state": updated}
