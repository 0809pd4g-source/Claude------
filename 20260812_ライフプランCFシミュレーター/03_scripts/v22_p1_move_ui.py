# -*- coding: utf-8 -*-
r"""v22 patch F：画面側の関数を、境界（`/* 状態 */`）より後ろへ移す。

**なぜ**
外部レビューの指摘は「`defaults` が `insGuideTable` を呼ぶ」の1件だったが、
新しく作った `03_scripts/check_engine_boundary.py` で洗ったところ、
**表示の切替まわりが丸ごとエンジン側（境界の手前）に置かれていた。**

  cfOneYear / toggleCfOneYear / cfSetYear / cfStepYear
  eduOneYear / toggleEduOneYear / eduSetYear / eduStepYear / eduYearRows
  isNarrowScreen / realFactor / disp / viewLabel / toggleFold / toggleView
  toggleMonthly / periodLabel / socialInsWarning

これらは `render()`・`document`・`localStorage`・`matchMedia` を触るのに、
**検証スクリプトが「エンジン」として切り出す範囲に入っていた。**
（レビューが言う「行番号の境界だけでは足りない」がまさにこれ。）

★関数宣言は巻き上げられるので、**動きは変わらない。**
  変わるのは「検証スクリプトがエンジンとして切り出す範囲」。
  そこにUIが混ざっていると、境界の検査が意味を持たない。

**注意**：`let CF_ONEYEAR` などは巻き上げられない。
移動先が「状態」の直後なので、これらを読むのは関数の中だけ＝実行時には初期化済み。
"""
import io
import re
import sys
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
ROOT = Path(__file__).resolve().parent.parent
P = ROOT / "02_output" / "20260831_ライフプランCFシミュレーター汎用版_v22.html"
t = P.read_text(encoding="utf-8")
ng = []

lines = t.split("\n")


def block(first_marker, last_marker):
    """`first_marker` で始まる行から `last_marker` の行までを切り出す。"""
    a = b = None
    for i, ln in enumerate(lines):
        if a is None and ln.startswith(first_marker):
            a = i
        elif a is not None and ln.startswith(last_marker):
            b = i
            break
    if a is None or b is None:
        ng.append(f"ブロックが見つかりません: {first_marker[:30]!r}")
        return None
    return a, b


# 1) 表示の切替ブロック（CF表の1年表示〜年額/月額の切替）
r1 = block("/* ---- キャッシュフロー表の見せ方（スマホ対応） ----",
           "const periodLabel = ")
# 2) 社会保険の警告（HTMLを返す＝画面側）
r2 = block("function socialInsWarning(){", "}")

if ng:
    print("NG:", " / ".join(ng))
    sys.exit(1)

# socialInsWarning は最初の "}" で終わる行を探すと早すぎるので、閉じかっこを数える
a2 = r2[0]
depth, b2 = 0, None
for i in range(a2, len(lines)):
    depth += lines[i].count("{") - lines[i].count("}")
    if depth == 0 and i > a2:
        b2 = i
        break
if b2 is None:
    print("NG: socialInsWarning の終わりが見つかりません")
    sys.exit(1)

moved = []
# 後ろから取り除く（行番号がずれないように）
for a, b in sorted([r1, (a2, b2)], reverse=True):
    moved.insert(0, "\n".join(lines[a:b+1]))
    del lines[a:b+1]

t = "\n".join(lines)

MARK = """/* ============================================================
   状態
   ============================================================ */"""
if t.count(MARK) != 1:
    print(f"NG: `状態` の区切りが {t.count(MARK)}件（期待1）")
    sys.exit(1)

NOTE = """
/* ============================================================
   画面の見せ方の切替（v22でここへ移した）

   ★もともと境界（上の「状態」）より**手前**に置かれていた。
     検証スクリプトは境界の手前を「計算エンジン」として切り出して動かすため、
     `render()`・`document`・`localStorage`・`matchMedia` を触るこれらが
     エンジンに混ざっていた。**境界の検査が意味を持たない状態。**
   ★関数宣言は巻き上げられるので、動きは変わらない。
     変わるのは「どこまでをエンジンと見なすか」だけ。
   ★検査は `03_scripts/check_engine_boundary.py`。
   ============================================================ */
"""
t = t.replace(MARK, MARK + NOTE + "\n" + "\n\n".join(moved) + "\n", 1)

P.write_text(t, encoding="utf-8")
print(f"OK v22 patch F（画面側の {len(moved)} ブロックを境界の後ろへ移した）")
