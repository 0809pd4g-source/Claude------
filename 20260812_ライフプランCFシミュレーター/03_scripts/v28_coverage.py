# -*- coding: utf-8 -*-
r"""v28：セットアップの網羅チェックを「宣言」から「実際の描画」まで見る形へ。

★ChatGPT版V78から取り込む。V78の `v78WizardCoverageAudit()` は
  **各ステップを実際に描画して、想定のセレクタが存在するか**を見ており、
  購入ON／OFFの両方で測っている。

  こちらの `checkWizardCoverage()` は `WIZ_STEPS[].covers` の一覧を
  `READY_STEPS` と突き合わせるだけだった。そのため：

  - **宣言した欄を置き忘れても通る**（`covers` に書けば合格になる）
  - **分岐を見ない**。実測で、住まいに「これから購入」を選んで見えている欄を
    すべて埋めても **9/10・足りない「いまの住居費」**（段階1）で止まるのに、
    `checkWizardCoverage()` は **0件**を返していた。

  ★「案内どおりに操作して最終段階に到達するか」は、V76・V78へこちらが指摘した観点。
    **自分では機械で測っていなかった。**

  あわせて、購入の分岐にも「取得するまでの住居費」と家賃の上昇率を置く
  （取得までの年数ぶん、実際に家計から出ていくお金なので必要）。
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


# ---- 購入の分岐にも「取得するまでの住居費」を置く ----
sub('''            + manField("物件価格", "house.price")
            + numField(hs === "own" ? "取得したときのあなたの年齢" : "取得するときのあなたの年齢",
                       "house.buyAge", "歳")''',
    '''            + manField("物件価格", "house.price")
            + numField(hs === "own" ? "取得したときのあなたの年齢" : "取得するときのあなたの年齢",
                       "house.buyAge", "歳")
            /* ★取得するまでの住居費。**購入する世帯にも要る**（取得年までは家計から出ていく）。
                 v27はこの欄を賃貸の分岐にしか置いていなかったため、
                 購入を選ぶとセットアップを一周しても 9/10 で止まっていた。
                 すでに持ち家なら過去の話なので聞かない。 */
            + (hs === "own" ? ""
                : manField("取得するまでの住居費（年額）", "house.rentNow")
                  + '<div class="hint" style="margin:-2px 0 9px">'
                  + 'いま払っている家賃・共益費・駐車場代の合計を年額で。'
                  + '取得する年まで、この金額がかかるものとして計算します。</div>'
                  + rentGrowthField())''',
    "購入の分岐に取得前の住居費")

# ---- 網羅チェックを、分岐ごとに実際へ描画して確かめる ----
sub('''function checkWizardCoverage(){
  const need = [];
  READY_STEPS.forEach(s => s.need.forEach(n => need.push({path:n[0], label:n[1]})));
  const covered = new Set();
  WIZ_STEPS.forEach(s => (s.covers || []).forEach(p => covered.add(p)));
  return need.filter(n => !covered.has(n.path));
}''',
    '''/** セットアップの本文（HTML）に、そのパスの入力欄が**実際に描かれているか**。
 *  `numField`／`manField` は `onNum('パス'` / `onMan('パス'`、
 *  年齢別テーブルは `onRowMan('表のパス',行,'キー'` を出す。 */
function wizHtmlHasField(html, path){
  if(html.indexOf("onNum('" + path + "'") >= 0) return true;
  if(html.indexOf("onMan('" + path + "'") >= 0) return true;
  const m = path.match(/^(.*)\\.(\\d+)\\.([A-Za-z]+)$/);
  if(m){
    if(html.indexOf("onRowMan('" + m[1] + "'," + m[2] + ",'" + m[3] + "'") >= 0) return true;
    if(html.indexOf("onRow('" + m[1] + "'," + m[2] + ",'" + m[3] + "'") >= 0) return true;
  }
  return false;
}
/** 住まいの分岐を、`PARAMS` を触らずに候補の上で作る。 */
function withHousing(P, key){
  const q = clone(P);
  if(key === "rent"){ q.house.buy = false; }
  else if(key === "own"){
    q.house.buy = true;
    if(q.house.buyAge >= q.family.ageH) q.house.buyAge = Math.max(20, q.family.ageH - 5);
  }else{
    q.house.buy = true;
    if(q.house.buyAge < q.family.ageH) q.house.buyAge = q.family.ageH + 1;
  }
  q.meta.housing = key;
  q.meta.preset = (key === "rent") ? "rent" : "buy";
  return q;
}
/** セットアップが `READY_STEPS` の必要項目を網羅しているか。
 *
 *  ★見るのは2つ。**宣言しているか**（`covers`）と、**実際に描かれるか**（本文のHTML）。
 *    v27は宣言だけを見ていたので、購入の分岐で家賃の欄が無くても**0件**を返していた
 *    （実測では 9/10 で止まる）。描画まで見る形はChatGPT版V78から取り込んだ。
 *  ★分岐（賃貸／これから購入／すでに持ち家）ごとに測る。
 *    分岐で必要な項目が変わるのに、1つの状態でしか測っていなかった。 */
function checkWizardCoverage(){
  const savedAt = WIZ_AT, savedParams = PARAMS;
  const out = [];
  try{
    HOUSING_KEYS.forEach(branch => {
      PARAMS = withHousing(savedParams, branch);
      const need = [];
      READY_STEPS.forEach(s =>
        needsOf(s, PARAMS).forEach(n => need.push({path:n[0], label:n[1]})));
      const covered = new Set();
      WIZ_STEPS.forEach(s => (s.covers || []).forEach(p => covered.add(p)));
      /* 入力のステップだけを描く（確認のステップはこの関数自身を呼ぶので入れない）。 */
      let html = "";
      WIZ_STEPS.forEach((s, i) => {
        if(s.kind === "view") return;
        WIZ_AT = i;
        try{ html += wizBody(); }catch(e){ /* 描けない分岐は下の判定で落ちる */ }
      });
      need.forEach(n => {
        const declared = covered.has(n.path);
        const rendered = wizHtmlHasField(html, n.path);
        if(!declared || !rendered)
          out.push({branch:(HOUSINGS[branch] || {}).short || branch,
                    path:n.path, label:n.label, 宣言:declared, 描画:rendered});
      });
    });
  }finally{
    PARAMS = savedParams; WIZ_AT = savedAt;
  }
  return out;
}''',
    "checkWizardCoverage を分岐＋描画で見る")

# ---- covers を実態に合わせる ----
sub('''  {t:"住まい",     n:"住まいはどうしますか",           kind:"input",
   covers:["house.rentNow"]},''',
    '''  {t:"住まい",     n:"住まいはどうしますか",           kind:"input",
   covers:["house.rentNow", "house.price", "house.loans.0.years"]},''',
    "住まいステップの covers")

if ng:
    print("NG:", " / ".join(ng))
    sys.exit(1)
P.write_text(t, encoding="utf-8")
print("OK v28（網羅チェックを分岐＋実描画で見る・購入分岐に取得前の住居費）")
