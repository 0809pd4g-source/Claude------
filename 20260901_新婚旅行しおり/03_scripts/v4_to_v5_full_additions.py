#!/usr/bin/env python3
"""
v4_to_v5_full_additions.py  ─  v4 → v5 全提案コンテンツ追加

追加内容:
  [ヘッダー]    出発カウントダウンバッジ
  [旅程表タブ]  日没・日の出カレンダー（15日分）＆ 記念日ハイライトカード
  [フォトタブ]  ブライダルフォト当日シート
  [歴史タブ]   旅のBGMプレイリスト提案
  [服装タブ]   現地調達OK vs 日本から必携リスト
  [TIPSタブ]   乳製品NG地雷メニュー / Googleマップオフライン /
               貴重品仕分け / 医療・保険 / 免税（Tax Refund）ガイド
"""

from pathlib import Path

BASE   = Path(__file__).parent.parent / "02_output"
INPUT  = BASE / "20260901_新婚旅行しおり_v4.html"
OUTPUT = BASE / "20260901_新婚旅行しおり_v5.html"

html = INPUT.read_text(encoding="utf-8")
print(f"読み込み完了: {len(html):,} chars\n")

# ══════════════════════════════════════════════════════════
# 1. ヘッダー：出発カウントダウンバッジ
# ══════════════════════════════════════════════════════════
BADGE_ANCHOR = '<span class="bg-amber-600/80 text-white px-1.5 py-0.5 rounded text-[10px] font-bold">15日間</span>'
BADGE_INSERT = ' <span id="countdown-badge" class="bg-rose-600 text-white px-1.5 py-0.5 rounded text-[10px] font-bold tabular-nums">--</span>'
assert BADGE_ANCHOR in html, "カウントダウンバッジ挿入点が見つかりません"
html = html.replace(BADGE_ANCHOR, BADGE_ANCHOR + BADGE_INSERT, 1)
print("1. ヘッダーカウントダウンバッジ挿入 ✓")

# ══════════════════════════════════════════════════════════
# 2. カウントダウン JS（既存DOMContentLoadedブロック内に追記）
# ══════════════════════════════════════════════════════════
JS_ANCHOR = "      setInterval(updateClocks, 1000);\n      updateClocks();"
JS_INSERT = """
      // カウントダウン（出発まで / 旅行中DAY / 帰国後）
      function updateCountdown() {
        var dep = new Date('2026-09-13T17:30:00+09:00');
        var ret = new Date('2026-09-27T12:05:00+09:00');
        var now = new Date();
        var el = document.getElementById('countdown-badge');
        if (!el) return;
        if (now < dep) {
          var diff = dep - now;
          var d = Math.floor(diff / 86400000);
          var h = Math.floor((diff % 86400000) / 3600000);
          el.textContent = 'あと' + d + '日' + h + 'h';
          el.className = 'bg-rose-600 text-white px-1.5 py-0.5 rounded text-[10px] font-bold tabular-nums';
        } else if (now <= ret) {
          var dayN = Math.floor((now - dep) / 86400000) + 1;
          el.textContent = '旅行中 DAY' + Math.min(dayN, 15) + '!';
          el.className = 'bg-emerald-600 text-white px-1.5 py-0.5 rounded text-[10px] font-bold animate-pulse';
        } else {
          el.textContent = '♡ 思い出';
          el.className = 'bg-rose-400 text-white px-1.5 py-0.5 rounded text-[10px] font-bold';
        }
      }
      setInterval(updateCountdown, 60000);
      updateCountdown();"""
assert JS_ANCHOR in html, "カウントダウンJS挿入点が見つかりません"
html = html.replace(JS_ANCHOR, JS_ANCHOR + JS_INSERT, 1)
print("2. カウントダウンJS追加 ✓")

# ══════════════════════════════════════════════════════════
# 3. 旅程表タブ：日没カレンダー＆記念日ハイライト
#    → 確定フライト一覧カードの後、DAY 1 の前に挿入
# ══════════════════════════════════════════════════════════
DAY1_MARKER = "      <!-- DAY 1 -->"
assert DAY1_MARKER in html, "DAY 1 マーカーが見つかりません"

ITINERARY_INSERT = """
      <!-- 日没・日の出カレンダー＆記念日ハイライト -->
      <div class="bg-white rounded-2xl shadow-xs border border-slate-200 p-4 sm:p-5 space-y-4">
        <div class="flex items-center justify-between border-b border-slate-100 pb-3 gap-2">
          <div class="flex items-center space-x-2.5">
            <i class="fa-solid fa-sun text-amber-500 text-lg"></i>
            <div>
              <h2 class="font-bold text-slate-800 text-sm sm:text-base">🌅 日没・日の出時刻カレンダー（全15日）</h2>
              <p class="text-xs text-slate-500">現地時刻・概算 ±5分。撮影計画・散策タイミングの目安に</p>
            </div>
          </div>
          <span class="text-[10px] text-slate-500 shrink-0">EGY=EET(UTC+2) / GR=EEST(UTC+3)</span>
        </div>
        <div class="overflow-x-auto">
          <table class="w-full text-xs border-collapse">
            <thead>
              <tr class="bg-slate-50 text-slate-600">
                <th class="p-1.5 text-left font-bold border-b border-slate-200">DAY</th>
                <th class="p-1.5 text-left font-bold border-b border-slate-200">日付</th>
                <th class="p-1.5 text-left font-bold border-b border-slate-200">エリア</th>
                <th class="p-1.5 text-center font-bold border-b border-slate-200">日の出🌄</th>
                <th class="p-1.5 text-center font-bold border-b border-slate-200">日の入り🌇</th>
                <th class="p-1.5 text-left font-bold border-b border-slate-200">撮影チャンス・メモ</th>
              </tr>
            </thead>
            <tbody class="divide-y divide-slate-100">
              <tr class="hover:bg-slate-50"><td class="p-1.5 font-bold text-amber-700">1</td><td class="p-1.5 whitespace-nowrap">9/13(日)</td><td class="p-1.5">機内</td><td class="p-1.5 text-center text-slate-400">―</td><td class="p-1.5 text-center text-slate-400">―</td><td class="p-1.5 text-slate-500">機内泊。着圧ソックス着用で睡眠確保</td></tr>
              <tr class="hover:bg-slate-50"><td class="p-1.5 font-bold text-amber-700">2</td><td class="p-1.5 whitespace-nowrap">9/14(月)</td><td class="p-1.5">ギザ</td><td class="p-1.5 text-center font-mono">05:47</td><td class="p-1.5 text-center font-mono">18:47</td><td class="p-1.5 text-slate-600">GEM夕景・ホテル屋上からピラミッド夜景</td></tr>
              <tr class="bg-amber-50 font-medium"><td class="p-1.5 font-bold text-amber-700">3</td><td class="p-1.5 whitespace-nowrap">9/15(火)</td><td class="p-1.5">ギザ</td><td class="p-1.5 text-center font-mono">05:48</td><td class="p-1.5 text-center font-mono text-amber-700">18:45</td><td class="p-1.5 text-amber-800">🎂 <strong>記念日ディナー①</strong>（Khufu'sまたは139 Pavilion）</td></tr>
              <tr class="hover:bg-slate-50"><td class="p-1.5 font-bold text-amber-700">4</td><td class="p-1.5 whitespace-nowrap">9/16(水)</td><td class="p-1.5">白砂漠へ</td><td class="p-1.5 text-center font-mono">05:48</td><td class="p-1.5 text-center font-mono">18:44</td><td class="p-1.5 text-slate-600">白砂漠の夕景シルエット撮影</td></tr>
              <tr class="bg-indigo-50 font-medium"><td class="p-1.5 font-bold text-amber-700">5</td><td class="p-1.5 whitespace-nowrap">9/17(木)</td><td class="p-1.5">白砂漠</td><td class="p-1.5 text-center font-mono text-indigo-700">05:49</td><td class="p-1.5 text-center font-mono">18:42</td><td class="p-1.5 text-indigo-800">⭐ <strong>白砂漠日の出&天の川星空 最高潮!</strong></td></tr>
              <tr class="hover:bg-slate-50"><td class="p-1.5 font-bold text-amber-700">6</td><td class="p-1.5 whitespace-nowrap">9/18(金)</td><td class="p-1.5">ルクソール</td><td class="p-1.5 text-center font-mono">05:43</td><td class="p-1.5 text-center font-mono">18:35</td><td class="p-1.5 text-slate-600">ルクソール神殿ライトアップ（夜の2回目推奨）</td></tr>
              <tr class="bg-amber-50"><td class="p-1.5 font-bold text-amber-700">7</td><td class="p-1.5 whitespace-nowrap">9/19(土)</td><td class="p-1.5">ルクソール</td><td class="p-1.5 text-center font-mono text-amber-700">05:43</td><td class="p-1.5 text-center font-mono">18:33</td><td class="p-1.5 text-amber-800">📸 カルナック斜光(7-9時)・ファルーカ夕日乾杯</td></tr>
              <tr class="hover:bg-slate-50"><td class="p-1.5 font-bold text-amber-700">8</td><td class="p-1.5 whitespace-nowrap">9/20(日)</td><td class="p-1.5">ルクソール→カイロ</td><td class="p-1.5 text-center font-mono">05:44</td><td class="p-1.5 text-center font-mono">18:31</td><td class="p-1.5 text-slate-600">ナイル川夕日・ルクソール神殿昼夜2回</td></tr>
              <tr class="hover:bg-slate-50"><td class="p-1.5 font-bold text-sky-700">9</td><td class="p-1.5 whitespace-nowrap">9/21(月)</td><td class="p-1.5">アテネ</td><td class="p-1.5 text-center font-mono">07:01</td><td class="p-1.5 text-center font-mono">19:44</td><td class="p-1.5 text-slate-600">アレオパゴス/フィロパポスの丘からパルテノン夕景</td></tr>
              <tr class="hover:bg-sky-50"><td class="p-1.5 font-bold text-sky-700">10</td><td class="p-1.5 whitespace-nowrap">9/22(火)</td><td class="p-1.5">アテネ→サントリーニ</td><td class="p-1.5 text-center font-mono">07:02</td><td class="p-1.5 text-center font-mono">19:52</td><td class="p-1.5 text-sky-700">アクロポリス早朝(8時〜)・サントリーニ初日の夕日</td></tr>
              <tr class="bg-rose-50 font-medium"><td class="p-1.5 font-bold text-sky-700">11</td><td class="p-1.5 whitespace-nowrap">9/23(水)</td><td class="p-1.5">サントリーニ</td><td class="p-1.5 text-center font-mono text-rose-600">07:02</td><td class="p-1.5 text-center font-mono text-rose-600">19:51</td><td class="p-1.5 text-rose-800">💍 <strong>ブライダルフォト(7:30〜)・イア夕日</strong></td></tr>
              <tr class="bg-amber-50 font-medium"><td class="p-1.5 font-bold text-sky-700">12</td><td class="p-1.5 whitespace-nowrap">9/24(木)</td><td class="p-1.5">サントリーニ</td><td class="p-1.5 text-center font-mono">07:03</td><td class="p-1.5 text-center font-mono text-amber-700">19:49</td><td class="p-1.5 text-amber-800">🎂 <strong>記念日ディナー②</strong>（The Athenian House）・イア夕日</td></tr>
              <tr class="hover:bg-sky-50"><td class="p-1.5 font-bold text-sky-700">13</td><td class="p-1.5 whitespace-nowrap">9/25(金)</td><td class="p-1.5">サントリーニ→アテネ</td><td class="p-1.5 text-center font-mono">07:04</td><td class="p-1.5 text-center font-mono">19:47</td><td class="p-1.5 text-slate-600">カルデラ朝景・午後フライトで帰路へ</td></tr>
              <tr class="hover:bg-slate-50"><td class="p-1.5 font-bold text-sky-700">14</td><td class="p-1.5 whitespace-nowrap">9/26(土)</td><td class="p-1.5">アテネ→機内</td><td class="p-1.5 text-center font-mono">07:05</td><td class="p-1.5 text-center font-mono">19:46</td><td class="p-1.5 text-slate-600">空港で免税（Tax Refund）手続き</td></tr>
              <tr class="hover:bg-slate-50"><td class="p-1.5 font-bold text-slate-500">15</td><td class="p-1.5 whitespace-nowrap">9/27(日)</td><td class="p-1.5">成田着</td><td class="p-1.5 text-center text-slate-400">―</td><td class="p-1.5 text-center text-slate-400">―</td><td class="p-1.5 text-slate-500">12:05帰国。2週間以内に発熱があれば受診を</td></tr>
            </tbody>
          </table>
        </div>
      </div>

      <!-- 記念日ハイライト＆ホテル演出アイデア -->
      <div class="bg-gradient-to-r from-rose-50 to-amber-50 border border-rose-200 rounded-2xl p-4 sm:p-5 shadow-xs space-y-3">
        <div class="flex items-center space-x-2.5 border-b border-rose-200 pb-2">
          <span class="text-xl">🎂</span>
          <div>
            <h2 class="font-bold text-rose-900 text-sm sm:text-base">記念日・ブライダル演出プランニング</h2>
            <p class="text-xs text-rose-700">ハネムーン特典を最大活用する事前リクエスト集</p>
          </div>
        </div>
        <div class="grid grid-cols-1 sm:grid-cols-2 gap-3 text-xs text-slate-700 leading-relaxed">
          <div class="p-3 bg-white rounded-xl border border-rose-200 space-y-2">
            <strong class="text-rose-900 block">9/15 ギザ 記念日ディナー①</strong>
            <p>🍽️ <strong>予約先：</strong> Khufu's Restaurant（ピラミッド至近）または 139 Pavilion（GEM隣接）。</p>
            <p>👔 <strong>ドレスコード：</strong> スマートカジュアル（男性：襟付きシャツ＋長ズボン、女性：ワンピース）。</p>
            <p>💌 <strong>ホテルへの事前リクエスト（英語メモ）：</strong><br><span class="font-mono text-slate-600 text-[11px]">"We are on our honeymoon. Could you arrange flower petals and a small card in our room on Sep 15? Thank you!"</span></p>
          </div>
          <div class="p-3 bg-white rounded-xl border border-amber-200 space-y-2">
            <strong class="text-amber-900 block">9/24 サントリーニ 記念日ディナー②</strong>
            <p>🍽️ <strong>予約先：</strong> The Athenian House（カルデラビュー・夕日）。</p>
            <p>👗 <strong>ドレスコード：</strong> スマートカジュアル（女性：リゾートワンピース、男性：リネンシャツ）。</p>
            <p>🌅 <strong>席リクエスト：</strong> 予約時に「Caldera view table, honeymoon」と記載。日没30分前（19:20頃）着席でベストシャッターチャンス。</p>
            <p>🍷 <strong>ワイン：</strong> サントワインズのAsyrtiko（辛口白）が定番。乳製品不使用のグリルシーフードと最高相性。</p>
          </div>
        </div>
      </div>

"""

html = html.replace(DAY1_MARKER, ITINERARY_INSERT + DAY1_MARKER, 1)
print("3. 旅程表タブ：日没カレンダー＆記念日カード追加 ✓")

# ══════════════════════════════════════════════════════════
# 4. フォトタブ：ブライダルフォト当日シート
#    → TAB 6 (ToDo) の直前（フォトタブ closing </section> の手前）に挿入
# ══════════════════════════════════════════════════════════
PHOTO_END = '    </section>\n\n    <!-- ==================== TAB 6: ToDo'
assert PHOTO_END in html, "フォトタブ終端マーカーが見つかりません"

BRIDAL_SHEET = """
      <!-- ⑤ ブライダルフォト当日シート（9/23） -->
      <div class="bg-gradient-to-r from-rose-50 to-pink-50 border border-rose-300 rounded-2xl p-4 sm:p-5 shadow-xs space-y-4">
        <div class="flex items-center space-x-2.5 border-b border-rose-200 pb-3">
          <i class="fa-solid fa-camera-rotate text-rose-500 text-lg"></i>
          <div>
            <h2 class="font-bold text-rose-950 text-sm sm:text-base">💍 ブライダルフォト当日シート（9/23 サントリーニ）</h2>
            <p class="text-xs text-rose-700">7:30 集合 ─ 早朝ゴールデンアワーの2時間で最高の1枚を</p>
          </div>
          <span class="shrink-0 text-[10px] bg-rose-600 text-white px-2 py-0.5 rounded font-bold">最重要イベント</span>
        </div>

        <div class="grid grid-cols-1 sm:grid-cols-2 gap-3 text-xs text-slate-700 leading-relaxed">
          <!-- 当日タイムライン -->
          <div class="p-3 bg-white rounded-xl border border-rose-200 space-y-2">
            <strong class="text-rose-900 block">⏰ 当日タイムライン</strong>
            <p>06:45 起床・ヘアメイク開始（パートナー先行）</p>
            <p>07:10 朝食を軽く（ブーゲンビリアカフェ等）</p>
            <p>07:30 カメラマン集合・ロケーション確認</p>
            <p>07:30〜09:30 撮影（ゴールデンアワー：観光客が来る前）</p>
            <p>09:30 撮影終了・カメラマンへのチップ目安：20〜30€</p>
            <p>⚠️ <strong>荒天スライドルール：</strong> 雨・強風の場合は9/24（木）に自動スライド。翌朝の予定を開けておくこと。</p>
          </div>
          <!-- 服装チェック -->
          <div class="p-3 bg-white rounded-xl border border-rose-200 space-y-2">
            <strong class="text-rose-900 block">👗 服装・持ち物チェック</strong>
            <p>□ ドレス（シワ防止のため前夜からハンガー掛け）</p>
            <p>□ 男性：リネン白シャツ＋スラックス（ブーツ可）</p>
            <p>□ アクセサリー：結婚指輪・ネックレス忘れず</p>
            <p>□ 補正下着・シームレス下着</p>
            <p>□ ヘアスプレー・ピンチ（海風対策）</p>
            <p>□ ウェットティッシュ・ミラー（直前の最終確認）</p>
            <p>□ スマホ満充電（バックアップ撮影用）</p>
          </div>
          <!-- カメラマンへの伝達事項 -->
          <div class="p-3 bg-white rounded-xl border border-pink-200 space-y-2">
            <strong class="text-pink-900 block">📋 カメラマンへの事前共有（希望ショット）</strong>
            <p>✅ ブルードームを背景に手繋ぎ（正面・横・後ろ姿）</p>
            <p>✅ 白い路地で向き合いキス</p>
            <p>✅ カルデラ展望テラスで乾杯ショット</p>
            <p>✅ 二人が映り込むロングショット（距離をとる）</p>
            <p>✅ 自然な笑顔カット（ポーズなしの歩きながら）</p>
            <p>❌ NG：顔を隠す演出、逆光が強すぎる帽子</p>
            <p class="text-slate-500 text-[11px]">事前にPinterestなどで「希望イメージ」をURL共有するとスムーズ</p>
          </div>
          <!-- 直前コンディション管理 -->
          <div class="p-3 bg-white rounded-xl border border-pink-200 space-y-2">
            <strong class="text-pink-900 block">💊 撮影前コンディション管理</strong>
            <p>🌊 <strong>9/22（前日）：</strong> 水分を十分に。塩分補給も忘れずに。アルコールは控えめに（むくみ防止）。</p>
            <p>😴 <strong>睡眠：</strong> 22時就寝を目標。早朝7:30撮影のため睡眠が命。</p>
            <p>🍽️ <strong>当日朝食：</strong> 食べすぎるとお腹が張る。軽めのパンかフルーツ程度に。</p>
            <p>☀️ <strong>日焼け止め：</strong> 早朝でも日差しが強い。ウォータープルーフのSPF50+を撮影前に塗布。</p>
            <p>🙏 <strong>緊張緩和：</strong> 「カメラマンを信頼する。自然に笑う」だけ意識すればOK！</p>
          </div>
        </div>
      </div>

"""

html = html.replace(PHOTO_END, BRIDAL_SHEET + PHOTO_END, 1)
print("4. フォトタブ：ブライダルフォト当日シート追加 ✓")

# ══════════════════════════════════════════════════════════
# 5. 歴史タブ：旅のBGMプレイリスト
#    → TAB 5 (フォト) の直前（歴史タブ closing </section> の手前）に挿入
# ══════════════════════════════════════════════════════════
HISTORY_END = '    </section>\n\n    <!-- ==================== TAB 5: フォト'
assert HISTORY_END in html, "歴史タブ終端マーカーが見つかりません"

BGM_SECTION = """
      <!-- BGM プレイリスト -->
      <div class="bg-white rounded-2xl shadow-xs border border-slate-200 p-4 sm:p-5 space-y-4">
        <div class="flex items-center space-x-2.5 border-b border-slate-100 pb-3">
          <i class="fa-solid fa-music text-purple-500 text-lg"></i>
          <div>
            <h2 class="font-bold text-slate-800 text-sm sm:text-base">🎵 旅のBGMプレイリスト提案（オフライン再生推奨）</h2>
            <p class="text-xs text-slate-500">Spotify / Apple Musicで事前ダウンロード。機内・白砂漠・カルデラビューのBGMに</p>
          </div>
        </div>
        <div class="grid grid-cols-1 sm:grid-cols-2 gap-3 text-xs text-slate-700 leading-relaxed">
          <div class="p-3 bg-amber-50/70 rounded-xl border border-amber-200 space-y-2">
            <strong class="text-amber-900 block">🇪🇬 エジプト編</strong>
            <p>🎼 <strong>Umm Kulthum（ウム・カルスーム）：</strong> エジプトの国民的歌手。「Enta Omri（あなたは私の人生）」が定番。アラビア語の美しさに浸る。</p>
            <p>🎼 <strong>映画「ナイル殺人事件」（2022）サントラ：</strong> Kenneth Branagh版。エジプト情緒満点のオーケストラ。</p>
            <p>🎼 <strong>Amr Diab（アムル・ディアブ）：</strong> 現代エジプトポップの王者。「Habibi（愛しい人）」シリーズ。</p>
            <p>🎼 <strong>Yanni Live at the Acropolis：</strong> ギリシャ録音の名盤。エジプト→ギリシャの移行BGMに。</p>
            <p class="text-amber-700 font-bold">Spotify検索：「Arabic Lounge」「Cairo Cafe Music」</p>
          </div>
          <div class="p-3 bg-sky-50/70 rounded-xl border border-sky-200 space-y-2">
            <strong class="text-sky-900 block">🇬🇷 ギリシャ編</strong>
            <p>🎼 <strong>Mikis Theodorakis（テオドラキス）：</strong> 映画「希望と栄光」「ゾルバのギリシャ人」。ブズーキの音色がアテネの石畳に響く。</p>
            <p>🎼 <strong>Nana Mouskouri（ナナ・ムスクーリ）：</strong> ギリシャの国民的歌手。「白いバラ」「You've Got a Friend」等。</p>
            <p>🎼 <strong>サントリーニ夕日BGM：</strong> George Skaroulis「Serenity」シリーズ。ピアノの音色がカルデラの夕日に合う。</p>
            <p>🎼 <strong>Yorgos Dalaras（ヨルゴス・ダラス）：</strong> レンベーティコ（ギリシャブルース）の現代的解釈者。</p>
            <p class="text-sky-700 font-bold">Spotify検索：「Greek Cafe Music」「Santorini Sunset Mix」</p>
          </div>
        </div>
        <div class="p-2.5 bg-purple-50 rounded-lg border border-purple-200 text-[11px] text-purple-800">
          <strong>💡 オフライン再生のすすめ：</strong> 白砂漠（圏外）・機内・サントリーニの電波不安定エリアに備え、出発前にWi-Fi環境でSpotifyの「ダウンロード」を完了させておくこと。Apple Musicも同様。
        </div>
      </div>

"""

html = html.replace(HISTORY_END, BGM_SECTION + HISTORY_END, 1)
print("5. 歴史タブ：BGMプレイリスト追加 ✓")

# ══════════════════════════════════════════════════════════
# 6. 服装＆持ち物タブ：現地調達OK / 日本から必携リスト
#    → TAB 8 (安心ガイド) の直前に挿入
# ══════════════════════════════════════════════════════════
PACKING_END = '    </section>\n\n    <!-- ==================== TAB 8: 安心'
assert PACKING_END in html, "服装タブ終端マーカーが見つかりません"

LOCAL_BUY_SECTION = """
      <!-- 現地調達OK vs 日本から必携リスト -->
      <div class="bg-white rounded-2xl shadow-xs border border-slate-200 p-4 sm:p-5 space-y-4">
        <div class="flex items-center space-x-2.5 border-b border-slate-100 pb-3">
          <i class="fa-solid fa-scale-balanced text-emerald-600 text-lg"></i>
          <div>
            <h2 class="font-bold text-slate-800 text-sm sm:text-base">⚖️ 現地調達OK vs 日本から必携リスト</h2>
            <p class="text-xs text-slate-500">スーツケースを軽くするための取捨選択ガイド</p>
          </div>
        </div>
        <div class="grid grid-cols-1 sm:grid-cols-2 gap-3 text-xs text-slate-700 leading-relaxed">
          <div class="p-3 bg-red-50 rounded-xl border border-red-200 space-y-2">
            <strong class="text-red-900 block flex items-center gap-1"><i class="fa-solid fa-suitcase text-red-500"></i> 日本から必ず持参（現地調達困難）</strong>
            <p>🧥 <strong>ウルトラライトダウン：</strong> 白砂漠の夜は18℃まで下がる。観光地では手に入らない。</p>
            <p>🔌 <strong>Cタイプ変換アダプター：</strong> 丸ピン2本。空港でも売っているが割高。1〜2個持参推奨。</p>
            <p>☀️ <strong>日焼け止めSPF50+（大容量）：</strong> エジプトは強烈な日差し。現地のものは品質にばらつきあり。</p>
            <p>💊 <strong>日本の市販薬：</strong> 整腸剤（正露丸・ビオフェルミン）、頭痛薬（ロキソニン）、胃薬（ガスター10）。現地薬と名称が違い入手に手間がかかる。</p>
            <p>🩹 <strong>絆創膏・ムヒ：</strong> 石畳・砂利道での靴ずれ・虫刺され対策。</p>
            <p>🌂 <strong>UVカット折りたたみ傘：</strong> 日傘兼雨傘。エジプトで傘を持っている観光客は少なく現地調達不可。</p>
            <p>🧴 <strong>ハンドサニタイザー（大容量）：</strong> 遺跡内・白砂漠キャンプは手洗い不可環境がある。</p>
          </div>
          <div class="p-3 bg-emerald-50 rounded-xl border border-emerald-200 space-y-2">
            <strong class="text-emerald-900 block flex items-center gap-1"><i class="fa-solid fa-store text-emerald-500"></i> 現地調達OK（荷物を減らせる）</strong>
            <p>💧 <strong>ミネラルウォーター：</strong> スーパーで5本1セット30〜40EGP。ホテルでも購入可。500mLを日本から持ち込む必要なし。</p>
            <p>🕶️ <strong>サングラス：</strong> カイロ・アテネの観光地で3〜5€から購入可（あくまで現地調達OK、良質なものは日本から）。</p>
            <p>🧢 <strong>帽子：</strong> ギザ・ルクソールの土産店で麦わら帽が10〜30EGP。ただし品質は低め。</p>
            <p>🪥 <strong>歯ブラシ・シャンプー：</strong> 高級ホテルなら備え付け。ルクソールのスーパーで購入も可。</p>
            <p>🍋 <strong>飴・お菓子類：</strong> 現地のお菓子を楽しんで。日本のお菓子（外国人に渡す用）は少量のみ持参。</p>
            <p>📦 <strong>お土産用のエコバッグ：</strong> スークでの買い物に便利。現地でも購入可。ただし折りたたみタイプは日本の方が品質良好。</p>
            <p>🧻 <strong>ティッシュ・トイレットペーパー：</strong> 高級ホテルは問題なし。観光地のトイレは備え付けなしが多いため小さいポケットティッシュを1〜2個常備で十分。</p>
          </div>
        </div>
      </div>

"""

html = html.replace(PACKING_END, LOCAL_BUY_SECTION + PACKING_END, 1)
print("6. 服装タブ：現地調達OK/必携リスト追加 ✓")

# ══════════════════════════════════════════════════════════
# 7. 安心ガイドタブ：5セクション追加
#    → <!-- 9. 緊急連絡先 --> の直前に挿入
# ══════════════════════════════════════════════════════════
TIPS_MARKER = "      <!-- 9. 緊急連絡先 -->"
assert TIPS_MARKER in html, "緊急連絡先マーカーが見つかりません"

TIPS_INSERT = """
      <!-- 9A. ギリシャ料理の乳製品NG地雷メニュー -->
      <div class="bg-rose-50 border border-rose-200 rounded-2xl p-4 sm:p-5 shadow-xs space-y-3">
        <div class="flex items-center space-x-2 border-b border-rose-200 pb-2">
          <i class="fa-solid fa-triangle-exclamation text-rose-600"></i>
          <h2 class="font-bold text-rose-900 text-sm sm:text-base">⚠️ ギリシャ料理の乳製品NG「地雷」メニューリスト</h2>
        </div>
        <div class="grid grid-cols-1 sm:grid-cols-2 gap-3 text-xs text-slate-700 leading-relaxed">
          <div class="space-y-1.5 p-3 bg-white rounded-xl border border-rose-200">
            <strong class="text-rose-800 block">🚫 注文前に要確認・要変更</strong>
            <p>🧀 <strong>ホリアティキ（Greek Salad）：</strong> フェタチーズが大量に乗っている。「<strong>χωρίς τυρί（ホリス・ティリ）</strong>＝チーズなし」で注文。</p>
            <p>🥣 <strong>ツァツィキ（Tzatziki）：</strong> ヨーグルト＋キュウリのディップ。定番前菜だが完全アウト。</p>
            <p>🥘 <strong>ムサカ（Moussaka）：</strong> ミートソース＋ベシャメルソース（バター＋牛乳）の重ね焼き。一見肉料理だが乳製品入り。</p>
            <p>🥐 <strong>ブガッツァ（Bougatsa）：</strong> クリームフィリング入りのフィロ生地パイ。朝食に出されることが多い。</p>
            <p>🥬 <strong>スパナコピタ（Spanakopita）：</strong> ほうれん草＋フェタチーズのパイ。スナック感覚で売っているが要注意。</p>
            <p>🍮 <strong>ガラクトブレコ（Galaktoboureko）：</strong> カスタードクリームのシロップパイ。デザートとして出る。</p>
          </div>
          <div class="space-y-1.5 p-3 bg-white rounded-xl border border-emerald-200">
            <strong class="text-emerald-800 block">✅ 安心して食べられるメニュー</strong>
            <p>🦑 <strong>カラマリ（Kalamari）：</strong> オリーブオイル揚げイカ。乳製品ゼロ。</p>
            <p>🦐 <strong>グリルシーフード（タコ・エビ・スズキ）：</strong> レモン＋オリーブオイルのみ。</p>
            <p>🍡 <strong>スブラキ（Souvlaki）：</strong> 塩・オレガノ・レモンのみ。肉串焼き。</p>
            <p>🫘 <strong>ファヴァ（Fava）：</strong> 黄えんどう豆ペースト。乳製品不使用。</p>
            <p>🫒 <strong>ドルマデス（Dolmades）：</strong> ぶどう葉のライス包み。スプレッドなし版は安全。</p>
            <p>🐟 <strong>プサロスーパ（魚スープ）：</strong> 魚と野菜のクリアスープ。クリームなし版を確認して。</p>
            <p class="text-emerald-700 font-bold">基本ルール：「χωρίς γαλακτοκομικά（ホリス・ガラクトコミカ）＝乳製品なし」を合言葉に！</p>
          </div>
        </div>
      </div>

      <!-- 9B. Googleマップ・オフラインDLガイド -->
      <div class="bg-white rounded-2xl shadow-xs border border-slate-200 p-4 sm:p-5 space-y-3">
        <div class="flex items-center space-x-2 border-b border-slate-100 pb-2">
          <i class="fa-solid fa-map text-blue-600 text-lg"></i>
          <h2 class="font-bold text-slate-800 text-sm sm:text-base">🗺️ Googleマップ オフラインDL準備ガイド</h2>
        </div>
        <div class="grid grid-cols-1 sm:grid-cols-2 gap-3 text-xs text-slate-700 leading-relaxed">
          <div class="p-3 bg-blue-50 rounded-xl border border-blue-200 space-y-2">
            <strong class="text-blue-900 block">📥 DL推奨エリア（出発前に完了）</strong>
            <p>🇪🇬 <strong>カイロ・ギザ周辺：</strong> ピラミッド・GEM・ザマレク・コルバ。圏外ではないが通信節約に。</p>
            <p>🏜️ <strong>白砂漠ルート（最重要）：</strong> バハレイヤ・オアシス ↔ White Desert National Park のルート。<strong>現地は完全圏外のためオフラインDL必須。</strong></p>
            <p>🛕 <strong>ルクソール市内：</strong> 王家の谷・カルナック・東岸スーク全域。</p>
            <p>🇬🇷 <strong>アテネ市内：</strong> アクロポリス・プラカ・アナフィオティカ・シンタグマ広場。</p>
            <p>🌊 <strong>サントリーニ島全域：</strong> フィラ・イメロヴィグリ・イア・アティニオス港。電波が不安定なエリアあり。</p>
          </div>
          <div class="p-3 bg-blue-50 rounded-xl border border-blue-200 space-y-2">
            <strong class="text-blue-900 block">📱 DL手順（Googleマップ）</strong>
            <p>1️⃣ Wi-Fi接続を確認（ホテルなどで必ず実施）</p>
            <p>2️⃣ Googleマップ → 右上アイコン → 「オフラインマップ」</p>
            <p>3️⃣ 「独自の地図を選択」→ 地図を拡大して対象エリアを枠に収める</p>
            <p>4️⃣ 「ダウンロード」→ 各エリアで実施。1エリア数十〜200MB程度</p>
            <p>5️⃣ 「更新期限」が30日のため出発直前にDLが最適</p>
            <p class="text-blue-700 font-bold">💡 補助アプリ：Maps.me（完全オフライン・詳細地図）も併用推奨。事前インストールしておく。</p>
          </div>
        </div>
      </div>

      <!-- 9C. 貴重品仕分けガイド -->
      <div class="bg-white rounded-2xl shadow-xs border border-slate-200 p-4 sm:p-5 space-y-3">
        <div class="flex items-center space-x-2 border-b border-slate-100 pb-2">
          <i class="fa-solid fa-shield-halved text-slate-600 text-lg"></i>
          <h2 class="font-bold text-slate-800 text-sm sm:text-base">🔐 貴重品仕分けガイド（スリ・紛失対策）</h2>
        </div>
        <div class="grid grid-cols-1 sm:grid-cols-3 gap-3 text-xs text-slate-700 leading-relaxed">
          <div class="p-3 bg-amber-50 rounded-xl border border-amber-200 space-y-1.5">
            <strong class="text-amber-900 block">👝 常時携行（ウエストポーチ）</strong>
            <p>・パスポートコピー（原本はホテルセーフ）</p>
            <p>・現金：少額のみ（EGP日常用＋USD少額）</p>
            <p>・メインクレジットカード × 1枚</p>
            <p>・スマホ（常にポーチ内に）</p>
            <p>・Uberアプリ用データ通信可eSIM</p>
            <p class="text-amber-700 font-bold">ポイント：ウエストポーチは前掛け（腹側）着用でスリ対策</p>
          </div>
          <div class="p-3 bg-slate-50 rounded-xl border border-slate-200 space-y-1.5">
            <strong class="text-slate-800 block">🏨 ホテルセーフティボックス</strong>
            <p>・パスポート原本</p>
            <p>・余剰現金（EGP大金・EUR・USD）</p>
            <p>・予備クレジットカード</p>
            <p>・航空券印刷版（eチケット）</p>
            <p>・海外旅行保険証書コピー</p>
            <p class="text-slate-600 font-bold">ポイント：チェックアウト時は必ずセーフ確認！忘れ物最頻出</p>
          </div>
          <div class="p-3 bg-red-50 rounded-xl border border-red-200 space-y-1.5">
            <strong class="text-red-900 block">🚫 スリ防止の鉄則</strong>
            <p>・背負うバッグは胸側に抱える（エジプトのスーク内）</p>
            <p>・スマホを後ろポケットに入れない</p>
            <p>・タクシー・Uberで車内にスマホ放置しない</p>
            <p>・財布は開けたまま取り出さない（小額は事前に分けておく）</p>
            <p>・「ガイドしてあげる」「見せたいものがある」は断固断る</p>
            <p class="text-red-700 font-bold">⚠️ カイロのスーク・ルクソール神殿周辺は特に注意</p>
          </div>
        </div>
      </div>

      <!-- 9D. 医療・旅行保険情報 -->
      <div class="bg-white rounded-2xl shadow-xs border border-slate-200 p-4 sm:p-5 space-y-3">
        <div class="flex items-center space-x-2 border-b border-slate-100 pb-2">
          <i class="fa-solid fa-kit-medical text-emerald-600 text-lg"></i>
          <h2 class="font-bold text-slate-800 text-sm sm:text-base">🏥 医療・旅行保険ガイド</h2>
        </div>
        <div class="grid grid-cols-1 sm:grid-cols-2 gap-3 text-xs text-slate-700 leading-relaxed">
          <div class="p-3 bg-emerald-50 rounded-xl border border-emerald-200 space-y-2">
            <strong class="text-emerald-900 block">💳 クレジットカード付帯保険の確認</strong>
            <p>・旅行前に使用するクレカの「海外旅行保険」が適用される条件（旅行代金の一部をそのカードで決済が条件のことが多い）を確認。</p>
            <p>・補償額の目安：疾病・傷害治療 → 最低500万円以上が望ましい。エジプトは私立病院が高額（診察1回＋薬で3〜5万円相当）。</p>
            <p>・万一の受診後：領収書・診断書・処方箋を必ず保管。帰国後に保険請求に使用。</p>
            <strong class="text-emerald-900 block mt-2">🏥 現地病院・薬局の探し方</strong>
            <p>・Googleマップで「Hospital」または「Pharmacy（薬局）」と入力。</p>
            <p>・エジプト：「As-Salam International Hospital（カイロ）」等の私立病院は英語対応可。</p>
            <p>・ギリシャ：緑十字「ΦΑΡΜΑΚΕΙΟ（ファルマキオ）」マークが薬局の目印。</p>
          </div>
          <div class="p-3 bg-emerald-50 rounded-xl border border-emerald-200 space-y-2">
            <strong class="text-emerald-900 block">💊 現地市販薬リスト</strong>
            <p>🇪🇬 <strong>エジプト（薬局で入手）：</strong></p>
            <p>・<strong>Antinal：</strong> 細菌性下痢の特効薬（エジプト旅行者定番）。20〜40EGP。</p>
            <p>・<strong>Panadol（パナドール）：</strong> 解熱・頭痛薬（アセトアミノフェン）。</p>
            <p>・<strong>Rehydration salts：</strong> 経口補水塩（Pedialyte等）。脱水対策。</p>
            <p>🇬🇷 <strong>ギリシャ（薬局で入手）：</strong></p>
            <p>・<strong>Depon / Panadol：</strong> 解熱・頭痛薬。</p>
            <p>・<strong>Imodium（イモジウム）：</strong> 下痢止め。薬局で購入可。</p>
            <strong class="text-emerald-900 block mt-2">☀️ 熱中症応急処置</strong>
            <p>① すぐに日陰へ移動 ② 冷たい水分補給（経口補水塩が最適）③ 首・脇・股を冷やす ④ 回復しない場合は病院へ。ルクソールの炎天下は特に注意。</p>
            <p class="text-emerald-700 font-bold">⚠️ 帰国後2週間以内の発熱はマラリア等の可能性あり。必ず医療機関を受診し「エジプト渡航歴あり」と申告。</p>
          </div>
        </div>
      </div>

      <!-- 9E. 免税（Tax Refund）手続きガイド -->
      <div class="bg-white rounded-2xl shadow-xs border border-slate-200 p-4 sm:p-5 space-y-3">
        <div class="flex items-center space-x-2 border-b border-slate-100 pb-2">
          <i class="fa-solid fa-receipt text-indigo-600 text-lg"></i>
          <h2 class="font-bold text-slate-800 text-sm sm:text-base">🧾 免税（Tax Refund）完全ガイド</h2>
        </div>
        <div class="grid grid-cols-1 sm:grid-cols-2 gap-3 text-xs text-slate-700 leading-relaxed">
          <div class="p-3 bg-indigo-50 rounded-xl border border-indigo-200 space-y-2">
            <strong class="text-indigo-900 block">🇬🇷 ギリシャ：Tax Refund対象（最重要）</strong>
            <p>📌 <strong>対象条件：</strong> EU非居住者（日本人はOK）がギリシャ国内で1店舗50€以上の買い物をした場合。</p>
            <p>🛍️ <strong>購入時：</strong> 「Tax Free（税金還付書類）ください」と申し出る。Global Blue・Planet等の書類に氏名・パスポート番号を記入。</p>
            <p>✈️ <strong>アテネ空港での手続き：</strong></p>
            <p>① 出国審査前（制限エリア外）のTax Refundカウンターへ</p>
            <p>② 書類・レシート・購入品（未使用・タグ付き）・パスポートを提示</p>
            <p>③ 承認スタンプをもらう（※購入品は検査される場合あり）</p>
            <p>④ 出国後（制限エリア内）の払い戻しカウンターで現金またはカード還付</p>
            <p class="text-indigo-700 font-bold">⏰ 出国3時間前には手続き開始を。行列で1時間かかることも。</p>
          </div>
          <div class="p-3 bg-indigo-50 rounded-xl border border-indigo-200 space-y-2">
            <strong class="text-indigo-900 block">💡 Tax Refundのコツと注意点</strong>
            <p>📦 <strong>購入品は機内持ち込みバッグに：</strong> スーツケースに預けると税関で開けられない（未使用の証明ができない）。</p>
            <p>🧾 <strong>書類の保管：</strong> 購入書類はアテネ空港まで財布の中に安全に保管。無くすと還付不可。</p>
            <p>💶 <strong>還付率：</strong> 購入額の12〜15%程度（手数料差し引き後）。50€購入なら6〜7€戻る計算。</p>
            <p>🏪 <strong>対象外の店舗：</strong> スーク（市場）や個人商店はTax Free非対応が多い。デパート・ブランド店は対応している。</p>
            <p>🇪🇬 <strong>エジプトは対象外：</strong> エジプトにはTax Refund制度がないため、お土産代の還付は期待できない。</p>
            <p>🗓️ <strong>帰国後の申請：</strong> 空港で手続きできなかった場合、Global Blueアプリから郵送申請が可能（時間はかかる）。</p>
          </div>
        </div>
      </div>

"""

html = html.replace(TIPS_MARKER, TIPS_INSERT + TIPS_MARKER, 1)
print("7. 安心ガイドタブ：5セクション追加 ✓")

# ══════════════════════════════════════════════════════════
# 出力
# ══════════════════════════════════════════════════════════
OUTPUT.write_text(html, encoding="utf-8")
size = OUTPUT.stat().st_size
print(f"\n=== 完了 ===")
print(f"出力: {OUTPUT.name}")
print(f"ファイルサイズ: {size:,} bytes ({size/1024/1024:.2f} MB)")
