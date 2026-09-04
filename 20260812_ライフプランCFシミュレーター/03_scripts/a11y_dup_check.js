/* 操作要素の名前の質を、実ブラウザで測る（全タブ・全折りたたみ）。
 *
 * **なぜ作ったか（2026-08-27）**
 * ChatGPT版V66を査読して「名称なし0件は『名前がある』ことしか測っていない」と
 * 指摘した。**同じ物差しを自分に当てたら、こちらにも同名が14個あった。**
 * 収入表と生活費表がどちらも「あなたの年齢別の…」、子ども2人の進路チェックが同名、
 * 確定拠出年金とNISAの終了年齢がどちらも「同（終了）」。
 * **読み上げでは、どちらの欄にいるのか分からない。**
 *
 * **静的検査（check_a11y_names.py）では見つからない**
 * 同名かどうかは「描画した結果」でしか分からない。
 * 段階名を子どもの数だけ繰り返す作りは、ソース上は1か所にしか現れない。
 *
 * **測るもの（3つ）**
 *   1. 名前なし        … 名前が無い（従来からの指標）
 *   2. 同名            … 同じ画面に同じ名前が2つ以上ある
 *   3. 型名の漏れ      … 名前が number / text / select-one などで終わる
 *                         （描画後に推測して名前を付けると出る。V66で15件あった）
 *
 * 使い方：
 *   1. preview_start（name: "ライフプランCF"）で対象のHTMLを開く
 *   2. このファイルの中身を javascript_tool でそのまま実行する
 *   3. 世帯の作り込みは呼び出し側で行う（子ども2人・パートナーあり・住宅ONなど、
 *      欄がいちばん多くなる状態にしてから測ること）
 *
 * ★負試験：どれか1つの aria-label を隣とわざと同じにして、同名が1件出ることを
 *   確かめてから信用すること。「0件でした」だけでは検査が生きている証拠にならない。
 */
(function () {
  function nameOf(x) {
    return String(
      x.getAttribute('aria-label')
      || (x.id && (document.querySelector('label[for="' + CSS.escape(x.id) + '"]') || {}).textContent)
      || (x.closest('label') || {}).textContent
      || ''
    ).trim();
  }

  function scan() {
    /* 折りたたみの中も対象にする。開かないと数え落とす。 */
    [].slice.call(document.querySelectorAll('details')).forEach(function (d) { d.open = true; });
    var all = [].slice.call(document.querySelectorAll('input,select,textarea'))
      .filter(function (x) { return x.offsetParent !== null && x.type !== 'hidden'; });
    var by = {};
    all.forEach(function (x) { var n = nameOf(x); (by[n] = by[n] || []).push(x); });

    var dup = [];
    Object.keys(by).forEach(function (n) {
      if (n && by[n].length > 1) {
        dup.push({
          名前: n,
          件数: by[n].length,
          /* どこで衝突しているかが分からないと直せないので、イベント属性を添える */
          個々: by[n].map(function (x) {
            return (x.getAttribute('oninput') || x.getAttribute('onchange') || '').slice(0, 60);
          })
        });
      }
    });

    var names = all.map(nameOf);
    return {
      総数: all.length,
      名前なし: names.filter(function (n) { return !n; }).length,
      型名漏れ: names.filter(function (n) {
        return /(number|text|checkbox|select-one|range|入力項目)$/i.test(n);
      }).length,
      同名: dup
    };
  }

  var out = {};
  var bad = 0;
  /* TABS は [[id, 表示名], …]。タブを持たない版でも動くようにしておく。 */
  var list = (typeof TABS !== 'undefined' && Array.isArray(TABS))
    ? TABS.map(function (p) { return p[0]; }) : [null];

  list.forEach(function (id) {
    try { if (id) setTab(id); } catch (e) { out[id] = '切替に失敗: ' + e.message; bad++; return; }
    var r = scan();
    out[id || '(現在の画面)'] = r;
    bad += r.名前なし + r.型名漏れ + r.同名.reduce(function (a, d) { return a + d.件数; }, 0);
  });

  out.__合計の問題件数 = bad;
  out.__判定 = bad === 0 ? 'OK  名前なし・同名・型名漏れ すべて0件'
                          : 'NG  ' + bad + '件（下の各タブを参照）';
  return JSON.stringify(out);
})()
