"""取得 → 判定 → 差分 → 通知 → 記録の保存 を 1 回分実行する。

環境変数 LINE_CHANNEL_ACCESS_TOKEN と LINE_USER_ID がなければ、送らずに内容を表示するだけにする。
"""

import json
import logging
import os
import sys
import traceback
from collections.abc import Callable
from pathlib import Path

from chair_watch import notify_line
from chair_watch.diff import SiteFetch, compute
from chair_watch.filters import is_target
from chair_watch.models import Listing
from chair_watch.sources import http_sources, mercari

log = logging.getLogger("chair_watch")
STATE_PATH = Path("state.json")


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


def fetch_all() -> dict[str, SiteFetch | None]:
    fetches: dict[str, SiteFetch | None] = {}
    with http_sources.client() as client:
        for site, fetch in http_sources.SOURCES.items():
            fetches[site] = fetch_site(site, lambda fetch=fetch: fetch(client))

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
    state = load_state(STATE_PATH)
    result = compute(state, fetch_all())

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
            log.info("LINE の設定がないので送らずに表示します")
            print(json.dumps(messages, ensure_ascii=False, indent=1))

    save_state(STATE_PATH, result.state)
    return 0


if __name__ == "__main__":
    sys.exit(main())
