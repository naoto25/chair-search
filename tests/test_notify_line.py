from chair_watch.diff import Notification
from chair_watch.models import Listing
from chair_watch.notify_line import build_messages, build_failure_message


def notification(i: int, kind: str = "new", old: int | None = None, image: str | None = "https://img/1.jpg") -> Notification:
    listing = Listing(
        site="mercari",
        item_id=str(i),
        title=f"オカムラ シルフィー 可動肘 {i}",
        price_yen=24800,
        url=f"https://jp.mercari.com/item/m{i}",
        image_url=image,
    )
    return Notification(kind, listing, old)


def bubbles(message: dict) -> list[dict]:
    return message["contents"]["contents"]


def all_text(node) -> str:
    if isinstance(node, dict):
        return " ".join(all_text(v) for v in node.values())
    if isinstance(node, list):
        return " ".join(all_text(v) for v in node)
    return str(node)


def test_通知がなければメッセージもない():
    assert build_messages([]) == []


def test_カルーセル1通にまとめて要約をaltTextに入れる():
    [message] = build_messages([notification(1), notification(2), notification(3, "price_drop", 32000)])
    assert message["type"] == "flex"
    assert message["altText"] == "新着2件・値下げ1件"
    assert message["contents"]["type"] == "carousel"
    assert len(bubbles(message)) == 3


def test_12件を超えたら分けて送る():
    messages = build_messages([notification(i) for i in range(13)])
    assert [len(bubbles(m)) for m in messages] == [12, 1]


def test_カードに価格と種類とサイト名とリンクが入る():
    [message] = build_messages([notification(1, "price_drop", 32000)])
    [bubble] = bubbles(message)
    text = all_text(bubble)
    assert "¥32,000 → ¥24,800" in text
    assert "値下げ" in text
    assert "メルカリ" in text
    assert bubble["footer"]["contents"][0]["action"]["uri"] == "https://jp.mercari.com/item/m1"
    assert bubble["hero"]["url"] == "https://img/1.jpg"


def test_新着のカード():
    [message] = build_messages([notification(1)])
    text = all_text(bubbles(message)[0])
    assert "¥24,800" in text and "新着" in text and "→" not in text


def test_肘の記載がない出品にはそのことを書く():
    n = notification(1)
    unknown = Notification("new", Listing("mercari", "9", "オカムラ シルフィー オフィスチェア", 20000, "https://x", None))
    [message] = build_messages([n, unknown])
    known_text, unknown_text = (all_text(b) for b in bubbles(message))
    assert "肘：記載なし" not in known_text
    assert "肘：記載なし（写真で確認）" in unknown_text


def test_画像がなければheroを付けない():
    [message] = build_messages([notification(1, image=None)])
    assert "hero" not in bubbles(message)[0]


def test_失敗の知らせはテキスト():
    message = build_failure_message(["mercari", "officebusters"])
    assert message["type"] == "text"
    assert "メルカリ" in message["text"] and "オフィスバスターズ" in message["text"]
