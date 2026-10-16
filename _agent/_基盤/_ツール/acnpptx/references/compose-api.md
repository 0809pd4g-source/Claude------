# compose-api.md — 部品（module）ごとのデータの形

`outline.json` の `panes[]` 要素に、`module` と以下のキーを書く。すべての部品で `header`（ペイン見出し）と `status` が使える。
文字列中の `**語**` は強調（太字＋アクセント色）。容量の目安は `grammar/modules.json` の `capacity`（grammar_check が検査）。

| module | キー | 例・注意 |
|---|---|---|
| M-BULLETS | `items`: [str \| {text, sub:[str]}] | 3〜6 項目、1 項目 40 字。箇条だけの本文は CB-34（避ける） |
| M-CHECKLIST | `items`: [str] | ✓ 付きの縦並び |
| M-NUMLIST | `items`: [{title, text, number?}] | 丸番号＋見出し＋説明 |
| M-ROWHEAD | `rows`: [{head, text \| items:[str]}], `head_w`? | 左に淡色の見出しセル（CB-17）。3〜7 行 |
| M-TABLE | `columns`: [str], `rows`: [[str]], `col_widths`?: [比], `highlight_col`?: int, `first_col_head`?: bool | 見出し行は濃色、交互色なし。5 列×8 行・セル 20 字まで |
| M-MATRIX-SYM | M-TABLE と同じ＋`legend`: "◎ 最適 ○ 対応 △ 限定的" | セルに ◎○△× |
| M-CALLOUT | `text`, `style`: "box" \| "key", `title`?, `items`?, `sub`? | key = 大きなキーメッセージ |
| M-QUOTE | `text`, `by` | 引用・発言 |
| M-CARD | `title`, `items` \| `text`, `icon`? | G-2x2 / G-GRID / G-N3 の 1 区画 |
| M-CARDSTACK | `cards`: [{title, text \| items, icon?}] | 左帯付きカードの縦積み 2〜4 段 |
| M-HEADCOL | `items` \| `text`, `icon`? | 見出しは `header` で付ける。N 列の 1 列 |
| M-BADGECOL | `badge`（番号・短語） \| `icon`, `title`, `text` \| `items` | 丸バッジ（またはアイコン）＋見出し＋説明。縦中央揃え |
| M-KPI-TILE | `tiles`: [{value, unit?, label, detail?}] | 横並びの数字タイル。出所 `source` か `illustrative` |
| M-KPI-STACK | 同上 | 縦積み |
| M-CHEVRON | `steps`: [{label, items? \| text?, highlight?}] | 矢羽根の工程帯。items/text があれば下に説明ボックス |
| M-PHASE | `phases`: [{label, items, highlight?}] | フェーズ帯＋各フェーズの実施事項 |
| M-DIAGRAM-FLOW | `nodes`: [{label, text?, highlight?}] | 箱と矢印。6 個以上は 2 段に折り返す |
| M-LAYER | `layers`: [{label, text \| items}] | 上から順に積層 |
| M-GANTT | `periods`: [str], `tasks`: [{label, start, end, highlight?, note?}], `now`?: float | start/end は periods の添字（end を含む）。バー長は期間に比例（CB-18） |
| M-TREE | `root`, `children`: [{label, children: [str \| {label, note?, emph?, children?}]}], `direction`?: "right" \| "down", `note_head`? | 段の数は自由。right（既定）は左→右で、葉の `note` を右端のコメント列に揃える（ドライバーツリー＋示唆）。down は上→下で組織図と同じ結線（イシューツリー） |
| M-CYCLE | `nodes`: [{label, text?, highlight?}], `center`? | 円周上に配置し時計回りの矢印 |
| M-NGOK | `ng`: {title, items}, `ok`: {title, items} | 同じ構造の鏡像（CB-09） |
| M-BEFORE-AFTER | `before`, `after`（NGOK と同形）, `before_label`?, `after_label`? | |
| M-DEFBOX | `term`, `definition`, `items`? | 定義ボックス |
| M-CHART | `chart_type`: column / bar / line / stacked / area / pie / doughnut / waterfall / combo, `title`, `unit`, `categories`, `series`: [{name, values}]（pie・doughnut は `labels`, `values`）, `source` | タイトル・単位必須（CB-06）。doughnut は中央に `center`（既定は合計）と `center_label`。waterfall は `steps`: [{label, value, total?}]（total に value が無ければ累計）と `value_unit`。combo は `series`（棒）＋`line_series`（折れ線・第 2 軸） |
| M-PHOTO / M-ILLUST / M-SCREEN / M-FIGREF | `asset` \| `image` \| `svg`, `caption`?, `source`? | FIGREF は出典必須（CB-35） |
| M-ICONGRID | `items`: [{icon, label, text?}] | 4〜12 個 |

## 画像・作図の指定（`icon` / `asset` / `image` / `svg`）

- 組み込み素材: `{"asset": "1635"}`（`asset_search.py` で探した ID）
- ユーザー抽出素材: `{"asset": "<set>:0012"}`
- 画像ファイル: `{"image": "C:/…/photo.png"}`
- 作図（編集可能な図形になる）: `{"svg": "<svg …>…</svg>"}` または `{"svg": "C:/…/figure.svg"}` — [svg-drawing.md](svg-drawing.md)

## 配置（grid）・関係記号（connectors）・締め（closing）・ナビ表現（devices）

| 種類 | 対応 ID | 備考 |
|---|---|---|
| grid | G-1, G-11, G-23, G-32, G-SIDE, G-N3, G-N4, G-N5, G-3W, G-IO, G-TB, G-RH, G-L, G-2x2, G-GRID, G-MATRIX, G-TL, G-FREE, G-HUB | ペイン数が合わないと grammar_check が ERROR |
| connectors | R-CAUSE（→）, R-SOLVE（⇒）, R-ADD（＋）, R-MUL（×）, R-EQ（＝）, R-VS, R-MUTUAL（⇄）, R-CONV（下の締めへ↓）, R-BRACKET（括り→）, R-ZOOM（拡大線）, R-PAR（記号なし） | 横並びは右向き、G-TB は下向き |
| closing | C-CONCLUSION, C-GOAL, C-TARGET, C-OUTCOME（濃色の全幅バー）, C-POINTS, C-NEXTACTION, C-CAVEAT, C-BRIDGE, C-QUESTION（淡色バー＋ラベル）, C-NOTE（注記） | `text` または `items` |
| devices | V-NAVTAB（`tabs`, `current`）, V-INDEX, V-SCOPE（`pane`, `label`）, V-STAMP（`text`）, V-STATUS（ペインの `status`） | V-SERIES / V-PAIR / V-RECAP はデッキ構成で表す（描画なし） |

## Python から使う

```python
import sys; sys.path.insert(0, "<SKILL_DIR>/scripts")
import helpers as _h; _h.set_lang("ja"); _h.load_theme("acn-technology-graphik")
import json, compose
outline = json.load(open("outline.json", encoding="utf-8"))

def slide12(slide, spec, prs):          # compose 未対応の描画だけ自前で書く
    from helpers import ML, CY, CW, BY
    ...                                  # helpers・compose の _rect / _textbox / _connector を使う

report = compose.build_deck(outline, "output.pptx", custom={12: slide12})
for r in report["slides"]:
    print(r["no"], r["warnings"])        # 文字あふれの推定などの警告
```

`render_body(slide, spec, box=(x, y, w, h))` で、本文の一部の領域だけを部品で描くこともできる。

## v6.1 で追加した部品（artifacts.py）

人が作った資料で多いのに、v6.0 に無かった「実物」と「流れ」の部品。どれも**中身の大きさに合わせて**描き、枠の下が 35% 以上空くと警告を出す（締めの帯ではなく、根拠・注釈・別の部品で埋める）。

| 部品 | 使う関係 | data の形 |
|---|---|---|
| M-CODE | 実物（コード） | `{"title": "mods/audit.ts", "lines": ["..."], "highlight": [3, 4], "notes": [{"line": 3, "head": "発火点", "text": ".."}], "width": 0.6}` |
| M-SCREEN-MOCK | 実物（画面・端末） | `{"title": "claude — ~/project", "kind": "terminal\|app", "rows": [{"text": "> /plugin", "style": "prompt\|out\|tool\|muted\|accent"}], "notes": [{"row": 1, "head": "..", "text": ".."}]}` |
| M-PROMPTBOX | 入力→出力 | `{"label_in": "プロンプト", "prompt": "..", "label_out": "出力", "output": "..", "mid": "Claude"}` |
| M-CHAT-MOCK | 対話の実例 | `{"title": "..", "messages": [{"role": "user\|ai", "text": "..", "name": ".."}]}` |
| M-FILETREE | 実物（ファイル構成）・階層 | `{"items": [{"path": "project/CLAUDE.md", "note": "常に読む", "emph": true}]}`（`/` の深さで字下げ、末尾 `/` はフォルダ） |
| M-TIMELINE | sequence（実行順・時系列） | `{"events": [{"label": "PreToolUse", "text": "..", "emph": true, "at": 0.3, "callout": "統制はここで効かせる"}], "phases": [{"label": "実行", "from": 0.3, "to": 0.8}], "axis_label": ["開始", "終了"]}` |
| M-PIPELINE | flow（成果物の連鎖） | `{"stages": [{"label": "Plan", "artifact": "intent.md", "text": "..", "items": [..], "gate": "レビュー", "emph": true, "hilite": "人が判断する"}], "loop_back": "本番 → 次の intent"}` |
| M-ACTORS | 体制・役割の流れ | `{"actors": [{"name": "人", "role": "判断点を握る", "emph": true, "icon": {"asset": ".."}}], "links": [{"from": 0, "to": 1, "label": "依頼"}], "layout": "row\|hub"}` |
| M-NUMCOL | 少数の要点を大きな番号で | `{"items": [{"head": "..", "text": "..", "items": [..], "icon": {..}}], "focus": 0}` |

既存部品の追加オプション:
- pane に `"focus": true` … その pane だけ紫の枠で強調（並びの中で 1 つだけ。人の資料の並びの 8%）
- 表のセル・本文の `**語句**` … 紫の太字（数値の強調に使う）
- M-ROWHEAD の行の高さは文字量に比例する（全部同じ高さにしない）
- M-TABLE: 既定は `"style": "rule"`（見出しは文字＋下線、行は点線で区切る。`"grid"` で塗りの見出し＋格子）。行の高さは中身の行数に比例。セルに `"^"` を書くと上のセルと縦に結合する（区分の縦帯）
- スライドの `"density": "high"` で本文の文字サイズが 12pt からになる（表・箇条・部品の中）

## 注釈（devices。本文の上に重ねる）

座標は本文領域に対する比率（0〜1）。

| ID | 形 |
|---|---|
| V-ANNOT | `{"type": "V-ANNOT", "text": "統制は実行前で効かせる", "at": [0.03, 0.82], "w": 0.28, "to": [0.3, 0.5]}` … 紫の太字の短い言い切りと、対象への引き出し線 |
| V-HILITE | `{"type": "V-HILITE", "box": [0.66, 0.0, 0.18, 0.62], "label": "人の判断", "dash": false}` … 対象の領域に重ねる強調枠 |
| V-LEGEND | `{"type": "V-LEGEND", "items": [{"fill": "purple", "label": ".."}, {"line": "purple", "label": ".."}]}` … 本文の右上に凡例 |

## 骨格（skeleton）— 人が作ったスライドの配置をそのまま使う

`grammar/skeletons.json` には、参考資料から取り出して採点で選んだ配置の骨格が入っている。図形の種類・位置・線・色の役割・文字枠（役割と目安字数）・繰り返し単位だけを持ち、文字・画像・参照元は持たない。

```bash
$PY …/skeleton.py --intent phases --relation sequence --n 4     # 候補（点数順）
$PY …/skeleton.py K-012                                          # 埋める項目と content の雛形
```
一覧画像: `assets/skeleton_previews/sheet_XX.jpg`（ID と意図のラベル付き）。

スライドの書き方:
```json
{"type": "content", "title": "...", "message": "...", "intent": "phases", "relation": "sequence",
 "skeleton": "K-012",
 "content": {"units": [{"num": "1", "head": "現状把握", "body": ["..", ".."]}, ...],
             "band1": "...", "body1": ["..."], "table1": {"columns": [...], "rows": [[...]]}}}
```
- `units`（2 つ目の繰り返しは `units2`）の個数は骨格の `min`〜`max` の範囲で変えられる（並べ直す）
- 文字は各枠の目安字数（`fit`）以内に。超えると grammar_check が CAPACITY を出す
- 画像枠は `{"asset": "1234"}` / `{"image": path}` / `{"svg": ".."}`、表は M-TABLE、グラフは M-CHART と同じ形
- 骨格の上にも `devices`（V-ANNOT など）と `closing` を重ねられる

## 旧パターンの部品（diagrams.py）

旧パターン N / Z / AA / AC / AE / AG / AK / AL / AM で使う部品。`grammar/presets.json` の組み合わせのまま compose で描ける。

| 部品（旧パターン） | data の形 |
|---|---|
| M-PROFILE（N） | `{"people": [{"name": "..", "role": "..", "org": "..", "items": [".."], "photo": {"image": path}, "emph": true}], "cols": 3}`（photo が無ければ人物の図） |
| M-PROFILE＋M-QUOTE（AM） | 1 人に `"quote": "..."` を付けるとインタビューカード（左に人物、右に大きな引用と要点） |
| M-ROADMAP（Z） | `{"stages": [{"label": "Lv1 個別対応", "items": [..]}], "current": 1, "target": 3, "axis": ["成熟度", "時間"]}` |
| M-2AXIS（AA） | `{"x_axis": ["低", "実現性", "高"], "y_axis": ["低", "効果", "高"], "quadrants": [左上, 右上, 左下, 右下], "highlight": 1, "items": [{"label": "..", "x": 0.8, "y": 0.7, "emph": true}], "side": 0.3, "notes": [..]}` |
| M-PYRAMID（AC） | `{"levels": [{"label": "..", "text": "..", "items": [..]}]（上から）, "share": ["5%", "25%", "70%"], "highlight": 0}` |
| M-VENN（AE） | `{"sets": [{"label": "..", "items": [..]}]（2〜4）, "center": "統合概念", "notes": [..]}` |
| M-ARCH（AG） | `{"zones": [{"label": "利用者", "items": ["..", {"label": "DB", "kind": "db"}]}]（上から）, "links": [["要素A", "要素B", "ラベル"]], "emph": ["要素名"], "direction": "rows\|cols"}` |
| M-TILEMAP（AL: キャンバス） | `{"layout": "canvas", "canvas": {"key_partners", "key_activities", "key_resources", "value", "relationships", "channels", "segments", "cost", "revenue"}, "highlight": "value"}` |
| M-TILEMAP（AK: カレンダー） | `{"layout": "calendar", "days": ["月", ...], "weeks": ["第1週", ...], "events": [{"week": 0, "day": 2, "text": "..", "on": true}]}` |
| M-TILEMAP（タイル） | `{"columns": [{"head": "..", "tiles": [{"text": "..", "on": true}]}], "on_label": "支援対象"}` |

`highlight` は部品の中の 1 か所（象限・段・ブロック）を強調する。pane の `focus`（pane 全体を紫の枠で囲む）とは別。

## v6.2 で追加した部品（体制・評価・公式 Starter Pack の図解）

| 部品 | data の形 | 使う場面 |
|---|---|---|
| M-ORG（org.py） | `{"sides": [{"label": "貴社", "nodes": [{"id": "po", "role": "プロジェクトオーナー", "people": ["経営企画担当役員"]}, {"id": "pm", "role": "PM", "people": [..], "parent": "po"}]}, {"label": "アクセンチュア", "scope": "ご提案範囲", "nodes": [{.., "scope": true}, {"id": "sme", "role": "SME", "parent": "pm", "attach": true}]}], "links": [["pm", "acn_pm", "連携"], ["biz", "acn_biz"]], "legend": ["(F) フルタイム", "(P) パートタイム"], "note": "※本体制図は指揮命令系統を示すものではありません"}` | 提案書の体制図。最後の系列（自社）が紫、他は灰の見出し帯。`attach` は親の横に付く役割（SME・PMO）。`scope: true` の箱を紫の破線で囲む。`links` は同じ高さなら横線（ラベル付きは両矢印）、間に別の箱があると省く。体制ピラミッド（`layers`）は v6.4 で廃止 |
| M-ORG-PYRAMID（廃止） | — | v6.4 で廃止。渡すと会議体の表（M-TABLE）に置き換えて描く。会議体は M-TABLE（会議名・目的・参加者・頻度）か M-MATRIX-SYM（会議体×参加者の ●○） |
| M-SCORE | `{"criteria": ["効果", "実現性", ..], "options": [{"name": "案 B", "scores": [3, 3, ..]（0〜4）, "notes": [".."], "total": "推奨", "emph": true}], "scale": ["なし", "低", "中", "高", "最大"], "total_head": "総合評価"}` | 選択肢の評価（ハーベイボール＋短いコメント）。推す行だけ薄く塗る。凡例は右上に自動 |
| M-PHASEGRID | `{"phases": ["構想", "設計", ..], "rows": [{"label": "業務", "cells": [["作業", ..], ..]}], "current": 1}` | 工程のシェブロン×領域の格子。現在の工程の列を薄く塗る |
| M-MATURITY | `{"levels": ["Lv1 個別", ..], "rows": [{"label": "業務プロセス", "current": 1, "target": 3, "note": "打ち手"}], "note_head": "打ち手", "target_label": "目標"}` | 領域ごとの現状 ● と目標 ◇、差を矢印で |
| M-HOUSE | `{"roof": "目指す姿", "roof_text": "..", "pillars": [{"label": "..", "items": [..]}], "base": ["土台1", "土台2"]}` | 屋根・柱・基盤（全体像） |
| M-CASE | `{"client": "大手化学メーカー", "attrs": [["業界", "化学"], ["期間", "9 か月"]], "headline": "..", "sections": [{"head": "背景・課題", "items": [..]}, {"head": "支援内容", "items": [..]}, {"head": "成果", "kpis": [{"value": "30%", "label": ".."}], "items": [..]}], "image": {..}}` | 事例ページ（左に属性、右に見出し＋課題→支援→成果） |

表（M-TABLE / M-MATRIX-SYM）の追加の指定:
- `highlight_row`: 1 行だけ薄く塗る（推す案）
- `gray_rows`: 今回の範囲外の行を灰色にする
- `scope_rows`: [最初, 最後]（データ行の添字）を紫の破線で囲み、右下に凡例（`scope_label`、既定「今回のご提案範囲」）
- M-MATRIX-SYM は凡例を右上に置く。`legend` が無ければ `legend_kind`（role: ◎ 主担当 ○ 支援・確認 － 対象外 / eval: ◎ 十分 ○ 一部対応 △ 限定的 × 対象外）の既定を付ける

言い切りページ（`"type": "statement"`）: `{"type": "statement", "kicker": "本提案の結論", "message": "保全の判断を、人の勘からデータに移す", "support": "最初の 3 か月で…"}`。濃い紫の単色の面に大きな一文。デッキで 3 枚まで。

## v6.4 で追加・変更した部品（図とアイコン）

アイコンの指定は、どの部品でも次のどれか。`"icon": "q:英語の概念語"`（素材を検索して 1 位を使う。例 `"q:calendar schedule"`）／`"icon": "1307"`（素材 ID）／`{"q": "...", "color": "white"}`（濃い地では白）／`"icon": "none"`（入れない）。部品に `"icons": "auto"` を付けると、icon の無い項目を `icon_q`（無ければラベル）で検索する（ラベルからの自動は点数 10 以上だけ。合う絵が無ければ入れない）。使った絵は `<出力名>_icons.json` / `_icons.png` に一覧が出る。

| 部品 | data の形 | 使う場面 |
|---|---|---|
| M-HUB（figures.py） | `{"center": {"label": "設備データ基盤", "text": "台帳・点検・部品", "icon": "q:database server"}, "nodes": [{"label": "保全計画", "text": "計画を自動で作る", "icon": "q:calendar schedule", "rel": "参照"}, ..]（3〜8）, "emph": ["保全計画"]}` | 中心の主体と周りの関係者・機能（提案書の「全体像」で最も多い型）。中心は濃い紫の円、線の中ほどに関係のラベル |
| M-DIAGRAM-FLOW `style: "icon"` | `{"style": "icon", "nodes": [{"label": "点検記録", "text": "タブレットで入力", "icon": "q:mobile tablet", "by": "人"}, {.., "by": "AI", "highlight": true}], "loop": {"from": 4, "to": 1, "label": "学習に戻す"}}` | アイコン＋ラベルを矢印でつなぐソリューション概要・処理の流れ（6 段まで）。`by` で担い手の札、`loop` で下を回る戻り矢印 |
| M-EQUATION（figures.py） | `{"terms": [{"label": "業務知見", "text": "..", "icon": "q:lightbulb idea"}, .., {"label": "計画工数 50% 減", "text": ".."}], "ops": ["＋", "×", "＝"]}` | 要素の掛け算で成果を示す。最後の項（＝の右）が結論で濃い紫の地 |
| M-ICONROW（figures.py） | `{"head": "提供する 3 つの価値（任意）", "items": [{"label": "計画を速く", "text": "..", "icon": "q:clock speed"}], "layout": "stack|side"}` | 価値・強み・要旨を、箱で囲まずにアイコン＋見出し＋説明で並べる軽い部品。他の部品と G-TB で組んでもよい |
| M-ARCH（変更） | `{"zones": [{"label": "業務", "items": ["保全計画", {"label": "台帳", "kind": "db", "col": 2, "icon": "q:database"}]}], "links": [["A", "B", "参照"], {"from": "A", "to": "B", "label": "記録", "dash": true}], "emph": [..], "scope": {"items": [..], "label": "ご提案範囲"}}` | 層×要素の構成図・範囲図。要素は層をまたいで同じ列にそろう（`col` で列を指定）。線は直角（縦の直線か、層の間を通るかぎ形）で 2pt・矢じり付き、ラベルは線の横に白地。同じ辺から複数の線が出るときは出口をずらす。`scope` の要素を破線で囲み右下にタグ |
| M-CYCLE（変更） | ノードに `icon` を付けると箱の左にアイコン | 矢印は濃い紫 |

並びの幅: 横に並ぶ文字の列（M-CARD・M-HEADCOL・M-BADGECOL・M-BULLETS・M-CHECKLIST・M-NUMLIST）は、文字量が 1.3 倍以上違えば幅を文字量に比例させる（0.75〜1.4 倍）。均等に固定するならスライドに `"equal": true`、手で決めるなら `"ratios"`。

## v6.8 で追加・変更した部品（人の提案書の型。寸法は [proposal-patterns](proposal-patterns.md)）

| 部品 | pane の書き方 | 使いどころ |
|---|---|---|
| M-CASELIST | `columns: ["背景・狙い", 観点…, "着手時期"]`、`rows: [{label, text, checks: [true/"partial"/false], date}]` | 同業の案件の実績一覧（✓ の列） |
| M-COLCARDS | `columns: [{head, sub, icon, cards: [{title, text / items / body}]}]`、`emph` | 支援領域（列×アクセント付きカード） |
| M-PROGRAM | `title, lead, band: {label, text}, panels_label, panels: [{no, title, items}], under, foot: {no, text}, strengths: {head, items}` | 中長期の支援の全体像（五方向の大きな器） |
| M-MELON | `levels`（内側から）、`horizons: [{label, level, dash}]`、`goal: [..]`、`tracks: [{label, milestones: [名前 \| {label, t}]}]` | メロン図（成熟度の段×時期×道筋のロードマップ） |
| M-OUTPUTS | `items: [{head, caption, image, kind: doc/table/chart/map/flow}]`、`cols` | 主要アウトプットのイメージ |
| M-GANTT（拡張） | `tasks[].group`・`lane`・`owner`、`year`、`phases`、`milestones: [{at, label}]`、`legend: {acn, client, joint}`、`scope: {start, end, label}` | 作業の流れ×月のスケジュール |
| M-TREE `style: "kpi"` | `root`、`heads`、`children: [{label, value, children: [{label, value, details}]}]` | 投資対効果・削減率の内訳 |
| M-RHMATRIX（拡張） | `groups: [{label, span}]`、セル `{"body": .., "status": "実施済", "done": true}`、`scope: [{cols / cells, label}]` | 2 段の工程見出し＋実施項目 |
| M-CYCLE（拡張） | arrows のまま段に `body` | 各段に説明＋箇条書き（中身の無い循環図にしない） |
| 箱の `items` | M-DIAGRAM-FLOW icon・M-HUB の段に `items: [..]` | 箱に箇条書きを足す |
| `compose.homeplate(slide, x, y, w, h, fill, line, line_w, tip)` | — | 工程の見出し（五方向の矢印。隙間 `PHASE_GAP`＝0.08） |
| `compose.merge_text_into_boxes(slide)` | build_deck が自動で呼ぶ | 矩形の上に重ねたテキストボックスを箱の文字に書き直す（環境変数 `ACNPPTX_NO_MERGE=1` で止める） |

## v6.6 で追加・変更した部品

| 部品・関数 | data の形 | 使う場面 |
|---|---|---|
| M-CYCLE（作り直し） | `{"style": "arrows|panels|band", "nodes": [{"label": "計画", "text": "..", "body": [リッチ本文], "highlight": false}], "center": "四半期ごと" | {"label":..,"text":..}}`（3〜6 段） | arrows＝円弧の矢印の円＋各矢印の外に番号・名前・説明／panels＝中央の円＋左右の同じ大きさのパネル（`body` があれば既定）／band＝太い帯の輪の上に名前。旧来の円周配置は `"free"`。`M-RING` は同じ |
| M-ZONE `style: "summary"`（変更） | `body: [{"b": [{"lead": "要点", "text": "説明"}, ..]}]`（文字列でもよい） | 要旨。番号の箱＋灰の面の行（すべて同じ高さ） |
| `density: "max"`（スライド） | — | 本文 600〜900 字。隙間・帯・余白を下限に、300 字以上で本文 11pt |
| `grid: "G-2x3"` | ペイン 6 個 | 6 つの論点など（3 列 × 2 行） |
| `==語==`（文中） | — | 太字＋濃い紫（1 文 1 句・1 枚 3 句まで）。`**語**` は太字だけ |
| `connect.link(slide, a, b, sa, sb, color, width, arrow=False, both=False, dash=False, mid=None)` | a・b は図形、sa・sb は辺 t/l/b/r（省略で自動） | 図形どうしをつなぐ線（接続付き。直線・L 字・Z 字・U 字を自動で選ぶ）。`mid` は曲がる位置の座標 |
| `figures.EMPH` | `{"fill": 淡紫, "line": 濃い紫, "w": 2.25}` | 並びの 1 つを強調する箱。M-HUB の `emph`、循環図の `highlight`、pane の `focus` |
| `connect.route(a, b, sa, sb, mid=None)` | — | link が描く線の通り道（インチの点の列）。手で図を描くとき、ほかの箱・線・ラベルに当たらないか `connect.seg_hits` / `seg_overlap` / `seg_cross` で確かめる（v6.7） |
| `helpers.add_message_line(slide, text, reserve=0)` | reserve は右端に空ける幅（in） | 2 行になるなら語の切れ目で改行する。右上に札・凡例を置くページは `compose.msg_reserve(spec)` の幅を空ける（compose が自動。v6.7） |
| `compose._connector(..., glyph=True)` | — | 線を継いで描く記号（ツリーの罫・座標軸）。LINE-02 の対象外 |

## v6.5 で追加・変更した部品（情報量の多いページ）

寸法と型の一覧は [dense-pages](dense-pages.md)。本文はリッチ本文（`[{"h": 小見出し}, {"p": 文}, {"b": [文 | {"text":.., "sub":[..]}], "mark": "□"}, {"n": [..]}, {"concl": 結論}, {"note": 補足}]`）で書ける。文字は面を埋める最大（16→14→12、密なページは 11 まで）を自動で選ぶ。

| 部品 | data の形 | 使う場面 |
|---|---|---|
| M-ZONE（dense.py） | `{"title": "課題・ニーズ", "style": "band|rule|summary", "fill": "gray|purple|white|none", "emph": false, "lead": "太字の先頭行", "body": [リッチ本文], "icons": [{"icon": "q:shield", "label": ".."}], "sections": [{"title":.., "body":..}], "bullet": "□"}` | 目的と骨子・パッケージ概要・課題/解決の列。`summary` は要旨（16〜20pt） |
| M-ROWHEAD の Why 型 | `{"columns": ["貴社の課題", "アクセンチュアの強み"], "rows": [{"head": "..", "sub": "（補足）", "badge": "a", "lead": "強みの要約（**強調**）", "detail": [リッチ本文]}]}` | 選ばれる理由（課題 3 行 × 強み a/b/c） |
| M-RHMATRIX（dense.py） | `{"title": "列の上の帯（任意）", "columns": [{"label": "..", "sub": ".."}], "col_style": "rule|band|chevron", "col_ratios": [1, 1], "emph_col": 1, "rows": [{"head": "対象", "cells": [リッチ本文 | {"icon": "q:..", "text": ..}], "why": false}], "head_w": 1.35}` | 行見出し × 列の文章の格子（両輪の比較・工程×層）。`why: true` で 1 セルが全列をまたぐ |
| M-STEPS（dense.py） | `{"steps": [{"label": "ツール変換", "title": "要点", "body": [リッチ本文], "icon": "q:server", "icon_label": "台帳"}], "icon_col": true}` | 番号ステップ（下向き五角形＋説明）。右端にアイコンの流れ |
| M-FIGNOTE（dense.py） | `{"figure": {"module": "M-CYCLE", ..}, "ratio": 0.56, "notes": [{"title": "..", "text": ".."}], "markers": [{"n": 1, "x": 0.1, "y": 0.3}]}` | 図＋番号の解説 |
| M-CARD の強み型 | `{"number": "01", "head": "CXO との\n信頼関係", "lead": "要点（**強調**）", "text": "補足", "icon": "q:handshake"}` | 5 つの強み（G-N5）。下端に C-CONCLUSION |
| M-ICONGRID の実績型 | `{"items": [{"icon": "q:flask", "value": "30+ years", "text": ".."}], "cols": 2}` | アイコン（小）＋数字＋説明の格子 |
| M-CYCLE（変更） | 変更なし（`nodes`・`center`） | 楕円のリングに箱を重ね、切れ目に向きの三角。旧来の円周配置は `style: "free"` |
| M-HUB（変更） | 変更なし | 中央の円の左右に面の箱を縦にそろえ、直角の短い線（1.5pt、強調 2.25pt）でつなぐ |
| M-DIAGRAM-FLOW `style: "icon"`（変更） | 変更なし | 上に小さなアイコン（0.6in）、面の箱、段の間に灰の三角、戻り矢印 2.25pt |
| M-ICONROW（変更） | `items[].value`（大きな数字）・`body`（リッチ本文）を追加 | アイコンは見出しの左に小さく。数字と説明が主役 |
| M-ORG（変更） | node に `"members": [{"name": "保全課 課長", "kind": "full|part|sme"}]` | 人のアイコン（塗り＝専任・胴が白＝兼任・線だけ＝専門家）。凡例は右上に自動。`people_legend` で文言を変えられる |
| R-TRI（関係記号） | `"connectors": ["R-TRI"]` | ゾーンの間の灰の三角（高さは面の 66%）。目的 → 骨子、課題 → 解決 |
| C-WHY（締め） | `{"type": "C-WHY", "label": "Why Accenture", "items": [{"h": "独自の進め方：", "p": ".."}]}` | 下端の Why 帯（紫の札＋灰の面に太字紫の見出し＋本文） |
