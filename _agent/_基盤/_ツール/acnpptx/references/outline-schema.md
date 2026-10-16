# Outline Schema v2 — デザイン文法で書くアウトライン

`outline.json` は「何を言うか（文言）」と「どう見せるか（構成）」を 1 枚ずつ持つ。
描画は `compose.py`（`build_deck`）がこのファイルだけを見て行う。部品ごとのデータの形は [compose-api.md](compose-api.md)、構成の選び方は [grammar-guide.md](grammar-guide.md)。

## トップレベル

```json
{
  "title": "Claude Code 活用ガイド",          // 表紙タイトル
  "subtitle": "Mods・Harness・ループ・SDLC",
  "date": "2026年10月",
  "author": "Accenture",
  "language": "ja",                          // ja / en（set_lang に渡す）
  "theme": "acn-technology-graphik",         // 【acnpptx設定】テーマ=
  "cover_layout": "cover",                   // 表紙のバリエーション（layout_indices の cover* から Claude が選ぶ）
  "story_template": "T-06",                  // grammar/compositions.json の story_templates
  "sequences": [{"id": "S-01", "slides": [5, 6, 7], "note": "全体図→スコープ枠→詳細"}],
  "settings": {"tone": "研修・解説", "variation": "バランス", "density": "標準", "images": "おまかせ",
               "chapters": "入れる", "min_body_slides": 15},
  "sources": [{"id": "src1", "title": "…", "url": "…", "fetched": true, "published": "2026-03"}],
  "as_of": "2026-10",                        // 作成日（今日）。実績は as_of 以前、スケジュールは as_of 以降（DATE-02/03）
  "anchors": [{"name": "（題材の製品・機能）の一般提供", "date": "YYYY-MM", "source": "src1"}],  // 題材の開始日。実績・事例の時期はこれ以降（DATE-01）
  "slides": [ … ]
}
```

## スライドの種類（`type`）

| type | 中身 | 枚数の数え方 |
|---|---|---|
| `cover` | トップレベルの title / subtitle / date / author を使う | 表紙 |
| `agenda` | `items`（省略時は section の title を自動列挙） | 本文に数えない |
| `section` | `title`, `number`（省略時は連番）, `description` | 本文に数えない |
| `content` | 下記 | **本文** |
| `closing` | `title`（既定 "Thank You"）, `subtitle` | 締め |
| `statement` | `message`（大きな一文）, `kicker`（上の小見出し）, `support`（下の補足 1 文） | 言い切りページ。本文に数えない。デッキで最大 3 枚、物語の転換点だけ |

「表紙と最後のページを含まずに 15 枚以上」= `content` が 15 枚以上（`settings.min_body_slides: 15`）。

## content スライド

```json
{
  "type": "content",
  "chapter": "Mods",              // 章（以降のスライドに引き継ぐ。中扉があればその title）→ パンくずを自動で付ける
  "crumb": "全体像",               // 任意: パンくずの小見出し（「Mods > 全体像」）。breadcrumb を書けばそれが優先、"" で消す
  "title": "Mods の 4 つの拡張点",                      // 1 行の短い論点（2 行になると ERROR）
  "message": "用途に応じて Skills・Hooks・MCP・Plugins を使い分ける",  // 1〜2 文・最大 2 行。主語と述語のある常体の文
  "role": "What",                 // Why / What / How / Ask / Plan / Proof / Learn / Appendix
  "intent": "framework",          // grammar/intent_map.json のキー
  "relations": ["parallel"],      // add / cause / contrast / converge / equation / flow / hierarchy / multiply / mutual / parallel / sequence / solve
  "materials": ["text", "icons"], // chart / diagram / external_figure / icons / logos / numbers / people_org / photo / screenshot / table_data / text
  "density": "mid",               // low / mid / high
  "composition": "P-014",         // 選んだ構成パターン（grammar_select.py の chosen）
  "grid": "G-N4",                 // 配置
  "ratios": [1, 1, 1, 1],         // 任意: ペインの幅（縦配置なら高さ）の比
  "panes": [ {"module": "M-BADGECOL", "header": "Skills", "icon": {"asset": "1635"}, "title": "…", "text": "…"}, … ],
  "connectors": ["R-PAR"],        // 文字列ならすべてのペイン間、{"type","from"} なら from 番目と次の間
  "closing": {"type": "C-CONCLUSION", "text": "まず Skills で手順を共有し、Hooks で自動化する"},
  "devices": ["V-INDEX", {"type": "V-SCOPE", "pane": 1, "label": "今回の範囲"}],
  "source": "出典: Anthropic「Claude Code の Mods」（2026）",
  "illustrative": false,          // 試算・仮置きの値なら true。source に「試算の前提: …」を書く（「イメージ」の札は成果物・画面の見本のページだけに自動で付く）
  "emphasis": ["Hooks"],          // 任意: 強調語（本文中の **語** も強調になる。1 枚 3 箇所まで）
  "visual_query": "拡張 部品 モジュール"   // 任意: 画像を探すときの検索語（asset_search に渡す）
}
```

- `panes[].header` はペイン上部の見出し帯。`V-INDEX` があると見出しに番号バッジが付く
- `panes[].status`（完了 / 進行中 / 未着手）で見出しにステータスタグ（V-STATUS）
- compose が対応していない部品を使うときは、build スクリプトで `custom={スライド番号: 関数}` を渡す

## v6.1 の追加項目（設計票）

| 項目 | 例 | 用途 |
|---|---|---|
| `relation` | `"sequence"` | 内容の関係（parallel / sequence / hierarchy / cause / flow / contrast / converge / mutual）。図の形を決める。並列でないのに均等カードを使うと grammar_check / craft_check が ERROR（`relations` 配列でもよい） |
| `dominant` | `"chart"` / `"kpi"` / `"statement"` / `"artifact"` | 主役（任意） |
| `evidence` | `["3.1 倍", "PR 150 件"]` | 根拠の数値・事例・実物（任意。メッセージの数値は本文にも出す） |
| `skeleton` + `content` | `"K-012"`, `{...}` | 人の配置の骨格を使うとき（compose-api の「骨格」） |
| `devices` | `[{"type": "V-ANNOT", ...}]` | 注釈・強調枠・凡例 |
| `settings.divider` | `"auto"`（既定）/ `"agenda"` / `"section"` | 中扉の出し方。auto は本文 ÷ 章 < 8 なら目次＋現在地 |
| section の `description` | `"まず挙動を変える。入力と実行点を制御する"` | 章の結論文（必須） |

## v6.2 の追加項目（捨てる編集とリズム）

トップレベル:

| 項目 | 例 | 用途 |
|---|---|---|
| `mode` | `"present"` / `"read"`（既定） | 投影用（LT・勉強会・講演）は本文 16pt・最小 14pt。読み物（提案書・報告書）は 14・12pt |

content スライド（設計票。描画には使わないが、craft_check と評価役が読む）:

| 項目 | 例 | 用途 |
|---|---|---|
| `page_type` | `"thesis"` / `"evidence"` / `"mechanism"` / `"decision"` / `"action"` | ページの役割。同じ型を 3 枚続けない |
| `signature` | `true` | 記憶に残すシグネチャースライド（デッキで 3〜5 枚） |
| `takeaway` | `"判断を握る所だけ人が持つ"` | 聞き手が 3 秒後に覚えている一文 |
| `proof` | `"M-PIPELINE の判断ゲート"` | その一文を証明する唯一の図 |
| `drop` | `["設定ファイルの一覧"]` | このスライドで捨てる情報 |
| `placement` | `"appendix"` / `"talk"` / `"next"` | 捨てた詳細の置き場 |
| `silhouette` | `"左に大きな数字、右に原因 3 行"` | 前後と違う輪郭 |
| `purple` | `"推奨案の行"` | 紫で強調する唯一の対象 |

検査（craft_check --outline）: 主図と同じ内容の表（ERROR）・タイトルの言い直し（ERROR）・凡例の無い ◎○△（ERROR）・表が 2 つ・紫の強調の競合・同じ page_type の 3 連続・言い切りページ 4 枚以上・投影用で 14pt 未満が多い（WARN）。

## v6.3 の追加項目（見出しの 3 階層と型の選択）

トップレベル: `deck_type`（`proposal` / `report` / `training` / `lt` / `offering` / `internal` / `techvision`）、`settings.breadcrumb`（`"auto"` 既定 / `false`）

content スライド:

| 項目 | 例 | 用途 |
|---|---|---|
| `chapter` / `crumb` | `"Harness"` / `"Effort"` | 章ラベル（パンくず）。章は次に変わるまで引き継ぐ。中扉があればその title |
| `purpose` | `"納得させる"` | 読み手にさせたいこと（掴ませる / 理解させる / 納得させる / 選ばせる / 決めさせる / 覚えさせる / 参照させる / 行動させる） |
| `story_step` | `"根拠"` | 話の段（背景 / 目的・ゴール / 要旨 / 課題 / 原因 / 打ち手 / 全体像 / 詳細 / 根拠 / 比較・評価 / 計画 / 体制 / 費用 / 前提 / 事例 / 効果 / 示唆 / 手順 / 定義 / まとめ / 依頼・次の一手） |
| `shape` | `{"n_items": 4, "attrs": 3, "relation": "contrast", "data": "magnitude", "focus": true, "text_load": "mid"}` | 内容の形。`attrs` は 1 要素あたりの観点の数（表なら列数−1）。`data`: timeseries / composition / magnitude / single_kpi / none |
| `from_prev` | `"evidence"` | 前のスライドとのつながり（zoom_in / evidence / contrast / next_step / parallel_next / shift / summary / new_topic） |
| `family` | `"table"` | 選んだ型（任意。無ければ骨格・部品から判定） |
| `layout_reason` | `"実データのガントが証拠なので維持"` | layout_select の 1 位と違う型にした理由（書くと SEL-01/02 を出さない） |

検査（grammar_check）: タイトルが 2 行（ERROR）・メッセージが 3 行以上（ERROR）・3 文以上（WARN）・体言止めの断片（MSG-12）・パンくずが文（BC-01）・型の選択（SEL-00〜03）。craft_check: 本文の 1 項目がメッセージを言い直す（重なり 60% 以上 ERROR、45% 以上 WARN）。

## v6.4 の追加項目（図・アイコン・幅）

| 欄 | どこに | 値 | 意味 |
|---|---|---|---|
| `icon` | 部品・項目 | `"q:英語の概念語"` / 素材 ID / `{"q": "..", "color": "white"}` / `"none"` | アイコン。`q:` は素材を検索して 1 位を使う（合う素材が無ければ入れない） |
| `icons` | pane・スライド | `"auto"` | icon の無い項目を `icon_q`（無ければラベル）で検索して入れる |
| `icon_q` | 項目 | 英語の概念語 | `icons: "auto"` のときの検索語 |
| `style` | M-DIAGRAM-FLOW | `"icon"` | アイコン＋ラベルの概念図（`by`・`loop`・`highlight`） |
| `equal` | スライド | `true` | 横に並ぶ文字の列を均等幅に固定（既定は文字量に比例） |
| `scope` | M-ARCH | `{"items": [..], "label": "ご提案範囲"}` | 範囲の要素を破線で囲む |
| `col` | M-ARCH の要素 | 列番号 | 層をまたいで同じ列にそろえる（縦の線がまっすぐ通る） |

定型ページ（提案書・報告書の体制・会議体・スケジュール・見積・前提）は `title` と `story_step` から自動で判定される（`grammar/standard_pages.json`）。

## v6.6 の追加項目

| 項目 | 場所 | 値 | 意味 |
|---|---|---|---|
| `density` | スライド | `"max"` | 本文 600〜900 字の最も密なページ（隙間・帯・余白を下限に、300 字以上で本文 11pt） |
| `grid` | スライド | `"G-2x3"` | 3 列 × 2 行の格子 |
| `style` | M-CYCLE | `"arrows"` / `"panels"` / `"band"` | 円弧の矢印の円 ／ 中央の円＋左右のパネル ／ 帯の輪 |
| `lead` | M-ZONE `summary` の項目 | 文字列 | 要旨の行の要点（太字 16〜18）。`text` が説明 |
| `==語==` | 文中 | — | 太字＋濃い紫（色付きの強調。1 文 1 句・1 枚 3 句まで）。`**語**` は太字だけ |

## v6.5 の追加項目（情報量の多いページ）

| 項目 | 場所 | 値 | 意味 |
|---|---|---|---|
| `density` | スライド | `"high"` | 提案書・報告書の中身のページ。本文 400 字以上なら本文を 11pt まで下げてよい（補足・注記は常に 11pt） |
| `body` | M-ZONE・M-CARD・M-HEADCOL・M-RHMATRIX のセル・M-STEPS・M-ROWHEAD の `detail` | リッチ本文 | 小見出し `h`・文 `p`・箇条書き `b`（`sub` で 2 段目、`mark` で記号）・番号 `n`・結論 `concl`・補足 `note` |
| `style` | M-ZONE | `"band"` / `"rule"` / `"summary"` | 帯の見出し／下線の見出し／要旨 |
| `members` | M-ORG の node | `[{"name":.., "kind": "full|part|sme"}]` | 人のアイコン付きの体制図 |
| `connectors` | スライド | `["R-TRI"]` | ゾーンの間の灰の三角 |
| `closing` | スライド | `{"type": "C-WHY", "items": [..]}` | 下端の Why 帯 |

定型ページに 要旨（タイトルに「サマリ」「骨子」「要旨」）・選ばれる理由（「Why」「選ばれる理由」）を追加。提案書の本文の最初の 3 枚に要旨が無いと STD-02。

## 検証

```bash
$PY <SKILL_DIR>/scripts/grammar_select.py outline.json --out candidates.json   # 候補とデッキ全体の選択
$PY <SKILL_DIR>/scripts/grammar_check.py outline.json                          # 描画前チェック（ERROR で exit 1）
$PY <SKILL_DIR>/scripts/compose.py outline.json output.pptx                     # 描画
```
