"""
Beyonder Characteristic Engine (mục 21 trong spec).

Characteristic KHÔNG phải item RPG bình thường: nó gắn chết với đúng một
(pathway_id, sequence_number) mà Character đã đạt qua Advancement thật
(progression.perform_advancement thành công), không phải thứ AI runtime
hay UI tự tạo ra. File này là nơi DUY NHẤT được phép gọi
db.add_character_characteristic() — không gọi trực tiếp từ cogs/menu.py.

Trạng thái hiện tại (đọc trước khi mở rộng):
- Acquisition: xong — gắn vào Advancement Engine (progression.py).
- Ownership / Storage: xong — character_characteristics là nguồn sự thật.
- Consumption: xong ở mức cơ bản — tiêu thụ 1 Characteristic 'stored' để cộng
  Spirituality tối đa vĩnh viễn (đúng "phải thực sự ảnh hưởng Engine" mục 15).
- Transfer (cho Character khác): CHƯA làm — cần Trade Engine (mục 38) trước
  để atomic đúng cách, nên chưa cắm tạm một bản không atomic vào đây.
"""
import database as db


class CharacteristicError(Exception):
    """Lỗi nghiệp vụ (không sở hữu, đã tiêu thụ rồi...) — hiển thị thẳng cho
    người chơi, không phải bug."""


def grant_from_advancement(character_id: int, pathway_id: str, sequence_number: int) -> dict | None:
    """Gọi DUY NHẤT từ progression.perform_advancement() khi Nghi thức thành
    công. Tên Characteristic suy ra từ tên Sequence vừa đạt (cùng quy ước với
    Potion: f"{seq_name} Potion" ở database.init_db) để không cần một bảng
    định nghĩa tĩnh riêng cho một dữ liệu vốn đã có sẵn ở bảng sequences.

    Trả về dict Characteristic vừa tạo, hoặc None nếu Character đã sở hữu
    Characteristic của đúng Sequence này từ trước (idempotent — không nhân
    đôi nếu Advancement Engine lỡ gọi lại, xem mục 21: "không bị duplicate").
    """
    seq = db.get_sequence(pathway_id, sequence_number)
    seq_name = seq["name_en"] if seq else f"Sequence {sequence_number}"
    seq_name_vi = seq["name_vi"] if seq else f"Sequence {sequence_number}"
    name_en = f"{seq_name} Characteristic"
    name_vi = f"Đặc Tính {seq_name_vi}"

    created = db.add_character_characteristic(
        character_id, pathway_id, sequence_number, name_en,
        source="advancement", stability=100, name_vi=name_vi,
    )
    if not created:
        return None

    db.log_action(character_id, "characteristic_acquired", name_en)
    rows = db.list_character_characteristics(character_id)
    return next(
        r for r in rows if r["pathway_id"] == pathway_id and r["sequence_number"] == sequence_number
    )


def list_owned(character_id: int):
    return db.list_character_characteristics(character_id)


def consume(character_id: int, characteristic_id: int):
    """Tiêu thụ 1 Characteristic đang giữ để cộng vĩnh viễn Spirituality tối đa
    (+5) — hiệu lực thật trên Character, không chỉ đổi state trong DB (mục 15:
    "nếu buff/hiệu ứng tồn tại thì phải thực sự ảnh hưởng Game Engine").
    Không thể tiêu thụ Characteristic đã 'consumed' hoặc không thuộc sở hữu.
    """
    characteristic = db.get_character_characteristic(characteristic_id)
    if characteristic is None or characteristic["character_id"] != character_id:
        raise CharacteristicError("Bạn không sở hữu Characteristic này.")
    if characteristic["state"] != "stored":
        raise CharacteristicError("Characteristic này đã được tiêu thụ trước đó.")

    ok = db.consume_character_characteristic(characteristic_id, character_id)
    if not ok:
        raise CharacteristicError("Không thể tiêu thụ Characteristic này (đã bị thay đổi trạng thái).")

    character = db.get_character_by_id(character_id)
    new_max = character["spirituality_max"] + 5
    new_current = min(character["spirituality"] + 5, new_max)
    db.set_character_spirituality_max(character_id, new_max, new_current)
    db.log_action(character_id, "characteristic_consumed", characteristic["name_en"])
    return {"characteristic": characteristic, "spirituality_max": new_max}
