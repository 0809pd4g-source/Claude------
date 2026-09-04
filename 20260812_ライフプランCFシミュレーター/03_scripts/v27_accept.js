/* v27 受入試験。★v26（基準線）で落ち、v27で通ることを確かめる。
   ChatGPT版の v25 独立再レビュー（P0 2件・P1 4件・P2 2件）に対応する。

   ★基準線を先に測るのが要点。「v27が通った」だけでは、
     その試験がもともと通っていたのか、直したから通ったのかが分からない。 */
window.__V27_ACCEPT__ = function(){
  const out = {version:(typeof VERSION !== "undefined" ? VERSION.tag : "?"), tests:{}};
  const rc = window.confirm, ra = window.alert, rp = window.prompt;
  window.confirm = () => true;
  window.alert = m => (window.__alerts = window.__alerts || []).push(String(m));
  window.prompt = () => null;
  const reset = () => {
    try{ localStorage.removeItem(STORE.plans); }catch(e){}
    PLANS = []; PARAMS = genericParams(); PARAMS.meta.blank = false;
    window.__alerts = []; recalc();
  };
  /* 基準線（v26）には無い関数があるので、同じ式をここに持つ。 */
  const gapOf = H => (typeof fundingGap === "function") ? fundingGap(H)
    : (Number(H.price||0) + feeTotal(H) - Number(H.selfFund||0) - Number(H.gift||0)
       - (H.loans||[]).reduce((s,l) => s + (Number(l.amount)||0), 0));
  const detailHouse = () => {
    reset();
    const H = PARAMS.house;
    H.buy = true; H.autoFitLoans = true;
    H.price = 50000000; H.selfFund = 10000000; H.gift = 0;
    H.feeMode = "detail"; H.feeBrokerageAuto = true; H.feeLoanRate = 2.2;
    H.loans = [{name:"本人", amount:0, years:35, steps:[{y:1, rate:1}]}];
    recalc();
    return H;
  };

  /* ============================================================
     P0-1  住宅資金の計算を、利用者の操作から通しても1本か
     ============================================================ */
  {
    /* (a) 価格を変える（借入0から） */
    const H1 = detailHouse();
    onMan("house.price", "5000");           // 5,000万円
    const a = Math.round(gapOf(H1));

    /* (b) 価格を変える（借入4,000万から） */
    const H2 = detailHouse();
    H2.loans[0].amount = 40000000; recalc();
    onMan("house.price", "5000");
    const b = Math.round(gapOf(H2));

    /* (c) 融資手数料率を変える */
    const H3 = detailHouse();
    onMan("house.price", "5000");
    onNum("house.feeLoanRate", "3.3");
    const c = Math.round(gapOf(H3));

    /* (d) 登記費用を変える */
    const H4 = detailHouse();
    onMan("house.price", "5000");
    onMan("house.feeRegistration", "200");   // 200万円
    const d = Math.round(gapOf(H4));

    /* (e) 諸費用の求め方を切り替える */
    const H5 = detailHouse();
    onMan("house.price", "5000");
    onTxt("house.feeMode", "simple");
    const e = Math.round(gapOf(H5));

    out.tests.autofit = {価格変更_借入0:a, 価格変更_借入4000万:b,
                         手数料率変更:c, 登記費用変更:d, 求め方切替:e};
    out.tests.autofit_ok = [a,b,c,d,e].every(x => Math.abs(x) <= 1);
  }

  /* 物件価格上限も同じ式を通るか */
  {
    detailHouse();
    /* ★上限が求まる世帯にする。求まらない（null）と、
         直っているかどうかを一度も測らないまま「合格」になってしまう。 */
    PARAMS.family.ageH = 40; PARAMS.family.hasSpouse = false;
    PARAMS.family.children = [];
    PARAMS.income.hBase = 15000000;
    PARAMS.income.hTable = [{age:40,amount:15000000,rate:0},{age:66,amount:0,rate:0}];
    PARAMS.living.table = [{age:40,amount:3000000,rate:0}];
    PARAMS.econ.deposit = 50000000; PARAMS.house.selfFund = 20000000;
    PARAMS.house.buyAge = 40;
    recalc();
    const cond = s => s.depleteAge === null;
    const lim = (typeof priceBreakEven === "function")
      ? priceBreakEven(PARAMS, cond) : null;

    /* ★同じ二分探索を、**候補ごとに `fitLoansOn()` を通して**やり直す。
         製品が返した上限と一致しなければ、製品は別の式で借入を出している。
         「返ってきた価格をあとから合わせ直す」と、どちらの版でも差額0になり
         **試験が何も測らない**（v26でも合格した。最初の版の誤り）。 */
    const build = price => {
      const p = clone(PARAMS);
      p.house.price = price;
      if(p.house.feeMode !== "detail")
        p.house.fees = Math.round(price * (feeTotal(PARAMS.house) / PARAMS.house.price));
      fitLoansOn(p);
      return p;
    };
    let ref = null;
    if(cond(simulate(build(20000000)))){
      if(cond(simulate(build(200000000)))) ref = 200000000;
      else {
        let lo = 20000000, hi = 200000000;
        for(let i = 0; i < 18; i++){
          const mid = (lo + hi) / 2;
          if(cond(simulate(build(mid)))) lo = mid; else hi = mid;
        }
        ref = lo;
      }
    }
    const over = (lim !== null && ref !== null) ? Math.round(lim - ref) : null;
    out.tests.price_limit = {製品の上限:lim, 閉じた式での上限:ref, 過大表示:over};
    out.tests.price_limit_ok = over !== null && Math.abs(over) <= 1;
  }

  /* ============================================================
     P0-2  数値の入口が、桁あふれと意味外の値を止めるか
     ============================================================ */
  {
    const probe = (name, before, act, read) => {
      const b = before();
      act();
      const after = read();
      return {name, 前:b, 後:after, 変わっていない:(b === after),
              有限:Number.isFinite(after)};
    };
    const rows = [];
    reset(); PARAMS.house.buy = true; PARAMS.house.loans =
      [{name:"本人", amount:20000000, years:35, steps:[{y:1,rate:1}]}]; recalc();
    rows.push(probe("onLoanMan", () => PARAMS.house.loans[0].amount,
      () => onLoanMan(0, "1e307"), () => PARAMS.house.loans[0].amount));
    /* ★前の試験の副作用を持ち込まない（Infinity から始めると「変わっていない」が
         正しく測れない）。**負試験のたびに基準の状態へ戻す。** */
    reset(); PARAMS.house.buy = true; PARAMS.house.loans =
      [{name:"本人", amount:20000000, years:35, steps:[{y:1,rate:1}]}]; recalc();
    rows.push(probe("onLoanMan（負数）", () => PARAMS.house.loans[0].amount,
      () => onLoanMan(0, "-1000"), () => PARAMS.house.loans[0].amount));
    reset();
    rows.push(probe("onRowMan", () => PARAMS.living.table[0].amount,
      () => onRowMan("living.table", 0, "amount", "1e307"),
      () => PARAMS.living.table[0].amount));
    reset(); PARAMS.other.items = [{name:"旅行",cat:"misc",kind:"yearly",
      from:40,to:50,amount:300000,every:5}]; recalc();
    rows.push(probe("onItemMan", () => PARAMS.other.items[0].amount,
      () => onItemMan("other.items", 0, "1e307"), () => PARAMS.other.items[0].amount));
    reset();
    rows.push(probe("onStageMan", () => PARAMS.edu.stages.univ.first,
      () => onStageMan("univ", "first", "1e307"), () => PARAMS.edu.stages.univ.first));
    reset();
    rows.push(probe("onStep（負の金利）", () => PARAMS.house.loans[0].steps[0].rate,
      () => onStep(0, 0, "rate", "-5"), () => PARAMS.house.loans[0].steps[0].rate));
    reset();
    PARAMS.saving.schedule = [{who:"h", kind:"nisa", from:40, to:60, monthly:100000}];
    recalc();
    rows.push(probe("onSchedule", () => PARAMS.saving.schedule[0].monthly,
      () => onSchedule(0, "monthly", "1e307"), () => PARAMS.saving.schedule[0].monthly));
    reset(); PARAMS.family.children = [{name:"子1",birthYear:2020,plan:{}}]; recalc();
    rows.push(probe("onKid（生まれ年）", () => PARAMS.family.children[0].birthYear,
      () => onKid(0, "birthYear", "1e307"), () => PARAMS.family.children[0].birthYear));
    out.tests.handlers = rows;
    out.tests.handlers_ok = rows.every(r => r.変わっていない && r.有限);
  }

  /* 巨大値を入れたあと、保存が「成功しました」と言わないか */
  {
    reset();
    PARAMS.house.buy = true;
    PARAMS.house.loans = [{name:"本人", amount:20000000, years:35, steps:[{y:1,rate:1}]}];
    recalc();
    /* 入口が守っていれば、そもそも Infinity は入らない。
       入ってしまう版（v26）でも、保存が成功表示しないことまで見る。 */
    PARAMS.house.loans[0].amount = Infinity;
    PARAMS.meta.planName = "巨大数";
    const el = document.getElementById("planName"); if(el) el.value = "巨大数";
    window.__alerts = [];
    savePlan();
    const stored = (() => { try{ return JSON.parse(localStorage.getItem(STORE.plans) || "[]"); }
                           catch(e){ return []; } })();
    out.tests.save_infinity = {
      画面のプラン数:PLANS.length, 保存件数:stored.length,
      成功表示:(window.__alerts || []).filter(m => m.indexOf("保存しました") >= 0)};
    out.tests.save_infinity_ok =
      PLANS.length === 0 && stored.length === 0
      && out.tests.save_infinity.成功表示.length === 0;
  }

  /* 入力は有限でも、計算結果が非有限になる候補を保存しないか */
  {
    reset();
    PARAMS.econ.inflation = 1e307;      // 有限な数だが、複利で桁があふれる
    PARAMS.meta.planName = "無限インフレ";
    const el = document.getElementById("planName"); if(el) el.value = "無限インフレ";
    window.__alerts = [];
    const s = simulate(PARAMS);
    savePlan();
    const stored = (() => { try{ return JSON.parse(localStorage.getItem(STORE.plans) || "[]"); }
                           catch(e){ return []; } })();
    out.tests.save_infinite_result = {
      最終資産:String(s.summary.last), 保存件数:stored.length,
      成功表示:(window.__alerts || []).filter(m => m.indexOf("保存しました") >= 0)};
    out.tests.save_infinite_result_ok =
      !Number.isFinite(s.summary.last)
      && stored.length === 0 && out.tests.save_infinite_result.成功表示.length === 0;
  }

  /* ============================================================
     P1-1  融資手数料率の無効値
     ============================================================ */
  {
    const tryRate = r => {
      detailHouse();
      onMan("house.price", "5000");
      /* ★開始値を試す値と違えておく。同じ値だと「変わっていない＝拒否された」と
           読めてしまい、**正しく受け付けた場合まで拒否に見える**（v26の実測で実際に出た）。 */
      PARAMS.house.feeLoanRate = 1.0; recalc();
      const before = PARAMS.house.feeLoanRate;
      onNum("house.feeLoanRate", String(r));
      const after = PARAMS.house.feeLoanRate;
      PARAMS.meta.planName = "rate" + r;
      const el = document.getElementById("planName"); if(el) el.value = "rate" + r;
      window.__alerts = [];
      savePlan();
      const stored = (() => { try{ return JSON.parse(localStorage.getItem(STORE.plans)||"[]"); }
                             catch(e){ return []; } })();
      return {料率:r, 入った値:after, 拒否された:(before === after),
              保存件数:stored.length, 資金差額:Math.round(gapOf(PARAMS.house))};
    };
    const rows = [tryRate(-1), tryRate(2.2), tryRate(99), tryRate(100), tryRate(120)];
    out.tests.fee_rate = rows;
    out.tests.fee_rate_ok =
      rows[0].拒否された && rows[3].拒否された && rows[4].拒否された
      && !rows[1].拒否された && !rows[2].拒否された;
  }

  /* ============================================================
     P1-2  年金開始初年度の軽減判定
     ============================================================ */
  {
    const T = clone(genericParams().tax);
    /* ★軽減の帯をまたぐ所得を選ぶ。単身・給与年金所得者1人なら
         7割≦43万／5割≦73.5万。判定所得50万は5割だが、
         15万円控除が当たると35万＝7割になる。**帯をまたがない額で測ると差が出ない**
         （最初は100万で測って差0になり、試験が何も見ていなかった）。 */
    const one = (prevPension) => kokuhoHousehold(
      [{inc:500000, prevInc:500000, age:70, wageEarner:true,
        pensionInc:500000, prevPensionInc:prevPension}], T);
    const noPrev = one(0), withPrev = one(500000);
    out.tests.kokuho_prev_pension_direct = {
      前年に年金なし:{総額:noPrev.total, 軽減:noPrev.reduce},
      前年にも年金あり:{総額:withPrev.total, 軽減:withPrev.reduce},
      差:Math.round((noPrev.total - withPrev.total) * 10) / 10};

    /* 統合経路：65歳で受け取り始めた年に、前年の年金を推定しないか */
    const build = (confirmPrev) => {
      const P = genericParams();
      P.meta.baseYear = 2026; P.meta.endAge = 65; P.meta.blank = false;
      P.family.ageH = 65; P.family.hasSpouse = false; P.family.children = [];
      P.work.typeH = "self";
      P.income.hBase = 0; P.income.hTable = [{age:65, amount:0, rate:0}];
      P.living.table = [{age:65, amount:0, rate:0}];
      P.house.buy = false; P.house.rentNow = 0;
      P.econ.deposit = 0; P.econ.invest = 0;
      P.saving.dcModeH = false; P.saving.nisaMonthlyH = 0; P.saving.stockMonthlyH = 0;
      P.retire.pensionAuto = false; P.retire.pensionH = 1600000; P.retire.pensionStartH = 65;
      P.tax.residentPrevYear = false; P.tax.kokuminNenkinMonthly = 0;
      /* ★前年の所得は50万円で確認済み（＝5割軽減の帯）。
           ここを0にすると判定所得が0になり、**15万円控除の有無が結果に出ない**
           （最初の版はそれで v26 と v27 が同じ値になり、何も測っていなかった）。 */
      P.tax.kokuhoPrevIncH = 500000;
      P.meta.inputState = {"tax.kokuhoPrevIncH":{source:"user", confirmed:true}};
      if(confirmPrev){
        P.tax.kokuhoPrevPensionH = 0;
        P.meta.inputState["tax.kokuhoPrevPensionH"] = {source:"user", confirmed:true};
      }
      const S = simulate(P);
      return {国保:Math.round(S.rows[0].taxH.social * 10) / 10,
              代用の断り:!!S.kokuhoUsedCurrent};
    };
    out.tests.kokuho_prev_pension_sim = {未確認:build(false), 前年年金0を確認:build(true)};
    /* 直った版では、当年の年金で15万円控除を当てない＝
       「前年に年金なし」と同じ側の（高い）保険料になる。 */
    out.tests.kokuho_prev_pension_ok =
      Math.abs(out.tests.kokuho_prev_pension_sim.未確認.国保 - noPrev.total) < 1
      && Math.abs(out.tests.kokuho_prev_pension_sim.前年年金0を確認.国保 - noPrev.total) < 1;
  }

  /* ============================================================
     P1-3  その他の課税所得の所有者
     ============================================================ */
  {
    const build = owner => {
      const P = genericParams();
      P.meta.baseYear = 2026; P.meta.endAge = 40; P.meta.blank = false;
      P.family.ageH = 40; P.family.ageW = 40; P.family.hasSpouse = true;
      P.family.children = [];
      P.work.typeH = "employee"; P.work.typeW = "none";
      P.income.hBase = 8000000;
      P.income.hTable = [{age:40, amount:8000000, rate:0}, {age:41, amount:0, rate:0}];
      P.income.wBase = 0;
      P.income.wTable = [{age:40, amount:0, rate:0}, {age:41, amount:0, rate:0}];
      P.living.table = [{age:40, amount:0, rate:0}];
      P.house.buy = false; P.house.rentNow = 0;
      P.econ.deposit = 0; P.econ.invest = 0;
      P.saving.dcModeH = false; P.saving.dcModeW = false;
      P.saving.nisaMonthlyH = 0; P.saving.nisaMonthlyW = 0;
      P.saving.stockMonthlyH = 0; P.saving.stockMonthlyW = 0;
      P.retire.pensionAuto = false; P.retire.pensionH = 0; P.retire.pensionW = 0;
      P.tax.residentPrevYear = false;
      P.other.incomes = [{name:"賃貸収入", cat:"misc", kind:"yearly",
                          from:40, to:41, amount:2000000, every:5,
                          taxFree:false, owner:owner}];
      const r = simulate(P).rows[0];
      return {あなた:Math.round(r.taxH.total), パートナー:Math.round(r.taxW.total),
              世帯:Math.round(r.taxH.total + r.taxW.total)};
    };
    const h = build("h"), w = build("w"), both = build("both");
    out.tests.income_owner = {あなたに寄せる:h, パートナーに寄せる:w, 折半:both,
                              差:h.世帯 - w.世帯};
    /* 直っていれば、所有者を変えると世帯の負担が変わる。 */
    /* ★「差が出れば合格」にしない。**パートナーに寄せたぶんが、
         パートナーの税として現れているか**まで見る。
         v27の最初の版は `argsW.miscInc` を足し忘れており、
         所有者を変えると収入が**どちらの税からも消えて**世帯負担が下がっていた。
         差が出ているので「合格」に見えた。 */
    out.tests.income_owner_ok =
      (h.世帯 !== w.世帯) && (both.世帯 !== h.世帯)
      && h.パートナー === 0 && w.パートナー > 0
      && both.パートナー > 0 && both.パートナー < w.パートナー;
  }

  /* ============================================================
     P1-4  家賃の上昇率の入力欄
     ============================================================ */
  {
    reset();
    PARAMS.house.buy = false; PARAMS.house.rentNow = 1200000; recalc();
    setTab("loan"); render();
    const has = typeof rentGrowthField === "function";
    const modeSel = [...document.querySelectorAll("select")]
      .filter(e => (e.getAttribute("onchange") || "").indexOf("setRentGrowthMode") >= 0)
      .filter(e => e.offsetParent !== null);
    const trip = k => {
      if(typeof setRentGrowthMode !== "function") return null;
      setRentGrowthMode(k);
      const v = PARAMS.house.rentGrowth;
      /* 保存して読み戻したときに null と 0 が区別されるか */
      const round = JSON.parse(JSON.stringify({g:v})).g;
      return {値:v === null ? "null" : v, 往復後:round === null ? "null" : round,
              区別できる:(v === null) === (round === null)};
    };
    out.tests.rent_growth = {
      関数がある:has, 画面の操作要素:modeSel.length,
      物価連動:trip("inflation"), 据え置き:trip("flat"), 自分で入れる:trip("custom")};
    out.tests.rent_growth_ok =
      has && modeSel.length === 1
      && out.tests.rent_growth.物価連動.値 === "null"
      && out.tests.rent_growth.据え置き.値 === 0
      && out.tests.rent_growth.自分で入れる.値 !== 0
      && out.tests.rent_growth.自分で入れる.値 !== "null";
  }

  /* 利用者が借入額を手で決めたときは、そのまま保存できるか
     （ツールが辻褄を合わせる約束＝`autoFitLoans` は外れる） */
  {
    const H = detailHouse();
    onMan("house.price", "5000");
    onMan("house.selfFund", "1000");
    const fitted = Math.round(gapOf(H));
    onLoanMan(0, "2000");                     // 借入を手で2,000万円に下げる
    const manual = Math.round(gapOf(H));
    PARAMS.meta.planName = "手で減らした借入";
    const el = document.getElementById("planName");
    if(el) el.value = "手で減らした借入";
    window.__alerts = [];
    savePlan();
    let stored = [];
    try{ stored = JSON.parse(localStorage.getItem(STORE.plans) || "[]"); }catch(e){}
    out.tests.manual_loan = {
      自動連動後の資金差:fitted, 手入力後の資金差:manual,
      自動連動:PARAMS.house.autoFitLoans, 保存件数:stored.length,
      成功表示:(window.__alerts || []).filter(m => m.indexOf("保存しました") >= 0).length};
    /* ★「保存できない」ことを正しさにしない。**利用者が決めた額は保存できる**。
         資金の過不足は `validateParams()` が画面で伝える。 */
    out.tests.manual_loan_ok =
      fitted === 0 && manual > 0
      && PARAMS.house.autoFitLoans === false && stored.length === 1;
  }

  /* ============================================================
     P2-1  比較の許可リストが根で許していないか
     ============================================================ */
  {
    const list = (typeof COMPARE_ALLOWED !== "undefined")
      ? (COMPARE_ALLOWED.loadAllPresets || []) : [];
    const roots = list.filter(x => x === "house" || x === "estate");
    out.tests.compare_allowed = {件数:list.length, 根で許可:roots, 一部:list.slice(0, 12)};
    out.tests.compare_allowed_ok = roots.length === 0 && list.length > 0;
  }

  /* ============================================================
     維持している合格（v22〜v26で通っていたもの）
     ============================================================ */
  {
    reset();
    PARAMS.family.hasSpouse = true;
    PARAMS.income.wBase = 4000000;
    PARAMS.income.wTable = [{age:35,amount:4000000,rate:0},{age:66,amount:0,rate:0}];
    PARAMS.house.buy = true; PARAMS.house.price = 50000000;
    PARAMS.house.autoFitLoans = true; recalc();
    const counts = {};
    [["loadAllPresets",2],["loadAllWScenarios",7],
     ["loadAllSavingPlans",4],["loadRaisePatterns",4]].forEach(([fn, want]) => {
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
