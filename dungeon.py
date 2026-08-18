"""
Dungeon Engine (mục 26 trong spec).

Procedural theo seed: Seed -> chuỗi Room (Combat / Treasure / Trap / Secret)
-> Boss luôn ở phòng cuối. Seed được lưu lại trong dungeon_runs nên cùng một
run luôn tái tạo được đúng chuỗi phòng đã đi qua (đúng mục 26: "Seed được
lưu để có thể truy xuất run").

QUAN TRỌNG: Không tạo Combat Engine riêng cho Dungeon. Phòng Combat/Boss đi
qua ĐÚNG combat.py hiện có (start_pve/perform_attack/...) — chỉ khác là
combat_sessions.dungeon_run_id được gắn để combat.py tự gọi ngược lại
on_combat_resolved() ở đây sau khi trận kết thúc, thay vì để mỗi hệ thống
tự có luồng combat riêng (đúng mục 16: dùng chung Engine, không phân mảnh).
"""
import random

import database as db
import combat
from data.dungeons_seed import ROOM_EVENTS


class DungeonError(Exception):
    """Lỗi nghiệp vụ hiển thị thẳng cho người chơi."""


def list_dungeons():
    return db.list_dungeons()


def get_dungeon(dungeon_id: str):
    return db.get_dungeon(dungeon_id)


def get_active_run(character_id: int):
    return db.get_active_dungeon_run(character_id)


def get_progress(character_id: int):
    run = db.get_active_dungeon_run(character_id)
    if run is None:
        return None
    run["events"] = db.list_dungeon_run_events(run["run_id"])
    run["dungeon"] = db.get_dungeon(run["dungeon_id"])
    return run


def _rng_for_room(run: dict, room_index: int) -> random.Random:
    """RNG tất định theo seed của run + room_index — cùng seed luôn cho
    đúng cùng kết quả tại đúng phòng đó (mục 26)."""
    return random.Random(f"{run['seed']}:{room_index}")


def _room_type_for(run: dict, room_index: int, rng: random.Random) -> str:
    if room_index >= run["total_rooms"] - 1:
        return "boss"
    return "combat" if rng.random() < 0.6 else "event"


def enter_dungeon(character: dict, dungeon_id: str):
    character_id = character["character_id"]
    if db.get_active_combat_session(character_id):
        raise DungeonError("Bạn đang có một trận đấu khác chưa kết thúc.")
    if db.get_active_dungeon_run(character_id):
        raise DungeonError("Bạn đang ở trong một Dungeon khác — hãy hoàn thành hoặc để nó kết thúc trước.")

    dungeon_row = db.get_dungeon(dungeon_id)
    if dungeon_row is None:
        raise DungeonError("Dungeon này không tồn tại.")
    if character["hp"] <= 0:
        raise DungeonError("HP hiện tại bằng 0 — cần hồi phục trước khi vào Dungeon.")

    seed = random.randint(1, 2_000_000_000)
    run_id = db.create_dungeon_run(character_id, dungeon_id, seed, dungeon_row["room_count"])
    db.log_action(character_id, "dungeon_enter", dungeon_row["name_en"])
    return enter_next_room(character, run_id)


def enter_next_room(character: dict, run_id: int):
    """Xử lý phòng hiện tại (current_room) của run — gọi khi mới vào Dungeon,
    ngay sau một phòng Event, hoặc ngay sau khi phòng Combat trước đó được
    thắng (qua continue_run)."""
    run = db.get_dungeon_run(run_id)
    if run is None or run["status"] != "active":
        raise DungeonError("Lượt khám phá Dungeon này không còn hoạt động.")
    dungeon_row = db.get_dungeon(run["dungeon_id"])
    room_index = run["current_room"]
    rng = _rng_for_room(run, room_index)
    room_type = _room_type_for(run, room_index, rng)

    if room_type in ("boss", "combat"):
        if room_type == "boss":
            monster_id = dungeon_row["boss_monster_id"]
        else:
            pool = dungeon_row["monster_pool"].split(",")
            monster_id = rng.choice(pool)
        session, monster = combat.start_pve(character, monster_id)
        db.link_combat_session_to_dungeon(session["session_id"], run_id)
        return {
            "kind": "combat",
            "room_type": room_type,
            "room_index": room_index,
            "total_rooms": run["total_rooms"],
            "session": session,
            "monster": monster,
        }

    return _resolve_event_room(character, run, room_index, rng)


def _resolve_event_room(character: dict, run: dict, room_index: int, rng: random.Random):
    total_weight = sum(w for _, _, w, *_ in ROOM_EVENTS)
    roll = rng.uniform(0, total_weight)
    upto = 0
    chosen = ROOM_EVENTS[-1]
    for event in ROOM_EVENTS:
        upto += event[2]
        if roll <= upto:
            chosen = event
            break
    event_type, name_vi, _weight, money_min, money_max, hp_min, hp_max = chosen
    money_delta = rng.randint(money_min, money_max)
    hp_delta = rng.randint(hp_min, hp_max)

    character_id = character["character_id"]
    new_hp = max(1, character["hp"] + hp_delta)
    with db.get_conn() as conn:
        conn.execute(
            "UPDATE characters SET money = MAX(0, money + ?), hp = ? WHERE character_id = ?",
            (money_delta, new_hp, character_id),
        )
    result_vi = f"{name_vi}: {'+' if money_delta >= 0 else ''}{money_delta} Bảng, {'+' if hp_delta >= 0 else ''}{hp_delta} HP"
    db.advance_dungeon_run(run["run_id"], event_type, result_vi)
    db.log_action(character_id, "dungeon_room_event", result_vi)

    updated_run = db.get_dungeon_run(run["run_id"])
    completed = updated_run is None or updated_run["current_room"] >= updated_run["total_rooms"]
    return {
        "kind": "event",
        "room_type": event_type,
        "room_index": room_index,
        "total_rooms": run["total_rooms"],
        "name_vi": name_vi,
        "money_delta": money_delta,
        "hp_delta": hp_delta,
        "completed": completed,
    }


def on_combat_resolved(character_id: int, run_id: int, combat_result: dict):
    """Gọi TỪ combat.py ngay sau khi một trận có dungeon_run_id kết thúc.

    victory ở phòng Boss  -> hoàn thành Dungeon, phát thưởng tổng (mục 26).
    victory ở phòng thường -> ghi log phòng, tiến current_room lên 1.
    defeat / fled          -> Dungeon run kết thúc thất bại ngay (không cho
                               "thử lại free" cùng seed để né phòng khó).
    """
    run = db.get_dungeon_run(run_id)
    if run is None or run["status"] != "active":
        return None
    dungeon_row = db.get_dungeon(run["dungeon_id"])
    room_index = run["current_room"]
    is_boss_room = room_index >= run["total_rooms"] - 1

    if combat_result["status"] == "victory":
        db.advance_dungeon_run(run_id, "boss" if is_boss_room else "combat", "Thắng trận")
        if is_boss_room:
            db.finish_dungeon_run(run_id, "completed")
            with db.get_conn() as conn:
                conn.execute(
                    "UPDATE characters SET money = money + ?, exp = exp + ? WHERE character_id = ?",
                    (dungeon_row["reward_money"], dungeon_row["reward_exp"], character_id),
                )
                if dungeon_row["reward_item_id"]:
                    conn.execute(
                        """INSERT INTO inventory (character_id, item_id, quantity) VALUES (?, ?, 1)
                           ON CONFLICT(character_id, item_id) DO UPDATE SET quantity = quantity + 1""",
                        (character_id, dungeon_row["reward_item_id"]),
                    )
            db.log_action(character_id, "dungeon_clear", dungeon_row["name_en"])
            db.increment_season_stat(character_id, "dungeon_clears")
            return {"dungeon_status": "cleared", "dungeon": dungeon_row}
        return {"dungeon_status": "room_cleared", "run_id": run_id}

    db.finish_dungeon_run(run_id, "failed" if combat_result["status"] == "defeat" else "abandoned")
    db.log_action(character_id, "dungeon_fail", dungeon_row["name_en"])
    return {"dungeon_status": "failed"}


def continue_run(character: dict):
    """UI gọi sau một phòng Event, hoặc sau khi phòng Combat vừa được thắng
    (dungeon_status == room_cleared) — tiến vào phòng kế tiếp."""
    run = db.get_active_dungeon_run(character["character_id"])
    if run is None:
        raise DungeonError("Bạn hiện không ở trong Dungeon nào.")
    return enter_next_room(character, run["run_id"])
