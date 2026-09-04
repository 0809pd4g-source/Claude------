# -*- coding: utf-8 -*-
r"""v24 patch A：P0-1（住宅比較が手入力の保険表を上書きする）＋P0-2（融資手数料の循環）。

**P0-1 何が起きていたか**
v23で `planWithPreset()` を新設したとき、`defaults()` にあった行をそのまま持ってきた。

    if(p.living.insMode === "table") insGuideTable(p);

`defaults()`（世帯を新規に作る）では正しい。しかし `planWithPreset()` は
**「いまの家計はそのままで、住まいだけを変える」**と画面で約束しているコマンドの部品で、
物件条件が1つも変わらない（buy→buy）場合でも**利用者が手で入れた年齢別保険表を作り直す。**

外部レビューの実測：44歳111,111円／50歳222,222円／65歳333,333円 の表が
44歳234,567円／45歳328,394円／55歳469,134円／67歳140,740円／70歳117,284円 に置換され、
**最終金融資産 −2,902,060円 → +425,876円、枯渇99歳 → なし**と結論が逆転した。

★v23で `COMPARE_ALLOWED` を作り「許可外差分0件」を確かめたのに見逃した。
  **試験を単純方式（`insMode` が table でない）だけで回していたため。**
  許可リストに `living.insuranceAfter` を入れていたので、`living.insTable` の差分は
  「許可外」に数えられなかった＝**許可リストが広すぎた。**
  **許可リストは根（`house`）ではなく葉（`house.buy`）で持つ。**

**P0-2 何が起きていたか**
諸費用を「内訳から積み上げる」方式では、融資手数料が **借入額 × 料率** で決まる。

    loanFee = borrow * (H.feeLoanRate||0)/100 + (H.feeLoanFixed||0);

`fitLoansOn()` は「変更前の借入で諸費用を1回計算 → 必要額を出す → 借入を変更」する。
**借入を増やすと融資手数料も増えるので、変更後の必要額はまた増える。** 循環式なので1回では合わない。

外部レビューの実測（物件5,000万・自己資金1,000万・手数料2.2%）：
価格スイープ7件すべてで資金不足。3,000万で495,792円 … 7,000万で1,404,832円。
5,000万のケースで最終資産を約249万円多く見せていた。

**直し方**：閉じた式で解く。

    L = 価格 + 借入に依らない取得費 + L×r − 自己資金 − 贈与
    L = (価格 + 借入に依らない取得費 − 自己資金 − 贈与) / (1 − r)

そして保存前に恒等式（価格＋諸費用−自己資金−贈与−借入合計 ≒ 0）を確かめる。
"""
import io
import sys
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
ROOT = Path(__file__).resolve().parent.parent
P = ROOT / "02_output" / "20260831_ライフプランCFシミュレーター汎用版_v24.html"
t = P.read_text(encoding="utf-8")
ng = []


def sub(old, new, label, count=1):
    global t
    c = t.count(old)
    if c == count:
        t = t.replace(old, new, count)
    else:
        ng.append(f"{label} ({c}件/期待{count})")


# ---- P0-1: planWithPreset を住まいの軸だけに限る ----
sub('''/** いまの家計を起点に、住まい（住宅プリセット）だけを差し替えたプランを作る。 */
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
}''',
    '''/** いまの家計を起点に、**住まいだけ**を差し替えたプランを作る。
 *
 *  ★触るのは住まいに属するものだけ（`meta.preset` / `house` / `estate`）。
 *
 *  ★v23は `defaults()` から次の行を持ってきていた。
 *
 *      if(p.living.insMode === "table") insGuideTable(p);
 *
 *    `defaults()`（世帯を新規に作る）では正しいが、ここでは**利用者が手で入れた
 *    年齢別保険表を作り直してしまう**。物件条件が1つも変わらない場合（buy→buy）でも起きた。
 *    実測で最終資産が −290万円 → +43万円、枯渇99歳 → なし と**結論が逆転した**（P0-1）。
 *    画面は「いまの家計はそのままで、住まいだけ」と書いてある。**保険表は家計側のデータ。**
 *
 *  ★プロフィールのプリセットが `incomeH` / `retire` / `insuranceAfter` を持つ場合も、
 *    **ここでは当てない**（住まいの軸ではないため）。それらを含めて切り替えたいときは
 *    `defaults()` を使う別のコマンドにすること。 */
function planWithPreset(base, key){
  const p = clone(base);
  const pre = PRESETS[key];
  p.meta.preset = key;
  if(pre){
    if(pre.house) Object.assign(p.house, clone(pre.house));
    if(pre.estate) Object.assign(p.estate, clone(pre.estate));
  }
  /* ★住宅取得で火災保険の想定が変わることは伝えたいが、**表は自動で書き換えない。**
     手入力を壊すより、気づいてもらうほうがよい。 */
  if(p.living.insMode === "table" && pre && pre.house
     && pre.house.buy !== base.house.buy){
    p.meta.insReviewNeeded = true;
  }
  p.meta.planName = autoPlanName(p);
  p.meta.memo = (pre && pre.note) || "";
  return p;
}''',
    "planWithPreset を住まいの軸だけに")

# ---- 許可リストを葉パスへ ----
sub('''const COMPARE_COMMON = ["meta.planName", "meta.memo"];
const COMPARE_ALLOWED = {
  loadAllWScenarios: COMPARE_COMMON.concat(["meta.wScenario", "income.wTable"]),
  loadAllPresets:    COMPARE_COMMON.concat(["meta.preset", "meta.hIncome",
                                            "house", "estate", "living.insuranceAfter",
                                            "retire"]),
  loadRaisePatterns: COMPARE_COMMON.concat(["meta.hIncome", "income.hTable"]),
  loadAllSavingPlans:COMPARE_COMMON.concat(["saving"]),
  sweepPrice:        COMPARE_COMMON.concat(["house.price", "house.loans", "house.fees"]),
};''',
    '''/* ★v23は根（`house`・`retire`・`saving`）で許可していた。**広すぎた。**
     `living.insuranceAfter` を許可していたため、`living.insTable` が
     書き換わっても「許可外0件」になり、P0-1を見逃した。
     **葉のパスで持つ**（前方一致は `house.loans[0].amount` のような添字だけに使う）。 */
const COMPARE_COMMON = ["meta.planName", "meta.memo", "meta.insReviewNeeded"];
const COMPARE_ALLOWED = {
  loadAllWScenarios: COMPARE_COMMON.concat(["meta.wScenario", "income.wTable"]),
  /* 住まいの軸。いまのプリセットは `house.buy` しか持たないが、
     プロフィールのプリセットは物件と不動産の前提を持つ。 */
  loadAllPresets:    COMPARE_COMMON.concat(["meta.preset", "house", "estate"]),
  loadRaisePatterns: COMPARE_COMMON.concat(["meta.hIncome", "income.hTable"]),
  /* 積立の軸。`setSavingPlan` は積立額と調整表だけを触る。 */
  loadAllSavingPlans:COMPARE_COMMON.concat(["saving.plan", "saving.adjustTable",
                                            "saving.nisaMonthlyH", "saving.nisaMonthlyW",
                                            "saving.stockMonthlyH", "saving.stockMonthlyW"]),
  sweepPrice:        COMPARE_COMMON.concat(["house.price", "house.loans", "house.fees",
                                            "house.feeBrokerage"]),
};''',
    "許可リストを葉パスへ")

# ---- 保険表の見直しを画面で伝える ----
sub('''  if(RESULT_NOTES.kokuhoHeadUnknown)''',
    '''  /* ★住まいを変えたプランでは、火災保険の前提も変わる。
       v24から表を自動で書き換えないので、代わりに気づいてもらう（P0-1）。 */
  if(P.meta && P.meta.insReviewNeeded && P.living.insMode === "table")
    add("info", "住まいを変えたプランです。年齢別の保険料の表はそのまま引き継いでいます。",
      "住宅を取得すると火災保険・地震保険が加わるため、実際の保険料は変わります。"
      + "「パラメータ」の保険料の表を、取得後の想定に合わせて見直してください。"
      + "（手で入れた表を勝手に書き換えないようにしています。）");
  if(RESULT_NOTES.kokuhoHeadUnknown)''',
    "保険表の見直しを促すお知らせ")

# ---- P0-2: 必要借入額を閉じた式で解く ----
sub('''function fitLoansOn(p){
  const H = p.house;
  /* ★必要額は0未満にしない（自己資金が取得額を上回る場合）。
       v22までクランプが無く、価格を下げる方向へ振ると**負の借入**を作っていた
       （実測：−2,000万〜−500万円を保存）。 */
  const need = Math.max(0,
    Number(H.price || 0) + feeTotal(H) - Number(H.selfFund || 0) - Number(H.gift || 0));''',
    '''/** 必要な借入総額。**融資手数料が借入額に比例する循環を閉じた式で解く。**
 *
 *  ★諸費用を「内訳から積み上げる」方式では
 *      融資手数料 = 借入額 × feeLoanRate
 *    なので、必要借入額 L は L 自身に依存する。
 *
 *      L = 価格 + 借入に依らない取得費 + L×r − 自己資金 − 贈与
 *      L = (価格 + 借入に依らない取得費 − 自己資金 − 贈与) / (1 − r)
 *
 *  ★v23までは「変更前の借入で諸費用を1回計算 → 必要額 → 借入を変更」だったため、
 *    変更後に手数料が増えて**資金不足が残った**（実測：物件7,000万で1,404,832円不足。
 *    価格スイープ7件すべてで不足し、最終資産を約249万円多く見せていた）。 */
function requiredLoanTotal(H){
  const detail = H.feeMode === "detail";
  const r = detail ? Number(H.feeLoanRate || 0) / 100 : 0;
  /* いまの借入から、借入に比例する分を引いて「借入に依らない取得費」を出す。 */
  const cur = (Array.isArray(H.loans) ? H.loans : [])
    .reduce((s, l) => s + Math.max(0, Number(l.amount) || 0), 0);
  const loanDependent = detail ? cur * r : 0;
  const fixedFees = feeTotal(H) - loanDependent;
  const numerator = Math.max(0,
    Number(H.price || 0) + fixedFees
    - Number(H.selfFund || 0) - Number(H.gift || 0));
  /* 料率が100%以上だと式が成り立たない（分母が0以下）。入力の誤りとして扱う。 */
  if(!Number.isFinite(r) || r < 0 || r >= 1) return numerator;
  return numerator / (1 - r);
}
function fitLoansOn(p){
  const H = p.house;
  /* ★必要額は0未満にしない（自己資金が取得額を上回る場合）。
       v22までクランプが無く、価格を下げる方向へ振ると**負の借入**を作っていた
       （実測：−2,000万〜−500万円を保存）。 */
  const need = requiredLoanTotal(H);''',
    "requiredLoanTotal を新設")

sub('''  if(cur <= 0){
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
    '''  if(cur <= 0){
    /* ★いま借入が0のときに比率で割ると 0/0 = NaN になる。
         NaN はJSON経由で `null` になり、月返済0円として計算されてしまう。 */
    H.loans.forEach((l, i) => { l.amount = (i === 0) ? Math.round(need) : 0; });
  }else{
    H.loans.forEach(l => {
      const share = Math.max(0, Number(l.amount) || 0) / cur;
      l.amount = Math.max(0, Math.round(share * need / 10000) * 10000);
    });
    /* ★丸めた残差を1本目に足して、合計を必要額に合わせる。
         万円単位で丸めるため、複数借入では数千円ずれる。 */
    const after = H.loans.reduce((s, l) => s + l.amount, 0);
    const gap = Math.round(need) - after;
    if(gap !== 0 && H.loans[0]) H.loans[0].amount = Math.max(0, H.loans[0].amount + gap);
  }
  return p;
}

/** 取得に必要なお金と、用意したお金が合っているか（円）。
 *  0に近いほど整合。保存前の検査に使う。 */
function fundingGap(H){
  const loans = (Array.isArray(H.loans) ? H.loans : [])
    .reduce((s, l) => s + (Number(l.amount) || 0), 0);
  return Number(H.price || 0) + feeTotal(H)
       - Number(H.selfFund || 0) - Number(H.gift || 0) - loans;
}''',
    "丸め残差の吸収と fundingGap")

if ng:
    print("NG:", " / ".join(ng))
    sys.exit(1)
P.write_text(t, encoding="utf-8")
print("OK v24 patch A（保険表の上書き／融資手数料の循環）")
