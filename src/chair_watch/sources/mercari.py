"""メルカリ。検索画面を Playwright で開き、画面が裏で呼ぶ検索 API の応答（JSON）を読む。

API を直接呼ばないのは、リクエストごとに署名（DPoP）が必要で、robots.txt でも /v2/ が禁止されているため。
検索画面（/search）の表示は robots.txt で許可されている。
"""

from urllib.parse import urlencode

from chair_watch.filters import PRICE_LIMIT_YEN
from chair_watch.models import Listing

SITE = "mercari"
KEYWORDS = ["オカムラ シルフィー", "イトーキ アクト"]
_SEARCH_API = "entities:search"


def search_url(keyword: str) -> str:
    # 3 万円以下に絞る。3 万円を超えていた出品が値下げで入ってきた場合は「新着」として通知される
    query = {
        "keyword": keyword,
        "status": "on_sale",
        "price_max": PRICE_LIMIT_YEN,
        "sort": "created_time",
        "order": "desc",
    }
    return "https://jp.mercari.com/search?" + urlencode(query)


def parse_search_response(body: dict) -> list[Listing]:
    listings = []
    for item in body.get("items", []):
        item_id = item["id"]
        if item.get("itemType") == "ITEM_TYPE_BEYOND":
            url = f"https://jp.mercari.com/shops/product/{item_id}"
        else:
            url = f"https://jp.mercari.com/item/{item_id}"
        thumbnails = item.get("thumbnails") or []
        brand = (item.get("itemBrand") or {}).get("name")
        listings.append(
            Listing(
                site=SITE,
                item_id=item_id,
                title=item["name"],
                price_yen=int(item["price"]),
                url=url,
                image_url=thumbnails[0] if thumbnails else None,
                description=brand,
            )
        )
    return listings


def fetch(browser) -> list[Listing]:
    """browser は playwright の Browser。キーワードごとに検索画面を開き、出品をまとめて返す。"""
    results: dict[str, Listing] = {}
    for keyword in KEYWORDS:
        page = browser.new_page(locale="ja-JP")
        try:
            with page.expect_response(lambda r: _SEARCH_API in r.url and r.status == 200, timeout=60_000) as info:
                page.goto(search_url(keyword), wait_until="domcontentloaded", timeout=60_000)
            for listing in parse_search_response(info.value.json()):
                results[listing.item_id] = listing
        finally:
            page.close()
    return list(results.values())
