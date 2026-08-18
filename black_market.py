"""
Black Market Engine (mục 41 trong spec).

Giao dịch vẫn phải atomic đúng nguyên tắc Trade (mục 38: Check -> Remove ->
Add -> Log -> Commit), nhưng khác Market/Auction thường ở chỗ kết quả "Add"
không chắc chắn — phải roll rủi ro TRƯỚC khi quyết định người chơi nhận được
gì. Toàn bộ hệ quả (mất tiền, dính bẫy, bị treo thưởng) đều là state THẬT ghi
vào DB — không có nhánh nào chỉ hiển thị text suông.
"""
import random

import database as db
import effects
import loss_of_control
import i18n


class BlackMarketError(Exception):
    """Lỗi nghiệp vụ hiển thị thẳng cho người chơi."""


def browse_catalog():
    return db.list_black_market_catalog()


def get_listing(listing_id: str, lang: str = None):
    listing = db.get_black_market_listing(listing_id)
    if listing is None:
        raise BlackMarketError(i18n.t("black_market.error_listing_gone", lang))
    return listing


def history(character_id: int):
    return db.list_black_market_history(character_id)


def buy(character_id: int, listing_id: str, lang: str = None) -> dict:
    """Atomic: CHECK+REMOVE tiền trước (charge_black_market_price), rồi mới
    roll rủi ro để quyết định ADD gì. Trả về dict {outcome, listing, detail}
    để UI hiển thị đúng những gì thực sự vừa xảy ra.

    `lang` (mục 60-61): outcome text giờ đọc từ locales/*.json thay vì
    hardcode tiếng Việt — nếu không truyền, i18n.t() tự fallback về vi."""
    listing = get_listing(listing_id, lang)

    charged = db.charge_black_market_price(character_id, listing["price"])
    if not charged:
        raise BlackMarketError(i18n.t("black_market.error_not_enough_money", lang))

    roll = random.randint(1, 100) if listing["risk_type"] != "none" else 101
    triggered = roll <= listing["risk_chance"]

    if listing["risk_type"] == "none" or not triggered:
        outcome = "success"
        if listing["item_id"]:
            db.add_inventory_item(character_id, listing["item_id"], listing["quantity"])
        detail = i18n.t("black_market.outcome_success_detail", lang)

    elif listing["risk_type"] == "scam":
        outcome = "scam"
        detail = i18n.t("black_market.outcome_scam_detail", lang)

    elif listing["risk_type"] == "trap":
        outcome = "trap"
        character = db.get_character_by_id(character_id)
        new_hp = max(1, round(character["hp"] * 0.85))
        db.set_character_hp_spirituality(character_id, new_hp, character["spirituality"])
        effects.apply_effect(character_id, "black_market_trap", source="black_market")
        loss_of_control.compute_risk(character_id)
        detail = i18n.t("black_market.outcome_trap_detail", lang)

    elif listing["risk_type"] == "wanted":
        outcome = "wanted"
        item_label = listing.get("description_vi", "")[:40]
        bounty_id = db.create_bounty(
            None, character_id,
            i18n.t("black_market.bounty_reason", lang, item=item_label),
            reward_money=round(listing["price"] * 1.5),
        )
        detail = i18n.t("black_market.outcome_wanted_detail", lang, bounty_id=bounty_id)

    else:
        outcome = "success"
        detail = i18n.t("black_market.outcome_success_detail", lang)

    db.log_black_market_purchase(character_id, listing_id, outcome, listing["price"])
    return {"outcome": outcome, "listing": listing, "detail": detail}
