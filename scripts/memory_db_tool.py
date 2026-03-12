#!/usr/bin/env python3
"""
memory_db_tool.py - Command-line interface for SQLite memory retrieval tools
Provides search_memory_db and read_archive_db functionality via exec calls.
"""

import sys
import os
import json
import argparse
from memory_retriever import MemoryRetriever, retrieve_l1_facts, retrieve_l2_raw, cleanup_raw_files

def search_memory_db(query: str, limit: int = 10) -> str:
    """
    Execute a semantic search over L1 structured facts.
    
    Parameters
    ----------
    query : str
        Search string. Empty string returns the latest facts.
    limit : int, default 10
        Maximum number of results.
        
    Returns
    -------
    str
        Compact formatted facts separated by newlines.
        Format: '[YYYY-MM-DD | fact_type | source:source_file] content...'
        Returns "No matching facts found." if none match.
    """
    retriever = MemoryRetriever()
    facts = retriever.search_l1_structured(query, limit)
    
    if not facts:
        return "No matching facts found."
    
    return "\n".join(facts)

def read_archive_db(source_file: str) -> str:
    """
    Retrieve exact raw content from the L2 archive.
    
    Parameters
    ----------
    source_file : str
        Exact filename as stored in the source_file column.
        
    Returns
    -------
    str
        Complete raw Markdown content.
        If the file is not found, returns an error message.
    """
    retriever = MemoryRetriever()
    content = retriever.get_l2_raw(source_file)
    
    if content is None:
        return f"Source file not found: {source_file}"
    
    return content

def main():
    parser = argparse.ArgumentParser(description="SQLite memory database retrieval tool")
    subparsers = parser.add_subparsers(dest="command", help="Command to execute")
    
    # search command
    search_parser = subparsers.add_parser("search", help="Search L1 structured facts")
    search_parser.add_argument("query", help="Search query (empty for latest)")
    search_parser.add_argument("--limit", type=int, default=5, help="Number of results (default: 5)")
    
    # read command
    read_parser = subparsers.add_parser("read", help="Read L2 raw archive")
    read_parser.add_argument("source_file", help="Source filename (e.g., 'example-project-update.md')")
    
    # stats command
    stats_parser = subparsers.add_parser("stats", help="Show database statistics")
    
    # cleanup command
    cleanup_parser = subparsers.add_parser("cleanup", help="Cleanup raw .md files (preserves database)")
    cleanup_parser.add_argument("--retention-days", type=int, default=1, 
                               help="Keep files newer than N days (default: 1)")
    cleanup_parser.add_argument("--max-size-kb", type=int, default=250,
                               help="Maximum total size in KB (default: 250)")
    cleanup_parser.add_argument("--dry-run", action="store_true",
                               help="Show what would be deleted without actually deleting")
    cleanup_parser.add_argument("--memory-dir", type=str,
                               help="Custom memory directory path (default: auto-detect)")
    
    args = parser.parse_args()
    
    if args.command == "search":
        result = search_memory_db(args.query, args.limit)
        print(result)
    
    elif args.command == "read":
        result = read_archive_db(args.source_file)
        print(result)
    
    elif args.command == "stats":
        retriever = MemoryRetriever()
        stats = retriever.get_table_stats()
        print(json.dumps(stats, indent=2, ensure_ascii=False))
    
    elif args.command == "cleanup":
        print("=== Memory File Cleanup ===\n")
        print("IMPORTANT: This only cleans raw .md session files in workspace/memory/")
        print("           L1/L2 data in memory.db is PERMANENT and will NOT be affected.\n")
        
        if args.dry_run:
            print("DRY RUN MODE: No files will be deleted.\n")
        
        # Execute cleanup (supports dry-run)
        result = cleanup_raw_files(
            retention_days=args.retention_days,
            max_size_kb=args.max_size_kb,
            memory_dir=args.memory_dir,
            dry_run=args.dry_run
        )
        
        # Display results
        print("Cleanup Summary:")
        print(f"  Status: {result.get('status', 'unknown')}")
        
        if result.get('status') in ['skipped', 'dry_run', 'completed']:
            if result.get('reason'):
                print(f"  Reason: {result['reason']}")
            
            print(f"  Memory Directory: {result.get('memory_dir', 'unknown')}")
            print(f"  Config: {result.get('config', {}).get('retention_days', args.retention_days)} day(s), "
                  f"{result.get('config', {}).get('max_size_kb', args.max_size_kb)} KB max")
            
            if 'total_files_before' in result:
                print(f"  Total Files Before: {result['total_files_before']}")
                print(f"  Total Size Before: {result['total_size_before_kb']:.2f} KB")
                print(f"  Files {'to Delete' if args.dry_run else 'Deleted'}: {result['deleted_files_count']}")
                print(f"  Size {'to Free' if args.dry_run else 'Freed'}: {result['deleted_size_kb']:.2f} KB")
                print(f"  Remaining Files: {result['remaining_files_count']}")
                print(f"  Remaining Size: {result['remaining_size_kb']:.2f} KB")
                
                if result.get("deleted_files"):
                    print(f"\n  Files {'that would be deleted' if args.dry_run else 'deleted'}:")
                    for filename in result["deleted_files"][:10]:  # Limit display count
                        print(f"    - {filename}")
                    if len(result["deleted_files"]) > 10:
                        print(f"    ... and {len(result['deleted_files']) - 10} more")
        else:
            print(f"  Error: {result.get('reason', 'Unknown error')}")
    
    else:
        parser.print_help()

if __name__ == "__main__":
    main()