# -*- coding: utf-8 -*-
"""汎用版 v30 → v31 の修正を当てる。

ChatGPT版のv30独立再レビュー（P1 5件・P2 3件）は**全件こちらで再現できた**ので、全件直す。

  P1-1 保存主領域の「意味的な破損」を正常な空一覧と誤認する
       `{}`・`null`・`"文字列"`・`params:null` は migratePlans() が [] に正規化するため、
       そのあとの Array.isArray() を通ってしまう。主領域欠損時に控えを見ていない。
       getItem 例外を「未保存」と同じ扱いにしている。
  P1-2 控えと復旧書戻しに read-after-write がない
  P1-3 複数タブ競合時、別タブの新しい有効データを古い値で上書きする
  P1-4 取得済み持ち家を、過去の取得資金差で未準備に落とす
  P1-5 「働いていない」を選んでも年収0円が無効
  P2-1 readinessFacts(P) が引数Pを完全には評価しない
  P2-2 畳んだ補足の説明ボタン名が計算値で変わる
  P2-3 受入試験の同梱（03_scripts/v31_accept.js として作る）

  あわせて、こちら側で見つけた分（V85査読の還流）:
  X-1  `[data-blankhide]` を持つ要素が0件で、抑制の仕組みが空回りしていた。
       未入力のまま「最終年まで金融資産は尽きません」と結論が出ていた。

使い方: python 03_scripts/v31_fixes.py
"""
import io, sys
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
SRC = BASE / "02_output" / "20260902_ライフプランCFシミュレーター汎用版_v30.html"
DST = BASE / "02_output" / "20260902_ライフプランCFシミュレーター汎用版_v31.html"

s = io.open(SRC, encoding="utf-8").read()
orig_len = len(s)
applied = []


def sub(tag, old, new, count=1):
    """厳密一致で置換する。当たらなければ止める（黙って通さない）。"""
    global s
    n = s.count(old)
    if n != count:
        print("!! アンカー不一致 [%s]: %d件（期待 %d件）" % (tag, n, count))
        sys.exit(1)
    s = s.replace(old, new, count)
    applied.append(tag)


# ================================================ P1-1 / P1-2  保存の読み書き
sub("S1-readStore",
'''/** localStorage から読む。読めないときは null を返す（例外を外へ出さない）。 */
function readStore(key){
  try{ return localStorage.getItem(key); }catch(e){ return null; }
}

/** 生の文字列をプラン配列として解釈できるか試す。 */
function parsePlansRaw(raw){
  try{
    const list = migratePlans(JSON.parse(raw));
    if(!Array.isArray(list)) return {ok:false, list:[]};
    return {ok:true, list:list};
  }catch(e){ return {ok:false, list:[]}; }
}''',
'''/** localStorage から読む。
 *
 *  ★「無い」と「読めない」を分けて返す（v31）。
 *    v30は両方 `null` に潰していたため、**保存領域を読めない端末**（プライベート
 *    ブラウズ・容量枯渇・権限拒否）で、利用者には「初めての利用」と同じ空一覧が出ていた
 *    （ChatGPT版のv30レビュー `storage.recover.read_error`）。 */
function readStore(key){
  try{
    const raw = localStorage.getItem(key);
    return {status: (raw === null) ? "missing" : "ok", raw: raw};
  }catch(e){ return {status:"unreadable", raw:null}; }
}

/** 書いて、**読み戻して一致を確かめる**。一致しなければ false。
 *
 *  ★例外が出ないことは成功の証拠にならない（静かに切り詰められる・別の値が入る）。
 *    v30は主領域だけ読み戻しており、**控えと復旧書戻しは例外の有無だけ**で見ていた
 *    （ChatGPT版のv30レビュー `storage.verify.backup` / `storage.verify.writeback`）。 */
function writeStoreVerified(key, value){
  try{
    localStorage.setItem(key, value);
    return localStorage.getItem(key) === value;
  }catch(e){ return false; }
}

/** 生の文字列をプラン配列として解釈できるか試す。
 *
 *  ★**移行の前に形を検査する。**
 *    `migratePlans()` は配列でない値を `[]` に直し、壊れたレコードを黙って捨てる。
 *    そのあとで `Array.isArray()` を見ても、**破損が「正常な空配列」に化けたあと**なので通る。
 *    v30は `{}`・`null`・`"文字列"`・`params:null` をすべて「0件の正常な一覧」として扱い、
 *    控えを見ずに利用者のプランを失っていた（ChatGPT版のv30レビュー `storage.recover.semantic`）。
 *    **空配列 `[]` は正当な「全部消した状態」なので、破損とは区別する。** */
function parsePlansRaw(raw){
  let parsed;
  try{ parsed = JSON.parse(raw); }
  catch(e){ return {ok:false, list:[], why:"JSONとして読み取れません"}; }
  if(!Array.isArray(parsed)) return {ok:false, list:[], why:"一覧（配列）の形ではありません"};
  for(const p of parsed){
    if(!p || typeof p !== "object" || Array.isArray(p))
      return {ok:false, list:[], why:"プラン1件分が入れ物の形ではありません"};
    if(typeof p.name !== "string" || !p.name.trim())
      return {ok:false, list:[], why:"名前が入っていないプランがあります"};
    if(!p.params || typeof p.params !== "object" || Array.isArray(p.params))
      return {ok:false, list:[], why:"設定値が入っていないプランがあります"};
  }
  const list = migratePlans(parsed);
  /* ★移行で件数が減ったら、正常扱いにしない（黙って落とさない）。 */
  if(list.length !== parsed.length)
    return {ok:false, list:[], why:"読み取れないプランが混じっています"};
  return {ok:true, list:list, why:""};
}''')

sub("S2-loadPlans",
'''function loadPlans(){
  const raw = readStore(STORE.plans);
  if(raw === null || raw === ""){ PLANS = []; return; }
  const first = parsePlansRaw(raw);
  if(first.ok){ PLANS = first.list; return; }
  /* 主領域が壊れている。控えを試す。 */
  const bakRaw = readStore(STORE.plansBak);
  const bak = (bakRaw === null || bakRaw === "") ? {ok:false, list:[]} : parsePlansRaw(bakRaw);
  if(bak.ok){
    PLANS = bak.list;
    /* 戻せた内容を主領域へ書き戻す（次回もまた壊れた値を読まないように）。 */
    try{ localStorage.setItem(STORE.plans, bakRaw); }catch(e){}
    pushNotice("planrecover", "warn",
      `<b>保存された内容が壊れていたため、控えから戻しました（${bak.list.length}件）。</b>`
      + `<span class="hint">直前の保存が最後まで書けなかった可能性があります。`
      + `内容を確かめてから、もう一度保存してください。</span>`);
    return;
  }
  PLANS = [];
  pushNotice("planbroken", "bad",
    `<b>保存された内容が読み取れませんでした。</b>`
    + `<span class="hint">控えからも戻せませんでした。`
    + `一覧は空で始まりますが、<b>壊れた内容は消していません</b>。`
    + `別のプランを保存すると上書きされるため、必要なら先に書き出してください。</span>`);
}''',
'''function loadPlans(){
  const prim = readStore(STORE.plans);
  /* ★読めない端末では「初めての利用」と同じ顔をしない。 */
  if(prim.status === "unreadable"){
    PLANS = [];
    pushNotice("planunreadable", "bad",
      `<b>ブラウザの保存領域を読み取れませんでした。</b>`
      + `<span class="hint">プライベートブラウズや保存容量の設定で読めないことがあります。`
      + `<b>保存済みのプランが消えたわけではありません。</b>`
      + `この画面では保存が使えないため、条件はファイルに書き出して持ち運んでください。</span>`);
    return;
  }
  if(prim.status === "ok" && prim.raw !== ""){
    const first = parsePlansRaw(prim.raw);
    if(first.ok){ PLANS = first.list; return; }
    recoverPlansFromBackup("壊れていた", first.why);
    return;
  }
  /* ★主領域が無い／空文字。**控えを見る。**
       v30はここで 0件のまま戻っており、控えがあっても使わなかった
       （ChatGPT版のv30レビュー `storage.recover.missing_primary`）。 */
  recoverPlansFromBackup("見つからなかった", "主領域がありません");
}

/** 控えから戻す。戻せたかどうかを**そのまま利用者に伝える**。 */
function recoverPlansFromBackup(what, why){
  const bak = readStore(STORE.plansBak);
  const parsed = (bak.status === "ok" && bak.raw) ? parsePlansRaw(bak.raw)
                                                  : {ok:false, list:[], why:"控えがありません"};
  if(!parsed.ok){
    PLANS = [];
    pushNotice("planbroken", "bad",
      `<b>保存された内容が${esc(what)}ため読み取れませんでした（${esc(why)}）。</b>`
      + `<span class="hint">控えからも戻せませんでした（${esc(parsed.why)}）。`
      + `一覧は空で始まりますが、<b>壊れた内容は消していません</b>。`
      + `別のプランを保存すると上書きされるため、必要なら先に書き出してください。</span>`);
    return;
  }
  PLANS = parsed.list;
  /* ★書き戻しも読み戻して確かめる。
       「戻しました」と言った内容が保存領域に入っていなければ、
       次に開いたときも同じ復旧を繰り返す。**画面の説明と永続状態を一致させる。** */
  const wrote = writeStoreVerified(STORE.plans, bak.raw);
  pushNotice("planrecover", wrote ? "warn" : "bad",
    `<b>保存された内容が${esc(what)}ため、控えから戻しました（${parsed.list.length}件）。</b>`
    + `<span class="hint">`
    + (wrote
        ? `保存領域にも書き戻しました。内容を確かめてから、もう一度保存してください。`
        : `<b>ただし保存領域へは書き戻せていません。この画面の中だけの復旧です。</b>`
          + `いま「書き出す」でファイルに保存してください。`
          + `そのまま閉じると、次に開いたときも同じ状態から始まります。`)
    + `</span>`);
}''')

sub("S3-commit",
'''    PLANS = nextPlans;
    /* ★主領域を書けたことを確かめた**あと**で控えを更新する。
         先に控えを書くと、主領域の書き込みが失敗したときに
         控えまで新しい壊れかけの内容になってしまう。
         控えが書けなくても保存そのものは成功として扱う（控えは保険）。 */
    try{ localStorage.setItem(STORE.plansBak, payload); }catch(e){}
    return true;
  }catch(e){
    /* ★保存領域を書く前の状態へ戻す。**戻したあとも読み直して確認する**
         （戻す操作そのものが静かに失敗することがある）。 */
    const restored = restorePlansRaw(before);
    noticeStoreFailed(e, restored);
    return false;   // ★PLANS は触らない（元の一覧のまま）
  }''',
'''    PLANS = nextPlans;
    /* ★主領域を書けたことを確かめた**あと**で控えを更新する。
         先に控えを書くと、主領域の書き込みが失敗したときに
         控えまで新しい壊れかけの内容になってしまう。
         控えが書けなくても保存そのものは成功として扱う（控えは保険）。
         ただし**控えも読み戻して確かめ、ずれていたら黙っていない**（v31）。
         v30は例外の有無だけを見ていたため、控えが静かに `[]` になっても
         「保存成功・控えあり」と扱っていた。 */
    if(!writeStoreVerified(STORE.plansBak, payload))
      pushNotice("planbakfail", "warn",
        `<b>保存はできましたが、控えを更新できませんでした。</b>`
        + `<span class="hint">保存領域が壊れたときに戻せない状態です。`
        + `大事な条件は「書き出す」でファイルにも残してください。</span>`);
    else
      /* ★成功したら前回の警告を取り下げる。`dismissNotice()` は render() を呼ぶので
           保存の途中では使わない（描画の再入を作らない）。 */
      NOTICES = NOTICES.filter(n => n.id !== "planbakfail");
    return true;
  }catch(e){
    /* ★戻す前に、**いま保存領域に何が入っているか**を見る（v31）。
         別のタブが有効な内容を書いていたら、**戻してはいけない。**
         v30は無条件に書く前の値へ戻していたため、
         **別タブの保存を消していた**（ChatGPT版のv30レビュー `storage.concurrent_writer`）。 */
    const now = readStore(STORE.plans);
    const cur = (now.status === "ok") ? now.raw : null;
    if(cur !== null && cur !== before && cur !== ""){
      const other = parsePlansRaw(cur);
      if(other.ok){
        /* 自分の payload でも書く前の値でもない、**有効な別の内容**。
           ＝別のタブが保存した。上書きせず、画面をそちらに合わせる。 */
        PLANS = other.list;
        pushNotice("planconflict", "warn",
          `<b>別のタブで保存内容が更新されたため、今回の保存は行いませんでした。</b>`
          + `<span class="hint">画面の一覧を、いま保存されている${other.list.length}件に合わせました。`
          + `必要な変更をもう一度行って保存してください。</span>`);
        return false;
      }
    }
    const restored = restorePlansRaw(before);
    noticeStoreFailed(e, restored);
    return false;   // ★PLANS は触らない（元の一覧のまま）
  }''')

sub("S4-revision",
'''  let before = null;
  try{ before = localStorage.getItem(STORE.plans); }catch(e){ before = null; }''',
'''  /* ★書く前の生の値を revision として控える。失敗したときに戻すため、
       かつ「別のタブが書いた内容」と「自分が書く前の内容」を見分けるため。 */
  const beforeRead = readStore(STORE.plans);
  const before = (beforeRead.status === "ok") ? beforeRead.raw : null;''')


# ============================================ P1-4  取得済み持ち家を巻き込まない
sub("H1-housing",
'''function housingReadiness(P){
  const src = P || PARAMS;
  const H = src.house;
  if(!H || !H.buy) return {level:"na", gap:0, note:""};
  const gap = fundingGap(H);''',
'''function housingReadiness(P){
  const src = P || PARAMS;
  const H = src.house;
  if(!H || !H.buy) return {level:"na", gap:0, note:""};
  /* ★すでに取得している住宅は、**取得時の資金恒等式で判定しない**（v31）。
       返済して減った元本を「不足」と読んでしまう。
       実測：40歳・35歳取得・当時5,000万・自己資金500万・現在残債2,500万で
       「住宅資金が 23,500,000円 足りません」と出て段階2で止まっていた
       （ChatGPT版のv30レビュー `readiness.already_owned`）。
       CLAUDE.mdに「取得済みなら頭金・諸費用の資金整合は検査しない（もう終わった話）」と
       **書いてあったのに、v30の housingReadiness はそれを使っていなかった。**
       分岐の判定は `housingOf()` に委ねる（住まいの分類を2か所に持たない）。 */
  if(typeof housingOf === "function" && housingOf(src) === "own")
    return {level:"na", gap:0, note:""};
  const gap = fundingGap(H);''')


# ==================================== P1-5 / P2-1  準備度の判定を引数と分岐に対応
sub("R1-isConfirmed",
'''function isConfirmed(path){
  const st = (PARAMS.meta && PARAMS.meta.inputState) || {};
  const e  = (PARAMS.meta && PARAMS.meta.entered) || {};
  return !!(st[path] ? st[path].confirmed : e[path]);
}''',
'''/** ★判定の対象を引数で受ける（v31）。
 *    v30は `readinessFacts(P)` が P を受けながら、`confirmed`／`valid` は
 *    グローバルの `PARAMS` を見ていた。候補で年齢を確認済みにしても
 *    `confirmed:false` が返る（ChatGPT版のv30レビュー `readiness.facts_parameter`）。
 *    **引数を受け取ったなら、その中だけを見る。** */
function isConfirmed(path, P){
  const src = P || PARAMS;
  const st = (src.meta && src.meta.inputState) || {};
  const e  = (src.meta && src.meta.entered) || {};
  return !!(st[path] ? st[path].confirmed : e[path]);
}''')

sub("R2-isUsable",
'''const READY_NONZERO = new Set([
  "family.ageH", "income.hBase", "living.table.0.amount",
  "house.price", "house.loans.0.years", "retire.retireAgeH",
]);
function isUsable(path){
  const v = get(PARAMS, path);
  if(v === null || v === undefined || v === "") return false;
  const n = Number(v);
  if(!Number.isFinite(n)) return false;
  if(n < 0) return false;
  if(READY_NONZERO.has(path) && n === 0) return false;
  return true;
}''',
'''const READY_NONZERO = new Set([
  "family.ageH", "living.table.0.amount",
  "house.price", "house.loans.0.years", "retire.retireAgeH",
]);

/** ★世帯の条件によって「0が有効か」が変わる項目（v31）。
 *    true を返すと「その世帯では0は無効」。
 *
 *    v30は `income.hBase` を一律に0無効としたため、
 *    **画面が正式な選択肢として用意している「働いていない」を選ぶと、
 *    確認済みの年収0円が無効になり段階0で止まった**
 *    （ChatGPT版のv30レビュー `readiness.zero_income`）。
 *    v28で分岐を `applies(P)` で条件付けた直後に、
 *    **同じ「分岐を見ない一律判定」を別の場所で作っていた。** */
const READY_NONZERO_IF = {
  "income.hBase": P => workTypeOf(P, "h") !== "none",
};

function isUsable(path, P){
  const src = P || PARAMS;
  const v = get(src, path);
  if(v === null || v === undefined || v === "") return false;
  const n = Number(v);
  if(!Number.isFinite(n)) return false;
  if(n < 0) return false;
  if(READY_NONZERO.has(path) && n === 0) return false;
  const cond = READY_NONZERO_IF[path];
  if(cond && n === 0 && cond(src)) return false;
  return true;
}''')

sub("R3-facts",
'''      out[path] = {label:n[1], step:step.key, applies:applies,
                   confirmed:isConfirmed(path), valid:isUsable(path)};''',
'''      out[path] = {label:n[1], step:step.key, applies:applies,
                   confirmed:isConfirmed(path, src), valid:isUsable(path, src)};''')


# ================================ P2-2  畳んだ補足のボタン名に計算値を入れない
sub("F1-foldname",
'''        + popBtn(key, "この説明をひらく", foldHead(full, text, 34)) + popBody(key, full);''',
'''        /* ★名前は `data-foldname` があればそれを使う（v31）。
             畳む対象が**計算結果の要約行**のとき、本文の先頭を名前にすると
             入力を変えるたびに名前が変わる。実測で3件あった：
             「維持費の合計 年 36万円（月 3万円）」「控除される総額 273万円」
             「取得時 5,000万円 → 10年後 4,309」。
             ChatGPT版V82に「読み上げ名に計算結果を入れない」と指摘した当人として直す
             （ChatGPT版のv30レビュー `a11y.fold_name_stability`）。
             ★なお本文が説明文のときは、数字を含んでいても値では変わらないので
               そのまま使う（「19歳未満の子がいる…」等を壊さない）。
               見落としは受入試験（値を変えて名前が変わらないか）で捕まえる。 */
        + popBtn(key, "この説明をひらく",
                 el.getAttribute("data-foldname") || foldHead(full, text, 34))
        + popBody(key, full);''')

# 計算結果の要約行3件に、固定の論点名を付ける
sub("F2-maint",
'''      + `<div class="hint" style="margin:7px 0; padding:7px 8px; background:var(--panel2); border-radius:4px">
          <b>維持費の合計 年 ${fmtMan(maintTotal(P.house,0))}万円</b>''',
'''      + `<div class="hint" data-foldname="維持費の合計" style="margin:7px 0; padding:7px 8px; background:var(--panel2); border-radius:4px">
          <b>維持費の合計 年 ${fmtMan(maintTotal(P.house,0))}万円</b>''')

sub("F3-deduction",
'''  return `<div class="hint" style="margin:8px 0; padding:8px 9px; background:var(--panel2); border-radius:4px; line-height:1.9">
    <b style="color:${allOK?"var(--ok)":"var(--bad)"}">''',
'''  return `<div class="hint" data-foldname="住宅ローン控除の要件と控除額" style="margin:8px 0; padding:8px 9px; background:var(--panel2); border-radius:4px; line-height:1.9">
    <b style="color:${allOK?"var(--ok)":"var(--bad)"}">''')

sub("F4-estate",
'''      + (P.house.buy ? `<div class="hint" style="margin:4px 0 9px; padding:7px; background:var(--panel2); border-radius:4px">
          取得時 <b>${fmtMan(P.house.price)}万円</b>''',
'''      + (P.house.buy ? `<div class="hint" data-foldname="不動産価値の推移" style="margin:4px 0 9px; padding:7px; background:var(--panel2); border-radius:4px">
          取得時 <b>${fmtMan(P.house.price)}万円</b>''')


# ============ X-1  未入力のうちは結論を出さない（[data-blankhide] が空回りしていた）
sub("X1-cf-banner",
'''    + (S.depleteYear
      ? `<div class="banner bad"><b>${S.depleteYear}年（あなた${S.depleteAge}歳）に金融資産が尽きます。</b>
         ［ストレステスト］タブの一番上に、生活費を毎年いくら見直せば足りるかを逆算した表があります。</div>`
      : `<div class="banner ok"><b>最終年（${last.ageH}歳）まで金融資産は尽きません。</b>
         もっとも少なくなるのは ${minAsset.year}年（${minAsset.ageH}歳）の
         ${fmtMan(minAsset.assetTotal)}万円です。</div>`);''',
'''    + (isBlank(PARAMS)
      /* ★未入力のうちは**結論を出さない**（v31）。
           v30まで、全部0円の計算に対して「最終年まで金融資産は尽きません」と
           断定していた。ページ上部の「まだ入力されていません」は約8,000px上にあるので、
           表のところだけ読むと「問題なし」と読める。
           `[data-blankhide]` の仕組みは用意してあったが、**どの要素にも付いていなかった**
           （実測0件）。ChatGPT版V85の「安全にしたコードが実は何もしていない」を
           自分の版に当てて見つけた。 */
      ? `<div class="banner warn"><b>まだ結論は出せません。</b>
         年齢・年収・年間の生活費を入れると、ここに「資産が尽きるかどうか」を出します。
         いま表に並んでいる0円は、計算の結果ではなく未入力の状態です。</div>`
      : S.depleteYear
      ? `<div class="banner bad"><b>${S.depleteYear}年（あなた${S.depleteAge}歳）に金融資産が尽きます。</b>
         ［ストレステスト］タブの一番上に、生活費を毎年いくら見直せば足りるかを逆算した表があります。</div>`
      : `<div class="banner ok"><b>最終年（${last.ageH}歳）まで金融資産は尽きません。</b>
         もっとも少なくなるのは ${minAsset.year}年（${minAsset.ageH}歳）の
         ${fmtMan(minAsset.assetTotal)}万円です。</div>`);''')

sub("X2-check-conclusion",
'''        : [`<b>この赤字は破綻ではありません。</b>`
           + `${P.meta.endAge}歳まで資産が尽きず、借入が必要になる年もないので、`
           + `貯めたお金から取り崩して乗り切れます`,''',
'''        : [(isBlank(P)
            /* ★未入力のうちは「破綻ではありません」と言わない（v31・X-1と同じ理由）。 */
            ? `<b>まだ結論は出せません。</b>`
              + `年齢・年収・年間の生活費を入れてから読んでください`
            : `<b>この赤字は破綻ではありません。</b>`
              + `${P.meta.endAge}歳まで資産が尽きず、借入が必要になる年もないので、`
              + `貯めたお金から取り崩して乗り切れます`),''')

# 空回りしていたループを消す（V85のP2-2と同型を自分の版に残さない）
sub("X3-remove-blankhide",
'''  /* ★未入力のうちは、CF表・グラフ・診断に「結論」を出さない（P0-1）。
     ヘッダーで「入力を始めてください」と言いながら、本文で
     「最終年まで金融資産は尽きません」と出ていた。**0円の計算を正式な結果と誤読させる。** */
  document.querySelectorAll("[data-blankhide]").forEach(el => {
    el.style.display = isBlank(PARAMS) ? "none" : "";
  });''',
'''  /* ★未入力のうちは、CF表・診断に「結論」を出さない（P0-1）。
     ヘッダーで「入力を始めてください」と言いながら、本文で
     「最終年まで金融資産は尽きません」と出ていた。**0円の計算を正式な結果と誤読させる。**
     ★v31で、描画後に `[data-blankhide]` を隠す方式をやめ、**結論を作る場所で出し分ける**形にした。
       v30までこのループは動いていたが、**属性を持つ要素が1つも無く（実測0件）空回りしていた**。
       「安全だが何もしていないコード」を残すと、直したつもりで直っていない状態が続く
       （ChatGPT版V85の同型を査読した流れで自分の版に見つけた）。
       隠すより**理由を書いたほうが親切**なので、断りの文へ差し替えている。 */''')


# ------------------------------------------------------------------ 版番号
sub("VER",
    'const VERSION = {tag:"汎用版 v30", date:"2026-09-02",',
    'const VERSION = {tag:"汎用版 v31", date:"2026-09-02",')
sub("VER-file",
    'file:"20260902_ライフプランCFシミュレーター汎用版_v30.html"};',
    'file:"20260902_ライフプランCFシミュレーター汎用版_v31.html"};')

io.open(DST, "w", encoding="utf-8").write(s)
print("当てた修正: %d件" % len(applied))
for a in applied:
    print("  -", a)
print("%s → %s" % (SRC.name, DST.name))
print("%d bytes → %d bytes（%+d）" % (orig_len, len(s), len(s) - orig_len))
