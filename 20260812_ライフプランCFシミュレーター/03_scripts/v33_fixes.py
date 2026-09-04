# -*- coding: utf-8 -*-
"""v32 -> v33。ChatGPT版のv32レビュー（P2 1件＋設計回答）と、
   彼らが実行できなかったブラウザ試験をこちらで走らせて見つけたP1に対応する。"""
import io, sys, hashlib
from pathlib import Path

OUT = Path("02_output")
SRC = OUT / "20260902_ライフプランCFシミュレーター汎用版_v32.html"
DST = OUT / "20260903_ライフプランCFシミュレーター汎用版_v33.html"

s = io.open(SRC, encoding="utf-8").read()
n_applied = 0

def sub(tag, old, new, count=1):
    global s, n_applied
    if s.count(old) != count:
        print("  [NG] " + tag + ": 期待 " + str(count) + " 件, 実際 " + str(s.count(old)) + " 件")
        sys.exit(1)
    s = s.replace(old, new, count)
    n_applied += 1
    print("  [ok] " + tag)

# ---- E1: 返済期間の要件を「借入があるとき」へ広げる（P1） -------------------
sub("E1-ready-steps",
'''         ["house.price","物件価格", P => housingOf(P) === "buy"],
         ["house.loans.0.years","返済期間", P => housingOf(P) === "buy"],''',
'''         ["house.price","物件価格", P => housingOf(P) === "buy"],
         /* ★返済期間は「これから買う」だけでなく**いま返済中**でも要る（v33）。
              v31で「取得済みなら取得時の資金恒等式で判定しない」を入れたとき、
              住宅まわりの要件を丸ごと `buy` 限定にした。その結果、
              **取得済み＋残債あり＋返済期間0年**でも段階3「判断の準備が整いました」になり、
              しかもその借入は**返済ゼロとして黙って計算から消えて**いた
              （実測：残債3,000万円で初年度返済0円・返済総額0円）。
              直したのは「過去の帳尻」なのに、**「現在の条件」まで一緒に落としていた。**
              ChatGPT版のv32レビュー `readiness.owned_home_current_debt_checked`
              （彼らの環境ではブラウザが起動できず未実行だったので、こちらで走らせて再現した）。 */
         ["house.loans.0.years","返済期間",
          P => housingOf(P) === "buy" || hasLoanBalance(P)],''')

# ---- E2: hasLoanBalance と 取得済み持ち家の現在時点の検査（P1） -------------
sub("E2-owned-readiness",
'''function housingReadiness(P){''',
'''/** いま返済中（またはこれから借りる）借入があるか。 */
function hasLoanBalance(P){
  const src = P || PARAMS;
  if(!src.house || !src.house.buy) return false;
  return (Array.isArray(src.house.loans) ? src.house.loans : [])
    .some(l => Number(l && l.amount) > 0);
}

/** すでに取得している住宅の準備度（v33）。
 *
 *  ★取得時の資金恒等式は見ない（もう終わった話）。
 *    見るのは**いまの借入が計算できる形をしているか**だけ。
 *    v32は `na` を返して終わりで、現在残債・返済期間・金利を誰も検査していなかった。
 *    **「過去を検査しない」と「現在を検査しない」は別のこと。** */
function ownedHousingReadiness(P){
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
}

function housingReadiness(P){''')

sub("E2-owned-branch",
'''  if(typeof housingOf === "function" && housingOf(src) === "own")
    return {level:"na", gap:0, note:""};''',
'''  if(typeof housingOf === "function" && housingOf(src) === "own")
    return ownedHousingReadiness(src);''')

# ---- E3: readiness に保存前と同じ検査を通す（P1） ---------------------------
sub("E3-readiness-gate",
'''  const hr = housingReadiness(PARAMS);
  out.housing = hr;''',
'''  /* ★保存できない値のままで「判断の準備が整いました」と言わない（v33）。
       保存の入口で使っている検査を、判断の準備度でも**同じものを**通す。
       v32は保存だけを止めていたため、**保存できない入力のまま診断だけが読めた**。
       判定を2本持つと、片方だけ直して安心してしまう。 */
  const badVals = badLoansIn([{name:"いまの入力", params:PARAMS}]);
  out.badValues = badVals;
  if(badVals.length && out.stage > 1){
    out.stage = 1;
    out.label = READY_STEPS[0].label;
    out.note  = `計算できない値が入っています`
              + `（${badVals[0].replace("いまの入力 の", "")}）。`
              + `その欄を直すと、続きの判断に使えます。`;
    if(!out.missing.length) out.missing = ["計算できる借入の条件"];
  }
  const hr = housingReadiness(PARAMS);
  out.housing = hr;''')

# ---- E4: 0円の有効性を人物ごとに一般化（設計回答） --------------------------
sub("E4-zero-income",
'''const READY_NONZERO_IF = {
  "income.hBase": P => workTypeOf(P, "h") !== "none",
};''',
'''/** ★0円の年収が有効かどうかを、**人物ごとに同じ規則で**決める（v33）。
 *    v31・v32は本人(`h`)だけを条件付けており、パートナー側は規則の外にあった。
 *    **規則を持っていることと、もう一人にも使っていることは別。**
 *    ・その人がいない（パートナー不在）＝当てはまらないので0は有効
 *    ・働いていない＝確認済みの0円は有効
 *    ・会社員・自営業＝0円は要確認
 *    ChatGPT版のv32レビュー §「0円の有効性」への対応。 */
function zeroIncomeNeedsCheck(P, who){
  const src = P || PARAMS;
  if(who === "w" && !(src.family && src.family.hasSpouse)) return false;
  return workTypeOf(src, who) !== "none";
}
const READY_NONZERO_IF = {
  "income.hBase": P => zeroIncomeNeedsCheck(P, "h"),
  "income.wBase": P => zeroIncomeNeedsCheck(P, "w"),
};''')

# ---- E5: pending を復旧候補として実際に読む（P2・相手の指摘） ---------------
sub("E5-pending-read",
'''function recoverPlansFromBackup(what, why){''',
'''/** 書けなかった控えの候補（pending）を、**印がある場合に限って**取り出す（v33）。
 *
 *  ★v32は pending を書くだけで誰も読まず、「台帳に載っているが効いていない」状態だった
 *    （ChatGPT版のv32レビュー P2-1。こちらも v32の依頼書 §7 で未着手と書いていた）。
 *  ★正常な主領域・控えより**優先しない**。marker があるとき＝
 *    前回の保存が途中で終わった記録が残っているときだけ見る。 */
function pendingPlans(){
  const mark = readStore(STORE.plansMarker);
  if(mark.status !== "ok" || !mark.raw) return null;
  const pend = readStore(STORE.plansPending);
  if(pend.status !== "ok" || !pend.raw) return null;
  const parsed = parsePlansRaw(pend.raw);
  return parsed.ok ? {raw:pend.raw, list:parsed.list} : null;
}

function recoverPlansFromBackup(what, why){''')

sub("E5-pending-use",
'''  if(!parsed.ok){
    PLANS = [];
    PLANS_REV = null;
    pushNotice("planbroken", "bad",''',
'''  if(!parsed.ok){
    /* ★控えも駄目なら、最後に pending を見る（v33）。 */
    const pend = pendingPlans();
    if(pend){
      PLANS = pend.list;
      PLANS_REV = null;
      const wrote = writeStoreVerified(STORE.plans, pend.raw);
      if(wrote) updateBackup(pend.raw);
      pushNotice("planpending", wrote ? "warn" : "bad",
        `<b>保存された内容が${esc(what)}ため、`
        + `前回書けなかった控えの候補から戻しました（${pend.list.length}件）。</b>`
        + `<span class="hint">`
        + (wrote
            ? `保存領域にも書き戻しました。`
            : `<b>ただし保存領域へは書き戻せていません。この画面の中だけの復旧です。</b>`)
        + `前回の保存が途中で終わった記録が残っていたため使いました。`
        + `内容を確かめてから、もう一度保存してください。</span>`);
      return;
    }
    PLANS = [];
    PLANS_REV = null;
    pushNotice("planbroken", "bad",''')

# ---- E6: 書く直前にロック所有権を確かめる（設計回答） -----------------------
sub("E6-lock-recheck",
'''  try{
    const payload = JSON.stringify(nextPlans);
    localStorage.setItem(STORE.plans, payload);''',
'''  /* ★書く直前に、**まだ自分がロックを持っているか**を確かめる（v33）。
       期限（4秒）が切れて別のタブに取られていたら、書かずに降りる。
       ChatGPT版のv32レビュー §「ロック期限4秒」への対応。
       彼らの助言どおり、**期限の長さそのものより、書込みの前後で
       所有権と revision を見直すほうが効く。** */
  const held = lockRead();
  if(!held || held.id !== TAB_ID){
    pushNotice("planlock", "warn",
      `<b>保存の順番待ちが切れたため、今回の保存は行いませんでした。</b>`
      + `<span class="hint">別のタブが先に保存を始めています。`
      + `画面の一覧を確かめてから、もう一度保存してください。</span>`);
    return false;
  }
  try{
    const payload = JSON.stringify(nextPlans);
    localStorage.setItem(STORE.plans, payload);''')

# ---- E7: 文がつながっていない（P2・自分で見つけた） ------------------------
sub("E7-whyhard-a", '''      + `${whyHard(b.worst)}`''', '''      + `${whyHard(b.worst)}。`''')
sub("E7-whyhard-b", '''      + `${whyHard(w)}`''', '''      + `${whyHard(w)}。`''')

# ---- E8: 借入欄に下限を付ける（P2・自分で見つけた） ------------------------
sub("E8-loan-amount",
'''<input type="number" value="${Math.round(l.amount/MAN)}" oninput="onLoanMan(${i},this.value)"''',
'''<input type="number" min="0" step="1" value="${Math.round(l.amount/MAN)}" oninput="onLoanMan(${i},this.value)"''')

sub("E8-loan-years",
'''<input type="number" value="${l.years}" oninput="onLoan(${i},'years',this.value)"''',
'''<input type="number" min="1" step="1" value="${l.years}" oninput="onLoan(${i},'years',this.value)"''')

# ---- E9: 版番号 -------------------------------------------------------------
sub("E9-version-tag", '''tag:"汎用版 v32"''', '''tag:"汎用版 v33"''')
sub("E9-version-file",
'''file:"20260902_ライフプランCFシミュレーター汎用版_v32.html"''',
'''file:"20260903_ライフプランCFシミュレーター汎用版_v33.html"''')
sub("E9-version-date", '''date:"2026-09-02"''', '''date:"2026-09-03"''',
    count=s.count('date:"2026-09-02"'))

# ★改行はv32と同じ CRLF のまま出す。読み込みで LF へ寄せているので書き戻す。
#   （揃えないと全行が差分になり、版どうしの比較ができなくなる）
CRLF = chr(13) + chr(10)
io.open(DST, "w", encoding="utf-8", newline=CRLF).write(s)
raw = DST.read_bytes()
print("")
print("適用: " + str(n_applied) + " 件")
print("出力: " + str(DST))
print("バイト: " + format(len(raw), ",") + " / 行: " + format(s.count("\n") + 1, ","))
print("SHA-256: " + hashlib.sha256(raw).hexdigest())
