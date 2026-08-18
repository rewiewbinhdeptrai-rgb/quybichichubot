"""
World Engine — City + Location (mục 31-32 trong spec).

Thay thế `characters.location` dạng String tự do ("Backlund") bằng entity
thật: mỗi Character luôn đứng ở đúng 1 Location, Location thuộc đúng 1 City
(mục 31: "Backlund" chưa phải một entity World thực sự — nay đã là).

Di chuyển trong cùng City: miễn phí.
Di chuyển sang City khác: tốn `travel_cost` (Bảng) của City đích, trừ tiền
thật qua db.set_character_location() (transaction atomic, mục 38/50) — không
có "dịch chuyển tức thời miễn phí toàn bản đồ".
"""
import database as db
import world_event
import quest


class WorldError(Exception):
    """Lỗi nghiệp vụ (không đủ tiền, Location không tồn tại...) — hiển thị
    thẳng cho người chơi, không phải bug."""


def list_cities():
    return db.list_cities()


def get_city(city_id: str):
    return db.get_city(city_id)


def list_locations(city_id: str = None):
    return db.list_locations(city_id)


def get_location(location_id: str):
    return db.get_location(location_id)


def get_current_location(character: dict):
    """Location hiện tại của Character, hoặc None nếu chưa từng được gán
    (không nên xảy ra sau migration, nhưng an toàn phòng hờ)."""
    if not character or not character.get("location_id"):
        return None
    return db.get_location(character["location_id"])


def travel_cost_to(character: dict, destination_location_id: str) -> int:
    """Phí di chuyển thật tới Location đích: 0 nếu cùng City hiện tại, ngược
    lại là travel_cost của City đích."""
    destination = db.get_location(destination_location_id)
    if destination is None:
        raise WorldError("Địa điểm này không tồn tại.")

    current_location = get_current_location(character)
    current_city_id = current_location["city_id"] if current_location else None
    if destination["city_id"] == current_city_id:
        return 0

    destination_city = db.get_city(destination["city_id"])
    return destination_city["travel_cost"]


def travel(character_id: int, destination_location_id: str) -> dict:
    """Di chuyển thật (mục 32). Trừ đúng phí (nếu khác City), cập nhật
    Location + log travel_log — atomic qua db.set_character_location()."""
    character = db.get_character_by_id(character_id)
    if character is None:
        raise WorldError("Không tìm thấy nhân vật.")

    destination = db.get_location(destination_location_id)
    if destination is None:
        raise WorldError("Địa điểm này không tồn tại.")

    current_location = get_current_location(character)
    if current_location and current_location["location_id"] == destination_location_id:
        raise WorldError("Bạn đã ở đây rồi.")

    cost = travel_cost_to(character, destination_location_id)
    if character["money"] < cost:
        raise WorldError(f"Không đủ tiền để di chuyển tới thành phố này (cần {cost} Bảng).")

    ok = db.set_character_location(
        character_id,
        current_location["location_id"] if current_location else None,
        destination_location_id,
        cost,
    )
    if not ok:
        raise WorldError(f"Không đủ tiền để di chuyển tới thành phố này (cần {cost} Bảng).")

    db.log_action(character_id, "travel", destination["name_en"])
    # Hook Quest (mục 43): Objective "visit_location" tiến độ đúng lúc
    # Character thật sự đứng tại Location đó, không phải khai báo tay.
    quest.progress_objective(character_id, "visit_location", destination_location_id, 1)
    updated_character = db.get_character_by_id(character_id)
    triggered_event = world_event.maybe_trigger_on_travel(destination["city_id"])
    return {
        "location": destination,
        "cost": cost,
        "character": updated_character,
        "triggered_event": triggered_event,
    }
