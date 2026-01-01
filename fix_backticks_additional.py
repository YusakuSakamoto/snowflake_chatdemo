#!/usr/bin/env python3
"""
Additional backtick removal for remaining cases.
"""
import re
from pathlib import Path

# Terms that are SQL/code identifiers and should NOT have backticks
REMOVE_BACKTICKS = {
    # View columns
    'PATH', 'FOLDER', 'CONTENT', 'RUN_DATE', 'TARGET_SCHEMA', 'TARGET_TABLE', 'TARGET_COLUMN',
    # File format and stage names (uppercase)
    'FF_JSON_LINES', 'STORAGE_INTEGRATION', 'S3_OBSIDIAN_INT',
    'OBSIDIAN_VAULT_SEARCH', 'OBSIDIAN_VAULT_STRUCTURE',
    # Function/system identifiers (uppercase)
    'ARRAY_CAT', 'FLATTEN', 'PARSE_JSON',
    # Column names in context
    'CONTENT_HASH', 'INGEST_RUN_ID', 'ERROR_STATUS', 'ERROR_MESSAGE',
    'METRICS', 'USAGE', 'SELECT', 'WRITE',
    # Procedure names
    'PROFILE_TABLE', 'INGEST_VAULT_MD', 'DOCS_OBSIDIAN',
    # Parameter/variable names (lowercase with underscores)
    'schema_id', 'table_id', 'column_id',
    'target_db', 'run_date', 'vault_prefix',
    'exported_ok', 'exported_failed', 'raw_file_suffix',
    'status', 'row_count', 'null_count', 'null_rate',
    'distinct_count', 'min_varchar', 'max_varchar',
    # Special parameters
    'FILE_TYPE', 'MAX_TABLES', 'MAX_COLUMNS',
    # SQL functions
    'ANY_VALUE',
}

# Terms that should KEEP backticks (sample data, examples)
KEEP_BACKTICKS = {
    # Example data in markdown tables
    'CUSTOMER_ID', 'EMAIL', 'PHONE', 'CUSTOMER_MASTER',
    # Literal string examples
    '"OK"', '_0_0_0',
}

def should_remove_backticks(term: str) -> bool:
    """Check if backticks should be removed from this term."""
    return term in REMOVE_BACKTICKS

def fix_file(content: str) -> tuple[str, int]:
    """Remove backticks from specific terms."""
    changes = 0
    
    for term in REMOVE_BACKTICKS:
        pattern = f'`{term}`'
        if pattern in content:
            # Don't replace if inside a link or if it's a markdown table example
            lines = content.split('\n')
            new_lines = []
            for line in lines:
                # Skip if it's in a markdown table (contains |)
                if pattern in line and '[[' not in line:
                    # Check if it's in a markdown table with example data
                    if '|' in line and any(keep in line for keep in ['%', '0.0%', '1500000']):
                        # This is example data, keep backticks
                        new_lines.append(line)
                    else:
                        count = line.count(pattern)
                        line = line.replace(pattern, term)
                        changes += count
                        new_lines.append(line)
                else:
                    new_lines.append(line)
            content = '\n'.join(new_lines)
    
    return content, changes

def main():
    design_dir = Path("docs/snowflake/chatdemo/design")
    total_changes = 0
    files_changed = 0
    
    for md_file in design_dir.rglob("*.md"):
        content = md_file.read_text(encoding="utf-8")
        new_content, changes = fix_file(content)
        
        if changes > 0 and new_content != content:
            md_file.write_text(new_content, encoding="utf-8")
            files_changed += 1
            total_changes += changes
            print(f"✓ {md_file.relative_to('docs/snowflake/chatdemo')}: {changes} changes")
    
    print(f"\n合計: {total_changes} 箇所を修正（{files_changed} ファイル）")

if __name__ == "__main__":
    main()
