"""商品詳細ページから読んだ内容を保存しておき、同じ出品の詳細ページを何度も読まないようにする。

形: {"<site>": {"<item_id>": "<詳細から読んだ文章>"}}
"""

import json
from collections.abc import Callable
from pathlib import Path


class DetailCache:
    def __init__(self, data: dict[str, dict[str, str | None]]):
        self.data = data

    @classmethod
    def load(cls, path: Path) -> "DetailCache":
        return cls(json.loads(path.read_text()) if path.exists() else {})

    def save(self, path: Path) -> None:
        path.write_text(json.dumps(self.data, ensure_ascii=False, indent=1, sort_keys=True) + "\n")

    def get_or_fetch(self, site: str, item_id: str, fetch: Callable[[], str | None]) -> str | None:
        items = self.data.setdefault(site, {})
        if item_id not in items:
            items[item_id] = fetch()
        return items[item_id]

    def prune(self, site: str, keep: set[str]) -> None:
        """今回の検索結果にない（売れた・消えた）出品の詳細を消す。"""
        items = self.data.get(site, {})
        for item_id in list(items):
            if item_id not in keep:
                del items[item_id]
