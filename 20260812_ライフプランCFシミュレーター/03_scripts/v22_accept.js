/* v22 受入試験（ブラウザで実行）。
 *
 * ★**v21 と v22 の両方に対して同じものを流す。**
 *   v21で不合格・v22で合格になって、はじめて「直った」と言える。
 *   v22だけで合格を確かめても、地の合格（もともと通っていた）と区別できない。
 *   2026-08-28のV72査読で、基準線を測らずに負試験6件を「検出」と誤報した反省。
 *
 * 使い方：ブラウザのコンソール（またはjavascript_tool）に貼って
 *   `__V22_ACCEPT__()` を呼ぶ。JSONを返す。
 */
window.__V22_ACCEPT__ = function(){
  const out = {version:(typeof VERSION!=="undefined"?VERSION.tag:"?"), tests:{}};
  const errs = [];
  const stored = () => { try{ return JSON.parse(localStorage.getItem(STORE.plans) || "[]"); }
                         catch(e){ return null; } };

  /* localStorage.setItem を失敗させる差し替え。元に戻せる形で持つ。 */
  const realSet = localStorage.setItem.bind(localStorage);
  const failOn  = () => { localStorage.setItem = function(k, v){
      if(k === STORE.plans) throw new DOMException("quota", "QuotaExceededError");
      return realSet(k, v);
    }; };
  const failOff = () => { localStorage.setItem = realSet; };

  const reset = () => {
    failOff();
    localStorage.removeItem(STORE.plans);
    PLANS = [];
    PARAMS = defaults("buy", "keep", "manual");
    PARAMS.meta.blank = false;
    recalc();
  };

  const shim = () => {
    window.confirm = () => true;
    window.__alerts = [];
    window.alert = m => window.__alerts.push(String(m));
    window.prompt = () => null;
  };
  const realConfirm = window.confirm, realAlert = window.alert, realPrompt = window.prompt;

  /* ---------- 1. まとめて作る経路が本当に保存されるか（P0-1） ---------- */
  const batch = {};
  [["loadAllPresets", () => loadAllPresets()],
   ["loadAllWScenarios", () => loadAllWScenarios()],
   ["loadAllSavingPlans", () => loadAllSavingPlans()],
   ["loadRaisePatterns", () => loadRaisePatterns()],
   ["makeCombos", () => makeCombos(["buy","rent"], ["keep","short75"])],
   ["sweepPrice", () => sweepPrice()],
  ].forEach(([name, fn]) => {
    reset(); shim();
    try{ fn(); }catch(e){ errs.push(name + ": " + e.message); }
    const s = stored();
    batch[name] = {memory:PLANS.length, stored:s ? s.length : null,
                   一致:PLANS.length === (s ? s.length : -1) && PLANS.length > 0};
  });

  /* 取込（非同期なので同期版で組み立てる） */
  reset(); shim();
  try{
    const p = defaults("rent", "keep", "manual"); p.meta.planName = "取込A";
    const add = migratePlans([{name:"取込A", params:p}]);
    let next = PLANS;
    add.forEach(x => { next = (typeof withPlanIn === "function")
      ? withPlanIn(next, x.params, x.name) : (putPlan(x.params, x.name), PLANS); });
    if(typeof withPlanIn === "function"){ commitPlans(next); }
    else { storePlans(); }
  }catch(e){ errs.push("import: " + e.message); }
  {
    const s = stored();
    batch["importPlans相当"] = {memory:PLANS.length, stored:s ? s.length : null,
                                一致:PLANS.length === (s ? s.length : -1) && PLANS.length > 0};
  }

  /* 新しい物件 */
  reset();
  window.confirm = () => true;
  window.__alerts = [];
  window.alert = m => window.__alerts.push(String(m));
  {
    const ans = ["5000", "物件A"];
    window.prompt = () => ans.shift();
    try{ newPropertyPlan(); }catch(e){ errs.push("newPropertyPlan: " + e.message); }
    const s = stored();
    batch["newPropertyPlan"] = {memory:PLANS.length, stored:s ? s.length : null,
                                一致:PLANS.length === (s ? s.length : -1) && PLANS.length > 0};
  }
  out.tests.batch = batch;
  out.tests.batch_all_ok = Object.values(batch).every(x => x.一致);

  /* ---------- 2. 保存に失敗したとき状態が動かないか（P0-2） ---------- */
  const quota = {};
  [["savePlan", () => { document.getElementById("planName").value = "失敗"; savePlan(); }],
   ["loadAllPresets", () => loadAllPresets()],
   ["loadAllWScenarios", () => loadAllWScenarios()],
   ["loadAllSavingPlans", () => loadAllSavingPlans()],
   ["loadRaisePatterns", () => loadRaisePatterns()],
   ["makeCombos", () => makeCombos(["buy","rent"], ["keep","short75"])],
   ["sweepPrice", () => sweepPrice()],
  ].forEach(([name, fn]) => {
    reset(); shim();
    /* 失敗前の状態を作る（1件だけ入れておく） */
    commitPlans(withPlan(defaults("rent","keep","manual"), "基準"));
    const before = {plans:JSON.stringify(PLANS), stored:localStorage.getItem(STORE.plans)};
    window.__alerts = [];
    failOn();
    try{ fn(); }catch(e){ /* 例外を投げてもよいが、状態は動かないこと */ }
    failOff();
    const after = {plans:JSON.stringify(PLANS), stored:localStorage.getItem(STORE.plans)};
    quota[name] = {
      メモリ不変:before.plans === after.plans,
      保存不変:before.stored === after.stored,
      成功表示なし:!window.__alerts.some(m => /保存しました|読み込みました/.test(m)),
    };
  });
  /* メモの書き換え */
  reset(); shim();
  commitPlans(withPlan(defaults("rent","keep","manual"), "メモ試験"));
  PLANS[0].params.meta.memo = "before";
  commitPlans(PLANS);
  failOn();
  try{ setPlanMemo(0, "after"); }catch(e){}
  failOff();
  quota["setPlanMemo"] = {
    メモリ不変:PLANS[0].params.meta.memo === "before",
    保存不変:JSON.parse(localStorage.getItem(STORE.plans))[0].params.meta.memo === "before",
    成功表示なし:true,
  };
  out.tests.quota = quota;
  out.tests.quota_all_ok = Object.values(quota)
    .every(x => x.メモリ不変 && x.保存不変 && x.成功表示なし);

  /* ---------- 3. 国保の擬制世帯主（P0-3・H/W対称） ---------- */
  const mixed = (hType, wType, hAmt, wAmt, head) => {
    const P = genericParams();
    P.meta.baseYear = 2026; P.meta.endAge = 40; P.meta.blank = false;
    P.family.ageH = 40; P.family.ageW = 40; P.family.hasSpouse = true;
    P.family.children = []; P.family.householdHead = head;
    P.work.typeH = hType; P.work.typeW = wType;
    P.income.hBase = hAmt; P.income.wBase = wAmt;
    P.income.hTable = [{age:40, amount:hAmt, rate:0}, {age:41, amount:0, rate:0}];
    P.income.wTable = [{age:40, amount:wAmt, rate:0}, {age:41, amount:0, rate:0}];
    P.living.table = [{age:40, amount:0, rate:0}];
    P.house.buy = false; P.house.rentNow = 0; P.econ.deposit = 0; P.econ.invest = 0;
    P.saving.dcModeH = false; P.saving.dcModeW = false;
    P.saving.nisaMonthlyH = 0; P.saving.nisaMonthlyW = 0;
    P.saving.stockMonthlyH = 0; P.saving.stockMonthlyW = 0;
    P.retire.pensionAuto = false; P.retire.pensionH = 0; P.retire.pensionW = 0;
    P.tax.residentPrevYear = false;
    P.meta.inputState = {
      "tax.kokuhoPrevIncH":{source:"user", confirmed:true},
      "tax.kokuhoPrevIncW":{source:"user", confirmed:true},
    };
    P.tax.kokuhoPrevIncH = 0; P.tax.kokuhoPrevIncW = 0;
    const S = simulate(P), r = S.rows[0];
    const nk = P.tax.kokuminNenkinMonthly * 12;
    return {kokuho:Math.round((hType === "self" ? r.taxH.social : r.taxW.social) - nk),
            警告:!!S.kokuhoHeadUnknown};
  };
  const nhi = {
    "会社員H_自営W_未選択": mixed("employee","self",8000000,0,null),
    "会社員H_自営W_主はH":  mixed("employee","self",8000000,0,"h"),
    "会社員H_自営W_主はW":  mixed("employee","self",8000000,0,"w"),
    "自営H_会社員W_未選択": mixed("self","employee",0,8000000,null),
    "自営H_会社員W_主はH":  mixed("self","employee",0,8000000,"h"),
    "自営H_会社員W_主はW":  mixed("self","employee",0,8000000,"w"),
  };
  out.tests.nhi_head = nhi;
  /* 合格条件：未選択は両向きとも「高いほう」と一致し、必ず警告が出る */
  out.tests.nhi_head_ok =
    nhi["会社員H_自営W_未選択"].kokuho ===
      Math.max(nhi["会社員H_自営W_主はH"].kokuho, nhi["会社員H_自営W_主はW"].kokuho)
    && nhi["自営H_会社員W_未選択"].kokuho ===
      Math.max(nhi["自営H_会社員W_主はH"].kokuho, nhi["自営H_会社員W_主はW"].kokuho)
    && nhi["会社員H_自営W_未選択"].警告 === true
    && nhi["自営H_会社員W_未選択"].警告 === true;

  /* ---------- 4. エンジンがUI関数・グローバルに依存しないか（P1-1） ---------- */
  const boundary = {};
  /* ★`window.insGuideTable = undefined` で試すのは**やめた**。
       トップレベルの関数宣言はどの層に書いてもグローバルなので、
       この方法では「UI層に居る」ことを区別できない（必ず落ちる）。
       層の判定は**定義位置**でしかできないため、静的検査
       （`03_scripts/check_engine_boundary.py`）に移した。
       ここでは「`defaults()` が素で通ること」だけを見る。 */
  {
    const origProfile = activeProfile();
    let err = "";
    try{
      setProfile({params:{living:{insMode:"table"}}});
      defaults("buy", "keep", "manual");
    }catch(e){ err = String(e); }
    finally{ setProfile(origProfile); }
    boundary.defaultsError = err;
    boundary.defaults動く = (err === "");
  }
  {
    const P2 = genericParams();
    const fakeSim = {rows:[
      {ageH:P2.family.ageH,   year:P2.meta.baseYear,   isSpecialYear:false, savingTotal:120000, net:-100000, takeHome:5000000},
      {ageH:P2.family.ageH+1, year:P2.meta.baseYear+1, isSpecialYear:false, savingTotal:120000, net:-200000, takeHome:5000000},
      {ageH:P2.family.ageH+2, year:P2.meta.baseYear+2, isSpecialYear:false, savingTotal:120000, net:-300000, takeHome:5000000},
    ]};
    const origSIM = SIM;
    /* グローバルを空にしたうえで、引数だけで警告が出るか */
    SIM = null;
    const byArg = (validateParams.length >= 2)
      ? validateParams(P2, fakeSim).map(x => x.msg) : [];
    const noArg = validateParams(P2).map(x => x.msg);
    /* 逆に、グローバルに置いても引数なしなら出ないこと */
    SIM = fakeSim;
    const byGlobal = validateParams(P2).map(x => x.msg);
    SIM = origSIM;
    const key = m => /積み立てながら赤字/.test(m);
    boundary.引数で出る = byArg.some(key);
    boundary.引数なしでは出ない = !noArg.some(key);
    boundary.グローバルでは出ない = !byGlobal.some(key);
    boundary.validateParams独立 =
      boundary.引数で出る && boundary.引数なしでは出ない && boundary.グローバルでは出ない;
  }
  out.tests.boundary = boundary;
  out.tests.boundary_ok = boundary.defaults動く && boundary.validateParams独立;

  /* ---------- 5. POLICYを変えたら画面の説明も変わるか（P1-2） ---------- */
  {
    PARAMS = genericParams(); PARAMS.family.hasSpouse = false;
    /* ★拠出額は 23,000 にしない。fmtMan1 で「2.3万円」となり、
       POLICYの旧値（企業年金なし2.3万円）と文字列が衝突する。
       2026-08-31に実際にこれで「旧値が残っている」と誤判定した。 */
    PARAMS.saving.dcModeH = true; PARAMS.saving.dcMonthlyH = 15000;
    PARAMS.meta.blank = false;
    recalc(); setTab("assets");
    const before = document.getElementById("assetCards").innerText;
    const old = {a:POLICY.dc.idecoEmployeeNoDb.v, b:POLICY.dc.idecoEmployeeWithDb.v,
                 c:POLICY.dc.limitSelfEmployed.v, n:POLICY.dc.limitSelfEmployed.next.v};
    POLICY.dc.idecoEmployeeNoDb.v = 99000; POLICY.dc.idecoEmployeeWithDb.v = 88000;
    POLICY.dc.limitSelfEmployed.v = 77000; POLICY.dc.limitSelfEmployed.next.v = 66000;
    const limit = dcMonthlyLimit(PARAMS, "h");
    recalc(); setTab("assets");
    const after = document.getElementById("assetCards").innerText;
    POLICY.dc.idecoEmployeeNoDb.v = old.a; POLICY.dc.idecoEmployeeWithDb.v = old.b;
    POLICY.dc.limitSelfEmployed.v = old.c; POLICY.dc.limitSelfEmployed.next.v = old.n;
    recalc();
    /* 判定は「上限を説明している行」だけを見る（利用者の入力額を拾わない）。 */
    const pick = s => (s.split("\n").find(l => /iDeCoの上限は勤め先の制度/.test(l)) || "");
    const oldRe = /2\.3万円|2\.0万円|6\.8万円|7\.5万円/;
    const newRe = /9\.9万円|8\.8万円|7\.7万円|6\.6万円/;
    out.tests.policy_display = {
      上限の行_変更前:pick(before),
      上限の行_変更後:pick(after),
      変更前に旧値がある:oldRe.test(pick(before)),
      変更後に旧値が残る:oldRe.test(pick(after)),
      変更後に新値が出る:newRe.test(pick(after)),
      計算の上限:limit,
    };
    out.tests.policy_display_ok =
      oldRe.test(pick(before)) && !oldRe.test(pick(after))
      && newRe.test(pick(after)) && limit === 99000;
  }

  /* ---------- 6. 自営業の入力語が統一されているか（P1-3） ---------- */
  {
    PARAMS = genericParams(); PARAMS.work.typeH = "self";
    PARAMS.family.hasSpouse = false; PARAMS.meta.blank = false;
    recalc(); setTab("params");
    const txt = document.getElementById("paramCards").innerText;
    out.tests.self_wording = {
      正しい語がある:/青色申告特別控除/.test(txt),
      誤読を招く語が残る:/事業所得（売上−経費）|事業所得＝売上−経費/.test(txt),
    };
    out.tests.self_wording_ok =
      out.tests.self_wording.正しい語がある && !out.tests.self_wording.誤読を招く語が残る;
  }

  /* ---------- 7. 印刷の確認が先か（P1-4） ---------- */
  {
    const origBuild = window.buildReport, origConfirm = window.confirm,
          origTimeout = window.setTimeout;
    const ev = [];
    window.buildReport = () => ev.push("build");
    window.confirm = () => { ev.push("confirm"); return false; };
    window.setTimeout = () => ev.push("timeout");
    try{ printReport(); }
    finally{ window.buildReport = origBuild; window.confirm = origConfirm;
             window.setTimeout = origTimeout; }
    out.tests.print_order = ev;
    out.tests.print_order_ok = (ev[0] === "confirm" && !ev.includes("build"));
  }

  /* ---------- 8. 教育費の1年表示（P2-1） ---------- */
  {
    PARAMS = genericParams(); PARAMS.family.hasSpouse = true; PARAMS.meta.blank = false;
    PARAMS.family.children = [{name:"第一子", birthYear:2020, plan:{}},
                              {name:"第二子", birthYear:2022, plan:{}}];
    recalc(); setTab("edu");
    const has = (typeof eduOneYear === "function");
    let one = null, wide = null;
    /* ★測る前に、その要素が表示されているかを確かめる。
         非表示だと getBoundingClientRect も clientWidth も0を返し、
         「収まっている」と読めてしまう（過去に3回やっている）。 */
    const shown = () => {
      const el = document.getElementById("eduTable");
      return !!(el && el.offsetParent !== null && el.clientWidth > 0);
    };
    if(has){
      if(typeof EDU_ONEYEAR !== "undefined") EDU_ONEYEAR = true;
      render();
      const w = document.getElementById("eduTableWrap");
      if(w) w.open = true;
      const tb = document.querySelector("#eduTable table");
      one = {表示中:shown(),
             表幅:tb ? Math.round(tb.getBoundingClientRect().width) : null,
             枠幅:document.getElementById("eduTable").clientWidth,
             ページのはみ出し:document.documentElement.scrollWidth - innerWidth,
             画面幅:innerWidth};
      EDU_ONEYEAR = false; render();
      if(w) w.open = true;
      const tb2 = document.querySelector("#eduTable table");
      wide = {表示中:shown(),
              表幅:tb2 ? Math.round(tb2.getBoundingClientRect().width) : null,
              枠幅:document.getElementById("eduTable").clientWidth};
      EDU_ONEYEAR = null; render();
    }
    out.tests.edu_oneyear = {実装あり:has, 一年表示:one, 横長表:wide};
    /* 合格条件：**表示中に測れていること**＋1年表示が枠に収まること＋
       横長表に切り替えると実際に広くなること（切替が効いている証拠）。 */
    out.tests.edu_oneyear_ok = has && one && one.表示中 && wide && wide.表示中
      && one.表幅 !== null && one.表幅 <= one.枠幅 + 2
      && one.ページのはみ出し <= 0
      && wide.表幅 > one.表幅;
  }

  window.confirm = realConfirm; window.alert = realAlert; window.prompt = realPrompt;
  reset();
  out.errors = errs;
  return out;
};
"__V22_ACCEPT__ ready";
