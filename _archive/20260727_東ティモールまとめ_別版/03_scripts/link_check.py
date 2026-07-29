# -*- coding: utf-8 -*-
"""
出典リンク検証ツール
成果物HTML内の href（http/https）を抽出し、到達性を並列チェックする。
- リダイレクト（3xx）は最終的に2xxになれば OK 扱い
- 4xx/5xx を BROKEN、接続不能/タイムアウトを ERROR として報告
使い方: python link_check.py [対象HTML(省略時は最新v7)]
"""
import re, sys, ssl, urllib.request, urllib.error
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

BASE = Path(__file__).resolve().parent.parent
target = Path(sys.argv[1]) if len(sys.argv) > 1 else \
    BASE / "02_成果物" / "20260727_東ティモールまとめ_別版_v7.html"

html = target.read_text(encoding="utf-8")
urls = sorted(set(re.findall(r'href="(https?://[^"]+)"', html)))

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120 Safari/537.36"


def check(url):
    req = urllib.request.Request(url, method="GET", headers={"User-Agent": UA})
    try:
        with urllib.request.urlopen(req, timeout=15, context=ctx) as r:
            return (url, "OK", r.status, r.geturl())
    except urllib.error.HTTPError as e:
        # 405(HEAD拒否等)や403はサイト側都合のことも多いので区別して表示
        cat = "BROKEN" if e.code >= 400 and e.code not in (403, 405, 429, 999) else "WARN"
        return (url, cat, e.code, "")
    except Exception as e:
        return (url, "ERROR", type(e).__name__, str(e)[:60])


results = []
with ThreadPoolExecutor(max_workers=12) as ex:
    futs = {ex.submit(check, u): u for u in urls}
    for f in as_completed(futs):
        results.append(f.result())

order = {"BROKEN": 0, "ERROR": 1, "WARN": 2, "OK": 3}
results.sort(key=lambda r: (order.get(r[1], 9), r[0]))

counts = {}
for _, cat, *_ in results:
    counts[cat] = counts.get(cat, 0) + 1

print(f"対象: {target.name}")
print(f"URL総数(ユニーク): {len(urls)}")
print("集計:", counts)
print("\n--- 要対応（BROKEN / ERROR / WARN=403/405/429等の到達注意） ---")
any_issue = False
for url, cat, code, extra in results:
    if cat != "OK":
        any_issue = True
        print(f"[{cat}] {code} {url} {('-> '+extra) if extra else ''}")
if not any_issue:
    print("なし（全URLが2xx/リダイレクト成功）")
