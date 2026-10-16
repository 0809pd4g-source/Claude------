# トラブルシューティング

## ERROR: 許可されていない場所への読み込み / 書き込みです
**原因:** スクリプトは、作業フォルダ（CWD）配下・`~/.acnpptx/`（または `ACNPPTX_DATA`）・スキル本体（読み取りのみ）の外のパスを受け付けない。
**対処:** 作業フォルダの外のファイルは作業フォルダにコピーしてから指定する。出力先は作業フォルダの中にする。`ACNPPTX_DATA` を使う場合は `~/.acnpptx` か作業フォルダの中を指定する。

## アイコン・イラストが見つからない / 素材の展開に失敗する
**原因:** 組み込みイラストは `assets/illustrations_*.zip` から `~/.acnpptx/cache/illustrations-<サイズ>/` へ初回に自動展開される。ディスク容量や書き込み権限が足りないと展開に失敗し、素材が使えない。`assets/illustrations_*.zip` を消した場合も見つからない。
**対処:** `~/.acnpptx/cache/illustrations-*` フォルダを削除して再実行する（次の素材検索で展開し直す）。`assets/illustrations_*.zip` が無ければスキルを入れ直す。保存先を変えたいときは環境変数 `ACNPPTX_DATA` を設定する。

## Error: Template file not found
**原因:** `TEMPLATE_PATH` が存在しないファイルを指している。
**対処:** `assets/slide-master.pptx` が存在するか確認する。または `helpers.py` の `TEMPLATE_PATH` を正しいパスに更新する。

## Warning: Layout sparse
**原因:** コンテンツが十分な垂直スペースを使用していない（verify_pptx チェック #7）。
**対処:** カード・テーブルの高さを動的計算で拡張: `h = AH - other_elements - gaps`。フォントサイズを上げるのではなく、チャートやフロー図を追加して密度を高める。

## Warning: Text may be clipped
**原因:** テキストボックスがコンテンツに対して小さすぎる（verify_pptx チェック #5）。
**対処:** シェイプの高さを増やす。目安: `min_h = lines × (font_pt / 72 × 1.4)`

## Footer/slidenum missing on content slides
**原因:** python-pptx はレイアウトからフッタープレースホルダーを自動継承しない。
**対処:** すべてのコンテンツスライドで `set_footer(slide)` を呼ぶ。これにより idx=20 と idx=21 がレイアウトからクローンされ、`FOOTER_TEXT` のテキストが設定される。会社名が間違っている場合は `helpers.py` の `FOOTER_TEXT` を更新する。

## PowerPoint COM で ERROR_FILE_CORRUPT (0x80070570)
**原因:** テキストボックスに負の高さが設定されている。テーブルが使用可能領域をほぼ全部使い切ると、下のテキストボックスの高さ計算が負になる。
**対処:** 高さ計算で `max(value, 0.20)` のガードを入れる。テーブル行高さを固定値にして tips テキストボックス用のスペースを確保する。

## プレースホルダーのヒントテキストが残留
**原因:** テンプレートの「タイトルを入力」「Click to add」等のテキストが上書きされていない。
**対処:** verify_pptx.py のチェック #0 で検出される。該当シェイプのテキストを実際のコンテンツで置き換える。

## テーブル/チャートの幅が狭い
**原因:** コンテンツ幅が CW (12.50") の 80% 未満。
**対処:** テーブル/チャートの幅を `w=CW` (12.50") に設定してフル幅を使う。
