# 🧠 DeepRecall for OpenClaw

> **The first full-lifecycle memory management system for AI Agents. Local, SQLite-powered, and LLM-integrated.**

[English](README.md) | [简体中文](README_zh-CN.md)

[![OpenClaw Compatible](https://img.shields.io/badge/OpenClaw-Skill-blue.svg)](#)
[![Local First](https://img.shields.io/badge/Privacy-100%25_Local-success.svg)](#)
[![LLM Summarizer](https://img.shields.io/badge/LLM-Summarizer_Integrated-blueviolet.svg)](#)

DeepRecall is a complete memory OS for OpenClaw that handles **Ingestion (L1/L2), Precise Retrieval, and Context Optimization (Read-and-Burn)**.

## 🔄 The Full Lifecycle Workflow

DeepRecall manages your Agent's memory through three integrated stages:

1.  **Ingestion (Summarizer):**
    - Automatically scans `memory/*.md` files.
    - Uses your preferred LLM via `openclaw.json` to distill raw logs into structured L1 facts.
    - Synchronizes original content to the L2 SQLite archive.
2.  **Retrieval (Engine):**
    - The Agent searches L1 facts via `search_memory_db` to find pointers.
    - If details are needed, it performs a surgical deep dive into L2 via `read_archive_db`.
3.  **Optimization (Read-and-Burn):**
    - Purges temporary raw files post-extraction to keep the context window 100% lean.



## 📸 Execution Trace (Dual-Tier Precision)

> Agent: "Retrieve the Vue sandbox error code from last week."

[0.01s] 🧠 Logic: Scanning L1 facts for "Vue sandbox"...
[0.02s] ⚡️ L1 HIT: [2026-03-06-dead-code.md] contains specific sandbox error.
[0.08s] 🔍 L2 DIVE: Extracting exact code from archive...
[0.09s] 🔥 READ-AND-BURN: Purging "2026-03-06-dead-code.md" from active context.
[0.10s] ✅ Success: Token Savings: ~15,420 tokens.
🚀 Key Features
Multi-LLM Summarizer: Native support for DeepSeek, Qwen, and OpenAI-compatible providers via openclaw.json.

Data Sovereignty: All summaries and archives are stored 100% locally in SQLite.

Auto-Config: Dynamically detects OPENCLAW_WORKSPACE and API settings.

Zero Hallucination: Surgical pointers prevent "Lost in the Middle" errors.

📦 Installation

```bash
clawhub install deeprecall
```

🛠️ Integrated Tools

summarize_memory_files: Triggers the LLM to process raw logs into the DB.

search_memory_db: Semantic/keyword search for L1 facts.

read_archive_db: Precise L2 raw content extraction.

🛡️ Security & Privacy Notice

Permission: This skill requires local file write/delete permissions for the "Read-and-Burn" feature.

Storage: L1 facts are persistent for long-term memory. All data stays 100% on your local machine.

Env Var: The code reads OPENCLAW_WORKSPACE to locate your data automatically.
