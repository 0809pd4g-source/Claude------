# -*- coding: utf-8 -*-
r"""v22 patch D：P2-1（教育費の年次表を「1年ずつ縦に見る」表示にする）。

**v20〜v21でやっていたこと**
折りたたみ＋「上の段階別の表を先に見てください」という誘導だけ。
外部レビューの実測では、開くと**表幅1,076.8px／枠349px／高さ1,428.8px**。
ページ自体の横崩れは0だが、**表は約3.1画面分**。
「軽減策であって本解決ではない」と自分でも書いていた。

**本解決の形は既にこのファイルの中にある。**
キャッシュフロー表は同じ問題（67列・3,615px）を `cfOneYearHtml()` で解いている。
年を「列」から「1画面」に変え、前年／翌年で移動する。
**同じ型を教育費にも当てる。**（新しい仕組みは作らない＝二重管理を避ける）

★行の定義を表と共有すること。表とカードで別々に項目を並べると、
  片方に足したときにもう片方が古くなる（維持費・保険で過去にやっている）。
  ここでは `eduRowDefs()` を1つ作り、横長の表とも1年表示とも共有する。
"""
import io
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


# ---- 1. 状態と操作（CF表と同じ形にそろえる） ----
sub('''function cfSetYear(y){ CF_YEAR = y; render(); }''',
    '''function cfSetYear(y){ CF_YEAR = y; render(); }
/* ---- 教育費の年次表も、狭い画面では1年ずつ縦に見る（v22 P2-1）。
       CF表と同じ形にそろえる（新しい仕組みを作らない）。 ---- */
let EDU_ONEYEAR = null;     // null＝画面幅から自動で決める
let EDU_YEAR = null;        // 見ている年（null＝いちばん最初の年）
function eduOneYear(){
  if(EDU_ONEYEAR !== null) return EDU_ONEYEAR;
  return isNarrowScreen();
}
function toggleEduOneYear(){
  EDU_ONEYEAR = !eduOneYear();
  render();
}
function eduSetYear(y){ EDU_YEAR = y; render(); }
function eduStepYear(d){
  const rows = eduYearRows();
  if(!rows.length) return;
  const i = Math.max(0, Math.min(rows.length - 1,
    rows.findIndex(r => r.year === (EDU_YEAR || rows[0].year)) + d));
  EDU_YEAR = rows[i].year;
  render();
}
/** 教育費が出る年だけを取り出す（表と1年表示で同じ集合を使う）。 */
function eduYearRows(){
  if(!SIM || !SIM.rows) return [];
  return SIM.rows.filter(r => r.eduTotal > 0 || r.childOther > 0);
}''',
    "教育費の1年表示の状態と操作")

# ---- 2. 行の定義を1つにまとめ、表と1年表示で共有する ----
sub('''  const rows = S.rows.filter(r => r.eduTotal > 0 || r.childOther > 0);
  const kidNames = P.family.children.map((c,i) => ["第1子","第2子","第3子","第4子"][i] || c.name);
  let h = `<table class="tbl"><thead><tr><th class="lbl">項目</th>`;
  rows.forEach(r => h += `<th>${r.year}</th>`);
  h += `<th>合計</th></tr></thead><tbody>`;
  h += `<tr class="grp"><td class="lbl">あなたの年齢</td>`
     + rows.map(r=>`<td>${r.ageH}</td>`).join("") + `<td></td></tr>`;
  kidNames.forEach((nm,i) => {
    h += `<tr><td class="lbl">${nm}（年齢）</td>`
       + rows.map(r=>`<td class="tr">${r.childAges[i]>=0?r.childAges[i]:""}</td>`).join("") + `<td></td></tr>`;
    const tot = S.rows.reduce((s,r)=>s+(r.eduByChild[i]||0), 0);
    h += `<tr><td class="lbl">${nm}（教育費）</td>`
       + rows.map(r=>`<td>${r.eduByChild[i]?fmtMan(r.eduByChild[i]):""}</td>`).join("")
       + `<td class="grp">${fmtMan(tot)}</td></tr>`;
  });
  const totOther = S.rows.reduce((s,r)=>s+r.childOther, 0);
  h += `<tr><td class="lbl">その他の子ども費用</td>`
     + rows.map(r=>`<td>${r.childOther?fmtMan(r.childOther):""}</td>`).join("")
     + `<td class="grp">${fmtMan(totOther)}</td></tr>`;
  const totAll = S.rows.reduce((s,r)=>s+r.childTotal, 0);
  h += `<tr class="grp"><td class="lbl">子ども関連費 合計</td>`
     + rows.map(r=>`<td>${r.childTotal?fmtMan(r.childTotal):""}</td>`).join("")
     + `<td>${fmtMan(totAll)}</td></tr>`;
  h += `<tr><td class="lbl">収入に占める割合</td>`
     + rows.map(r=>`<td class="tr">${r.incomeTotal>0?(r.childTotal/r.incomeTotal*100).toFixed(1)+"%":""}</td>`).join("")
     + `<td></td></tr>`;
  h += `</tbody></table>`;
  document.getElementById("eduTable").innerHTML = h;''',
    '''  const rows = S.rows.filter(r => r.eduTotal > 0 || r.childOther > 0);
  const R = eduRowDefs(P, S);
  /* ★横長の表と1年ずつの表示で、項目の並びを同じ定義（R）から作る。
       別々に並べると、片方に行を足したときにもう片方が古くなる。 */
  const oneBtn = `<div style="margin:0 0 9px">
      <button class="btn sec" onclick="toggleEduOneYear()">${
        eduOneYear() ? "表で見る（横に広い一覧）" : "1年ずつ見る（スマホ向け）"}</button>
      <span class="hint" style="margin-left:7px">${
        eduOneYear()
          ? "年ごとに縦に並べています。横に広い一覧に戻せます。"
          : "年を横に並べています。狭い画面では1年ずつ縦に見るほうが読めます。"}</span>
    </div>`;
  if(eduOneYear()){
    document.getElementById("eduTable").innerHTML = oneBtn + eduOneYearHtml(R, rows);
    document.getElementById("eduRates").innerHTML = courseRatesBlock();
    return;
  }
  let h = `<table class="tbl"><thead><tr><th class="lbl">項目</th>`;
  rows.forEach(r => h += `<th>${r.year}</th>`);
  h += `<th>合計</th></tr></thead><tbody>`;
  R.forEach(row => {
    h += `<tr class="${row.grp ? "grp" : ""}"><td class="lbl">${row.lbl}</td>`
       + rows.map(r => `<td class="${row.plain ? "tr" : ""}">${row.cell(r)}</td>`).join("")
       + `<td class="${row.grp ? "" : "grp"}">${row.total == null ? "" : fmtMan(row.total)}</td></tr>`;
  });
  h += `</tbody></table>`;
  document.getElementById("eduTable").innerHTML = oneBtn + h;''',
    "教育費の表を行定義から作る")

# ---- 3. 行定義と1年表示の本体を足す ----
sub('''function onStage(k, key, v){ PARAMS.edu.stages[k][key] = parseFloat(v)||0; recalc(); }''',
    '''/** 教育費の年次表の行の定義。**横長の表と1年表示で共有する。**
 *  `cell(r)` はその年のセル、`total` は右端の合計（無い行は null）。 */
function eduRowDefs(P, S){
  const kidNames = P.family.children.map((c,i) => ["第1子","第2子","第3子","第4子"][i] || c.name);
  const R = [{lbl:"あなたの年齢", grp:true, plain:true, total:null,
              cell:r => r.ageH}];
  kidNames.forEach((nm,i) => {
    R.push({lbl:`${nm}（年齢）`, plain:true, total:null,
            cell:r => (r.childAges[i] >= 0 ? r.childAges[i] : "")});
    R.push({lbl:`${nm}（教育費）`,
            total:S.rows.reduce((s,r) => s + (r.eduByChild[i] || 0), 0),
            cell:r => (r.eduByChild[i] ? fmtMan(r.eduByChild[i]) : "")});
  });
  R.push({lbl:"その他の子ども費用",
          total:S.rows.reduce((s,r) => s + r.childOther, 0),
          cell:r => (r.childOther ? fmtMan(r.childOther) : "")});
  R.push({lbl:"子ども関連費 合計", grp:true,
          total:S.rows.reduce((s,r) => s + r.childTotal, 0),
          cell:r => (r.childTotal ? fmtMan(r.childTotal) : "")});
  R.push({lbl:"収入に占める割合", plain:true, total:null,
          cell:r => (r.incomeTotal > 0
            ? (r.childTotal / r.incomeTotal * 100).toFixed(1) + "%" : "")});
  return R;
}

/** 教育費を1年ずつ縦に見る（狭い画面向け）。
 *  ★v21までは折りたたんで「段階別の表を見てください」と誘導するだけだった。
 *    開くと390px幅で表1,076.8px＝約3.1画面分で、年次で追う人には解決していない。
 *    CF表と同じ形（`cfOneYearHtml`）にそろえる。 */
function eduOneYearHtml(R, rows){
  if(!rows.length) return `<div class="hint">教育費が出る年がありません。</div>`;
  const cur = rows.find(r => r.year === EDU_YEAR) || rows[0];
  const i = rows.indexOf(cur);
  const opt = rows.map(r =>
    `<option value="${r.year}"${r.year === cur.year ? " selected" : ""}>`
    + `${r.year}年（あなた${r.ageH}歳）</option>`).join("");
  let h = `<div class="f" style="margin-bottom:10px; gap:6px">
      <button class="btn sec" onclick="eduStepYear(-1)"${i <= 0 ? " disabled" : ""}
        style="min-width:56px">← 前年</button>
      <select onchange="eduSetYear(parseInt(this.value,10))" aria-label="教育費を表示する年"
        style="flex:1 1 auto; min-width:0; font-size:16px; padding:7px">${opt}</select>
      <button class="btn sec" onclick="eduStepYear(1)"${i >= rows.length-1 ? " disabled" : ""}
        style="min-width:56px">翌年 →</button>
    </div>
    <div class="hint" style="margin-bottom:9px">
      <b>${cur.year}年・あなた${cur.ageH}歳</b>の内訳です。
      年を選ぶか、前年／翌年で移動できます。
      右端の「生涯合計」は全期間の合計です。
    </div>
    <table class="tbl"><tbody>`;
  R.forEach(row => {
    const v = row.cell(cur);
    if(v === "" && row.total == null) return;      // その年に関係ない行は出さない
    h += `<tr class="${row.grp ? "grp" : ""}">
      <td class="lbl" style="white-space:normal">${row.lbl}</td>
      <td style="text-align:right; white-space:nowrap">${v === "" ? "—" : v}</td>
      <td style="text-align:right; white-space:nowrap" class="hint">${
        row.total == null ? "" : "生涯 " + fmtMan(row.total) + "万"}</td>
    </tr>`;
  });
  h += `</tbody></table>`;
  return h;
}
function onStage(k, key, v){ PARAMS.edu.stages[k][key] = parseFloat(v)||0; recalc(); }''',
    "eduRowDefs と eduOneYearHtml を追加")

# ---- 4. 折りたたみの説明を、1年表示があることに合わせて直す ----
sub('''    <h3>子ども別の年次教育費</h3>
    <!-- ★狭い画面では、この表は22列・幅約1,140px（約2.9画面分）になる。
         年が「列」なので列を減らしても解決しない（CF表と同じ型）。
         上の「段階別の表」は6列で縦積みされ、狭い画面でも読める。
         そちらを先に見てもらい、年次で追いたい人だけ開く形にする。 -->
    <details id="eduTableWrap">
      <summary style="cursor:pointer; font-size:12.5px; color:var(--accent); font-weight:600"
        aria-label="子ども別の年次教育費の表をひらく">年ごとの表を開く（横に長い表です）</summary>
      <div class="hint" style="margin:6px 0 8px">
        <b>画面が狭いときは、上の「段階別」の表のほうが読みやすいです。</b>
        こちらは年を横に並べるため、スマートフォンでは横スクロールが必要です。
      </div>
      <div class="scroll" id="eduTable" data-wide="year"></div>
    </details>''',
    '''    <h3>子ども別の年次教育費</h3>
    <!-- ★v22から、狭い画面では既定で「1年ずつ縦に見る」表示になる
         （CF表と同じ `eduOneYearHtml`）。横に広い一覧にも切り替えられる。
         v21までは折りたたんで「段階別の表を見てください」と誘導するだけで、
         開くと390px幅で表1,076.8px＝約3.1画面分だった。 -->
    <details id="eduTableWrap" open>
      <summary style="cursor:pointer; font-size:12.5px; color:var(--accent); font-weight:600"
        aria-label="子ども別の年次教育費の表を開いたり閉じたりする">年ごとの内訳</summary>
      <div class="scroll" id="eduTable" data-wide="year"></div>
    </details>''',
    "折りたたみの説明を差し替え")

if ng:
    print("NG:", " / ".join(ng))
    sys.exit(1)
P.write_text(t, encoding="utf-8")
print("OK v22 patch D（教育費を1年ずつ縦に見られるようにした）")
