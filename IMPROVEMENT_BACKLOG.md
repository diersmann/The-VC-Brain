# The VC Brain - Improvement Backlog

Status: open backlog
Audit date: 2026-08-02
Audited branch: post-hackathon-polish at 8f072a8
Comparison base: origin/main at b4dcc88

## Purpose

This is an implementation backlog for the next coding agent. It is grounded in the current code, the nine-page challenge brief, docs/ARCHITECTURE.md, local validation, and live browser QA at desktop and mobile widths.

The main conclusion is simple: make the product truthful before making it broader. Several screens and lifecycle events currently present drafts, fallbacks, missing values, or operational failures as completed investment work. The first milestones should make states, scores, evidence, outreach, memos, and SLA claims precise and auditable.

## How to use this backlog

- Priorities are P0 (trust, safety, or core-contract blocker), P1 (next complete product milestone), P2 (quality, UX, and production readiness), and P3 (differentiated learning features).
- Evidence labels: Observed means directly reproduced or read in code; Missing means a required capability was not found; Inferred means a concrete risk follows from the implementation and should be verified while implementing.
- Before taking an item, inspect its evidence and dependencies, then update this file with owner/status or link the replacement issue.
- Preserve the hard project rules: Founder Score is person-scoped; Market and Idea-vs-Market are opportunity-scoped; Trust Score is claim-scoped; missing evidence lowers confidence, not founder quality; network signals aid sourcing, not merit.
- A backlog item is not done until behavior, tests, migrations, documentation, and observability are updated together.

## Recommended delivery sequence

1. Truth and safety: VCB-001 through VCB-018.
2. Evidence and lifecycle foundation: VCB-019 through VCB-035, VCB-051 through VCB-057.
3. Fair sourcing and a complete investment workflow: VCB-036 through VCB-050, VCB-058 through VCB-060.
4. Investor-grade UX and engineering quality: VCB-061 through VCB-101.
5. Learning and differentiation only after trustworthy data exists: VCB-102 through VCB-110.

## P0 - Product truth, security, and data integrity

- [ ] **VCB-001 - Remove the fake application path and keep one real submission flow.** Observed: App.tsx:19 exposes /apply; InboundPage.tsx:5-20 discards all form values, does not require a deck, and shows success for hard-coded Aperture AI. Done when /apply redirects to or shares the real /submit implementation, a failed request can never show success, and an integration test verifies the persisted opportunity ID and uploaded deck.

- [ ] **VCB-002 - Add authentication, fund/tenant scoping, and RBAC.** Observed: main.py:22-32 mounts all routers without auth; candidates.py:95-115 exposes email, handles, and consent; unauthenticated callers can decide, contact, collect, merge identities, and change the active thesis. Done when only health and a rate-limited public submission endpoint are anonymous, every internal route enforces role and tenant scope, and 401/403 coverage exists.

- [ ] **VCB-003 - Fix FastAPI database-session lifecycle.** Observed: db/session.py:23-28 returns an AsyncSession rather than yielding it from a closing context. Done when requests close sessions deterministically, roll back on exceptions, and a concurrency test proves checked-out connections return to baseline.

- [ ] **VCB-004 - Harden untrusted pitch uploads before storage or parsing.** Observed: inbound.py:23-48 reads the full upload into memory with no byte, MIME-signature, filename, page, encryption, malware, or decompression limits; inbound_job.py:42-53 parses it inside the privileged worker. Done when uploads stream to quarantine, are validated and scanned, parsing is resource-limited/isolated, and abuse tests cover oversized, polyglot, encrypted, malformed, and bomb files.

- [ ] **VCB-005 - Make inbound submission transactional and idempotent.** Observed: inbound.py:74-85 commits before Redis enqueue, leaks a new Redis pool, and has no idempotency key; retries can create duplicate opportunities or persisted work that never runs. Done when one DB transaction writes the application and durable outbox, duplicate client retries resolve to the same submission, and dispatch is recoverable after Redis outages.

- [ ] **VCB-006 - Converge activated outbound submissions into the same opportunity.** Observed: outreach sends a generic /submit link; inbound creates a new opportunity; lifecycle_job.py:289-295 intentionally leaves the outbound record at contacted. Done when signed expiring activation tokens bind person, opportunity, thesis, and channel, and a valid submission advances the same opportunity while ambiguous identity matches enter review.

- [ ] **VCB-007 - Require explicit opportunity IDs for every opportunity-scoped job.** Observed: opportunity_service.py:21-54 returns the latest opportunity for a person; memo_job.py:110-115 may create/reuse an outbound opportunity; collectors/jobs.py:998-1002 drops the inbound opportunity ID. Done when research, assessment, memo, and decision work reject ambiguous person-only invocation and multi-company tests prove isolation.

- [ ] **VCB-008 - Replace simulated outreach with honest delivery states.** Observed: lifecycle_job.py:268-287 marks contacted before work; contact_job.py:60-104 stores an outreach_email_draft and writes Cold outreach sent without any mail-provider call. Done when drafted, approved, send_requested, sent, delivered, bounced, replied, opted_out, and failed are distinct; only provider-confirmed send changes delivery state; first contact requires human approval and suppression checks.

- [ ] **VCB-009 - Separate Founder Score, sourcing signal, thesis alignment, and opportunity assessments.** Observed: candidates.py:226-254 merges newest components across every person-scoped rubric; Tavily stores Market and Idea-Market in person snapshots. Done when each artifact has one subject type and schema, and no Market or Idea-Market value can leak across a repeat founder's companies.

- [ ] **VCB-010 - Implement the canonical independent three-axis assessment contract.** Observed: scoring_job.py:88-108 persists execution, technical, and commercial as Assessment axes, while the product requires Founder, Market, and Idea-vs-Market. Done when specialist dimensions feed the persistent Founder Score, a separate opportunity assessor emits exactly the three required axes, and API/UI/tests use one versioned ontology without averaging them.

- [ ] **VCB-011 - Treat missing evidence as unknown, never bearish or zero.** Observed: collectors/jobs.py:676-709 assigns 0.30 and Bearish when Tavily returns nothing; candidateProfile.ts:14-20 and 131-133 convert null scores to zero. Done when absent evidence yields neutral/unknown with low confidence and explicit gaps, and cold-start regression tests prove it cannot reduce founder quality.

- [ ] **VCB-012 - Generate memos only from accepted claims for the exact opportunity and pinned thesis.** Observed: memo_job.py:47-108 consumes raw observations, person-wide assessments, and the currently active thesis. Done when memo inputs are immutable accepted-claim and assessment snapshots for one opportunity/thesis version, with contradictions and unavailable data surfaced inline.

- [ ] **VCB-013 - Validate memo citations and sentence support server-side.** Observed: memo.py:143-153 accepts arbitrary model-returned evidence IDs; memo_job.py:129-143 unions them with every observation and truncates an unordered set. Done when every citation is membership- and scope-checked, factual sentences map to supporting claim IDs, unknown IDs fail validation, and citation order is deterministic.

- [ ] **VCB-014 - Do not let fallback content make an opportunity memo-ready.** Observed: memo.py:77-89 returns placeholder sections when the model is unavailable; the row is persisted and lifecycle_job.py:297-304 treats any memo as ready. Done when memo runs have pending/failed/degraded/succeeded status and only a validated successful memo satisfies the lifecycle gate.

- [ ] **VCB-015 - Route decisions through the lifecycle domain service with real actor attribution.** Observed: candidates.py:708-743 mutates the latest opportunity directly, permits any source state, and hard-codes vc-ui:sophie-werner. Done when the authenticated actor, exact opportunity, allowed source state, evidence snapshot, idempotency key, and optimistic/row lock are enforced and stale concurrent decisions return 409.

- [ ] **VCB-016 - Make reconciliation idempotent and define one supersession direction.** Observed: reconcile.py:50-131 creates new claims on every run; contradiction and dedup code use opposite supersession semantics; valid_time_end is never closed. Done when unchanged inputs create zero rows, superseded_by semantics are consistent, prior validity closes atomically, and current truth is deterministic.

- [ ] **VCB-017 - Make identity resolution conservative, auditable, and reversible.** Observed: matchers.py:193-212 auto-merges fuzzy name plus company/location at 0.85; merge.py:84-125 rewrites evidence, omits Claim subjects and conflict handling, and deletes self-relationships. Done when only verified stable identifiers auto-merge, fuzzy matches require review, original subjects/provenance remain immutable, all dependents are covered, and merge rollback is tested.

- [ ] **VCB-018 - Never present operational failure as valid investment data.** Observed in live QA: HomePage.tsx:11-30 turns API 500s into a healthy zero pipeline/no thesis; PitchSubmissionPage.tsx:21-29 reduces submit failure to an alert and returns to an apparently normal form. Done when loading, empty, partial, offline, permission, and failure states are distinct, persistent, accessible, retryable, and never mutate or imply investment conclusions.

## P1 - Complete the trustworthy product loop

- [ ] **VCB-019 - Enforce append-only evidence and audit history.** Observed: model FKs cascade-delete snapshots, observations, assessments, events, and memos; import_public_inbound.py:120-136 updates observations in place. Done when normal application roles cannot mutate/delete evidence, corrections append superseding records, and privacy erasure retains lawful non-sensitive tombstones.

- [ ] **VCB-020 - Implement a real per-claim Trust Score.** Observed: Claim stores a scalar confidence; candidateProfile.ts:53-73 relabels confidence as Trust. Done when versioned inputs include source authority, directness, independence, corroboration, freshness, extraction and identity confidence, contradiction penalties, explanation, status, and calibrated interval.

- [ ] **VCB-021 - Model contradiction sets without silently choosing a favorable winner.** Observed: reconcile.py:23-29 uses confidence times recency and treats all values for a predicate as timeless competitors. Done when temporal change is distinct from same-time conflict, contradiction sets retain every version, and policy/human resolution is explicit and evidence-linked.

- [ ] **VCB-022 - Preserve source coordinates end to end.** Observed: inbound_job.py concatenates pages and truncates at 50k; observation/claim DTOs omit page, slide, DOM fragment, or text span. Done when every claim can open the immutable source at its page/slide/timestamp/span and unavailable content still exposes provenance metadata.

- [ ] **VCB-023 - Make advertised deck formats match actual parser support.** Observed: PitchSubmissionPage.tsx:169-175 accepts PDF/PPT/PPTX while inbound_job.py always uses pypdf. Done when the product is PDF-only with server enforcement or safely parses every advertised format with coordinates and format-specific tests.

- [ ] **VCB-024 - Orchestrate inbound through triage, Founder Score, three axes, diligence, memo, and decision.** Observed: inbound_job.py:55-101 reconciles/embeds/deduplicates then queues a memo without scoring or opportunity assessment. Done when every stage has a durable run/output and explicit gap/failure state before a validated memo can be ready.

- [ ] **VCB-025 - Implement the real 24-hour SLA clock.** Missing: Opportunity has no received_at, decision_due_at, stage deadlines, owner, or pause reason; DecisionDetail shows Not scheduled. Done when per-stage budgets, countdown/breach states, alerts, owner, p50/p90 metrics, and persisted SLA attainment derive from events rather than UI guesses.

- [ ] **VCB-026 - Align one canonical lifecycle across domain, jobs, API, and workflow diagram.** Observed: lifecycle.py and lifecycle_job.py use a simplified vocabulary while the dashboard claims triage, screening, diligence, memo, and feedback. Done when a versioned state machine defines entry/exit requirements, actors, timestamps, transitions, and tests the UI diagram against the same source.

- [ ] **VCB-027 - Persist a structured decision proposal and readiness snapshot.** Observed: DecisionDetailPage.tsx:555-593 synthesizes Proceed/Hold/Investigate and narrative locally; backend decision accepts only action/reason. Done when backend artifacts include action, check amount, conviction, exact three-axis IDs, evidence, risks, open conditions, readiness blockers, versions, and override reason.

- [ ] **VCB-028 - Make reviewed outreach a first-class workspace.** Observed: InvestigatedPage.tsx:14-21 immediately calls /contact while an OutreachComposer exists elsewhere. Done when Contact opens an editable draft, displays evidence/contact provenance and suppression, requires explicit approval, and shows provider delivery/reply state.

- [ ] **VCB-029 - Gate external AI use with privacy purpose and PII minimization.** Observed: scoring.py:422-427 sends email/handles and raw deck observations while consent defaults to pending. Done when legal basis/notice version, provider policy, retention/residency, redaction, and per-purpose consent controls are modeled and pending/suppressed data cannot leave the system.

- [ ] **VCB-030 - Add correction, export, deletion, retention, and outreach-suppression workflows.** Missing: only a free-form consent_state exists. Done when authenticated rights requests, global/channel do-not-contact, retention jobs, correction review, export, restricted processing, deletion propagation, and audit events are complete.

- [ ] **VCB-031 - Enforce source-use and licensing policy.** Observed: SourceSnapshot.license_metadata is nullable and no central connector policy gate exists. Done when every source declares allowed collection, retention, display, model, contact, and export uses, and disallowed/unknown content is quarantined rather than scored.

- [ ] **VCB-032 - Normalize Organization, Opportunity, and founder-role relationships.** Observed: Opportunity stores company_name instead of an Organization FK; Organization is minimally used. Done when company identity, founder roles with valid time, applications, source channel, and multi-founder teams are first-class and company research no longer attaches to a person.

- [ ] **VCB-033 - Replace polymorphic UUID/JSON references with enforceable evidence links.** Observed: Observation.subject_id, Claim.subject_id, ScoreSnapshot.subject_id, observation_ids, and evidence_ids have little or no referential integrity. Done when typed subjects and FK-backed join tables reject orphan or wrong-scope evidence.

- [ ] **VCB-034 - Version every derived artifact and model invocation.** Observed: Assessments lack rubric/prompt/model/input package metadata; score metadata returned by agents is not fully persisted. Done when claims, relations, scores, assessments, memos, and proposals store run ID, code/rubric/prompt/model versions, parameters, input fingerprint, latency, cost, validator result, and compatibility.

- [ ] **VCB-035 - Treat validator failure as failure and verify agent citations deterministically.** Observed: scoring.py returns an empty critique on missing key/API/JSON failure and aggregation interprets it as no hard issues. Done when validator_status is explicit, threshold actions require successful validation, and cited IDs/support are checked outside the LLM.

- [ ] **VCB-036 - Build a visible natural-language sourcing query planner.** Observed: SourcingPage sends a compound default query to hard-coded GitHub; github.py:54-65 interprets the entire string as a location. Done when role, geography, sector, traction, exclusions, freshness, and graph clauses compile into a user-visible plan with corrections and per-result clause explanations.

- [ ] **VCB-037 - Stop ranking candidates by averaging the three axes.** Observed: SourcingPage.tsx:57-64 averages Founder, Market, and Idea-Market despite the product contract. Done when a documented thesis-specific ranking policy preserves disagreement, floors/material risks are visible, and ranking explanations show why one opportunity precedes another.

- [ ] **VCB-038 - Use a versioned activation priority model.** Observed: lifecycle gates mostly on signal composite/founder aggregate. Done when priority includes thesis fit, novelty, momentum, evidence confidence, identity confidence, contactability, deadline, cost, and exploration quota, with missing values explicit and offline evaluation.

- [ ] **VCB-039 - Add a real cold-start evidence path.** Missing: structured work samples, prototypes, references, interviews, and learning-velocity inputs. Done when quiet/no-profile applicants can submit comparable direct work evidence and missing public history widens uncertainty without lowering merit.

- [ ] **VCB-040 - Add fairness evaluation and scoring guardrails.** Observed: public stars, votes, citations, and appearances shape discovery; arXiv hard-filters by citation count. Done when proxy-sensitive features are documented, subgroup coverage/error/advancement/override metrics exist where lawful, and new rankers run in shadow mode before affecting recommendations.

- [ ] **VCB-041 - Make collection persistence idempotent.** Observed: collectors/jobs.py:132-187 inserts new snapshot and observation rows even when MinIO detects identical content. Done when source/snapshot/observation fingerprints and conflict-safe refresh versions make unchanged collection runs produce no duplicates.

- [ ] **VCB-042 - Validate observation schemas at ingestion.** Observed: empty values, arbitrary confidence, naive string dates, and missing coordinates can be inserted. Done when UTC time, nonempty predicate/value, confidence range, extractor schema, source coordinates, and future-time tolerance are enforced and invalid outputs are quarantined.

- [ ] **VCB-043 - Give signal snapshots deterministic provenance.** Observed: signal aggregation uses arbitrary historical setdefault values and writes evidence_ids empty. Done when signals select latest valid claims deterministically, retain exact evidence and coverage/confidence, fingerprint outputs, and quarantine malformed numerics.

- [ ] **VCB-044 - Treat search snippets and synthesized answers as leads, not trusted claims.** Observed: Tavily results/answers become observations and a nonstandard tavily_synthesized Claim. Done when original pages are fetched and verified, search output stays low-authority discovery material, and unsupported conclusions cannot enter accepted claims.

- [ ] **VCB-045 - Repair Tavily discovery routing.** Observed: tavily_search emits web seeds, discover_job ignores seed source type, then invokes Tavily collect which raises NotImplementedError. Done when declared collection connector and discovery provenance are distinct and an end-to-end Tavily discovery test persists verified web observations.

- [ ] **VCB-046 - Classify entities before founder scoring.** Observed: hackathon projects, YouTube channels, Tavily URLs, and other seeds are all passed through person creation. Done when Person, Organization, Project, Channel, and Event are classified with confidence and only verified people enter founder ranking.

- [ ] **VCB-047 - Fix Product Hunt query and cursor semantics.** Observed: the GraphQL query variable is unused and pagination fabricates an offset instead of provider cursor. Done when thesis/query inputs affect results, pageInfo cursors are used, and multi-page tests show no skip/duplication.

- [ ] **VCB-048 - Remove citation count as an arXiv eligibility gate.** Observed: arxiv.py:55-118 drops authors below the configured citation minimum. Done when citations are one confidence/momentum observation, recent uncited work remains discoverable through exploration, and cold-start coverage is measured.

- [ ] **VCB-049 - Make connectors async-safe and block SSRF.** Observed: multiple async connectors call synchronous Tavily SDKs; website.py follows arbitrary redirects and buffers arbitrary URLs without private-IP/size checks. Done when calls have bounded async/thread execution, cancellation/timeouts, redirect-by-redirect IP validation, HTTP(S) allow rules, and streamed byte limits.

- [ ] **VCB-050 - Classify connector failures for retries and operator action.** Observed: collect_job converts exceptions into successful result dictionaries and several connectors return empty lists on upstream errors. Done when transient/rate-limit/permanent failures are persisted distinctly, retry with backoff/jitter, and end in a visible DLQ when exhausted.

- [ ] **VCB-051 - Add a durable job ledger with real job IDs.** Missing: durable status/progress/error/result for collection, research, scoring, memo, parsing, and identity work. Done when trigger endpoints return a job ID and UI can resume polling/subscription after navigation with phase, attempt, progress, last error, and cancel/retry.

- [ ] **VCB-052 - Make DB transitions, queue delivery, and budgets crash-safe.** Observed: lifecycle mutates DB/decrements Redis budget/enqueues before final commit; dispatcher pops a task before Arq enqueue. Done when transactional outbox/inbox, deterministic job IDs, lease/ack/requeue, and budget reservation/refund prevent loss or duplicate side effects.

- [ ] **VCB-053 - Correct provider/model budget accounting.** Observed: worker.py:45-48 resets a monthly budget on every restart; tasks are charged rather than actual calls/tokens; manual routes bypass caps. Done when billing-period counters survive restarts, every entry point reserves/reconciles actual usage, and skipped work visibly changes confidence.

- [ ] **VCB-054 - Prevent historical scores from stalling or satisfying a new opportunity.** Observed: lifecycle_job.py:77-87 and 177-268 checks any person-wide founder-agent score and can leave interesting opportunities stuck or reuse stale results. Done when stage outputs are keyed by opportunity/run while historical Founder Score remains only a versioned input.

- [ ] **VCB-055 - Schedule pipeline work by SLA risk and fairness.** Observed: lifecycle_job.py:126-136 repeatedly selects the oldest five; budget-blocked rows can starve later work. Done when decision_due_at, stage budget, fair pagination, SKIP LOCKED/concurrency, and needs-attention queues drive priority.

- [ ] **VCB-056 - Complete the thesis editor and immutable version history.** Observed: OnboardingPage hard-codes name, ownership, risk, exclusions, and weights; backend uses count+1 versioning and rescoring mutates opportunity thesis_version. Done when every persisted dimension round-trips, save is race-safe, history/compare/clone/activate/rollback exist, and decisions keep their original thesis.

- [ ] **VCB-057 - Make thesis scoring typed, evidence-backed, and benchmarked.** Observed: thesis.py is primarily keyword/rule matching with neutral defaults. Done when structured constraints, semantic similarity, and analyst judgment are distinct; every dimension returns evidence/missing/confidence/version; exclusions are explicit; labeled benchmarks guard precision.

- [ ] **VCB-058 - Build one opportunity inbox instead of fragmented person views.** Observed: Inbound, Investigated, and Decisions are separate filters and Opportunity DTO lacks owner/deadline/next action. Done when a unified inbound/outbound inbox shows current stage, source ancestry, owner, SLA risk, next action, blockers, and saved views.

- [ ] **VCB-059 - Preserve channel attribution and measure conversion quality.** Missing: first-touch, contributing source/query, outreach, application, and decision conversion are not connected. Done when multi-touch events support funnel latency, evidence yield, false positives, cost, and conversion by channel without treating correlation as merit.

- [ ] **VCB-060 - Persist analyst feedback instead of local dismissals.** Observed: CandidateCard.tsx:30-32 and 77-87 hides a card only in component state. Done when dismiss/save/assign/defer include structured reason, audit, undo, prior-feedback visibility, and are kept separate from investment outcome labels.

## P2 - Investor-grade UX, engineering quality, and production readiness

- [ ] **VCB-061 - Make memo and claim evidence drillable.** Observed: DecisionDetailPage.tsx:444-454 shows only an evidence-reference count; claim/assessment/relationship DTOs omit key provenance. Done when every memo sentence and claim opens source excerpt, coordinates, authority, freshness, Trust interval, counter-evidence, supersession, and derivation metadata.

- [ ] **VCB-062 - Finish the founder profile's core analytical views.** Observed: candidateProfile.ts builds timeline, coverage, relations, affiliations, and gaps, but FounderProfilePage does not render most of them. Done when profile exposes persistent score history, evidence timeline, coverage/gaps, projects, typed graph, corrections, and weak-vs-verified relationship semantics.

- [ ] **VCB-063 - Replace one-shot timers with durable async progress.** Observed: memo generation refetches once after 5 seconds; research once after 65 seconds; queued state can remain forever. Done when job status drives bounded polling/subscription, terminal timeout/error, retry, last-updated, and cleanup on unmount.

- [ ] **VCB-064 - Add complete mobile navigation and decision flows.** Observed in live QA at 390px: LeftNav.tsx:14 hides the only navigation and RootLayout supplies no replacement. Done when accessible mobile nav exposes all routes/current state and core sourcing, evidence, memo, and decision tasks pass 320/390/768px visual tests without clipping.

- [ ] **VCB-065 - Fix semantic and dialog accessibility.** Observed: pointer-only article cards, nested interactive inbound rows, a non-keyboard upload div, placeholder-only form labels, an outreach dialog without focus trap/Escape/restore, and nested main landmarks. Done when semantic controls, focus-visible, one main landmark, skip link, standards-based dialogs, keyboard tests, and screen-reader smoke tests pass.

- [ ] **VCB-066 - Replace hard-coded Sophie, actor identity, and 12-of-18 progress.** Observed: LeftNav.tsx:30-35 and HomePage.tsx:35 show fake user/workload values that conflict with live zero data. Done when authenticated session/workspace data drives identity and workload, or demo values are visibly labeled and never enter audit events.

- [ ] **VCB-067 - Correct candidate list semantics and add cursor pagination.** Observed: list query omits canonical filter, uses unsafe concurrent queries on one AsyncSession, stage/origin can match a historical opportunity, and frontend caps at 200. Done when current opportunity is explicit, ordering/ties are stable, filters match displayed data, and indexed cursor pagination/server search work at target scale.

- [ ] **VCB-068 - Make mutations update all affected caches and lock conflicting actions.** Observed: decision action buttons remain usable during save and only detail refetches; Contact/discovery errors are often silent. Done when mutations have idempotency, all related queries invalidate/optimistically update, controls lock during requests, and failures preserve user intent.

- [ ] **VCB-069 - Preserve null score semantics throughout the UI.** Observed: missing Founder/Thesis/axis values render as 0, null%, or zero meters in profiles, decisions, and Investigated. Done when types use nullable values and every display renders Not scored/Unknown with separate confidence/coverage; zero remains a valid measured value.

- [ ] **VCB-070 - Separate evidence coverage from confidence.** Observed: candidateProfile.ts:18-20 averages observation confidence but UI labels it confidence-weighted coverage. Done when formulas, names, tooltips, API fields, and tests distinguish breadth/coverage, source quality, claim Trust, and model uncertainty.

- [ ] **VCB-071 - Normalize domain statuses at the API boundary.** Observed: backend stores supported lowercase while DecisionDetail checks Supported and renders it as warning; many states/axes/ratings are free strings. Done when typed enums and DB constraints drive API/UI styles and every allowed value has text/icon tests.

- [ ] **VCB-072 - Distinguish 404, 403, network, and server failures.** Observed: FounderProfile and DecisionDetail treat any fetch error as candidate not found; memo fetch errors become No memo. Done when typed API errors map to accurate recoverable states and prior data remains visible during transient failures.

- [ ] **VCB-073 - Upgrade search, filter, sort, and result-state UX.** Observed: inbound search only matches founder name/stable ID and KPI totals change with the filter; no-match says the DB is empty. Done when global/filtered counts, no-data/no-results states, clear action, relevant company/email/source/deck fields, filter chips, URL state, and server-side search are present.

- [ ] **VCB-074 - Centralize all investment thresholds and labels.** Observed: Investigated calls 70 percent strong while shared thesis aligned is 75 percent. Done when versioned thesis/rubric config owns thresholds and every view explains the same rule and confidence requirement.

- [ ] **VCB-075 - Render real nullable deadlines and SLA risk.** Observed: DecisionDetail says Decision due in Not scheduled. Done when no deadline renders plainly, real countdown/overdue/pause state comes from persisted SLA fields, and the queue sorts/alerts by risk.

- [ ] **VCB-076 - Show identity verification only when verified.** Observed: FounderProfile always shows a green check next to the founder name. Done when marker, label, method, source, and time come from explicit identity-verification state; otherwise it is omitted.

- [ ] **VCB-077 - Fix misleading workflow navigation.** Observed: Decision feedback/Memory navigates to thesis; Home View all uses every candidate but routes to Investigated only. Done when nodes route to the exact workspace/result set, or are visibly disabled with an explanation until implemented.

- [ ] **VCB-078 - Make the public submission form trustworthy and accessible.** Observed: public copy says next cohort, form lacks persistent labels/privacy/support, silent failure relies on alert, and Submit Another retains the previous file. Done when brand/purpose/privacy/retention/support are clear, controls are labeled, inline errors are announced, progress/retry is durable, and a new submission resets all fields.

- [ ] **VCB-079 - Sanitize every external link through one utility.** Observed: several components anchor raw backend URLs despite candidateLinks.ts having a safe URL helper. Done when only validated HTTP(S) URLs render, malformed/unsafe schemes are non-clickable, and every external link has tests and clear new-tab behavior.

- [ ] **VCB-080 - Add route-level error boundaries and a real 404.** Observed: malformed dates can throw; catch-all renders Coming soon for Not Found. Done when root/route boundaries preserve navigation and report redacted diagnostics, date parsing is defensive, and 404 offers useful recovery.

- [ ] **VCB-081 - Meet contrast, text-size, touch, and mobile information-density standards.** Observed: several muted colors are below AA at 9-12px; mobile lifecycle consumes roughly 2,300px before candidate content; metric detail truncates with mouse-only title. Done when WCAG AA, touch targets, wrapping/accessible tooltips, reduced-motion, and compact mobile priorities pass automated and manual QA.

- [ ] **VCB-082 - Unify product and public-facing branding.** Observed: repository says The VC Brain, investor shell says FirstCheck24, public form says Fund Application/next cohort, and favicon returns 404. Done when one approved brand vocabulary, page metadata, favicon, fund identity, privacy/contact copy, and demo labeling are consistent.

- [ ] **VCB-083 - Split oversized React modules by feature responsibility.** Observed: DecisionDetailPage is 594 lines, Onboarding 330, FounderProfile 299, CandidateCard 266, above the 150-line review limit. Done when page containers, query/mutation hooks, domain sections, and pure display components are cohesive, feature-local, and behavior-tested.

- [ ] **VCB-084 - Centralize score, trend, metric, and status display logic.** Observed: similar formatting/fallback/threshold logic is duplicated across cards, profiles, decisions, visuals, and portfolioMetrics. Done when one typed view model owns scale, null semantics, status visuals, confidence, trend compatibility, and accessible explanations.

- [ ] **VCB-085 - Remove dead code, unused dependencies, and generated config drift.** Observed: unused UI/components and several declared packages; tracked vite.config.js/d.ts diverge from vite.config.ts. Done when unused exports/dependencies are removed or intentionally adopted, only canonical config is tracked, and CI detects drift.

- [ ] **VCB-086 - Lazy-load routes and set a bundle budget.** Observed: App.tsx eagerly imports every route into a 350.5 kB bundle. Done when public form, admin shell, profiles, and decision pages are route chunks with accessible fallbacks and CI enforces a justified size budget.

- [ ] **VCB-087 - Add real integration, E2E, accessibility, and abuse coverage.** Observed: unit tests pass but heavily mock DB/worker paths; major pages have little/no rendered coverage. Done when clean PostgreSQL/Redis/MinIO tests cover migrations, session cleanup, reconciliation, merge rollback, outbox, concurrency, citations, and browser flows for discover-to-decision plus pitch-to-decision.

- [ ] **VCB-088 - Restore and enforce a green CI quality gate.** Observed: no CI workflow; backend Ruff fails in migration e093... lines 23/27; mypy fails inbound.py:19,24,77. Done when make check, migration smoke, frontend production build, security scans, and deterministic E2E pass from a clean clone and are required for merge.

- [ ] **VCB-089 - Make clean quick start migrate and optionally seed automatically.** Observed: README says make up on a fresh DB but Compose API does not apply migrations. Done when a clean-volume start reaches the migration head before readiness, failure blocks API, and a separate one-command deterministic demo seeds known data.

- [ ] **VCB-090 - Make configuration names and Compose wiring coherent.** Observed: .env.example mixes APP_ and unprefixed names; Compose passes only a subset, retains removed MOCK_REPLY_DELAY, and many new knobs never reach services. Done when one convention works identically in local/Docker/tests, enabled features validate required settings, unused knobs are removed, and ranges are startup-validated.

- [ ] **VCB-091 - Add production-grade health, telemetry, and PII-safe logs.** Observed: readiness checks only PostgreSQL; collection health means registered; logs include founder email; no end-to-end correlation. Done when migration/DB/Redis/MinIO/worker heartbeat are checked appropriately and request-job-source-model IDs, queue latency, cost, SLA, connector health, and redacted errors feed dashboards/alerts.

- [ ] **VCB-092 - Close shared clients cleanly.** Observed: storage.close_client exists but neither API nor worker lifecycle calls it; inbound creates Redis pools per request. Done when DB, Redis, HTTP, AI, and object-storage clients have bounded initialization/shutdown and leak tests cover repeated startup.

- [ ] **VCB-093 - Harden production images and network defaults.** Observed: backend image runs as root and copies broadly; Compose publishes DB/Redis/MinIO with development credentials and uses minio:latest. Done when non-root minimal pinned images, internal-only data ports, secrets/TLS/auth, read-only FS/capability drops, resource limits, and separate dev/prod profiles exist.

- [ ] **VCB-094 - Add backup, restore, migration, rollback, and incident runbooks.** Missing: production RPO/RTO and tested recovery. Done when PostgreSQL/object-storage backups, scheduled restore drills, forward-fix/rollback policy, rolling worker compatibility, and incident ownership are documented and exercised.

- [ ] **VCB-095 - Rewrite stale README and architecture status.** Observed: README still says Boilerplate phase and once a router is added despite implemented routes/features. Done when docs distinguish implemented/partial/proposed behavior, list honest limitations/provider costs, and provide one clean start, one demo start, reset, troubleshooting, and workflow map.

- [ ] **VCB-096 - Ship a deterministic, visibly labeled demo walkthrough.** Observed: a large seed exists but root onboarding does not expose a one-command demo. Done when no paid APIs are required to walk sourcing, contradiction, axes, evidence, memo, and decision; expected counts/routes are smoke-tested; screenshots/script stay current.

- [ ] **VCB-097 - Add connector contract tests and readiness levels.** Observed: ten registered connectors vary widely in pagination, provenance, retry, and completeness. Done when shared fixtures test cursoring, dedup, coordinates, licensing, rate limits, retries, partial failure, and connectors are marked experimental/beta/production with last-success health.

- [ ] **VCB-098 - Finish evidence-aware source depth.** Observed: arXiv PDF extraction contains pass; podcasts/YouTube lack transcript-level citations; generic/Tavily wrappers mostly capture snippets/metadata. Done when licensed primary content, page/timestamp coordinates, speaker/author identity confidence, incremental cursors, and source-specific tests exist before scoring.

- [ ] **VCB-099 - Store valid deterministic JSON for JSON snapshots.** Observed: GitHub, arXiv, Product Hunt, HN, and YouTube use Python str(dict/list) while declaring application/json. Done when canonical json serialization round-trips, hashes deterministically, and MIME matches bytes.

- [ ] **VCB-100 - Replace or govern committed public-profile demo data.** Observed: seed README describes 112 public people and includes pending-consent profile content/avatar bytes; importer labels non-submitted demos as inbound and mutates evidence. Done when fixtures are synthetic/anonymized or have a source-by-source license/legal manifest, unnecessary PII/avatar data is removed, and demo/reference data is excluded from operational metrics.

- [ ] **VCB-101 - Add automated dependency, image, secret, and license scanning.** Missing: CI security gates. Done when Python/npm dependencies, container images, repository secrets, and licenses are scanned; critical findings block release; exceptions are time-bounded and documented.

## P3 - Differentiated learning and workflow features

- [ ] **VCB-102 - Define outcome labels without equating VC selection with founder merit.** Done when sourcing, process, decision, and longitudinal outcomes have separate definitions, provenance, horizon, censoring, and confidence, and historical VC decisions are never treated as universal success truth.

- [ ] **VCB-103 - Calibrate scores and uncertainty empirically.** Done when each rubric/version has held-out, time/entity-separated evaluation, reliability diagrams/Brier metrics, missing-evidence analysis, uncertainty intervals, subgroup coverage/error reporting, and historical scores remain immutable.

- [ ] **VCB-104 - Measure marginal source value.** Done when evidence yield, unique claim contribution, verification/correction rate, freshness, latency, cost, and decision impact are measured per source with uncertainty and exploration holdouts.

- [ ] **VCB-105 - Add safe ranking experiments and exploration quotas.** Done when new rankers run offline replay then shadow mode, preserve source/cohort diversity, protect cold-start discovery, have rollback/guardrails, and every result remains explainable by thesis clauses and evidence.

- [ ] **VCB-106 - Build a channel-learning dashboard.** Done when query/source/cohort funnels show conversion, cost, latency, evidence quality, correction rate, confidence intervals, and minimum-sample warnings while feedback and outcomes remain distinct.

- [ ] **VCB-107 - Add saved sourcing plans and change alerts.** Done when investors can save/version a query plan, schedule lawful refreshes, receive deduplicated meaningful-change alerts, see why a candidate entered/left results, and control cost/frequency.

- [ ] **VCB-108 - Add IC collaboration and decision packet export.** Done when versioned memos support comments, mentions, assignments, resolved threads, compare, and PDF/Markdown export that locks the exact evidence/thesis/rubric snapshot and respects source permissions.

- [ ] **VCB-109 - Add founder-facing status and correction experiences.** Done when founders can securely verify/claim a profile, see submission status, answer decision-critical gaps, propose evidence-backed corrections, opt out, and receive a decision/update without exposing internal confidential analysis.

- [ ] **VCB-110 - Expand the graph into evidence-backed sourcing intelligence.** Done when person, organization, project, event, channel, and investor nodes have valid-time, typed evidence-linked edges; weak inferences are visually distinct; graph insights improve channel exploration but never founder merit directly.

## Verification baseline from this audit

- Frontend ESLint: passed.
- Frontend TypeScript: passed.
- Frontend Vitest: 25 tests passed.
- Frontend production build: passed; 350.50 kB JavaScript, 104.86 kB gzip.
- Backend pytest: 116 tests passed with one Starlette/httpx deprecation warning.
- Backend Ruff: failed on two E501 violations in migrations/versions/e093be299381_add_discovery_config_to_thesis.py:23 and :27.
- Backend mypy: failed on three errors in app/api/routes/inbound.py:19, :24, and :77.
- Alembic: one head, revision 008.
- git diff --check: passed.
- Docker Compose/runtime migration check: not run because Docker Desktop was not running.
- Live browser QA: reproduced false-zero outage state, silent failed submission, and missing mobile navigation. Temporary evidence was kept outside the repository.

## First practical milestone

Do not start by adding more connectors. A strong first milestone is:

1. VCB-001, VCB-002, VCB-004, VCB-005, VCB-008, VCB-018.
2. VCB-009 through VCB-015.
3. VCB-024 through VCB-027 and VCB-051 through VCB-055.
4. One deterministic E2E test proving: approved outbound lead -> traceable submission -> triage -> persistent Founder Score -> three independent opportunity axes -> claim-backed memo -> authenticated human decision inside the SLA.

That slice would convert the current hackathon demonstration into an honest, testable product foundation.
