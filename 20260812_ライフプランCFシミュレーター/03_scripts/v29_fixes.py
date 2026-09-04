# -*- coding: utf-8 -*-
r"""v29：ChatGPT版のv28レビューで挙がった5件のうち、**実在した2件**を直す。

**A｜案内が「まず6つの質問」のまま（テストID `wizard.not_six`）— 実在した。**

  セットアップに入る前の案内が、v25の6ステップ時代のまま残っていた：

      「はじめて使う方は、まず6つの質問に答えてください。
        世帯・収入・いまの資産・住まい・生活費・気になることを順に聞きます。」

  実体は**入力7＋確認1の8ステップ**で、v26で足した**長期前提が案内に無い**。

  ★これは**こちらがV76〜V80へ5版にわたって指摘してきたのと同じ型**（案内と実体のずれ）。
    しかも v26 で入れた `checkWizardCoverage()` は
    `WIZ_STEPS[].covers` と `READY_STEPS` を突き合わせるだけで、
    **利用者を招き入れる文章そのものを一度も見ていなかった。**
    「案内と要求を別々に書いた瞬間からずれ始める」と書いておいて、
    **案内文を手書きのまま残していた。**

  直し方：**案内文を `WIZ_STEPS` から組み立てる**（件数も項目名も実体から引く）。
  さらに `checkWizardWording()` で、案内文に出る件数・項目名が
  `WIZ_STEPS` と一致するかを機械で確かめる。

**B｜保存に失敗したときに保存領域を元へ戻していない（テストID `save.rollback`）— 実在した。**

  v28は read-after-write の不一致を検出して `PLANS` を触らずに戻るが、
  **保存領域には壊れた内容が残ったまま**だった。
  次に開くと、その壊れた内容が読み込まれる。
  （こちらのv28再レビュー依頼 §13 で「未着手」と書いた項目そのもの。）

  直し方：書く**前**の生の値を控え、不一致・例外のときに**書き戻して読み直して確認**する。

---

**残る3件は、こちらの実装を正規表現が拾えていないだけだった**（下の受入試験で挙動を示す）。

  `new_property.draft`     … 期待マーカー `clone(PARAMS)`。実装は `clone(P)`（`P = PARAMS`）
  `loan_structure.autofit_semantics`
                          … `addLoan`/`delLoan` の本文だけを見ている。
                             実装は `refitAfterLoanCountChange()` に切り出してあり、
                             その中に `autoFitLoans` と `fitLoansOn` がある
  `result_notes.isolated`  … 期待マーカーは `snapshot`／`restore`。
                             **`simulate()` が `notes` を戻り値で返す形にしたので、
                             退避と復元が不要になった。** маーカーが無いのは直した結果
"""
import io
import sys
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
ROOT = Path(__file__).resolve().parent.parent
P = ROOT / "02_output" / "20260901_ライフプランCFシミュレーター汎用版_v29.html"
t = P.read_text(encoding="utf-8")
ng = []


def sub(old, new, label, count=1):
    global t
    c = t.count(old)
    if c == count:
        t = t.replace(old, new, count)
    else:
        ng.append(f"{label} ({c}件/期待{count})")


# ============================================================
# A  案内文を WIZ_STEPS から組み立てる
# ============================================================
sub('''    return '<div class="infobox" style="margin-bottom:12px">'
      + '<b>はじめて使う方は、まず6つの質問に答えてください。</b>'
      + '世帯・収入・いまの資産・住まい・生活費・気になることを順に聞きます。'
      + '<b>どれも飛ばせます。</b><br>' ''' .rstrip(),
    '''    /* ★件数と項目名を**`WIZ_STEPS` から作る**。
         v28まで「まず6つの質問」「世帯・収入・いまの資産・住まい・生活費・気になること」と
         **手で書いてあり、v26で8ステップにしたあとも6のまま**だった
         （長期前提が案内から抜けていた。ChatGPT版のv28レビュー `wizard.not_six` で指摘）。
         **案内文を手書きで持つと、ステップを足した瞬間からずれる。**
         こちらがV76〜V80へ5版にわたって指摘してきたのと同じ型を、自分がやっていた。 */
    return '<div class="infobox" style="margin-bottom:12px">'
      + '<b>はじめて使う方は、まず' + wizInputCount() + 'つの質問に答えてください。</b>'
      + esc(wizInputTitles().join("・")) + 'を順に聞き、'
      + '最後に' + esc(wizViewTitles().join("・")) + 'の画面で入力状況を確かめます。'
      + '<b>どれも飛ばせます。</b><br>' ''' .rstrip(),
    "案内文を WIZ_STEPS から組み立てる")

sub('''function checkWizardCoverage(){''',
    '''/** セットアップの入力ステップの数（案内文に出す件数の正本）。 */
function wizInputCount(){ return WIZ_STEPS.filter(s => s.kind !== "view").length; }
/** 入力ステップの見出し（案内文に並べる項目名の正本）。 */
function wizInputTitles(){ return WIZ_STEPS.filter(s => s.kind !== "view").map(s => s.t); }
/** 確認だけのステップの見出し。 */
function wizViewTitles(){ return WIZ_STEPS.filter(s => s.kind === "view").map(s => s.t); }

/** 案内文が `WIZ_STEPS` と食い違っていないか。**足りない項目名と件数のずれを返す。**
 *
 *  ★`checkWizardCoverage()` は `covers` と `READY_STEPS` を突き合わせるだけで、
 *    **利用者を招き入れる文章そのものを一度も見ていなかった**。
 *    v28は「まず6つの質問」と書きながら8ステップあり、長期前提が案内から抜けていた。
 *    案内文も**実体から作り、機械で突き合わせる**。 */
function checkWizardWording(){
  const out = [];
  const saved = WIZ_ON;
  let html = "";
  try{ WIZ_ON = false; html = wizardBlock(); }
  catch(e){ out.push({問題:"案内文を描けない", 詳細:String(e)}); }
  finally{ WIZ_ON = saved; }
  const text = html.replace(/<[^>]*>/g, "");
  const n = wizInputCount();
  /* 件数が数字で書かれていて、実体と違っていないか。 */
  const m = text.match(/まず\\s*(\\d+)\\s*つの質問/);
  if(!m) out.push({問題:"案内文に質問の件数が見つからない"});
  else if(Number(m[1]) !== n)
    out.push({問題:"案内文の件数が実体と違う", 案内:Number(m[1]), 実体:n});
  /* すべての入力ステップの見出しが案内文に出ているか。 */
  wizInputTitles().forEach(title => {
    if(text.indexOf(title) < 0) out.push({問題:"案内文に出ていない入力ステップ", 項目:title});
  });
  return out;
}

function checkWizardCoverage(){''',
    "checkWizardWording を追加")

# ============================================================
# B  保存に失敗したら保存領域を元へ戻す
# ============================================================
sub('''  try{
    const payload = JSON.stringify(nextPlans);
    localStorage.setItem(STORE.plans, payload);
    /* ★書いたあとに読み戻して一致を確かめる（ChatGPT版 `v61StorePlans` から取り込み）。
         例外が出なければ成功とみなすと、**静かに切り詰められた・別の内容が書かれた**
         場合を捕まえられない。実測で「メモリ1件・保存 `[]`・成功表示」になった。 */
    if(localStorage.getItem(STORE.plans) !== payload)
      throw new Error("保存したあとの読み戻しで内容が一致しませんでした");
    PLANS = nextPlans;
    return true;
  }catch(e){
    noticeStoreFailed(e);
    return false;   // ★PLANS は触らない（元の一覧のまま）
  }
}''',
    '''  /* ★書く**前**の生の値を控える。失敗したときに戻すため。
       v28は `PLANS` を触らずに戻るだけで、**保存領域には壊れた内容が残った**。
       次に開くとその壊れた内容が読み込まれる
       （ChatGPT版のv28レビュー `save.rollback` で指摘。こちらも §13 で未着手と書いていた）。 */
  let before = null;
  try{ before = localStorage.getItem(STORE.plans); }catch(e){ before = null; }
  try{
    const payload = JSON.stringify(nextPlans);
    localStorage.setItem(STORE.plans, payload);
    /* ★書いたあとに読み戻して一致を確かめる（ChatGPT版 `v61StorePlans` から取り込み）。
         例外が出なければ成功とみなすと、**静かに切り詰められた・別の内容が書かれた**
         場合を捕まえられない。実測で「メモリ1件・保存 `[]`・成功表示」になった。 */
    if(localStorage.getItem(STORE.plans) !== payload)
      throw new Error("保存したあとの読み戻しで内容が一致しませんでした");
    PLANS = nextPlans;
    return true;
  }catch(e){
    /* ★保存領域を書く前の状態へ戻す。**戻したあとも読み直して確認する**
         （戻す操作そのものが静かに失敗することがある）。 */
    const restored = restorePlansRaw(before);
    noticeStoreFailed(e, restored);
    return false;   // ★PLANS は触らない（元の一覧のまま）
  }
}

/** 保存領域を、書く前の生の値へ戻す。戻せたかを返す。
 *  ★「戻した」と言うだけにしない。**書き戻したあと読み直して一致を見る。** */
function restorePlansRaw(before){
  try{
    if(before === null) localStorage.removeItem(STORE.plans);
    else localStorage.setItem(STORE.plans, before);
    const now = localStorage.getItem(STORE.plans);
    return now === before;
  }catch(e){ return false; }
}''',
    "commitPlans にロールバック")

if ng:
    print("NG:", " / ".join(ng))
    sys.exit(1)
P.write_text(t, encoding="utf-8")
print("OK v29（案内文を実体から組み立て・保存失敗時のロールバック）")
