# grammar-guide.md — デザイン文法でアウトラインを決める

スライドを「1 枚 = 1 パターン」ではなく **部品 × 配置 × 関係記号 × 締め（＋ナビ表現）** の組み合わせとして決める。
語彙と規則は実物デッキ 25 本・本文 906 枚の分析から作った `grammar/*.json` にある（実例への参照は除去済み）。

| ファイル | 中身 |
|---|---|
| `layouts.json` | 配置 21（G-1, G-11, G-RH …）定義・使う場面・避ける場面・容量 |
| `modules.json` | 部品 63（M-BULLETS, M-ROWHEAD …）同上＋`capacity`（数値）＋`accepts_images` |
| `connectors.json` / `devices.json` / `closings.json` | 関係記号 18 / ナビ表現 16 / 締め 17 |
| `rules.json` | 作成ルール・NG パターン・組み合わせ OK/NG・図解の型。`checked_by` で検査担当がわかる |
| `intent_map.json` | 意図 35 → 候補パターンの順位（条件: relation / materials / density） |
| `compositions.json` | 構成パターン P-001〜080（観測）・P-101〜136（提案）、デッキ横断の型 S-01〜17、ストーリー型 T-01〜08 |
| `presets.json` | 旧パターン A〜AN を組み合わせとして再定義したもの |

## 手順（Step 3 で行う。ユーザーには見せない・聞かない）

1. **ストーリー型を決める**: 【acnpptx設定】のデッキ種類（T-01〜08）。おまかせなら依頼内容から最も近いものを選ぶ。`compositions.json` の `story_templates[].chapters` を章立ての下敷きにする
2. **1 枚ずつ役割を決める**: `role` / `intent` / `relations` / `materials` / `density` を書く（中身の文言はまだ粗くてよい）
   - intent は `intent_map.json` のキーから選ぶ（例: overview, framework, problem_solution, phases, comparison, fact_to_insight, howto, architecture, schedule, case, summary, request …）
   - materials は**手元にある素材だけ**（記事から数値が取れたら numbers、図解するなら diagram、アイコンを使うなら icons）
3. **候補を出してデッキ全体で選ぶ**: `grammar_select.py outline.json --out candidates.json`
   - 各スライドの上位 3 候補と選択結果、使えそうなデッキ横断の型が出る
   - 選択は「意図との一致」＋「同じパターンの再使用・隣接の同一配置へのペナルティ（variation で強さが変わる）」
   - Claude が最終決定する。候補の `summary` と `cautions`（CB-/NG-）を読み、中身に合わないものは 2・3 位に替える
4. **デッキ横断の型を入れる**（本文 8 枚以上なら最低 1 つ）: 例
   - S-01 全体図 → スコープ枠 → 詳細ズーム（全体像のスライドを縮小再掲し V-SCOPE で範囲を示してから各論）
   - S-02 同型 2 枚組（課題 / 解決を同じ構造の鏡像で）
   - S-03 全体像の番号を索引にして各論へ（V-INDEX の番号を後続スライドの見出しに使う）
   - S-08 現在地ナビ（章ごとに全体工程を再掲＋ハイライト、V-NAVTAB）
   採用したら outline の `sequences` に `{"id", "slides": [番号…]}` で記録する
5. **骨格を書き込む**: `grammar_select.py outline.json --apply` で、選んだパターンの grid / panes(module) / connectors / closing / devices が空のスライドに入る。中身（文言・項目・数値・画像指定）を [compose-api.md](compose-api.md) の形で書く
6. **描画前チェック**: `grammar_check.py outline.json`。ERROR は必ず直す。WARN は理由があれば残してよい（理由をメモ）

## 選び方の勘所

- **関係記号は関係があるときだけ**: 並列なら記号なし（R-PAR）、因果・変化は →、課題→解決は ⇒、合算は ＋。並列に矢印は CB-01
- **結論は全幅で締める**: 複数ペインの根拠 → C-CONCLUSION（CB-13）。片側だけの結論バーは CB-12
- **比較は鏡像**: 左右で同じ部品・同じ項目数（CB-08 / LAY-07）
- **箇条書きだけにしない**: M-BULLETS 単独は CB-34。行見出し（M-ROWHEAD）やカード（M-CARDSTACK）に分ける
- **リズム**: 密度 high の後に low（キーメッセージ・図解）を挟む。同じ配置を 2 枚続けない（DEC-08）
- **バリエーション設定**: 統一感重視 = 同じ型の再利用を許す（重複率 60% まで）、バランス = 40% まで、多彩 = 25% まで（grammar_check の DIVERSITY）

## 画像を使う部品

`modules.json` の `accepts_images` が付いた部品（M-ICONGRID, M-ILLUST, M-PHOTO, M-SCREEN, M-FIGREF, M-CARD・M-BADGECOL・M-HEADCOL の icon など）に画像を入れる。優先順位と探し方は SKILL.md の「画像と作図」を参照。

## 旧パターン（A〜AN）との関係

`presets.json` に対応表がある（例: K = G-N3 × M-HEADCOL×3、T = G-11 × M-CARDSTACK×2 × R-SOLVE、U = G-N3 × M-BADGECOL×3 × C-CONCLUSION）。
旧パターンの部品はすべて compose で描ける。人物カード（N・AM）・成熟度（Z）・2 軸（AA）・ピラミッド（AC）・ベン図（AE）・構成図（AG）・カレンダー（AK）・ビジネスモデルキャンバス（AL）は `diagrams.py` の M-PROFILE / M-ROADMAP / M-2AXIS / M-PYRAMID / M-VENN / M-ARCH / M-TILEMAP（data の形は compose-api.md）。
