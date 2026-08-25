"""成果物HTMLを最小のDOMスタブ上で実行し、全タブの描画とパラメータ操作が
エラーなく通ることを確認する。ブラウザを使わずに壊れを検出するためのもの。

使い方:  python 03_scripts/smoke_test.py
"""
import io
import json
import re
import sys
from pathlib import Path

import dukpy

ROOT = Path(__file__).resolve().parent.parent
def pick_html():
    """対象のHTMLを決める。第1引数で指定でき、なければ 02_output のいちばん新しいもの。"""
    if len(sys.argv) > 1:
        p = Path(sys.argv[1])
        return p if p.is_absolute() else (ROOT / p)
    return sorted((ROOT / "02_output").glob("*_v*.html"))[-1]


HTML = pick_html()
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

script = re.search(r"<script>(.*?)</script>", HTML.read_text(encoding="utf-8"), re.S).group(1)

DOM_STUB = r"""
var __log = [];
var __els = {};
function __mkEl(id){
  return {
    id:id, innerHTML:"", textContent:"", value:"", checked:false,
    dataset:{}, style:{},
    classList:{
      _s:{},
      add:function(c){ this._s[c]=1; },
      remove:function(c){ delete this._s[c]; },
      toggle:function(c,on){ if(on===undefined) on = !this._s[c];
                             if(on) this._s[c]=1; else delete this._s[c]; return on; },
      contains:function(c){ return !!this._s[c]; }
    },
    appendChild:function(){}, addEventListener:function(){},
    _attr:{},
    setAttribute:function(k,v){ this._attr[k]=String(v); },
    getAttribute:function(k){ return this._attr[k]===undefined?null:this._attr[k]; },
    removeAttribute:function(k){ delete this._attr[k]; },
    closest:function(){ return null; },
    querySelectorAll:function(){ var a=[]; a.forEach=function(f){}; return a; },
    scrollIntoView:function(){},
    click:function(){ __log.push("click: " + (this.download || this.id)); },
    href:"", download:""
  };
}
var __bodyAttrs = {};
var document = {
  body:{
    appendChild:function(){}, removeChild:function(){},
    setAttribute:function(k,v){ __bodyAttrs[k] = v; },
    getAttribute:function(k){ return __bodyAttrs[k] === undefined ? null : __bodyAttrs[k]; },
    removeAttribute:function(k){ delete __bodyAttrs[k]; }
  },
  getElementById:function(id){
    if(!__els[id]) __els[id] = __mkEl(id);
    return __els[id];
  },
  querySelectorAll:function(sel){
    // nav の button と .card を返す想定。最小限の空配列で十分。
    var a = [];
    a.forEach = function(f){ for(var i=0;i<this.length;i++) f(this[i], i); };
    return a;
  },
  createElement:function(t){ return __mkEl(t); }
};
function prompt(msg, def){ return "改名テスト"; }
function Blob(parts, opts){ this.parts = parts; }
var URL = {createObjectURL:function(){ return "blob:x"; }, revokeObjectURL:function(){}};
function setTimeout(fn, ms){ fn(); return 1; }
var __store = {};
var localStorage = {
  getItem:function(k){ return __store[k] === undefined ? null : __store[k]; },
  setItem:function(k,v){ __store[k] = String(v); },
  removeItem:function(k){ delete __store[k]; }
};
function alert(m){ __log.push("alert: " + String(m).slice(0,60)); }
function confirm(m){ return true; }
var window = {print:function(){ __log.push("window.print called"); },
              addEventListener:function(){}, alert:function(m){ __log.push("alert: "+m); }};
"""

CHECK = r"""
var __result = {tabs:{}, errors:[]};

function __try(label, fn){
  try { fn(); }
  catch(e){ __result.errors.push(label + " => " + (e && e.message ? e.message : String(e))); }
}
/* 版によって存在しない機能（個人版だけの一括作成など）は、あるときだけ確かめる。
   汎用版と個人版のどちらに対しても同じスクリプトを流せるようにするため。 */
function __has(name){ try { return typeof eval(name) === "function"; } catch(e){ return false; } }
function __tryIf(name, label, fn){
  if(!__has(name)){ __result.skipped = (__result.skipped||[]).concat(label); return; }
  __try(label, fn);
}
/* この版に実在するキーを使う（個人版の p1／koiwa などは汎用版にはない）。 */
function __pick(keys, want){          // 望みのキーがあればそれ、なければ代わりの1つめ
  for(var i=0;i<want.length;i++) if(keys.indexOf(want[i]) >= 0) return want[i];
  return keys[0];
}
var __P0 = PRESET_KEYS[0];                                  // 1つめの住宅プラン
var __P1 = PRESET_KEYS.length > 1 ? PRESET_KEYS[1] : PRESET_KEYS[0];
var __W0 = __pick(WSCENARIO_KEYS, ["keep"]);                // 収入を維持
var __W1 = WSCENARIO_KEYS.length > 1 ? WSCENARIO_KEYS[1] : WSCENARIO_KEYS[0];
var __HI_FLAT = __pick(HINCOME_KEYS, ["flat800", "flat"]);  // 昇給なし
var __HI_0    = HINCOME_KEYS[0];
var __RG0     = __pick(Object.keys(REGIONS), ["pdf", "manual"]);   // 既定の地域

// 全タブを描画する
var __tabIds = ["start","check","params","cf","graph","loan","edu","compare","stress","dict","about"];
for (var i = 0; i < __tabIds.length; i++) {
  (function(t){
    __try("setTab(" + t + ")", function(){
      TAB = t;
      render();
    });
  })(__tabIds[i]);
}

/* 描画したHTMLをぜんぶ集めておく。
   onclick などのイベント属性は、ブラウザが「押したとき」に解析するため、
   関数を直接呼ぶだけのこのテストでは壊れていても気づけない。
   集めたHTMLは Python 側で属性を取り出し、1つずつ構文検査する。 */
__result.renderedHtml = (function(){
  var parts = [];
  for (var id in __els) {
    var h = __els[id].innerHTML;
    if (h) parts.push(h);
  }
  return parts.join("\n");
})();

// パラメータ操作が通るか（代表的な入力ハンドラを叩く）
__try("onMan(house.price)",      function(){ onMan("house.price", "9000"); });
__try("onNum(econ.investRate)",  function(){ onNum("econ.investRate", "1.5"); });
__try("onChk(house.buy=false)",  function(){ onChk("house.buy", false); });
__try("render after buy=false",  function(){ TAB = "loan"; render(); TAB = "cf"; render(); });
__try("onChk(house.buy=true)",   function(){ onChk("house.buy", true); });
__try("addRow(income.hTable)",   function(){ addRow("income.hTable"); });
__try("delRow(income.hTable)",   function(){ delRow("income.hTable", PARAMS.income.hTable.length-1); });
__try("addItem(other.items)",    function(){ addItem("other.items"); });
__try("delItem(other.items)",    function(){ delItem("other.items", PARAMS.other.items.length-1); });
__try("addKid",                  function(){ addKid(); });
__try("delKid",                  function(){ delKid(PARAMS.family.children.length-1); });
__try("addLoan/delLoan",         function(){ addLoan(); delLoan(PARAMS.house.loans.length-1); });
__try("addStep/delStep",         function(){ addStep(0); delStep(0, PARAMS.house.loans[0].steps.length-1); });
__try("fitLoans",                function(){ fitLoans(); });
__try("onStage(univ.years=4)",   function(){ onStage("univ", "years", "4"); });
__try("onPlan(univ=false)",      function(){ onPlan(0, "univ", false); });
__try("savePlan",                function(){ document.getElementById("planName").value = "テストプラン";
                                             savePlan(); });
__try("sweepPrice",              function(){ sweepPrice(); });
__try("render compare",          function(){ TAB = "compare"; render(); });
__try("render stress",           function(){ TAB = "stress"; render(); });
__try("loadPlan",                function(){ loadPlan("テストプラン"); });
__try("resetParams",             function(){ resetParams(); });
__try("clearPlans",              function(){ clearPlans(); });

// プリセットの切替（①〜⑤）と一括比較
__try("presets: 全キーを適用", function(){
  __result.presets = {};
  for (var pi = 0; pi < PRESET_KEYS.length; pi++){
    var k = PRESET_KEYS[pi];
    applyPreset(k);
    var last = SIM.rows[SIM.rows.length-1];
    var borrow = PARAMS.house.buy
      ? PARAMS.house.loans.reduce(function(s,l){ return s + l.amount; }, 0) : 0;
    __result.presets[k] = {
      label: PRESETS[k].label,
      price: PARAMS.house.price,
      borrow: borrow,
      firstPay: SIM.loanTotal.length ? Math.round(SIM.loanTotal[0].total) : 0,
      totalPay: Math.round(SIM.loanTotal.reduce(function(s,r){ return s + r.total; }, 0)),
      finalAsset: Math.round(last.assetTotal),
      deplete: SIM.depleteAge
    };
    // 各プリセットで全タブが描画できるか
    for (var ti = 0; ti < __tabIds.length; ti++){ TAB = __tabIds[ti]; render(); }
  }
});
__try("loadAllPresets",  function(){ loadAllPresets(); });
__try("render compare after loadAll", function(){ TAB = "compare"; render(); });

// 配偶者の収入シナリオ A〜E
__try("wscenarios: 全キーを適用", function(){
  __result.wsc = {};
  for (var wi = 0; wi < WSCENARIO_KEYS.length; wi++){
    var wk = WSCENARIO_KEYS[wi];
    applyPreset(__P0);
    applyWScenario(wk);
    var mm = SIM.summary;
    __result.wsc[wk] = {
      label: WSCENARIOS[wk].label,
      atRetire: Math.round(mm.atRetire),
      last: Math.round(mm.last),
      min: Math.round(mm.minAsset.assetTotal),
      minAge: mm.minAsset.ageH,
      deplete: SIM.depleteAge
    };
    for (var ti2 = 0; ti2 < __tabIds.length; ti2++){ TAB = __tabIds[ti2]; render(); }
  }
});
__try("loadAllWScenarios", function(){ loadAllWScenarios(); });
__try("render compare after wsc", function(){ TAB = "compare"; render(); });

// 不動産の売却・住み替え（配偶者シナリオはAに戻して確認する）
__try("estate: 売却あり", function(){
  applyPreset(__P0);
  applyWScenario(__W0);
  onChk("estate.sell", true);
  onNum("estate.sellAgeH", "70");
  onMan("estate.nextPrice", "2000");
  for (var ti3 = 0; ti3 < __tabIds.length; ti3++){ TAB = __tabIds[ti3]; render(); }
  var sr = SIM.rows.filter(function(r){ return r.isSellYear; })[0];
  __result.sell = sr ? {
    year: sr.year, age: sr.ageH,
    proceeds: Math.round(sr.sellProceeds),
    tax: Math.round(sr.sellTax),
    estateAfter: Math.round(sr.estateValue),
    acquisition: Math.round(sr.acquisition)
  } : null;
  __result.sellSummary = {
    atRetire: Math.round(SIM.summary.atRetire),
    last: Math.round(SIM.summary.last),
    lastNW: Math.round(SIM.summary.lastNW)
  };
});
__try("estate: 売却して賃貸へ", function(){
  onMan("estate.nextPrice", "0");
  onMan("estate.nextRent", "120");
  recalc();
  TAB = "cf"; render();
});
__try("estate: 売却なしに戻す", function(){
  onChk("estate.sell", false);
  TAB = "params"; render();
});

// 地域シナリオ（0〜2歳の保育料）
__try("regions: 全キーを適用", function(){
  applyPreset(__P0); applyWScenario(__W0);
  __result.regions = {};
  for (var ri = 0; ri < REGION_KEYS.length; ri++){
    var rk = REGION_KEYS[ri];
    applyRegion(rk);
    __result.regions[rk] = {
      label: REGIONS[rk].label,
      n1: PARAMS.edu.stages.nursery.first,
      n2: PARAMS.edu.nursery2nd,
      lifeEdu: Math.round(SIM.summary.lifeEdu),
      atRetire: Math.round(SIM.summary.atRetire),
      last: Math.round(SIM.summary.last)
    };
    for (var ti4 = 0; ti4 < __tabIds.length; ti4++){ TAB = __tabIds[ti4]; render(); }
  }
  applyRegion(__RG0);
});

// 物件種別（マンション／戸建て）
__try("estateType: 全キーを適用", function(){
  __result.types = {};
  for (var ei = 0; ei < ESTATE_TYPE_KEYS.length; ei++){
    var ek = ESTATE_TYPE_KEYS[ei];
    applyEstateType(ek);
    __result.types[ek] = {
      label: ESTATE_TYPES[ek].label,
      maint: maintTotal(PARAMS.house, 0),
      maintPreset: (function(){ var p = clone(PARAMS); applyMaintPreset(p, ek);
                                return maintTotal(p.house, 0); })(),
      bigRepair: PARAMS.house.bigRepair,
      cycle: PARAMS.house.bigRepairCycle,
      landRatio: PARAMS.estate.landRatio,
      life: PARAMS.estate.buildingLife,
      v10: Math.round(estateValueAt(PARAMS.house.price, 10, PARAMS.estate)),
      v20: Math.round(estateValueAt(PARAMS.house.price, 20, PARAMS.estate)),
      v30: Math.round(estateValueAt(PARAMS.house.price, 30, PARAMS.estate)),
      last: Math.round(SIM.summary.last),
      lastNW: Math.round(SIM.summary.lastNW)
    };
    for (var ti5 = 0; ti5 < __tabIds.length; ti5++){ TAB = __tabIds[ti5]; render(); }
  }
  applyEstateType("mansion");
});

// 月々の負担と老後資金の指標
__try("burden / oldAge", function(){
  applyPreset(__P0); applyWScenario(__W0); applyRegion(__RG0);
  __result.burden = {
    first: Math.round(SIM.summary.burden.firstRate*10)/10,
    worst: Math.round(SIM.summary.burden.worstRate*10)/10,
    worstYear: SIM.summary.burden.worst ? SIM.summary.burden.worst.year : null,
    over30: SIM.summary.burden.over30,
    over35: SIM.summary.burden.over35
  };
  __result.oldAge = {
    asset: Math.round(SIM.summary.oldAge.asset),
    avgGap: Math.round(SIM.summary.oldAge.avgGap),
    lastsUntil: SIM.summary.oldAge.lastsUntil,
    needFor100: Math.round(SIM.summary.oldAge.needFor100),
    shortage: Math.round(SIM.summary.oldAge.shortage)
  };
});

// テーマ切替
__try("theme toggle", function(){
  toggleTheme(); __result.theme1 = currentTheme();
  toggleTheme(); __result.theme2 = currentTheme();
});

// 名目／実質（現在価値）の切替
__try("view real toggle", function(){
  applyPreset(__P0); applyWScenario(__W0); applyRegion(__RG0);
  var nominal = SIM.summary.last;
  toggleView();
  __result.view = {real:VIEW_REAL, nominalLast:Math.round(nominal),
                   factorAt40:realFactor(40), factorAtEnd:realFactor(SIM.rows.length-1)};
  toggleView();
  __result.view.backToNominal = !VIEW_REAL;
});

// 安心の条件（目標）の判定
__try("goal judge", function(){
  applyPreset(__P0); applyWScenario(__W0); applyRegion("tokyo");
  var g = SIM.summary.goal;
  __result.goal = {
    passed:g.passed, total:g.total, allOk:g.allOk,
    surplus:{v:Math.round(g.surplus.valueReal), t:g.surplus.target, ok:g.surplus.ok},
    burden:{v:Math.round(g.burden.value*10)/10, t:g.burden.target, ok:g.burden.ok},
    cash:{v:Math.round(g.cash.months*10)/10, t:g.cash.target, ok:g.cash.ok},
    retire:{v:Math.round(g.retire.value), t:g.retire.target, ok:g.retire.ok},
    floor:{v:Math.round(g.floor.value), t:g.floor.target, ok:g.floor.ok},
    lasts:{ok:g.lasts.ok}
  };
});
__try("goal params change", function(){
  onNum("goal.burdenLimit", "25");
  onNum("goal.cashMonths", "12");
  onNum("goal.retireTargetReal", "5000");
  TAB = "check"; render();
  __result.goalAfter = {passed:SIM.summary.goal.passed, total:SIM.summary.goal.total};
  onNum("goal.burdenLimit", "30");
  onNum("goal.cashMonths", "6");
  onNum("goal.retireTargetReal", "3000");
});

// 配偶者年収の損益分岐点
__try("break even", function(){
  applyPreset(__P0); applyWScenario(__W0); applyRegion("tokyo");
  var noDep = wIncomeBreakEven(PARAMS, function(s){ return !s.depleteAge; });
  var allOk = wIncomeBreakEven(PARAMS, function(s){ return s.summary.goal.allOk; });
  var ret   = wIncomeBreakEven(PARAMS, function(s){ return s.summary.goal.retire.ok; });
  __result.breakEven = {
    noDeplete: noDep === null ? -1 : Math.round(noDep),
    allGoals:  allOk === null ? -1 : Math.round(allOk),
    retireGoal:ret === null ? -1 : Math.round(ret)
  };
});

// 固定資産税の3方式
__try("propertyTax 3 methods", function(){
  applyPreset(__P0); applyWScenario(__W0); applyRegion(__RG0);
  __result.ptax = {};
  ["simple","detail","manual"].forEach(function(mth){
    onTxt("house.holdMethod", mth);
    TAB = "params"; render();
    __result.ptax[mth] = [0,5,6,20].map(function(n){
      return Math.round(propertyTax(PARAMS.house, PARAMS.estate, n)); });
  });
  onTxt("house.holdMethod", "simple");
});

// 年金の自動計算
__try("pension auto", function(){
  __result.pension = {};
  [false, true].forEach(function(auto){
    onChk("retire.pensionAuto", auto);
    __result.pension[auto ? "auto" : "manual"] = {
      h: Math.round(SIM.summary.pension.amtH),
      w: Math.round(SIM.summary.pension.amtW),
      atRetire: Math.round(SIM.summary.atRetire),
      last: Math.round(SIM.summary.last)
    };
    TAB = "params"; render();
  });
  onChk("retire.pensionAuto", false);
});

// 相続税
__try("inheritance tax", function(){
  var ih = SIM.summary.inherit;
  __result.inherit = {
    atAge: ih.atAge, total: Math.round(ih.totalEstate1),
    first: Math.round(ih.first.net), second: Math.round(ih.second.net),
    grand: Math.round(ih.grandTotal), basic: ih.first.basic,
    // 国税庁の速算例との照合
    check2oku: Math.round(inheritanceTax(200000000, 2, true, 0.5).total),
    check2okuKids: Math.round(inheritanceTax(200000000, 2, false, 0).net),
    checkBasic: Math.round(inheritanceTax(48000000, 2, true, 0.5).net)
  };
  TAB = "check"; render();
});

// 資金の整合性チェック
__try("fund consistency", function(){
  var H = PARAMS.house;
  onMan("house.selfFund", "500");     // わざと不一致にする
  TAB = "params"; render();
  __result.fundGap = Math.round(H.price + H.fees - H.selfFund - (H.gift||0)
                     - H.loans.reduce(function(s,l){ return s+l.amount; }, 0));
  fitLoans();
  __result.fundGapFixed = Math.round(H.price + H.fees - H.selfFund - (H.gift||0)
                          - H.loans.reduce(function(s,l){ return s+l.amount; }, 0));
  applyPreset(__P0);
});

// 辞書（知っておきたいこと）
__try("dict render / search / filter", function(){
  TAB = "dict"; render();
  __result.dict = {count:DICT.length, cats:DICT_CATS.length};
  __els["dictQ"].value = "保育料";   // 「保育料」で検索
  renderDict();
  __result.dict.searchLen = (__els["dictBody"].innerHTML || "").length;
  __els["dictQ"].value = "ありえない語句";
  renderDict();
  __result.dict.noHit = (__els["dictBody"].innerHTML || "").indexOf("見つかり") >= 0;
  __els["dictQ"].value = "";
  setDictCat(DICT_CATS[0]);
  __result.dict.filtered = (__els["dictBody"].innerHTML || "").length;
  setDictCat(DICT_CATS[0]);
  renderDict();
});

// 住宅ローン控除の住宅の種類
__try("ld housing types", function(){
  applyPreset(__P0);
  __result.ldTypes = {};
  for (var li = 0; li < LD_TYPE_KEYS.length; li++){
    var lk = LD_TYPE_KEYS[li];
    applyLdType(lk);
    TAB = "params"; render();
    __result.ldTypes[lk] = {label:LD_HOUSING_TYPES[lk].label,
      limit:PARAMS.house.ldLimit, years:PARAMS.house.ldYears,
      total:Math.round(SIM.summary.loanDeductionTotal)};
  }
  // 子育て世帯の上乗せ
  applyLdType("chouki");
  onChk("house.ldKidsBonus", true);
  __result.ldBonus = {limit:PARAMS.house.ldLimit,
                      total:Math.round(SIM.summary.loanDeductionTotal)};
  onChk("house.ldKidsBonus", false);
  applyPreset(__P0);
});

// 入力の整合性チェックと借入額の自動連動
__try("validate + autoFit", function(){
  applyPreset(__P0); applyWScenario(__W0); applyRegion(__RG0);
  __result.validate = {
    clean: validateParams(PARAMS).filter(function(i){ return i.level==="bad"; }).length,
    warns: validateParams(PARAMS).filter(function(i){ return i.level==="warn"; }).length};
  // 頭金を変えたら借入額が自動で追随するか
  var before = PARAMS.house.loans.reduce(function(s,l){ return s+l.amount; }, 0);
  onMan("house.selfFund", "2000");
  var after = PARAMS.house.loans.reduce(function(s,l){ return s+l.amount; }, 0);
  __result.autoFit = {before:before, after:after,
    gap: PARAMS.house.price + PARAMS.house.fees - PARAMS.house.selfFund
         - (PARAMS.house.gift||0) - after,
    issues: validateParams(PARAMS).length};
  // 自動連動を切ると差額が残るか
  onChk("house.autoFitLoans", false);
  onMan("house.selfFund", "500");
  __result.noAutoFit = {
    gap: PARAMS.house.price + PARAMS.house.fees - PARAMS.house.selfFund
         - (PARAMS.house.gift||0)
         - PARAMS.house.loans.reduce(function(s,l){ return s+l.amount; }, 0),
    issues: validateParams(PARAMS).filter(function(i){ return i.level==="bad"; }).length};
  TAB = "params"; render();
  applyPreset(__P0);
});

// 開いた直後の案内と「検討中の条件で見る」
__tryIf("applyRealPatternDefault", "startGuide + applyRealPatternDefault", function(){
  applyPreset(__P0); applyWScenario(__W0); applyRegion(__RG0);
  TAB = "check"; render();
  __result.guide = {shownOnPdf: (__els["startGuide"].innerHTML || "").length > 0};
  applyRealPatternDefault();
  __result.guide.afterClick = {
    preset: PARAMS.meta.preset, w: PARAMS.meta.wScenario, region: PARAMS.meta.region,
    price: PARAMS.house.price, dep: SIM.depleteAge,
    last: Math.round(SIM.summary.last),
    hidden: (__els["startGuide"].innerHTML || "").length === 0
  };
  applyPreset(__P0); applyWScenario(__W0); applyRegion(__RG0);
});

// はじめにタブと診断コメント
__try("start tab + diagnose", function(){
  applyPreset(__P0); applyWScenario(__W0); applyRegion(__RG0);
  TAB = "start"; render();
  __result.startTab = {len: (__els["s-start"].innerHTML || "").length};
  TAB = "check"; render();
  var d1 = diagnose();
  __result.diag = {ok: d1.length, levels: d1.map(function(x){ return x.level; }).join(",")};
  // 厳しい条件でも診断が出るか
  applyPreset(__P1); applyWScenario(__W1); applyHIncome(__HI_FLAT);
  var d2 = diagnose();
  __result.diagBad = {n: d2.length, levels: d2.map(function(x){ return x.level; }).join(","),
                      titles: d2.map(function(x){ return x.title; })};
  TAB = "check"; render();
  __result.diagBad.rendered = (__els["diagnose"].innerHTML || "").length;
  applyPreset(__P0); applyWScenario(__W0); applyHIncome(__HI_0);
});

// ページヘルプと初心者表示
__try("tab help + easy mode", function(){
  __result.tabHelp = {};
  for (var hi = 0; hi < __tabIds.length; hi++){
    TAB = __tabIds[hi]; render();
    var box = __els["tabHelp-" + __tabIds[hi]];
    __result.tabHelp[__tabIds[hi]] = box ? (box.innerHTML || "").length : 0;
  }
  var __easy0 = EASY_MODE;
  toggleEasy();
  __result.easy = {on:EASY_MODE, tabs:BASIC_TABS.length,
                   nav:(__els["nav"].innerHTML || "").length,
                   toggled:(EASY_MODE !== __easy0)};
  toggleEasy();
  __result.easy.off = (EASY_MODE === __easy0);   // 2回で元に戻る
});

// 万一のときの保障
__try("survivor", function(){
  applyPreset(__P1); applyWScenario(__W1); applyRegion("tokyo");
  calcSurvivor();
  var d = HEAVY.survivor;
  __result.survivor = {
    h:{deathAge:d.h.deathAge, pension:Math.round(d.h.pension1),
       dep:d.h.noIns.dep, need:d.h.need===null?-1:Math.round(d.h.need)},
    w:d.w?{deathAge:d.w.deathAge, pension:Math.round(d.w.pension1),
       dep:d.w.noIns.dep, need:d.w.need===null?-1:Math.round(d.w.need)}:null,
    rendered:(__els["q5"].innerHTML||"").length};
  applyPreset(__P0); applyWScenario(__W0); applyRegion(__RG0);
});

// 印刷レポートの生成
__try("buildReport", function(){ buildReport(); });
__try("printReport", function(){ printReport(); });

// プランの管理操作
__try("dupPlan/renamePlan", function(){
  if (PLANS.length){
    dupPlan(PLANS[0].name);
    renamePlan(PLANS[PLANS.length-1].name);
  }
});
__try("setPlanMemo", function(){
  if (PLANS.length){
    setPlanMemo(0, "テスト用のメモ：妻が時短勤務を続ける前提");
    __result.memo = PLANS[0].params.meta.memo;
  }
});
__try("onTxt(meta.memo)", function(){
  onTxt("meta.memo", "編集中プランのメモ");
  TAB = "params"; render();
  buildReport();
  __result.memoInReport = document.getElementById("report").innerHTML.indexOf("編集中プランのメモ") > 0;
});
__try("exportPlans", function(){ exportPlans(); });
__result.planCount = PLANS.length;
// プリセット適用時にメモが自動で入るか
__try("preset memo", function(){
  applyPreset(__P1);
  applyWScenario("half");
  __result.autoMemo = PARAMS.meta.memo;
});

// 固定資産税の自動計算の切替
__try("holdCostAuto off/on", function(){
  applyPreset(__P0);
  onChk("house.holdCostAuto", false);
  TAB = "params"; render();
  onChk("house.holdCostAuto", true);
  render();
});

// 配偶者なし・子なしでも壊れないか
__try("no spouse / no children", function(){
  PARAMS.family.hasSpouse = false;
  PARAMS.family.children = [];
  recalc();
  for (var k = 0; k < __tabIds.length; k++){ TAB = __tabIds[k]; render(); }
});

// 極端な値でも壊れないか
__try("extreme: 金利10% 物件2億", function(){
  PARAMS = defaults();
  PARAMS.house.price = 200000000;
  fitLoans();
  PARAMS.house.loans.forEach(function(l){ l.steps.forEach(function(s){ s.rate = 10; }); });
  recalc();
  for (var k = 0; k < __tabIds.length; k++){ TAB = __tabIds[k]; render(); }
  __result.extremeDeplete = SIM.depleteAge;
});

/* 保険料の年齢別テーブル
   ・既定（2値方式）と年齢別で、生涯の保険料合計がどう変わるか
   ・目安テーブルの中身が年齢の昇順になっているか
   ・物件を変えたときにテーブルが追従するか
   ・不整合（開始年齢が現在より後）を検出できるか  */
__try("保険料の年齢別テーブル", function(){
  PARAMS = defaults(__P1, __W1);
  recalc();
  var sumSimple = 0, i;
  for (i = 0; i < SIM.rows.length; i++) sumSimple += SIM.rows[i].insurance;
  var o = {mode0: PARAMS.living.insMode, simpleTotal: sumSimple,
           simpleAt40: null, simpleAt56: null};
  for (i = 0; i < SIM.rows.length; i++){
    if (SIM.rows[i].ageH === 40) o.simpleAt40 = SIM.rows[i].insurance;
    if (SIM.rows[i].ageH === 56) o.simpleAt56 = SIM.rows[i].insurance;
  }
  setInsMode("table");
  o.mode1 = PARAMS.living.insMode;
  o.table = PARAMS.living.insTable.map(function(r){
    return {age: r.age, man: Math.round(r.amount / 10000 * 10) / 10};
  });
  o.ascending = true;
  for (i = 1; i < PARAMS.living.insTable.length; i++)
    if (PARAMS.living.insTable[i].age <= PARAMS.living.insTable[i-1].age) o.ascending = false;
  var sumTable = 0;
  for (i = 0; i < SIM.rows.length; i++) sumTable += SIM.rows[i].insurance;
  o.tableTotal = sumTable;
  for (i = 0; i < SIM.rows.length; i++){
    if (SIM.rows[i].ageH === 40) o.tableAt40 = SIM.rows[i].insurance;
    if (SIM.rows[i].ageH === 56) o.tableAt56 = SIM.rows[i].insurance;
  }
  o.deplSimpleVsTable = SIM.depleteAge;
  // 入力欄が描画できるか（テーブル方式のとき）
  TAB = "params"; render();
  o.editorLen = document.getElementById("paramCards").innerHTML.length;
  // 物件を変えるとテーブルが追従するか（平井は火災保険が厚い）
  var before = PARAMS.living.insTable[1] ? PARAMS.living.insTable[1].amount : 0;
  PARAMS = defaults(__P1, __W1);
  PARAMS.living.insMode = "table";
  PARAMS = defaults(__P1, __W1);   // insMode は defaults で作り直されるため下で明示
  PARAMS.living.insMode = "table"; insGuideTable(PARAMS); recalc();
  o.followBuyAmount = PARAMS.living.insTable[1] ? PARAMS.living.insTable[1].amount : 0;
  o.followBefore = before;
  // 不整合の検出（現在年齢より後から始まるテーブル）
  PARAMS.living.insTable = [{age:50, amount:120000, rate:0}];
  var v = validateParams(PARAMS);
  o.badDetected = 0;
  for (i = 0; i < v.length; i++)
    if (v[i].level === "bad" && v[i].msg.indexOf("保険料") >= 0) o.badDetected++;
  __result.ins = o;
});

/* 赤字の評価が「一時的な赤字」と「借入が必要」を区別できているか。
   単年の赤字だけで危険と判定していないことを確かめる。 */
__try("赤字と借入の区別", function(){
  __result.judge = [];
  [[__P0,__W0],[__P0,__W1],[__P1,__W0],[__P1,__W1]]
  .forEach(function(pair){
    PARAMS = defaults(pair[0], pair[1]); recalc();
    var D = SIM.summary.deficit, g = SIM.summary.goal;
    var items = diagnose();
    var lv = {bad:0, warn:0, ok:0}, i;
    for (i = 0; i < items.length; i++) lv[items[i].level] = (lv[items[i].level]||0) + 1;
    // 赤字に関する診断のレベルと見出しを取り出す
    var negTitle = "", negLevel = "";
    for (i = 0; i < items.length; i++)
      if (items[i].title.indexOf("赤字") >= 0 && items[i].level !== "ok"){
        negTitle = items[i].title; negLevel = items[i].level; break;
      }
    TAB = "concerns"; render();
    __result.judge.push({
      plan: pair[0] + "/" + pair[1],
      depl: SIM.depleteAge,
      negYears: D.negYears, negRunMax: D.negRunMax, borrowYears: D.borrowYears,
      coveredNeg: D.coveredNeg,
      persistent: D.persistent, negKind: D.negKind,
      runs: D.negRuns.map(function(r){
        return {age: r.ageFrom + "-" + r.ageTo, years: r.years,
                avg: Math.round(r.sum / r.years / 12 / 10000 * 10) / 10};
      }),
      avgNeg: Math.round(D.avgNegMonthly / 10000 * 10) / 10,
      avgWork: Math.round(D.avgWorkMonthly / 10000 * 10) / 10,
      workYears: D.workYears, posYears: D.posYears,
      decisiveOk: g.decisive.allOk, comfortPassed: g.comfort.passed,
      goalPassed: g.passed,
      bad: lv.bad, warn: lv.warn, okItems: lv.ok, floorOk: !!g.floor.ok,
      negTitle: negTitle, negLevel: negLevel,
      q0len: document.getElementById("q0").innerHTML.length
    });
  });
});

/* 古い版で保存されたプラン・壊れたプランが localStorage に残っていても
   プラン比較のタブが描画できるか。
   ここが落ちると表もグラフも一切出ず、利用者からは
   「プラン比較がうまくいかない」としか見えないため、必ず検査する。 */
__try("古い/壊れた保存プランからの復旧", function(){
  __result.migrate = [];
  function old(dropped){
    var p = clone(defaults(__P1, __W1));
    for (var i = 0; i < dropped.length; i++){
      var seg = dropped[i].split("."), o = p, j;
      for (j = 0; j < seg.length - 1; j++){ if(!o) break; o = o[seg[j]]; }
      if (o) delete o[seg[seg.length-1]];
    }
    return JSON.stringify([{name:"古いプラン", params:p}]);
  }
  var cases = [
    ["壊れたJSON", "{これはJSONではない"],
    ["paramsがnull", '[{"name":"x","params":null}]'],
    ["loansが空配列", '[{"name":"x","params":{"house":{"buy":true,"loans":[]}}}]'],
    ["loansの中身が壊れている", '[{"name":"x","params":{"house":{"buy":true,"loans":[{"amount":1}]}}}]'],
    ["hTableが空", '[{"name":"x","params":{"income":{"hTable":[]}}}]'],
    ["children文字列", '[{"name":"x","params":{"family":{"children":"abc"}}}]'],
    ["savingなし（追補2より前）", old(["saving"])],
    ["goalなし（v5より前）", old(["goal"])],
    ["estateなし（v3より前）", old(["estate"])],
    ["careなし", old(["care"])],
    ["otherなし", old(["other"])],
    ["inheritなし", old(["inherit"])],
    ["insTableなし（追補16より前）", old(["living.insMode","living.insTable"])],
    ["まとめて欠落", old(["saving","goal","estate","care","other","inherit","survivor"])]
  ];
  for (var ci = 0; ci < cases.length; ci++){
    var name = cases[ci][0], rec = {name:name};
    try {
      __store["lpcf_plans"] = cases[ci][1];
      loadPlans();
      PARAMS = defaults(__P1, __W1); recalc();
      TAB = "compare"; render();
      var pm = document.getElementById("planManage").innerHTML;
      rec.plans = PLANS.length;
      rec.manage = pm.length;
      rec.key = document.getElementById("cmpKeyTable").innerHTML.length;
      rec.chart = document.getElementById("cmpChart").innerHTML.length;
      rec.notice = pm.indexOf("読み込めませんでした") >= 0 ? "読込エラー"
                 : (pm.indexOf("計算できな") >= 0 ? "計算できない旨" : "");
      rec.ok = true;
    } catch(e){ rec.ok = false; rec.err = e && e.message ? e.message : String(e); }
    __result.migrate.push(rec);
  }
  __store["lpcf_plans"] = "[]"; loadPlans();
});

/* UI の3機能（凡例で線を隠す／1つずつ進む表示／スライダー）が動くか */
__try("UIの3機能", function(){
  var o = {};
  PARAMS = defaults(__P0, __W0); PARAMS.saving.nisaOn = true; recalc();

  // (1) 凡例を押して線を隠せるか（比較用のプランはこの版にある方法で作る）
  PLANS = [];
  if(__has("loadRealPatterns")) loadRealPatterns(); else loadAllWScenarios();
  TAB = "compare"; render();
  var before = document.getElementById("cmpChart").innerHTML.length;
  /* いま編集中のプランと同名の保存プランは、凡例では「〜（編集中）」という
     別名で1本だけ描かれる。実在する系列名を選ばないと押しても何も起きない。 */
  var __target = null;
  for (var __i = 0; __i < PLANS.length; __i++)
    if (PLANS[__i].name !== PARAMS.meta.planName) { __target = PLANS[__i].name; break; }
  if (__target === null) __target = PARAMS.meta.planName + "（編集中）";
  o.legendTarget = __target;
  toggleSeries(__target); TAB = "compare"; render();
  var html = document.getElementById("cmpChart").innerHTML;
  o.legend = {before: before, after: html.length, hidden: HIDDEN_SERIES.size,
              struck: html.indexOf("lgtoggle off") >= 0,
              allBtn: html.indexOf("lgall") >= 0};
  showAllSeries();
  o.legend.restored = HIDDEN_SERIES.size;

  // (2) 1つずつ進む表示
  TAB = "check"; render();
  o.step = {count: STEPS.length, at: STEP, all: STEP_ALL,
            navLen: document.getElementById("stepNav").innerHTML.length,
            footLen: document.getElementById("stepFoot").innerHTML.length};
  setStep(3); o.step.moved = STEP;
  /* ステップ数は版によって違う（汎用版は選んだ心配ごとの数で変わる）ので、
     「4／7」のように決め打ちにせず、いまの STEPS.length から作る。 */
  o.step.showsPos = document.getElementById("stepNav").innerHTML
                      .indexOf((STEP + 1) + "／" + STEPS.length) >= 0;
  toggleStepAll(); o.step.allOn = STEP_ALL;
  o.step.footWhenAll = document.getElementById("stepFoot").innerHTML.length;
  toggleStepAll(); setStep(0);

  // (3) スライダー
  TAB = "params"; render();
  // 設定は パラメータ／住宅とローン／教育費／資産形成 に分かれている
  var ph = ["paramCards","loanCards","assetCards","eduParamCards"]
    .map(function(id){ var e=document.getElementById(id); return e?e.innerHTML:""; }).join("");
  TAB = "check"; STEP_ALL = true; render();
  var qh = document.getElementById("q0").innerHTML;
  STEP_ALL = false;
  o.slider = {defined: Object.keys(SLIDERS).length,
              inSettings: (ph.match(/type="range"/g) || []).length,
              inGoals: (qh.match(/type="range"/g) || []).length};
  var p0 = PARAMS.house.price; onMan("house.price", "9000");
  o.slider.moved = {from: p0, to: PARAMS.house.price};
  __result.ui = o;
});

/* 制度どおりの計算になっているかを、独立した手計算と突き合わせる。
   PDF照合は「FPの数字と合うか」なので、制度そのものの検算は別に持つ。 */
__try("制度の検算", function(){
  var bad=[];
  // (1) 退職所得課税：控除＝800万＋70万×(勤続−20)、超過分の1/2に課税
  function taxAt(lump, years){
    // 積立を0に戻す（既定は確定拠出年金から受け取る設定なので、一時金が使われない）
    var p=applyPdfSavings(defaults(__P0,__W0));
    p.retire.lumpH=lump; p.retire.workYearsH=years; p.retire.lumpW=0;
    var s=simulate(p), i=-1;
    s.rows.forEach(function(r,k){ if(r.ageH===p.retire.retireAgeH) i=k; });
    return s.rows[i].taxTotal;
  }
  function handRetire(L, y){
    var ded = y>20 ? 8000000+700000*(y-20) : 400000*y;
    var ti = Math.floor(Math.max(0, L-ded)/2/1000)*1000, it;
    if(ti<=1950000) it=ti*0.05;
    else if(ti<=3300000) it=ti*0.10-97500;
    else if(ti<=6950000) it=ti*0.20-427500;
    else if(ti<=9000000) it=ti*0.23-636000;
    else if(ti<=18000000) it=ti*0.33-1536000;
    else if(ti<=40000000) it=ti*0.40-2796000;
    else it=ti*0.45-4796000;
    return it*1.021 + ti*0.10;
  }
  [[15000000,43],[30000000,43],[50000000,43],[30000000,10],[100000000,43]].forEach(function(c){
    var d=taxAt(c[0],c[1])-taxAt(0,c[1]), h=handRetire(c[0],c[1]);
    if(Math.abs(d-h)>30000)
      bad.push("退職所得 "+(c[0]/10000)+"万/"+c[1]+"年: 計算"+Math.round(d)+" 手計算"+Math.round(h));
  });
  // (2) NISAの生涯投資枠：既存残高＋これから積む額が1,800万を超えないこと
  [0, 4000000, 15000000].forEach(function(b){
    var p=applyPdfSavings(defaults(__P0,__W0));
    p.saving.nisaBal0=b; p.saving.nisaMonthlyH=100000; p.saving.nisaMonthlyW=50000;
    var s=simulate(p), total=b+s.summary.saving.nisaInTotal;
    if(total > p.saving.nisaLimitTotal+1)
      bad.push("NISA枠 残高"+(b/10000)+"万: 元本合計"+Math.round(total/10000)+"万が上限を超えた");
  });
  // (3) 借入残高：資産が尽きたあと、最終年の資産と借入残高の符号が整合すること
  PRESET_KEYS.forEach(function(h){
    var s=simulate(defaults(h,__W1)), last=s.rows[s.rows.length-1];
    if(last.debt>0 && Math.abs(last.assetTotal + last.debt) > 1)
      bad.push(h+": 借入残高と最終資産が整合しない");
  });
  __result.rule={n:bad.length, sample:bad.slice(0,6)};
});

/* 数字が内部で矛盾していないかを全数で確かめる。
   「これっておかしくない？」を防ぐための検算。
   合計と内訳、収支の式、資産の増減の向きを、全プリセット×全シナリオ×全年で見る。 */
__try("恒等式チェック", function(){
  var bad=[];
  for (var pi=0; pi<PRESET_KEYS.length; pi++){
    for (var wi=0; wi<WSCENARIO_KEYS.length; wi++){
      var pk=PRESET_KEYS[pi], wk=WSCENARIO_KEYS[wi];
      var s=simulate(defaults(pk,wk)), tag=pk+"/"+wk;
      var last=s.rows[s.rows.length-1], prev=null;
      for (var ri=0; ri<s.rows.length; ri++){
        var r=s.rows[ri];
        if (Math.abs((r.deposit+r.invest+r.nisaBal+r.stockBal-r.debt)-r.assetTotal)>1)
          bad.push(tag+" "+r.year+": 金融資産の内訳が合わない");
        if (Math.abs((r.assetTotal+r.dcBalance+r.estateValue-r.loanBalance)-r.netWorth)>1)
          bad.push(tag+" "+r.year+": 純資産の内訳が合わない");
        if (Math.abs((r.incomeTotal-r.expenseTotal-r.savingTotal)-r.net)>1)
          bad.push(tag+" "+r.year+": 年間収支が合わない");
        if (r.debt>1 && r.deposit>1)
          bad.push(tag+" "+r.year+": 預金があるのに借入が残っている");
        if (prev!==null && r.loanBalance>prev+1 && !r.isSellYear && r.acquisition===0)
          bad.push(tag+" "+r.year+": ローン残高が増えている");
        prev=r.loanBalance;
      }
      if (last.assetTotal<0 && !s.depleteAge) bad.push(tag+": 資産がマイナスなのに枯渇年齢が出ない");
    }
  }
  __result.identity={n:bad.length, sample:bad.slice(0,8),
    cases:PRESET_KEYS.length*WSCENARIO_KEYS.length};
});

// 最後に、既定の状態で全タブを描画し直して各要素のHTMLサイズを測る
__try("final: 既定状態で全タブ描画", function(){
  PARAMS = defaults(__P0, __W0);
  recalc();
  for (var fi = 0; fi < __tabIds.length; fi++){ TAB = __tabIds[fi]; render(); }
  buildReport();
});
var __watch = ["paramCards","cfTable","cfKpis","gAssets","gFlow","gIE",
               "loanTable","loanSummary","eduTable","eduCards",
               "cmpChart","cmpChartNW","cmpTable","cmpKeyTable","planManage",
               "stressTable","heatTable","wscTable","wscNote",
               "matrixTable","matrixNote","stressChart","aboutBody","report"];
for (var j = 0; j < __watch.length; j++) {
  __result.tabs[__watch[j]] = document.getElementById(__watch[j]).innerHTML.length;
}

__result.log = __log;
JSON.stringify(__result);
"""

R = json.loads(dukpy.evaljs(DOM_STUB + script + CHECK))

print("=" * 76)
print(f"スモークテスト: {HTML.name}")
print("=" * 76)

print("\n【描画された要素のHTMLサイズ】")
empty = []
for k, v in R["tabs"].items():
    mark = "OK " if v > 40 else "空 "
    if v <= 40:
        empty.append(k)
    print(f"  {mark}{k:<16}{v:>9,} 文字")

man = lambda v: f"{round(v/10000):,}"

if R.get("presets"):
    print("\n【住宅プランごとの結果】")
    print(f"  {'':<38}{'物件':>7}{'借入':>7}{'初年返済':>9}{'返済総額':>10}"
          f"{'最終資産':>10}{'枯渇':>6}")
    for k, v in R["presets"].items():
        print(f"  {v['label']:<38}{man(v['price']):>7}{man(v['borrow']):>7}"
              f"{man(v['firstPay']):>9}{man(v['totalPay']):>10}"
              f"{man(v['finalAsset']):>10}{(str(v['deplete'])+'歳') if v['deplete'] else '—':>6}")
    print("  （単位：万円）")

if R.get("wsc"):
    print("\n【配偶者の収入シナリオごとの結果（住宅は①）】")
    print(f"  {'':<28}{'65歳時':>9}{'最終':>9}{'最低値':>9}{'その年齢':>9}{'枯渇':>7}")
    for k, v in R["wsc"].items():
        print(f"  {v['label']:<28}{man(v['atRetire']):>9}{man(v['last']):>9}"
              f"{man(v['min']):>9}{str(v['minAge'])+'歳':>9}"
              f"{(str(v['deplete'])+'歳') if v['deplete'] else '—':>7}")
    print("  （単位：万円）")

if R.get("sell"):
    s, ss = R["sell"], R["sellSummary"]
    print("\n【不動産の売却・住み替え（①を70歳で売却、住み替え先2,000万円）】")
    print(f"  売却年 {s['year']}年（{s['age']}歳）／手残り {man(s['proceeds'])}万円"
          f"／譲渡税 {man(s['tax'])}万円")
    print(f"  住み替え先の購入 {man(s['acquisition'])}万円"
          f"／売却後の不動産価値 {man(s['estateAfter'])}万円")
    print(f"  65歳時 {man(ss['atRetire'])}万円／最終 {man(ss['last'])}万円"
          f"／最終の純資産 {man(ss['lastNW'])}万円")

if R.get("regions"):
    print("\n【地域シナリオ（0〜2歳の保育料）】")
    print(f"  {'':<24}{'第1子/月':>10}{'第2子/月':>10}{'生涯教育費':>11}"
          f"{'65歳時':>10}{'最終':>10}")
    for k, v in R["regions"].items():
        print(f"  {v['label']:<24}{man(v['n1']/12):>10}{('無償' if v['n2']==0 else man(v['n2']/12)):>10}"
              f"{man(v['lifeEdu']):>11}{man(v['atRetire']):>10}{man(v['last']):>10}")
    print("  （単位：万円）")

if R.get("types"):
    print("\n【物件種別（マンション／戸建て）】")
    for k, v in R["types"].items():
        print(f"  {v['label']}：維持費 年{man(v['maint'])}万"
              f"（相場の目安なら{man(v['maintPreset'])}万）"
              f"／臨時修繕 {man(v['bigRepair'])}万×{v['cycle']}年ごと"
              f"／土地{v['landRatio']}%・減価年数{v['life']}年")
        print(f"      価値の推移 10年後 {man(v['v10'])}万 → 20年後 {man(v['v20'])}万"
              f" → 30年後 {man(v['v30'])}万")
        print(f"      最終資産 {man(v['last'])}万／純資産 {man(v['lastNW'])}万")

if R.get("burden"):
    b = R["burden"]
    print(f"\n【月々の負担（住宅費÷手取り）】")
    print(f"  1年目 {b['first']}%／もっとも重い年 {b['worst']}%（{b['worstYear']}年）"
          f"／30%超 {b['over30']}年・35%超 {b['over35']}年")

if R.get("oldAge"):
    o = R["oldAge"]
    print(f"\n【老後資金】")
    print(f"  65歳の資産 {man(o['asset'])}万／年金生活の年間収支 {man(o['avgGap'])}万"
          f"／資産が持つ年齢 {o['lastsUntil'] or '生涯'}")
    print(f"  100歳まで必要 {man(o['needFor100'])}万／不足 {man(o['shortage'])}万")

if R.get("view"):
    v = R["view"]
    print(f"\n【名目／実質（現在価値）】")
    print(f"  40年後の1円は現在価値で {v['factorAt40']:.3f}円"
          f"／最終年（{v['factorAtEnd']:.3f}）")
    print(f"  最終資産 名目 {man(v['nominalLast'])}万円"
          f" → 現在価値 {man(v['nominalLast']*v['factorAtEnd'])}万円")
    print(f"  切替の復帰: {'OK' if v.get('backToNominal') else 'NG'}")

if R.get("goal"):
    g = R["goal"]
    print(f"\n【安心の条件（東京・884万維持）】{g['passed']}/{g['total']} 達成"
          f"{'（すべて満たす）' if g['allOk'] else ''}")
    fmt = lambda d, unit="万円": f"{'OK ' if d['ok'] else 'NG '}" \
        f"実績 {man(d['v']) if unit=='万円' else d['v']}{unit}" \
        f" / 目標 {man(d['t']) if unit=='万円' else d['t']}{unit}"
    print(f"  毎月残るお金　　: {fmt(g['surplus'])}")
    print(f"  住宅費の負担率　: {'OK ' if g['burden']['ok'] else 'NG '}"
          f"実績 {g['burden']['v']}% / 目標 {g['burden']['t']}%以内")
    print(f"  生活防衛資金　　: {'OK ' if g['cash']['ok'] else 'NG '}"
          f"実績 {g['cash']['v']}か月 / 目標 {g['cash']['t']}か月")
    print(f"  定年時の資産　　: {fmt(g['retire'])}")
    print(f"  老後の下限　　　: {fmt(g['floor'])}")
    print(f"  指定年齢まで残る: {'OK' if g['lasts']['ok'] else 'NG'}")
    if R.get("goalAfter"):
        print(f"  基準を厳しくした場合: {R['goalAfter']['passed']}/{R['goalAfter']['total']} 達成")

if R.get("breakEven"):
    b = R["breakEven"]
    f = lambda v: "1,200万でも不足" if v == -1 else ("収入0でも可" if v == 0 else man(v)+"万円以上")
    print(f"\n【配偶者年収の損益分岐点（東京・住宅①）】")
    print(f"  資産が尽きない　　　: {f(b['noDeplete'])}")
    print(f"  定年時の目標を満たす: {f(b['retireGoal'])}")
    print(f"  6条件すべて満たす　 : {f(b['allGoals'])}")

if R.get("ptax"):
    print("\n【固定資産税の3方式（①7,500万マンション）】")
    lbl = {"simple":"簡易（価格×0.306%）","detail":"詳細（土地建物・特例）","manual":"手入力"}
    print(f"  {'方式':<22}{'1年目':>8}{'6年目':>8}{'7年目':>8}{'21年目':>8}")
    for k, v in R["ptax"].items():
        print(f"  {lbl[k]:<22}" + "".join(f"{man(x):>8}" for x in v))
    d = R["ptax"]["detail"]
    print(f"  → 詳細方式では新築減額が終わる7年目に {man(d[2]-d[1])}万円 上がる")
    print("  （単位：万円／年）")

if R.get("pension"):
    print("\n【年金の自動計算】")
    p = R["pension"]
    for k, lb in [("manual","手入力（PDF値）"),("auto","収入から自動計算")]:
        v = p.get(k)
        if v:
            print(f"  {lb:<18}世帯主 {man(v['h']):>5}万／配偶者 {man(v['w']):>5}万"
                  f"／65歳資産 {man(v['atRetire']):>6}万／最終 {man(v['last']):>6}万")

if R.get("inherit"):
    i = R["inherit"]
    print("\n【相続税】")
    print(f"  国税庁の速算例との照合：")
    print(f"    {'OK ' if i['check2oku']==27000000 else 'NG '}遺産2億・配偶者と子2人の総額"
          f" 計算{man(i['check2oku'])}万 / 速算例 2,700万")
    print(f"    {'OK ' if i['check2okuKids']==33400000 else 'NG '}遺産2億・子2人のみ"
          f" 計算{man(i['check2okuKids'])}万 / 速算例 3,340万")
    print(f"    {'OK ' if i['checkBasic']==0 else 'NG '}基礎控除ぴったり（4,800万）は0円"
          f" 計算{man(i['checkBasic'])}万")
    print(f"  実プラン：世帯主{i['atAge']}歳時の遺産 {man(i['total'])}万"
          f"（基礎控除 {man(i['basic'])}万）")
    print(f"    一次 {man(i['first'])}万 ＋ 二次 {man(i['second'])}万"
          f" ＝ 合計 {man(i['grand'])}万")

if R.get("fundGap") is not None:
    print(f"\n【資金の整合性】")
    print(f"  わざと不一致にしたとき: 差額 {man(R['fundGap'])}万円 → 検出")
    print(f"  借入を合わせたあと　　: 差額 {man(R['fundGapFixed'])}万円"
          f"  {'OK' if abs(R['fundGapFixed']) < 10000 else 'NG'}")

if R.get("tabHelp"):
    print(f"\n【各ページの説明】")
    miss = [k for k, v in R["tabHelp"].items() if v == 0]
    print(f"  説明が出るページ: {len([v for v in R['tabHelp'].values() if v > 0])}"
          f"/{len(R['tabHelp'])}"
          + (f"　（出ない: {', '.join(miss)}）" if miss else "　OK 全ページ"))
    e = R.get("easy", {})
    if e:
        print(f"  初心者表示: {e['tabs']}ページに絞り込み"
              f"／切替で変わる {'OK' if e.get('toggled') else 'NG'}"
              f"／2回で元に戻る {'OK' if e.get('off') else 'NG'}")

if R.get("startTab"):
    print(f"\n【はじめにタブ】{R['startTab']['len']:,}文字を描画")

if R.get("diag"):
    print(f"\n【診断コメント】")
    print(f"  PDF前提（①・妻884万・年2%昇給）: {R['diag']['ok']}件"
          f"（{R['diag']['levels']}）")
    b = R.get("diagBad", {})
    if b:
        print(f"  厳しい条件（西小岩・妻500万・昇給なし）: {b['n']}件（{b['levels']}）")
        for tt in b.get("titles", []):
            print(f"    ・{tt}")
        print(f"  描画: {b.get('rendered', 0):,}文字")

if R.get("validate") is not None:
    print(f"\n【入力の整合性チェック】")
    print(f"  正常な状態での重大な問題: {R['validate']['clean']}件"
          f"（警告 {R['validate'].get('warns', 0)}件＝積立が大きいなどの妥当な指摘）"
          f"  {'OK' if R['validate']['clean'] == 0 else 'NG'}")
    a = R.get("autoFit", {})
    if a:
        print(f"  頭金900万→2,000万に変更（自動連動オン）")
        print(f"    借入額 {man(a['before'])}万 → {man(a['after'])}万"
              f"／資金差額 {man(a['gap'])}万"
              f"  {'OK 自動で合った' if abs(a['gap']) < 10000 else 'NG'}")
    n = R.get("noAutoFit", {})
    if n:
        print(f"  自動連動をオフにして頭金を変更")
        print(f"    資金差額 {man(n['gap'])}万／重大な問題 {n['issues']}件"
              f"  {'OK 検出された' if n['issues'] > 0 else 'NG 検出されない'}")

if R.get("dict"):
    d = R["dict"]
    print(f"\n【知っておきたいこと（辞書）】")
    print(f"  項目数 {d['count']}件／カテゴリ {d['cats']}種")
    print(f"  「保育料」で検索　　: {d.get('searchLen',0):,}文字を描画")
    print(f"  当てはまらない語句　: "
          f"{'OK 見つからない旨を表示' if d.get('noHit') else 'NG'}")
    print(f"  カテゴリで絞り込み　: {d.get('filtered',0):,}文字を描画")

if R.get("ldTypes"):
    print(f"\n【住宅ローン控除の住宅の種類】")
    print(f"  {'種類':<30}{'限度額':>9}{'期間':>6}{'控除総額':>10}")
    for k, v in R["ldTypes"].items():
        print(f"  {v['label']:<28}{man(v['limit']):>9}{str(v['years'])+'年':>6}"
              f"{man(v['total']):>10}")
    if R.get("ldBonus"):
        b = R["ldBonus"]
        print(f"  ＋子育て世帯の上乗せ（認定長期優良）: 限度額 {man(b['limit'])}万"
              f"／控除総額 {man(b['total'])}万")
    print("  （単位：万円）")

print(f"\n【テーマ切替】{R.get('theme1')} → {R.get('theme2')}")

print(f"\n【メモ機能】")
print(f"  プラン一覧での編集: {R.get('memo') or '（失敗）'}")
print(f"  レポートへの反映　: {'OK' if R.get('memoInReport') else '（未反映）'}")
print(f"  自動生成されるメモ: {(R.get('autoMemo') or '')[:78]}")

print(f"\n  保存されたプラン数: {R.get('planCount')}")

print("\n【エラー】")
if R["errors"]:
    for e in R["errors"]:
        print(f"  NG  {e}")
else:
    print("  なし（全タブの描画とパラメータ操作が通りました）")

RL = R.get("rule")
if RL:
    print(chr(10)+"【制度の検算（手計算との照合）】")
    print("  退職所得課税5ケース／NISAの生涯投資枠3ケース／借入残高と資産の整合3ケース")
    if RL["n"] == 0:
        print("  ずれ 0件  OK 制度どおりに計算されています")
    else:
        print(f"  ずれ {RL['n']}件  NG")
        for s in RL["sample"]:
            print("    ", s)
        R["errors"].append("制度の検算でずれ: " + " / ".join(RL["sample"][:3]))

I2 = R.get("identity")
if I2:
    print("\n【数字の整合性（全数検算）】")
    print(f"  {I2['cases']}通り × 全年について、合計と内訳・収支の式・資産の増減を確認")
    if I2["n"] == 0:
        print("  違反 0件  OK すべての年で数字が矛盾していません")
    else:
        print(f"  違反 {I2['n']}件  NG")
        for s in I2["sample"]:
            print("    ", s)
        R["errors"].append(f"数字の整合性に違反 {I2['n']}件: " + " / ".join(I2["sample"][:3]))

U = R.get("ui")
if U:
    print("\n【UIの3機能】")
    lg = U["legend"]
    ng_ui = []
    print(f"  凡例で線を隠す　　: {lg['before']:,}字 → {lg['after']:,}字"
          f"（{lg['after']-lg['before']:+,}）／隠している数 {lg['hidden']}"
          f"／取消線 {'出る' if lg['struck'] else '出ない'}"
          f"／全表示ボタン {'出る' if lg['allBtn'] else '出ない'}")
    if lg["after"] >= lg["before"]:
        ng_ui.append("凡例を押しても線が減っていない")
    if not (lg["struck"] and lg["allBtn"]):
        ng_ui.append("隠したことが凡例に表れていない")
    if lg["restored"] != 0:
        ng_ui.append("すべて表示に戻せていない")
    st = U["step"]
    print(f"  1つずつ進む表示　: {st['count']}ステップ／移動 0→{st['moved']}"
          f"／現在位置の表示 {'あり' if st['showsPos'] else 'なし'}"
          f"／まとめて表示 {st['allOn']}（そのとき下ボタン {st['footWhenAll']}字）")
    if st["moved"] != 3:
        ng_ui.append("ステップの移動ができていない")
    if not st["showsPos"]:
        ng_ui.append("いま何番目かが出ていない")
    if st["footWhenAll"] != 0:
        ng_ui.append("まとめて表示のとき次へボタンが残っている")
    sl = U["slider"]
    print(f"  スライダー　　　　: 定義{sl['defined']}件"
          f"／設定ページ{sl['inSettings']}件＋安心の条件{sl['inGoals']}件"
          f"／動かすと {sl['moved']['from']:,}→{sl['moved']['to']:,}円")
    if sl["inSettings"] + sl["inGoals"] != sl["defined"]:
        ng_ui.append(f"スライダーの表示数{sl['inSettings']+sl['inGoals']}が定義{sl['defined']}と合わない")
    if sl["moved"]["from"] == sl["moved"]["to"]:
        ng_ui.append("スライダーを動かしても値が変わらない")
    print("  動作の一貫性: " + ("OK すべて意図どおり" if not ng_ui else "NG " + " / ".join(ng_ui)))
    if ng_ui:
        R["errors"].append("UIの3機能が意図と違う: " + " / ".join(ng_ui))

M = R.get("migrate")
if M:
    print("\n【古い/壊れた保存プランからの復旧】")
    print(f"  {'保存データ':34}{'件数':>4}{'一覧':>7}{'指標':>7}{'グラフ':>8}  判定")
    bad_mig = []
    for r in M:
        if not r.get("ok"):
            print(f"  {r['name']:34}{'':>4}{'':>7}{'':>7}{'':>8}  NG 落ちた: {r.get('err')}")
            bad_mig.append(f"{r['name']}: {r.get('err')}")
            continue
        if r["plans"] == 0:
            # 読み込めるプランが1件もない場合は「まだプランがありません」の案内が正しい
            mark = "OK（0件の案内）" if r["manage"] > 100 else "NG 案内も出ていない"
            if r["manage"] <= 100:
                bad_mig.append(f"{r['name']}: 0件の案内が出ていない")
        else:
            # 表とグラフが両方出ていれば復旧成功
            full = r["manage"] > 300 and r["key"] > 300 and r["chart"] > 300
            mark = "OK" if full else ("OK（案内表示）" if r["notice"] else "NG 中身が出ていない")
            if not full and not r["notice"]:
                bad_mig.append(f"{r['name']}: 表もグラフも出ていない")
        print(f"  {r['name']:34}{r['plans']:>4}{r['manage']:>7}{r['key']:>7}{r['chart']:>8}  {mark}")
    print("  復旧の一貫性: " + ("OK すべて描画できた" if not bad_mig
                                else "NG " + " / ".join(bad_mig)))
    if bad_mig:
        R["errors"].append("古い保存プランから復旧できない: " + " / ".join(bad_mig))

J = R.get("judge")
if J:
    print("\n【赤字と借入の区別】")
    print(f"  {'プラン':14}{'枯渇':>6}{'赤字年':>7}{'最長':>5}{'借入年':>7}"
          f"{'決定的OK':>9}{'余裕度':>7}{'●':>3}{'▲':>3}{'✓':>3}  赤字の診断")
    for j in J:
        print(f"  {j['plan']:14}{str(j['depl'] or '—'):>6}{j['negYears']:>7}{j['negRunMax']:>5}"
              f"{j['borrowYears']:>7}{('OK' if j['decisiveOk'] else 'NG'):>9}"
              f"{str(j['comfortPassed'])+'/4':>7}{j['bad']:>3}{j['warn']:>3}{j['okItems']:>3}"
              f"  [{j['negLevel'] or '-'}] {j['negTitle'] or '（なし）'}")
    bad_judge = []
    for j in J:
        # 借入が要らないのに赤字を重大扱いしていたらNG
        if j["borrowYears"] == 0 and j["negLevel"] == "bad":
            bad_judge.append(f"{j['plan']}: 借入不要なのに赤字を●（重大）と判定")
        # 借入が必要なのに軽く扱っていたらNG
        if j["borrowYears"] > 0 and j["negYears"] > 0 and j["negLevel"] == "warn":
            bad_judge.append(f"{j['plan']}: 借入が必要なのに赤字を▲（軽い）と判定")
        # 破綻しないプランで「破綻しない」と明言する✓が出ているか
        if not j["depl"] and j["borrowYears"] == 0 and j["floorOk"] and j["okItems"] == 0:
            bad_judge.append(f"{j['plan']}: 破綻しないのに、そう明言する✓の項目が出ていない")
    print("\n  ―― 赤字がいつ来るか（一時的か恒久的か）――")
    for j in J:
        kind = {"none":"赤字なし", "spot":"一時的",
                "long":"一時的だが長い", "chronic":"恒常的（ならしても赤字）",
                "toRetire":"定年まで続く"}[j["negKind"]]
        runs = " / ".join(f"{r['age']}歳 {r['years']}年 平均{r['avg']}万" for r in j["runs"]) or "なし"
        print(f"  {j['plan']:14}{kind:18}赤字{j['negYears']}年・黒字{j['posYears']}年"
              f"（現役{j['workYears']}年）")
        print(f"  {'':14}山: {runs}")
        print(f"  {'':14}赤字の年の平均 {j['avgNeg']}万円/月 ／ "
              f"現役期ぜんぶの平均 {j['avgWork']}万円/月")
    # 区間の年数の合計が赤字年数と一致するか（数え漏れ・重複の検出）
    for j in J:
        s = sum(r["years"] for r in j["runs"])
        if s != j["negYears"]:
            bad_judge.append(f"{j['plan']}: 区間の年数合計{s}年が赤字年数{j['negYears']}年と不一致")
        if j["negYears"] + j["posYears"] != j["workYears"]:
            bad_judge.append(f"{j['plan']}: 赤字＋黒字が現役期の年数と合わない")
        if j["runs"] and j["negRunMax"] != max(r["years"] for r in j["runs"]):
            bad_judge.append(f"{j['plan']}: 最長連続年数が区間の最大と合わない")
        # ならして赤字なのに「一時的」と言っていないか
        if j["avgWork"] < 0 and j["negKind"] in ("spot", "long"):
            bad_judge.append(f"{j['plan']}: ならして赤字なのに一時的と判定")
        # 5年以上続くのに「一時的（spot）」で済ませていないか
        if j["negRunMax"] >= 5 and j["negKind"] == "spot":
            bad_judge.append(f"{j['plan']}: {j['negRunMax']}年続くのに spot と判定")
    print("\n  判定の一貫性: " + ("OK すべて意図どおり" if not bad_judge
                                 else "NG " + " / ".join(bad_judge)))
    if bad_judge:
        R["errors"].append("赤字の評価が意図と違う: " + " / ".join(bad_judge))

I = R.get("ins")
if I:
    print("\n【保険料の年齢別テーブル】")
    print(f"  既定の方式　　　　: {I['mode0']}（2値方式）"
          f"  {'OK' if I['mode0'] == 'simple' else 'NG PDF再現の既定が変わっている'}")
    print(f"  年齢別に切り替え　: {I['mode1']}"
          f"  {'OK' if I['mode1'] == 'table' else 'NG'}")
    print(f"  目安テーブルの中身: "
          + " / ".join(f"{r['age']}歳〜{r['man']}万" for r in I["table"]))
    print(f"  年齢が昇順　　　　: {'OK' if I['ascending'] else 'NG 逆順の行がある'}")
    print(f"  40歳時点の保険料　: 2値 {I['simpleAt40']:,}円 → 年齢別 {I['tableAt40']:,}円")
    print(f"  56歳時点の保険料　: 2値 {I['simpleAt56']:,}円 → 年齢別 {I['tableAt56']:,}円"
          f"  {'OK 50代が重くなる' if I['tableAt56'] > I['simpleAt56'] else 'NG 上がっていない'}")
    print(f"  生涯の保険料合計　: 2値 {I['simpleTotal']/10000:,.0f}万円"
          f" → 年齢別 {I['tableTotal']/10000:,.0f}万円"
          f"（差 {(I['tableTotal']-I['simpleTotal'])/10000:+,.0f}万円）")
    print(f"  物件プリセットへの追従（個人版のみ）　: {I['followBefore']:,}円 → {I['followBuyAmount']:,}円"
          f"  {'OK 物件ごとの火災保険が反映される' if I['followBuyAmount'] != I['followBefore'] else 'NG 追従しない'}")
    print(f"  不整合の検出　　　: {I['badDetected']}件"
          f"  {'OK' if I['badDetected'] >= 1 else 'NG 50歳開始のテーブルを見逃した'}")

def check_inline_handlers(html_text):
    """描画したHTMLのイベント属性を1つずつ構文検査する。

    ブラウザは onclick を「押したとき」に解析するので、壊れていても
    関数を直接呼ぶテストでは通ってしまう。ここで先に捕まえる。
    """
    import html as _html

    pat = re.compile(r'\bon(?:click|change|input|keyup|submit)\s*=\s*"([^"]*)"')
    seen, bad = set(), []
    for m in pat.finditer(html_text):
        code = _html.unescape(m.group(1))
        if code in seen:
            continue
        seen.add(code)
        try:
            dukpy.evaljs("(function(){" + code + "\n}); 'OK'")
        except Exception as exc:
            bad.append((code[:88], str(exc)[:80]))
    return len(seen), bad


print("\n【イベント属性の構文検査】")
print("  onclick などはブラウザが押したときに解析するので、"
      "関数を直接呼ぶだけでは壊れていても気づけない")
_handler_ng = []
_html_all = R.get("renderedHtml") or ""
if not _html_all:
    print("  描画HTMLを取得できませんでした（スキップ）")
else:
    _n, _handler_ng = check_inline_handlers(_html_all)
    print(f"  {_n} 種類を検査")
    if _handler_ng:
        for _code, _err in _handler_ng:
            print(f"  NG  {_code}")
            print(f"      -> {_err}")
    else:
        print("  OK  すべて構文として正しく、押せば動きます")

print(f"\n極端値テスト（物件2億・金利10%）の資産枯渇年齢: "
      f"{R.get('extremeDeplete') or 'なし'}")

ng = len(R["errors"]) + len(empty) + len(_handler_ng)
print("\n" + "=" * 76)
if ng == 0:
    print("結果: 異常なし")
else:
    print(f"結果: 要確認 {ng} 件"
          + (f"（描画が空: {', '.join(empty)}）" if empty else ""))
print("=" * 76)
sys.exit(1 if ng else 0)
