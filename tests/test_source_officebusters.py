from dataclasses import replace
from pathlib import Path

from chair_watch.filters import is_target
from chair_watch.sources.officebusters import SERIES_PATHS, parse_detail_text, parse_series_html

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


DETAIL = Path(__file__).parent / "fixtures" / "officebusters_detail.html"


def test_詳細ページのキャッチコピーとタグと商品説明を読む():
    text = parse_detail_text(DETAIL.read_text())
    assert "固定肘" in text  # キャッチコピーとタグ
    assert "・可動肘" in text  # 商品説明


def test_おすすめ商品の欄は読まない():
    html = """
    <div class="m-goodsDetailExplain_head__text"><h2>シルフィー</h2><span>可動肘 ハイバック</span></div>
    <div class="m-goodsTopics"><ul><li><a>前傾チルト</a></li></ul></div>
    <div class="m-goodsDescription_wrap">・アジャストアーム</div>
    <ul class="m-recommend_list"><li><p class="m-recommend_list__name">シルフィー デザインアーム（固定肘）</p></li></ul>
    """
    text = parse_detail_text(html)
    assert "可動肘" in text and "アジャストアーム" in text
    assert "固定肘" not in text


def test_固定肘と書かれた詳細なら対象外になる():
    [listing] = parse_series_html(FIXTURE.read_text())[:1]
    assert is_target(listing)
    assert not is_target(replace(listing, description=parse_detail_text(DETAIL.read_text())))
