<!-- markdownlint-disable-file MD013 -->

# ScenarioLab Product Requirements Document (PRD)

## 1. Executive Summary

**ScenarioLab** is an AI-powered strategic simulation and war-gaming platform designed for strategy consultants and enterprise decision-makers. Unlike traditional prediction engines, ScenarioLab functions as an **AI decision lab** for scenario rehearsal and strategic stress-testing. It constructs high-fidelity parallel digital worlds where intelligent agents—modeled after real-world stakeholders—interact in strategy-native environments (boardrooms, negotiations, war games) to help consultants rehearse decisions before real-world implementation.

**Tagline:** *AI-Powered War Gaming and Scenario Simulation Platform for Strategic Decision-Making.*

**Key Differentiator:** ScenarioLab transforms the traditional $50K-$200K war-gaming engagement into an on-demand, repeatable capability, delivering consulting-grade deliverables including scenario matrices, risk registers, stakeholder heatmaps, and executive summaries. Supports flexible LLM backends—from cloud APIs to local inference (Ollama, llama.cpp) and CLI subprocess providers (Claude, ChatGPT, Gemini CLIs)—so you can match provider, compliance, and latency needs.

---

## 2. Product Vision

### 2.1 Vision Statement

Create an AI-powered strategic simulation platform that enables consultants and enterprise leaders to rehearse high-stakes decisions in a zero-risk digital environment. By modeling real-world stakeholder dynamics with high-fidelity agent archetypes and strategy-native simulation environments, ScenarioLab bridges the gap between qualitative scenario analysis and quantitative decision support—positioning it as an essential tool for modern strategic advisory.

**Positioning Note:** ScenarioLab is a scenario rehearsal platform, not a prediction engine. Accuracy benchmarks will be established via backtesting against historical events in Phase 3. All outputs should be framed as structured scenario analysis and stress-testing results rather than predictions of future outcomes.

### 2.2 Target Users

| Segment | Description | Use Cases |
| --------- | ------------- | ----------- |
| **Strategy Consultants** | McKinsey, BCG, Bain, Strategy& consultants; boutique advisory firms | M&A culture clash simulation, regulatory shock testing, competitive response war-gaming, boardroom dynamics rehearsal |
| **Enterprise Strategy Teams** | Fortune 100 strategy officers, corporate development | Strategic initiative validation, stakeholder alignment testing, policy rollout simulation |
| **Risk & Compliance Officers** | GRC professionals in financial services | Operational risk scenario testing, compliance policy impact assessment, crisis response rehearsal |
| Decision Makers | Policy makers, business strategists, PR professionals | Zero-risk policy testing, crisis simulation, market scenario analysis |
| Researchers | Academics, data scientists | Social dynamics modeling, behavioral simulation, organizational behavior research |

### 2.3 Key Value Propositions

1. **Consulting-Grade War Gaming** - Transform $50K-$200K traditional war-gaming engagements into on-demand simulations with structured deliverables (scenario matrices, risk registers, stakeholder heatmaps)
2. **Zero-Risk Strategic Rehearsal** - Test high-stakes decisions in a digital sandbox before real-world implementation, from M&A integrations to regulatory responses
3. **Stakeholder-Accurate Agent Modeling** - Calibrate agent populations to mirror actual client organizational structures (via HR system exports) for structurally faithful simulations
4. **Strategy-Native Environments** - Move beyond social media simulations to boardroom debates, negotiation tables, and competitive war rooms
5. **Flexible LLM Backend** - Unified factory-based provider layer: cloud APIs (OpenAI, Anthropic, and OpenAI-compatible endpoints), local servers (Ollama, llama.cpp), and CLI subprocess providers (Claude, ChatGPT, Gemini CLIs) with bounded timeouts for non-interactive runs. Maximum flexibility and provider independence.
6. **MCP Server Integration** - Invoke simulations directly from Claude Desktop, Cursor, or existing CLI pipelines for seamless consultant workflows

---

## 3. Core Features

### 3.1 Feature Overview

| Feature | Priority | Description |
| --------- | ---------- | ------------- |
| Graph Building Engine | P0 | Seed extraction, memory injection, GraphRAG construction |
| Multi-Agent Simulation | P0 | Strategy-native environments (boardroom, war games, negotiations) with dynamic temporal memory |
| Report Generation | P0 | Consulting-grade deliverables: scenario matrices, risk registers, stakeholder heatmaps, exec summaries |
| Consulting Persona Library | P0 | Pre-built agent archetypes: CEO, CFO, regulator, competitor exec, activist investor, union rep |
| Strategy-Native Environments | P0 | Purpose-built simulation environments (boardroom, war room, negotiation, integration planning) with role-based visibility and structured decision rules |
| Flexible LLM Backend | P0 | Unified interface: cloud APIs (OpenAI, Anthropic, OpenAI-compatible), local (Ollama, llama.cpp), CLI providers (cli-claude, cli-chatgpt, cli-gemini) |
| MCP Server Integration | P0 | CLI/agentic workflow integration for Claude Desktop, Cursor, and IDE pipelines |
| Interactive Chat | P1 | Chat with any agent in the simulated world |
| Multi-Scenario Batch Execution | P1 | Compare scenarios side-by-side with Monte Carlo confidence intervals |
| Miro Board Auto-Generation | P1 | Export simulation outputs to Miro boards with frames, app cards, sticky notes |
| AnalyticsAgent | P1 | Silent monitoring of swarm state changes for quantitative metrics (% compliance violation, time-to-consensus, sentiment drop) |
| Emergent Pattern Recognition Module | P1 | Detect agent behavior deviations from archetype baseline using statistical drift detection |
| Interview-Based Persona Extraction | P1 | Structured interview protocol for auto-extracting persona attributes from stakeholder responses |
| Assumption Register with Evidence Tracing | P1 | Track all assumptions with confidence scores, evidence links, and sensitivity analysis |
| Interactive Agent Network Graph | P1 | Real-time force-directed graph visualization of agent communications and coalitions |
| Timeline/Replay Interface | P1 | Interactive timeline slider to scrub through simulation events round-by-round |
| Sensitivity Analysis Visualization | P2 | Tornado charts showing which parameters/assumptions have biggest impact on outcomes |
| Scenario Branching & Version Control | P2 | Git-like branching for scenarios with DAG storage and visual tree view |
| Automated Playbook Templating | P2 | Auto-suggest relevant playbook templates based on scenario description |
| Pre-Built Scenario Libraries by Vertical | P2 | Pre-packaged scenario packs for Fintech, Pharma, Oil & Gas, Tech, etc. |
| Hallucination Detection | P2 | Flag agent statements contradicting established facts from seed material |
| Simulation Narrative Generator | P2 | Auto-generate compelling narrative summary of simulation as a story |
| Voice Chat with Simulated Agents | P2 | Natural voice conversation with agents using Whisper + TTS |
| Gamification & Scoring | P2 | Optional gamification layer for human-participated war games with real-time scoring |
| Bias & Fairness Auditing | P3 | Post-simulation fairness audit via perturbation analysis |
| Outcome Attribution Analysis | P3 | Shapley values computation for outcome explanatory power |
| Interactive Presentation Deck Export | P3 | Generate interactive React-based decks for stakeholder exploration |
| Real-Time Market Intelligence Layer | P3 | Live integration of market data feeds that dynamically update agent worldviews |
| Fine-Tuned Domain-Specific LLM Agents | P3 | Domain-specific model fine-tuning (LoRA/QLoRA) for specialized agent behaviors |
| Client Counterpart Agent | P3 | Generate client counterpart agents for executive presentation rehearsal |
| Regulatory Scenario Generator | P3 | Auto-generate regulatory scenarios by parsing new regulations |
| Behavioral Axioms from Historical Data | P3 | Extract behavioral axioms from historical decision patterns |

### 3.2 Detailed Feature Specifications

#### 3.2.1 Graph Building Engine

**User Story:** As a user, I want to upload seed materials so the system can extract entities and relationships for simulation.

**Requirements:**

- Support text documents, reports, and narrative content as seed input
- Automatic entity extraction and relationship mapping
- Individual and collective memory injection for agents
- GraphRAG construction for knowledge retrieval

**Acceptance Criteria:**

- System processes seed materials within 60 seconds for documents under 10MB
- Extracts minimum 80% of key entities as measured against a human-annotated reference corpus of 5 representative consulting documents (M&A brief, regulatory filing, competitive analysis, board memo, strategy report). Entity types: organizations, people, policies, financial figures, timelines, dependencies.
- Constructs navigable knowledge graph with relationship weights

#### 3.2.2 Multi-Agent Simulation

**User Story:** As a user, I want to run simulations with multiple agents that interact and evolve over time in strategy-native environments.

**Requirements:**

- Generate agents with consulting-specific archetypes (CEO, CFO, regulator, competitor exec, activist investor, union rep, media stakeholder)
- Support strategy-native environments: boardroom debates, war games, negotiations, M&A integration scenarios
- Dynamic temporal memory updates as simulation progresses
- **Simulation Scale:**
  - **Agent Count:** 50-200 well-structured agents for consulting scenarios
  - **Simulation Rounds:** 5-20 rounds for boardroom scenarios; up to 50 rounds for complex war games
- Real-time monitoring of agent interactions and emergent behaviors
- Calibrate swarm demographics to mirror actual client org structure (10% risk officers, 60% front-office, 30% back-office)

**Acceptance Criteria:**

- Support 50-200 concurrent agents per simulation (optimized for consulting use cases)
- Agents demonstrate believable boardroom and negotiation behaviors
- Simulation state persists and can be resumed
- Memory updates reflect agent experiences accurately
- Environment supports structured round-based interactions (proposal → critique → counter-proposal → vote)

#### 3.2.3 Report Generation

**User Story:** As a user, I want to receive detailed scenario analysis reports after simulation completion.

**Requirements:**

- ReportAgent with rich toolset for environment analysis
- Consulting-grade deliverables: scenario matrices, risk registers, stakeholder heatmaps, executive summaries
- Deep interaction with post-simulation environment
- Assumption registers with evidence tracing
- Human-review checkpoints at each pipeline stage
- Export capabilities (PDF, Markdown, JSON, Miro board)
- **Deliverable Schemas:**
  - **Risk Register:** `{risk_id, description, probability, impact, owner, mitigation, trigger}`
  - **Scenario Matrix:** 3-5 scenarios × 4-6 outcomes with probability ranges and confidence intervals
  - **Stakeholder Heatmap:** `{stakeholder, position, influence, support_level, key_concerns}`
  - **Executive Summary:** ≤2 pages, maximum 3 key recommendations

**Acceptance Criteria:**

- Initial auto-generated report draft: within 30 seconds of simulation completion
- Human-reviewed report with checkpoints: configurable, typically 5-15 minutes per checkpoint
- Include at least 5 distinct scenario outcomes with probability ranges
- Provide reasoning chains for each scenario outcome
- Support natural language querying of results
- Deliverables formatted for direct client presentation (SteerCo-ready)

#### 3.2.4 Interactive Chat Interface

**User Story:** As a user, I want to chat with individual agents to understand their perspectives and motivations.

**Requirements:**

- Select and chat with any agent from the simulation
- Agents respond based on their simulated experiences and personality
- Chat history persistence per simulation
- Context-aware responses referencing simulation events

**Acceptance Criteria:**

- Response latency under 3 seconds
- Agents maintain consistent personality throughout conversation
- Reference specific simulation events when relevant
- Support follow-up questions with context retention

#### 3.2.5 Consulting Persona Library

**User Story:** As a consultant, I want pre-built agent archetypes with realistic behavioral patterns so simulations produce credible boardroom dynamics.

**Requirements:**

- Library of 10-15 consulting-specific archetypes: CEO, CFO, CRO, Board Member, Activist Investor, Union Representative, Regulator, Competitor Executive, Media Stakeholder, HR Head, General Counsel, Strategy VP, Operations Head
- Each archetype defined by structured attributes:
  - `role`: Functional position
  - `authority_level`: Decision-making power (1-10 scale)
  - `risk_tolerance`: Risk appetite (conservative/moderate/aggressive)
  - `information_bias`: Data preference (qualitative/quantitative/balanced)
  - `decision_speed`: Deliberation style (fast/moderate/slow)
  - `coalition_tendencies`: Likelihood to form alliances
  - `incentive_structure`: Primary motivations (financial, reputational, operational)
- Behavioral axioms for each archetype (e.g., "CFO defaults to risk-averse; seeks quantitative justification before support")
- Archetype mixing rules for realistic organizational dynamics

**Acceptance Criteria:**

- 3 independent raters evaluate agent transcripts ≥4/5 for realistic decision-making
- Agents reference prior simulation events in contextually appropriate ways
- Behavioral axioms consistently manifest across different simulation scenarios
- Archetype library covers 90%+ of common consulting stakeholder scenarios

**Playbook Role Mapping:**
The following playbook-specific roles reuse or specialize core archetypes:

- Integration PMO → Operations Head archetype with program-management focus
- Chief Compliance Officer → General Counsel / CRO hybrid archetype
- Business Line Heads → Operations Head archetype with business-unit-specific context
- Market Analysts / Key Customers / Industry Observer → Specialized variants of Competitor Executive and Media Stakeholder archetypes
- Activist / Institutional / Independent Board Member / Board Chair → Board Member archetype with governance-style parameters (activist, institutional, independent, chair)

#### 3.2.6 AnalyticsAgent

**User Story:** As a consultant, I want quantitative metrics extracted from simulations so I can present CFO-ready dashboards.

**Requirements:**

- Silent monitoring during simulation (non-intrusive observation)
- Real-time metric collection without impacting agent behavior
- **Key Metrics:**
  - Compliance violation rate (% of actions violating stated policies)
  - Time-to-consensus (rounds/minutes to reach decision)
  - Sentiment trajectory (positive/negative/neutral trend over time)
  - Role-based polarization index (alignment divergence by function)
  - Policy adoption rate (% of proposed initiatives accepted)
- Monte Carlo confidence intervals (20-50 runs per scenario for statistical rigor)
- Metric export formats: JSON, CSV, visual dashboard

**Acceptance Criteria:**

- Metrics computed within 60 seconds of simulation completion
- All metrics exportable as JSON and visual dashboard
- Monte Carlo runs complete within 10 minutes for 20-50 iterations
- Dashboard charts suitable for direct inclusion in client presentations

#### 3.2.7 Miro Board Export Engine

**User Story:** As a consultant, I want simulation outputs auto-exported to Miro boards so I can present directly to steering committees.

**Requirements:**

- Frame hierarchy: Scenario → Outcomes → Risks → Recommendations
- App cards for initiative tracking (with optional Jira/Asana sync)
- Sticky note clustering for evidence and supporting data
- Connector lines showing relationships between outcomes and risks
- Batch PDF export for SteerCo packs
- One-click board generation from simulation results

**Acceptance Criteria:**

- Board pack directly presentable to client SteerCo without manual rework
- Export completes within 60 seconds
- All deliverable schemas (Risk Register, Scenario Matrix, Stakeholder Heatmap) exportable to corresponding Miro elements
- PDF export produces presentation-ready documents

#### 3.2.8 MCP Server Integration

**User Story:** As a consultant, I want to invoke simulations from Claude Desktop or Cursor without context-switching.

**Requirements:**

- CLI interface: `scenariolab-sim --playbook <name> --seed <file.md> --output <format>`
- MCP protocol compliance for agentic workflow integration
- Integration support for:
  - Claude Desktop
  - Cursor IDE
  - Generic IDE pipelines
- Configuration file support for default settings
- Programmatic result retrieval (JSON output for downstream processing)

**Acceptance Criteria:**

- Full simulation lifecycle executable via CLI (configure → run → report → export)
- Results retrievable programmatically via API and CLI
- MCP server responds within 2 seconds for status queries
- CLI commands support non-interactive execution for CI/CD pipelines

#### 3.2.9 Strategy-Native Environment Specification

**User Story:** As a consultant, I want purpose-built simulation environments that mirror real strategic decision-making contexts rather than generic social platforms.

**Environment Types:**

| Environment | Round Structure | Information Visibility | Decision Mechanism |
| ------------- | ----------------- | ------------------------ | -------------------- |
| **Boardroom Debate** | Presentation → Q&A → Objection → Rebuttal → Vote | All participants see same materials; private caucuses allowed between rounds | Majority vote (51%), with Chair tie-breaker; Executive override for CEO decisions |
| **War Room** | Intel briefing → Threat assessment → Response options → Decision → Action assignment | Role-based information access (e.g., CRO sees full risk data; BU heads see operational impact only) | Time-boxed consensus (2-minute decision windows); CRO escalation for compliance issues |
| **Negotiation Table** | Position statements → Private caucus → Counter-proposal → Red-line identification → Agreement/Impasse | Bilateral exchanges between specific parties; mediator sees all communications | Mutual agreement required; BATNA (Best Alternative) triggers if impasse persists >3 rounds |
| **Integration Planning** | Current state mapping → Future state vision → Gap analysis → Initiative prioritization → Resource allocation | Workstream leads see detailed plans; executives see summary dashboards only | Priority matrix scoring (impact × effort); CFO veto on budget exceedance |

**Turn-Taking Rules:**

- **Formal:** Strict rotation (boardroom, regulatory hearings)
- **Dynamic:** Priority based on authority level or urgency (war rooms)
- **Bilateral:** Two-party exchanges with optional mediator (negotiations)
- **Parallel:** Simultaneous workstreams with synchronization points (integration planning)

**Information Asymmetry Controls:**

- Configurable visibility rules per role
- Private message channels for coalition-building
- Public broadcast for official statements
- Intelligence leaks (simulated) for competitive scenarios

**Acceptance Criteria:**

- Each environment type supports its defined round structure without modification
- Information visibility rules enforce role-based access correctly
- Decision mechanisms produce unambiguous outcomes with audit trails
- Environment configurations persist and are reusable across simulations

#### 3.2.10 Emergent Pattern Recognition Module

**User Story:** As a consultant, I want to detect when agent behavior diverges from expected archetype patterns so I can identify emergent dynamics that may impact strategic outcomes.

**Requirements:**

- Detect agent behavior divergence from archetype baseline (e.g., risk-averse CFO suddenly goes aggressive due to coalition dynamics)
- Use behavioral axioms from Persona Library as baseline reference
- Statistical drift detection algorithms to flag emergent patterns
- Output: "Emergent Behaviors Register" alongside Risk Register in reports
- Confidence scoring for detected deviations
- Causal explanation generation for flagged behaviors

**Acceptance Criteria:**

- Flags ≥80% of archetype deviations during simulation
- False positive rate <20% for flagged behaviors
- Flagged behaviors include confidence scores and causal explanations
- Register updates in real-time during simulation
- Exportable as structured data for client presentations

#### 3.2.11 Interview-Based Persona Extraction

**User Story:** As a consultant, I want to extract persona attributes through structured interviews so I can quickly calibrate agents to real stakeholders without manual parameter tuning.

**Requirements:**

- Structured interview protocol (10-15 questions per persona)
- Auto-extraction of persona attributes from interview responses
- Natural language processing: "Tell me about the CEO's risk appetite" → LLM analyzes response, calibrates risk_tolerance parameter
- Enhancement path: audio/video interview analysis (transcribe, extract tone/sentiment, infer traits)
- Integration with Consulting Persona Library for attribute mapping

**Acceptance Criteria:**

- Persona extraction from interview completes in <60 seconds
- Extracted attributes match manual calibration ≥85% of the time
- Supports text, audio, and video input formats
- Interview protocol customizable by consulting firm methodology
- Exported personas directly importable into simulation configuration

#### 3.2.12 Assumption Register with Evidence Tracing

**User Story:** As a consultant, I want to track all assumptions underlying the simulation with evidence links so I can defend recommendations and perform sensitivity analysis.

**Requirements:**

- Track ALL assumptions in simulation: {assumption_id, value, confidence, evidence, sensitivity_score}
- Show which assumptions drive which outcomes
- Flag "HIGH SENSITIVITY" assumptions (small change = big outcome shift)
- Assumption sensitivity table in reports
- Support "What if we're wrong about X?" queries
- Evidence linking to seed materials and external sources

**Acceptance Criteria:**

- All agent initialization assumptions captured automatically
- Sensitivity analysis runs within 120 seconds
- Results include tornado chart visualization data
- Assumption register exportable as structured table
- Evidence links are clickable and verifiable
- HIGH SENSITIVITY flags appear when sensitivity_score > threshold

#### 3.2.13 Interactive Agent Network Graph

**User Story:** As a consultant, I want to visualize agent relationships and coalitions in real-time so I can identify influence patterns and communication flows during simulations.

**Requirements:**

- Real-time force-directed graph visualization: nodes = agents, edges = communications/coalitions
- Click nodes → view agent transcripts and state
- Hover edges → view sentiment/agreement level
- Color edges by sentiment (green = agreement, red = conflict)
- Update in real-time during simulation
- Tech: D3.js or Cytoscape.js; WebGL renderer (Three.js) for 50-200 node scale
- Filter by role, coalition, or sentiment threshold

**Acceptance Criteria:**

- Renders 200-node graph at ≥30fps
- Updates within 1 second of simulation events
- Supports zoom, pan, filter by role/coalition
- Edge colors accurately reflect sentiment analysis
- Node click reveals full agent transcript history
- Exportable as PNG/SVG for client presentations

#### 3.2.14 Timeline/Replay Interface

**User Story:** As a consultant, I want to scrub through simulation history so I can review key turning points and prepare detailed retrospective analysis.

**Requirements:**

- Interactive timeline slider to scrub through simulation events round-by-round
- Drag slider to any round → see all agent states, communications, decisions at that moment
- Store full state snapshots per round (delta-compressed)
- Support forward/backward playback
- Bookmark key turning points with annotations
- Export annotated timeline as presentation material

**Acceptance Criteria:**

- Scrub latency <500ms per round
- Supports bookmarking key turning points
- Exportable as annotated timeline
- State snapshots include all agent memories and relationships
- Playback controls: play, pause, step forward/backward, jump to bookmark
- Timeline visualizes major events (coalition formations, decisions, conflicts)

#### 3.2.15 Voice Chat with Simulated Agents

**User Story:** As a consultant, I want to have natural voice conversations with agents so I can conduct client workshops where stakeholders "talk to" simulated competitors/regulators.

**Requirements:**

- Natural voice conversation with agents during or after simulation
- Stack: OpenAI Whisper (or equivalent) for transcription + TTS for generation
- Client workshop mode: stakeholders "talk to" simulated competitors/regulators
- Voice quality optimization for professional settings
- Maintain agent personality consistency across voice interactions

**Acceptance Criteria:**

- Response latency <3 seconds
- Voice quality rated ≥4/5 by testers
- Maintains agent personality consistency across voice interactions
- Supports multiple languages for international engagements
- Transcription accuracy ≥95% for business terminology
- Exportable conversation transcripts

#### 3.2.16 Scenario Branching & Version Control

**User Story:** As a consultant, I want to create scenario branches so I can compare "what-if" alternatives and explore strategic options systematically.

**Requirements:**

- Git-like branching for scenarios: "What if aggressive pricing?" vs "What if conservative hiring?"
- DAG storage for scenario tree
- Branch at scenario config level
- Visual tree view of branches + comparative metrics dashboard
- Merge/diff capability for scenario configs
- Side-by-side comparison of branch outcomes

**Acceptance Criteria:**

- Branch creation <5 seconds
- Side-by-side comparison of up to 5 branches
- Merge/diff capability for scenario configs
- Visual tree view shows branch relationships clearly
- Comparative metrics dashboard auto-generated
- Branch metadata includes creator, timestamp, and change summary

#### 3.2.17 Hallucination Detection

**User Story:** As a consultant, I want to detect when agents make statements contradicting established facts so I can ensure simulation credibility and accuracy.

**Requirements:**

- Flag agent statements contradicting established facts from seed material or prior simulation events
- Store ground truth facts in Neo4j
- Check generated statements against ground truth during agent reasoning
- Threshold: flag large contradictions (agent denies something that happened), tolerate minor numerical variance (±10%)
- Flagged items include source evidence and suggested correction

**Acceptance Criteria:**

- Detects ≥90% of factual contradictions
- False positive rate <15%
- Flagged items include source evidence
- Real-time detection during agent generation
- Hallucination report included in simulation outputs
- Configurable tolerance thresholds by fact type

#### 3.2.18 Simulation Narrative Generator

**User Story:** As a consultant, I want auto-generated narrative summaries of simulations so I can quickly communicate key insights to executives in story format.

**Requirements:**

- Auto-generate compelling narrative summary of simulation as a story
- Focus on key turning points, coalition shifts, and surprising dynamics
- Example: "In round 3, the CFO and Strategy VP formed an unlikely coalition around cost reduction..."
- 2-3 paragraph executive narrative + detailed round-by-round chronicle
- Highlight unexpected outcomes and counter-intuitive dynamics

**Acceptance Criteria:**

- Narrative generated within 30 seconds
- Covers all major turning points
- Rated ≥4/5 for readability by test users
- Executive narrative ≤2 paragraphs
- Full chronicle includes all significant events
- Exportable as Markdown and PDF

#### 3.2.19 Sensitivity Analysis Visualization (Tornado Charts)

**User Story:** As a consultant, I want to visualize which parameters most impact outcomes so I can focus calibration efforts and present sensitivity insights to CFOs.

**Requirements:**

- Show which agent parameters/assumptions have biggest impact on outcomes
- Run 10-20 parameter variants (e.g., CFO risk tolerance ±0.2)
- Measure outcome sensitivity across variants
- Tornado chart visualization for CFO-focused presentations
- Rank parameters by impact magnitude

**Acceptance Criteria:**

- Sensitivity analysis completes within 5 minutes for 20 variants
- Tornado chart auto-generated
- Exportable as SVG/PNG
- Parameters ranked by impact magnitude
- Confidence intervals shown for sensitivity estimates
- Integration with Assumption Register for parameter selection

#### 3.2.20 Real-Time Market Intelligence Layer

**User Story:** As a consultant, I want agents to reference real-time market data so simulations reflect current conditions and breaking developments.

**Requirements:**

- Live integration of market data feeds (stock prices, news, social sentiment, regulatory announcements)
- Dynamically update agent worldviews based on incoming data
- Start with financial APIs (Alpha Vantage, NewsAPI) + semantic search for relevance
- Configurable data sources per scenario type
- Data relevance filtering to prevent noise

**Acceptance Criteria:**

- Data ingestion latency <30 seconds
- Agents reference real market events in reasoning
- Configurable data sources
- Relevance filtering reduces noise by ≥70%
- Historical data backfill capability
- API rate limiting and error handling

#### 3.2.21 Fine-Tuned Domain-Specific LLM Agents

**User Story:** As a consultant, I want domain-specific agent models so simulations reflect industry-specific language, norms, and decision patterns.

**Requirements:**

- Fine-tune domain-specific models (e.g., "FinServ CEO" trained on earnings call transcripts; "Pharma Regulator" trained on FDA testimony)
- Support LoRA/QLoRA fine-tuning
- Use public data sources (SEC filings, news archives) or client-provided datasets
- Domain-specific reasoning benchmarks for validation
- Model versioning and A/B testing capability

**Acceptance Criteria:**

- Fine-tuned agent demonstrably outperforms generic agent on domain-specific reasoning benchmarks
- Fine-tuning completes within 4 hours on a single NVIDIA A100 (40GB) or equivalent; within 8 hours on NVIDIA A10G (24GB). LoRA/QLoRA methods used to minimize hardware requirements.
- LoRA/QLoRA adapters <100MB for efficient storage
- Benchmark suite covers domain-specific scenarios
- Easy rollback to base model if needed

#### 3.2.22 Client Counterpart Agent (Executive Coach Mode)

**User Story:** As an executive, I want to rehearse presentations against AI counterparts so I can anticipate objections and refine my messaging before SteerCo meetings.

**Requirements:**

- Generate "client counterpart agent" from client briefs
- Executives practice presentations against AI counterpart
- Counterpart generates objections, pushback, and challenging questions calibrated to specific stakeholder
- Bridges ScenarioLab from analysis tool to executive coaching tool
- Multiple rehearsal modes: friendly, challenging, hostile

**Acceptance Criteria:**

- Counterpart generates ≥5 relevant objections per presentation
- Responses reference client context from seed materials
- Latency <3 seconds
- Objections rated ≥4/5 for relevance by test users
- Supports presentation upload (PDF, PPT) for context
- Rehearsal transcript exportable with annotated feedback

#### 3.2.23 Interactive Presentation Deck Export

**User Story:** As a consultant, I want to export interactive presentations so stakeholders can explore simulation results at their own pace.

**Requirements:**

- Generate interactive decks (React-based) where stakeholders click to explore:
  - Agent personas & motivations
  - Risk details with simulation evidence
  - Monte Carlo distributions for recommendations
- Must work offline (no external service dependency)
- Self-contained HTML export
- Mobile-responsive design

**Acceptance Criteria:**

- Deck loads in <3 seconds
- All interactive elements functional offline
- Exportable as self-contained HTML
- Mobile-responsive for tablet presentation
- Interactive charts: zoom, filter, drill-down
- Branding customization (client logo, colors)

#### 3.2.24 Outcome Attribution Analysis (Shapley Values)

**User Story:** As a consultant, I want to quantify which agents drove specific outcomes so I can attribute responsibility and explain results with rigor.

**Requirements:**

- For each outcome, compute which agents/coalitions had highest explanatory power using game theory (Shapley values)
- Use approximation algorithms (KernelSHAP) for 50-200 agent scale
- Output: "The regulator's stance was 40% responsible for blocking the initiative"
- Confidence intervals for attribution estimates
- Coalition-level attribution (not just individual agents)

**Acceptance Criteria:**

- Attribution computed within 10 minutes for 100-agent simulation
- Results include confidence intervals
- Exportable as visualization
- Shapley values sum to 100% for each outcome
- Coalition attributions identified when relevant
- Methodology documented for client credibility

#### 3.2.25 Bias & Fairness Auditing

**User Story:** As a consultant, I want to audit simulations for unintended bias so I can ensure fair and equitable strategic recommendations.

**Requirements:**

- Post-simulation fairness audit: detect whether agent behavior patterns show unintended bias
- Run perturbation simulations (e.g., gender-flipped agent names) and compare outcomes
- Output: Fairness report showing which demographic groups had less influence/satisfaction
- Statistical significance testing
- Mitigation recommendations for identified biases

**Acceptance Criteria:**

- Perturbation analysis runs within 2x base simulation time
- Detects statistically significant disparities at p<0.05
- Fairness report includes visualization of disparities
- Mitigation suggestions provided for flagged biases
- Supports multiple demographic dimensions
- Report suitable for compliance documentation

#### 3.2.26 Automated Playbook Templating

**User Story:** As a consultant, I want auto-suggested playbook templates so I can quickly configure simulations without manual template selection.

**Requirements:**

- Given scenario description, auto-suggest most relevant playbook template
- Pre-fill agent rosters, environment configs, seed material requirements
- MVP: LLM-based semantic matching ("This sounds like a regulatory scenario" → suggest Regulatory Shock Test)
- Confidence score for suggestions
- One-click template application with editable pre-fill

**Acceptance Criteria:**

- Correct playbook suggested ≥80% of the time
- Pre-filled config requires <5 minutes of manual adjustment
- Suggestion confidence score displayed
- Editable pre-fill before simulation launch
- Learning from user corrections over time

#### 3.2.27 Pre-Built Scenario Libraries by Vertical

**User Story:** As a consultant, I want industry-specific scenario packs so I can quickly start simulations with relevant, credible setups.

**Requirements:**

- Pre-packaged scenario packs: "Fintech Disruption in Banking," "AI Talent Flight in Tech," "ESG Regulatory Tightening in Oil & Gas"
- 5-10 scenarios per vertical with pre-configured agents, environment, expected deliverables
- Content sourced from public case studies and industry reports
- Vertical-specific agent archetypes
- Regular updates as industry dynamics evolve

**Acceptance Criteria:**

- Each scenario runnable within 5 minutes of selection
- Includes industry-specific agent archetypes
- Scenarios based on real case studies
- Agent behaviors reflect industry norms
- Deliverables match vertical reporting standards
- Quarterly content updates

#### 3.2.28 Gamification & Scoring for Interactive War Games

**User Story:** As a workshop facilitator, I want gamification features so I can run engaging competitive war games with client teams.

**Requirements:**

- Optional gamification layer for human-participated war games
- Track metrics: consensus points reached, speed, risk reduction score
- Running scoreboard during workshop sessions
- Team-based scoring (2-6 competing teams)
- Real-time leaderboard updates
- Post-game analytics and highlights

**Acceptance Criteria:**

- Scores computed in real-time
- Leaderboard updates within 5 seconds
- Supports 2-6 competing teams
- Metrics align with strategic objectives
- Post-game report with team performance analysis
- Configurable scoring weights by scenario type

#### 3.2.29 Regulatory Scenario Generator

**User Story:** As a compliance consultant, I want to auto-generate scenarios from new regulations so I can quickly assess organizational impact.

**Requirements:**

- Auto-generate regulatory scenarios by parsing new regulations (LLM summarizes legal text)
- Monitor regulatory sources (SEC, industry bulletins)
- Template-based scenario generation
- Auto-generated agent roster based on regulation type
- Expected impacts and compliance requirements identified

**Acceptance Criteria:**

- Scenario generated from regulatory text within 5 minutes
- Includes auto-generated agent roster
- Expected impacts identified with confidence scores
- Compliance requirements extracted accurately
- Links to source regulatory text
- Exportable for legal review

#### 3.2.30 Behavioral Axioms from Real Historical Data

**User Story:** As a consultant, I want to extract behavioral patterns from historical data so agents reflect actual client decision-making tendencies.

**Requirements:**

- Extract behavioral axioms from historical decision patterns (board minutes, earnings calls, prior war game outputs)
- Example: "This client's CFO voted for risk mitigation 85% of the time" → bake into agent behavior
- Pattern recognition across multiple data sources
- Confidence scoring for extracted axioms
- Integration with Consulting Persona Library

**Acceptance Criteria:**

- Axiom extraction from 50+ historical data points completes within 30 minutes
- Extracted axioms validated against holdout data with ≥75% accuracy
- Axioms include confidence scores and source references
- Exportable as persona customization profile
- Supports multiple data formats (PDF, text, structured data)

#### 3.2.31 Simulation Cost Estimator

**User Story:** As a consultant, I want to see projected token usage and cost before running a simulation so I can optimize parameters within budget constraints.

**Requirements:**

- Calculate estimated LLM calls based on agent count × rounds × Monte Carlo iterations
- Display cost estimate per provider
- Allow parameter adjustment to reduce cost
- Show cost breakdown (agent reasoning vs. report generation vs. analytics)

**Acceptance Criteria:**

- Cost estimate displayed within 5 seconds of configuration
- Estimate accuracy within ±20% of actual cost
- Supports all configured LLM providers

#### 3.2.32 Consultant Annotation Layer

**User Story:** As a consultant, I want to add inline commentary and dispute agent outputs during replay so I can bridge AI analysis with expert judgment.

**Requirements:**

- Inline annotation on any agent statement or simulation event during timeline replay
- Support agree/disagree/caveat tags
- Annotations persist with simulation and appear in exported reports
- Collaborative (multiple consultants can annotate same simulation)

**Acceptance Criteria:**

- Annotations saved within 1 second
- Visible in all export formats (PDF, Miro, Interactive Deck)
- Support ≥100 annotations per simulation
- Filterable by annotator and tag type

#### 3.2.33 Multi-Language Seed Material Support

**User Story:** As a consultant working on global engagements, I want to upload seed materials in any language so the system processes them correctly.

**Requirements:**

- Support seed materials in at least: English, German, French, Spanish, Japanese, Mandarin Chinese, Korean, Portuguese, Arabic
- Automatic language detection
- Translation to English for internal processing with original-language preservation for reference
- Agent outputs in user's configured language

**Acceptance Criteria:**

- Language detection accuracy ≥95%
- Entity extraction quality within 10% of English-language baseline for supported languages
- Processing time overhead <30% vs. English-only

#### 3.2.34 Playbook Co-Pilot

**User Story:** As a consultant, I want AI-assisted structuring of my seed materials before simulation launch so I can reduce setup time.

**Requirements:**

- LLM analyzes uploaded seed material and suggests: relevant playbook template, agent roster, key entities to model, recommended simulation parameters, missing information gaps
- Interactive refinement ("Add more detail about the regulatory environment")
- Auto-generates structured seed format from unstructured documents

**Acceptance Criteria:**

- Suggestions generated within 30 seconds of upload
- Reduces manual configuration time from ~5 minutes to <2 minutes
- Suggestion acceptance rate ≥70% (users accept without major modification)

#### 3.2.35 Simulation Confidence Decay Model

**User Story:** As a consultant, I want simulation outputs to honestly reflect decreasing confidence as simulations run longer, so deliverables maintain intellectual rigor.

**Requirements:**

- Confidence scores on agent positions and outcomes decrease as simulation rounds increase (reflecting memory drift and compounding uncertainty)
- Decay rate configurable per environment type
- Reports clearly indicate confidence level per round
- Visual confidence band on timeline

**Acceptance Criteria:**

- Confidence decay curves validated against agent memory coherence metrics
- Decay rate calibrated so round-20 confidence is 15-30% lower than round-1 for typical simulations
- Clearly displayed in all reports and timeline views

#### 3.2.36 Cross-Simulation Learning

**User Story:** As a platform operator, I want anonymized patterns aggregated across simulations to improve archetype calibration over time, creating a proprietary data advantage.

**Requirements:**

- Opt-in only
- Privacy-preserving aggregation (no client-identifiable data leaves the simulation)
- Extract behavioral pattern statistics (e.g., "CFO archetypes block proposals 62% of the time across 500 simulations")
- Use aggregate data to improve default archetype behavioral axioms
- Differential privacy guarantees

**Acceptance Criteria:**

- Zero client data leakage (verified by privacy audit)
- Archetype calibration improvement measurable after 100+ simulations
- Opt-in rate tracked
- Users can verify what data is shared

#### 3.2.37 Negotiation ZOPA Mapping

**User Story:** As a consultant running a negotiation simulation, I want the system to auto-compute the Zone of Possible Agreement from agent positions so I can add quantitative rigor to negotiation analysis.

**Requirements:**

- For Negotiation Table environment, extract each agent's red-lines (non-negotiable positions) and BATNA (Best Alternative to Negotiated Agreement)
- Compute overlap zone (ZOPA) across all negotiating parties
- Visualize ZOPA as a multi-dimensional space
- Identify which concessions would expand ZOPA

**Acceptance Criteria:**

- ZOPA computed within 30 seconds of simulation completion
- Visualization shows each party's range and overlap
- Correctly identifies no-deal scenarios when ZOPA is empty
- Concession recommendations ranked by impact on ZOPA size

#### 3.2.38 Simulation Audit Trail

**User Story:** As a GRC professional, I want immutable audit logs of simulation runs so I can use simulation outputs as compliance documentation.

**Requirements:**

- Design audit trail schema from Phase 1 (even if full implementation is Phase 4)
- Log: simulation configuration, all agent decisions with reasoning, all parameter changes, user interactions, report generation events
- Immutable append-only log
- Cryptographic hash chain for tamper detection
- Exportable for regulatory review

**Acceptance Criteria:**

- Phase 1-2: audit trail schema defined and core events logged (even if not tamper-proof yet)
- Phase 4: full immutable audit trail with hash chain
- Export to standard compliance formats (JSON, CSV with digital signatures)

---

## 4. Technical Architecture

### 4.1 System Architecture

```text
┌─────────────────────────────────────────────────────────────────┐
│                        Frontend (Next.js)                        │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────┐  │
│  │   Upload    │  │ Simulation  │  │    Chat Interface       │  │
│  │   Module    │  │   Monitor   │  │                         │  │
│  └─────────────┘  └─────────────┘  └─────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                      Backend API (Python)                        │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────┐  │
│  │   Graph     │  │   Agent     │  │    Report Generator     │  │
│  │   Builder   │  │  Simulation │  │                         │  │
│  └─────────────┘  └─────────────┘  └─────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
                              │
              ┌───────────────┼───────────────┐
              ▼               ▼               ▼
        ┌─────────┐    ┌──────────┐    ┌──────────┐
        │   LLM   │    │  Memory  │    │ Graph DB │
        │         │    │          │    │  (RAG)   │
        └─────────┘    └──────────┘    └──────────┘
```

> **Note:** Diagram shows a representative configuration. The LLM component supports multiple providers (cloud APIs, local servers, and CLI subprocess backends). **Graph / memory:** Neo4j powers GraphRAG and seed/knowledge-graph features in `app/graph`. **Graphiti** is **not** a Neo4j built-in; it is an **external Python library** (`graphiti_core`) that **integrates with Neo4j** to store a temporal episode graph per simulation (`group_id`). **`GRAPHITI_ENABLED`** toggles whether the backend starts that Graphiti integration at runtime; when off, Graphiti is not initialized and temporal-graph features are inactive. Graphiti’s default embedder/LLM expect an OpenAI-class API key (`GRAPHITI_OPENAI_API_KEY`, or `LLM_API_KEY` with `LLM_PROVIDER=openai`, or `OPENAI_API_KEY`). GraphRAG/seed graph paths can fall back when Neo4j is unavailable; **Graphiti itself requires a reachable Neo4j** (it does not run on the SQLite graph fallback).

### 4.2 Technology Stack

| Component | Technology | Version | Deployment Mode |
| ----------- | ------------ | --------- | ----------------- |
| Frontend | Next.js + React + Tailwind + Zustand | 16.x (App Router) | Both |
| Backend | Python (FastAPI) + uv | 3.11-3.12 | Both |
| Package Manager | uv | Latest | Both |
| LLM API | Provider factory (`LLM_PROVIDER`): `openai`, `anthropic`, `google`, `qwen`, `ollama`, `llamacpp`, `cli-claude`, `cli-chatgpt`, `cli-gemini`, `cli-codex`; OpenAI-compatible `LLM_BASE_URL` for Azure/proxies | - | Both |
| Memory | Neo4j-backed temporal agent memory and GraphRAG (`app/graph`); SQLite fallback when Neo4j unavailable | 5.x Neo4j | Both |
| Graph DB | Neo4j | 5.x | Both |
| Reports DB | SQLite (aiosqlite, WAL) for report persistence | - | Both |
| Container | Docker + Docker Compose | - | Both |
| MCP Server | In-process MCP server (`app/mcp`), toggle via `MCP_SERVER_ENABLED` | - | Both |

### 4.3 API Requirements

#### External API (v1)

ScenarioLab exposes an authenticated external API at `/api/v1/` for third-party integrations:

| Category | Endpoints | Auth |
|----------|-----------|------|
| **API Key Management** | `POST/GET/DELETE /api/v1/api-keys` | Admin key (`ADMIN_API_KEY`) |
| **Webhooks** | `POST/GET/DELETE /api/v1/webhooks` | API key |
| **Simulations** | `POST /api/v1/simulations`, `GET .../results`, `POST .../start` | API key with `write:simulations` or `read:simulations` scope |
| **Reports** | `GET /api/v1/reports/{id}` | API key with `read:reports` scope |

All endpoints require `Authorization: Bearer <key>`. API keys are scoped (read/write per resource type).

#### Dual-Create Rollback Safety

The platform supports atomic creation of simulation pairs for A/B comparison:
- `POST /api/simulations/dual-create`: Creates two simulations; if the second fails, the first is automatically rolled back (deleted).
- `POST /api/simulations/dual-run-preset`: Preview two payloads without persistence.
- `POST /api/simulations/dual-run-preset-create`: Preview and persist in one call.

#### Seed Upload Protocol

Uploads use a client-ID handshake for reliability:
- Each upload receives an `X-Client-Upload-Id` header
- `POST /api/seeds/upload/ack-client-id`: Acknowledge successful upload
- `POST /api/seeds/upload/cancel-by-client-id`: Safe abort on browser disconnect

#### LLM Response Sanitization

All LLM output passes through defensive processing:
- JSON fence stripping (`reports/llm_json_fences.py`): Removes markdown ` ```json ` / ` ``` ` wrappers before JSON parsing
- Agent response sanitization (`simulation/agent.py:sanitize_llm_response()`): Strips `<think>` blocks, detects non-English hallucinations (>40% non-Latin chars)

**LLM Configuration:**

- Providers implemented in `backend/app/llm/`: `openai`, `anthropic`, `google`, `qwen`, `ollama`, `llamacpp`, `cli-claude`, `cli-chatgpt`, `cli-gemini`, `cli-codex` (CLI providers use subprocess execution with bounded timeouts)
- **Cloud APIs:** OpenAI, Anthropic, Google, Qwen, and OpenAI-compatible clients; `LLM_BASE_URL` overrides for Azure OpenAI and other proxies
- **Local servers:** Ollama, llama.cpp
- **CLI inference:** Native Claude / OpenAI / Gemini / Codex CLI installers for air-gapped or keyless local workflows
- **Hybrid inference:** `INFERENCE_MODE=hybrid` routes rounds between local and cloud providers; `GET /api/llm/capabilities` probes availability (cached)
- Base URL examples:
  - Ollama: `http://localhost:11434/v1`
  - OpenAI: `https://api.openai.com/v1`

**Memory and graph service:**

- Neo4j 5.x for knowledge graph, GraphRAG, and simulation memory (`SimulationMemoryManager` in `app/simulation/memory_manager.py`)
- Optional **Graphiti (external `graphiti_core` library integrating with Neo4j)** — enable with **`GRAPHITI_ENABLED`**; requires **Neo4j** for the Graphiti driver; default embedder/LLM need an **OpenAI-class API key** (`GRAPHITI_OPENAI_API_KEY`, or `LLM_API_KEY` with `LLM_PROVIDER=openai`, or `OPENAI_API_KEY`). Temporal facts are keyed per simulation (`group_id`); see `GET /api/graph/temporal-memory-status`
- When Neo4j is not reachable, GraphRAG/seed graph features degrade and core simulation/report flows continue using SQLite and in-memory state; **Graphiti does not operate without Neo4j**

---

## 5. User Experience

### 5.1 User Flow

```text
┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐
│  Upload  │───▶│ Configure│───▶│ Simulate │───▶│  Review  │───▶│  Chat/   │
│  Seeds   │    │  Agents  │    │   Run    │    │  Report  │    │ Explore  │
└──────────┘    └──────────┘    └──────────┘    └──────────┘    └──────────┘
```

### 5.2 Key User Interfaces

1. **Dashboard** - Overview of simulations, recent reports, quick actions
2. **Upload Interface** - Drag-and-drop seed material upload with preview
3. **Simulation creation wizard** - Five-step flow at `/simulations/new` (playbook → agents → seeds → parameters → review/launch)
4. **Simulation Monitor** - Real-time visualization of agent interactions
5. **Report Viewer** - Structured scenario analysis reports with interactive elements
6. **Chat Interface** - Conversational UI for agent interaction
7. **Miro Board Export** - One-click export of simulation outputs to Miro boards
8. **Consulting Playbooks** - Pre-configured templates for M&A, regulatory shock, competitive response
9. **CLI/MCP Interface** - Command-line (`scenariolab-sim`) and Model Context Protocol integration for IDE workflows
10. **Interactive Network Graph** - Force-directed visualization of agent dynamics and coalitions; nodes represent agents, edges show communications with sentiment coloring; supports zoom, pan, and filter by role/coalition
11. **Timeline/Replay** - Scrub through simulation history with interactive timeline slider; bookmark key turning points; export annotated timelines
12. **Voice Chat** - Natural voice conversation with simulated agents using Whisper transcription and TTS generation; enables client workshops where stakeholders "talk to" simulated competitors/regulators
13. **Interactive Deck Viewer** - Self-contained interactive presentation export (React-based HTML); stakeholders click to explore agent personas, risk details, and Monte Carlo distributions; works offline

#### 5.2.8 CLI/MCP Interface Workflow

**Consultant Invocation Flow:**

```bash
# From terminal or IDE integrated terminal
$ scenariolab-sim --playbook mna-culture --seed ./deal-materials.md --output miro

# Or via MCP from Claude Desktop/Cursor
> Run M&A culture clash simulation with the uploaded deal materials and export to Miro
```

**Workflow Description:**

1. **Configuration** - Consultant selects playbook, provides seed material path, specifies output format
2. **Validation** - System validates seed material format and completeness
3. **Simulation Execution** - Runs multi-agent simulation with progress indicators
4. **Report Generation** - Auto-generates draft report; optional human review checkpoints
5. **Export** - Delivers outputs to specified destination (Miro board, local files, JSON API)

**MCP Protocol Support:**

- `scenariolab/simulate`: Initiate simulation with parameters
- `scenariolab/status`: Check simulation progress
- `scenariolab/results`: Retrieve completed simulation results
- `scenariolab/export`: Export to specified format (miro, pdf, json)
- `scenariolab/playbooks/list`: List available consulting playbooks

**IDE Integration Examples:**

- **Claude Desktop:** Natural language simulation requests with context awareness
- **Cursor:** `/scenariolab` command palette for quick simulation invocation
- **VS Code:** Extension with sidebar for playbook selection and result viewing

### 5.3 Design Principles

- **Clean and Minimal** - Focus on content, reduce visual noise
- **Progressive Disclosure** - Show complexity only when needed
- **Real-time Feedback** - Visual indicators for simulation progress
- **Accessibility First** - WCAG 2.1 AA compliance

---

## 6. Non-Functional Requirements

### 6.1 Performance

| Metric | Target |
| -------- | -------- |
| Page Load Time | < 3 seconds |
| API Response Time | < 500ms (p95) |
| Simulation Initialization | < 60 seconds |
| Report Generation | < 30 seconds |
| Concurrent Users | 100+ |
| **New Feature Performance Targets** | |
| Network Graph Rendering | ≥30fps for 200 nodes |
| Timeline Scrub Latency | <500ms per round |
| Voice Response Latency | <3 seconds |
| Sensitivity Analysis | <5 minutes for 20 variants |
| Hallucination Detection | Real-time during generation |
| Shapley Value Computation | <10 minutes for 100-agent simulation |
| Scenario Branch Creation | <5 seconds |
| Perturbation Analysis | <2x base simulation time |

### 6.2 Security

**Security Requirements:**

- API key encryption at rest
- Input validation and sanitization
- Rate limiting on API endpoints
- No persistent storage of sensitive user data
- **Data residency**: Configurable data storage location; all simulation data stored locally by default
- **Encryption in transit**: TLS 1.3 for all API communications
- **Encryption at rest**: AES-256 for stored simulation data, seed materials, and reports
- **Client data isolation**: Multi-tenant deployments use strict data isolation; no cross-client data leakage
- **Seed material handling**: Sensitive M&A/board-level documents processed in-memory where possible; configurable auto-deletion after simulation completion
- **Audit trail design-in**: Core simulation event logging designed from Phase 1 to support future regulatory audit requirements (Phase 4 implementation)

### 6.3 Scalability

- Horizontal scaling via containerization
- Stateless backend design
- Efficient memory management for large agent populations

### 6.4 Reliability

- 99.5% uptime target
- Graceful degradation when LLM API is unavailable
- Automatic retry with exponential backoff

### 6.5 Cost Management & Token Budgeting

Running 50-200 agents × 5-50 rounds × 20-50 Monte Carlo iterations = potentially 5,000-500,000 LLM calls per simulation.

**Cost Management Requirements:**

- **Pre-simulation cost estimator**: Display projected token usage and estimated cost before execution; allow user to adjust parameters (fewer agents, fewer rounds, fewer Monte Carlo runs) to fit budget
- **Token budgeting**: Configurable per-simulation token budget with automatic truncation/summarization when approaching limits
- **Cost optimization strategies**: Agent response caching for identical prompts; batch inference where supported; tiered model usage (use smaller/cheaper models for routine agent reasoning, reserve larger models for critical decisions and report generation)
- **Baseline cost targets**: Simple simulation (50 agents, 10 rounds, no Monte Carlo): <$5 with GPT-4-class models; Full war game (200 agents, 50 rounds, 50 Monte Carlo): <$200

**Note:** Actual costs depend on LLM provider pricing; local models (Ollama) have zero marginal token cost.

---

## 7. Deployment & Operations

### 7.1 Deployment Options

#### Option 1: Source Code Deployment (Recommended)

```bash
# Setup
npm run setup:all

# Development
npm run dev

# Services
# Frontend: http://localhost:3000
# Backend: http://localhost:5001
```

#### Option 2: Docker Deployment

```bash
cp .env.example .env
# Configure API keys
docker compose up -d
```

### 7.2 Environment Variables

| Variable | Required | Description |
| ---------- | ---------- | ------------- |
| `LLM_PROVIDER` | Yes | `openai`, `anthropic`, `google`, `qwen`, `ollama`, `llamacpp`, `cli-claude`, `cli-chatgpt`, `cli-gemini`, `cli-codex` |
| `LLM_API_KEY` | Conditional | API key for cloud providers (not needed for Ollama/llama.cpp or CLI providers) |
| `LLM_BASE_URL` | Conditional | **Required** when `LLM_PROVIDER` is `ollama`, `llamacpp`, or any setup that talks to a **non-default HTTP base** (self-hosted OpenAI-compatible servers, Azure OpenAI, LiteLLM/vLLM gateways, corporate proxies). **Optional** when using vendor public APIs with built-in defaults (`openai`, `anthropic`, `google`, `qwen`)—omit unless you intentionally override the hostname. **CLI providers** (`cli-*`) do not use `LLM_BASE_URL`. See `.env.example`. |
| `LLM_MODEL_NAME` | Yes | Model identifier sent to the active provider |
| `LLM_CONCURRENCY_DEFAULT` | No | Max concurrent LLM calls (default 3); per-provider overrides via `LLM_CONCURRENCY_OVERRIDES` JSON map |
| `INFERENCE_MODE` | No | `cloud` (default), `hybrid`, or `local`; hybrid routes rounds between cloud and local |
| `LOCAL_LLM_PROVIDER` | For hybrid | Local provider key (`ollama` or `llamacpp`) |
| `LOCAL_LLM_BASE_URL` | For hybrid | Local provider URL (default `http://localhost:11434/v1`) |
| `LOCAL_LLM_MODEL_NAME` | For hybrid | Local model name (default `qwen3:14b`) |
| `HYBRID_CLOUD_ROUNDS` | For hybrid | Every Nth round uses cloud (default 1) |
| `SIMULATION_MAX_AGENTS` | No | Max agents per simulation (default 48) |
| `SIMULATION_LLM_PARALLELISM` | No | Concurrent LLM calls during simulation (default 4) |
| `SIMULATION_ROUND_TIMEOUT_SECONDS` | No | Per-round wall-clock timeout; 0 = disabled (default) |
| `INLINE_MONTE_CARLO_MAX_ITERATIONS` | No | Max Monte Carlo iterations from wizard (default 25) |
| `DEBUG` | No | Exposes exception messages in HTTP errors; **never enable in production** |
| `NEO4J_URI` | For graph features | Neo4j Bolt URI (e.g., `bolt://localhost:7687`); omit or unreachable → graceful degradation |
| `NEO4J_USER` | With Neo4j | Neo4j username |
| `NEO4J_PASSWORD` | With Neo4j | Neo4j password |
| `MIRO_API_TOKEN` | No | Miro REST API token for board export |
| `MIRO_BOARD_ID` | No | Target Miro board when syncing |
| `MCP_SERVER_ENABLED` | No | Enable built-in MCP server (`true` / `false`, default false) |
| `TAVILY_API_KEY` | For autoresearch web search | Tavily API key (`/research` flows) |
| `SEC_USER_AGENT` | For SEC EDGAR | Required string for SEC EDGAR API calls |
| `GRAPHITI_ENABLED` | No | Enable Graphiti temporal graph (`true` / `false`); requires OpenAI-compatible key for Graphiti |
| `NEO4J_GRAPHITI_DATABASE` | No | Neo4j database name for Graphiti (default `neo4j`) |
| `GRAPHITI_OPENAI_API_KEY` | No | Optional; defaults from `LLM_API_KEY` when `LLM_PROVIDER=openai` |
| `ADMIN_API_KEY` | For integration API key mgmt | Protects `/api/v1/api-keys` admin routes |

**`LLM_BASE_URL` quick check:** No self-hosted or custom API base URL → usually omit for cloud defaults. Using Ollama / llama.cpp / Azure or another OpenAI-compatible endpoint → set `LLM_BASE_URL` to that server’s base (e.g. `http://localhost:11434/v1` for Ollama).

### 7.3 Monitoring & Logging

- Application logs centralized
- LLM API usage tracking
- Simulation performance metrics
- Error tracking and alerting

---

## 8. Roadmap

**Phase Prioritization Rationale:** Phases are prioritized based on (1) client unblockers — features required for first paid engagements, (2) consulting workflow integration — tools that fit existing consultant habits, and (3) credibility building — capabilities that establish ScenarioLab as a serious consulting tool rather than a demo.

### Phase 1: MVP (30-Day Sprint)

**Priority:** Unblock first client engagements

- [x] Core simulation engine
- [x] Basic web interface
- [x] Report generation
- [x] MCP server wrapper around FastAPI backend
- [x] Flexible LLM backend with multi-provider support (OpenAI, Anthropic, Google, Qwen, Ollama, llama.cpp)
- [x] 4 consulting playbook templates (M&A culture clash, regulatory shock test, competitive response war game, boardroom rehearsal)
- [x] Consulting persona library with 13 archetypes
- [x] Structured deliverable templates for ReportAgent

### Phase 2: Enhanced Experience

**Priority:** Consultant workflow integration and credibility

- [x] Multi-scenario batch execution with comparison views
- [x] Monte Carlo confidence intervals
- [x] AnalyticsAgent for quantitative metrics extraction
- [x] Miro board auto-generation with frames, app cards, sticky notes (real API integration when MIRO_API_TOKEN is set; mock fallback otherwise)
- [x] Interactive chat improvements
- [x] Additional LLM provider support
- [x] Mobile-responsive design
- [x] **Emergent Pattern Recognition Module** - Detect agent behavior deviations from archetype baseline
- [x] **Interview-Based Persona Extraction** - Structured interview protocol for auto-extracting persona attributes
- [x] **Assumption Register with Evidence Tracing** - Track all assumptions with confidence scores and sensitivity analysis
- [x] **Interactive Agent Network Graph** - Real-time force-directed graph visualization of agent dynamics
- [x] **Timeline/Replay Interface** - Interactive timeline slider to scrub through simulation events
- [x] **Scenario Branching & Version Control** - Git-like branching for scenarios with DAG storage
- [x] **Hallucination Detection** - Flag agent statements contradicting established facts
- [x] **Simulation Narrative Generator** - Auto-generate compelling narrative summary of simulation
- [x] **Sensitivity Analysis Visualization (Tornado Charts)** - Show which parameters have biggest impact on outcomes
- [x] **Automated Playbook Templating** - Auto-suggest relevant playbook templates based on scenario description
- [x] **Pre-Built Scenario Libraries by Vertical** - Pre-packaged scenario packs for Fintech, Pharma, Oil & Gas, Tech, etc.
- [x] **Gamification & Scoring for Interactive War Games** - Optional gamification layer for human-participated war games
- [x] **Simulation Cost Estimator** - Display projected token usage and cost before execution
- [x] **Consultant Annotation Layer** - Inline commentary and dispute agent outputs during replay (full backend persistence + frontend UI)
- [x] **Multi-Language Seed Material Support** - Upload seed materials in 8+ languages
- [x] **Playbook Co-Pilot** - AI-assisted structuring of seed materials before simulation launch

### Phase 3: Advanced Features

**Priority:** Differentiation and accuracy validation

- [x] **Voice Chat with Simulated Agents** - Natural voice conversation with agents using Whisper + TTS
- [x] Client Counterpart Agent for rehearsing executive presentations
- [x] Backtesting engine against historical events (establish accuracy benchmarks)
- [x] Backtesting methodology: Feed historical events, compare simulated vs. actual outcomes, calibrate confidence intervals
  - **Historical datasets**: Start with 3-5 well-documented public cases (major M&A outcomes, regulatory responses, competitive market entries) sourced from public filings, news archives, and published case studies
  - **Accuracy definition**: "Scenario outcome correlation" — measure whether simulated stakeholder positions and decision outcomes align with actual historical outcomes on a structured rubric (stakeholder stance accuracy, timeline accuracy, outcome direction accuracy)
  - **Validation approach**: Blind test — configure simulation with pre-event seed materials only, compare outputs against known post-event outcomes
  - **Note**: This is a sketch; full methodology to be specified in Phase 3 planning
- [x] Custom agent personality designer
- [x] Financial scenario templates
- [x] Political news scenario models
- [x] API for third-party integrations
- [x] **Real-Time Market Intelligence Layer** - Live integration of market data feeds
- [x] **Fine-Tuned Domain-Specific LLM Agents** - Domain-specific model fine-tuning (LoRA/QLoRA)
- [x] **Client Counterpart Agent (Executive Coach Mode)** - Generate client counterpart agents for presentation rehearsal
- [x] **Interactive Presentation Deck Export** - Generate interactive React-based decks for stakeholder exploration
- [x] **Outcome Attribution Analysis (Shapley Values)** - Compute which agents/coalitions had highest explanatory power
- [x] **Bias & Fairness Auditing** - Post-simulation fairness audit via perturbation analysis
- [x] **Regulatory Scenario Generator** - Auto-generate regulatory scenarios by parsing new regulations
- [x] **Behavioral Axioms from Real Historical Data** - Extract behavioral axioms from historical decision patterns
- [x] **Simulation Confidence Decay Model** - Confidence scores reflect decreasing confidence as simulations run longer
- [x] **Cross-Simulation Learning** - Anonymized patterns aggregated across simulations (opt-in, privacy-preserving)
- [x] **Negotiation ZOPA Mapping** - Auto-compute Zone of Possible Agreement from agent positions
- [x] **Simulation Audit Trail** - Schema design (full implementation with immutable logs in Phase 4)

### Phase 4: Enterprise

**Priority:** Scale and compliance certification

- [ ] Multi-tenant support
- [ ] Advanced analytics dashboard
- [ ] Collaboration features
- [ ] SSO/SAML integration
- [ ] Air-gapped local deployment option
- [ ] Audit logging for compliance
- [ ] SOC 2 Type II certification
- [ ] ISO 27001 certification
- [ ] **Video Integration with Agent Avatars** - Visual representation of agents in video format
- [ ] **3D Boardroom Visualization** - Immersive 3D environment for boardroom simulations
- [ ] **Real-Time Multiplayer Simulation Observation** - Multiple stakeholders observing simulations simultaneously
- [ ] **Tableau/PowerBI Live Dashboard Integration** - Direct integration with enterprise BI tools
- [ ] **HR System Integration for Organizational Structure Import** - Import org structures from AD/Workday
- [ ] **Memory Pruning & Forgetting Mechanisms** - Intelligent memory management for long-running simulations
- [ ] **Simulation Audit Trail** - Full implementation with immutable logs and cryptographic hash chain

---

## 9. Success Metrics

### 9.1 SaaS Metrics

| Metric | Target |
| -------- | -------- |
| User Signups | 1000 in first 3 months |
| Simulation Runs | 5000+ per month |
| Average Session Duration | 15+ minutes |
| Report Sharing Rate | 30%+ |
| User Retention (7-day) | 40%+ |

### 9.2 Consulting-Specific Metrics

| Metric | Target | Measurement Method |
| -------- | -------- | ------------------- |
| Engagements Deployed | 50+ in first 6 months | Count of unique client engagements with simulation usage |
| Time to First Simulation | <15 minutes | From login to completed first simulation run |
| Consultant Satisfaction (Report Quality) | >4/5 | Post-simulation survey: "Deliverables ready for client presentation" |
| Miro Board Export Adoption | >70% of simulations | % of simulations with Miro export enabled |
| MCP Invocation Rate | >50% for IDE users | % of simulations initiated via CLI/MCP vs. web UI |
| SteerCo Presentation Rate | >60% | % of simulations resulting in board/SteerCo presentation |
| **New Feature Success Metrics** | | |
| Emergent Behavior Detection Rate | ≥80% | % of significant archetype deviations flagged by system |
| Persona Setup Time (with interview extraction) | <10 minutes | Time to complete persona calibration using interview method |
| Scenario Branch Exploration | Avg 3+ branches | Average number of scenario branches created per simulation |
| Voice Chat Adoption | >30% | % of post-simulation interactions using voice interface |
| Assumption Register Completeness | 100% | % of simulations with fully populated assumption register |
| Hallucination Detection Accuracy | ≥90% | % of factual contradictions correctly detected |
| Sensitivity Analysis Usage | >50% | % of simulations including sensitivity analysis |
| Network Graph Engagement | >40% | % of users interacting with network visualization |
| Timeline Replay Usage | >35% | % of simulations with timeline replay accessed |
| Playbook Template Accuracy | ≥80% | % of correctly suggested playbook templates |
| Narrative Generator Satisfaction | ≥4/5 | User rating of auto-generated simulation narratives |
| Pre-simulation cost estimate accuracy | within ±20% of actual | Compare estimated vs. actual LLM costs |
| Multi-language seed material support | ≥8 languages | Number of supported languages for seed processing |
| Playbook co-pilot adoption | >60% of simulations | % of simulations using co-pilot suggestions |
| Consultant annotation usage | avg ≥5 annotations per simulation review | Average annotations added per simulation review |

---

## 10. Open Source & Community

### 10.1 License

- Open source under appropriate license (TBD)

### 10.2 Acknowledgments

- Powered by [OASIS](https://github.com/camel-ai/oasis) (Open Agent Social Interaction Simulations)
- Strategic support from Shanda Group

### 10.3 Community

- GitHub: <https://github.com/666ghj/ScenarioLab>
- Contact: <scenariolab@shanda.com>

---

## 11. Appendix

### 11.1 Glossary

| Term | Definition |
| ------ | ------------ |
| **Seed Material** | Source documents used to initialize the simulation world |
| **GraphRAG** | Graph-based Retrieval-Augmented Generation for knowledge retrieval |
| **Agent** | AI entity with personality, memory, and behavioral logic |
| **Simulation Round** | One iteration of agent interactions in the digital world |
| **Neo4j memory layer** | GraphRAG, entity extraction, and related graph code in `app/graph`, primarily backed by **Neo4j** (with graceful degradation for some paths when Neo4j is down). **Graphiti** is an **optional external package** (`graphiti_core`) used only when **`GRAPHITI_ENABLED`** is true: that flag turns on integration with the Graphiti library for a temporal context graph per simulation over Neo4j. When `GRAPHITI_ENABLED` is false, Graphiti is not loaded for that integration; core GraphRAG/seed features do not depend on Graphiti. |
| **MCP** | Model Context Protocol for agentic workflow integration |
| **War Gaming** | Structured simulation of competitive or strategic scenarios |
| **Strategy-Native Environment** | Simulation setting designed for business strategy (boardroom, negotiation, war room, integration planning) rather than social media platforms. Defines round structure, information visibility rules, and decision mechanisms. |
| **Consulting Archetype** | Pre-defined agent persona based on common consulting stakeholders with structured attributes: role, authority_level, risk_tolerance, information_bias, decision_speed, coalition_tendencies, and incentive_structure. Includes behavioral axioms that guide agent decision-making. |
| **SteerCo** | Steering Committee - executive decision-making body that reviews strategic recommendations |
| **AnalyticsAgent** | Silent monitoring component that extracts quantitative metrics from swarm behavior without interfering with simulation dynamics. Collects compliance violation rates, time-to-consensus, sentiment trajectories, role-based polarization indices, and policy adoption rates. |
| **Consulting Playbook** | Pre-configured simulation template for specific consulting scenarios (M&A culture clash, regulatory shock test, competitive response war game, boardroom decision rehearsal) with defined agent rosters, environment configurations, and expected deliverables. |
| **Client Counterpart Agent** | Specialized agent type that simulates client executive behavior for rehearsing presentations and anticipating objections before SteerCo meetings. |
| **Monte Carlo Confidence Interval** | Statistical method running 20-50 simulation iterations per scenario to establish probability ranges and confidence bounds for outcomes. |
| **LLM Provider** | Backend inference service selected via `LLM_PROVIDER`: cloud/OpenAI-compatible (`openai`, `anthropic`, `google`, `qwen`), local servers (`ollama`, `llamacpp`), or CLI subprocess providers (`cli-claude`, `cli-chatgpt`, `cli-gemini`, `cli-codex`). |
| **BATNA** | Best Alternative To a Negotiated Agreement - fallback option triggered in negotiation scenarios when impasse persists. |
| **Scenario Rehearsal** | ScenarioLab's core positioning: stress-testing strategic decisions in simulated environments rather than predicting future outcomes. |
| **Scenario Matrix** | Deliverable format showing 3-5 scenarios × 4-6 outcomes with probability ranges and confidence intervals. |
| **Risk Register** | Structured deliverable documenting risks with fields: risk_id, description, probability, impact, owner, mitigation, trigger. |
| **Stakeholder Heatmap** | Visual deliverable mapping stakeholders by position, influence, support_level, and key_concerns. |
| **Emergent Behavior** | Unexpected agent behavior patterns that arise from multi-agent interactions, diverging from baseline archetype expectations. |
| **Shapley Values** | Game theory-based metric for attributing outcome explanatory power to individual agents or coalitions; ensures fair attribution where contributions sum to total outcome. |
| **Tornado Chart** | Sensitivity visualization showing which parameters/assumptions have the largest impact on outcomes; bars ranked by impact magnitude resembling tornado shape. |
| **Scenario Branch** | A variant of a base scenario created through Git-like branching; enables systematic exploration of "what-if" alternatives with full version control. |
| **Perturbation Analysis** | Method for detecting bias by running simulations with systematically altered inputs (e.g., gender-flipped names) and comparing outcomes. |
| **Sensitivity Analysis** | Technique to determine how different values of an input variable affect a particular output variable under given assumptions. |
| **Agent Network Graph** | Force-directed visualization where nodes represent agents and edges represent communications or coalitions; edge colors indicate sentiment. |
| **Hallucination Detection** | Automated flagging of agent-generated statements that contradict established facts from seed materials or prior simulation events. |
| **Domain-Specific Fine-Tuning** | Training specialized LLM variants (via LoRA/QLoRA) on domain-specific data (e.g., earnings calls, regulatory testimony) for more authentic agent behaviors. |

### 11.2 References

- [OASIS Repository](https://github.com/camel-ai/oasis)
- [Neo4j Documentation](https://neo4j.com/docs/) — graph database used for GraphRAG and temporal agent memory

---

## 12. Consulting Playbook Templates

### 12.1 M&A Culture Clash Simulation

| Field | Specification |
| ------- | --------------- |
| **Use Case** | Pre-deal cultural integration assessment |
| **Typical Duration** | 10-15 rounds, ~20 minutes |
| **Agent Roster** | Acquirer CEO (1), Target CEO (1), CHROs (2), Business Unit Leaders (4-6), Integration PMO (1), Union Representative (1) |
| **Environment Configuration** | Round structure: Position statements → Cultural values mapping → Integration scenario walkthrough → Red-line negotiation → Resolution vote |
| **Seed Material Template** | Deal thesis (1-2 pages), Organizational charts (both entities), Cultural assessment surveys, Integration timeline, Synergy targets |
| **Expected Deliverables** | Cultural alignment heatmap, integration risk register, stakeholder resistance forecast, decision timeline recommendations |

### 12.2 Regulatory Shock Test

| Field | Specification |
| ------- | --------------- |
| **Use Case** | Assess organizational response to new compliance requirements |
| **Typical Duration** | 8-12 rounds, ~15 minutes |
| **Agent Roster** | CRO (1), Chief Compliance Officer (1), Business Line Heads (3-4), Regulator (1), General Counsel (1), Operations Head (1) |
| **Environment Configuration** | Round structure: Regulatory announcement → Impact assessment → Resource scramble → Compliance plan drafting → Implementation vote |
| **Seed Material Template** | Regulatory text/summary, Current compliance posture, Business impact analysis, Resource constraints, Implementation deadlines |
| **Expected Deliverables** | Compliance violation probability matrix, time-to-remediation forecast, resource allocation recommendations, escalation triggers |

### 12.3 Competitive Response War Game

| Field | Specification |
| ------- | --------------- |
| **Use Case** | Simulate competitor reactions to market entry or pricing move |
| **Typical Duration** | 15-20 rounds, ~25 minutes |
| **Agent Roster** | Your Strategy VP (1), Competitor CEO (1), Competitor CMO (1), Market Analysts (2), Key Customers (2), Industry Observer (1) |
| **Environment Configuration** | Round structure: Market move announcement → Competitive intelligence → Response option generation → War game scenarios → Counter-move selection |
| **Seed Material Template** | Market entry/pricing strategy, Competitor profiles, Market share data, Customer segmentation, Historical competitive responses |
| **Expected Deliverables** | Competitor move probability tree, market share impact scenarios, counter-move recommendations, timing analysis |

### 12.4 Boardroom Decision Rehearsal

| Field | Specification |
| ------- | --------------- |
| **Use Case** | Prepare for high-stakes board presentations |
| **Typical Duration** | 5-10 rounds, ~15 minutes |
| **Agent Roster** | Activist Board Member (1), Institutional Board Member (1), Independent Board Member (2), Board Chair (1), CEO (1), CFO (1), Strategy VP (1) |
| **Environment Configuration** | Round structure: Management presentation → Clarifying questions → Objection round → Rebuttal opportunity → Amendment proposals → Vote |
| **Seed Material Template** | Board deck, Financial projections, Risk assessment, Competitive context, Implementation plan |
| **Expected Deliverables** | Anticipated objection register, response strategy recommendations, approval probability with confidence intervals, amendment forecast |

---

---

## 13. Competitive Landscape

### 13.1 Market Overview

The AI-powered strategic simulation and war-gaming market is experiencing rapid growth, driven by enterprise demand for scenario planning tools and competitive intelligence platforms.

| Market Segment         | 2024 Value | 2033 Projection | CAGR  |
| ---------------------- | ---------- | --------------- | ----- |
| AI Strategy Simulation | $1.62B     | $8.3B           | 19.8% |

### 13.2 Key Competitors

#### Principle ($2M funded, Feb 2026)

- **Positioning:** Pentagon-style corporate wargaming platform
- **Key Features:** Persistent continuously-learning models; custom LLM on AWS Nova for "plausibility classification"
- **Market Position:** "Living strategy" platform targeting enterprise and government
- **Differentiation:** Military-grade simulation heritage; proprietary model training

#### Palantir / Hadean

- **Positioning:** Military-grade wargaming extending to corporate applications
- **Key Features:** Edge deployment architecture; massive-scale simulation capabilities
- **Market Position:** Defense contractor pivoting to commercial markets
- **Differentiation:** Government-grade security; established enterprise relationships

#### McKinsey / BCG / Bain (Internal AI Tools)

- **Positioning:** Embedding AI into existing consulting workflows
- **Key Features:** Proprietary models trained on internal engagement data
- **Market Position:** Internal tools for consultant augmentation
- **Strategic Gap:** NOT building standalone simulation platforms — focused on productivity tools rather than client-facing war-gaming products

#### Strategyzer / Wardley Tools

- **Positioning:** Visual strategy frameworks and mapping tools
- **Key Features:** Business model canvas, Wardley mapping, visual collaboration
- **Market Position:** Strategy visualization and framework tools
- **Strategic Gap:** No agent-based simulation capabilities; static framework tools rather than dynamic behavioral simulation

### 13.3 ScenarioLab Positioning

**Unique Value Proposition:** Open-source, consultant-native, LLM-flexible, MCP-integrated war-gaming platform.

| Dimension | ScenarioLab Advantage |
| ----------- | ------------------- |
| **Open Source** | Community-driven development; transparent methodology; no vendor lock-in |
| **Consultant-Native** | Built by consultants for consultants; playbook templates match actual engagement types |
| **LLM-Flexible** | Supports any LLM provider (cloud or local); future-proof against model obsolescence |
| **MCP-Integrated** | Native CLI/agentic workflow integration; fits existing consultant toolchains |
| **Air-Gap Ready** | Full local deployment option for confidential client engagements |
| **Strategy-Native** | Purpose-built for boardrooms, negotiations, war rooms — not social media simulations |

### 13.4 Competitive Moats

1. **Consulting Playbook Library** - Pre-configured templates for M&A, regulatory shock, competitive response that match actual consulting methodologies
2. **Persona Library with Behavioral Axioms** - Domain-specific agent archetypes (CEO, CFO, regulator) with realistic decision patterns
3. **MCP Ecosystem Integration** - Deep integration with Claude Desktop, Cursor, and IDE workflows that competitors lack
4. **Open Source Community** - Network effects from contributor ecosystem; rapid feature iteration
5. **Air-Gapped Deployment** - Unique capability for confidential financial services and government engagements

### 13.5 Strategic Opportunities

The competitive landscape reveals a significant gap: **no standalone, open-source, consultant-native war-gaming platform exists**. Incumbents either:

- Focus on internal consultant productivity (MBB firms)
- Lack agent-based simulation (Strategyzer/Wardley)
- Are closed-source and expensive (Principle, Palantir)
- Require cloud dependencies that block confidential engagements

ScenarioLab fills this gap by combining open-source accessibility with consulting-grade methodology and enterprise-ready deployment options.

---

Document Version: 3.1

Last Updated: 2026-04-05

**Changelog (3.1):** Aligned stack with the current monorepo: Next.js 16, FastAPI + uv, Neo4j-first graph/memory with SQLite degradation, CLI LLM providers, SQLite report persistence, five-step simulation wizard, and environment-variable table updates.
