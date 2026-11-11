import json
from pathlib import Path

from chair_watch.sources.bicreyouth import parse_search_response, search_url

FIXTURE = Path(__file__).parent / "fixtures" / "bicreyouth_search.json"


def product(**overrides) -> dict:
    base = {
        "system_code": "000000000001",
        "product_name": "【中古】オカムラ シルフィー 肘付き",
        "product_group_name": "肘付 オフィスチェア",
        "sell_price": 36300,
        "discount_rate": "0.00",
        "discount_period": "000000000000|999999999999",
        "quantity": 1,
        "display": "Y",
        "max_image_url": "https://img/1.jpg",
    }
    return base | overrides


def test_在庫のある出品だけ読む():
    listings = parse_search_response(json.loads(FIXTURE.read_text()))
    # フィクスチャ 5 件のうち在庫があるのは 1 件だけ（ほかは SOLD OUT）
    [item] = listings
    assert item.site == "bicreyouth"
    assert item.item_id == "000000019388"
    assert item.price_yen == 44000
    assert item.url == "https://bic-reyouth.shop/view/item/000000019388"
    assert item.title.startswith("【中古】オカムラ 肘無オフィスチェア シルフィー")
    assert item.image_url and item.image_url.startswith("https://makeshop-multi-images.akamaized.net/")
    assert item.description == "肘無 オフィスチェア"


def test_割引中は割引後の価格():
    [item] = parse_search_response({"data": [product(sell_price=26400, discount_rate="55.00")]})
    assert item.price_yen == 11880


def test_割引期間外なら割引しない():
    expired = "202001010000|202001312359"
    [item] = parse_search_response({"data": [product(sell_price=26400, discount_rate="55.00", discount_period=expired)]})
    assert item.price_yen == 26400


def test_非表示の出品は読まない():
    assert parse_search_response({"data": [product(display="N")]}) == []


def test_カテゴリ名がなくても読める():
    [item] = parse_search_response({"data": [product(product_group_name=None)]})
    assert item.description is None


def test_検索URL():
    assert search_url("シルフィ") == (
        "https://kanri.bic-reyouth.com/api/shop/product/search?keyword=%E3%82%B7%E3%83%AB%E3%83%95%E3%82%A3&limit=50"
    )
