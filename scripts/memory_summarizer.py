#!/usr/bin/env python3
"""
DeepRecall Memory Summarizer - LLM-powered fact extraction for SQLite L1/L2 memory system.
Integrates with DeepRecall database to store structured facts and raw content.
"""

import os
import json
import re
import hashlib
import asyncio
import aiohttp
import sqlite3
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Any
import sys

# Import DeepRecall's path detection utilities
from memory_retriever import get_agent_db_path, get_workspace_memory_dir

class DeepRecallSummarizer:
    def __init__(self, db_path: str = None):
        """
        Initialize the DeepRecall summarizer.
        
        Parameters
        ----------
        db_path : str, optional
            Database path. If None, auto-detect using DeepRecall's logic.
        """
        if db_path is None:
            self.db_path = get_agent_db_path()
        else:
            self.db_path = db_path
        
        # Ensure database directory exists
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        
        # Get workspace memory directory for raw files
        self.memory_dir = get_workspace_memory_dir()
        
        # Load DeepRecall configuration
        self.config = self._get_deeprecall_config()
        
        # Processing statistics
        self.stats = {
            "files_processed": 0,
            "facts_extracted": 0,
            "facts_stored": 0,
            "raw_content_stored": 0
        }
        
        # LLM extraction prompt template (English version)
        self.extraction_prompt_template = """
You are a professional memory analysis assistant. Your task is to extract key facts from raw memory files and classify them into structured data.

## Input
Raw memory file content provided by the user.

## Output Requirements
Output a JSON array, each element is a fact object in the following format:
```json
[
  {
    "type": "fact_type",
    "content": "Fact content (concise and clear)",
    "confidence": 0.95,
    "tags": ["tag1", "tag2"],
    "project_name": "Optional project name (only when type is project)"
  }
]
```

## Fact Type (type) Definitions
1. **user_profile**: User personal information, preferences, habits, background
2. **identity**: System/assistant identity, role, mission statement
3. **project_[project_name]**: Facts related to specific projects (use underscore, e.g., project_example-project)
4. **technical**: Technical details, code snippets, architecture decisions, configurations
5. **preferences**: System preferences, settings, UI/UX choices, defaults
6. **learnings**: Learning experiences, error analysis, improvement suggestions, lessons
7. **milestones**: Development milestones, important completions, version releases

## Extraction Rules
1. **Conciseness**: Keep each fact content within 1-3 sentences
2. **Specificity**: Include specific names, dates, numbers, technical terms
3. **Deduplication**: Extract the same fact only once
4. **Classification Accuracy**: Choose the most appropriate type based on content
5. **Project Identification**: When content involves a specific project, note the project name in the project_name field

## Example
Input:
"2024-01-01: Completed Japanese textbook summary script today, processed 20 PDF lessons."

Output:
```json
[
  {
    "type": "project_japanese-textbook-summary",
    "content": "2024-01-01: Completed Japanese textbook summary script, processed 20 PDF lessons, generated Word documents.",
    "confidence": 0.9,
    "tags": ["Japanese", "PDF processing", "automation"],
    "project_name": "japanese-textbook-summary"
  }
]
```

Now analyze the following memory content:
"""
    
    def _get_openclaw_config(self) -> Dict:
        """
        Read OpenClaw configuration from openclaw.json.
        Returns model provider configuration.
        """
        try:
            # Try to find openclaw.json in common locations
            possible_paths = [
                Path.home() / ".openclaw" / "openclaw.json",
                Path("/root/.openclaw/openclaw.json"),
                Path.cwd().parent / "openclaw.json",
                Path.cwd() / "openclaw.json"
            ]
            
            config_path = None
            for path in possible_paths:
                if path.exists():
                    config_path = path
                    break
            
            if not config_path:
                print("Warning: OpenClaw configuration not found, using default API endpoint")
                return {}
            
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
            
            return config.get("models", {}).get("providers", {})
            
        except Exception as e:
            print(f"Error reading OpenClaw config: {e}")
            return {}
    
    def _get_deeprecall_config(self) -> Dict:
        """
        Read DeepRecall configuration from config files.
        Returns DeepRecall-specific configuration.
        """
        try:
            # Try to find DeepRecall configuration in common locations
            possible_paths = [
                Path.cwd() / "config.json",
                Path.cwd() / "deeprecall_config.json",
                Path.cwd().parent / "config.json",
                Path(self.memory_dir).parent / "config.json",
                Path.home() / ".deeprecall.json"
            ]
            
            config_path = None
            for path in possible_paths:
                if path.exists():
                    config_path = path
                    print(f"Found DeepRecall config at: {path}")
                    break
            
            if not config_path:
                # Return default configuration
                return {
                    "summarizer": {
                        "preferred_provider": None,  # Auto-select first available
                        "preferred_model": None,     # Auto-select first model
                        "max_content_length": 6000,
                        "temperature": 0.1,
                        "max_tokens": 4000,
                        "timeout_seconds": 180,
                        "store_raw_content": True
                    }
                }
            
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
            
            # Return deeprecall section or full config
            return config.get("deeprecall", config)
            
        except json.JSONDecodeError as e:
            print(f"Warning: Invalid JSON in DeepRecall config: {e}, using defaults")
            return {"summarizer": {}}
        except Exception as e:
            print(f"Warning: Error reading DeepRecall config: {e}, using defaults")
            return {"summarizer": {}}
    
    async def extract_facts_with_llm(self, content: str) -> List[Dict]:
        """
        Extract structured facts from content using LLM API.
        
        Parameters
        ----------
        content : str
            Raw content to analyze
            
        Returns
        -------
        List[Dict]
            List of fact objects
        """
        try:
            # Get API configuration from OpenClaw config
            providers = self._get_openclaw_config()
            
            # Get preferred provider from DeepRecall configuration
            summarizer_config = self.config.get("summarizer", {})
            preferred_provider = summarizer_config.get("preferred_provider")
            preferred_model = summarizer_config.get("preferred_model")
            
            # Select provider based on configuration
            api_config = None
            provider_key = None
            
            if preferred_provider and preferred_provider in providers:
                # Use configured preferred provider
                api_config = providers[preferred_provider]
                provider_key = preferred_provider
                print(f"Using configured preferred provider: {preferred_provider}")
            else:
                # Auto-select first available provider with baseUrl and apiKey
                for name, config in providers.items():
                    if "baseUrl" in config and config.get("apiKey"):
                        api_config = config
                        provider_key = name
                        print(f"Auto-selected provider: {name}")
                        break
            
            if not api_config:
                print("Warning: No LLM API configuration found, using rule-based extraction")
                return await self._extract_facts_with_rules(content)
            
            base_url = api_config.get("baseUrl", "https://api.deepseek.com/v1")
            api_key = api_config.get("apiKey", "")
            
            if not api_key:
                print("Warning: API Key not configured, using rule-based extraction")
                return await self._extract_facts_with_rules(content)
            
            # Get model ID from provider config
            models = api_config.get("models", [])
            model_id = None
            
            if preferred_model:
                # Try to find the preferred model in provider's model list
                for model in models:
                    if model.get("id") == preferred_model:
                        model_id = preferred_model
                        break
            
            # If no preferred model or not found, use first available model
            if not model_id and models and len(models) > 0:
                model_id = models[0].get("id")
            
            if not model_id:
                print("Warning: No model configured in provider, using rule-based extraction")
                return await self._extract_facts_with_rules(content)
            
            # Get configuration parameters
            max_content_length = summarizer_config.get("max_content_length", 6000)
            temperature = summarizer_config.get("temperature", 0.1)
            max_tokens = summarizer_config.get("max_tokens", 4000)
            timeout_seconds = summarizer_config.get("timeout_seconds", 180)
            
            # Build complete prompt with length limit
            full_prompt = self.extraction_prompt_template + "\n" + content[:max_content_length]
            
            # Prepare API request
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {api_key}"
            }
            
            payload = {
                "model": model_id,
                "messages": [
                    {"role": "user", "content": full_prompt}
                ],
                "temperature": temperature,
                "max_tokens": max_tokens,
                "response_format": {"type": "json_object"}
            }
            
            print(f"Calling LLM API to extract facts, content length: {len(content)} characters")
            print(f"API endpoint: {base_url}/chat/completions")
            print(f"Using provider: {provider_key}, model: {model_id}")
            print(f"Configuration: temp={temperature}, max_tokens={max_tokens}, timeout={timeout_seconds}s")
            
            # Send async request with configured timeout
            timeout = aiohttp.ClientTimeout(total=timeout_seconds)
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{base_url}/chat/completions",
                    json=payload,
                    headers=headers,
                    timeout=timeout
                ) as response:
                    
                    if response.status == 200:
                        result = await response.json()
                        response_text = result.get("choices", [{}])[0].get("message", {}).get("content", "")
                        
                        # Parse JSON response
                        try:
                            # Extract JSON part (may contain markdown code blocks)
                            json_match = re.search(r'```json\s*(.*?)\s*```', response_text, re.DOTALL)
                            if json_match:
                                json_str = json_match.group(1)
                            else:
                                # Try to parse entire response
                                json_str = response_text
                            
                            facts = json.loads(json_str)
                            print(f"LLM extraction successful, obtained {len(facts)} facts")
                            return facts
                            
                        except json.JSONDecodeError as e:
                            print(f"LLM response JSON parsing failed: {e}")
                            print(f"Raw response (first 500 chars): {response_text[:500]}")
                            # Fallback to rule extraction
                            return await self._extract_facts_with_rules(content)
                            
                    else:
                        error_text = await response.text()
                        print(f"LLM API error: {response.status} - {error_text[:500]}")
                        # Fallback to rule extraction
                        return await self._extract_facts_with_rules(content)
                        
        except asyncio.TimeoutError:
            print("LLM API call timeout (180 seconds), using rule-based extraction")
            return await self._extract_facts_with_rules(content)
        except Exception as e:
            print(f"LLM API call exception: {type(e).__name__}: {e}")
            import traceback
            traceback.print_exc()
            # Fallback to rule extraction
            return await self._extract_facts_with_rules(content)
    
    async def _extract_facts_with_rules(self, content: str) -> List[Dict]:
        """
        Rule-based extraction fallback method.
        Used when LLM API fails.
        """
        facts = []
        lines = content.split('\n')
        
        # Extract project-related facts (simplified rules)
        project_keywords = ["project", "Project", "example", "Example", "development", "Development"]
        for line in lines:
            if any(keyword in line.lower() for keyword in project_keywords):
                # Try to extract project name
                import re
                project_match = re.search(r'[Pp]roject[:\s]*([\w\s\-]+)', line)
                project_name = "unknown-project"
                if project_match:
                    project_name = project_match.group(1).strip().lower().replace(' ', '-')
                
                facts.append({
                    "type": f"project_{project_name}",
                    "content": line.strip(),
                    "confidence": 0.8,
                    "tags": ["project"],
                    "project_name": project_name
                })
        
        # Extract technical facts
        tech_keywords = ["api", "API", "database", "model", "config", "code", "implementation", "python", "sql"]
        for line in lines:
            if any(keyword in line.lower() for keyword in tech_keywords):
                facts.append({
                    "type": "technical",
                    "content": line.strip(),
                    "confidence": 0.85,
                    "tags": ["technical"]
                })
        
        # Extract learning facts
        learning_keywords = ["learn", "error", "experience", "lesson", "improve", "mistake", "failure"]
        for line in lines:
            if any(keyword in line.lower() for keyword in learning_keywords):
                facts.append({
                    "type": "learnings",
                    "content": line.strip(),
                    "confidence": 0.9,
                    "tags": ["learning"]
                })
        
        # If no facts extracted, add a general fact
        if not facts and content.strip():
            facts.append({
                "type": "learnings",
                "content": content[:200] + ("..." if len(content) > 200 else ""),
                "confidence": 0.7,
                "tags": ["general"]
            })
        
        print(f"Rule-based extraction complete, obtained {len(facts)} facts")
        return facts
    
    def _get_db_connection(self) -> sqlite3.Connection:
        """Get SQLite database connection."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn
    
    def store_fact_to_db(self, fact: Dict, source_file: str, date: str = None) -> bool:
        """
        Store a fact to the L1 structured table in DeepRecall database.
        
        Parameters
        ----------
        fact : Dict
            Fact object with type, content, confidence, tags
        source_file : str
            Source filename (without path)
        date : str, optional
            Date in YYYY-MM-DD format, defaults to today
            
        Returns
        -------
        bool
            True if successful, False otherwise
        """
        try:
            if date is None:
                date = datetime.now().strftime("%Y-%m-%d")
            
            fact_type = fact.get("type", "unknown")
            content = fact.get("content", "")
            confidence = float(fact.get("confidence", 0.0))
            tags_list = fact.get("tags", [])
            tags = ",".join(tags_list) if tags_list else ""
            
            # Generate content hash for deduplication
            content_hash = hashlib.md5(content.encode()).hexdigest()
            
            conn = self._get_db_connection()
            cursor = conn.cursor()
            
            # Check if fact already exists (by content hash)
            cursor.execute(
                "SELECT id FROM l1_structured WHERE content_hash = ?",
                (content_hash,)
            )
            existing = cursor.fetchone()
            
            if existing:
                print(f"  Fact already exists (hash: {content_hash[:8]}), skipping")
                conn.close()
                return False
            
            # Insert new fact
            cursor.execute(
                """
                INSERT INTO l1_structured 
                (date, source_file, fact_type, confidence, tags, content_hash, content)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (date, source_file, fact_type, confidence, tags, content_hash, content)
            )
            
            conn.commit()
            conn.close()
            
            self.stats["facts_stored"] += 1
            return True
            
        except Exception as e:
            print(f"Error storing fact to database: {e}")
            return False
    
    def store_raw_content_to_db(self, source_file: str, content: str, date: str = None) -> bool:
        """
        Store raw content to the L2 archive table in DeepRecall database.
        
        Parameters
        ----------
        source_file : str
            Source filename (without path)
        content : str
            Raw content to store
        date : str, optional
            Date in YYYY-MM-DD format, defaults to today
            
        Returns
        -------
        bool
            True if successful, False otherwise
        """
        try:
            if date is None:
                date = datetime.now().strftime("%Y-%m-%d")
            
            conn = self._get_db_connection()
            cursor = conn.cursor()
            
            # Check if raw content already exists (by source_file)
            cursor.execute(
                "SELECT id FROM l2_archive WHERE source_file = ?",
                (source_file,)
            )
            existing = cursor.fetchone()
            
            if existing:
                print(f"  Raw content already exists for {source_file}, updating")
                cursor.execute(
                    """
                    UPDATE l2_archive 
                    SET raw_content = ?, date = ?
                    WHERE source_file = ?
                    """,
                    (content, date, source_file)
                )
            else:
                # Insert new raw content
                cursor.execute(
                    """
                    INSERT INTO l2_archive 
                    (date, source_file, raw_content)
                    VALUES (?, ?, ?)
                    """,
                    (date, source_file, content)
                )
            
            conn.commit()
            conn.close()
            
            self.stats["raw_content_stored"] += 1
            return True
            
        except Exception as e:
            print(f"Error storing raw content to database: {e}")
            return False
    
    def mark_file_as_processed(self, file_path: Path) -> bool:
        """
        Mark a file as processed by creating a marker file.
        
        Parameters
        ----------
        file_path : Path
            Path to the original file
            
        Returns
        -------
        bool
            True if successful, False otherwise
        """
        try:
            marker_path = file_path.with_suffix(file_path.suffix + ".processed")
            marker_path.write_text(f"Processed at {datetime.now().isoformat()}\n", encoding='utf-8')
            return True
        except Exception as e:
            print(f"Error marking file as processed {file_path}: {e}")
            return False
    
    async def process_single_file(self, file_path: Path, store_raw: bool = True) -> bool:
        """
        Process a single memory file.
        
        Parameters
        ----------
        file_path : Path
            Path to the memory file
        store_raw : bool
            Whether to store raw content to L2 archive
            
        Returns
        -------
        bool
            True if successful, False otherwise
        """
        try:
            if not file_path.exists():
                print(f"  File does not exist: {file_path}")
                return False
            
            file_name = file_path.name
            print(f"Processing file: {file_name}")
            
            # 1. Read content
            content = file_path.read_text(encoding='utf-8', errors='ignore')
            if not content.strip():
                print(f"  File is empty, skipping")
                return False
            
            # 2. Extract date from filename if possible (YYYY-MM-DD pattern)
            date_match = re.search(r'(\d{4}-\d{2}-\d{2})', file_name)
            file_date = date_match.group(1) if date_match else None
            
            # 3. Store raw content to L2 archive (if requested)
            if store_raw:
                self.store_raw_content_to_db(file_name, content, file_date)
            
            # 4. Use LLM to extract facts
            facts = await self.extract_facts_with_llm(content)
            print(f"  Extracted {len(facts)} facts")
            
            # 5. Store facts to L1 structured table
            for fact in facts:
                self.store_fact_to_db(fact, file_name, file_date)
            
            # 6. Mark file as processed
            self.mark_file_as_processed(file_path)
            
            self.stats["files_processed"] += 1
            self.stats["facts_extracted"] += len(facts)
            
            return True
            
        except Exception as e:
            print(f"Error processing file {file_path}: {e}")
            return False
    
    async def process_all_files(self, store_raw: bool = True) -> Dict:
        """
        Process all unprocessed memory files in the memory directory.
        
        Parameters
        ----------
        store_raw : bool
            Whether to store raw content to L2 archive
            
        Returns
        -------
        Dict
            Processing statistics
        """
        print(f"Starting to process all raw memory files in: {self.memory_dir}")
        
        # Find all unprocessed .md files
        unprocessed_files = []
        for file_path in Path(self.memory_dir).rglob("*.md"):
            # Skip already processed files
            marker_path = file_path.with_suffix(file_path.suffix + ".processed")
            if not marker_path.exists():
                unprocessed_files.append(file_path)
        
        print(f"Found {len(unprocessed_files)} unprocessed files")
        
        # Process each file
        for file_path in unprocessed_files:
            await self.process_single_file(file_path, store_raw)
        
        # Print statistics
        print("\n" + "="*60)
        print("Processing Complete - Statistics:")
        print(f"  Files processed:      {self.stats['files_processed']}")
        print(f"  Facts extracted:      {self.stats['facts_extracted']}")
        print(f"  Facts stored to L1:   {self.stats['facts_stored']}")
        print(f"  Raw content stored:   {self.stats['raw_content_stored']}")
        print("="*60)
        
        return self.stats.copy()

def main():
    """Command-line interface for DeepRecall Summarizer."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="DeepRecall Memory Summarizer - LLM-powered fact extraction for SQLite memory system"
    )
    parser.add_argument(
        "--process-all",
        action="store_true",
        help="Process all unprocessed memory files"
    )
    parser.add_argument(
        "--process-file",
        help="Process a specific memory file (relative to memory directory)"
    )
    parser.add_argument(
        "--no-store-raw",
        action="store_true",
        help="Do not store raw content to L2 archive (only extract facts)"
    )
    parser.add_argument(
        "--db-path",
        help="Custom database path (default: auto-detected)"
    )
    parser.add_argument(
        "--memory-dir",
        help="Custom memory directory (default: auto-detected)"
    )
    parser.add_argument(
        "--test-config",
        action="store_true",
        help="Test OpenClaw configuration and API connectivity"
    )
    
    args = parser.parse_args()
    
    # Initialize summarizer
    summarizer = DeepRecallSummarizer(db_path=args.db_path)
    
    print("DeepRecall Memory Summarizer")
    print(f"Database: {summarizer.db_path}")
    print(f"Memory directory: {summarizer.memory_dir}")
    
    if args.test_config:
        # Test configuration
        print("\n=== DeepRecall Configuration Test ===\n")
        
        # Test OpenClaw configuration
        openclaw_config = summarizer._get_openclaw_config()
        print("1. OpenClaw Model Providers:")
        print(f"   Found {len(openclaw_config)} provider(s)")
        
        available_providers = []
        for provider_name, provider_config in openclaw_config.items():
            has_base_url = "baseUrl" in provider_config
            has_api_key = bool(provider_config.get("apiKey"))
            models = provider_config.get("models", [])
            status = "✅ Available" if has_base_url and has_api_key else "⚠️  Incomplete"
            
            print(f"\n   {provider_name}: {status}")
            if has_base_url:
                print(f"      baseUrl: {provider_config.get('baseUrl')}")
            if models:
                print(f"      models: {len(models)} model(s)")
                for model in models[:2]:
                    print(f"        - {model.get('id', 'Unknown')}")
                if len(models) > 2:
                    print(f"        ... and {len(models) - 2} more")
            
            if has_base_url and has_api_key:
                available_providers.append(provider_name)
        
        # Test DeepRecall configuration
        print("\n2. DeepRecall Summarizer Configuration:")
        deeprecall_config = summarizer.config.get("summarizer", {})
        
        if deeprecall_config:
            print("   ✅ Custom configuration loaded")
            for key, value in deeprecall_config.items():
                print(f"      {key}: {value}")
        else:
            print("   ℹ️  Using default configuration")
        
        # Show provider selection logic
        print("\n3. Provider Selection Logic:")
        if available_providers:
            preferred = deeprecall_config.get("preferred_provider")
            if preferred:
                if preferred in available_providers:
                    print(f"   ✅ Will use configured provider: {preferred}")
                else:
                    print(f"   ⚠️  Configured provider '{preferred}' not available")
                    print(f"   ⚠️  Will auto-select from: {available_providers}")
            else:
                print(f"   ℹ️  No preferred provider configured")
                print(f"   ℹ️  Will auto-select from: {available_providers}")
            
            # Show what would be selected
            if preferred and preferred in available_providers:
                selected = preferred
            elif available_providers:
                selected = available_providers[0]
            else:
                selected = None
            
            if selected:
                print(f"   📍 Selected provider would be: {selected}")
        else:
            print("   ❌ No available providers found")
            print("   ⚠️  Summarizer will use rule-based extraction")
        
        print("\n=== Configuration Test Complete ===")
    
    elif args.process_all:
        # Process all files
        store_raw = not args.no_store_raw
        print(f"\nProcessing all files (store_raw: {store_raw})...")
        import asyncio
        stats = asyncio.run(summarizer.process_all_files(store_raw=store_raw))
        
        # Save statistics to file
        stats_file = Path(summarizer.memory_dir) / "summarizer_stats.json"
        with open(stats_file, 'w', encoding='utf-8') as f:
            json.dump(stats, f, indent=2)
        print(f"Statistics saved to: {stats_file}")
    
    elif args.process_file:
        # Process single file
        store_raw = not args.no_store_raw
        file_path = Path(args.process_file)
        
        if not file_path.is_absolute():
            # Assume relative to memory directory
            file_path = Path(summarizer.memory_dir) / file_path
        
        print(f"\nProcessing single file: {file_path} (store_raw: {store_raw})...")
        import asyncio
        success = asyncio.run(summarizer.process_single_file(file_path, store_raw))
        
        if success:
            print(f"File processed successfully")
        else:
            print(f"File processing failed")
            sys.exit(1)
    
    else:
        # Show help
        print("\nAvailable commands:")
        print("  --process-all       Process all unprocessed memory files")
        print("  --process-file      Process a specific memory file")
        print("  --no-store-raw      Do not store raw content (only facts)")
        print("  --test-config       Test OpenClaw configuration")
        print("\nExamples:")
        print("  python3 memory_summarizer.py --process-all")
        print("  python3 memory_summarizer.py --process-file 2024-01-01-daily-log.md")
        print("  python3 memory_summarizer.py --test-config")

if __name__ == "__main__":
    main()