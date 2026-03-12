# 🧠 DeepRecall for OpenClaw

> **A 100% local, SQLite-powered L1/L2 memory engine. Stop vector-search token bloat with a two-tier "Index & Deep Dive" architecture.**

[English](README.md) | [简体中文](README_zh-CN.md)

[![OpenClaw Compatible](https://img.shields.io/badge/OpenClaw-Skill-blue.svg)](#)
[![Local First](https://img.shields.io/badge/Privacy-100%25_Local-success.svg)](#)
[![Zero Config](https://img.shields.io/badge/Setup-Zero_Config-orange.svg)](#)

## 🛑 The Problem

Most memory plugins for AI Agents either rely on cloud SaaS (compromising privacy) or use naive Vector Search that dumps massive chunks of raw Markdown into your context window. This leads to **severe context pollution, high token costs, and LLM hallucination**.

## ⚡️ The Solution: L1/L2 Architecture

DeepRecall brings CPU-style memory caching to LLM Agents:

* **L1 Cache (Structured Facts):** A highly compressed SQLite table storing only distilled facts and file pointers. This acts as your Agent's "daily context" at a fraction of the token cost.
* **L2 Archive (Raw Context):** The complete original conversation/code files. The Agent is strictly instructed to **never** scan L2 directly. It only dives into L2 when it finds an exact `source_file` pointer in L1.
* 🔥 **Read-and-Burn Mechanism:** Once the Agent extracts the specific lines (e.g., an exact code snippet) from the L2 archive, it immediately releases the massive raw file from the active context window.

## 📸 See It In Action (Execution Trace)

Here is a real internal execution trace of an Agent using DeepRecall to cross-reference a bug from a previous week:

> Agent Request: "Find the 3 causes of Vue silent failures, and extract the exact sandbox error code with variable interpolation from last week."

[System] Initiating DeepRecall L1/L2 Retrieval Engine...

[0.02s] ⚡️ L1 CACHE HIT (Structured Facts)
> Tool: search_memory_db(query="Vue silent failure OR sandbox error", limit=5)
  ├─ Fact 1: [2026-03-05 | learnings | pointer: 2026-03-05-vue-render.md] 
  │  Causes: missing setup return, unclosed tags, v-if logic error.
  └─ Fact 2: [2026-03-06 | learnings | pointer: 2026-03-06-dead-code.md] 
     Sandbox validation failed after 3 attempts. (Needs L2 for exact code)

[0.08s] 🔍 L2 ARCHIVE DIVE (Raw Content)
> Tool: read_archive_db(source_file="2026-03-06-dead-code.md")
  └─ Extracting exact lines 215-220...
     Code found: `await self.fail_task(task['id'], f"Sandbox validation failed after 3 attempts. Last error: {stderr[:500]}")`

[0.09s] 🔥 CONTEXT MANAGEMENT
> Action: Read-and-Burn
> Status: Releasing "2026-03-06-dead-code.md" from active context window.
  └─ Token Savings: ~15,420 tokens reclaimed. 

[0.10s] ✅ DeepRecall routine complete. Firing response to user...
🚀 Features

Zero-Config Self-Bootstrapping: Just install the skill. It automatically creates the SQLite database, builds the schema, and maintains its own state.

Extreme Token Efficiency: Formatted to strip out redundant metadata before feeding it to the LLM.

📦 Installation
To install DeepRecall globally into your OpenClaw environment, simply run:

```bash
clawhub install deeprecall
```

🛠️ Tools Registered
Once installed, your Agent automatically gains access to:

search_memory_db(query: str, limit: int) - For L1 semantic and keyword lookups.

read_archive_db(source_file: str) - For precise L2 raw data extraction guided by L1 pointers.

Built with ❤️ for the OpenClaw Community.
