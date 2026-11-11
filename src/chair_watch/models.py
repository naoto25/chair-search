from dataclasses import dataclass


@dataclass(frozen=True)
class Listing:
    """各サイトの検索結果に出ていた出品 1 件。"""

    site: str
    item_id: str
    title: str
    # 表示価格（円）。送料は含めない
    price_yen: int
    url: str
    image_url: str | None
    # 検索結果に説明文があるサイトだけ入る
    description: str | None = None
    # チェアのカテゴリで絞り込んだ検索から取得したか
    from_chair_category: bool = False
