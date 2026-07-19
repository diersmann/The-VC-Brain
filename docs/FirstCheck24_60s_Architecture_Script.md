# FirstCheck24 — 60-Second Architecture Script

FirstCheck24 is built as one evidence pipeline with two entry paths.

Outbound starts from an investor thesis: discovery agents scan public sources, create a signal score, promote promising founders, enrich their digital footprints, and draft approved outreach. Inbound starts with an application or pitch deck: a deck agent extracts claims and adds them to the same evidence graph.

Both paths converge on our explainable three-axis engine, which scores Founder, Market, and Idea–Market Fit independently, with SWOT, trends, confidence, and source-level provenance.

React and TypeScript power the investor workflow. FastAPI orchestrates agent services, while ARQ and Redis run asynchronous collection jobs. Postgres and pgvector store identities, evidence, memory, and scores; MinIO preserves source artifacts, and Docker makes deployment reproducible.

Finally, the system recommends proceed, hold, or decline, while every human decision feeds memory and improves future discovery and scoring.

_Approximate delivery time: 58–62 seconds at a natural pitch pace._
