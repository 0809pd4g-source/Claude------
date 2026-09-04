# -*- coding: utf-8 -*-
r"""表示中の操作要素に名前が付いているかの検査（静的）。

**なぜ作ったか（2026-08-26）**
ChatGPTの独立レビューで、表示中の操作要素158個に名前が無いと指摘された。
v10で0件にしたが、**入力欄を1つ足すだけで簡単に戻る。**
ブラウザを開かずに気づけるよう、静的に見る検査を置く。

**2026-08-28に検査を1つ足した：属性がタグの外に出ていないか**
同じ誤りを1つのセッションで2回した。
  1回目：サンプルボタン（v14で作り、外部レビューで指摘された）
  2回目：用語の `<summary>`（その指摘を直している最中に、同じ形で作った）
どちらも「開始タグを閉じる `>` のあとに aria-label を書いた」もので、
**属性が本文として画面に出る**（`aria-label="..."> このサンプルを読み込む`）。
原因は、置換のアンカーを**タグの途中の行**に取り、
その前の行で `>` が閉じられていることを確かめなかったこと。
★属性を足すときは、**開始タグ全体をアンカーにすること。**

**限界を先に書く**
これはソースを読む検査なので、**実際に表示されているかは分からない。**
**正確な判定は実ブラウザで行うこと**（全タブ・全折りたたみ・住宅ON/OFF・
パートナー有無・子ども有無・保存プラン0/1/複数件で0件、かつ
`label` の `for` を1つ外すと1件以上になること）。

★このスクリプトは「入れ忘れの早期発見」用で、実機監査の代わりにはならない。

使い方:
  python 03_scripts/check_a11y_names.py                    # 汎用版の最新
  python 03_scripts/check_a11y_names.py 02_output/xxx.html
"""
import io
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")


def pick_html():
    if len(sys.argv) > 1:
        p = Path(sys.argv[1])
        return p if p.is_absolute() else (ROOT / p)
    cands = [p for p in (ROOT / "02_output").glob("*_v*.html") if "汎用版" in p.name]
    if not cands:
        raise SystemExit("汎用版のHTMLが 02_output に見つかりません")

    def ver(p):
        m = re.search(r"_v(\d+)\.html$", p.name)
        return int(m.group(1)) if m else 0

    return max(cands, key=ver)


HTML = pick_html()
src = HTML.read_text(encoding="utf-8")

# `<input ...>` などの開始タグを1つずつ取り出す（属性が複数行にまたがる場合も拾う）
TAG = re.compile(r"<(input|select|textarea)\b((?:[^>\"']|\"[^\"]*\"|'[^']*')*?)>", re.S)

# 名前になりうるもの
HAS_ARIA = re.compile(r"aria-label\s*=", re.I)
HAS_LABELLEDBY = re.compile(r"aria-labelledby\s*=", re.I)
HAS_TITLE = re.compile(r"\btitle\s*=", re.I)
HAS_ID = re.compile(r"\bid\s*=\s*[\"']?\$?\{?([A-Za-z0-9_${}.+\-]*)", re.I)
# テンプレートで id を作っている場合（`id="${id}"` など）は label for も動的なので通す
DYN_ID = re.compile(r"id\s*=\s*\"\$\{")

print(f"操作要素の名前の検査（静的）: {HTML.name}")
print("=" * 78)

missing = []
total = 0
for m in TAG.finditer(src):
    tag, attrs = m.group(1), m.group(2)
    if re.search(r'type\s*=\s*["\']?(hidden|file)', attrs, re.I):
        continue
    total += 1
    if HAS_ARIA.search(attrs) or HAS_LABELLEDBY.search(attrs) or HAS_TITLE.search(attrs):
        continue
    if DYN_ID.search(attrs):
        continue          # id を動的に振っている＝label for とセットで作っている想定
    # `<label ...>` の内側なら、label そのものが名前になる。
    before = src[max(0, m.start() - 300):m.start()]
    if "<label" in before and before.rfind("<label") > before.rfind("</label>"):
        continue
    # コメント（/* ... */）の中の記述は数えない（説明文に例を書いていることがある）
    open_c = src.rfind("/*", 0, m.start())
    close_c = src.rfind("*/", 0, m.start())
    if open_c > close_c:
        continue
    idm = HAS_ID.search(attrs)
    if idm and idm.group(1):
        if f'for="{idm.group(1)}"' in src:
            continue
    line = src[:m.start()].count("\n") + 1
    missing.append((line, tag, attrs.strip().replace("\n", " ")[:74]))

print(f"\n調べた操作要素（ソース上）: {total}件")
if not missing:
    print("OK  名前になりうる指定が見つからないものはありません")
else:
    print(f"NG  名前が見つからないもの: {len(missing)}件\n")
    for line, tag, attrs in missing[:20]:
        print(f"  {line:>6}行  <{tag} {attrs}>")
    if len(missing) > 20:
        print(f"  ほか {len(missing)-20}件")


def check_attr_outside_tag(text):
    """属性が、開いているタグの外に書かれていないかを見る。

    直前の `<` と `>` を比べ、`>` の方が近ければタグの外にある＝
    **画面に文字として出てしまう。**
    """
    bad = []
    pat = re.compile(r"\b(aria-label|aria-labelledby|aria-current|onclick)\s*=")
    for m in pat.finditer(text):
        i = m.start()
        # コメント（/* ... */）の中の記述は数えない。
        # 説明として `aria-label="スライダー"` のように書いていることがある。
        open_c = text.rfind("/*", 0, i)
        close_c = text.rfind("*/", 0, i)
        if open_c > close_c:
            continue
        lt = text.rfind("<", 0, i)
        gt = text.rfind(">", 0, i)
        if gt > lt:
            line = text[:i].count("\n") + 1
            ctx = text[max(0, i - 60):i + 60].replace("\n", " ")
            bad.append((line, ctx))
    return bad


outside = check_attr_outside_tag(src)
print(f"\n属性がタグの外に出ているもの: {len(outside)}件")
if outside:
    print("NG  開始タグの `>` より後ろに属性があります（画面に文字として出ます）\n")
    for line, ctx in outside[:10]:
        print(f"  {line:>6}行  …{ctx}…")
    if len(outside) > 10:
        print(f"  ほか {len(outside)-10}件")
else:
    print("OK  すべての属性が開始タグの中にあります")

print("\n" + "=" * 78)
print("※ これはソースを読む検査です。実際に表示されているかは分かりません。")
print("   正確な判定は実ブラウザで、全タブ・全折りたたみ・住宅ON/OFF・")
print("   パートナー有無・子ども有無・保存プラン0/1/複数件の各状態で行ってください。")
print("   あわせて、label の for を1つ外すと1件以上になることを確かめてください。")
sys.exit(1 if (missing or outside) else 0)
