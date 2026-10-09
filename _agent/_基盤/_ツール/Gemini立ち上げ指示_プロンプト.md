# Gemini CLI 立ち上げ指示プロンプト

Claude Code で運用している「プロジェクト管理＋業務AIエージェント」の仕組みを、**Gemini CLI で同じリポジトリ上に立ち上げる**ための指示プロンプト。
`CLAUDE.md` を読む Claude と、`GEMINI.md` を読む Gemini は**同じリポジトリに共存できる**（フォルダ規約・管理文書・Pythonチェッカーは共通資産として流用）。

下の「===== ここから =====」〜「===== ここまで =====」をコピーして、対象リポジトリの直下で起動した **Gemini CLI** に貼り付ける。
（作成：2026-10-02。Gemini CLIの仕様＝GEMINI.md階層コンテキスト／`.gemini/commands/*.toml`カスタムコマンド／`/memory`／`settings.json` に基づく。実行前に最新のGemini CLIドキュメントで記法を確認すること。）

> 先に `Gemini移行チェック_プロンプト.md` で「再現可否」を確認してから本プロンプトで構築すると確実。

===== ここから =====

# 依頼
私はこのリポジトリを「Claude Code」で、プロジェクト管理規約＋業務AIエージェントとして運用しています。**まったく同じ運用を、あなた（Gemini CLI）でもこのリポジトリ上に立ち上げてください。** Claude用の `CLAUDE.md` はそのまま残し、Gemini用に `GEMINI.md` 等を新設して**共存**させます。フォルダ規約・管理文書・Pythonチェッカーは共通資産として流用します。

## 0. まず調査（いきなり作らない）
以下を読んで現状を把握してから、作成計画を提案し、私の承認を得てからファイルを作ってください。
- ルート `CLAUDE.md` / `_agent/CLAUDE.md`（再現すべきルール本体）
- `00_プロジェクトテンプレート/`（各プロジェクトの雛形）
- `_agent/` の構造（`_ツール/` `_input/` `_タスク管理/` `_log/` `_評価/` ＋ `01_定常業務〜06_その他`）
- `_agent/_基盤/_ツール/` の Python ツール（`html_checker.py` `md_checker.py` `容量整理.py` `プロジェクト一覧生成.py` 等）
- 既存の管理文書例（任意のプロジェクトの `プロジェクト状況.md` / `更新履歴.md`）

## 1. 作ってほしい成果物
1. **ルート `GEMINI.md`** … ワークスペース横断の共通ルール（下の #3 を反映）。Claudeの `CLAUDE.md` 相当。
2. **`_agent/GEMINI.md`** … 業務エージェント専用の下位ルール（`_agent/CLAUDE.md` 相当）。「上位との関係（優先順位・昇格）」も含める。
3. **`.gemini/commands/*.toml`** … スラッシュコマンド群（下の #4）。プロジェクト配下に置きgit管理する。
4. 必要なら **`.gemini/settings.json`** … コンテキストファイル名・ツール許可・MCP等の最小設定。

## 2. Claude Code → Gemini CLI 機構対応表（この対応で再現すること）
| Claude Code | Gemini CLI での実現 |
|---|---|
| `CLAUDE.md`（自動読込・階層） | `GEMINI.md`（階層コンテキスト。毎プロンプト連結送信。`@path` で分割import可） |
| `_agent/CLAUDE.md`（下位ルール） | `_agent/GEMINI.md`（サブディレクトリ階層のコンテキスト） |
| スラッシュコマンド（/new-project 等） | `.gemini/commands/<name>.toml`（`description`＋`prompt`、`{{args}}`、サブフォルダ→`:`名前空間） |
| セッション横断の自動recallメモリ | **該当なし。** 恒久知識はgit内MDに置く。`/memory`はGEMINI.md群の表示/再読込/追記であり、GEMINI.md自体がメモリ |
| html_checker.py / md_checker.py / 容量整理.py | **そのまま流用**（shellツールで同じコマンドを実行） |
| PostToolUseフック | 該当なし（元々未使用のため不要） |
※「GEMINI.md相当が無い/違う」等あれば、正しい名称・記法を明記して代替してください。

## 3. ルート `GEMINI.md` に入れる内容（CLAUDE.mdから移植）
- **フォルダ構成**：コンテナ＝1 gitリポジトリ。各プロジェクト `YYYYMMDD_プロジェクト名/`（`01_input/ 02_output/ 03_scripts/ 04_reference/` ＋ `プロジェクト状況.md` ＋ `更新履歴.md`）。直下に `00_プロジェクトテンプレート/`・`_agent/`・`_archive/`。
- **命名・版管理**：成果物＝`YYYYMMDD_名称_vN.拡張子`。改訂で vN+1、旧版はgit履歴に委ね作業ツリーは最新＋確定版。最新は `更新履歴.md` で明示。
- **管理文書2点の役割分担**：`更新履歴.md`＝版の台帳（表）、`プロジェクト状況.md`＝意思決定・進捗（文章）。二重記載しない。
- **情報の正本マップ**（二重管理防止）：情報ごとに正本を1つに固定。※Gemini版では「横断の恒久知識」の正本を **ルート `GEMINI.md`（恒久ルール）＋ 必要時grep参照するgit内MD**とする（Claudeのメモリ層の代替）。
  - Project固有の意思決定→`プロジェクト状況.md` ／ 版→`更新履歴.md` ／ 当日の迷い→`_agent/_基盤/_タスク管理/daily/` ／ タスク→`tasks_current.md` ／ 横展開知見→`_agent/_基盤/_ツール/ルール候補.md`。
- **2ユースケース**：A=壁打ち→整理（`02_output/..._v1.md`）、B=作成依頼→成果物。
  - **壁打ち救済**：成果物を作らず終わる壁打ちでも、結論・決定・前提・知見が出たか確認し、正本マップに従い既存正本へ**最小反映**（新規ファイルは作らない／未確定は確定保存しない／価値なしは保存しない）。
- **成果物の形式選定**：目的から先に選ぶ（読む→MD、見せる→単一HTML、配る→PDF、数える→xlsx…）。中身ファースト。
- **HTML作業ルール**：単一ファイル・外部依存なし／色はCSS変数／版番号はJS定数1箇所／既存は差分編集／相互リンクは版フォルダ方式。
- **検証プロトコル（/ship前）**：`python _agent/_基盤/_ツール/html_checker.py <file>` と `md_checker.py` を実行しFAIL0を確認（Pythonをそのまま流用）。
- **セッション開始**：既存プロジェクトなら `プロジェクト状況.md`＋`更新履歴.md` を読む／新規はテンプレをコピー／冒頭で「プロジェクト・状況有無・モード」を宣言。
- **セッション終了**：`プロジェクト状況.md` 変更履歴を追記／成果物を出したら `更新履歴.md` 更新。
- **容量管理**：中間版は間引き（git復元可）、`python _agent/_基盤/_ツール/容量整理.py --apply`。
- **記述原則**：出典明記／事実と推論を区別／未確認を隠さない／絶対日付。

## 4. `.gemini/commands/` に作るコマンド（prompt欄に手順を記述）
- `new-project.toml` … テンプレ一式を `YYYYMMDD_{{args}}/` にコピーして初期化。
- `ship.toml` … 対象ファイルを版上げ＋`更新履歴.md`/`プロジェクト状況.md`を更新。前に `md_checker.py`/`html_checker.py` を実行しFAIL0を確認。
- `status.toml` … `プロジェクト状況.md`/`更新履歴.md` から現状を要約。
- `review-rules.toml` … `_agent/_基盤/_ツール/ルール候補.md` を棚卸ししGEMINI.md/チェッカーへ昇格。
- （任意）`minutes.toml` `weekly.toml` `eval.toml` … Claude側スキル相当。
※各 `.toml` は `description`（1行）と `prompt`（複数行の手順。`{{args}}` で引数）だけでよい。

## 5. `_agent/GEMINI.md` に入れる内容（業務エージェント下位ルール）
- **上位との関係（優先順位・昇格）**：ルート `GEMINI.md` を基盤とし業務セッションで重ねて適用。追加が原則。同一項目を具体化する場合（宣言フォーマット等）は業務版を使用。**業務固有ルールを上位へ勝手に逆流させない。横断で有用なら承認を得てから昇格**。
- 開始Step0（`tasks_current.md`・`個人の残論点.md`（旧 残論点台帳.md）・直近daily確認）／タスク表示フォーマット・タグ／終了Step3-4（活動ログ・daily）／業務の参照先。

## 6. 進め方
1. #0 の調査結果を要約し、作成するファイル一覧と各中身の要点を**先に提示**。
2. 私の承認後にファイルを作成（既存の `CLAUDE.md` は変更しない）。
3. 作成後に検証：`/memory show`（GEMINI.md群が意図通り読めるか）、`/commands list`、`python _agent/_基盤/_ツール/md_checker.py <作ったGEMINI.md>` を実行。
4. 最後に「Claude版との差分（できる/できない/代替した点）」を一覧で報告。

## 7. 制約・優先順位
- 現行（Claude運用）を壊さない／新規ファイルを最小化（既存正本へ統合優先）／二重管理しない／恒久知識はAI非依存のMD・gitで保持／コンテキスト肥大化を避ける（巨大知識はGEMINI.mdに常駐させずgrep参照）／Pythonチェッカーは再実装せず流用。

===== ここまで =====

## 使い方メモ
- 対象リポジトリ直下で Gemini CLI を起動し、上の本文を貼る。
- 焦点は **(1) メモリ代替**（Claudeの自動recall層が無い＝横断知識はgit内MDへ）、**(2) スラッシュコマンドのTOML化**、**(3) Pythonチェッカーの流用**。
- Gemini の回答・生成物は、この下に日付つきで記録しておくと Claude版・ChatGPT版・Antigravity版と横並び比較できる。

## 参考リンク（2026-10-02確認）
- GEMINI.md コンテキスト: https://geminicli.com/docs/cli/gemini-md/
- カスタムコマンド(TOML): https://cloud.google.com/blog/topics/developers-practitioners/gemini-cli-custom-slash-commands
- /memory・設定: https://geminicli.com/docs/reference/configuration/
