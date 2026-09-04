# -*- coding: utf-8 -*-
r"""v22 patch B：P0-3（国保の擬制世帯主を、未選択のとき暗黙に「あなた」へ寄せない）。

**何が起きていたか**

    const head = (P.family.householdHead === "w") ? "w" : "h";

未選択（null）が `"h"`＝あなた に落ちていた。すると

  - あなた＝会社員／パートナー＝自営業 → head=h は国保非加入 →
    あなたの給与が軽減判定に入る → 高く出る（警告も出る）
  - **あなた＝自営業／パートナー＝会社員 → head=h は国保加入者 →
    `extra` が空 → パートナーの給与800万円が軽減判定から消える。
    しかも `extra.length===0` なので警告も出ない。**

外部レビューの実測で、後者は年57,801.1円の過少計上だった。
**「未選択」を「あなた」と読んだこと**が原因で、向きによって症状が反転した。

**直し方**
未選択のときは h/w の両方で計算し、**高いほう（軽減が効かないほう）を採る。**
このツールの方針（結果は隠さず概算＋未確認を明示）に合わせ、
安全側に倒したうえで必ず画面で断る。

★向きを反転した対称試験を検証に入れること。今回の欠陥は、片方向だけ試すと通る。
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


sub('''      const extra = [];
      const head = (P.family.householdHead === "w") ? "w" : "h";
      const headIsMember = (head === "h") ? selfH : selfW;
      if(!headIsMember){
        const sal  = (head === "h") ? salaryH : (F.hasSpouse ? salaryW : 0);
        const pen  = (head === "h") ? pensionH : (F.hasSpouse ? pensionW : 0);
        const age2 = (head === "h") ? ageH : ageW;
        if(sal > 0 || pen > 0){
          /* 世帯主の所得（給与所得控除・公的年金等控除のあと）。 */
          const inc = Math.max(0, sal - salaryDeduction(sal))
                    + Math.max(0, pen - pensionDeduction(pen, age2));
          extra.push({who:"head", inc:inc, prevInc:inc, age:age2, wageEarner:true});
        }
      }
      const kh = kokuhoHousehold(mem, P.tax, extra);
      /* 世帯主が誰か未確認のまま軽減を当てると過少計上になりうる。
         混在世帯（国保と会社員が同居）で未確認なら、画面で断る。 */
      if(!P.family.householdHead && extra.length) kokuhoHeadUnknown = true;''',
    '''      /** 世帯主を h／w と決めたときの「軽減判定にだけ加える人」を作る。
       *  世帯主が国保に入っていれば `mem` に既にいるので、加えるものはない。 */
      const extraFor = (head) => {
        const headIsMember = (head === "h") ? selfH : selfW;
        if(headIsMember) return [];
        const sal  = (head === "h") ? salaryH : (F.hasSpouse ? salaryW : 0);
        const pen  = (head === "h") ? pensionH : (F.hasSpouse ? pensionW : 0);
        const age2 = (head === "h") ? ageH : ageW;
        if(sal <= 0 && pen <= 0) return [];
        /* 世帯主の所得（給与所得控除・公的年金等控除のあと）。 */
        const inc = Math.max(0, sal - salaryDeduction(sal))
                  + Math.max(0, pen - pensionDeduction(pen, age2));
        return [{who:"head", inc:inc, prevInc:inc, age:age2, wageEarner:true}];
      };
      let kh;
      if(P.family.householdHead === "h" || P.family.householdHead === "w"){
        kh = kokuhoHousehold(mem, P.tax, extraFor(P.family.householdHead));
      }else{
        /* ★未選択を「あなた」に寄せない（P0-3）。
           v21まで `=== "w" ? "w" : "h"` としており、あなたが国保加入者・
           パートナーが会社員の向きでは、パートナーの所得が軽減判定から消え、
           警告も出ないまま**年5万円以上少なく**出ていた。
           両方を計算し、**高いほう（軽減が効かないほう）を採る**。
           安全側に倒したうえで、下の警告で必ず断る。 */
        const khH = kokuhoHousehold(mem, P.tax, extraFor("h"));
        const khW = kokuhoHousehold(mem, P.tax, extraFor("w"));
        kh = (khW.total > khH.total) ? khW : khH;
        /* 向きで結果が変わるときだけ断る（両方が国保加入者なら差は出ない）。 */
        if(Math.round(khH.total) !== Math.round(khW.total)) kokuhoHeadUnknown = true;
      }''',
    "擬制世帯主：未選択なら両ケースを計算して高いほうを採る")

sub('''  if(RESULT_NOTES.kokuhoHeadUnknown)
    add("warn", "世帯主が未確認のまま、国保の軽減を判定しています。",
      "低所得の軽減は、国保に入っていない世帯主の所得も判定に入ります。"
      + "会社員と自営業が同居する世帯では、**誰が世帯主か**で結果が変わります"
      + "（実測で年5万円以上の差が出ることがあります）。"
      + "「税・社会保険」の設定で世帯主を選んでください。");''',
    '''  if(RESULT_NOTES.kokuhoHeadUnknown)
    add("warn", "世帯主が未確認のため、国保は高いほうの見積りを載せています。",
      "低所得の軽減は、国保に入っていない世帯主の所得も判定に入ります。"
      + "会社員と自営業が同居する世帯では、誰が世帯主かで保険料が変わります"
      + "（実測で年5万円以上の差が出ることがあります）。"
      + "どちらか分からないため、あなたが世帯主の場合とパートナーが世帯主の場合の"
      + "両方を計算し、高いほうを採っています。"
      + "「税・社会保険」の設定で世帯主を選ぶと、実際の額になります。");''',
    "警告文を「高いほうを採った」に直す")

sub("""          + '未選択のままだと、軽減を当てたうえで画面に確認をうながします。</div>'""",
    """          + '未選択のままだと<b>両方を計算して高いほうを載せ</b>、'
          + '画面に確認をうながします（少なく見積もらないため）。</div>'""",
    "世帯主の説明文")

if ng:
    print("NG:", " / ".join(ng))
    sys.exit(1)
P.write_text(t, encoding="utf-8")
print("OK v22 patch B（擬制世帯主の未選択フォールバックを廃止）")
