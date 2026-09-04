/* 汎用版 v33 受入試験。依存なし。対象HTMLを開いて全文を貼り、Enter。
   v32では不合格になり、v33で合格することを確かめるためのもの。 */
(() => {
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

  clearStore();
  const pass = R.filter(x => x.ok).length;
  console.log(`v33受入試験: ${pass}/${R.length} 合格`);
  R.filter(x => !x.ok).forEach(x => console.log("  NG " + x.id, x.detail));
  return {passed:pass, total:R.length, failed:R.filter(x => !x.ok).map(x => x.id), results:R};
})()
