# -*- coding: utf-8 -*-
"""汎用版 v29 → v30 の修正を当てる。

当てる内容:
  A. 保存の復旧（ChatGPT版 v29レビューの唯一の指摘 static.recovery_journal）
     v29 は主キーが壊れていると loadPlans() が catch で PLANS=[] にして黙って全消失した。
     バックアップキーを持ち、壊れていたら復旧し、必ず利用者に知らせる。
  B. 入力欄の読み上げ名から「？」と補足文を外す（ChatGPT版V82の査読を自分に当てて発見）
     v29 は <label for> の中に「？」ボタンと補足文が同居していたため、
     実効名が「ラベル＋？＋補足文」になっていた（住宅とローンで11/54件）。
     入力欄に aria-label（見出し語だけ）を付け、補足は aria-describedby で参照する。
  C. 準備度で「確認したか」と「値が使えるか」を分ける（ChatGPT版V80から取り込み・v29依頼書§7で約束）
     あわせて READY_STEPS を凍結し、completionKeyForPath() を持たせる。
  D. 借入を手で決めて資金差が残るとき、保存は許すが住宅の判断は未確定にする
     （ChatGPT版 v29レビュー §5 の助言）。

使い方: python 03_scripts/v30_fixes.py
"""
import io, re, sys, shutil
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
SRC = BASE / "02_output" / "20260901_ライフプランCFシミュレーター汎用版_v29.html"
DST = BASE / "02_output" / "20260902_ライフプランCFシミュレーター汎用版_v30.html"

s = io.open(SRC, encoding="utf-8").read()
orig_len = len(s)
applied = []


def sub(tag, old, new, count=1):
    """厳密一致で置換する。当たらなければ止める（黙って通さない）。"""
    global s
    n = s.count(old)
    if n != count:
        print("!! アンカー不一致 [%s]: %d件（期待 %d件）" % (tag, n, count))
        sys.exit(1)
    s = s.replace(old, new, count)
    applied.append(tag)


# ---------------------------------------------------------------- A. 保存の復旧
sub("A1-STORE",
'''const STORE = {
  plans:   "lpcfg_plans",''',
'''const STORE = {
  plans:   "lpcfg_plans",
  /* ★保存の控え。主領域が壊れたときに戻すためだけに使う（v30で追加）。
       v29は主領域の JSON.parse に失敗すると `PLANS = []` にして、
       **利用者のプランが黙って全部消えた**（ChatGPT版のv29レビュー
       `static.recovery_journal` で指摘。こちらも §13 で未着手と書いていた）。 */
  plansBak:"lpcfg_plans_bak",''')

sub("A2-loadPlans",
'''function loadPlans(){
  try{ PLANS = migratePlans(JSON.parse(localStorage.getItem(STORE.plans) || "[]")); }
  catch(e){ PLANS = []; }
}''',
'''/** 保存されたプランを読む。
 *
 *  ★主領域が壊れていたら**控えから戻す**。戻せなくても、
 *    **黙って空にしない**（消えたことを必ず知らせる）。
 *    v29は `catch(e){ PLANS = []; }` だけで、次に開いたときには
 *    利用者のプランが理由も告げられず全部消えていた。 */
function loadPlans(){
  const raw = readStore(STORE.plans);
  if(raw === null || raw === ""){ PLANS = []; return; }
  const first = parsePlansRaw(raw);
  if(first.ok){ PLANS = first.list; return; }
  /* 主領域が壊れている。控えを試す。 */
  const bakRaw = readStore(STORE.plansBak);
  const bak = (bakRaw === null || bakRaw === "") ? {ok:false, list:[]} : parsePlansRaw(bakRaw);
  if(bak.ok){
    PLANS = bak.list;
    /* 戻せた内容を主領域へ書き戻す（次回もまた壊れた値を読まないように）。 */
    try{ localStorage.setItem(STORE.plans, bakRaw); }catch(e){}
    pushNotice("planrecover", "warn",
      `<b>保存された内容が壊れていたため、控えから戻しました（${bak.list.length}件）。</b>`
      + `<span class="hint">直前の保存が最後まで書けなかった可能性があります。`
      + `内容を確かめてから、もう一度保存してください。</span>`);
    return;
  }
  PLANS = [];
  pushNotice("planbroken", "bad",
    `<b>保存された内容が読み取れませんでした。</b>`
    + `<span class="hint">控えからも戻せませんでした。`
    + `一覧は空で始まりますが、<b>壊れた内容は消していません</b>。`
    + `別のプランを保存すると上書きされるため、必要なら先に書き出してください。</span>`);
}

/** localStorage から読む。読めないときは null を返す（例外を外へ出さない）。 */
function readStore(key){
  try{ return localStorage.getItem(key); }catch(e){ return null; }
}

/** 生の文字列をプラン配列として解釈できるか試す。 */
function parsePlansRaw(raw){
  try{
    const list = migratePlans(JSON.parse(raw));
    if(!Array.isArray(list)) return {ok:false, list:[]};
    return {ok:true, list:list};
  }catch(e){ return {ok:false, list:[]}; }
}''')

sub("A3-commit",
'''    if(localStorage.getItem(STORE.plans) !== payload)
      throw new Error("保存したあとの読み戻しで内容が一致しませんでした");
    PLANS = nextPlans;
    return true;''',
'''    if(localStorage.getItem(STORE.plans) !== payload)
      throw new Error("保存したあとの読み戻しで内容が一致しませんでした");
    PLANS = nextPlans;
    /* ★主領域を書けたことを確かめた**あと**で控えを更新する。
         先に控えを書くと、主領域の書き込みが失敗したときに
         控えまで新しい壊れかけの内容になってしまう。
         控えが書けなくても保存そのものは成功として扱う（控えは保険）。 */
    try{ localStorage.setItem(STORE.plansBak, payload); }catch(e){}
    return true;''')


# ------------------------------------------------- B. 入力欄の読み上げ名を分ける
sub("B1-plainName",
'''/** 「？」ボタン。**本文が「？」なので、title では名前にならない**''',
'''/** 読み上げ名にする「見出し語だけ」の文字列を作る。
 *
 *  ★タグ・改行・連続空白・末尾の「？」「…」を落とす。
 *    v29は `<label for>` の中に「？」ボタンと補足文が同居していたため、
 *    入力欄の実効名が「ラベル＋？＋補足文」になっていた。
 *    実測：住宅とローンのタブで可視の入力欄54件中11件。
 *    例「諸費用の合計？物件価格の7.0%。中古は6〜9%が目安」
 *      「自己資金物件価格の10.0%。頭金を入れない場合も、契約時の手付金…」（91字・区切りなし）
 *    ChatGPT版V82に同じ型を指摘した直後に、自分の版で見つけた（査読の還流9回目）。
 *    なおV82は入力欄側を先に直しており、この点はあちらが先行していた。 */
function plainName(x){
  return String(x == null ? "" : x)
    .replace(/<[^>]*>/g, " ")
    .replace(/\\s+/g, " ")
    .replace(/[？?…]+\\s*$/, "")
    .trim();
}

/** 見出し語が同じになってしまう欄の、読み上げ名の上書き。
 *
 *  ★補足文を名前から外したことで、**補足が偶然担っていた区別が消えた**欄がある。
 *    `saving.nisaRate` と `saving.stockRate` はどちらも見出し語が「運用利回り」で、
 *    v29では補足文が名前に混ざっていたおかげで**たまたま**別名になっていた。
 *    見えるラベルは直上の `<h3>`（NISA／持株会など）で区別できるが、**読み上げでは消える。**
 *    **名前は path から引いて一意を保証する**（`AGETABLE_NAME` と同じ考え方）。
 *    受入試験の「同名0件」がこれを捕まえた（短くした結果、同名が1件**増えた**）。 */
const FIELD_NAME_OVERRIDE = {
  "saving.nisaRate":  "NISAの運用利回り",
  "saving.stockRate": "持株会など（課税口座）の運用利回り",
};

/** 入力欄に付ける読み上げ用の属性。
 *  **名前は見出し語だけ。補足は `aria-describedby` で参照する。** */
function a11yField(path, label, H){
  const nm = FIELD_NAME_OVERRIDE[path]
          || plainName(label) || plainName(FIELD_LABELS[path]) || "";
  const ids = (H && H.describedby) ? H.describedby : "";
  return `aria-label="${esc(nm)}"` + (ids ? ` aria-describedby="${esc(ids)}"` : "");
}

/** 「？」ボタン。**本文が「？」なので、title では名前にならない**''')

sub("B2-popBtn",
'''function popBtn(key, title, name){
  const nm = name || title || "くわしく";''',
'''function popBtn(key, title, name){
  /* ★名前からタグ・改行・連続空白を落とす。
       畳んだ補足に付くボタンは、名前に生の改行とインデントが入っていた
       （例「✓ 要件を満たしています\\n    　控除される総額 273万円（あな…」）。 */
  const nm = plainName(name) || plainName(title) || "くわしく";''')

sub("B3-fieldHelp",
'''function fieldHelp(path, note, fieldLabel){
  const key = popKey(path);
  const b = BENCH[path];
  const long = note && plainLen(note) > HINT_INLINE_MAX;
  const parts = [];
  if(long) parts.push(note);
  if(b) parts.push(`${esc(b.note)}<span class="src">出典：${esc(b.src)}</span>`);
  if(!parts.length){
    return {btn:"", inline: note ? `<br><span class="hint">${note}</span>` : "", extra:""};
  }
  return {
    btn: popBtn(key, "くわしく", fieldLabel || path),
    inline: (note && !long) ? `<br><span class="hint">${note}</span>` : "",
    extra: popBody(key, parts.join(`<div style="height:7px"></div>`)),
  };
}''',
'''function fieldHelp(path, note, fieldLabel, fieldId){
  const key = popKey(path);
  const b = BENCH[path];
  const long = note && plainLen(note) > HINT_INLINE_MAX;
  const parts = [];
  if(long) parts.push(note);
  if(b) parts.push(`${esc(b.note)}<span class="src">出典：${esc(b.src)}</span>`);
  /* ★補足に id を振り、入力欄から `aria-describedby` で指す。
       こうすると補足は**読み上げられるが、名前には入らない**。 */
  const hintId = fieldId ? (fieldId + "-hint") : "";
  const hintTag = ho => `<br><span class="hint"${hintId ? ` id="${hintId}"` : ""}>${ho}</span>`;
  if(!parts.length){
    return {btn:"", inline: note ? hintTag(note) : "", extra:"",
            describedby: (note && hintId) ? hintId : ""};
  }
  return {
    btn: popBtn(key, "くわしく", plainName(fieldLabel) || path),
    inline: (note && !long) ? hintTag(note) : "",
    extra: popBody(key, parts.join(`<div style="height:7px"></div>`)),
    describedby: [(note && !long && hintId) ? hintId : "", "pop-" + key]
                   .filter(Boolean).join(" "),
  };
}''')

sub("B4-numField",
'''function numField(label, path, unit, step, note){
  rememberFieldLabel(path, label);
  const v = get(PARAMS, path);
  const H = fieldHelp(path, note, label);
  /* ★label と input を id / for で結ぶ（P0-3）。
     v7までは for が無く、支援技術からは名前のない入力欄だった。 */
  const id = nextFieldId(path);
  return `<div class="f"><label for="${id}">${label}${H.btn}${H.inline}</label>
    <input id="${id}" type="number" step="${step||1}" value="${shownVal(v, path)}"
      placeholder="未入力" oninput="onNum('${path}',this.value)">
    <span class="u">${unit||""}</span></div>`
    + sliderRow(path, false, id, label) + inactiveNote(path) + benchLine(path) + H.extra;
}''',
'''function numField(label, path, unit, step, note){
  rememberFieldLabel(path, label);
  const v = get(PARAMS, path);
  /* ★id を先に作る。補足に id を振って `aria-describedby` で指すため。 */
  const id = nextFieldId(path);
  const H = fieldHelp(path, note, label, id);
  /* ★label と input を id / for で結ぶ（P0-3）。
     v7までは for が無く、支援技術からは名前のない入力欄だった。
     ★ただし for だけだと、ラベルの中の「？」と補足文まで名前に入る。
       名前は `aria-label` で見出し語だけにする（v30）。 */
  return `<div class="f"><label for="${id}">${label}${H.btn}${H.inline}</label>
    <input id="${id}" type="number" step="${step||1}" value="${shownVal(v, path)}"
      placeholder="未入力" ${a11yField(path, label, H)} oninput="onNum('${path}',this.value)">
    <span class="u">${unit||""}</span></div>`
    + sliderRow(path, false, id, label) + inactiveNote(path) + benchLine(path) + H.extra;
}''')

sub("B5-manField",
'''function manField(label, path, note){
  rememberFieldLabel(path, label);
  const v = get(PARAMS, path);
  const H = fieldHelp(path, note, label);
  const id = nextFieldId(path);
  return `<div class="f"><label for="${id}">${label}${H.btn}${H.inline}</label>
    <input id="${id}" type="number" step="1" value="${shownVal(Math.round(v/MAN*10)/10, path)}"
      placeholder="未入力" oninput="onMan('${path}',this.value)">
    <span class="u">万円</span></div>`
    + sliderRow(path, true, id, label) + inactiveNote(path) + benchLine(path) + H.extra;
}''',
'''function manField(label, path, note){
  rememberFieldLabel(path, label);
  const v = get(PARAMS, path);
  const id = nextFieldId(path);
  const H = fieldHelp(path, note, label, id);
  return `<div class="f"><label for="${id}">${label}${H.btn}${H.inline}</label>
    <input id="${id}" type="number" step="1" value="${shownVal(Math.round(v/MAN*10)/10, path)}"
      placeholder="未入力" ${a11yField(path, label, H)} oninput="onMan('${path}',this.value)">
    <span class="u">万円</span></div>`
    + sliderRow(path, true, id, label) + inactiveNote(path) + benchLine(path) + H.extra;
}''')


# ----------------------------------- C. 準備度：確認したか／値が使えるか を分ける
sub("C1-facts",
'''function isConfirmed(path){
  const st = (PARAMS.meta && PARAMS.meta.inputState) || {};
  const e  = (PARAMS.meta && PARAMS.meta.entered) || {};
  return !!(st[path] ? st[path].confirmed : e[path]);
}''',
'''function isConfirmed(path){
  const st = (PARAMS.meta && PARAMS.meta.inputState) || {};
  const e  = (PARAMS.meta && PARAMS.meta.entered) || {};
  return !!(st[path] ? st[path].confirmed : e[path]);
}

/** その項目の**値が計算に使えるか**。確認済みの旗とは別に見る。
 *
 *  ★v29は旗だけを見ていたため、**「確認した」と記録されていれば
 *    物件価格0円・返済期間0年でも段階が上がった。**
 *    ChatGPT版V80の `readinessFacts()` が `confirmed` と `valid` を
 *    分けて持っているのを取り込んだ（v29の依頼書§7で取り込むと書いた分）。
 *
 *  判定は控えめにする：**数値として壊れていないこと**を必須にし、
 *  「0では意味を成さない」項目だけ 0 を無効とする。
 *  （生活費0円はありえないが、預金0円はありうる。一律に0を弾かない。） */
const READY_NONZERO = new Set([
  "family.ageH", "income.hBase", "living.table.0.amount",
  "house.price", "house.loans.0.years", "retire.retireAgeH",
]);
function isUsable(path){
  const v = get(PARAMS, path);
  if(v === null || v === undefined || v === "") return false;
  const n = Number(v);
  if(!Number.isFinite(n)) return false;
  if(n < 0) return false;
  if(READY_NONZERO.has(path) && n === 0) return false;
  return true;
}

/** 準備度の素材。**旗と値を別々に返す**（どちらが欠けたかを言い分けるため）。 */
function readinessFacts(P){
  const src = P || PARAMS;
  const out = {};
  READY_STEPS.forEach(step => {
    (step.need || []).forEach(n => {
      const path = n[0];
      const applies = !n[2] || n[2](src);
      out[path] = {label:n[1], step:step.key, applies:applies,
                   confirmed:isConfirmed(path), valid:isUsable(path)};
    });
  });
  return out;
}

/** そのパスがどの段階に属するか。**一覧を2か所に持たないための引き当て。** */
function completionKeyForPath(path){
  for(const step of READY_STEPS)
    for(const n of (step.need || []))
      if(n[0] === path) return step.key;
  return null;
}''')

sub("C2-readiness",
'''  READY_STEPS.forEach((s, i) => {
    const need = needsOf(s, PARAMS);
    const miss = need.filter(n => !isConfirmed(n[0])).map(n => n[1]);''',
'''  READY_STEPS.forEach((s, i) => {
    const need = needsOf(s, PARAMS);
    /* ★「確認した」だけでなく「値が使える」ことも要る（v30）。
         旗だけを見ていたv29は、物件価格0円でも段階が上がった。 */
    const miss = need.filter(n => !(isConfirmed(n[0]) && isUsable(n[0]))).map(n => n[1]);''')

sub("C3-freeze",
'''/** その世帯に当てはまる必要項目だけを返す。 */
function needsOf(step, P){''',
'''/* ★正本を凍結する。実行中に書き換えられないようにして、
     「判定の元になる一覧」が1つであることを保つ（ChatGPT版V80から取り込み）。 */
READY_STEPS.forEach(s => { Object.freeze(s.need); s.need.forEach(Object.freeze); Object.freeze(s); });
Object.freeze(READY_STEPS);

/** その世帯に当てはまる必要項目だけを返す。 */
function needsOf(step, P){''')


# ---------------------------- D. 手動借入で資金差が残るとき、住宅の判断は未確定に
sub("D1-housing",
'''/** 画面に出す値。未入力のあいだ、まだ触っていない主要欄は空で見せる。''',
'''/** 住宅の判断がどこまで整っているか。
 *
 *  ★**「保存できる」と「判断に使える」を分ける**（ChatGPT版のv29レビュー §5 の助言）。
 *    v27で `underfundedIn()` を自動調整ONのプランだけに限ったのは正しかったが、
 *    その結果**手で借入を決めて資金が足りないプランが、何の断りもなく
 *    「判断の準備が整いました」に含まれる**ようになっていた。
 *    保存は許す（利用者の意思）。ただし住宅については未確定と言う。
 *
 *  返り値: "ready"（整った）／"estimate"（概算どまり）／"insufficient"（資金が足りない）
 *          ／"na"（買わないので対象外） */
function housingReadiness(P){
  const src = P || PARAMS;
  const H = src.house;
  if(!H || !H.buy) return {level:"na", gap:0, note:""};
  const gap = fundingGap(H);
  if(!Number.isFinite(gap))
    return {level:"insufficient", gap:NaN, note:"住宅資金の差額が数値になりません。"};
  if(gap > FUND_TOLERANCE)
    return {level:"insufficient", gap:gap,
            note:`住宅資金が ${Math.round(gap).toLocaleString()}円 足りません。`
               + `自己資金か借入を増やすか、物件価格を下げてください。`};
  if(gap < -FUND_TOLERANCE)
    return {level:"estimate", gap:gap,
            note:`借入が必要額より ${Math.round(-gap).toLocaleString()}円 多くなっています。`};
  return {level:"ready", gap:gap, note:""};
}

/** 画面に出す値。未入力のあいだ、まだ触っていない主要欄は空で見せる。''')

sub("D2-readiness-housing",
'''  if(out.stage === 0 && !out.missing.length)
    out.missing = READY_STEPS[0].need.map(n => n[1]);
  return out;
}''',
'''  if(out.stage === 0 && !out.missing.length)
    out.missing = READY_STEPS[0].need.map(n => n[1]);
  /* ★住宅の資金が合っていないうちは、段階3（判断の準備が整いました）と言わない。
       借入を手で決めた場合も同じ。**保存はできるが、判断はできない。** */
  const hr = housingReadiness(PARAMS);
  out.housing = hr;
  if(out.stage >= 3 && (hr.level === "insufficient" || hr.level === "estimate")){
    out.stage = 2;
    out.label = READY_STEPS[1].label;
    out.note  = hr.note + "（住宅の条件が整うと判断に使えます）";
    if(!out.missing.length) out.missing = ["住宅資金の一致"];
  }
  return out;
}''')

# ------------------------------------------------------------------ 版番号
sub("VER",
    'const VERSION = {tag:"汎用版 v29", date:"2026-09-01",',
    'const VERSION = {tag:"汎用版 v30", date:"2026-09-02",')
sub("VER-file",
    'file:"20260901_ライフプランCFシミュレーター汎用版_v29.html"};',
    'file:"20260902_ライフプランCFシミュレーター汎用版_v30.html"};')

io.open(DST, "w", encoding="utf-8").write(s)
print("当てた修正: %d件" % len(applied))
for a in applied:
    print("  -", a)
print("%s → %s" % (SRC.name, DST.name))
print("%d bytes → %d bytes（%+d）" % (orig_len, len(s), len(s) - orig_len))
