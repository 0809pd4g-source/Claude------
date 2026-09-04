#!/usr/bin/env python3
"""
v8_to_v9_content_update.py

変更内容:
  1. BGMプレイリスト削除（歴史タブ内）
  2. ローカルフード図鑑追加（エリア・宿タブ末尾）
  3. 緊急連絡先まとめ追加（安心ガイドタブ末尾）
  4. 現地タブー&マナーカード追加（安心ガイドタブ末尾）
  5. 重量配分シート縮小（服装タブ）
"""
from pathlib import Path

BASE   = Path(__file__).parent.parent / "02_output"
INPUT  = BASE / "20260901_新婚旅行しおり_v8.html"
OUTPUT = BASE / "20260901_新婚旅行しおり_v9.html"

html = INPUT.read_text(encoding="utf-8")
print(f"読み込み: {len(html):,} chars")

# ══════════════════════════════════════════════════════════
# 1. BGMプレイリスト削除
# ══════════════════════════════════════════════════════════
GRADIENT_UNIQUE = "from-amber-700 via-purple-800 to-sky-800"
BGM_END_MARKER  = "\n      <!-- スポット別 現地活用ガイド -->"
assert GRADIENT_UNIQUE in html and BGM_END_MARKER in html

bgm_pos       = html.find(GRADIENT_UNIQUE)
bgm_div_start = html.rfind("\n      <div", 0, bgm_pos)
bgm_div_end   = html.find(BGM_END_MARKER)
html = html[:bgm_div_start] + html[bgm_div_end:]
print(f"1. BGM削除OK ({bgm_div_end - bgm_div_start:,}chars削除)")

# ══════════════════════════════════════════════════════════
# 2. ローカルフード図鑑をエリア・宿タブの末尾に挿入
# ══════════════════════════════════════════════════════════
SOUVENIR_ANCHOR = '<section id="tab-souvenir"'
assert SOUVENIR_ANCHOR in html
spots_end_pos = html.rfind("</section>", 0, html.find(SOUVENIR_ANCHOR))
assert spots_end_pos > 0

FOOD_SECTION = """
      <!-- ローカルフード図鑑 -->
      <div class="bg-white rounded-2xl shadow-xs border border-slate-200 p-4 sm:p-5 space-y-3">
        <div class="flex items-center space-x-2 border-b border-slate-100 pb-2">
          <span class="text-xl">🍽️</span>
          <div>
            <h2 class="font-bold text-slate-800 text-sm sm:text-base">ローカルフード図鑑（エジプト&amp;ギリシャ）</h2>
            <p class="text-xs text-slate-500">🟢乳製品なし安全 ／ 🔴乳製品あり注意 ／ 💡おすすめ度</p>
          </div>
        </div>
        <div class="grid grid-cols-1 sm:grid-cols-2 gap-3">

          <!-- エジプト料理 -->
          <div class="space-y-2">
            <div class="text-[11px] font-bold text-amber-800 uppercase tracking-wide pb-1 border-b border-amber-100">🐫 エジプト料理</div>
            <div class="space-y-1.5 text-xs text-slate-700">
              <div class="p-2 bg-amber-50 rounded-lg border border-amber-200">
                <div class="flex justify-between items-start"><span class="font-bold text-amber-900">コシャリ (Koshari)</span><span class="text-[10px]">🟢 💡💡💡</span></div>
                <p>米・レンズ豆・マカロニ・フライドオニオン・トマトソースの重ね盛り。エジプトのソウルフード。30〜50EGP。乳製品なし！</p>
              </div>
              <div class="p-2 bg-amber-50 rounded-lg border border-amber-200">
                <div class="flex justify-between items-start"><span class="font-bold text-amber-900">タアミーヤ (Ta'amiya)</span><span class="text-[10px]">🟢 💡💡</span></div>
                <p>空豆ベースのファラフェル。朝食の定番。ピタパンに挟んで食べる。</p>
              </div>
              <div class="p-2 bg-amber-50 rounded-lg border border-amber-200">
                <div class="flex justify-between items-start"><span class="font-bold text-amber-900">フール (Ful Medames)</span><span class="text-[10px]">🟢 💡💡</span></div>
                <p>空豆の煮込み。オリーブ油・レモン・クミンで調味。ルクソールの朝食定番。</p>
              </div>
              <div class="p-2 bg-amber-50 rounded-lg border border-amber-200">
                <div class="flex justify-between items-start"><span class="font-bold text-amber-900">コフタ (Kofta)</span><span class="text-[10px]">🟢 💡💡💡</span></div>
                <p>スパイス入り挽き肉の串焼き。どこでも食べられる安定の一品。</p>
              </div>
              <div class="p-2 bg-amber-50 rounded-lg border border-amber-200">
                <div class="flex justify-between items-start"><span class="font-bold text-amber-900">ハンマム (Hamam)</span><span class="text-[10px]">🟢 💡</span></div>
                <p>鳩料理。カイロの珍味。レストランでのフルコースで登場することが多い。</p>
              </div>
              <div class="p-2 bg-amber-50 rounded-lg border border-amber-200">
                <div class="flex justify-between items-start"><span class="font-bold text-amber-900">シャワルマ (Shawarma)</span><span class="text-[10px]">🟢 💡💡</span></div>
                <p>中東版ケバブ。回転肉をピタパンに挟む。ファストフードとして街中に。</p>
              </div>
              <div class="p-2 bg-white rounded-lg border border-amber-200 text-[11px] text-amber-800">⚠️ <strong>注意：</strong>路上の食べ物・生水は避ける。ボトル水を必ず使用。</div>
            </div>
          </div>

          <!-- ギリシャ料理 -->
          <div class="space-y-2">
            <div class="text-[11px] font-bold text-sky-800 uppercase tracking-wide pb-1 border-b border-sky-100">🏛️ ギリシャ料理</div>
            <div class="space-y-1.5 text-xs text-slate-700">
              <div class="p-2 bg-sky-50 rounded-lg border border-sky-200">
                <div class="flex justify-between items-start"><span class="font-bold text-sky-900">スブラキ (Souvlaki)</span><span class="text-[10px]">🟢 💡💡💡</span></div>
                <p>豚・鶏の串焼き肉。ピタパン包みが人気。プラカでのランチに最適。</p>
              </div>
              <div class="p-2 bg-sky-50 rounded-lg border border-sky-200">
                <div class="flex justify-between items-start"><span class="font-bold text-sky-900">ギリシャサラダ (Horiatiki)</span><span class="text-[10px]">🔴 💡💡💡</span></div>
                <p>トマト・オリーブ・フェタチーズ。乳製品注意。「No feta please」で対応可。</p>
              </div>
              <div class="p-2 bg-sky-50 rounded-lg border border-sky-200">
                <div class="flex justify-between items-start"><span class="font-bold text-sky-900">ムサカ (Moussaka)</span><span class="text-[10px]">🔴 💡💡</span></div>
                <p>挽き肉＋ナス＋ベシャメルソースの重ね焼き。乳製品（ベシャメル）あり注意。</p>
              </div>
              <div class="p-2 bg-sky-50 rounded-lg border border-sky-200">
                <div class="flex justify-between items-start"><span class="font-bold text-sky-900">タラモサラダ (Taramosalata)</span><span class="text-[10px]">🟢 💡💡</span></div>
                <p>タラコ入りクリーミーなディップ。パンにつけて食べる前菜。乳製品なし。</p>
              </div>
              <div class="p-2 bg-sky-50 rounded-lg border border-sky-200">
                <div class="flex justify-between items-start"><span class="font-bold text-sky-900">ツァツィキ (Tzatziki)</span><span class="text-[10px]">🔴</span></div>
                <p>ヨーグルト＋きゅうりのディップ。<strong>乳製品あり注意。</strong></p>
              </div>
              <div class="p-2 bg-sky-50 rounded-lg border border-sky-200">
                <div class="flex justify-between items-start"><span class="font-bold text-sky-900">フレスカダ (Frescada)</span><span class="text-[10px]">🟢 💡</span></div>
                <p>イア周辺のカフェで出るトマト・オリーブの素朴なサラダ。サントリーニ産。</p>
              </div>
              <div class="p-2 bg-white rounded-lg border border-sky-200 text-[11px] text-sky-800">💡 <strong>サントリーニ：</strong>地元産アシルティコ白ワインがシーフードと絶品。乳製品なし料理が多い。</div>
            </div>
          </div>

        </div>
      </div>

"""

html = html[:spots_end_pos] + FOOD_SECTION + html[spots_end_pos:]
print(f"2. フード図鑑追加OK")

# ══════════════════════════════════════════════════════════
# 3 & 4. 緊急連絡先 + タブー&マナーカードを安心ガイドタブ末尾に挿入
# ══════════════════════════════════════════════════════════
PHRASES_ANCHOR = '<section id="tab-phrases"'
assert PHRASES_ANCHOR in html
tips_end_pos = html.rfind("</section>", 0, html.find(PHRASES_ANCHOR))
assert tips_end_pos > 0

EMERGENCY_AND_MANNERS = """
      <!-- 緊急連絡先まとめ -->
      <div class="bg-red-50 border border-red-200 rounded-2xl p-4 sm:p-5 space-y-3">
        <div class="flex items-center space-x-2 border-b border-red-200 pb-2">
          <span class="text-xl">🆘</span>
          <div>
            <h2 class="font-bold text-red-900 text-sm sm:text-base">緊急連絡先まとめ（お守り）</h2>
            <p class="text-xs text-red-700">このページを見せるだけでOK。スクショも推奨。</p>
          </div>
        </div>
        <div class="grid grid-cols-1 sm:grid-cols-2 gap-3 text-xs">

          <!-- 大使館 -->
          <div class="p-3 bg-white rounded-xl border border-red-200 space-y-2">
            <div class="font-bold text-red-800 text-[11px] uppercase tracking-wide">🏛️ 日本大使館</div>
            <div class="space-y-1.5">
              <div class="flex justify-between items-center p-1.5 bg-red-50 rounded border border-red-100">
                <span class="font-bold text-slate-800">在エジプト日本大使館</span>
                <span class="font-mono text-red-800 font-bold">+20-2-2528-5910</span>
              </div>
              <div class="text-[10px] text-slate-500 pl-1">カイロ 勤務時間外の緊急は留守電から連絡先を確認</div>
              <div class="flex justify-between items-center p-1.5 bg-red-50 rounded border border-red-100">
                <span class="font-bold text-slate-800">在ギリシャ日本大使館</span>
                <span class="font-mono text-red-800 font-bold">+30-210-670-9900</span>
              </div>
              <div class="text-[10px] text-slate-500 pl-1">アテネ Ethnikis Antistaseos 46, Halandri</div>
            </div>
          </div>

          <!-- 現地緊急番号 -->
          <div class="p-3 bg-white rounded-xl border border-red-200 space-y-2">
            <div class="font-bold text-red-800 text-[11px] uppercase tracking-wide">🚨 現地緊急番号</div>
            <div class="space-y-1 text-[11px]">
              <div class="font-bold text-amber-800 mt-1">🐫 エジプト</div>
              <div class="grid grid-cols-2 gap-1">
                <div class="p-1 bg-amber-50 rounded text-center"><div class="font-mono font-bold text-amber-900">122</div><div class="text-slate-500">警察</div></div>
                <div class="p-1 bg-amber-50 rounded text-center"><div class="font-mono font-bold text-amber-900">123</div><div class="text-slate-500">救急</div></div>
                <div class="p-1 bg-amber-50 rounded text-center"><div class="font-mono font-bold text-amber-900">126</div><div class="text-slate-500">観光警察</div></div>
                <div class="p-1 bg-amber-50 rounded text-center"><div class="font-mono font-bold text-amber-900">180</div><div class="text-slate-500">消防</div></div>
              </div>
              <div class="font-bold text-sky-800 mt-1">🏛️ ギリシャ</div>
              <div class="grid grid-cols-2 gap-1">
                <div class="p-1 bg-sky-50 rounded text-center"><div class="font-mono font-bold text-sky-900">100</div><div class="text-slate-500">警察</div></div>
                <div class="p-1 bg-sky-50 rounded text-center"><div class="font-mono font-bold text-sky-900">166</div><div class="text-slate-500">救急</div></div>
                <div class="p-1 bg-sky-50 rounded text-center"><div class="font-mono font-bold text-sky-900">199</div><div class="text-slate-500">消防</div></div>
                <div class="p-1 bg-sky-50 rounded text-center"><div class="font-mono font-bold text-sky-900">171</div><div class="text-slate-500">観光警察（英語）</div></div>
              </div>
            </div>
          </div>

          <!-- クレカ紛失 -->
          <div class="p-3 bg-white rounded-xl border border-red-200 space-y-2">
            <div class="font-bold text-red-800 text-[11px] uppercase tracking-wide">💳 クレカ紛失・盗難（海外から）</div>
            <div class="space-y-1.5 text-[11px]">
              <div class="text-[10px] text-slate-500 mb-1">持参カード4枚 — カード裏面の番号を出発前に写真で保存すること</div>
              <div class="flex justify-between p-1.5 bg-rose-50 rounded border border-rose-200">
                <span class="font-bold">楽天カード 海外緊急</span>
                <span class="font-mono text-red-800">+81-3-6893-3770</span>
              </div>
              <div class="flex justify-between p-1.5 bg-rose-50 rounded border border-rose-200">
                <span class="font-bold">エポスカード 海外緊急</span>
                <span class="font-mono text-red-800">+81-3-3383-4560</span>
              </div>
              <div class="flex justify-between p-1.5 bg-rose-50 rounded border border-rose-200">
                <span class="font-bold">PayPayカード 海外緊急</span>
                <span class="font-mono text-red-800">+81-3-6737-3200</span>
              </div>
              <div class="flex justify-between p-1.5 bg-rose-50 rounded border border-rose-200">
                <span class="font-bold">三井住友カード 海外緊急</span>
                <span class="font-mono text-red-800">+81-3-6627-4520</span>
              </div>
              <div class="p-1.5 bg-slate-50 rounded border border-slate-200">
                <div class="text-[10px] text-slate-500">ネットワーク共通（カード番号不明時）: VISA +1-303-967-1096 / MC +1-636-722-7111</div>
              </div>
            </div>
          </div>

          <!-- 旅行保険・航空会社 -->
          <div class="p-3 bg-white rounded-xl border border-red-200 space-y-2">
            <div class="font-bold text-red-800 text-[11px] uppercase tracking-wide">✈️ 航空会社・保険</div>
            <div class="space-y-1.5 text-[11px]">
              <div class="flex justify-between p-1.5 bg-slate-50 rounded border border-slate-200">
                <span class="font-bold">エジプト航空 カイロ</span>
                <span class="font-mono text-slate-800">+20-2-2267-4700</span>
              </div>
              <div class="p-2 bg-amber-50 rounded border border-amber-200">
                <div class="font-bold text-amber-900 mb-1">旅行保険緊急デスク</div>
                <div class="text-slate-500">← ここに保険証書の番号を書いておく</div>
                <div class="mt-1 h-6 border-b border-dashed border-amber-300"></div>
              </div>
              <p class="text-[10px] text-slate-500">保険証書は紙で印刷して財布に。海外のATMは手数料に注意。</p>
            </div>
          </div>

        </div>
      </div>

      <!-- 現地タブー&マナーカード -->
      <div class="bg-white rounded-2xl shadow-xs border border-slate-200 p-4 sm:p-5 space-y-3">
        <div class="flex items-center space-x-2 border-b border-slate-100 pb-2">
          <span class="text-xl">🙏</span>
          <div>
            <h2 class="font-bold text-slate-800 text-sm sm:text-base">現地タブー&amp;マナーカード</h2>
            <p class="text-xs text-slate-500">知らずにやってしまうミスを防ぐ。出発前に一読を。</p>
          </div>
        </div>
        <div class="grid grid-cols-1 sm:grid-cols-2 gap-3 text-xs text-slate-700">

          <!-- エジプトのマナー -->
          <div class="p-3 bg-amber-50 rounded-xl border border-amber-200 space-y-2">
            <div class="font-bold text-amber-900 text-[11px] uppercase tracking-wide">🐫 エジプト編</div>
            <div class="space-y-1.5">
              <div class="flex gap-2 p-1.5 bg-red-50 rounded border border-red-200">
                <span class="text-red-600 shrink-0">❌</span>
                <div><strong>写真撮影NG：</strong>軍・警察・橋・空港・政府施設。必ず確認を。人物は「May I?」と許可を取る。</div>
              </div>
              <div class="flex gap-2 p-1.5 bg-red-50 rounded border border-red-200">
                <span class="text-red-600 shrink-0">❌</span>
                <div><strong>左手でのNG：</strong>握手・食事・物の受け渡しは右手で。左手は不潔とされる。</div>
              </div>
              <div class="flex gap-2 p-1.5 bg-amber-100 rounded border border-amber-300">
                <span class="text-amber-600 shrink-0">⚠️</span>
                <div><strong>モスク入場：</strong>肌を隠す（女性はスカーフ持参）。靴脱ぎ必須。礼拝時間（アザーン後）は入場不可。</div>
              </div>
              <div class="flex gap-2 p-1.5 bg-amber-100 rounded border border-amber-300">
                <span class="text-amber-600 shrink-0">⚠️</span>
                <div><strong>バクシーシュ（チップ）：</strong>写真撮影の案内・トイレ使用など随所で求められる。1〜5EGP（20〜100円）程度を常備。</div>
              </div>
              <div class="flex gap-2 p-1.5 bg-amber-100 rounded border border-amber-300">
                <span class="text-amber-600 shrink-0">⚠️</span>
                <div><strong>値切り交渉：</strong>バザールでは必須。最初の言い値の30〜50%が相場。笑顔で楽しく。</div>
              </div>
              <div class="flex gap-2 p-1.5 bg-emerald-50 rounded border border-emerald-200">
                <span class="text-emerald-600 shrink-0">✅</span>
                <div><strong>スナップ写真：</strong>「Surah?（写真いいですか？）」と聞くと喜ばれる。子供の写真はチップ要求に注意。</div>
              </div>
            </div>
          </div>

          <!-- ギリシャのマナー -->
          <div class="p-3 bg-sky-50 rounded-xl border border-sky-200 space-y-2">
            <div class="font-bold text-sky-900 text-[11px] uppercase tracking-wide">🏛️ ギリシャ編</div>
            <div class="space-y-1.5">
              <div class="flex gap-2 p-1.5 bg-red-50 rounded border border-red-200">
                <span class="text-red-600 shrink-0">❌</span>
                <div><strong>アクロポリス厳禁：</strong>飲食・石の上に座るのは完全禁止。水も石の上にこぼさないよう注意。</div>
              </div>
              <div class="flex gap-2 p-1.5 bg-red-50 rounded border border-red-200">
                <span class="text-red-600 shrink-0">❌</span>
                <div><strong>軍・政府施設の撮影：</strong>エジプト同様に注意。特に変電所・基地付近。</div>
              </div>
              <div class="flex gap-2 p-1.5 bg-amber-100 rounded border border-amber-300">
                <span class="text-amber-600 shrink-0">⚠️</span>
                <div><strong>正教会の礼拝堂：</strong>肌の露出を控える。短パン・タンクトップで入ると断られることあり。</div>
              </div>
              <div class="flex gap-2 p-1.5 bg-amber-100 rounded border border-amber-300">
                <span class="text-amber-600 shrink-0">⚠️</span>
                <div><strong>サービスの速度：</strong>レストランはゆっくりが普通。急かすのは失礼。のんびり楽しむのが文化。</div>
              </div>
              <div class="flex gap-2 p-1.5 bg-amber-100 rounded border border-amber-300">
                <span class="text-amber-600 shrink-0">⚠️</span>
                <div><strong>チップ：</strong>必須ではないが10%程度が一般的。カード払いの場合も現金チップが喜ばれる。</div>
              </div>
              <div class="flex gap-2 p-1.5 bg-emerald-50 rounded border border-emerald-200">
                <span class="text-emerald-600 shrink-0">✅</span>
                <div><strong>Evil Eye（青い目）：</strong>お土産として買っても全く問題なし。魔除けの縁起物として喜ばれる。</div>
              </div>
            </div>
          </div>

        </div>
      </div>

"""

html = html[:tips_end_pos] + EMERGENCY_AND_MANNERS + html[tips_end_pos:]
print(f"3&4. 緊急連絡先+マナーカード追加OK")

# ══════════════════════════════════════════════════════════
# 5. 重量配分シートを縮小（h2タグで特定→次のdivまでを差し替え）
# ══════════════════════════════════════════════════════════
WEIGHT_H2 = "重量配分シート</h2>"
assert WEIGHT_H2 in html
weight_pos = html.find(WEIGHT_H2)
weight_div_start = html.rfind("\n      <div", 0, weight_pos)

# 重量配分はtab-packingの最終divのため、次のdivがtab-tipsに入り込む。
# tab-tipsの開始位置を上限として正確な境界を設定する。
tips_section_pos = html.find('id="tab-tips"')
assert tips_section_pos > 0
packing_close = html.rfind("\n    </section>", 0, tips_section_pos)

weight_div_end = html.find("\n      <div", weight_div_start + 20)
if weight_div_end == -1 or weight_div_end > packing_close:
    weight_div_end = packing_close

old_weight = html[weight_div_start:weight_div_end]
print(f"重量配分 section length: {len(old_weight)}")

NEW_WEIGHT = """
      <div class="bg-white rounded-2xl shadow-xs border border-slate-200 p-4 sm:p-5 space-y-3">
        <div class="flex items-center space-x-2 border-b border-slate-100 pb-2">
          <span class="text-xl">⚖️</span>
          <h2 class="font-bold text-slate-800 text-sm sm:text-base">重量配分シート（簡易版）</h2>
        </div>
        <div class="overflow-x-auto text-xs">
          <table class="w-full border-collapse">
            <thead><tr class="bg-slate-50">
              <th class="p-2 text-left border border-slate-200">区間</th>
              <th class="p-2 text-center border border-slate-200">預入<br>（上限23kg）</th>
              <th class="p-2 text-center border border-slate-200">機内持込<br>（上限7kg）</th>
              <th class="p-2 text-left border border-slate-200">ポイント</th>
            </tr></thead>
            <tbody>
              <tr><td class="p-2 border border-slate-200 font-bold text-amber-800">行き<br>成田→カイロ</td><td class="p-2 border border-slate-200 text-center">衣類・日用品<br>一式</td><td class="p-2 border border-slate-200 text-center">カメラ・PC<br>貴重品</td><td class="p-2 border border-slate-200 text-slate-600">液体は100ml以下。現金・パスポートは必ず機内持込</td></tr>
              <tr class="bg-slate-50"><td class="p-2 border border-slate-200 font-bold text-sky-800">乗継・移動区間<br>（国内便含む）</td><td class="p-2 border border-slate-200 text-center">同上（都度確認）</td><td class="p-2 border border-slate-200 text-center">同上</td><td class="p-2 border border-slate-200 text-slate-600">国内線は規定が異なる場合あり。スーツケースが満杯なら送らず手持ちで分散</td></tr>
              <tr><td class="p-2 border border-slate-200 font-bold text-emerald-800">帰り<br>アテネ→成田</td><td class="p-2 border border-slate-200 text-center">お土産追加<br>（重量注意）</td><td class="p-2 border border-slate-200 text-center">同上＋免税品</td><td class="p-2 border border-slate-200 text-slate-600">お土産で荷物が増える。帰りは荷物を計量してから出発を。超過料金は高額</td></tr>
            </tbody>
          </table>
        </div>
        <div class="text-[11px] text-slate-500">機内持込必須：パスポート・現金・クレカ・薬・カメラ・充電器。スーツケースには鍵をかけ、TSAロック推奨。</div>
      </div>
"""

html = html[:weight_div_start] + NEW_WEIGHT + html[weight_div_end:]
print("5. 重量配分縮小OK")

# ══════════════════════════════════════════════════════════
# 出力
# ══════════════════════════════════════════════════════════
OUTPUT.write_text(html, encoding="utf-8")
size = OUTPUT.stat().st_size
print(f"\n=== 完了 ===  {OUTPUT.name}  {size/1024/1024:.2f} MB")
