/* 汎用版 v30 の受入試験。
 *
 *  ★v29（修正前）で**落ち**、v30（修正後）で**通る**ことを確かめるために作る。
 *    v27で「所有者を変えると差が出る」という緩い条件にしたせいで
 *    `argsW.miscInc` の付け忘れを合格させた。条件は**直した向きまで縛る**。
 *
 *  ★B群は「タブ×状態」で回す（ChatGPT版V82の査読から）。
 *    V82は13経路のa11y監査と4分岐のE2Eを別々に回しており、
 *    E2Eが作った状態の上で監査を回していなかったため、
 *    「子どもを追加」1回で自前の監査が不合格になる欠陥が残っていた。
 *    経路だけを網羅しても、状態を渡さなければ交差部分は無検査になる。
 *
 *  使い方: ブラウザのコンソールに貼り付けて __V30_ACCEPT__() を呼ぶ（Promiseを返す）。
 *  v29でも走るように、v30で足した関数・キーは存在を確かめてから使う。
 *
 *  実測（2026-09-02・HTTP配信）:
 *      v29 = 5/13 合格 ／ v30 = 13/13 合格
 *
 *  ★D2・D3 は v29 でも合格する。これは「厳しくしすぎていないか」を見る側の試験で、
 *    両方の版で通るのが正しい（v27で不変条件を全プランに課して
 *    「手入力を保存できない」をやった再発を防ぐため）。
 *  ★最初の測定では v29 を 3/13 と読んだが、これは**こちらの試験の汚染**だった。
 *    C2の負試験（凍結されていない配列に push する）を**元へ戻していなかった**ため、
 *    `need:[]` の段階が1つ増えて D群の stage が 3→4 になっていた。
 *    **負試験は必ず元へ戻す。戻さないと、自分の修正を実際より良く見せてしまう。**
 */
window.__V30_ACCEPT__ = async function(){
  const R = [];
  const add = (id, ok, observed, expected) => R.push({id, ok: !!ok, observed, expected});
  const sleep = ms => new Promise(r => setTimeout(r, ms));

  const nameOf = e => {
    const al = e.getAttribute("aria-label");
    if(al) return al.trim();
    if(e.id){
      const l = document.querySelector('label[for="' + CSS.escape(e.id) + '"]');
      if(l) return l.textContent.trim();
    }
    const p = e.closest("label");
    if(p) return p.textContent.trim();
    return (e.textContent || "").trim();
  };

  /* ============ A. 保存の復旧（ChatGPT版 v29レビューの唯一の指摘） ============ */

  // A-1: 主領域が壊れていたら控えから戻す
  //      v29実測: 復旧後 []（2件保存していたのに、黙って全消失）
  try{
    localStorage.clear(); PARAMS = genericParams();
    const okSave = commitPlans([{name:"甲", params:clone(PARAMS)},
                                {name:"乙", params:clone(PARAMS)}]);
    localStorage.setItem(STORE.plans, "{壊れた");
    PLANS = []; loadPlans();
    const names = (PLANS || []).map(p => p.name);
    add("A1_主領域が壊れたら控えから戻す",
        okSave === true && names.length === 2 && names[0] === "甲" && names[1] === "乙",
        {保存:okSave, 復旧後:names}, {保存:true, 復旧後:["甲","乙"]});
  }catch(e){ add("A1_主領域が壊れたら控えから戻す", false, String(e), "例外なし"); }

  // A-2: 控えも壊れていたら、空にはするが**黙ってはいない**
  //      v29実測: 知らせが増えた false（理由も告げずに消える）
  try{
    localStorage.clear(); PARAMS = genericParams();
    commitPlans([{name:"甲", params:clone(PARAMS)}]);
    localStorage.setItem(STORE.plans, "{壊れた");
    if(STORE.plansBak) localStorage.setItem(STORE.plansBak, "{これも壊れた");
    const before = JSON.stringify(typeof NOTICES !== "undefined" ? NOTICES : {});
    PLANS = []; loadPlans();
    const after = JSON.stringify(typeof NOTICES !== "undefined" ? NOTICES : {});
    add("A2_控えも壊れていたら知らせる", PLANS.length === 0 && after !== before,
        {件数:PLANS.length, 知らせが増えた:after !== before},
        {件数:0, 知らせが増えた:true});
  }catch(e){ add("A2_控えも壊れていたら知らせる", false, String(e), "例外なし"); }

  // A-3: 控えが無いときに、壊れた主領域を**勝手に消さない**（書き出す機会を残す）
  try{
    localStorage.clear(); PLANS = [];
    localStorage.setItem(STORE.plans, "{壊れた"); loadPlans();
    const raw = localStorage.getItem(STORE.plans);
    add("A3_控えが無ければ壊れた内容を消さない", raw === "{壊れた",
        {残っている値:raw}, {残っている値:"{壊れた"});
  }catch(e){ add("A3_控えが無ければ壊れた内容を消さない", false, String(e), "例外なし"); }

  // A-4: 正常に保存し続けたとき、控えも最新に保たれる（控えが古いままにならない）
  try{
    localStorage.clear(); PARAMS = genericParams();
    commitPlans([{name:"甲", params:clone(PARAMS)}]);
    const ok = commitPlans([{name:"甲", params:clone(PARAMS)},
                            {name:"乙", params:clone(PARAMS)}]);
    PLANS = []; loadPlans();
    add("A4_正常時は控えも最新に保たれる", ok === true && PLANS.length === 2,
        {保存:ok, 読み直し件数:PLANS.length}, {保存:true, 読み直し件数:2});
  }catch(e){ add("A4_正常時は控えも最新に保たれる", false, String(e), "例外なし"); }

  /* ============ B. 入力欄の読み上げ名（V82の査読を自分に当てて発見） ============ */

  const STATES = {
    "初期": () => { PARAMS = genericParams(); },
    "全部盛り": () => { PARAMS = genericParams(); PARAMS.family.hasSpouse = true;
      PARAMS.family.children = [{name:"第1子",birthYear:2016},{name:"第2子",birthYear:2019}];
      PARAMS.house.buy = true; PARAMS.house.price = 50000000;
      PARAMS.house.loans = [{name:"本人",amount:20000000,years:35,steps:[{y:1,rate:1}]},
                            {name:"配偶者",amount:15000000,years:30,steps:[{y:1,rate:1}]}]; },
  };
  const TABS_B = ["params", "loan", "edu", "assets"];

  try{
    let 欄 = 0, 違反 = 0, 名前なし = 0, db = 0, dbOk = 0;
    const 違反例 = [], 同名 = [];
    for(const st in STATES){
      STATES[st](); recalc(); await sleep(40);
      for(const t of TABS_B){
        setTab(t); render(); await sleep(50);
        const inp = [...document.querySelectorAll("input,select,textarea")]
                      .filter(e => e.offsetParent !== null);
        const all = [...document.querySelectorAll("input,select,textarea,button")]
                      .filter(e => e.offsetParent !== null);
        const iN = inp.map(nameOf), aN = all.map(nameOf);
        欄 += inp.length;
        iN.forEach(n => {
          if(/[？?]|。|…|\n/.test(n)){
            違反++;
            if(違反例.length < 4) 違反例.push(st + "／" + t + "：" + n.slice(0,40).replace(/\n/g,"\\n"));
          }
        });
        名前なし += aN.filter(x => !x).length;
        const cnt = {}; aN.forEach(x => { if(x) cnt[x] = (cnt[x] || 0) + 1; });
        Object.entries(cnt).filter(p => p[1] > 1)
          .forEach(p => 同名.push(st + "／" + t + "：" + p[0].slice(0,30) + "×" + p[1]));
        const d = [...document.querySelectorAll("input[aria-describedby]")]
                    .filter(e => e.offsetParent !== null);
        db += d.length;
        dbOk += d.filter(e => String(e.getAttribute("aria-describedby")).split(/\s+/)
                  .every(id => id && document.getElementById(id))).length;
      }
    }
    // B-1: 名前に「？」・補足文・改行が入らない　v29実測: 20件
    add("B1_入力欄の名前に？と補足文が入らない", 違反 === 0,
        {調べた欄:欄, 違反:違反, 例:違反例}, {違反:0});
    // B-2: 補足は捨てずに aria-describedby で参照する　v29実測: 0件（＝名前に混ざっていた）
    add("B2_補足はaria-describedbyで参照される", db > 0 && dbOk === db,
        {describedby付き:db, 参照先が実在:dbOk}, {describedby付き:"1件以上", 参照先が実在:"全件"});
    // B-3: 短くした結果、同名が増えていないか
    //      ★これが saving.nisaRate / saving.stockRate の衝突（どちらも「運用利回り」）を捕まえた。
    //        v29では補足文が名前に混ざっていたおかげで**偶然**区別できていた。
    add("B3_名前なし0・同名0（状態を変えても）", 名前なし === 0 && 同名.length === 0,
        {名前なし:名前なし, 同名:同名}, {名前なし:0, 同名:[]});
  }catch(e){
    add("B1_入力欄の名前に？と補足文が入らない", false, String(e), "例外なし");
    add("B2_補足はaria-describedbyで参照される", false, String(e), "例外なし");
    add("B3_名前なし0・同名0（状態を変えても）", false, String(e), "例外なし");
  }

  /* ============ C. 準備度：確認したか／値が使えるか ============ */

  const fillFlags = P => READY_STEPS.forEach(s => (s.need || []).forEach(n => {
    if(!n[2] || n[2](P)) P.meta.inputState[n[0]] = {confirmed:true};
  }));
  const baseP = () => {
    PARAMS = genericParams(); PARAMS.meta.inputState = {};
    PARAMS.family.ageH = 40; PARAMS.income.hBase = 6000000;
    PARAMS.living.table = [{age:40, amount:3000000, rate:0}];
    PARAMS.econ.deposit = 10000000; PARAMS.house.rentNow = 1200000;
    PARAMS.living.insurance = 100000; PARAMS.saving.nisaMonthlyH = 30000;
    PARAMS.retire.retireAgeH = 65; PARAMS.econ.inflation = 1; PARAMS.econ.investRate = 3;
  };

  // C-1: 旗が立っていても、値が使えなければ段階を上げない
  //      ★住宅の判定（D）と混ざらないよう、**賃貸**にして生活費だけ0にする。
  //        v29実測: stage 3・missing なし（0円の生活費で「判断の準備が整いました」）
  try{
    baseP(); PARAMS.house.buy = false;
    PARAMS.living.table = [{age:40, amount:0, rate:0}];   // ★0円だが旗は立てる
    fillFlags(PARAMS); recalc();
    const r = readiness();
    const f = (typeof readinessFacts === "function") ? readinessFacts(PARAMS) : null;
    add("C1_旗が立っていても値が0なら段階を上げない",
        r.stage < 3 && (r.missing || []).indexOf("年間の生活費") >= 0,
        {stage:r.stage, missing:r.missing,
         生活費のfacts: f ? f["living.table.0.amount"] : "readinessFacts無し"},
        {stage:"3未満", missing:"年間の生活費を含む"});
  }catch(e){ add("C1_旗が立っていても値が0なら段階を上げない", false, String(e), "例外なし"); }

  // C-2: 正本が凍結されている（実行中に書き換えられない）　v29実測: false
  try{
    const frozen = Object.isFrozen(READY_STEPS);
    const n0 = READY_STEPS.length;
    try{ READY_STEPS.push({key:"x", need:[]}); }catch(e){}
    const 増えた = READY_STEPS.length;
    /* ★凍結されていない版（v29）では push が通ってしまう。
         **そのまま残すと後続のD群が汚染される**（need:[] の段階が1つ増え、
         段階が3ではなく4になる）。負試験は必ず元へ戻す。 */
    if(増えた > n0) READY_STEPS.splice(n0, 増えた - n0);
    add("C2_準備度の正本が凍結されている", frozen && 増えた === n0,
        {isFrozen:frozen, 件数:増えた + "（元 " + n0 + "）"},
        {isFrozen:true, 件数:"変わらない"});
  }catch(e){ add("C2_準備度の正本が凍結されている", false, String(e), "例外なし"); }

  // C-3: completionKeyForPath が正本から引ける　v29実測: 関数なし
  try{
    const ok = typeof completionKeyForPath === "function"
      && completionKeyForPath("family.ageH") === "preview"
      && completionKeyForPath("econ.inflation") === "decision"
      && completionKeyForPath("無い.path") === null;
    add("C3_completionKeyForPathが正本から引ける", ok,
        typeof completionKeyForPath === "function"
          ? {ageH:completionKeyForPath("family.ageH"),
             inflation:completionKeyForPath("econ.inflation")}
          : "関数が無い",
        {ageH:"preview", inflation:"decision"});
  }catch(e){ add("C3_completionKeyForPathが正本から引ける", false, String(e), "例外なし"); }

  /* ============ D. 手動借入で資金差が残るとき、住宅は未確定 ============ */

  // D-1: 保存はできるが、段階3にはしない（ChatGPT版 v29レビュー §5 の助言）
  //      v29実測: 資金差 38,500,000円 で stage 3（＝3,850万足りないのに「判断の準備が整いました」）
  try{
    baseP();
    PARAMS.house.buy = true; PARAMS.house.price = 50000000;
    PARAMS.house.selfFund = 5000000; PARAMS.house.gift = 0;
    PARAMS.house.autoFitLoans = false;                    // ★手で決めた
    PARAMS.house.loans = [{name:"A", amount:10000000, years:35, steps:[{y:1,rate:1}]}];
    fillFlags(PARAMS); recalc();
    const gap = fundingGap(PARAMS.house);
    const r = readiness();
    PLANS = []; try{ localStorage.clear(); }catch(e){}
    const saved = commitPlans([{name:"手動", params:clone(PARAMS)}]);
    add("D1_手動借入で資金差があると保存はできるが段階3にしない",
        gap > 1 && r.stage < 3 && saved === true,
        {資金差:Math.round(gap), stage:r.stage,
         住宅:r.housing ? r.housing.level : "housing無し", 保存:saved},
        {資金差:">0", stage:"3未満", 保存:true});
  }catch(e){ add("D1_手動借入で資金差があると保存はできるが段階3にしない", false, String(e), "例外なし"); }

  // D-2: 資金が合えば段階3に届く（厳しくしすぎて通らなくなっていないか）
  //      ★v27で不変条件を全プランに課して「手入力を保存できない」をやった。同じ轍を踏まない。
  try{
    baseP();
    PARAMS.house.buy = true; PARAMS.house.price = 50000000;
    PARAMS.house.selfFund = 5000000; PARAMS.house.gift = 0;
    PARAMS.house.autoFitLoans = true;
    PARAMS.house.loans = [{name:"A", amount:40000000, years:35, steps:[{y:1,rate:1}]}];
    fitLoansOn(PARAMS); fillFlags(PARAMS); recalc();
    const r = readiness();
    add("D2_資金が合えば段階3に届く", r.stage === 3,
        {stage:r.stage, 資金差:Math.round(fundingGap(PARAMS.house)),
         住宅:r.housing ? r.housing.level : "housing無し"}, {stage:3});
  }catch(e){ add("D2_資金が合えば段階3に届く", false, String(e), "例外なし"); }

  // D-3: 賃貸の世帯が、住宅の判定に巻き込まれない
  try{
    baseP(); PARAMS.house.buy = false;
    fillFlags(PARAMS); recalc();
    const r = readiness();
    add("D3_賃貸なら住宅判定に邪魔されず段階3", r.stage === 3,
        {stage:r.stage, 住宅:r.housing ? r.housing.level : "housing無し"},
        {stage:3, 住宅:"na"});
  }catch(e){ add("D3_賃貸なら住宅判定に邪魔されず段階3", false, String(e), "例外なし"); }

  const passed = R.filter(x => x.ok).length;
  return {合計:R.length, 合格:passed, 不合格:R.length - passed,
          結果:R.map(x => (x.ok ? "○ " : "× ") + x.id), 詳細:R};
};
