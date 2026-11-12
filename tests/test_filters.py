import pytest

from chair_watch.filters import arm_status, is_target
from chair_watch.models import Listing


def listing(
    title: str, description: str | None = None, chair_category: bool = False, allow_arm_unknown: bool = False
) -> Listing:
    return Listing(
        site="test",
        item_id="1",
        title=title,
        price_yen=20000,
        url="https://example.com/1",
        image_url=None,
        description=description,
        from_chair_category=chair_category,
        allow_arm_unknown=allow_arm_unknown,
    )


def test_肘の状態():
    assert arm_status(listing("オカムラ シルフィー 可動肘")) == "yes"
    assert arm_status(listing("オカムラ シルフィー 肘なし")) == "no"
    assert arm_status(listing("オカムラ シルフィー 固定肘")) == "no"
    assert arm_status(listing("オカムラ シルフィー ハイバック")) == "unknown"


def test_肘の記載なしを許すサイトでは記載なしも対象():
    assert is_target(listing("オカムラ シルフィー オフィスチェア", allow_arm_unknown=True))


def test_肘の記載なしを許すサイトでも肘なしと部品は除外():
    assert not is_target(listing("オカムラ シルフィー 肘無し", allow_arm_unknown=True))
    assert not is_target(listing("オカムラ シルフィー用 ヘッドレスト", allow_arm_unknown=True))


@pytest.mark.parametrize(
    "title",
    [
        "オカムラ シルフィー 可動肘付 ブラック",
        "okamura シルフィ アジャストアーム",
        "OKAMURA SYLPHY 肘付き ハイバック",
        "ｵｶﾑﾗ シルフィー ｱｰﾑ付き",  # 半角カナ
        "イトーキ アクトチェア 可動肘",
        "ITOKI ACT チェア アームレスト付",
        "イトーキ アクト ひじ付き",
    ],
)
def test_肘付きのシルフィーとアクトは対象(title):
    assert is_target(listing(title))


@pytest.mark.parametrize(
    "title",
    [
        "オカムラ シルフィー 肘なし",
        "オカムラ シルフィー 肘無し ローバック",
        "イトーキ アクト アームレス",
        "イトーキ アクトチェア アームなし",
        "オカムラ シルフィー 固定肘",
        "オカムラ シルフィー 肘固定タイプ",
        "オカムラ シルフィー ローバック 5本脚 メッシュ 肘無 オフィスチェア",
    ],
)
def test_肘なしと固定肘は除外(title):
    assert not is_target(listing(title))


def test_肘の記載がないものは除外():
    assert not is_target(listing("オカムラ シルフィー ハイバック"))


def test_説明文の肘の記載も見る():
    assert is_target(listing("オカムラ シルフィー ハイバック", description="可動肘付きです"))
    assert not is_target(listing("オカムラ シルフィー 肘付き", description="肘は固定肘です"))


@pytest.mark.parametrize(
    "title",
    [
        "日産 シルフィ アームレスト",  # 車の部品
        "アクトフォーム アーム",  # メーカー名がない
        "コクヨ ベゼル 肘付き",
    ],
)
def test_メーカー名がないものや別製品は除外(title):
    assert not is_target(listing(title))


@pytest.mark.parametrize(
    "title",
    [
        "オカムラ　シルフィー用　可動ヘッドレスト　アーム",
        "【オカムラ】シルフィー用 肘パッド 2個セット",
        "オカムラ シルフィー アームパッドのみ",
        "イトーキ アクトチェア 肘 交換パーツ",
        "オカムラ シルフィー 可動肘 部品",
        "オカムラ シルフィー アジャストアーム レストアーム 肘置き スポンジ",
        "オカムラ シルフィー/サブリナ アジャストアーム 左右セット",
        "イトーキ アクトチェア用ハンガー アーム",
    ],
)
def test_部品だけの出品は除外(title):
    assert not is_target(listing(title))


def test_状態の説明にパッドとあっても本体なら対象():
    assert is_target(listing("肘パッドスレあり 2019年製 イトーキ アクトチェア ハイバック 可動肘"))


def test_ブランド情報だけにメーカー名があっても対象():
    assert is_target(listing("シルフィー 可動肘 ブラック", description="OKAMURA"))


def test_チェアのカテゴリから取得したシルフィーはメーカー名がなくても対象():
    assert is_target(listing("シルフィー 可動肘 ブラック", chair_category=True))


def test_contactなどの英単語のactには反応しない():
    assert not is_target(listing("ITOKI contact desk 肘付き"))
