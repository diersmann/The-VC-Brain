# VC Brain: Architecture and Scoring

## Objective

The VC Brain discovers promising founders, maintains evidence-backed profiles, and supports sourcing, screening, diligence, and investment decisions. Profiles and scores must remain time-aware, explainable, and traceable to their original evidence. Sourcing depth is the MVP priority; the other layers remain deliberately thin where necessary to prove that strong founders can be found before they begin fundraising.

## Implementation status

This document is the target architecture and contract, not a claim that every surface is shipped. The current repository has a working local Docker stack, provenance-aware source collection, inbound PDF submission, deterministic scoring foundations, a persisted inbound decision clock, and tested sourcing/inbound/decision UI states. Authentication and tenant scoping, the complete triage-to-decision lifecycle, authenticated SLA ownership/alerting/metrics, production observability, and several connector depth requirements remain partial or proposed. The durable implementation status is tracked in [`IMPROVEMENT_BACKLOG.md`](../IMPROVEMENT_BACKLOG.md).

## Evaluation Criteria Coverage

| Criterion | Weight | Primary architecture coverage |
|---|---:|---|
| Data Architecture and Intelligence | 30% | Memory and Data Contracts, Source Quality, Identity and Knowledge, Cold-Start Method |
| Intelligent Analysis and Trust | 25% | Independent Assessments, Claim-Level Trust, Multi-Agent Scoring, Memo Contracts |
| Investment Utility and Execution | 30% | Unified Deal Lifecycle, 24-Hour SLA, Activation, Decision Contract, Observability |
| User Experience and Design | 15% | Investor Experience, evidence drill-down, progressive disclosure, accessibility |

## Logical Systems

```text
Sources and applications
          |
          v
Data Collector -> Processing Pipeline -> Identity and Knowledge Engine
                                             |
                                +------------+------------+
                                |                         |
                                v                         v
                         Profile Features          Relationship Graph
                                +------------+------------+
                                             |
                                             v
                                  Intelligence and Scoring
                                             |
                                             v
                                      Backend API
                                             |
                                             v
                                          Frontend
```

The systems are logical boundaries, not initial deployment boundaries. The MVP keeps them in a modular monolith plus background workers so that provenance, scoring, and workflow rules can evolve without premature distributed-system complexity.

## Memory and Data Contracts

Memory is append-only at the evidence layer. Corrections supersede prior observations rather than deleting history, allowing profiles and decisions to be reproduced as they appeared at a given time.

Core entities are:

| Entity | Purpose | Required fields |
|---|---|---|
| Person | Persistent identity across opportunities | Stable ID, names, handles, consent/privacy state, cached public avatar bytes and source provenance |
| Organization | Company, institution, accelerator, or fund | Stable ID, names, type, locations |
| Opportunity | A company and idea evaluated at a point in time | Company, founders, source kind, lifecycle state, thesis version |
| SourceSnapshot | Immutable copy or reference to collected material | URI, source type, content hash, collected time, license/access metadata |
| Observation | Extracted source statement before reconciliation | Subject, opportunity when known, predicate, object/value, source locator, observed time, extractor version, snapshot |
| Claim | Reconciled assertion used by scoring and memos | Subject, opportunity when known, observation references, status, confidence, valid time, supersession link |
| Relationship | Typed graph edge | Endpoints, relationship type, evidence, confidence, observed/valid time |
| ScoreSnapshot | Reproducible score at a point in time | Person-scoped Founder Score/sourcing/thesis or opportunity-scoped axis snapshot, rubric/model version, components, confidence interval, evidence IDs |
| Assessment | Per-opportunity Founder, Market, or Idea-vs-Market result | Exactly three canonical axes, rating, trend, confidence, evidence and counter-evidence |
| DecisionEvent | Auditable lifecycle transition | Opportunity, prior/new state, authenticated actor, idempotency key, reason, timestamp, evidence/thesis snapshot metadata |
| InboundSubmission | Idempotent application envelope | Idempotency key, person/opportunity/deck references, accepted status, timestamps |
| OutboxEvent | Durable handoff from PostgreSQL to workers | Dedupe key, event payload, dispatch status, retry count, availability, error metadata |
| OutreachMessage | Human-reviewed contact and provider state | Draft, approval, send request, provider ID, delivery state, suppression/failure metadata |

Every observation, claim, relationship, score, and recommendation retains provenance, observation time, confidence, and the version of the extractor, rubric, prompt, or model that produced it. Evidence corrections append a new observation rather than mutating the prior statement. Personally identifying data is stored only when necessary and is subject to correction, retention, and deletion controls; audit records retain non-sensitive tombstones where legally permissible.

### Source Quality and Collection Policy

Collection is prioritized by expected decision value rather than volume:

1. Founder-submitted decks, interviews, and structured application answers
2. First-party artifacts such as repositories, product sites, papers, patents, and launch pages
3. Independent verification such as customer references, usage evidence, and reputable databases
4. Community and social signals used primarily for discovery
5. Inferred relationships and low-authority aggregations, clearly marked as weak evidence

Each connector defines source authority, expected freshness, refresh cadence, legal basis, rate limits, and failure policy. The scheduler uses expected information gain, source staleness, opportunity deadline, and collection cost to decide what to fetch next. Low-value duplication is skipped; missing or inaccessible evidence becomes an explicit unknown.

### 1. Frontend

The investor-facing application provides:

- Founder discovery and natural-language search
- Founder profiles, evidence timelines, and relationship graphs
- Founder Score components, trends, and confidence
- Founder, Market, and Idea-vs-Market opportunity assessments
- Contradiction, missing-data, and evidence views
- Thesis configuration and investment memo workflows
- A unified opportunity inbox showing stage, deadline, owner, and SLA risk
- Human approval controls for outreach and investment decisions

### 2. Backend API

The backend coordinates the application:

- Authentication and authorization
- Founder, company, evidence, and search APIs
- Inbound applications and deck uploads, committed with an idempotent submission envelope and durable outbox before worker dispatch
- Sourcing-to-decision workflow state
- Collection, correlation, and analysis jobs
- Profile, score, graph, and memo delivery
- Versioned thesis, rubric, memo, and decision contracts
- Opportunity-scoped jobs carry and validate the exact opportunity ID; person-only fallback selection is not permitted for research, memo, or decisions.
- Append-only lifecycle events and investor feedback capture

For an MVP, this should be a modular monolith rather than a set of microservices.

### 3. Data Collector

The collector handles APIs, crawlers, imports, and uploads for sources such as GitHub, Product Hunt, Hacker News, arXiv, hackathons, company websites, and pitch decks.

It should:

- Preserve immutable snapshots of original material
- Record provenance and collection timestamps
- Detect source changes
- Respect licenses, terms, privacy, and rate limits
- Queue collected material for processing
- Assign authority, freshness, and licensing metadata
- Prioritize deadline-critical and high-information sources

### 4. Processing Pipeline

The pipeline converts raw material into normalized observations:

- Parse PDFs, websites, repositories, and structured APIs
- Extract people, companies, projects, skills, milestones, and claims
- Generate embeddings for semantic retrieval
- Normalize dates, names, locations, and identifiers
- Attach every extracted claim to its source evidence
- Preserve source coordinates such as deck page, transcript span, or webpage fragment
- Record extractor/model version and distinguish observations from reconciled claims

### 5. Identity and Knowledge Engine

This is the data correlation layer. It:

- Resolves whether records represent the same person or organization
- Deduplicates founders, companies, and projects
- Detects contradictory claims
- Builds persistent, time-aware founder profiles
- Creates typed relationships with evidence and confidence
- Maintains supersession links and valid-time history instead of overwriting claims

The graph must distinguish confirmed collaboration from weak signals such as attending the same institution. Relationship types include `founded_with`, `worked_with`, `coauthored_with`, `participated_in`, `invested_in`, and `possibly_knows`; only the first five may become confirmed, and all require evidence. Network prestige supports sourcing, team analysis, and outreach, but never directly inflates founder merit.

## Unified Deal Lifecycle

Inbound applications and outbound discoveries converge into one opportunity pipeline:

```text
Inbound: deck + company --------------------+
                                             v
                                       [Received]
                                             |
Outbound: signal -> threshold -> outreach -> application
                                             |
                                             v
 [Received] -> [Triage] -> [Screening] -> [Diligence] -> [Memo Ready]
                    |             |              |              |
                    +----------> [Closed] <------+              v
                                                          [Decision]
```

The canonical lifecycle is versioned as `unified-v2` in `backend/app/lifecycle.py`,
served at `GET /api/v1/lifecycle`, and consumed by the workflow diagram. Each
stage declares entry and exit requirements, allowed actors, transitions, and
timestamp provenance. Opportunity creation establishes the initial state;
subsequent transitions are timestamped by `DecisionEvent`.

An outbound signal does not trigger an investment. It creates a candidate, and crossing a configurable conviction threshold creates an activation task. Approved outreach asks the founder to submit or confirm the minimum application: company name and deck. The resulting application enters the same `Received` state as inbound applications and is evaluated by the same rules.

Outreach is stateful: drafting and human approval are distinct from a send request, and `contacted` is only recorded after a mail provider confirms submission. Delivery, bounce, reply, opt-out, and failure signals remain separate states.

Every transition emits a `DecisionEvent`, writes the latest evidence and assessment snapshots back to Memory, and records who or what initiated the transition. A closed opportunity retains its reason, evidence, and reopen conditions.

### First-Pass Triage

Triage is a fast, inexpensive stage before full agent analysis. Deterministic rules check minimum input validity, hard thesis exclusions, duplicate opportunities, obvious legal conflicts, and whether enough evidence exists to continue. It may request missing information or close clearly non-viable opportunities, but it cannot reject a founder merely for lacking public history, funding, credentials, or network connections.

### Outbound Activation

The Intelligence system continuously evaluates new observations against the active thesis. A threshold combines thesis fit, novelty, momentum, evidence confidence, and contactability. Candidates above the threshold enter a human-approved outreach queue with:

- The exact signals that triggered activation
- Confidence and likely identity-match quality
- A personalized but reviewable outreach draft
- Contact provenance, consent status, and suppression state
- Conversion tracking from signal to application

### 24-Hour Decision SLA

The decision clock starts when a valid inbound application is received or an activated founder submits the minimum application. Outbound discovery-to-contact time is measured separately and does not silently consume the applicant's decision window.

Target stage budgets are:

| Stage | Target elapsed time | Output |
|---|---:|---|
| Triage | 30 minutes | Advance, request information, or close with reason |
| Screening | 3 hours | Three preliminary axes and diligence plan |
| Diligence | 14 hours | Verified claims, contradictions, and resolved truth gaps |
| Memo | 4 hours | Evidence-backed memo and decision proposal |
| Human decision buffer | 2.5 hours | Approve, decline, or escalate |

Workers use deadline-aware priority queues. Slow or unavailable sources degrade confidence and become explicit gaps instead of blocking indefinitely. Opportunities approaching a deadline trigger alerts and progressively narrow diligence to decision-critical unknowns.

Required telemetry includes:

- Timestamps for every lifecycle transition and asynchronous job
- Stage duration, total cycle time, queue latency, retries, and failure reasons
- Percentage decided within 24 hours and percentile decision times
- Evidence freshness and coverage at decision time
- Human escalation and override rates
- Outbound signal-to-contact and contact-to-application conversion

The dashboard exposes current SLA risk and historical reliability. The system never marks an SLA as met without a persisted decision event.

### 6. Intelligence and Scoring System

This system contains:

- A persistent, person-level Founder Score
- Independent Founder, Market, and Idea-vs-Market opportunity assessments
- A configurable investor Thesis Engine
- Per-claim Trust Scores
- Evidence-backed memo generation and diligence suggestions

The Founder Score, opportunity assessments, and Trust Scores are separate concepts and should not be collapsed into one opaque number.

### Thesis Engine

Each immutable thesis version defines:

- Sectors and excluded sectors
- Company stage
- Geography
- Check-size range
- Ownership target
- Risk appetite

The engine applies hard eligibility constraints separately from soft preferences. It produces a thesis-alignment explanation with matched criteria, failed criteria, evidence, and unknowns. Re-evaluating an opportunity under a new thesis creates a new assessment without rewriting the historical decision context.

The implemented MVP persists immutable versions in `investment_theses` and exposes the active version through `/api/v1/theses/active`. Saving a new active thesis appends a `thesis-match-v1:<thesis-version>` `ScoreSnapshot` for every canonical candidate and updates the latest linked opportunity's thesis version. Stage and explicitly excluded sectors are hard constraints; sector, geography, and requested check size are weighted preferences. Missing criteria contribute a neutral value and reduce evidence confidence instead of lowering founder quality. Each snapshot stores matched, failed, and unknown criteria plus the observation IDs used by the deterministic rubric.

### Multi-Attribute Reasoning

Natural-language requests are compiled into a visible query plan containing structured filters, semantic concepts, graph constraints, and exclusions. For example, "technical founder, Berlin, AI infrastructure, enterprise traction, no prior VC backing" becomes exact filters where reliable structured data exists and embedding retrieval where meaning is fuzzy. Results show how each clause was interpreted, which evidence matched it, and which clauses remain uncertain. Investors can correct the interpretation before acting on it.

### Persistent Founder Score

The Founder Score belongs to a person, persists across companies and applications, and is one input to the Founder opportunity axis. It is stored as a versioned scorecard rather than only a scalar:

- Execution evidence
- Technical or product capability
- Learning velocity
- Founder-market fit history
- Team-building evidence
- Commercial evidence
- Momentum
- Evidence coverage and confidence interval

New milestones append a `ScoreSnapshot`; they never erase earlier values. Network centrality, school prestige, investor proximity, protected characteristics, and absence of public data are excluded from merit components.

### Independent Opportunity Assessments

Founder, Market, and Idea-vs-Market are evaluated independently and are not averaged. Each assessment returns:

```json
{
  "axis": "market",
  "rating": "bullish",
  "trend": "improving",
  "confidence": 0.71,
  "evidence": ["claim_123"],
  "counterEvidence": ["claim_456"],
  "unknowns": ["Reliable bottom-up market size"]
}
```

Ratings are `bullish`, `neutral`, or `bear`; trends are `improving`, `stable`, or `declining`. Trend compares time-versioned inputs and prior assessments using the same rubric version. When the rubric changes, the system either recomputes comparable history or labels the trend incomparable. Every assessment and investor correction feeds back into Memory.

### Claim-Level Trust Score

A Trust Score belongs to an individual claim, never to an entire founder or company. Version `claim-trust-v1` combines source authority, directness, independent corroboration, identity-match confidence, freshness, extraction certainty, and unresolved contradiction penalties. The current implementation keeps identity confidence explicit as unknown (`0.5`) until a verified identity signal is available; it does not silently turn that gap into certainty. The score includes a calibrated confidence interval, an explanation, and a status such as `unverified`, `supported`, `contradicted`, or `superseded`. `Claim.supersession_id` always points from an older claim to the newer claim that supersedes it; the older row's `valid_time_end` closes when that replacement is recorded. Reconciliation is idempotent for an unchanged observation set.

Contradictory observations are retained and linked. The validator cannot silently choose the more favorable statement: it must either resolve the contradiction using stronger evidence or expose both versions as an open diligence item. Trust calibration is tested with seeded contradictions and held-out verified claims.

### Cold-Start and Fairness Method

Founders with no funding, GitHub history, credentials, or network receive an assessment path designed around demonstrated work rather than historical access. Admissible evidence includes:

- Submitted prototypes, demos, designs, writing, or technical artifacts
- Structured interviews and scenario-based work samples
- Hackathon, research, community, or employment outputs with direct evidence
- Learning velocity between application milestones
- Customer discovery quality and clarity of problem understanding
- References describing concrete observed behavior

Cold-start components use wider confidence intervals and clearly display missing evidence. The system may request a short, role-relevant work sample, but missing public history cannot become a negative feature. The same rubric is applied to comparable evidence regardless of school, geography, prior funding, or network. Fairness checks compare evidence coverage, advancement, confidence, and overrides across relevant cohorts where lawful and statistically meaningful.

## Multi-Agent Scoring Method

A multi-agent committee can assess different dimensions, but agents should first evaluate the same evidence independently. Unstructured discussion risks anchoring, groupthink, and conclusions that cannot be audited.

```text
Founder profile and evidence
          |
          +-- Execution Agent
          +-- Technical Agent
          +-- Commercial Agent
          +-- Founder-Market-Fit Agent
          +-- Cold-Start and Fairness Agent
          |
          v
    Critic / Validator
          |
          v
 Targeted Adjudication
          |
          v
Deterministic Aggregator
          |
          v
Scorecard, confidence, and evidence
```

Each specialist returns structured output containing:

- Dimension and sub-score
- Supporting evidence references
- Counter-evidence
- Missing information
- Confidence
- Recommended diligence questions

The validator checks unsupported claims, source quality, contradictions, and identity errors. Adjudication is triggered only for meaningful disagreement or threshold decisions. A deterministic, versioned service combines accepted sub-scores; an LLM should not invent the final numerical score.

Agents receive the same immutable evidence package and assess it independently before seeing other outputs. Every run records the evidence IDs, prompt and model versions, structured output, validation result, latency, and cost. Targeted adjudication produces a concise disagreement record; it does not expose or depend on private chain-of-thought.

For the Agentic Traceability stretch goal, the system deliberately substitutes step-level evidence IDs, source coordinates, structured decisions, and validator results for raw chain-of-thought logging. This provides reproducible auditability without exposing private reasoning or treating unverifiable model narration as evidence.

Example output:

```json
{
  "dimension": "execution",
  "score": 78,
  "confidence": 0.72,
  "evidence": ["claim_123", "claim_456"],
  "counterEvidence": ["claim_789"],
  "unknowns": ["No customer retention data"],
  "recommendation": "Verify whether Project X had active users"
}
```

Store concise rationales and evidence rather than private chain-of-thought. Missing information should reduce confidence, not automatically reduce founder quality.

For an MVP, use three specialist agents, one critic, and one deterministic aggregator.

## Investment Memo and Decision Contracts

The memo is generated from accepted claims and assessment snapshots, not directly from raw model prose. For the current contract, accepted claims are supported or explicitly synthesized claims that are not superseded; every referenced observation must resolve to the same person and opportunity. Each memo persists the exact claim IDs, assessment IDs, evidence IDs, and pinned thesis version used for generation, so later collection or thesis changes cannot silently change its input package. The server rejects unknown claim/evidence IDs, requires claim support for factual sentences, permits uncited sentences only when they explicitly state an unavailable/unknown condition, and stores citations in deterministic order. Every factual sentence links to one or more claim IDs and exposes its Trust Score. Contradictions and unavailable information appear inline rather than being silently omitted or guessed.

Required memo sections are:

1. Company snapshot
2. Investment hypotheses
3. SWOT
4. Problem and product
5. Traction and KPIs

Optional sections include team and history, technology and defensibility, market sizing, competition, financials and round structure, cap table, due diligence log, and exit perspective. Missing optional information is explicit, for example, `Cap table: not disclosed`. Memo versions preserve the evidence and thesis versions used to produce them.

Memo runs are persisted with `pending`, `failed`, `degraded`, or `succeeded` status. Only a validated `succeeded` memo may advance an opportunity to `memo_ready`; degraded or fallback drafts remain visibly non-decision-ready.

The decision proposal is a separate structured artifact:

```json
{
  "action": "invest",
  "checkAmount": 100000,
  "ownershipTarget": null,
  "conviction": "medium",
  "founderAssessmentId": "assessment_1",
  "marketAssessmentId": "assessment_2",
  "ideaMarketAssessmentId": "assessment_3",
  "topEvidence": ["claim_123", "claim_456"],
  "topRisks": ["Single design partner", "Market-size estimate unverified"],
  "openConditions": ["Confirm incorporation details"]
}
```

The persisted `DecisionProposal` artifact also stores the proposal status,
readiness status and blockers, exact assessment foreign keys, memo/model and
thesis versions, and any human override reason. Check amount, ownership target,
and conviction remain explicitly nullable until an investor supplies them; the
system must not infer capital intent from scores. Proposal risks and open
conditions are copied only from persisted assessment unknowns or missing
artifact requirements. A proposal is created with the memo run and updated in
the same transaction as a human decision override.

A human investor must approve, decline, or escalate the proposal. The system records overrides and reasons but does not autonomously deploy capital or contact founders without configured approval.

## Investor Experience

The design bar is Notion-level approachability at the top layer and Bloomberg-level analytical depth in drill-downs. The UX follows progressive disclosure: a non-technical investor first sees the recommendation, three independent axes, deadline, confidence, and material risks; deeper views reveal component scores, trend history, claims, source excerpts, contradictions, and model metadata.

Primary views are:

1. **Sourcing feed:** verified public identities ranked by the three independent Founder, Market, and Idea-Market axes; compact cards also expose company, location, evidence-backed summary, source coverage, observation count, and profile completeness. Handle-only leads remain outside the ranked feed until identity evidence is sufficient.
2. **Opportunity inbox:** unified inbound/outbound funnel, stage, owner, SLA risk, and next action
3. **Founder profile:** persistent scorecard, timeline, projects, evidence coverage, and corrections
4. **Relationship graph:** typed, time-aware, evidence-backed edges with weak inferences visually separated
5. **Diligence workspace:** truth gaps, contradictions, requests, agent disagreements, and completed checks
6. **Memo and decision:** concise memo, three-axis assessment, evidence drill-down, and human approval
7. **Thesis and quality dashboard:** thesis versions, sourcing-channel performance, SLA metrics, calibration, and overrides

Accessibility, keyboard navigation, readable uncertainty displays, and plain-language explanations are required. The interface never uses color alone for ratings or confidence. Investor corrections are captured as structured feedback and remain distinguishable from externally verified facts.

## Complementary Scoring Approaches

### Rubric-Based Weighted Scoring

AI extracts evidence into explicit dimensions, while deterministic rules calculate the score. This is transparent and suitable when training data is limited.

### Bayesian Scoring

Update score distributions as evidence arrives. Bayesian methods naturally represent source strength, uncertainty, contradictions, and changes over time.

### Learning to Rank

Rank candidates for a particular investment thesis instead of predicting universal founder success. Pairwise investor preferences and observed outcomes can train models such as LambdaMART or XGBoost ranking.

### Gradient-Boosted Trees

Models such as XGBoost, LightGBM, or CatBoost can combine structured profile and traction features. They become useful once reliable historical labels exist and can be interpreted using SHAP values.

### Embedding Similarity

Compare founder, company, and investor-thesis embeddings for semantic discovery and matching. Similarity represents thesis alignment, not founder merit.

### Trajectory and Momentum Models

Measure direction and rate of change, including release cadence, repository adoption, product launches, and traction growth. Momentum can reveal promising founders before fundraising begins.

### Graph-Based Scoring

Graph algorithms can identify repeated collaboration, complementary teams, productive communities, and effective sourcing channels. They should not reward proximity to prestigious institutions or investors.

### Anomaly and Novelty Detection

Clustering, Isolation Forest, and embedding outlier detection can surface overlooked candidates with unusual combinations of ability, activity, and low visibility.

### Outcome and Survival Models

Once longitudinal data exists, estimate time to observable milestones such as shipping a product, reaching traction, or remaining active. These models handle incomplete and time-dependent outcomes better than a single success label.

## Recommended Hybrid

The MVP should combine:

1. Rubric-based deterministic scoring for explainability
2. Bayesian confidence updates for uncertainty
3. Embedding similarity for thesis matching
4. Momentum analysis for early sourcing
5. Multi-agent review for qualitative judgment and validation

Expose a scorecard rather than only a single number:

- Founder capability
- Execution momentum
- Thesis alignment
- Opportunity assessments
- Novelty or discovery signal
- Evidence confidence

Before training predictive models, define measurable outcomes. A vague label such as "successful founder" will encode historical VC selection and network bias rather than founder potential.

## Feedback, Learning, and Evaluation

### Sourcing-Channel Intelligence

Programs, institutions, communities, events, referrals, and web sources are represented as sourcing-channel nodes. Each opportunity preserves first-touch and contributing channels. The system measures application conversion, thesis fit, diligence advancement, investment, subsequent milestones, evidence quality, cost, and time-to-decision by channel.

Funded and declined outcomes update channel estimates without becoming direct founder-merit features. A Bayesian exploration policy can suggest underexplored channels with promising quality signals while reserving capacity for discovery outside historically successful networks. Reports show quality and uncertainty, not only lead volume.

### Outcome Feedback

The system records investor decisions, overrides, founder corrections, application conversion, and later observable milestones. Labels remain outcome-specific, such as `shipped_product_within_6_months`, rather than collapsing into "successful founder." Historical decisions are not treated as ground truth; they are analyzed for selection bias and missing counterfactuals.

Two research questions remain explicit evaluation tracks rather than assumed capabilities. First, prediction intervals around inferred soft skills such as resilience and founder-market fit must be calibrated against observable behavior and should remain wide when evidence is indirect. Second, the predictive value of public footprints must be tested on held-out, time-separated outcome labels with subgroup analysis before any such signal becomes a merit feature; social visibility alone is never treated as founder quality.

Score or model updates require:

- A versioned dataset and documented label definition
- Train/validation splits that respect time and entity boundaries
- Baselines against deterministic rubric scoring
- Calibration, ranking quality, coverage, and subgroup error analysis
- Regression tests using synthetic profiles with seeded contradictions
- Shadow evaluation before a new version affects recommendations
- Rollback to the prior rubric/model version

### Data-Collection Value

Connector value is evaluated by information gain, claim verification rate, freshness, latency, monetary cost, legal risk, and downstream decision impact. Sources that add volume without resolving important unknowns are deprioritized. Collection policy changes are versioned and evaluated against SLA and evidence-quality metrics.

## Security, Privacy, and Governance

- Use licensed data, public APIs, or founder-provided information according to source terms.
- Encrypt sensitive data in transit and at rest; restrict raw documents and contact details by role.
- Maintain consent, outreach suppression, correction, export, retention, and deletion workflows.
- Treat uploaded documents and web content as untrusted input and isolate parsing from privileged services.
- Prevent prompts or retrieved content from changing system policy or authorizing external actions.
- Audit access, automated outreach drafts, score changes, memo generation, and decisions.
- Do not infer protected characteristics or use them as founder-merit features.

## Initial Deployment

Keep logical boundaries while minimizing operational complexity:

1. Web application for the frontend
2. Application server containing backend, identity, scoring, and intelligence modules
3. Worker service for collection and processing
4. PostgreSQL with `pgvector`, object storage, and a job queue

PostgreSQL can initially store graph edges. Introduce a dedicated graph database only if deep graph traversal becomes a central product capability.

The application emits structured logs and traces carrying opportunity, lifecycle stage, job, source, model, and request IDs. Local and production dashboards cover queue depth, connector health, parse failures, identity-resolution uncertainty, model latency/cost, Trust Score calibration, SLA attainment, and outreach conversion. Sensitive evidence is referenced by ID and never written directly to logs.

## MVP Demonstration Slice

The initial demonstration should prove the complete loop rather than maximum source breadth:

1. Collect a focused cohort from two or three complementary outbound sources and accept a deck-plus-company inbound application.
2. Resolve identities, retain source snapshots, and create evidence-backed claims with at least one seeded contradiction.
3. Activate one outbound candidate and route the resulting application into the same screening workflow as inbound.
4. Execute triage, three independent assessments with trends, cold-start handling, and targeted agent validation.
5. Produce the required memo sections, explicit unknowns, and a human-approved decision proposal within the instrumented 24-hour SLA.
6. Demonstrate natural-language thesis search, claim-level evidence drill-down, relationship provenance, and sourcing-channel feedback.
