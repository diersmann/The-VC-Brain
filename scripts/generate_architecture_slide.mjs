import path from "node:path";
import { createRequire } from "node:module";

const root = path.resolve(import.meta.dirname, "..");
const requireFromFrontend = createRequire(path.join(root, "frontend", "package.json"));
const PptxGenJS = requireFromFrontend("pptxgenjs");

const output = path.join(root, "docs", "FirstCheck24_Architecture_60s.pptx");
const architecture = path.join(root, "docs", "pitch-assets", "architecture-flow.svg");
const speakerNotes = "FirstCheck24 runs one evidence pipeline with two connected entry paths. Outbound starts from the fund thesis. A discovery agent scans public sources, creates an initial signal score, and places high-potential founders in a promising queue. A footprint agent then resolves identity and gathers deeper technical, company, and network evidence. The three-axis engine scores Founder, Market, and Idea–Market Fit independently, including trends, confidence, and SWOT. If the case is strong, the outreach agent drafts a personalized message, with the investor approving the send. When a founder applies inbound and uploads a deck, the deck agent extracts claims and adds them to the same evidence graph. The system re-scores the opportunity, highlights contradictions, and produces an explainable recommendation: proceed, hold, or decline. Every human decision feeds memory and improves the next search.";

const pptx = new PptxGenJS();
pptx.layout = "LAYOUT_WIDE";
pptx.author = "FirstCheck24";
pptx.company = "FirstCheck24";
pptx.subject = "Agent architecture and 60-second pitch";
pptx.title = "FirstCheck24 Architecture — 60 Seconds";
pptx.lang = "en-US";

const slide = pptx.addSlide();
slide.background = { color: "F2F6FB" };
slide.addImage({ path: architecture, x: 0, y: 0, w: 13.333, h: 7.5 });
slide.addNotes(speakerNotes);

await pptx.writeFile({ fileName: output });
console.log(output);
