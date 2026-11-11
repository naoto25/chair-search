"""LINE Messaging API で自分に push 通知する。"""

import httpx

from chair_watch.diff import Notification

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


def build_messages(notifications: list[Notification]) -> list[dict]:
    """通知を Flex Message のカルーセルにまとめる。12 件ごとに 1 通。"""
    if not notifications:
        return []
    new = sum(1 for n in notifications if n.kind == "new")
    drop = len(notifications) - new
    summary = "・".join(s for s in (f"新着{new}件" if new else "", f"値下げ{drop}件" if drop else "") if s)

    messages = []
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
