#!/usr/bin/env python3
"""
v5_to_v6_expand_existing.py  ─  既存コンテンツの大幅拡充

変更内容:
  1. 新タブ「💬 会話＆フレーズ」追加（シーン別アラビア語/ギリシャ語フレーズ）
  2. 旅程表：15日間 出費目安・昼食候補・移動手段テーブル
  3. お土産タブ：価格帯・真贋チェックガイド
  4. エリア・宿タブ：ホテル別実用Tips
  5. 歴史タブ：スポット別「見どころ3点＋推奨所要時間」カード
  6. フォトタブ：ブライダルフォト ロケーション名具体化
  7. 服装タブ：スーツケース重量配分シート
"""

from pathlib import Path

BASE   = Path(__file__).parent.parent / "02_output"
INPUT  = BASE / "20260901_新婚旅行しおり_v5.html"
OUTPUT = BASE / "20260901_新婚旅行しおり_v6.html"

html = INPUT.read_text(encoding="utf-8")
print(f"読み込み完了: {len(html):,} chars\n")

# ══════════════════════════════════════════════════════════
# 1. 新タブボタン「💬 会話＆フレーズ」追加
# ══════════════════════════════════════════════════════════
TAB_BTN_ANCHOR = '安心ガイド・Tips\n        </button>'
NEW_TAB_BTN    = '\n        <button id="btn-tab-phrases" onclick="switchTab(\'tab-phrases\')" class="nav-btn px-3 py-1.5 rounded-full whitespace-nowrap transition border border-slate-300 bg-white text-slate-700 shadow-xs hover:bg-amber-50">\n          <i class="fa-solid fa-language mr-1"></i> 会話＆フレーズ\n        </button>'
assert TAB_BTN_ANCHOR in html, "安心ガイドタブボタンが見つかりません"
html = html.replace(TAB_BTN_ANCHOR, TAB_BTN_ANCHOR + NEW_TAB_BTN, 1)
print("1a. タブボタン追加 ✓")

# ══════════════════════════════════════════════════════════
# 1b. 新タブセクション本体（tab-tipsの後に追加）
# ══════════════════════════════════════════════════════════
LAST_SECTION = html.rfind('\n    </section>')
assert LAST_SECTION > 0, "最後の</section>が見つかりません"
INSERT_POS = LAST_SECTION + len('\n    </section>')

PHRASES_TAB = """

    <!-- ==================== TAB 9: 会話＆フレーズ ==================== -->
    <section id="tab-phrases" class="tab-content space-y-5">

      <!-- 使い方説明 -->
      <div class="bg-gradient-to-r from-indigo-50 to-purple-50 border border-indigo-200 rounded-2xl p-4 sm:p-5 shadow-xs">
        <div class="flex items-center space-x-2.5 mb-3">
          <i class="fa-solid fa-language text-indigo-600 text-xl"></i>
          <div>
            <h2 class="font-bold text-indigo-950 text-sm sm:text-base">💬 シーン別フレーズ集（アラビア語 ＆ ギリシャ語）</h2>
            <p class="text-xs text-indigo-700">画面を相手に見せるだけでOK。カタカナ読みで通じます。</p>
          </div>
        </div>
        <div class="grid grid-cols-3 gap-2 text-[11px] text-center">
          <div class="bg-white rounded-lg p-2 border border-indigo-200"><span class="text-lg">🍽️</span><br>レストラン</div>
          <div class="bg-white rounded-lg p-2 border border-indigo-200"><span class="text-lg">🏥</span><br>薬局</div>
          <div class="bg-white rounded-lg p-2 border border-indigo-200"><span class="text-lg">🚖</span><br>移動</div>
          <div class="bg-white rounded-lg p-2 border border-indigo-200"><span class="text-lg">🛍️</span><br>値切り</div>
          <div class="bg-white rounded-lg p-2 border border-indigo-200"><span class="text-lg">🆘</span><br>緊急</div>
          <div class="bg-white rounded-lg p-2 border border-indigo-200"><span class="text-lg">🤝</span><br>挨拶</div>
        </div>
      </div>

      <!-- 🇪🇬 アラビア語フレーズ -->
      <div class="bg-amber-50 border border-amber-200 rounded-2xl p-4 sm:p-5 shadow-xs space-y-4">
        <div class="flex items-center space-x-2 border-b border-amber-200 pb-2">
          <span class="text-xl">🇪🇬</span>
          <h2 class="font-bold text-amber-950 text-sm sm:text-base">エジプト（エジプト・アラビア語）フレーズ集</h2>
        </div>

        <!-- 挨拶・基本 -->
        <div class="bg-white rounded-xl border border-amber-200 p-3 space-y-2">
          <h3 class="font-bold text-amber-800 text-xs border-b border-amber-100 pb-1">🤝 挨拶・基本</h3>
          <div class="grid grid-cols-1 sm:grid-cols-2 gap-1.5 text-xs">
            <div class="flex justify-between p-1.5 bg-amber-50 rounded"><span>こんにちは（日中）</span><span class="font-bold text-amber-900">サラーム・アレイコム <span class="text-slate-500 font-normal">السلام عليكم</span></span></div>
            <div class="flex justify-between p-1.5 bg-amber-50 rounded"><span>ありがとう</span><span class="font-bold text-amber-900">シュクラン <span class="text-slate-500 font-normal">شكراً</span></span></div>
            <div class="flex justify-between p-1.5 bg-amber-50 rounded"><span>はい / いいえ</span><span class="font-bold text-amber-900">アイワ / ラー <span class="text-slate-500 font-normal">أيوا / لأ</span></span></div>
            <div class="flex justify-between p-1.5 bg-amber-50 rounded"><span>いくらですか？</span><span class="font-bold text-amber-900">ビカーム・ダー？ <span class="text-slate-500 font-normal">بكام ده؟</span></span></div>
            <div class="flex justify-between p-1.5 bg-amber-50 rounded"><span>高すぎます</span><span class="font-bold text-amber-900">ダー・ガーリ・アウィー <span class="text-slate-500 font-normal">ده غالي أوي</span></span></div>
            <div class="flex justify-between p-1.5 bg-amber-50 rounded"><span>美味しい！</span><span class="font-bold text-amber-900">ラズィーズ！ <span class="text-slate-500 font-normal">لذيذ</span></span></div>
            <div class="flex justify-between p-1.5 bg-amber-50 rounded"><span>結構です/いりません</span><span class="font-bold text-amber-900">ラー・シュクラン <span class="text-slate-500 font-normal">لأ شكراً</span></span></div>
            <div class="flex justify-between p-1.5 bg-amber-50 rounded"><span>トイレはどこ？</span><span class="font-bold text-amber-900">フェーン・エル・ハンマーム？ <span class="text-slate-500 font-normal">فين الحمام؟</span></span></div>
          </div>
        </div>

        <!-- レストラン（乳製品なし） -->
        <div class="bg-white rounded-xl border border-rose-200 p-3 space-y-2">
          <h3 class="font-bold text-rose-800 text-xs border-b border-rose-100 pb-1">🍽️ レストラン（乳製品アレルギー対応）— 画面を見せてください</h3>
          <div class="p-3 bg-rose-50 rounded-lg text-sm leading-relaxed text-right" dir="rtl">
            <p class="font-bold text-rose-900 text-base mb-1">من فضلك، أنا عندي حساسية من منتجات الألبان.</p>
            <p class="text-rose-800">بدون لبن، بدون جبن، بدون زبدة، بدون زبادي.</p>
            <p class="text-rose-700 text-sm">ممكن تأكدلي من المطبخ؟ شكراً جزيلاً.</p>
          </div>
          <p class="text-[11px] text-rose-700 text-center">（発音）ミン・ファドラック、アナ・アンディ・ハサシーヤ・ミン・マンタガート・アルアルバーン。ビドーン・ラバン、ビドーン・ジュブン、ビドーン・ズィブダ、ビドーン・ザバーディ。</p>
          <div class="grid grid-cols-1 sm:grid-cols-2 gap-1.5 text-xs mt-2">
            <div class="flex justify-between p-1.5 bg-amber-50 rounded"><span>牛乳なしで</span><span class="font-bold text-amber-900">ミン・ガイル・ラバン</span></div>
            <div class="flex justify-between p-1.5 bg-amber-50 rounded"><span>チーズなしで</span><span class="font-bold text-amber-900">ミン・ガイル・ジュブン</span></div>
            <div class="flex justify-between p-1.5 bg-amber-50 rounded"><span>お勘定をお願い</span><span class="font-bold text-amber-900">エル・ヒサーブ・ロウ・サマハト</span></div>
            <div class="flex justify-between p-1.5 bg-amber-50 rounded"><span>水（ボトル）ください</span><span class="font-bold text-amber-900">ウィーズ・マイヤ・ザガザーバ</span></div>
          </div>
        </div>

        <!-- 薬局 -->
        <div class="bg-white rounded-xl border border-emerald-200 p-3 space-y-2">
          <h3 class="font-bold text-emerald-800 text-xs border-b border-emerald-100 pb-1">🏥 薬局で症状を伝える</h3>
          <div class="grid grid-cols-1 sm:grid-cols-2 gap-1.5 text-xs">
            <div class="p-1.5 bg-emerald-50 rounded"><div class="font-bold text-emerald-900">お腹を壊しています</div><div class="text-emerald-700">アンディ・イスハール（عندي إسهال）</div></div>
            <div class="p-1.5 bg-emerald-50 rounded"><div class="font-bold text-emerald-900">頭痛があります</div><div class="text-emerald-700">アンディ・スダーウ（عندي صداع）</div></div>
            <div class="p-1.5 bg-emerald-50 rounded"><div class="font-bold text-emerald-900">熱があります</div><div class="text-emerald-700">アンディ・ハラーラ（عندي حرارة）</div></div>
            <div class="p-1.5 bg-emerald-50 rounded"><div class="font-bold text-emerald-900">気分が悪いです</div><div class="text-emerald-700">アナ・ミッシュ・クワイィス（أنا مش كويس）</div></div>
            <div class="p-1.5 bg-emerald-50 rounded"><div class="font-bold text-emerald-900">Antinalください（細菌性下痢薬）</div><div class="text-emerald-700">アナ・アウィーズ・アンティナール</div></div>
            <div class="p-1.5 bg-emerald-50 rounded"><div class="font-bold text-emerald-900">解熱剤をください</div><div class="text-emerald-700">アナ・アウィーズ・ハーガ・リル・ハラーラ</div></div>
          </div>
        </div>

        <!-- 移動・配車 -->
        <div class="bg-white rounded-xl border border-sky-200 p-3 space-y-2">
          <h3 class="font-bold text-sky-800 text-xs border-b border-sky-100 pb-1">🚖 タクシー・移動（Uberが使えない時）</h3>
          <div class="grid grid-cols-1 sm:grid-cols-2 gap-1.5 text-xs">
            <div class="p-1.5 bg-sky-50 rounded"><div class="font-bold text-sky-900">メーターで行ってください</div><div class="text-sky-700">ビル・アッダード（بالعداد）</div></div>
            <div class="p-1.5 bg-sky-50 rounded"><div class="font-bold text-sky-900">高すぎます！</div><div class="text-sky-700">ダー・ガーリ・アウィー（ده غالي أوي）</div></div>
            <div class="p-1.5 bg-sky-50 rounded"><div class="font-bold text-sky-900">止まってください</div><div class="text-sky-700">ウッアフ・フナー（وقف هنا）</div></div>
            <div class="p-1.5 bg-sky-50 rounded"><div class="font-bold text-sky-900">急いでいます</div><div class="text-sky-700">アナ・ムスタアゲル（أنا مستعجل）</div></div>
          </div>
          <div class="p-2 bg-amber-50 rounded text-[11px] text-amber-800">💡 <strong>Uber推奨：</strong>料金はアプリで確定済み。タクシーは乗車前に「紙に金額を書いてもらい合意」が鉄則。</div>
        </div>

        <!-- 値切り交渉 -->
        <div class="bg-white rounded-xl border border-orange-200 p-3 space-y-2">
          <h3 class="font-bold text-orange-800 text-xs border-b border-orange-100 pb-1">🛍️ 値切り交渉フレーズ</h3>
          <div class="grid grid-cols-1 sm:grid-cols-2 gap-1.5 text-xs">
            <div class="p-1.5 bg-orange-50 rounded"><div class="font-bold text-orange-900">〇〇ポンドにしてください</div><div class="text-orange-700">ビ [数字] ジュニー（بـ ... جنيه）</div></div>
            <div class="p-1.5 bg-orange-50 rounded"><div class="font-bold text-orange-900">考えます（歩き去る）</div><div class="text-orange-700">ハフィッキル・ワ・アルガウ（هفكر وأرجع）</div></div>
            <div class="p-1.5 bg-orange-50 rounded"><div class="font-bold text-orange-900">最後の価格は？</div><div class="text-orange-700">アーヒル・タマン？（آخر تمن؟）</div></div>
            <div class="p-1.5 bg-orange-50 rounded"><div class="font-bold text-orange-900">友達価格で！</div><div class="text-orange-700">ビサア・エル・アスハーブ！（بسعر الأصحاب）</div></div>
          </div>
          <div class="p-2 bg-orange-50 rounded text-[11px] text-orange-800">💡 値切りのコツ：提示額の40〜60%を最初のカウンターに。笑顔で楽しみながら交渉するのがルール。</div>
        </div>
      </div>

      <!-- 🇬🇷 ギリシャ語フレーズ -->
      <div class="bg-sky-50 border border-sky-200 rounded-2xl p-4 sm:p-5 shadow-xs space-y-4">
        <div class="flex items-center space-x-2 border-b border-sky-200 pb-2">
          <span class="text-xl">🇬🇷</span>
          <h2 class="font-bold text-sky-950 text-sm sm:text-base">ギリシャ（ギリシャ語）フレーズ集</h2>
        </div>

        <!-- 挨拶・基本 -->
        <div class="bg-white rounded-xl border border-sky-200 p-3 space-y-2">
          <h3 class="font-bold text-sky-800 text-xs border-b border-sky-100 pb-1">🤝 挨拶・基本</h3>
          <div class="grid grid-cols-1 sm:grid-cols-2 gap-1.5 text-xs">
            <div class="flex justify-between p-1.5 bg-sky-50 rounded"><span>こんにちは/やあ</span><span class="font-bold text-sky-900">ヤーサス <span class="text-slate-500 font-normal">Γεια σας</span></span></div>
            <div class="flex justify-between p-1.5 bg-sky-50 rounded"><span>ありがとう</span><span class="font-bold text-sky-900">エフハリスト <span class="text-slate-500 font-normal">Ευχαριστώ</span></span></div>
            <div class="flex justify-between p-1.5 bg-sky-50 rounded"><span>はい / いいえ</span><span class="font-bold text-sky-900">ネ / オヒ <span class="text-slate-500 font-normal">Ναι / Όχι</span></span></div>
            <div class="flex justify-between p-1.5 bg-sky-50 rounded"><span>お願いします</span><span class="font-bold text-sky-900">パラカロー <span class="text-slate-500 font-normal">Παρακαλώ</span></span></div>
            <div class="flex justify-between p-1.5 bg-sky-50 rounded"><span>いくらですか？</span><span class="font-bold text-sky-900">ポソ・コスティジ？ <span class="text-slate-500 font-normal">Πόσο κοστίζει;</span></span></div>
            <div class="flex justify-between p-1.5 bg-sky-50 rounded"><span>美味しい！</span><span class="font-bold text-sky-900">ノスティモ！ <span class="text-slate-500 font-normal">Νόστιμο!</span></span></div>
            <div class="flex justify-between p-1.5 bg-sky-50 rounded"><span>お会計をお願い</span><span class="font-bold text-sky-900">トン・ロガリアズモ・パラカロー <span class="text-slate-500 font-normal">Τον λογαριασμό</span></span></div>
            <div class="flex justify-between p-1.5 bg-sky-50 rounded"><span>助けてください！</span><span class="font-bold text-sky-900">ヴォーイシャ！ <span class="text-slate-500 font-normal">Βοήθεια!</span></span></div>
          </div>
        </div>

        <!-- レストラン（乳製品なし） -->
        <div class="bg-white rounded-xl border border-rose-200 p-3 space-y-2">
          <h3 class="font-bold text-rose-800 text-xs border-b border-rose-100 pb-1">🍽️ レストラン（乳製品アレルギー対応）— 画面を見せてください</h3>
          <div class="p-3 bg-rose-50 rounded-lg text-sm leading-relaxed">
            <p class="font-bold text-rose-900 text-base mb-1">Έχω αλλεργία στα γαλακτοκομικά.</p>
            <p class="text-rose-800">Χωρίς τυρί, χωρίς γάλα, χωρίς βούτυρο, χωρίς γιαούρτι.</p>
            <p class="text-rose-700 text-sm">Μπορείτε να ελέγξετε με την κουζίνα; Ευχαριστώ πολύ.</p>
          </div>
          <p class="text-[11px] text-rose-700 text-center">（発音）エホ・アレルギア・スタ・ガラクトコミカ。ホリス・ティリ、ホリス・ガラ、ホリス・ブティロ、ホリス・ヤウルティ。</p>
          <div class="grid grid-cols-1 sm:grid-cols-2 gap-1.5 text-xs mt-2">
            <div class="flex justify-between p-1.5 bg-sky-50 rounded"><span>チーズなしで</span><span class="font-bold text-sky-900">ホリス・ティリ（χωρίς τυρί）</span></div>
            <div class="flex justify-between p-1.5 bg-sky-50 rounded"><span>ヨーグルトなしで</span><span class="font-bold text-sky-900">ホリス・ヤウルティ（χωρίς γιαούρτι）</span></div>
            <div class="flex justify-between p-1.5 bg-sky-50 rounded"><span>グリル魚はありますか？</span><span class="font-bold text-sky-900">エヘテ・スカラ・プサリ？</span></div>
            <div class="flex justify-between p-1.5 bg-sky-50 rounded"><span>地元のワインを一杯</span><span class="font-bold text-sky-900">エナ・ポティリ・トピコ・クラシ</span></div>
          </div>
        </div>

        <!-- ショッピング -->
        <div class="bg-white rounded-xl border border-emerald-200 p-3 space-y-2">
          <h3 class="font-bold text-emerald-800 text-xs border-b border-emerald-100 pb-1">🛍️ ショッピング・免税</h3>
          <div class="grid grid-cols-1 sm:grid-cols-2 gap-1.5 text-xs">
            <div class="p-1.5 bg-emerald-50 rounded"><div class="font-bold text-emerald-900">Tax Freeの書類をください</div><div class="text-emerald-700">パラカロー・エナ・エグラフォ・アフォロロギティス・アゴラス</div></div>
            <div class="p-1.5 bg-emerald-50 rounded"><div class="font-bold text-emerald-900">試着できますか？</div><div class="text-emerald-700">ボロー・ナ・ト・ドキマソ；（Μπορώ να το δοκιμάσω;）</div></div>
            <div class="p-1.5 bg-emerald-50 rounded"><div class="font-bold text-emerald-900">もう少し安くなりますか？</div><div class="text-emerald-700">ボリテ・ナ・カネテ・カリテリ・ティミ；</div></div>
            <div class="p-1.5 bg-emerald-50 rounded"><div class="font-bold text-emerald-900">カードで払えますか？</div><div class="text-emerald-700">ボロー・ナ・プリロソ・メ・カルタ；</div></div>
          </div>
        </div>

        <!-- 道を聞く -->
        <div class="bg-white rounded-xl border border-indigo-200 p-3 space-y-2">
          <h3 class="font-bold text-indigo-800 text-xs border-b border-indigo-100 pb-1">🗺️ 道を聞く・移動</h3>
          <div class="grid grid-cols-1 sm:grid-cols-2 gap-1.5 text-xs">
            <div class="p-1.5 bg-indigo-50 rounded"><div class="font-bold text-indigo-900">〇〇はどこですか？</div><div class="text-indigo-700">プー・ィネ・ト [場所名]；（Πού είναι το ...;）</div></div>
            <div class="p-1.5 bg-indigo-50 rounded"><div class="font-bold text-indigo-900">右 / 左 / 真っ直ぐ</div><div class="text-indigo-700">デクシア / アリステラ / エフティア</div></div>
            <div class="p-1.5 bg-indigo-50 rounded"><div class="font-bold text-indigo-900">イアへのバスは？</div><div class="text-indigo-700">プー・ィネ・ト・レオフォリオ・ギア・ティン・イア；</div></div>
            <div class="p-1.5 bg-indigo-50 rounded"><div class="font-bold text-indigo-900">港まで何分？</div><span class="text-indigo-700">ポサ・レプタ・アポ・エドー・スト・リマニ；</span></div>
          </div>
        </div>
      </div>

      <!-- ドライバー提示カード（拡充版） -->
      <div class="bg-white rounded-2xl shadow-xs border border-slate-200 p-4 sm:p-5 space-y-4">
        <div class="flex items-center space-x-2 border-b border-slate-100 pb-2">
          <i class="fa-solid fa-car text-slate-600 text-lg"></i>
          <h2 class="font-bold text-slate-800 text-sm sm:text-base">🚖 ドライバー提示カード（全宿泊先）</h2>
          <p class="text-xs text-slate-500">タクシー・Uberで画面を見せるだけ</p>
        </div>
        <div class="grid grid-cols-1 sm:grid-cols-2 gap-3 text-xs">
          <div class="p-3 bg-amber-50 border border-amber-200 rounded-xl space-y-1">
            <div class="font-bold text-amber-900">🇪🇬 ギザ（DAY2-4 &amp; DAY5-6）</div>
            <div class="text-right text-sm font-bold leading-relaxed text-amber-800" dir="rtl">فندق تركواز بيراميدز<br>بجوار المتحف المصري الكبير</div>
            <div class="text-amber-700">Turquoise Pyramids Hotel, near GEM</div>
          </div>
          <div class="p-3 bg-amber-50 border border-amber-200 rounded-xl space-y-1">
            <div class="font-bold text-amber-900">🇪🇬 ルクソール（DAY6-8）</div>
            <div class="text-right text-sm font-bold leading-relaxed text-amber-800" dir="rtl">فندق ايبيروتيل لوكسور<br>كورنيش النيل، الأقصر</div>
            <div class="text-amber-700">Iberotel Luxor, Corniche el-Nil</div>
          </div>
          <div class="p-3 bg-amber-50 border border-amber-200 rounded-xl space-y-1">
            <div class="font-bold text-amber-900">🇪🇬 ヘリオポリス/カイロ（DAY8-9）</div>
            <div class="text-right text-sm font-bold leading-relaxed text-amber-800" dir="rtl">أوشن بلو ستوديوز<br>هليوبوليس، القاهرة</div>
            <div class="text-amber-700">Ocean Blue Studios, Heliopolis Cairo</div>
          </div>
          <div class="p-3 bg-sky-50 border border-sky-200 rounded-xl space-y-1">
            <div class="font-bold text-sky-900">🇬🇷 アテネ1泊目（DAY9-10）</div>
            <div class="text-sm font-bold text-sky-800">Galleria Romvis<br>Μοναστηράκι, Αθήνα</div>
            <div class="text-sky-700">Near Monastiraki, Athens</div>
          </div>
          <div class="p-3 bg-sky-50 border border-sky-200 rounded-xl space-y-1">
            <div class="font-bold text-sky-900">🇬🇷 サントリーニ（DAY10-13）</div>
            <div class="text-sm font-bold text-sky-800">Andronikos Canaves<br>Imerovigli, Santorini</div>
            <div class="text-sky-700">Imerovigli Village, Caldera view</div>
          </div>
          <div class="p-3 bg-sky-50 border border-sky-200 rounded-xl space-y-1">
            <div class="font-bold text-sky-900">🇬🇷 アテネ2泊目（DAY13-14）</div>
            <div class="text-sm font-bold text-sky-800">Atelier Apartment<br>Κέντρο Αθήνας</div>
            <div class="text-sky-700">Central Athens Apartment</div>
          </div>
        </div>
      </div>

    </section>"""

html = html[:INSERT_POS] + PHRASES_TAB + html[INSERT_POS:]
print("1b. 会話＆フレーズタブ本体追加 ✓")

# ══════════════════════════════════════════════════════════
# 2. 旅程表：15日間 実用情報テーブル（DAY1の前に挿入）
# ══════════════════════════════════════════════════════════
DAY1_MARKER = "      <!-- DAY 1 -->"
assert DAY1_MARKER in html, "DAY 1マーカーが見つかりません"

DAILY_TABLE = """
      <!-- 15日間 実用情報サマリー -->
      <div class="bg-white rounded-2xl shadow-xs border border-slate-200 p-4 sm:p-5 space-y-3">
        <div class="flex items-center justify-between border-b border-slate-100 pb-2 gap-2 flex-wrap">
          <div class="flex items-center space-x-2">
            <i class="fa-solid fa-coins text-amber-500 text-lg"></i>
            <div>
              <h2 class="font-bold text-slate-800 text-sm sm:text-base">💰 15日間 出費目安・昼食・移動 クイックテーブル</h2>
              <p class="text-xs text-slate-500">2人合計目安。ツアー代別途。レートはEGP≈3.1円、EUR≈163円で試算</p>
            </div>
          </div>
        </div>
        <div class="overflow-x-auto">
          <table class="w-full text-xs border-collapse">
            <thead>
              <tr class="bg-slate-50 text-slate-600">
                <th class="p-1.5 text-center font-bold border-b border-slate-200 whitespace-nowrap">DAY</th>
                <th class="p-1.5 text-left font-bold border-b border-slate-200 whitespace-nowrap">日付・エリア</th>
                <th class="p-1.5 text-left font-bold border-b border-slate-200 whitespace-nowrap">💰 出費目安（2人）</th>
                <th class="p-1.5 text-left font-bold border-b border-slate-200 whitespace-nowrap">🍽️ 昼食候補</th>
                <th class="p-1.5 text-left font-bold border-b border-slate-200 whitespace-nowrap">🚗 移動手段</th>
              </tr>
            </thead>
            <tbody class="divide-y divide-slate-100">
              <tr class="hover:bg-slate-50"><td class="p-1.5 text-center font-bold text-amber-700">1</td><td class="p-1.5 whitespace-nowrap">9/13 機内</td><td class="p-1.5">¥3,000〜5,000（成田飲食）</td><td class="p-1.5">機内食×2回（MS965）</td><td class="p-1.5">成田第1T Lカウンター</td></tr>
              <tr class="hover:bg-slate-50"><td class="p-1.5 text-center font-bold text-amber-700">2</td><td class="p-1.5 whitespace-nowrap">9/14 ギザ</td><td class="p-1.5">GEM 800〜1,200EGP/人＋ビザ25USD/人</td><td class="p-1.5">ホテル内or GEMカフェ（体調優先）</td><td class="p-1.5">空港→Uber 700〜1,000EGP</td></tr>
              <tr class="bg-amber-50/60"><td class="p-1.5 text-center font-bold text-amber-700">3</td><td class="p-1.5 whitespace-nowrap">9/15 ギザ</td><td class="p-1.5">ピラミッド 700EGP/人＋ディナー 2,000〜4,000EGP</td><td class="p-1.5">Khan el-Khalili近く（Felfela等）</td><td class="p-1.5">専用ガイド車（ホテル発着込）</td></tr>
              <tr class="hover:bg-slate-50"><td class="p-1.5 text-center font-bold text-amber-700">4</td><td class="p-1.5 whitespace-nowrap">9/16 白砂漠へ</td><td class="p-1.5">ツアー代込（食事付き）</td><td class="p-1.5">道中オアシス料理（ツアー込）</td><td class="p-1.5">4WD専用車（ギザ→バハレイヤ4h）</td></tr>
              <tr class="bg-indigo-50/60"><td class="p-1.5 text-center font-bold text-amber-700">5</td><td class="p-1.5 whitespace-nowrap">9/17 白砂漠</td><td class="p-1.5">ツアー代込（全食事付き）</td><td class="p-1.5">キャンプ料理（ベドウィン伝統食）</td><td class="p-1.5">4WD砂漠内移動（ツアー込）</td></tr>
              <tr class="hover:bg-slate-50"><td class="p-1.5 text-center font-bold text-amber-700">6</td><td class="p-1.5 whitespace-nowrap">9/18 ルクソール</td><td class="p-1.5">国内線込＋ルクソール神殿 350EGP/人</td><td class="p-1.5">Sofra Restaurant（ナイル沿い）600EGP</td><td class="p-1.5">空港→Uber/タクシー 200EGP</td></tr>
              <tr class="hover:bg-slate-50"><td class="p-1.5 text-center font-bold text-amber-700">7</td><td class="p-1.5 whitespace-nowrap">9/19 ルクソール</td><td class="p-1.5">王家の谷 600EGP/人＋カルナック 400EGP/人</td><td class="p-1.5">Al-Sahaby Lane（東岸・ローカル）500EGP</td><td class="p-1.5">フェリー20EGP×2＋タクシー 400EGP</td></tr>
              <tr class="hover:bg-slate-50"><td class="p-1.5 text-center font-bold text-amber-700">8</td><td class="p-1.5 whitespace-nowrap">9/20 ルクソール→カイロ</td><td class="p-1.5">ファルーカ 400EGP＋空港移動 300EGP</td><td class="p-1.5">ホテル近くカフェ or 神殿前（500EGP）</td><td class="p-1.5">徒歩→タクシー→ルクソール空港</td></tr>
              <tr class="bg-sky-50/60"><td class="p-1.5 text-center font-bold text-sky-700">9</td><td class="p-1.5 whitespace-nowrap">9/21 アテネ</td><td class="p-1.5">Metro 9€/人＋食事 40〜60€</td><td class="p-1.5">プラカ地区（To Kafeneio等）30〜40€</td><td class="p-1.5">空港Metro 9€/人 or バスX95 5€/人</td></tr>
              <tr class="hover:bg-sky-50"><td class="p-1.5 text-center font-bold text-sky-700">10</td><td class="p-1.5 whitespace-nowrap">9/22 アテネ→サントリーニ</td><td class="p-1.5">アクロポリス 20€/人＋食事 40〜60€</td><td class="p-1.5">プラカ（Scholarhis等）35〜50€</td><td class="p-1.5">Metro→空港→サントリーニ空港送迎</td></tr>
              <tr class="bg-rose-50/70"><td class="p-1.5 text-center font-bold text-sky-700">11</td><td class="p-1.5 whitespace-nowrap">9/23 サントリーニ💍</td><td class="p-1.5">カメラマンチップ20〜30€＋食事 60〜80€</td><td class="p-1.5">Oia「Lithos」or「Pitogyros」35〜50€</td><td class="p-1.5">バスKTEL 3€/人 or タクシー 20€</td></tr>
              <tr class="bg-amber-50/60"><td class="p-1.5 text-center font-bold text-sky-700">12</td><td class="p-1.5 whitespace-nowrap">9/24 サントリーニ🎂</td><td class="p-1.5">記念日ディナー 150〜300€＋観光 50€</td><td class="p-1.5">フィラ「Aktaion」or「Roka」30〜40€</td><td class="p-1.5">バスorバイクレンタル 30€/日</td></tr>
              <tr class="hover:bg-sky-50"><td class="p-1.5 text-center font-bold text-sky-700">13</td><td class="p-1.5 whitespace-nowrap">9/25 サントリーニ→アテネ</td><td class="p-1.5">移動＋夕食 60〜80€</td><td class="p-1.5">フィラで軽く（Argo等）15〜25€</td><td class="p-1.5">空港→アテネ Metro 9€/人</td></tr>
              <tr class="hover:bg-slate-50"><td class="p-1.5 text-center font-bold text-sky-700">14</td><td class="p-1.5 whitespace-nowrap">9/26 アテネ→帰路</td><td class="p-1.5">空港食事 20〜30€＋Tax Refund手続き</td><td class="p-1.5">アテネ空港内レストラン（20〜30€）</td><td class="p-1.5">タクシー50〜60€→空港HO1658便</td></tr>
              <tr class="hover:bg-slate-50"><td class="p-1.5 text-center font-bold text-slate-500">15</td><td class="p-1.5 whitespace-nowrap">9/27 成田着</td><td class="p-1.5">帰宅交通費のみ</td><td class="p-1.5">機内食（HO1658便）</td><td class="p-1.5">成田第1T着→電車/リムジン</td></tr>
            </tbody>
          </table>
        </div>
        <div class="p-2 bg-amber-50 rounded-lg border border-amber-200 text-[11px] text-amber-800">
          ⚠️ <strong>注意：</strong> EGP・EURは概算。ツアー代・ガイド代・入場料セット購入は別途。チップは安心ガイドタブのチップ相場表を参照。
        </div>
      </div>

"""

html = html.replace(DAY1_MARKER, DAILY_TABLE + DAY1_MARKER, 1)
print("2. 旅程表：出費/昼食/移動テーブル追加 ✓")

# ══════════════════════════════════════════════════════════
# 3. お土産タブ：価格帯・真贋チェックガイド
# ══════════════════════════════════════════════════════════
SOUVENIR_END = '    </section>\n\n    <!-- ==================== TAB 4: 歴史'
assert SOUVENIR_END in html, "お土産タブ終端マーカーが見つかりません"

SOUVENIR_INSERT = """
      <!-- 価格帯・真贋チェックガイド -->
      <div class="bg-white rounded-2xl shadow-xs border border-slate-200 p-4 sm:p-5 space-y-4">
        <div class="flex items-center space-x-2 border-b border-slate-100 pb-2">
          <i class="fa-solid fa-magnifying-glass text-orange-500 text-lg"></i>
          <div>
            <h2 class="font-bold text-slate-800 text-sm sm:text-base">🔍 本物 vs 偽物チェック＋適正価格帯ガイド</h2>
            <p class="text-xs text-slate-500">スークで迷わないための真贋ポイントと価格の目安（2026年概算）</p>
          </div>
        </div>
        <div class="grid grid-cols-1 sm:grid-cols-2 gap-3 text-xs text-slate-700 leading-relaxed">

          <div class="p-3 bg-amber-50 rounded-xl border border-amber-200 space-y-2">
            <strong class="text-amber-900 block">📜 パピルス（エジプト）</strong>
            <p>🔑 <strong>本物の見分け方：</strong> 端を曲げてもひびが入らずしなやか。水で濡らすと柔らかくなり乾くと元に戻る（バナナの葉や葦で作った「偽パピルス」は硬くパリパリになる）。</p>
            <p>💰 <strong>適正価格：</strong> A4程度の絵柄付きで 500〜2,000EGP（約1,500〜6,200円）。「10ドルで売る」は偽物確定。</p>
            <p>📍 <strong>推奨購入先：</strong> Khan el-Khalili内の老舗パピルス専門店、またはルクソールのアンティーク系ショップ。</p>
          </div>

          <div class="p-3 bg-amber-50 rounded-xl border border-amber-200 space-y-2">
            <strong class="text-amber-900 block">🧴 香水瓶（エジプト）</strong>
            <p>🔑 <strong>本物の見分け方：</strong> 手吹きガラス製は継ぎ目がなく、厚みが均一でない。金彩は手描きで多少のムラがある。机に置いたとき均等に立つかも確認。</p>
            <p>💰 <strong>適正価格：</strong> 小瓶（5cm）で 200〜500EGP、中瓶で 400〜800EGP。エジプト香水（ローズ・ジャスミン等）もセット購入で値引き可。</p>
            <p>⚠️ <strong>注意：</strong> 「空港では買えない」「ここだけの価格」はセールストーク。笑顔でスルーしてOK。</p>
          </div>

          <div class="p-3 bg-amber-50 rounded-xl border border-amber-200 space-y-2">
            <strong class="text-amber-900 block">🌸 カルカデ・スパイス（エジプト）</strong>
            <p>🔑 <strong>品質の見分け方：</strong> カルカデ（ハイビスカスティー）は花びらが丸ごと入っているものが最高品質。粉末状や細かく砕けているものは等級が低い。</p>
            <p>💰 <strong>適正価格：</strong> 250g 150〜300EGP。スパイスミックス（クミン・コリアンダー等）は小袋50〜100EGP。「密封パック済み」のものを選ぶ（スーク内の量り売りは水分や不純物混入リスク）。</p>
          </div>

          <div class="p-3 bg-amber-50 rounded-xl border border-amber-200 space-y-2">
            <strong class="text-amber-900 block">📿 Evil Eyeアクセサリー・陶器（ギリシャ）</strong>
            <p>🔑 <strong>手工芸品の見分け方：</strong> 「Made in Greece」のラベルより職人作のものはわずかに左右非対称。量産品はプラスチック製でも「ガラス」と表示することがある（持つと軽い）。</p>
            <p>💰 <strong>適正価格：</strong> Evil Eyeチャーム（ガラス）3〜10€、陶器（小皿・マグ）5〜20€、ハンドペイント陶器15〜50€。観光地の土産店は定価制が多い（値切り文化は薄い）。</p>
            <p>📍 <strong>推奨購入先：</strong> アテネのモナスティラキ蚤の市（日曜開催）、プラカ地区のセラミック専門店。</p>
          </div>

          <div class="p-3 bg-sky-50 rounded-xl border border-sky-200 space-y-2 sm:col-span-2">
            <strong class="text-sky-900 block">🫒 ギリシャ産オリーブオイル・ハチミツ（液体物注意）</strong>
            <p>🔑 <strong>品質の見分け方：</strong> エクストラバージン（Extra Virgin）表示＋「Protected Designation of Origin（PDO）」マーク付きが最高品質保証。カラマタ産・クレタ産が有名産地。</p>
            <p>💰 <strong>適正価格：</strong> 250ml瓶 4〜8€、500ml缶 8〜15€。スーパー（AB Vassilopoulos・Sklavenitis）での購入が最安値。ハチミツはタイム蜂蜜（θυμαρίσιο）500g 8〜15€。</p>
            <p>✈️ <strong>機内持込注意：</strong> 液体物は100ml以下のみ機内持込可。100ml超は必ずスーツケース（受託荷物）に入れること。割れ防止のため厚手のビニール袋に二重包装推奨。</p>
          </div>

        </div>
      </div>

"""
html = html.replace(SOUVENIR_END, SOUVENIR_INSERT + SOUVENIR_END, 1)
print("3. お土産タブ：真贋・価格ガイド追加 ✓")

# ══════════════════════════════════════════════════════════
# 4. エリア・宿タブ：ホテル実用Tips
# ══════════════════════════════════════════════════════════
SPOTS_END = '    </section>\n\n    <!-- ==================== TAB 3: お土産'
assert SPOTS_END in html, "エリアタブ終端マーカーが見つかりません"

HOTEL_TIPS = """
      <!-- ホテル実用Tips -->
      <div class="bg-white rounded-2xl shadow-xs border border-slate-200 p-4 sm:p-5 space-y-4">
        <div class="flex items-center space-x-2 border-b border-slate-100 pb-2">
          <i class="fa-solid fa-bell-concierge text-amber-500 text-lg"></i>
          <div>
            <h2 class="font-bold text-slate-800 text-sm sm:text-base">🔔 ホテル別 チェックイン時リクエスト＆実用Tips</h2>
            <p class="text-xs text-slate-500">一言伝えるだけで滞在クオリティが格段に上がる</p>
          </div>
        </div>
        <div class="grid grid-cols-1 sm:grid-cols-2 gap-3 text-xs text-slate-700 leading-relaxed">

          <div class="p-3 bg-amber-50 rounded-xl border border-amber-200 space-y-1.5">
            <div class="font-bold text-amber-900">🏨 Turquoise Pyramids（ギザ・DAY2〜6）</div>
            <p>📍 チェックイン時リクエスト：「屋上テラスからピラミッドが正面に見える高層階の部屋をお願いします」<br><span class="text-amber-700 font-mono text-[11px]">Can we have a room with a pyramid view on a higher floor?</span></p>
            <p>🧳 <strong>白砂漠前荷物預かり：</strong> DAY4出発時にスーツケース2個をフロントに預ける（1泊分リュックのみで出発）。事前にフロントへ一言伝えておく。</p>
            <p>🌙 <strong>屋上バー：</strong> 夜のピラミッドライトアップ（20〜23時）が屋上テラスから見える。ディナー前後の絶景狙い。</p>
          </div>

          <div class="p-3 bg-amber-50 rounded-xl border border-amber-200 space-y-1.5">
            <div class="font-bold text-amber-900">⛺ 白砂漠キャンプ（DAY4〜5）</div>
            <p>🥛 <strong>食事の乳製品アレルギー：</strong> ツアー会社への予約確認時に「乳製品（牛乳・チーズ・バター・ヨーグルト）なしの食事をお願いします」と事前メール送信。<br><span class="text-amber-700 font-mono text-[11px]">Please prepare dairy-free meals for us.</span></p>
            <p>🌙 <strong>星空観察：</strong> ガイドに「星空（star gazing）の時間を取ってほしい」と伝えると、消灯後に最高ロケーションへ案内してくれる。</p>
            <p>🔦 <strong>持参必須：</strong> ヘッドライト・防寒着（夜は15℃以下）・耳栓（砂の音）。</p>
          </div>

          <div class="p-3 bg-amber-50 rounded-xl border border-amber-200 space-y-1.5">
            <div class="font-bold text-amber-900">🏨 Iberotel Luxor（ルクソール・DAY6〜8）</div>
            <p>📍 チェックイン時リクエスト：「ナイル川側の部屋をお願いします」<br><span class="text-amber-700 font-mono text-[11px]">We'd love a Nile-facing room, please.</span></p>
            <p>🍳 <strong>朝食は6:30から：</strong> カルナック神殿は7〜9時が斜光で美しい。朝食を早めに終え7:30到着を目標に。</p>
            <p>♨️ <strong>プール：</strong> ナイル川に浮かぶ温水プールが名物。観光後の夕方利用が◎（夜は虫が増えるため注意）。</p>
          </div>

          <div class="p-3 bg-amber-50 rounded-xl border border-amber-200 space-y-1.5">
            <div class="font-bold text-amber-900">🏨 Ocean Blue Studios（ヘリオポリス・DAY8〜9）</div>
            <p>📍 <strong>役割：</strong> 翌朝10:10発アテネ便のための前泊。空港から車10分の好立地。</p>
            <p>⏰ <strong>翌日早朝：</strong> チェックアウト7:30目標（フライト10:10のため）。モーニングコールをフロントに依頼。</p>
            <p>🛒 <strong>周辺：</strong> 近くにスーパー（Carrefour等）あり。帰国前に足りない日用品・薬・お菓子の補充ができる最後のチャンス。</p>
          </div>

          <div class="p-3 bg-sky-50 rounded-xl border border-sky-200 space-y-1.5">
            <div class="font-bold text-sky-900">🏨 Galleria Romvis（アテネ1泊目・DAY9〜10）</div>
            <p>📍 <strong>ロケーション：</strong> モナスティラキ・プラカ地区から徒歩圏内。アクロポリスへも徒歩15分。</p>
            <p>☕ <strong>朝食：</strong> ホテル周辺にギリシャコーヒーのカフェが多数。「フラッペ（Frappe）」はギリシャ発祥のアイスインスタントコーヒー。</p>
            <p>🗺️ <strong>翌日の動き：</strong> アクロポリスは8時開館（到着が早いほど人が少ない）。前日にGoogleマップでルートを確認しておく。</p>
          </div>

          <div class="p-3 bg-sky-50 rounded-xl border border-sky-200 space-y-1.5">
            <div class="font-bold text-sky-900">🌊 Andronikos Canaves（サントリーニ・DAY10〜13）</div>
            <p>📍 チェックイン時リクエスト：「カルデラ（火口）が正面に見えるお部屋とジャグジー付きテラスをお願いします」<br><span class="text-sky-700 font-mono text-[11px]">We'd love a caldera-view room with a private jacuzzi.</span></p>
            <p>💌 <strong>ハネムーン特典：</strong> 予約確認メールに「Honeymoon」と記載があれば、到着時にウェルカムシャンパンや花びらサービスがある場合が多い。チェックイン時に「ハネムーンです」と一声。</p>
            <p>🍽️ <strong>記念日ディナー予約：</strong> ホテルへ「9/24のディナーはThe Athenian Houseにカルデラビューの席を取ってほしい」と到着時に相談。コンシェルジュが対応可。</p>
          </div>

        </div>
      </div>

"""
html = html.replace(SPOTS_END, HOTEL_TIPS + SPOTS_END, 1)
print("4. エリアタブ：ホテル実用Tips追加 ✓")

# ══════════════════════════════════════════════════════════
# 5. 歴史タブ：スポット別「見どころ3点＋推奨所要時間」
# ══════════════════════════════════════════════════════════
HISTORY_END = '    </section>\n\n    <!-- ==================== TAB 5: フォト'
assert HISTORY_END in html, "歴史タブ終端マーカーが見つかりません"

SPOT_GUIDE = """
      <!-- スポット別 現地活用ガイド -->
      <div class="bg-white rounded-2xl shadow-xs border border-slate-200 p-4 sm:p-5 space-y-4">
        <div class="flex items-center space-x-2 border-b border-slate-100 pb-3">
          <i class="fa-solid fa-map-pin text-rose-500 text-lg"></i>
          <div>
            <h2 class="font-bold text-slate-800 text-sm sm:text-base">📍 スポット別 現地攻略ガイド（見どころ3点＋推奨所要時間）</h2>
            <p class="text-xs text-slate-500">現地で「ここだけは外さない」をまとめたクイックリファレンス</p>
          </div>
        </div>
        <div class="grid grid-cols-1 sm:grid-cols-2 gap-3 text-xs text-slate-700 leading-relaxed">

          <div class="p-3 bg-amber-50 rounded-xl border border-amber-200 space-y-2">
            <div class="flex justify-between items-start"><strong class="text-amber-900">🟡 ギザ三大ピラミッド＆スフィンクス</strong><span class="shrink-0 bg-amber-200 text-amber-900 px-1.5 py-0.5 rounded text-[10px] font-bold ml-2">推奨3〜4h</span></div>
            <p>① <strong>クフ王大ピラミッド内部（大回廊）：</strong> 傾斜60°の1m幅の廊下を腰をかがめながら登る体験。息切れ注意。入場は別料金（500EGP/人）・事前チケット推奨。</p>
            <p>② <strong>カフラー王ピラミッドのパノラマポイント：</strong> 3基すべてが一直線に並ぶ撮影スポット。東側・砂漠側からのアングルが王道。ガイドに「パノラマビュー」と伝える。</p>
            <p>③ <strong>スフィンクスを鼻の高さで見る：</strong> 河岸神殿から進むとスフィンクスの顔と目線が合う角度がある。人が少ない早朝（8時前）が◎。</p>
            <div class="text-amber-700 font-bold text-[11px]">⚠️ 炎天下注意。帽子・水必携。ラクダ乗りは価格を先に書面確認してから。</div>
          </div>

          <div class="p-3 bg-amber-50 rounded-xl border border-amber-200 space-y-2">
            <div class="flex justify-between items-start"><strong class="text-amber-900">🟡 大エジプト博物館（GEM）</strong><span class="shrink-0 bg-amber-200 text-amber-900 px-1.5 py-0.5 rounded text-[10px] font-bold ml-2">推奨2〜3h</span></div>
            <p>① <strong>大階段のラムセス2世巨像（高さ11m）：</strong> エントランスホールで迎える巨大彫刻。世界最大の博物館エントランスとして圧巻。必ず見上げて撮影を。</p>
            <p>② <strong>ツタンカーメン展示室：</strong> 黄金のマスクは必見。棺・ネックレス・椅子など5,000点超が一堂に。混雑前（開館直後）が空いている。</p>
            <p>③ <strong>太陽の船（Khufu's Boat）：</strong> 4,500年前の実物大木造船。43mのスケールに圧倒される。2F特別エリアで保存展示。</p>
            <div class="text-amber-700 font-bold text-[11px]">入場料2,000EGP/人以上（2026概算）。カメラ持込料が別途かかる場合あり。荷物検査あり。</div>
          </div>

          <div class="p-3 bg-amber-50 rounded-xl border border-amber-200 space-y-2">
            <div class="flex justify-between items-start"><strong class="text-amber-900">🟡 サッカラ（階段ピラミッド）</strong><span class="shrink-0 bg-amber-200 text-amber-900 px-1.5 py-0.5 rounded text-[10px] font-bold ml-2">推奨1.5〜2h</span></div>
            <p>① <strong>ジェセル王の階段ピラミッド：</strong> 世界最古のピラミッド（紀元前2650年）。ギザより1段荒削りで「進化の途中」の迫力がある。</p>
            <p>② <strong>セラペウム（地下牛神墓）：</strong> 地下に続く巨石の廊下に重さ70トンの花崗岩棺が並ぶ。自然に冷えていて涼しい（夏場の休憩地点にも）。</p>
            <p>③ <strong>メレルカのマスタバ（貴族墓）：</strong> 内壁の彩色レリーフが驚くほど鮮明。魚・鳥・農民の日常が3,400年前のまま残る。</p>
            <div class="text-amber-700 font-bold text-[11px]">ギザから専用車で45分。別敷地のため入場料が別（150〜200EGP/人）。</div>
          </div>

          <div class="p-3 bg-amber-50 rounded-xl border border-amber-200 space-y-2">
            <div class="flex justify-between items-start"><strong class="text-amber-900">🟡 カルナック神殿（ルクソール）</strong><span class="shrink-0 bg-amber-200 text-amber-900 px-1.5 py-0.5 rounded text-[10px] font-bold ml-2">推奨2〜2.5h</span></div>
            <p>① <strong>134本の大列柱室（ヒュポスタイルホール）：</strong> 世界最大の宗教建築の一部。朝7〜9時に西から差し込む斜光がオレンジに染まり圧巻。この時間帯に来ることが最重要。</p>
            <p>② <strong>スフィンクス参道（人頭羊身）：</strong> 神殿入口から続く羊頭スフィンクスの列。ルクソール神殿とカルナックをつなぐ2.7kmの参道の一部。</p>
            <p>③ <strong>聖なる池（Sacred Lake）：</strong> 神殿中央の池で神官が浄めを行った場所。周囲に日陰があり休憩ポイントにもなる。</p>
            <div class="text-amber-700 font-bold text-[11px]">入場料400EGP/人（2026概算）。夜のサウンド＆ライトショー（別料金）も幻想的。</div>
          </div>

          <div class="p-3 bg-amber-50 rounded-xl border border-amber-200 space-y-2">
            <div class="flex justify-between items-start"><strong class="text-amber-900">🟡 王家の谷＆ハトシェプスト女王神殿</strong><span class="shrink-0 bg-amber-200 text-amber-900 px-1.5 py-0.5 rounded text-[10px] font-bold ml-2">推奨2〜3h</span></div>
            <p>① <strong>ツタンカーメン王墓（KV62）：</strong> 発掘当時のほぼ原形。黄金の棺の内側に眠るミイラが今もそこにある。ミイラ見学は追加料金（300EGP）だが、一生に一度の体験。</p>
            <p>② <strong>セティ1世墓（KV17）：</strong> 王家の谷で最長（全長136m）・最美の彩色壁画を持つ墓。追加チケット（1,000EGP）が必要だが芸術的価値は最高。</p>
            <p>③ <strong>ハトシェプスト女王葬祭殿：</strong> 断崖を背にした3段テラス式の白い神殿。「女性ファラオ」の波乱の生涯を感じながら鑑賞。</p>
            <div class="text-amber-700 font-bold text-[11px]">基本チケット（墓3基込）600EGP/人。電気カートで墓まで移動（30EGP/人）。炎天下注意。</div>
          </div>

          <div class="p-3 bg-sky-50 rounded-xl border border-sky-200 space-y-2">
            <div class="flex justify-between items-start"><strong class="text-sky-900">🔵 アクロポリス＆パルテノン神殿</strong><span class="shrink-0 bg-sky-200 text-sky-900 px-1.5 py-0.5 rounded text-[10px] font-bold ml-2">推奨1.5〜2h</span></div>
            <p>① <strong>パルテノン神殿（东面）：</strong> 完成当時は全面彩色で赤・青・金色に輝いていた。現在の白さは「経年変化後の姿」。東ファサードが最も完全に残っている。</p>
            <p>② <strong>エレクテイオンのカリアティード：</strong> 女神像の柱（コレー）が屋根を支える独特の建築。実物は博物館に移管され、ここにあるのはレプリカ（本物は下のアクロポリス博物館に）。</p>
            <p>③ <strong>丘頂からのアテネ360度パノラマ：</strong> リカヴィトスの丘、アゴラ、サロニコス湾まで見渡せる。朝8時の開館直後が最も空いている。</p>
            <div class="text-sky-700 font-bold text-[11px]">入場20€/人（5日間コンバインドチケット30€でアテネ5スポット巡りがおトク）。</div>
          </div>

          <div class="p-3 bg-sky-50 rounded-xl border border-sky-200 space-y-2 sm:col-span-2">
            <div class="flex justify-between items-start"><strong class="text-sky-900">🔵 アクロポリス博物館</strong><span class="shrink-0 bg-sky-200 text-sky-900 px-1.5 py-0.5 rounded text-[10px] font-bold ml-2">推奨1〜1.5h</span></div>
            <p>① <strong>カリアティードの実物5体：</strong> エレクテイオンから移された女神像柱の「本物」。劣化保護のため博物館内で保存。ロンドン大英博物館が持つ1体だけが空白になっている（政治問題）。</p>
            <p>② <strong>パルテノン・ギャラリー（最上階）：</strong> 神殿と同じ方向・縮尺で展示されたフリーズ（彫刻帯）。東・西・南・北の4面を一周できる。館外のパルテノン神殿を見ながら照らし合わせると理解が深まる。</p>
            <p>③ <strong>ガラス越しの発掘現場：</strong> 博物館の床がガラス張りで、紀元前5世紀の古代アテネの路地・建物基礎がそのまま見える。現代のビルを建設中に遺跡が出てきたため博物館がその上に建てられた経緯がある。</p>
            <div class="text-sky-700 font-bold text-[11px]">入場12€/人（コンバインドチケット利用でアクロポリスと共通）。月曜休館なし。カフェテリアからのアクロポリス眺望も◎。</div>
          </div>

        </div>
      </div>

"""
html = html.replace(HISTORY_END, SPOT_GUIDE + HISTORY_END, 1)
print("5. 歴史タブ：スポット別見どころガイド追加 ✓")

# ══════════════════════════════════════════════════════════
# 6. フォトタブ：ブライダルフォト ロケーション名拡充
#    既存シートの「当日タイムライン」カードの後に挿入
# ══════════════════════════════════════════════════════════
BRIDAL_ANCHOR = "翌朝の予定を開けておくこと。</p>\n          </div>"
assert BRIDAL_ANCHOR in html, "ブライダルフォトシートアンカーが見つかりません"

LOCATION_BLOCK = """
          <div class="mt-2 p-2 bg-rose-50 border border-rose-200 rounded-lg space-y-1">
            <strong class="text-rose-900 text-[11px] block">📍 Oia撮影推奨ロケーション（カメラマンへ伝達）</strong>
            <p class="text-[11px] text-rose-800">1. <strong>Oia Castle（ヴェネチア要塞跡）</strong>: 断崖に建つ廃墟と海が重なるダイナミックショット（人気スポット・早朝推奨）</p>
            <p class="text-[11px] text-rose-800">2. <strong>Oia Main Lane（イア村メイン路地）</strong>: 早朝7:30なら観光客ゼロ。白壁・青ドア・花の路地を独占できる。</p>
            <p class="text-[11px] text-rose-800">3. <strong>Anastasis Church（アナスタシス教会・イメロヴィグリ）</strong>: ホテル徒歩5分。小さな白い礼拝堂とカルデラのクラシックショット。</p>
            <p class="text-[11px] text-rose-800">4. <strong>Ammoudi Bay（アモウディ湾）</strong>: イアから急な石段を300段下る。海と白壁・赤い岩のコントラストが唯一無二（体力注意）。</p>
          </div>"""

html = html.replace(BRIDAL_ANCHOR, BRIDAL_ANCHOR + LOCATION_BLOCK, 1)
print("6. フォトタブ：ブライダルロケーション名追加 ✓")

# ══════════════════════════════════════════════════════════
# 7. 服装タブ：スーツケース重量配分シート
# ══════════════════════════════════════════════════════════
PACKING_END = '    </section>\n\n    <!-- ==================== TAB 8: 安心'
assert PACKING_END in html, "服装タブ終端マーカーが見つかりません"

WEIGHT_SHEET = """
      <!-- スーツケース重量配分シート -->
      <div class="bg-white rounded-2xl shadow-xs border border-slate-200 p-4 sm:p-5 space-y-4">
        <div class="flex items-center space-x-2 border-b border-slate-100 pb-2">
          <i class="fa-solid fa-weight-hanging text-slate-600 text-lg"></i>
          <div>
            <h2 class="font-bold text-slate-800 text-sm sm:text-base">⚖️ スーツケース重量配分シート</h2>
            <p class="text-xs text-slate-500">3フェーズの体重変化を先読みして過積載を防ぐ</p>
          </div>
        </div>

        <div class="grid grid-cols-1 sm:grid-cols-3 gap-3 text-xs text-slate-700">
          <div class="p-3 bg-green-50 rounded-xl border border-green-200 space-y-1.5">
            <div class="font-bold text-green-900 border-b border-green-200 pb-1">🟢 行き（成田出発）</div>
            <p>受託スーツケース：23kg上限×2個（46kg）</p>
            <p>機内持込：10kg上限×2個（20kg）</p>
            <p class="text-green-700 font-bold">目標：各スーツケース18〜19kgで出発<br>→ 帰りのお土産分4〜5kgを余裕として確保</p>
            <div class="mt-1 p-1.5 bg-white rounded border border-green-200 text-[11px]">
              機内持込に入れるもの（重量管理）：<br>カメラ3台体制一式（約5kg）、PC・モバイルバッテリー（約2kg）、機内用衣類（約1kg）
            </div>
          </div>

          <div class="p-3 bg-amber-50 rounded-xl border border-amber-200 space-y-1.5">
            <div class="font-bold text-amber-900 border-b border-amber-200 pb-1">🟡 エジプト→ギリシャ乗り継ぎ</div>
            <p>ギザ→白砂漠：スーツケース2個をTurquoise Pyramidsに預ける。リュック1個で軽量参加。</p>
            <p>白砂漠→ルクソール：スーツケース回収後ルクソールへ。</p>
            <p>カイロ→アテネ：手荷物規定を確認（エジプト航空国内線は23kg×1が多い）。</p>
            <div class="mt-1 p-1.5 bg-white rounded border border-amber-200 text-[11px] text-amber-800">
              ⚠️ 国内線（カイロ↔ルクソール）は機材が小さく手荷物規制が厳しい。カメラバッグ（手荷物）のサイズを事前確認。
            </div>
          </div>

          <div class="p-3 bg-rose-50 rounded-xl border border-rose-200 space-y-1.5">
            <div class="font-bold text-rose-900 border-b border-rose-200 pb-1">🔴 帰り（アテネ発・お土産込み）</div>
            <p>見込み増量：お土産5〜10kg（オリーブオイル・陶器・パピルス等）</p>
            <p>分散策：2個のスーツケースにバランス良く分ける</p>
            <p>液体物（オリーブオイル等）は受託のみ：機内持込不可（100ml超）</p>
            <div class="mt-1 p-1.5 bg-white rounded border border-rose-200 text-[11px] text-rose-800">
              ⚠️ アテネ空港のセキュリティは厳格。液体物・刃物類は必ず受託荷物に。大きなお土産品はしっかりバブルラップで保護。
            </div>
            <p class="text-rose-700 font-bold text-[11px] mt-1">超過料金目安：HO便 超過1kgあたり約4,000〜6,000円。気をつけて！</p>
          </div>
        </div>

        <div class="overflow-x-auto">
          <table class="w-full text-xs border-collapse mt-1">
            <thead>
              <tr class="bg-slate-50 text-slate-600">
                <th class="p-1.5 text-left font-bold border-b border-slate-200">カテゴリ</th>
                <th class="p-1.5 text-center font-bold border-b border-slate-200">推定重量</th>
                <th class="p-1.5 text-left font-bold border-b border-slate-200">収納先（受託 or 機内）</th>
                <th class="p-1.5 text-left font-bold border-b border-slate-200">備考</th>
              </tr>
            </thead>
            <tbody class="divide-y divide-slate-100">
              <tr><td class="p-1.5">衣類15日分（2人）</td><td class="p-1.5 text-center">10〜14kg</td><td class="p-1.5">受託スーツケース</td><td class="p-1.5">薄手・速乾素材で軽量化</td></tr>
              <tr class="bg-slate-50"><td class="p-1.5">カメラ3台＋レンズ＋三脚</td><td class="p-1.5 text-center">4〜6kg</td><td class="p-1.5">機内持込（必須）</td><td class="p-1.5">衝撃・気温変化リスクで受託NG</td></tr>
              <tr><td class="p-1.5">PC・モバイルバッテリー等</td><td class="p-1.5 text-center">2〜3kg</td><td class="p-1.5">機内持込（必須）</td><td class="p-1.5">リチウム電池は受託不可</td></tr>
              <tr class="bg-slate-50"><td class="p-1.5">シューズ（2〜3足）</td><td class="p-1.5 text-center">2〜3kg</td><td class="p-1.5">受託スーツケース</td><td class="p-1.5">スーツケースの隙間に詰める</td></tr>
              <tr><td class="p-1.5">お土産（帰り）</td><td class="p-1.5 text-center">5〜10kg</td><td class="p-1.5">受託スーツケース</td><td class="p-1.5">行きに余裕を持たせておく</td></tr>
              <tr class="bg-amber-50 font-bold"><td class="p-1.5">合計（受託2個目標）</td><td class="p-1.5 text-center">行き 36〜38kg<br>帰り 40〜44kg</td><td class="p-1.5">上限46kg以内を維持</td><td class="p-1.5">余裕が4〜6kgあると安心</td></tr>
            </tbody>
          </table>
        </div>
      </div>

"""
html = html.replace(PACKING_END, WEIGHT_SHEET + PACKING_END, 1)
print("7. 服装タブ：重量配分シート追加 ✓")

# ══════════════════════════════════════════════════════════
# 出力
# ══════════════════════════════════════════════════════════
OUTPUT.write_text(html, encoding="utf-8")
size = OUTPUT.stat().st_size
print(f"\n=== 完了 ===")
print(f"出力: {OUTPUT.name}")
print(f"ファイルサイズ: {size:,} bytes ({size/1024/1024:.2f} MB)")
