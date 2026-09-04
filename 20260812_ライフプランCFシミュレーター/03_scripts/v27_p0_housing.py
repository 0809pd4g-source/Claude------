# -*- coding: utf-8 -*-
r"""v27 P0-1／P1-1：住宅資金の計算を1本にし、無効な融資手数料率を入口で止める。

ChatGPT版の v25 独立再レビューで指摘され、**現物で再現を確認した**：

  - `maybeAutoFit()` が閉じた式を使わず、`need = price + feeTotal - selfFund - gift`
    のままだった。詳細諸費用では融資手数料が借入額に比例するため、
    この式は**借入が足りない額を返す**（実測 950,312円不足）。
    さらに `Math.round(l.amount/cur*need/10000)*10000` で万円丸めしており、
    複数本の借入では丸め残差も残る。
  - 自動連動のトリガー `FUND_PATHS` が price/fees/selfFund/gift の4つだけ。
    **手数料率・登記費用などを変えても借入が合わせ直されない**（実測 485,845円不足）。
  - `priceBreakEven()` が独自の「費用率固定＋借入按分」式を持っており、
    物件価格上限を **53〜71万円 高く**表示していた。

  ★同じ数値を出す経路を2本置くと、片方だけ直る。v24で `requiredLoanTotal()` を
    入れたときに `fitLoansOn()` だけを直し、**残る2経路を見落とした**。

  - `requiredLoanTotal()` は料率100%以上のとき分子をそのまま返して**続行**していた。
    コメント自身が「入力の誤りとして扱う」と書いているのに、成功経路を通す。
    実測：料率100%で 43,196,000円不足のプランが保存できた。
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


# ============================================================
# 1. 自動連動を閉じた式へ一本化し、トリガーに諸費用の全項目を入れる
# ============================================================
sub('''/* 物件価格・諸費用・自己資金・贈与を変えたら、借入額を必要額に合わせ直す。
   合わせないと「頭金を増やしたのに毎月の返済が変わらない」という不整合が起きる。 */
const FUND_PATHS = ["house.price","house.fees","house.selfFund","house.gift"];
function maybeAutoFit(path){
  if(!PARAMS.house.autoFitLoans) return;
  if(!FUND_PATHS.includes(path)) return;
  if(!PARAMS.house.buy) return;
  const H = PARAMS.house;
  const need = H.price + feeTotal(H) - H.selfFund - (H.gift||0);
  const cur = H.loans.reduce((s,l)=>s+l.amount, 0);
  if(cur <= 0){
    if(H.loans[0]) H.loans[0].amount = Math.max(0, need);
  }else{
    H.loans.forEach(l => {
      l.amount = Math.max(0, Math.round(l.amount / cur * need / 10000) * 10000);
    });
  }
}''',
    '''/* 物件価格・諸費用・自己資金・贈与を変えたら、借入額を必要額に合わせ直す。
   合わせないと「頭金を増やしたのに毎月の返済が変わらない」という不整合が起きる。

   ★**取得費に効く入力はすべてここに並べる。**
     v26までは price/fees/selfFund/gift の4つだけだった。詳細諸費用にすると
     融資手数料率・登記費用・仲介手数料なども取得費を動かすのに、
     変えても借入が合わせ直されず**資金が足りないまま**になっていた
     （実測：手数料率2.2%→3.3%で485,845円不足／登記費用+130万円で1,300,000円不足）。
     並べ忘れを防ぐため、`feeBreakdown()` が読む項目と対応させて書く。 */
const FUND_PATHS = [
  "house.price", "house.fees", "house.selfFund", "house.gift",
  /* 諸費用の求め方そのもの（合計を入れる／内訳から積み上げる） */
  "house.feeMode",
  /* 内訳から積み上げるときの各項目（`feeBreakdown()` と同じ並び） */
  "house.feeBrokerageAuto", "house.feeBrokerage", "house.feeRegistration",
  "house.feeAcquisitionTax", "house.feeStamp", "house.feeLoanRate",
  "house.feeLoanFixed", "house.feeInsurance", "house.feeSettlement",
  "house.feeOther",
];
function maybeAutoFit(path){
  if(!PARAMS.house.autoFitLoans) return;
  if(!FUND_PATHS.includes(path)) return;
  if(!PARAMS.house.buy) return;
  /* ★計算は `fitLoansOn()`（＝`requiredLoanTotal()`）だけを使う。
       v26までここに独自の式を持っており、**融資手数料が借入額に比例する分を
       無視していた**ため、価格を変えるたびに資金が足りなくなっていた
       （実測：借入0円から5,000万円の物件へ変更で950,312円不足）。
       同じ数値を出す式を2本置くと、必ず片方だけが直る。 */
  fitLoansOn(PARAMS);
}''',
    "maybeAutoFit を閉じた式へ一本化")

# 諸費用の求め方（select）は onTxt を通るので、そこでも連動させる
sub('''function onTxt(path, v){ set(PARAMS, path, v); recalc(); }''',
    '''function onTxt(path, v){
  set(PARAMS, path, v);
  /* ★文字の選択でも取得費が動く（諸費用の求め方＝simple/detail）。
       v26は数値の入口だけで連動させており、求め方を切り替えると資金がずれた。 */
  markEntered(path); maybeAutoFit(path); recalc();
}''',
    "onTxt でも自動連動")

sub('''function onChk(path, v){
  set(PARAMS, path, v);
  // 子育て世帯の上乗せを切り替えたら借入限度額を入れ替える
  if(path === "house.ldKidsBonus") setLdHousingType(PARAMS, PARAMS.house.ldHousingType);
  // 自動連動をオンにした瞬間に、いまの資金差額を解消する
  if(path === "house.autoFitLoans" && v) maybeAutoFit("house.price");
  recalc();
}''',
    '''function onChk(path, v){
  set(PARAMS, path, v);
  // 子育て世帯の上乗せを切り替えたら借入限度額を入れ替える
  if(path === "house.ldKidsBonus") setLdHousingType(PARAMS, PARAMS.house.ldHousingType);
  // 自動連動をオンにした瞬間に、いまの資金差額を解消する
  if(path === "house.autoFitLoans" && v) maybeAutoFit("house.price");
  /* ★仲介手数料の自動計算のON/OFFも取得費を動かす。 */
  else maybeAutoFit(path);
  recalc();
}''',
    "onChk でも自動連動")

# ============================================================
# 2. 物件価格上限も同じ閉じた式を通す
# ============================================================
sub('''function priceBreakEven(P, ok){
  const feeRate = P.house.price > 0 ? feeTotal(P.house) / P.house.price : 0.06;
  const ratio = P.house.loans.map(l => {
    const t = P.house.loans.reduce((s,x)=>s+x.amount, 0);
    return t > 0 ? l.amount / t : 1 / P.house.loans.length;
  });
  const build = price => {
    const p = clone(P);
    p.house.price = price;
    p.house.fees = Math.round(price * feeRate);
    const need = price + p.house.fees - p.house.selfFund - (p.house.gift||0);
    p.house.loans.forEach((l,i) => { l.amount = Math.max(0, Math.round(need * ratio[i])); });
    return p;
  };''',
    '''function priceBreakEven(P, ok){
  /* 諸費用の合計を入れる方式では、価格に対する率を保って伸縮させる
     （価格だけ動かして諸費用を据え置くと、上限を高く見せてしまう）。 */
  const feeRate = P.house.price > 0 ? feeTotal(P.house) / P.house.price : 0.06;
  const build = price => {
    const p = clone(P);
    p.house.price = price;
    if(p.house.feeMode !== "detail") p.house.fees = Math.round(price * feeRate);
    /* ★借入は `fitLoansOn()` に決めさせる。
         v26はここに独自の按分式を持っており、詳細諸費用のとき
         **融資手数料が借入額に比例する分を落として**上限を高く出していた
         （実測：資産枯渇軸で533,524円・返済負担軸で709,305円の過大表示）。 */
    fitLoansOn(p);
    return p;
  };''',
    "priceBreakEven を閉じた式へ")

# ============================================================
# 3. 融資手数料率の無効値は入口で拒否し、式のフォールバックをやめる
# ============================================================
sub('''  /* 料率が100%以上だと式が成り立たない（分母が0以下）。入力の誤りとして扱う。 */
  if(!Number.isFinite(r) || r < 0 || r >= 1) return numerator;
  return numerator / (1 - r);''',
    '''  /* ★料率が0未満・100%以上だと式が成り立たない（分母が0以下）。
       v26は分子をそのまま返して**成功経路を続行**しており、
       料率100%で43,196,000円不足・120%で51,835,200円不足のプランが保存できた。
       いまは入口（`onNum`）で拒否するので、ここへは到達しない。
       それでも旧データ・取込ファイル経由で来たときに黙って続けないよう、
       **計算不能を示す `null`** を返す。 */
  if(!Number.isFinite(r) || r < 0 || r >= 1) return null;
  return numerator / (1 - r);''',
    "requiredLoanTotal は無効料率で null")

sub('''  const need = requiredLoanTotal(H);
  /* ★借入の配列が空・壊れている場合に1本用意する。 */''',
    '''  const need = requiredLoanTotal(H);
  /* ★必要額が求まらない（料率が0未満・100%以上）ときは借入を触らない。
       触ると「合わせたのに合っていない」状態を作ってしまう。
       画面には `validateParams()` が理由を出す。 */
  if(need === null) return p;
  /* ★借入の配列が空・壊れている場合に1本用意する。 */''',
    "fitLoansOn は need=null で何もしない")

# 入口で範囲を拒否する（onNum の項目別スキーマ）
sub('''function onNum(path, v){
  const x = readFinite(v, 1);
  if(x === null){ noticeBadInput([path], "その欄は変更していません"); render(); return; }''',
    '''/** 数値の入口で使う、項目ごとの許される範囲。
 *
 *  ★「有限かどうか」だけでは足りない。融資手数料率100%は有限な数だが、
 *    必要借入額の式（`numerator / (1 - r)`）の分母を0以下にする。
 *    v26は保存まででき、43,196,000円不足のプランが残った。
 *    **意味として成り立たない値は、PARAMSへ入れる前に止める。** */
const NUM_RANGE = {
  "house.feeLoanRate": {min:0, max:99.999, label:"融資手数料率",
    why:"借入額に対する割合です。100%以上は必要な借入額が求まりません。"},
  "family.ageH":  {min:0, max:130, label:"あなたの年齢"},
  "family.ageW":  {min:0, max:130, label:"パートナーの年齢"},
  "meta.endAge":  {min:1, max:130, label:"最終年齢"},
};
/** 範囲を外れていたら理由の文字列を返す（範囲内なら null）。 */
function rangeError(path, x){
  const s = NUM_RANGE[path];
  if(!s) return null;
  if(x < s.min || x > s.max)
    return `${s.label}は ${s.min} 〜 ${s.max} の範囲で入れてください`
         + (s.why ? `。${s.why}` : "。");
  return null;
}
function onNum(path, v){
  const x = readFinite(v, 1);
  if(x === null){ noticeBadInput([path], "その欄は変更していません"); render(); return; }
  const re = rangeError(path, x);
  if(re){
    pushNotice("range", "bad", `<b>${esc(re)}</b>`
      + `<span class="hint">その欄は変更していません（いまの値のままです）。</span>`);
    render(); return;
  }''',
    "onNum に項目別範囲")

# ============================================================
# 4. 保存・生成の不変条件に「資金が足りていること」を入れる
# ============================================================
sub('''/** 借入額が負になっていないか（負の借入は「返済がマイナス＝収入」になってしまう）。 */
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
}''',
    '''/** 借入額が負になっていないか（負の借入は「返済がマイナス＝収入」になってしまう）。 */
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

/** 住宅を買うプランで、**資金が足りているか**を確かめる。
 *
 *  ★これを不変条件として持つのが要点。計算の経路を1本にしても、
 *    「1本にしたつもり」を検査していなければ、次に増えた経路で同じことが起きる。
 *    足りない額が1円を超えたら不合格とする（丸め残差は許す）。
 *    **自己資金が余る側（借入0で足りる）は不合格にしない。** */
const FUND_TOLERANCE = 1;
function underfundedIn(plans){
  const out = [];
  (plans || []).forEach(p => {
    const H = p.params && p.params.house;
    if(!H || !H.buy) return;
    const gap = fundingGap(H);
    if(!Number.isFinite(gap)){ out.push(`${p.name} の資金差額が数値になりません`); return; }
    const loans = (Array.isArray(H.loans) ? H.loans : [])
      .reduce((s, l) => s + (Number(l.amount) || 0), 0);
    /* 借入0で余っている（＝現金で足りる）のは正しい状態。 */
    if(gap < -FUND_TOLERANCE && loans > 0)
      out.push(`${p.name} の借入が必要額より ${Math.round(-gap).toLocaleString()}円 多い`);
    if(gap > FUND_TOLERANCE)
      out.push(`${p.name} の住宅資金が ${Math.round(gap).toLocaleString()}円 足りない`);
  });
  return out;
}''',
    "underfundedIn を追加")

sub('''function commitPlans(nextPlans){
  /* ★保存の直前に1回だけ検査する。ここを通らない保存経路を作らない。 */
  const bad = nonFiniteIn(nextPlans, "plans")
    .concat(badNumbersIn(nextPlans, "plans")).concat(badLoansIn(nextPlans));''',
    '''function commitPlans(nextPlans){
  /* ★候補が `null` のときは、作る途中で失敗している（`withPlanIn` が返す）。
       v26は「何も足していない元配列」が返っていたため、
       `commitPlans([])` が成功し **実体0件のまま「保存しました（計0件）」**と出た。
       失敗は値の形で伝え、ここで必ず止める。 */
  if(nextPlans === null || nextPlans === undefined){
    pushNotice("badplan", "bad",
      `<b>入れた値が数値として扱えないため、保存しませんでした。</b>`
      + `<span class="hint">上に出ている欄を直してから、もう一度保存してください。</span>`);
    return false;
  }
  /* ★保存の直前に1回だけ検査する。ここを通らない保存経路を作らない。 */
  const bad = nonFiniteIn(nextPlans, "plans")
    .concat(badNumbersIn(nextPlans, "plans")).concat(badLoansIn(nextPlans))
    .concat(underfundedIn(nextPlans));''',
    "commitPlans に null と資金差の検査")

sub('''  const bad = nonFiniteIn(params, "params");
  if(bad.length){
    noticeBadInput(bad, "このプランは保存していません");
    return (list || []).slice();     // 何も足さずに返す
  }
  const next = (list || []).slice();''',
    '''  const bad = nonFiniteIn(params, "params");
  if(bad.length){
    noticeBadInput(bad, "このプランは保存していません");
    /* ★v26は「何も足していない元配列」を返していた。呼び出し側は成功と区別できず、
         `commitPlans([])` が通って **0件で「保存しました」**と表示した。
         **失敗は `null` で返す。** `commitPlans(null)` が必ず止める。 */
    return null;
  }
  /* まとめて作る途中で1件でも失敗したら、以降も作らない。 */
  if(list === null || list === undefined) return null;
  const next = list.slice();''',
    "withPlanIn は失敗で null")

if ng:
    print("NG:", " / ".join(ng))
    sys.exit(1)
P.write_text(t, encoding="utf-8")
print("OK v27 P0-1／P1-1（住宅資金の一本化・料率の拒否・資金差の不変条件）")
