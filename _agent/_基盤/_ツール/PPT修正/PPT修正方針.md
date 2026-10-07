# PPT修正 作業マニュアル

このフォルダはPPT資料を修正するための汎用ワークスペース。複数チャットセッションから利用されるため、**作業を始める前に必ずこのドキュメントを読み込み、最新の方針・技術的な落とし穴・コードテンプレートを把握すること**。新たな知見・トラブルはこのファイルに随時追記し、改訂履歴を残す。

---

## 1. ワークフロー全体像

```
[1] Input/ から対象pptxを発見
   ↓
[2] python-pptx でテキスト抽出(markitdownは文字化けするので不可)
   ↓
[3] 修正観点の洗い出し(承認不要/承認必須に分類)
   ↓
[4] 承認必須項目を Before/After 形式・通し番号付きでユーザーに提示
   ↓
[5] 承認を得る(個別却下があり得るので一括「承認」だけに頼らない)
   ↓
[6] フォルダ作成 → 原本移動 → ビルドスクリプト実行 → 検証
   ↓
[7] 出力pptxの内容をテキスト抽出で確認(修正前後が交互配置されているか/ワッペンが入っているか)
```

---

## 2. フォルダ運用ルール

- 修正対象の資料はユーザーが `Input/` に格納
- 修正完了時、ワークスペース直下に **資料名と同名のフォルダ** を作成
  - 例: `Input/提案書.pptx` → `提案書/` フォルダ
- フォルダ内に格納するもの:
  - **修正前ファイル**(`Input/` から **移動**。コピーではない)
  - **修正後ファイル** (`<元ファイル名>_修正後.pptx`)
- `Input/` は作業後に空になる

---

## 3. 修正方針

### 3.1 対象範囲

- **修正するのはボディ部の日本語記載のみ**
- **タイトル(各スライド先頭の大見出し)は修正対象外**
- フォント・文字サイズ・色・配置などの体裁は **一切変更しない**(テキスト内容のみ置換)
- 日付ヘッダー(例:「2026/4/30 会議名」)・小見出し(章番号付き問い)はボディ扱いで修正可

### 3.2 修正カテゴリ

#### 事前確認 **不要**(検出次第そのまま修正)

| カテゴリ | 内容 |
|---------|------|
| 誤字脱字 | タイプミス、変換ミス |
| 文法誤り | てにをは、活用、係り受け、助詞抜け |
| 表記ゆれ統一 | 漢字/かな(「事/こと」「為/ため」)、カタカナ長音(「サーバ/サーバー」)、固有名詞(「Restful/RESTful」「JaDES/JAdES」) |
| **括弧の半角化** | **全角括弧 `（）` は全て半角括弧 `()` に統一**(本ワークスペースの確定ルール) |
| 句読点の適正化 | 読点の打ちすぎ・不足、孤立した括弧記号 |
| 不要記号・スペース除去 | 全角スペース混入、重複記号、文末の不完全な句読点 |

> **重要**: 括弧 **以外** の体裁(コロン `:`/`：`、ブラケット `[]`/`［］`、数字 `1`/`１`)は **原本の表記を尊重して変えない**。原本が全角コロン `：` を使っていれば修正後も全角コロンを維持する。

#### 事前確認 **必須**(チャットで修正案を提示し承認後に反映)

| カテゴリ | 内容 |
|---------|------|
| 冗長性の排除 | 重複表現、不要な修飾語の削除 |
| 論理構造の改善 | 文の順序、接続、構成の見直し |
| きれいな日本語化 | 不自然な言い回し、翻訳調、口語表現をビジネス文書らしい自然な日本語に |
| 語彙の統一・適正化 | 同概念の表現揺れ統一(例: お客様/顧客/クライアント) |
| 敬体/常体の統一 | 「です・ます調」と「だ・である調」の混在解消 |
| 抽象度の調整 | 曖昧表現の具体化 / 冗長な具体例の抽象化 |
| 能動/受動の最適化 | 不要な受動態を能動態に(主語の明確化) |
| 箇条書きの粒度統一 | 粒度のバラつきを揃える |
| 文末スタイルの統一 | 体言止め/用言止めの統一(箇条書き内) |

> ⚠ **承認必須カテゴリは意図を変えうるため、修正前に必ずチャットで Before/After を提示**して承認を得る。承認不要カテゴリは検出次第そのまま反映。

### 3.3 Before/After 提示時のフォーマットルール

- **通し番号必須**: `#1`, `#2`, ... をスライドをまたいで通しで振る(部分却下を可能にする)
- 各項目の構成:
  - `#N` + **種類タグ**(冗長性排除 / 論理構造改善 / きれいな日本語化 等)+ **箇所**(Slide N / 段落特定情報)
  - **Before**: 原文
  - **After**: 修正案
- スライド毎に小見出しでグルーピング(可読性確保)

### 3.4 スライド対応関係

- 修正前スライドと修正後スライドは **1対1で対応**(交互配置)
  - 出力構成: `[修正前1, 修正後1, 修正前2, 修正後2, ...]`
- 修正後スライドの **右上に「修正後」ワッペン** を追加
  - 色は赤系(C8102E) + 白文字、Meiryo UI 16pt Bold が標準
- ワッペン以外はレイアウト変えない
- 修正前スライドはそのまま残す(削除しない)

---

## 4. 技術的な落とし穴(必読)

### 4.1 文字化け対策

- **markitdown は Windows 環境で日本語pptxの抽出が文字化けする**。テキスト確認は必ず `python-pptx` で直接読む
- スクリプト実行時は `PYTHONUTF8=1 PYTHONIOENCODING=utf-8` を環境変数として付ける

### 4.2 原本の文字エンコーディングを必ず確認する

日本のpptx原本は **全角句読点を多用** している。例:

| 文字 | 半角(U+) | 全角(U+) | 原本でよく見るパターン |
|------|---------|---------|----------------------|
| コロン | `:` (003A) | `：` (FF1A) | 「課題意識：」「対応策：」 |
| 角括弧 | `[]` (005B/005D) | `［］` (FF3B/FF3D) | 「［基金からのコメント］」 |
| 丸括弧 | `()` (0028/0029) | `（）` (FF08/FF09) | 「（lastUpdated）」 ← **これだけ半角化対象** |
| 数字 | `12` (0031/0032) | `１２` (FF11/FF12) | 「対応策１」「対応策２」 |
| ピリオド | `.` (002E) | `．` (FF0E) | 「1．タイトル」 |

**置換キーは原本の文字を使う必要がある**。半角で書いた検索キーは全角文字には絶対マッチしない。

調査方法(コードスニペット):
```python
from pptx import Presentation
prs = Presentation("path/to/file.pptx")
for i, slide in enumerate(prs.slides, 1):
    for shape in slide.shapes:
        if not shape.has_text_frame: continue
        for p in shape.text_frame.paragraphs:
            for ch in p.text[:30]:
                if ord(ch) > 127:
                    print(f"S{i}: {ch}=U+{ord(ch):04X}")
```

### 4.3 置換順序

1. **先**: 全角括弧 `（）` → 半角 `()` の文字レベル変換(`str.translate` を使う)
2. **後**: 段落単位の特定置換(冗長性・論理構造・誤字)
   - 特定置換のキーは「**1のあとの状態**」と一致させる必要がある(つまり半角丸括弧で書く)
   - 一方、コロン・角括弧・数字は原本の全角を保つので、**全角のまま** キーに書く

### 4.4 run単位のテキスト置換

- `paragraph.text = "..."` は **書式が落ちる**。絶対に使わない
- 1つのrun内に置換対象が収まる場合: `run.text = run.text.replace(old, new)`
- 複数runにまたがる場合: 結合した全文で置換し、先頭runに書き戻す + 他runを空文字に
- 既存runの font.name / font.size / font.bold / font.color は触らない(自動的に維持される)

### 4.5 スライド複製テクニック

python-pptx には公式の `duplicate_slide` がない。spTreeのdeepcopyで実現:

```python
def duplicate_slide(prs, src_idx):
    src = prs.slides[src_idx]
    new_slide = prs.slides.add_slide(src.slide_layout)
    spTree = new_slide.shapes._spTree
    # add_slideで自動付与される placeholder shape類を消す
    for child in list(spTree):
        tag = child.tag.split("}")[-1]
        if tag in ("sp", "pic", "graphicFrame", "grpSp", "cxnSp"):
            spTree.remove(child)
    # 元スライドの shape を deepcopy で持ってくる
    from copy import deepcopy
    for child in src.shapes._spTree:
        tag = child.tag.split("}")[-1]
        if tag in ("sp", "pic", "graphicFrame", "grpSp", "cxnSp"):
            spTree.append(deepcopy(child))
    return new_slide
```

**注意**: 画像(`pic`)を含むスライドでは relationship のコピーが別途必要。本ワークスペースの過去案件はテキスト中心だったので未対応。画像付きが来たら拡張すること。

### 4.6 スライド順序操作

```python
def move_slide(prs, from_idx, to_idx):
    sldIdLst = prs.slides._sldIdLst
    target = list(sldIdLst)[from_idx]
    sldIdLst.remove(target)
    sldIdLst.insert(to_idx, target)
```

複製戦略:「全スライドを末尾に複製 → `move_slide` で交互配置に並べ替え」がシンプル。
3スライドの場合: `[S1,S2,S3,S1',S2',S3']` → `move_slide(prs,3,1)` → `[S1,S1',S2,S3,S2',S3']` → `move_slide(prs,4,3)` → `[S1,S1',S2,S2',S3,S3']`

### 4.7 タイトル除外

タイトル文字列の一部を `TITLE_TEXT` 定数に入れ、各段落の全文に含まれていたら置換スキップ。

---

## 5. 標準ビルドスクリプトのテンプレート

過去案件で動作確認済みのスクリプト構成。新規案件では下記を雛形にして REPLACEMENTS 部分だけ書き換える。

```python
# -*- coding: utf-8 -*-
import os, shutil
from copy import deepcopy
from pptx import Presentation
from pptx.util import Inches, Pt, Emu
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import PP_ALIGN

WORKDIR = r"<このワークスペースの絶対パス>"
INPUT_NAME = "<元ファイル名>.pptx"
OUTDIR_NAME = "<元ファイル名(拡張子なし)>"

INPUT = os.path.join(WORKDIR, "Input", INPUT_NAME)
OUTDIR = os.path.join(WORKDIR, OUTDIR_NAME)
ORIGINAL = os.path.join(OUTDIR, INPUT_NAME)
MODIFIED = os.path.join(OUTDIR, INPUT_NAME.replace(".pptx", "_修正後.pptx"))

os.makedirs(OUTDIR, exist_ok=True)
if os.path.exists(INPUT):
    shutil.move(INPUT, ORIGINAL)

PAREN_TRANS = str.maketrans({"（": "(", "）": ")"})
TITLE_TEXT = "<タイトル文字列(部分一致用)>"

REPLACEMENTS = {
    0: [  # Slide index 0
        # ("Before原文", "After修正案"),
        # ...
    ],
    1: [
        # ...
    ],
}

def _to_zenkaku_punct(s):
    """検索キー/置換値を原本の全角句読点に揃える(括弧以外)"""
    s = s.replace(":", "：").replace("[", "［").replace("]", "］")
    s = s.replace("対応策1", "対応策１").replace("対応策2", "対応策２")
    return s

REPLACEMENTS = {k: [(_to_zenkaku_punct(o), _to_zenkaku_punct(n)) for o, n in v]
                for k, v in REPLACEMENTS.items()}
# 重複除去
for k in REPLACEMENTS:
    seen, uniq = set(), []
    for o, n in REPLACEMENTS[k]:
        if (o, n) not in seen:
            seen.add((o, n)); uniq.append((o, n))
    REPLACEMENTS[k] = uniq

def convert_parens_in_slide(slide):
    for shape in slide.shapes:
        if not shape.has_text_frame: continue
        for p in shape.text_frame.paragraphs:
            if TITLE_TEXT in "".join(r.text for r in p.runs):
                continue
            for run in p.runs:
                if "（" in run.text or "）" in run.text:
                    run.text = run.text.translate(PAREN_TRANS)

def replace_in_paragraph(p, old, new):
    full = "".join(r.text for r in p.runs)
    if old not in full: return 0
    for run in p.runs:
        if old in run.text:
            run.text = run.text.replace(old, new); return 1
    runs = list(p.runs)
    runs[0].text = full.replace(old, new, 1)
    for r in runs[1:]: r.text = ""
    return 1

def replace_in_slide(slide, replacements):
    misses = []
    for old, new in replacements:
        n = 0
        for shape in slide.shapes:
            if not shape.has_text_frame: continue
            for p in shape.text_frame.paragraphs:
                n += replace_in_paragraph(p, old, new)
        if n == 0: misses.append(old[:50])
    return misses

def duplicate_slide(prs, src_idx):
    src = prs.slides[src_idx]
    new_slide = prs.slides.add_slide(src.slide_layout)
    spTree = new_slide.shapes._spTree
    for child in list(spTree):
        tag = child.tag.split("}")[-1]
        if tag in ("sp", "pic", "graphicFrame", "grpSp", "cxnSp"):
            spTree.remove(child)
    for child in src.shapes._spTree:
        tag = child.tag.split("}")[-1]
        if tag in ("sp", "pic", "graphicFrame", "grpSp", "cxnSp"):
            spTree.append(deepcopy(child))
    return new_slide

def move_slide(prs, from_idx, to_idx):
    sldIdLst = prs.slides._sldIdLst
    target = list(sldIdLst)[from_idx]
    sldIdLst.remove(target); sldIdLst.insert(to_idx, target)

def add_revised_badge(prs, slide):
    w, h = Inches(1.2), Inches(0.45)
    x = prs.slide_width - w - Inches(0.25)
    y = Inches(0.10)
    shape = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, x, y, w, h)
    shape.fill.solid(); shape.fill.fore_color.rgb = RGBColor(0xC8, 0x10, 0x2E)
    shape.line.fill.background()
    tf = shape.text_frame
    tf.margin_left = tf.margin_right = tf.margin_top = tf.margin_bottom = Emu(0)
    p = tf.paragraphs[0]; p.alignment = PP_ALIGN.CENTER
    run = p.add_run(); run.text = "修正後"
    run.font.size = Pt(16); run.font.bold = True
    run.font.color.rgb = RGBColor(0xFF, 0xFF, 0xFF); run.font.name = "Meiryo UI"

# ===== Build =====
prs = Presentation(ORIGINAL)
n = len(prs.slides)
dups = [(i, duplicate_slide(prs, i)) for i in range(n)]
for orig_idx, dup in dups:
    convert_parens_in_slide(dup)
    misses = replace_in_slide(dup, REPLACEMENTS.get(orig_idx, []))
    add_revised_badge(prs, dup)
    for m in misses:
        print(f"[MISS] S{orig_idx+1}: {m}...")

# 交互配置に並べ替え: [S1..Sn, S1'..Sn'] -> [S1,S1',S2,S2',...]
for i in range(1, n):
    move_slide(prs, n + i, 2 * i + 1)
# 上記は n=3 では: move(4,3) を意味するが、 n=3 の場合の正解は move(3,1) then move(4,3)
# → スライド数が変動する案件では下記の確実版を使うこと
# 確実版(全スライド数 n):
#   現状 [S1, S2, ..., Sn, S1', S2', ..., Sn']
#   目標 [S1, S1', S2, S2', ..., Sn, Sn']
#   ループで k=0..n-1, move_slide(prs, n + k, 2*k + 1)
#   ※ k=0 は S1' を index1 に動かす操作

prs.save(MODIFIED)
print(f"saved: {MODIFIED}")
```

> **注**: 並べ替えループは n に依存。シンプルなのは「複製を末尾に置いて、k=0..n-1 で `move_slide(prs, n+k, 2*k+1)`」。

### 実行コマンド(Windows / PowerShell or Bash)

```bash
PYTHONUTF8=1 PYTHONIOENCODING=utf-8 python build_revised.py
```

### 検証(必須)

ビルド後、出力pptxを python-pptx で読み戻して以下を確認:

- スライド数が原本×2 になっている
- 偶数番(2, 4, 6, ...)に「修正後」ワッペンが入っている
- 全角丸括弧 `（）` が残っていない(タイトル除外を確認した上で)
- 承認必須項目の Before→After が反映されている
- [MISS] ログが出ていれば、なぜミスしたか調査(大概はエンコーディング不一致 or 上位パターンに包含済み)

---

## 6. 作業完了時チェックリスト

- [ ] `Input/` から元ファイルを移動済み(コピーではない)
- [ ] 資料名のフォルダに修正前/修正後の両方が入っている
- [ ] スライド構成が「修正前→修正後」の交互配置になっている
- [ ] 修正後スライドの右上に「修正後」ワッペンが入っている
- [ ] タイトルを書き換えていない(全スライドで一致確認)
- [ ] フォント・サイズ・色・配置が変わっていない
- [ ] 承認不要カテゴリ(誤字脱字・括弧半角化等)が全て反映済み
- [ ] 承認必須カテゴリは Before/After 提示 → 承認 → 反映 の手順を踏んでいる
- [ ] [MISS] ログがあれば原因を説明済み
- [ ] 出力pptxを python-pptx でテキスト再抽出して目視確認した

---

## 7. ナレッジ追加ルール

このファイルは作業の都度進化させる。**毎セッション完了時に以下を確認**:

1. **新しい修正観点**: 修正カテゴリ表に追加すべき観点があったか?
2. **技術的な落とし穴**: 今回ハマったポイントを「4. 技術的な落とし穴」に追加
3. **テンプレートの改善**: ビルドスクリプトの雛形に組み込むべき改善はあるか?
4. **改訂履歴**: 末尾に1行追記(日付 + 変更概要)

---

## 改訂履歴

- 2026-05-14: 初版作成(フォルダ運用ルール・修正方針の骨子)
- 2026-05-14: 修正観点を拡充(きれいな日本語化、語彙統一、敬体常体統一、表記ゆれ、括弧半角化など)
- 2026-05-14: Before/After 提示時の項番付与ルールを追加
- 2026-05-14: 第1回実案件(開発課題検討会_20260518)を実施。以下のナレッジを追加:
  - 文字化け対策(markitdownは使用不可、PYTHONUTF8環境変数必須)
  - 原本の文字エンコーディング調査の重要性(全角コロン・全角ブラケット・全角数字が混在)
  - 「括弧以外の体裁(コロン・ブラケット・数字)は原本を尊重」のルールを明文化
  - 置換順序(パレン変換→特定置換)の明確化
  - run単位置換・スライド複製・並べ替えの実装パターンをコードテンプレート化
  - 標準ビルドスクリプトのテンプレートを掲載
  - 検証手順・チェックリストを拡充
