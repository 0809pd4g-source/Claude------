# Antigravity 立ち上げ指示プロンプト

Claude Code で運用している「プロジェクト管理＋業務AIエージェント」の仕組みを、**Google Antigravity の独立ワークスペース**（例：`Downloads/Antigravityプロジェクト/`）に立ち上げるための指示プロンプト。
`Gemini移行チェック_プロンプト.md`／`Antigravity移行チェック_プロンプト.md` で再現可否を確認済みの前提。

## 渡し方（2系統）
1. **先にファイルをコピー**（AI非依存の共有資産。作り直させない）
   - `_agent/_基盤/_ツール/html_checker.py` `md_checker.py` `容量整理.py` `プロジェクト一覧生成.py`（＋必要なら他ツール）
   - `00_プロジェクトテンプレート/` 一式
   - 参考：Claude側の `CLAUDE.md` / `_agent/CLAUDE.md`（移植元として読ませる用）
2. **下の「===== ここから =====」〜「===== ここまで =====」をコピーして Antigravity のエージェントに貼る**（AGENTS.md・Workflows・Knowledge を組ませる）

（作成：2026-10-02。Antigravity仕様＝AGENTS.md/.agents/rules・Workflows・Knowledge Items・Skills・**1ファイル12,000字上限**・ネイティブbrowser検証 に基づく。実行前に最新ドキュメントで記法確認。）

===== ここから =====

# 依頼
私は別のエージェント「Claude Code」で、プロジェクト管理規約＋業務AIエージェントとしてリポジトリを運用しています。**まったく同じ運用を、この Antigravity ワークスペースで立ち上げてください。** フォルダ規約・管理文書・Pythonチェッカーは共通資産として流用します（別途コピー済み）。

## 0. まず調査（いきなり作らない）
- 参考として置いた移植元 `CLAUDE.md` / `_agent/CLAUDE.md` を読み、再現すべきルールを把握する。
- このワークスペースの現状（既存の `AGENTS.md`・`_agent/`・`業務情報.md`・コピー済みの `_agent/_基盤/_ツール/*.py`・`00_プロジェクトテンプレート/`）を確認する。
- そのうえで作成計画を提示し、私の承認を得てから作る。

## 1. Claude Code → Antigravity 機構対応表（この対応で再現）
| Claude Code | Antigravity での実現 |
|---|---|
| `CLAUDE.md`（自動読込・階層） | ルート `AGENTS.md`（＋ `.agents/rules/`）。**1ファイル12,000字上限**に注意 |
| `_agent/CLAUDE.md`（下位ルール） | `_agent/AGENTS.md`（サブディレクトリのルール） |
| 冗長なHTML作業ルール・検証プロトコル | **Skill（SKILL.md）**に切り出し、HTML作業時だけロード（上限対策＋コンテキスト効率） |
| スラッシュコマンド（/ship 等） | **Workflow**（定型手順。`/` で起動） |
| セッション横断の自動recallメモリ | **Knowledge Items**。恒久知識は `業務情報.md` 等のgit内MDを正本にしKnowledge登録 |
| ブラウザ統合テスト（launch.json+手動） | **ネイティブのbrowser操作＋Artifacts（スクショ/録画）**で自己検証（上位互換） |
| html_checker.py / md_checker.py / 容量整理.py | **そのまま流用**（ターミナルで実行） |

## 2. 作ってほしいもの
### (A) ルート `AGENTS.md`（12,000字以内・核だけ）
- フォルダ構成：コンテナ＝1 gitリポジトリ。各プロジェクト `YYYYMMDD_プロジェクト名/`（`01_input/ 02_output/ 03_scripts/ 04_reference/` ＋ `プロジェクト状況.md` ＋ `更新履歴.md`）。直下に `00_プロジェクトテンプレート/`・`_agent/`・`_archive/`。
- 命名・版管理：成果物＝`YYYYMMDD_名称_vN.拡張子`。旧版はgit履歴に委ね作業ツリーは最新＋確定版。最新は `更新履歴.md` で明示。
- 管理文書2点の役割分担：`更新履歴.md`＝版の台帳（表）、`プロジェクト状況.md`＝意思決定・進捗（文章）。二重記載しない。
- **情報の正本マップ**（二重管理防止）：情報ごとに正本を1つに固定。横断の恒久知識の正本＝**Knowledge Items ＋ `業務情報.md`（git内MD）**。Project決定→`プロジェクト状況.md`／版→`更新履歴.md`／当日の迷い→`daily/`／タスク→`tasks_current.md`／横展開知見→`ルール候補.md`。
- 2ユースケース：A=壁打ち→整理、B=作成依頼→成果物。**壁打ち救済**＝成果物なしで終わる壁打ちでも、結論・決定・前提・知見が出たか確認し正本へ最小反映（新規ファイルを作らない／未確定は確定保存しない／価値なしは保存しない）。
- セッション開始：既存は `プロジェクト状況.md`＋`更新履歴.md` を読む／新規はテンプレをコピー／冒頭で「プロジェクト・状況有無・モード」を宣言。
- セッション終了：`プロジェクト状況.md` 変更履歴を追記／成果物を出したら `更新履歴.md` 更新。
- 記述原則：出典明記／事実と推論を区別／未確認を隠さない／絶対日付。
- 詳細（HTML作業・検証）は Skill に委譲する旨を1行で明記。

### (B) `_agent/AGENTS.md`（業務下位ルール・12,000字以内）
- **上位との関係（優先順位・昇格）**：ルート `AGENTS.md` を基盤に重ねて適用。追加が原則。同一項目を具体化する場合は業務版を使用。**業務固有ルールを上位へ勝手に逆流させない。横断で有用なら承認を得てから昇格**。
- 開始Step0（`tasks_current.md`・`残論点台帳.md`・直近daily確認）／タスク表示フォーマット・タグ／終了（活動ログ・daily）／業務の参照先。
- Knowledge管理ルール（確定＝`業務情報.md`へ反映／未確定＝確定保存しない／重複記載しない／保存先を簡潔に報告）。

### (C) Skill「html-work」（SKILL.md）
- HTML作業ルール（単一ファイル・外部依存なし・色はCSS変数・版番号JS定数1箇所・差分編集・版フォルダ方式）と、3層検証（静的＝`python _agent/_基盤/_ツール/html_checker.py`、ブラウザ＝Antigravityネイティブでコンソール0/スクショ/ダーク・モバイル、計算系＝スモークテスト）。
- HTML作成・改訂タスクのときだけロードされるようにする。

### (D) Workflows
- `new-project`（テンプレ複製で初期化）／`ship`（版上げ＋管理文書2点更新。前に md_checker/html_checker 実行しFAIL0）／`status`（状況要約）／`review-rules`（`ルール候補.md` 棚卸し）。

### (E) Knowledge 初期化
- `業務情報.md` を横断恒久知識の正本とし、主要な確定事項（例：週次報告は毎週金曜作成）を登録。Knowledge Items として参照できるようにする。

## 3. 進め方・検証・制約
1. 調査結果と作成ファイル一覧・各要点を**先に提示**→承認後に作成。
2. 各 `AGENTS.md`/`SKILL.md` が**12,000字以内**かを数えて確認。超える分は Skill へ退避。
3. 作成後：`python _agent/_基盤/_ツール/md_checker.py <作ったAGENTS.md>` を実行（PASS確認）。Workflowsが `/` で出るか確認。
4. 最後に「Claude版との差分（できた/できない/代替した点）」を一覧で報告。
5. 制約：現行を壊さない／新規ファイル最小化（既存正本へ統合優先）／二重管理しない／恒久知識はAI非依存のMD・gitで保持／コンテキスト肥大化を避ける（詳細はSkillで必要時ロード）／Pythonチェッカーは再実装せず流用。

===== ここまで =====

## 使い方メモ
- 焦点は **(1) 12,000字上限 → 核はAGENTS.md、詳細はSkillへ分割**、**(2) スラッシュコマンド→Workflows**、**(3) メモリ→Knowledge/業務情報.md（git内MD）**、**(4) 検証はネイティブbrowserで上位互換**。
- すでに出来ている `AGENTS.md`＋`_agent/`＋`業務情報.md` はこの設計と整合するので、ゼロからではなく**不足分の追加**として進めさせるとよい。

## 参考リンク（2026-10-02確認）
- Rules(AGENTS.md)・12,000字上限: https://antigravity.google/docs/rules/ , https://thepromptshelf.dev/blog/google-antigravity-agents-md-rules-guide-2026/
- Skills/Workflows/Knowledge: https://iceberglakehouse.com/posts/2026-03-context-google-antigravity/
