// 使い方: NODE_PATH=<pptxgenjsのnode_modules> node make_bloodtype_slide.js <出力pptx>
const pptxgen = require("pptxgenjs");
const out = process.argv[2];
if (!out) { console.error("出力ファイルを指定してください"); process.exit(1); }

const FONT = "Meiryo UI";
const NAVY = "1F3864", TEAL = "2E8B9A", RED = "C00000", GREY = "D9D9D9", PINK = "F2DCDB", OK = "1E7B34", SUB = "404040";

const pres = new pptxgen();
pres.defineLayout({ name: "A4L", width: 11.69, height: 8.27 });
pres.layout = "A4L";
pres.theme = { headFontFace: FONT, bodyFontFace: FONT };
const s = pres.addSlide();
const T = (text, o) => s.addText(text, Object.assign({ isTextBox: true, fontFace: FONT, color: "000000", margin: 0 }, o));

T("X. モデル期間中に登録された血液型の論理削除の方針に係る相談", { x: 0.45, y: 0.3, w: 10.8, h: 0.55, fontSize: 22, bold: true, color: NAVY, valign: "middle" });
s.addShape(pres.shapes.LINE, { x: 0.3, y: 0.92, w: 11.1, h: 0, line: { color: TEAL, width: 1.5 } });
T("続き", { x: 0.45, y: 1.05, w: 2, h: 0.3, fontSize: 12 });

s.addShape(pres.shapes.RECTANGLE, { x: 0.45, y: 1.4, w: 8.2, h: 0.42, fill: { color: NAVY }, line: { type: "none" } });
T("ご相談事項（2）技術解説書公開（1/18）～3月リリースまでの血液型の登録・表示抑制について", {
  x: 0.55, y: 1.4, w: 8.0, h: 0.42, fontSize: 13, bold: true, color: "FFFFFF", valign: "middle",
});

const bullets = [
  "技術解説書公開(1/18)から3月リリースまでの間、血液型データを登録しないよう電カルベンダに周知する必要があるが、技術解説書(1/18公開)で周知する場合、本格運用開始まで1週間しかなく、電カルベンダの対応が間に合わないことが想定される。",
  "そのため、1月に適用するJLACマスターより血液型に係る項目を削除し、登録エラーとする形で当該期間における血液型データの登録を抑制したい。",
  "なお、血液型の登録がエラーになることのベンダ・医療機関への周知について、血液型を共有対象外とする件を付議する12月WGが終了次第、周知を進めることとする。",
];
T(bullets.map((t, i) => ({ text: t, options: { bullet: true, breakLine: i < bullets.length - 1, paraSpaceAfter: 4 } })), {
  x: 0.45, y: 1.92, w: 10.8, h: 1.45, fontSize: 12, valign: "top",
});

// タイムライン（x座標は下の表の列幅とそろえる）
const X0 = 0.6, XL = 2.4, X1 = 11.1;
const M = { wg: 3.0, doc: 5.0, go: 5.6, rel: 8.4 };
const LY = 3.5, RY = 3.85, RH = 0.85;

const mark = (label, x, side) => {
  const parts = side === "left"
    ? [{ text: label, options: {} }, { text: "▼", options: { color: RED } }]
    : [{ text: "▼", options: { color: RED } }, { text: label, options: {} }];
  const w = 3.4;
  T(parts, { x: side === "left" ? x - w + 0.08 : x - 0.08, y: LY, w, h: 0.3, fontSize: 11, align: side === "left" ? "right" : "left", valign: "bottom" });
};
mark("12月WG(12/4)", M.wg, "left");
mark("技術解説書公開(1/18)", M.doc, "left");
mark("本格運用開始(1/25)", M.go, "right");
mark("3月リリース(3月末)=案件ID210実装", M.rel, "right");

s.addShape(pres.shapes.RECTANGLE, { x: XL, y: RY, w: M.doc - XL, h: RH, fill: { color: GREY }, line: { type: "none" } });
s.addShape(pres.shapes.RECTANGLE, { x: M.doc, y: RY, w: M.rel - M.doc, h: RH, fill: { color: PINK }, line: { type: "none" } });
s.addShape(pres.shapes.RECTANGLE, { x: M.rel, y: RY, w: X1 - M.rel, h: RH, fill: { color: GREY }, line: { type: "none" } });
T("登録可", { x: XL, y: RY, w: M.doc - XL, h: RH, fontSize: 12, align: "center", valign: "middle" });
T("登録不可", { x: M.doc, y: RY, w: M.rel - M.doc, h: RH, fontSize: 12, bold: true, color: RED, align: "center", valign: "middle" });
T([{ text: "登録可", options: { fontSize: 12, breakLine: true } }, { text: "※ただし案件ID210の実装により非表示", options: { fontSize: 9 } }],
  { x: M.rel, y: RY, w: X1 - M.rel, h: RH, align: "center", valign: "middle" });
T("血液型データの\n登録可否", { x: X0, y: RY, w: XL - X0, h: RH, fontSize: 12, align: "center", valign: "middle", underline: { style: "sng" } });
s.addShape(pres.shapes.LINE, { x: X0, y: RY, w: X1 - X0, h: 0, line: { color: "000000", width: 1 } });
s.addShape(pres.shapes.LINE, { x: X0, y: RY + RH, w: X1 - X0, h: 0, line: { color: "000000", width: 1 } });
s.addShape(pres.shapes.LINE, { x: XL, y: RY, w: 0, h: RH, line: { color: "000000", width: 1 } });
for (const x of [M.wg, M.doc, M.go, M.rel]) {
  s.addShape(pres.shapes.LINE, { x, y: RY, w: 0, h: RH, line: { color: RED, width: 1, dashType: "dash" } });
}

// フェーズ別の登録可否・表示可否
const TY = 5.0;
const hd = (t, sub) => ({
  text: [{ text: t, options: { bold: true, breakLine: true } }, { text: sub, options: { fontSize: 9, color: SUB } }],
  options: { fill: { color: "DCE3EE" }, align: "center", valign: "middle" },
});
const cell = (mark, note, fill) => {
  const runs = [{ text: mark, options: { fontSize: 14, bold: true, color: mark === "○" ? OK : RED, breakLine: !!note } }];
  if (note) runs.push({ text: note, options: { fontSize: 9, color: SUB } });
  const o = { align: "center", valign: "middle" };
  if (fill) o.fill = { color: fill };
  return { text: runs, options: o };
};
const item = (t, sub) => ({
  text: [{ text: t, options: { bold: true, breakLine: true } }, { text: sub, options: { fontSize: 9, color: SUB } }],
  options: { rowspan: 2, align: "center", valign: "middle" },
});
const kind = (t) => ({ text: t, options: { align: "center", valign: "middle" } });

const rows = [
  [{ text: "", options: { colspan: 2, fill: { color: "DCE3EE" } } },
    hd("① ～1/17", "モデル期間"), hd("② 1/18～3月末", "技術解説書公開～3月リリース"), hd("③ 3月末～", "案件ID210実装後")],
  [item("血液型", "ABO・Rh"), kind("登録"),
    cell("○", "12/4以降、ベンダ・医療機関へ周知"), cell("×", "JLACマスタから削除し、登録するとエラーを返却", PINK), cell("○", "JLACマスタに戻す")],
  [kind("表示"), cell("○"), cell("×", "登録されないため出力されない", PINK), cell("×", "案件ID210により非表示")],
  [item("それ以外", "検査41項目\n感染症5項目"), kind("登録"), cell("○"), cell("○"), cell("○")],
  [kind("表示"), cell("○"), cell("○"), cell("○")],
];
s.addTable(rows, {
  x: X0, y: TY, w: X1 - X0, colW: [1.1, 0.7, M.doc - XL, M.rel - M.doc, X1 - M.rel],
  rowH: [0.5, 0.55, 0.55, 0.45, 0.45], fontFace: FONT, fontSize: 12, color: "000000",
  border: { type: "solid", pt: 0.75, color: "7F7F7F" }, margin: 0.04,
});
T("○：できる・表示される　×：できない・表示されない", { x: X0, y: TY + 2.6, w: 6, h: 0.25, fontSize: 10, color: SUB });

pres.writeFile({ fileName: out }).then((f) => console.log("written:", f));
