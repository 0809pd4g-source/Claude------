/* v24 受入試験。★v23（基準線）で落ち、v24で通ることを確かめる。 */
window.__V24_ACCEPT__ = function(){
  const out = {version:(typeof VERSION!=="undefined"?VERSION.tag:"?"), tests:{}};
  const errs = [];
  const rc = window.confirm, ra = window.alert, rp = window.prompt;
  window.confirm = () => true;
  window.alert = m => (window.__alerts = window.__alerts || []).push(String(m));
  window.prompt = () => null;
  const reset = () => {
    try{ localStorage.removeItem(STORE.plans); }catch(e){}
    PLANS = []; PARAMS = defaults("buy","keep","manual"); PARAMS.meta.blank = false; recalc();
  };

  /* ---------- P0-1 住宅比較が手入力の年齢別保険表を壊さないか ---------- */
  {
    reset();
    const P = clone(PARAMS);
    P.family.ageH = 44; P.family.ageW = 42;
    P.living.insMode = "table";
    P.living.insurance = 111111; P.living.insuranceAfter = 234567;
    P.living.insTable = [{age:44,amount:111111,rate:0},
                         {age:50,amount:222222,rate:0},
                         {age:65,amount:333333,rate:0}];
    P.house.buy = true; P.house.price = 30000000;
    const before = JSON.stringify(P.living.insTable);
    const Q = planWithPreset(P, "buy");                 // 同じプリセット（住宅条件は不変）
    const R = planWithPreset(P, "rent");
    /* 実際のコマンドでも確かめる */
    PARAMS = clone(P); recalc();
    loadAllPresets();
    const cmd = PLANS.map(pl => ({name:pl.name,
      表:JSON.stringify(pl.params.living.insTable) === before}));
    out.tests.ins_table = {
      同一プリセットで表が不変:JSON.stringify(Q.living.insTable) === before,
      賃貸プリセットでも表が不変:JSON.stringify(R.living.insTable) === before,
      住宅条件は同じ:Q.house.buy === P.house.buy && Q.house.price === P.house.price,
      コマンド経由:cmd,
      見直しの案内:!!R.meta.insReviewNeeded};
    out.tests.ins_table_ok =
      out.tests.ins_table.同一プリセットで表が不変
      && out.tests.ins_table.賃貸プリセットでも表が不変
      && cmd.length > 0 && cmd.every(x => x.表);
  }

  /* ---------- P0-2 詳細諸費用で借入が必要額に届くか ---------- */
  {
    /* ★`fundingGap()` は v24 で追加したもの。基準線（v23）でも同じ試験を流せるよう、
         無ければここで同じ計算をする。**基準線が動かないと「直った」が言えない。** */
    const gapNow = (H) => (typeof fundingGap === "function") ? fundingGap(H)
      : (Number(H.price||0) + feeTotal(H) - Number(H.selfFund||0) - Number(H.gift||0)
         - (H.loans||[]).reduce((s,l)=>s+(Number(l.amount)||0),0));
    const gapOf = (setup) => {
      reset();
      const P = clone(PARAMS); const H = P.house;
      H.buy = true; H.price = 50000000; H.selfFund = 10000000; H.gift = 0;
      H.feeMode = "detail"; H.feeBrokerageAuto = true; H.feeLoanRate = 2.2;
      setup(H);
      fitLoansOn(P);
      return {借入:H.loans.reduce((s,l)=>s+l.amount,0),
              資金差額:Math.round(gapNow(H))};
    };
    const cases = {
      現在借入0円:      gapOf(H => { H.loans=[{name:"あなた",amount:0,years:35,steps:[{y:1,rate:1}]}]; }),
      現在借入4000万:   gapOf(H => { H.loans=[{name:"あなた",amount:40000000,years:35,steps:[{y:1,rate:1}]}]; }),
      借入配列が空:      gapOf(H => { H.loans=[]; }),
      複数借入3対1:     gapOf(H => { H.loans=[{name:"A",amount:30000000,years:35,steps:[{y:1,rate:1}]},
                                            {name:"B",amount:10000000,years:35,steps:[{y:1,rate:1.2}]}]; }),
      手数料0パーセント:  gapOf(H => { H.feeLoanRate=0; H.loans=[{name:"あなた",amount:0,years:35,steps:[{y:1,rate:1}]}]; }),
      自己資金超過:      gapOf(H => { H.selfFund=60000000; H.loans=[{name:"あなた",amount:40000000,years:35,steps:[{y:1,rate:1}]}]; }),
    };
    /* 価格スイープを実コマンドで回す */
    reset();
    PARAMS.house.buy = true; PARAMS.house.price = 50000000; PARAMS.house.selfFund = 10000000;
    PARAMS.house.gift = 0; PARAMS.house.feeMode = "detail";
    PARAMS.house.feeBrokerageAuto = true; PARAMS.house.feeLoanRate = 2.2;
    PARAMS.house.loans = [{name:"あなた",amount:0,years:35,steps:[{y:1,rate:1}]}];
    recalc();
    try{ sweepPrice(); }catch(e){ errs.push("sweepPrice: "+e.message); }
    const sweep = PLANS.map(pl => ({name:pl.name,
      価格:pl.params.house.price,
      借入:pl.params.house.loans.reduce((s,l)=>s+l.amount,0),
      資金差額:Math.round(gapNow(pl.params.house))}));
    out.tests.loan_fit = {各ケース:cases, 価格スイープ:sweep};
    /* 許容差は丸め（1万円単位×借入本数）＋わずかな端数 */
    const TOL = 20000;
    /* ★「不足」だけを不合格にする。**余り（負の差額）は欠陥ではない**
         （自己資金が取得額を上回れば借入0で正しい）。
         最初 `Math.abs()` で見て自己資金超過を不合格にし、製品を疑いかけた。 */
    const okGap = x => x.資金差額 <= TOL && (x.資金差額 >= -TOL || x.借入 === 0);
    out.tests.loan_fit_ok =
      Object.values(cases).every(okGap)
      && sweep.length === 7 && sweep.every(okGap);
  }

  /* ---------- P0-3 実入力の巨大数が保存されないか ---------- */
  {
    reset(); setTab("assets");
    window.__alerts = [];
    /* 実際の入力欄を探して値を入れる（onMan を通す） */
    /* ★セレクタは**厳密に**書く。`includes('econ.deposit')` だと
         `econ.depositRate`（利回りの欄・`onNum`）に前方一致してしまい、
         **別の欄を測って「拒否された」と誤読した**（2026-08-31）。 */
    const inp = [...document.querySelectorAll('input')]
      .find(x => /onMan\('econ\.deposit'/.test(x.getAttribute('oninput')||''));
    const beforeDeposit = PARAMS.econ.deposit;
    let via = "input";
    if(inp){ inp.value = "1e307"; inp.dispatchEvent(new Event('input',{bubbles:true})); }
    else { via = "欄が見つからない"; }
    const afterInput = {経路:via, 入力前:beforeDeposit, 預金:PARAMS.econ.deposit,
                        有限:Number.isFinite(PARAMS.econ.deposit),
                        値が変わっていない:beforeDeposit === PARAMS.econ.deposit,
                        知らせ:document.body.innerText.includes("数値として扱えない")};
    /* そのうえで保存を試みる */
    PARAMS.meta.planName = "巨大数";
    const pn = document.getElementById("planName"); if(pn) pn.value = "巨大数";
    savePlan();
    let stored = [];
    try{ stored = JSON.parse(localStorage.getItem(STORE.plans) || "[]"); }catch(e){}
    out.tests.huge_input = {入力後:afterInput, プラン件数:PLANS.length, 保存件数:stored.length,
      成功表示:(window.__alerts||[]).some(m => /保存しました/.test(m)),
      預金がnull:stored.length ? stored[0].params.econ.deposit === null : null};
    /* ★合格条件：**PARAMSが汚れない・値が変わらない・画面で断る**。
         入力が拒否されたあとに正常なプランを保存できるのは正しい挙動なので、
         「保存0件」を条件にしてはいけない（最初それで製品を疑いかけた）。
         保存された預金が有限であることも見る。 */
    out.tests.huge_input_ok =
      inp !== undefined
      && afterInput.有限 && afterInput.値が変わっていない && afterInput.知らせ
      && (stored.length === 0 || Number.isFinite(stored[0].params.econ.deposit));
  }

  /* ---------- P0-4 年金だけの世帯の国保が翌年も変わらないか ---------- */
  {
    const P = genericParams();
    P.meta.baseYear = 2026; P.meta.endAge = 73; P.meta.blank = false;
    P.family.ageH = 71; P.family.ageW = 68; P.family.hasSpouse = true;
    P.family.children = []; P.family.householdHead = "h";
    P.work.typeH = "self"; P.work.typeW = "self";
    P.income.hBase = 0; P.income.wBase = 0;
    P.income.hTable = [{age:71,amount:0,rate:0}]; P.income.wTable = [{age:68,amount:0,rate:0}];
    P.living.table = [{age:71,amount:0,rate:0}];
    P.house.buy = false; P.house.rentNow = 0; P.econ.deposit = 0; P.econ.invest = 0;
    P.saving.dcModeH = false; P.saving.dcModeW = false;
    P.saving.nisaMonthlyH = 0; P.saving.nisaMonthlyW = 0;
    P.saving.stockMonthlyH = 0; P.saving.stockMonthlyW = 0;
    P.retire.pensionAuto = false; P.retire.pensionH = 3100000; P.retire.pensionW = 2600000;
    P.retire.pensionStartH = 65; P.retire.pensionStartW = 65;
    P.tax.residentPrevYear = false; P.tax.kokuminNenkinMonthly = 0;
    P.tax.kokuhoPrevIncH = 2000000; P.tax.kokuhoPrevIncW = 1500000;
    P.meta.inputState = {"tax.kokuhoPrevIncH":{source:"user",confirmed:true},
                         "tax.kokuhoPrevIncW":{source:"user",confirmed:true}};
    const S = simulate(P);
    const rows = S.rows.map(r => ({年:r.year,
      国保:Math.round((r.taxH.social + r.taxW.social) * 10) / 10}));
    const vals = rows.map(r => r.国保);
    out.tests.pension_kokuho = {各年:rows,
      最大差:Math.round((Math.max(...vals) - Math.min(...vals)) * 10) / 10};
    /* 合格条件：年金が同額なら国保も毎年ほぼ同額（丸めの範囲） */
    out.tests.pension_kokuho_ok = out.tests.pension_kokuho.最大差 < 1000;
  }

  /* ---------- P1-2 65歳以上の年金15万円控除 ---------- */
  {
    const T = clone(genericParams().tax);
    const one = (age, prevInc, pension) =>
      kokuhoHousehold([{inc:prevInc, prevInc:prevInc, age:age,
                        wageEarner:pension>0, pensionInc:pension, prevPensionInc:pension}], T);
    const a = one(70, 530000, 530000);   // 70歳・前年所得53万・年金あり
    const b = one(60, 530000, 0);        // 60歳・年金なし（控除の対象外）
    out.tests.pension65 = {
      '70歳_年金あり':{軽減率:a.reduce, 合計:Math.round(a.total*10)/10},
      '60歳_年金なし':{軽減率:b.reduce, 合計:Math.round(b.total*10)/10},
      控除額:T.kokuhoPension65Deduct};
    /* 53万 − 15万 = 38万 ≦ 43万 → 7割軽減。年金なしの60歳は5割のまま。 */
    out.tests.pension65_ok = a.reduce === 0.7 && b.reduce === 0.5;
  }

  /* ---------- P1-1 確認が値の編集で失効するか ---------- */
  {
    const warn = () => {
      const P = clone(PARAMS);
      return validateParams(P, null).filter(x => /国民健康保険の料率/.test(x.msg)).length;
    };
    reset(); PARAMS.work.typeH = "self"; PARAMS.family.hasSpouse = false; recalc();
    /* ★`setKokuhoConfirmed` は v24 で追加したもの。基準線（v23）では
         チェックボックス直結だったので、そちらの経路で同じ操作をする。 */
    const setConfirmed = (on) => {
      if(typeof setKokuhoConfirmed === "function") return setKokuhoConfirmed(on);
      PARAMS.tax.kokuhoMunicipalityConfirmed = !!on; recalc();
    };
    const before = warn();
    setConfirmed(true);
    const afterConfirm = warn();
    onNum("tax.kokuhoMedRate", "99");
    const afterEdit = warn();
    setConfirmed(true);
    const afterReconfirm = warn();
    out.tests.confirm_fp = {未確認:before, 確認後:afterConfirm,
      料率を99に変更後:afterEdit, 再確認後:afterReconfirm,
      指紋:PARAMS.tax.kokuhoConfirmedFingerprint ? "あり" : "なし"};
    out.tests.confirm_fp_ok =
      before === 1 && afterConfirm === 0 && afterEdit === 1 && afterReconfirm === 0;
  }

  /* ---------- P2-1 保存後の書き戻し確認 ---------- */
  {
    reset();
    const realSet = localStorage.setItem.bind(localStorage);
    const realGet = localStorage.getItem.bind(localStorage);
    /* 例外を出さずに別の内容を書く環境を作る */
    localStorage.setItem = (k, v) => realSet(k, k === STORE.plans ? "[]" : v);
    window.__alerts = [];
    const ok = commitPlans(withPlan(defaults("rent","keep","manual"), "書き戻し試験"));
    localStorage.setItem = realSet;
    out.tests.readback = {戻り値:ok, メモリ件数:PLANS.length,
      成功表示:(window.__alerts||[]).some(m => /保存しました/.test(m))};
    out.tests.readback_ok = ok === false && PLANS.length === 0;
  }

  /* ---------- 取り込み：`.f` ラベルの潰れ ---------- */
  {
    const tabs = [...document.querySelectorAll('#nav button[data-t]')].map(x => x.dataset.t);
    let n = 0; const narrow = []; let over = 0;
    for(const t of tabs){
      try{ setTab(t); }catch(e){ continue; }
      document.querySelectorAll('#s-'+t+' details').forEach(x => x.open = true);
      for(const lab of document.querySelectorAll('#s-'+t+' .f>label')){
        const b = lab.getBoundingClientRect();
        if(b.width === 0 && b.height === 0) continue;
        n++;
        if(b.width < 40) narrow.push({t, txt:lab.textContent.trim().slice(0,14),
                                      w:Math.round(b.width*10)/10, h:Math.round(b.height*10)/10});
      }
      for(const fr of document.querySelectorAll('#s-'+t+' .f')){
        if(fr.offsetParent === null) continue;
        if(fr.scrollWidth - fr.clientWidth > 1) over++;
      }
    }
    out.tests.labels = {画面幅:innerWidth, 調べたラベル:n,
      幅40px未満:narrow.length, 例:narrow.slice(0,4), はみ出す行:over};
    /* 狭い画面（760px以下）は縦積みなので対象外 */
    out.tests.labels_ok = innerWidth <= 760
      ? true : (narrow.length === 0 && over === 0);
  }

  window.confirm = rc; window.alert = ra; window.prompt = rp;
  reset();
  out.errors = errs;
  out.ok = ["ins_table_ok","loan_fit_ok","huge_input_ok","pension_kokuho_ok",
            "pension65_ok","confirm_fp_ok","readback_ok","labels_ok"]
    .every(k => out.tests[k]);
  return out;
};
"__V24_ACCEPT__ ready";
