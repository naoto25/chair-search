"""ビックリユース。検索画面が裏で呼んでいる検索 API（JSON）を読む。"""

from datetime import datetime, timedelta, timezone
from urllib.parse import quote

import httpx

from chair_watch.models import Listing

SITE = "bicreyouth"
KEYWORDS = ["シルフィ", "アクト"]
_JST = timezone(timedelta(hours=9))


def search_url(keyword: str) -> str:
    return f"https://kanri.bic-reyouth.com/api/shop/product/search?keyword={quote(keyword)}&limit=50"


def parse_search_response(body: dict, now: datetime | None = None) -> list[Listing]:
    now_str = (now or datetime.now(_JST)).strftime("%Y%m%d%H%M")
    listings = []
    for p in body.get("data", []):
        # 在庫 0 は「SOLD OUT」として表示されている
        if p.get("display") != "Y" or int(p.get("quantity") or 0) <= 0:
            continue
        code = p["system_code"]
        listings.append(
            Listing(
                site=SITE,
                item_id=code,
                title=p["product_name"].strip(),
                price_yen=_price(p, now_str),
                url=f"https://bic-reyouth.shop/view/item/{code}",
                image_url=p.get("max_image_url"),
                description=p.get("product_group_name"),
            )
        )
    return listings


def _price(p: dict, now_str: str) -> int:
    """税込価格。割引期間中なら割引率を反映する（画面の表示と同じ計算）。"""
    price = int(p["sell_price"])
    rate = float(p.get("discount_rate") or 0)
    start, _, end = (p.get("discount_period") or "").partition("|")
    if rate > 0 and start <= now_str <= end:
        price = round(price * (100 - rate) / 100)
    return price


def fetch(client: httpx.Client) -> list[Listing]:
    results: dict[str, Listing] = {}
    for keyword in KEYWORDS:
        response = client.get(search_url(keyword))
        response.raise_for_status()
        for listing in parse_search_response(response.json()):
            results[listing.item_id] = listing
    return list(results.values())
