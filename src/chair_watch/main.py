"""取得 → 判定 → 差分 → 通知 → 記録の保存 を 1 回分実行する。

環境変数 LINE_CHANNEL_ACCESS_TOKEN と LINE_USER_ID がなければ、送らずに内容を表示するだけにして、
state.json も更新しない（GitHub Actions 上では失敗として終わる）。
"""

import json
import logging
import os
import sys
import traceback
from collections.abc import Callable
from pathlib import Path

from chair_watch import notify_line
from chair_watch.detail_cache import DetailCache
from chair_watch.diff import Notification, SiteFetch, compute
from chair_watch.filters import is_target
from chair_watch.models import Listing
from chair_watch.sources import http_sources, mercari

log = logging.getLogger("chair_watch")
STATE_PATH = Path("state.json")
DETAIL_CACHE_PATH = Path("detail_cache.json")


def load_state(path: Path) -> dict:
    if not path.exists():
        return {"sites": {}}
    return json.loads(path.read_text())


def save_state(path: Path, state: dict) -> None:
    path.write_text(json.dumps(state, ensure_ascii=False, indent=1, sort_keys=True) + "\n")


def fetch_site(site: str, fetch: Callable[[], list[Listing]]) -> SiteFetch | None:
    try:
        raw = fetch()
    except Exception:  # noqa: BLE001 1 サイトの失敗でほかのサイトを止めない
        log.error("%s の取得に失敗しました\n%s", site, traceback.format_exc())
        return None
    targets = [listing for listing in raw if is_target(listing)]
    log.info("%s: 検索結果 %d 件、条件に合う %d 件", site, len(raw), len(targets))
    return SiteFetch(raw_count=len(raw), listings=targets)


def fetch_all(cache: DetailCache) -> dict[str, SiteFetch | None]:
    fetches: dict[str, SiteFetch | None] = {}
    with http_sources.client() as client:
        for site, fetch in http_sources.SOURCES.items():
            fetches[site] = fetch_site(site, lambda fetch=fetch: fetch(client, cache))

    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        browser = p.chromium.launch()
        try:
            fetches[mercari.SITE] = fetch_site(mercari.SITE, lambda: mercari.fetch(browser))
        finally:
            browser.close()
    return fetches


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    preview = os.environ.get("CHAIR_WATCH_PREVIEW") == "true"
    state = load_state(STATE_PATH)
    cache = DetailCache.load(DETAIL_CACHE_PATH)
    fetches = fetch_all(cache)
    # 詳細ページの内容は通知の成否に関係なく保存してよい（読み直しを減らすため）
    cache.save(DETAIL_CACHE_PATH)

    if preview:
        # お試し送信: 記録が空だったとして通知を作り、その中から 2 件だけ送る。state は変えない
        result = compute({"sites": {}}, fetches)
        result.notifications[:] = preview_notifications(result.notifications)
        result.failure_alerts.clear()
    else:
        result = compute(state, fetches)

    messages = notify_line.build_messages(result.notifications)
    if result.failure_alerts:
        messages.append(notify_line.build_failure_message(result.failure_alerts))

    token = os.environ.get("LINE_CHANNEL_ACCESS_TOKEN")
    user_id = os.environ.get("LINE_USER_ID")
    if messages:
        if token and user_id:
            # 送信に失敗したら例外で止まり、state は保存しない（次回送り直す）
            notify_line.push(token, user_id, messages)
            log.info("LINE に %d 通送りました", len(messages))
        else:
            # 送れなかった通知を「送ったこと」にしないよう、state は保存しない
            log.info("LINE の設定がないので送らずに表示します（state.json は更新しません）")
            print(json.dumps(messages, ensure_ascii=False, indent=1))
            # GitHub Actions では Secrets の登録漏れに気づけるよう失敗させる
            return 1 if os.environ.get("GITHUB_ACTIONS") else 0

    if not preview:
        save_state(STATE_PATH, result.state)
    return 0


def preview_notifications(notifications: list[Notification]) -> list[Notification]:
    """お試し送信用に、メルカリ（画像が WebP なので画像まわりの確認になる）とほかのサイトから 1 件ずつ選ぶ。"""
    mercari_first = [n for n in notifications if n.listing.site == mercari.SITE][:1]
    others = [n for n in notifications if n.listing.site != mercari.SITE][:1]
    return mercari_first + others


if __name__ == "__main__":
    sys.exit(main())
