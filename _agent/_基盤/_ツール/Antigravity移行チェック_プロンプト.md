# Antigravity移行チェック用プロンプト

このプロジェクト管理の運用が **Google Antigravity**（2025年11月公開のエージェント型IDE。Windsurfチーム由来。Gemini 3中心／Claude等も選択可・Agent Manager・Artifacts・ネイティブなブラウザ操作・Knowledge/Memory・ルールファイルを備える）で再現できるかを、Antigravity自身に判定させるためのプロンプト。
下の「===== ここから =====」〜「===== ここまで =====」をコピーして Antigravity のエージェントに貼り付けて使う。
（現行の `CLAUDE.md`／`README_プロジェクト管理規約.md` に合わせて作成：2026-09-28）

⚠️ **注意**: Antigravityの仕様は更新が速い。実際に使う前に最新の公式ドキュメントで用語・記法を確認すること。本プロンプトの想定用語＝**AGENTS.md/GEMINI.md（Rules）／Workflows（定型手順）／Knowledge Items（永続記憶）／Skills（SKILL.md）／Artifacts（計画・タスク・スクショ・ブラウザ記録）／Agent Manager／Lifecycle Hooks**。

## 裏付け（2026-09-28 Web確認・要点）
実際に移行するなら下記が効いてくる。詳細出典はファイル末尾「参考リンク」。
- **Rules**: `AGENTS.md` と `GEMINI.md` を Rules として読む。グローバル＝`~/.gemini/GEMINI.md`、ワークスペース＝`<project>/.agents/rules/`。**⚠️ RulesもWorkflowsも1ファイル12,000文字上限**。→ 現行 `CLAUDE.md` は超過するため**分割（規約/HTMLルール/検証プロトコル等）**が必須。
- **永続メモリ = Knowledge Items（KI）**。会話履歴と違い、蒸留・キュレーションされた事実として永続。Skills/KI/Artifacts の3本柱。→ 現行メモリ（`~/.claude/.../memory/`）は KI に移し替え可。
- **Workflows**（`/` で起動する定型プロンプト。`~/.gemini/antigravity/global_workflows/<NAME>.md` 等）→ `/new-project`・`/ship`・`/status` はここに移植。
- **Skills**（`SKILL.md`。グローバル`~/.gemini/antigravity/skills/`／WS`.agents/skills/`。必要時のみロード）→ 大きめの定型ノウハウはこちらが適する。
- **Lifecycle Hooks は存在する**（SDKの PreInvocation/PostInvocation）。PreInvocationで文脈を注入、PostInvocationで実行後処理・通知抑制。→ **当初「フックは不透明」と評したのは訂正。** ただし粒度は「セッション前後」寄りで、Claude Codeの「ツール実行ごと(PostToolUse)」と完全一致かは要確認。
- **ブラウザ自己検証はネイティブで上位互換**：サーバ起動→Chrome操作→クリック→スクショ＋録画→検証ウォークスルーを自律実行し **Artifacts** に残す。→ Layer2検証が標準機能。

===== ここから =====

# 依頼
私はエージェント型のコーディング/文書作成環境「Claude Code」で、成果物プロジェクトを一定の規約で管理しています。まったく同じ運用を、あなた（**Google Antigravity**）で再現できるかを判定してください。

各「仕組み」について、必ず次の4点を答えること：
(a) Antigravity に同等機能はあるか（Yes / 部分的 / No）
(b) あるなら具体的な設定方法（ルール/設定ファイルの場所・形式、Workflowの記法、コマンド名、UI操作）
(c) Claude Code との差異・制約
(d) 無い/弱い場合の最も近い代替手段
※ Antigravity固有の用語（AGENTS.md・Workflows・Knowledge/Memory・Artifacts・Agent Manager 等）に対応づけて答えること。用語が実在しない場合は「その名称は無い」と明記し、正しい名称を示すこと。

## A. 管理規約（この運用自体を再現できるかも判定して）
- 全プロジェクトを1つのコンテナフォルダ（＝**1つの git リポジトリ**）に集約。
- 各プロジェクト = フォルダ `YYYYMMDD_プロジェクト名/`。直下は英語名で固定：
  - `01_input/`（入力原本・改変しない）／`02_output/`（成果物）／`03_scripts/`（スクリプト）／`04_reference/`（任意）
  - ＋ 管理文書2つ：`プロジェクト状況.md`（目的・前提・論点/スコープ・成果物・未確認事項・変更履歴）と `更新履歴.md`（成果物の版一覧の表。最新版は「太字＋（最新）」で明示）
- 成果物ファイル = `YYYYMMDD_名称_vN.拡張子`。改訂ごとに vN を +1、旧版は削除せず残す。試作は `02_output/_wip/` に隔離。
- コンテナ直下に `00_プロジェクトテンプレート/`（雛形）・`_agent/_基盤/_ツール/`（横断ツール）・`_agent/_基盤/_input/`（横断参照資料）・`_archive/`（統合済み/凍結プロジェクト）を置く。
- 記述原則：出典・根拠を明記／事実と推論を区別／未確認事項を隠さない／日付は絶対日付。
- 成果物の形式は目的から選ぶ（HTML/MD/PDF/xlsx/pptx/docx）。「とりあえずHTML」にせず、迷えばMDで中身を固めてから必要な形式へ展開（中身ファースト）。
- 容量管理：旧版は git 履歴で保全し、作業ツリー(`02_output`)は最新＋確定版のみ。中間版の間引き・重複バイナリ排除・`git gc` を再利用スクリプト（`_agent/_基盤/_ツール/`）で回す。

## B. 再現したい「仕組み」
1. **自動読み込みの前提指示ファイル**：フォルダ階層に置いた指示ファイル（Claude Codeでは `CLAUDE.md`）を、そのフォルダで作業するたびに自動で文脈に読み込む（規約・命名・振る舞い）。Antigravity の相当（**AGENTS.md／ワークスペースRules**？）と、親→子への階層的マージ挙動、参照される文字数/範囲の上限は？長い規約（数百行）はそのまま読ませられるか、分割が要るか？
2. **セッションをまたぐ永続メモリ**：ユーザーの好み・運用ルールを保存し、次回以降のセッションで自動的に思い出す。Antigravity の **Knowledge/Memory** の保存先・記法・自動想起の条件・手動追加の方法は？プロジェクト単位とグローバルの区別はあるか？
3. **カスタム・定型コマンド（Workflows）**：定型作業をコマンド化。例）
   - `/new-project <名称>`：テンプレ一式をコピーして新規プロジェクトを初期化
   - `/ship <ファイル>`：版を vN+1 に上げ、管理文書2点を自動更新
   - `/status`：管理文書から現在の状況を要約
   Antigravity での定義方法（**Workflow ファイルの置き場所・形式（.md 等）・呼び出し方・引数の渡し方**）は？Claude Code のスラッシュコマンドと1対1で対応づくか？
4. **イベントフック（最重要の確認点）**：ファイル編集後に、条件（例：パスに `02_output` を含む）に応じて「管理文書2点を更新して」というリマインドを自動で差し込む（Claude Code の PostToolUse フック）。Antigravity に同等の「ツール/編集の前後で任意コマンドを走らせる」フック機構はあるか？無ければ最も近い代替（Workflowsの必須ステップ化・Rulesへの明文化・拡張・MCP等）は？
5. **ファイル操作・シェル・git**：フォルダ作成、ファイルの移動/リネーム、`git init`・コミットをエージェント自身が実行できるか。実行時の承認（許可）モデル、および Agent Manager での複数エージェント並列実行の可否は？
6. **大きな単一HTML成果物の安全な改訂**：数千行・1MB級の単一HTML（CSS/JS/データを1ファイル内包・外部依存なし）を、**全体書き直しせず差分（部分置換）で**安全に編集できるか。トークン上限・部分編集ツールの有無・大規模ファイルでの精度は？
7. **ブラウザによる自己検証（Antigravityの強み確認）**：作った単一HTMLを**エージェント自身がブラウザで開いて検証**できるか。具体的に、(i) JSコンソールのエラー0件確認、(ii) 主要セクションの存在確認、(iii) スクリーンショット取得、(iv) ダーク/ライト・モバイル幅の切替確認、を **Artifacts（ブラウザ記録・スクショ）** として残せるか。`file://` 直開き可否、ローカルHTTP配信が要るかも明記。
8. **多形式の成果物生成**：目的に応じて出力形式を選ぶ運用のため、Markdown/HTML に加え **docx・pdf・pptx・xlsx** をエージェント自身が生成できるか（専用機能・ライブラリ実行の可否）。
9. **静的チェッカー（Pythonスクリプト）の実行**：`html_checker.py`（外部CDN依存・ID重複・内部リンク切れ等を検出）や `md_checker.py`（命名規約・見出し飛び・(最新)重複 等）を、**エージェントがターミナルで実行して合否を確認**できるか。これはモデル非依存のはずだが、ターミナル実行と結果の取り込みが自動で回るかを確認したい。

## C. 出力形式
1. 可否一覧表（列：仕組み / Antigravity相当 / 設定場所・記法 / 制約 / 代替）
2. 「ゼロから同じ運用を Antigravity で立ち上げる最短手順」（AGENTS.md・Workflow・Knowledge 登録の具体例つき）
3. 「Claude Code に比べてできない・弱い点」と「逆に Antigravity の方が得意な点」の明示

===== ここまで =====

## 使い方メモ
- 上の本文をコピーして Antigravity のエージェント（Agent Manager／チャット）に貼る。
- 焦点は **B-4（イベントフック）**・**B-6（大規模単一HTMLの差分編集）**・**B-7（ブラウザ自己検証＝Antigravityの強み）**・**B-9（Pythonチェッカーのターミナル実行）**。
  - 4は Claude Code 固有機能なので「代替（Workflow必須ステップ化／Rules明文化）」の質が焦点。
  - 7は Antigravity の方が上位互換になりやすい（ネイティブなブラウザ操作＋Artifacts記録）。ここが移行の主な利点。
  - 6・9は移植可否の実利き所。9のチェッカーはただのPythonなので本来モデル非依存＝移行の一番の資産。
- 回答は下に日付つきで追記していけば、Gemini版・ChatGPT版と横並びで比較できる。

## 回答ログ
<!-- Antigravityの回答をここに日付つきで貼る。例:
### 2026-MM-DD Antigravityの回答
（貼り付け）
-->

## 参考リンク（裏付け・2026-09-28確認）
- Rules（AGENTS.md/GEMINI.md・置き場所）: https://antigravity.google/docs/rules/
- Agent Overview: https://antigravity.google/docs/agent
- Screenshots/ブラウザ検証: https://antigravity.google/docs/screenshots/
- Lifecycle & hooks（Pre/PostInvocation）: https://antigravity.google/docs/sdk/lifecycle/
- 12,000字上限・Workflows/Skillsの置き場所（解説）: https://thepromptshelf.dev/blog/google-antigravity-agents-md-rules-guide-2026/
- Knowledge Items＝永続メモリ（3本柱: Skills/KI/Artifacts）: https://iceberglakehouse.com/posts/2026-03-context-google-antigravity/
- 公式ブログ（Artifacts=スクショ/録画で検証）: https://developers.googleblog.com/build-with-google-antigravity-our-new-agentic-development-platform/
