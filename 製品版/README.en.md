# MINIDORA Product Prototype v1

This is not a thin hackathon mock. It is a product-oriented chat layer built by attaching everyday capability modules to the established MINIDORA Core without retraining the Core.

The Japanese document is the normative source. This English file is a translation for international access.

## Goals
- provide a usable chat-AI product surface;
- demonstrate news retrieval followed by grounded summarization;
- demonstrate capability growth outside benchmark-specific tasks through pluggable Modules;
- keep the actual response path traceable by construction;
- aim toward a GPT-4-class general chat experience as a development target, not as a current equivalence claim.

## Architecture

```text
Browser / API Client
        ↓
MINIDORA Product Chat
        ↓
Capability Registry
 ├─ Basic Chat
 ├─ News Retrieval
 ├─ Summarization
 ├─ Context Transformation
 ├─ Information Extraction
 ├─ Deterministic Calculation
 ├─ Knowledge Reference
 └─ Existing MINIDORA Core
        ↓
Governance Ledger
```

Each capability Module exposes a common contract: name, version, priority, applicability decision, and execution. New capabilities can be registered without retraining the Core.

## Run

```bash
python -m pip install -e .
python -m minidora.製品版 --serve
```

Open `http://localhost:8080/`.
