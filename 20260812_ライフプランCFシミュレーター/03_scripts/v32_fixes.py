# -*- coding: utf-8 -*-
"""汎用版 v31 → v32 の修正を当てる。

ChatGPT版のv31独立再レビュー（P1 4件・P2 2件）は**全件こちらで再現できた**ので、全件直す。

  P1-1 初回利用を破損扱いする（**依頼者の実機スクリーンショットにも出た**）
       v31は「主領域が無い」→控えを見る→控えも無い→`planbroken`（赤）を出していた。
       主領域と控えが**両方 missing なら、それは初めての利用**。静かに0件で始める。
  P1-2 控え更新が失敗すると、最後の正常な控えを失う
       新しい控えを書けなかったとき、旧控えを戻す。戻せなければ pending/marker を残す。
  P1-3 複数タブ競合の2つの窓（書込み前／読戻し後）
       revision（保存の起点）＋期限付き協調ロック＋最終読戻し＋storageイベント同期。
  P1-4 完全未入力でも住宅ローン控除が「✓ 要件を満たしています」と出る
       CF・診断はv31で抑えたが、控除ブロックが漏れていた。
  P2-1 説明ボタン名が入力値で変わる（生活費目安・年金見込みの2件）
  P2-2 受入試験JSの同梱（03_scripts/v32_accept.js）

  あわせて自分で約束した分:
  X-1  暗黙の `type="submit"` を `type="button"` にする（V87レビューでこちらも同じと書いた分）。

使い方: python 03_scripts/v32_fixes.py
"""
import io, re, sys
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
SRC = BASE / "02_output" / "20260902_ライフプランCFシミュレーター汎用版_v31.html"
DST = BASE / "02_output" / "20260902_ライフプランCFシミュレーター汎用版_v32.html"

s = io.open(SRC, encoding="utf-8").read()
orig_len = len(s)
applied = []


def sub(tag, old, new, count=1):
    global s
    n = s.count(old)
    if n != count:
        print("!! アンカー不一致 [%s]: %d件（期待 %d件）" % (tag, n, count))
        sys.exit(1)
    s = s.replace(old, new, count)
    applied.append(tag)


# ============================================== 保存キーを増やす（journal + lock）
sub("S0-STORE",
'''  plansBak:"lpcfg_plans_bak",''',
'''  plansBak:"lpcfg_plans_bak",
  /* ★控えを書けなかったときの控え候補と、その印（v32）。
       次に開いたとき、正常な主領域から控えを作り直すために使う
       （ChatGPT版のv31レビュー P1-2 の助言）。 */
  plansPending:"lpcfg_plans_pending",
  plansMarker: "lpcfg_plans_marker",
  /* ★複数タブの協調ロック。期限付きなので、タブが落ちても自然に回収される（v32）。 */
  plansLock:   "lpcfg_plans_lock",''')


# ============================================== P1-1  初回利用を破損扱いしない
sub("F1-loadPlans",
'''  /* ★主領域が無い／空文字。**控えを見る。**
       v30はここで 0件のまま戻っており、控えがあっても使わなかった
       （ChatGPT版のv30レビュー `storage.recover.missing_primary`）。 */
  recoverPlansFromBackup("見つからなかった", "主領域がありません");
}''',
'''  /* ★主領域が無い／空文字。
       ここで**控えも無ければ「初めての利用」**なので、静かに0件で始める（v32）。
       v31は無条件に復旧へ入り、控えも無いため `planbroken`（赤）を出していた。
       **初めて開いた人に「保存された内容が読み取れませんでした」と見せていた**
       （ChatGPT版のv31レビュー P1-1。依頼者の実機スクリーンショットにも出ていた）。
       直した経路（主領域欠損＋控えあり）の**隣にある正常系**を試験していなかった。 */
  const bak0 = readStore(STORE.plansBak);
  if(bak0.status !== "ok" || bak0.raw === null || bak0.raw === ""){
    PLANS = [];
    PLANS_REV = null;
    return;                     // ★知らせを出さない
  }
  recoverPlansFromBackup("見つからなかった", "主領域がありません");
}''')

# 正常読み込み時に revision を覚える
sub("F1-rev-ok",
'''    const first = parsePlansRaw(prim.raw);
    if(first.ok){ PLANS = first.list; return; }
    recoverPlansFromBackup("壊れていた", first.why);
    return;''',
'''    const first = parsePlansRaw(prim.raw);
    if(first.ok){
      PLANS = first.list;
      PLANS_REV = prim.raw;     /* ★保存の起点として覚える（P1-3） */
      repairBackupIfMarked(prim.raw);
      return;
    }
    recoverPlansFromBackup("壊れていた", first.why);
    return;''')

sub("F1-rev-unreadable",
'''  if(prim.status === "unreadable"){
    PLANS = [];''',
'''  if(prim.status === "unreadable"){
    PLANS = [];
    PLANS_REV = null;''')

sub("F1-rev-recover",
'''  PLANS = parsed.list;
  /* ★書き戻しも読み戻して確かめる。''',
'''  PLANS = parsed.list;
  PLANS_REV = bak.raw;          /* ★復旧した内容を保存の起点にする */
  /* ★書き戻しも読み戻して確かめる。''')

sub("F1-rev-broken",
'''  if(!parsed.ok){
    PLANS = [];
    pushNotice("planbroken", "bad",''',
'''  if(!parsed.ok){
    PLANS = [];
    PLANS_REV = null;
    pushNotice("planbroken", "bad",''')


# ==================================== P1-2 / P1-3  revision・ロック・控えの保全
sub("F2-helpers",
'''/** 保存領域を、書く前の生の値へ戻す。戻せたかを返す。''',
'''/* ============================================================
   保存の同時実行と控えの保全（v32）
   ------------------------------------------------------------
   ★v31は「主領域を1回読み戻す」だけで競合を見ていたため、
     **2つの窓**を取りこぼした（ChatGPT版のv31レビュー P1-3）。
     ① 保存の起点を取ったあと、自分が書く前に別タブが書いた
        → 自分の内容で**別タブの保存を消していた**（実測：`[旧,別タブ]`→`[旧,このタブ]`）
     ② 主領域の読み戻しに成功したあと、控えを更新する前に別タブが書いた
        → primary `[旧,別タブ]` / backup `[旧,このタブ]` / メモリ `[旧,このタブ]` の**三者不一致**
     どちらも保存は成功と表示され、知らせも出なかった。
   ★対策は3つ重ねる。
     (a) **revision**：`PLANS` を作った時点の主領域の生値を覚え、書く前に一致を確かめる
         （＝compare-and-set。これが①を止める）
     (b) **期限付き協調ロック**：同じ版のタブ同士が同時に書き始めないようにする。
         期限を持たせるので、タブが落ちても自然に回収される
     (c) **最終読み戻し**：控えを書く前後にもう一度主領域を確かめる（これが②を止める）
   ★localStorage に本物のCASは無いので、これで「完全」にはならない。
     同じ版のタブ同士の事故を減らすところまで、と割り切って書く。
   ============================================================ */

/** このタブを見分ける値。保存のたびに作り直さない。 */
const TAB_ID = "t" + Date.now().toString(36) + Math.random().toString(36).slice(2, 8);

/** `PLANS` を作った時点の主領域の生値。null は「まだ保存が無い」。 */
let PLANS_REV = null;

const LOCK_MS = 4000;

function lockRead(){
  const r = readStore(STORE.plansLock);
  if(r.status !== "ok" || !r.raw) return null;
  try{
    const o = JSON.parse(r.raw);
    return (o && typeof o === "object" && Number.isFinite(o.until)) ? o : null;
  }catch(e){ return null; }
}
/** ロックを取る。期限内の他タブが持っていれば false。 */
function lockAcquire(){
  const cur = lockRead(), now = Date.now();
  if(cur && cur.until > now && cur.id !== TAB_ID) return false;
  if(!writeStoreVerified(STORE.plansLock, JSON.stringify({id:TAB_ID, until:now + LOCK_MS})))
    return false;
  const back = lockRead();
  return !!back && back.id === TAB_ID;
}
function lockRelease(){
  const cur = lockRead();
  if(cur && cur.id === TAB_ID){ try{ localStorage.removeItem(STORE.plansLock); }catch(e){} }
}

/** 控えを新しい内容へ更新する。失敗したら**旧控えを戻す**。
 *  戻せなければ pending と marker を残し、次回起動で作り直す。 */
function updateBackup(payload){
  const before = readStore(STORE.plansBak);
  if(writeStoreVerified(STORE.plansBak, payload)){
    try{ localStorage.removeItem(STORE.plansPending); }catch(e){}
    try{ localStorage.removeItem(STORE.plansMarker); }catch(e){}
    NOTICES = NOTICES.filter(n => n.id !== "planbakfail");
    return {ok:true, keptOld:false};
  }
  /* ★新しい控えが書けなかった。**古い控えを取り戻す。**
       v31はここで何もせず、静かに壊れた控え（`[]`）が残っていた。 */
  let keptOld = false;
  if(before.status === "ok" && before.raw !== null)
    keptOld = writeStoreVerified(STORE.plansBak, before.raw);
  if(!keptOld){
    try{ localStorage.setItem(STORE.plansPending, payload); }catch(e){}
    try{ localStorage.setItem(STORE.plansMarker,
      JSON.stringify({at:Date.now(), why:"backup-write-failed"})); }catch(e){}
  }
  pushNotice("planbakfail", "warn",
    `<b>保存はできましたが、控えを更新できませんでした。</b>`
    + `<span class="hint">`
    + (keptOld ? `控えは<b>ひとつ前の内容のまま</b>残しています。`
               : `控えを作り直す印を残しました。次に開いたときに作り直します。`)
    + `保存領域が壊れたときに戻せる範囲が狭くなっています。`
    + `大事な条件は「書き出す」でファイルにも残してください。</span>`);
  return {ok:false, keptOld:keptOld};
}

/** 印が残っていれば、正常な主領域から控えを作り直す（次回起動時の修復）。 */
function repairBackupIfMarked(primaryRaw){
  const mark = readStore(STORE.plansMarker);
  if(mark.status !== "ok" || !mark.raw) return;
  if(writeStoreVerified(STORE.plansBak, primaryRaw)){
    try{ localStorage.removeItem(STORE.plansPending); }catch(e){}
    try{ localStorage.removeItem(STORE.plansMarker); }catch(e){}
    pushNotice("planbakrepair", "info",
      `<b>控えを作り直しました。</b>`
      + `<span class="hint">前回、控えの更新に失敗した記録が残っていました。`
      + `いま保存されている内容から作り直したので、対処は要りません。</span>`);
  }
}

/** 別タブが保存した内容を、この画面に取り込む。 */
function adoptForeignPlans(raw, list){
  PLANS = list;
  PLANS_REV = raw;
  pushNotice("planconflict", "warn",
    `<b>別のタブで保存内容が更新されたため、今回の保存は行いませんでした。</b>`
    + `<span class="hint">画面の一覧を、いま保存されている${list.length}件に合わせました。`
    + `必要な変更をもう一度行って保存してください。</span>`);
}

/** 別タブの保存を検知して画面を合わせる（storageイベント）。 */
if(typeof window !== "undefined" && window.addEventListener){
  window.addEventListener("storage", function(ev){
    if(!ev || ev.key !== STORE.plans) return;
    const raw = ev.newValue;
    if(raw === null || raw === "" || raw === PLANS_REV) return;
    const parsed = parsePlansRaw(raw);
    if(!parsed.ok) return;                 /* 壊れた値は取り込まない */
    PLANS = parsed.list;
    PLANS_REV = raw;
    pushNotice("planexternal", "info",
      `<b>別のタブで保存内容が変わりました（${parsed.list.length}件）。</b>`
      + `<span class="hint">この画面の一覧をそちらに合わせました。</span>`);
    if(typeof render === "function") render();
  });
}

/** 保存領域を、書く前の生の値へ戻す。戻せたかを返す。''')

# commitPlans を revision + lock + 最終読戻し へ組み替える
sub("F3-commit",
'''  /* ★書く前の生の値を revision として控える。失敗したときに戻すため、
       かつ「別のタブが書いた内容」と「自分が書く前の内容」を見分けるため。 */
  const beforeRead = readStore(STORE.plans);
  const before = (beforeRead.status === "ok") ? beforeRead.raw : null;
  try{
    const payload = JSON.stringify(nextPlans);
    localStorage.setItem(STORE.plans, payload);''',
'''  /* ★同じ版のタブ同士が同時に書き始めないよう、期限付きロックを取る（v32）。 */
  if(!lockAcquire()){
    pushNotice("planlock", "warn",
      `<b>別のタブが保存中のため、今回の保存は行いませんでした。</b>`
      + `<span class="hint">数秒おいてから、もう一度保存してください。</span>`);
    return false;
  }
  try{
  /* ★書く前の生の値を revision として控える。失敗したときに戻すため、
       かつ「別のタブが書いた内容」と「自分が書く前の内容」を見分けるため。 */
  const beforeRead = readStore(STORE.plans);
  const before = (beforeRead.status === "ok") ? beforeRead.raw : null;
  /* ★いまの主領域が、`PLANS` を作った時点（revision）と同じかを確かめる。
       違っていれば、別タブが保存している。**自分の内容で上書きしない。**
       これが「保存の起点を取ったあと、自分が書く前に別タブが書いた」窓を塞ぐ。 */
  if(PLANS_REV !== null && before !== null && before !== PLANS_REV){
    const other = parsePlansRaw(before);
    if(other.ok){ adoptForeignPlans(before, other.list); return false; }
  }
  try{
    const payload = JSON.stringify(nextPlans);
    localStorage.setItem(STORE.plans, payload);''')

sub("F3-commit-tail",
'''    PLANS = nextPlans;
    /* ★主領域を書けたことを確かめた**あと**で控えを更新する。
         先に控えを書くと、主領域の書き込みが失敗したときに
         控えまで新しい壊れかけの内容になってしまう。
         控えが書けなくても保存そのものは成功として扱う（控えは保険）。
         ただし**控えも読み戻して確かめ、ずれていたら黙っていない**（v31）。
         v30は例外の有無だけを見ていたため、控えが静かに `[]` になっても
         「保存成功・控えあり」と扱っていた。 */
    if(!writeStoreVerified(STORE.plansBak, payload))
      pushNotice("planbakfail", "warn",
        `<b>保存はできましたが、控えを更新できませんでした。</b>`
        + `<span class="hint">保存領域が壊れたときに戻せない状態です。`
        + `大事な条件は「書き出す」でファイルにも残してください。</span>`);
    else
      /* ★成功したら前回の警告を取り下げる。`dismissNotice()` は render() を呼ぶので
           保存の途中では使わない（描画の再入を作らない）。 */
      NOTICES = NOTICES.filter(n => n.id !== "planbakfail");
    return true;''',
'''    /* ★控えを更新する**前**に、主領域をもう一度確かめる（v32）。
         読み戻しに成功したあと・控えを書く前に別タブが書くと、
         v31は primary／backup／メモリが三者不一致になったまま「成功」を返していた。 */
    const midRead = readStore(STORE.plans);
    if(midRead.status === "ok" && midRead.raw !== payload){
      const other = parsePlansRaw(midRead.raw);
      if(other.ok){
        /* 別タブが有効な内容を書いた。**控えもメモリもそちらに合わせる。** */
        updateBackup(midRead.raw);
        adoptForeignPlans(midRead.raw, other.list);
        return false;
      }
    }
    PLANS = nextPlans;
    PLANS_REV = payload;
    /* ★主領域を書けたことを確かめた**あと**で控えを更新する。
         控えが書けなくても保存そのものは成功として扱う（控えは保険）。
         ただし**旧控えを失わない**（v32・`updateBackup`）。 */
    updateBackup(payload);
    return true;''')

sub("F3-commit-catch",
'''    const restored = restorePlansRaw(before);
    noticeStoreFailed(e, restored);
    return false;   // ★PLANS は触らない（元の一覧のまま）
  }
}''',
'''    const restored = restorePlansRaw(before);
    noticeStoreFailed(e, restored);
    return false;   // ★PLANS は触らない（元の一覧のまま）
  }
  }finally{ lockRelease(); }
}''')


# ============================ P1-4  未入力で住宅ローン控除の肯定結論を出さない
sub("F4-deduction",
'''  const allOK = items.every(x => x.ok);
  return `<div class="hint" data-foldname="住宅ローン控除の要件と控除額"''',
'''  /* ★未入力・住宅購入なし・物件価格0・借入0では**判定しない**（v32）。
       v31は完全未入力でも「✓ 要件を満たしています／控除される総額 0万円」と出しており、
       0円を「適合」と読ませていた（ChatGPT版のv31レビュー P1-4）。
       CF表と診断はv31で抑えたのに、**この控除ブロックだけ漏れていた**。
       「症状の出た場所だけを覆っていないか」を、直すたびに確かめる。 */
  const loanSum = (Array.isArray(H.loans) ? H.loans : [])
                    .reduce((a, l) => a + (Number(l.amount) || 0), 0);
  if(isBlank(P) || !H.buy || !(Number(H.price) > 0) || !(loanSum > 0)){
    return `<div class="hint" data-foldname="住宅ローン控除の要件と控除額"
      style="margin:8px 0; padding:8px 9px; background:var(--panel2); border-radius:4px; line-height:1.9">
      <b>まだ判定できません。</b>
      <span class="hint">住宅購入をONにして、物件価格と借入額を入れると、
      住宅ローン控除の要件と控除額をここに出します。
      いまの0円は計算の結果ではなく未入力の状態です。</span></div>`;
  }
  const allOK = items.every(x => x.ok);
  return `<div class="hint" data-foldname="住宅ローン控除の要件と控除額"''')


# ==================================== P2-1  説明ボタン名に計算値を入れない（2件）
sub("F5-living",
'''      + `<div class="hint" style="margin-top:7px; display:flex; gap:8px;
            align-items:center; flex-wrap:wrap">
          <button class="btn sec sm" onclick="applyLivingByHeadcount()">''',
'''      + `<div class="hint" data-foldname="世帯人数別の生活費目安"
            style="margin-top:7px; display:flex; gap:8px;
            align-items:center; flex-wrap:wrap">
          <button class="btn sec sm" type="button" onclick="applyLivingByHeadcount()">''')

sub("F5-pension",
'''  return `<div class="hint" style="margin:7px 0; padding:8px 9px; background:var(--panel2); border-radius:4px; line-height:1.9">
    ${line("あなた", h, P.retire.otherPensionH||0)}<br>''',
'''  return `<div class="hint" data-foldname="年金見込み額と計算前提"
    style="margin:7px 0; padding:8px 9px; background:var(--panel2); border-radius:4px; line-height:1.9">
    ${line("あなた", h, P.retire.otherPensionH||0)}<br>''')


# ================================ X-1  暗黙の type="submit" を type="button" に
#  ★V87レビューで「こちらも45件中27件が同じ状態」と書いた分を揃える。
#    `<form>` は1つも無いので実害は無いが、指摘した標準は自分にも当てる。
#
#  ★最初は `<button` を無条件に一括置換して**HTMLを壊した**
#    （SyntaxError: Unexpected identifier 'button'）。
#    1090行に**二重引用符のJS文字列の中**の `<button` が1件あり、
#    そこへ `type="button"` を入れると、文字列がその場で閉じてしまう。
#    CLAUDE.mdの「属性を足すときは開始タグ全体をアンカーにする」の兄弟で、
#    **一括置換は、その文字列がどの引用符で囲まれているかを見ないと壊れる。**
#    → 直前が `"` の `"<button` は一括対象から外し、その1件だけ別に手当てする。
BTN_RE = r'<button(?![^>]*\btype=)'
before_btn = len(re.findall(BTN_RE, s))
s = re.sub(r'(?<!")' + BTN_RE, '<button type="button"', s)

# 二重引用符の文字列の中にある1件は、エスケープした引用符で入れる
ESC_OLD = '+ "<button onclick=\\"this.parentNode.style.display=' + "'none'" + '\\" "'
ESC_NEW = '+ "<button type=\\"button\\" onclick=\\"this.parentNode.style.display=' + "'none'" + '\\" "'
sub("X1-escaped", ESC_OLD, ESC_NEW)

after_btn = len(re.findall(BTN_RE, s))
applied.append("X1-button-type（%d件 → 残り%d件）" % (before_btn, after_btn))


# ------------------------------------------------------------------ 版番号
sub("VER",
    'const VERSION = {tag:"汎用版 v31", date:"2026-09-02",',
    'const VERSION = {tag:"汎用版 v32", date:"2026-09-02",')
sub("VER-file",
    'file:"20260902_ライフプランCFシミュレーター汎用版_v31.html"};',
    'file:"20260902_ライフプランCFシミュレーター汎用版_v32.html"};')

io.open(DST, "w", encoding="utf-8").write(s)
print("当てた修正: %d件" % len(applied))
for a in applied:
    print("  -", a)
print("%s → %s" % (SRC.name, DST.name))
print("%d bytes → %d bytes（%+d）" % (orig_len, len(s), len(s) - orig_len))
