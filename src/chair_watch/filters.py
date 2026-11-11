"""出品がシルフィー / アクトの肘付きかを、タイトルと説明文の文字だけで判定する。"""

import re
import unicodedata

from chair_watch.models import Listing

PRICE_LIMIT_YEN = 30_000

_SYLPHY = re.compile(r"シルフィ|sylphy")
_OKAMURA = re.compile(r"オカムラ|okamura")
_ACT = re.compile(r"アクト|(?<![a-z])act(?![a-z])")
_ITOKI = re.compile(r"イトーキ|itoki")
_ARM = re.compile(r"肘|ひじ|アーム")
# 「アームレスト」は肘ありなので「アームレス」の後に「ト」が続く場合は除外しない
_NO_OR_FIXED_ARM = re.compile(
    r"肘なし|肘無|ひじなし|ひじ無|アームレス(?!ト)|アームなし|アーム無|アームレストなし|アームレスト無|固定肘|肘固定"
)

# 「シルフィー用 ヘッドレスト」「肘パッド」など、椅子本体ではない部品の出品
_PARTS_ONLY = re.compile(
    r"(シルフィ|シルフィー|アクト|sylphy|act)(チェア)?\s*用|パーツ|部品|パッドのみ|パッド\s*\d+個|肘置き|スポンジ|左右セット"
)


def normalize(text: str) -> str:
    """半角カナ・全角英数をそろえ、英字を小文字にする。"""
    return unicodedata.normalize("NFKC", text).lower()


def _text(listing: Listing) -> str:
    return normalize(f"{listing.title}\n{listing.description or ''}")


def is_chair_model(listing: Listing) -> bool:
    """肘の有無は問わず、シルフィー / アクトの椅子本体の出品か。"""
    text = _text(listing)
    is_sylphy = bool(_SYLPHY.search(text)) and (bool(_OKAMURA.search(text)) or listing.from_chair_category)
    is_act = bool(_ACT.search(text)) and bool(_ITOKI.search(text))
    return (is_sylphy or is_act) and not _PARTS_ONLY.search(normalize(listing.title))


def is_target(listing: Listing) -> bool:
    """シルフィー / アクトで、肘があり、肘なし・固定肘と書かれていない出品か。"""
    if not is_chair_model(listing):
        return False
    text = _text(listing)
    if _NO_OR_FIXED_ARM.search(text):
        return False
    return bool(_ARM.search(text))
