"""
Auction Engine (mục 41 trong spec) — KHÁC Market (economy.py: giá cố định,
mua trọn ngay). Auction có bidding thật: escrow tiền ngay khi ra giá, hoàn
tiền người giữ giá cao nhất trước đó, và tự chốt phiên khi hết hạn (lazy
settle — không cần thêm scheduler/cron riêng, đúng tinh thần World Event
mục 47 hiện có).
"""
import database as db

MIN_DURATION_HOURS = 1
MAX_DURATION_HOURS = 72

_ERROR_MESSAGES = {
    "not_found": "Phiên đấu giá này không còn tồn tại hoặc đã kết thúc.",
    "own_auction": "Bạn không thể ra giá cho chính phiên đấu giá của mình.",
    "bid_too_low": "Giá ra phải cao hơn giá hiện tại (tối thiểu +5%).",
    "not_enough_money": "Bạn không đủ Bảng cho mức giá này.",
}


class AuctionError(Exception):
    """Lỗi nghiệp vụ — hiển thị thẳng cho người chơi, không phải bug hệ thống."""


def list_active(limit: int = 15):
    return db.list_active_auctions(limit)


def get_auction(auction_id: int):
    return db.get_auction(auction_id)


def create_auction(seller_character_id: int, item_id: str, quantity: int,
                    starting_price: int, duration_hours: int):
    if quantity <= 0 or starting_price <= 0:
        raise AuctionError("Số lượng và giá khởi điểm phải lớn hơn 0.")
    if not (MIN_DURATION_HOURS <= duration_hours <= MAX_DURATION_HOURS):
        raise AuctionError(f"Thời hạn phiên đấu giá phải từ {MIN_DURATION_HOURS} đến {MAX_DURATION_HOURS} giờ.")
    auction_id = db.create_auction_transaction(
        seller_character_id, item_id, quantity, starting_price, duration_hours
    )
    if auction_id is None:
        raise AuctionError("Bạn không có đủ số lượng vật phẩm này trong túi.")
    return auction_id


def place_bid(character_id: int, auction_id: int, amount: int):
    if amount <= 0:
        raise AuctionError("Giá ra phải lớn hơn 0.")
    reason = db.place_bid_transaction(auction_id, character_id, amount)
    if reason:
        raise AuctionError(_ERROR_MESSAGES.get(reason, "Ra giá thất bại."))


def cancel_auction(seller_character_id: int, auction_id: int):
    if not db.cancel_auction_transaction(seller_character_id, auction_id):
        raise AuctionError(
            "Không thể huỷ phiên này — đã có người ra giá, hoặc phiên không thuộc về bạn."
        )
