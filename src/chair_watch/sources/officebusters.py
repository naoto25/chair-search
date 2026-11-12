"""オフィスバスターズ。シリーズ別の一覧ページ（新しい順、1 ページ 60 件）を読む。

検索ページ（/kensaku/）は robots.txt で禁止されているので使わない。
一覧の 1 ページ目だけを読むため、古い出品が値下げされた場合は拾えないことがある。
"""

import re

import httpx
from selectolax.lexbor import LexborHTMLParser as HTMLParser

from chair_watch.models import Listing

SITE = "officebusters"
BASE = "https://www.officebusters.com"
SERIES_PATHS = [
    "/series/okamura/sylphy/",
    "/series/okamura/Sylphymesh/",
    "/series/itoki/act-chair/",
    "/series/itoki/act-chair-mesh/",
    "/series/itoki/act-chair-aluminium/",
    "/series/itoki/act-chair-mesh-aluminium/",
]


def parse_series_html(html: str) -> list[Listing]:
    tree = HTMLParser(html)
    listings = []
    for card in tree.css("li.result"):
        link = card.css_first('a[href*="/items/"]')
        img = card.css_first(".result_detail_card_photo img")
        ontax = card.css_first(".result_detail_card_ontax")
        if not (link and img and ontax):
            continue
        item_id = link.attributes["href"].rstrip("/").rsplit("/", 1)[-1]
        listings.append(
            Listing(
                site=SITE,
                item_id=item_id,
                title=" ".join((img.attributes.get("alt") or "").split()),
                price_yen=int(re.sub(r"[^\d]", "", ontax.text())),
                url=f"{BASE}/items/{item_id}",
                image_url=img.attributes.get("data-src") or img.attributes.get("src"),
            )
        )
    return listings


def fetch(client: httpx.Client) -> list[Listing]:
    results: dict[str, Listing] = {}
    for path in SERIES_PATHS:
        response = client.get(BASE + path)
        response.raise_for_status()
        for listing in parse_series_html(response.text):
            results[listing.item_id] = listing
    return list(results.values())
