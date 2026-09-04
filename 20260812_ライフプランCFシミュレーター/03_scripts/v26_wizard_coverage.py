# -*- coding: utf-8 -*-
r"""v26：ChatGPT版V76の査読から取り込む2点。

**取り込み1｜案内が「準備完了に必要な項目」を網羅する**

V76に「ガイドの3ステップどおりに入れても4段階目に到達しない」と指摘したので、
**同じ物差しを自分に当てた。結果はこちらのほうが重かった。**

実測（セットアップの6ステップの入力欄をすべて埋めた状態）:

    到達した段階 : 1「概算を表示できます」   ← 最終段階は3
    進捗         : 6/10
    足りない     : 毎月の積立・リタイアする年齢（段階2用）
                   物価上昇率・運用利回り（段階3用）

**セットアップはこの4項目を一度も聞かない。**
V76は段階2まで進めて3が足りない状態だったが、**こちらは段階1で止まる。**

直し方（`READY_STEPS` が要求する項目を、セットアップが必ず聞く）:
  - 「収入」ステップに **リタイアする年齢** を足す（収入がいつまで続くかの話なので同じ画面が自然）
  - 「いまの資産」ステップに **毎月の積立** を足す（資産形成の話なので同じ画面）
  - **「長期前提」ステップを新設**（物価上昇率・運用利回り）

★これで「セットアップを一周すれば段階3に届く」が成立する。
  網羅しているかは `readiness()` の必要パスと突き合わせて**機械で確かめる**
  （人が並べ直すと、また抜ける）。

**取り込み2｜入力と確認を明示的に区別する（V76の良い工夫）**

V76はステップ3に「確認画面」とラベルし、「上部メニュー『診断』で見る」と書いていた。
**「入力が終わらないと結果が見られない」という誤解を避けられている。**
こちらのセットアップは全ステップが入力欄で、最後のボタンが「結果を見る →」だけだった。

  - `WIZ_STEPS` に `kind:"input" | "view"` を持たせる
  - ステップの見出しと丸ボタンに「入力」「確認」を出す
  - 最後に **入力欄のない「診断」ステップ**を置き、そこが確認画面だと明示する
"""
import io
import sys
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
ROOT = Path(__file__).resolve().parent.parent
P = ROOT / "02_output" / "20260831_ライフプランCFシミュレーター汎用版_v26.html"
t = P.read_text(encoding="utf-8")
ng = []


def sub(old, new, label, count=1):
    global t
    c = t.count(old)
    if c == count:
        t = t.replace(old, new, count)
    else:
        ng.append(f"{label} ({c}件/期待{count})")


# ---- 1. ステップの定義に「入力／確認」と、網羅すべき項目を持たせる ----
sub('''const WIZ_STEPS = [
  {t:"世帯",       n:"どなたと暮らしていますか"},
  {t:"収入",       n:"いまの年収はいくらですか"},
  {t:"いまの資産", n:"貯蓄と運用はいくらありますか"},
  {t:"住まい",     n:"住まいはどうしますか"},
  {t:"支出",       n:"毎年の生活費はいくらですか"},
  {t:"心配ごと",   n:"何が気になっていますか"},
];''',
    '''/** セットアップのステップ。
 *
 *  ★`kind` で**入力する画面と、見るだけの画面**を分ける（ChatGPT版V76から取り込み）。
 *    V76はガイドの3つ目に「確認画面」とラベルし、「上部メニュー『診断』で見る」と書いていた。
 *    **「入力が終わらないと結果が見られない」という誤解を避けられている。**
 *    こちらは全ステップが入力欄で、最後のボタンが「結果を見る →」だけだった。
 *
 *  ★`covers` は、そのステップで**必ず聞く** `READY_STEPS` の必要パス。
 *    v25まで、セットアップは「毎月の積立」「リタイアする年齢」「物価上昇率」「運用利回り」を
 *    **一度も聞かなかった**。6ステップ全部を埋めても段階1（概算）で止まっていた（進捗6/10）。
 *    **案内どおりに進めて最終段階へ到達しないなら、案内が足りていない。**
 *    網羅は `checkWizardCoverage()` が機械で確かめる（人が並べ直すとまた抜ける）。 */
const WIZ_STEPS = [
  {t:"世帯",       n:"どなたと暮らしていますか",       kind:"input",
   covers:["family.ageH"]},
  {t:"収入",       n:"いまの年収と、いつまで働くか",   kind:"input",
   covers:["income.hBase", "retire.retireAgeH"]},
  {t:"いまの資産", n:"貯蓄・運用と、毎月の積立",       kind:"input",
   covers:["econ.deposit", "saving.nisaMonthlyH"]},
  {t:"住まい",     n:"住まいはどうしますか",           kind:"input",
   covers:["house.rentNow"]},
  {t:"支出",       n:"毎年の生活費と保険料",           kind:"input",
   covers:["living.table.0.amount", "living.insurance"]},
  {t:"長期前提",   n:"物価と運用をどう見ますか",       kind:"input",
   covers:["econ.inflation", "econ.investRate"]},
  {t:"心配ごと",   n:"何が気になっていますか",         kind:"input", covers:[]},
  {t:"診断",       n:"結果を見ます（ここに入力欄はありません）", kind:"view", covers:[]},
];

/** セットアップが `READY_STEPS` の必要項目を網羅しているか。
 *  **足りない項目を返す**（空なら網羅）。「計算の前提」ページの自己診断から呼ぶ。 */
function checkWizardCoverage(){
  const need = [];
  READY_STEPS.forEach(s => s.need.forEach(n => need.push({path:n[0], label:n[1]})));
  const covered = new Set();
  WIZ_STEPS.forEach(s => (s.covers || []).forEach(p => covered.add(p)));
  return need.filter(n => !covered.has(n.path));
}''',
    "WIZ_STEPS に kind と covers を持たせる")

# ---- 2. 収入ステップにリタイア年齢 ----
sub('''  if(i === 1){
    const selfH = workTypeOf(P, "h") === "self";
    return workTypeBox()
      + '<h3>いまの収入</h3>''',
    '''  if(i === 1){
    const selfH = workTypeOf(P, "h") === "self";
    return workTypeBox()
      + '<h3>いまの収入</h3>''',
    "収入ステップの先頭（変更なし・位置確認）")

# ---- 3. 新しいステップ本体（長期前提・診断）と、収入・資産への追加 ----
sub('''  if(i === 2){
    return '<div class="hint" style="margin-bottom:9px">'
      + '<b>いま持っているお金</b>を入れてください。''',
    '''  if(i === 2){
    return '<div class="hint" style="margin-bottom:9px">'
      + '<b>いま持っているお金</b>を入れてください。''',
    "資産ステップの先頭（位置確認）")

if ng:
    print("NG:", " / ".join(ng))
    sys.exit(1)
P.write_text(t, encoding="utf-8")
print("OK v26 patch 1（ステップ定義と網羅チェック）")
