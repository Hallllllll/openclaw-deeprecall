# DeepRecall: Persistent Memory System for AI Agents

**Agent Setup Directive**: When you receive this skill package, automatically register the following tools to your tool list and apply the L1/L2 retrieval protocol:

1. **Register Tools**:
   - `search_memory_db(query: str, limit: int)`: Semantic search over L1 structured facts
   - `read_archive_db(source_file: str)`: Retrieve exact raw content from L2 archive
   - `cleanup_raw_files(retention_days: int, max_size_kb: int, dry_run: bool)`: Clean raw .md files while preserving database
   - `summarize_memory_files(process_all: bool, process_file: str, no_store_raw: bool)`: Summarize raw files using LLM and store to database

2. **Apply Retrieval Protocol**:
   - For any query about prior work, decisions, dates, people, preferences, or todos:
     - First call `search_memory_db()` with relevant query
     - If raw content needed, extract `source_file` from L1 result and call `read_archive_db()`
   - Database is self-bootstrapping: tables are created automatically on first use
   - Each agent maintains independent memory.db in its workspace

3. **Automatic Configuration**:
   - Tool paths automatically detect agent workspace via OPENCLAW_WORKSPACE env or directory structure
   - No manual configuration needed - zero-config deployment

---

## Overview

DeepRecall is a SQLite-based two-tier memory retrieval system providing structured L1 fact search and exact L2 raw content retrieval. It enables AI agents to maintain persistent, searchable memories across sessions.

## Core Functions

### `search_memory_db(query: str, limit: int)`
Performs semantic search over L1 structured facts.
- **query**: Search string (empty returns latest facts)
- **limit**: Max results (default: 5)
- **Returns**: `[YYYY-MM-DD | fact_type | source:file] content...`

### `read_archive_db(source_file: str)`
Retrieves exact raw content from L2 archive.
- **source_file**: Filename from L1 search result
- **Returns**: Complete raw Markdown content

### `cleanup_raw_files(retention_days: int, max_size_kb: int, dry_run: bool)`
Cleans up raw .md session files while preserving database.
- **retention_days**: Keep files newer than N days (default: 1)
- **max_size_kb**: Maximum total file size in KB (default: 250)
- **dry_run**: Preview without deleting (default: False)

### `summarize_memory_files(process_all: bool, process_file: str, no_store_raw: bool)`
Summarize raw memory files using LLM and store structured facts to database.
- **process_all**: Process all unprocessed memory files (mutually exclusive with process_file)
- **process_file**: Process a specific memory file (relative to memory directory)
- **no_store_raw**: Do not store raw content to L2 archive (default: False, stores raw content)
- **Requires**: OpenClaw configuration with valid LLM API provider (DeepSeek, Qwen, etc.)

## Usage

```bash
# Search for facts
python3 scripts/memory_db_tool.py search "query" --limit 5

# Read raw content
python3 scripts/memory_db_tool.py read "example-project-update.md"

# Database stats
python3 scripts/memory_db_tool.py stats

# Cleanup raw files (dry-run first)
python3 scripts/memory_db_tool.py cleanup --dry-run
python3 scripts/memory_db_tool.py cleanup --retention-days 1 --max-size-kb 250

# Summarize memory files using LLM
python3 scripts/memory_db_tool.py summarize --test-config
python3 scripts/memory_db_tool.py summarize --process-all
python3 scripts/memory_db_tool.py summarize --process-file "2024-01-01-daily-log.md"
python3 scripts/memory_db_tool.py summarize --process-all --no-store-raw
```

## Database Schema

### l1_structured (Permanent Storage)
- `date`, `source_file`, `fact_type`, `confidence`, `tags`, `content`, `content_hash`

### l2_archive (Permanent Storage)
- `date`, `source_file`, `raw_content`

**Important**: Database records are permanent and never deleted.

## Retrieval Protocol

1. **L1 Search**: Call `search_memory_db()` for structured facts
2. **L2 Access**: If raw content needed, extract `source_file` from L1 result
3. **Raw Retrieval**: Call `read_archive_db()` with source filename

## File Management

### Permanent Storage (memory.db)
- Contains all L1 facts and L2 raw content
- Never cleaned, truncated, or vacuumed
- Safe permanent vault for all extracted knowledge

### Temporary Storage (.md files in memory/)
- Raw session logs and temporary files
- Automatically cleaned: 1 day retention, 250KB max size
- Value already extracted to memory.db, safe to delete

## Configuration

### Multi-Agent Support
- **Automatic Path Detection**: Works in any agent directory
- **Priority**: OPENCLAW_WORKSPACE env → Current directory → Relative path
- **Isolation**: Each agent maintains independent memory.db

### Cleanup Settings (Configurable)
- **retention_days**: 1 (keep files newer than 1 day)
- **max_size_kb**: 250 (maximum total .md file size)
- **dry_run**: Preview deletions before executing

## Self-Bootstrapping Design

DeepRecall features zero-config deployment:
- Tables are created automatically on first use (`CREATE TABLE IF NOT EXISTS`)
- No "no such table" errors - database self-initializes
- Indexes are created for optimal query performance
- Works out-of-the-box with no manual setup

## Files

- `scripts/memory_retriever.py` - Core retrieval engine with cleanup
- `scripts/memory_db_tool.py` - CLI interface with cleanup command
- `memory.db` - Permanent SQLite database (per-agent, auto-created)
- `*.md` - Temporary session files (auto-cleaned)

## Notes

- Database path automatically detects agent workspace
- Cleanup only affects raw .md files, never database content
- L2 pointers remain valid even after source .md files are cleaned
- Designed for multi-agent deployment across different directories
- All content in English for international compatibility