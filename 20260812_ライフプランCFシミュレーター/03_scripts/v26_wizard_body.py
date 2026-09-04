# -*- coding: utf-8 -*-
r"""v26 patch 2：ステップの中身と、入力／確認の区別を画面に出す。

- 収入ステップに **リタイアする年齢**
- 資産ステップに **毎月の積立**
- **長期前提**ステップを新設（物価上昇率・運用利回り）
- 最後に **入力欄のない「診断」ステップ**（ChatGPT版V76の「確認画面」ラベルを取り込み）
- 丸ボタンと見出しに「入力／確認」を出す
"""
import io
import sys
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
ROOT = Path(__file__).resolve().parent.parent
P = ROOT / "02_output" / "20260831_ライフプランCFシミュレーター汎用版_v26.html"
t = P.read_text(encoding="utf-8")
ng = []


def sub(old, new, label, count=1):
    global t
    c = t.count(old)
    if c == count:
        t = t.replace(old, new, count)
    else:
        ng.append(f"{label} ({c}件/期待{count})")


# ---- 収入ステップに「リタイアする年齢」 ----
sub('''  if(i === 2){
    return '<div class="hint" style="margin-bottom:9px">'
      + '<b>いま持っているお金</b>を入れてください。''',
    '''  if(i === 2){
    return '<div class="hint" style="margin-bottom:9px">'
      + '<b>いま持っているお金と、毎月の積立</b>を入れてください。''',
    "資産ステップの導入文")

sub('''      + '<div class="hint">毎月の積立額は「資産形成」のページで入れられます。''',
    '''      /* ★毎月の積立は `READY_STEPS` の必要項目。
           v25まで「資産形成のページで入れられます」と案内するだけで、
           **セットアップでは一度も聞いていなかった**（段階2に進めない・v26で追加）。 */
      + '<h3>毎月の積立</h3>'
      + '<div class="hint" style="margin-bottom:7px">'
      + '<b>いま毎月いくら積み立てているか</b>を入れてください。'
      + '<b>していない場合は0のままで結構です</b>（0も入力として扱います）。</div>'
      + manField("毎月の積立（あなた・NISA）", "saving.nisaMonthlyH")
      + (P.family.hasSpouse
          ? manField("毎月の積立（パートナー・NISA）", "saving.nisaMonthlyW") : "")
      + '<div class="hint">確定拠出年金・持株会の積立は「資産形成」のページで入れられます。''',
    "資産ステップに毎月の積立")

# ---- 長期前提ステップと診断ステップを、心配ごとの前に差し込む ----
sub('''      + 'よく入れる項目の相場の目安も、そこに一覧があります。</div>';
  }
  // 心配ごと''',
    '''      + 'よく入れる項目の相場の目安も、そこに一覧があります。</div>';
  }
  if(i === 5){
    /* ★長期前提は `READY_STEPS` の最終段階の必要項目なのに、
         v25までセットアップで一度も聞いていなかった（段階3に到達できない・v26で追加）。 */
    return '<div class="hint" style="margin-bottom:9px">'
      + '<b>この2つは「当てにいく」ものではありません。</b>'
      + '何十年も先まで当たる数字はないので、'
      + '<b>いくつか変えて幅を見るため</b>に入れます。<br>'
      + '分からなければ、そのまま次へ進んでも構いません'
      + '（既定の値で計算し、あとで「ストレステスト」のページで幅を確かめられます）。</div>'
      + numField("物価上昇率", "econ.inflation", "%/年", 0.1)
      + '<div class="hint">生活費・教育費などが毎年どれだけ上がるかの前提です。'
      + '高くすると将来の支出がふくらみます。</div>'
      + numField("運用利回り", "econ.investRate", "%/年", 0.1)
      + '<div class="hint">運用資産が毎年どれだけふえるかの前提です。'
      + '<b>結果にもっとも強く効くうえ、いちばん当たらない数字</b>なので、'
      + '低めに置いて確かめるほうが安全です。</div>'
      + '<div class="infobox" style="margin-top:10px; font-size:12.5px">'
      + '<b>この2つを入れると「判断の準備が整いました」になります。</b>'
      + 'ただしそれは「入力がそろった」という意味で、'
      + '<b>前提が当たっている保証ではありません。</b></div>';
  }
  if(i === 7){
    /* ★入力欄を持たない「確認」のステップ（ChatGPT版V76から取り込み）。
         V76はガイドの3つ目に「確認画面」とラベルし、上部メニューで見ると書いていた。
         **「入力が終わらないと結果が見られない」という誤解を避けられる。**
         こちらは全ステップが入力欄で、最後のボタンが「結果を見る →」だけだった。 */
    const r = readiness();
    const miss = checkWizardCoverage();
    return '<div class="hint" style="margin-bottom:9px">'
      + '<b>ここは入力欄ではありません。</b>入力はここまでで終わりです。<br>'
      + 'このあとは<b>上のメニュー</b>から結果を見ます。'
      + '数字はいつでも「パラメータ」などのページで直せます。</div>'
      + '<div class="infobox" style="margin-bottom:10px">'
      + '<b>いまの状態：' + esc(r.label) + '</b>'
      + (r.note ? '<br><span class="hint">' + esc(r.note) + '</span>' : "")
      + (r.missing.length
          ? '<br><b style="color:var(--warn)">まだ入れていない項目：'
            + esc(r.missing.join("・")) + '</b>'
            + '<span class="hint">（上の丸いボタンから戻って入れられます）</span>'
          : '')
      + '</div>'
      + '<div class="cards" style="grid-template-columns:repeat(auto-fill,minmax(240px,1fr))">'
      + [["check", "あなたの心配に答える", "選んだ心配ごとに、順番に答えます。まずここから。"],
         ["cf", "キャッシュフロー表", "毎年の収入・支出・残高を1年ずつ見られます。"],
         ["compare", "プラン比較", "条件のちがうプランを並べて見比べます。"]]
        .map(function(x){
          return '<div class="card"><div class="body" style="padding:10px 12px">'
            + '<div style="font-weight:700; font-size:13px; margin-bottom:4px">'
            + esc(x[1]) + '</div>'
            + '<div class="hint" style="line-height:1.8">' + esc(x[2]) + '</div>'
            + '<button class="btn sm" style="margin-top:8px" onclick="endWizard(false); setTab('
            + jsAttr(x[0]) + ')">このページを開く</button>'
            + '</div></div>';
        }).join("")
      + '</div>'
      + (miss.length
          ? '<div class="noticebar bad" style="margin-top:10px"><b>'
            + 'セットアップが聞いていない必須項目があります：'
            + esc(miss.map(function(x){ return x.label; }).join("・"))
            + '</b><span class="hint">（作り手向けの表示です。'
            + 'WIZ_STEPS の covers に足してください。）</span></div>'
          : '');
  }
  // 心配ごと''',
    "長期前提ステップと診断ステップを追加")

# ---- 丸ボタンと見出しに「入力／確認」を出す ----
sub('''    + '<h2>セットアップ　' + (i+1) + '／' + n + '：' + esc(WIZ_STEPS[i].n) + '</h2>'
    + '<div class="body">'
    + '<div class="steppills" style="margin-bottom:10px">'
    + WIZ_STEPS.map(function(s, j){
        return '<button class="steppill' + (j === i ? " on" : "") + '"'
          + ' onclick="wizGo(' + j + ')">' + (j+1) + '. ' + s.t + '</button>';
      }).join("")
    + '</div>' ''' .rstrip(),
    '''    + '<h2>セットアップ　' + (i+1) + '／' + n + '：' + esc(WIZ_STEPS[i].n)
    + ' <span class="tag">' + (WIZ_STEPS[i].kind === "view" ? "確認" : "入力")
    + '</span></h2>'
    + '<div class="body">'
    /* ★入力する画面と、見るだけの画面を分けて見せる（ChatGPT版V76から取り込み）。
         どこまでが入力で、どこから結果を見るのかが、番号だけでは分からなかった。 */
    + '<div class="steppills" style="margin-bottom:6px">'
    + WIZ_STEPS.map(function(s, j){
        return '<button class="steppill' + (j === i ? " on" : "") + '"'
          + ' onclick="wizGo(' + j + ')"'
          + ' aria-label="' + esc((j+1) + '. ' + s.t
              + (s.kind === "view" ? "（確認画面）" : "（入力）")) + '">'
          + (j+1) + '. ' + s.t
          + (s.kind === "view" ? ' <span style="opacity:.75">（確認）</span>' : '')
          + '</button>';
      }).join("")
    + '</div>'
    + '<div class="hint" style="margin-bottom:10px">'
    + '<b>1〜' + (n-1) + 'が入力、' + n + 'が確認画面です。</b>'
    + '入力は途中でやめても構いません（入れた分だけで概算が出ます）。</div>' ''' .rstrip(),
    "ステップの見出しと丸ボタンに入力／確認を出す")

# ---- 最後のボタンの文言を、確認ステップに合わせる ----
sub('''    + (i < n - 1
        ? '<button class="btn" onclick="wizGo(' + (i+1) + ')">'
          + esc(WIZ_STEPS[i+1].t) + ' →</button>'
        : '<button class="btn" onclick="endWizard(true)">結果を見る →</button>')''',
    '''    + (i < n - 1
        ? '<button class="btn" onclick="wizGo(' + (i+1) + ')">'
          + esc(WIZ_STEPS[i+1].t)
          + (WIZ_STEPS[i+1].kind === "view" ? "（確認）" : "") + ' →</button>'
        : '<button class="btn" onclick="endWizard(true)">セットアップを終える →</button>')''',
    "次へボタンの文言")

if ng:
    print("NG:", " / ".join(ng))
    sys.exit(1)
P.write_text(t, encoding="utf-8")
print("OK v26 patch 2（ステップの中身と入力／確認の区別）")
