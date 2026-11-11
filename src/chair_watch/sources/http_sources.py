"""ブラウザを使わずに HTTP だけで読めるサイトをまとめる。"""

from collections.abc import Callable

import httpx

from chair_watch.models import Listing
from chair_watch.sources import bicreyouth, happy119, officebusters

USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/130.0 Safari/537.36"
)

SOURCES: dict[str, Callable[[httpx.Client], list[Listing]]] = {
    officebusters.SITE: officebusters.fetch,
    bicreyouth.SITE: bicreyouth.fetch,
    happy119.SITE: happy119.fetch,
}


def client() -> httpx.Client:
    return httpx.Client(
        headers={"User-Agent": USER_AGENT, "Accept-Language": "ja"},
        follow_redirects=True,
        timeout=30,
    )
