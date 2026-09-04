# -*- coding: utf-8 -*-
r"""v22 patch C：P1-1〜P1-4。

**P1-1 エンジンとUIの境界**
2つ残っていた。どちらも「エンジンだけを切り出した検証では再現できない」形。

  1. `defaults()`（エンジン側・行2022）が `insGuideTable()`（UI側・行7526）を呼ぶ。
     → `insGuideTable` は `P` しか触らない純関数なので、**エンジン側へ移す**。
  2. `validateParams(P)` が引数にないグローバル `SIM` を読む。
     → `validateParams(P, sim)` と第2引数で受ける。読み手を引数だけにする。

★v21で `dcMonthlyLimit`・`matchCapApplies`・`fmtMan1`・`fmtJP` を移したときに、
  同じ観点で `insGuideTable` と `SIM` を探していれば一緒に見つかった。
  **1件直したら、同じ形が他にないかを機械的に洗うこと。**

**P1-2 POLICYを変えても画面の説明が変わらない**
確定拠出年金の上限が3か所に直書きされていた（2.3万円／2.0万円／6.8万円／7.5万円）。
POLICYを99,000円に変えても、計算だけ変わって説明文は古いまま。
**台帳に集めた意味が無くなる。** `pol()` から引く。

**P1-3 自営業の入力語の不統一**
同じ画面に3つの言い方があった。
  「青色申告特別控除の前の事業利益」（正）／「事業所得（売上−経費）」（誤読を招く）
一般に「事業所得」は控除後の意味に読まれ得るので、控除後の額を入れると二重に引かれる。

**P1-4 印刷の確認が、機微情報を含むレポートを作ったあと**
`buildReport()` → `confirm()` の順。断っても `#report` は既に出来ている。
書き出し（`exportPlans`）は確認が先なので、そちらに揃える。
"""
import io
import re
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


# ---- P1-1a: insGuideTable をエンジン側へ移す ----
INS = '''/** 年齢別の目安を作る。
 *  いま入っている金額（取得前・取得後）を起点に、年齢による上がり方をかける。
 *  倍率の根拠：定期保険・収入保障保険・医療保険の保険料は年齢とともに上がり、
 *  10年更新型では更新のたびに1.4〜2倍になるのが一般的。
 *  一方で60歳以降は子が独立しローンも終わるため、死亡保障は縮小できる
 *  （火災保険と医療保険が中心になる）。 */
function insGuideTable(P){
  const L = P.living, F = P.family, H = P.house;
  const now = L.insurance;                 // いまの保険料
  const base = L.insuranceAfter;           // 住宅取得後の保険料
  const buyAge = H.buy ? H.buyAge : F.ageH;
  const rows = [{age:F.ageH, amount:now, rate:0}];
  if(buyAge > F.ageH) rows.push({age:buyAge, amount:base, rate:0});
  else rows[0] = {age:F.ageH, amount:base, rate:0};
  rows.push({age:45, amount:Math.round(base * 1.4), rate:0});
  rows.push({age:55, amount:Math.round(base * 2.0), rate:0});
  rows.push({age:P.retire.retireAgeH || 60, amount:Math.round(base * 0.6), rate:0});
  rows.push({age:70, amount:Math.round(base * 0.5), rate:0});
  /* 年齢が重複・逆順にならないよう整える。
     同じ年齢が2行あると、あとの行の金額が使われて意図とずれるため。 */
  L.insTable = rows
    .sort((a,b) => a.age - b.age)
    .filter((r,i,a) => i === 0 || r.age > a[i-1].age);
  return L.insTable;
}
'''
if t.count(INS) != 1:
    ng.append(f"insGuideTable の切り出し ({t.count(INS)}件/期待1)")
else:
    t = t.replace(INS, "/* ★`insGuideTable` はエンジン側（`defaults` の直前）へ移した（v22 P1-1）。\n"
                       "     `defaults()` から呼ぶのに定義がUI側にあり、エンジンだけを切り出した\n"
                       "     検証では `insGuideTable is not a function` で落ちていた。 */\n", 1)
    ANCHOR = 'const DEFAULT_PRESET = "buy";\nfunction defaults(presetKey, wKey, regionKey, typeKey){'
    if t.count(ANCHOR) != 1:
        ng.append(f"defaults のアンカー ({t.count(ANCHOR)}件/期待1)")
    else:
        t = t.replace(ANCHOR,
                      "/* ★UI側から移動（v22 P1-1）。`P` しか触らない純関数なので、\n"
                      "     エンジン側に置いて `defaults()` から安全に呼べるようにする。 */\n"
                      + INS + "\n" + ANCHOR, 1)

# ---- P1-1b: validateParams(P, sim) ----
sub("function validateParams(P){",
    '''/** 入力の矛盾・行き過ぎを拾う。
 *
 *  ★v21まで第2引数が無く、**グローバルの `SIM` を直接読んでいた**。
 *    同じ `P` でも `SIM` の有無で警告の件数が変わり、
 *    エンジンだけを切り出した検証では試算後の分岐を一度も通せなかった。
 *    引数で受け取る形にして、読み手を引数だけに閉じる（P1-1）。 */
function validateParams(P, sim){''',
    "validateParams のシグネチャ")
sub('''     SIM がある場合だけ判定する（描画時に呼ばれる） */
  if(typeof SIM !== "undefined" && SIM && SIM.rows){
    const work = SIM.rows.filter(r => r.ageH <= R.retireAgeH && !r.isSpecialYear);''',
    '''     試算結果が渡されたときだけ判定する（描画時に呼ばれる） */
  if(sim && sim.rows){
    const work = sim.rows.filter(r => r.ageH <= R.retireAgeH && !r.isSpecialYear);''',
    "validateParams 内の SIM 参照")
sub("  const issues = validateParams(PARAMS);",
    "  const issues = validateParams(PARAMS, SIM);",
    "validateParams の呼び出し側")

# ---- P1-2: 確定拠出年金の上限をPOLICYから引く ----
sub('''            : "会社員の上限は勤め先の制度で決まります（企業年金なし2.3万円・あり2.0万円）。"
              + "上の「勤め先に企業年金がある」の設定を確かめてください。");''',
    '''            : `会社員の上限は勤め先の制度で決まります`
              + `（企業年金なし${fmtMan1(pol("dc.idecoEmployeeNoDb"))}万円・`
              + `あり${fmtMan1(pol("dc.idecoEmployeeWithDb"))}万円）。`
              + `上の「勤め先に企業年金がある」の設定を確かめてください。`);''',
    "警告文の上限をPOLICY参照に")
sub('''      + `<div class="hint" style="margin:-2px 0 9px">
          iDeCoの上限は勤め先の制度で変わります（企業年金なし月2.3万円・あり月2.0万円）。
          自営業は月6.8万円で、<b>2026年12月から7.5万円</b>になります。</div>`''',
    '''      /* ★v21まで「2.3万円／2.0万円／6.8万円／7.5万円」を直書きしていた。
           POLICYを変えても画面の説明が古いまま残る（P1-2）。台帳から引く。 */
      + `<div class="hint" style="margin:-2px 0 9px">
          iDeCoの上限は勤め先の制度で変わります`
      + `（企業年金なし月${fmtMan1(pol("dc.idecoEmployeeNoDb"))}万円・`
      + `あり月${fmtMan1(pol("dc.idecoEmployeeWithDb"))}万円）。`
      + `自営業は月${fmtMan1(pol("dc.limitSelfEmployed"))}万円で、`
      + (POLICY.dc.limitSelfEmployed.next
          ? `<b>${polDateJP(POLICY.dc.limitSelfEmployed.next.from)}から`
            + `${fmtMan1(POLICY.dc.limitSelfEmployed.next.v)}万円</b>になります。`
          : "")
      + `</div>`''',
    "積立カードの説明をPOLICY参照に")
sub('''          + 'iDeCo（自営業は月' + pol("dc.limitSelfEmployed").toLocaleString() + '円まで。'
          + '2026年12月から' + (POLICY.dc.limitSelfEmployed.next
              ? POLICY.dc.limitSelfEmployed.next.v.toLocaleString() : '75,000') + '円）・' ''' .rstrip(),
    '''          + 'iDeCo（自営業は月' + pol("dc.limitSelfEmployed").toLocaleString() + '円まで。'
          + (POLICY.dc.limitSelfEmployed.next
              ? polDateJP(POLICY.dc.limitSelfEmployed.next.from) + 'から'
                + POLICY.dc.limitSelfEmployed.next.v.toLocaleString() + '円'
              : '') + '）・' ''' .rstrip(),
    "自営業カードの上限日付をPOLICY参照に")

# polDateJP を polFill の隣に足す
sub('''function polFill(html){''',
    '''/** POLICYが持つ日付（"2026-12-01"）を「2026年12月」の形にする。
 *  ★施行日を説明文に直書きすると、台帳を直しても文章が古いまま残る（P1-2）。 */
function polDateJP(iso){
  const m = /^(\\d{4})-(\\d{2})/.exec(String(iso || ""));
  return m ? `${m[1]}年${parseInt(m[2],10)}月` : String(iso || "");
}
function polFill(html){''',
    "polDateJP を追加")

# ---- P1-3: 自営業の入力語を統一 ----
SELF = "事業利益（青色申告特別控除の前）"
sub('''          ? "あなたの収入（事業所得＝売上−経費）" : "あなたの収入（給与・額面）",''',
    '''          ? "あなたの収入（青色申告特別控除の前の事業利益）" : "あなたの収入（給与・額面）",''',
    "収入カード名（あなた）")
sub('''          ? "パートナーの収入（事業所得＝売上−経費）" : "パートナーの収入（給与・額面）",''',
    '''          ? "パートナーの収入（青色申告特別控除の前の事業利益）" : "パートナーの収入（給与・額面）",''',
    "収入カード名（パートナー）")
sub('''          + '・<b>「年収」の欄には事業所得（売上−経費）を入れてください。</b>'
          + '給与ではないので給与所得控除は使わず、代わりに'
          + '青色申告特別控除（既定65万円）を引きます。白色申告なら0にしてください。<br>' ''' .rstrip(),
    '''          + '・<b>「年収」の欄には、青色申告特別控除を引く<u>前</u>の'
          + '事業利益（売上−必要経費）を入れてください。</b>'
          + '給与ではないので給与所得控除は使わず、代わりに'
          + '青色申告特別控除（既定65万円）を<b>このツールが引きます</b>。'
          + '控除後の額を入れると二重に引かれます。白色申告なら控除額を0にしてください。<br>' ''' .rstrip(),
    "自営業の注意書き")

if ng:
    print("NG:", " / ".join(ng))
    sys.exit(1)

# ---- P1-4: 印刷の確認を先に ----
sub('''function printReport(){
  buildReport();
  // レイアウトが確定してから印刷ダイアログを開く
  /* ★印刷・PDFにも家計の中身が入る（P1-11）。 */
  if(!confirm("このレポートには、入力した年収・資産・家族構成・住宅条件が含まれます。"
    + "共有先と保管場所を確かめてください。印刷（PDF保存）に進みますか？")) return;
  setTimeout(() => window.print(), 60);
}''',
    '''function printReport(){
  /* ★印刷・PDFにも家計の中身が入る。
     v21まで `buildReport()` のあとに断っていたため、
     **断っても `#report` に家計の中身が組み上がっていた**（P1-4）。
     ファイル書き出し（`exportPlans`）と同じく、作る前に断る。 */
  if(!confirm("このレポートには、入力した年収・資産・家族構成・住宅条件が含まれます。"
    + "共有先と保管場所を確かめてください。印刷（PDF保存）に進みますか？")) return;
  buildReport();
  // レイアウトが確定してから印刷ダイアログを開く
  setTimeout(() => window.print(), 60);
}''',
    "printReport の確認順")

if ng:
    print("NG:", " / ".join(ng))
    sys.exit(1)
P.write_text(t, encoding="utf-8")
print("OK v22 patch C（境界・POLICY直書き・自営業の語・印刷の確認順）")
