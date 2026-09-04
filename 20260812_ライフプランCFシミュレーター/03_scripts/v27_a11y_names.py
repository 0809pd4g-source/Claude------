# -*- coding: utf-8 -*-
r"""v27：同じ画面に同じ名前のボタンが並ぶのを直す。

★ChatGPT版V78を査読する過程で、同じ物差しを自分に当てて見つけた（査読の還流8回目）。

  セットアップの8ステップを1つずつ測ったところ、**名前なしは0件**だったが、
  **同じ画面に同じ名前のボタン**があった：

    ステップ7（気になること）: 「選んでいます」×2
    ステップ8（診断）        : 「このページを開く」×4

  どちらも**v26で自分が足した**もの。読み上げでは
  「このページを開く」が4回続き、**どれがどのページなのか分からない**。
  CLAUDE.mdに「名前があると、名前が役に立つは別」「同一画面での同名を測る」と
  書いておきながら、**新しく足したカードで同じことをした。**

  ボタンの本文は短いままにして、`aria-label` で行き先・対象を名乗らせる。
"""
import io
import sys
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
ROOT = Path(__file__).resolve().parent.parent
P = ROOT / "02_output" / "20260831_ライフプランCFシミュレーター汎用版_v27.html"
t = P.read_text(encoding="utf-8")
ng = []


def sub(old, new, label, count=1):
    global t
    c = t.count(old)
    if c == count:
        t = t.replace(old, new, count)
    else:
        ng.append(f"{label} ({c}件/期待{count})")


# ---- 診断ステップの3枚のカード（+ 使い方の1枚）が同じ名前だった ----
sub('''            + '<button class="btn sm" style="margin-top:8px" onclick="endWizard(false); setTab('
            + jsAttr(x[0]) + ')">このページを開く</button>' ''' .rstrip(),
    '''            /* ★行き先をボタンの名前に入れる。本文は短いままで、読み上げだけ足す。
                 v26は4つとも「このページを開く」で、**読み上げでは区別できなかった**。 */
            + '<button class="btn sm" style="margin-top:8px"'
            + ' aria-label="' + esc(x[1] + "のページを開く") + '"'
            + ' onclick="endWizard(false); setTab('
            + jsAttr(x[0]) + ')">このページを開く</button>' ''' .rstrip(),
    "診断ステップのカードのボタン")

sub('''         <button class="btn" onclick="setTab('check')">このページを開く</button>`)}''',
    '''         <button class="btn" aria-label="「あなたの心配に答える」のページを開く"
           onclick="setTab('check')">このページを開く</button>`)}''',
    "使い方のボタン")

# ---- 心配ごとの選択ボタン（セットアップ側と本体側の2か所） ----
sub('''          + '<button class="btn' + (on ? "" : " sec") + ' sm" style="margin-top:8px"'
          + ' onclick="toggleConcern(' + jsAttr(k) + ')">'
          + (on ? "選んでいます" : "これを選ぶ") + '</button>' ''' .rstrip(),
    '''          /* ★どの心配ごとのボタンなのかを名前に入れる。
               v26は選んだ項目が2つ以上あると「選んでいます」が並び、
               **読み上げではどれを外すのか分からなかった。** */
          + '<button class="btn' + (on ? "" : " sec") + ' sm" style="margin-top:8px"'
          + ' aria-label="' + esc(CONCERNS[k].q + (on ? "：選択を外す" : "：これを選ぶ")) + '"'
          + ' onclick="toggleConcern(' + jsAttr(k) + ')">'
          + (on ? "選んでいます" : "これを選ぶ") + '</button>' ''' .rstrip(),
    "セットアップの心配ごとボタン")

sub('''              <button class="btn${on ? "" : " sec"} sm" style="margin-top:8px"
                onclick="toggleConcern(${jsAttr(k)})">${on ? "選んでいます" : "これを選ぶ"}</button>''',
    '''              <button class="btn${on ? "" : " sec"} sm" style="margin-top:8px"
                aria-label="${esc(CONCERNS[k].q + (on ? "：選択を外す" : "：これを選ぶ"))}"
                onclick="toggleConcern(${jsAttr(k)})">${on ? "選んでいます" : "これを選ぶ"}</button>''',
    "本体の心配ごとボタン")

if ng:
    print("NG:", " / ".join(ng))
    sys.exit(1)
P.write_text(t, encoding="utf-8")
print("OK v27（同一画面の同名ボタンに行き先・対象の名前を付ける）")
