from chair_watch.detail_cache import DetailCache


def test_読んだ詳細を保存して次回は読まない(tmp_path):
    path = tmp_path / "detail_cache.json"
    cache = DetailCache.load(path)
    calls = []

    def fetch(item_id: str) -> str:
        calls.append(item_id)
        return f"詳細 {item_id}"

    assert cache.get_or_fetch("officebusters", "1", lambda: fetch("1")) == "詳細 1"
    cache.save(path)

    again = DetailCache.load(path)
    assert again.get_or_fetch("officebusters", "1", lambda: fetch("1")) == "詳細 1"
    assert calls == ["1"]


def test_サイトごとに分けて持つ(tmp_path):
    cache = DetailCache.load(tmp_path / "none.json")
    cache.get_or_fetch("a", "1", lambda: "A")
    assert cache.get_or_fetch("b", "1", lambda: "B") == "B"


def test_今回の検索結果にない出品の詳細は消す(tmp_path):
    cache = DetailCache.load(tmp_path / "none.json")
    cache.get_or_fetch("a", "1", lambda: "x")
    cache.get_or_fetch("a", "2", lambda: "y")
    cache.get_or_fetch("b", "9", lambda: "z")
    cache.prune("a", keep={"2"})
    assert cache.data == {"a": {"2": "y"}, "b": {"9": "z"}}
