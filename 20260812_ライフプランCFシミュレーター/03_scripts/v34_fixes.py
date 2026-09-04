# -*- coding: utf-8 -*-
"""v33 -> v34。ChatGPT版のv33独立再レビュー（P1 2件・P2 2件／7試験不合格）へ対応する。"""
import io, sys, hashlib
from pathlib import Path

OUT = Path("02_output")
SRC = OUT / "20260903_ライフプランCFシミュレーター汎用版_v33.html"
DST = OUT / "20260903_ライフプランCFシミュレーター汎用版_v34.html"

s = io.open(SRC, encoding="utf-8").read()
n = 0

def sub(tag, old, new, count=1):
    global s, n
    if s.count(old) != count:
        print("  [NG] " + tag + ": 期待 " + str(count) + " 件, 実際 " + str(s.count(old)) + " 件")
        sys.exit(1)
    s = s.replace(old, new, count)
    n += 1
    print("  [ok] " + tag)

# ---- E1: 意思決定・保存・取込で使う検査の正本を1本にする（P1-2） ----------
sub("E1-validator",
'''const FUND_TOLERANCE = 1;''',
'''/** ★借入の条件が「いまの家計計算に使える形か」を見る（v34）。
 *
 *  ★v33は `badLoansIn` で「返済期間が1年以上か」しか見ていなかった。
 *    そのため次の2つが素通りした（ChatGPT版のv33レビュー P1-1）：
 *    (a) **契約期間がすでに経過している残債**。35歳取得・返済期間5年・いま40歳で
 *        残債3,000万円があっても段階3になり、**年次表からその借入が消える**
 *        （実測：初年度返済0円・残高0円なのに、要約では返済総額3,076万円・完済39歳）。
 *        同じ借入について、年次表と要約が違うことを言っていた。
 *    (b) **マイナス金利**。金利−5%で段階3のまま、返済総額1,287万円＜元本3,000万円。
 *        v33は警告を出すだけで止めていなかった。
 */
function loanDecisionIssues(P){
  const src = P || PARAMS;
  const F = src.family || {}, H = src.house || {};
  const owned = !!H.buy && Number(H.buyAge) < Number(F.ageH);
  const elapsed = owned ? Math.max(0, Number(F.ageH) - Number(H.buyAge)) : 0;
  const blocking = [], warnings = [];
  (Array.isArray(H.loans) ? H.loans : []).forEach((l, i) => {
    const tag = (l && l.name) || `${i+1}本目`;
    const amount = Number(l && l.amount), years = Number(l && l.years);
    if(!Number.isFinite(amount) || amount < 0){ blocking.push(`${tag}の借入額`); return; }
    if(!(amount > 0)) return;                     /* 完済済みは検査しない */
    if(!Number.isFinite(years) || years < 1) blocking.push(`${tag}の返済期間`);
    else if(owned && years <= elapsed)
      blocking.push(`${tag}の残りの返済期間（契約${years}年に対し取得から${elapsed}年）`);
    const steps = Array.isArray(l && l.steps) ? l.steps : [];
    if(!steps.length){ blocking.push(`${tag}の金利`); return; }
    let prev = 0;
    steps.forEach((st, j) => {
      const y = Number(st && st.y), rate = Number(st && st.rate);
      if(!Number.isFinite(y) || y < 1 || (j === 0 && y !== 1) || y <= prev)
        blocking.push(`${tag}・${j+1}段目の開始年`);
      if(Number.isFinite(y)) prev = y;
      if(!Number.isFinite(rate) || rate < 0 || rate >= 100)
        blocking.push(`${tag}・${j+1}段目の金利`);
      else if(rate > 15)
        warnings.push(`${tag}・${j+1}段目の金利が高すぎないか確かめてください`);
    });
  });
  return {blocking:[...new Set(blocking)], warnings:[...new Set(warnings)],
          owned:owned, elapsed:elapsed};
}

/** 負にすると「収入」として働いてしまう費目。**負を許さない。** */
const NONNEG_PATHS = [
  ["house.mgmtFee","管理費"], ["house.repairFund","修繕積立金"],
  ["house.parkingFee","駐車場代"], ["house.holdCost","年間維持費"],
  ["house.bigRepair","大規模修繕費"], ["house.selfRepairFund","自主修繕積立"],
  ["house.rentNow","いまの住居費"], ["house.price","物件価格"],
  ["house.selfFund","自己資金"], ["house.fees","諸費用"], ["house.gift","贈与"],
  ["house.moveCost","引っ越し費用"], ["living.insurance","年間の保険料"],
  ["econ.deposit","預金・現金"], ["econ.invest","運用資産"],
];
/** ★負の費用が収入として働くのを止める（v34）。
 *    v33は `house.mgmtFee = -1,200,000` で初年度住宅費が **−867,000円** になり、
 *    段階3のまま保存もできた（`commitPlans` が true を返した）。
 *    ChatGPT版のv33レビュー `semantic.negative_housing_cost_as_income`。 */
function costDecisionIssues(P){
  const src = P || PARAMS;
  const blocking = [];
  NONNEG_PATHS.forEach(pair => {
    const v = get(src, pair[0]);
    if(v === null || v === undefined || v === "") return;
    const x = Number(v);
    if(!Number.isFinite(x) || x < 0) blocking.push(pair[1]);
  });
  const tbl = (src.living && Array.isArray(src.living.table)) ? src.living.table : [];
  tbl.forEach((r, i) => {
    const x = Number(r && r.amount);
    if(!Number.isFinite(x) || x < 0) blocking.push(`生活費${i+1}行目の金額`);
  });
  return {blocking:[...new Set(blocking)]};
}

/** ★判断・保存・取込が**同じ検査**を使うための正本（v34）。
 *
 *  ★v33は検査が3か所に散っていた。
 *    - `readiness()`   … `badLoansIn` だけ
 *    - `commitPlans()` … 数値・借入・資金・結果の4種
 *    - JSON取込        … **何も検査していなかった**
 *    そのため「保存はできないが診断は読める」「取込だけ素通り」が同時に成立していた
 *    （ChatGPT版のv33レビュー P1-2）。**検査を1本にし、呼ぶ側が用途で使い分ける。**
 *  ★`blocking` は判断・保存・取込を止める。`warnings` は止めないが「準備できた」とは言わない。
 *  ★`options.sim` に計算済みの結果を渡せる。描画のたびに再計算しないため。
 */
function decisionValidation(P, options){
  options = options || {};
  const src = P || PARAMS;
  const name = options.name || "いまの入力";
  const blocking = [], warnings = [];
  blocking.push(...badNumbersIn(src, "params").map(x => `数値：${x}`));
  const cost = costDecisionIssues(src);
  blocking.push(...cost.blocking);
  const loan = loanDecisionIssues(src);
  blocking.push(...loan.blocking);
  warnings.push(...loan.warnings);
  let simulationIssues = [];
  if(options.simulate !== false){
    const s = options.sim;
    if(s && s.rows && s.summary) simulationIssues = nonFiniteIn({rows:s.rows, summary:s.summary}, name);
    else simulationIssues = badResultsIn([{name:name, params:src}]);
    if(simulationIssues.length) blocking.push("試算の結果が数値になりません");
  }
  return {ok: blocking.length === 0, blocking:[...new Set(blocking)],
          warnings:[...new Set(warnings)], loanIssues:loan, simulationIssues:simulationIssues};
}

const FUND_TOLERANCE = 1;''')

# ---- E2: 取得済み持ち家の判定を loanDecisionIssues ベースへ（P1-1） --------
sub("E2-owned",
'''function ownedHousingReadiness(P){
  const H = (P && P.house) || {};
  const loans = Array.isArray(H.loans) ? H.loans : [];
  const bad = [];
  loans.forEach((l, i) => {
    if(!(Number(l && l.amount) > 0)) return;      // 完済済みは検査しない
    const label = (l && l.name) || `${i+1}本目`;
    if(!(Number(l.years) >= 1))
      bad.push(`${label}の返済期間が ${String(l && l.years)} 年`);
    const steps = Array.isArray(l.steps) ? l.steps : [];
    if(!steps.length) bad.push(`${label}の金利が入っていません`);
    else if(steps.some(x => !Number.isFinite(Number(x && x.rate))))
      bad.push(`${label}の金利が数値になりません`);
  });
  if(bad.length)
    return {level:"insufficient", gap:0,
            note:`いま返済中の借入の条件が計算できません`
               + `（${bad.slice(0,2).join(" / ")}`
               + `${bad.length > 2 ? ` ほか ${bad.length-2}件` : ""}）。`
               + `返済予定表のとおりに入れ直してください。`};
  return {level:"na", gap:0, note:""};
}''',
'''function ownedHousingReadiness(P){
  const src = P || PARAMS;
  const loan = loanDecisionIssues(src);
  const cost = costDecisionIssues(src);
  /* 住まいに関わる費目だけを住宅の判定へ回す（他は decisionValidation が拾う）。 */
  const housingCost = cost.blocking.filter(x =>
    /管理費|修繕|駐車場|維持費|住居費|物件価格|自己資金|諸費用|引っ越し/.test(x));
  const bad = [...loan.blocking, ...housingCost];
  if(bad.length)
    return {level:"insufficient", gap:0, issues:bad,
            note:`いま返済中の借入や住まいの費用が計算できません`
               + `（${bad.slice(0,2).join(" / ")}`
               + `${bad.length > 2 ? ` ほか ${bad.length-2}件` : ""}）。`
               + `返済予定表や管理費の通知のとおりに入れ直してください。`};
  if(loan.warnings.length)
    return {level:"estimate", gap:0, issues:loan.warnings,
            note:`${loan.warnings[0]}（概算としては使えます）`};
  /* ★取得済みで問題がなければ「検査の対象外(na)」として扱う。
       ただし v33 のように**検査そのものを飛ばす**のではなく、
       上の検査を通ったうえでの na であることが違い。 */
  return {level:"na", gap:0, issues:[], note:""};
}''')

# ---- E3: readiness が正本を使う（P1-2） -----------------------------------
sub("E3-readiness",
'''  const badVals = badLoansIn([{name:"いまの入力", params:PARAMS}]);
  out.badValues = badVals;
  if(badVals.length && out.stage > 1){''',
'''  /* ★描画のたびに再計算しないよう、計算済みの結果を渡す（v34）。 */
  const gate = decisionValidation(PARAMS,
    {sim: (typeof SIM !== "undefined" ? SIM : null), name:"いまの入力"});
  const badVals = gate.blocking;
  out.badValues = badVals;
  out.validation = gate;
  if(badVals.length && out.stage > 1){''')

sub("E3-readiness-note",
'''    out.note  = `計算できない値が入っています`
              + `（${badVals[0].replace("いまの入力 の", "")}）。`
              + `その欄を直すと、続きの判断に使えます。`;''',
'''    out.note  = `計算できない値が入っています`
              + `（${badVals[0].replace("いまの入力 の", "")}`
              + `${badVals.length > 1 ? ` ほか ${badVals.length-1}件` : ""}）。`
              + `その欄を直すと、続きの判断に使えます。`;''')

# ---- E4: commitPlans が正本を使う（P1-2） ---------------------------------
sub("E4-commit",
'''  const bad = nonFiniteIn(nextPlans, "plans")
    .concat(badNumbersIn(nextPlans, "plans")).concat(badLoansIn(nextPlans))
    .concat(underfundedIn(nextPlans)).concat(badResultsIn(nextPlans));''',
'''  /* ★保存も判断と同じ正本を通す（v34）。
       v33は `badNumbersIn` 等だけを見ており、**負の管理費を保存できた**
       （ChatGPT版のv33レビュー `semantic.negative_housing_cost_as_income`）。 */
  const gateBad = [];
  (nextPlans || []).forEach(p => {
    const g = decisionValidation(p && p.params, {name:(p && p.name) || "プラン"});
    if(!g.ok) gateBad.push(`${(p && p.name) || "プラン"}：${g.blocking.slice(0,2).join(" / ")}`);
  });
  const bad = nonFiniteIn(nextPlans, "plans")
    .concat(badNumbersIn(nextPlans, "plans")).concat(badLoansIn(nextPlans))
    .concat(underfundedIn(nextPlans)).concat(badResultsIn(nextPlans))
    .concat(gateBad);''')

# ---- E5: JSON取込を検証してから反映する（P1-2C） --------------------------
sub("E5-import",
'''      // 古い版で書き出したファイルも読めるよう、いまの形に補ってから取り込む
      const add = migratePlans(d.plans);
      let next = PLANS;
      add.forEach(p => { next = withPlanIn(next, p.params, p.name); });
      /* ★保存できなかったら、読み込んだことにしない（件数表示も出さない）。 */
      if(!commitPlans(next)){ input.value = ""; return; }
      if(d.current && d.current.params){
        PARAMS = migrateParams(d.current.params);
        document.getElementById("planName").value = PARAMS.meta.planName || "";
        syncSelectors();
      }''',
'''      // 古い版で書き出したファイルも読めるよう、いまの形に補ってから取り込む
      const add = migratePlans(d.plans);
      const cur = (d.current && d.current.params) ? migrateParams(d.current.params) : null;
      /* ★取り込む前に、保存・判断と同じ正本で検査する（v34）。
           v33は取込だけ**何も検査していなかった**ため、
           `econ.inflation = 1e307` を入れたファイルが通知なしで受理され、
           最終資産が非有限のまま段階3になった
           （ChatGPT版のv33レビュー `import.current_nonfinite_accepted`）。
         ★現在の入力にも保存プランにも触れる**前**に全部を調べ、
           1件でも駄目なら**何も変えない**。途中まで反映して止まらないようにする。 */
      const errs = [];
      add.forEach((p, i) => {
        const g = decisionValidation(p.params, {name:p.name});
        if(!g.ok) errs.push(`保存プラン${i+1}「${esc(p.name)}」：${g.blocking.slice(0,2).join(" / ")}`);
      });
      if(cur){
        const g = decisionValidation(cur, {name:"読み込むファイルの現在の入力"});
        if(!g.ok) errs.push(`現在の入力：${g.blocking.slice(0,2).join(" / ")}`);
      }
      if(errs.length)
        throw new Error("計算や判断に使えない値があるため、何も読み込みませんでした。"
          + errs.slice(0,3).join(" ／ ")
          + (errs.length > 3 ? ` ほか ${errs.length-3}件` : ""));
      let next = PLANS;
      add.forEach(p => { next = withPlanIn(next, p.params, p.name); });
      /* ★保存できなかったら、読み込んだことにしない（件数表示も出さない）。 */
      if(!commitPlans(next)){ input.value = ""; return; }
      if(cur){
        PARAMS = cur;
        document.getElementById("planName").value = PARAMS.meta.planName || "";
        syncSelectors();
      }''')

# ---- E6: pending を payload と結び付け、鮮度を伝える（P2-1） --------------
sub("E6-hash",
'''function pendingPlans(){
  const mark = readStore(STORE.plansMarker);
  if(mark.status !== "ok" || !mark.raw) return null;
  const pend = readStore(STORE.plansPending);
  if(pend.status !== "ok" || !pend.raw) return null;
  const parsed = parsePlansRaw(pend.raw);
  return parsed.ok ? {raw:pend.raw, list:parsed.list} : null;
}''',
'''/** 文字列の短い指紋。暗号用途ではなく、控え候補と印の結び付き確認だけに使う。 */
function hashText(t){
  const str = String(t == null ? "" : t);
  let h = 2166136261;
  for(let i = 0; i < str.length; i++){ h ^= str.charCodeAt(i); h = Math.imul(h, 16777619); }
  return (h >>> 0).toString(16).padStart(8, "0") + ":" + str.length;
}

const PENDING_STALE_MS = 24 * 60 * 60 * 1000;

/** 書けなかった控えの候補（pending）を、**印と結び付いている場合に限って**取り出す（v34）。
 *
 *  ★v33は「印があること」だけを根拠に採用していた。
 *    そのため**10年前の印**と無関係な pending でも、現在の保存プランとして
 *    黙って採用された（ChatGPT版のv33レビュー `pending.stale_marker_auto_adopted`）。
 *  ★印に payload の指紋を持たせ、**一致しなければ採用しない**。
 *    古いだけで捨てはしない（最後に残った唯一の手掛かりかもしれない）が、
 *    「古い候補」「古い形式の印」であることを必ず伝える。
 */
function pendingPlans(){
  const mark = readStore(STORE.plansMarker);
  if(mark.status !== "ok" || !mark.raw) return null;
  const pend = readStore(STORE.plansPending);
  if(pend.status !== "ok" || !pend.raw) return null;
  const parsed = parsePlansRaw(pend.raw);
  if(!parsed.ok) return null;
  let m = null;
  try{ m = JSON.parse(mark.raw); }catch(e){ return null; }
  if(!m || typeof m !== "object") return null;
  const legacy = !m.payloadHash;
  if(!legacy && m.payloadHash !== hashText(pend.raw)) return null;   /* 印と中身が違う */
  const at = Number(m.at);
  const age = Number.isFinite(at) && at > 0 ? Math.max(0, Date.now() - at) : null;
  return {raw:pend.raw, list:parsed.list, legacy:legacy,
          stale: age === null || age > PENDING_STALE_MS, ageMs:age};
}''')

sub("E6-marker-write",
'''    try{ localStorage.setItem(STORE.plansPending, payload); }catch(e){}
    try{ localStorage.setItem(STORE.plansMarker,
      JSON.stringify({at:Date.now(), why:"backup-write-failed"})); }catch(e){}''',
'''    try{ localStorage.setItem(STORE.plansPending, payload); }catch(e){}
    /* ★印に payload の指紋・保存の起点・版・タブを持たせる（v34）。
         印だけでは「その候補が本当にこの保存のものか」が分からない。 */
    try{ localStorage.setItem(STORE.plansMarker, JSON.stringify({
      at: Date.now(), why: "backup-write-failed",
      payloadHash: hashText(payload),
      baselineHash: hashText(PLANS_REV),
      version: VERSION.tag, tab: TAB_ID
    })); }catch(e){}''')

sub("E6-pending-notice",
'''      pushNotice("planpending", wrote ? "warn" : "bad",
        `<b>保存された内容が${esc(what)}ため、`
        + `前回書けなかった控えの候補から戻しました（${pend.list.length}件）。</b>`
        + `<span class="hint">`
        + (wrote
            ? `保存領域にも書き戻しました。`
            : `<b>ただし保存領域へは書き戻せていません。この画面の中だけの復旧です。</b>`)
        + `前回の保存が途中で終わった記録が残っていたため使いました。`
        + `内容を確かめてから、もう一度保存してください。</span>`);''',
'''      const oldish = pend.stale
        ? `<b>この候補は24時間より前のもの</b>（または時刻が分からないもの）です。`
        : "";
      const legacyNote = pend.legacy
        ? `<b>古い形式の印から戻したため、内容が最新とは限りません。</b>`
        : "";
      pushNotice("planpending", wrote ? "warn" : "bad",
        `<b>保存された内容が${esc(what)}ため、`
        + `前回書けなかった控えの候補から戻しました（${pend.list.length}件）。</b>`
        + `<span class="hint">`
        + (wrote
            ? `保存領域にも書き戻しました。`
            : `<b>ただし保存領域へは書き戻せていません。この画面の中だけの復旧です。</b>`)
        + oldish + legacyNote
        + `<b>最新の内容かどうかを必ず確かめてから</b>、もう一度保存してください。</span>`);''')

# ---- E7: 数値入力に意味のある min/max/step を付ける（P2-2） ---------------
sub("E7-constraints",
'''function foldLongNotes(){''',
'''/** ★数値欄の意味範囲をブラウザにも伝える（v34）。
 *
 *  ★v33は可視の数値入力133件のうち min なし131件・max なし133件だった
 *    （ChatGPT版のv33レビュー `dom.range.numeric_minmax_coverage`）。
 *    JavaScript側の検査が主防御であることは変えないが、
 *    画面から許容範囲が分からないと、入力経路を足したときに検査を通し忘れる。
 *  ★**一律に0以上にはしない。** 物価上昇率・運用利回り・収入や生活費の変動率は
 *    負に意味がある。逆に料率・割合・金額は負を許さない。
 *    ChatGPT版V92では `rate` を含むパスを総当たりで負許容にしたため、
 *    健康保険料率にまで `min="-99.9"` が付いていた。**名前だけで決めない。**
 *  ★上限は「あり得ない桁」を弾く安全弁で、推奨範囲（スライダー）とは別物。
 *    推奨範囲を上限にすると、正当な入力（例：3,000万円の物件）を弾いてしまう。
 */
const NUM_SPEC = [
  [/^house\.loans\.\d+\.amount$/,               {min:0}],
  [/^house\.loans\.\d+\.years$/,                {min:1, max:50, step:1}],
  [/^house\.loans\.\d+\.steps\.\d+\.y$/,       {min:1, max:50, step:1}],
  [/^house\.loans\.\d+\.steps\.\d+\.rate$/,    {min:0, max:99.9, step:0.1}],
  [/^family\.children\.\d+\.birthYear$/,        {min:1900, max:2200, step:1}],
  [/^meta\.baseYear$/,                           {min:1900, max:2200, step:1}],
  /* ★年齢は**末尾で**判定する。`/age/i` だと `edu.stages.univ.first` の
       「st-age-s」まで拾い、大学費用243万円に上限120を付けてしまった。
       これは私がChatGPT版V92に「名前の総当たりで決めない」と指摘したのと同じ誤り。 */
  [/(age|Age)[HW]?$/,                           {min:0, max:120, step:1}],
  [/^tax\..*(Rate|Ratio)$/,                      {min:0, max:100, step:0.01}],
  [/(rate|growth|inflation|share)$/i,           {max:100, step:0.1}],   /* 下限なし＝負を許す */
  [/(amount|price|fee|fees|fund|cost|deposit|invest|insurance|balance|bal0|monthly|salary|pension)/i,
                                                {min:0}],
];
function numSpecFor(path){
  for(const pair of NUM_SPEC) if(pair[0].test(path)) return pair[1];
  return null;
}
/** 入力欄のハンドラからパスを読む（欄に属性を足さずに済ませる）。 */
function numPathOf(el){
  const h = (el.getAttribute("oninput") || "") + " " + (el.getAttribute("onchange") || "");
  let m;
  if((m = h.match(/on(?:Num|Man)\(\s*'([^']+)'/))) return m[1];
  if((m = h.match(/onLoanMan\(\s*(\d+)/))) return `house.loans.${m[1]}.amount`;
  if((m = h.match(/onLoan\(\s*(\d+)\s*,\s*'([^']+)'/))) return `house.loans.${m[1]}.${m[2]}`;
  if((m = h.match(/onStep\(\s*(\d+)\s*,\s*(\d+)\s*,\s*'([^']+)'/)))
    return `house.loans.${m[1]}.steps.${m[2]}.${m[3]}`;
  if((m = h.match(/on(?:Row|RowMan)\(\s*'([^']+)'\s*,\s*(\d+)\s*,\s*'([^']+)'/)))
    return `${m[1]}.${m[2]}.${m[3]}`;
  if((m = h.match(/onKid\(\s*(\d+)\s*,\s*'([^']+)'/))) return `family.children.${m[1]}.${m[2]}`;
  return null;
}
function applyNumericConstraints(root){
  let els;
  try{ els = (root || document).querySelectorAll('input[type="number"]'); }catch(e){ return 0; }
  let done = 0;
  Array.from(els || []).forEach(el => {
    try{
      const path = numPathOf(el);
      if(!path) return;
      const spec = numSpecFor(path);
      if(!spec) return;
      if(spec.min !== undefined) el.setAttribute("min", String(spec.min));
      if(spec.max !== undefined) el.setAttribute("max", String(spec.max));
      if(spec.step !== undefined && !el.hasAttribute("step")) el.setAttribute("step", String(spec.step));
      done++;
    }catch(e){ /* 1件失敗しても他は付ける */ }
  });
  return done;
}

function foldLongNotes(){''')

# render の末尾処理に applyNumericConstraints を足す
sub("E7-call", '''  foldLongNotes();''', '''  foldLongNotes();
  applyNumericConstraints(document);''', count=s.count('  foldLongNotes();'))

# ---- E8: 版番号 -----------------------------------------------------------
sub("E8-tag", '''tag:"汎用版 v33"''', '''tag:"汎用版 v34"''')
sub("E8-file",
'''file:"20260903_ライフプランCFシミュレーター汎用版_v33.html"''',
'''file:"20260903_ライフプランCFシミュレーター汎用版_v34.html"''')


# ---- E9: 教育費の段階欄もパスを読めるようにする ---------------------------
sub("E9-onstage",
"""  if((m = h.match(/onKid\(\s*(\d+)\s*,\s*'([^']+)'/))) return `family.children.${m[1]}.${m[2]}`;""",
"""  if((m = h.match(/onKid\(\s*(\d+)\s*,\s*'([^']+)'/))) return `family.children.${m[1]}.${m[2]}`;
  if((m = h.match(/onStage(?:Man)?\(\s*'([^']+)'\s*,\s*'([^']+)'/))) return `edu.stages.${m[1]}.${m[2]}`;""")

# ---- E10: 残りの欄に「負を許さない」を明示列挙で足す ----------------------
sub("E10-nonneg-prefixes",
"""  [/(amount|price|fee|fees|fund|cost|deposit|invest|insurance|balance|bal0|monthly|salary|pension)/i,
                                                {min:0}],
];""",
"""  [/(amount|price|fee|fees|fund|cost|deposit|invest|insurance|balance|bal0|monthly|salary|pension)/i,
                                                {min:0}],
  /* ★ここまでで「負が正当な欄」（率・変動率・割合）は上の行が拾い終えている。
       残りは金額・年数・件数・上限値なので、**接頭辞を明示列挙**して負を禁じる。
       総当たりの正規表現1本で決めないのは、名前だけでは
       「負が正当な変動率」と「負が無意味な料率」を見分けられないため。 */
  [/^(income\.|retire\.|living\.|tax\.|house\.|estate\.|verify\.|edu\.|saving\.|econ\.deposit|econ\.invest$)/,
                                                {min:0}],
];""")

CRLF = chr(13) + chr(10)
io.open(DST, "w", encoding="utf-8", newline=CRLF).write(s)
raw = DST.read_bytes()
print("")
print("適用: " + str(n) + " 件")
print("出力: " + str(DST))
print("バイト: " + format(len(raw), ",") + " / 行: " + format(s.count("\n") + 1, ","))
print("SHA-256: " + hashlib.sha256(raw).hexdigest())
