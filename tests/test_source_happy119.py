from pathlib import Path

from chair_watch.sources.happy119 import parse_arm_type, parse_search_html, search_url

FIXTURE = Path(__file__).parent / "fixtures" / "happy119_search.html"


def test_検索結果のHTMLから出品を読む():
    listings = parse_search_html(FIXTURE.read_text())
    assert [l.item_id for l in listings] == ["IO-886027B", "IO-886026B", "IO-886025B", "IO-881613B"]

    item = listings[0]
    assert item.site == "happy119"
    # メーカー名を商品名の前に付ける
    assert item.title == "オカムラ シルフィーチェア　ハイバック　メッシュタイプ　C685XW FMP3"
    assert item.price_yen == 28600
    assert item.url == "https://www.119happy.com/ws/chair_cmdty/IO-886027B/IO-886027B/IO"
    assert item.image_url == "https://www.119happy.com/ws/image/cmdty/IO-886027B/mobile_IO-886027B_IO-886027B_1.jpg"


def test_詳細ページのタイプ欄から肘の種類を読む():
    html = (Path(__file__).parent / "fixtures" / "happy119_detail.html").read_text()
    assert parse_arm_type(html) == "肘無"


def test_タイプ欄がなければNone():
    assert parse_arm_type("<html><body><table></table></body></html>") is None


def test_出品がなければ空():
    assert parse_search_html("<html><body>現在、お探しの商品はございません</body></html>") == []


def test_検索語はShift_JISでURLに入れる():
    assert search_url("シルフィー") == (
        "https://www.119happy.com/ws/advancedsearch?srchWordTxt=%83V%83%8B%83t%83B%81%5B"
        "&cmdtyFlagTxt=sr&dispModeTxt=2&actionNameTxt=list&pass=advancedsearch&pageSizeSel=80"
    )
