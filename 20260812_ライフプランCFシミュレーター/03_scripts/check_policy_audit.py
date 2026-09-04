# -*- coding: utf-8 -*-
r"""制度値（POLICY）と金額リテラルの監査。

**なぜ作ったか（2026-08-28）**
ChatGPTのレビューで「P0修正の直後、追加機能より先にやるべき」と位置づけられた。
リリース条件として次が挙がっている。

  1. 出所未分類の金額リテラル 0件
  2. 未定義POLICY参照 0件
  3. 計算用POLICYの未使用 0件
  4. POLICY値を変えたら該当結果が変わる変異試験
  5. 説明文の制度値の直書き 0件

**この監査が必要になった経緯**
・v12：`dc.limitEmployee` を分割したのに呼び出し側を直し忘れ、**undefined を返していた**
・v12：児童手当・老齢基礎年金・国民年金保険料が **POLICYにあるのに計算は直書き**
・v13：辞書に「2025年度 831,700円」が残っていた（**説明文の直書き**）
いずれも「台帳に載せた」だけで、**効いているかを確かめていなかった。**

**限界を先に書く**
JavaScriptのASTは解析していない。**字句（正規表現）で見ている。**
そのため次は苦手：
  ・動的に組み立てるパス（`pol("dc." + key)` など）
  ・文字列の中の数字が金額かどうかの判定
**「0件だから正しい」ではなく、「見えている範囲では問題がない」と読むこと。**

使い方:
  python 03_scripts/check_policy_audit.py                    # 汎用版の最新
  python 03_scripts/check_policy_audit.py 02_output/xxx.html
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


HTML = pick_html()
src = HTML.read_text(encoding="utf-8")
js = re.search(r"<script>(.*?)</script>", src, re.S).group(1)
STUB = ("var window={addEventListener:function(){},alert:function(){},"
        "print:function(){}};")
# 計算エンジンだけを切り出す（UI状態の手前まで）。ほかの検証スクリプトと同じ切り方。
ENGINE = STUB + js[:js.rfind("/* ", 0, js.find("   状態"))]

print(f"制度値と金額リテラルの監査: {HTML.name}")
print("=" * 78)

fails = []


def head(t):
    print(f"\n{'-' * 78}\n{t}\n{'-' * 78}")


# ============================================================
# POLICY のリーフを取り出す
# ============================================================
LEAVES_JS = """
function leaves(o, pre, acc){
  Object.keys(o).forEach(function(k){
    if(k==='asOf'||k==='note') return;
    var v=o[k];
    if(v && typeof v==='object' && !('v' in v)) leaves(v, pre?pre+'.'+k:k, acc);
    else if(v && typeof v==='object' && 'v' in v)
      acc.push({path:(pre?pre+'.'+k:k), v:v.v, label:v.label||'', verified:!!v.verified});
  });
  return acc;
}
JSON.stringify(leaves(POLICY,'',[]));
"""
leaves = json.loads(dukpy.evaljs(ENGINE + LEAVES_JS))
defined = {x["path"]: x for x in leaves}

# ============================================================
# 参照を集める
# ============================================================
refs = set(re.findall(r'pol(?:At)?\(\s*"([\w.]+)"', js))
refs |= set(re.findall(r'POLICY\.([\w.]+?)(?=[^\w.]|$)', js))
# `POLICY.asOf` `POLICY.note` は台帳そのものの属性なので除く
refs = {r for r in refs if r not in ("asOf", "note") and not r.endswith(".v")}
# `POLICY.dc.kyosaiMax.v` や `POLICY.dc.x.next.v.toLocaleString` のように、
# **リーフのあとに属性やメソッドが続く**ことがある。
# 末尾から、台帳の属性・メソッド名を落とし切って正規化する。
# （`.next.v.toLocaleString` を1回しか落とさず、存在しないキーとして誤検出した。）
META = {"v", "label", "src", "asOf", "verified", "note", "next", "from", "to",
        "toLocaleString", "toFixed", "toString"}


def norm(path):
    parts = path.split(".")
    while len(parts) > 1 and parts[-1] in META:
        parts.pop()
    return ".".join(parts)


refs = {norm(r) for r in refs}

head("1. 未定義のPOLICY参照（存在しないキーを読んでいないか）")
undefined = sorted(r for r in refs if r not in defined)
if undefined:
    fails.append("未定義のPOLICY参照")
    print(f"NG  {len(undefined)}件")
    for r in undefined:
        print(f"    {r}")
else:
    print("OK  0件")

head("2. 計算に使われていないPOLICY（台帳にあるだけの値）")
unused = sorted(p for p in defined if p not in refs)
if unused:
    print(f"参照が見つからないもの: {len(unused)}件")
    for p in unused:
        print(f"    {p:<34} {defined[p]['label'][:34]}")
    print("\n※ 画面の一覧（計算の前提）には全件出るので、"
          "「表示専用」として意図的なものも含まれる。")
    print("   ★ただし『計算に効くはずの値』がここに並んでいたら、それは断線している。")
else:
    print("OK  すべてのPOLICYがどこかから参照されている")

# ============================================================
# 3. 変異試験：値を変えたら結果が変わるか
# ============================================================
head("3. 変異試験（POLICYの値を変えたら、計算結果が変わるか）")
MUT_JS = """
/* ★1つの世帯だけで測ると、「その世帯では条件が当たらない」値まで
   「効かない」に見えてしまう（上限・ひとり親控除・退職金控除・遺族年金など）。
   **値ごとに、それが効くはずの世帯を含めて回す。** */
var PROFILES = {
  "会社員・夫婦・子1人": function(){
    var P = genericParams();
    P.family.ageH=40; P.family.ageW=38; P.family.hasSpouse=true;
    P.family.children=[{name:"A",birthYear:2024}];   /* 3歳未満 */
    P.work.typeH="employee";
    P.income.hBase=5000000; P.income.hTable=[{age:40,amount:5000000,rate:0}];
    P.income.wBase=3000000; P.income.wTable=[{age:38,amount:3000000,rate:0}];
    P.living.table=[{age:40,amount:3000000,rate:0}];
    P.retire.lumpH=15000000; P.retire.workYearsH=38;
    return P;
  },
  "自営業・単身": function(){
    var P = genericParams();
    P.family.ageH=40; P.family.hasSpouse=false; P.family.children=[];
    P.work.typeH="self";
    P.income.hBase=4000000; P.income.hTable=[{age:40,amount:4000000,rate:0}];
    P.living.table=[{age:40,amount:2400000,rate:0}];
    return P;
  },
  "ひとり親・子2人": function(){
    var P = genericParams();
    P.family.ageH=38; P.family.hasSpouse=false;
    P.family.children=[{name:"A",birthYear:2018},{name:"B",birthYear:2021}];
    P.work.typeH="employee";
    P.income.hBase=3500000; P.income.hTable=[{age:38,amount:3500000,rate:0}];
    P.living.table=[{age:38,amount:2600000,rate:0}];
    return P;
  },
  "高収入・子3人": function(){
    var P = genericParams();
    P.family.ageH=45; P.family.ageW=43; P.family.hasSpouse=true;
    P.family.children=[{name:"A",birthYear:2014},{name:"B",birthYear:2017},
                       {name:"C",birthYear:2020}];
    P.work.typeH="employee";
    /* ★標準報酬月額の上限（月139万）・標準賞与の年間上限を確実に超える水準にする。
       1,500万円では月125万で上限に届かず、上限値を変えても結果が動かなかった。 */
    P.income.hBase=30000000; P.income.hTable=[{age:45,amount:30000000,rate:0}];
    P.income.wBase=8000000; P.income.wTable=[{age:43,amount:8000000,rate:0}];
    P.living.table=[{age:45,amount:5000000,rate:0}];
    P.retire.lumpH=25000000; P.retire.workYearsH=25;
    return P;
  },
  "短い勤続・退職金あり": function(){
    /* ★退職所得控除の最低額は、勤続年数が短いときだけ効く。
       勤続3年では 40万×3＝120万 < 最低額80万… ではなく、
       最低額のほうが下回るので、勤続1〜2年で効く。 */
    var P = genericParams();
    P.family.ageH=58; P.family.hasSpouse=false; P.family.children=[];
    P.work.typeH="employee";
    P.income.hBase=6000000; P.income.hTable=[{age:58,amount:6000000,rate:0}];
    P.living.table=[{age:58,amount:2400000,rate:0}];
    P.retire.lumpH=3000000; P.retire.workYearsH=1;
    P.retire.retireAgeH=60;
    return P;
  },
  "ひとり親・控除の境目": function(){
    /* ★ひとり親控除の所得上限は、境目の近くでしか効かない。
       上限(500万)をまたぐ所得を置く。 */
    var P = genericParams();
    P.family.ageH=42; P.family.hasSpouse=false;
    P.family.children=[{name:"A",birthYear:2016}];
    P.work.typeH="employee";
    P.income.hBase=7000000; P.income.hTable=[{age:42,amount:7000000,rate:0}];
    P.living.table=[{age:42,amount:3000000,rate:0}];
    return P;
  }
};
function fingerprint(P){
  var s = 0;
  var S = simulate(P);
  /* 代表的な年の税社保・収入・資産を足して1つの数にする。 */
  for(var i=0;i<S.rows.length;i+=5){
    var r=S.rows[i];
    s += (r.taxTotal||0) + (r.incomeTotal||0) + (r.assetTotal||0);
  }
  /* ★「万一のとき」（遺族年金）は別の計算経路。
     `simulate` だけを見ていると、遺族厚生年金の制度値が
     「どの世帯でも効かない」に見えてしまう。 */
  try{
    var V = simulateSurvivor(P);
    var rows = (V && V.rows) ? V.rows : [];
    for(var j=0;j<rows.length;j+=5){
      var q=rows[j];
      s += (q.pensionW||0) + (q.pensionH||0) + (q.assetTotal||0);
    }
  }catch(e){ /* この世帯では回せない場合は無視する */ }
  return Math.round(s);
}
function setAt(path, val){
  var ks = path.split("."), o = POLICY;
  for(var i=0;i<ks.length-1;i++) o = o[ks[i]];
  var leaf = o[ks[ks.length-1]];
  var old = leaf.v;
  leaf.v = val;
  return old;
}
function mutate(path){
  var ks = path.split("."), o = POLICY;
  for(var i=0;i<ks.length-1;i++) o = o[ks[i]];
  var cur = o[ks[ks.length-1]].v;
  if(typeof cur !== "number") return {結果:"数値でない", 効いた世帯:[]};
  var hit = [], warnHit = [];
  /* ★`validateParams` の警告にだけ使う値がある（上限を超えたときの注意など）。
     `simulate` の結果には出ないので、警告文も指紋に含めて別に判定する。
     これを分けないと「断線している」と誤って報告してしまう。 */
  Object.keys(PROFILES).forEach(function(name){
    var mk = PROFILES[name];
    try{
      var pw = mk();
      /* 上限を超える拠出を置いて、警告が出る状態にする */
      pw.saving.dcModeH = true; pw.saving.dcMonthlyH = 90000;
      pw.saving.dcStartAgeH = 35; pw.saving.dcEndAgeH = 65;
      var w1 = JSON.stringify(validateParams(pw));
      var o2 = setAt(path, cur === 0 ? 1000 : cur * 1.37);
      var pw2 = mk();
      pw2.saving.dcModeH = true; pw2.saving.dcMonthlyH = 90000;
      pw2.saving.dcStartAgeH = 35; pw2.saving.dcEndAgeH = 65;
      var w2 = JSON.stringify(validateParams(pw2));
      setAt(path, o2);
      if(w1 !== w2 && warnHit.indexOf(name) < 0) warnHit.push(name);
    }catch(e){ /* 警告の検査ができない場合は無視 */ }
    /* ★params は POLICY から値を写して作る箇所がある（basicFullPension など）。
       **変更したあとに作り直さないと、写した値が古いままで「効かない」と誤判定する。**
       初版でこれをやり、老齢基礎年金と国民年金保険料を誤って「変わらない」と報告した。 */
    var before = fingerprint(mk());
    var old = setAt(path, cur === 0 ? 1000 : cur * 1.37);
    var after = fingerprint(mk());
    setAt(path, old);
    if(before !== after) hit.push(name);
  });
  if(!hit.length && warnHit.length)
    return {結果:"警告に効く", 効いた世帯:warnHit};
  return {結果: hit.length ? "効いた" : "変わらない", 効いた世帯: hit};
}
JSON.stringify((function(){
  var out = {};
  %s.forEach(function(p){ try{ out[p] = mutate(p); }catch(e){ out[p] = "エラー:" + e.message; } });
  return out;
})());
"""
targets = sorted(refs & set(defined))
res = json.loads(dukpy.evaljs(ENGINE + MUT_JS % json.dumps(targets)))

effective, inert, errored, skipped, warnonly = [], [], [], [], []
for p in targets:
    r = res.get(p)
    if isinstance(r, str):          # "エラー:..." が返る
        errored.append((p, r, ""))
    elif r.get("結果") == "数値でない":
        skipped.append(p)
    elif r.get("結果") == "効いた":
        effective.append((p, r.get("効いた世帯", [])))
    elif r.get("結果") == "警告に効く":
        warnonly.append((p, r.get("効いた世帯", [])))
    else:
        inert.append(p)

print(f"参照されているPOLICY: {len(targets)}件")
print(f"  どれかの世帯で結果が変わる : {len(effective)}件")
print(f"  どの世帯でも変わらない     : {len(inert)}件")
print(f"  警告文にだけ効く           : {len(warnonly)}件")
print(f"  数値でない（対象外）       : {len(skipped)}件")
print("")
print("※ 回した世帯：" + "／".join(
    ["会社員・夫婦・子1人", "自営業・単身", "ひとり親・子2人",
     "高収入・子3人", "短い勤続・退職金あり", "ひとり親・控除の境目"]))
print("   指紋には simulate（本編）と simulateSurvivor（万一のとき）の両方を含む。")
if errored:
    print(f"  エラー                   : {len(errored)}件")
    for p, a, _ in errored[:5]:
        print(f"    {p}: {a}")
if inert:
    print("\n※ 変わらないもの（表示専用か、この世帯では効かない条件のどちらか）:")
    for p in inert:
        print(f"    {p:<34} {defined[p]['label'][:34]}")
    print("   ★『計算に効くはず』の値がここにあれば、参照はあっても届いていない。")

# ============================================================
# 4. 説明文の中の制度値の直書き
# ============================================================
head("4. 説明文に制度値が直書きされていないか")
# POLICY の数値が、文字列リテラルの中に「そのまま」または「3桁区切り」で出ていないか
strings = re.findall(r'"([^"\\\n]{6,200})"|\'([^\'\\\n]{6,200})\'', js)
flat = [a or b for a, b in strings]
hard = []
for path, x in defined.items():
    v = x["v"]
    if not isinstance(v, (int, float)) or v < 1000:
        continue
    # ★3桁区切りの形だけを見る。生の数値だとコード中の比較式まで拾ってしまう
    #   （`p.r.salaryW < 3000000` を「直書き」と誤検出した）。
    pats = {f"{int(v):,}"}
    if int(v) < 10000:
        continue   # 4桁未満は区切りが出ないので判定できない
    for s in flat:
        if any(p in s for p in pats):
            # `{{path}}` で書いてあるものは対象外（polFill が差し込む）
            if "{{" in s:
                continue
            hard.append((path, int(v), s.strip()[:60]))
            break
if hard:
    print(f"NG  {len(hard)}件（説明文の中に制度値がそのまま書かれています）\n")
    for path, v, s in hard[:12]:
        print(f"    {path} = {v:,}")
        print(f"        …{s}…")
    print("\n   ★`{{POLICYのパス}}` と書いて polFill() に差し込ませること。")
    print("     直書きすると、制度値を直しても説明が古いまま残る（v13で3回起きた）。")
    fails.append("説明文の制度値の直書き")
else:
    print("OK  0件")

# ============================================================
# 5. 金額リテラルの出所分類
# ============================================================
head("5. 金額リテラルの出所（どのブロックで定義されているか）")
# 「金額らしい」数値＝4桁以上の整数リテラル
BLOCKS = [
    ("POLICY",  r"const POLICY = \{"),
    ("BENCH",   r"const BENCH = \{"),
    ("EDU",     r"const EDU\w* = \{"),
    ("REGION",  r"const REGIONS = \{"),
    ("SAMPLE",  r"const SAMPLE_PROFILES = \{"),
    ("PRESETS", r"const PRESETS = \{"),
    ("VERIFY",  r"const VERIFY = \{"),
    ("既定値",  r"function genericParams\(\)"),
    ("個人版の既定", r"function defaults\("),
]
marks = []
for name, pat in BLOCKS:
    m = re.search(pat, js)
    if m:
        marks.append((m.start(), name))
marks.sort()


def block_of(pos):
    cur = "その他"
    for start, name in marks:
        if pos >= start:
            cur = name
    return cur


counts = {}
unknown = []
for m in re.finditer(r"(?<![\w.])(\d{4,})(?![\w.])", js):
    i = m.start()
    # コメントの中は数えない
    oc, cc = js.rfind("/*", 0, i), js.rfind("*/", 0, i)
    if oc > cc:
        continue
    ls = js.rfind("\n", 0, i)
    if "//" in js[ls:i]:
        continue
    b = block_of(i)
    counts[b] = counts.get(b, 0) + 1
    if b == "その他":
        line = js[:i].count("\n") + 1
        unknown.append((line, js[max(0, i - 55):i + 45].replace("\n", " ")))

for k in sorted(counts, key=lambda k: -counts[k]):
    print(f"    {k:<14} {counts[k]:>5}件")
print(f"\n出所が分類できない金額リテラル: {len(unknown)}件")
if unknown:
    print("※ 計算式の係数・年齢・年・桁の定数なども混ざる。")
    print("   ★『世帯の金額』がここにあれば、出所を持たない数字が紛れている。")
    for line, ctx in unknown[:10]:
        print(f"  {line:>6}行  …{ctx}…")
    if len(unknown) > 10:
        print(f"  ほか {len(unknown)-10}件")

# ============================================================
print("\n" + "=" * 78)
if fails:
    print("NG  " + " / ".join(fails))
else:
    print("OK  未定義参照0件・説明文の直書き0件")
print("※ この監査は字句（正規表現）で見ています。ASTは解析していません。")
print("   動的に組み立てるパスや、文字列の中の数字は苦手です。")
print("   『0件だから正しい』ではなく『見えている範囲では問題がない』と読んでください。")
print("=" * 78)
sys.exit(1 if fails else 0)
