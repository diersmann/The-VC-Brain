import path from "node:path";
import { createRequire } from "node:module";

const root = path.resolve(import.meta.dirname, "..");
const requireFromFrontend = createRequire(path.join(root, "frontend", "package.json"));
const PptxGenJS = requireFromFrontend("pptxgenjs");

const output = path.join(root, "docs", "FirstCheck24_Hackathon_Pitch_Editable.pptx");
const overview = path.join(root, "docs", "pitch-assets", "overview.png");
const decision = path.join(root, "docs", "pitch-assets", "decision-detail.png");

const pptx = new PptxGenJS();
pptx.layout = "LAYOUT_WIDE";
pptx.author = "FirstCheck24";
pptx.company = "FirstCheck24";
pptx.subject = "Evidence-backed founder intelligence";
pptx.title = "FirstCheck24 Hackathon Pitch — Editable";
pptx.lang = "en-US";
pptx.theme = { headFontFace: "Aptos Display", bodyFontFace: "Aptos", lang: "en-US" };
pptx.defineSlideMaster({
  title: "FIRSTCHECK_LIGHT",
  background: { color: "F2F6FB" },
  objects: [],
});

const C = {
  ink: "172337", ink2: "344258", muted: "718097", muted2: "94A3B8",
  blue: "557DC0", blueSoft: "E7EEF9", green: "2F8B72", greenSoft: "E4F2ED",
  purple: "7656A5", purpleSoft: "EEE8F8", amber: "B87932", amberSoft: "FFF1DF",
  rose: "B9575F", roseSoft: "FBE8E9", white: "FFFFFF", surface: "F7F9FC", line: "DCE5F0",
};
const SPEAKER_NOTES = [
  "Great founders often leave meaningful signals long before they raise a round, but traditional VC teams usually find them only after fundraising begins. FirstCheck24 finds these founders earlier and makes every investment judgment evidence-backed, explainable, and traceable.",
  "Today's VC workflow is reactive. Valuable information is scattered across GitHub, product launches, research, company websites, and social networks. Teams discover opportunities too late, repeat the same research, and often receive an AI score that behaves like a black box rather than a decision tool.",
  "FirstCheck24 is built around two ideas: autonomous discovery and explainable intelligence. The system proactively identifies promising founders and turns public signals into verifiable evidence. Investors see not only the score, but exactly why the score exists.",
  "The first capability is autonomous discovery. Based on the fund's investment thesis, the system continuously scans sources such as GitHub, Product Hunt, Hacker News, research papers, and hackathons. It collects signals, resolves identities, scores opportunities, and leaves outreach approval with the investor.",
  "The second capability is explainability. Every conclusion follows a transparent chain: source, observation, claim, score, and decision. An investor can open any score to see its origin, discovery date, confidence level, and any conflicting evidence.",
  "We do not average everything into one misleading number. Founder, Market, and Idea–Market Fit remain independent dimensions. Each has its own score, trend, evidence, and confidence. For an investor, disagreement between the dimensions is often the most important signal.",
  "This is a live example for Eoghan McCabe. The system summarizes his track record and the evidence around Intercom, then separates Thesis Match, Founder Signal, and Evidence Quality. Investors can trace every claim, challenge or override the analysis, and choose to proceed, hold, or decline.",
  "FirstCheck24 runs one evidence pipeline with two connected entry paths. Outbound starts from the fund thesis. A discovery agent scans public sources, creates an initial signal score, and places high-potential founders in a promising queue. A footprint agent then resolves identity and gathers deeper technical, company, and network evidence. The three-axis engine scores Founder, Market, and Idea–Market Fit independently, including trends, confidence, and SWOT. If the case is strong, the outreach agent drafts a personalized message, with the investor approving the send. When a founder applies inbound and uploads a deck, the deck agent extracts claims and adds them to the same evidence graph. The system re-scores the opportunity, highlights contradictions, and produces an explainable recommendation: proceed, hold, or decline. Every human decision feeds memory and improves the next search.",
  "This is more than a polished interface. The system already integrates ten types of public data sources, stores 112 persistent founder identities, and passes 106 automated tests. Our north star is to compress the journey from first signal to an investment decision into 24 hours.",
  "FirstCheck24 can be summarized in one line: find first, explain everything, and decide in 24 hours. We help exceptional founders get discovered earlier and help investors make every decision on transparent, verifiable evidence.",
];
const FONT = "Aptos";
const HEAD = "Aptos Display";
const SHADOW = { type: "outer", color: "405875", opacity: 0.12, blur: 2, angle: 45, distance: 1 };
const X = (px) => px / 120;
const PT = (px) => px * 0.6;

function addText(slide, value, x, y, w, h, size, color = C.ink, bold = false, options = {}) {
  slide.addText(value, {
    x: X(x), y: X(y), w: X(w), h: X(h), fontFace: options.fontFace ?? FONT,
    fontSize: PT(size), color, bold, margin: 0, breakLine: false,
    valign: options.valign ?? "mid", align: options.align ?? "left",
    fit: "shrink", paraSpaceAfterPt: 0, isTextBox: true,
    charSpacing: options.charSpacing ?? 0, italic: options.italic ?? false,
    ...options,
  });
}

function addRichText(slide, runs, x, y, w, h, options = {}) {
  slide.addText(runs, { x: X(x), y: X(y), w: X(w), h: X(h), margin: 0, valign: "mid", fit: "shrink", ...options });
}

function box(slide, x, y, w, h, fill, radius = 0.12, options = {}) {
  slide.addShape(pptx.ShapeType.roundRect, {
    x: X(x), y: X(y), w: X(w), h: X(h), rectRadius: radius,
    fill: { color: fill, transparency: options.transparency ?? 0 },
    line: { color: options.lineColor ?? fill, transparency: options.lineTransparency ?? 100, width: options.lineWidth ?? 0.5 },
    shadow: options.shadow ? SHADOW : undefined,
  });
}

function circle(slide, cx, cy, r, fill, transparency = 0) {
  slide.addShape(pptx.ShapeType.ellipse, { x: X(cx - r), y: X(cy - r), w: X(r * 2), h: X(r * 2), fill: { color: fill, transparency }, line: { transparency: 100 } });
}

function line(slide, x1, y1, x2, y2, color = C.line, width = 1.5, dash = "solid") {
  slide.addShape(pptx.ShapeType.line, { x: X(x1), y: X(y1), w: X(x2 - x1), h: X(y2 - y1), line: { color, width, dashType: dash, beginArrowType: "none", endArrowType: "none" } });
}

function arrow(slide, x1, y1, x2, y2, color = C.blue, width = 2) {
  slide.addShape(pptx.ShapeType.line, { x: X(x1), y: X(y1), w: X(x2 - x1), h: X(y2 - y1), line: { color, width, beginArrowType: "none", endArrowType: "triangle" } });
}

function trendSegment(slide, x1, y1, x2, y2, color, width = 2.5) {
  const dx = x2 - x1;
  const dy = y2 - y1;
  const length = Math.hypot(dx, dy);
  const angle = Math.atan2(dy, dx) * 180 / Math.PI;
  const midX = (x1 + x2) / 2;
  const midY = (y1 + y2) / 2;
  slide.addShape(pptx.ShapeType.line, {
    x: X(midX - length / 2), y: X(midY), w: X(length), h: 0.001, rotate: angle,
    line: { color, width, beginArrowType: "none", endArrowType: "none" },
  });
}

function logo(slide, x = 90, y = 52, light = false) {
  addRichText(slide, [
    { text: "FirstCheck", options: { bold: true, fontFace: HEAD, fontSize: 14, color: light ? C.white : C.ink } },
    { text: "24", options: { bold: true, fontFace: HEAD, fontSize: 12, color: light ? "AFC8F6" : C.blue } },
  ], x, y, 180, 32);
}

function footer(slide, number, dark = false) {
  logo(slide, 90, 815, dark);
  addText(slide, String(number).padStart(2, "0"), 1460, 820, 50, 20, 13, dark ? "AFC0D8" : C.muted2, true, { align: "right", charSpacing: 2 });
}

function titleBlock(slide, kicker, title, subtitle = "", titleSize = 52, options = {}) {
  addText(slide, kicker.toUpperCase(), 90, 72, options.width ?? 760, 28, 15, C.blue, true, { charSpacing: 2.4 });
  const lines = title.split("\n").length;
  const titleH = lines * titleSize * 1.04;
  addText(slide, title, 90, 105, options.width ?? 760, titleH, titleSize, C.ink, true, { fontFace: HEAD, valign: "top", breakLine: true, breakLineOnTextOverflow: false });
  if (subtitle) addText(slide, subtitle, 90, 122 + titleH, options.subtitleWidth ?? 920, subtitle.split("\n").length * 32, 20, C.muted, false, { valign: "top", breakLine: true });
}

function pill(slide, label, x, y, w, fill, color, options = {}) {
  box(slide, x, y, w, options.h ?? 35, fill, 0.16);
  addText(slide, label, x + 10, y + 3, w - 20, (options.h ?? 35) - 6, options.size ?? 13, color, true, { align: "center", charSpacing: options.charSpacing ?? 0.3 });
}

function progress(slide, x, y, w, value, color, soft) {
  box(slide, x, y, w, 8, soft, 0.05);
  box(slide, x, y, w * value / 100, 8, color, 0.05);
}

const slides = [];

function addSlide(layout) {
  const slide = layout ? pptx.addSlide(layout) : pptx.addSlide();
  slides.push(slide);
  return slide;
}

function addLightSlide() {
  const slide = addSlide("FIRSTCHECK_LIGHT");
  slide.background = { color: "F2F6FB" };
  return slide;
}

// 01 — Cover
{
  const slide = addSlide();
  slide.background = { color: C.ink };
  circle(slide, 1350, 120, 360, C.blue, 86);
  circle(slide, 1310, 700, 310, C.green, 87);
  logo(slide, 90, 62, true);
  addText(slide, "THE VC OPERATING SYSTEM", 90, 175, 560, 30, 15, "AFC8F6", true, { charSpacing: 3 });
  addText(slide, "Find the founder\nbefore the round.", 90, 235, 850, 180, 72, C.white, true, { fontFace: HEAD, valign: "top", breakLine: true });
  addText(slide, "Autonomous discovery surfaces hidden builders early.\nExplainable intelligence shows exactly why they matter.", 95, 485, 830, 90, 23, "CFDAEA", false, { valign: "top", breakLine: true });
  pill(slide, "FIRST SIGNAL → EVIDENCE → $100K DECISION", 95, 625, 500, "263A55", "DCE8F8", { size: 11 });
  addText(slide, "24:00", 1120, 340, 400, 115, 118, "BFD0EA", true, { fontFace: HEAD, align: "center" });
  addText(slide, "One investor.\nAn entire organisation's reach.", 1120, 475, 400, 62, 20, "DDE7F5", true, { align: "center", valign: "top", breakLine: true });
  addText(slide, "Hack-Nation × MIT Clubs × Maschmeyer Group", 95, 760, 600, 30, 15, "91A7C5");
}

// 02 — Problem
{
  const slide = addLightSlide();
  titleBlock(slide, "The problem", "VC discovers founders\nafter the signal is obvious.", "Discovery starts too late. Diligence restarts from zero. Scores hide their reasoning.");
  const fragments = [
    ["Pitch deck", "private context", C.purpleSoft, C.purple], ["GitHub", "execution trail", C.greenSoft, C.green],
    ["Website", "product claim", C.blueSoft, C.blue], ["Social", "weak signal", C.amberSoft, C.amber],
  ];
  fragments.forEach(([a, b, fill, color], i) => {
    const x = 90 + (i % 2) * 235; const y = 385 + Math.floor(i / 2) * 142;
    box(slide, x, y, 210, 116, fill); circle(slide, x + 25, y + 27, 6, color);
    addText(slide, a, x + 44, y + 14, 140, 34, 17, C.ink, true); addText(slide, b, x + 24, y + 62, 160, 26, 13, C.muted);
  });
  line(slide, 550, 440, 680, 440, "B9C8DA", 2); line(slide, 550, 642, 680, 642, "B9C8DA", 2);
  box(slide, 680, 330, 390, 390, C.white, 0.18, { shadow: true });
  addText(slide, "TODAY", 720, 355, 220, 28, 13, C.rose, true, { charSpacing: 2 });
  addText(slide, "Weeks", 720, 405, 280, 80, 68, C.ink, true, { fontFace: HEAD });
  addText(slide, "to collect, reconcile and\nunderstand one opportunity", 720, 495, 300, 70, 18, C.muted, false, { valign: "top", breakLine: true });
  line(slide, 720, 600, 1025, 600, C.line, 1.2);
  addText(slide, "Capital flows through networks,\nnot merit.", 720, 620, 300, 70, 22, C.rose, true, { valign: "top", breakLine: true });
  box(slide, 1120, 330, 390, 390, "4E70A6", 0.18, { shadow: true });
  addText(slide, "FIRSTCHECK24", 1160, 355, 280, 28, 13, "C7D8F2", true, { charSpacing: 2 });
  addText(slide, "24h", 1160, 405, 280, 84, 78, C.white, true, { fontFace: HEAD });
  addText(slide, "from a valid application\nto an evidence-backed decision", 1160, 495, 300, 70, 18, "D7E3F4", false, { valign: "top", breakLine: true });
  line(slide, 1160, 600, 1465, 600, "7894BA", 1.2);
  addText(slide, "Find them before\nthe market does.", 1160, 620, 300, 70, 24, C.white, true, { valign: "top", breakLine: true });
  footer(slide, 2);
}

// 03 — Two core capabilities
{
  const slide = addLightSlide();
  titleBlock(slide, "The product thesis", "Autonomous discovery.\nExplainable decisions.", "Find hidden founders early — then show\nevery step behind the score.", 48, { width: 560, subtitleWidth: 500 });
  box(slide, 88, 425, 520, 103, C.greenSoft); addText(slide, "CORE 01 · AUTONOMOUS DISCOVERY", 118, 440, 380, 28, 12, C.green, true, { charSpacing: 1.2 }); addText(slide, "Public signals → ranked founders", 118, 475, 430, 32, 20, C.ink, true);
  box(slide, 88, 548, 520, 103, C.purpleSoft); addText(slide, "CORE 02 · EXPLAINABLE INTELLIGENCE", 118, 563, 410, 28, 12, C.purple, true, { charSpacing: 1.1 }); addText(slide, "Source → claim → score → decision", 118, 598, 440, 32, 20, C.ink, true);
  addText(slide, "One investor approves outreach and capital.\nMemory learns from every correction.", 95, 685, 480, 62, 17, C.muted, false, { valign: "top", breakLine: true });
  box(slide, 680, 115, 840, 583, C.white, 0.18, { shadow: true });
  slide.addImage({ path: overview, x: X(692), y: X(127), w: X(816), h: X(559), sizing: "crop", transparency: 0 });
  pill(slide, "LIVE PRODUCT", 1285, 725, 230, C.blueSoft, C.blue);
  footer(slide, 3);
}

// 04 — Sourcing
{
  const slide = addLightSlide();
  titleBlock(slide, "Core 01 · Autonomous discovery", "Always on.\nThesis directed.", "Ten collectors continuously scan execution, research, launches and community signals.", 52);
  const sources = ["GitHub", "Product Hunt", "Hacker News", "arXiv", "Hackathons", "YouTube", "Web", "Tavily", "LinkedIn", "Podcasts"];
  const palette = [[C.greenSoft, C.green], [C.purpleSoft, C.purple], [C.blueSoft, C.blue], [C.amberSoft, C.amber], ["EAF0F6", C.ink2]];
  sources.forEach((source, i) => { const col = i % 5; const row = Math.floor(i / 5); pill(slide, source.toUpperCase(), 90 + col * 220, 315 + row * 58, 198, palette[col][0], palette[col][1], { size: 11 }); });
  const steps = [["01", "Collect", "immutable snapshots"], ["02", "Resolve", "one persistent identity"], ["03", "Score", "thesis + momentum"], ["04", "Activate", "human-approved outreach"]];
  steps.forEach(([n, a, b], i) => { const x = 90 + i * 365; box(slide, x, 545, 315, 165, C.white, 0.16, { shadow: true }); addText(slide, n, x + 25, 560, 60, 24, 13, C.blue, true, { charSpacing: 1.5 }); addText(slide, a, x + 25, 595, 230, 42, 25, C.ink, true, { fontFace: HEAD }); addText(slide, b, x + 25, 645, 250, 28, 15, C.muted); if (i < 3) addText(slide, "→", x + 322, 600, 50, 40, 28, C.blue, false, { align: "center" }); });
  addText(slide, "Cold outreach, never cold investment — every activated founder enters the same application funnel.", 90, 755, 1120, 32, 17, C.ink2, true);
  footer(slide, 4);
}

// 05 — Explainability + Trust
{
  const slide = addLightSlide();
  titleBlock(slide, "Core 02 · Explainable intelligence", "Every score\nshows its work.", "", 52);
  const stack = [["SOURCE SNAPSHOT", "Immutable deck, repo, page or post", C.blueSoft, C.blue], ["OBSERVATION", "Timestamped extraction with provenance", C.purpleSoft, C.purple], ["CLAIM", "Reconciled assertion + contradiction state", C.amberSoft, C.amber], ["AXIS SCORE", "Versioned result linked to supporting claims", C.greenSoft, C.green], ["DECISION MEMO", "Investor conclusion with a complete audit trail", "EAF0F6", C.ink2]];
  stack.forEach(([a, b, fill, color], i) => { const y = 270 + i * 88; box(slide, 90, y, 640, 68, fill); circle(slide, 122, y + 22, 5, color); addText(slide, a, 145, y + 6, 230, 26, 12, color, true, { charSpacing: 1.2 }); addText(slide, b, 380, y + 8, 315, 25, 13, C.ink2, true, { align: "right" }); if (i < 4) line(slide, 410, y + 68, 410, y + 88, C.line, 2); });
  box(slide, 820, 260, 690, 520, C.white, 0.18, { shadow: true });
  addText(slide, "EXPLAINABILITY CONTRACT", 865, 285, 380, 30, 13, C.blue, true, { charSpacing: 1.7 });
  addText(slide, "Every claim answers\nfour questions.", 865, 335, 520, 90, 38, C.ink, true, { fontFace: HEAD, valign: "top", breakLine: true });
  const questions = [["01", "Where did it come from?", C.blue], ["02", "When was it observed?", C.purple], ["03", "How confident are we?", C.amber], ["04", "What contradicts it?", C.green]];
  questions.forEach(([n, q, color], i) => { const y = 470 + i * 58; addText(slide, n, 865, y, 35, 28, 14, color, true); addText(slide, q, 915, y, 480, 28, 18, C.ink2, true); });
  pill(slide, "CLICK SCORE → SOURCE", 865, 718, 280, C.blueSoft, C.blue, { size: 10 });
  pill(slide, "MISSING DATA ≠ BAD FOUNDER", 1160, 718, 305, C.roseSoft, C.rose, { size: 10 });
  footer(slide, 5);
}

// 06 — Multi-axis screening
{
  const slide = addLightSlide();
  titleBlock(slide, "Explainability, not a black box", "A score is not\nan answer.", "Three independent axes preserve disagreement — each with evidence, confidence and trend.", 50);
  const axes = [["Founder", 82, "Bullish", "Improving", C.green, C.greenSoft, [45, 53, 58, 69, 82]], ["Market", 68, "Neutral", "Stable", C.amber, C.amberSoft, [61, 65, 67, 66, 68]], ["Idea × Market", 74, "Bullish", "Improving", C.purple, C.purpleSoft, [52, 55, 63, 70, 74]]];
  axes.forEach(([name, score, rating, trend, color, soft, values], i) => {
    const x = 90 + i * 490; box(slide, x, 300, 445, 440, C.white, 0.18, { shadow: true });
    addText(slide, name, x + 30, 320, 245, 35, 22, C.ink, true, { fontFace: HEAD }); addText(slide, String(score), x + 330, 315, 70, 48, 42, color, true, { fontFace: HEAD, align: "right" });
    pill(slide, rating.toUpperCase(), x + 30, 377, 125, soft, color, { size: 10 }); addText(slide, trend, x + 172, 380, 150, 28, 13, C.muted, true);
    progress(slide, x + 30, 455, 385, score, color, soft); addText(slide, "AXIS SCORE", x + 30, 472, 180, 22, 11, C.muted2, true, { charSpacing: 1.3 });
    line(slide, x + 30, 620, x + 415, 620, C.line, 0.8, "dash");
    const points = values.map((v, j) => [x + 35 + j * 92, 680 - v * 2.1]);
    points.slice(0, -1).forEach((point, j) => trendSegment(slide, point[0], point[1], points[j + 1][0], points[j + 1][1], color, 2.5));
    points.forEach(([px, py]) => circle(slide, px, py, 5, color));
    addText(slide, "TREND · LAST 5 UPDATES", x + 30, 682, 260, 22, 11, C.muted2, true, { charSpacing: 1.1 });
  });
  addText(slide, "Click any axis → inspect evidence, confidence, contradictions and trend.", 90, 755, 900, 32, 18, C.ink2, true);
  pill(slide, "INDEPENDENT · NOT AVERAGED", 1160, 755, 350, C.blueSoft, C.blue, { size: 10 });
  footer(slide, 6);
}

// 07 — Investor experience (Eoghan McCabe)
{
  const slide = addLightSlide();
  titleBlock(slide, "Live decision case · Eoghan McCabe", "A decision, not\na dashboard.", "AI compresses the evidence.\nThe investor can challenge every claim.", 40, { width: 410, subtitleWidth: 400 });
  box(slide, 535, 90, 985, 684, C.white, 0.18, { shadow: true });
  slide.addImage({ path: decision, x: X(547), y: X(102), w: X(961), h: X(660), sizing: "crop" });
  box(slide, 90, 390, 365, 86, C.blueSoft); addText(slide, "AI SUMMARY + CITATIONS", 117, 405, 290, 24, 11, C.blue, true, { charSpacing: 1.2 }); addText(slide, "Every sentence traces to evidence", 117, 435, 300, 30, 16, C.ink, true);
  box(slide, 90, 495, 365, 86, C.purpleSoft); addText(slide, "SCORE EXPLANATION", 117, 510, 280, 24, 11, C.purple, true, { charSpacing: 1.3 }); addText(slide, "Score → claim → source", 117, 540, 290, 30, 17, C.ink, true);
  box(slide, 90, 600, 365, 86, C.greenSoft); addText(slide, "HUMAN CONTROL", 117, 615, 250, 24, 11, C.green, true, { charSpacing: 1.5 }); addText(slide, "Challenge · override · decide", 117, 645, 300, 30, 16, C.ink, true);
  pill(slide, "LIVE PRODUCT · EOGHAN MCCABE", 1160, 795, 350, C.blueSoft, C.blue, { size: 10 });
  footer(slide, 7);
}

// 08 — End-to-end agent architecture
{
  const slide = addLightSlide();
  titleBlock(slide, "Agent architecture", "Two entry paths. One evidence pipeline.", "Outbound discovers hidden founders. Inbound turns applications and decks into structured evidence.", 44, { width: 1240, subtitleWidth: 1320 });

  pill(slide, "OUTBOUND · PROACTIVE", 90, 246, 245, C.blueSoft, C.blue, { size: 10 });
  const outbound = [
    ["01", "DISCOVER", "Thesis + public signals", C.blueSoft, C.blue],
    ["02", "SIGNAL SCORE", "Fast triage", C.purpleSoft, C.purple],
    ["03", "PROMISING", "Human gate", C.greenSoft, C.green],
    ["04", "FOOTPRINTS", "Identity + evidence", C.amberSoft, C.amber],
    ["05", "3-AXIS SCORE", "Founder · Market · Fit", C.purpleSoft, C.purple],
    ["06", "OUTREACH", "Draft + approve", C.blueSoft, C.blue],
  ];
  outbound.forEach(([n, a, b, fill, color], i) => {
    const x = 90 + i * 245;
    box(slide, x, 300, 210, 116, fill, 0.14, { shadow: i === 5 });
    pill(slide, n, x + 16, 315, 42, C.white, color, { h: 28, size: 9 });
    addText(slide, a, x + 16, 351, 178, 23, 13, color, true, { charSpacing: 0.8 });
    addText(slide, b, x + 16, 380, 178, 22, 11, C.ink2, true);
    if (i < outbound.length - 1) arrow(slide, x + 213, 358, x + 241, 358, color, 1.8);
  });

  arrow(slide, 1525, 418, 1525, 492, C.blue, 2.2);
  pill(slide, "INBOUND · RESPONSE", 1275, 455, 250, C.greenSoft, C.green, { size: 10 });
  const inbound = [
    ["11", "RECOMMEND", "Proceed · Hold · Decline", C.greenSoft, C.green],
    ["10", "RE-SCORE", "Axes + SWOT + trend", C.purpleSoft, C.purple],
    ["09", "EVIDENCE GRAPH", "Claims + provenance", C.blueSoft, C.blue],
    ["08", "DECK AGENT", "Extract + challenge", C.amberSoft, C.amber],
    ["07", "INBOUND", "Application + pitch deck", C.greenSoft, C.green],
  ];
  inbound.forEach(([n, a, b, fill, color], i) => {
    const x = 90 + i * 294;
    box(slide, x, 510, 250, 116, fill, 0.14, { shadow: i === 0 });
    pill(slide, n, x + 16, 525, 42, C.white, color, { h: 28, size: 9 });
    addText(slide, a, x + 16, 561, 218, 23, 13, color, true, { charSpacing: 0.7 });
    addText(slide, b, x + 16, 590, 218, 22, 11, C.ink2, true);
    if (i < inbound.length - 1) arrow(slide, x + 290, 568, x + 254, 568, color, 1.8);
  });

  box(slide, 90, 664, 1470, 58, "E9F0F8", 0.12);
  addText(slide, "HUMAN DECISIONS + OUTCOMES", 115, 678, 340, 25, 12, C.ink2, true, { charSpacing: 0.8 });
  addText(slide, "→", 455, 675, 45, 25, 18, C.blue, true, { align: "center" });
  addText(slide, "MEMORY", 510, 678, 120, 25, 12, C.blue, true, { charSpacing: 1.2 });
  addText(slide, "→", 640, 675, 45, 25, 18, C.blue, true, { align: "center" });
  addText(slide, "SHARPER THESIS + FUTURE SCORING", 695, 678, 430, 25, 12, C.ink2, true, { charSpacing: 0.8 });
  pill(slide, "React + TypeScript", 90, 747, 195, C.white, C.blue, { size: 9 });
  pill(slide, "FastAPI", 300, 747, 125, C.white, C.purple, { size: 9 });
  pill(slide, "ARQ + Redis", 440, 747, 145, C.white, C.amber, { size: 9 });
  pill(slide, "Postgres + pgvector", 600, 747, 215, C.white, C.green, { size: 9 });
  pill(slide, "MinIO + Docker", 830, 747, 180, C.white, C.ink2, { size: 9 });
  pill(slide, "VERSIONED EVIDENCE", 1160, 747, 250, C.blueSoft, C.blue, { size: 9 });
  footer(slide, 8);
}

// 09 — Proof
{
  const slide = addLightSlide();
  titleBlock(slide, "Proof, not promise", "Built, tested,\nand decision-ready.", "Real data, live state transitions, reproducible scores and an investor-ready interface.", 50);
  const metrics = [["10", "public-source\ncollectors", C.green], ["112", "persistent founder\nidentities", C.blue], ["106", "automated\ntests passed", C.purple], ["24h", "decision\nnorth star", C.amber]];
  metrics.forEach(([value, label, color], i) => { const x = 90 + i * 370; box(slide, x, 300, 330, 235, C.white, 0.18, { shadow: true }); addText(slide, value, x + 30, 330, 220, 66, 64, color, true, { fontFace: HEAD }); addText(slide, label, x + 30, 415, 240, 65, 20, C.ink2, true, { valign: "top", breakLine: true }); });
  const wins = [["Autonomous discovery", "Signals before fundraising"], ["Explainable scoring", "Per-claim provenance + confidence"], ["Actionable output", "Memo + next step + human approval"], ["Learning memory", "Every outcome sharpens future scoring"]];
  wins.forEach(([a, b], i) => { const x = 90 + i * 370; circle(slide, x + 8, 650, 6, C.green); addText(slide, a, x + 27, 632, 280, 30, 16, C.ink, true); addText(slide, b, x + 27, 668, 300, 30, 13, C.muted); });
  pill(slide, "SOURCING → SCREENING → DILIGENCE → DECISION", 485, 760, 630, C.blueSoft, C.blue, { size: 11 });
  footer(slide, 9);
}

// 10 — Close
{
  const slide = addSlide();
  slide.background = { color: C.ink };
  circle(slide, 1270, 150, 380, C.blue, 86); circle(slide, 240, 840, 310, C.green, 86);
  logo(slide, 90, 62, true); addText(slide, "THE OUTCOME", 90, 205, 330, 30, 15, "AFC8F6", true, { charSpacing: 3 });
  addText(slide, "Find first.\nExplain everything.\nDecide in 24h.", 90, 260, 900, 230, 64, C.white, true, { fontFace: HEAD, valign: "top", breakLine: true });
  addText(slide, "From a fragmented public signal to an evidence-backed\n$100K decision — with one human in control.", 95, 585, 760, 80, 23, "CFDAEA", false, { valign: "top", breakLine: true });
  pill(slide, "FIRSTCHECK24", 95, 720, 260, "263A55", "DCE8F8", { size: 11 });
  addText(slide, "Autonomous discovery. Explainable decisions.", 880, 755, 620, 34, 18, "AFC0D8", true, { align: "right" });
}

slides.forEach((slide, index) => slide.addNotes(SPEAKER_NOTES[index]));

await pptx.writeFile({ fileName: output });
console.log(output);
