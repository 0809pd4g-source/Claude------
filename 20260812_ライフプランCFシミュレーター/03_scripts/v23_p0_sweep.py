# -*- coding: utf-8 -*-
r"""v23 patch B：P0-2（価格スイープが null・負数の借入を保存する）。

**何が起きていたか**

    const cur = p.house.loans.reduce((s,l)=>s+l.amount, 0);
    p.house.loans.forEach(l => { l.amount = Math.round(l.amount / cur * need / MAN) * MAN; });

`cur === 0`（いま借入が無い）だと `0/0 = NaN`。
`clone()` も保存もJSON経由なので、**NaN は例外にならず `null` になって永続化される。**

実測（購入・現在借入0円）: 7件すべて借入 `null`。
実測（自己資金が取得額を上回る）: −2,000万／−1,500万／−1,000万／−500万 の**負の借入**を保存。
実測（賃貸）: 画面は「7件作りました」、実際は**1件**（プラン名が同じで上書きされる）。

借入が `null` だと月返済0円・返済総額0円として計算され、最終資産を過大に見せる。

★**同じ処理の正しい版が、すでにこのファイルの中にあった。**
  `fitLoansOn(p)` は `cur <= 0` を見ている。`sweepPrice()` がそれを使っていなかっただけ。
  **「直し方が分からない」ではなく「既にあるものを使っていない」。着手前に既存を探す。**
  ただし `fitLoansOn` にも `need` の下限クランプが無いので、そちらも直す。

**直し方**
  1. `fitLoansOn(p)` に `need >= 0` のクランプと配列ガードを入れ、`fitLoans()` も共通化する
  2. `sweepPrice()` は `fitLoansOn()` を使う
  3. 購入しない／価格0なら作らずに入力へ誘導する
  4. **保存の直前に、候補の全数値が有限かを再帰で確かめる**（`commitPlans` の入口）
  5. 成功件数は「実際に増減した一意のプラン数」から出す
"""
import io
import sys
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
ROOT = Path(__file__).resolve().parent.parent
P = ROOT / "02_output" / "20260831_ライフプランCFシミュレーター汎用版_v23.html"
t = P.read_text(encoding="utf-8")
ng = []


def sub(old, new, label, count=1):
    global t
    c = t.count(old)
    if c == count:
        t = t.replace(old, new, count)
    else:
        ng.append(f"{label} ({c}件/期待{count})")


# ---- 1. fitLoansOn を安全にし、fitLoans を共通化する ----
sub('''function fitLoansOn(p){
  const H = p.house;
  const need = H.price + feeTotal(H) - H.selfFund - (H.gift || 0);
  const cur = H.loans.reduce((s, l) => s + l.amount, 0);
  if(cur <= 0){ if(H.loans[0]) H.loans[0].amount = need; }
  else H.loans.forEach(l => {
    l.amount = Math.round(l.amount / cur * need / 10000) * 10000; });
  return p;
}''',
    '''function fitLoansOn(p){
  const H = p.house;
  /* ★必要額は0未満にしない（自己資金が取得額を上回る場合）。
       v22までクランプが無く、価格を下げる方向へ振ると**負の借入**を作っていた
       （実測：−2,000万〜−500万円を保存）。 */
  const need = Math.max(0,
    Number(H.price || 0) + feeTotal(H) - Number(H.selfFund || 0) - Number(H.gift || 0));
  /* ★借入の配列が空・壊れている場合に1本用意する。 */
  if(!Array.isArray(H.loans) || !H.loans.length){
    H.loans = [{name:"あなた", amount:0, years:35, steps:[{y:1, rate:1}]}];
  }
  const cur = H.loans.reduce((s, l) => s + Math.max(0, Number(l.amount) || 0), 0);
  if(cur <= 0){
    /* ★いま借入が0のときに比率で割ると 0/0 = NaN になる。
         NaN はJSON経由で `null` になり、月返済0円として計算されてしまう。 */
    H.loans.forEach((l, i) => { l.amount = (i === 0) ? need : 0; });
  }else{
    H.loans.forEach(l => {
      const share = Math.max(0, Number(l.amount) || 0) / cur;
      l.amount = Math.max(0, Math.round(share * need / 10000) * 10000);
    });
  }
  return p;
}''',
    "fitLoansOn を安全にする")

sub('''function fitLoans(){
  const H = PARAMS.house;
  const need = H.price + feeTotal(H) - H.selfFund - (H.gift||0);
  const cur = H.loans.reduce((s,l)=>s+l.amount, 0);
  if(cur <= 0){ H.loans[0].amount = need; }
  else H.loans.forEach(l => { l.amount = Math.round(l.amount / cur * need / 10000) * 10000; });
  recalc();
}''',
    '''function fitLoans(){
  /* ★計算は `fitLoansOn()` に一本化する（同じ式を2か所に置かない）。
       v22までここだけクランプが無く、負の借入・NaN が作れた。 */
  fitLoansOn(PARAMS);
  recalc();
}''',
    "fitLoans を fitLoansOn に一本化")

# ---- 2. 保存の入口で、非有限値・負の借入を拒否する ----
sub('''function commitPlans(nextPlans){
  try{''',
    '''/** 保存する候補に、計算を壊す値が混ざっていないかを見る。
 *
 *  ★`NaN` は `JSON.stringify` で `null` になり、例外も出ずに保存される。
 *    そのあと `Number(null) === 0` なので、**月返済0円として静かに計算される**。
 *    「保存できた」と「保存した中身が使える」は別（v22のP0-2）。
 *  戻り値は問題のあったパスの配列（空なら健全）。 */
function badNumbersIn(obj, path, out){
  out = out || []; path = path || "";
  if(obj === null || obj === undefined) return out;
  if(typeof obj === "number"){
    if(!Number.isFinite(obj)) out.push(path + " = " + String(obj));
    return out;
  }
  if(Array.isArray(obj)){
    obj.forEach((v, i) => badNumbersIn(v, path + "[" + i + "]", out));
    return out;
  }
  if(typeof obj === "object"){
    Object.keys(obj).forEach(k => badNumbersIn(obj[k], path ? path + "." + k : k, out));
  }
  return out;
}
/** 借入額が負になっていないか（負の借入は「返済がマイナス＝収入」になってしまう）。 */
function badLoansIn(plans){
  const out = [];
  (plans || []).forEach(p => {
    const loans = (p.params && p.params.house && p.params.house.loans) || [];
    loans.forEach((l, i) => {
      const v = l && l.amount;
      if(typeof v !== "number" || !Number.isFinite(v) || v < 0)
        out.push(`${p.name} の借入${i+1} = ${String(v)}`);
    });
  });
  return out;
}
function commitPlans(nextPlans){
  /* ★保存の直前に1回だけ検査する。ここを通らない保存経路を作らない。 */
  const bad = badNumbersIn(nextPlans, "plans").concat(badLoansIn(nextPlans));
  if(bad.length){
    pushNotice("badplan", "bad",
      `<b>計算できない値が混じっていたため、保存しませんでした。</b>`
      + `<span class="hint">（${esc(bad.slice(0,3).join(" / "))}`
      + `${bad.length > 3 ? ` ほか ${bad.length-3}件` : ""}）<br>`
      + `物件価格・自己資金・借入の設定を確かめてください。</span>`);
    return false;
  }
  try{''',
    "commitPlans に数値の健全性検査を足す")

# ---- 3. sweepPrice を作り直す ----
sub('''  const names = [];
  let next = PLANS;
  list.forEach((manPrice, i) => {
    const p = clone(PARAMS);
    p.house.price = manPrice * MAN;
    // 自己資金は据え置き、必要借入額を持分比で割り振る
    const need = p.house.price + p.house.fees - p.house.selfFund;
    const cur = p.house.loans.reduce((s,l)=>s+l.amount, 0);
    p.house.loans.forEach(l => { l.amount = Math.round(l.amount / cur * need / MAN) * MAN; });
    p.meta.planName = autoPlanName(p);''',
    '''  const names = [];
  let next = PLANS;
  list.forEach((manPrice, i) => {
    const p = clone(PARAMS);
    p.house.price = manPrice * MAN;
    /* ★自己資金は据え置き、必要借入額を持分比で割り振る。
         v22まではここで直接割り算しており、いま借入が0だと 0/0 = NaN、
         自己資金が取得額を上回ると負数になっていた（P0-2）。
         同じ計算の安全な版が `fitLoansOn()` にあるので、それを使う。 */
    fitLoansOn(p);
    p.meta.planName = autoPlanName(p);''',
    "sweepPrice の按分を fitLoansOn に置き換える")

sub('''    next = withPlanIn(next, p, p.meta.planName);
    names.push(p.meta.planName);
  });
  if(!commitPlans(next)) return;
  setTab("compare");
  flash(`<b>物件価格を振った ${names.length}件 を作りました。</b>すぐ下の表に並んでいます。<br>`''',
    '''    next = withPlanIn(next, p, p.meta.planName);
    if(names.indexOf(p.meta.planName) < 0) names.push(p.meta.planName);
  });
  /* ★件数は「実際にできた一意のプラン数」から出す。
       v22までは振った価格の数（7）を表示していたが、賃貸などプラン名に価格が
       入らない場合は同名で上書きされ、**画面7件・実体1件**になっていた。 */
  const beforeCount = PLANS.length;
  if(!commitPlans(next)) return;
  const added = PLANS.length - beforeCount;
  setTab("compare");
  flash(`<b>物件価格を振った ${names.length}件 を作りました`
    + `${added !== names.length ? `（うち新規 ${added}件・同名は上書き）` : ""}。</b>`
    + `すぐ下の表に並んでいます。<br>`''',
    "sweepPrice の件数を実体から出す")

# ---- 4. 購入しない／価格0なら作らない ----
sub('''function sweepPrice(){
  const base = PARAMS.house.price;''',
    '''function sweepPrice(){
  /* ★購入しない設定・価格未入力では、価格を振っても意味がない。
       v22までは実行でき、賃貸のまま「7件作りました」と出て実体1件だった（P0-2）。 */
  if(!PARAMS.house.buy || !(PARAMS.house.price > 0)){
    setTab("compare");
    flash(`<b>物件価格を振るには、購入する設定と物件価格が必要です。</b><br>`
      + `<span class="hint">「住宅とローン」のページで「住宅を購入する」を選び、`
      + `物件価格を入れてから、もう一度押してください。</span>`);
    return;
  }
  const base = PARAMS.house.price;''',
    "sweepPrice の前提チェック")

if ng:
    print("NG:", " / ".join(ng))
    sys.exit(1)
P.write_text(t, encoding="utf-8")
print("OK v23 patch B（価格スイープの null・負数・件数不一致）")
