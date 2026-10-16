# retheme.py — テーマ移行の内部仕様

## レイアウトタイプ判定ルール

ソースの `slide_layout.name` にキーワードが含まれるかを見てタイプを推定する（名前でマッチしない場合はすべて "content"）。移行先（destination）は プレースホルダー **型**（`placeholder_format.type`）の構造で判定するためテンプレート名・言語に依存しない。

| タイプ | ソース判定キーワード（例） | 移行先構造条件 | 選ばれるレイアウト例（ACN） |
|--------|--------------------------|---------------|---------------------------|
| cover | cover / 表紙 / タイトルスライド / title slide | CENTER_TITLE (type=3) + SUBTITLE (type=4) を持つ | `Title: White3+Image` (idx=0) |
| section | section / セクション / divider / chapter / 区切り | CENTER_TITLE を持ち SUBTITLE を持たない | `Title Master: White` (idx=6) |
| content | （上記いずれにも一致しない場合） | 段階的フォールバック（下記参照） | `3_Blank - Light` (idx=2) |
| blank | blank / 空白 | content にフォールバック | 同上 |

### content レイアウトの段階的フォールバック（2026-03-17 改修）

テンプレート間でプレースホルダー構造が大きく異なる場合（例: ACN → BCG）、従来の完全一致では適切なレイアウトが見つからず、装飾要素の多いレイアウトにフォールバックしてレイアウトが崩壊する問題があった。

現在の判定優先順位:

| 優先度 | 条件 | 例 |
|--------|------|-----|
| 1（最優先）| TITLE + BODY + footer idx=20/21 | ACN `3_Blank - Light` |
| 2 | TITLE のみ（CENTER_TITLE/SUBTITLE/BODY なし、最少ph数優先） | BCG `Title Only` |
| 3 | TITLE + BODY（footer なし） | BCG `4_Title and Text` |
| 4（最終）| idx=1 のレイアウト（ハードコードフォールバック） | — |

**設計原則**: リテーマはレイアウトを可能な限り元のまま維持する。色・フォント・マスターのみを変更し、コンテンツの配置は崩さない。最もクリーンなキャンバス（"Title Only" 相当）を優先することで、元のスライドの図形配置をそのまま保持できる。

## コンテンツスライドのプレースホルダー移植方針

| placeholder | 方針 | 理由 |
|------------|------|------|
| idx=0 (title) | 移行先 idx=0 へ直接コピー | テンプレート共通・位置が同じ |
| idx=11 (message line / breadcrumb) | **free-floating textbox** として元の座標で移植 | Fiori では msg line が idx=11 配置だが ACN の idx=11 はブレッドクラム（y=0.08"）と位置が異なるため |
| idx=10 (body) | free-floating textbox として移植 | Fiori のボディ位置が ACN と異なる場合があるため |
| 上記以外の未マッチ idx | free-floating textbox として移植 | テンプレート固有の配置を保持 |

## 処理ステップ一覧

| ステップ | 内容 |
|----------|------|
| カラーマップ構築 | 旧テーマの tokens hex → 新テーマの tokens hex の対応表を作成（token 名が一致するもの）|
| スライドタイプ自動判定 | 移行先レイアウトをプレースホルダー型で判定。レイアウト名が異なるテンプレート間でも正しくマッピングされる |
| スライドマスター差し替え | 新テンプレート PPTX を土台にし、旧スライドの図形・画像を移植 |
| プレースホルダー位置保持 | 移行先に存在しない idx の placeholder は `p:ph` を除去して free-floating textbox として元の座標に移植 |
| 空 placeholder 除去 | コンテンツのない placeholder を削除し「タイトルを入力」等のヒントテキスト表示を防止 |
| schemeClr 解決 | 旧テーマの schemeClr（テーマスロット参照＋lumMod/tint 等の HLS 修飾）を実 hex に変換してから色置換を適用 |
| 色の一括置換 | 全スライドの `srgbClr` 要素を color_map に従って置換（図形塗り・テキスト色・線色） |
| 画像リレーション維持 | icon PNG 等の `r:embed` rId を新スライドに引き継ぐ |

## master_to_theme.py — 色抽出の内部仕様（デバッグ参考）

`master_to_theme.py` はテンプレート PPTX からカラートークンを抽出するスクリプト。色がおかしいと感じたら以下を参照。

| 仕様 | 内容 |
|------|------|
| **走査方式** | `fill.fore_color.rgb`（python-pptx API）は使わない。`schemeClr` 参照に対して `AttributeError` を silently raise するため、Fiori・SAP 系テンプレートでは色が1件も拾えない |
| **schemeClr 解決** | `_build_theme_map` でマスターテーマ XML から slot → hex を構築し、`lumMod`/`lumOff`/`shade`/`tint` モディファイアを **HLS 色空間**で適用して実際の表示色を算出 |
| **Namespace 非依存走査** | `element.iter(f"{NS_A}solidFill")` で全 solidFill を取得。`element.findall(".//a:sp")` は `p:sp`（PresentationML）ネームスペースを見落とすため使わない |
| **text_body / text_muted 選択基準** | 彩度 `< 0.20` のグレー系のみ選択。アクセント色・警告色がテキストに使われていても body/muted トークンには混入しない |

再実行コマンド: `$PY <SKILL_DIR>/scripts/master_to_theme.py <file.pptx> "テーマ名"`（保存先は ~/.acnpptx/themes/）

## テンプレート準備（新テーマ登録時の注意）

外部プレゼンテーション（他社テンプレート等）をテーマとして登録する場合、元ファイルにコンテンツスライドが含まれていることがある。retheme.py は新テンプレートの既存スライドをクリアしてからコンテンツを移植するが、**マスターPPTXはコンテンツスライドを含まないクリーン版を用意すべき**。

```python
# クリーンマスター作成手順
from pptx import Presentation
from pptx.oxml.ns import qn
prs = Presentation("original_template.pptx")
while len(prs.slides) > 0:
    sldId = prs.slides._sldIdLst[0]
    prs.part.drop_rel(sldId.get(qn("r:id")))
    del prs.slides._sldIdLst[0]
prs.save("template-clean.pptx")
```

theme JSON の `template` フィールドはクリーン版を指すようにすること。

## ZIP 重複メディアエントリの修復

retheme.py 実行後に `Duplicate name: 'ppt/media/imageXX.png'` 警告が出た場合、PowerPoint COM がファイルを開けなくなることがある。以下のスクリプトで修復する:

```python
import zipfile, io
src = "rethemed.pptx"
seen = set(); buf = io.BytesIO()
with zipfile.ZipFile(src, 'r') as zin, zipfile.ZipFile(buf, 'w', zipfile.ZIP_DEFLATED) as zout:
    for item in zin.infolist():
        if item.filename not in seen:
            seen.add(item.filename)
            zout.writestr(item, zin.read(item.filename))
with open(src, 'wb') as f:
    f.write(buf.getvalue())
```

**retheme 実行後は必ず thumbnail.py でファイルが開けることを確認すること。** COM エラーが出た場合は上記の修復を適用する。

## 制限事項

- チャート内部の色は置換されない（コンテンツとして保持はされる）
- 新マスターの背景色が旧マスターと大きく異なる場合（白↔紫）、テキスト色が視認できなくなることがある → thumbnail で確認して手動修正
- セクション区切りスライドが旧テーマにある場合、ソース側でキーワードを含まないレイアウト名だと "content" として扱われる。その場合は手動でスライドを修正するか、ソースのレイアウト名を事前に確認すること
