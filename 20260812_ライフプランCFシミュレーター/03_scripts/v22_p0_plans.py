# -*- coding: utf-8 -*-
r"""v22 patch A：P0-1／P0-2（保存の全経路をトランザクションにする）。

**何が起きていたか**
v19で `putPlan()` を「`PLANS` を書き換えず候補配列を返すだけ」の純粋関数に変え、
`savePlan()` だけを `commitPlans(withPlan(...))` に移行した。
**残る5経路は戻り値を捨てたまま**で、そのあと `storePlans()` を呼んでいた。
`storePlans()` は変わっていない `PLANS` を書くので、**1件も増えない。**
それなのに「4件作りました」「1件読み込みました」と表示していた。

  - loadAllWScenarios / loadAllSavingPlans / loadRaisePatterns
  - importPlans / newPropertyPlan

さらに、次の3経路は `PLANS` を**直接**書き換えてから保存していたため、
保存に失敗すると画面だけ増える（幽霊プラン）。

  - loadAllPresets（ループ内で `PLANS = next`）
  - makeCombos / sweepPrice（`PLANS.push()`）
  - setPlanMemo（保存前に `PLANS[i].params.meta.memo` を書き換え）

★私はv21で「保存系をトランザクション化」と報告した。**helperだけを直し、
  呼出側の移行を確かめていなかった。** 外部レビューで検出された。

**直し方（1つの型に統一する）**
  1. `withPlanIn(list, params, name)` … 任意の配列に足した**新しい配列**を返す
  2. 候補を全部積み上げる
  3. `commitPlans(candidate)` が true のときだけ画面反映・成功表示
`storePlans()` は呼び出し元が0になるので削除する（再発の入口を残さない）。
"""
import io
import sys
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
ROOT = Path(__file__).resolve().parent.parent
P = ROOT / "02_output" / "20260831_ライフプランCFシミュレーター汎用版_v22.html"
t = P.read_text(encoding="utf-8")
ng = []


def sub(old, new, label, count=1):
    global t
    c = t.count(old)
    if c == count:
        t = t.replace(old, new, count)
    else:
        ng.append(f"{label} ({c}件/期待{count})")


# ---- 1. storePlans() を削除する（呼び出し元を0にしたうえで） ----
sub('''/** 保存済みプランをブラウザに書き込む。**成否を返す。**
 *
 *  ★v4まではここで catch(e){} と例外を握りつぶし、呼び出し元が
 *    無条件に「保存しました」と表示していた。プライベートブラウズや
 *    保存容量がいっぱいの端末で、**保存できていないのに成功したように見えていた。**
 *  ★呼び出し元は15箇所ある。**そのすべてを直すのではなく、ここで成否を返す。**
 *  ★知らせは一度だけ出す（操作のたびに出すと邪魔になる）。
 *    「保存」を明示的に押したときは savePlan() が毎回きちんと伝える。
 *  ★テーマ・表示切替・ウィザード完了フラグの保存は黙って失敗してよいので触っていない
 *    （失われても害がなく、警告を出すほうが邪魔になる）。 */
let STORE_WARNED = false;
function storePlans(){
  try{
    localStorage.setItem(STORE.plans, JSON.stringify(PLANS));
    return true;
  }catch(e){
    /* ★v7から：alert ではなく画面に残す（V63から取り込み）。
       alert は閉じた瞬間に消え、「保存したつもり」に戻ってしまう。
       理由で文言を変え、その場からファイル書き出しへ進めるようにする。 */
    noticeStoreFailed(e);
    return false;
  }
}''',
    '''/* ★v22で `storePlans()` を削除した。
     この関数は「いまの `PLANS` をそのまま書き出す」ものだったため、
     **呼ぶ前に `PLANS` を書き換えておく**という使い方を誘発した。
     保存に失敗すると画面だけ増える（幽霊プラン）。
     保存は `commitPlans(候補配列)` の1経路だけにする。
     知らせを一度だけにするための旗はそちらへ移した。 */
let STORE_WARNED = false;''',
    "storePlans を削除")

# ---- 2. withPlanIn / withPlan、putPlan の削除 ----
sub('''/** 保存の候補配列を作る（この時点では `PLANS` を変えない）。 */
function withPlan(params, name){
  const nm = name || params.meta.planName;
  const next = PLANS.slice();
  const i = next.findIndex(x => x.name === nm);
  const rec = {name:nm, params:clone(params)};
  if(i >= 0) next[i] = rec; else next.push(rec);
  return next;
}

/** 従来の呼び出し互換。**単体で使うと保存の成否を返さない**ので、
 *  新しい経路では `commitPlans(withPlan(...))` を使うこと。 */
function putPlan(params, name){
  return withPlan(params, name);
}''',
    '''/** 任意の候補配列にプランを足した**新しい配列**を返す（元の配列は変えない）。
 *
 *  ★v21まで `withPlan()` しかなく、必ず `PLANS` を起点にしていた。
 *    そのため「まとめて4件作る」ときは、途中で `PLANS` を書き換えながら
 *    積み上げるしかなく、失敗しても戻せなかった。
 *    **積み上げの起点を引数で受ければ、`PLANS` に触らずに全件を作れる。** */
function withPlanIn(list, params, name){
  const nm = name || params.meta.planName;
  const next = (list || []).slice();
  const i = next.findIndex(x => x.name === nm);
  const rec = {name:nm, params:clone(params)};
  if(i >= 0) next[i] = rec; else next.push(rec);
  return next;
}

/** 1件だけ足す場合の入口（いまの `PLANS` が起点）。 */
function withPlan(params, name){
  return withPlanIn(PLANS, params, name);
}''',
    "withPlanIn を追加し putPlan を削除")

# ---- 3. loadAllPresets ----
sub('''function loadAllPresets(){
  let next = PLANS;
  PRESET_KEYS.forEach(k => { PLANS = next; next = withPlan(defaults(k, PARAMS.meta.wScenario)); });
  commitPlans(next);
  setTab("compare");
  flash(`<b>住宅プランをまとめて作りました</b>（計 ${PLANS.length} 件）。すぐ下の表に並んでいます。`);
}''',
    '''function loadAllPresets(){
  /* ★v21までループの中で `PLANS = next` としており、保存に失敗しても
     途中まで書き換えた `PLANS` が残っていた。候補配列だけで積み上げる。 */
  let next = PLANS;
  PRESET_KEYS.forEach(k => { next = withPlanIn(next, defaults(k, PARAMS.meta.wScenario)); });
  if(!commitPlans(next)) return;      // 失敗したら画面も表示も動かさない
  setTab("compare");
  flash(`<b>住宅プランをまとめて作りました</b>（計 ${PLANS.length} 件）。すぐ下の表に並んでいます。`);
}''',
    "loadAllPresets")

# ---- 4. loadAllWScenarios ----
sub('''function loadAllWScenarios(){
  WSCENARIO_KEYS.forEach(k => {
    const p = defaults(PARAMS.meta.preset || DEFAULT_PRESET, k);
    // いま編集中の住宅条件を引き継ぐ（プリセットから変更している場合に対応）
    p.house = clone(PARAMS.house);
    p.estate = clone(PARAMS.estate);
    p.meta.planName = autoPlanName(p);
    putPlan(p);
  });
  storePlans();
  setTab("compare");
  flash(`<b>パートナーの収入パターンをまとめて作りました</b>（計 ${PLANS.length} 件）。すぐ下の表に並んでいます。`);
}''',
    '''function loadAllWScenarios(){
  let next = PLANS;
  WSCENARIO_KEYS.forEach(k => {
    const p = defaults(PARAMS.meta.preset || DEFAULT_PRESET, k);
    // いま編集中の住宅条件を引き継ぐ（プリセットから変更している場合に対応）
    p.house = clone(PARAMS.house);
    p.estate = clone(PARAMS.estate);
    p.meta.planName = autoPlanName(p);
    next = withPlanIn(next, p);
  });
  if(!commitPlans(next)) return;
  setTab("compare");
  flash(`<b>パートナーの収入パターンをまとめて作りました</b>（計 ${PLANS.length} 件）。すぐ下の表に並んでいます。`);
}''',
    "loadAllWScenarios")

# ---- 5. setPlanMemo ----
sub('''function setPlanMemo(i, v){
  if(!PLANS[i]) return;
  PLANS[i].params.meta.memo = v;
  if(PLANS[i].name === PARAMS.meta.planName) PARAMS.meta.memo = v;
  storePlans();
}''',
    '''function setPlanMemo(i, v){
  if(!PLANS[i]) return;
  /* ★v21まで `PLANS` を直接書き換えてから保存していた。保存に失敗すると
     画面は新しいメモ、開き直すと古いメモになる。複製に当ててから保存する。 */
  const next = PLANS.slice();
  next[i] = clone(next[i]);
  next[i].params.meta.memo = v;
  if(!commitPlans(next)) return;
  if(PLANS[i].name === PARAMS.meta.planName) PARAMS.meta.memo = v;
}''',
    "setPlanMemo")

# ---- 6. importPlans ----
sub('''      const add = migratePlans(d.plans);
      add.forEach(p => putPlan(p.params, p.name));
      storePlans();
      if(d.current && d.current.params){''',
    '''      const add = migratePlans(d.plans);
      let next = PLANS;
      add.forEach(p => { next = withPlanIn(next, p.params, p.name); });
      /* ★保存できなかったら、読み込んだことにしない（件数表示も出さない）。 */
      if(!commitPlans(next)){ input.value = ""; return; }
      if(d.current && d.current.params){''',
    "importPlans")

# ---- 7. loadAllSavingPlans ----
sub('''function loadAllSavingPlans(){
  const made = [];
  SAVINGPLAN_KEYS.forEach(k => {
    const p = clone(PARAMS);
    setSavingPlan(p, k);
    const name = autoPlanName(p);
    p.meta.planName = name;
    p.meta.memo = SAVINGPLAN[k].note;
    putPlan(p, name);
    made.push(name);
  });
  storePlans();
  setTab("compare");''',
    '''function loadAllSavingPlans(){
  const made = [];
  let next = PLANS;
  SAVINGPLAN_KEYS.forEach(k => {
    const p = clone(PARAMS);
    setSavingPlan(p, k);
    const name = autoPlanName(p);
    p.meta.planName = name;
    p.meta.memo = SAVINGPLAN[k].note;
    next = withPlanIn(next, p, name);
    made.push(name);
  });
  if(!commitPlans(next)) return;
  setTab("compare");''',
    "loadAllSavingPlans")

# ---- 8. makeCombos ----
sub('''      const i = PLANS.findIndex(x => x.name === name);
      const rec = {name, params:p};
      if(i >= 0) PLANS[i] = rec; else PLANS.push(rec);
      made.push(name);
    });
  });
  storePlans();
  return made;
}''',
    '''      next = withPlanIn(next, p, name);
      made.push(name);
    });
  });
  if(!commitPlans(next)) return [];   // 保存できなければ「作った」と言わない
  return made;
}''',
    "makeCombos 本体")
sub('''function makeCombos(houses, incomes, hIncome){
  const made = [];''',
    '''function makeCombos(houses, incomes, hIncome){
  const made = [];
  let next = PLANS;''',
    "makeCombos 先頭")

# ---- 9. loadRaisePatterns ----
sub('''function loadRaisePatterns(){
  const made = [];
  HINCOME_KEYS.forEach(hk => {
    if(hk === "custom") return;          // 「自分で入れる」は自動生成の対象外
    const p = clone(PARAMS);
    p.meta.hIncome = hk;
    p.income.hTable = hTableOf(hk, p);
    const name = autoPlanName(p);
    p.meta.planName = name;
    p.meta.memo = "あなたの昇給：" + HINCOME[hk].note;
    putPlan(p, name);
    made.push(name);
  });
  storePlans();
  setTab("compare");''',
    '''function loadRaisePatterns(){
  const made = [];
  let next = PLANS;
  HINCOME_KEYS.forEach(hk => {
    if(hk === "custom") return;          // 「自分で入れる」は自動生成の対象外
    const p = clone(PARAMS);
    p.meta.hIncome = hk;
    p.income.hTable = hTableOf(hk, p);
    const name = autoPlanName(p);
    p.meta.planName = name;
    p.meta.memo = "あなたの昇給：" + HINCOME[hk].note;
    next = withPlanIn(next, p, name);
    made.push(name);
  });
  if(!commitPlans(next)) return;
  setTab("compare");''',
    "loadRaisePatterns")

# ---- 10. newPropertyPlan ----
sub('''  putPlan(P, nm);
  storePlans();
  recalc();
  alert("「" + nm + "」を保存しました。" + NL + NL''',
    '''  if(!commitPlans(withPlan(P, nm))){ recalc(); return; }
  recalc();
  alert("「" + nm + "」を保存しました。" + NL + NL''',
    "newPropertyPlan")

# ---- 11. sweepPrice ----
sub('''    const j = PLANS.findIndex(x => x.name === p.meta.planName);
    const rec = {name:p.meta.planName, params:p};
    if(j >= 0) PLANS[j] = rec; else PLANS.push(rec);
    names.push(p.meta.planName);
  });
  storePlans();
  setTab("compare");''',
    '''    next = withPlanIn(next, p, p.meta.planName);
    names.push(p.meta.planName);
  });
  if(!commitPlans(next)) return;
  setTab("compare");''',
    "sweepPrice 本体")
sub('''  const names = [];
  list.forEach((manPrice, i) => {
    const p = clone(PARAMS);
    p.house.price = manPrice * MAN;''',
    '''  const names = [];
  let next = PLANS;
  list.forEach((manPrice, i) => {
    const p = clone(PARAMS);
    p.house.price = manPrice * MAN;''',
    "sweepPrice 先頭")

if ng:
    print("NG:", " / ".join(ng))
    sys.exit(1)
P.write_text(t, encoding="utf-8")

# 呼び出し元が残っていないことを確かめる
for bad in ("storePlans(", "putPlan("):
    n = t.count(bad)
    print(f"  残存 {bad} : {n}件")
print("OK v22 patch A（保存の全経路をトランザクション化）")
