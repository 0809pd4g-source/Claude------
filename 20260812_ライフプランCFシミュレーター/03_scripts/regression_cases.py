# -*- coding: utf-8 -*-
"""世帯の型ごとの回帰テスト（12ケース＋保存データの移行）。

これまでのスモークテストは「全タブが描けるか」「恒等式が成り立つか」を見ていたが、
**世帯の型の組み合わせ**は網羅していなかった。
自営業×ひとり親、3人以上の大人、住宅モジュールOFFなどは一度も通していなかった。

各ケースで次を確かめる。
  (1) NaN / Infinity が出ないこと
  (2) 収入合計が内訳の和と一致すること（二重計上・計上漏れの検出）
  (3) 支出合計が内訳の和と一致すること
  (4) 金融資産が内訳の和と一致すること
  (5) ローン残高が増えないこと
  (6) 税・社会保険が就業形態に整合すること
      （自営業に雇用保険料がない／会社員にはある／自営業に老齢厚生年金がない）
  (7) パートナーなしならパートナーの税が0であること
  (8) 住宅を買わない設定で住宅の重大警告が出ないこと
  (9) 資産が異常な大きさにならないこと
  (10) 古い保存データが、いまの版で読めるキーに移行されること

★生活費の既定は「夫婦2人」を想定した仮の値なので、
  世帯人数の平方根で調整してから流す。そうしないと単身・ひとり親のケースが
  非現実的に破綻して、整合性の検査より前に結果が読めなくなる。

使い方:
  python 03_scripts/regression_cases.py                    # 汎用版の最新
  python 03_scripts/regression_cases.py 02_output/xxx.html  # 対象を指定
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
    cands = [p for p in sorted((ROOT / "02_output").glob("*_v*.html")) if "汎用版" in p.name]
    if not cands:
        raise SystemExit("汎用版のHTMLが 02_output に見つかりません")
    return cands[-1]


HTML = pick_html()
FULL = re.search(r"<script>(.*?)</script>", HTML.read_text(encoding="utf-8"), re.S).group(1)
WINDOW = 'var window={addEventListener:function(){},alert:function(){},print:function(){}};'
ENGINE = (WINDOW + FULL)[:(WINDOW + FULL).rfind("/* ", 0, (WINDOW + FULL).find("   状態"))]


def dom_stub():
    """スモークテストのDOMスタブを、**テキストとして**抜き出す。

    smoke_test.py を exec すると、その冒頭で sys.stdout が同じバッファを包む
    TextIOWrapper に差し替えられ、破棄時にこちらの出力先まで閉じてしまう。
    実行せずに文字列を取り出すだけにする。
    """
    src = (ROOT / "03_scripts" / "smoke_test.py").read_text(encoding="utf-8")
    m = re.search(r'DOM_STUB\s*=\s*r?"""(.*?)"""', src, re.S)
    if not m:
        raise SystemExit("smoke_test.py から DOM_STUB を取り出せませんでした")
    return m.group(1)


# 生活費を世帯人数に合わせる（既定は夫婦2人を想定した仮の値）
FIT_LIVING = """
  var n = (P.family.hasSpouse ? 2 : 1) + ((P.family.children||[]).length);
  P.living.table = [{age:P.family.ageH,
                     amount: Math.round(1800000*Math.sqrt(n)/10000)*10000, rate:0}];
"""

CASES = [
    ("1. 単身・会社員・賃貸", """
     P.meta.household="single"; P.family.hasSpouse=false; P.family.children=[];
     P.work.typeH="employee"; P.income.hBase=4500000; P.income.wBase=0;
     P.house.buy=false; P.house.rentNow=1080000;
    """),
    ("2. 単身・自営業・賃貸", """
     P.meta.household="single"; P.family.hasSpouse=false; P.family.children=[];
     P.work.typeH="self"; P.income.hBase=6000000; P.income.wBase=0;
     P.retire.lumpH=0; P.house.buy=false; P.house.rentNow=1080000;
    """),
    ("3. 夫婦・会社員2人・子なし", """
     P.family.hasSpouse=true; P.family.children=[];
     P.work.typeH="employee"; P.work.typeW="employee";
     P.income.hBase=5500000; P.income.wBase=4500000; P.house.buy=false;
    """),
    ("4. 夫婦・会社員＋自営業", """
     P.family.hasSpouse=true; P.family.children=[];
     P.work.typeH="employee"; P.work.typeW="self";
     P.income.hBase=5500000; P.income.wBase=4000000; P.retire.lumpW=0;
    """),
    ("5. ひとり親＋子ども1人", """
     P.meta.household="parent"; P.family.hasSpouse=false;
     P.income.hBase=4500000; P.income.wBase=0;
     P.family.children=[{name:"第一子", birthYear:P.meta.baseYear-8}];
     P.house.buy=false; P.house.rentNow=1200000;
    """),
    ("6. 夫婦＋子2人＋住宅購入", """
     P.family.hasSpouse=true;
     P.family.children=[{name:"第一子", birthYear:P.meta.baseYear+2},
                        {name:"第二子", birthYear:P.meta.baseYear+4}];
     P.income.hBase=5500000; P.income.wBase=4500000;
     P.house.buy=true; P.house.buyAge=P.family.ageH+1;
    """),
    ("7. すでに持ち家・ローン返済中", """
     P.family.ageH=45; P.family.ageW=43; P.family.hasSpouse=true;
     P.family.children=[{name:"第一子", birthYear:P.meta.baseYear-10}];
     P.income.hBase=7000000; P.income.wBase=3500000;
     P.house.buy=true; P.house.buyAge=40; P.house.price=42000000;
     P.house.loans=[{name:"あなた", amount:38000000, years:35, steps:[{y:1,rate:1.0}]}];
    """),
    ("8. 3人以上の大人（同居の親を その他収入・支出 で表す）", """
     P.family.hasSpouse=true; P.family.children=[];
     P.income.hBase=5500000; P.income.wBase=4000000;
     P.other.incomes=[{name:"同居の親の年金", cat:"misc", kind:"yearly",
                       from:P.family.ageH, to:P.family.ageH+25,
                       amount:1800000, every:0, taxFree:1}];
     P.other.items=[{name:"親の生活費・医療費", cat:"misc", kind:"yearly",
                     from:P.family.ageH, to:P.family.ageH+25,
                     amount:1200000, every:0}];
    """),
    ("9. 副業あり（課税されること）", """
     P.family.hasSpouse=true; P.family.children=[];
     P.income.hBase=5000000; P.income.wBase=4000000;
     P.other.incomes=[{name:"副業", cat:"misc", kind:"yearly",
                       from:P.family.ageH, to:P.retire.retireAgeH,
                       amount:1200000, every:0}];
    """),
    ("10. 収入が下がる・育休あり", """
     P.family.hasSpouse=true;
     P.family.children=[{name:"第一子", birthYear:P.meta.baseYear+2}];
     P.income.hBase=6000000; P.income.wBase=5000000;
     P.meta.hIncome="flat"; P.meta.wScenario="down60";
    """),
    ("11. 住宅モジュールOFF（賃貸を続ける）", """
     P.family.hasSpouse=true; P.family.children=[];
     P.house.buy=false; P.house.rentNow=1440000; P.house.rentGrowth=0;
     P.estate.track=false;
    """),
    ("12. 極端な設定（高収入・高額物件・高金利・子3人）", """
     P.family.hasSpouse=true;
     P.family.children=[{name:"第一子", birthYear:P.meta.baseYear+1},
                        {name:"第二子", birthYear:P.meta.baseYear+3},
                        {name:"第三子", birthYear:P.meta.baseYear+5}];
     P.income.hBase=20000000; P.income.wBase=12000000;
     P.house.buy=true; P.house.price=200000000;
     P.house.loans=[{name:"あなた", amount:180000000, years:35, steps:[{y:1,rate:8.0}]}];
     P.econ.deposit=50000000; P.house.selfFund=30000000;
    """),
]

PROBE = """
var CASES = __CASES__, FIT = __FIT__;
var R = [];
CASES.forEach(function(c){
  var out = {name:c[0]};
  try{
    var P = defaults();
    (new Function("P","hTableOf","wTableOf", c[1]))(P, hTableOf, wTableOf);
    (new Function("P", FIT))(P);
    if(P.meta.hIncome !== "custom") P.income.hTable = hTableOf(P.meta.hIncome, P);
    if(P.family.hasSpouse && P.meta.wScenario !== "custom")
      P.income.wTable = wTableOf(P.meta.wScenario, P);
    if(!P.family.hasSpouse) P.income.wTable = [{age:P.family.ageW, amount:0, rate:0}];

    var S = simulate(P), bad = [];
    var isBad = function(v){ return typeof v === "number" && !isFinite(v); };

    S.rows.forEach(function(r, i){
      Object.keys(r).forEach(function(k){
        if(isBad(r[k])) bad.push(r.year + " " + k + " が数値でない"); });
      var inc = r.salaryH + r.salaryW + r.pensionH + r.pensionW + r.lumpH + r.lumpW
              + r.otherIncome + r.sellProceeds;
      if(Math.abs(inc - r.incomeTotal) > 2) bad.push(r.year + " 収入合計が内訳と合わない");
      var exp = r.living + r.housing + r.acquisition + r.loanRepay + r.insurance
              + r.childTotal + r.otherLoanRepay + r.taxTotal + r.medical
              + r.careCost + r.otherExp;
      if(Math.abs(exp - r.expenseTotal) > 2) bad.push(r.year + " 支出合計が内訳と合わない");
      var at = r.deposit + r.invest + r.nisaBal + r.stockBal - r.debt;
      if(Math.abs(at - r.assetTotal) > 2) bad.push(r.year + " 金融資産が内訳と合わない");
      if(i > 0 && r.loanBalance > S.rows[i-1].loanBalance + 2 && !r.isBuyYear)
        bad.push(r.year + " ローン残高が増えている");
      if(Math.abs(r.assetTotal) > 1e15) bad.push(r.year + " 資産が異常な大きさ");
    });

    var wt = P.work.typeH, r0 = S.rows[0];
    if(wt === "self" && r0.taxH.si.koyo > 0) bad.push("自営業なのに雇用保険料がある");
    if(wt === "employee" && r0.salaryH > 0 && r0.taxH.si.koyo <= 0)
      bad.push("会社員なのに雇用保険料がない");
    if(!P.family.hasSpouse && r0.taxW.total > 0)
      bad.push("パートナーなしなのにパートナーの税がある");
    if(wt === "self"){
      var e = estimatePension(P.income.hTable, P.retire.workStartH, P.retire.retireAgeH,
                              P.retire, "self");
      if(e.kosei > 0) bad.push("自営業なのに老齢厚生年金がある");
    }
    var v = validateParams(P);
    var hb = v.filter(function(x){
      return x.level === "bad" && /住宅|物件|借入|自己資金|頭金/.test(x.msg); });
    if(!P.house.buy && hb.length)
      bad.push("住宅を買わない設定なのに住宅の重大警告: " + hb[0].msg);

    out.rows = S.rows.length;
    out.last = Math.round(S.summary.last/10000);
    out.dep  = S.depleteAge;
    out.badN = v.filter(function(x){ return x.level === "bad"; }).length;
    out.errs = bad.slice(0, 4);
    out.errN = bad.length;
  }catch(e){ out.crash = (e && e.message) ? e.message : String(e); }
  R.push(out);
});
JSON.stringify(R);
"""

MIGRATE = """
var R = [];
try{
  var old = {name:"古いプラン", params:{
    meta:{preset:"koiwa", wScenario:"w550", region:"kanagawa",
          hIncome:"flat800", concerns:["昔の心配","retire"]},
    family:{hasSpouse:true}, work:{typeH:"kaishain", typeW:"jieigyou"},
    income:{}, house:{}, other:{}}};
  var m = migratePlans([old]), mp = m[0].params, miss = [];
  if(!REGIONS[mp.meta.region])       miss.push("地域のキーが存在しない: " + mp.meta.region);
  if(!PRESETS[mp.meta.preset])       miss.push("住宅プランのキーが存在しない: " + mp.meta.preset);
  if(!WSCENARIOS[mp.meta.wScenario]) miss.push("収入シナリオのキーが存在しない: " + mp.meta.wScenario);
  if(!HINCOME[mp.meta.hIncome])      miss.push("昇給カーブのキーが存在しない: " + mp.meta.hIncome);
  if(!WORKTYPES[mp.work.typeH])      miss.push("就業形態のキーが存在しない: " + mp.work.typeH);
  if(mp.meta.concerns.length !== 1)  miss.push("存在しない心配ごとが落ちていない");
  var S = simulate(mp);
  R.push({name:"13. 古い保存データの移行", rows:S.rows.length,
          last:Math.round(S.summary.last/10000), dep:S.depleteAge, badN:0,
          errs:miss.slice(0,4), errN:miss.length});
}catch(e){
  R.push({name:"13. 古い保存データの移行", crash:(e && e.message) ? e.message : String(e)});
}
JSON.stringify(R);
"""

print("=" * 96)
print(f"世帯の型ごとの回帰テスト　対象: {HTML.name}")
print("=" * 96)

code = PROBE.replace("__CASES__", json.dumps(CASES)).replace("__FIT__", json.dumps(FIT_LIVING))
results = json.loads(dukpy.evaljs(ENGINE + code))
# 移行のテストはUI側の関数を使うのでDOMスタブつきで流す
results += json.loads(dukpy.evaljs(dom_stub() + FULL + MIGRATE))

ng = 0
for r in results:
    if "crash" in r:
        print(f"  NG  {r['name']}")
        print(f"      落ちた: {r['crash']}")
        ng += 1
        continue
    if r["errN"]:
        ng += 1
    dep = f"{r['dep']}歳枯渇" if r["dep"] else "枯渇なし"
    print(f"  {'OK ' if r['errN'] == 0 else 'NG '} {r['name']}")
    print(f"      {r['rows']}年 / 最終 {r['last']:>8,}万円 / {dep}"
          f" / 入力の重大な問題 {r['badN']}件")
    for e in r["errs"]:
        print(f"      ★ {e}")
    if r["errN"] > len(r["errs"]):
        print(f"      ★ ほか {r['errN'] - len(r['errs'])}件")

print("=" * 96)
print(f"{len(results)}ケース中 {len(results)-ng}件OK ／ {ng}件NG")
print("=" * 96)
if ng:
    print("※ NGが出たケースでは、その世帯の型で計算が信頼できません。")
    sys.exit(1)
print("すべてのケースで、数値の異常・二重計上・整合性の破れがありませんでした。")
print("※ このテストは「計算が矛盾していないか」を見るものです。")
print("　 前提そのものが妥当かどうかは別の話で、それは利用者が判断する部分です。")
