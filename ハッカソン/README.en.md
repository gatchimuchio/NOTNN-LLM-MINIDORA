# MINIDORA Hackathon Implementation v0.2

[日本語正本](README.md) / [Public MINIDORA README](../README.en.md)

> **The hackathon demo uses a short “What are today's news stories? → Summarize them” interaction to show MINIDORA's external references, conversation state, capability modules, and response traceability as one product behavior.**

This directory records the operational boundary for the hackathon submission and demonstration. The implementation lives under [`../src/minidora/ハッカソン/`](../src/minidora/ハッカソン/) and is connected as a capability layer without rewriting the existing MINIDORA Core.

> This file is an English translation for international access. The Japanese version is the normative source.

## What the demo is intended to show

The point is not news summarization by itself.

```text
user input
↓
select the required capability path
↓
retrieve external data
↓
retain it in conversation state
↓
reuse the same data for the next instruction
↓
fix the actual response path into an audit record
```

The demo therefore aims to show a **minimal usable chat-AI flow whose response path can be inspected as execution evidence**.

## Demo scenario

```text
> 今日のニュースは？

MINIDORA
- retrieves current news from external references
- retains the source identifiers
- stores the retrieved items in conversation state
- returns a news list

> 要約して

MINIDORA
- reuses the previous news from conversation state
- extracts and compresses only the retrieved data
- does not add facts outside the referenced material
- returns the summary
```

The dedicated news-to-summary path does not use free-form generation from an external LLM.

## v0.2 implemented scope

- Minimal basic chat
- Delegation of general questions to the existing MINIDORA Core
- Current-news retrieval through RSS
- Same-session “today's news → summarize” flow
- Deterministic extractive summarization of explicitly supplied text
- A `trace_id` and audit root hash for each response
- Recording of input acceptance, route selection, external references, context references, capability execution, response composition, and conversation-state updates
- SHA-256 hash chaining for stage-level tamper detection
- Linking the previous response's trace ID and root hash into the next response's audit chain
- When the existing MINIDORA Core exposes execution records, capturing `result / references / history / decision / language plan / HDS_IR`
- Optional append-only JSONL audit persistence

## Response governance

“Why did MINIDORA produce this response?” is not answered by asking the AI to generate a retrospective explanation.

**The actual execution path is recorded directly.**

```text
input accepted
↓
route selected
↓
external reference / context reference
↓
capability execution
↓
response composition
↓
conversation-state update
↓
audit root hash
↓
previous hash linked into the next response
```

### Recorded information

Representative audit fields include:

- input text
- session ID
- route-selection conditions and rule
- referenced news items, identifiers, and sources
- module and module version
- module input and output
- conversation-state references and updates
- exposed MINIDORA Core execution records when delegated
- final response
- final response state
- stage hashes and root hash

When a general question is delegated to the existing MINIDORA Core, the public execution result, references, history, decision, and HDS_IR are included in the same audit chain.

If an alternative connected component does not expose an execution-record API, the trace boundary is explicitly marked as the **module boundary**; it is not represented as internally fully traced.

## Tamper detection and persistence

Each audit event includes the previous event hash before being hashed with SHA-256. A root hash is finalized with the final response, and overwriting an existing trace ID is rejected.

Set `MINIDORA_AUDIT_LOG` to append one JSON record per response with `flush + fsync`.

```bash
MINIDORA_AUDIT_LOG=.audit/minidora_hackathon.jsonl python -m minidora.ハッカソン
```

Windows PowerShell:

```powershell
$env:MINIDORA_AUDIT_LOG = ".audit/minidora_hackathon.jsonl"
python -m minidora.ハッカソン
```

This JSONL mode is append-oriented but does not make the operating-system file itself WORM storage. A product deployment can connect the same audit record to Cloud Logging, a database, object locking, signatures, or an external anchor.

## Local run

Requirement: Python 3.11+

```bash
python -m pip install -e .
python -m minidora.ハッカソン
```

In the same session:

```text
> 今日のニュースは？
> 要約して
```

Each response prints a `trace_id` and `trace_hash`.

Library users can inspect `ハッカソンチャット.監査台帳.取得(trace_id)` and call `検証(trace_id)` to verify the execution path and hash chain.

## Modules

| Implementation | Responsibility |
|---|---|
| `チャット.py` | Capability routing, delegation to the existing MINIDORA Core, audit connection |
| `ニュース.py` | RSS external references and current-news extraction |
| `要約.py` | Deterministic extractive summarization without free-form generation |
| `会話状態.py` | Session history, previous-news retention, removal of stale news context |
| `基本会話.py` | Minimal greetings and capability description |
| `ガバナンス.py` | Execution ledger, stage hashes, root hash, JSONL append persistence |
| `型.py` | Types for news, responses, and audit records |

## Validation

Repository-wide checks:

```bash
python tools/repository_consistency_check.py
python tools/日本語基底監査.py
python -m compileall -q src tests tools
python -m unittest discover -s tests -v
```

The hackathon tests inject a fixed news provider instead of external RSS and reproducibly cover:

- news-to-summary context connection
- trace-ID and audit-hash continuity across responses
- delegation to the base Core
- explicit-text summarization
- basic chat
- removal of stale news context after another route is used
- JSONL audit append
- hash-chain verification for each response

## Delivery layer not implemented yet

v0.2 establishes the chat Core and governance boundary first. The following delivery and presentation layers are next-stage work:

- browser chat UI
- Cloud Run delivery boundary
- Gemini comparison view
- Cloud Logging / database / WORM-equivalent external audit persistence
- signature or external anchor for audit roots
- Trace visualization in the response UI

These items are **not** presented as already implemented.

## Japanese-first policy

The hackathon layer follows MINIDORA's Japanese-first semantic policy. [`README.md`](README.md) is the normative version; this English file is a translation for international presentation.