# -*- coding: utf-8 -*-
r"""v28 P1-1〜P1-6。ChatGPT版のv27レビューで指摘され、**すべて現物で再現を確認した**。

  P1-1 借入の追加・削除で資金がずれる（実測：追加直後に 9,780,000円 の過剰）
  P1-2 保存の検査が、いま画面に出ている警告を書き換える（実測：`kokuhoUsedCurrent` false→true）
  P1-3 新しい物件の名前をキャンセルしても、いまのプランが書き換わっている
       （実測：価格5,000万→6,000万・諸費用の方式・自己資金・借入が変わったまま）
  P1-4 物価上昇率が0%のとき「自分で年率を入れる」を選んでも入力欄が出ない
       （実測：値0 → モードが「上がらない」に戻る）。−200%も入る
  P1-5 購入する世帯は、セットアップを一周しても最終段階に届かない
       （実測：9/10・足りない「いまの住居費」。購入分岐では家賃の欄が出ない）
  P1-6 借入額があるのに返済期間0年を入れられる（実測：毎月返済0円）
"""
import io
import sys
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
ROOT = Path(__file__).resolve().parent.parent
P = ROOT / "02_output" / "20260901_ライフプランCFシミュレーター汎用版_v28.html"
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
# P1-1  借入の追加・削除でも資金を合わせ直す
# ============================================================
sub('''function addLoan(){
  PARAMS.house.loans.push({name:"追加借入", amount:10000000, years:35,
    steps:[{y:1,rate:1.3}]}); recalc();
}
function delLoan(i){ PARAMS.house.loans.splice(i,1); recalc(); }''',
    '''function addLoan(){
  /* ★金額0で足して、必要額を配分し直す。
       v27は1,000万円を勝手に上乗せしており、**追加した瞬間に資金が
       9,780,000円 過剰**になった（「自動で合わせる」がONでも合わせ直さない）。
       本数を変えるのは**配分の変更**であって、必要額の変更ではない。 */
  PARAMS.house.loans.push({name:"追加借入", amount:0, years:35,
    steps:[{y:1,rate:1.3}]});
  refitAfterLoanCountChange();
  recalc();
}
function delLoan(i){
  PARAMS.house.loans.splice(i,1);
  refitAfterLoanCountChange();
  recalc();
}
/** 借入の本数を変えたあと、資金の辻褄を合わせ直す。
 *  「自動で合わせる」がOFFなら触らない（利用者が自分で決めている）。 */
function refitAfterLoanCountChange(){
  const H = PARAMS.house;
  if(!H.buy || !H.autoFitLoans) return;
  /* 全部0だと配分できないので、1本目に必要額を寄せてから配分する。 */
  fitLoansOn(PARAMS);
}''',
    "addLoan / delLoan で合わせ直す")

# ============================================================
# P1-2  保存の検査が、いまの画面の警告を書き換えない
# ============================================================
sub('''  RESULT_NOTES.kokuhoUsedCurrent = kokuhoUsedCurrent;
  RESULT_NOTES.kokuhoHeadUnknown = kokuhoHeadUnknown;

  return {rows, loanRows, loanTotal, buyYear, kokuhoUsedCurrent, kokuhoHeadUnknown,''',
    '''  /* ★気づいたことは**戻り値に入れる**。
       v27まで `RESULT_NOTES`（グローバル）へ直接書いていたため、
       保存前の検査（`badResultsIn`）が候補を `simulate()` した瞬間に
       **いま画面に出ている警告が候補のものへ書き換わっていた**
       （実測：会社員のプランを表示中に自営業の候補を保存すると
        `kokuhoUsedCurrent` が false → true になる）。
       画面側は `recalc()` が `SIM.notes` から詰め替える。 */
  const notes = {kokuhoUsedCurrent, kokuhoHeadUnknown};

  return {rows, loanRows, loanTotal, buyYear, kokuhoUsedCurrent, kokuhoHeadUnknown, notes,''',
    "simulate は notes を返す")

sub('''function recalc(){ SIM = simulate(PARAMS); render(); }''',
    '''function recalc(){
  SIM = simulate(PARAMS);
  /* ★画面の断り書きは**いま表示しているプランの結果**から詰める。
       `simulate()` はもう何も書き換えないので、候補の計算に汚されない。 */
  syncResultNotes(SIM);
  render();
}
/** `simulate()` の戻り値から、画面用の断り書きを詰め替える。 */
function syncResultNotes(sim){
  const n = (sim && sim.notes) || {};
  Object.keys(RESULT_NOTES).forEach(k => { delete RESULT_NOTES[k]; });
  Object.keys(n).forEach(k => { RESULT_NOTES[k] = n[k]; });
}''',
    "recalc が notes を詰め替える")

# ============================================================
# P1-3  新しい物件は候補の上で作り、保存できたときだけ移す
# ============================================================
sub("""  H.buy = true;
  H.price = price;
  H.selfFund = Math.round(price * 0.05 / 10000) * 10000;   // 手付金は価格の5%
  H.feeMode = "detail";                                     // 諸費用は内訳から積み上げる
  H.feeBrokerageAuto = true;
  fitLoans();                                               // 借入を必要額に合わせる

  const loan = H.loans.reduce((s,l) => s + l.amount, 0);
  const nm = prompt("このプランの名前を付けてください。",
    "新しい物件" + fmtMan(price) + "万／"
    + ((WSCENARIOS[P.meta.wScenario]||{}).short || "パートナーの収入"));
  if(nm === null){ recalc(); return; }
  P.meta.planName = nm;
  P.meta.memo = "価格" + fmtMan(price) + "万円。手付金5%＝" + fmtMan(H.selfFund) + "万円、"
    + "諸費用" + fmtMan(feeTotal(H)) + "万円（内訳から積み上げ）、借入" + fmtMan(loan) + "万円。"
    + "土地・建物の面積や築年は「物件・借入・不動産の設定」で直してください。";
  if(!commitPlans(withPlan(P, nm))){ recalc(); return; }
  recalc();""",
    """  /* ★いまのプランを直接書き換えない。**候補の上で作り、保存できたときだけ移す。**
       v27は先に `PARAMS.house` を書き換えてから名前を聞いていたため、
       名前の入力をキャンセルすると**価格・諸費用の方式・自己資金・借入が
       変わったまま残った**（実測：5,000万→6,000万／simple→detail／自己資金500万→300万）。
       保存に失敗したときも同じことが起きていた。 */
  const CAND = clone(P);
  const CH = CAND.house;
  CH.buy = true;
  CH.price = price;
  CH.selfFund = Math.round(price * 0.05 / 10000) * 10000;   // 手付金は価格の5%
  CH.feeMode = "detail";                                     // 諸費用は内訳から積み上げる
  CH.feeBrokerageAuto = true;
  CH.autoFitLoans = true;
  fitLoansOn(CAND);                                          // 借入を必要額に合わせる

  const loan = CH.loans.reduce((s,l) => s + l.amount, 0);
  const nm = prompt("このプランの名前を付けてください。",
    "新しい物件" + fmtMan(price) + "万／"
    + ((WSCENARIOS[P.meta.wScenario]||{}).short || "パートナーの収入"));
  if(nm === null) return;                       // ★何も変えずに戻る
  CAND.meta.planName = nm;
  CAND.meta.memo = "価格" + fmtMan(price) + "万円。手付金5%＝" + fmtMan(CH.selfFund) + "万円、"
    + "諸費用" + fmtMan(feeTotal(CH)) + "万円（内訳から積み上げ）、借入" + fmtMan(loan) + "万円。"
    + "土地・建物の面積や築年は「物件・借入・不動産の設定」で直してください。";
  if(!commitPlans(withPlan(CAND, nm))) return;  // ★保存できなければ現状のまま
  /* 保存できたので、いまのプランをこの物件に切り替える。 */
  PARAMS = CAND;
  syncSelectors();
  const nameBox = document.getElementById("planName");
  if(nameBox) nameBox.value = nm;
  recalc();""",
    "newPropertyPlan を候補の上で作る")

sub("""    + "「プラン比較」のページで、ほかのプランと並べて見られます。" + NL
    + "土地・建物の面積、築年、修繕費はこのページの下で直せます。");""",
    """    + "「プラン比較」のページで、ほかのプランと並べて見られます。" + NL
    + "土地・建物の面積、築年、修繕費はこのページの下で直せます。");""",
    "保存後の案内（変更なし・位置確認）")

if ng:
    print("NG:", " / ".join(ng))
    sys.exit(1)
P.write_text(t, encoding="utf-8")
print("OK v28 P1-1／P1-2／P1-3（借入の本数・警告の純粋性・キャンセル安全性）")
