"""
Economy / Trade Engine (mục 37-38 trong spec).

Mọi giao dịch đi qua database.py dưới dạng MỘT transaction atomic thật:
CHECK -> REMOVE -> ADD -> Log -> COMMIT trong cùng một connection SQLite
(sqlite3 tự rollback toàn bộ nếu có exception giữa chừng — không có
trường hợp A mất item mà B không nhận, hoặc ngược lại).
"""
import database as db
import achievements


class EconomyError(Exception):
    """Lỗi nghiệp vụ hiển thị thẳng cho người chơi."""


# ---------- Market (Chợ) ----------

def list_market(limit: int = 20):
    return db.list_market_listings(limit)


def sell_on_market(character_id: int, item_id: str, quantity: int, price_per_unit: int) -> int:
    if quantity <= 0 or price_per_unit <= 0:
        raise EconomyError("Số lượng và giá phải lớn hơn 0.")
    listing_id = db.create_market_listing(character_id, item_id, quantity, price_per_unit)
    if listing_id is None:
        raise EconomyError("Bạn không có đủ số lượng vật phẩm này trong túi.")
    return listing_id


def cancel_listing(character_id: int, listing_id: int):
    ok = db.cancel_market_listing(listing_id, character_id)
    if not ok:
        raise EconomyError("Không tìm thấy tin rao bán này, hoặc nó không thuộc về bạn.")


def buy_from_market(character_id: int, listing_id: int):
    listing = db.get_market_listing(listing_id)
    if listing is None:
        raise EconomyError("Tin rao bán này không còn tồn tại.")
    if listing["seller_character_id"] == character_id:
        raise EconomyError("Bạn không thể mua chính món hàng mình rao bán.")
    ok = db.buy_market_listing_transaction(listing_id, character_id)
    if not ok:
        raise EconomyError("Bạn không đủ Bảng cho giao dịch này.")
    achievements.unlock(character_id, "first_trade")
    achievements.unlock(listing["seller_character_id"], "first_trade")
    return listing


# ---------- Direct Trade (Trade 1-đổi-1 giữa hai người chơi) ----------

def direct_trade(from_character_id: int, to_character_id: int, item_id: str, quantity: int, price: int):
    if from_character_id == to_character_id:
        raise EconomyError("Không thể giao dịch với chính mình.")
    if quantity <= 0 or price < 0:
        raise EconomyError("Số lượng phải lớn hơn 0 và giá không được âm.")
    ok = db.direct_trade_item_for_money_transaction(from_character_id, to_character_id, item_id, quantity, price)
    if not ok:
        raise EconomyError("Giao dịch thất bại — bên bán không đủ hàng hoặc bên mua không đủ Bảng.")
    achievements.unlock(from_character_id, "first_trade")
    achievements.unlock(to_character_id, "first_trade")


def trade_history(character_id: int):
    return db.list_trade_history(character_id)


# ---------- Contract (mục 39) ----------

def post_contract(character_id: int, task_vi: str, reward_money: int):
    if reward_money <= 0:
        raise EconomyError("Phần thưởng Contract phải lớn hơn 0.")
    contract_id = db.create_contract(character_id, task_vi, reward_money)
    if contract_id is None:
        raise EconomyError("Bạn không đủ Bảng để ký quỹ phần thưởng Contract này.")
    return contract_id


def list_open_contracts():
    return db.list_open_contracts()


def my_contracts(character_id: int):
    return db.list_character_contracts(character_id)


def accept_contract(character_id: int, contract_id: int):
    ok = db.accept_contract(contract_id, character_id)
    if not ok:
        raise EconomyError("Contract này không còn khả dụng, hoặc là Contract của chính bạn.")


def complete_contract(character_id: int, contract_id: int):
    ok = db.complete_contract_transaction(contract_id, character_id)
    if not ok:
        raise EconomyError("Không thể xác nhận hoàn thành — chỉ người đăng Contract mới xác nhận được.")


def cancel_contract(character_id: int, contract_id: int):
    ok = db.cancel_contract_transaction(contract_id, character_id)
    if not ok:
        raise EconomyError("Không thể huỷ Contract này (đã có người nhận, hoặc không thuộc về bạn).")


# ---------- Bounty (mục 40) ----------

def post_bounty(issuer_character_id, target_character_id: int, crime_vi: str, reward_money: int):
    if reward_money <= 0:
        raise EconomyError("Phần thưởng Truy nã phải lớn hơn 0.")
    bounty_id = db.create_bounty(issuer_character_id, target_character_id, crime_vi, reward_money)
    if bounty_id is None:
        raise EconomyError("Bạn không đủ Bảng để treo thưởng Truy nã này.")
    return bounty_id


def list_active_bounties():
    return db.list_active_bounties()


def claim_bounty(claimer_character_id: int, bounty_id: int):
    ok = db.claim_bounty_transaction(bounty_id, claimer_character_id)
    if not ok:
        raise EconomyError("Không thể nhận thưởng Truy nã này.")
    db.increment_season_stat(claimer_character_id, "bounty_claims")
