from pathlib import Path

from chair_watch.sources.officebusters import SERIES_PATHS, parse_series_html

FIXTURE = Path(__file__).parent / "fixtures" / "officebusters_series.html"


def test_シリーズ一覧のHTMLから出品を読む():
    listings = parse_series_html(FIXTURE.read_text())
    assert [l.item_id for l in listings] == ["628059", "628058", "628048"]

    item = listings[0]
    assert item.site == "officebusters"
    assert item.title == "【中古】シルフィー C687ER-FSF9 オカムラ（okamura） 肘付ハイバックチェア"
    # 税込価格を使う（ほかのサイトと揃える）
    assert item.price_yen == 26840
    assert item.url == "https://www.officebusters.com/items/628059"
    assert item.image_url == "https://image.officebusters.com/images/item/set628/628059/628059_m_1.jpg"


def test_出品がなければ空():
    assert parse_series_html("<html><body></body></html>") == []


def test_robots_txtで禁止されている検索ページは使わない():
    assert all(path.startswith("/series/") for path in SERIES_PATHS)
