# NOTNN-LLM-MINIDORA — MINIDORA

> **A Japanese-first non-neural LLM research and implementation project that separates LLM constitutive requirements and capability effects from today's dominant implementation architecture, then reimplements them without neural networks or Transformers as the core.**

[日本語正本](README.md) / [Product](製品版/README.en.md) / [Design](設計/README.md) / [Evaluation](評価/README.md)

The Japanese documents are the normative source of meaning. The public repository does not publish complete internal-theory definitions or full theory-to-implementation mappings.

## Current status

Current and historical evaluation lines are kept separate.

| Evaluation line | Status | GPQA Diamond |
|---|---|---:|
| Current MINIDORA integrated core | **Current canon** | **40 / 198 (20.20%)** |
| MINIDORA30 | Historical save point | 30 / 198 (15.15%) |
| MINIDORA80 | Historical save point | 80 / 198 (40.40%) |

The current 2026-09-27 canonical run evaluates all 198 GPQA Diamond questions with newly retrieved `LIVE_ONLY` references through `HDS駆動コア.選択実行`. It measured **40 / 198**, with 36 initial inherited correct answers, 40 final correct answers, zero within-run regressions, full final candidate coverage on 198/198 cases, and exactly one problem bundle formation per case.

Frozen reference data, saved search results, and per-problem replay bundles are not used for current canonical performance evaluation. Score differences across separate runs, including paired runs with independent LIVE retrieval, are not treated as code-only causal effects.

MINIDORA80 remains a historical demonstration of the capability-module extension path. Its same-run controlled A/B measured 29 / 198 with modules OFF and 80 / 198 with modules ON, for a +51 correct delta and zero regressions. It is a separate historical line, not the current integrated-core score.

Canonical references:
- [Current canon](CURRENT_CANONICAL.md)
- [Current MINIDORA integrated core 40/198](評価/GPQA_Diamond_MINIDORA_中核_正本_2026-09-27.md)
- [Evaluation contract v3](評価/評価契約_v3.md)
- [Development canon history](開発正本履歴.md)

## Architecture boundary

MINIDORA separates a compact model core from exchangeable capabilities.

```text
model core
├─ non-neural language model
├─ general capabilities
├─ deterministic computation
├─ external references
└─ execution / audit

capability modules
├─ conversation
├─ summarization
├─ extraction
├─ calculation
├─ knowledge reference
└─ additional general or specialist capabilities
```

Adding a capability module is not the same as retraining, fine-tuning, enlarging, or replacing the model core.

## Run

```bash
python -m pip install -e .
python -m minidora.製品版 --HDS --serve
```

Product-only entry:

```bash
python -m minidora.製品版 --serve
```

HTTP:

```text
POST /api/chat
GET  /api/trace/{trace_id}
GET  /api/capabilities
GET  /health
```

## Evaluation boundaries

MINIDORA keeps these separate:

```text
strict language-model conformance
!= reasoning mechanism
!= model-core performance
!= system performance with capability modules
!= product maturity
!= Large classification
```

Historical work logs and obsolete evaluation payloads are not duplicated in the default tree. Canonical development milestones and restore commits are recorded in [開発正本履歴.md](開発正本履歴.md). The `構文化/` corpus is retained as construction input, not treated as disposable work logs.

## Repository

| Path | Responsibility |
|---|---|
| [`src/minidora/`](src/minidora/) | current implementation |
| [`tests/`](tests/) | unit, regression and acceptance tests |
| [`設計/`](設計/) | public local design / compatibility boundaries |
| [`評価/`](評価/) | current canonical and acceptance evidence |
| [`docs/`](docs/) | current supporting documents |
| [`構文化/`](構文化/) | observation / reconstruction history |
| [`製品版/`](製品版/) | product documentation |
| [`artifacts/`](artifacts/) | small fixed artifacts only |

Large benchmark result JSON and frozen reference bundles are kept out of the default tree.

## Japanese-first policy

Japanese is the normative language and internal semantic source of truth. English is an external/publication surface.

## Verification

```bash
python tools/リポジトリ整合性監査.py
python tools/日本語基底監査.py
python tools/日本語基底詳細監査.py
python tools/公開境界監査.py
python -m compileall -q src tests tools
python -m unittest discover -s tests -q
```

## License

- Source code and implementation: **Apache License 2.0** — [LICENSE-APACHE-2.0](LICENSE-APACHE-2.0)
- Specifications, design, evaluation and documentation: **CC-BY-4.0** — [LICENSE-CC-BY-4.0](LICENSE-CC-BY-4.0)
- Scope: [LICENSE](LICENSE)
- Attribution: [NOTICE](NOTICE)

## Author

**がっちむち♂**
