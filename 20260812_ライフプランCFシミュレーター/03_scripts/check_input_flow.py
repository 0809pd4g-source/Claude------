# -*- coding: utf-8 -*-
r"""「未入力から自分の数字を入れる」経路の検査。

**なぜ作ったか（2026-08-26）**
ChatGPTの独立レビューで、汎用版v7に重いP0が見つかった。
未入力から 年齢40・年収600万・生活費25万 を入れても、
`income.hBase` は更新されるのに `income.hTable` が0円のままで、
**初年度の給与が0円**になっていた。
利用者は「年収600万円を入れた結果」のつもりで、無収入世帯の破綻結果を見ていた。

**私の既存スイートは、これを一度も検出できなかった。**
PDF照合も13ケース回帰も `defaults()` からパラメータを作るため、
`hTable` に最初から正しい値が入っている。
**v6で入れた「未入力から開始」という中心機能の経路を、一度も通っていなかった。**

★教訓：**新しい入口を作ったら、その入口を通る検査を同時に作る。**
  既存の検査は、既存の入口しか通らない。

使い方:
  python 03_scripts/check_input_flow.py                    # 汎用版の最新
  python 03_scripts/check_input_flow.py 02_output/xxx.html  # 対象を指定
"""
import io
import json
import re
import sys
from pathlib import Path

import dukpy

ROOT = Path(__file__).resolve().parent.parent
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")


def pick_html():
    if len(sys.argv) > 1:
        p = Path(sys.argv[1])
        return p if p.is_absolute() else (ROOT / p)
    cands = [p for p in (ROOT / "02_output").glob("*_v*.html") if "汎用版" in p.name]
    if not cands:
        raise SystemExit("汎用版のHTMLが 02_output に見つかりません")

    def ver(p):
        m = re.search(r"_v(\d+)\.html$", p.name)
        return int(m.group(1)) if m else 0

    return max(cands, key=ver)


def dom_stub():
    """スモークテストのDOMスタブをテキストとして借りる。"""
    src = (ROOT / "03_scripts" / "smoke_test.py").read_text(encoding="utf-8")
    m = re.search(r'DOM_STUB\s*=\s*r?"""(.*?)"""', src, re.S)
    if not m:
        raise SystemExit("smoke_test.py から DOM_STUB を取り出せませんでした")
    return m.group(1)


HTML = pick_html()
FULL = re.search(r"<script>(.*?)</script>", HTML.read_text(encoding="utf-8"), re.S).group(1)

PROBE = r"""
var R = {};
/* 未入力の状態から始める。ここが v6 で入れた新しい入口。 */
PARAMS = blankParams();
SIM = simulate(PARAMS);
R.blankStart = {
  blank: !!PARAMS.meta.blank,
  preset: PARAMS.meta.preset,
  buy: !!PARAMS.house.buy,
  hBase: PARAMS.income.hBase,
  firstSalary: SIM.rows[0].salaryH
};

/* 利用者と同じ順で入れる（画面の入口 onNum / onMan を通す） */
onNum("family.ageH", 40);
onMan("income.hBase", 600);
onMan("living.table.0.amount", 25);

var f = SIM.rows[0];
var parts = f.salaryH + f.salaryW + f.pensionH + f.pensionW
          + f.lumpH + f.lumpW + f.otherIncome + f.sellProceeds;
R.afterInput = {
  hBase: PARAMS.income.hBase,
  tableRows: PARAMS.income.hTable,
  firstSalary: f.salaryH,
  incomeTotal: f.incomeTotal,
  partsSum: parts,
  blank: !!PARAMS.meta.blank
};

/* パートナーも同じ経路を通るか */
PARAMS.family.hasSpouse = true;
onNum("family.ageW", 38);
onMan("income.wBase", 400);
R.spouse = {
  wBase: PARAMS.income.wBase,
  wTable: PARAMS.income.wTable,
  firstSalaryW: SIM.rows[0].salaryW
};

/* 負試験：ベース年収とテーブルを意図的に切り離すと、食い違いが見えること */
PARAMS.income.hTable = [{age:40, amount:0, rate:0}];
SIM = simulate(PARAMS);
R.negative = {
  hBase: PARAMS.income.hBase,
  firstSalary: SIM.rows[0].salaryH,
  mismatch: (PARAMS.income.hBase > 0 && SIM.rows[0].salaryH === 0)
};
JSON.stringify(R);
"""

code = dom_stub() + "\n" + FULL + "\n" + PROBE
try:
    R = json.loads(dukpy.evaljs(code))
except Exception as e:  # noqa: BLE001
    print(f"NG  実行できませんでした: {e}")
    sys.exit(1)

print(f"入力経路の検査: {HTML.name}")
print("=" * 78)
ng = 0

b = R["blankStart"]
print("\n【未入力で始めたとき】")
for label, ok, detail in [
    ("未入力の印が立つ", b["blank"], b["blank"]),
    ("住まいが賃貸で始まる（preset と house.buy が一致）",
     (b["preset"] == "rent" and not b["buy"]), f"preset={b['preset']} buy={b['buy']}"),
    ("年収が0で始まる", b["hBase"] == 0, b["hBase"]),
]:
    print(("  OK  " if ok else "  NG  ") + label + f"   {detail}")
    if not ok:
        ng += 1

a = R["afterInput"]
print("\n【年齢40・年収600万・生活費25万 を入れたあと】")
checks = [
    ("ベース年収に入る", a["hBase"] == 6000000, a["hBase"]),
    ("**年齢別テーブルにも入る**", any(r["amount"] == 6000000 for r in a["tableRows"]),
     a["tableRows"]),
    ("テーブルの開始年齢が40に揃う", any(r["age"] == 40 for r in a["tableRows"]),
     [r["age"] for r in a["tableRows"]]),
    ("**初年度の給与が600万円になる**", abs(a["firstSalary"] - 6000000) < 100000,
     a["firstSalary"]),
    ("収入合計が内訳の和と一致", abs(a["partsSum"] - a["incomeTotal"]) < 2,
     f"{a['partsSum']} vs {a['incomeTotal']}"),
    ("3項目そろって未入力が解除される", not a["blank"], a["blank"]),
]
for label, ok, detail in checks:
    print(("  OK  " if ok else "  NG  ") + label + f"   {detail}")
    if not ok:
        ng += 1

s = R["spouse"]
print("\n【パートナーも同じ経路を通るか】")
for label, ok, detail in [
    ("ベース年収に入る", s["wBase"] == 4000000, s["wBase"]),
    ("**年齢別テーブルにも入る**", any(r["amount"] == 4000000 for r in s["wTable"]),
     s["wTable"]),
    ("初年度の給与に出る", abs(s["firstSalaryW"] - 4000000) < 100000, s["firstSalaryW"]),
]:
    print(("  OK  " if ok else "  NG  ") + label + f"   {detail}")
    if not ok:
        ng += 1

n = R["negative"]
print("\n【負試験：ベース年収とテーブルを切り離す】")
print(("  OK  " if n["mismatch"] else "  NG  ")
      + "切り離すと初年度給与が0になり、食い違いが見える   "
      + f"hBase={n['hBase']} salary={n['firstSalary']}")
if not n["mismatch"]:
    ng += 1
    print("      ※これが検出できないと、この検査自体が意味を持ちません")

print("\n" + "=" * 78)
if ng == 0:
    print("結果: 異常なし（入力した年収が年次計算に届いています）")
    sys.exit(0)
print(f"結果: {ng}件のNG。**入力した数字が計算に届いていません**")
sys.exit(1)
