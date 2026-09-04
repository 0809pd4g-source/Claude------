#!/usr/bin/env python3
"""
v3_to_v4_tips_reorg.py
v3 → v4 の改修スクリプト。

変更内容:
  1. 安心ガイド・TipsタブへeSIM詳細版を拡充（既存の簡易eSIM欄を差し替え）
  2. 安心ガイド・Tipsタブへ「移動手段（配車アプリ・交通）」セクション追加
  3. 安心ガイド・Tipsタブへ「決済・通貨・チップ完全ガイド」セクション追加
  4. 「全フライト手荷物・受託規定＆機材注意点」をToDoタブから
      安心ガイド・Tipsタブへ移管し、ToDoタブ側は削除

入力: 02_output/20260901_新婚旅行しおり_v3.html
出力: 02_output/20260901_新婚旅行しおり_v4.html
"""

from pathlib import Path

BASE   = Path(__file__).parent.parent / "02_output"
INPUT  = BASE / "20260901_新婚旅行しおり_v3.html"
OUTPUT = BASE / "20260901_新婚旅行しおり_v4.html"

html = INPUT.read_text(encoding="utf-8")
print(f"読み込み完了: {len(html):,} chars")

# ══════════════════════════════════════════════════════════
# Step 1: ToDoタブの手荷物規定ブロックを抽出して削除
# ══════════════════════════════════════════════════════════
BAGGAGE_START = '      <!-- 航空会社・手荷物規定サマリー -->'
BAGGAGE_END   = '      <!-- ToDoチェックリスト'

idx_s = html.find(BAGGAGE_START)
idx_e = html.find(BAGGAGE_END)
assert idx_s > 0 and idx_e > 0, "手荷物規定ブロックが見つかりません"

baggage_html = html[idx_s:idx_e]   # Tipsへ移管するHTML
html = html[:idx_s] + "\n      " + html[idx_e:]  # ToDoから削除
print("Step 1: ToDoタブから手荷物規定を抽出・削除")

# ══════════════════════════════════════════════════════════
# Step 2: Tips内の「通信・電源・Wi-Fi環境」を詳細版eSIM欄に差し替え
# ══════════════════════════════════════════════════════════
OLD_ESIM_START = '      <!-- 8. 通信・電源・電圧 -->'
OLD_ESIM_END   = '      <!-- 9. 緊急連絡先 -->'

idx_s2 = html.find(OLD_ESIM_START)
idx_e2 = html.find(OLD_ESIM_END)
assert idx_s2 > 0 and idx_e2 > 0, "通信・電源ブロックが見つかりません"

NEW_SECTIONS = """\
      <!-- 8A. 移動手段（配車アプリ・交通） -->
      <div class="bg-white rounded-2xl shadow-xs border border-slate-200 p-4 sm:p-5 space-y-3">
        <div class="flex items-center space-x-2 border-b border-slate-100 pb-2">
          <i class="fa-solid fa-car text-emerald-600 text-lg"></i>
          <div>
            <h2 class="font-bold text-slate-800 text-sm sm:text-base">🚗 移動手段完全ガイド（配車アプリ・交通）</h2>
            <p class="text-xs text-slate-500">ぼったくり防止のためUber/Careem推奨。タクシー交渉は最終手段</p>
          </div>
        </div>
        <div class="grid grid-cols-1 sm:grid-cols-2 gap-3 text-xs text-slate-700 leading-relaxed">
          <div class="p-3 bg-amber-50 rounded-xl border border-amber-200 space-y-2">
            <strong class="text-amber-900 block">🇪🇬 エジプト（カイロ・ギザ・ルクソール）</strong>
            <p>📱 <strong>Uber（推奨・第1選択）：</strong> カイロ・ギザで使用可。料金が事前確定でぼったくりゼロ。アプリで日本語表示可。空港からホテルへはUberが最安・最安心。</p>
            <p>📱 <strong>Careem（カリーム）：</strong> 中東最大の配車アプリ。UberがつながらないときはCareemを使う。</p>
            <p>⚠️ <strong>ルクソール内移動：</strong> Uberのカバレッジが限定的。ホテルに手配を依頼するかツアー専用車を利用。</p>
            <p>🚕 <strong>白タク（交渉タクシー）：</strong> 相場の3〜5倍を吹っかけられます。Uberが使えない場面のみ、乗車前に料金を書いてもらい合意してから乗る。</p>
            <p>🚉 <strong>カイロ地下鉄（メトロ）：</strong> Line 1/2/3が運行。料金5〜7EGPで激安。女性専用車両あり。ザマレク等の観光には不向き（最寄駅が遠い）。</p>
          </div>
          <div class="p-3 bg-sky-50 rounded-xl border border-sky-200 space-y-2">
            <strong class="text-sky-900 block">🇬🇷 ギリシャ（アテネ・サントリーニ）</strong>
            <p>📱 <strong>Uber（アテネ）：</strong> アテネ市内で使用可。ただしギリシャではUberはプロドライバー登録のみのため一般タクシーより少し高め。Beat（旧Taxibeat）も有力な代替アプリ。</p>
            <p>🚇 <strong>アテネ地下鉄（Metro）：</strong> アクロポリス駅・シンタグマ駅等が観光拠点。1回券1.2€。空港↔シンタグマは9€（約45分）で快適。</p>
            <p>🚌 <strong>空港バス X95：</strong> アテネ空港↔シンタグマ広場を約1時間で結ぶ。料金5€。深夜・早朝も運行。</p>
            <p>🚗 <strong>サントリーニ島内：</strong> 島の公共バス（KTEL）はフィラ起点で1〜3€。イア行きは本数あり。タクシーは割高（フィラ↔イア約20€）。Uberは使用不可。</p>
            <p>⚓ <strong>港↔島内：</strong> サントリーニ港（アティニオス）からフィラ中心部はバスまたはタクシー。荷物が多い場合はホテルの送迎を事前手配が安心。</p>
          </div>
        </div>
      </div>

      <!-- 8B. 決済・通貨・チップ完全ガイド -->
      <div class="bg-white rounded-2xl shadow-xs border border-slate-200 p-4 sm:p-5 space-y-3">
        <div class="flex items-center space-x-2 border-b border-slate-100 pb-2">
          <i class="fa-solid fa-money-bill-wave text-emerald-600 text-lg"></i>
          <div>
            <h2 class="font-bold text-slate-800 text-sm sm:text-base">💴 決済・通貨・チップ完全ガイド</h2>
            <p class="text-xs text-slate-500">3通貨（EGP/EUR/USD）の使い分けとキャッシュレス事情</p>
          </div>
        </div>
        <div class="grid grid-cols-1 sm:grid-cols-2 gap-3 text-xs text-slate-700 leading-relaxed">
          <div class="p-3 bg-amber-50 rounded-xl border border-amber-200 space-y-2">
            <strong class="text-amber-900 block">🇪🇬 エジプト（EGP・USD）</strong>
            <p>💳 <strong>カード払い：</strong> 高級ホテル・大手レストラン・EMCでVisa/Masterが使用可。スーク・ローカル食堂・交通は現金のみ。</p>
            <p>💵 <strong>USD新札（ピン札）：</strong> アライバルビザ（25USD×人数）は必ずUSドル新札で支払う。古い・折れ曲がった紙幣は断られることあり。</p>
            <p>💱 <strong>両替場所：</strong> 空港銀行窓口（手数料やや高め）またはホテルフロント（レート良好）。スーク内の両替所は交渉次第だが詐欺リスクあり。</p>
            <p>🏧 <strong>ATM：</strong> 主要空港・ホテルのATMでVisaからEGP引き出し可（手数料50〜100EGP程度）。観光地外では壊れているATMも多い。</p>
            <p>💰 <strong>チップ（バクシーシ）：</strong> エジプト文化の根幹。トイレ10〜20EGP、ポーター20〜50EGP、ドライバー200〜300EGP/組、ガイド300〜500EGP/組が相場。小額EGP紙幣を常に財布の取り出しやすい場所に分けておく。</p>
          </div>
          <div class="p-3 bg-sky-50 rounded-xl border border-sky-200 space-y-2">
            <strong class="text-sky-900 block">🇬🇷 ギリシャ（EUR）</strong>
            <p>💳 <strong>カード払い：</strong> アテネ・サントリーニのレストラン・ホテル・土産店はほぼカード対応（Visa/Master）。むしろ現金を持ちすぎる必要なし。</p>
            <p>💶 <strong>ユーロ現金：</strong> 島のキオスク・小規模カフェ・バス・港の売店は現金のみ。100〜150€あれば十分。</p>
            <p>🏧 <strong>ATM：</strong> アテネ・フィラ中心部にATMあり。海外引き出し手数料（銀行＋ATM）で1回300〜500円程度かかるため最小限の利用に。</p>
            <p>💰 <strong>チップ（ギリシャ）：</strong> 義務ではないが慣習。レストランでは端数の切り上げが一般的（例：請求43.5€→45€渡す）。タクシーは端数切り上げ程度。ホテルポーターには1〜2€/個。</p>
            <p>🚫 <strong>ダイナーズ・AmEx：</strong> 使えない店が多い。VISAまたはMastercardを持参すること。</p>
          </div>
        </div>
      </div>

      <!-- 8C. SIM・eSIM・Wi-Fi詳細ガイド ＆ 電源・電圧 -->
      <div class="bg-white rounded-2xl shadow-xs border border-slate-200 p-4 sm:p-5 space-y-3">
        <div class="flex items-center space-x-2 border-b border-slate-100 pb-2">
          <i class="fa-solid fa-plug text-indigo-600 text-lg"></i>
          <h2 class="font-bold text-slate-800 text-sm sm:text-base">📶 SIM・eSIM・Wi-Fi詳細ガイド ＆ 電源・電圧</h2>
        </div>
        <div class="grid grid-cols-1 sm:grid-cols-2 gap-3 text-xs text-slate-700 leading-relaxed">
          <div class="p-3 bg-indigo-50 rounded-xl border border-indigo-200 space-y-2">
            <strong class="text-indigo-900 block">🇪🇬 エジプトの通信事情</strong>
            <p>📱 <strong>eSIM（推奨）：</strong> AiraloやHolafly等のeSIMアプリで事前購入・設定が最も楽。「Egypt 10GB / 15日」が1,500〜2,000円程度。</p>
            <p>📡 <strong>現地SIM：</strong> カイロ空港到着ロビーにOrange・Vodafone Egyptのショップあり。パスポート提示で即日発行。10GB/1週間で約150〜200EGP（約500〜600円）。</p>
            <p>🏨 <strong>ホテルWi-Fi：</strong> 高級ホテルは概ね良好だが、白砂漠キャンプは<strong>完全圏外</strong>。出発前に家族へ連絡・Googleマップオフラインをダウンロードしておく。</p>
            <p>🔒 <strong>eSIM注意：</strong> iPhoneのデュアルSIM設定で「データ通信 = eSIM」、「通話 = 日本SIM」にすると日本への緊急電話も可能。</p>
          </div>
          <div class="p-3 bg-sky-50 rounded-xl border border-sky-200 space-y-2">
            <strong class="text-sky-900 block">🇬🇷 ギリシャ・EU圏の通信事情</strong>
            <p>📱 <strong>eSIM（推奨）：</strong> AiraloのEurope eSIM（EU全土対応10GB）が約2,000〜2,500円で最もコスパ良好。エジプト出国後、ギリシャ入国と同時にeSIMを切り替える。</p>
            <p>📡 <strong>現地SIM：</strong> アテネ空港・市内のCosmoTE・Vodafone GRショップで購入可。EU漫遊プラン対応でサントリーニでも使える。</p>
            <p>🏨 <strong>島内Wi-Fi：</strong> フィラ・イア・イメロヴィグリのホテルは概ね良好。カルデラビュー断崖のホテルは地形の関係でやや不安定なことも。</p>
            <p>🔌 <strong>電源プラグ・電圧（共通）：</strong> エジプト・ギリシャともに<strong>Cタイプ（丸ピン2本）・220V</strong>。スマホ・カメラ充電器は全世界対応100-240Vのため変圧器不要。念のため変換アダプター1個を持参。</p>
          </div>
        </div>
      </div>

"""

# 手荷物規定ブロックをTipsへ（ヘッダーだけ若干調整して挿入）
BAGGAGE_IN_TIPS = baggage_html.replace(
    '<!-- 航空会社・手荷物規定サマリー -->',
    '<!-- 8D. 全フライト手荷物・受託規定（ToDoタブより移管） -->'
)

NEW_SECTIONS += BAGGAGE_IN_TIPS + "\n      "

html = html[:idx_s2] + NEW_SECTIONS + "      " + html[idx_e2:]
print("Step 2: Tips内の旧eSIM欄を詳細版3セクション＋手荷物規定に差し替え")

# ══════════════════════════════════════════════════════════
# 出力
# ══════════════════════════════════════════════════════════
OUTPUT.write_text(html, encoding="utf-8")
size = OUTPUT.stat().st_size
print(f"\n完了: {OUTPUT.name} ({size:,} bytes / {size/1024/1024:.2f} MB)")
