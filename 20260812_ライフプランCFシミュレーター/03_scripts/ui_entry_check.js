/* 「画面の操作だけで未入力から抜けられるか」を実ブラウザで測る。
 *
 * **なぜ作ったか（2026-08-27）**
 * v14で、**パラメータ画面だけを使う利用者は未入力状態から永久に抜けられなかった。**
 *   ・生活費は `onRowMan('living.table',0,'amount')` でしか入れられないのに、
 *     `onRow`/`onRowMan` が `markEntered` を呼んでいなかった
 *   ・`income.hBase` の欄がセットアップ画面にしか無かった
 * 値は入るのに「入れたこと」が記録されず、ヘッダーはずっと
 * 「入力を始めてください」のままだった。
 *
 * **既存の `check_input_flow.py` はこれを通り抜けた。**
 * あちらは `PARAMS` に**プログラムから値を代入**して確かめる。
 * つまり「計算が値を受け取るか」は見ていたが、
 * **「画面の操作で値と記録が入るか」は一度も見ていなかった。**
 *
 * ★入口を作ったら、その入口を**画面の操作で**通る検査を作ること。
 *   プログラムから値を入れる検査は、UIの配線が切れていても通る。
 *
 * 測るもの
 *   1. 未入力から始まるか
 *   2. パラメータ画面の操作だけで、必須3項目の不足が0になるか
 *   3. そのとき入れた値が年次計算に届くか（給与・生活費）
 *   4. 収入表を直接編集したとき、ベース年収が追随するか（表示と計算の食い違い）
 *   5. 負試験：追随を止めたら食い違いが検出されるか
 *
 * 使い方：preview_start でHTMLを開き、この中身を javascript_tool で実行する。
 */
(function () {
  const log = [];
  const ok = (name, pass, detail) => log.push({ name, pass: !!pass, detail: detail || "" });

  /* 実際の入力と同じ経路を通す（value を代入して input/change を投げる）。 */
  function fire(el, v) {
    if (!el) return false;
    const proto = el.tagName === "SELECT" ? HTMLSelectElement.prototype : HTMLInputElement.prototype;
    Object.getOwnPropertyDescriptor(proto, "value").set.call(el, String(v));
    el.dispatchEvent(new Event("input", { bubbles: true }));
    el.dispatchEvent(new Event("change", { bubbles: true }));
    return true;
  }
  /* 折りたたみの中も対象。開かないと欄が見つからない。 */
  function open() {
    [].slice.call(document.querySelectorAll("details")).forEach(d => { d.open = true; });
  }
  /* イベント属性で欄を特定する（ラベル文言は改訂で変わるため当てにしない）。 */
  function byOn(pat) {
    return [].slice.call(document.querySelectorAll("input,select"))
      .filter(x => x.offsetParent !== null)
      .filter(x => ((x.getAttribute("oninput") || "") + (x.getAttribute("onchange") || ""))
        .indexOf(pat) >= 0)[0];
  }
  const go = () => { setTab("params"); open(); };

  // ---- 1. 未入力から始まる
  PARAMS = blankParams(); PARAMS.meta.blank = true; recalc(); go();
  ok("未入力から始まる", isBlank(PARAMS) && blankMissing(PARAMS).length === 3,
    "不足=" + blankMissing(PARAMS).join("・"));

  // ---- 2. パラメータ画面の操作だけで必須3項目が埋まる
  const hasAge = fire(byOn("'family.ageH'"), 40); go();
  const hasInc = fire(byOn("'income.hBase'"), 600); go();
  const hasLiv = fire(byOn("onRowMan('living.table',0,'amount'"), 300); go();
  ok("年齢の欄がパラメータ画面にある", hasAge);
  ok("年収の欄がパラメータ画面にある", hasInc,
    hasInc ? "" : "★セットアップ画面にしか無いと、ここだけを使う人は抜けられない");
  ok("生活費の欄がパラメータ画面にある", hasLiv);
  ok("画面の操作だけで未入力を抜けられる",
    !isBlank(PARAMS) && blankMissing(PARAMS).length === 0,
    "不足=" + (blankMissing(PARAMS).join("・") || "なし"));

  // ---- 3. 入れた値が年次計算に届く
  const r0 = simulate(PARAMS).rows[0];
  ok("年収600万円が初年度給与に届く", Math.round(r0.salaryH) === 6000000,
    "salaryH=" + Math.round(r0.salaryH));
  ok("生活費300万円が年次計算に届く", Math.round(r0.living) === 3000000,
    "living=" + Math.round(r0.living));

  // ---- 4. 収入表を直接編集したら、ベース年収が追随する
  fire(byOn("onRowMan('income.hTable',0,'amount'"), 300); go();
  const base = PARAMS.income.hBase, row = PARAMS.income.hTable[0].amount;
  ok("収入表の編集にベース年収が追随する", Math.abs(base - row) < 1,
    "hBase=" + base + " / 表=" + row);
  ok("計算も表の値になる", Math.round(simulate(PARAMS).rows[0].salaryH) === 3000000,
    "salaryH=" + Math.round(simulate(PARAMS).rows[0].salaryH));

  // ---- 5. 負試験：わざと食い違わせたら、検算が拾うか
  PARAMS.income.hBase = 6000000;   // 表は300万のまま
  const found = (validateParams(PARAMS) || [])
    .filter(x => /食い違/.test(x.msg || "")).length;
  ok("負試験：食い違いを検出する", found >= 1, "検出=" + found + "件");
  PARAMS.income.hBase = row;       // 元に戻す

  const ng = log.filter(x => !x.pass);
  return JSON.stringify({
    版: (typeof VERSION !== "undefined" ? VERSION.tag : "?"),
    件数: log.length, NG: ng.length,
    判定: ng.length === 0 ? "OK  画面の操作だけで入力を始められます" : "NG  下を参照",
    結果: log,
  });
})()
