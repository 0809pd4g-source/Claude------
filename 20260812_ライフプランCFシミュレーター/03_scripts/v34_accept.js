/* 汎用版 v34 受入試験。依存なし。対象HTMLを開いて全文を貼り、Enter（Promiseを返すので `await` するか、
   Playwrightなら page.evaluate がそのまま解決を待つ）。
   v32では不合格になり、v33で合格することを確かめるためのもの。 */
(async () => {
  const R = [];
  const T = (id, ok, detail) => R.push({id, ok: !!ok, detail});
  const P0 = () => genericParams();
  const clearStore = () => Object.values(STORE).forEach(k => { try{ localStorage.removeItem(k); }catch(e){} });
  const mark = P => { for(const s of READY_STEPS) for(const n of (s.need||[])) if(!n[2] || n[2](P)) markEntered(n[0]); };

  /* A: 取得済み持ち家の「いまの借入」を検査する */
  const owned = years => {
    PARAMS = P0();
    PARAMS.family.ageH = 40; PARAMS.house.buy = true; PARAMS.house.buyAge = 35;
    PARAMS.house.autoFitLoans = false;
    PARAMS.house.loans = [{name:"本人", amount:30000000, years:years, steps:[{y:1, rate:1.0}]}];
    mark(PARAMS);
    return readiness();
  };
  const a1 = owned(0);
  T("A1 取得済み・残債あり・返済期間0年は判断の準備にしない",
    a1.stage <= 1 && a1.housing.level === "insufficient",
    {stage:a1.stage, housing:a1.housing.level, missing:a1.missing});
  const a2 = owned(30);
  T("A2 返済期間を直せば元に戻る", a2.stage === 3 && a2.housing.level === "na", {stage:a2.stage});
  PARAMS = P0();
  PARAMS.family.ageH = 40; PARAMS.house.buy = true; PARAMS.house.buyAge = 35;
  PARAMS.house.autoFitLoans = false;
  PARAMS.house.loans = [{name:"本人", amount:0, years:0, steps:[{y:1, rate:1.0}]}];
  mark(PARAMS);
  const a3 = readiness();
  T("A3 完済済み（残債0）は妨げない", a3.stage === 3 && a3.housing.level === "na", {stage:a3.stage});
  PARAMS = P0();
  PARAMS.family.ageH = 40; PARAMS.house.buy = true; PARAMS.house.buyAge = 45;
  PARAMS.house.autoFitLoans = false;
  PARAMS.house.loans = [{name:"本人", amount:30000000, years:0, steps:[{y:1, rate:1.0}]}];
  mark(PARAMS);
  const a4 = readiness();
  T("A4 これから購入でも返済期間0年は止める", a4.stage <= 1, {stage:a4.stage});

  /* B: 保存できない値では「判断の準備が整いました」と言わない */
  T("B1 保存前検査と準備度が同じ検査を使う",
    Array.isArray(a1.badValues) && a1.badValues.length > 0, {badValues:a1.badValues});

  /* C: 0円の年収の有効性を人物ごとに同じ規則で決める */
  const w = (spouse, type) => { const P = P0(); P.family.hasSpouse = spouse; P.work.typeW = type; P.income.wBase = 0; return isUsable("income.wBase", P); };
  const h = type => { const P = P0(); P.work.typeH = type; P.income.hBase = 0; return isUsable("income.hBase", P); };
  T("C1 パートナー不在の0円は有効", w(false, "employee") === true);
  T("C2 パートナーあり・会社員の0円は要確認", w(true, "employee") === false);
  T("C3 パートナーあり・働かないの0円は有効", w(true, "none") === true);
  T("C4 本人・会社員の0円は要確認", h("employee") === false);
  T("C5 本人・働かないの0円は有効", h("none") === true);

  /* D: pending を復旧候補として実際に使う（ただし控えより優先しない） */
  const rec = n => ({name:n, params:P0()});
  const pend = JSON.stringify([rec("保留から戻る")]);
  const bak  = JSON.stringify([rec("控えから戻る")]);
  clearStore(); NOTICES = [];
  localStorage.setItem(STORE.plans, "{}");
  localStorage.setItem(STORE.plansBak, "{}");
  localStorage.setItem(STORE.plansPending, pend);
  localStorage.setItem(STORE.plansMarker, JSON.stringify({at:Date.now(), why:"backup-write-failed"}));
  loadPlans();
  T("D1 marker付きpendingから復旧し主領域へ書き戻す",
    PLANS.map(p => p.name).join() === "保留から戻る" && localStorage.getItem(STORE.plans) === pend,
    {names:PLANS.map(p => p.name), notices:NOTICES.map(n => n.id)});
  clearStore(); NOTICES = [];
  localStorage.setItem(STORE.plans, "{}");
  localStorage.setItem(STORE.plansBak, "{}");
  localStorage.setItem(STORE.plansPending, pend);
  loadPlans();
  T("D2 markerが無ければpendingを使わない",
    PLANS.length === 0 && NOTICES.some(n => n.id === "planbroken"), {notices:NOTICES.map(n => n.id)});
  clearStore(); NOTICES = [];
  localStorage.setItem(STORE.plans, "{}");
  localStorage.setItem(STORE.plansBak, bak);
  localStorage.setItem(STORE.plansPending, pend);
  localStorage.setItem(STORE.plansMarker, JSON.stringify({at:Date.now(), why:"x"}));
  loadPlans();
  T("D3 正常な控えはpendingより優先", PLANS.map(p => p.name).join() === "控えから戻る",
    {names:PLANS.map(p => p.name)});

  /* E: 回帰（v32で入れた分を壊していないこと） */
  clearStore(); NOTICES = [];
  loadPlans();
  T("E1 初回利用は無言で0件開始", PLANS.length === 0 && NOTICES.length === 0, {notices:NOTICES.map(n => n.id)});
  clearStore(); PLANS = []; PLANS_REV = null;
  const okCommit = commitPlans([rec("通常保存")]);
  T("E2 正常保存でprimaryと控えが一致",
    okCommit === true && localStorage.getItem(STORE.plans) === localStorage.getItem(STORE.plansBak));
  const semantic = ["{}", "null", '"文字列"', '[{"name":"A","params":null}]'];
  const semOk = semantic.every(v => { const r = parsePlansRaw(v); return !r.ok; });
  T("E3 意味的破損をmigration前に拒否", semOk);
  clearStore();
  PARAMS = P0();
  PARAMS.family.ageH = 40; PARAMS.income.hBase = 4000000;
  PARAMS.income.hTable = [{age:40, amount:4000000, rate:0}];
  PARAMS.living.table = [{age:40, amount:4200000, rate:0}];
  PARAMS.econ.deposit = 2000000;
  recalc(); setTab("check"); render();
  const txt = (document.querySelector("main>section.on").innerText || "").replace(/\s+/g, " ");
  T("E4 理由の文と次の文がつながっていない", !/要因はなし[^。]/.test(txt),
    {bad:(txt.match(/要因はなし[^。]{0,20}/g) || []).slice(0, 2)});
  PARAMS = P0(); PARAMS.house.buy = true; recalc(); setTab("loan"); render();
  const li = [...document.querySelectorAll("#s-loan input[type=number]")]
    /* ★「借入額」「返済期間」を含む欄は他にもある（返済期間の要件・銀行の借入額・借入額の差）。
     下限を付けたのは借入の行の2欄だけなので、そこに絞って測る。
     最初は緩い正規表現で拾って、直していない欄まで数えて不合格にしていた。 */
    .filter(e => /本目のローンの(借入額|返済期間)/.test(e.getAttribute("aria-label") || ""));
  T("E5 借入額と返済期間に下限がある",
    li.length >= 2 && li.every(e => e.getAttribute("min") !== null),
    li.map(e => ({label:e.getAttribute("aria-label"), min:e.getAttribute("min")})));
  const noType = [...document.querySelectorAll("button")].filter(b => b.getAttribute("type") !== "button");
  T("E6 すべてのbuttonにtype=button", noType.length === 0, {count:noType.length});

  /* ===== v34で追加（ChatGPT版のv33独立再レビューが落とした7試験） ===== */
  const markNeeds = P => { for(const st of READY_STEPS) for(const n of (st.need||[])) if(!n[2] || n[2](P)) markEntered(n[0]); };
  const ownedCase = mut => {
    PARAMS = P0();
    PARAMS.family.ageH = 40; PARAMS.house.buy = true; PARAMS.house.buyAge = 35;
    PARAMS.house.autoFitLoans = false;
    PARAMS.house.loans = [{name:"本人", amount:30000000, years:5, steps:[{y:1, rate:1}]}];
    if(mut) mut(PARAMS);
    markNeeds(PARAMS); recalc();
    return readiness();
  };
  const f1 = ownedCase();
  T("F1 契約期間が経過済みの残債は判断の準備にしない",
    f1.stage <= 1 && f1.housing.level === "insufficient",
    {stage:f1.stage, housing:f1.housing.level, blocking:f1.badValues});
  const f2 = ownedCase(P => { P.house.loans[0].years = 30; });
  T("F2 返済期間を直せば元に戻る", f2.stage === 3 && f2.housing.level === "na", {stage:f2.stage});
  const f3 = ownedCase(P => { P.house.loans[0].amount = 0; P.house.loans[0].years = 0; });
  T("F3 完済済み（残債0）は妨げない", f3.stage === 3, {stage:f3.stage});
  const f4 = ownedCase(P => { P.house.loans[0].years = 30; P.house.loans[0].steps = [{y:1, rate:-5}]; });
  T("F4 マイナス金利を止める", f4.stage <= 1 && f4.badValues.some(x => /金利/.test(x)),
    {stage:f4.stage, blocking:f4.badValues});
  const f5 = ownedCase(P => { P.house.loans[0].years = 30; P.house.loans[0].steps = []; });
  T("F5 金利段階なしを止める", f5.stage <= 1, {stage:f5.stage, blocking:f5.badValues});
  const f6 = ownedCase(P => { P.house.loans[0].years = 30; P.house.loans[0].steps = [{y:1,rate:1},{y:1,rate:2}]; });
  T("F6 開始年の逆転を止める", f6.stage <= 1 && f6.badValues.some(x => /開始年/.test(x)),
    {stage:f6.stage, blocking:f6.badValues});

  PARAMS = P0();
  PARAMS.family.ageH = 40; PARAMS.house.buy = true; PARAMS.house.buyAge = 35;
  PARAMS.house.autoFitLoans = false;
  PARAMS.house.loans = [{name:"本人", amount:0, years:0, steps:[{y:1, rate:1}]}];
  PARAMS.house.mgmtFee = -1200000;
  markNeeds(PARAMS); recalc();
  const g1 = readiness();
  const g1saved = commitPlans([{name:"負の管理費", params:PARAMS}]);
  T("G1 負の管理費は判断も保存も止める",
    g1.stage <= 1 && g1saved === false && g1.badValues.some(x => /管理費/.test(x)),
    {stage:g1.stage, saved:g1saved, blocking:g1.badValues});

  PARAMS = P0();
  PARAMS.family.ageH = 40; PARAMS.income.hBase = 6000000;
  PARAMS.income.hTable = [{age:40, amount:6000000, rate:0}];
  PARAMS.living.table = [{age:40, amount:3600000, rate:0}];
  PARAMS.econ.inflation = 1e307;
  markNeeds(PARAMS); recalc();
  const g2 = readiness();
  const g2saved = commitPlans([{name:"huge", params:PARAMS}]);
  T("G2 試算結果が非有限なら判断も保存も止める",
    g2.stage <= 1 && g2saved === false, {stage:g2.stage, saved:g2saved, blocking:g2.badValues});

  const badCur = P0();
  badCur.family.ageH = 40; badCur.income.hBase = 6000000;
  badCur.income.hTable = [{age:40, amount:6000000, rate:0}];
  badCur.living.table = [{age:40, amount:3600000, rate:0}];
  badCur.econ.inflation = 1e307;
  PARAMS = P0(); PARAMS.family.ageH = 41; recalc();
  const beforeImport = {ageH:PARAMS.family.ageH, inflation:PARAMS.econ.inflation, plans:PLANS.length};
  let importAlert = null;
  const origAlert = window.alert; window.alert = m => { importAlert = String(m); };
  try{
    importPlans({files:[new File([JSON.stringify({format:"lpcf-plans", version:3,
      current:{name:"bad", params:badCur}, plans:[]})], "bad.json", {type:"application/json"})], value:""});
  }catch(e){ importAlert = "throw:" + e.message; }
  /* ★`importPlans` は FileReader を使うので**非同期**。
       待たずに測ると、取込前後が同じに見えて**どの版でも合格してしまう**。
       最初はこれに気づかず、v33でもv34でも通る意味のない試験になっていた。 */
  await new Promise(r => setTimeout(r, 300));
  window.alert = origAlert;
  const afterImport = {ageH:PARAMS.family.ageH, inflation:PARAMS.econ.inflation, plans:PLANS.length};
  T("G3 不正なJSONは何も変えずに拒否する",
    JSON.stringify(beforeImport) === JSON.stringify(afterImport),
    {before:beforeImport, after:afterImport});

  /* ★旧版でも走るようにする。v33に `hashText` は無いので、無ければ代用を使う。
       受入試験は「新版で通る」だけでなく「旧版で落ちる」ことを示すためのものなので、
       旧版で例外になって止まってはいけない。 */
  const hash = (typeof hashText === "function") ? hashText : (t => "nohash:" + String(t == null ? "" : t).length);
  const pendRec = JSON.stringify([rec("保留候補")]);
  clearStore(); PLANS = []; NOTICES = [];
  localStorage.setItem(STORE.plans, "{}");
  localStorage.setItem(STORE.plansBak, "{}");
  localStorage.setItem(STORE.plansPending, pendRec);
  localStorage.setItem(STORE.plansMarker, JSON.stringify({at:Date.now(), why:"x", payloadHash:hash("別の内容")}));
  loadPlans();
  T("H1 印と中身の指紋が違うpendingは採用しない",
    PLANS.length === 0 && NOTICES.some(n => n.id === "planbroken"),
    {names:PLANS.map(p => p.name), notices:NOTICES.map(n => n.id)});

  clearStore(); PLANS = []; NOTICES = [];
  localStorage.setItem(STORE.plans, "{}");
  localStorage.setItem(STORE.plansBak, "{}");
  localStorage.setItem(STORE.plansPending, pendRec);
  localStorage.setItem(STORE.plansMarker, JSON.stringify({at:0, why:"backup-write-failed"}));
  loadPlans();
  const staleText = NOTICES.map(n => String(n.html || "")).join(" ");
  T("H2 古い・旧形式の候補から戻すときは必ず断る",
    PLANS.map(p => p.name).join() === "保留候補" && /24時間より前/.test(staleText) && /古い形式/.test(staleText),
    {names:PLANS.map(p => p.name), hasStale:/24時間より前/.test(staleText), hasLegacy:/古い形式/.test(staleText)});

  clearStore();
  PARAMS = P0(); PARAMS.house.buy = true; recalc(); render();
  let numTotal = 0, numMin = 0, numBadNeg = 0, numViolate = 0;
  ((typeof TABS !== "undefined") ? TABS.map(x => x[0]) : []).forEach(t => {
    try{ setTab(t); render(); }catch(e){ return; }
    [...document.querySelectorAll("main>section.on input[type=number]")]
      .filter(e => e.getClientRects().length).forEach(e => {
        numTotal++;
        const min = e.getAttribute("min"), max = e.getAttribute("max");
        const v = e.value === "" ? null : Number(e.value);
        const path = ((typeof numPathOf === "function") ? numPathOf(e) : null) || "";
        if(min !== null) numMin++;
        /* 率・変動率以外で負を許していたら不合格（V92で相手が踏んだ穴） */
        if(min !== null && Number(min) < 0 && !/(rate|growth|inflation|share)$/i.test(path)) numBadNeg++;
        if(v !== null && ((min !== null && v < Number(min)) || (max !== null && v > Number(max)))) numViolate++;
      });
  });
  T("I1 数値欄に意味のある下限が付いている",
    numMin >= 100 && numBadNeg === 0 && numViolate === 0,
    {total:numTotal, withMin:numMin, wrongNegativeMin:numBadNeg, selfViolating:numViolate});

  clearStore();
  const pass = R.filter(x => x.ok).length;
  console.log(`v34受入試験: ${pass}/${R.length} 合格`);
  R.filter(x => !x.ok).forEach(x => console.log("  NG " + x.id, x.detail));
  return {passed:pass, total:R.length, failed:R.filter(x => !x.ok).map(x => x.id), results:R};
})()
