# -*- coding: utf-8 -*-
r"""v24 patch B：P0-3（巨大数が null として成功保存される）。

**何が起きていたか**
利用者が「預金・現金」に `1e307` と入れる。`onMan()` が ×10,000 して `Infinity`。
`withPlanIn()` が `clone()`（JSON経由）するので **`Infinity` は `null` に変わる**。
そのあと `commitPlans()` の `badNumbersIn()` が走るが、**`null` は許容している**ので通る。
結果：「プラン「巨大数入力」を保存しました」と出て、預金は `null`。

    保存前 PARAMS.econ.deposit = Infinity
    保存後 PLANS[0].params.econ.deposit = null   ／ localStorage も null
    成功メッセージあり・エラー通知なし

★v23で `commitPlans` に検査を入れたとき、**`Infinity` を直接渡す負試験だけ**を書いた。
  それは拒否できる。**実際の利用者経路（input → onMan → withPlanIn → commitPlans）を
  通していなかった。** v22のP0-1（helperだけ直して呼出側が残る）と同じ形の見落ち。
  **負試験は実際の `<input>` から保存まで通すこと。**

**直し方（3段）**
  1. `onNum` / `onMan` で、**PARAMSへ入れる前に**有限性を確かめる。だめなら値を変えず画面で断る。
  2. `withPlanIn` が **複製する前に**元データを検査する（JSONで null になる前）。
  3. `commitPlans` の検査は残す（別経路の保険）。
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


# ---- 1. 非有限値をJSON複製の前に見つける道具 ----
sub('''function badNumbersIn(obj, path, out){''',
    '''/** 非有限な数（`NaN`・`Infinity`・`-Infinity`）が混ざっていないかを、
 *  **JSONを通す前の生データ**に対して探す。
 *
 *  ★`JSON.stringify` は `Infinity` を `null` にする。だから `clone()` のあとで
 *    探しても見つからない（`badNumbersIn` は `null` を許容する）。
 *    **複製する前に、この関数で止める。** */
function nonFiniteIn(obj, path, out){
  out = out || []; path = path || "";
  if(obj === null || obj === undefined) return out;
  if(typeof obj === "number"){
    if(!Number.isFinite(obj)) out.push(path + " = " + String(obj));
    return out;
  }
  if(Array.isArray(obj)){
    obj.forEach((v, i) => nonFiniteIn(v, path + "[" + i + "]", out));
    return out;
  }
  if(typeof obj === "object"){
    Object.keys(obj).forEach(k => nonFiniteIn(obj[k], path ? path + "." + k : k, out));
  }
  return out;
}
function badNumbersIn(obj, path, out){''',
    "nonFiniteIn を追加")

# ---- 2. withPlanIn は複製前に検査する ----
sub('''function withPlanIn(list, params, name){
  const nm = name || params.meta.planName;
  const next = (list || []).slice();
  const i = next.findIndex(x => x.name === nm);''',
    '''function withPlanIn(list, params, name){
  const nm = name || params.meta.planName;
  /* ★複製（JSON経由）の**前**に検査する。あとでは `Infinity` が `null` になって見えない。
     実測：預金に 1e307 を入れると `Infinity` → 複製で `null` → 「保存しました」（v23のP0-3）。 */
  const bad = nonFiniteIn(params, "params");
  if(bad.length){
    noticeBadInput(bad, "このプランは保存していません");
    return (list || []).slice();     // 何も足さずに返す
  }
  const next = (list || []).slice();
  const i = next.findIndex(x => x.name === nm);''',
    "withPlanIn の事前検査")

# ---- 3. 画面に残る知らせ（共通） ----
sub('''/** 借入額が負になっていないか（負の借入は「返済がマイナス＝収入」になってしまう）。 */''',
    '''/** 数値として扱えない入力があったことを、画面に残る形で伝える。 */
function noticeBadInput(paths, tail){
  pushNotice("badnum", "bad",
    `<b>数値として扱えない値が入っています。${esc(tail || "")}。</b>`
    + `<span class="hint">（${esc(paths.slice(0,3).join(" / "))}`
    + `${paths.length > 3 ? ` ほか ${paths.length-3}件` : ""}）<br>`
    + `桁が大きすぎる値（例：1e307）や、計算できない値が入ると起きます。`
    + `その欄を確かめて入れ直してください。</span>`);
}

/** 借入額が負になっていないか（負の借入は「返済がマイナス＝収入」になってしまう）。 */''',
    "noticeBadInput を追加")

# ---- 4. onNum / onMan で入力時に止める ----
sub('''function onNum(path, v){
  set(PARAMS, path, parseFloat(v)||0);''',
    '''/** 入力欄の値を数として読む。**扱えない値なら null を返す**（呼び出し側が拒否する）。
 *  ★`parseFloat("1e307") * 10000` は `Infinity` になる。
 *    `PARAMS` に入れてしまうと、あとの複製で `null` に化けて静かに保存される（P0-3）。
 *    **PARAMSへ入れる前に止める。** */
function readFinite(v, scale){
  const n = parseFloat(v);
  if(!isFinite(n)) return (v === "" || v === null || v === undefined) ? 0 : null;
  const x = n * (scale || 1);
  return Number.isFinite(x) ? x : null;
}
function onNum(path, v){
  const x = readFinite(v, 1);
  if(x === null){ noticeBadInput([path], "その欄は変更していません"); render(); return; }
  set(PARAMS, path, x);''',
    "onNum で非有限を拒否")

if ng:
    print("NG:", " / ".join(ng))
    sys.exit(1)
P.write_text(t, encoding="utf-8")
print("OK v24 patch B（非有限値を複製前に止める）")
