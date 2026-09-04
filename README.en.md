# NOTNN-LLM-MINIDORA — MINIDORA

> **A Japanese-first non-neural LLM research and implementation project that separates a minimal language-model Core from exchangeable capability Modules, without using neural networks or Transformers as the core architecture.**

[日本語正本](README.md) / [Product Prototype](製品版/README.en.md) / [Design canon](設計/README.md) / [Evaluation evidence](評価/README.md)

> This file is an English translation for international access. The Japanese documents are the normative source of meaning and design.

## Canonical upstream repositories

- [**Cognitive Engineering Foundations**](https://github.com/gatchimuchio/cognitive-engineering-foundations) — top-level cognitive-engineering, language-base, and HDS canon.
- [**LLM Constitutive Specification**](https://github.com/gatchimuchio/LLM-Constitutive-Specification) — constitutive requirements for language-model formation and capability-action structure.

```text
Cognitive Engineering Foundations
        ↓
LLM Constitutive Specification
        ↓
MINIDORA Core
        ↓ exchangeable Capability Modules
MINIDORA Product Prototype
```

## Product Prototype v1

The hackathon demonstration is "today's news → summarize it", but the implementation is not a news-only demo. The product layer adds a common Capability contract and registry around the established MINIDORA Core.

Implemented capabilities include:

- basic chat;
- RSS news retrieval;
- grounded summarization from the retrieved reference bodies;
- explicit-text summarization;
- context transformation;
- information extraction;
- deterministic calculation;
- Wikipedia knowledge reference;
- delegation to the existing MINIDORA Core when no specialist Module applies;
- session-scoped conversation state;
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

Every capability Module follows a common contract: **name / version / priority / applicability decision / execution**. New capabilities can be registered without retraining the established Core.

The prior GPQA Diamond controlled replay measured a Module OFF → ON change from **8/198 to 63/198**, with 55 Module activations, 55 improvements, and 0 regressions. This is **not claimed as Core-only performance**; it is evidence that external capability Modules can create measurable system-level capability gains.

The Product Prototype adds `tools/製品能力Module実証.py` so the same OFF/ON structure can also be measured on everyday, non-benchmark-specific tasks. Formal values should be taken from execution on the actual current MINIDORA Core.

## Governance

MINIDORA records the actual execution path rather than asking a generative model to invent a post-hoc explanation.

```text
input
→ capability candidates
→ Module selection
→ Module I/O and references
→ optional Core fallback
→ response composition
→ conversation-state update
→ root hash
→ previous response hash linked to the next response
```

Audit events are chained with SHA-256. This provides tamper detection, not immutable WORM storage or cryptographic signing. Production WORM/signature/external anchoring remains a deployment-layer responsibility.

## Performance target

A **GPT-4-class general chat experience** is a development target, not a current equivalence claim. Progress should be measured through real-use capabilities such as conversation continuity, summarization, knowledge reference, comparison, reasoning, calculation, transformation, search, and coding as Modules are added.

Current Core GPQA observation with specialist solvers excluded from the active path:

```text
Formal MINIDORA general Core / HDS off = 19 / 198  (9.60%)
Minimal general Core + HDS supervision = 23 / 198 (11.62%)
```

The v0.5 **Large** classification remains subject to **re-audit**; older scale judgments are not automatically inherited.

## Japanese-first policy

MINIDORA treats Japanese as its normative language, base language, and internal semantic source of truth.

- Cognitive Engineering Foundations referenced commit: `60131da52ba7931ed7f82c7648a74ac790f50d08`
- LLM Constitutive Specification version: `2026-08-28-成立規定-8`
- LLM Constitutive Specification referenced commit: `fcbc2fa4bc89d749942e8ebee2764115488d29c4`

## Claim boundaries

```text
strict language-model conformance
!= Core general capability
!= GPQA score
!= system performance with Modules
!= Product Prototype maturity
!= Large classification
!= GPT-4-class performance achieved
```

## License

- Source code and implementation: **Apache License 2.0** — [`LICENSE-APACHE-2.0`](LICENSE-APACHE-2.0)
- Specifications, design, theory, evaluation, README and other documents: **CC-BY-4.0** — [`LICENSE-CC-BY-4.0`](LICENSE-CC-BY-4.0)
- Scope: [`LICENSE`](LICENSE)
- Attribution and third-party material: [`NOTICE`](NOTICE)

## Author

**がっちむち♂**
