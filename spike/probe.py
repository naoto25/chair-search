"""スパイク: GitHub Actions から各サイトを取得できるか確かめる使い捨てスクリプト。

取得した HTML/JSON と要約を out/ に保存する。本実装では使わない。
"""

import json
import re
import sys
from pathlib import Path
from urllib.parse import urljoin

import httpx
from playwright.sync_api import sync_playwright

OUT = Path("out")
UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/130.0 Safari/537.36"
)

targets = json.loads(Path(sys.argv[1]).read_text())


def summarize(name: str, url: str, final_url: str, status: int, html: str) -> dict:
    title = re.search(r"<title[^>]*>(.*?)</title>", html, re.S | re.I)
    forms = re.findall(r"<form[^>]*>.*?</form>", html, re.S | re.I)
    form_info = []
    for f in forms[:10]:
        action = re.search(r'action="([^"]*)"', f)
        inputs = re.findall(r'<input[^>]*name="([^"]*)"', f)
        form_info.append({"action": action.group(1) if action else None, "inputs": inputs})
    hrefs = re.findall(r'href="([^"]+)"', html)
    interesting = sorted(
        {
            urljoin(final_url, h)
            for h in hrefs
            if re.search(r"search|item|product|goods|chair|category|keyword", h, re.I)
        }
    )[:60]
    return {
        "name": name,
        "url": url,
        "final_url": final_url,
        "status": status,
        "bytes": len(html),
        "title": title.group(1).strip() if title else None,
        "forms": form_info,
        "links": interesting,
        "price_hits": len(re.findall(r"[0-9,]+\s*円|¥\s*[0-9,]+", html)),
    }


def main() -> None:
    OUT.mkdir(exist_ok=True)
    results = []
    with httpx.Client(headers={"User-Agent": UA, "Accept-Language": "ja"}, follow_redirects=True, timeout=30) as c:
        for t in targets:
            if t.get("browser"):
                continue
            try:
                r = c.get(t["url"])
                (OUT / f"{t['name']}.html").write_text(r.text)
                results.append(summarize(t["name"], t["url"], str(r.url), r.status_code, r.text))
            except Exception as e:  # noqa: BLE001
                results.append({"name": t["name"], "url": t["url"], "error": repr(e)})

    with sync_playwright() as p:
        browser = p.chromium.launch()
        ctx = browser.new_context(user_agent=UA, locale="ja-JP")
        for t in targets:
            if not t.get("browser"):
                continue
            page = ctx.new_page()
            captured = []

            def on_response(resp, captured=captured):
                if any(k in resp.url for k in t.get("capture", [])):
                    try:
                        captured.append({"url": resp.url, "status": resp.status, "body": resp.json()})
                    except Exception as e:  # noqa: BLE001
                        captured.append({"url": resp.url, "status": resp.status, "error": repr(e)})

            page.on("response", on_response)
            try:
                resp = page.goto(t["url"], wait_until="networkidle", timeout=60000)
                page.wait_for_timeout(3000)
                html = page.content()
                (OUT / f"{t['name']}.html").write_text(html)
                (OUT / f"{t['name']}.captured.json").write_text(json.dumps(captured, ensure_ascii=False, indent=1))
                s = summarize(t["name"], t["url"], page.url, resp.status if resp else -1, html)
                s["captured"] = [{"url": x["url"], "status": x["status"]} for x in captured]
                results.append(s)
            except Exception as e:  # noqa: BLE001
                results.append({"name": t["name"], "url": t["url"], "error": repr(e)})
            page.close()
        browser.close()

    (OUT / "summary.json").write_text(json.dumps(results, ensure_ascii=False, indent=1))
    for r in results:
        print(json.dumps({k: r.get(k) for k in ("name", "status", "final_url", "bytes", "title", "price_hits", "error")}, ensure_ascii=False))


if __name__ == "__main__":
    main()
