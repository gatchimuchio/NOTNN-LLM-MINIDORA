# NOTNN-LLM-MINIDORA — MINIDORA

> **A Japanese-first non-neural LLM research and implementation project that separates a minimal language-model core from external capability modules, without using neural networks or Transformers as the core architecture.**

[日本語正本](README.md) / [Hackathon implementation](ハッカソン/README.en.md) / [Design canon](設計/README.md) / [Evaluation evidence](評価/README.md)

> **Language note:** this file is an English translation for international access. The Japanese documents are the normative source of meaning and design.

## Canonical upstream repositories

MINIDORA is not defined in isolation. It is implemented against the following upstream canonical repositories.

| Repository | Responsibility | Relationship to MINIDORA |
|---|---|---|
| [**Cognitive Engineering Foundations**](https://github.com/gatchimuchio/cognitive-engineering-foundations) | Top-level canon for cognitive engineering, language-base policy, HDS, and related theory | Upstream source for theory, semantics, and the Japanese-first foundation |
| [**LLM Constitutive Specification**](https://github.com/gatchimuchio/LLM-Constitutive-Specification) | Defines what constitutes an LLM and the capability-action structure | Normative source for MINIDORA's language-model constitutive conditions and capability structure |

```text
Cognitive Engineering Foundations
    ↓ theory / semantics / language base
LLM Constitutive Specification
    ↓ LLM constitutive conditions / capability structure
MINIDORA
    ↓ implementation / measurement / productization
Hackathon chat layer
```

See [REFERENCES.md](REFERENCES.md) for referenced versions, commits, and responsibility boundaries.

## MINIDORA in 30 seconds

MINIDORA does not aim to keep embedding world knowledge, specialist solvers, and task-specific capabilities into one increasingly large model. It separates responsibilities instead.

```text
MINIDORA Core
├─ non-neural strict language-model core
├─ general capability-model core
├─ general-purpose computation executor
├─ external references
└─ minimal HDS intervention on abnormal states

External Capability Modules
├─ news
├─ summarization
├─ science
├─ coding
└─ other specialist capabilities
```

The project follows three basic principles:

1. **Keep the Core small** — do not endlessly embed world knowledge or specialist solvers into the Core.
2. **Add capabilities as Modules** — extend the system without retraining the established Core.
3. **Trace the response path** — the hackathon layer records why a response was produced as an execution trace rather than generating a post-hoc explanation.

The current package version is **v0.5.0**. The hackathon-specific chat layer is **v0.2**.

## What works today

| Area | Status | Current implementation |
|---|---|---|
| Non-neural language-model Core | Implemented | Complete language-state space, persistent model state, and a coherent language probability law |
| General capability Core | Implemented | General operations over candidates, evidence, relations, and state differences |
| HDS supervision | Implemented | Minimal intervention only for unresolved, conflicting, or under-observed states |
| Capability Modules | Implemented and measured | Controlled replay confirms that external Modules can add effective capability without Core retraining |
| Hackathon chat | v0.2 implemented | Basic chat, news retrieval, summarization of prior context, and delegation to the existing Core |
| Response tracing | v0.2 implemented | Route selection, references, module I/O, conversation state, and final response are chained by hashes |
| Browser UI / Cloud Run | Next stage | Delivery layer planned for the hackathon submission |

## Hackathon demonstration

The demonstration is intentionally simple.

```text
User: What are today's news stories?
MINIDORA: retrieves and presents current news from external references

User: Summarize them.
MINIDORA: summarizes only the news retrieved in the previous turn
```

The dedicated news-to-summary path does not insert free-form generation from an external LLM. It deterministically extracts and compresses already retrieved data.

Each response also receives a `trace_id` and an audit root hash, allowing the actual execution path to be inspected:

```text
input
→ route selection
→ external reference / context reference
→ capability module execution
→ response composition
→ conversation-state update
→ audit root hash
→ previous hash linked into the next response
```

Details: [Hackathon implementation v0.2](ハッカソン/README.en.md)

## Why a Module architecture?

MINIDORA treats the Core and specialist capabilities as different responsibilities.

```text
Core      = general operations
Data      = externalizable
Knowledge = externally referenceable
Module    = specialist capability
Compute   = general computation
HDS       = minimal control on abnormal states
```

In a GPQA Diamond controlled replay on 2026-09-02, existing science-specialist capability Modules were attached to the same saved baseline. The following difference was observed:

| Condition | Correct | Overall accuracy | Accuracy when answered |
|---|---:|---:|---:|
| Module OFF | 8 / 198 | 4.04% | 20.51% |
| Module ON | **63 / 198** | **31.82%** | **73.26%** |

```text
Module activations = 55
Improvements       = 55
Regressions        = 0
Correct-answer gain = +55
```

This **does not claim 63/198 as Core-only performance**. It is evidence that an external capability can be connected to the same Core and that the added capability can appear as a measurable system-level performance difference.

Details:
- [Module extensibility evidence — Japanese](評価/MINIDORA_モジュール拡張成立実証_2026-09-02.md)
- [Capability Module boundary — Japanese](設計/35_MINIDORA_能力Module拡張境界_v1.md)

## Current Core capability

On the 2026-09-01 GPQA Diamond run with specialist solvers excluded from the active path:

```text
Formal MINIDORA general core / HDS off = 19 / 198  (9.60%)
Minimal general Core + HDS supervision = 23 / 198 (11.62%)
```

These numbers are an observation of the current Core. They do **not** show that MINIDORA has performance equivalent to GPT-4 or other frontier models.

The **Large** classification for v0.5 is also subject to **re-audit**; older scale judgments are not automatically inherited.

Details: [GPQA Diamond — Minimal Generic Core, Japanese](評価/GPQA_Diamond_MINIMAL_GENERIC_CORE_2026-09-01.md)

## Quick start

Requirement: Python 3.11+

```bash
python -m pip install -e .
```

MINIDORA Core:

```bash
python -m minidora "2+3"
```

Hackathon chat:

```bash
python -m minidora.ハッカソン
```

Then use the same session:

```text
> 今日のニュースは？
> 要約して
```

Set `MINIDORA_AUDIT_LOG` to append audit records as JSONL. See the [hackathon README](ハッカソン/README.en.md) for details.

## Repository map

For a first visit, read from top to bottom.

| Path | Responsibility |
|---|---|
| [`README.md`](README.md) | Japanese normative public entry point |
| [`README.en.md`](README.en.md) | English translation; subordinate to the Japanese source |
| [`ハッカソン/`](ハッカソン/) | Demo and product-facing hackathon layer |
| [`設計/`](設計/) | Current local design canon |
| [`評価/`](評価/) | Conformance, performance, regression, and measurement evidence |
| [`src/minidora/`](src/minidora/) | Current implementation |
| [`tests/`](tests/) | Unit and regression tests |
| [`docs/`](docs/) | Supporting documents, savepoints, and navigation |
| [`構文化/`](構文化/) | Observation and reconstruction history |
| [`artifacts/`](artifacts/) | Frozen inputs and derived artifacts |
| [`REFERENCES.md`](REFERENCES.md) | Canonical upstream references and relationships |

External upstream repositories:

- [Cognitive Engineering Foundations](https://github.com/gatchimuchio/cognitive-engineering-foundations)
- [LLM Constitutive Specification](https://github.com/gatchimuchio/LLM-Constitutive-Specification)

More navigation: [docs/README.md](docs/README.md)

## Japanese-first language policy

MINIDORA treats **Japanese as its normative language, base language, and internal semantic source of truth**. English is an international translation and compatibility surface, not a parallel semantic authority.

Canonical upstream references:

- Cognitive Engineering Foundations: https://github.com/gatchimuchio/cognitive-engineering-foundations
  - referenced commit: `60131da52ba7931ed7f82c7648a74ac790f50d08`
- LLM Constitutive Specification: https://github.com/gatchimuchio/LLM-Constitutive-Specification
  - version: `2026-08-28-成立規定-8`
  - referenced commit: `fcbc2fa4bc89d749942e8ebee2764115488d29c4`

Details: [REFERENCES.md](REFERENCES.md)

## Claim boundaries

This repository does not collapse the following into one claim:

```text
strict language-model conformance
!= general capability performance
!= GPQA score
!= system performance with Modules
!= Large classification
!= frontier-model performance equivalence
!= product completion
```

Conformance to MINIDORA's adopted constitutive specification, Core capability, Module extensibility, and the hackathon product layer are maintained as separate evidence and evaluation tracks.

## Validation

Standard repository checks:

```bash
python tools/repository_consistency_check.py
python tools/日本語基底監査.py
python -m compileall -q src tests tools
python -m unittest discover -s tests -v
python -m minidora "2+3"
```

CI targets Ubuntu / Windows with Python 3.11–3.14.

## License

Licenses are separated by artifact type.

- Source code and implementation: **Apache License 2.0** — [`LICENSE-APACHE-2.0`](LICENSE-APACHE-2.0)
- Specifications, design, theory, evaluation, README, and other documents: **CC-BY-4.0** — [`LICENSE-CC-BY-4.0`](LICENSE-CC-BY-4.0)
- Scope: [`LICENSE`](LICENSE)
- Attribution and third-party material: [`NOTICE`](NOTICE)

## Author

**がっちむち♂**

MINIDORA keeps its research history, failed paths, current evidence, and Legacy artifacts distinguishable rather than presenting only a polished end state.