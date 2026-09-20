# NOTNN-LLM-MINIDORA — MINIDORA

> **A Japanese-first non-neural LLM research and implementation project that separates a minimal language-model 模型核 from exchangeable capability 能力モジュールs, without using neural networks or Transformers as the core architecture.**

[日本語正本](README.md) / [Product Prototype](製品版/README.en.md) / [Design canon](設計/README.md) / [Evaluation evidence](評価/README.md)

> This file is an English translation for international access. The Japanese documents are the normative source of meaning and design.


## Current GPQA canon — 模型核 30 / System with 能力モジュールs 80

Since 2026-09-09, canonical GPQA performance runs forbid frozen reference data and use newly retrieved `LIVE_ONLY` references.

| Layer | Canon | GPQA Diamond | Meaning |
|---|---|---:|---|
| 模型核 / HDS | **MINIDORA30** | **30 / 198 (15.15%)** | current general E2E 模型核 savepoint |
| 模型核 + scientific 能力モジュールs | **MINIDORA80** | **80 / 198 (40.40%)** | current system-capability savepoint |

In the same-run LIVE controlled A/B that established MINIDORA80:

```text
能力モジュール OFF = 29 / 198 (14.65%)
能力モジュール ON  = 80 / 198 (40.40%)
net correct gain = +51
能力モジュール activations = 55
correct 能力モジュール activations = 55
improvements = 51
regressions = 0
```

> **On the limited axis of GPQA score, MINIDORA + scientific 能力モジュールs reached the same roughly-40% score range as the strongest GPT-4-based baseline reported by the original GPQA paper (39%).**

MINIDORA80 is numerically above 39%, but the original GPT-4 result and this GPQA Diamond LIVE E2E run do not use identical subsets or execution conditions. This is therefore a **same-score-band statement, not a claim of overall GPT-4 capability equivalence**.

## Public specification boundary

Internal theory references, fixed upstream commits, and complete theory-to-implementation mappings are not published in this repository.
Public documentation is limited to interfaces, implementation behavior, tests, limitations, and evaluation evidence.

## Product Prototype v1

The hackathon demonstration is "today's news → summarize it", but the implementation is not a news-only demo. The product layer adds a common Capability contract and 登録簿 around the established MINIDORA 模型核.

Implemented capabilities include:

- basic chat;
- RSS news retrieval;
- grounded summarization from the retrieved reference bodies;
- explicit-text summarization;
- context transformation;
- information extraction;
- deterministic calculation;
- Wikipedia knowledge reference;
- delegation to the existing MINIDORA 模型核 when no specialist 能力モジュール applies;
- session-範囲d conversation state;
- end-to-end execution tracing;
- a browser UI and HTTP API.

Run:

```bash
python -m pip install -e .
python -m minidora.製品版 --serve
```

Open `http://localhost:8080/`.

API:

```text
POST /api/chat
GET  /api/trace/{trace_id}
GET  /api/capabilities
GET  /health
```

## Capability growth

Every capability 能力モジュール follows a common contract: **name / version / priority / applicability decision / execution**. New capabilities can be registered without retraining the established 模型核.

The current LIVE GPQA Diamond same-run controlled A/B measured 能力モジュール OFF **29/198 (14.65%)** → 能力モジュール ON **80/198 (40.40%)**, with 55 能力モジュール activations, 55 correct activations, 51 net improvements, and 0 regressions. The earlier 8/198 → 63/198 frozen replay remains historical evidence only. This is **not claimed as 模型核-only performance**; it is evidence that external capability 能力モジュールs can create measurable system-level capability gains without retraining the established 模型核.

The Product Prototype adds `tools/製品能力モジュール実証.py` so the same OFF/ON structure can also be measured on everyday, non-benchmark-specific tasks. Formal values should be taken from execution on the actual current MINIDORA 模型核.

## Governance

MINIDORA records the actual execution path rather than asking a generative model to invent a post-hoc explanation.

```text
input
→ capability candidates
→ 能力モジュール selection
→ 能力モジュール I/O and references
→ optional 模型核 代替経路
→ response composition
→ conversation-state update
→ root hash
→ previous response hash linked to the next response
```

Audit events are chained with SHA-256. This provides tamper detection, not immutable WORM storage or cryptographic signing. Production WORM/signature/external anchoring remains a deployment-layer responsibility.

## Performance target

A **GPT-4-class general chat experience** remains a development target. MINIDORA80 has reached the same roughly-40% GPQA score band as the original GPT-4-based baseline, but this is not a general capability equivalence claim. Progress should be measured through real-use capabilities such as conversation continuity, summarization, knowledge reference, comparison, reasoning, calculation, transformation, search, and coding as 能力モジュールs are added.

Current canonical GPQA savepoints:

```text
MINIDORA30 模型核 E2E LIVE              = 30 / 198 (15.15%)
MINIDORA80 模型核 + scientific 能力モジュールs  = 80 / 198 (40.40%)
```

The v0.5 **Large** classification remains subject to **re-audit**; older scale judgments are not automatically inherited.

## Japanese-first policy

MINIDORA treats Japanese as its normative language, base language, and internal semantic source of truth.

- LLM Constitutive Specification version: `2026-08-28-成立規定-8`
- LLM Constitutive Specification referenced commit: `fcbc2fa4bc89d749942e8ebee2764115488d29c4`

## Claim boundaries

```text
strict language-model conformance
!= 模型核 general capability
!= GPQA score
!= system performance with 能力モジュールs
!= Product Prototype maturity
!= Large classification
GPQA same score band as GPT-4 baseline
!= overall GPT-4 capability equivalence
```

## License

- Source code and implementation: **Apache License 2.0** — [`LICENSE-APACHE-2.0`](LICENSE-APACHE-2.0)
- Specifications, design, theory, evaluation, README and other documents: **CC-BY-4.0** — [`LICENSE-CC-BY-4.0`](LICENSE-CC-BY-4.0)
- Scope: [`LICENSE`](LICENSE)
- Attribution and third-party material: [`NOTICE`](NOTICE)

## Author

**がっちむち♂**
