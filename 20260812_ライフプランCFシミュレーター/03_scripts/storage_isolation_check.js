/* 汎用版が、個人版の保存データを読まないことを実ブラウザで確かめる。
 *
 * **なぜ作ったか（2026-08-27）**
 * 依頼者から「汎用版に、個人版で入力した年収を使ったプランが32個ある」と指摘された。
 * 切り分けると、**配布するHTMLファイル自体は綺麗**だった（プラン0件・架空サンプル3件）。
 * 原因は **汎用版と個人版が同じ localStorage キー `lpcf_plans` を使っていたこと**。
 * 同一オリジン（同じ localhost、または file:// 同士）で個人版を開いたことがある端末では、
 * **汎用版が個人版の保存プランを読み込んで画面に出していた。**
 *
 * ★**匿名化検査では原理的に見つからない。** 語句も金額もファイルの中を見る検査で、
 *   保存領域はファイルの外にある。
 *   「個人データが無いこと」を確かめる範囲に、**ブラウザの保存領域を必ず含める。**
 *
 * 測るもの
 *   1. 汎用版のキーが個人版と分かれているか（`lpcfg_` 名前空間）
 *   2. 旧キーに32件置いても、汎用版が0件のままか
 *   3. 旧キーの中身が画面に出ないか
 *   4. 旧キーを勝手に消していないか（利用者のデータなので残す）
 *   5. 残っていることを知らせているか
 *   6. 保存すると新キーに入り、旧キーを汚さないか
 *   7. `getItem` を監視して、**個人版のキーを一度も読まないこと**
 *
 * 使い方：preview_start でHTMLを開き、この中身を javascript_tool で実行する。
 *   ★実行後にリロードが必要な検査があるため、2段に分かれている。
 *     手順1を実行 → location.reload() → 手順2を実行。
 */
(function () {
  const OLD = "lpcf_plans";       // 個人版・旧汎用版
  const NEW = "lpcfg_plans";      // 汎用版
  const log = [];
  const ok = (name, pass, detail) => log.push({ name, pass: !!pass, detail: detail || "" });

  /* ---- 手順1：旧キーに32件を仕込む（まだ読み込ませない） ---- */
  if (!localStorage.getItem(OLD)) {
    const old = [];
    for (let i = 0; i < 32; i++) {
      const p = JSON.parse(JSON.stringify(blankParams()));
      /* 個人版の実額に相当する値を入れる。これが画面に出たら失格。 */
      p.income.hBase = 8840000;
      p.meta.planName = "他の版のプラン" + (i + 1);
      old.push({ name: "他の版のプラン" + (i + 1), at: "2026-08-20 10:00", params: p });
    }
    localStorage.setItem(OLD, JSON.stringify(old));
    localStorage.removeItem(NEW);
    localStorage.removeItem(NEW + "_notified");
    return JSON.stringify({
      手順: 1,
      次にやること: "location.reload() してから、もう一度これを実行してください",
      仕込んだ件数: old.length,
    });
  }

  /* ---- 手順2：リロード後の状態を測る ---- */
  ok("汎用版のキーが分かれている", typeof STORE === "object" && STORE.plans === NEW,
    "STORE.plans=" + (typeof STORE === "object" ? STORE.plans : "なし"));

  ok("旧キーの32件を読み込んでいない", PLANS.length === 0, "PLANS=" + PLANS.length + "件");

  const body = document.body.innerText;
  ok("旧キーの中身が画面に出ない", !/他の版のプラン/.test(body) && !/884万/.test(body));

  const oldNow = JSON.parse(localStorage.getItem(OLD) || "[]");
  ok("旧キーを勝手に消していない", oldNow.length === 32, "旧キー=" + oldNow.length + "件");

  ok("残っていることを知らせている", /別の版で保存されたプランが32件/.test(body));

  /* 保存すると新キーに入り、旧キーを汚さないか */
  PARAMS = blankParams();
  PARAMS.family.ageH = 40; PARAMS.income.hBase = 6000000;
  PARAMS.income.hTable = [{ age: 40, amount: 6000000, rate: 0 }];
  PARAMS.meta.blank = false; PARAMS.meta.planName = "検査用";
  const el = document.getElementById("planName"); if (el) el.value = "検査用";
  savePlan();
  ok("保存は新キーに入る", JSON.parse(localStorage.getItem(NEW) || "[]").length === 1);
  ok("保存で旧キーを汚さない",
    JSON.parse(localStorage.getItem(OLD) || "[]").length === 32);

  /* ★getItem を監視して、個人版のキーを一度も読まないことを確かめる */
  const reads = [];
  const realGet = Storage.prototype.getItem;
  Storage.prototype.getItem = function (k) { reads.push(k); return realGet.apply(this, arguments); };
  try {
    loadPlans(); recalc();
    if (typeof TABS !== "undefined") TABS.forEach(p => { try { setTab(p[0]); } catch (e) {} });
  } finally {
    Storage.prototype.getItem = realGet;
  }
  ok("個人版のキーを一度も読まない", reads.indexOf(OLD) < 0,
    "読んだキー=" + Array.from(new Set(reads)).join(", "));

  /* 片付け */
  localStorage.removeItem(OLD);
  localStorage.removeItem(NEW);
  localStorage.removeItem(NEW + "_notified");
  loadPlans();

  const ng = log.filter(x => !x.pass);
  return JSON.stringify({
    手順: 2,
    版: (typeof VERSION !== "undefined" ? VERSION.tag : "?"),
    件数: log.length, NG: ng.length,
    判定: ng.length === 0 ? "OK  汎用版は個人版の保存データを読みません" : "NG  下を参照",
    結果: log,
  });
})()
