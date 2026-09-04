# -*- coding: utf-8 -*-
r"""v24 patch D：P1-1（確認済みが編集後も残る）＋P2-1（保存後の書き戻し確認）
             ＋ChatGPT版の査読から自分に取り込むもの（`.f` ラベルの潰れ）。

**P1-1 何が起きていたか**
v23で「自治体・年度を確認した」チェックを1つ持たせた。しかし
**チェックしたあとに料率を99%に変えても、確認済みのまま警告が出ない。**

★v23で「2項目のANDを代用にしない」と直したのに、**代わりに置いた旗が値の変化を見ていない。**
  「確認した」は**その時点の値に対する確認**なので、値と一緒に持たないと意味が薄れる。

**直し方**：確認したときの指紋（自治体・年度・国保の値のハッシュ・確認日）を持ち、
現在値の指紋と一致するときだけ確認済みとみなす。1項目でも変えれば自動で未確認へ戻る。

**P2-1（ChatGPT版から取り込む）**
`localStorage.setItem()` が例外を出さずに別の内容を書く環境で、
メモリ1件・保存 `[]`・成功表示、という状態になった。
ChatGPT版 `v61StorePlans` は `setItem` のあと `getItem` して一致を確かめている。**安くて確実。**

**ChatGPT版の査読から自分に返ってきたもの（`.f` ラベルの潰れ）**
V72で13.7px×131px、V73で0px×37.5pxとして指摘した欠陥を、自分の版で測ったら
**もっと悪い形であった**（768pxで「どちらで計算するか」が **0px×168.8px**、
「どちらで入れるか」が1.7px×150px、「住宅の種類」が11px×93.8px。
1440pxでも「住宅の種類」0px。7ラベルが40px未満・最大38ラベルが高さ45px超）。

★**他ツールの査読で見つけた欠陥を自分に当てる、が5回目。**
  今回は「相手に勧めて相手が採用した修正」をそのまま自分に当てる形になった。
  `min-width` だけの版（`flex:0 0 auto` は付けない）で 7件→0件・行のはみ出し0件を確認済み。
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


# ---- P1-1: 確認の指紋 ----
sub('''    kokuhoMunicipalityConfirmed:false,''',
    '''    kokuhoMunicipalityConfirmed:false,
    /* ★確認したときの国保の値の指紋。現在値と一致するときだけ「確認済み」とみなす。
       v23はチェックボックス1つだけだったため、**確認後に料率を99%に変えても
       確認済みのままで警告が消えていた**（v24 P1-1）。 */
    kokuhoConfirmedFingerprint:"",''',
    "確認の指紋を params に追加")

# ---- 指紋を作る関数と判定 ----
sub('''function paramConfirmed(P, path){''',
    '''/** 国保の値の指紋。ここに挙げた項目のどれかが変われば、確認は失効する。 */
const KOKUHO_FINGERPRINT_KEYS = [
  "kokuhoBasic",
  "kokuhoMedRate","kokuhoMedPer","kokuhoMedCap","kokuhoMedFlat",
  "kokuhoSupRate","kokuhoSupPer","kokuhoSupCap","kokuhoSupFlat",
  "kokuhoCareRate","kokuhoCarePer","kokuhoCareCap","kokuhoCareFlat",
  "kokuhoKodomoRate","kokuhoKodomoPer","kokuhoKodomoCap","kokuhoKodomoFlat",
  "kokuhoKodomoFromAge","kokuhoPreschoolCut",
  "kokuhoReduceOn","kokuhoReduceBase","kokuhoReduce5Add","kokuhoReduce2Add",
  "kokuhoReduceWageAdd","kokuhoPension65Deduct",
];
function kokuhoFingerprint(P){
  const T = (P && P.tax) || {};
  return KOKUHO_FINGERPRINT_KEYS.map(k => String(T[k])).join("|");
}
/** 利用者が「自分の自治体・年度の値だ」と確認済みか。
 *  ★チェックが入っているだけでは足りない。**確認した時点の値のままか**も見る。 */
function kokuhoConfirmed(P){
  const T = (P && P.tax) || {};
  if(!T.kokuhoMunicipalityConfirmed) return false;
  return T.kokuhoConfirmedFingerprint === kokuhoFingerprint(P);
}
function paramConfirmed(P, path){''',
    "指紋の関数を追加")

# ---- 警告の判定を指紋つきに ----
sub('''  if(!P.tax.kokuhoMunicipalityConfirmed
     && (workTypeOf(P, "h") === "self"
         || (P.family.hasSpouse && workTypeOf(P, "w") === "self")))''',
    '''  if(!kokuhoConfirmed(P)
     && (workTypeOf(P, "h") === "self"
         || (P.family.hasSpouse && workTypeOf(P, "w") === "self")))''',
    "警告の判定に指紋を使う")

# ---- チェックを入れたら指紋を記録する ----
sub("""function onChk(path, v){""",
    '''/** 「自治体・年度を確認した」を切り替える。**入れた時点の値を指紋として残す。** */
function setKokuhoConfirmed(on){
  PARAMS.tax.kokuhoMunicipalityConfirmed = !!on;
  PARAMS.tax.kokuhoConfirmedFingerprint = on ? kokuhoFingerprint(PARAMS) : "";
  markEntered("tax.kokuhoMunicipalityConfirmed");
  recalc();
}
function onChk(path, v){''',
    "setKokuhoConfirmed を追加")

sub('''          + chkField("お住まいの自治体・年度の料率を確認した",
                     "tax.kokuhoMunicipalityConfirmed",
                     "ここにチェックを入れるまで、結果に「概算です」と表示します")''',
    '''          + `<label class="rowitem" style="display:flex; align-items:flex-start; gap:7px">
              <input type="checkbox" ${kokuhoConfirmed(PARAMS) ? "checked" : ""}
                onchange="setKokuhoConfirmed(this.checked)"
                aria-label="お住まいの自治体・年度の料率を確認した">
              <span><b>お住まいの自治体・年度の料率を確認した</b>
                <span class="hint">ここにチェックを入れるまで、結果に「概算です」と表示します。
                ${PARAMS.tax.kokuhoMunicipalityConfirmed && !kokuhoConfirmed(PARAMS)
                  ? `<br><b style="color:var(--bad)">確認したあとに値が変わったため、`
                    + `確認は外れています。</b>もう一度確かめて入れ直してください。` : ""}
                </span></span></label>`''',
    "確認チェックを指紋つきに")

# ---- P2-1: 保存後の書き戻し確認 ----
sub('''function commitPlans(nextPlans){
  /* ★保存の直前に1回だけ検査する。ここを通らない保存経路を作らない。 */
  const bad = badNumbersIn(nextPlans, "plans").concat(badLoansIn(nextPlans));''',
    '''function commitPlans(nextPlans){
  /* ★保存の直前に1回だけ検査する。ここを通らない保存経路を作らない。 */
  const bad = nonFiniteIn(nextPlans, "plans")
    .concat(badNumbersIn(nextPlans, "plans")).concat(badLoansIn(nextPlans));''',
    "commitPlans の検査に nonFiniteIn を足す")

sub('''  try{
    localStorage.setItem(STORE.plans, JSON.stringify(nextPlans));
    PLANS = nextPlans;
    return true;
  }catch(e){
    noticeStoreFailed(e);
    return false;   // ★PLANS は触らない（元の一覧のまま）
  }
}''',
    '''  try{
    const payload = JSON.stringify(nextPlans);
    localStorage.setItem(STORE.plans, payload);
    /* ★書いたあとに読み戻して一致を確かめる（ChatGPT版 `v61StorePlans` から取り込み）。
         例外が出なければ成功とみなすと、**静かに切り詰められた・別の内容が書かれた**
         場合を捕まえられない。実測で「メモリ1件・保存 `[]`・成功表示」になった。 */
    if(localStorage.getItem(STORE.plans) !== payload)
      throw new Error("保存したあとの読み戻しで内容が一致しませんでした");
    PLANS = nextPlans;
    return true;
  }catch(e){
    noticeStoreFailed(e);
    return false;   // ★PLANS は触らない（元の一覧のまま）
  }
}''',
    "保存後の書き戻し確認")

if ng:
    print("NG:", " / ".join(ng))
    sys.exit(1)
P.write_text(t, encoding="utf-8")
print("OK v24 patch D（確認の指紋・書き戻し確認）")
