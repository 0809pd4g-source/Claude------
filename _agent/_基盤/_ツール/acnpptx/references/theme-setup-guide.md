# theme-setup-guide.md — テーマ選択・設定の詳細ガイド

## テーマの決め方（確認ゲートなし）

- テーマは**最初の設定 Widget**（SKILL.md Step 1）でユーザーが選ぶ。届いた `【acnpptx設定】テーマ=<name>` の `<name>` をそのまま `load_theme()` に渡す。改めて確認しない
- 利用可能テーマ = 組み込み（`<SKILL_DIR>/assets/themes/*.json`）＋ユーザー追加（`~/.acnpptx/themes/*.json`）− 非表示リスト。一覧は `paths.list_themes()`
- **`theme_selector.py` / `select_theme()` は使わない**（Tkinter ダイアログは Claude Code から結果を取得できない）
- **`set_lang` → `load_theme` の順序厳守**（逆にすると `set_lang` が `TEMPLATE_PATH` を上書きする）
- レイアウト番号は固定値で書かず `layout_idx("cover" | "content" | "section" | "agenda" | "closing" | "cover_light" …)` で引く

---

## マスターの追加（Widget の「マスターを追加」→ `【acnpptxマスター追加】パス=…`）

1. テーマ名はファイル名から決める（ユーザーに聞かない）。同名があれば末尾に `-2` を付ける
2. 抽出（`~/.acnpptx/themes/<name>.json` と `~/.acnpptx/masters/<name>.pptx` に保存。スキル本体には書き込まない）:
   ```bash
   $PY <SKILL_DIR>/scripts/master_to_theme.py '<path/to/file.pptx>' '<name>'
   ```
   作業フォルダの外のファイルなら、先に作業フォルダへコピーしてそのパスを使う（スクリプトは作業フォルダ・`~/.acnpptx`・スキル本体の外を読まない）。パスは**単一引用符**で囲む。`.pptx` / `.potx` で終わる実在のファイルであることを確かめ、`'` `"` `$` `` ` `` `;` `|` `&` `<` `>` や改行を含むパスはコマンドに入れず、ユーザーにファイル名の変更を頼む。`<name>` は文字・数字・`-`・`_` だけにする（それ以外の記号はスクリプト側でも `-` に置き換えられる）
   `layout_indices`（cover / content / section / agenda / closing / cover_2…）はレイアウト名から自動推定される
3. プレビューを作る: `$PY <SKILL_DIR>/scripts/build_master_previews.py <name>`
4. 作ったプレビュー（`~/.acnpptx/master_previews/<name>/strip.jpg`）を Read で見て、表紙・本文の割り当てが不自然なら theme JSON の `layout_indices` を直して 3 をやり直す
5. Widget を作り直して再表示する（追加テーマが選択肢に入る）

## マスターの削除（Widget の「このマスターを削除」→ `【acnpptxマスター削除】テーマ=…`）

破壊的操作なので、ここだけは **AskUserQuestion で確認**してから実行する（「<name> を削除します。よろしいですか？」— はい / いいえ）。

- ユーザー追加テーマ: `~/.acnpptx/themes/<name>.json`・`~/.acnpptx/masters/<name>.pptx`・`~/.acnpptx/master_previews/<name>/` を削除
- 組み込みテーマ: ファイルは消さず非表示にする（`paths.set_hidden_themes(paths.hidden_themes() | {"<name>"})`）。プラグイン更新で復活しない
- 削除後に Widget を作り直して再表示する

**`master_to_theme.py` の仕組み:**

| 項目 | 内容 |
|------|------|
| 走査方式 | `fill.fore_color.rgb`（python-pptx API）は使わない — `schemeClr` 参照で AttributeError を silently raise するため Fiori・SAP 系では色が1件も拾えない |
| schemeClr 解決 | `_build_theme_map` でマスターテーマ XML から slot → hex を構築し、`lumMod`/`lumOff`/`shade`/`tint` モディファイアを HLS 色空間で適用して実際の表示色を算出 |
| Namespace 非依存 | `element.iter(f"{NS_A}solidFill")` で全 solidFill を取得 |
| text_body/text_muted | 彩度 < 0.20 のグレー系のみ選択 — アクセント色は混入しない |

---

## テーマ JSON の `layout_notes` を使ったレイアウト設定

theme JSON に以下のフィールドがある場合、スクリプト冒頭で必ず参照して定数を設定:

| JSON フィールド | 設定例 |
|----------------|--------|
| `layout_indices.cover` | `LAYOUT_COVER = theme_data["layout_indices"]["cover"]` |
| `layout_indices.content` | `LAYOUT_CONTENT = theme_data["layout_indices"]["content"]` |
| `layout_notes.content.content_area_y` | `CONTENT_Y = layout_notes["content"]["content_area_y"]`（未定義なら `CY=1.50"` を使う）|
| `layout_notes.cover.placeholders` | 表紙プレースホルダーの idx 割り当てを確認してから埋める |
| `cover_text_color` | `"BLACK"` なら全プレースホルダーを BLACK/MID_GRAY で埋める（白背景テーマでは WHITE は不可視）|
| `layout_notes.content.message_line_idx` | null なら `add_message_line()` を使う。数値なら該当 idx に直接書き込む |

```python
import json as _json
_theme_path = os.path.join(_SKILL, "..", "assets", "themes", "テーマ名.json")
with open(_theme_path) as _f:
    _td = _json.load(_f)
LAYOUT_COVER   = _td["layout_indices"]["cover"]
LAYOUT_CONTENT = _td["layout_indices"]["content"]
CONTENT_Y      = _td.get("layout_notes", {}).get("content", {}).get("content_area_y", CY)
_MSG_IDX       = _td.get("layout_notes", {}).get("content", {}).get("message_line_idx")
```