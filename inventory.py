"""
Inventory / Item / Equipment engine (mục 22, 59).

Nguyên tắc: Equipment KHÔNG tính riêng một hệ số nào — khi equip, nó áp một
Effect vào EffectEngine (effects.py) với source="equip:<slot>" và thời hạn
gần như vô hạn. Mọi công thức damage/risk vẫn chỉ đọc qua
effects.get_modifier_sum() như buff/debuff bình thường — không có đường
tính riêng cho "đồ trang bị" (đúng nguyên tắc mục 16: dùng chung một Effect
Engine cho mọi hệ thống).
"""
import database as db
import effects

EQUIP_EFFECTIVELY_PERMANENT_DURATION = 999_999


class InventoryError(Exception):
    """Lỗi nghiệp vụ (không đủ số lượng, item không đúng loại...)."""


def list_inventory(character_id: int):
    return db.list_inventory(character_id)


def use_item(character: dict, item_id: str):
    """Dùng Consumable — hồi HP/Spirituality thật, trừ đúng 1 item khỏi túi."""
    item = db.get_item(item_id)
    if item is None or item["type"] != "consumable":
        raise InventoryError("Vật phẩm này không thể sử dụng trực tiếp.")

    if not db.remove_inventory_item(character["character_id"], item_id, 1):
        raise InventoryError("Bạn không còn vật phẩm này trong túi.")

    new_hp = min(character["hp_max"], character["hp"] + item["heal_hp"])
    new_spirituality = min(
        character["spirituality_max"], character["spirituality"] + item["heal_spirituality"]
    )
    db.set_character_hp_spirituality(character["character_id"], new_hp, new_spirituality)
    db.log_action(character["character_id"], "use_item", item["name_en"])
    return item, new_hp, new_spirituality


def equip_item(character: dict, item_id: str):
    """Trang bị Equipment — áp Effect thật qua EffectEngine, không giữ
    một hệ số riêng ngoài luồng buff/debuff."""
    item = db.get_item(item_id)
    if item is None or item["type"] != "equipment":
        raise InventoryError("Vật phẩm này không phải Trang bị.")
    if db.get_inventory_quantity(character["character_id"], item_id) <= 0:
        raise InventoryError("Bạn không sở hữu vật phẩm này.")

    slot = item["equip_slot"]
    character_id = character["character_id"]
    current = db.get_equipment(character_id)

    if current.get(slot) == item_id:
        raise InventoryError("Vật phẩm này đã được trang bị.")

    if slot in current:
        # Gỡ trang bị cũ trước — xóa đúng effect nguồn "equip:<slot>", không đụng buff khác
        db.remove_character_effects_by_source(character_id, f"equip:{slot}")

    db.set_equipment(character_id, slot, item_id)
    effects.apply_effect(
        character_id,
        _effect_id_for_item(item),
        source=f"equip:{slot}",
        duration=EQUIP_EFFECTIVELY_PERMANENT_DURATION,
    )
    db.log_action(character_id, "equip_item", item["name_en"])
    return item


def unequip_item(character: dict, slot: str):
    character_id = character["character_id"]
    current = db.get_equipment(character_id)
    if slot not in current:
        raise InventoryError("Không có gì đang trang bị ở vị trí này.")

    db.remove_character_effects_by_source(character_id, f"equip:{slot}")
    db.clear_equipment_slot(character_id, slot)
    db.log_action(character_id, "unequip_item", slot)


def get_equipped_items(character: dict):
    """Trả về dict slot -> item dict đầy đủ (thay vì chỉ item_id)."""
    equipment = db.get_equipment(character["character_id"])
    return {slot: db.get_item(item_id) for slot, item_id in equipment.items()}


def _effect_id_for_item(item: dict) -> str:
    """Equipment dùng effect_id riêng theo item, đăng ký động vào
    effect_definitions nếu chưa có — vẫn là dữ liệu tĩnh (đọc từ items_seed),
    không phải AI runtime tự nghĩ ra modifier."""
    effect_id = f"equip_{item['item_id']}"
    if db.get_effect_definition(effect_id) is None:
        _register_equipment_effect(effect_id, item)
    return effect_id


def _register_equipment_effect(effect_id: str, item: dict):
    with db.get_conn() as conn:
        conn.execute(
            """INSERT OR IGNORE INTO effect_definitions
               (effect_id, name_en, type, description, default_duration, modifier_key, modifier_value)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (
                effect_id,
                item["name_en"],
                "buff",  # Equipment trong bản demo luôn có lợi; nếu sau này có Cursed Item gây hại thật, tách riêng cột is_beneficial thay vì suy từ dấu modifier_value
                item["description"],
                EQUIP_EFFECTIVELY_PERMANENT_DURATION,
                item["modifier_key"],
                item["modifier_value"],
            ),
        )
