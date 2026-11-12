"""オフィスレスキュー119Happy。検索結果の HTML を読む。検索語は Shift_JIS で URL に入れる。"""

import re
from dataclasses import replace
from urllib.parse import quote, urljoin

import httpx
from selectolax.lexbor import LexborHTMLParser as HTMLParser

from chair_watch.detail_cache import DetailCache
from chair_watch.filters import PRICE_LIMIT_YEN, is_chair_model
from chair_watch.models import Listing

SITE = "happy119"
KEYWORDS = ["シルフィー", "イトーキ アクト"]
BASE = "https://www.119happy.com"


def search_url(keyword: str) -> str:
    word = quote(keyword.encode("cp932"))
    return (
        f"{BASE}/ws/advancedsearch?srchWordTxt={word}"
        "&cmdtyFlagTxt=sr&dispModeTxt=2&actionNameTxt=list&pass=advancedsearch&pageSizeSel=80"
    )


def parse_search_html(html: str) -> list[Listing]:
    tree = HTMLParser(html)
    listings = []
    for box in tree.css("div.listBox"):
        item_id_node = box.css_first(".item_id")
        name_node = box.css_first("h3.itemName a")
        price_node = box.css_first(".finalPrice span")
        if not (item_id_node and name_node and price_node):
            continue
        item_id = item_id_node.text(strip=True)
        maker_node = box.css_first(".maker_name")
        maker = maker_node.text(strip=True) if maker_node else ""
        img = box.css_first(".itemPic img")
        listings.append(
            Listing(
                site=SITE,
                item_id=item_id,
                title=f"{maker} {name_node.text(strip=True)}".strip(),
                price_yen=int(re.sub(r"[^\d]", "", price_node.text())),
                url=urljoin(BASE, name_node.attributes["href"]),
                image_url=urljoin(BASE, img.attributes["src"]) if img and img.attributes.get("src") else None,
            )
        )
    return listings


def parse_arm_type(html: str) -> str | None:
    """商品詳細ページの「タイプ」欄（肘付 / 肘無 など）を返す。"""
    for row in HTMLParser(html).css("tr"):
        th, td = row.css_first("th"), row.css_first("td")
        if th and td and th.text(strip=True) == "タイプ":
            return td.text(strip=True)
    return None


def fetch(client: httpx.Client, cache: DetailCache) -> list[Listing]:
    results: dict[str, Listing] = {}
    for keyword in KEYWORDS:
        response = client.get(search_url(keyword))
        response.raise_for_status()
        for listing in parse_search_html(response.text):
            results[listing.item_id] = listing

    # 一覧の商品名には肘の有無が書かれていないので、通知対象になりうる出品だけ詳細ページで確かめる
    cache.prune(SITE, keep=set(results))
    for item_id, listing in results.items():
        if listing.price_yen <= PRICE_LIMIT_YEN and is_chair_model(listing):
            arm_type = cache.get_or_fetch(SITE, item_id, lambda url=listing.url: _get_arm_type(client, url))
            results[item_id] = replace(listing, description=arm_type)
    return list(results.values())


def _get_arm_type(client: httpx.Client, url: str) -> str | None:
    response = client.get(url)
    response.raise_for_status()
    return parse_arm_type(response.text)
