/* v28 受入試験。★v27（基準線）で落ち、v28で通ることを確かめる。
   ChatGPT版の v27 レビュー（P0 2件・P1 6件・P2 5件）に対応する。 */
window.__V28_ACCEPT__ = function(){
  const out = {version:(typeof VERSION !== "undefined" ? VERSION.tag : "?"), tests:{}};
  const rc = window.confirm, ra = window.alert, rp = window.prompt;
  window.confirm = () => true;
  window.alert = m => (window.__alerts = window.__alerts || []).push(String(m));
  const reset = () => {
    try{ localStorage.removeItem(STORE.plans); }catch(e){}
    PLANS = []; PARAMS = genericParams(); PARAMS.meta.blank = false;
    window.__alerts = []; window.prompt = () => null; recalc();
  };

  /* ---------- P0-1 擬制世帯主の前年所得 ---------- */
  {
    const mk = (prevW) => {
      const P = genericParams();
      P.meta.baseYear = 2026; P.meta.endAge = 40; P.meta.blank = false;
      P.family.ageH = 40; P.family.ageW = 40; P.family.hasSpouse = true;
      P.family.children = []; P.family.householdHead = "w";
      P.work.typeH = "self"; P.work.typeW = "employee";
      P.income.hBase = 0; P.income.hTable = [{age:40, amount:0, rate:0}];
      P.income.wBase = 0; P.income.wTable = [{age:40, amount:0, rate:0}];
      P.living.table = [{age:40, amount:0, rate:0}];
      P.house.buy = false; P.house.rentNow = 0;
      P.econ.deposit = 0; P.econ.invest = 0;
      P.saving.dcModeH = false; P.saving.dcModeW = false;
      P.saving.nisaMonthlyH = 0; P.saving.nisaMonthlyW = 0;
      P.saving.stockMonthlyH = 0; P.saving.stockMonthlyW = 0;
      P.retire.pensionAuto = false; P.retire.pensionH = 0; P.retire.pensionW = 0;
      P.tax.residentPrevYear = false; P.tax.kokuminNenkinMonthly = 0;
      P.tax.kokuhoPrevIncH = 0; P.tax.kokuhoPrevIncW = prevW;
      P.meta.inputState = {"tax.kokuhoPrevIncH":{source:"user", confirmed:true},
                           "tax.kokuhoPrevIncW":{source:"user", confirmed:true}};
      const S = simulate(P), r = S.rows[0];
      return {国保:Math.round((r.taxH.social + r.taxW.social) * 10) / 10,
              代用の断り:!!(S.notes ? S.notes.kokuhoUsedCurrent : S.kokuhoUsedCurrent)};
    };
    const high = mk(8000000), zero = mk(0);
    out.tests.kokuho_head = {前年800万を確認済み:high, 前年0円:zero,
                             差:Math.round((high.国保 - zero.国保) * 10) / 10};
    /* ★前年所得800万円の世帯主がいれば軽減は効かない＝**明らかに高くなる**。
         v27は当年だけで作っており、どちらも同じ値だった（差0円）。 */
    out.tests.kokuho_head_ok = high.国保 > zero.国保 + 1000;
  }

  /* ---------- P0-2 トップレベル金額の下限 ---------- */
  {
    reset(); PARAMS.house.buy = true; recalc();
    const probe = (path, read) => {
      const b = read(); onMan(path, "-1000");
      return {path, 前:b, 後:read(), 拒否:(b === read())};
    };
    const rows = [
      probe("house.price",       () => PARAMS.house.price),
      probe("house.selfFund",    () => PARAMS.house.selfFund),
      probe("house.gift",        () => PARAMS.house.gift),
      probe("econ.deposit",      () => PARAMS.econ.deposit),
      probe("econ.invest",       () => PARAMS.econ.invest),
      probe("living.insurance",  () => PARAMS.living.insurance),
      probe("house.feeRegistration", () => PARAMS.house.feeRegistration),
    ];
    out.tests.negative_money = rows;
    out.tests.negative_money_ok = rows.every(r => r.拒否);
  }

  /* ---------- P0-2b 年齢の下限 ---------- */
  {
    reset();
    const b = PARAMS.family.ageH;
    onNum("family.ageH", "0");   const a0 = PARAMS.family.ageH;
    onNum("family.ageH", "-5");  const a1 = PARAMS.family.ageH;
    out.tests.age_bounds = {前:b, ゼロを入れた後:a0, マイナスを入れた後:a1};
    out.tests.age_bounds_ok = (a0 === b) && (a1 === b);
  }

  /* ---------- P1-1 借入の追加・削除 ---------- */
  {
    reset();
    const H = PARAMS.house;
    H.buy = true; H.autoFitLoans = true; H.price = 50000000; H.selfFund = 10000000;
    H.feeMode = "detail"; H.feeBrokerageAuto = true; H.feeLoanRate = 2.2;
    H.loans = [{name:"本人", amount:0, years:35, steps:[{y:1, rate:1}]}];
    recalc(); onMan("house.price", "5000");
    const g0 = Math.round(fundingGap(H));
    addLoan();  const g1 = Math.round(fundingGap(H));
    delLoan(1); const g2 = Math.round(fundingGap(H));
    out.tests.loan_count = {追加前:g0, 追加後:g1, 削除後:g2, 本数:H.loans.length};
    out.tests.loan_count_ok = [g0, g1, g2].every(x => Math.abs(x) <= 1);
  }

  /* ---------- P1-2 保存の検査が、いまの画面の警告を汚さないか ---------- */
  {
    reset();
    PARAMS.work.typeH = "employee"; PARAMS.income.hBase = 6000000;
    PARAMS.income.hTable = [{age:35, amount:6000000, rate:0}, {age:66, amount:0, rate:0}];
    recalc();
    const before = JSON.stringify(RESULT_NOTES);
    const q = clone(PARAMS);
    q.work.typeH = "self"; q.meta.planName = "自営業";
    q.tax.kokuhoMunicipalityConfirmed = false;
    commitPlans([{name:"自営業", params:q}]);
    const after = JSON.stringify(RESULT_NOTES);
    out.tests.notes_purity = {保存前:JSON.parse(before), 保存後:JSON.parse(after),
                              同じ:(before === after)};
    out.tests.notes_purity_ok = (before === after);
  }

  /* ---------- P1-3 新しい物件をキャンセルしても現状が変わらないか ---------- */
  {
    reset();
    const snap = JSON.stringify(PARAMS.house);
    let n = 0;
    window.prompt = () => (n++ === 0 ? "6000" : null);   // 価格は入れる／名前はキャンセル
    newPropertyPlan();
    const after = JSON.stringify(PARAMS.house);
    out.tests.newproperty_cancel = {不変:(snap === after),
      前の価格:JSON.parse(snap).price, 後の価格:JSON.parse(after).price};
    out.tests.newproperty_cancel_ok = (snap === after);
    window.prompt = () => null;
  }

  /* ---------- P1-4 物価0%でも「自分で年率を入れる」が使えるか ---------- */
  {
    reset();
    PARAMS.econ.inflation = 0; recalc();
    setRentGrowthMode("custom");
    const v = PARAMS.house.rentGrowth, mode = rentGrowthMode(PARAMS);
    const b = PARAMS.house.rentGrowth;
    onNum("house.rentGrowth", "-200");
    out.tests.rent_custom = {物価0でcustomの値:v, 読み戻したモード:mode,
      マイナス200の前:b, マイナス200の後:PARAMS.house.rentGrowth,
      拒否:(b === PARAMS.house.rentGrowth)};
    out.tests.rent_custom_ok = (mode === "custom") && (Number(v) !== 0)
      && (b === PARAMS.house.rentGrowth);
  }

  /* ---------- P1-5 分岐ごとに、セットアップを一周したら最終段階へ届くか ---------- */
  {
    const walk = (branch) => {
      reset();
      startWizard();
      wizGo(3); applyHousing(branch);
      for(let s = 0; s < 7; s++){
        wizGo(s);
        [...document.querySelectorAll("input[type=number]")]
          .filter(e => e.offsetParent !== null).forEach(e => {
            const nm = (e.getAttribute("aria-label") || "")
              || ((document.querySelector('label[for="' + CSS.escape(e.id) + '"]') || {}).textContent || "").trim();
            let v = 10;
            if(/リタイア/.test(nm)) v = 63;
            else if(/取得(する|した)とき/.test(nm)) v = 45;
            else if(/年齢/.test(nm)) v = 42;
            else if(/年収/.test(nm)) v = 620;
            else if(/生活費/.test(nm)) v = 300;
            else if(/保険/.test(nm)) v = 24;
            else if(/積立/.test(nm)) v = 3;
            else if(/預金|貯蓄/.test(nm)) v = 800;
            else if(/運用/.test(nm)) v = 3;
            else if(/物価/.test(nm)) v = 2;
            else if(/住居費|家賃/.test(nm)) v = 150;
            else if(/物件価格/.test(nm)) v = 5000;
            else if(/自己資金/.test(nm)) v = 1000;
            else if(/借入/.test(nm)) v = 4000;
            else if(/返済期間/.test(nm)) v = 35;
            else if(/金利/.test(nm)) v = 1.2;
            e.value = String(v);
            e.dispatchEvent(new Event("input", {bubbles:true}));
          });
      }
      const r = readiness();
      endWizard(false);
      return {段階:r.label, 進捗:r.done + "/" + r.total, 足りない:r.missing};
    };
    const res = {};
    HOUSING_KEYS.forEach(k => { res[(HOUSINGS[k] || {}).short || k] = walk(k); });
    out.tests.wizard_walk = res;
    out.tests.wizard_walk_ok =
      Object.keys(res).every(k => res[k].足りない.length === 0
        && res[k].段階 === "判断の準備が整いました");
  }

  /* ---------- P1-5b 網羅チェックが分岐と描画を見るか ---------- */
  {
    reset();
    out.tests.coverage = checkWizardCoverage();
    /* ★負試験：`covers` に宣言だけあって欄が無い項目を足したら落ちるか。 */
    const step = READY_STEPS[1];
    step.need.push(["econ.investShare", "存在しない案内の項目"]);
    const broken = checkWizardCoverage();
    step.need.pop();
    out.tests.coverage_negative = broken.filter(x => x.path === "econ.investShare").length;
    /* ★負試験2：**`covers` に宣言だけして、欄は置かない**。
         v27は宣言を見るだけなので**素通りした**。描画まで見る版は落ちる。
         これが「宣言の突き合わせ」と「実際に描かれるか」の差を測る唯一の試験。 */
    step.need.push(["econ.investShare", "宣言だけあって欄が無い項目"]);
    const housingStep = WIZ_STEPS.find(s => s.t === "住まい");
    housingStep.covers.push("econ.investShare");
    const declaredOnly = checkWizardCoverage();
    housingStep.covers.pop(); step.need.pop();
    out.tests.coverage_declared_only =
      declaredOnly.filter(x => x.path === "econ.investShare").length;
    out.tests.coverage_ok = out.tests.coverage.length === 0
      && out.tests.coverage_negative > 0
      && out.tests.coverage_declared_only > 0;
  }

  /* ---------- P1-6 借入額があるのに返済期間0年 ---------- */
  {
    reset();
    PARAMS.house.buy = true;
    PARAMS.house.loans = [{name:"本人", amount:30000000, years:35, steps:[{y:1, rate:1}]}];
    recalc();
    const b = PARAMS.house.loans[0].years;
    onLoan(0, "years", "0");
    const kept = PARAMS.house.loans[0].years;
    /* 保存の入口でも止まるか（古い保存データ経由） */
    const q = clone(PARAMS);
    q.house.loans[0].years = 0; q.meta.planName = "返済0年";
    const saved = commitPlans([{name:"返済0年", params:q}]);
    out.tests.loan_years = {前:b, 後:kept, 入力で拒否:(b === kept), 保存:saved};
    out.tests.loan_years_ok = (b === kept) && (saved === false);
  }

  /* ---------- 維持している合格 ---------- */
  {
    reset();
    PARAMS.family.hasSpouse = true;
    PARAMS.income.wBase = 4000000;
    PARAMS.income.wTable = [{age:35, amount:4000000, rate:0}, {age:66, amount:0, rate:0}];
    PARAMS.house.buy = true; PARAMS.house.price = 50000000;
    PARAMS.house.autoFitLoans = true; recalc();
    const counts = {};
    [["loadAllPresets",2], ["loadAllWScenarios",7],
     ["loadAllSavingPlans",4], ["loadRaisePatterns",4]].forEach(([fn, want]) => {
      try{ localStorage.removeItem(STORE.plans); }catch(e){}
      PLANS = []; window[fn]();
      let stored = 0;
      try{ stored = JSON.parse(localStorage.getItem(STORE.plans) || "[]").length; }catch(e){}
      counts[fn] = {画面:PLANS.length, 保存:stored, 期待:want,
                    ok:(PLANS.length === want && stored === want)};
    });
    out.tests.batch = counts;
    out.tests.batch_ok = Object.keys(counts).every(k => counts[k].ok);
  }

  const keys = Object.keys(out.tests).filter(k => k.endsWith("_ok"));
  out.summary = {合格:keys.filter(k => out.tests[k]).length, 全体:keys.length,
                 不合格:keys.filter(k => !out.tests[k])};
  window.confirm = rc; window.alert = ra; window.prompt = rp;
  return out;
};
