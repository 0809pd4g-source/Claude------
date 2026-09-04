#!/usr/bin/env python3
"""
add_photo_sections.py
v2 のフォトタブに欠落していた4セクションを追加して v3 を生成する。

追加内容:
  1. ハネムーン映え構図＆ポーズ図鑑（ギザ/白砂漠/ルクソール/サントリーニ）
  2. 撮影マナー・法律・厳格禁止事項
  3. ストリートスナップ極意＆映え路地マップ（4エリア）
  4. 望遠レンズ＆ズームで狙う！遠景・圧縮効果ポイント（4エリア）

入力: 02_output/20260901_新婚旅行しおり_v2.html
出力: 02_output/20260901_新婚旅行しおり_v3.html
"""

from pathlib import Path

BASE  = Path(__file__).parent.parent / "02_output"
INPUT  = BASE / "20260901_新婚旅行しおり_v2.html"
OUTPUT = BASE / "20260901_新婚旅行しおり_v3.html"

# ────────────────────────────────────────────────────────
# 追加するHTMLブロック（フォトタブ closing </section> の直前に挿入）
# ────────────────────────────────────────────────────────
PHOTO_ADDITIONS = """
      <!-- ① ハネムーン映え構図＆ポーズ図鑑 -->
      <div class="bg-gradient-to-r from-rose-50 to-pink-50 border border-rose-200 rounded-2xl p-4 sm:p-5 shadow-xs space-y-4">
        <div class="flex items-center space-x-2.5 border-b border-rose-200 pb-3">
          <i class="fa-solid fa-heart text-rose-500 text-lg"></i>
          <div>
            <h2 class="font-bold text-rose-950 text-sm sm:text-base">💑 ハネムーン映え構図＆ポーズ図鑑</h2>
            <p class="text-xs text-rose-700">各スポットのベストショット・シャッターチャンス早見表</p>
          </div>
        </div>
        <div class="grid grid-cols-1 sm:grid-cols-2 gap-3 text-xs text-slate-700 leading-relaxed">
          <div class="p-3 bg-white rounded-xl border border-amber-200 space-y-2">
            <strong class="text-amber-900 block">🐪 ギザ・ピラミッド</strong>
            <p>・<strong>遠近法マジック：</strong> パノラマポイントから「クフ王の頂点に手を乗せる」構図。iPhone超広角（0.5x）＋パートナーを手前に大きく配置。</p>
            <p>・<strong>スフィンクスキス：</strong> スフィンクスの頭部が重なる角度（南東側）から望遠で圧縮。顔を向き合わせてキスショット。</p>
            <p>・<strong>黄金時間帯：</strong> 日没1時間前（オレンジ斜光）か夜明け直後（やわらかい逆光）が最美。</p>
          </div>
          <div class="p-3 bg-white rounded-xl border border-slate-200 space-y-2">
            <strong class="text-slate-800 block">🌌 白砂漠</strong>
            <p>・<strong>夕日逆光シルエット：</strong> 奇岩（マッシュルーム岩）を背景に二人のシルエット。一眼でF8〜F11に絞り逆光を浴びる。</p>
            <p>・<strong>焚き火＆星空：</strong> キャンプ焚き火を前景に天の川バック。SS20秒・ISO4000・F2以下で二人を光彩にシルエット化。</p>
            <p>・<strong>白砂に寝転ぶ：</strong> 俯瞰ショット（脚立やドライバーに撮影依頼）で真っ白な砂漠に寝転ぶ二人を上から。</p>
          </div>
          <div class="p-3 bg-white rounded-xl border border-amber-200 space-y-2">
            <strong class="text-amber-900 block">🛕 ルクソール</strong>
            <p>・<strong>カルナック斜光：</strong> 朝8時台の斜光が石柱の列廊を照らす時間帯。柱の長い影とともに二人が並ぶ構図（一眼レフ）。</p>
            <p>・<strong>ファルーカ夕日乾杯：</strong> ナイル川上のファルーカ船上から夕日をバックに乾杯ショット。RX100でポートレートモード。</p>
            <p>・<strong>ルクソール神殿ライトアップ：</strong> 夜の2回目訪問で黄金ライトアップを背景にロマンティックショット。</p>
          </div>
          <div class="p-3 bg-white rounded-xl border border-sky-200 space-y-2">
            <strong class="text-sky-900 block">🇬🇷 サントリーニ</strong>
            <p>・<strong>ブルードーム手繋ぎ：</strong> イメロヴィグリのブルードームを背景に手を繋ぐ。朝7〜9時台（観光客が少ない）が最適。白壁が逆光になる西側から。</p>
            <p>・<strong>ホテルテラス乾杯：</strong> プール・ジャグジー越しにカルデラ海を望む構図。スパークリングワインを持ってテラスへ。夕方の斜光が美しい。</p>
            <p>・<strong>断崖の階段：</strong> イアへの細道・階段の上下で向き合う構図。白い壁と青い空が額縁になる。iPhone広角が映える。</p>
          </div>
        </div>
      </div>

      <!-- ② 撮影マナー・法律・厳格禁止事項 -->
      <div class="bg-red-50 border border-red-300 rounded-2xl p-4 sm:p-5 shadow-xs space-y-3">
        <div class="flex items-center space-x-2.5 border-b border-red-200 pb-2">
          <i class="fa-solid fa-triangle-exclamation text-red-600 text-lg"></i>
          <h2 class="font-bold text-red-900 text-sm sm:text-base">⚠️ 撮影マナー・法律・厳格禁止事項</h2>
        </div>
        <div class="grid grid-cols-1 sm:grid-cols-2 gap-3 text-xs text-slate-700 leading-relaxed">
          <div class="p-3 bg-white rounded-xl border border-red-200 space-y-2">
            <strong class="text-red-900 block flex items-center gap-1"><i class="fa-solid fa-ban text-red-600"></i> 🇪🇬 エジプト：絶対禁止</strong>
            <p>🚫 <strong>ドローン持ち込み厳禁：</strong> 申請なしの持ち込みは入国時に即没収。最悪の場合、拘束・罰金のリスク。機内預け含め持ち込まないこと。</p>
            <p>🚫 <strong>軍・警察・インフラ施設：</strong> 軍の建物、警察署、橋、ダム等の撮影は法律で禁止（スパイ行為とみなされることあり）。</p>
            <p>🚫 <strong>遺跡内フラッシュ撮影禁止：</strong> 王家の谷・ルクソール神殿などの内部でフラッシュ使用厳禁（壁画の退色防止）。カメラの自動フラッシュは事前にOFFに。</p>
            <p>⚠️ <strong>人物撮影：</strong> 地元の人をカメラで直接狙うと怒られる場合あり。撮る前に「スラ？（撮っていいですか？）」と確認するのがマナー。</p>
          </div>
          <div class="p-3 bg-white rounded-xl border border-red-200 space-y-2">
            <strong class="text-sky-900 block flex items-center gap-1"><i class="fa-solid fa-ban text-red-600"></i> 🇬🇷 ギリシャ：マナー＆禁止</strong>
            <p>🚫 <strong>サントリーニ民家屋根への侵入禁止：</strong> 映えスポットとして有名なブルードーム屋根は民家の私有地。侵入・登頂は厳禁（警察に通報されるケースあり）。路地から撮影を。</p>
            <p>🚫 <strong>アクロポリスの触れる・座る禁止：</strong> パルテノン神殿の大理石柱・石材への接触、段差への着席撮影は禁止。監視員が常駐。</p>
            <p>⚠️ <strong>混雑時間帯を避ける：</strong> 10〜16時は超混雑。映えショットは開場直後（08:00〜09:30）が唯一のチャンス。</p>
          </div>
        </div>
      </div>

      <!-- ③ ストリートスナップ極意＆映え路地マップ -->
      <div class="bg-white border border-slate-200 rounded-2xl p-4 sm:p-5 shadow-xs space-y-4">
        <div class="flex items-center space-x-2.5 border-b border-slate-100 pb-3">
          <i class="fa-solid fa-map-location-dot text-violet-600 text-lg"></i>
          <div>
            <h2 class="font-bold text-slate-800 text-sm sm:text-base">🗺️ ストリートスナップ極意＆映え路地マップ</h2>
            <p class="text-xs text-slate-500">目立たないRX100が主役。歩いて見つける光と影の世界</p>
          </div>
        </div>
        <div class="grid grid-cols-1 sm:grid-cols-2 gap-3 text-xs text-slate-700 leading-relaxed">
          <div class="p-3 bg-violet-50 rounded-xl border border-violet-200 space-y-1.5">
            <strong class="text-violet-900 block">🇬🇷 アテネ「アナフィオティカ地区」</strong>
            <p>アクロポリスの北麓に広がる極小集落。白壁に咲くブーゲンビリア、路地に眠る猫、青いドアと花鉢。手持ちRX100で迷い込むように撮る。早朝7〜8時台は静寂で光も柔らかい。</p>
            <p class="text-violet-700 font-bold">📍 アクロポリス北側出口から徒歩5分</p>
          </div>
          <div class="p-3 bg-amber-50 rounded-xl border border-amber-200 space-y-1.5">
            <strong class="text-amber-900 block">🇪🇬 カイロ「コルバ地区＆ザマレク」</strong>
            <p>ヘリオポリスのコルバ：ベルギー様式の優美なアーチ回廊に差し込む強い南国の斜光。影が長い14〜16時が撮り時。ザマレク島：レトロな集合住宅に生活感あふれる洗濯物と光影。</p>
            <p class="text-amber-700 font-bold">📍 ナイル川中洲のザマレク島・コルバ歴史街区</p>
          </div>
          <div class="p-3 bg-orange-50 rounded-xl border border-orange-200 space-y-1.5">
            <strong class="text-orange-900 block">🛕 ルクソール「東岸スーク」</strong>
            <p>スパイス屋の赤・黄・緑の色彩、布製品の幾何学模様、魚屋のギラつく鱗。ボケ表現（F2.8以下）で手前の香辛料を前景にしつつ奥の商人を主役にする。夕方16〜17時が光と熱気のピーク。</p>
            <p class="text-orange-700 font-bold">📍 ルクソール神殿前の旧市場エリア</p>
          </div>
          <div class="p-3 bg-sky-50 rounded-xl border border-sky-200 space-y-1.5">
            <strong class="text-sky-900 block">🇬🇷 サントリーニ「早朝イメロヴィグリ」</strong>
            <p>幾何学的な白壁と青ドームが整然と並ぶ。観光客が来る前の06:30〜08:00が狙い目。空のグラデーションと建物のコントラストが最大。iPhone超広角でパノラマ状に切り取る。</p>
            <p class="text-sky-700 font-bold">📍 ホテル周辺の細い路地・展望テラス</p>
          </div>
        </div>
      </div>

      <!-- ④ 望遠レンズ＆ズームで狙う！遠景・圧縮効果ポイント -->
      <div class="bg-gradient-to-r from-slate-50 to-slate-100 border border-slate-200 rounded-2xl p-4 sm:p-5 shadow-xs space-y-4">
        <div class="flex items-center space-x-2.5 border-b border-slate-200 pb-3">
          <i class="fa-solid fa-magnifying-glass text-slate-600 text-lg"></i>
          <div>
            <h2 class="font-bold text-slate-800 text-sm sm:text-base">🔭 望遠レンズ＆ズームで狙う！遠景・圧縮効果ポイント</h2>
            <p class="text-xs text-slate-500">200mm以上の望遠圧縮で「絵葉書を超えた」1枚を</p>
          </div>
        </div>
        <div class="grid grid-cols-1 sm:grid-cols-2 gap-3 text-xs text-slate-700 leading-relaxed">
          <div class="p-3 bg-white rounded-xl border border-amber-200 space-y-1.5">
            <strong class="text-amber-900 block">🐪 ギザ「パノラマポイント」</strong>
            <p>ギザ台地南側の砂漠（パノラマポイント）から200〜300mmで狙うと3大ピラミッドが横一列に並ぶ超圧縮構図が完成。手前の砂丘にラクダを入れると奥行きと深みが加わる。</p>
            <p class="text-amber-700 font-bold">📍 ツアー車でパノラマポイント（Panorama Point）と指定</p>
          </div>
          <div class="p-3 bg-white rounded-xl border border-violet-200 space-y-1.5">
            <strong class="text-violet-900 block">🇬🇷 アテネ「アレオパゴス/フィロパポスの丘」</strong>
            <p>フィロパポスの丘（Filopappou）から現代のビル群の向こうにパルテノン神殿が浮かぶ対比構図。100〜200mmで圧縮し「今と2500年前が同じフレーム」に。夕方の黄金光が最高。</p>
            <p class="text-violet-700 font-bold">📍 アクロポリス南西の丘。徒歩約15分。</p>
          </div>
          <div class="p-3 bg-white rounded-xl border border-sky-200 space-y-1.5">
            <strong class="text-sky-900 block">🇬🇷 サントリーニ「イメロヴィグリ → イア展望」</strong>
            <p>イメロヴィグリのスカロス岩展望台から北側のイアを望遠（200mm）で切り取ると、白い断崖都市が整然と重なり合い絵画のような1枚に。夕方のマジックアワーに。</p>
            <p class="text-sky-700 font-bold">📍 スカロス岩（Skaros Rock）の先端展望台</p>
          </div>
          <div class="p-3 bg-white rounded-xl border border-orange-200 space-y-1.5">
            <strong class="text-orange-900 block">🛕 ルクソール「ナイル越しのオベリスク夕景」</strong>
            <p>ナイル西岸・農村地帯の土手（または西岸ホテルテラス）から東岸のルクソール神殿の巨大オベリスクを望遠で狙う。水面のリフレクションと夕焼けで黄金色に染まる絶景。</p>
            <p class="text-orange-700 font-bold">📍 ファルーカ船上または西岸の土手道</p>
          </div>
        </div>
      </div>
"""

# ────────────────────────────────────────────────────────
# v2 を読み込み、フォトタブの closing </section> を差し替え
# ────────────────────────────────────────────────────────
print("v2 を読み込み中...")
html = INPUT.read_text(encoding="utf-8")

# フォトタブの終端マーカー（TAB 6 のコメントブロック）
PHOTO_END_MARKER = '</section>\n\n    <!-- ==================== TAB 6: ToDo'

if PHOTO_END_MARKER not in html:
    # スペース差異を吸収するため別パターンも試みる
    PHOTO_END_MARKER = '</section>\n    <!-- ==================== TAB 6: ToDo'

if PHOTO_END_MARKER not in html:
    raise RuntimeError("フォトタブの終端マーカーが見つかりません。スクリプトを要確認。")

replacement = PHOTO_ADDITIONS + '    </section>\n\n    <!-- ==================== TAB 6: ToDo'
html = html.replace(PHOTO_END_MARKER, replacement, 1)

OUTPUT.write_text(html, encoding="utf-8")
size = OUTPUT.stat().st_size
print(f"完了: {OUTPUT.name} ({size:,} bytes / {size/1024/1024:.2f} MB)")
