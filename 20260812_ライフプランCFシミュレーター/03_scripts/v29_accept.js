/* v29 受入試験。★v28（基準線）で落ち、v29で通ることを確かめる。
   ChatGPT版の v28 レビュー（静的監査5件が不合格）に対応する。

   ★5件のうち2件は実在した。3件は正規表現がこちらの実装を拾えていないだけだった。
     **後者は「挙動」で示す**（マーカーの有無ではなく、利用者の操作の結果で測る）。 */
window.__V29_ACCEPT__ = function(){
  const out = {version:(typeof VERSION !== "undefined" ? VERSION.tag : "?"), tests:{}};
  const rc = window.confirm, ra = window.alert, rp = window.prompt;
  window.confirm = () => true;
  window.alert = m => (window.__alerts = window.__alerts || []).push(String(m));
  const reset = () => {
    try{ localStorage.removeItem(STORE.plans); }catch(e){}
    PLANS = []; PARAMS = genericParams(); PARAMS.meta.blank = false;
    window.__alerts = []; window.prompt = () => null; recalc();
  };
  /* ★基準線（v28）には v29 で足した関数が無い。同じ式をここに持つ。
       **基準線が動かないと「直った」が言えない。** */
  const inputCount = () => (typeof wizInputCount === "function") ? wizInputCount()
    : WIZ_STEPS.filter(s => s.kind !== "view").length;
  const inputTitles = () => (typeof wizInputTitles === "function") ? wizInputTitles()
    : WIZ_STEPS.filter(s => s.kind !== "view").map(s => s.t);
  const wording = () => (typeof checkWizardWording === "function")
    ? checkWizardWording()
    : [{問題:"案内文の突き合わせが実装されていない"}];

  /* ============================================================
     A（実在）案内文が実体と一致するか  — テストID wizard.not_six
     ============================================================ */
  {
    reset();
    const saved = WIZ_ON; WIZ_ON = false;
    const html = wizardBlock();
    WIZ_ON = saved;
    const text = html.replace(/<[^>]*>/g, "");
    const m = text.match(/まず\s*(\d+)\s*つの質問/);
    out.tests.wording = {
      案内の件数:m ? Number(m[1]) : null,
      入力ステップ数:inputCount(),
      旧文言が残っている:text.indexOf("まず6つの質問") >= 0 && inputCount() !== 6,
      案内に出ていない入力ステップ:
        inputTitles().filter(x => text.indexOf(x) < 0),
      突き合わせ:wording()};
    out.tests.wording_ok =
      m !== null && Number(m[1]) === inputCount()
      && out.tests.wording.案内に出ていない入力ステップ.length === 0
      && wording().length === 0;

    /* 負試験：ステップを1つ足したら案内文の突き合わせが落ちるか。 */
    WIZ_STEPS.push({t:"試験用", n:"試験用", kind:"input", covers:[]});
    const broken = wording().length;
    WIZ_STEPS.pop();
    out.tests.wording_negative = broken;
    out.tests.wording_ok = out.tests.wording_ok && broken === 0;
    /* ★件数も項目名も `WIZ_STEPS` から作るので、足しても案内文が追いつく＝0件が正しい。
         **負試験は「案内文だけを古い手書きに戻す」形にする。**
         最初は `wizInputTitles()` を差し替えたが、**案内文も検査も同じ関数を読むので
         両方が同時に変わり、食い違いが出なかった**（＝一本化できている証拠でもある）。
         壊すのは案内文の側だけ。 */
    out.tests.wording_negative2 = (function(){
      if(typeof checkWizardWording !== "function") return 0;   // v28には無い
      const orig = window.wizardBlock;
      try{
        window.wizardBlock = () => '<div><b>はじめて使う方は、まず6つの質問に'
          + '答えください。</b>世帯・収入・いまの資産・住まい・生活費・気になること'
          + 'を順に聞きます。</div>';
        return checkWizardWording().length;
      }finally{ window.wizardBlock = orig; }
    })();
    out.tests.wording_ok = out.tests.wording_ok && out.tests.wording_negative2 > 0;
  }

  /* ============================================================
     B（実在）保存に失敗したら保存領域を元へ戻すか — テストID save.rollback
     ============================================================ */
  {
    reset();
    /* まず正常に1件保存して、保存領域に「前の内容」を作る。 */
    const p0 = clone(PARAMS); p0.meta.planName = "前の内容";
    commitPlans([{name:"前の内容", params:p0}]);
    const before = localStorage.getItem(STORE.plans);
    const beforeCount = PLANS.length;

    /* `setItem` を1回だけ横取りして、別の内容を静かに書く。 */
    const real = Storage.prototype.setItem;
    let hit = 0;
    Storage.prototype.setItem = function(k, v){
      if(k === STORE.plans && hit++ === 0) return real.call(this, k, "[]");
      return real.call(this, k, v);
    };
    let ret;
    try{
      const p1 = clone(PARAMS); p1.meta.planName = "新しい内容";
      ret = commitPlans([{name:"前の内容", params:p0}, {name:"新しい内容", params:p1}]);
    }finally{ Storage.prototype.setItem = real; }

    const after = localStorage.getItem(STORE.plans);
    out.tests.rollback = {
      戻り値:ret, 画面のプラン数:{前:beforeCount, 後:PLANS.length},
      保存領域が元に戻った:(after === before),
      保存領域の中身:(after === before) ? "前の内容のまま" : String(after).slice(0, 40)};
    out.tests.rollback_ok = (ret === false) && (after === before)
      && (PLANS.length === beforeCount);
  }

  /* ============================================================
     C（マーカー不一致）新しい物件のキャンセル — テストID new_property.draft
     マーカー `clone(PARAMS)` ではなく `clone(P)` と書いているだけ。
     **挙動で示す。**
     ============================================================ */
  {
    reset();
    const snapP = JSON.stringify(PARAMS);
    const snapL = JSON.stringify(PLANS);
    let n = 0;
    window.prompt = () => (n++ === 0 ? "6000" : null);   // 価格は入れ、名前をキャンセル
    newPropertyPlan();
    out.tests.newproperty = {
      価格promptに答え名前をキャンセル:{
        PARAMSが不変:(snapP === JSON.stringify(PARAMS)),
        PLANSが不変:(snapL === JSON.stringify(PLANS))}};
    /* 価格promptをキャンセルした場合 */
    window.prompt = () => null;
    newPropertyPlan();
    out.tests.newproperty.価格promptをキャンセル = {
      PARAMSが不変:(snapP === JSON.stringify(PARAMS))};
    out.tests.newproperty_ok =
      out.tests.newproperty.価格promptに答え名前をキャンセル.PARAMSが不変
      && out.tests.newproperty.価格promptに答え名前をキャンセル.PLANSが不変
      && out.tests.newproperty.価格promptをキャンセル.PARAMSが不変;
  }

  /* ============================================================
     D（マーカー不一致）借入の追加・削除 — テストID loan_structure.autofit_semantics
     `addLoan`/`delLoan` の本文だけを見ると見えない。
     実装は `refitAfterLoanCountChange()` に切り出してある。**挙動で示す。**
     ============================================================ */
  {
    reset();
    const H = PARAMS.house;
    H.buy = true; H.autoFitLoans = true; H.price = 50000000; H.selfFund = 10000000;
    H.feeMode = "detail"; H.feeBrokerageAuto = true; H.feeLoanRate = 2.2;
    H.loans = [{name:"本人", amount:0, years:35, steps:[{y:1, rate:1}]}];
    recalc(); onMan("house.price", "5000");
    const g0 = Math.round(fundingGap(H));
    addLoan();   const g1 = Math.round(fundingGap(H)), n1 = H.loans.length;
    delLoan(1);  const g2 = Math.round(fundingGap(H)), n2 = H.loans.length;
    /* 「自動で合わせる」をOFFにしたら、本数を変えても触らないこと。 */
    H.autoFitLoans = false;
    const before = H.loans.map(l => l.amount).join(",");
    addLoan();
    const offKept = H.loans.slice(0, n2).map(l => l.amount).join(",") === before;
    out.tests.loan_count = {自動連動ON:{追加前:g0, 追加後:g1, 削除後:g2, 本数:[n1, n2]},
                            自動連動OFFで既存の借入が不変:offKept};
    out.tests.loan_count_ok = [g0, g1, g2].every(x => Math.abs(x) <= 1) && offKept;
  }

  /* ============================================================
     E（マーカー不一致）候補試算の副作用 — テストID result_notes.isolated
     期待マーカーは `snapshot`/`restore`。**`simulate()` が `notes` を返すので
     退避も復元も要らない。** 副作用が無いことを挙動で示す。
     ============================================================ */
  {
    reset();
    PARAMS.work.typeH = "employee"; PARAMS.income.hBase = 6000000;
    PARAMS.income.hTable = [{age:35, amount:6000000, rate:0}, {age:66, amount:0, rate:0}];
    recalc();
    const notesBefore = JSON.stringify(RESULT_NOTES);
    const paramsBefore = JSON.stringify(PARAMS);
    const simBefore = JSON.stringify({last:SIM.summary.last});
    /* 自営業・前年所得未確認の候補を検査させる（`badResultsIn` が `simulate` を呼ぶ）。 */
    const q = clone(PARAMS);
    q.work.typeH = "self"; q.meta.planName = "自営業";
    q.tax.kokuhoMunicipalityConfirmed = false;
    badResultsIn([{name:"自営業", params:q}]);
    out.tests.notes = {
      RESULT_NOTESが不変:(notesBefore === JSON.stringify(RESULT_NOTES)),
      PARAMSが不変:(paramsBefore === JSON.stringify(PARAMS)),
      SIMが不変:(simBefore === JSON.stringify({last:SIM.summary.last})),
      simulateはnotesを返す:!!(SIM && SIM.notes)};
    /* 保存の経路からも同じことを確かめる。 */
    const n2 = JSON.stringify(RESULT_NOTES);
    commitPlans([{name:"自営業", params:q}]);
    out.tests.notes.保存経路でも不変 = (n2 === JSON.stringify(RESULT_NOTES));
    out.tests.notes_ok = out.tests.notes.RESULT_NOTESが不変
      && out.tests.notes.PARAMSが不変 && out.tests.notes.SIMが不変
      && out.tests.notes.simulateはnotesを返す && out.tests.notes.保存経路でも不変;
  }

  /* ============================================================
     維持している合格（v28で通っていたもの）
     ============================================================ */
  {
    reset();
    out.tests.coverage = (typeof checkWizardCoverage === "function") ? checkWizardCoverage() : [];
    out.tests.coverage_ok = out.tests.coverage.length === 0;
  }
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
