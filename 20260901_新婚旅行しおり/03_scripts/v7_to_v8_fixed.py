#!/usr/bin/env python3
"""v7_to_v8_fixed.py  ─  タブ再編成（修正版）"""
import re
from pathlib import Path

BASE   = Path(__file__).parent.parent / "02_output"
INPUT  = BASE / "20260901_新婚旅行しおり_v7.html"
OUTPUT = BASE / "20260901_新婚旅行しおり_v8.html"

html = INPUT.read_text(encoding="utf-8")
print(f"読み込み: {len(html):,} chars")

# 1. 3セクション抽出（末尾の余白をstrip）
sunset_pos = html.find("日没・日の出時刻カレンダー")
sec_start = html.rfind("\n      <div", 0, sunset_pos)
day1_pos = html.find("<!-- DAY 1 -->")
assert sec_start > 0 and day1_pos > 0
three = html[sec_start:day1_pos].rstrip()   # ← rstrip()で末尾余白を除去
html = html[:sec_start] + html[day1_pos:]
print(f"1. 抽出OK  末尾: {repr(three[-30:])}")

# 2. カレンダータブボタンを旅程表の直後に挿入
ITN_END = "route mr-1\"></i> 旅程表 (DAY 1-15)\n        </button>"
assert ITN_END in html
NEW_BTN = (
    "route mr-1\"></i> 旅程表 (DAY 1-15)\n        </button>\n"
    "        <button id=\"btn-tab-calendar\" onclick=\"switchTab('tab-calendar')\" "
    "class=\"nav-btn px-3 py-1.5 rounded-full whitespace-nowrap transition "
    "border border-slate-300 bg-white text-slate-700 shadow-xs hover:bg-amber-50\">\n"
    "          <i class=\"fa-solid fa-calendar-days mr-1\"></i> カレンダー&amp;計画\n"
    "        </button>"
)
html = html.replace(ITN_END, NEW_BTN, 1)
print("2. ボタン挿入OK")

# 3. カレンダータブセクションを tab-spots の直前（TAB2コメントの前）に挿入
#    anchor: TAB 2 コメントの直前に挿入する
TAB2_COMMENT = "<!-- ==================== TAB 2:"
assert TAB2_COMMENT in html, "TAB 2コメントが見つかりません"

CAL_SECTION = (
    "<!-- ==================== TAB: カレンダー&amp;計画 ==================== -->\n"
    "    <section id=\"tab-calendar\" class=\"tab-content space-y-4 pb-4\">\n"
    + three + "\n"
    "    </section>\n\n"
    "    "
    + TAB2_COMMENT
)
html = html.replace("    " + TAB2_COMMENT, CAL_SECTION, 1)
print("3. セクション挿入OK")

# 4. fa-language アイコン削除
FA = '<i class="fa-solid fa-language text-indigo-600 text-xl"></i>'
html = html.replace(FA, "", 1)
print("4. fa-language削除OK")

OUTPUT.write_text(html, encoding="utf-8")
size = OUTPUT.stat().st_size
print(f"\n=== 完了 ===  {OUTPUT.name}  {size/1024/1024:.2f} MB")
