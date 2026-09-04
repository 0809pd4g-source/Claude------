#!/usr/bin/env python3
"""
v6_to_v7_history_expand.py  ─  歴史タブ大幅拡充 ＆ ToDoタブ改名

変更内容:
  1. ToDoタブボタン名 「ToDo & 規定」→「ToDo リスト」
  2. 歴史タブに10カード追加:
     [Group A] エジプト神々クイックリファレンス / 王朝タイムライン / ファラオ逸話集
     [Group B] ギリシャ12神 / 哲学者逸話 / パルテノン受難史 / ビザンティン/オスマン史
     [Group C] サントリーニ火山＆アトランティス / アクロティリ遺跡
     [Group D] ギリシャ文字入門
"""

from pathlib import Path

BASE   = Path(__file__).parent.parent / "02_output"
INPUT  = BASE / "20260901_新婚旅行しおり_v6.html"
OUTPUT = BASE / "20260901_新婚旅行しおり_v7.html"

html = INPUT.read_text(encoding="utf-8")
print(f"読み込み完了: {len(html):,} chars\n")

# ══════════════════════════════════════════════════════════
# 1. ToDoタブボタン改名
# ══════════════════════════════════════════════════════════
html = html.replace('ToDo &amp; 規定\n        </button>', 'ToDo リスト\n        </button>', 1)
html = html.replace('<!-- ==================== TAB 6: ToDo & 手荷物規定', '<!-- ==================== TAB 6: ToDo リスト', 1)
print("1. ToDoタブ改名 ✓")

# ══════════════════════════════════════════════════════════
# 2. 歴史タブ拡充コンテンツ（10カード）を挿入
#    → 既存の「スポット別現地攻略ガイド」の後・</section>の前
# ══════════════════════════════════════════════════════════
HISTORY_END = '    </section>\n\n    <!-- ==================== TAB 5: フォト'
assert HISTORY_END in html, "歴史タブ終端マーカーが見つかりません"

HISTORY_ADDITIONS = """
      <!-- ════ GROUP A: エジプト神話・歴史 ════ -->
      <div class="text-xs font-bold text-amber-800 uppercase tracking-wider px-1 pt-2">🐫 エジプト 神話・歴史</div>

      <!-- A1. エジプト神々クイックリファレンス -->
      <div class="bg-amber-50 border border-amber-200 rounded-2xl p-4 sm:p-5 shadow-xs space-y-3">
        <div class="flex items-center space-x-2 border-b border-amber-200 pb-2">
          <span class="text-xl">⚡</span>
          <div>
            <h2 class="font-bold text-amber-950 text-sm sm:text-base">① 古代エジプト神々クイックリファレンス</h2>
            <p class="text-xs text-amber-700">壁画・神殿で「この神様は誰？」と迷わないための早見表</p>
          </div>
        </div>
        <div class="overflow-x-auto">
          <table class="w-full text-xs border-collapse">
            <thead><tr class="bg-amber-100 text-amber-900"><th class="p-1.5 text-left font-bold border-b border-amber-300">神名</th><th class="p-1.5 text-left font-bold border-b border-amber-300">外見の特徴</th><th class="p-1.5 text-left font-bold border-b border-amber-300">担当領域</th><th class="p-1.5 text-left font-bold border-b border-amber-300">現地での出会い</th></tr></thead>
            <tbody class="divide-y divide-amber-100">
              <tr class="hover:bg-amber-100"><td class="p-1.5 font-bold text-amber-900">☀️ ラー (Ra)</td><td class="p-1.5">鷹の頭に太陽円盤</td><td class="p-1.5">太陽・創造の主神</td><td class="p-1.5">カルナック神殿・GEM壁画</td></tr>
              <tr class="hover:bg-amber-100"><td class="p-1.5 font-bold text-amber-900">🌿 オシリス (Osiris)</td><td class="p-1.5">緑肌・ミイラ姿・二本の羽飾り冠</td><td class="p-1.5">冥界の王・死と再生</td><td class="p-1.5">王家の谷の壁画（死者の書）</td></tr>
              <tr class="hover:bg-amber-100"><td class="p-1.5 font-bold text-amber-900">🪶 イシス (Isis)</td><td class="p-1.5">翼を持つ女性・頭に玉座のシンボル</td><td class="p-1.5">魔法・母性・治癒</td><td class="p-1.5">ルクソール神殿内壁・GEM</td></tr>
              <tr class="hover:bg-amber-100"><td class="p-1.5 font-bold text-amber-900">🦅 ホルス (Horus)</td><td class="p-1.5">鷹の頭・二重王冠</td><td class="p-1.5">空の神・ファラオの守護</td><td class="p-1.5">スフィンクスはホルスの化身。ほぼ全神殿に登場</td></tr>
              <tr class="hover:bg-amber-100"><td class="p-1.5 font-bold text-amber-900">🐺 アヌビス (Anubis)</td><td class="p-1.5">ジャッカル（黒犬）の頭</td><td class="p-1.5">死・ミイラ化・冥界の案内人</td><td class="p-1.5">王家の谷の棺・GEMミイラ展示室</td></tr>
              <tr class="hover:bg-amber-100"><td class="p-1.5 font-bold text-amber-900">🐦 トト (Thoth)</td><td class="p-1.5">トキまたはヒヒの頭・筆と巻物</td><td class="p-1.5">知恵・文字・月・時間</td><td class="p-1.5">カルナック神殿の碑文・GEM</td></tr>
              <tr class="hover:bg-amber-100"><td class="p-1.5 font-bold text-amber-900">🦁 セクメト (Sekhmet)</td><td class="p-1.5">ライオンの頭・赤い衣</td><td class="p-1.5">戦争・疫病・癒し（破壊と回復）</td><td class="p-1.5">カルナック神殿に600体以上の像</td></tr>
              <tr class="hover:bg-amber-100"><td class="p-1.5 font-bold text-amber-900">🐄 ハトホル (Hathor)</td><td class="p-1.5">牛の耳を持つ女性・シストラム（楽器）</td><td class="p-1.5">愛・音楽・美・喜び</td><td class="p-1.5">ルクソール神殿の礼拝堂・デンデラ神殿</td></tr>
            </tbody>
          </table>
        </div>
        <div class="p-2 bg-white rounded-lg border border-amber-200 text-[11px] text-amber-800">💡 <strong>観察のコツ：</strong>頭の形が鑑定の鍵。鷹＝ラーかホルス、犬＝アヌビス、トキ＝トト。体の色も重要で緑は再生・オシリスを示す。</div>
      </div>

      <!-- A2. 古代エジプト王朝タイムライン -->
      <div class="bg-white rounded-2xl shadow-xs border border-slate-200 p-4 sm:p-5 space-y-3">
        <div class="flex items-center space-x-2 border-b border-slate-100 pb-2">
          <span class="text-xl">📅</span>
          <div>
            <h2 class="font-bold text-slate-800 text-sm sm:text-base">② 古代エジプト王朝タイムライン（約5000年）</h2>
            <p class="text-xs text-slate-500">訪れる遺跡がどの時代のものか一目でわかる年表</p>
          </div>
        </div>
        <div class="relative pl-4">
          <div class="absolute left-0 top-0 bottom-0 w-0.5 bg-amber-300"></div>
          <div class="space-y-3 text-xs">
            <div class="relative pl-3">
              <div class="absolute -left-[13px] top-1 w-3 h-3 rounded-full bg-amber-400 border-2 border-white"></div>
              <div class="font-bold text-amber-900">先王朝・初期王朝時代 〜紀元前2686年</div>
              <p class="text-slate-600">ナルメル王によるエジプト統一。ヒエログリフ誕生。マスタバ（平屋根型石墓）が始まる。</p>
            </div>
            <div class="relative pl-3">
              <div class="absolute -left-[13px] top-1 w-3 h-3 rounded-full bg-amber-500 border-2 border-white"></div>
              <div class="font-bold text-amber-900">🟡 旧王国時代 紀元前2686〜2181年</div>
              <p class="text-slate-600"><strong>「ピラミッドの時代」。</strong>ジョセル王の階段ピラミッド（サッカラ）→クフ王・カフラー王・メンカウラー王のギザ三大ピラミッド完成。スフィンクス建造。</p>
              <div class="mt-1 p-1.5 bg-amber-50 rounded text-amber-800">📍 <strong>今回の旅：</strong>ギザ・サッカラはまさにこの時代！</div>
            </div>
            <div class="relative pl-3">
              <div class="absolute -left-[13px] top-1 w-3 h-3 rounded-full bg-slate-400 border-2 border-white"></div>
              <div class="font-bold text-slate-700">第1中間期 紀元前2181〜2055年</div>
              <p class="text-slate-600">中央集権の崩壊。地方豪族が群立。混乱期。</p>
            </div>
            <div class="relative pl-3">
              <div class="absolute -left-[13px] top-1 w-3 h-3 rounded-full bg-amber-500 border-2 border-white"></div>
              <div class="font-bold text-amber-900">中王国時代 紀元前2055〜1650年</div>
              <p class="text-slate-600">テーベ（ルクソール）を拠点に再統一。カルナック神殿の原形が建設開始。文学・芸術が花開く「古典期」。</p>
            </div>
            <div class="relative pl-3">
              <div class="absolute -left-[13px] top-1 w-3 h-3 rounded-full bg-amber-600 border-2 border-white"></div>
              <div class="font-bold text-amber-900">🟠 新王国時代 紀元前1550〜1070年</div>
              <p class="text-slate-600"><strong>「最盛期」。</strong>ハトシェプスト女王・アクナトン（宗教改革）・ツタンカーメン・ラムセス2世（カルナック建設・カデシュの戦い）。王家の谷が王の埋葬地に。</p>
              <div class="mt-1 p-1.5 bg-amber-50 rounded text-amber-800">📍 <strong>今回の旅：</strong>ルクソール神殿・カルナック・王家の谷は全てこの時代！</div>
            </div>
            <div class="relative pl-3">
              <div class="absolute -left-[13px] top-1 w-3 h-3 rounded-full bg-slate-400 border-2 border-white"></div>
              <div class="font-bold text-slate-700">第3中間期・末期王朝 紀元前1070〜332年</div>
              <p class="text-slate-600">ヌビア・アッシリア・ペルシャによる断続的支配。段階的な衰退。</p>
            </div>
            <div class="relative pl-3">
              <div class="absolute -left-[13px] top-1 w-3 h-3 rounded-full bg-sky-500 border-2 border-white"></div>
              <div class="font-bold text-sky-900">プトレマイオス朝 紀元前332〜30年</div>
              <p class="text-slate-600">アレキサンドロス大王がエジプト征服→ギリシャ系プトレマイオス朝が支配。クレオパトラ7世が最後の女王。彼女はエジプト語を話した最初のプトレマイオス朝君主。</p>
            </div>
            <div class="relative pl-3">
              <div class="absolute -left-[13px] top-1 w-3 h-3 rounded-full bg-red-400 border-2 border-white"></div>
              <div class="font-bold text-red-800">ローマ支配〜イスラム征服 紀元前30年〜641年</div>
              <p class="text-slate-600">クレオパトラ死去でローマの属州に。以後、キリスト教化（コプト教）を経て、641年にイスラム軍がカイロ（旧フスタート）を建設。</p>
            </div>
          </div>
        </div>
      </div>

      <!-- A3. ファラオ・有名人の逸話集 -->
      <div class="bg-white rounded-2xl shadow-xs border border-slate-200 p-4 sm:p-5 space-y-3">
        <div class="flex items-center space-x-2 border-b border-slate-100 pb-2">
          <span class="text-xl">👑</span>
          <div>
            <h2 class="font-bold text-slate-800 text-sm sm:text-base">④ ファラオたちの「知られざる逸話」集</h2>
            <p class="text-xs text-slate-500">現地で彼らの痕跡を見ると、物語が生き返ってくる</p>
          </div>
        </div>
        <div class="grid grid-cols-1 sm:grid-cols-2 gap-3 text-xs text-slate-700 leading-relaxed">
          <div class="p-3 bg-amber-50 rounded-xl border border-amber-200 space-y-1.5">
            <div class="font-bold text-amber-900">⚡ ラムセス2世（在位67年）</div>
            <p>紀元前1279〜1213年。90歳超まで生きた最長命ファラオ。カデシュの戦い（対ヒッタイト）は引き分けだったが、巨大なレリーフで「大勝利」として全神殿に刻ませた。歴史上最初の平和条約も結んでいる。200人以上の子供を持ち、王妃ネフェルタリへの愛は有名（彼女のために豪華な墓を造った）。</p>
          </div>
          <div class="p-3 bg-amber-50 rounded-xl border border-amber-200 space-y-1.5">
            <div class="font-bold text-amber-900">👸 ハトシェプスト女王（在位20年）</div>
            <p>紀元前1479〜1458年。摂政から「ファラオ」に昇格した唯一の女性王。男装し付け髭をつけて公式行事に登場。交易遠征でパント（現ソマリア）から没薬の木を持ち帰り、自分の葬祭殿（ルクソール西岸）に植えた。死後、継子トトメス3世が彼女の像と記録のほとんどを削り取った（嫉妬か政治的理由か）。そのため長年「謎の女王」だった。</p>
          </div>
          <div class="p-3 bg-amber-50 rounded-xl border border-amber-200 space-y-1.5">
            <div class="font-bold text-amber-900">💎 ツタンカーメン（在位10年・享年18〜20歳）</div>
            <p>紀元前1332〜1323年。生前はさほど重要なファラオではなかった。墓が無傷だった理由：建造当時は王家の谷の奥に隠れる位置で目立たず、後代のラムセス6世の工事の瓦礫が入口を塞いで発見不可能になった。1922年、ハワード・カーターが発掘。棺と黄金のマスクの価値は当時推定10億ドル以上。DNA検査で父はアクナトン、近親婚由来の疾患を持ちながら短命だったことが判明。</p>
          </div>
          <div class="p-3 bg-amber-50 rounded-xl border border-amber-200 space-y-1.5">
            <div class="font-bold text-amber-900">🐍 クレオパトラ7世（享年39歳）</div>
            <p>紀元前69〜30年。プトレマイオス朝最後のファラオ。ギリシャ系だが9か国語を話し、エジプト語を解した最初の王。カエサルと出会った時は絨毯に包まれて謁見したという伝説がある（実際は秘密の訪問）。カエサル暗殺後はアントニウスと同盟。最後はアウグストゥスに敗れ、毒蛇（コブラ）に噛まれて自害。死後エジプトはローマの属州に。</p>
          </div>
        </div>
      </div>

      <!-- ════ GROUP B: ギリシャ神話・哲学・歴史 ════ -->
      <div class="text-xs font-bold text-sky-800 uppercase tracking-wider px-1 pt-2">🏛️ ギリシャ 神話・哲学・歴史</div>

      <!-- B1. ギリシャ12神クイックリファレンス -->
      <div class="bg-sky-50 border border-sky-200 rounded-2xl p-4 sm:p-5 shadow-xs space-y-3">
        <div class="flex items-center space-x-2 border-b border-sky-200 pb-2">
          <span class="text-xl">⚡</span>
          <div>
            <h2 class="font-bold text-sky-950 text-sm sm:text-base">A ギリシャ12神（オリンポス）クイックリファレンス</h2>
            <p class="text-xs text-sky-700">アクロポリスの彫刻・神殿でどの神が祀られているか即わかる</p>
          </div>
        </div>
        <div class="overflow-x-auto">
          <table class="w-full text-xs border-collapse">
            <thead><tr class="bg-sky-100 text-sky-900"><th class="p-1.5 text-left font-bold border-b border-sky-300">神名</th><th class="p-1.5 text-left font-bold border-b border-sky-300">シンボル</th><th class="p-1.5 text-left font-bold border-b border-sky-300">担当領域</th><th class="p-1.5 text-left font-bold border-b border-sky-300">アテネとの関係</th></tr></thead>
            <tbody class="divide-y divide-sky-100">
              <tr class="hover:bg-sky-100"><td class="p-1.5 font-bold text-sky-900">⚡ ゼウス (Zeus)</td><td class="p-1.5">雷矢・鷲</td><td class="p-1.5">天空・雷・神々の王</td><td class="p-1.5">オリンピア神殿。アクロポリス南麓に巨大神殿（柱が残る）</td></tr>
              <tr class="hover:bg-sky-100"><td class="p-1.5 font-bold text-sky-900">🦉 アテナ (Athena)</td><td class="p-1.5">梟・槍・盾（アイギス）・オリーブ</td><td class="p-1.5">知恵・戦略・工芸</td><td class="p-1.5"><strong>アテネの守護神。</strong>パルテノン神殿は彼女の神殿。エレクテイオンには彼女の聖木（オリーブ）が植わる</td></tr>
              <tr class="hover:bg-sky-100"><td class="p-1.5 font-bold text-sky-900">🔱 ポセイドン (Poseidon)</td><td class="p-1.5">三叉槍・馬・波</td><td class="p-1.5">海・地震・馬</td><td class="p-1.5">エレクテイオンはアテナとポセイドンが争った地（泉の跡が残る）</td></tr>
              <tr class="hover:bg-sky-100"><td class="p-1.5 font-bold text-sky-900">☀️ アポロン (Apollo)</td><td class="p-1.5">弓・竪琴・月桂樹</td><td class="p-1.5">太陽・音楽・予言・詩</td><td class="p-1.5">デルフォイの神託所（今回の旅程外）。アゴラにも神殿</td></tr>
              <tr class="hover:bg-sky-100"><td class="p-1.5 font-bold text-sky-900">🌙 アルテミス (Artemis)</td><td class="p-1.5">弓矢・三日月・鹿</td><td class="p-1.5">月・狩猟・出産</td><td class="p-1.5">エフェソスの大神殿（今回の旅程外）</td></tr>
              <tr class="hover:bg-sky-100"><td class="p-1.5 font-bold text-sky-900">💕 アフロディテ (Aphrodite)</td><td class="p-1.5">バラ・白鳩・貝</td><td class="p-1.5">愛・美・欲望</td><td class="p-1.5">アテネのアゴラ南西に神殿跡。ミロのヴィーナス（ルーブル）が有名</td></tr>
              <tr class="hover:bg-sky-100"><td class="p-1.5 font-bold text-sky-900">⚔️ アレス (Ares)</td><td class="p-1.5">剣・盾・ハゲタカ</td><td class="p-1.5">戦争・暴力</td><td class="p-1.5">アクロポリス北西の岩山「アレオパゴス（アレスの丘）」は彼の名に由来</td></tr>
              <tr class="hover:bg-sky-100"><td class="p-1.5 font-bold text-sky-900">🪶 ヘルメス (Hermes)</td><td class="p-1.5">翼の帽子・カドゥケウス（蛇の杖）</td><td class="p-1.5">商業・旅人・伝令・盗人</td><td class="p-1.5">商業の神。アゴラ（市場）の守護神。プラカの土産店街もヘルメスの庇護下</td></tr>
              <tr class="hover:bg-sky-100"><td class="p-1.5 font-bold text-sky-900">🔥 ヘファイストス (Hephaestus)</td><td class="p-1.5">ハンマー・炎・鍛冶</td><td class="p-1.5">火・鍛冶・工芸</td><td class="p-1.5">アゴラを見下ろす丘に「ヘファイストス神殿」（保存状態最良のギリシャ神殿の一つ）</td></tr>
              <tr class="hover:bg-sky-100"><td class="p-1.5 font-bold text-sky-900">👑 ヘラ (Hera)</td><td class="p-1.5">孔雀・王冠・ざくろ</td><td class="p-1.5">結婚・女性・家族の守護</td><td class="p-1.5">ゼウスの妻。ハネムーンのご縁！オリンピアに大神殿</td></tr>
              <tr class="hover:bg-sky-100"><td class="p-1.5 font-bold text-sky-900">🌾 デメテル (Demeter)</td><td class="p-1.5">麦の穂・松明</td><td class="p-1.5">農業・大地・実り</td><td class="p-1.5">エレウシスの秘儀（今回旅程外）。アテネ南西エレウシスが聖地</td></tr>
              <tr class="hover:bg-sky-100"><td class="p-1.5 font-bold text-sky-900">🍇 ディオニュソス (Dionysus)</td><td class="p-1.5">葡萄・蔦・チュルソス（松毬の杖）</td><td class="p-1.5">ワイン・祝祭・演劇</td><td class="p-1.5">アクロポリス南麓の「ディオニュソス劇場」（紀元前世界最古の劇場）が聖地</td></tr>
            </tbody>
          </table>
        </div>
      </div>

      <!-- B2. ギリシャ哲学者の逸話集 -->
      <div class="bg-white rounded-2xl shadow-xs border border-slate-200 p-4 sm:p-5 space-y-3">
        <div class="flex items-center space-x-2 border-b border-slate-100 pb-2">
          <span class="text-xl">💭</span>
          <div>
            <h2 class="font-bold text-slate-800 text-sm sm:text-base">C ギリシャ哲学者たちの「生きた逸話」集</h2>
            <p class="text-xs text-slate-500">プラカ・アゴラを歩くと「この石畳で彼らが話していた」と感じられる</p>
          </div>
        </div>
        <div class="grid grid-cols-1 sm:grid-cols-2 gap-3 text-xs text-slate-700 leading-relaxed">
          <div class="p-3 bg-sky-50 rounded-xl border border-sky-200 space-y-1.5">
            <div class="font-bold text-sky-900">🏺 ソクラテス（紀元前469〜399年）</div>
            <p>「無知の知」を説いた哲学の父。著作を残さず（全ての記録はプラトンによる）。「知らないことを知っている」という謙虚さが彼の出発点。アゴラで市民に問いかけ続け「アテネの若者を惑わした」として告訴された。死刑判決を受けたが逃亡を拒み、毒ニンジンの杯を自ら飲んで死を選ぶ。理由：「法への服従なくして国家は成立しない」という信念。</p>
          </div>
          <div class="p-3 bg-sky-50 rounded-xl border border-sky-200 space-y-1.5">
            <div class="font-bold text-sky-900">📚 プラトン（紀元前427〜347年）</div>
            <p>ソクラテスの最愛の弟子。「イデア論」（現実は真実の世界のコピー）を提唱。ソクラテスの死後、各地を放浪し「アカデメイア」（世界最古の大学の一つ）をアテネに設立。シラクサ（現シチリア）の僭主ディオニュシオスに哲学を教えに行き3度も失敗、うち一度は奴隷として売られそうになったとも伝わる。「アトランティス」の記述を残したのもプラトン。</p>
          </div>
          <div class="p-3 bg-sky-50 rounded-xl border border-sky-200 space-y-1.5">
            <div class="font-bold text-sky-900">🌍 アリストテレス（紀元前384〜322年）</div>
            <p>プラトンの弟子。生物学・倫理学・政治学・修辞学・詩学など学問のほぼ全分野を体系化した「万学の祖」。最大の「授業」：17歳のアレキサンドロス（後の大王）の家庭教師を8年間務めた。師の影響でアレキサンドロスは征服した土地に図書館を設置する習慣を持ち、アレキサンドリア図書館もその系譜。師プラトンと違い「現実の世界にこそ真理がある」と主張。</p>
          </div>
          <div class="p-3 bg-sky-50 rounded-xl border border-sky-200 space-y-1.5">
            <div class="font-bold text-sky-900">🛢️ ディオゲネス（紀元前412〜323年）</div>
            <p>桶（壺）の中に住み、「必要最低限の生活」を実践したキニク派哲学者。あるとき視察に来たアレキサンドロス大王が「何か望みはあるか」と尋ねると「あなたが日陰になっているのでどいてほしい」と答えたという伝説が有名。大王は「もし私がアレキサンドロスでなければ、ディオゲネスになりたかった」と言ったとも。全財産を持たず、最小限の自由を最大の富とした。</p>
          </div>
        </div>
      </div>

      <!-- B3. パルテノン神殿の受難2500年史 -->
      <div class="bg-white rounded-2xl shadow-xs border border-slate-200 p-4 sm:p-5 space-y-3">
        <div class="flex items-center space-x-2 border-b border-slate-100 pb-2">
          <span class="text-xl">🏛️</span>
          <div>
            <h2 class="font-bold text-slate-800 text-sm sm:text-base">D パルテノン神殿の受難2500年史</h2>
            <p class="text-xs text-slate-500">なぜあの状態なのか、エルギン・マーブルはなぜ大英博物館に？</p>
          </div>
        </div>
        <div class="relative pl-4">
          <div class="absolute left-0 top-0 bottom-0 w-0.5 bg-sky-300"></div>
          <div class="space-y-3 text-xs">
            <div class="relative pl-3">
              <div class="absolute -left-[13px] top-1 w-3 h-3 rounded-full bg-sky-500 border-2 border-white"></div>
              <div class="font-bold text-sky-900">紀元前438年 ── 完成</div>
              <p class="text-slate-600">ペリクレス主導・建築家イクティノス設計。完成当時は外壁が赤・青・金に彩色され、内部に高さ12mの黄金象牙装飾のアテナ像があった。現在の「白い廃墟」とは全く異なる姿。</p>
            </div>
            <div class="relative pl-3">
              <div class="absolute -left-[13px] top-1 w-3 h-3 rounded-full bg-slate-400 border-2 border-white"></div>
              <div class="font-bold text-slate-700">5〜6世紀 ── キリスト教礼拝堂に改修</div>
              <p class="text-slate-600">東ローマ（ビザンティン）時代。アテナ像が撤去され、「聖母マリアへの奉納教会」に転用。アプス（半円形後陣）が追加される。</p>
            </div>
            <div class="relative pl-3">
              <div class="absolute -left-[13px] top-1 w-3 h-3 rounded-full bg-amber-500 border-2 border-white"></div>
              <div class="font-bold text-amber-900">1458年 ── オスマン帝国がアテネを征服。モスクに転用</div>
              <p class="text-slate-600">十字架が三日月に替わり、ミナレット（礼拝塔）が建設される。それでも神殿本体の構造は保たれていた。</p>
            </div>
            <div class="relative pl-3">
              <div class="absolute -left-[13px] top-1 w-3 h-3 rounded-full bg-red-500 border-2 border-white"></div>
              <div class="font-bold text-red-900">💥 1687年 ── ヴェネツィア軍の砲撃で爆発</div>
              <p class="text-slate-600">ヴェネツィア共和国がアテネを包囲。オスマン軍が神殿内に火薬庫を置いていたため、砲弾が直撃して大爆発。屋根・中央部が崩壊し、現在の姿に。</p>
            </div>
            <div class="relative pl-3">
              <div class="absolute -left-[13px] top-1 w-3 h-3 rounded-full bg-indigo-500 border-2 border-white"></div>
              <div class="font-bold text-indigo-900">1801〜12年 ── エルギン卿が彫刻帯を搬出</div>
              <p class="text-slate-600">英国大使エルギン卿がオスマン当局の許可（真偽は今も議論中）を得て、パルテノンのフリーズ（彫刻帯）約半分・メトープ・ペディメント像を切り取り英国へ。現在ロンドンの大英博物館に展示。</p>
            </div>
            <div class="relative pl-3">
              <div class="absolute -left-[13px] top-1 w-3 h-3 rounded-full bg-emerald-500 border-2 border-white"></div>
              <div class="font-bold text-emerald-900">1975年〜現在 ── 修復工事進行中</div>
              <p class="text-slate-600">ギリシャ政府が大規模修復プロジェクト開始。2037年頃の完成を目標に現在も工事中。ギリシャは大英博物館に彫刻の返還を求め続けており、英国は拒否を続けている。あなたが9月に訪れる際も工事中の足場が見えるはず。</p>
            </div>
          </div>
        </div>
      </div>

      <!-- B4. ビザンティン帝国とオスマン支配のアテネ -->
      <div class="bg-white rounded-2xl shadow-xs border border-slate-200 p-4 sm:p-5 space-y-3">
        <div class="flex items-center space-x-2 border-b border-slate-100 pb-2">
          <span class="text-xl">🕌</span>
          <div>
            <h2 class="font-bold text-slate-800 text-sm sm:text-base">G ビザンティン帝国〜オスマン支配〜ギリシャ独立</h2>
            <p class="text-xs text-slate-500">プラカになぜオスマン建築が混在しているのか、その理由がわかる</p>
          </div>
        </div>
        <div class="grid grid-cols-1 sm:grid-cols-2 gap-3 text-xs text-slate-700 leading-relaxed">
          <div class="p-3 bg-slate-50 rounded-xl border border-slate-200 space-y-1.5">
            <div class="font-bold text-slate-800">🏰 東ローマ（ビザンティン）帝国時代 330〜1453年</div>
            <p>コンスタンティヌス大帝が330年に「新ローマ（コンスタンティノープル）」を建設→ローマ帝国の中心がトルコへ移行。476年に西ローマ滅亡後も東ローマが継続。キリスト教が国教となりアテネの神殿が次々に教会に改修。1000年超にわたる独自の文明を築く。</p>
          </div>
          <div class="p-3 bg-amber-50 rounded-xl border border-amber-200 space-y-1.5">
            <div class="font-bold text-amber-900">🌙 オスマン帝国支配 1458〜1821年</div>
            <p>メフメト2世がコンスタンティノープル陥落（1453年）後にアテネを占領。約400年にわたるオスマン支配。この時代に建てられたモスク・ハマム（浴場）・トルコ様式の建物がプラカ地区に今も残る（Tzistarakis Mosque等）。一方でオスマン当局は古代遺跡を比較的保護した。</p>
          </div>
          <div class="p-3 bg-sky-50 rounded-xl border border-sky-200 space-y-1.5 sm:col-span-2">
            <div class="font-bold text-sky-900">🔵 ギリシャ独立戦争 1821〜1829年 ＆ 近代国家誕生</div>
            <p>1821年3月25日（現在もギリシャの独立記念日）、正教会の大主教らが独立を宣言。ヨーロッパ中から義勇兵が集結し、イギリスのロマン派詩人バイロン卿も参戦（1824年に病死）。フランス・イギリス・ロシアの艦隊がオスマン艦隊を撃破（ナヴァリノの海戦1827年）。1829年独立確定。1833年、17歳のバイエルン王子オットーが初代ギリシャ国王として即位し、アテネを首都に定めた。</p>
            <div class="p-1.5 bg-white rounded border border-sky-200 text-[11px] text-sky-800">📍 <strong>アテネで感じる独立の記憶：</strong>国立考古学博物館・シンタグマ広場の衛兵交代式（エヴゾーン）・プラカのビザンティン教会。</div>
          </div>
        </div>
      </div>

      <!-- ════ GROUP C: サントリーニ ════ -->
      <div class="text-xs font-bold text-indigo-800 uppercase tracking-wider px-1 pt-2">🌊 サントリーニ 地質・文明</div>

      <!-- C1. サントリーニ火山とアトランティス伝説 -->
      <div class="bg-indigo-50 border border-indigo-200 rounded-2xl p-4 sm:p-5 shadow-xs space-y-3">
        <div class="flex items-center space-x-2 border-b border-indigo-200 pb-2">
          <span class="text-xl">🌋</span>
          <div>
            <h2 class="font-bold text-indigo-950 text-sm sm:text-base">B サントリーニ火山・ミノア文明・アトランティス伝説</h2>
            <p class="text-xs text-indigo-700">カルデラを眺めながら「3600年前にここで何が起きたか」を想像する</p>
          </div>
        </div>
        <div class="grid grid-cols-1 sm:grid-cols-2 gap-3 text-xs text-slate-700 leading-relaxed">
          <div class="p-3 bg-white rounded-xl border border-indigo-200 space-y-2">
            <div class="font-bold text-indigo-900">🌋 ミノア噴火（テラ噴火）紀元前1600年頃</div>
            <p>噴火規模：VEI（火山爆発指数）7〜8。20世紀最大と言われるピナトゥボ火山（VEI 6）の10倍以上のエネルギー。島の中心部が崩落してカルデラ（現在のエーゲ海に沈んだ海）が形成された。</p>
            <p>津波の高さ：推定50m超。クレタ島・エーゲ海沿岸に甚大な被害。ミノア文明の衰退加速の一因とされる。</p>
            <p>現在のサントリーニ：カルデラの縁が島となっている。イア・フィラが建つ白い断崖は噴火で吹き飛んだ火口の縁。カルデラの海底には今も噴火活動を続ける「ネア・カメニ（溶岩島）」がある。</p>
          </div>
          <div class="p-3 bg-white rounded-xl border border-indigo-200 space-y-2">
            <div class="font-bold text-indigo-900">🏝️ アトランティス伝説との関係</div>
            <p>紀元前360年頃、哲学者プラトンが著書「ティマイオス」「クリティアス」に記述：「9000年前、ジブラルタル海峡の外（大西洋）に高度文明を持つアトランティス島があったが、一夜にして海に沈んだ」。</p>
            <p>現代の学者の有力説の一つ：プラトンが数字を誇張（9000年→900年、ジブラルタル外→エーゲ海内）していたとすると、ミノア文明の噴火による沈没と一致する。アクロティリの発掘が決定的な証拠を与えた。</p>
            <div class="p-1.5 bg-indigo-50 rounded text-[11px] text-indigo-800">🌅 <strong>夕日鑑賞の深み：</strong>イアから見るカルデラは「アトランティスが沈んだ海」かもしれない。</div>
          </div>
        </div>
      </div>

      <!-- C2. アクロティリ遺跡 -->
      <div class="bg-white rounded-2xl shadow-xs border border-slate-200 p-4 sm:p-5 space-y-3">
        <div class="flex items-center space-x-2 border-b border-slate-100 pb-2">
          <span class="text-xl">🏺</span>
          <div>
            <h2 class="font-bold text-slate-800 text-sm sm:text-base">F アクロティリ遺跡「エーゲ海のポンペイ」</h2>
            <p class="text-xs text-slate-500">フィラから車20分。サントリーニに泊まるなら絶対に寄れる</p>
          </div>
        </div>
        <div class="grid grid-cols-1 sm:grid-cols-2 gap-3 text-xs text-slate-700 leading-relaxed">
          <div class="p-3 bg-slate-50 rounded-xl border border-slate-200 space-y-2">
            <div class="font-bold text-slate-800">📜 遺跡の概要</div>
            <p>紀元前1600年頃のミノア文明の港町。テラ噴火の直前に住民が脱出し（人骨が見つかっていない）、火山灰に丸ごと埋もれて3600年間保存された。1967年にスピロス・マリナトスが発掘開始。</p>
            <p>保存状態はポンペイに匹敵：3〜4階建ての建物・道路・排水システム・陶器・家具が当時のまま残る。建物の中には穀物の容器も現存。</p>
          </div>
          <div class="p-3 bg-slate-50 rounded-xl border border-slate-200 space-y-2">
            <div class="font-bold text-slate-800">🎨 見どころと観光情報</div>
            <p>① <strong>「ボクサーの少年」フレスコ画（複製）：</strong>2人の少年が拳を構える鮮明な壁画。原本はアテネ国立考古学博物館に。ミノア人の芸術的センスの高さを示す。</p>
            <p>② <strong>「青い猿」フレスコ画：</strong>熱帯に生息するサルがエーゲ海文明の壁画に描かれており、当時の広域交易ネットワークの証拠。</p>
            <p>③ <strong>遺跡全体：</strong>現代の屋根で覆われた発掘現場を見学。空調完備で快適。</p>
            <div class="p-1.5 bg-amber-50 rounded border border-amber-200 text-[11px] text-amber-800">📍 <strong>アクセス：</strong>フィラから車20分・入場12€（5遺跡コンバインド30€に含まれない）。月曜休館。所要約45〜60分。</div>
          </div>
        </div>
      </div>

      <!-- ════ GROUP D: 言語 ════ -->
      <div class="text-xs font-bold text-emerald-800 uppercase tracking-wider px-1 pt-2">🔤 ギリシャ文字</div>

      <!-- D1. ギリシャ文字入門 -->
      <div class="bg-white rounded-2xl shadow-xs border border-slate-200 p-4 sm:p-5 space-y-3">
        <div class="flex items-center space-x-2 border-b border-slate-100 pb-2">
          <span class="text-xl">🔤</span>
          <div>
            <h2 class="font-bold text-slate-800 text-sm sm:text-base">E ギリシャ文字入門（看板・メニューが少し読める！）</h2>
            <p class="text-xs text-slate-500">24文字すべてカタカナ読み付き＋現地で見る実用単語集</p>
          </div>
        </div>
        <div class="grid grid-cols-1 sm:grid-cols-2 gap-3">
          <div class="space-y-2">
            <div class="font-bold text-xs text-slate-700 border-b border-slate-100 pb-1">ギリシャ文字アルファベット（24字）</div>
            <div class="grid grid-cols-4 gap-1 text-xs">
              <div class="text-center p-1 bg-slate-50 rounded border border-slate-200"><div class="font-bold text-base">Α α</div><div class="text-slate-600 text-[10px]">アルファ (A)</div></div>
              <div class="text-center p-1 bg-slate-50 rounded border border-slate-200"><div class="font-bold text-base">Β β</div><div class="text-slate-600 text-[10px]">ヴィタ (V)</div></div>
              <div class="text-center p-1 bg-slate-50 rounded border border-slate-200"><div class="font-bold text-base">Γ γ</div><div class="text-slate-600 text-[10px]">ガンマ (G)</div></div>
              <div class="text-center p-1 bg-slate-50 rounded border border-slate-200"><div class="font-bold text-base">Δ δ</div><div class="text-slate-600 text-[10px]">デルタ (D)</div></div>
              <div class="text-center p-1 bg-slate-50 rounded border border-slate-200"><div class="font-bold text-base">Ε ε</div><div class="text-slate-600 text-[10px]">エプシロン (E)</div></div>
              <div class="text-center p-1 bg-slate-50 rounded border border-slate-200"><div class="font-bold text-base">Ζ ζ</div><div class="text-slate-600 text-[10px]">ジータ (Z)</div></div>
              <div class="text-center p-1 bg-slate-50 rounded border border-slate-200"><div class="font-bold text-base">Η η</div><div class="text-slate-600 text-[10px]">イータ (I)</div></div>
              <div class="text-center p-1 bg-slate-50 rounded border border-slate-200"><div class="font-bold text-base">Θ θ</div><div class="text-slate-600 text-[10px]">シータ (TH)</div></div>
              <div class="text-center p-1 bg-slate-50 rounded border border-slate-200"><div class="font-bold text-base">Ι ι</div><div class="text-slate-600 text-[10px]">イオタ (I)</div></div>
              <div class="text-center p-1 bg-slate-50 rounded border border-slate-200"><div class="font-bold text-base">Κ κ</div><div class="text-slate-600 text-[10px]">カッパ (K)</div></div>
              <div class="text-center p-1 bg-slate-50 rounded border border-slate-200"><div class="font-bold text-base">Λ λ</div><div class="text-slate-600 text-[10px]">ラムダ (L)</div></div>
              <div class="text-center p-1 bg-slate-50 rounded border border-slate-200"><div class="font-bold text-base">Μ μ</div><div class="text-slate-600 text-[10px]">ミュー (M)</div></div>
              <div class="text-center p-1 bg-slate-50 rounded border border-slate-200"><div class="font-bold text-base">Ν ν</div><div class="text-slate-600 text-[10px]">ニュー (N)</div></div>
              <div class="text-center p-1 bg-slate-50 rounded border border-slate-200"><div class="font-bold text-base">Ξ ξ</div><div class="text-slate-600 text-[10px]">クシー (X)</div></div>
              <div class="text-center p-1 bg-slate-50 rounded border border-slate-200"><div class="font-bold text-base">Ο ο</div><div class="text-slate-600 text-[10px]">オミクロン (O)</div></div>
              <div class="text-center p-1 bg-slate-50 rounded border border-slate-200"><div class="font-bold text-base">Π π</div><div class="text-slate-600 text-[10px]">パイ (P)</div></div>
              <div class="text-center p-1 bg-slate-50 rounded border border-slate-200"><div class="font-bold text-base">Ρ ρ</div><div class="text-slate-600 text-[10px]">ロー (R)</div></div>
              <div class="text-center p-1 bg-slate-50 rounded border border-slate-200"><div class="font-bold text-base">Σ σ</div><div class="text-slate-600 text-[10px]">シグマ (S)</div></div>
              <div class="text-center p-1 bg-slate-50 rounded border border-slate-200"><div class="font-bold text-base">Τ τ</div><div class="text-slate-600 text-[10px]">タウ (T)</div></div>
              <div class="text-center p-1 bg-slate-50 rounded border border-slate-200"><div class="font-bold text-base">Υ υ</div><div class="text-slate-600 text-[10px]">イプシロン (I)</div></div>
              <div class="text-center p-1 bg-slate-50 rounded border border-slate-200"><div class="font-bold text-base">Φ φ</div><div class="text-slate-600 text-[10px]">ファイ (F)</div></div>
              <div class="text-center p-1 bg-slate-50 rounded border border-slate-200"><div class="font-bold text-base">Χ χ</div><div class="text-slate-600 text-[10px]">ヒー (H)</div></div>
              <div class="text-center p-1 bg-slate-50 rounded border border-slate-200"><div class="font-bold text-base">Ψ ψ</div><div class="text-slate-600 text-[10px]">プシー (PS)</div></div>
              <div class="text-center p-1 bg-slate-50 rounded border border-slate-200"><div class="font-bold text-base">Ω ω</div><div class="text-slate-600 text-[10px]">オメガ (O)</div></div>
            </div>
          </div>
          <div class="space-y-2">
            <div class="font-bold text-xs text-slate-700 border-b border-slate-100 pb-1">現地で見る実用単語</div>
            <div class="space-y-1 text-xs">
              <div class="flex justify-between p-1.5 bg-emerald-50 rounded border border-emerald-200"><span class="font-bold text-emerald-900">ΦΑΡΜΑΚΕΙΟ</span><span>薬局（緑十字マーク）</span></div>
              <div class="flex justify-between p-1.5 bg-slate-50 rounded border border-slate-200"><span class="font-bold">ΕΙΣΟΔΟΣ</span><span>入口 (Entrance)</span></div>
              <div class="flex justify-between p-1.5 bg-slate-50 rounded border border-slate-200"><span class="font-bold">ΕΞΟΔΟΣ</span><span>出口 (Exit)</span></div>
              <div class="flex justify-between p-1.5 bg-emerald-50 rounded border border-emerald-200"><span class="font-bold text-emerald-900">ΑΝΟΙΧΤΟ</span><span>営業中 (Open)</span></div>
              <div class="flex justify-between p-1.5 bg-red-50 rounded border border-red-200"><span class="font-bold text-red-900">ΚΛΕΙΣΤΟ</span><span>閉店 (Closed)</span></div>
              <div class="flex justify-between p-1.5 bg-slate-50 rounded border border-slate-200"><span class="font-bold">ΤΑΞΙ</span><span>タクシー</span></div>
              <div class="flex justify-between p-1.5 bg-blue-50 rounded border border-blue-200"><span class="font-bold text-blue-900">ΑΣΤΥΝΟΜΙΑ</span><span>警察 (Police)</span></div>
              <div class="flex justify-between p-1.5 bg-red-50 rounded border border-red-200"><span class="font-bold text-red-900">ΝΟΣΟΚΟΜΕΙΟ</span><span>病院 (Hospital)</span></div>
              <div class="flex justify-between p-1.5 bg-slate-50 rounded border border-slate-200"><span class="font-bold">ΕΣΤΙΑΤΟΡΙΟ</span><span>レストラン</span></div>
              <div class="flex justify-between p-1.5 bg-sky-50 rounded border border-sky-200"><span class="font-bold text-sky-900">ΑΘΗΝΑ</span><span>アテナイ（アテネ）</span></div>
              <div class="flex justify-between p-1.5 bg-sky-50 rounded border border-sky-200"><span class="font-bold text-sky-900">ΣΑΝΤΟΡΙΝΗ</span><span>サントリーニ</span></div>
              <div class="flex justify-between p-1.5 bg-sky-50 rounded border border-sky-200"><span class="font-bold text-sky-900">ΟΙΑ</span><span>イア（Oia）</span></div>
            </div>
            <div class="p-2 bg-amber-50 rounded border border-amber-200 text-[11px] text-amber-800">💡 <strong>読み方のコツ：</strong>Γ＝Y、Π＝P、Σ＝Sの3文字を覚えれば「ΕΛΛΑΔΑ（エラダ＝ギリシャ）」「ΠΟΛΙΣ（ポリス＝都市）」が読めるようになる！</div>
          </div>
        </div>
      </div>

"""

html = html.replace(HISTORY_END, HISTORY_ADDITIONS + HISTORY_END, 1)
print("2. 歴史タブ：10カード追加 ✓")

# ══════════════════════════════════════════════════════════
# 出力
# ══════════════════════════════════════════════════════════
OUTPUT.write_text(html, encoding="utf-8")
size = OUTPUT.stat().st_size
print(f"\n=== 完了 ===")
print(f"出力: {OUTPUT.name}")
print(f"サイズ: {size:,} bytes ({size/1024/1024:.2f} MB)")
