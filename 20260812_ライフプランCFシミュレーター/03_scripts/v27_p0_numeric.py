# -*- coding: utf-8 -*-
r"""v27 P0-2：数値の入口を1つにし、意味の範囲まで検査する。

ChatGPT版の v25 独立再レビューで指摘され、**現物で再現を確認した**：

  v24で `readFinite()` を入れたのは `onNum` / `onMan` の2経路だけだった。
  表・明細・ローン・教育費・積立の入口は素の `parseFloat(v)||0` のままで、
  `parseFloat("1e307") * 10000` が `Infinity` になる。

    onLoanMan('1e307')  → 借入 Infinity、毎月返済 NaN、最終資産 NaN
    onRowMan('1e307')   → 最終資産 -Infinity
    onItemMan('1e307')  → 最終資産 -Infinity
    onNum('1e307')      → 値は有限だが最終資産 -Infinity（物価変動率）

  ★**「有限な値だけ入れる」では足りない。** 物価変動率 1e307 は有限だが、
    複利で回すと結果が -Infinity になる。**入力の範囲**と**計算結果**の
    両方を見なければ止まらない。

  さらに、巨大な借入を保存すると `withPlanIn()` が「何も足していない元配列」を
  返し、`commitPlans([])` が成功して **実体0件のまま「保存しました（計0件）」**と
  表示した（`null` を返す形に直したのは v27_p0_housing.py）。
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
# 1. 共通の入口 setNum() を、readFinite の隣に置く
# ============================================================
sub('''function onNum(path, v){
  const x = readFinite(v, 1);''',
    '''/** 添字つきの欄（表の行・明細・ローン・教育費・積立）の共通の入口。
 *
 *  ★入口を1つにするのが要点。v26は入口が11個あり、そのうち `readFinite()` を
 *    通るのは2個だけだった。**同じ検査を各所に書き足す形にすると、次に増えた
 *    入口がまた素通りする。** 書き込みの直前をここに集める。
 *
 *  @param holder 書き込む先のオブジェクト（行・明細・ローンなど）
 *  @param key    書き込むキー
 *  @param v      画面から来た文字列
 *  @param spec   {man:万円入力か, min, max, label:画面に出す名前}
 *  @return 書き込めたら true、止めたら false */
function setNum(holder, key, v, spec){
  spec = spec || {};
  const name = spec.label || key;
  if(!holder){ return false; }
  const x = readFinite(v, spec.man ? MAN : 1);
  if(x === null){
    noticeBadInput([name], "その欄は変更していません");
    render(); return false;
  }
  const lo = (spec.min === undefined) ? -Infinity : spec.min;
  const hi = (spec.max === undefined) ?  Infinity : spec.max;
  if(x < lo || x > hi){
    /* ★桁が大きすぎるだけでなく、**意味として成り立たない値**も止める。
         負の借入は「返済がマイナス＝毎月お金が入る」になってしまう。 */
    const unit = spec.man ? "万円" : "";
    pushNotice("range", "bad",
      `<b>${esc(name)}に入れられる範囲を外れています。</b>`
      + `<span class="hint">入れた値：${esc(String(v))}${unit}／`
      + `入れられる範囲：${lo === -Infinity ? "―" : fmtYen(spec.man ? lo/MAN : lo)}`
      + ` 〜 ${hi === Infinity ? "―" : fmtYen(spec.man ? hi/MAN : hi)}${unit}。<br>`
      + `その欄は変更していません（いまの値のままです）。</span>`);
    render(); return false;
  }
  holder[key] = x;
  return true;
}
/* 使いまわす範囲。**同じ意味の欄は同じ範囲を使う**（個別に書かない）。 */
const SPEC = {
  age:      {min:0,    max:130},          // 年齢
  year:     {min:1900, max:2200},         // 西暦の年
  span:     {min:0,    max:100},          // 年数（返済期間・在学年数など）
  every:    {min:1,    max:200},          // 何年ごと
  rateAny:  {min:-100, max:100},          // 増減率（マイナスもある）
  ratePos:  {min:0,    max:100},          // 金利・割合（マイナスはない）
  money:    {man:true, min:0,    max:100000000},   // 金額（万円入力・上限1兆円）
  moneyAny: {man:true, min:-100000000, max:100000000}, // 収支の金額（符号を反転させたい人がいる）
  monthly:  {man:true, min:0,    max:1000000},     // 毎月の積立（万円入力・上限100億円）
};
function onNum(path, v){
  const x = readFinite(v, 1);''',
    "setNum と SPEC を追加")

# ============================================================
# 2. 年齢別テーブル（onRow / onRowMan）
# ============================================================
sub('''function onRow(path, i, key, v){
  get(PARAMS,path)[i][key] = parseFloat(v)||0;
  markEntered(path + "." + i + "." + key);
  syncBaseFromTable(path);
  recalc();
}
function onRowMan(path, i, key, v){
  get(PARAMS,path)[i][key] = (parseFloat(v)||0)*MAN;
  markEntered(path + "." + i + "." + key);
  syncBaseFromTable(path);
  recalc();
}''',
    '''function onRow(path, i, key, v){
  const who = AGETABLE_NAME[path] || path;
  const spec = (key === "age") ? SPEC.age : SPEC.rateAny;
  if(!setNum(get(PARAMS,path)[i], key, v,
             Object.assign({label:`${who} ${i+1}行目の${key === "age" ? "開始年齢" : "変動率"}`}, spec))) return;
  markEntered(path + "." + i + "." + key);
  syncBaseFromTable(path);
  recalc();
}
function onRowMan(path, i, key, v){
  const who = AGETABLE_NAME[path] || path;
  if(!setNum(get(PARAMS,path)[i], key, v,
             Object.assign({label:`${who} ${i+1}行目の金額`}, SPEC.money))) return;
  markEntered(path + "." + i + "." + key);
  syncBaseFromTable(path);
  recalc();
}''',
    "onRow / onRowMan")

# ============================================================
# 3. その他の収支（onItem / onItemMan）
# ============================================================
sub('''function onItem(path, i, key, v, isStr){
  get(PARAMS,path)[i][key] = isStr ? v : (parseFloat(v)||0); recalc();
}
function onItemMan(path, i, v){ get(PARAMS,path)[i].amount = (parseFloat(v)||0)*MAN; recalc(); }''',
    '''const ITEM_SPEC = {from:SPEC.age, to:SPEC.age, every:SPEC.every};
function onItem(path, i, key, v, isStr){
  const it = get(PARAMS,path)[i];
  if(isStr){ it[key] = v; recalc(); return; }
  if(!setNum(it, key, v,
             Object.assign({label:`${i+1}件目の${key === "from" ? "開始年齢"
                                              : key === "to" ? "終了年齢"
                                              : key === "every" ? "間隔（年）" : key}`},
                           ITEM_SPEC[key] || {}))) return;
  recalc();
}
function onItemMan(path, i, v){
  if(!setNum(get(PARAMS,path)[i], "amount", v,
             Object.assign({label:`${i+1}件目の金額`}, SPEC.moneyAny))) return;
  recalc();
}''',
    "onItem / onItemMan")

# ============================================================
# 4. お子さん（onKid）
# ============================================================
sub('''function onKid(i, key, v, isStr){
  PARAMS.family.children[i][key] = isStr ? v : (parseFloat(v)||0); recalc();
}''',
    '''function onKid(i, key, v, isStr){
  const c = PARAMS.family.children[i];
  if(!c) return;
  if(isStr){ c[key] = v; recalc(); return; }
  /* 生まれ年は西暦。1900〜2200の外はまず入力の誤り。 */
  if(!setNum(c, key, v,
             Object.assign({label:`${i+1}人目のお子さんの${key === "birthYear" ? "生まれ年" : key}`},
                           key === "birthYear" ? SPEC.year : {}))) return;
  recalc();
}''',
    "onKid")

# ============================================================
# 5. 住宅ローン（onLoan / onLoanMan / onStep）
# ============================================================
sub('''function onLoan(i, key, v, isStr){
  PARAMS.house.loans[i][key] = isStr ? v : (parseFloat(v)||0); recalc();
}
function onLoanMan(i, v){ PARAMS.house.loans[i].amount = (parseFloat(v)||0)*MAN; recalc(); }''',
    '''function onLoan(i, key, v, isStr){
  const l = PARAMS.house.loans[i];
  if(!l) return;
  if(isStr){ l[key] = v; recalc(); return; }
  if(!setNum(l, key, v,
             Object.assign({label:`${i+1}本目のローンの${key === "years" ? "返済期間（年）" : key}`},
                           key === "years" ? SPEC.span : {}))) return;
  recalc();
}
function onLoanMan(i, v){
  /* ★負の借入を**入力の時点で**拒否する（`SPEC.money` の min:0）。
       v26は入れられてしまい、「返済がマイナス＝毎月お金が入る」計算になった。
       保存時の `badLoansIn()` でも止まるが、画面はその間ずっと嘘の結果を出す。 */
  if(!setNum(PARAMS.house.loans[i], "amount", v,
             Object.assign({label:`${i+1}本目のローンの借入額`}, SPEC.money))) return;
  recalc();
}''',
    "onLoan / onLoanMan")

sub('''function onStep(i, j, key, v){
  PARAMS.house.loans[i].steps[j][key] = parseFloat(v)||0; recalc();
}''',
    '''function onStep(i, j, key, v){
  const l = PARAMS.house.loans[i];
  if(!l || !l.steps || !l.steps[j]) return;
  if(!setNum(l.steps[j], key, v,
             Object.assign({label:`${i+1}本目のローンの${j+1}段目の${key === "y" ? "開始年" : "金利"}`},
                           key === "y" ? SPEC.span : SPEC.ratePos))) return;
  recalc();
}''',
    "onStep")

# ============================================================
# 6. 教育費（onStage / onStageMan / onStartAge）
# ============================================================
sub('''function onStage(k, key, v){ PARAMS.edu.stages[k][key] = parseFloat(v)||0; recalc(); }
function onStageMan(k, key, v){ PARAMS.edu.stages[k][key] = (parseFloat(v)||0)*MAN; recalc(); }
function onStartAge(k, v){ PARAMS.edu.startAge[k] = parseFloat(v)||0; recalc(); }''',
    '''/** 教育費の段階の呼び名。画面に出ているものと同じ文字を使う。 */
function stageLabelOf(k){
  return ((PARAMS.edu.stages[k] || {}).label) || STAGE_LABEL[k] || k;
}
function onStage(k, key, v){
  if(!setNum(PARAMS.edu.stages[k], key, v,
             Object.assign({label:`${stageLabelOf(k)}の${key === "years" ? "在学年数" : key}`},
                           key === "years" ? SPEC.span : {}))) return;
  recalc();
}
function onStageMan(k, key, v){
  if(!setNum(PARAMS.edu.stages[k], key, v,
             Object.assign({label:`${stageLabelOf(k)}の`
                                  + `${key === "first" ? "初年度の費用" : "2年目以降の費用"}`},
                           SPEC.money))) return;
  recalc();
}
function onStartAge(k, v){
  if(!setNum(PARAMS.edu.startAge, k, v,
             Object.assign({label:`${stageLabelOf(k)}が始まる年齢`}, SPEC.age))) return;
  recalc();
}''',
    "onStage / onStageMan / onStartAge")

# ============================================================
# 7. 積立スケジュール（onSchedule）
# ============================================================
sub('''function onSchedule(i, key, v){
  const s = PARAMS.saving.schedule[i];
  if(!s) return;
  s[key] = (key === "who" || key === "kind") ? v
         : (key === "monthly") ? (parseFloat(v)||0)*MAN : (parseFloat(v)||0);
  recalc();
}''',
    '''function onSchedule(i, key, v){
  const s = PARAMS.saving.schedule[i];
  if(!s) return;
  if(key === "who" || key === "kind"){ s[key] = v; recalc(); return; }
  const spec = (key === "monthly") ? SPEC.monthly : SPEC.age;
  const label = `${i+1}件目の積立の`
    + (key === "monthly" ? "毎月の額" : key === "from" ? "始める年齢" : "終える年齢");
  if(!setNum(s, key, v, Object.assign({label}, spec))) return;
  recalc();
}''',
    "onSchedule")

# ============================================================
# 8. 新しい物件の価格（prompt 経由）
# ============================================================
sub('''  const price = Math.round(parseFloat(priceMan) || 0) * MAN;
  if(price <= 0){ alert("価格が読み取れませんでした。数字だけを入れてください。"); return; }''',
    '''  /* ★`prompt` から来る値も同じ検査を通す（画面の欄だけが入口ではない）。 */
  const priceRaw = readFinite(priceMan, MAN);
  const price = (priceRaw === null) ? null : Math.round(priceRaw / 10000) * 10000;
  if(price === null || !(price > 0) || price > 100000000 * MAN){
    alert("価格が読み取れませんでした。1〜100000000（万円）の数字だけを入れてください。"); return;
  }''',
    "newPropertyPlan の価格")

# ============================================================
# 9. 保存の直前に、計算結果そのものも検査する
# ============================================================
sub('''  /* ★保存の直前に1回だけ検査する。ここを通らない保存経路を作らない。 */
  const bad = nonFiniteIn(nextPlans, "plans")
    .concat(badNumbersIn(nextPlans, "plans")).concat(badLoansIn(nextPlans))
    .concat(underfundedIn(nextPlans));''',
    '''  /* ★保存の直前に1回だけ検査する。ここを通らない保存経路を作らない。 */
  const bad = nonFiniteIn(nextPlans, "plans")
    .concat(badNumbersIn(nextPlans, "plans")).concat(badLoansIn(nextPlans))
    .concat(underfundedIn(nextPlans)).concat(badResultsIn(nextPlans));''',
    "commitPlans に計算結果の検査")

sub('''const FUND_TOLERANCE = 1;''',
    '''/** 入力は有限でも、**計算結果**が非有限になるプランを保存しない。
 *
 *  ★これがないと「入れた値は有限だから通す」で終わってしまう。
 *    実測：物価変動率に 1e307 を入れると、値は有限のまま
 *    最終資産が -Infinity になる（複利で桁があふれる）。
 *    入力の範囲だけでは防げないので、**結果の側からも見る**。
 *    ChatGPT版V77も同じ不変条件を入れている（`simulationFinite`）。 */
function badResultsIn(plans){
  const out = [];
  (plans || []).forEach(p => {
    let s;
    try{ s = simulate(p.params); }
    catch(e){ out.push(`${p.name} の計算が途中で止まりました（${e.message}）`); return; }
    /* 行の数値と要約だけを見る（描画用の文字列は対象外）。 */
    const hit = nonFiniteIn({rows:s.rows, summary:s.summary}, p.name);
    if(hit.length) out.push(hit[0] + (hit.length > 1 ? ` ほか ${hit.length-1}件` : ""));
  });
  return out;
}

const FUND_TOLERANCE = 1;''',
    "badResultsIn を追加")

if ng:
    print("NG:", " / ".join(ng))
    sys.exit(1)
P.write_text(t, encoding="utf-8")
print("OK v27 P0-2（数値の入口を1つに・範囲検査・計算結果の検査）")
