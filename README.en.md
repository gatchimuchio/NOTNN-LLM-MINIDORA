# ⚙️ MINIDORA — Rebuilding LLMs Without a Transformer Core

### Beyond the parameter-scaling race: a different engineering route to language-model capabilities.

**What if making an AI system more capable did not always require retraining or enlarging its model? MINIDORA builds and measures an alternative.**

MINIDORA is not an attempt to make a smaller copy of a neural LLM. It separates **what constitutes a language model**, **what governs decisions**, **where knowledge and computation live**, and **how capabilities can be added**. The core is non-neural and does not use a Transformer; HDS-governed answer selection, deterministic computation, retrieval and replaceable capability modules are composed around it. **What the system can do, why it returned a given answer, and what conditions reproduce it** are central engineering questions.

> **The bet is not on smaller models. It is on a different way of building capabilities.**
> This is no longer only an architecture proposal: source code, benchmark records, a live cloud demonstration and inspectable execution traces exist.

[日本語正本](README.md) · [Implementation](src/minidora/) · [Product](製品版/README.en.md) · [Design](設計/README.md) · [Evaluation](評価/README.md) · [Publication scope](PUBLICATION_BOUNDARY.md)

## What MINIDORA Can Do — Scope of Use

**MINIDORA is more than a non-neural model experiment. It is an extensible execution system connecting conversation, documents, computation, evidence retrieval and specialized capabilities.** Modules can be added without retraining the retained core for that addition.

| Application | Implemented function | Scope |
|---|---|---|
| **Conversation and text** | Basic dialogue, bounded summarization, extraction, formatting and follow-up requests | Supported patterns and retained conversation context |
| **Documents and numbers** | Arithmetic, JSON/CSV-based comparisons and aggregation, limited multi-document comparison and corrections | Supported formats and operations, including the optional general-conversation mode |
| **External evidence** | News, Wikipedia, local search and permitted webpage text, linked to subsequent answers | Provider configuration, permissions and live availability; cloud sources are restricted |
| **Specialist modules** | Register and select trusted scientific, computational or knowledge modules | Explicit module contracts; unrestricted natural-language routing is not claimed |
| **Traceable answers** | Inspect capability selection, execution results, grounds, acceptance, suspension and failure | Depth depends on the recorded path |

Interfaces include Python CLI, local HTTP API, HDS-integrated chat, an optional general-conversation mode and a bounded Google ADK / Cloud Run demonstration. See the [product guide](製品版/README.md).

## Answer Governance — Why This Answer?

**Governance in MINIDORA is not a plausible explanation generated after the fact. It is the ability to inspect the execution path: which evidence and capability were used, what the system did, and how the particular answer was selected.**

The ordinary product-chat path records:

~~~text
Input and current conversation state
  → Candidate capabilities, selected module and version
  → Module input, output, grounds and references
  → Accepted / suspended / failed result, or bounded fallback
  → Response construction and conversation-state update
  → Final answer, Trace ID and audit hash
~~~

In the public Cloud Run demonstration, a question about seaweed beds was answered using actual retrieved webpage text; the response, source and trace were checked. A follow-up formatting request reused the source without another search.

Audit records connect module/version, input/output, grounds and decisions. SHA-256 links events and successive responses. **The aim is to investigate why the answer was produced through the route that actually executed—not to fabricate a narrative about an opaque result.**

The depth of evidence depends on the runtime path. Matching hashes do not independently establish factual truth or guarantee that the answer is correct. See the [product governance contract](製品版/README.md#ガバナンス).

## Determinism — Conditions, Reproduction and Audit

**Determinism does not mean always being correct. It means that with the relevant input, model state, conversation state, reference data, capability versions and execution conditions held fixed, deterministic computation, selection and state transitions can be reproduced.**

The non-neural language-model core uses exact rational (`Fraction`) probability values and fixed tie-breaking for most-likely-symbol selection. Those probabilities describe the model's language distribution; they do not require random sampling to select an answer. A local test checks 100 identical arithmetic inputs for identical responses.

**Deterministic operations make traceability more useful:** differences can be investigated against changes in source material, state, module versions, the selected path or the executed operation.

Live web content may change, retrieval may fail, and sessions may differ. Trace IDs and timestamps are also generated per run. No byte-for-byte identity of external network responses or entire audit logs is implied. Deterministic local processing and environment-dependent behavior are separate.

## The engineering results that matter

| Demonstration | Recorded outcome | What it shows |
|---|---|---|
| **Capability growth without core retraining** | **GPQA Diamond 29/198 OFF → 80/198 ON; +51 net correct, zero regressions** (Sep 9, 2026; same-run LIVE comparison) | Attaching scientific-capability modules increased the system's effective performance without retraining, replacing or enlarging the model core for that addition |
| **A non-neural integrated core, tested separately** | **40/198 (20.20%)** (Sep 27, 2026; all 198 questions, LIVE retrieval) | A separate core-only measurement, with each problem represented once and no external scientific capability modules |
| **Not just a benchmark runner** | Google ADK 2.11.0 / Cloud Run returned arithmetic, evidence-backed web answers and follow-up formatting with matching traces (Oct 13, 2026) | Selected non-neural/HDS chat paths were exercised through a real HTTP deployment |

**The central result is not simply the score change.** It is the observed **mechanism of capability growth**: keep the model core, attach additional capabilities, and measure improvements in end-to-end task performance. In the bounded scientific-question experiment, capability extension was an *actual performance-producing operation*, not merely an extensibility promise.

The historical MINIDORA80 score was **80/198 (40.40%)**. That is in the same roughly 40% numerical band as the **39% GPT-4 baseline reported in the original GPQA paper**. Crucially, the evaluation subset and execution/retrieval conditions are not identical; **this is not a head-to-head win or a claim of overall GPT-4 parity**. Sources: [MINIDORA80 same-run evaluation](評価/GPQA_Diamond_MINIDORA80_Module_E2E_正本_2026-09-09.md) and the [GPQA paper](https://arxiv.org/abs/2311.12022).

## Why the design matters

- **Architecture is not definition.** A dominant Transformer implementation is not automatically the constitutive definition of a language model.
- **A model is not a decision authority.** HDS governs request interpretation, action selection, acceptance and suspension as a distinct responsibility.
- **Capability is not synonymous with model weights.** Computation, evidence retrieval and specialist modules can be composed around a retained core.
- **Claims are tied to execution.** Retrieved page content, trace evidence and explicit failure boundaries matter alongside answer quality.
- **Measurements are version-specific.** Model-core, capability-augmented, integrated-code and cloud-demo results are not interchangeable.

**MINIDORA is an attempt to reopen the engineering design space for LLMs—not merely to compete on parameter count.**

The current integrated implementation dates from Oct 1, 2026, with later basic-chat additions. **Its full 198-question GPQA performance has not been remeasured**; the Sep 27 result is a prior core measurement, and the Sep 9 MINIDORA80 result is a distinct historical capability-augmented series. General chatbot quality, persistent session memory and broad model parity remain unestablished. [Canonical version boundaries](CURRENT_CANONICAL.md).

**Watch it run:** [3-minute recorded cloud demo](https://youtu.be/q7hF26QBabI).

The Japanese text is the normative source of meaning. Public materials include implementation, interface contracts and local evidence—not complete private theory definitions, fixed private references or full theory-to-code mappings. [Publication policy](PUBLICATION_BOUNDARY.md).

---

## Live Cloud Run demonstration

**Video:** [3-minute recorded browser demonstration](https://youtu.be/q7hF26QBabI) (older `a38` revision with authenticated owner access).

**Review endpoint:** [MINIDORA ADK Cloud Run](https://minidora-adk-verify-qp5ojmzmyq-an.a.run.app) (review-only **HTTP Basic authentication**; credentials are not published in this repository).

![MINIDORA public Cloud architecture](docs/minidora-cloud-architecture.png)

The subsequent review revision, `minidora-adk-verify-judge-d2397cc3fc08-7234f7`, added a Basic-protected entry point. For this revision, 19 direct HTTPS checks without owner OIDC and three actual responses were verified. Among them:

| Prompt | Observed outcome |
|---|---|
| `8*9` | `72` — approved |
| `藻場とは何か。` (“What is a seaweed bed?”) | `藻場は海藻が茂る場所です。` — approved with public source text |
| Same conversation: `引用形式にして` (“Put it in quote format”) | A blockquote of the preceding answer — approved, without an additional search |

These are **finite demonstration observations**, not a comprehensive validation of general response quality. The ordinary browser journey from entering Basic credentials to receiving a full chat response was not independently verified for the newer review revision. Session memory is in-process only and does not survive instance replacement. The old video is an edited sequence rather than an uninterrupted screen recording.

The public diagram represents the Basic-protected review design; the video records the older owner-authenticated revision. Details: [Japanese README](README.md), [Cloud Run deployment notes](deploy/CLOUD_RUN.md), and [Product README](製品版/README.md).

## Run locally

```bash
python -m pip install -e .
python -m minidora.製品版 --HDS --serve
```

Alternative product-mode entry: `python -m minidora.製品版 --serve`.

| Endpoint | Purpose |
|---|---|
| `POST /api/chat` | Submit a message |
| `GET /api/trace/{trace_id}` | Retrieve a bounded execution trace |
| `GET /api/capabilities` | Inspect declared capabilities |
| `GET /health` | Health endpoint |

For basic-chat retrieval settings, ADK/Cloud Run deployment, and mode-specific limitations, see [製品版/README.md](製品版/README.md).

## Evaluate and contribute

```bash
python tools/リポジトリ整合性監査.py
python tools/日本語基底監査.py
python tools/日本語基底詳細監査.py
python tools/公開境界監査.py
python -m compileall -q src tests tools
python -m unittest discover -s tests -q
```

The language of normative meaning is Japanese. Read [AGENTS.md](AGENTS.md), [CURRENT_CANONICAL.md](CURRENT_CANONICAL.md), and [PUBLICATION_BOUNDARY.md](PUBLICATION_BOUNDARY.md) before changing the implementation or publishing technical details. Internal theory definitions and complete theory-to-implementation mappings are not part of the public scope.

## Licenses

- **Software, source, tests and tools:** [Apache-2.0](LICENSE-APACHE-2.0)
- **Specifications, designs, evaluation documents and README:** [CC-BY-4.0](LICENSE-CC-BY-4.0)
- [Scope](LICENSE) · [Third-party notices and attribution](NOTICE)

**MINIDORA — the question is not only how large an LLM must be, but what makes its capabilities possible.**
