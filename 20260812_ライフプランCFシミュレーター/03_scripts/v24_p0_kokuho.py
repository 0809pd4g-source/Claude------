# -*- coding: utf-8 -*-
r"""v24 patch C：P0-4（年金受給中の国保が翌年から激減）＋P1-2（65歳以上の年金15万円控除）。

**P0-4 何が起きていたか**
国保の所得を `bizIncome(salary)`＝**事業所得だけ**で組んでいた。

    mem.push({who:"h", inc:bizIncome(salaryH, P.tax), …})
    prevBizH = (workTypeOf(P,"h") === "self") ? bizIncome(salaryH, P.tax) : null;

年金収入は `pensionH` に入っており、**国保の所得に一切入っていない。**
初年度は利用者が入れた前年所得を使うので正しく出るが、
2年目からは「事業所得0円」が前年所得として繰り越され、**7割軽減が当たる。**

実測（新宿区公式ケース3と同じ世帯・年金310万／260万が毎年同額）:

    2026年 413,458円 → 2027年 40,243.8円 → 2028年 40,243.8円   （年373,214円の減少）

★`kokuhoHousehold()` 単体では公式3ケースと完全一致していた。
  **部品が正しくても、統合経路が誤る。** 単体と `simulate()` の両方を回帰にする。

**P1-2（新宿区公式で確認）**
> 「65歳以上の方で年金所得がある場合、年金所得からさらに15万円が控除されます。」

これは**均等割の軽減判定に使う所得**だけの控除。所得割の算定基礎は下げない。
実測の境界（70歳・前年所得53万円・年金あり・単身）：5割軽減 → **7割軽減**、
44,116.5円 → 30,701.9円（差13,414.6円）。

**あわせて直すもの（対称性）**
`wageEarner`（給与または年金の所得者）を **h にしか設定していなかった**。
w 側は `mem.push({who:"w", inc, age, prevInc})` で `wageEarner` が無い。
公式の式は「給与または年金所得者の**合計数**−1」なので、
パートナーが年金受給者の世帯で加算が1人ぶん足りなくなる。
**v22の擬制世帯主と同じ H/W 非対称。**
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


# ---- 1. POLICY/既定に 65歳以上の年金控除を持たせる ----
sub('''    kokuhoReduceWageAdd:100000,   // 給与所得者等の数−1 に対する加算（円）''',
    '''    kokuhoReduceWageAdd:100000,   // 給与所得者等の数−1 に対する加算（円）
    /* ★65歳以上で年金所得がある人は、**軽減判定に使う所得から**さらに15万円を引く。
       新宿区公式（hoken01_002030.html・2026-08-31に確認）:
       「65歳以上の方で年金所得がある場合、年金所得からさらに15万円が控除されます。」
       所得割の算定基礎は下げない（v24 P1-2）。 */
    kokuhoPension65Deduct:150000,''',
    "65歳以上の年金控除を既定に追加")

# ---- 2. kokuhoHousehold の軽減判定所得を分ける ----
sub('''  const subjects = members.concat(extraSubjects || []);
  const wageEarners = subjects.filter(m => m.wageEarner).length;
  const red = kokuhoReduceRate(subjects.reduce((a, m) => a + incOf(m), 0), n, T, wageEarners);''',
    '''  const subjects = members.concat(extraSubjects || []);
  /* 公式の式は「給与**または年金**所得者の合計数 − 1」に10万円を加算する。 */
  const wageEarners = subjects.filter(m => m.wageEarner).length;
  /* ★軽減判定に使う所得は、所得割の算定基礎とは別（v24 P1-2）。
       65歳以上で年金所得がある人は、判定用の所得からさらに15万円を引く。
       所得割は引かない。 */
  const reduceIncOf = m => {
    const base = incOf(m);
    const hasPension = (m.pensionInc || 0) > 0;
    const cut = ((m.age || 0) >= 65 && hasPension)
      ? Math.min(T.kokuhoPension65Deduct || 0, m.pensionInc || 0) : 0;
    return Math.max(0, base - cut);
  };
  const red = kokuhoReduceRate(subjects.reduce((a, m) => a + reduceIncOf(m), 0),
                               n, T, wageEarners);''',
    "軽減判定所得を分ける")

# ---- 3. 国保の所得に年金雑所得・その他所得を含める ----
sub('''      if(selfH){
        const cur = bizIncome(salaryH, P.tax);
        /* 給与所得者等＝給与収入または公的年金収入がある人。軽減判定の加算に使う。 */
        mem.push({who:"h", inc:cur, age:ageH, wageEarner:(pensionH > 0),
                  prevInc:prevOf(cur, prevBizH, P.tax.kokuhoPrevIncH,
                                 "tax.kokuhoPrevIncH")});
      }
      if(selfW){
        const cur = bizIncome(salaryW, P.tax);
        mem.push({who:"w", inc:cur, age:ageW,
                  prevInc:prevOf(cur, prevBizW, P.tax.kokuhoPrevIncW,
                                 "tax.kokuhoPrevIncW")});
      }''',
    '''      /* ★国保の所得は「事業所得だけ」ではない（v24 P0-4）。
           公的年金等の雑所得・その他の課税所得も入る。
           v23までは `bizIncome(salary)` だけを使っており、年金収入だけの世帯は
           **2年目から前年所得0円が繰り越されて7割軽減が当たっていた**
           （実測：413,458円 → 40,243.8円。年373,214円の減少）。 */
      const pensionMiscOf = (pen, age) =>
        Math.max(0, (pen || 0) - pensionDeduction(pen || 0, age));
      /* その他の課税所得は、この試算では「あなた」に寄せている（税の扱いと同じ）。 */
      const kokuhoIncOf = (salary, pen, age, misc) =>
        bizIncome(salary, P.tax) + pensionMiscOf(pen, age) + Math.max(0, misc || 0);
      if(selfH){
        const cur = kokuhoIncOf(salaryH, pensionH, ageH, otherTaxable);
        const pen = pensionMiscOf(pensionH, ageH);
        /* 給与所得者等＝給与収入または公的年金収入がある人。軽減判定の加算に使う。 */
        mem.push({who:"h", inc:cur, age:ageH, wageEarner:(pensionH > 0), pensionInc:pen,
                  prevInc:prevOf(cur, prevKokuhoH, P.tax.kokuhoPrevIncH,
                                 "tax.kokuhoPrevIncH"),
                  prevPensionInc:(prevPensionH !== null && prevPensionH !== undefined)
                    ? prevPensionH : pen});
      }
      if(selfW){
        const cur = kokuhoIncOf(salaryW, pensionW, ageW, 0);
        const pen = pensionMiscOf(pensionW, ageW);
        /* ★v23まで w 側に `wageEarner` を渡しておらず、パートナーが年金受給者でも
             「給与または年金所得者」に数えられていなかった（H/W非対称・v22と同型）。 */
        mem.push({who:"w", inc:cur, age:ageW, wageEarner:(pensionW > 0), pensionInc:pen,
                  prevInc:prevOf(cur, prevKokuhoW, P.tax.kokuhoPrevIncW,
                                 "tax.kokuhoPrevIncW"),
                  prevPensionInc:(prevPensionW !== null && prevPensionW !== undefined)
                    ? prevPensionW : pen});
      }''',
    "国保の所得に年金・その他を含める")

# ---- 4. 軽減判定は「前年の年金所得」で見る ----
sub('''  const reduceIncOf = m => {
    const base = incOf(m);
    const hasPension = (m.pensionInc || 0) > 0;''',
    '''  const reduceIncOf = m => {
    const base = incOf(m);
    /* 判定は前年の所得で行うので、年金の有無も前年で見る（無ければ当年で代用）。 */
    const pi = (m.prevPensionInc !== undefined && m.prevPensionInc !== null)
      ? m.prevPensionInc : (m.pensionInc || 0);
    const hasPension = (pi || 0) > 0;''',
    "前年の年金所得で判定")
sub('''    const cut = ((m.age || 0) >= 65 && hasPension)
      ? Math.min(T.kokuhoPension65Deduct || 0, m.pensionInc || 0) : 0;''',
    '''    const cut = ((m.age || 0) >= 65 && hasPension)
      ? Math.min(T.kokuhoPension65Deduct || 0, pi) : 0;''',
    "控除額の上限を前年年金額に")

# ---- 5. 繰越の変数名と中身を直す ----
sub('''  let prevBizH = null, prevBizW = null;''',
    '''  /* ★国保の前年所得。事業所得だけでなく年金雑所得・その他所得を含む（v24 P0-4）。
       名前も `prevBiz` から改めた（事業所得だけだと読めてしまうため）。 */
  let prevKokuhoH = null, prevKokuhoW = null;
  let prevPensionH = null, prevPensionW = null;''',
    "繰越変数の宣言")
sub('''    /* ★次の年の国保も、この年の事業所得で決まる。
       自営業でない年は null に戻す（国保の対象でなくなるため）。 */
    prevBizH = (workTypeOf(P, "h") === "self") ? bizIncome(salaryH, P.tax) : null;
    prevBizW = (F.hasSpouse && workTypeOf(P, "w") === "self")
      ? bizIncome(salaryW, P.tax) : null;''',
    '''    /* ★次の年の国保は、この年の**総所得**（事業＋年金雑所得＋その他）で決まる。
       自営業でない年は null に戻す（国保の対象でなくなるため）。 */
    if(workTypeOf(P, "h") === "self"){
      const penH = Math.max(0, pensionH - pensionDeduction(pensionH, ageH));
      prevKokuhoH = bizIncome(salaryH, P.tax) + penH + Math.max(0, otherTaxable || 0);
      prevPensionH = penH;
    }else{ prevKokuhoH = null; prevPensionH = null; }
    if(F.hasSpouse && workTypeOf(P, "w") === "self"){
      const penW = Math.max(0, pensionW - pensionDeduction(pensionW, ageW));
      prevKokuhoW = bizIncome(salaryW, P.tax) + penW;
      prevPensionW = penW;
    }else{ prevKokuhoW = null; prevPensionW = null; }''',
    "繰越の中身")
sub('''         前の年の値（prevBizH/W）→ 入力された前年所得 → 当年で代用、の順に使う。 */''',
    '''         前の年の値（prevKokuhoH/W）→ 入力された前年所得 → 当年で代用、の順に使う。 */''',
    "コメントの変数名")

# ---- 6. 擬制世帯主にも同じ規則を当てる ----
sub('''        const inc = Math.max(0, sal - salaryDeduction(sal))
                  + Math.max(0, pen - pensionDeduction(pen, age2));
        return [{who:"head", inc:inc, prevInc:inc, age:age2, wageEarner:true}];''',
    '''        const penMisc = Math.max(0, pen - pensionDeduction(pen, age2));
        const inc = Math.max(0, sal - salaryDeduction(sal)) + penMisc;
        /* ★擬制世帯主にも65歳以上の年金15万円控除を当てる（v24 P1-2）。 */
        return [{who:"head", inc:inc, prevInc:inc, age:age2, wageEarner:true,
                 pensionInc:penMisc, prevPensionInc:penMisc}];''',
    "擬制世帯主に年金控除")

if ng:
    print("NG:", " / ".join(ng))
    sys.exit(1)
P.write_text(t, encoding="utf-8")
print("OK v24 patch C（国保の前年所得と65歳以上の年金控除）")
