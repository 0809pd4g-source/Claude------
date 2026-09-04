/* v23 受入試験（ブラウザで実行）。
 *
 * ★v22 と v23 の両方に流すこと。v22で落ち、v23で通ってはじめて「直った」と言える。
 *
 * 使い方：`__V23_ACCEPT__()` を呼ぶ。JSONを返す。
 */
window.__V23_ACCEPT__ = function(){
  const out = {version:(typeof VERSION!=="undefined"?VERSION.tag:"?"), tests:{}};
  const errs = [];
  const realConfirm = window.confirm, realAlert = window.alert, realPrompt = window.prompt;
  window.confirm = () => true;
  window.alert = m => (window.__alerts = window.__alerts || []).push(String(m));
  window.prompt = () => null;

  const reset = () => {
    try{ localStorage.removeItem(STORE.plans); }catch(e){}
    PLANS = [];
    PARAMS = defaults("buy", "keep", "manual");
    PARAMS.meta.blank = false;
    recalc();
  };

  /* 利用者が自分の家計を入れた状態を作る（既定値と全部ちがう値にする） */
  const setUserHousehold = () => {
    reset();
    PARAMS.family.ageH = 44; PARAMS.family.ageW = 42;
    PARAMS.family.children = [{name:"子", birthYear:2020, plan:{}}];
    PARAMS.income.hBase = 7770000;
    PARAMS.income.hTable = [{age:44, amount:7770000, rate:0}, {age:66, amount:0, rate:0}];
    PARAMS.income.wBase = 3330000;
    PARAMS.income.wTable = [{age:42, amount:3330000, rate:0}, {age:66, amount:0, rate:0}];
    PARAMS.living.table = [{age:44, amount:4440000, rate:0}];
    PARAMS.econ.deposit = 12340000; PARAMS.econ.invest = 5670000;
    PARAMS.econ.inflation = 1.3;
    PARAMS.house.price = 67890000; PARAMS.house.selfFund = 8900000;
    PARAMS.saving.nisaMonthlyH = 12345;
    PARAMS.retire.retireAgeH = 67;
    recalc();
    return clone(PARAMS);
  };

  /* ---------- 1. 比較プランが「その軸だけ」を変えているか（P0-1） ---------- */
  /** base と p の差分パスを列挙する（配列は length と各要素を見る）。 */
  const diffPaths = (a, b, path, out) => {
    out = out || []; path = path || "";
    if(a === b) return out;
    const ta = Object.prototype.toString.call(a), tb = Object.prototype.toString.call(b);
    if(ta !== tb){ out.push(path); return out; }
    if(Array.isArray(a)){
      if(a.length !== b.length) out.push(path + ".length");
      const n = Math.min(a.length, b.length);
      for(let i = 0; i < n; i++) diffPaths(a[i], b[i], path + "[" + i + "]", out);
      return out;
    }
    if(a && typeof a === "object"){
      const keys = new Set(Object.keys(a).concat(Object.keys(b)));
      keys.forEach(k => diffPaths(a[k], b[k], path ? path + "." + k : k, out));
      return out;
    }
    if(a !== b) out.push(path);
    return out;
  };
  /** 許可リストに含まれるか（前方一致：`house` は `house.price` を許す）。 */
  const allowedBy = (list, p) =>
    list.some(a => p === a || p.indexOf(a + ".") === 0 || p.indexOf(a + "[") === 0);

  const scenarioTest = (name, fn) => {
    const base = setUserHousehold();
    try{ fn(); }catch(e){ errs.push(name + ": " + e.message); }
    const allowed = (typeof COMPARE_ALLOWED !== "undefined" && COMPARE_ALLOWED[name]) || [];
    const rows = PLANS.map(pl => {
      const bad = diffPaths(base, pl.params).filter(p => !allowedBy(allowed, p));
      return {name:pl.name, 許可外の差分:bad.length, 例:bad.slice(0, 6)};
    });
    return {件数:PLANS.length, 許可リスト:allowed,
            許可外の合計:rows.reduce((s, r) => s + r.許可外の差分, 0), 各プラン:rows};
  };

  out.tests.scenario = {
    loadAllWScenarios: scenarioTest("loadAllWScenarios", () => loadAllWScenarios()),
    loadAllPresets:    scenarioTest("loadAllPresets",    () => loadAllPresets()),
    loadRaisePatterns: scenarioTest("loadRaisePatterns", () => loadRaisePatterns()),
    loadAllSavingPlans:scenarioTest("loadAllSavingPlans",() => loadAllSavingPlans()),
  };
  out.tests.scenario_ok = Object.values(out.tests.scenario)
    .every(x => x.件数 > 0 && x.許可外の合計 === 0);

  /* ひとり暮らしでパートナー収入の比較を作らないこと */
  reset();
  PARAMS.family.hasSpouse = false; PARAMS.family.ageW = 0; recalc();
  try{ loadAllWScenarios(); }catch(e){ errs.push("single: " + e.message); }
  out.tests.single_household = {生成件数:PLANS.length};
  out.tests.single_household_ok = PLANS.length === 0;

  /* ---------- 2. 価格スイープ（P0-2） ---------- */
  const sweepCase = (label, setup) => {
    reset(); setup(PARAMS); recalc();
    let ex = null;
    try{ sweepPrice(); }catch(e){ ex = String(e.message); }
    let stored = [];
    try{ stored = JSON.parse(localStorage.getItem(STORE.plans) || "[]"); }catch(e){}
    const loans = stored.map(p => (p.params.house.loans || []).map(l => l.amount)).flat();
    /* 保存された全数値に非有限（JSON経由で null になったもの）が無いか */
    const nulls = [];
    const scan = (o, path) => {
      if(o === null){ if(/amount|price|fees|selfFund|deposit|invest/.test(path)) nulls.push(path); return; }
      if(Array.isArray(o)) return o.forEach((v, i) => scan(v, path + "[" + i + "]"));
      if(o && typeof o === "object") return Object.keys(o).forEach(k => scan(o[k], path + "." + k));
    };
    scan(stored, "plans");
    return {label, 例外:ex, メモリ:PLANS.length, 保存:stored.length,
            借入:loans.slice(0, 8),
            null件数:nulls.length, 負の借入:loans.filter(v => typeof v === "number" && v < 0).length,
            件数一致:PLANS.length === stored.length};
  };
  out.tests.sweep = {
    購入_借入0円: sweepCase("購入・現在借入0円", P => {
      P.house.buy = true;
      P.house.loans = [{name:"あなた", amount:0, years:35, steps:[{y:1, rate:1}]}];
    }),
    自己資金超過: sweepCase("自己資金が取得額を上回る", P => {
      P.house.buy = true; P.house.price = 50000000; P.house.fees = 3500000;
      P.house.selfFund = 53500000; P.house.autoFitLoans = false;
      P.house.loans = [{name:"あなた", amount:1000000, years:35, steps:[{y:1, rate:1}]}];
    }),
    賃貸: sweepCase("賃貸（購入しない）", P => { P.house.buy = false; }),
    価格0: sweepCase("購入だが価格0", P => { P.house.buy = true; P.house.price = 0; }),
    借入配列なし: sweepCase("借入の配列が空", P => {
      P.house.buy = true; P.house.loans = [];
    }),
  };
  /* 合格条件：nullなし・負の借入なし・件数一致。
     購入していない／価格0のときは作らない（0件が正しい）。 */
  out.tests.sweep_ok =
    Object.values(out.tests.sweep).every(x =>
      x.null件数 === 0 && x.負の借入 === 0 && x.件数一致 && !x.例外)
    && out.tests.sweep.賃貸.保存 === 0
    && out.tests.sweep.価格0.保存 === 0
    && out.tests.sweep.購入_借入0円.保存 === 7;

  /* 非有限値を直接ねじ込んでも保存されないこと */
  reset();
  {
    const p = clone(PARAMS); p.house.loans[0].amount = NaN;
    const okNaN = commitPlans(withPlanIn([], p, "NaN試験"));
    const p2 = clone(PARAMS); p2.house.loans[0].amount = -1000000;
    const okNeg = commitPlans(withPlanIn([], p2, "負数試験"));
    out.tests.reject_bad = {NaNを拒否:okNaN === false, 負の借入を拒否:okNeg === false};
    out.tests.reject_bad_ok = okNaN === false && okNeg === false;
  }

  /* ---------- 3. 国保の概算警告（P1-1） ---------- */
  const warnOf = (mutate) => {
    const P = genericParams();
    P.meta.blank = false; P.work.typeH = "self"; P.family.hasSpouse = false;
    P.meta.inputState = {};
    mutate(P);
    return validateParams(P, null)
      .filter(x => /国民健康保険の料率/.test(x.msg)).length;
  };
  out.tests.kokuho_warn = {
    何も確認しない: warnOf(() => {}),
    医療分所得割だけ確認: warnOf(P => { P.meta.inputState["tax.kokuhoMedRate"] = {source:"user", confirmed:true}; }),
    医療分均等割だけ確認: warnOf(P => { P.meta.inputState["tax.kokuhoMedPer"] = {source:"user", confirmed:true}; }),
    介護分だけ確認: warnOf(P => { P.meta.inputState["tax.kokuhoCareRate"] = {source:"user", confirmed:true}; }),
    自治体を確認した: warnOf(P => { P.tax.kokuhoMunicipalityConfirmed = true; }),
  };
  /* 合格条件：自治体を確認したときだけ消える */
  out.tests.kokuho_warn_ok =
    out.tests.kokuho_warn.何も確認しない === 1
    && out.tests.kokuho_warn.医療分所得割だけ確認 === 1
    && out.tests.kokuho_warn.医療分均等割だけ確認 === 1
    && out.tests.kokuho_warn.介護分だけ確認 === 1
    && out.tests.kokuho_warn.自治体を確認した === 0;

  /* ---------- 4. 国保の値が新宿区・令和8年度か（P1-2）＋手計算との照合 ---------- */
  {
    const T = genericParams().tax;
    const 期待 = {kokuhoMedRate:7.51, kokuhoMedPer:47600, kokuhoMedCap:670000,
                  kokuhoSupRate:2.80, kokuhoSupPer:17600, kokuhoSupCap:260000,
                  kokuhoCareRate:2.43, kokuhoCarePer:17800, kokuhoCareCap:170000,
                  kokuhoKodomoRate:0.27, kokuhoKodomoPer:1873, kokuhoKodomoCap:30000};
    const ちがう = Object.keys(期待).filter(k => T[k] !== 期待[k])
      .map(k => `${k}: ${T[k]} ≠ ${期待[k]}`);

    /* 手計算：単身40歳・前年所得300万円・軽減なし
       賦課基準額 = 3,000,000 − 430,000 = 2,570,000
       医療 2,570,000×7.51% =193,007 + 47,600 = 240,607
       支援 2,570,000×2.80% = 71,960 + 17,600 =  89,560
       介護 2,570,000×2.43% = 62,451 + 17,800 =  80,251
       子ども 2,570,000×0.27% =  6,939 +  1,873 =   8,812
       合計 419,230
       ★最初 240,556.7 と書いて試験が落ちた。**エンジンではなく手計算のほうが誤り**
         （193,007 を 192,957 と掛け違えた）。検査が食い違ったら、まず自分の数字を疑う。 */
    const kh = kokuhoHousehold([{inc:3000000, prevInc:3000000, age:40}], T);
    out.tests.kokuho_values = {ちがう値:ちがう,
      手計算:419230, エンジン:Math.round(kh.total * 10) / 10,
      差:Math.round((kh.total - 419230) * 10) / 10};
    out.tests.kokuho_values_ok = ちがう.length === 0 && Math.abs(kh.total - 419230) < 1;
  }

  window.confirm = realConfirm; window.alert = realAlert; window.prompt = realPrompt;
  reset();
  out.errors = errs;
  out.ok = ["scenario_ok","single_household_ok","sweep_ok","reject_bad_ok",
            "kokuho_warn_ok","kokuho_values_ok"].every(k => out.tests[k]);
  return out;
};
"__V23_ACCEPT__ ready";
