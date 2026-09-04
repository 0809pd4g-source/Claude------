# -*- coding: utf-8 -*-
r"""v27 P1-2／P1-3 の画面側：所有者の選択欄と、前年の年金所得の欄。

★エンジンに持たせただけでは、利用者は変えられない。
  v26で `RESULT_NOTES.kokuhoUsedCurrent` を「画面で断る」と書きながら
  **どこからも読んでいなかった**のと同じ形を繰り返さない。
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


# ---- その他の収入の行に「誰の収入か」を出す ----
sub('''    ${path.indexOf("incomes") >= 0 ? `<label class="tag" style="cursor:pointer"''',
    '''    ${(path.indexOf("incomes") >= 0 && PARAMS.family.hasSpouse) ? `<select
        onchange="onItem('${path}',${i},'owner',this.value,1)"
        aria-label="${esc((it.name || (i+1)+"件目") + "は誰の収入か")}" style="min-width:96px">
      ${Object.entries(INCOME_OWNERS).map(([k,v]) =>
        `<option value="${k}" ${(it.owner||"h")===k?"selected":""}>${v}</option>`).join("")}
    </select>` : ""}
    ${path.indexOf("incomes") >= 0 ? `<label class="tag" style="cursor:pointer"''',
    "その他の収入に所有者の選択欄")

sub('''/** 項目表の名前。**path から引いて一意にする**（ageTable と同じ考え方）。 */
const ITEMTABLE_NAME = {''',
    '''/** その他の収入が**誰のものか**。所得税・住民税・国保に個人別で効く。
 *  ★v26は全部を「あなた」に足していた。実測で年426,200円の差が出るケースがある。 */
const INCOME_OWNERS = {h:"あなたの分", w:"パートナーの分", both:"世帯共通（折半）"};
/** 項目表の名前。**path から引いて一意にする**（ageTable と同じ考え方）。 */
const ITEMTABLE_NAME = {''',
    "INCOME_OWNERS を追加")

sub('''    card("otherinc","その他の収入", itemList("other.incomes")''',
    '''    card("otherinc","その他の収入",
      (PARAMS.family.hasSpouse
        ? `<div class="hint" style="margin-bottom:7px">
            <b>誰の収入かを選んでください。</b>所得税・住民税・国民健康保険は
            <b>ひとりずつ</b>にかかるので、寄せ方で世帯の負担が変わります
            （実測で年40万円以上ちがうことがあります）。<br>
            <b>世帯共通（折半）</b>は、ふたりで等分して計上します。
            持ち分がはっきりしているなら、2件に分けて入れるほうが正確です。</div>`
        : "")
      + itemList("other.incomes")''',
    "その他の収入に配賦の説明")

# ---- 国保の前年の所得の隣に、前年の年金所得 ----
sub('''          + manField("あなたの前年の所得", "tax.kokuhoPrevIncH")''',
    '''          + manField("あなたの前年の所得", "tax.kokuhoPrevIncH")
          + manField("あなたの前年の公的年金等の所得", "tax.kokuhoPrevPensionH",
              "上の「前年の所得」のうち、公的年金による分")''',
    "前年の年金所得（あなた）")

sub('''              ? manField("パートナーの前年の所得", "tax.kokuhoPrevIncW") : "")''',
    '''              ? manField("パートナーの前年の所得", "tax.kokuhoPrevIncW")
                + manField("パートナーの前年の公的年金等の所得", "tax.kokuhoPrevPensionW",
                    "上の「前年の所得」のうち、公的年金による分")
              : "")
          + `<div class="hint" style="margin-top:6px">
              <b>公的年金による分を分けて聞くのは、均等割の軽減の判定に使うためです。</b>
              65歳以上で<b>前の年に</b>年金所得があった方は、判定用の所得から
              さらに15万円を引きます（保険料そのものの計算には使いません）。<br>
              <b>入れないと、この15万円は引かずに計算します</b>
              （年金を受け取り始めた年に、保険料を安く見せないための扱いです）。</div>`''',
    "前年の年金所得（パートナー）と説明")

if ng:
    print("NG:", " / ".join(ng))
    sys.exit(1)
P.write_text(t, encoding="utf-8")
print("OK v27 P1-2／P1-3 の画面側")
