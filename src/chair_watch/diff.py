"""前回の記録（state）と今回の取得結果を比べて、通知する出品を決める。通信はしない。

state の形:
    {"sites": {"<site>": {"items": {"<item_id>": <価格>}, "failures": <連続失敗回数>,
                          "initialized": false  # 一度も取得に成功していないときだけ入る
    }}}
"""

import copy
from dataclasses import dataclass, field
from typing import Literal

from chair_watch.filters import PRICE_LIMIT_YEN
from chair_watch.models import Listing

FAILURE_ALERT_THRESHOLD = 3


@dataclass(frozen=True)
class SiteFetch:
    """1 サイト分の取得結果。"""

    # 解析できた検索結果の件数（判定で絞り込む前）。0 は解析失敗の疑いとして扱う
    raw_count: int
    # 判定（filters.is_target）を通った出品
    listings: list[Listing]


@dataclass(frozen=True)
class Notification:
    kind: Literal["new", "price_drop"]
    listing: Listing
    old_price: int | None = None


@dataclass
class DiffResult:
    notifications: list[Notification] = field(default_factory=list)
    # このサイトの取得が続けて失敗しているので知らせるべきサイト名
    failure_alerts: list[str] = field(default_factory=list)
    state: dict = field(default_factory=dict)


def compute(state: dict, fetches: dict[str, SiteFetch | None]) -> DiffResult:
    """fetches の値が None のサイトは取得に失敗したものとして扱う。"""
    new_state = copy.deepcopy(state)
    sites = new_state.setdefault("sites", {})
    result = DiffResult(state=new_state)

    for site, fetch in fetches.items():
        prev = sites.get(site)
        prev_items: dict[str, int] = prev["items"] if prev else {}

        failed = fetch is None or (fetch.raw_count == 0 and len(prev_items) > 0)
        if failed:
            entry = prev if prev else {"items": {}, "failures": 0, "initialized": False}
            entry["failures"] += 1
            if entry["failures"] == FAILURE_ALERT_THRESHOLD:
                result.failure_alerts.append(site)
            sites[site] = entry
            continue

        first_run = prev is None or prev.get("initialized") is False
        if not first_run:
            for listing in fetch.listings:
                n = _notification(listing, prev_items.get(listing.item_id))
                if n:
                    result.notifications.append(n)

        sites[site] = {
            "items": {listing.item_id: listing.price_yen for listing in fetch.listings},
            "failures": 0,
        }

    return result


def _notification(listing: Listing, old_price: int | None) -> Notification | None:
    if listing.price_yen > PRICE_LIMIT_YEN:
        return None
    if old_price is None:
        return Notification("new", listing)
    if listing.price_yen < old_price:
        return Notification("price_drop", listing, old_price)
    return None
