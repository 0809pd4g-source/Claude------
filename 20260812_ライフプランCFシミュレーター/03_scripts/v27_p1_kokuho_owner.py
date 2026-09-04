# -*- coding: utf-8 -*-
r"""v27 P1-2／P1-3：国保の前年年金所得と、その他収入の所有者。

**P1-3｜その他の課税所得を、常に「あなた」へ寄せていた。**
  `otherTaxable` を `argsH.miscInc` にだけ渡し、国保の所得にも h 側だけへ足していた。
  コメント自身が「誰の収入かを持っていないため」と書いていた＝**持たせればよい。**
  ChatGPT版の実測：その他課税所得200万円を、高所得の本人ではなく無収入の
  パートナーに帰属させるべきケースで、世帯の税・社会保険を**年426,200円多く**計上した。

  `other.incomes[].owner` を持たせる（"h" ／ "w" ／ "both"）。
  既定は "h"（v26までの挙動と同じ＝古い保存データも結果が変わらない）。
  "both" は**世帯共通**として折半する。配賦の規則を画面にも書く。

**P1-2｜年金を受け取り始めた年に、前年も年金があったと推定していた。**
  前年の所得が分からない年は当年で代用する（`prevOf`）。これ自体は仕様だが、
  **軽減判定の「65歳以上の年金所得15万円控除」まで当年の年金で判定していた。**
  65歳・当年年金200万円・前年年金0円のケースで、5割軽減であるべきところ
  7割軽減が当たっていた（ChatGPT版の実測：44,116.5円 → 30,701.9円）。

  ★向きに注意：この誤りは**保険料を安く見せる側**に外れる。
    生活設計では、負担を小さく見せるほうが危ない。

  `tax.kokuhoPrevPensionH/W` を独立した入力として持ち、
  確認済みならそれを使う。**未確認のときは15万円控除を当てない**（安全側）。
  代用したことは `kokuhoUsedCurrent` で画面に出る（既存）。
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
# P1-3-a  既定値・移行
# ============================================================
sub('''    kokuhoPrevIncH:0,             // あなたの前年の所得（円）''',
    '''    /* ★前年の「公的年金等の雑所得」。前年の所得とは**別に**持つ。
         v26は前年の所得しか持たず、軽減判定の15万円控除を
         **当年の年金があれば前年にもあったものとして**当てていた。
         年金を受け取り始めた年に、実際より軽い保険料を出す（安全でない側）。 */
    kokuhoPrevPensionH:0,         // あなたの前年の公的年金等の雑所得（円）
    kokuhoPrevPensionW:0,         // 同（パートナー）
    kokuhoPrevIncH:0,             // あなたの前年の所得（円）''',
    "前年の年金所得を既定値に追加")

sub('''  if(!Array.isArray(p.other.incomes))   p.other.incomes   = [];''',
    '''  if(!Array.isArray(p.other.incomes))   p.other.incomes   = [];
  /* ★古い保存データには所有者が無い。**v26までの挙動（あなたに寄せる）**を明示して補う。
       「無い＝あなた」にしておけば、開き直しても結果が変わらない。 */
  p.other.incomes.forEach(it => { if(!it.owner) it.owner = "h"; });
  if(p.tax){
    if(p.tax.kokuhoPrevPensionH === undefined) p.tax.kokuhoPrevPensionH = 0;
    if(p.tax.kokuhoPrevPensionW === undefined) p.tax.kokuhoPrevPensionW = 0;
  }''',
    "移行：所有者と前年年金所得を補う")

sub('''function addItem(path){
  get(PARAMS,path).push({name:"新しい項目", cat:"misc", kind:"yearly",
                         from:PARAMS.family.ageH, to:100, amount:100000, every:5});
  recalc();
}''',
    '''function addItem(path){
  const it = {name:"新しい項目", cat:"misc", kind:"yearly",
              from:PARAMS.family.ageH, to:100, amount:100000, every:5};
  /* 収入は誰のものかで税率も国保も変わるので、所有者を持たせる（既定はあなた）。 */
  if(path.indexOf("incomes") >= 0) it.owner = "h";
  get(PARAMS,path).push(it);
  recalc();
}''',
    "addItem に所有者")

# ============================================================
# P1-3-b  エンジン：所有者ごとに分ける
# ============================================================
sub('''    let otherIncome = childBenefit(P, year);
    let otherTaxable = 0;
    for(const it of P.other.incomes){
      const v = otherAmount(it, ageH, k, P);
      otherIncome += v;
      if(!it.taxFree) otherTaxable += v;
    }''',
    '''    let otherIncome = childBenefit(P, year);
    /* ★その他の課税所得は**誰のものか**で税率も国保も変わる（v27・P1-3）。
         v26は全部を「あなた」に足していた。実測で、無収入のパートナーに
         帰属させるべき200万円を本人に寄せると**世帯の税・社保が年426,200円多く**なった。
         `owner` は "h"（あなた）／"w"（パートナー）／"both"（世帯共通＝折半）。 */
    let otherTaxableH = 0, otherTaxableW = 0;
    for(const it of P.other.incomes){
      const v = otherAmount(it, ageH, k, P);
      otherIncome += v;
      if(it.taxFree) continue;
      const own = (F.hasSpouse && (it.owner === "w" || it.owner === "both"))
        ? it.owner : "h";
      if(own === "w") otherTaxableW += v;
      else if(own === "both"){ otherTaxableH += v/2; otherTaxableW += v/2; }
      else otherTaxableH += v;
    }
    const otherTaxable = otherTaxableH + otherTaxableW;''',
    "その他収入を所有者ごとに分ける")

sub('''      miscInc:otherTaxable,''',
    '''      miscInc:otherTaxableH,''',
    "h の雑所得")

# ============================================================
# P1-3-c  エンジン：国保の所得も所有者ごとに
# ============================================================
sub('''      /* その他の課税所得は、この試算では「あなた」に寄せている（税の扱いと同じ）。 */
      const kokuhoIncOf = (salary, pen, age, misc) =>''',
    '''      /* その他の課税所得は、所有者（`other.incomes[].owner`）に従って割り当てる。
         税の扱い（`miscInc`）と同じ分け方を使う。 */
      const kokuhoIncOf = (salary, pen, age, misc) =>''',
    "国保の雑所得のコメント")

sub('''        const cur = kokuhoIncOf(salaryW, pensionW, ageW, 0);''',
    '''        const cur = kokuhoIncOf(salaryW, pensionW, ageW, otherTaxableW);''',
    "国保：パートナーのその他所得")

sub('''        const cur = kokuhoIncOf(salaryH, pensionH, ageH, otherTaxable);''',
    '''        const cur = kokuhoIncOf(salaryH, pensionH, ageH, otherTaxableH);''',
    "国保：あなたのその他所得")

sub('''      prevKokuhoH = bizIncome(salaryH, P.tax) + penH + Math.max(0, otherTaxable || 0);''',
    '''      prevKokuhoH = bizIncome(salaryH, P.tax) + penH + Math.max(0, otherTaxableH || 0);''',
    "翌年へ持ち越す：あなた")

sub('''      prevKokuhoW = bizIncome(salaryW, P.tax) + penW;''',
    '''      prevKokuhoW = bizIncome(salaryW, P.tax) + penW + Math.max(0, otherTaxableW || 0);''',
    "翌年へ持ち越す：パートナー")

# ============================================================
# P1-2  前年の年金所得を独立させる
# ============================================================
sub('''        mem.push({who:"h", inc:cur, age:ageH, wageEarner:(pensionH > 0), pensionInc:pen,
                  prevInc:prevOf(cur, prevKokuhoH, P.tax.kokuhoPrevIncH,
                                 "tax.kokuhoPrevIncH"),
                  prevPensionInc:(prevPensionH !== null && prevPensionH !== undefined)
                    ? prevPensionH : pen});''',
    '''        mem.push({who:"h", inc:cur, age:ageH, wageEarner:(pensionH > 0), pensionInc:pen,
                  prevInc:prevOf(cur, prevKokuhoH, P.tax.kokuhoPrevIncH,
                                 "tax.kokuhoPrevIncH"),
                  prevPensionInc:prevPensionOf(prevPensionH, P.tax.kokuhoPrevPensionH,
                                               "tax.kokuhoPrevPensionH")});''',
    "前年の年金所得：あなた")

sub('''        mem.push({who:"w", inc:cur, age:ageW, wageEarner:(pensionW > 0), pensionInc:pen,
                  prevInc:prevOf(cur, prevKokuhoW, P.tax.kokuhoPrevIncW,
                                 "tax.kokuhoPrevIncW"),
                  prevPensionInc:(prevPensionW !== null && prevPensionW !== undefined)
                    ? prevPensionW : pen});''',
    '''        mem.push({who:"w", inc:cur, age:ageW, wageEarner:(pensionW > 0), pensionInc:pen,
                  prevInc:prevOf(cur, prevKokuhoW, P.tax.kokuhoPrevIncW,
                                 "tax.kokuhoPrevIncW"),
                  prevPensionInc:prevPensionOf(prevPensionW, P.tax.kokuhoPrevPensionW,
                                               "tax.kokuhoPrevPensionW")});''',
    "前年の年金所得：パートナー")

sub('''      const prevOf = (cur, carried, entered, confirmedPath) => {''',
    '''      /** 前年の**公的年金等の雑所得**。均等割の軽減判定でだけ使う
       *  （65歳以上で前年に年金所得がある人は、判定用の所得からさらに15万円を引く）。
       *
       *  ★v26は「前の年の値が無ければ**当年の年金**で代用」していた。
       *    そのため、65歳で年金を受け取り始めた年に
       *    「前年にも年金があった」ことにして15万円控除を当てていた。
       *    実測（ChatGPT版）：5割軽減44,116.5円であるべきところ7割軽減30,701.9円。
       *    **保険料を安く見せる向きに外れる**ので、生活設計では特に危ない。
       *
       *  未確認のときは **0（控除を当てない）** とする。当年で代用しない。 */
      const prevPensionOf = (carried, entered, confirmedPath) => {
        if(carried !== null && carried !== undefined) return carried;
        if(confirmedIn(confirmedPath)) return Math.max(0, Number(entered) || 0);
        kokuhoUsedCurrent = true;   // 前年が分からないことは画面で断る
        return 0;
      };
      const prevOf = (cur, carried, entered, confirmedPath) => {''',
    "prevPensionOf を追加")

if ng:
    print("NG:", " / ".join(ng))
    sys.exit(1)
P.write_text(t, encoding="utf-8")
print("OK v27 P1-2／P1-3（前年の年金所得・その他収入の所有者）")
