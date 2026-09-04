/* 汎用版 v31 の受入試験。
 *
 *  ChatGPT版のv30独立再レビュー（P1 5件・P2 3件）は全件こちらで再現できたので、
 *  **その各ケースを、v30で落ち v31で通る形**に書き下したもの。
 *  あわせて v30 で通っていた項目を回帰として残す（厳しくしすぎて壊していないか）。
 *
 *  使い方: ページと同一オリジンから読み込んで __V31_ACCEPT__() を呼ぶ（Promiseを返す）。
 *      const src = await fetch("../03_scripts/v31_accept.js").then(r=>r.text());
 *      (0,eval)(src); await __V31_ACCEPT__();
 *
 *  ★v30でも走るように、v31で足した関数は存在を確かめてから使う。
 *  ★負試験（Storage の故障注入・正本の書き換え）は**必ず元へ戻す**。
 *    戻さないと後続を汚染して、自分の修正を実際より良く見せてしまう（v30で実際にやった）。
 */
window.__V31_ACCEPT__ = async function(){
  const R = [];
  const add = (id, ok, observed, expected) => R.push({id, ok: !!ok, observed, expected});
  const sleep = ms => new Promise(r => setTimeout(r, ms));
  const notices = () => (typeof NOTICES !== "undefined" ? NOTICES : []).map(n => n.id);

  /** 甲・乙の2件を正常に保存し、控えも作る。 */
  const seed = () => {
    try{ localStorage.clear(); }catch(e){}
    PARAMS = genericParams();
    return commitPlans([{name:"甲", params:clone(PARAMS)},
                        {name:"乙", params:clone(PARAMS)}]);
  };

  /** Storage.prototype.setItem に故障を注入して fn を実行し、**必ず元へ戻す**。 */
  const withSetItemFault = async (fault, fn) => {
    const proto = Storage.prototype, orig = proto.setItem;
    proto.setItem = function(k, v){ return fault.call(this, k, v, orig); };
    try{ return await fn(); }
    finally{ proto.setItem = orig; }
  };

  /* ========== P1-1 意味的な破損を「正常な空一覧」と誤認しない ========== */

  // 依頼書の6ケースすべてで、控えの甲・乙へ復旧し、知らせを出すこと
  const badPrimaries = ['{}', 'null', '"文字列"', '[{"name":"甲","params":null}]'];
  for(const bad of badPrimaries){
    try{
      seed();
      localStorage.setItem(STORE.plans, bad);
      PLANS = []; NOTICES = []; loadPlans();
      const names = (PLANS || []).map(p => p.name);
      add("P1-1_意味的破損から復旧【" + bad.slice(0,22) + "】",
          names.length === 2 && names[0] === "甲" && names[1] === "乙" && notices().length > 0,
          {復旧後:names, 知らせ:notices()}, {復旧後:["甲","乙"], 知らせ:"1件以上"});
    }catch(e){ add("P1-1_意味的破損から復旧【" + bad.slice(0,22) + "】", false, String(e), "例外なし"); }
  }

  // 一部のレコードだけ壊れているとき、残りを黙って落とさない
  try{
    seed();
    localStorage.setItem(STORE.plans,
      JSON.stringify([{name:"甲", params:{}}, {name:"", params:null}]));
    PLANS = []; NOTICES = []; loadPlans();
    const names = (PLANS || []).map(p => p.name);
    add("P1-1_一部不正レコードを黙って落とさない",
        names.length === 2 && notices().length > 0,
        {復旧後:names, 知らせ:notices()}, {復旧後:["甲","乙"], 知らせ:"1件以上"});
  }catch(e){ add("P1-1_一部不正レコードを黙って落とさない", false, String(e), "例外なし"); }

  // 主領域が消え、控えだけが残っている
  try{
    seed();
    localStorage.removeItem(STORE.plans);
    PLANS = []; NOTICES = []; loadPlans();
    const names = (PLANS || []).map(p => p.name);
    add("P1-1_主領域欠損・控えありで復旧",
        names.length === 2 && notices().length > 0,
        {復旧後:names, 知らせ:notices()}, {復旧後:["甲","乙"], 知らせ:"1件以上"});
  }catch(e){ add("P1-1_主領域欠損・控えありで復旧", false, String(e), "例外なし"); }

  // 空配列は「全部消した」なので、破損として扱わない（過剰反応の確認）
  try{
    seed();
    localStorage.setItem(STORE.plans, "[]");
    PLANS = []; NOTICES = []; loadPlans();
    add("P1-1_空配列は破損扱いにしない",
        (PLANS || []).length === 0 && notices().length === 0,
        {件数:(PLANS||[]).length, 知らせ:notices()}, {件数:0, 知らせ:[]});
  }catch(e){ add("P1-1_空配列は破損扱いにしない", false, String(e), "例外なし"); }

  // 読み取れない（getItem が投げる）ときは「未保存」と別の顔をする
  try{
    seed();
    const proto = Storage.prototype, origGet = proto.getItem;
    proto.getItem = function(k){ if(k === STORE.plans) throw new Error("読めません"); return origGet.call(this, k); };
    let names, ns;
    try{ PLANS = []; NOTICES = []; loadPlans(); names = (PLANS||[]).map(p=>p.name); ns = notices(); }
    finally{ proto.getItem = origGet; }
    add("P1-1_読取不能を未保存と区別して知らせる",
        ns.length > 0, {件数:names.length, 知らせ:ns}, {知らせ:"1件以上"});
  }catch(e){ add("P1-1_読取不能を未保存と区別して知らせる", false, String(e), "例外なし"); }

  /* ========== P1-2 控えと復旧書戻しに read-after-write ========== */

  // A: 控えへの書込みだけが静かに [] になる → 「控えあり」と言わない
  try{
    try{ localStorage.clear(); }catch(e){}
    PARAMS = genericParams(); NOTICES = [];
    const ok = await withSetItemFault(function(k, v, orig){
      if(k === STORE.plansBak) return orig.call(this, k, "[]");
      return orig.call(this, k, v);
    }, async () => commitPlans([{name:"甲", params:clone(PARAMS)},
                                {name:"乙", params:clone(PARAMS)}]));
    const bak = localStorage.getItem(STORE.plansBak);
    add("P1-2_控えが静かに壊れたら知らせる",
        ok === true && bak === "[]" && notices().indexOf("planbakfail") >= 0,
        {保存:ok, 控え:bak, 知らせ:notices()},
        {保存:true, 控え:"[]", 知らせ:"planbakfail を含む"});
  }catch(e){ add("P1-2_控えが静かに壊れたら知らせる", false, String(e), "例外なし"); }

  // B: 復旧の書戻しだけが静かに無視される → 「戻しました」で終わらせない
  try{
    seed();
    localStorage.setItem(STORE.plans, "{壊れた");
    NOTICES = []; PLANS = [];
    await withSetItemFault(function(k, v, orig){
      if(k === STORE.plans) return;           // 書いたふりをする（例外は出さない）
      return orig.call(this, k, v);
    }, async () => { loadPlans(); });
    const primary = localStorage.getItem(STORE.plans);
    const rec = (typeof NOTICES !== "undefined" ? NOTICES : []).find(n => n.id === "planrecover");
    add("P1-2_書戻し失敗を画面の説明に反映する",
        (PLANS||[]).length === 2 && primary === "{壊れた"
          && !!rec && /書き戻せていません/.test(rec.html),
        {メモリ:(PLANS||[]).map(p=>p.name), 主領域:String(primary).slice(0,10),
         知らせの文:rec ? rec.html.replace(/<[^>]*>/g,"").slice(0,60) : null},
        {メモリ:["甲","乙"], 主領域:"壊れたまま", 知らせの文:"書き戻せていない旨を含む"});
  }catch(e){ add("P1-2_書戻し失敗を画面の説明に反映する", false, String(e), "例外なし"); }

  /* ========== P1-3 別タブの新しい保存を古い値で上書きしない ========== */

  try{
    try{ localStorage.clear(); }catch(e){}
    PARAMS = genericParams();
    commitPlans([{name:"旧", params:clone(PARAMS)}]);
    const other = JSON.stringify([{name:"旧", params:clone(PARAMS)},
                                  {name:"別タブ", params:clone(PARAMS)}]);
    NOTICES = [];
    const ok = await withSetItemFault(function(k, v, orig){
      /* このタブが書こうとした瞬間に、別タブが有効な内容を書いた状況を作る */
      if(k === STORE.plans && String(v).indexOf('"このタブ"') >= 0)
        return orig.call(this, k, other);
      return orig.call(this, k, v);
    }, async () => commitPlans([{name:"旧", params:clone(PARAMS)},
                                {name:"このタブ", params:clone(PARAMS)}]));
    const final = JSON.parse(localStorage.getItem(STORE.plans) || "[]").map(p => p.name);
    add("P1-3_別タブの保存を古い値で上書きしない",
        ok === false && final.length === 2 && final[1] === "別タブ"
          && notices().indexOf("planconflict") >= 0,
        {戻り値:ok, 主領域:final, メモリ:(PLANS||[]).map(p=>p.name), 知らせ:notices()},
        {戻り値:false, 主領域:["旧","別タブ"], 知らせ:"planconflict を含む"});
  }catch(e){ add("P1-3_別タブの保存を古い値で上書きしない", false, String(e), "例外なし"); }

  // 別タブが「壊れた値」を書いた場合は、これまで通り書く前へ戻す（過剰緩和の確認）
  try{
    try{ localStorage.clear(); }catch(e){}
    PARAMS = genericParams();
    commitPlans([{name:"旧", params:clone(PARAMS)}]);
    const before = localStorage.getItem(STORE.plans);
    NOTICES = [];
    const ok = await withSetItemFault(function(k, v, orig){
      if(k === STORE.plans && String(v).indexOf('"このタブ"') >= 0)
        return orig.call(this, k, "{壊れた");
      return orig.call(this, k, v);
    }, async () => commitPlans([{name:"旧", params:clone(PARAMS)},
                                {name:"このタブ", params:clone(PARAMS)}]));
    add("P1-3_壊れた値が入っていたら書く前へ戻す",
        ok === false && localStorage.getItem(STORE.plans) === before,
        {戻り値:ok, 主領域が元に戻ったか:localStorage.getItem(STORE.plans) === before},
        {戻り値:false, 主領域が元に戻ったか:true});
  }catch(e){ add("P1-3_壊れた値が入っていたら書く前へ戻す", false, String(e), "例外なし"); }

  /* ========== 準備度（P1-4 / P1-5 / P2-1） ========== */

  const fillFlags = P => READY_STEPS.forEach(s => (s.need || []).forEach(n => {
    if(!n[2] || n[2](P)) P.meta.inputState[n[0]] = {confirmed:true};
  }));
  const baseP = () => {
    PARAMS = genericParams(); PARAMS.meta.inputState = {};
    PARAMS.family.ageH = 40; PARAMS.income.hBase = 6000000;
    PARAMS.income.hTable = [{age:40, amount:6000000, rate:0}];
    PARAMS.living.table = [{age:40, amount:3000000, rate:0}];
    PARAMS.econ.deposit = 10000000; PARAMS.house.rentNow = 1200000;
    PARAMS.living.insurance = 100000; PARAMS.saving.nisaMonthlyH = 30000;
    PARAMS.retire.retireAgeH = 65; PARAMS.econ.inflation = 1; PARAMS.econ.investRate = 3;
  };

  // P1-4: 取得済み持ち家に、過去の取得資金差を要求しない
  try{
    baseP();
    PARAMS.house.buy = true; PARAMS.house.buyAge = 35;      // 現在40歳 → 取得済み
    PARAMS.house.price = 50000000; PARAMS.house.selfFund = 5000000; PARAMS.house.gift = 0;
    PARAMS.house.autoFitLoans = false;
    PARAMS.house.loans = [{name:"A", amount:25000000, years:30, steps:[{y:1,rate:1}]}];
    fillFlags(PARAMS); recalc();
    const h = housingReadiness(PARAMS), r = readiness();
    add("P1-4_取得済み持ち家は過去の資金差で落とさない",
        h.level === "na" && r.stage === 3,
        {housingOf:(typeof housingOf === "function") ? housingOf(PARAMS) : "?",
         住宅:h.level, gap:h.gap, stage:r.stage, missing:r.missing},
        {住宅:"na", stage:3});
  }catch(e){ add("P1-4_取得済み持ち家は過去の資金差で落とさない", false, String(e), "例外なし"); }

  // P1-4b: これから購入する世帯では、引き続き不足を捕まえる（緩めすぎていないか）
  try{
    baseP();
    PARAMS.house.buy = true; PARAMS.house.buyAge = 45;      // 現在40歳 → これから購入
    PARAMS.house.price = 50000000; PARAMS.house.selfFund = 5000000; PARAMS.house.gift = 0;
    PARAMS.house.autoFitLoans = false;
    PARAMS.house.loans = [{name:"A", amount:10000000, years:35, steps:[{y:1,rate:1}]}];
    fillFlags(PARAMS); recalc();
    const h = housingReadiness(PARAMS), r = readiness();
    PLANS = []; try{ localStorage.clear(); }catch(e){}
    const saved = commitPlans([{name:"将来購入", params:clone(PARAMS)}]);
    add("P1-4b_将来購入の資金不足は引き続き段階2・保存可",
        h.level === "insufficient" && r.stage < 3 && saved === true,
        {住宅:h.level, gap:Math.round(h.gap), stage:r.stage, 保存:saved},
        {住宅:"insufficient", stage:"3未満", 保存:true});
  }catch(e){ add("P1-4b_将来購入の資金不足は引き続き段階2・保存可", false, String(e), "例外なし"); }

  // P1-5: 「働いていない」なら確認済みの年収0円は有効
  try{
    baseP();
    PARAMS.work.typeH = "none";
    PARAMS.income.hBase = 0; PARAMS.income.hTable = [{age:40, amount:0, rate:0}];
    PARAMS.house.buy = false;
    fillFlags(PARAMS); recalc();
    const r = readiness();
    add("P1-5_働いていないなら年収0円を有効にする",
        isUsable("income.hBase", PARAMS) === true && r.stage === 3,
        {働き方:workTypeOf(PARAMS, "h"), isUsable:isUsable("income.hBase", PARAMS),
         stage:r.stage, missing:r.missing},
        {isUsable:true, stage:3});
  }catch(e){ add("P1-5_働いていないなら年収0円を有効にする", false, String(e), "例外なし"); }

  // P1-5b: 会社員では年収0円を引き続き無効にする（緩めすぎていないか）
  try{
    baseP();
    PARAMS.work.typeH = "employee";
    PARAMS.income.hBase = 0; PARAMS.income.hTable = [{age:40, amount:0, rate:0}];
    PARAMS.house.buy = false;
    fillFlags(PARAMS); recalc();
    const r = readiness();
    add("P1-5b_会社員の年収0円は引き続き無効",
        isUsable("income.hBase", PARAMS) === false && r.stage < 3,
        {働き方:workTypeOf(PARAMS, "h"), isUsable:isUsable("income.hBase", PARAMS), stage:r.stage},
        {isUsable:false, stage:"3未満"});
  }catch(e){ add("P1-5b_会社員の年収0円は引き続き無効", false, String(e), "例外なし"); }

  // P2-1: readinessFacts(P) は渡した P だけを見る
  try{
    baseP(); recalc();
    const cand = clone(PARAMS);
    cand.family.ageH = 55;
    cand.meta.inputState = {"family.ageH":{confirmed:true}};
    PARAMS.meta.inputState = {};                 // グローバルは未確認にしておく
    const f = readinessFacts(cand)["family.ageH"];
    add("P2-1_readinessFactsは引数Pを評価する",
        f && f.confirmed === true && f.valid === true,
        {グローバル年齢:PARAMS.family.ageH, 候補年齢:cand.family.ageH, 返り値:f},
        {confirmed:true, valid:true});
  }catch(e){ add("P2-1_readinessFactsは引数Pを評価する", false, String(e), "例外なし"); }

  /* ========== P2-2 畳んだ補足のボタン名が計算値で変わらない ========== */

  try{
    const foldNames = () => {
      const out = {};
      [...document.querySelectorAll("button.q")].filter(e => e.offsetParent !== null)
        .forEach(b => { if(b.id) out[b.id] = b.getAttribute("aria-label") || ""; });
      return out;
    };
    PARAMS = genericParams();
    PARAMS.house.buy = true; PARAMS.house.price = 50000000;
    PARAMS.house.maintFee = 20000; PARAMS.estate.sellOn = true;
    recalc(); setTab("loan"); render(); await sleep(600);
    const before = foldNames();
    // 値を大きく変える（物件価格・維持費）
    PARAMS.house.price = 90000000; PARAMS.house.maintFee = 45000;
    recalc(); setTab("loan"); render(); await sleep(600);
    const after = foldNames();
    const changed = Object.keys(before).filter(k => after[k] !== undefined && after[k] !== before[k])
      .map(k => ({id:k, 前:before[k].slice(0,40), 後:after[k].slice(0,40)}));
    add("P2-2_値を変えても畳んだボタン名が変わらない", changed.length === 0,
        {調べた数:Object.keys(before).length, 変わった:changed}, {変わった:[]});
  }catch(e){ add("P2-2_値を変えても畳んだボタン名が変わらない", false, String(e), "例外なし"); }

  /* ========== X-1 未入力のうちは結論を出さない（V85査読の還流） ========== */

  try{
    try{ localStorage.clear(); }catch(e){}
    /* ★起動時の状態は `blankParams()`。`genericParams()` は `meta.blank` を立てないので
         `isBlank()` が false になり、**この試験が何も測らなくなる**（最初にそれをやった）。
         「未入力の画面」を測るなら、アプリが起動時に使う関数と同じものを使う。 */
    PARAMS = blankParams();
    recalc();
    const hits = {};
    for(const t of ["cf", "check"]){
      setTab(t); render(); await sleep(700);
      const sec = document.querySelector("main>section.on") || document.querySelector("section.on");
      const txt = (sec ? sec.innerText : "").replace(/\s+/g, " ");
      hits[t] = {
        結論語: ["尽きません", "破綻ではありません", "乗り切れます"].filter(w => txt.indexOf(w) >= 0),
        断りがある: txt.indexOf("まだ結論は出せません") >= 0,
      };
    }
    /* ★断りの有無は cf で判定する。診断タブの結論の箇条書きは
         「赤字の年がある」分岐でしか描かれないので、未入力では出ないことがある。
         **出ていない結論に断りを要求しない**（試験が状態に依存して落ちる）。 */
    add("X1_未入力のうちは結論を出さない",
        hits.cf.結論語.length === 0 && hits.check.結論語.length === 0
          && hits.cf.断りがある,
        hits, {結論語:[], "cfに断りがある":true});
  }catch(e){ add("X1_未入力のうちは結論を出さない", false, String(e), "例外なし"); }

  // X-1b: 入力後は、これまで通り結論を出す（抑制しすぎていないか）
  try{
    baseP(); PARAMS.house.buy = false; PARAMS.meta.blank = false;
    fillFlags(PARAMS); recalc();
    setTab("cf"); render(); await sleep(700);
    const sec = document.querySelector("main>section.on") || document.querySelector("section.on");
    const txt = (sec ? sec.innerText : "").replace(/\s+/g, " ");
    add("X1b_入力後は結論を出す",
        /尽きません|尽きます/.test(txt) && txt.indexOf("まだ結論は出せません") < 0,
        {結論が出ている:/尽きません|尽きます/.test(txt),
         断りが残っていない:txt.indexOf("まだ結論は出せません") < 0},
        {結論が出ている:true, 断りが残っていない:true});
  }catch(e){ add("X1b_入力後は結論を出す", false, String(e), "例外なし"); }

  /* ========== v30から維持すべき回帰 ========== */

  // 正常保存では主領域と控えが一致し、余計な警告を出さない
  try{
    try{ localStorage.clear(); }catch(e){}
    PARAMS = genericParams(); NOTICES = [];
    const ok = commitPlans([{name:"甲", params:clone(PARAMS)}]);
    const same = localStorage.getItem(STORE.plans) === localStorage.getItem(STORE.plansBak);
    add("回帰_正常保存で主領域と控えが一致・余計な警告なし",
        ok === true && same && notices().indexOf("planbakfail") < 0
          && notices().indexOf("planconflict") < 0,
        {保存:ok, 一致:same, 知らせ:notices()}, {保存:true, 一致:true, 知らせ:"警告なし"});
  }catch(e){ add("回帰_正常保存で主領域と控えが一致・余計な警告なし", false, String(e), "例外なし"); }

  // 構文不正でも控えから復旧（v30で入れた分）
  try{
    seed();
    localStorage.setItem(STORE.plans, "{壊れた");
    PLANS = []; NOTICES = []; loadPlans();
    add("回帰_構文不正から控えで復旧",
        (PLANS||[]).length === 2, {復旧後:(PLANS||[]).map(p=>p.name)}, {復旧後:["甲","乙"]});
  }catch(e){ add("回帰_構文不正から控えで復旧", false, String(e), "例外なし"); }

  // 正本の凍結と completionKeyForPath（v30で入れた分）
  try{
    const frozen = Object.isFrozen(READY_STEPS);
    const n0 = READY_STEPS.length;
    try{ READY_STEPS.push({key:"x", need:[]}); }catch(e){}
    const grew = READY_STEPS.length;
    if(grew > n0) READY_STEPS.splice(n0, grew - n0);       // ★必ず元へ戻す
    add("回帰_正本の凍結とcompletionKeyForPath",
        frozen && grew === n0
          && completionKeyForPath("family.ageH") === "preview"
          && completionKeyForPath("econ.inflation") === "decision",
        {isFrozen:frozen, 件数:grew + "（元 " + n0 + "）",
         ageH:completionKeyForPath("family.ageH")},
        {isFrozen:true, 件数:"変わらない", ageH:"preview"});
  }catch(e){ add("回帰_正本の凍結とcompletionKeyForPath", false, String(e), "例外なし"); }

  // 読み上げ名（v30で入れた分）を、タブ×状態で維持
  try{
    const nameOf = e => {
      const al = e.getAttribute("aria-label");
      if(al) return al.trim();
      if(e.id){
        const l = document.querySelector('label[for="' + CSS.escape(e.id) + '"]');
        if(l) return l.textContent.trim();
      }
      const p = e.closest("label");
      return p ? p.textContent.trim() : (e.textContent || "").trim();
    };
    const STATES = {
      "初期": () => { PARAMS = genericParams(); },
      "全部盛り": () => { PARAMS = genericParams(); PARAMS.family.hasSpouse = true;
        PARAMS.family.children = [{name:"第1子",birthYear:2016},{name:"第2子",birthYear:2019}];
        PARAMS.house.buy = true; PARAMS.house.price = 50000000;
        PARAMS.house.loans = [{name:"本人",amount:20000000,years:35,steps:[{y:1,rate:1}]},
                              {name:"配偶者",amount:15000000,years:30,steps:[{y:1,rate:1}]}]; },
    };
    let 違反 = 0, 名前なし = 0, db = 0, dbOk = 0; const 同名 = [];
    for(const st in STATES){
      STATES[st](); recalc(); await sleep(40);
      for(const t of ["params", "loan", "edu", "assets"]){
        setTab(t); render(); await sleep(60);
        const inp = [...document.querySelectorAll("input,select,textarea")].filter(e => e.offsetParent !== null);
        const all = [...document.querySelectorAll("input,select,textarea,button")].filter(e => e.offsetParent !== null);
        const iN = inp.map(nameOf), aN = all.map(nameOf);
        違反 += iN.filter(n => /[？?]|。|…|\n/.test(n)).length;
        名前なし += aN.filter(x => !x).length;
        const cnt = {}; aN.forEach(x => { if(x) cnt[x] = (cnt[x] || 0) + 1; });
        Object.entries(cnt).filter(p => p[1] > 1)
          .forEach(p => 同名.push(st + "／" + t + "：" + p[0].slice(0,28) + "×" + p[1]));
        const d = [...document.querySelectorAll("input[aria-describedby]")].filter(e => e.offsetParent !== null);
        db += d.length;
        dbOk += d.filter(e => String(e.getAttribute("aria-describedby")).split(/\s+/)
                  .every(id => id && document.getElementById(id))).length;
      }
    }
    add("回帰_読み上げ名（違反0・名前なし0・同名0・describedby参照実在）",
        違反 === 0 && 名前なし === 0 && 同名.length === 0 && db > 0 && dbOk === db,
        {違反:違反, 名前なし:名前なし, 同名:同名, describedby:db, 参照実在:dbOk},
        {違反:0, 名前なし:0, 同名:[], 参照実在:"全件"});
  }catch(e){ add("回帰_読み上げ名（違反0・名前なし0・同名0・describedby参照実在）", false, String(e), "例外なし"); }

  // 賃貸・資金一致購入は段階3（v30で入れた分）
  try{
    baseP(); PARAMS.house.buy = false; fillFlags(PARAMS); recalc();
    const rent = readiness().stage;
    baseP(); PARAMS.house.buy = true; PARAMS.house.buyAge = 45;
    PARAMS.house.price = 50000000; PARAMS.house.selfFund = 5000000; PARAMS.house.gift = 0;
    PARAMS.house.autoFitLoans = true;
    PARAMS.house.loans = [{name:"A", amount:40000000, years:35, steps:[{y:1,rate:1}]}];
    fitLoansOn(PARAMS); fillFlags(PARAMS); recalc();
    const buy = readiness().stage;
    add("回帰_賃貸と資金一致購入は段階3", rent === 3 && buy === 3,
        {賃貸:rent, 資金一致購入:buy}, {賃貸:3, 資金一致購入:3});
  }catch(e){ add("回帰_賃貸と資金一致購入は段階3", false, String(e), "例外なし"); }

  const passed = R.filter(x => x.ok).length;
  return {合計:R.length, 合格:passed, 不合格:R.length - passed,
          結果:R.map(x => (x.ok ? "○ " : "× ") + x.id), 詳細:R};
};
