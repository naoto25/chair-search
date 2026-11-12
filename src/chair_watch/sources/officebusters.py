"""オフィスバスターズ。シリーズ別の一覧ページ（新しい順、1 ページ 60 件）を読む。

検索ページ（/kensaku/）は robots.txt で禁止されているので使わない。
一覧の 1 ページ目だけを読むため、古い出品が値下げされた場合は拾えないことがある。

一覧の商品名は「肘付ハイバックチェア」のように可動か固定かが分からないので、
3 万円以下の肘付きだけ詳細ページを読み、キャッチコピー・タグ・商品説明を判定に加える。
"""

import re
from dataclasses import replace

import httpx
from selectolax.lexbor import LexborHTMLParser as HTMLParser

from chair_watch.detail_cache import DetailCache
from chair_watch.filters import PRICE_LIMIT_YEN, is_target
from chair_watch.models import Listing

# 詳細ページのうち、その商品自身について書かれた欄（下にある「おすすめ商品」の欄は含めない）
_DETAIL_SELECTORS = [
    ".m-goodsDetailExplain_head__text span",  # 見出しの下のキャッチコピー
    ".m-goodsTopics a",  # タグ（「固定肘」タグなど）
    ".m-goodsDescription_wrap",  # 商品説明
]

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


def parse_detail_text(html: str) -> str:
    tree = HTMLParser(html)
    parts = [node.text(separator=" ", strip=True) for sel in _DETAIL_SELECTORS for node in tree.css(sel)]
    return " ".join(p for p in parts if p)


def fetch(client: httpx.Client, cache: DetailCache) -> list[Listing]:
    results: dict[str, Listing] = {}
    for path in SERIES_PATHS:
        response = client.get(BASE + path)
        response.raise_for_status()
        for listing in parse_series_html(response.text):
            results[listing.item_id] = listing

    cache.prune(SITE, keep=set(results))
    for item_id, listing in results.items():
        if listing.price_yen <= PRICE_LIMIT_YEN and is_target(listing):
            detail = cache.get_or_fetch(SITE, item_id, lambda url=listing.url: _get_detail_text(client, url))
            results[item_id] = replace(listing, description=detail)
    return list(results.values())


def _get_detail_text(client: httpx.Client, url: str) -> str:
    response = client.get(url)
    response.raise_for_status()
    return parse_detail_text(response.text)
