"""成果物HTMLの計算エンジンを取り出して、参照PDFの記載値と突き合わせる。

HTML内の <script> から、DOMに依存しない計算部分（defaults() 〜 eventsFor()）だけを
切り出して dukpy で評価し、simulate() の結果をPDFの数値と比較する。

使い方:  python 03_scripts/verify_against_pdf.py
"""
import io
import json
import re
import sys
from pathlib import Path

import dukpy

from verify_profile import with_pdf_profile

ROOT = Path(__file__).resolve().parent.parent
def pick_html():
    """対象のHTMLを決める。

    第1引数でファイルを指定できる。指定がなければ 02_output のいちばん新しいものを使うが、
    このスクリプトは「参照PDFの世帯」を前提にした照合なので、
    その前提を持たない汎用版は既定では選ばない（明示指定すれば使える）。
    """
    if len(sys.argv) > 1:
        p = Path(sys.argv[1])
        return p if p.is_absolute() else (ROOT / p)
    cands = [p for p in sorted((ROOT / "02_output").glob("*_v*.html"))
             if "汎用版" not in p.name]
    if not cands:
        raise SystemExit("照合対象のHTMLが 02_output に見つかりません")
    return cands[-1]


HTML = pick_html()

# UTF-8で出力（Windowsコンソールの既定コードページ対策）
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")


def extract_engine(html_text):
    """計算エンジン部分のみを抽出する。DOM参照が始まる「状態」節の直前で切る。"""
    m = re.search(r"<script>(.*?)</script>", html_text, re.S)
    if not m:
        raise SystemExit("scriptブロックが見つかりません")
    js = m.group(1)
    # ブラウザ専用の window を使う箇所があるため、最小限のダミーを先に置く
    js = 'var window={addEventListener:function(){},alert:function(){},print:function(){}};' + js
    cut = js.find("   状態")
    if cut < 0:
        raise SystemExit("計算エンジンの終端マーカーが見つかりません")
    # 直前のコメント開始位置まで戻す
    cut = js.rfind("/* ", 0, cut)
    # 汎用版は参照PDFの世帯を持たないので、プロフィールを流し込む
    return with_pdf_profile(js[:cut])


ENGINE = extract_engine(HTML.read_text(encoding="utf-8"))

RUN = ENGINE + """
// 参照PDFは「今後は積み立てをしない」前提。既定は実額なので、ここで0に戻して比べる。
var P = applyPdfSavings(defaults());
// 参照PDFは住民税を同年所得から計上している。既定は前年計上なので戻す。
// ★フラグ名が版で違う（個人版 residentLag／汎用版 residentPrevYear）。両方に入れる。
if(P.tax.residentLag !== undefined) P.tax.residentLag = false;
if(P.tax.residentPrevYear !== undefined) P.tax.residentPrevYear = false;
var S = simulate(P);
var out = {rows:[], loan:[]};
for (var i = 0; i < S.rows.length; i++) {
  var r = S.rows[i];
  out.rows.push({
    year:r.year, ageH:r.ageH, ageW:r.ageW,
    salaryH:r.salaryH, salaryW:r.salaryW,
    incomeTotal:r.incomeTotal, expenseTotal:r.expenseTotal,
    taxTotal:r.taxTotal, living:r.living, housing:r.housing,
    loanRepay:r.loanRepay, childTotal:r.childTotal,
    otherExp:r.otherExp, otherLoanRepay:r.otherLoanRepay,
    acquisition:r.acquisition, insurance:r.insurance,
    net:r.net, deposit:r.deposit, invest:r.invest,
    assetTotal:r.assetTotal, loanBalance:r.loanBalance,
    taxH_it:r.taxH.incomeTax, taxH_rt:r.taxH.residentTax, taxH_si:r.taxH.social,
    taxW_it:r.taxW.incomeTax, taxW_rt:r.taxW.residentTax, taxW_si:r.taxW.social,
    taxH_taxableIT:r.taxH.taxableIT, taxH_taxableRT:r.taxH.taxableRT,
    taxW_taxableIT:r.taxW.taxableIT, taxW_taxableRT:r.taxW.taxableRT,
    eduTotal:r.eduTotal
  });
}
for (var j = 0; j < S.loanTotal.length; j++) {
  var l = S.loanTotal[j];
  out.loan.push({y:l.y, total:l.total, principal:l.principal,
                 interest:l.interest, balance:l.balance});
}
out.buyYear = S.buyYear;
out.depleteAge = S.depleteAge;
JSON.stringify(out);
"""

R = json.loads(dukpy.evaljs(RUN))
rows = {r["year"]: r for r in R["rows"]}
loan = R["loan"]

OK, NG = 0, 0
LINES = []


def chk(label, actual, expect, tol, unit="万円"):
    """actual/expect は同じ単位で渡す。tol は許容差（同単位）。"""
    global OK, NG
    diff = actual - expect
    ok = abs(diff) <= tol
    if ok:
        OK += 1
    else:
        NG += 1
    mark = "OK  " if ok else "NG  "
    LINES.append(f"{mark}{label:<40} 計算={actual:>12,.0f} PDF={expect:>12,.0f} "
                 f"差={diff:>+10,.0f} {unit}")


man = lambda v: v / 10000

print("=" * 96)
print(f"検証対象: {HTML.name}")
print("=" * 96)

# ---------------------------------------------------------------- 住宅ローン
LINES.append("\n【住宅ローン償還表】（円・許容差1円）")
chk("1年目 年間返済額", loan[0]["total"], 2_543_818, 1, "円")
chk("1年目 元金", loan[0]["principal"], 1_623_971, 1, "円")
chk("1年目 利息", loan[0]["interest"], 919_847, 1, "円")
chk("1年目 年末残高", loan[0]["balance"], 69_876_029, 1, "円")
chk("11年目 年間返済額", loan[10]["total"], 2_635_278, 1, "円")
chk("11年目 元金", loan[10]["principal"], 1_779_966, 1, "円")
chk("11年目 年末残高", loan[10]["balance"], 52_490_520, 1, "円")
chk("21年目 年間返済額", loan[20]["total"], 2_692_850, 1, "円")
chk("21年目 年末残高", loan[20]["balance"], 33_079_475, 1, "円")
chk("31年目 年間返済額", loan[30]["total"], 2_713_078, 1, "円")
chk("31年目 年末残高", loan[30]["balance"], 10_379_418, 1, "円")
chk("35年目 年末残高", loan[34]["balance"], 0, 1, "円")
chk("返済総額", sum(r["total"] for r in loan), 92_284_842, 2, "円")
chk("利息合計", sum(r["interest"] for r in loan), 20_784_843, 2, "円")

# ---------------------------------------------------------------- 給与の将来推計
LINES.append("\n【世帯主給与の将来推計】（万円・許容差1万円）")
pdf_h = [800, 815, 832, 848, 865, 883, 900, 918, 937, 955, 975, 994, 1014,
         1034, 1055, 1076, 1098, 1119, 1142, 1165]
for i, exp in enumerate(pdf_h):
    y = 2026 + i
    chk(f"{y}年（{rows[y]['ageH']}歳）", man(rows[y]["salaryH"]), exp, 1)

LINES.append("\n【世帯主給与 55歳以降のテーブル切替】（万円）")
for y, exp in [(2048, 1212), (2052, 1212), (2053, 969), (2057, 969)]:
    chk(f"{y}年（{rows[y]['ageH']}歳）", man(rows[y]["salaryH"]), exp, 1)

LINES.append("\n【配偶者給与】（万円）")
for y, exp in [(2026, 884), (2027, 884), (2029, 340), (2031, 340), (2034, 884),
               (2054, 884), (2055, 800), (2059, 800)]:
    chk(f"{y}年（{rows[y]['ageW']}歳）", man(rows[y]["salaryW"]), exp, 1)

# ---------------------------------------------------------------- 生活費
LINES.append("\n【基本生活費】（万円）")
for y, exp in [(2026, 420), (2027, 420), (2028, 444), (2030, 468), (2038, 504),
               (2040, 540), (2053, 504), (2055, 420)]:
    chk(f"{y}年（{rows[y]['ageH']}歳）", man(rows[y]["living"]), exp, 1)

# ---------------------------------------------------------------- 税の内訳
# PDFは厚生年金の標準報酬月額の上限（650,000円）を適用していないため、
# 社会保険料が過大になっている。その控除差がそのまま課税所得の差になる。
# ここでは「社会保険料控除の差を戻した課税所得」で税額ロジックを検証する。
LINES.append("\n【初年度の税額内訳】（円・PDF p11/p12。社会保険料控除の差を補正して比較）")
r0 = rows[2026]
siDiffH = 1_193_019 - r0["taxH_si"]
siDiffW = (1_352_528 - 60_000) - r0["taxW_si"]  # PDFはDC拠出60,000円を社保欄に含む
chk("世帯主 課税所得（所得税）", r0["taxH_taxableIT"] - siDiffH, 4_270_000, 1500, "円")
chk("世帯主 課税所得（住民税）", r0["taxH_taxableRT"] - siDiffH, 4_460_000, 1500, "円")
chk("配偶者 課税所得（所得税）", r0["taxW_taxableIT"] - siDiffW, 4_917_000, 1500, "円")
chk("配偶者 課税所得（住民税）", r0["taxW_taxableRT"] - siDiffW, 5_107_000, 1500, "円")

LINES.append("\n【初年度の社会保険料】（円・PDFは厚生年金の上限を適用していないため差が出る）")
LINES.append(f"    世帯主：計算 {r0['taxH_si']:>10,.0f} ／ PDF {1_193_019:>10,.0f} "
             f"／ 差 {-siDiffH:>+9,.0f}")
LINES.append(f"    配偶者：計算 {r0['taxW_si']:>10,.0f} ／ PDF {1_292_528:>10,.0f} "
             f"／ 差 {-siDiffW:>+9,.0f}  ※PDFのDC拠出60,000円を除いた額と比較")
LINES.append("    PDFの世帯主の厚生年金は737,033円（年収比9.22%）だが、標準報酬月額の上限")
LINES.append("    650,000円を適用すれば 650,000×9.15%×12＝713,700円 が正しい。")
LINES.append("    本シミュレーターは制度どおり上限を適用するため保険料が少なくなる。")

# ---------------------------------------------------------------- 収支
LINES.append("\n【初年度の収支】（万円）")
chk("収入合計", man(r0["incomeTotal"]), 1684, 3)
chk("税・社会保険料", man(r0["taxTotal"]), 452, 20)
chk("年間収支（貯蓄額）", man(r0["net"]), 119, 20)

# ---------------------------------------------------------------- 収入の全年比較
PDF_INC = [1684, 1699, 1195, 1206, 1044, 1253, 1270, 1282, 1845, 1863,
           1883, 1902, 1922, 1942, 1963, 1984, 2006, 2027, 2050, 2073,
           2096, 2108, 2108, 2096, 2096, 2096, 2096, 1853, 1853, 1769,
           1769, 1769, 2625, 1125, 2936, 536, 536, 536, 536, 536]
LINES.append("\n【収入合計の年次比較】（万円・全40年）")
bad = [f"{2026+i}:{man(rows[2026+i]['incomeTotal']):.0f}/{e}"
       for i, e in enumerate(PDF_INC) if abs(man(rows[2026+i]["incomeTotal"]) - e) > 2]
if bad:
    NG += 1
    LINES.append(f"NG  収入合計                                   不一致 {len(bad)}/40年")
    LINES.append("      " + "  ".join(bad[:14]))
else:
    OK += 1
    LINES.append("OK  収入合計                                   全40年が一致（差2万円以内）")

# ---------------------------------------------------------------- 資産
# ---------------------------------------------------------------- 支出の年次比較
# PDF p14/p15 のキャッシュフロー表（2026〜2065年）
PDF_EXP = [1565, 2497, 1243, 1189, 1224, 1233, 1279, 1465, 1384, 1462,
           1568, 1611, 1547, 1655, 1635, 1665, 1802, 1766, 1706, 1855,
           1800, 2485, 2001, 2023, 1948, 2064, 2001, 1787, 1771, 1364,
           1359, 1571, 1233, 1127, 1129, 933, 698, 868, 669, 669]
PDF_LIVING = [420, 420, 444, 444, 468, 468, 468, 468, 468, 468,
              468, 468, 504, 504, 540, 540, 540, 540, 540, 540,
              540, 540, 540, 540, 540, 540, 540, 504, 504, 420,
              420, 420, 420, 420, 420, 420, 420, 420, 420, 420]
PDF_HOUSING = [180, 1258, 59, 59, 109, 59, 90, 60, 60, 61,
               61, 91, 62, 62, 62, 63, 93, 63, 64, 64,
               64, 495, 65, 66, 66, 66, 97, 67, 68, 68,
               68, 99, 69, 70, 70, 71, 101, 71, 72, 72]
PDF_CHILD = [0, 0, 80, 18, 18, 37, 37, 37, 37, 53,
             54, 70, 70, 70, 71, 94, 94, 118, 159, 203,
             245, 415, 341, 469, 395, 396, 398, 200, 201, 0,
             0, 0, 0, 0, 0, 0, 0, 0, 0, 0]
PDF_TAX = [452, 411, 248, 255, 216, 269, 284, 299, 418, 480,
           485, 492, 502, 509, 553, 559, 566, 575, 574, 578,
           581, 579, 579, 574, 573, 586, 590, 541, 523, 500,
           495, 495, 368, 261, 168, 71, 77, 77, 77, 77]
PDF_OTHEREXP = [480, 120, 120, 120, 120, 120, 120, 220, 120, 120,
                220, 200, 120, 220, 120, 120, 220, 80, 80, 180,
                80, 160, 180, 80, 80, 180, 80, 80, 180, 80,
                80, 260, 80, 80, 180, 80, 80, 180, 80, 80]

LINES.append("\n【支出項目の年次比較】（万円・許容差を超えた年のみ表示）")
# 支出合計の許容差は、社会保険料の差（PDFが厚生年金の上限を適用していない）を織り込んだ値。
# 住宅関連費は取得年のみ、PDFが自己資金・引っ越し費用を同じ行に含めるため一致しない。
# 理由が分かっている差異。ここに載っているものは「不一致」ではなく
# 「既知の差異」として数える。**理由を書けないものは載せない。**
KNOWN = {
    ("住宅関連費", 2027):
        "PDFは取得年の住宅関連費に自己資金424万円と引っ越し費用300万円を含めている。"
        "この試算はそれを「住宅の取得・住み替え費」に分けて計上している（合計は一致）。",
    ("支出合計", 2058):
        "PDFは2058年に住み替え関連の費用を計上している。この試算は住み替えなしの前提。",
    ("支出合計", 2060):
        "同上（2060年）。",
    ("その他支出", 2043):
        "PDFのその他支出に、内訳の記載がない40万円が含まれている。根拠が特定できないため計上していない。",
}
KNOWN_HIT = []

labels = [("支出合計", "expenseTotal", PDF_EXP, 60),
          ("生活費", "living", PDF_LIVING, 1),
          ("住宅関連費", "housing", PDF_HOUSING, 3),
          ("子ども関連費", "childTotal", PDF_CHILD, 3),
          ("税・社会保険料", "taxTotal", PDF_TAX, 120),
          ("その他支出", "otherExp", PDF_OTHEREXP, 3)]
for label, key, pdf_list, tol in labels:
    bad = []
    for i, exp in enumerate(pdf_list):
        y = 2026 + i
        if y not in rows:
            continue
        act = man(rows[y][key])
        if abs(act - exp) > tol:
            if (label, y) in KNOWN:
                KNOWN_HIT.append((label, y, f"{act:.0f}/{exp}"))
            else:
                bad.append(f"{y}:{act:.0f}/{exp}")
    if bad:
        NG += 1
        LINES.append(f"NG  {label:<38} 不一致 {len(bad)}/{len(pdf_list)}年")
        LINES.append(f"      " + "  ".join(bad[:14]) + ("  …" if len(bad) > 14 else ""))
    else:
        OK += 1
        kn = [k for k in KNOWN_HIT if k[0] == label]
        note = f"（既知の差異 {len(kn)}年をのぞく）" if kn else ""
        LINES.append(f"OK  {label:<38} 全{len(pdf_list)}年が許容差{tol}万円以内{note}")

# ---------------------------------------------------------------- 資産残高の乖離
PDF_ASSET = [2873, 2131, 2141, 2217, 2098, 2180, 2236, 2120, 2644, 3111,
             3492, 3853, 4300, 4661, 5065, 5462, 5746, 6090, 6519, 6825,
             7212, 6928, 7131, 7303, 7552, 7689, 7893, 8070, 8268, 8792,
             9324, 9648, 11169, 11300, 13244, 12989, 12973, 12791, 12813, 12839]
LINES.append("\n【金融資産残高の乖離】（万円・社会保険料の差に起因する既知の乖離）")
worst_pct, worst_year = 0.0, None
for i, exp in enumerate(PDF_ASSET):
    y = 2026 + i
    pct = (man(rows[y]["assetTotal"]) - exp) / exp * 100
    if abs(pct) > abs(worst_pct):
        worst_pct, worst_year = pct, y
for y in (2026, 2035, 2045, 2055, 2060, 2065):
    exp = PDF_ASSET[y - 2026]
    act = man(rows[y]["assetTotal"])
    LINES.append(f"    {y}年：計算 {act:>7,.0f} ／ PDF {exp:>7,.0f} "
                 f"／ 差 {act-exp:>+6,.0f}（{(act-exp)/exp*100:>+5.1f}%）")
LINES.append(f"    最大乖離：{worst_year}年 {worst_pct:+.1f}%")
if abs(worst_pct) <= 5.0:
    OK += 1
    LINES.append("OK  資産残高の乖離                               全40年が5%以内")
else:
    NG += 1
    LINES.append(f"NG  資産残高の乖離                               最大 {worst_pct:+.1f}% が5%を超過")

LINES.append("\n【運用資産（利回り3%のみで増える。取り崩しの挙動を確認）】（万円）")
for y, exp in [(2026, 1854), (2027, 1910)]:
    chk(f"{y}年", man(rows[y]["invest"]), exp, 2)

LINES.append("\n【住宅ローン残高】（万円）※CF表の残高行は取得年2027から始まる")
for y, exp in [(2027, 6988), (2028, 6823), (2045, 3718), (2058, 787), (2060, 268)]:
    chk(f"{y}年", man(rows[y]["loanBalance"]), exp, 3)

# ---------------------------------------------------------------- 教育費
LINES.append("\n【子ども関連費の総額】（万円・将来価値。PDFのCF表の合計）")
child_total = sum(r["childTotal"] for r in R["rows"])
chk("生涯の子ども関連費（2人分）", man(child_total), sum(PDF_CHILD), 40)

# ---------------------------------------------------------------- 出力
for line in LINES:
    print(line)

print()
print("=" * 96)
if KNOWN_HIT:
    print()
    print("【既知の差異】理由が分かっており、直す必要のないもの")
    for label, y, v in KNOWN_HIT:
        print(f"  {label} {y}年（計算/PDF = {v}）")
        print(f"    {KNOWN[(label, y)]}")
    print()
print(f"一致 {OK} 件 ／ 既知の差異 {len(KNOWN_HIT)} 件 ／ 不一致 {NG} 件 "
      f"／ 合計 {OK+NG} 件")
print("=" * 96)
print(f"住宅取得年: {R['buyYear']} ／ 資産が尽きる年齢: {R['depleteAge'] or 'なし'}")
