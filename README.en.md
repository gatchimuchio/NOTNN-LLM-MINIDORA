# MINIDORA — A Non-Neural Route to LLMs
### What if scaling neural networks is not the only way to build language-model capabilities?

**MINIDORA is a Japanese-first research and implementation project exploring language-model functionality without using neural networks or Transformers as its core.**

Instead of reproducing an existing LLM at smaller scale, MINIDORA revisits the machinery: how a request is represented, how a decision is reached, how evidence is retrieved, and how capabilities can be attached without retraining a huge model.

The ambition is deliberately bold: **build a different foundation for language-model systems, then test it against real tasks.** The evidence is deliberately specific: source code, local tests, historical benchmark runs, and a bounded live Cloud Run demonstration—not a claim of general parity with frontier models.

[日本語正本](README.md) · [Product](製品版/README.en.md) · [Design](設計/README.md) · [Evaluation](評価/README.md) · [Publication policy](PUBLICATION_BOUNDARY.md)

## Why it is different

| Design focus | MINIDORA approach |
|---|---|
| **Non-neural core** | Language processing and system capabilities without NN/Transformer as the core implementation |
| **Capability composition** | Conversation, computation, summarization, extraction, and evidence retrieval outside the core |
| **Evidence-linked answers** | Actual retrieved source text, provenance, and execution traces rather than snippet-only assertions |
| **HDS-governed execution** | Separate request interpretation, action selection, approval, and suspension |
| **Runnable surfaces** | Python application, HTTP API, Google ADK 2.11.0 and a bounded Cloud Run demo |

## Current evidence — as of October 13, 2026

**Keep implementation dates, benchmark dates and deployment revisions separate.**

- **Canonical benchmark run (Sep 27):** GPQA Diamond **40 / 198 (20.20%)**, all 198 questions with LIVE retrieval. This is the canonical historical measurement for the non-neural core, **not a newly measured score for the Oct 1 integrated implementation or subsequent chatbot changes**.
- **Historical capability-module experiment:** MINIDORA80 measured **29 / 198** with modules OFF and **80 / 198** with modules ON in a controlled same-run comparison (net +51 correct, zero within-run regressions). This is a different series, not a replacement for the 40/198 canonical-core result.
- **Working online demo:** Google ADK and Cloud Run returned bounded arithmetic, one sourced explanation from a public webpage, and a follow-up formatting change. HTTP Basic protection, trace agreement, and independently recomputed audit evidence were checked.
- **Not yet established:** general chatbot quality across unseen tasks, renewed GPQA measurement for the latest code, permanent conversational memory, and a general-availability product claim.

The public implementation remains centered on [`src/minidora/`](src/minidora/), with test and evaluation evidence under [`tests/`](tests/) and [`評価/`](評価/). See the [canonical implementation/evaluation distinction](CURRENT_CANONICAL.md).

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
