# -*- coding: utf-8 -*-
r"""v28 P0-1／P0-2。ChatGPT版のv27レビューで指摘され、**現物で再現を確認した**。

**P0-1｜擬制世帯主の所得が、当年だけで作られていた。**

  国保の軽減判定は前年所得で行う。加入者（`mem`）についてはv27で
  `prevOf()` / `prevPensionOf()` を通すようにしたのに、
  **擬制世帯主（`extraFor`）は当年の給与・年金だけで作っていた。**
  しかも `if(sal <= 0 && pen <= 0) return [];` で、
  **当年0円なら世帯主が判定から丸ごと消える。**

  実測（H自営・W会社員で世帯主、当年は両方0円、前年800万円を確認済み）:

      前年800万を確認済み : 25,461.9円
      前年0円             : 25,461.9円   ← **同じ**。前年所得が効いていない

  ★向きに注意：**保険料を安く見せる側**に外れる。
    退職直後・独立初年度など「当年は0円だが前年は高い」年ほど大きく外す。

  ★これはv27で自分が直した誤りの**片割れ**。加入者側だけ直して、
    同じループの中にある擬制世帯主を見落とした。
    CLAUDE.mdに「1回直して終わりにしない」と書いておきながら、また同じことをした。

**P0-2｜金額の入口に下限が無かった。**

  v27で `setNum()` に範囲を持たせたのは**配列の中の欄**（表・明細・ローン）だけで、
  `onMan()` を通るトップレベルの金額は素通りだった。実測：

      house.price      -5,000万円  → 受理
      house.selfFund   -1,000万円  → 受理
      econ.deposit     -1,000万円  → 受理
      living.insurance   -100万円  → 受理

  ★`onMan()` は**金額の入口**なので、既定を「0以上」にするのが素直。
    負を許す項目だけを allowlist に明記する（ChatGPT版の提案どおり）。
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
# P0-1  擬制世帯主も前年所得で判定する
# ============================================================
sub('''  let prevKokuhoH = null, prevKokuhoW = null;''',
    '''  let prevKokuhoH = null, prevKokuhoW = null;
  /* ★擬制世帯主（国保に入っていない世帯主）の前年所得も持ち越す。
       v27は当年の給与・年金だけで作っており、**当年0円なら判定から消えていた**
       （退職直後の世帯主が居なかったことになる。実測で差0円＝前年所得が効かない）。
       加入者と同じ「前の年の値 → 入力された前年所得 → 当年で代用」の順で使う。 */
  let prevHeadIncH = null, prevHeadIncW = null;
  let prevHeadPenH = null, prevHeadPenW = null;''',
    "擬制世帯主の前年所得を持ち越す変数")

sub('''      const extraFor = (head) => {
        const headIsMember = (head === "h") ? selfH : selfW;
        if(headIsMember) return [];
        const sal  = (head === "h") ? salaryH : (F.hasSpouse ? salaryW : 0);
        const pen  = (head === "h") ? pensionH : (F.hasSpouse ? pensionW : 0);
        const age2 = (head === "h") ? ageH : ageW;
        if(sal <= 0 && pen <= 0) return [];
        /* 世帯主の所得（給与所得控除・公的年金等控除のあと）。 */
        const penMisc = Math.max(0, pen - pensionDeduction(pen, age2));
        const inc = Math.max(0, sal - salaryDeduction(sal)) + penMisc;
        /* ★擬制世帯主にも65歳以上の年金15万円控除を当てる（v24 P1-2）。 */
        return [{who:"head", inc:inc, prevInc:inc, age:age2, wageEarner:true,
                 pensionInc:penMisc, prevPensionInc:penMisc}];
      };''',
    '''      const extraFor = (head) => {
        const headIsMember = (head === "h") ? selfH : selfW;
        if(headIsMember) return [];
        const sal  = (head === "h") ? salaryH : (F.hasSpouse ? salaryW : 0);
        const pen  = (head === "h") ? pensionH : (F.hasSpouse ? pensionW : 0);
        const age2 = (head === "h") ? ageH : ageW;
        /* 世帯主の所得（給与所得控除・公的年金等控除のあと）。 */
        const penMisc = Math.max(0, pen - pensionDeduction(pen, age2));
        const cur = Math.max(0, sal - salaryDeduction(sal)) + penMisc;
        /* ★**判定は前年所得**。加入者（`mem`）と同じ入口を通す。
             v27はここだけ当年で作っており、`sal<=0 && pen<=0` で
             **当年0円の世帯主を判定から消していた**（前年800万円が効かない）。 */
        const prevInc = prevOf(cur,
          (head === "h") ? prevHeadIncH : prevHeadIncW,
          (head === "h") ? P.tax.kokuhoPrevIncH : P.tax.kokuhoPrevIncW,
          (head === "h") ? "tax.kokuhoPrevIncH" : "tax.kokuhoPrevIncW");
        const prevPen = prevPensionOf(
          (head === "h") ? prevHeadPenH : prevHeadPenW,
          (head === "h") ? P.tax.kokuhoPrevPensionH : P.tax.kokuhoPrevPensionW,
          (head === "h") ? "tax.kokuhoPrevPensionH" : "tax.kokuhoPrevPensionW");
        /* 当年も前年も0円なら、判定に足しても何も変わらない。 */
        if(cur <= 0 && prevInc <= 0) return [];
        /* ★擬制世帯主にも65歳以上の年金15万円控除を当てる（v24 P1-2）。 */
        return [{who:"head", inc:cur, prevInc:prevInc, age:age2, wageEarner:true,
                 pensionInc:penMisc, prevPensionInc:prevPen}];
      };''',
    "extraFor を前年所得で作る")

sub('''    }else{ prevKokuhoW = null; prevPensionW = null; }''',
    '''    }else{ prevKokuhoW = null; prevPensionW = null; }
    /* ★国保に入っていない側（＝擬制世帯主になりうる側）の所得も翌年へ渡す。
         国保加入者のときは `mem` 側で扱うので null に戻す。 */
    if(workTypeOf(P, "h") !== "self"){
      const penH3 = Math.max(0, pensionH - pensionDeduction(pensionH, ageH));
      prevHeadIncH = Math.max(0, salaryH - salaryDeduction(salaryH)) + penH3;
      prevHeadPenH = penH3;
    }else{ prevHeadIncH = null; prevHeadPenH = null; }
    if(F.hasSpouse && workTypeOf(P, "w") !== "self"){
      const penW3 = Math.max(0, pensionW - pensionDeduction(pensionW, ageW));
      prevHeadIncW = Math.max(0, salaryW - salaryDeduction(salaryW)) + penW3;
      prevHeadPenW = penW3;
    }else{ prevHeadIncW = null; prevHeadPenW = null; }''',
    "擬制世帯主の所得を翌年へ渡す")

# ============================================================
# P0-2  金額の入口（onMan）に下限を持たせる
# ============================================================
sub('''const NUM_RANGE = {
  "house.feeLoanRate": {min:0, max:99.999, label:"融資手数料率",
    why:"借入額に対する割合です。100%以上は必要な借入額が求まりません。"},
  "family.ageH":  {min:0, max:130, label:"あなたの年齢"},
  "family.ageW":  {min:0, max:130, label:"パートナーの年齢"},
  "meta.endAge":  {min:1, max:130, label:"最終年齢"},
};''',
    '''const NUM_RANGE = {
  "house.feeLoanRate": {min:0, max:99.999, label:"融資手数料率",
    why:"借入額に対する割合です。100%以上は必要な借入額が求まりません。"},
  /* ★年齢の下限は0ではなく18。**この試算は働いて家計を持つ人が使う**もので、
       0歳・マイナスの年齢は入力の誤り。v27は0と−5を受け付け、
       見出しが「あなた-5歳〜100歳」になった。 */
  "family.ageH":  {min:18, max:120, label:"あなたの年齢",
    why:"この試算は、働いて家計を持っている方を想定しています。"},
  "family.ageW":  {min:18, max:120, label:"パートナーの年齢",
    why:"この試算は、働いて家計を持っている方を想定しています。"},
  "meta.endAge":  {min:19, max:130, label:"最終年齢",
    why:"いまの年齢より大きくしてください。"},
  "econ.inflation":  {min:-20, max:20, label:"物価上昇率"},
  "econ.investRate": {min:-50, max:50, label:"運用利回り"},
  "house.rentGrowth":{min:-99.9, max:50, label:"家賃の上昇率",
    why:"−100%以下にすると家賃がマイナス（もらえる）になってしまいます。"},
};

/** `onMan()`（万円で入れる金額の欄）で**負の値を許すパス**。
 *
 *  ★金額の既定は「0以上」にする。v27は `setNum()` に範囲を持たせたものの、
 *    それは**配列の中の欄だけ**で、トップレベルの金額は素通りだった。
 *    実測：物件価格 −5,000万円・自己資金 −1,000万円・預金 −1,000万円・
 *    保険料 −100万円がそのまま入った。
 *    **「どれを守るか」を列挙すると必ず漏れるので、「どれを許すか」を列挙する。** */
const NEGATIVE_MONEY_OK = new Set([
  /* いまのところ無し。負を許す金額を足すときは、
     画面にも「マイナスで入れると◯◯という意味になります」と書くこと。 */
]);''',
    "NUM_RANGE を広げ、負を許す金額の allowlist を作る")

sub('''  const x = readFinite(v, MAN);
  if(x === null){ noticeBadInput([path], "その欄は変更していません"); render(); return; }
  set(PARAMS, path, x);
  markEntered(path); maybeAutoFit(path); recalc(); }''',
    '''  const x = readFinite(v, MAN);
  if(x === null){ noticeBadInput([path], "その欄は変更していません"); render(); return; }
  /* ★金額は既定で0以上（`NEGATIVE_MONEY_OK` にあるパスだけ負を許す）。 */
  if(x < 0 && !NEGATIVE_MONEY_OK.has(path)){
    pushNotice("range", "bad",
      `<b>${esc(fieldLabelOf(path))}にマイナスの金額は入れられません。</b>`
      + `<span class="hint">入れた値：${esc(String(v))}万円。`
      + `その欄は変更していません（いまの値のままです）。</span>`);
    render(); return;
  }
  const re = rangeError(path, x);
  if(re){
    pushNotice("range", "bad", `<b>${esc(re)}</b>`
      + `<span class="hint">その欄は変更していません（いまの値のままです）。</span>`);
    render(); return;
  }
  set(PARAMS, path, x);
  markEntered(path); maybeAutoFit(path); recalc(); }''',
    "onMan に下限と範囲")

sub('''function rangeError(path, x){
  const s = NUM_RANGE[path];''',
    '''/** 画面に出す欄の名前。範囲外を断るときに使う。 */
function fieldLabelOf(path){
  const s = NUM_RANGE[path];
  if(s && s.label) return s.label;
  const nm = (typeof FIELD_LABELS !== "undefined" && FIELD_LABELS[path]) || "";
  return nm || path;
}
function rangeError(path, x){
  const s = NUM_RANGE[path];''',
    "fieldLabelOf を追加")

if ng:
    print("NG:", " / ".join(ng))
    sys.exit(1)
P.write_text(t, encoding="utf-8")
print("OK v28 P0-1／P0-2（擬制世帯主の前年所得・金額の下限）")
