# verify-guide.md — 検証・品質チェック詳細

## 実行コマンド（Step 9）

```bash
# $PY と <SKILL_DIR> は SKILL.md の Setup 参照
$PY <SKILL_DIR>/scripts/grammar_check.py outline.json        # 描画前（構成・文言・容量）
$PY <SKILL_DIR>/scripts/brand_check.py output.pptx --theme <theme>
$PY <SKILL_DIR>/scripts/verify_pptx.py output.pptx
$PY <SKILL_DIR>/scripts/thumbnail.py output.pptx slides/

# プレースホルダーヒントテキストの最終確認
$PY -m markitdown output.pptx
# "タイトルを入力", "Place subtitle here" 等が出たらスクリプトを修正
```

ERRORは全て修正。WARNINGは内容を確認して判断。

### v6.9 で足した検査

| 規則 | どこで | 内容と直し方 |
|---|---|---|
| FONT-01 | verify_pptx | 全体が日本語なら Meiryo UI、英語なら Graphik 以外の書体（欧文・和文）が残っている → `unify_fonts.py`（build_deck は自動） |
| STAMP-01 | grammar_check（ERROR） | 成果物・画面の見本ではないページに V-STAMP → 外す。試算は `source` に前提を書く |
| DAT-09 | grammar_check | illustrative なのに `source` に試算の前提が無い |
| MSG-14 / MSG-15 | grammar_check | メッセージの改行（ERROR）／「左に〜」「下表の通り」の構成説明 |
| DATE-00〜03 | grammar_check | `as_of`・`anchors` が無い／実績が題材の開始日より前・作成日より後（ERROR）／計画が作成日より前 |
| DENS-02 | grammar_check | 提案書・報告書（本文 10 枚以上）に density max の詳細ページが無い（ERROR）・少ない |
| TBL-01 / NUM-01 | grammar_check | 表の曖昧な列名／桁区切りの無い 4 桁以上の数 |

---

## brand_check.py — チェック内容

| チェック項目 | 内容 |
|------------|------|
| カバーロゴ | マスターから提供されているか |
| 丸角図形 | roundRect が使われていないか |
| カラーパレット | 承認済みカラーのみ使用しているか |
| フォントサイズ | 12pt 未満の文字がないか |
| オーバーフロー | テキストがボックスからはみ出していないか |
| ヘッドライン | Sentence case になっているか |
| **コントラスト** | WCAG コントラスト比をチェック |

**コントラストチェック詳細:**
- 全スライドの全テキストについて、スライド背景色（slide → layout → master の順に解決）との WCAG コントラスト比を算出
- **ratio < 2.0** → ERROR（ほぼ不可視。白背景に白文字など）
- **ratio < 3.0** → WARNING（カバー/閉じスライドのみ。読みにくい）
- 背景色が解決できない場合は白 (#FFFFFF) と仮定する

---

## verify_pptx.py — チェック内容

| チェック項目 | 内容 |
|------------|------|
| ヒントテキスト残留 | 「タイトルを入力」「Place subtitle here」等を正規表現で検出 → ERROR |
| フォントサイズ | 各テキストの pt サイズ |
| オーバーフロー | テキストのはみ出し |
| 重複 | 図形の重なり |
| フッター | `set_footer()` が呼ばれているか |
| **縦クリッピング** | CJK/ASCII 混在対応の行数推定。+8% → WARN、+20% → FAIL |
| **横オーバーフロー** | 2パターンを検出（下記参照） |
| レイアウト密度 | テーブル/チャートが CW の 80% 未満なら WARNING |

**横オーバーフロー (Check 6) 詳細:**
- `word_wrap=False` のボックス: 推定テキスト幅がボックス幅を 10% 超えたら FAIL
- カード境界超え: textbox の右端が周囲のコンテナシェイプの右端を超えたら FAIL → テキストが隣カードに食み出すパターンを捕捉

---

## 目視確認チェックリスト（9b の評価と併せて自分でも thumbnail を確認）

`slides/slide_NN.png` を Read ツールで読み、以下を確認:

- [ ] **Cover: 背景色とテキスト色のコントラストが十分か**（白背景→BLACK文字、紫背景→WHITE文字）
- [ ] Cover: logo, GT symbol がマスターから提供されている
- [ ] Content slides: white bg, BLACK title, small GT bottom-right
- [ ] **プレースホルダーヒントテキストが残っていないか**（「タイトルを入力」「Place subtitle here」等）
- [ ] **メッセージライン: 全コンテンツスライド（カバー・アジェンダ除く）に表示されている**
- [ ] **メッセージライン: タイトル直下・DARK_PURPLE色・18pt・コンテンツと重なっていない**
- [ ] Purple accent bars visible on panels/cards
- [ ] No rounded rectangles anywhere
- [ ] Text not clipped, generous whitespace
- [ ] Sentence case headlines
- [ ] Body text >= 14pt, captions >= 12pt
- [ ] Charts: theme palette applied, axis labels readable
- [ ] Icons: visible and properly labeled

問題があれば修正し、verify を再実行すること。