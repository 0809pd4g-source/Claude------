# -*- coding: utf-8 -*-
r"""v23 patch A：P0-1（比較プランが「1項目だけ」でなく、別世帯へ差し替わる）。

**何が起きていたか**
画面はこう約束している。

  「いまの住宅プランはそのままで、**パートナーの収入だけ**を…変えたプランを作ります」
  「**いまの条件で**住宅を購入した場合と、賃貸を続けた場合を並べます」

ところが実装は `defaults(...)` から**新しい世帯を作り直して**いた。

    const p = defaults(PARAMS.meta.preset || DEFAULT_PRESET, k);
    p.house  = clone(PARAMS.house);      // 住宅だけは引き継ぐ
    p.estate = clone(PARAMS.estate);

引き継ぐのは住宅と不動産だけ。年齢・子ども・本人の年収・生活費・預金・運用・
積立・リタイア年齢・働き方は、**汎用の既定値に戻る**。

実測（44歳／42歳・子1人・本人777万・生活費444万・預金1,234万で比較を作る）:

  年齢44→35 ／ 42→35 ／ 子1人→0人 ／ 本人777万→500万 ／ 生活費444万→300万
  預金1,234万→800万 ／ 運用567万→0 ／ NISA月12,345→0 ／ リタイア67→65

**比較軸以外が動くので、結論が逆転する。**
外部レビューの実測では、枯渇75歳・最終−9,290万円の家計が、
生成後は枯渇90歳・最終−1,122万円、住宅プランでは枯渇なし・+3,278万円になった。

★これは「保存できたか」を数える試験では絶対に見つからない。件数は正しいから。
  **中身が正しいか（比較軸以外が不変か）を測る試験がなかった。**

**直し方**
`clone(PARAMS)` を起点にし、その軸に属するパスだけを変える。
許可パスは `COMPARE_ALLOWED` に1か所で持ち、受入試験がそれを読む
（表示文言と検査が同じ定義を見る）。
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


# ---- 1. 許可パスの台帳と、軸ごとのプラン生成 ----
sub('''function loadAllPresets(){
  /* ★v21までループの中で `PLANS = next` としており、保存に失敗しても
     途中まで書き換えた `PLANS` が残っていた。候補配列だけで積み上げる。 */
  let next = PLANS;
  PRESET_KEYS.forEach(k => { next = withPlanIn(next, defaults(k, PARAMS.meta.wScenario)); });
  if(!commitPlans(next)) return;      // 失敗したら画面も表示も動かさない
  setTab("compare");
  flash(`<b>住宅プランをまとめて作りました</b>（計 ${PLANS.length} 件）。すぐ下の表に並んでいます。`);
}
/** パートナーの収入シナリオA〜Eをまとめて保存し、比較タブを開く */
function loadAllWScenarios(){
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
    '''/** まとめて作るプランで、**その軸として変わってよいパス**の台帳。
 *
 *  ★v22まで `loadAllWScenarios` / `loadAllPresets` が `defaults()` から
 *    新しい世帯を作り直しており、**年齢・子ども・本人の年収・生活費・預金・
 *    運用・積立・リタイア年齢まで汎用の既定値に戻っていた**（P0-1）。
 *    画面は「パートナーの収入だけ」と書いているのに別世帯になる。
 *    比較軸以外が動くと結論が逆転するため、
 *    **どのパスが変わってよいかを1か所に書き、受入試験もここを読む。**
 *  ★`meta.planName` / `meta.memo` はどの軸でも変わる（名前と説明なので）。 */
const COMPARE_COMMON = ["meta.planName", "meta.memo"];
const COMPARE_ALLOWED = {
  loadAllWScenarios: COMPARE_COMMON.concat(["meta.wScenario", "income.wTable"]),
  loadAllPresets:    COMPARE_COMMON.concat(["meta.preset", "meta.hIncome",
                                            "house", "estate", "living.insuranceAfter",
                                            "retire"]),
  loadRaisePatterns: COMPARE_COMMON.concat(["meta.hIncome", "income.hTable"]),
  loadAllSavingPlans:COMPARE_COMMON.concat(["saving"]),
  sweepPrice:        COMPARE_COMMON.concat(["house.price", "house.loans", "house.fees"]),
};

/** いまの家計を起点に、パートナーの収入シナリオだけを差し替えたプランを作る。 */
function planWithWScenario(base, key){
  const p = clone(base);
  const ws = WSCENARIOS[key];
  p.meta.wScenario = key;
  /* 「自分で入れる」は表を触らない（利用者が入れた表をそのまま使う）。 */
  if(key !== "custom"){
    const t = wTableOf(key, p);
    if(t) p.income.wTable = t;
  }
  p.meta.planName = autoPlanName(p);
  p.meta.memo = "パートナーの収入：" + ((ws && ws.note) || key);
  return p;
}

/** いまの家計を起点に、住まい（住宅プリセット）だけを差し替えたプランを作る。 */
function planWithPreset(base, key){
  const p = clone(base);
  const pre = PRESETS[key];
  p.meta.preset = key;
  if(pre){
    if(pre.house) Object.assign(p.house, clone(pre.house));
    if(pre.estate) Object.assign(p.estate, clone(pre.estate));
    if(pre.incomeH && HINCOME[pre.incomeH]) p.meta.hIncome = pre.incomeH;
    if(pre.retire) Object.assign(p.retire, clone(pre.retire));
    if(pre.insuranceAfter) p.living.insuranceAfter = pre.insuranceAfter;
  }
  /* 保険料を年齢別で持っている世帯は、物件が変わると火災保険の想定も変わる。 */
  if(p.living.insMode === "table") insGuideTable(p);
  p.meta.planName = autoPlanName(p);
  p.meta.memo = (pre && pre.note) || "";
  return p;
}

function loadAllPresets(){
  /* ★いまの家計を起点にする。`defaults()` から作り直さない（P0-1）。 */
  let next = PLANS;
  PRESET_KEYS.forEach(k => { next = withPlanIn(next, planWithPreset(PARAMS, k)); });
  if(!commitPlans(next)) return;      // 失敗したら画面も表示も動かさない
  setTab("compare");
  flash(`<b>住宅プランをまとめて作りました</b>（計 ${PLANS.length} 件）。`
    + `すぐ下の表に並んでいます。<br>`
    + `<span class="hint">いまの家計（年齢・収入・生活費・資産）はそのままで、`
    + `<b>住まいだけ</b>を変えています。</span>`);
}
/** パートナーの収入シナリオをまとめて保存し、比較タブを開く */
function loadAllWScenarios(){
  /* ★パートナーがいない世帯で「パートナーの収入」を作らない。
     v22までは、ひとり暮らしでも**パートナーあり・年収400万円の7件**を生成していた。 */
  if(!PARAMS.family.hasSpouse){
    setTab("compare");
    flash(`<b>この世帯にはパートナーがいないため、パートナーの収入の比較は作れません。</b><br>`
      + `<span class="hint">「パラメータ」の「世帯の形」でパートナーありに変えると使えます。</span>`);
    return;
  }
  let next = PLANS;
  WSCENARIO_KEYS.forEach(k => { next = withPlanIn(next, planWithWScenario(PARAMS, k)); });
  if(!commitPlans(next)) return;
  setTab("compare");
  flash(`<b>パートナーの収入パターンをまとめて作りました</b>（計 ${PLANS.length} 件）。`
    + `すぐ下の表に並んでいます。<br>`
    + `<span class="hint">いまの家計はそのままで、<b>パートナーの収入だけ</b>を変えています。</span>`);
}''',
    "比較プランを現在の家計から作る")

# ---- 2. 使われていない makeCombos を削除する ----
MAKE_COMBOS_HEAD = '''/** 物件とパートナーの収入の組み合わせをまとめて作る共通処理。
 *  hIncome を渡すとあなたの昇給も指定できる。 */
function makeCombos(houses, incomes, hIncome){'''
if t.count(MAKE_COMBOS_HEAD) != 1:
    ng.append(f"makeCombos の先頭 ({t.count(MAKE_COMBOS_HEAD)}件/期待1)")
else:
    i = t.index(MAKE_COMBOS_HEAD)
    j = t.index("\n}\n", t.index("if(!commitPlans(next)) return [];", i)) + 3
    t = t[:i] + (
        "/* ★`makeCombos()` は v23 で削除した。\n"
        "     どこからも呼ばれていない死んだコードなのに、`defaults(hk, wk, ...)` から\n"
        "     新しい世帯を作る形が残っており、**P0-1と同じ罠**を将来また踏ませる。\n"
        "     組み合わせを作りたくなったら `planWithPreset` / `planWithWScenario` を重ねること。 */\n"
    ) + t[j:]

# ---- 3. パートナーがいないときはボタンを無効にする（到達させない） ----
sub('''        <button class="btn" style="margin-top:9px" onclick="safeRun('プランの作成', loadAllWScenarios)" aria-label="パートナーの収入ちがいのプランをまとめて作る">
          まとめて作る</button>''',
    '''        <button class="btn" style="margin-top:9px" onclick="safeRun('プランの作成', loadAllWScenarios)"
          aria-label="パートナーの収入ちがいのプランをまとめて作る" data-needs-spouse="1">
          まとめて作る</button>''',
    "パートナー収入ボタンに印を付ける")

if ng:
    print("NG:", " / ".join(ng))
    sys.exit(1)
P.write_text(t, encoding="utf-8")
print("OK v23 patch A（比較プランを現在の家計から作る／makeCombos 削除）")
