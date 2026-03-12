#!/usr/bin/env python3
"""
memory_retriever.py - Token-optimized memory retrieval engine for SQLite-based L1/L2 memory system.
Provides compact-format L1 fact search and exact L2 raw-content retrieval.
"""

import sqlite3
import os
import glob
from typing import List, Optional
from datetime import datetime, timedelta

def get_agent_db_path() -> str:
    """
    Dynamically detect the current agent's database path.
    Priority order:
    1. OPENCLAW_WORKSPACE environment variable
    2. Current directory structure detection (looking for memory/ directory)
    3. Fallback to relative path
    """
    # 1. Check framework environment variable
    workspace = os.environ.get("OPENCLAW_WORKSPACE")
    if workspace:
        potential_path = os.path.join(workspace, "memory", "memory.db")
        if os.path.exists(os.path.dirname(potential_path)):
            return potential_path
    
    # 2. Check current directory structure
    cwd = os.getcwd()
    
    # Check for memory/ subdirectory in current directory
    if os.path.exists(os.path.join(cwd, "memory")):
        return os.path.join(cwd, "memory", "memory.db")
    
    # Check if parent directory is an agents structure
    parent = os.path.dirname(cwd)
    if "agents" in parent or "agents" in cwd:
        # Try to find memory in agents directory structure
        for path in [cwd, parent]:
            memory_dir = os.path.join(path, "memory")
            if os.path.exists(memory_dir):
                return os.path.join(memory_dir, "memory.db")
    
    # 3. Fallback to relative path
    return "./memory/memory.db"

def get_workspace_memory_dir() -> str:
    """
    Get workspace/memory directory path for storing raw .md session files.
    Uses the same priority order as database path detection.
    """
    # 1. Check framework environment variable
    workspace = os.environ.get("OPENCLAW_WORKSPACE")
    if workspace:
        memory_dir = os.path.join(workspace, "memory")
        if os.path.exists(memory_dir) or os.path.exists(os.path.dirname(memory_dir)):
            return memory_dir
    
    # 2. Check current directory structure
    cwd = os.getcwd()
    
    # Check for memory/ subdirectory in current directory
    if os.path.exists(os.path.join(cwd, "memory")):
        return os.path.join(cwd, "memory")
    
    # Check if parent directory is an agents structure
    parent = os.path.dirname(cwd)
    if "agents" in parent or "agents" in cwd:
        # Try to find memory in agents directory structure
        for path in [cwd, parent]:
            memory_dir = os.path.join(path, "memory")
            if os.path.exists(memory_dir):
                return memory_dir
    
    # 3. Fallback to relative path
    return "./memory"

class MemoryRetriever:
    def __init__(self, db_path: str = None):
        """
        Initialize the memory retriever.
        
        Parameters
        ----------
        db_path : str, optional
            Database path. If None, auto-detect.
        """
        if db_path is None:
            self.db_path = get_agent_db_path()
        else:
            self.db_path = db_path
        
        # Ensure database directory exists
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        
        # Initialize database tables (self-bootstrapping)
        self._init_db()
    
    def _init_db(self):
        """
        Initialize database tables if they don't exist.
        This ensures zero-config deployment - tables are created automatically.
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Create L1 structured facts table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS l1_structured (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT NOT NULL,
                source_file TEXT NOT NULL,
                fact_type TEXT NOT NULL,
                confidence REAL,
                tags TEXT,
                content_hash TEXT UNIQUE,
                content TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Create L2 raw archive table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS l2_archive (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT NOT NULL,
                source_file TEXT UNIQUE NOT NULL,
                raw_content TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Create indexes for faster queries
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_l1_date ON l1_structured(date)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_l1_type ON l1_structured(fact_type)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_l1_source ON l1_structured(source_file)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_l2_source ON l2_archive(source_file)')
        
        conn.commit()
        conn.close()
    
    def search_l1_structured(self, query: str = None, limit: int = 10) -> List[str]:
        """
        Retrieve L1 structured facts in a compact, token-optimized format.
        
        Parameters
        ----------
        query : str, optional
            Search string. If None or empty, returns the latest facts.
        limit : int, default 10
            Maximum number of results.
            
        Returns
        -------
        List[str]
            Formatted facts: '[YYYY-MM-DD | fact_type | source:source_file] content...'
            No content truncation is applied.
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        if query:
            # Semantic search (vector search can be integrated later)
            sql = '''
                SELECT date, fact_type, source_file, content 
                FROM l1_structured 
                WHERE content LIKE ? OR tags LIKE ?
                ORDER BY confidence DESC, date DESC
                LIMIT ?
            '''
            params = (f'%{query}%', f'%{query}%', limit)
        else:
            # Retrieve latest records
            sql = '''
                SELECT date, fact_type, source_file, content
                FROM l1_structured
                ORDER BY date DESC, confidence DESC
                LIMIT ?
            '''
            params = (limit,)
        
        cursor.execute(sql, params)
        results = cursor.fetchall()
        conn.close()
        
        # Format output - extreme compression (no content truncation)
        formatted = []
        for date, fact_type, source_file, content in results:
            # Clean fact_type: strip prefix, e.g., "project_example-project" -> "project"
            clean_type = fact_type.split('_')[0] if '_' in fact_type else fact_type
            
            # Compact format: [date | type | source:file] content
            # Note: no truncation is applied; content is returned in full
            line = f"[{date} | {clean_type} | source:{source_file}] {content}"
            formatted.append(line)
        
        return formatted
    
    def get_l2_raw(self, source_file: str) -> Optional[str]:
        """
        Retrieve exact raw content from the L2 archive.
        
        Parameters
        ----------
        source_file : str
            Exact filename as stored in the source_file column.
            
        Returns
        -------
        Optional[str]
            Complete raw Markdown content, or None if the file is not found.
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT raw_content FROM l2_archive 
            WHERE source_file = ? 
            LIMIT 1
        ''', (source_file,))
        
        result = cursor.fetchone()
        conn.close()
        
        return result[0] if result else None
    
    def get_table_stats(self) -> dict:
        """Return basic statistics about the memory database."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('SELECT COUNT(*) FROM l1_structured')
        l1_count = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(*) FROM l2_archive')
        l2_count = cursor.fetchone()[0]
        
        cursor.execute('SELECT DISTINCT fact_type FROM l1_structured')
        fact_types = [row[0] for row in cursor.fetchall()]
        
        conn.close()
        
        return {
            'l1_structured_count': l1_count,
            'l2_archive_count': l2_count,
            'fact_types': fact_types
        }

def cleanup_raw_files(retention_days: int = 1, max_size_kb: int = 250, memory_dir: str = None, dry_run: bool = False) -> dict:
    """
    Clean up raw .md session files, keeping recent data and controlling total size.
    
    Important: This function only cleans raw .md files in workspace/memory/ directory,
    and does NOT affect the permanent L1/L2 data in memory.db database.
    
    Parameters
    ----------
    retention_days : int, default 1
        Keep files newer than N days (based on modification time)
    max_size_kb : int, default 250
        Maximum total file size (KB), delete oldest files if exceeds
    memory_dir : str, optional
        Memory directory path, if None auto-detected
    dry_run : bool, default False
        If True, only calculate files to delete without actually deleting
        
    Returns
    -------
    dict
        Cleanup statistics
    """
    if memory_dir is None:
        memory_dir = get_workspace_memory_dir()
    
    # Ensure directory exists
    if not os.path.exists(memory_dir):
        return {"status": "skipped", "reason": f"Directory not found: {memory_dir}"}
    
    # Get all .md files (excluding memory.db)
    md_files = glob.glob(os.path.join(memory_dir, "*.md"))
    
    if not md_files:
        return {"status": "skipped", "reason": "No .md files found"}
    
    # Sort by modification time (oldest to newest)
    files_with_info = []
    for file_path in md_files:
        try:
            stat = os.stat(file_path)
            files_with_info.append({
                "path": file_path,
                "size_kb": stat.st_size / 1024,
                "mtime": stat.st_mtime,
                "date": datetime.fromtimestamp(stat.st_mtime),
                "filename": os.path.basename(file_path)
            })
        except Exception as e:
            continue
    
    # Sort by modification time (oldest to newest)
    files_with_info.sort(key=lambda x: x["mtime"])
    
    total_size_kb = sum(f["size_kb"] for f in files_with_info)
    total_files = len(files_with_info)
    
    # Calculate cutoff time (keep files from last retention_days)
    cutoff_time = datetime.now() - timedelta(days=retention_days)
    cutoff_timestamp = cutoff_time.timestamp()
    
    # First pass cleanup: time-based
    to_delete_time = []
    kept_files = []
    
    for file_info in files_with_info:
        if file_info["mtime"] < cutoff_timestamp:
            to_delete_time.append(file_info)
        else:
            kept_files.append(file_info)
    
    # Second pass cleanup: size-based (if needed)
    remaining_size_kb = sum(f["size_kb"] for f in kept_files)
    to_delete_size = []
    
    if remaining_size_kb > max_size_kb:
        # Delete oldest files until size limit is met
        kept_files.sort(key=lambda x: x["mtime"])  # Ensure chronological order
        
        while kept_files and remaining_size_kb > max_size_kb:
            oldest_file = kept_files.pop(0)
            to_delete_size.append(oldest_file)
            remaining_size_kb -= oldest_file["size_kb"]
    
    # Combine files to delete
    files_to_delete = to_delete_time + to_delete_size
    
    # Execute deletion (unless dry-run)
    deleted_files = []
    deleted_size_kb = 0
    
    if not dry_run:
        for file_info in files_to_delete:
            try:
                os.remove(file_info["path"])
                deleted_files.append(file_info["path"])
                deleted_size_kb += file_info["size_kb"]
            except Exception as e:
                continue
    else:
        # Dry-run mode: only record files that would be deleted
        deleted_files = [f["path"] for f in files_to_delete]
        deleted_size_kb = sum(f["size_kb"] for f in files_to_delete)
    
    # Return cleanup statistics
    return {
        "status": "completed" if not dry_run else "dry_run",
        "memory_dir": memory_dir,
        "total_files_before": total_files,
        "total_size_before_kb": round(total_size_kb, 2),
        "deleted_files_count": len(files_to_delete),
        "deleted_size_kb": round(deleted_size_kb, 2),
        "remaining_files_count": len(kept_files),
        "remaining_size_kb": round(remaining_size_kb, 2),
        "deleted_files": [f["filename"] for f in files_to_delete][:10],  # Limit output length
        "config": {
            "retention_days": retention_days,
            "max_size_kb": max_size_kb,
            "dry_run": dry_run
        }
    }

# Tool functions - for OpenClaw Tool calls
def retrieve_l1_facts(query: str = "", limit: int = 5) -> str:
    """
    Primary entry point for L1 fact retrieval.
    
    Parameters
    ----------
    query : str, default ""
        Search string. Empty string returns the latest facts.
    limit : int, default 5
        Maximum number of results.
        
    Returns
    -------
    str
        Compact formatted facts separated by newlines.
        Format: '[YYYY-MM-DD | fact_type | source:source_file] content...'
        
    Example
    -------
    >>> retrieve_l1_facts("example-project", 2)
    '[2024-01-01 | project | source:example-project.md] example-project backend upgrade...'
    '[2024-01-01 | technical | source:example-project.md] Database model upgrade: Task model adds project_id field...'
    """
    retriever = MemoryRetriever()
    facts = retriever.search_l1_structured(query, limit)
    
    if not facts:
        return "No matching facts found."
    
    # Convert list to compact text block
    return "\n".join(facts)

def retrieve_l2_raw(source_file: str) -> str:
    """
    Primary entry point for L2 raw-content retrieval.
    
    Parameters
    ----------
    source_file : str
        Exact filename as obtained from an L1 search result.
        
    Returns
    -------
    str
        Complete raw Markdown content of the specified file.
        If the file is not found, returns an error message.
    """
    retriever = MemoryRetriever()
    content = retriever.get_l2_raw(source_file)
    
    if content is None:
        return f"Source file not found: {source_file}"
    
    return content

# Example usage and testing
if __name__ == "__main__":
    retriever = MemoryRetriever()
    
    print("=== Database Statistics ===")
    stats = retriever.get_table_stats()
    print(f"L1 facts count: {stats['l1_structured_count']}")
    print(f"L2 files count: {stats['l2_archive_count']}")
    print(f"Fact types: {', '.join(stats['fact_types'][:5])}...")
    
    print("\n=== Auto-Detected Paths ===")
    print(f"Database path: {retriever.db_path}")
    print(f"Memory directory: {get_workspace_memory_dir()}")
    
    print("\n=== L1 Retrieval Test (query 'example-project') ===")
    results = retrieve_l1_facts("example-project", 3)
    print(results)
    
    print("\n=== L1 Retrieval Test (latest records) ===")
    results = retrieve_l1_facts(limit=2)
    print(results)
    
    print("\n=== L2 Retrieval Test ===")
    raw = retrieve_l2_raw("example-project-update.md")
    if raw:
        print(f"Raw file size: {len(raw)} characters")
        print("First 200 characters preview:", raw[:200] + "...")
    else:
        print("File not found")
    
    print("\n=== File Cleanup Test (Dry Run) ===")
    cleanup_result = cleanup_raw_files(retention_days=1, max_size_kb=250, dry_run=True)
    print(f"Cleanup status: {cleanup_result.get('status', 'unknown')}")
    print(f"Files to delete: {cleanup_result.get('deleted_files_count', 0)}")
    print(f"Files to keep: {cleanup_result.get('remaining_files_count', 0)}")