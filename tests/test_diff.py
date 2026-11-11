from chair_watch.diff import FAILURE_ALERT_THRESHOLD, SiteFetch, compute
from chair_watch.models import Listing


def item(item_id: str, price: int, site: str = "a") -> Listing:
    return Listing(
        site=site,
        item_id=item_id,
        title=f"item {item_id}",
        price_yen=price,
        url=f"https://example.com/{item_id}",
        image_url=None,
    )


def fetched(*items: Listing) -> SiteFetch:
    return SiteFetch(raw_count=len(items), listings=list(items))


def state_with(items: dict[str, int], failures: int = 0, site: str = "a") -> dict:
    return {"sites": {site: {"items": items, "failures": failures}}}


def test_初回はそのサイトを記録するだけで通知しない():
    result = compute({"sites": {}}, {"a": fetched(item("1", 20000))})
    assert result.notifications == []
    assert result.state["sites"]["a"]["items"] == {"1": 20000}


def test_新着で3万円以下なら通知():
    result = compute(state_with({}), {"a": fetched(item("1", 30000))})
    [n] = result.notifications
    assert (n.kind, n.listing.item_id, n.old_price) == ("new", "1", None)


def test_新着でも3万円を超えたら通知せず記録だけ():
    result = compute(state_with({}), {"a": fetched(item("1", 30001))})
    assert result.notifications == []
    assert result.state["sites"]["a"]["items"] == {"1": 30001}


def test_3万円超から3万円以下に値下げしたら通知():
    result = compute(state_with({"1": 35000}), {"a": fetched(item("1", 29800))})
    [n] = result.notifications
    assert (n.kind, n.old_price, n.listing.price_yen) == ("price_drop", 35000, 29800)


def test_3万円以下のままさらに値下げしても通知():
    result = compute(state_with({"1": 28000}), {"a": fetched(item("1", 25000))})
    [n] = result.notifications
    assert n.kind == "price_drop"


def test_値下げしても3万円を超えていれば通知しない():
    result = compute(state_with({"1": 40000}), {"a": fetched(item("1", 35000))})
    assert result.notifications == []
    assert result.state["sites"]["a"]["items"] == {"1": 35000}


def test_値上げと同額は通知せず記録を更新():
    result = compute(state_with({"1": 20000, "2": 25000}), {"a": fetched(item("1", 22000), item("2", 25000))})
    assert result.notifications == []
    assert result.state["sites"]["a"]["items"] == {"1": 22000, "2": 25000}


def test_消えた出品は記録から外す():
    result = compute(state_with({"1": 20000, "2": 25000}), {"a": fetched(item("2", 25000))})
    assert result.state["sites"]["a"]["items"] == {"2": 25000}


def test_取得失敗したサイトは記録を残し失敗回数を増やす():
    result = compute(state_with({"1": 20000}), {"a": None})
    assert result.notifications == []
    assert result.state["sites"]["a"] == {"items": {"1": 20000}, "failures": 1}
    assert result.failure_alerts == []


def test_前回1件以上あって今回0件なら失敗として扱う():
    result = compute(state_with({"1": 20000}), {"a": SiteFetch(raw_count=0, listings=[])})
    assert result.state["sites"]["a"] == {"items": {"1": 20000}, "failures": 1}


def test_条件に合う出品が0件でも検索結果があれば成功として扱う():
    result = compute(state_with({"1": 20000}, failures=2), {"a": SiteFetch(raw_count=5, listings=[])})
    assert result.state["sites"]["a"] == {"items": {}, "failures": 0}


def test_続けて失敗したら閾値の回だけ知らせる():
    almost = state_with({}, failures=FAILURE_ALERT_THRESHOLD - 1)
    result = compute(almost, {"a": None})
    assert result.failure_alerts == ["a"]

    again = compute(result.state, {"a": None})
    assert again.failure_alerts == []


def test_成功したら失敗回数を0に戻す():
    result = compute(state_with({}, failures=5), {"a": fetched(item("1", 40000))})
    assert result.state["sites"]["a"]["failures"] == 0


def test_初回から失敗したサイトは成功した回を初回として扱う():
    failed = compute({"sites": {}}, {"a": None})
    assert failed.state["sites"]["a"]["initialized"] is False

    first_success = compute(failed.state, {"a": fetched(item("1", 20000))})
    assert first_success.notifications == []
    assert first_success.state["sites"]["a"]["items"] == {"1": 20000}


def test_今回取得しなかったサイトの記録はそのまま残す():
    state = {"sites": {"a": {"items": {"1": 1}, "failures": 0}, "b": {"items": {"2": 2}, "failures": 0}}}
    result = compute(state, {"a": fetched(item("1", 1))})
    assert result.state["sites"]["b"] == {"items": {"2": 2}, "failures": 0}


def test_元のstateは書き換えない():
    state = state_with({"1": 20000})
    compute(state, {"a": fetched(item("1", 10000))})
    assert state == state_with({"1": 20000})
