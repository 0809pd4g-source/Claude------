# -*- coding: utf-8 -*-
"""v34 -> v35。地域別保育料の目安3件（low/mid/high）に「階層の考え方」の
   参考資料を添える。金額そのものは確認できていないので verified:false は変えない。
   manual（利用者が自分で入れる欄）には出典を付けない。"""
import io, sys, hashlib
from pathlib import Path

OUT = Path("02_output")
SRC = OUT / "20260903_ライフプランCFシミュレーター汎用版_v34.html"
DST = OUT / "20260903_ライフプランCFシミュレーター汎用版_v35.html"
lines = io.open(SRC, encoding="utf-8").read().split(chr(10))

URL = ("https://www.cfa.go.jp/assets/contents/node/basic_page/field_ref_resources/"
       "c47709ef-8880-42e6-bb7e-9818b6b728c5/5d767a64/"
       "20230929_policies_kokoseido_jigyousha_38.pdf")
REF = [
    '    /* \u2605\u91d1\u984d\u306f\u78ba\u8a8d\u3067\u304d\u3066\u3044\u306a\u3044\uff08\u81ea\u6cbb\u4f53\u3054\u3068\u306b\u9055\u3046\uff09\u3002',
    '         \u305f\u3060\u3057\u300c\u306a\u305c\u6240\u5f97\u968e\u5c64\u3067\u5206\u304b\u308c\u308b\u306e\u304b\u300d\u306f\u56fd\u306e\u67a0\u7d44\u307f\u3067\u6c7a\u307e\u308b\u306e\u3067\u3001',
    '         \u305d\u306e\u8003\u3048\u65b9\u306e\u53c2\u8003\u8cc7\u6599\u3060\u3051\u3092\u6dfb\u3048\u308b\u3002**\u91d1\u984d\u306e\u88cf\u3065\u3051\u3067\u306f\u306a\u3044\u3002** */',
    '    source:"' + URL + '",',
    '    sourceLabel:"\u53c2\u8003\uff1a\u3053\u3069\u3082\u5bb6\u5ead\u5e81\u300c\u56fd\u304c\u5b9a\u3081\u308b\u5229\u7528\u8005\u8ca0\u62c5\u306e\u4e0a\u9650\u984d\u300d\uff08\u968e\u5c64\u306e\u8003\u3048\u65b9\u3002\u91d1\u984d\u306f\u81ea\u6cbb\u4f53\u3054\u3068\u306b\u7570\u306a\u308a\u307e\u3059\uff09",',
]
TARGET = '    source:"", sourceLabel:"",'

hits = [i for i, l in enumerate(lines) if l == TARGET]
if len(hits) != 4:
    print("  [NG] source:\"\" の行が4件ではない: " + str(len(hits))); sys.exit(1)
# 先頭は manual（自分で入力する欄）なので触らない。残り3件（low/mid/high）に付ける。
for i in reversed(hits[1:]):
    lines[i:i+1] = REF
print("  [ok] low/mid/high の3件に参考資料を追加（manual は対象外）")

src = "\n".join(lines)
for old, new, tag in [
    ('tag:"\u6c4e\u7528\u7248 v34"', 'tag:"\u6c4e\u7528\u7248 v35"', "V-tag"),
    ('file:"20260903_\u30e9\u30a4\u30d5\u30d7\u30e9\u30f3CF\u30b7\u30df\u30e5\u30ec\u30fc\u30bf\u30fc\u6c4e\u7528\u7248_v34.html"',
     'file:"20260903_\u30e9\u30a4\u30d5\u30d7\u30e9\u30f3CF\u30b7\u30df\u30e5\u30ec\u30fc\u30bf\u30fc\u6c4e\u7528\u7248_v35.html"', "V-file"),
]:
    if src.count(old) != 1:
        print("  [NG] " + tag); sys.exit(1)
    src = src.replace(old, new, 1)
    print("  [ok] " + tag)

CRLF = chr(13) + chr(10)
io.open(DST, "w", encoding="utf-8", newline=CRLF).write(src)
raw = DST.read_bytes()
print("")
print("\u30d0\u30a4\u30c8: " + format(len(raw), ",") + " / \u884c: " + format(src.count("\n") + 1, ","))
print("SHA-256: " + hashlib.sha256(raw).hexdigest())
