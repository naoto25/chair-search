import json
from pathlib import Path

from chair_watch.sources.mercari import parse_search_response, search_url

FIXTURE = Path(__file__).parent / "fixtures" / "mercari_search.json"


def test_検索結果のJSONから出品を読む():
    listings = parse_search_response(json.loads(FIXTURE.read_text()))
    assert len(listings) == 10

    item = next(l for l in listings if l.item_id == "m26476732034")
    assert item.site == "mercari"
    assert item.title == "【中古 訳あり】オカムラ シルフィー ハイバック 可動肘 ジャケットハンガー"
    assert item.price_yen == 15880
    assert item.url == "https://jp.mercari.com/item/m26476732034"
    assert item.image_url == "https://static.mercdn.net/thumb/item/webp/m26476732034_1.jpg?1793834806"
    # ブランド名を説明文として持つ（タイトルにメーカー名がない出品を拾うため）
    assert item.description == "OKAMURA"


def test_メルカリShopsの出品はshopsのURLにする():
    listings = parse_search_response(json.loads(FIXTURE.read_text()))
    shop = next(l for l in listings if l.item_id == "2JYarP978UPTJtogyfJWy2")
    assert shop.url == "https://jp.mercari.com/shops/product/2JYarP978UPTJtogyfJWy2"
    assert shop.price_yen == 95000


def test_itemsがなければ空():
    assert parse_search_response({}) == []


def test_検索URLは販売中_3万円以下_新しい順():
    url = search_url("イトーキ アクト")
    assert url.startswith("https://jp.mercari.com/search?")
    assert "keyword=%E3%82%A4%E3%83%88%E3%83%BC%E3%82%AD+%E3%82%A2%E3%82%AF%E3%83%88" in url
    assert "status=on_sale" in url
    assert "price_max=30000" in url
    assert "sort=created_time" in url and "order=desc" in url
