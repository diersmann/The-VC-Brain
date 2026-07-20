import path from "node:path";
import { createRequire } from "node:module";

const root = path.resolve(import.meta.dirname, "..");
const requireFromFrontend = createRequire(path.join(root, "frontend", "package.json"));
const PptxGenJS = requireFromFrontend("pptxgenjs");

const output = path.join(root, "docs", "FirstCheck24_Architecture_60s.pptx");
const architecture = path.join(root, "docs", "pitch-assets", "architecture-flow.svg");
const speakerNotes = "FirstCheck24 is built as one evidence pipeline with two entry paths. Outbound starts from an investor thesis: discovery agents scan public sources, create a signal score, promote promising founders, enrich their digital footprints, and draft approved outreach. Inbound starts with an application or pitch deck: a deck agent extracts claims and adds them to the same evidence graph. Both paths converge on our explainable three-axis engine, which scores Founder, Market, and Idea–Market Fit independently, with SWOT, trends, confidence, and source-level provenance. React and TypeScript power the investor workflow. FastAPI orchestrates agent services, while ARQ and Redis run asynchronous collection jobs. Postgres and pgvector store identities, evidence, memory, and scores; MinIO preserves source artifacts, and Docker makes deployment reproducible. Finally, the system recommends proceed, hold, or decline, while every human decision feeds memory and improves future discovery and scoring.";

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
