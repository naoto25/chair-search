from chair_watch.diff import Notification
from chair_watch.main import preview_notifications
from chair_watch.models import Listing


def n(site: str, item_id: str) -> Notification:
    return Notification("new", Listing(site, item_id, "t", 1, "https://x", None))


def test_お試し送信はメルカリとほかのサイトから1件ずつ():
    picked = preview_notifications([n("officebusters", "1"), n("officebusters", "2"), n("mercari", "3"), n("mercari", "4")])
    assert [(x.listing.site, x.listing.item_id) for x in picked] == [("mercari", "3"), ("officebusters", "1")]


def test_候補がなければ空():
    assert preview_notifications([]) == []
