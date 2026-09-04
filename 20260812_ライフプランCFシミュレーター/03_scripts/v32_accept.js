/* 汎用版 v32 の受入試験。
 *
 *  ChatGPT版のv31独立再レビュー（P1 4件・P2 2件）を全件再現したうえで、
 *  **v31で落ち v32で通る**形に書き下したもの。
 *  「厳しくしすぎていないか」を見る側の試験も同居させる（両版で通るのが正しい）。
 *
 *  使い方（ページと同一オリジンから）:
 *      const src = await fetch("../03_scripts/v32_accept.js").then(r=>r.text());
 *      (0,eval)(src); await __V32_ACCEPT__();
 *
 *  依存: なし（このファイル単体で動く）。対象HTMLを開いた状態で実行する。
 *
 *  ★負試験（Storage の故障注入・ロックの偽装）は**必ず元へ戻す**。
 *  ★v31でも走るように、v32で足した関数・キーは存在を確かめてから使う。
 */
window.__V32_ACCEPT__ = async function(){
  const R = [];
  const add = (id, ok, observed, expected) => R.push({id, ok: !!ok, observed, expected});
  const sleep = ms => new Promise(r => setTimeout(r, ms));
  const ids = () => (typeof NOTICES !== "undefined" ? NOTICES : []).map(n => n.id);
  const P0 = () => { PARAMS = genericParams(); return clone(PARAMS); };
  const names = () => (typeof PLANS !== "undefined" && PLANS ? PLANS : []).map(p => p.name);
  const KEY = k => (typeof STORE !== "undefined" && STORE[k]) ? STORE[k] : null;
  const setRev = v => { try{ PLANS_REV = v; }catch(e){} };

  /** setItem に故障を注入して fn を実行し、必ず元へ戻す。 */
  const withSet = async (fault, fn) => {
    const proto = Storage.prototype, orig = proto.setItem;
    proto.setItem = function(k, v){ return fault.call(this, k, v, orig); };
    try{ return await fn(); } finally{ proto.setItem = orig; }
  };
  /** getItem に故障を注入して fn を実行し、必ず元へ戻す。 */
  const withGet = async (fault, fn) => {
    const proto = Storage.prototype, orig = proto.getItem;
    proto.getItem = function(k){ return fault.call(this, k, orig); };
    try{ return await fn(); } finally{ proto.getItem = orig; }
  };
  const clearAll = () => { try{ localStorage.clear(); }catch(e){} NOTICES = []; };

  /* ===== A. 保存の読み込み：初回・正当な空・破損・読取不能 ===== */

  // A1: 初回利用（主領域も控えも無い）は**破損扱いしない**
  //     v31実測: planbroken（赤）が出る。依頼者の実機スクリーンショットにも出ていた。
  try{
    clearAll(); PLANS = [{name:"のこり", params:P0()}];
    loadPlans();
    const bad = ids().filter(x => ["planbroken","planrecover","planunreadable"].indexOf(x) >= 0);
    add("A1_初回利用を破損扱いしない",
        names().length === 0 && bad.length === 0,
        {件数:names().length, 破損系の知らせ:bad, 全知らせ:ids()},
        {件数:0, 破損系の知らせ:[]});
  }catch(e){ add("A1_初回利用を破損扱いしない", false, String(e), "例外なし"); }

  // A2: 明示的な `[]` も静かに0件（過剰反応の確認）
  try{
    clearAll(); localStorage.setItem(KEY("plans"), "[]");
    PLANS = [{name:"のこり", params:P0()}]; NOTICES = []; loadPlans();
    const bad = ids().filter(x => ["planbroken","planrecover"].indexOf(x) >= 0);
    add("A2_明示的な空も破損扱いしない",
        names().length === 0 && bad.length === 0,
        {件数:names().length, 破損系:bad}, {件数:0, 破損系:[]});
  }catch(e){ add("A2_明示的な空も破損扱いしない", false, String(e), "例外なし"); }

  // A3: 主領域だけ無く控えがある → 復旧して知らせる
  try{
    clearAll(); PARAMS = genericParams();
    const ok = commitPlans([{name:"甲", params:P0()},{name:"乙", params:P0()}]);
    localStorage.removeItem(KEY("plans"));
    PLANS = []; NOTICES = []; loadPlans();
    add("A3_主領域欠損・控えありで復旧",
        ok === true && names().join(",") === "甲,乙" && ids().indexOf("planrecover") >= 0,
        {復旧後:names(), 知らせ:ids()}, {復旧後:["甲","乙"], 知らせ:"planrecover"});
  }catch(e){ add("A3_主領域欠損・控えありで復旧", false, String(e), "例外なし"); }

  // A4: 意味的破損（4種）から復旧
  for(const bad of ['{}','null','"文字列"','[{"name":"甲","params":null}]']){
    try{
      clearAll(); PARAMS = genericParams();
      commitPlans([{name:"甲", params:P0()},{name:"乙", params:P0()}]);
      localStorage.setItem(KEY("plans"), bad);
      PLANS = []; NOTICES = []; loadPlans();
      add("A4_意味的破損から復旧【" + bad.slice(0,20) + "】",
          names().join(",") === "甲,乙" && ids().indexOf("planrecover") >= 0,
          {復旧後:names(), 知らせ:ids()}, {復旧後:["甲","乙"]});
    }catch(e){ add("A4_意味的破損から復旧【" + bad.slice(0,20) + "】", false, String(e), "例外なし"); }
  }

  // A5: 読取不能は「未保存」と別の顔をする
  try{
    clearAll(); PARAMS = genericParams();
    commitPlans([{name:"甲", params:P0()}]);
    NOTICES = []; PLANS = [];
    await withGet(function(k, orig){
      if(k === KEY("plans")) throw new Error("読めません");
      return orig.call(this, k);
    }, async () => { loadPlans(); });
    add("A5_読取不能を未保存と区別する", ids().length > 0,
        {知らせ:ids(), 件数:names().length}, {知らせ:"1件以上"});
  }catch(e){ add("A5_読取不能を未保存と区別する", false, String(e), "例外なし"); }

  /* ===== B. 控えの保全（P1-2） ===== */

  // B1: 控えが静かに壊れたら、**旧控えを維持する**
  //     v31実測: backup が [] になり、最後の正常な控えを失う
  //  ★故障は**1回だけ**にする。毎回壊れる故障にすると、旧控えを書き戻す操作も
  //    同じように壊れるので、**どんな実装でも旧控えは維持できない**（＝満たせない試験になる）。
  //    最初に毎回壊す形で書いてしまい、自分の修正を不合格にした。
  try{
    clearAll(); PARAMS = genericParams();
    const old = JSON.stringify([{name:"旧", params:P0()}]);
    localStorage.setItem(KEY("plans"), old);
    localStorage.setItem(KEY("plansBak"), old);
    PLANS = JSON.parse(old); setRev(old); NOTICES = [];
    let once = true;
    let ok = await withSet(function(k, v, orig){
      if(k === KEY("plansBak") && once){ once = false; return orig.call(this, k, "[]"); }
      return orig.call(this, k, v);
    }, async () => commitPlans([{name:"新", params:P0()}]));
    const bak = localStorage.getItem(KEY("plansBak"));
    const bakNames = bak ? JSON.parse(bak).map(p => p.name) : null;
    add("B1_控えが壊れたら旧控えを維持する",
        ok === true && Array.isArray(bakNames) && bakNames.join(",") === "旧"
          && ids().indexOf("planbakfail") >= 0,
        {保存:ok, 控え:bakNames, 主領域:JSON.parse(localStorage.getItem(KEY("plans"))||"[]").map(p=>p.name), 知らせ:ids()},
        {保存:true, 控え:["旧"], 知らせ:"planbakfail"});
  }catch(e){ add("B1_控えが壊れたら旧控えを維持する", false, String(e), "例外なし"); }

  // B2: 旧控えも戻せないときは pending/marker を残し、次回起動で作り直す
  //  ★ここは**毎回壊れる**故障にする（＝旧控えも書き戻せない状況）。
  //    書込みを「無視」する故障だと**旧控えがそのまま残る**ので印は要らず、
  //    印を期待する試験は通らない（最初にそれをやった）。
  //    「壊れて別の値になる」と「書けずに元のまま」は別の故障。
  try{
    clearAll(); PARAMS = genericParams();
    const old = JSON.stringify([{name:"旧", params:P0()}]);
    localStorage.setItem(KEY("plans"), old);
    localStorage.setItem(KEY("plansBak"), old);
    PLANS = JSON.parse(old); setRev(old); NOTICES = [];
    await withSet(function(k, v, orig){
      if(k === KEY("plansBak")) return orig.call(this, k, "[]");  // 毎回 [] に化ける
      return orig.call(this, k, v);
    }, async () => commitPlans([{name:"新", params:P0()}]));
    const marked = KEY("plansMarker") ? localStorage.getItem(KEY("plansMarker")) : null;
    // 次回起動：正常な主領域から控えを作り直す
    NOTICES = []; PLANS = []; loadPlans();
    const bak = localStorage.getItem(KEY("plansBak"));
    const bakNames = bak ? JSON.parse(bak).map(p => p.name) : null;
    add("B2_控えを戻せなければ印を残し次回起動で作り直す",
        !!marked && Array.isArray(bakNames) && bakNames.join(",") === "新"
          && (KEY("plansMarker") ? !localStorage.getItem(KEY("plansMarker")) : true),
        {印が残った:!!marked, 起動後の控え:bakNames, 印は消えたか:!localStorage.getItem(KEY("plansMarker")||"x"), 知らせ:ids()},
        {印が残った:true, 起動後の控え:["新"], 印は消えたか:true});
  }catch(e){ add("B2_控えを戻せなければ印を残し次回起動で作り直す", false, String(e), "例外なし"); }

  /* ===== C. 複数タブ競合（P1-3） ===== */

  const setupRace = () => {
    clearAll(); PARAMS = genericParams();
    const old = JSON.stringify([{name:"旧", params:P0()}]);
    const other = JSON.stringify([{name:"旧", params:P0()},{name:"別タブ", params:P0()}]);
    localStorage.setItem(KEY("plans"), old);
    localStorage.setItem(KEY("plansBak"), old);
    PLANS = JSON.parse(old); setRev(old); NOTICES = [];
    return {old, other};
  };

  // C1: 窓A（自分が保存を始める前に、別タブが書いていた）
  //     v31実測: 保存 true・primary が [旧,このタブ]（別タブの保存を消した）
  //  ★別タブの書込みは、**自分の commit の外**で起きる形にする。
  //    localStorage の書込みは同期でストレージ・ミューテックスに守られるため、
  //    自分の `setItem` の**実行中**に別タブの書込みが割り込むことは実際には起こらない。
  //    「setItem の内側で他タブが書く」故障注入は、起こり得ない順序を作ってしまう。
  //    現実に起こる窓は「読んだあと・書く前」で、それを revision（保存の起点）で止める。
  try{
    const {other} = setupRace();
    localStorage.setItem(KEY("plans"), other);   // 別タブが先に保存した
    NOTICES = [];
    const ok = commitPlans([{name:"旧", params:P0()},{name:"このタブ", params:P0()}]);
    const prim = JSON.parse(localStorage.getItem(KEY("plans"))||"[]").map(p=>p.name);
    add("C1_窓A_別タブの保存を上書きしない",
        ok === false && prim.join(",") === "旧,別タブ" && names().join(",") === "旧,別タブ"
          && ids().indexOf("planconflict") >= 0,
        {保存:ok, 主領域:prim, メモリ:names(), 知らせ:ids()},
        {保存:false, 主領域:["旧","別タブ"], メモリ:["旧","別タブ"], 知らせ:"planconflict"});
  }catch(e){ add("C1_窓A_別タブの保存を上書きしない", false, String(e), "例外なし"); }

  // C2: 窓B（読戻し成功後、控えを更新する前に別タブが書く）
  //     v31実測: primary [旧,別タブ] / backup [旧,このタブ] / memory [旧,このタブ] の三者不一致
  try{
    const {other} = setupRace();
    let gets = 0;
    const ok = await withGet(function(k, orig){
      const v = orig.call(this, k);
      if(k === KEY("plans")){
        gets++;
        if(gets === 2){ Storage.prototype.setItem.call(localStorage, k, other); }
      }
      return v;
    }, async () => commitPlans([{name:"旧", params:P0()},{name:"このタブ", params:P0()}]));
    const prim = JSON.parse(localStorage.getItem(KEY("plans"))||"[]").map(p=>p.name);
    const bak  = JSON.parse(localStorage.getItem(KEY("plansBak"))||"[]").map(p=>p.name);
    add("C2_窓B_primary=backup=memoryへ揃える",
        ok === false && prim.join(",") === bak.join(",") && prim.join(",") === names().join(",")
          && prim.indexOf("別タブ") >= 0,
        {保存:ok, 主領域:prim, 控え:bak, メモリ:names(), 知らせ:ids()},
        {保存:false, "三者一致":true, 主領域:"別タブを含む"});
  }catch(e){ add("C2_窓B_primary=backup=memoryへ揃える", false, String(e), "例外なし"); }

  // C3: 期限内の他タブのロックがあれば、自分の保存を見送る
  try{
    setupRace();
    if(!KEY("plansLock")){ add("C3_期限内ロックなら見送る", false, "ロックキーが無い", "あり"); }
    else{
      localStorage.setItem(KEY("plansLock"), JSON.stringify({id:"other-tab", until:Date.now()+60000}));
      NOTICES = [];
      const ok = commitPlans([{name:"旧", params:P0()},{name:"このタブ", params:P0()}]);
      const prim = JSON.parse(localStorage.getItem(KEY("plans"))||"[]").map(p=>p.name);
      add("C3_期限内ロックなら見送る",
          ok === false && prim.join(",") === "旧" && ids().indexOf("planlock") >= 0,
          {保存:ok, 主領域:prim, 知らせ:ids()}, {保存:false, 主領域:["旧"], 知らせ:"planlock"});
      localStorage.removeItem(KEY("plansLock"));
    }
  }catch(e){ add("C3_期限内ロックなら見送る", false, String(e), "例外なし"); }

  // C4: 期限切れのロックは回収できる（緩めすぎ／締めすぎの両方の確認）
  try{
    setupRace();
    if(!KEY("plansLock")){ add("C4_期限切れロックは回収できる", false, "ロックキーが無い", "あり"); }
    else{
      localStorage.setItem(KEY("plansLock"), JSON.stringify({id:"other-tab", until:Date.now()-1}));
      NOTICES = [];
      const ok = commitPlans([{name:"旧", params:P0()},{name:"このタブ", params:P0()}]);
      const prim = JSON.parse(localStorage.getItem(KEY("plans"))||"[]").map(p=>p.name);
      add("C4_期限切れロックは回収できる",
          ok === true && prim.join(",") === "旧,このタブ",
          {保存:ok, 主領域:prim, 知らせ:ids()}, {保存:true, 主領域:["旧","このタブ"]});
    }
  }catch(e){ add("C4_期限切れロックは回収できる", false, String(e), "例外なし"); }

  // C5: 別タブが不正な内容を書いたら、書く前の値へ戻す（他タブ扱いにしない）
  try{
    const {old} = setupRace();
    const ok = await withSet(function(k, v, orig){
      if(k === KEY("plans") && String(v).indexOf('"このタブ"') >= 0)
        return orig.call(this, k, "{壊れた");
      return orig.call(this, k, v);
    }, async () => commitPlans([{name:"旧", params:P0()},{name:"このタブ", params:P0()}]));
    add("C5_別タブが不正値なら書く前へ戻す",
        ok === false && localStorage.getItem(KEY("plans")) === old,
        {保存:ok, 主領域が元に戻ったか:localStorage.getItem(KEY("plans")) === old},
        {保存:false, 主領域が元に戻ったか:true});
  }catch(e){ add("C5_別タブが不正値なら書く前へ戻す", false, String(e), "例外なし"); }

  // C6: 競合が無ければ普通に保存できる（締めすぎの確認）
  try{
    setupRace(); NOTICES = [];
    const ok = commitPlans([{name:"旧", params:P0()},{name:"このタブ", params:P0()}]);
    const prim = JSON.parse(localStorage.getItem(KEY("plans"))||"[]").map(p=>p.name);
    const bak  = JSON.parse(localStorage.getItem(KEY("plansBak"))||"[]").map(p=>p.name);
    add("C6_競合が無ければ普通に保存できる",
        ok === true && prim.join(",") === "旧,このタブ" && bak.join(",") === "旧,このタブ"
          && ids().indexOf("planconflict") < 0 && ids().indexOf("planlock") < 0,
        {保存:ok, 主領域:prim, 控え:bak, 知らせ:ids()},
        {保存:true, 主領域:["旧","このタブ"], 控え:["旧","このタブ"], 知らせ:"競合系なし"});
  }catch(e){ add("C6_競合が無ければ普通に保存できる", false, String(e), "例外なし"); }

  /* ===== D. 未入力で肯定結論を出さない（P1-4 と v31の回帰） ===== */

  try{
    clearAll(); PARAMS = blankParams(); recalc();
    const hits = {};
    for(const t of ["loan","cf","check"]){
      setTab(t); render(); await sleep(700);
      const sec = document.querySelector("main>section.on");
      const txt = (sec ? sec.innerText : "").replace(/\s+/g, " ");
      hits[t] = ["要件を満たしています","控除される総額","適用できます",
                 "尽きません","破綻ではありません","乗り切れます"].filter(w => txt.indexOf(w) >= 0);
    }
    add("D1_未入力で肯定結論を出さない（住宅ローン控除・CF・診断）",
        hits.loan.length === 0 && hits.cf.length === 0 && hits.check.length === 0,
        hits, {すべて:[]});
  }catch(e){ add("D1_未入力で肯定結論を出さない（住宅ローン控除・CF・診断）", false, String(e), "例外なし"); }

  // D2: 入力すれば控除の判定が出る（抑制しすぎの確認）
  try{
    PARAMS = genericParams(); PARAMS.meta.blank = false;
    PARAMS.family.ageH = 40; PARAMS.house.buy = true; PARAMS.house.buyAge = 45;
    PARAMS.house.price = 50000000; PARAMS.house.selfFund = 5000000;
    PARAMS.house.autoFitLoans = true;
    PARAMS.house.loans = [{name:"A", amount:40000000, years:35, steps:[{y:1,rate:1}]}];
    fitLoansOn(PARAMS); recalc();
    setTab("loan"); render(); await sleep(700);
    const sec = document.querySelector("main>section.on");
    const txt = (sec ? sec.innerText : "").replace(/\s+/g, " ");
    add("D2_入力後は控除の判定が出る",
        /要件を満たしています|満たしていない要件があります/.test(txt)
          && txt.indexOf("まだ判定できません") < 0,
        {判定が出ている:/要件を満たしています|満たしていない要件があります/.test(txt),
         断りが残っていない:txt.indexOf("まだ判定できません") < 0},
        {判定が出ている:true, 断りが残っていない:true});
  }catch(e){ add("D2_入力後は控除の判定が出る", false, String(e), "例外なし"); }

  /* ===== E. 説明ボタン名がデータで変わらない（P2-1） ===== */

  try{
    const collect = () => {
      const out = {};
      for(const t of TABS.map(x => x[0])){
        setTab(t); render();
        const sec = document.querySelector("main>section.on");
        if(!sec) continue;
        [...sec.querySelectorAll('button[aria-controls^="pop-"]')].forEach((b, i) => {
          out[t + "|" + (b.getAttribute("aria-controls") || b.id || i)] =
            b.getAttribute("aria-label") || b.textContent.trim();
        });
      }
      return out;
    };
    clearAll();
    PARAMS = genericParams(); PARAMS.meta.blank = false;
    PARAMS.family.hasSpouse = true;
    PARAMS.family.children = [{name:"第1子", birthYear:2020}];
    PARAMS.house.buy = true; PARAMS.house.buyAge = 45;
    PARAMS.house.price = 50000000; PARAMS.house.selfFund = 5000000;
    fitLoansOn(PARAMS); recalc();
    const before = collect();
    // 世帯人数・年収・年金・物件・維持費・子ども数を広く変える
    PARAMS.income.hBase = 8000000;
    PARAMS.income.hTable = [{age:PARAMS.family.ageH, amount:8000000, rate:2}];
    PARAMS.income.wBase = 4000000;
    PARAMS.living.table = [{age:PARAMS.family.ageH, amount:6000000, rate:1}];
    PARAMS.house.price = 90000000; PARAMS.house.selfFund = 15000000;
    PARAMS.house.maintFee = 45000; PARAMS.house.repairFee = 30000;
    PARAMS.econ.inflation = 4; PARAMS.econ.investRate = 6;
    PARAMS.saving.nisaMonthlyH = 200000;
    PARAMS.family.children = [{name:"第1子", birthYear:2015},{name:"第2子", birthYear:2020},
                              {name:"第3子", birthYear:2022}];
    fitLoansOn(PARAMS); recalc();
    const after = collect();
    const changed = Object.keys(before)
      .filter(k => k in after && after[k] !== before[k])
      .map(k => ({key:k, 前:String(before[k]).slice(0,44), 後:String(after[k]).slice(0,44)}));
    add("E1_広いデータ変異で説明ボタン名が変わらない", changed.length === 0,
        {調べた数:Object.keys(before).length, 変わった:changed}, {変わった:[]});
  }catch(e){ add("E1_広いデータ変異で説明ボタン名が変わらない", false, String(e), "例外なし"); }

  /* ===== F. v31から維持すべき回帰 ===== */

  const fillFlags = P => READY_STEPS.forEach(s => (s.need || []).forEach(n => {
    if(!n[2] || n[2](P)) P.meta.inputState[n[0]] = {confirmed:true};
  }));
  const baseP = () => {
    PARAMS = genericParams(); PARAMS.meta.inputState = {}; PARAMS.meta.blank = false;
    PARAMS.family.ageH = 40; PARAMS.income.hBase = 6000000;
    PARAMS.income.hTable = [{age:40, amount:6000000, rate:0}];
    PARAMS.living.table = [{age:40, amount:3000000, rate:0}];
    PARAMS.econ.deposit = 10000000; PARAMS.house.rentNow = 1200000;
    PARAMS.living.insurance = 100000; PARAMS.saving.nisaMonthlyH = 30000;
    PARAMS.retire.retireAgeH = 65; PARAMS.econ.inflation = 1; PARAMS.econ.investRate = 3;
  };

  try{
    baseP(); PARAMS.house.buy = true; PARAMS.house.buyAge = 35;
    PARAMS.house.price = 50000000; PARAMS.house.selfFund = 5000000; PARAMS.house.gift = 0;
    PARAMS.house.autoFitLoans = false;
    PARAMS.house.loans = [{name:"A", amount:25000000, years:30, steps:[{y:1,rate:1}]}];
    fillFlags(PARAMS); recalc();
    const h = housingReadiness(PARAMS), r = readiness();
    add("F1_取得済み持ち家は過去の資金差で落とさない", h.level === "na" && r.stage === 3,
        {住宅:h.level, stage:r.stage}, {住宅:"na", stage:3});
  }catch(e){ add("F1_取得済み持ち家は過去の資金差で落とさない", false, String(e), "例外なし"); }

  try{
    baseP(); PARAMS.house.buy = true; PARAMS.house.buyAge = 45;
    PARAMS.house.price = 50000000; PARAMS.house.selfFund = 5000000; PARAMS.house.gift = 0;
    PARAMS.house.autoFitLoans = false;
    PARAMS.house.loans = [{name:"A", amount:10000000, years:35, steps:[{y:1,rate:1}]}];
    fillFlags(PARAMS); recalc();
    const h = housingReadiness(PARAMS), r = readiness();
    clearAll(); PLANS = [];
    const saved = commitPlans([{name:"将来購入", params:clone(PARAMS)}]);
    add("F2_将来購入の資金不足は段階2・保存可",
        h.level === "insufficient" && r.stage < 3 && saved === true,
        {住宅:h.level, stage:r.stage, 保存:saved}, {住宅:"insufficient", stage:"3未満", 保存:true});
  }catch(e){ add("F2_将来購入の資金不足は段階2・保存可", false, String(e), "例外なし"); }

  try{
    baseP(); PARAMS.work.typeH = "none"; PARAMS.income.hBase = 0;
    PARAMS.income.hTable = [{age:40, amount:0, rate:0}]; PARAMS.house.buy = false;
    fillFlags(PARAMS); recalc();
    const a = readiness().stage, av = isUsable("income.hBase", PARAMS);
    baseP(); PARAMS.work.typeH = "employee"; PARAMS.income.hBase = 0;
    PARAMS.income.hTable = [{age:40, amount:0, rate:0}]; PARAMS.house.buy = false;
    fillFlags(PARAMS); recalc();
    const b = readiness().stage, bv = isUsable("income.hBase", PARAMS);
    add("F3_無職の0円は有効・会社員の0円は無効",
        av === true && a === 3 && bv === false && b < 3,
        {無職:{isUsable:av, stage:a}, 会社員:{isUsable:bv, stage:b}},
        {無職:{isUsable:true, stage:3}, 会社員:{isUsable:false, stage:"3未満"}});
  }catch(e){ add("F3_無職の0円は有効・会社員の0円は無効", false, String(e), "例外なし"); }

  try{
    baseP(); recalc();
    const cand = clone(PARAMS); cand.family.ageH = 55;
    cand.meta.inputState = {"family.ageH":{confirmed:true}};
    PARAMS.meta.inputState = {};
    const f = readinessFacts(cand)["family.ageH"];
    add("F4_readinessFactsは候補Pだけを評価する",
        f && f.confirmed === true && f.valid === true,
        {返り値:f, グローバル年齢:PARAMS.family.ageH, 候補年齢:cand.family.ageH},
        {confirmed:true, valid:true});
  }catch(e){ add("F4_readinessFactsは候補Pだけを評価する", false, String(e), "例外なし"); }

  try{
    const nameOf = e => {
      const al = e.getAttribute("aria-label");
      if(al) return al.trim();
      if(e.id){ const l = document.querySelector('label[for="' + CSS.escape(e.id) + '"]');
                if(l) return l.textContent.trim(); }
      const p = e.closest("label");
      return p ? p.textContent.trim() : (e.textContent || "").trim();
    };
    let 違反 = 0, 名前なし = 0, db = 0, dbOk = 0; const 同名 = [];
    const STATES = {
      "初期": () => { PARAMS = genericParams(); },
      "全部盛り": () => { PARAMS = genericParams(); PARAMS.family.hasSpouse = true;
        PARAMS.family.children = [{name:"第1子",birthYear:2016},{name:"第2子",birthYear:2019}];
        PARAMS.house.buy = true; PARAMS.house.price = 50000000;
        PARAMS.house.loans = [{name:"本人",amount:20000000,years:35,steps:[{y:1,rate:1}]},
                              {name:"配偶者",amount:15000000,years:30,steps:[{y:1,rate:1}]}]; },
    };
    for(const st in STATES){
      STATES[st](); recalc(); await sleep(40);
      for(const t of ["params","loan","edu","assets"]){
        setTab(t); render(); await sleep(60);
        const inp = [...document.querySelectorAll("input,select,textarea")].filter(e => e.offsetParent !== null);
        const all = [...document.querySelectorAll("input,select,textarea,button")].filter(e => e.offsetParent !== null);
        const iN = inp.map(nameOf), aN = all.map(nameOf);
        違反 += iN.filter(n => /[？?]|。|…|\n/.test(n)).length;
        名前なし += aN.filter(x => !x).length;
        const cnt = {}; aN.forEach(x => { if(x) cnt[x] = (cnt[x] || 0) + 1; });
        Object.entries(cnt).filter(p => p[1] > 1)
          .forEach(p => 同名.push(st + "／" + t + "：" + p[0].slice(0,26) + "×" + p[1]));
        const d = [...document.querySelectorAll("input[aria-describedby]")].filter(e => e.offsetParent !== null);
        db += d.length;
        dbOk += d.filter(e => String(e.getAttribute("aria-describedby")).split(/\s+/)
                  .every(id => id && document.getElementById(id))).length;
      }
    }
    add("F5_読み上げ名（違反0・名前なし0・同名0・describedby参照実在）",
        違反 === 0 && 名前なし === 0 && 同名.length === 0 && db > 0 && dbOk === db,
        {違反:違反, 名前なし:名前なし, 同名:同名, describedby:db, 参照実在:dbOk},
        {違反:0, 名前なし:0, 同名:[], 参照実在:"全件"});
  }catch(e){ add("F5_読み上げ名（違反0・名前なし0・同名0・describedby参照実在）", false, String(e), "例外なし"); }

  // F6: 暗黙の type="submit" を残さない（V87レビューで自分にも当てると書いた分）
  try{
    setTab("params"); render(); await sleep(200);
    const btns = [...document.querySelectorAll("button")];
    const implicit = btns.filter(e => !e.getAttribute("type"));
    add("F6_暗黙のtype=submitを残さない", implicit.length === 0,
        {ボタン総数:btns.length, type未指定:implicit.length,
         form要素:document.querySelectorAll("form").length},
        {type未指定:0});
  }catch(e){ add("F6_暗黙のtype=submitを残さない", false, String(e), "例外なし"); }

  // F7: 正本の凍結（v30から）
  try{
    const frozen = Object.isFrozen(READY_STEPS);
    const n0 = READY_STEPS.length;
    try{ READY_STEPS.push({key:"x", need:[]}); }catch(e){}
    const grew = READY_STEPS.length;
    if(grew > n0) READY_STEPS.splice(n0, grew - n0);      // ★必ず元へ戻す
    add("F7_準備度の正本が凍結されている", frozen && grew === n0,
        {isFrozen:frozen, 件数:grew + "（元 " + n0 + "）"}, {isFrozen:true, 件数:"変わらない"});
  }catch(e){ add("F7_準備度の正本が凍結されている", false, String(e), "例外なし"); }

  const passed = R.filter(x => x.ok).length;
  return {合計:R.length, 合格:passed, 不合格:R.length - passed,
          結果:R.map(x => (x.ok ? "○ " : "× ") + x.id), 詳細:R};
};
