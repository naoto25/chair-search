"""LINE Messaging API で自分に push 通知する。"""

import httpx

from chair_watch.diff import Notification
from chair_watch.filters import arm_status
from chair_watch.models import Listing

PUSH_URL = "https://api.line.me/v2/bot/message/push"
# Flex Message のカルーセルに入れられるカードの上限
MAX_BUBBLES = 12
# 1 回の push に入れられるメッセージの上限
MAX_MESSAGES_PER_PUSH = 5

SITE_NAMES = {
    "officebusters": "オフィスバスターズ",
    "bicreyouth": "ビックリユース",
    "happy119": "オフィスレスキュー119",
    "mercari": "メルカリ",
}


def site_name(site: str) -> str:
    return SITE_NAMES.get(site, site)


def build_messages(notifications: list[Notification], image_url: str | None = None) -> list[dict]:
    """通知を Flex Message のカルーセルにまとめる。12 件ごとに 1 通。

    image_url（1 件目の写真。JPEG か PNG）があれば、先頭に画像メッセージを付ける。
    1 回の push にまとめたメッセージは何個でも 1 通と数えられるので、通数は増えない。
    """
    if not notifications:
        return []
    summary = _summary(notifications)

    messages: list[dict] = []
    if image_url:
        messages.append({"type": "image", "originalContentUrl": image_url, "previewImageUrl": image_url})
    for start in range(0, len(notifications), MAX_BUBBLES):
        chunk = notifications[start : start + MAX_BUBBLES]
        messages.append(
            {
                "type": "flex",
                "altText": summary,
                "contents": {"type": "carousel", "contents": [_bubble(n) for n in chunk]},
            }
        )
    return messages


_TITLE_MAX = 40


def _summary(notifications: list[Notification]) -> str:
    """プッシュ通知に出る文。件数と、1 件目の価格・商品名・サイト名。"""
    new = sum(1 for n in notifications if n.kind == "new")
    drop = len(notifications) - new
    counts = "・".join(s for s in (f"新着{new}件" if new else "", f"値下げ{drop}件" if drop else "") if s)
    first = notifications[0].listing
    title = first.title if len(first.title) <= _TITLE_MAX else first.title[:_TITLE_MAX] + "…"
    rest = "ほか" if len(notifications) > 1 else ""
    return f"{counts}｜¥{first.price_yen:,} {title}（{site_name(first.site)}）{rest}"


def jpeg_url_candidates(listing: Listing) -> list[str]:
    """LINE の画像メッセージに使えそうな（JPEG で返りそうな）画像 URL を、試す順に返す。"""
    url = listing.image_url
    if not url:
        return []
    candidates = []
    if "static.mercdn.net/thumb/item/webp/" in url:
        candidates.append(url.replace("/thumb/item/webp/", "/item/detail/orig/photos/"))
    if url.endswith("@webp"):
        candidates.append(url.removesuffix("@webp") + "@jpg")
    return [*candidates, url]


def find_jpeg_image(client: httpx.Client, listing: Listing) -> str | None:
    """候補 URL を実際に取りに行き、JPEG か PNG で返ってきた最初の URL を返す。"""
    for url in jpeg_url_candidates(listing):
        try:
            response = client.get(url)
        except httpx.HTTPError:
            continue
        content_type = response.headers.get("content-type", "")
        if response.status_code == 200 and content_type.split(";")[0] in ("image/jpeg", "image/png"):
            return url
    return None


def _bubble(n: Notification) -> dict:
    listing = n.listing
    if n.kind == "price_drop":
        badge, color = "⬇値下げ", "#D93025"
        price = f"¥{n.old_price:,} → ¥{listing.price_yen:,}"
    else:
        badge, color = "🆕新着", "#1A73E8"
        price = f"¥{listing.price_yen:,}"

    bubble: dict = {
        "type": "bubble",
        "size": "kilo",
        "body": {
            "type": "box",
            "layout": "vertical",
            "spacing": "sm",
            "contents": [
                {"type": "text", "text": listing.title, "wrap": True, "maxLines": 3, "size": "sm", "weight": "bold"},
                {"type": "text", "text": price, "size": "lg", "weight": "bold", "wrap": True},
                {"type": "text", "text": badge, "size": "sm", "color": color},
                {"type": "text", "text": site_name(listing.site), "size": "xs", "color": "#888888"},
            ],
        },
        "footer": {
            "type": "box",
            "layout": "vertical",
            "contents": [
                {
                    "type": "button",
                    "style": "primary",
                    "height": "sm",
                    "action": {"type": "uri", "label": "商品ページを開く", "uri": listing.url},
                }
            ],
        },
    }
    if arm_status(listing) == "unknown":
        bubble["body"]["contents"].append(
            {"type": "text", "text": "肘：記載なし（写真で確認）", "size": "xs", "color": "#B06000", "wrap": True}
        )
    if listing.image_url:
        bubble["hero"] = {
            "type": "image",
            "url": listing.image_url,
            "size": "full",
            "aspectRatio": "1:1",
            "aspectMode": "cover",
        }
    return bubble


def build_failure_message(sites: list[str]) -> dict:
    names = "、".join(site_name(s) for s in sites)
    return {
        "type": "text",
        "text": f"{names} の取得に続けて失敗しています。サイトの画面が変わった可能性があります。",
    }


def push(token: str, user_id: str, messages: list[dict]) -> None:
    """messages を 5 通ずつ push する。失敗したら例外を投げる。"""
    with httpx.Client(timeout=30) as client:
        for start in range(0, len(messages), MAX_MESSAGES_PER_PUSH):
            response = client.post(
                PUSH_URL,
                headers={"Authorization": f"Bearer {token}"},
                json={"to": user_id, "messages": messages[start : start + MAX_MESSAGES_PER_PUSH]},
            )
            response.raise_for_status()
