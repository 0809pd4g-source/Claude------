# -*- coding: utf-8 -*-
r"""v28 P1-4／P1-5／P1-6。

**P1-4｜物価上昇率が0%のとき、家賃の上昇率で「自分で年率を入れる」が選べない。**
  モードを値から引く設計（v27）は正しいが、`custom` を選んだときの初期値を
  「いまの物価上昇率」にしていたため、**物価が0%だと値が0になり、
  読み戻したモードが「上がらない」に戻る**（実測：値0／モード flat）。
  入力欄が一度も出ないので、**年率を入れる方法が無い。**
  → `custom` の初期値は「物価上昇率、ただし0なら1.0%」にする。
  あわせて `house.rentGrowth` に範囲を持たせる（−200%が入り、家賃がマイナスになった）。

**P1-5｜購入する世帯は、セットアップを一周しても最終段階に届かない。**
  実測：住まいで「これから購入」を選び、見えている欄をすべて埋めても
  **9/10・足りない「いまの住居費」**（段階1）。購入分岐に家賃の欄が無いため。
  `checkWizardCoverage()` は `covers` の一覧を突き合わせるだけなので**0件**を返す。

  ★これは、こちらがV76・V78へ指摘したのと**同じ欠陥**。
    「案内どおりに操作して最終段階に到達するか」を、自分では機械で測っていなかった。

  直し方は2つ。
  1. **準備度を分岐で条件付ける**（`need` に `applies(P)` を持たせる）。
     すでに持ち家なら取得前の家賃は要らない。購入するなら物件価格と返済期間が要る。
  2. **網羅の検査を、分岐ごとに実際へ描画して確かめる**（ChatGPT版V78から取り込み）。
     `covers` の突き合わせだけでは、**宣言した欄を置き忘れても通ってしまう。**

**P1-6｜借入額があるのに返済期間0年を入れられる。**
  実測：借入3,000万円・返済期間0年で毎月返済0円。**払わずに家が買えることになる。**
"""
import io
import sys
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
ROOT = Path(__file__).resolve().parent.parent
P = ROOT / "02_output" / "20260901_ライフプランCFシミュレーター汎用版_v28.html"
t = P.read_text(encoding="utf-8")
ng = []


def sub(old, new, label, count=1):
    global t
    c = t.count(old)
    if c == count:
        t = t.replace(old, new, count)
    else:
        ng.append(f"{label} ({c}件/期待{count})")


# ============================================================
# P1-4  custom の初期値と、家賃上昇率の範囲
# ============================================================
sub('''    /* 「自分で入れる」を選んだ直後の初期値は、いまの物価上昇率
       （それまでの計算と同じ結果から始まるので、変えた影響が読みやすい）。 */
    const g = P.house.rentGrowth;
    P.house.rentGrowth = (g === null || g === undefined || Number(g) === 0)
      ? Number(P.econ.inflation) || 0 : Number(g);''',
    '''    /* 「自分で入れる」を選んだ直後の初期値は、いまの物価上昇率。
       ★ただし**0にしてはいけない**。0は「上がらない」と同じ値なので、
         モードを値から引く設計では**選んだ瞬間に「上がらない」へ戻り、
         入力欄が一度も出ない**（物価上昇率0%の世帯で実測）。
         物価が0%のときは1.0%から始める（値はすぐ変えられる）。 */
    const g = P.house.rentGrowth;
    const seed = Number(P.econ.inflation) || 0;
    P.house.rentGrowth = (g === null || g === undefined || Number(g) === 0)
      ? (seed !== 0 ? seed : 1.0) : Number(g);''',
    "custom の初期値が0にならないようにする")

# ============================================================
# P1-6  借入額があるのに返済期間0年を許さない
# ============================================================
sub('''             Object.assign({label:`${i+1}本目のローンの${key === "years" ? "返済期間（年）" : key}`},
                           key === "years" ? SPEC.span : {}))) return;''',
    '''             Object.assign({label:`${i+1}本目のローンの${key === "years" ? "返済期間（年）" : key}`},
                           key === "years" ? SPEC.loanYears : {}))) return;''',
    "返済期間に専用の範囲")

sub('''  monthly:  {man:true, min:0,    max:1000000},     // 毎月の積立（万円入力・上限100億円）
};''',
    '''  monthly:  {man:true, min:0,    max:1000000},     // 毎月の積立（万円入力・上限100億円）
  /* ★返済期間は1年以上。0年だと**借りたのに毎月返済0円**になる（実測で確認）。 */
  loanYears:{min:1,    max:100},
};''',
    "SPEC.loanYears を追加")

sub('''      if(typeof v !== "number" || !Number.isFinite(v) || v < 0)
        out.push(`${p.name} の借入${i+1} = ${String(v)}`);''',
    '''      if(typeof v !== "number" || !Number.isFinite(v) || v < 0)
        out.push(`${p.name} の借入${i+1} = ${String(v)}`);
      /* ★借入額があるのに返済期間0年のプランを保存しない。
           毎月返済0円・残高0円という**あり得ない結論**が比較や診断に出てしまう。
           古い保存データから来ることもあるので、保存の入口でも見る。 */
      else if(v > 0 && !(Number(l.years) >= 1))
        out.push(`${p.name} の借入${i+1} の返済期間が ${String(l && l.years)} 年`);''',
    "badLoansIn に返済期間の検査")

# ============================================================
# P1-5  準備度を分岐で条件付ける
# ============================================================
sub('''   need:[["econ.deposit","いまの預金"], ["house.rentNow","いまの住居費"],
         ["living.insurance","年間の保険料"], ["saving.nisaMonthlyH","毎月の積立"],
         ["retire.retireAgeH","リタイアする年齢"]]},''',
    '''   /* ★3つ目の要素は「その世帯に当てはまるか」。**当てはまらない項目を要求しない。**
        v27は住まいによらず `house.rentNow` を要求していたため、
        購入する世帯はセットアップを一周しても **9/10・足りない「いまの住居費」**で止まった
        （購入の分岐に家賃の欄が無い）。逆に、すでに持ち家なら取得前の家賃は要らない。 */
   need:[["econ.deposit","いまの預金"],
         ["house.rentNow","いまの住居費", P => housingOf(P) !== "own"],
         ["house.price","物件価格", P => housingOf(P) === "buy"],
         ["house.loans.0.years","返済期間", P => housingOf(P) === "buy"],
         ["living.insurance","年間の保険料"], ["saving.nisaMonthlyH","毎月の積立"],
         ["retire.retireAgeH","リタイアする年齢"]]},''',
    "READY_STEPS を分岐で条件付ける")

sub('''function readiness(){
  const out = {stage:0, label:"入力を始めてください", note:"", missing:[], done:0, total:0};
  let allPrev = true;
  READY_STEPS.forEach((s, i) => {
    const miss = s.need.filter(n => !isConfirmed(n[0])).map(n => n[1]);''',
    '''/** その世帯に当てはまる必要項目だけを返す。 */
function needsOf(step, P){
  return (step.need || []).filter(n => !n[2] || n[2](P || PARAMS));
}
function readiness(){
  const out = {stage:0, label:"入力を始めてください", note:"", missing:[], done:0, total:0};
  let allPrev = true;
  READY_STEPS.forEach((s, i) => {
    const need = needsOf(s, PARAMS);
    const miss = need.filter(n => !isConfirmed(n[0])).map(n => n[1]);''',
    "readiness が分岐を見る")

sub('''    out.total += s.need.length;
    out.done  += s.need.length - miss.length;''',
    '''    out.total += need.length;
    out.done  += need.length - miss.length;''',
    "readiness の集計")

if ng:
    print("NG:", " / ".join(ng))
    sys.exit(1)
P.write_text(t, encoding="utf-8")
print("OK v28 P1-4／P1-5（準備度の条件付け）／P1-6")
