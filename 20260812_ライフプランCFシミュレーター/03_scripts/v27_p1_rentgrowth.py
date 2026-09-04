# -*- coding: utf-8 -*-
r"""v27 P1-4／P2-1／P2-2。

**P1-4｜家賃の上昇率に入力欄が無かった。**
  計算は `rentGrowth == null`（物価連動）と `0`（据え置き）を区別し、
  セットアップの案内も「『住宅とローン』のページの家賃の上昇率で、
  0%と物価並みの両方を試してください」と**存在しない欄を指していた**。
  12タブを探しても操作要素は0件（ChatGPT版の実測）。

  ★これは依頼者が2026-08-31に指摘した「心配ごとが2つしか見えない」と**同じ型**。
    案内が実物と食い違っている。**書いた案内どおりに操作できるかを通すこと。**

  値の持ち方は `house.rentGrowth`（null か数値）**1つだけ**にする。
  表示のための「モード」を別に保存すると、値とモードが食い違う経路ができる
  （v4の維持費で実際に起きた。CLAUDE.mdのルールD）。
    null → 物価上昇率と同じ ／ 0 → 上がらない ／ その他 → 自分で入れた年率

**P2-1｜比較の許可リストが `house` / `estate` を根ごと許可していた。**
  いまの結果に許可外差分は0件だが、将来フィールドが増えると
  比較軸の外の変更も自動的に許可される。**プリセットが実際に持つ葉パスから作る。**

**P2-2｜国保の説明が実装より古い。**
  画面は「前の年の事業所得を自動で引き継ぎます」だが、実装は
  事業所得＋公的年金等の雑所得＋その他の課税所得を繰り越す（v24で直した）。
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
# P1-4：家賃の上昇率の入力欄
# ============================================================
sub('''function chkField(label, path){''',
    '''/** 家賃の上昇率の入れ方。**保存する値は `house.rentGrowth` の1つだけ。**
 *
 *  ★モードを別に保存しない。保存すると「モードは据え置きなのに値は1.5%」という
 *    食い違いが作れてしまう（同じ値の設定経路を2本にしない）。
 *    表示するモードは値から引く：null＝物価連動／0＝上がらない／それ以外＝自分で入れた年率。
 *    「自分で入れた年率」に0を入れると表示は「上がらない」に戻るが、
 *    **意味は同じ0%なので情報は失われない。** */
function rentGrowthMode(P){
  const g = P.house.rentGrowth;
  if(g === null || g === undefined) return "inflation";
  return Number(g) === 0 ? "flat" : "custom";
}
function setRentGrowthMode(mode){
  const P = PARAMS;
  if(mode === "inflation") P.house.rentGrowth = null;
  else if(mode === "flat") P.house.rentGrowth = 0;
  else {
    /* 「自分で入れる」を選んだ直後の初期値は、いまの物価上昇率
       （それまでの計算と同じ結果から始まるので、変えた影響が読みやすい）。 */
    const g = P.house.rentGrowth;
    P.house.rentGrowth = (g === null || g === undefined || Number(g) === 0)
      ? Number(P.econ.inflation) || 0 : Number(g);
  }
  markEntered("house.rentGrowth");
  recalc();
}
/** 家賃の上昇率の入力欄。買う／借りるの結論を左右するので、賃貸のときは必ず見せる。 */
function rentGrowthField(){
  const P = PARAMS, m = rentGrowthMode(P);
  const id = nextFieldId("house.rentGrowth", "mode");
  const opt = (k, label) =>
    `<option value="${k}"${m === k ? " selected" : ""}>${label}</option>`;
  return `<div class="f"><label for="${id}">家賃の上昇率</label>
    <select id="${id}" onchange="setRentGrowthMode(this.value)">
      ${opt("inflation", `物価上昇率と同じ（いま ${fmtNum(P.econ.inflation)}%/年）`)}
      ${opt("flat", "上がらない（0%）")}
      ${opt("custom", "自分で年率を入れる")}
    </select><span class="u"></span></div>`
    + (m === "custom"
        ? numField("家賃の上昇率（年率）", "house.rentGrowth", "%/年", 0.1)
        : "")
    + `<div class="hint" style="margin:-2px 0 9px">
        <b>買うか借りるかの結論を、いちばん強く動かす前提のひとつです。</b>
        更新のたびに上がる物件も、何十年も据え置きの物件もあります。<br>
        <b>0%と物価並みの両方を試して、どちらでも結論が変わらないかを見てください。</b>
        （未設定＝物価上昇率と同じ、として計算します）</div>`;
}
function chkField(label, path){''',
    "rentGrowthField を追加")

sub('''      + manField("取得前の住宅関連費（年）","house.rentNow","家賃など")''',
    '''      + manField("取得前の住宅関連費（年）","house.rentNow","家賃など")
      /* ★家賃の上昇率。v26まで**計算だけがあって入力欄が無かった**。
           セットアップの案内は「『住宅とローン』のページの家賃の上昇率で」と
           存在しない欄を指していた（ChatGPT版のv25レビューで指摘・実測0件）。 */
      + rentGrowthField()''',
    "住宅ページに家賃の上昇率")

sub('''          ? manField("いまの住居費（年額）", "house.rentNow")
            + '<div class="hint" style="margin:-2px 0 9px">'
            + '家賃・共益費・駐車場代の合計を年額で。'
            + '<b>家賃が上がるかどうかは「買うか借りるか」の結論を左右します。</b>'
            + '「住宅とローン」のページの<b>家賃の上昇率</b>で、0%と物価並みの両方を試してください。</div>' ''' .rstrip(),
    '''          ? manField("いまの住居費（年額）", "house.rentNow")
            + '<div class="hint" style="margin:-2px 0 9px">'
            + '家賃・共益費・駐車場代の合計を年額で。</div>'
            /* ★案内で別ページへ送るのをやめ、**ここで入れられるようにした**。
                 v26は「『住宅とローン』のページの家賃の上昇率で試してください」と
                 書いていたが、その欄はどのページにも無かった。 */
            + rentGrowthField()''',
    "セットアップの住まいステップに家賃の上昇率")

# ============================================================
# P2-1：比較の許可リストを葉パスから作る
# ============================================================
sub('''  /* 住まいの軸。いまのプリセットは `house.buy` しか持たないが、
     プロフィールのプリセットは物件と不動産の前提を持つ。 */
  loadAllPresets:    COMPARE_COMMON.concat(["meta.preset", "house", "estate"]),''',
    '''  /* 住まいの軸。**プリセットが実際に持つキーから葉パスを作る**（`presetLeafPaths()`）。
     ★v26は `house` / `estate` を**根ごと**許可していた。いまの結果に許可外差分は
       0件だが、将来 `house` にフィールドが増えたとき、比較軸の外の変更も
       自動的に許可されてしまう。v23で `living.insuranceAfter` を根で許可していたために
       手入力の保険表が丸ごと置換されるP0を見逃した、あれと同じ形。 */
  loadAllPresets:    COMPARE_COMMON.concat(["meta.preset"]).concat(presetLeafPaths()),''',
    "COMPARE_ALLOWED の根許可をやめる")

sub('''const COMPARE_COMMON = ["meta.planName", "meta.memo", "meta.insReviewNeeded"];''',
    '''const COMPARE_COMMON = ["meta.planName", "meta.memo", "meta.insReviewNeeded"];

/** 住まいのプリセットが**実際に書き換えるキー**を、`PRESETS` の定義から集める。
 *
 *  ★差分そのものから作ると検査が自明に通ってしまう（自分で自分を許可する）。
 *    許可リストは**プリセットの定義**（何を変えると宣言しているか）から作り、
 *    実際の差分と突き合わせる。宣言していないものが動いたら不合格になる。 */
function presetLeafPaths(){
  const out = new Set(["house.buy"]);   // `planWithPreset` が必ず触る
  Object.keys(PRESETS).forEach(k => {
    const pre = PRESETS[k];
    ["house", "estate"].forEach(root => {
      const o = pre && pre[root];
      if(o && typeof o === "object")
        Object.keys(o).forEach(key => out.add(root + "." + key));
    });
  });
  return Array.from(out);
}''',
    "presetLeafPaths を追加")

# ============================================================
# P2-2：国保の説明を実装に合わせる
# ============================================================
sub("""          + '2年目以降は、このツールが前の年の事業所得を自動で引き継ぎます。</div>'""",
    """          + '2年目以降は、このツールが<b>前の年の「国保の計算対象になる所得」</b>を'
          + '自動で引き継ぎます'
          + '（事業所得＋公的年金等の雑所得＋その他の課税所得の合計）。</div>'""",
    "国保の説明を実装に合わせる")

if ng:
    print("NG:", " / ".join(ng))
    sys.exit(1)
P.write_text(t, encoding="utf-8")
print("OK v27 P1-4／P2-1／P2-2（家賃の上昇率・許可リストの葉パス化・国保の説明）")
