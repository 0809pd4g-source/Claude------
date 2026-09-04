#!/usr/bin/env python3
"""
v7_to_v8_tab_reorganize.py

変更内容:
  1. 旅程タブから3セクション（日没カレンダー・記念日演出・出費テーブル）を抽出
  2. 新タブ「📅 カレンダー＆計画」を旅程表の右隣に新設し、3セクションを移動
  3. フレーズタブの fa-language デコアイコンを削除
"""

import re
from pathlib import Path

BASE   = Path(__file__).parent.parent / "02_output"
INPUT  = BASE / "20260901_新婚旅行しおり_v7.html"
OUTPUT = BASE / "20260901_新婚旅行しおり_v8.html"

html = INPUT.read_text(encoding="utf-8")
print(f"読み込み: {len(html):,} chars")

# ══════════════════════════════════════════════════════════
# 1. 旅程タブから3セクションを抽出
#    sec_start = 日没カレンダーdivの先頭
#    day1_pos  = <!-- DAY 1 --> の位置
# ══════════════════════════════════════════════════════════
sunset_pos = html.find("日没・日の出時刻カレンダー")
assert sunset_pos > 0, "日没カレンダーが見つかりません"

sec_start = html.rfind("\n      <div", 0, sunset_pos)
assert sec_start > 0, "sec_start が見つかりません"

day1_pos = html.find("<!-- DAY 1 -->")
assert day1_pos > 0, "<!-- DAY 1 --> が見つかりません"

three_sections = html[sec_start:day1_pos]
html = html[:sec_start] + html[day1_pos:]
print(f"1. 3セクション抽出 ({len(three_sections):,} chars) OK")

# ══════════════════════════════════════════════════════════
# 2. 新タブボタンを旅程表ボタンの直後に挿入
# ══════════════════════════════════════════════════════════
ITN_BTN_END = '旅程表 (DAY 1-15)\n        </button>'
assert ITN_BTN_END in html, "旅程表ボタン末尾が見つかりません"

NEW_BTN = ('旅程表 (DAY 1-15)\n        </button>\n'
           '        <button id="btn-tab-calendar" onclick="switchTab(\'tab-calendar\')" '
           'class="nav-btn px-3 py-1.5 rounded-full whitespace-nowrap transition '
           'border border-slate-300 bg-white text-slate-700 shadow-xs hover:bg-amber-50">\n'
           '          <i class="fa-solid fa-calendar-days mr-1"></i> カレンダー＆計画\n'
           '        </button>')
html = html.replace(ITN_BTN_END, NEW_BTN, 1)
print("2. カレンダータブボタン挿入 OK")

# ══════════════════════════════════════════════════════════
# 3. 新タブセクションをエリア・宿タブの直前に挿入
# ══════════════════════════════════════════════════════════
SPOTS_ANCHOR = '    <section id="tab-spots"'
assert SPOTS_ANCHOR in html, "tab-spots セクションが見つかりません"

CALENDAR_SECTION = (
    '    <!-- ==================== TAB: カレンダー＆計画 ==================== -->\n'
    '    <section id="tab-calendar" class="tab-section hidden space-y-4 pb-4">\n'
    + three_sections +
    '    </section>\n\n'
    '    '
)
html = html.replace(SPOTS_ANCHOR, CALENDAR_SECTION + SPOTS_ANCHOR, 1)
print("3. カレンダータブセクション挿入 OK")

# ══════════════════════════════════════════════════════════
# 4. フレーズタブの fa-language デコアイコン削除
# ══════════════════════════════════════════════════════════
n_removed = 0
html, n_removed = re.subn(
    r'\n\s*<i class="fa-solid fa-language[^"]*"[^>]*></i>',
    '',
    html,
    count=1
)
print(f"4. fa-language アイコン削除 (n={n_removed}) OK")

# ══════════════════════════════════════════════════════════
# 出力
# ══════════════════════════════════════════════════════════
OUTPUT.write_text(html, encoding="utf-8")
size = OUTPUT.stat().st_size
print(f"\n=== 完了 ===")
print(f"出力: {OUTPUT.name}")
print(f"サイズ: {size:,} bytes ({size/1024/1024:.2f} MB)")
