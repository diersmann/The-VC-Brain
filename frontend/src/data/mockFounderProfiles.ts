export interface FounderEvent {
  date: string;
  title: string;
  body: string;
  type: string;
  trust: number;
}

export interface FounderClaim {
  claim: string;
  source: string;
  trust: number;
  status: string;
}

export interface FounderAssessment {
  title: "Founder" | "Market" | "Idea × Market";
  rating: "Bullish" | "Neutral" | "Bearish";
  trend: "Improving" | "Stable" | "Declining";
  confidence: number;
  body: string;
}

export interface FounderRelation {
  label: string;
  sub: string;
  kind: "company" | "person" | "institution" | "investor";
  verified: boolean;
}

export interface FounderProfile {
  stableId: string;
  initials: string;
  company: string;
  role: string;
  location: string;
  stage: string;
  sector: string;
  summary: string;
  signal: string;
  tags: string[];
  founderScore: number;
  momentum: number;
  thesisFit: number;
  evidence: number;
  scoreHint: string;
  assessments: FounderAssessment[];
  events: FounderEvent[];
  claims: FounderClaim[];
  coverage: { label: string; value: number }[];
  gaps: string[];
  relations: FounderRelation[];
  affiliations: { name: string; role: string; meta: string; kind: "company" | "work" | "education" }[];
}

const assessment = (
  founder: FounderAssessment,
  market: FounderAssessment,
  fit: FounderAssessment,
): FounderAssessment[] => [founder, market, fit];

export const mockFounderProfiles: Record<string, FounderProfile> = {
  "founder-001": {
    stableId: "founder-001", initials: "AC", company: "NeuraGrid", role: "Co-founder & CTO", location: "Berlin, Germany", stage: "Pre-seed", sector: "AI Infrastructure",
    summary: "Technical founder building an orchestration layer for private enterprise AI. Strong execution cadence and uncommon systems depth, with early validation from regulated-industry design partners.",
    signal: "Open-source inference engine grew 4.2× in eight weeks", tags: ["AI infrastructure", "Enterprise", "Technical"], founderScore: 82, momentum: 88, thesisFit: 91, evidence: 74, scoreHint: "Top 8% of cohort",
    assessments: assessment(
      {title:"Founder",rating:"Bullish",trend:"Improving",confidence:86,body:"Exceptional technical depth and high learning velocity."},
      {title:"Market",rating:"Neutral",trend:"Stable",confidence:63,body:"Large market, but bottom-up sizing remains unverified."},
      {title:"Idea × Market",rating:"Bullish",trend:"Improving",confidence:78,body:"Strong pain evidence in regulated enterprise teams."},
    ),
    events: [
      {date:"Jul 2026",title:"Enterprise pilot expanded",body:"Design partner expanded deployment from one to four internal teams.",type:"Traction",trust:92},
      {date:"Jun 2026",title:"NeuraGrid v0.8 released",body:"Added distributed inference and published reproducible benchmarks.",type:"Product",trust:88},
      {date:"Apr 2026",title:"Open-source project crossed 2,400 stars",body:"Organic developer adoption accelerated across eight weeks.",type:"Momentum",trust:84},
      {date:"Jan 2026",title:"Founded NeuraGrid",body:"Started company with former colleague Daniel Weber.",type:"Company",trust:96},
      {date:"2022–25",title:"Staff ML Engineer · Celonis",body:"Led inference infrastructure for production ML workloads.",type:"Career",trust:91},
    ],
    claims: [
      {claim:"Three enterprise design partners are active",source:"Data room + two customer confirmations",trust:91,status:"Supported"},
      {claim:"Inference costs reduced by 38%",source:"Published benchmark; independent run pending",trust:72,status:"Partially verified"},
      {claim:"€48k contracted ARR",source:"Founder-provided contract summary",trust:58,status:"Needs verification"},
    ],
    coverage:[{label:"Product & technical",value:92},{label:"Team & references",value:78},{label:"Commercial traction",value:61},{label:"Market evidence",value:46}],
    gaps:["Verify contracted ARR and renewal terms","Validate bottom-up market sizing","Request reference from former direct report"],
    relations:[{label:"NeuraGrid",sub:"Company",kind:"company",verified:true},{label:"Daniel",sub:"Co-founder",kind:"person",verified:true},{label:"Celonis",sub:"Employer",kind:"company",verified:true},{label:"TU Berlin",sub:"Education",kind:"institution",verified:true}],
    affiliations:[{name:"NeuraGrid",role:"Co-founder & CTO",meta:"2026 — Present",kind:"company"},{name:"Celonis",role:"Staff ML Engineer",meta:"2022 — 2025",kind:"work"},{name:"TU Berlin",role:"MSc Computer Science",meta:"2018 — 2020",kind:"education"}],
  },
  "founder-002": {
    stableId:"founder-002",initials:"MJ",company:"RelayOps",role:"Founder & CEO",location:"London, UK",stage:"Seed",sector:"Developer Tools",summary:"Repeat product operator automating incident response for enterprise platform teams. Commercial evidence is strong, while technical defensibility needs deeper diligence.",signal:"Three enterprise design partners converted into paid pilots",tags:["DevTools","B2B SaaS","Repeat founder"],founderScore:77,momentum:90,thesisFit:68,evidence:81,scoreHint:"Top 18% of cohort",
    assessments:assessment({title:"Founder",rating:"Bullish",trend:"Stable",confidence:82,body:"Strong commercial leadership and proven hiring ability."},{title:"Market",rating:"Bullish",trend:"Improving",confidence:75,body:"Clear budget owner and expanding reliability spend."},{title:"Idea × Market",rating:"Neutral",trend:"Improving",confidence:69,body:"Demand is validated; differentiation is not yet durable."}),
    events:[{date:"Jul 2026",title:"First annual contract signed",body:"European fintech converted from pilot to a £72k annual contract.",type:"Traction",trust:94},{date:"May 2026",title:"RelayOps private beta",body:"Six platform engineering teams joined the private beta.",type:"Product",trust:86},{date:"Feb 2026",title:"Core team formed",body:"Recruited former SRE lead and product designer.",type:"Team",trust:90},{date:"2020–24",title:"VP Product · Pagerly",body:"Scaled product organization from 8 to 42 people.",type:"Career",trust:88}],
    claims:[{claim:"£180k contracted ARR",source:"Signed customer summaries",trust:89,status:"Supported"},{claim:"Incident resolution improves by 43%",source:"Customer dashboard export",trust:76,status:"Supported"},{claim:"Proprietary remediation graph",source:"Founder interview only",trust:47,status:"Needs verification"}],
    coverage:[{label:"Commercial traction",value:91},{label:"Team & references",value:84},{label:"Product & technical",value:65},{label:"Competitive evidence",value:52}],gaps:["Review architecture defensibility","Validate gross retention assumptions","Interview technical co-founder candidate"],relations:[{label:"RelayOps",sub:"Company",kind:"company",verified:true},{label:"Pagerly",sub:"Former employer",kind:"company",verified:true},{label:"Northstar",sub:"Angel syndicate",kind:"investor",verified:false},{label:"Maya Cole",sub:"Design partner",kind:"person",verified:true}],affiliations:[{name:"RelayOps",role:"Founder & CEO",meta:"2025 — Present",kind:"company"},{name:"Pagerly",role:"VP Product",meta:"2020 — 2024",kind:"work"},{name:"University of Leeds",role:"BSc Economics",meta:"2012 — 2015",kind:"education"}],
  },
  "founder-003": {
    stableId:"founder-003",initials:"YT",company:"Kanso Robotics",role:"Founder & Chief Scientist",location:"Tokyo, Japan",stage:"Pre-seed",sector:"Robotics",summary:"Robotics researcher translating adaptive control work into flexible warehouse automation. Technical novelty is exceptional, but customer discovery and commercial ownership are early.",signal:"Filed two robotics-control patents this quarter",tags:["Robotics","Deep tech","Research"],founderScore:84,momentum:66,thesisFit:79,evidence:55,scoreHint:"Top 6% technical score",
    assessments:assessment({title:"Founder",rating:"Bullish",trend:"Improving",confidence:72,body:"Rare research depth with growing evidence of product execution."},{title:"Market",rating:"Neutral",trend:"Stable",confidence:58,body:"Automation demand is clear; wedge and sales cycle remain open."},{title:"Idea × Market",rating:"Neutral",trend:"Improving",confidence:61,body:"Promising technical edge with limited field validation."}),
    events:[{date:"Jun 2026",title:"Second patent application filed",body:"Adaptive grasping controller submitted in Japan and the US.",type:"Research",trust:95},{date:"Apr 2026",title:"Warehouse prototype demo",body:"Completed 500 autonomous pick-and-place cycles.",type:"Product",trust:73},{date:"Jan 2026",title:"Kanso Robotics incorporated",body:"University spinout established in Tokyo.",type:"Company",trust:92},{date:"2021–25",title:"Research Fellow · RIKEN",body:"Published seven papers in adaptive robotic control.",type:"Career",trust:96}],
    claims:[{claim:"Controller adapts with 60% fewer training samples",source:"Preprint and experiment logs",trust:83,status:"Supported"},{claim:"Two logistics groups requested pilots",source:"Email screenshots",trust:54,status:"Needs verification"},{claim:"Exclusive patent licence available",source:"University letter of intent",trust:68,status:"Partially verified"}],coverage:[{label:"Research & technical",value:95},{label:"IP & defensibility",value:72},{label:"Customer discovery",value:42},{label:"Commercial traction",value:24}],gaps:["Confirm IP licence economics","Interview prospective pilot customers","Assess commercial co-founder plan"],relations:[{label:"Kanso",sub:"Company",kind:"company",verified:true},{label:"RIKEN",sub:"Research",kind:"institution",verified:true},{label:"Keio Univ.",sub:"Education",kind:"institution",verified:true},{label:"Aiko Mori",sub:"Co-author",kind:"person",verified:true}],affiliations:[{name:"Kanso Robotics",role:"Founder & Chief Scientist",meta:"2026 — Present",kind:"company"},{name:"RIKEN",role:"Research Fellow",meta:"2021 — 2025",kind:"work"},{name:"Keio University",role:"PhD Robotics",meta:"2017 — 2021",kind:"education"}],
  },
  "founder-004": {
    stableId:"founder-004",initials:"SW",company:"Lattice Health",role:"Co-founder & CEO",location:"San Francisco, US",stage:"Pre-seed",sector:"Clinical AI",summary:"Clinical ML leader building a decision-support layer for specialist care. High-quality problem insight, but the public evidence footprint is intentionally limited.",signal:"New clinical validation study registered with two hospitals",tags:["Healthcare","Applied AI","Clinical"],founderScore:80,momentum:73,thesisFit:76,evidence:43,scoreHint:"High potential · wider interval",
    assessments:assessment({title:"Founder",rating:"Bullish",trend:"Stable",confidence:64,body:"Strong domain expertise with limited team-building evidence."},{title:"Market",rating:"Bullish",trend:"Stable",confidence:70,body:"Expensive workflow with clear unmet clinical need."},{title:"Idea × Market",rating:"Neutral",trend:"Improving",confidence:57,body:"Clinical pull exists; regulatory pathway remains uncertain."}),
    events:[{date:"Jul 2026",title:"Clinical study registered",body:"Prospective validation protocol published with two sites.",type:"Validation",trust:91},{date:"May 2026",title:"Prototype completed",body:"Clinician workflow prototype passed internal usability review.",type:"Product",trust:62},{date:"2022–25",title:"ML Director · DeepLearning.AI",body:"Managed applied research partnerships in healthcare.",type:"Career",trust:84}],claims:[{claim:"Two hospitals committed to validation",source:"Study registry",trust:91,status:"Supported"},{claim:"Workflow saves 18 minutes per case",source:"Internal usability test",trust:52,status:"Needs verification"},{claim:"FDA pathway qualifies as CDS exemption",source:"Legal memo excerpt",trust:48,status:"Needs verification"}],coverage:[{label:"Clinical problem",value:88},{label:"Product evidence",value:56},{label:"Regulatory evidence",value:41},{label:"Commercial traction",value:22}],gaps:["Review full regulatory memo","Verify site principal investigators","Request prototype walkthrough"],relations:[{label:"Lattice",sub:"Company",kind:"company",verified:true},{label:"UCSF",sub:"Study site",kind:"institution",verified:false},{label:"DeepLearning",sub:"Employer",kind:"company",verified:true},{label:"Dr. Patel",sub:"Clinical advisor",kind:"person",verified:true}],affiliations:[{name:"Lattice Health",role:"Co-founder & CEO",meta:"2026 — Present",kind:"company"},{name:"DeepLearning.AI",role:"ML Director",meta:"2022 — 2025",kind:"work"},{name:"Stanford University",role:"MS Biomedical Informatics",meta:"2018 — 2020",kind:"education"}],
  },
  "founder-005": {
    stableId:"founder-005",initials:"DP",company:"HelixForge",role:"Founder & CEO",location:"Boston, US",stage:"Seed",sector:"Biotech",summary:"Computational biologist developing enzyme-design tooling for industrial biotech teams. Strong founder-market fit and credible paid validation, with long technical timelines.",signal:"Second paid discovery program started with a chemicals group",tags:["Biotech","Computational biology","Enterprise"],founderScore:79,momentum:72,thesisFit:82,evidence:69,scoreHint:"Top 15% of cohort",
    assessments:assessment({title:"Founder",rating:"Bullish",trend:"Stable",confidence:79,body:"Deep domain expertise and strong customer empathy."},{title:"Market",rating:"Neutral",trend:"Stable",confidence:66,body:"High-value use case with concentrated buyer universe."},{title:"Idea × Market",rating:"Bullish",trend:"Improving",confidence:74,body:"Paid programs validate willingness to buy early tooling."}),events:[{date:"Jun 2026",title:"Second discovery program",body:"Global chemicals company began a paid eight-week program.",type:"Traction",trust:87},{date:"Mar 2026",title:"Enzyme candidate validated",body:"Wet-lab partner replicated stability improvement.",type:"Science",trust:81},{date:"Nov 2025",title:"HelixForge founded",body:"Company formed after customer interviews with 22 teams.",type:"Company",trust:90},{date:"2019–25",title:"Scientist · Ginkgo Bioworks",body:"Worked on enzyme optimization programs.",type:"Career",trust:94}],claims:[{claim:"Two paid discovery programs active",source:"Redacted statements of work",trust:84,status:"Supported"},{claim:"10× faster candidate ranking",source:"Internal benchmark",trust:61,status:"Partially verified"},{claim:"$9m qualified pipeline",source:"Founder CRM export",trust:49,status:"Needs verification"}],coverage:[{label:"Scientific validation",value:81},{label:"Founder-market fit",value:90},{label:"Commercial traction",value:68},{label:"Pipeline evidence",value:44}],gaps:["Reference both program sponsors","Review wet-lab replication protocol","Validate weighted sales pipeline"],relations:[{label:"HelixForge",sub:"Company",kind:"company",verified:true},{label:"Ginkgo",sub:"Employer",kind:"company",verified:true},{label:"MIT",sub:"Research",kind:"institution",verified:true},{label:"NovaChem",sub:"Customer",kind:"company",verified:false}],affiliations:[{name:"HelixForge",role:"Founder & CEO",meta:"2025 — Present",kind:"company"},{name:"Ginkgo Bioworks",role:"Senior Scientist",meta:"2019 — 2025",kind:"work"},{name:"MIT",role:"PhD Computational Biology",meta:"2014 — 2019",kind:"education"}],
  },
  "founder-006": {
    stableId:"founder-006",initials:"ER",company:"Terraloom",role:"Co-founder & COO",location:"Madrid, Spain",stage:"Pre-seed",sector:"Climate Tech",summary:"Climate operator coordinating industrial heat electrification projects. Unusually strong execution momentum and stakeholder access, though unit economics are still modeled rather than observed.",signal:"Secured municipal approval for first industrial pilot",tags:["Climate tech","Industrial","Operations"],founderScore:83,momentum:85,thesisFit:72,evidence:62,scoreHint:"Top 10% execution score",
    assessments:assessment({title:"Founder",rating:"Bullish",trend:"Improving",confidence:81,body:"Excellent multi-stakeholder execution and learning speed."},{title:"Market",rating:"Bullish",trend:"Improving",confidence:73,body:"Regulation and energy prices create a strong tailwind."},{title:"Idea × Market",rating:"Neutral",trend:"Stable",confidence:60,body:"Pilot demand is real; scalable economics need proof."}),events:[{date:"Jul 2026",title:"Pilot permit approved",body:"Municipal and grid approvals completed for first site.",type:"Milestone",trust:94},{date:"May 2026",title:"Engineering partner signed",body:"EPC contractor joined on milestone-based terms.",type:"Partnership",trust:83},{date:"Feb 2026",title:"Terraloom founded",body:"Company formed after a six-month field study.",type:"Company",trust:90},{date:"2018–25",title:"Program Lead · Iberdrola",body:"Delivered industrial decarbonization programs.",type:"Career",trust:92}],claims:[{claim:"First pilot has all major permits",source:"Municipal permit register",trust:94,status:"Supported"},{claim:"Site could save 1,800 tCO₂ annually",source:"Engineering model",trust:68,status:"Partially verified"},{claim:"Target payback below four years",source:"Founder financial model",trust:45,status:"Needs verification"}],coverage:[{label:"Execution evidence",value:91},{label:"Stakeholder references",value:83},{label:"Engineering model",value:64},{label:"Unit economics",value:38}],gaps:["Stress-test electricity price inputs","Confirm equipment warranty structure","Verify customer capex approval"],relations:[{label:"Terraloom",sub:"Company",kind:"company",verified:true},{label:"Iberdrola",sub:"Employer",kind:"company",verified:true},{label:"Madrid City",sub:"Permit authority",kind:"institution",verified:true},{label:"EcoWorks",sub:"EPC partner",kind:"company",verified:true}],affiliations:[{name:"Terraloom",role:"Co-founder & COO",meta:"2026 — Present",kind:"company"},{name:"Iberdrola",role:"Program Lead",meta:"2018 — 2025",kind:"work"},{name:"IE Business School",role:"MBA",meta:"2016 — 2017",kind:"education"}],
  },
  "founder-007": {
    stableId:"founder-007",initials:"JO",company:"OpenLedger",role:"Solo Founder",location:"Lagos, Nigeria",stage:"Idea",sector:"Fintech Infrastructure",summary:"Cold-start founder building reconciliation APIs for African marketplaces. Public history is sparse, but submitted prototypes and customer discovery show strong learning velocity.",signal:"Prototype processed 18k synthetic transactions with zero mismatches",tags:["Fintech","Cold start","API"],founderScore:74,momentum:59,thesisFit:71,evidence:37,scoreHint:"Promising · wide confidence interval",
    assessments:assessment({title:"Founder",rating:"Neutral",trend:"Improving",confidence:51,body:"Work sample is strong; broader execution history is unknown."},{title:"Market",rating:"Bullish",trend:"Stable",confidence:68,body:"Reconciliation pain is frequent and costly for marketplaces."},{title:"Idea × Market",rating:"Neutral",trend:"Improving",confidence:48,body:"Prototype is credible; no live customer deployment yet."}),events:[{date:"Jul 2026",title:"Technical work sample completed",body:"Built reconciliation service and documented failure modes.",type:"Work sample",trust:88},{date:"Jun 2026",title:"Twelve customer interviews",body:"Interview notes cover marketplaces in three countries.",type:"Discovery",trust:65},{date:"Apr 2026",title:"OpenLedger concept started",body:"Problem selected after marketplace operations role.",type:"Company",trust:72}],claims:[{claim:"Prototype reconciles 18k synthetic transactions",source:"Submitted repository and test run",trust:88,status:"Supported"},{claim:"Eight teams requested a beta",source:"Founder interview notes",trust:42,status:"Needs verification"},{claim:"Reconciliation costs teams 30 hours monthly",source:"Twelve interview summaries",trust:57,status:"Partially verified"}],coverage:[{label:"Technical work sample",value:89},{label:"Customer discovery",value:61},{label:"Identity & references",value:35},{label:"Commercial traction",value:12}],gaps:["Verify three customer interviewees","Run structured founder scenario","Request former manager reference"],relations:[{label:"OpenLedger",sub:"Project",kind:"company",verified:true},{label:"KoraMart",sub:"Employer",kind:"company",verified:false},{label:"Lagos Devs",sub:"Community",kind:"institution",verified:true},{label:"Amaka N.",sub:"Former manager",kind:"person",verified:false}],affiliations:[{name:"OpenLedger",role:"Solo Founder",meta:"2026 — Present",kind:"company"},{name:"KoraMart",role:"Operations Engineer",meta:"2023 — 2026",kind:"work"},{name:"Lagos Dev Community",role:"Volunteer mentor",meta:"2022 — Present",kind:"education"}],
  },
  "founder-008": {
    stableId:"founder-008",initials:"LS",company:"QubitWorks",role:"Co-founder & CTO",location:"Munich, Germany",stage:"Pre-seed",sector:"Quantum Software",summary:"Quantum algorithms engineer building compilation software for near-term hardware. Exceptional technical credibility, with market timing and customer urgency still uncertain.",signal:"Compiler benchmark accepted at a leading quantum conference",tags:["Quantum","Developer tools","Deep tech"],founderScore:86,momentum:64,thesisFit:75,evidence:57,scoreHint:"Top 4% technical score",
    assessments:assessment({title:"Founder",rating:"Bullish",trend:"Stable",confidence:76,body:"Rare technical capability and credible scientific leadership."},{title:"Market",rating:"Bearish",trend:"Stable",confidence:59,body:"Near-term buyer urgency and market timing are uncertain."},{title:"Idea × Market",rating:"Neutral",trend:"Improving",confidence:54,body:"Strong performance result without production validation."}),events:[{date:"Jul 2026",title:"Benchmark paper accepted",body:"Compiler results accepted at QCE 2026.",type:"Research",trust:96},{date:"May 2026",title:"Cloud integration released",body:"Added support for two quantum hardware providers.",type:"Product",trust:78},{date:"Dec 2025",title:"QubitWorks incorporated",body:"Founded with former TUM lab colleague.",type:"Company",trust:91},{date:"2020–25",title:"Quantum Engineer · IQM",body:"Worked on compiler optimization and device mapping.",type:"Career",trust:94}],claims:[{claim:"Compiler reduces circuit depth by 24%",source:"Peer-reviewed benchmark",trust:92,status:"Supported"},{claim:"Four enterprise teams evaluating SDK",source:"Founder pipeline sheet",trust:43,status:"Needs verification"},{claim:"Hardware-agnostic approach is defensible",source:"Technical diligence note",trust:65,status:"Partially verified"}],coverage:[{label:"Technical & research",value:96},{label:"Founder references",value:75},{label:"Customer discovery",value:39},{label:"Commercial urgency",value:21}],gaps:["Interview enterprise evaluators","Assess open-source alternatives","Model timing under hardware scenarios"],relations:[{label:"QubitWorks",sub:"Company",kind:"company",verified:true},{label:"IQM",sub:"Employer",kind:"company",verified:true},{label:"TUM",sub:"Education",kind:"institution",verified:true},{label:"Felix Braun",sub:"Co-founder",kind:"person",verified:true}],affiliations:[{name:"QubitWorks",role:"Co-founder & CTO",meta:"2025 — Present",kind:"company"},{name:"IQM",role:"Quantum Engineer",meta:"2020 — 2025",kind:"work"},{name:"TU Munich",role:"PhD Quantum Computing",meta:"2016 — 2020",kind:"education"}],
  },
};

export function getMockFounderProfile(stableId: string): FounderProfile {
  return mockFounderProfiles[stableId] ?? mockFounderProfiles["founder-001"];
}
