#!/usr/bin/env python3
"""
Comprehensive backtick removal for markdown files.
Handles all types of identifiers that should not be in backticks.
"""
import re
from pathlib import Path
from typing import Tuple

# Master column files
MASTER_COLUMNS = set()

# Technical terms that SHOULD keep backticks
KEEP_BACKTICKS = {
    'logging', 'AUTO_REFRESH', 'metadata$filename', 'FLATTEN', 'GET',
    'HttpTrigger1', 'stream_endpoint', 'snowflake_cortex',
    'INFO', 'WARNING', 'ERROR', 'user', 'assistant',
    'CUSTOMER_SUPPORT_AGENT', 'ARRAY_CAT', 'CUSTOMER_MASTER',
    'FF_JSON_LINES', 'STORAGE_INTEGRATION', 'S3_OBSIDIAN_INT',
    'schema_id', 'table_id', 'column_id',
    'CONTENT_HASH', 'INGEST_RUN_ID', 'ERROR_STATUS', 'ERROR_MESSAGE',
    'OBSIDIAN_VAULT_SEARCH', 'PATHS_JSON', 'MAX_CHARS', 'MAX_COLUMNS',
    'INCLUDE_COLUMNS', 'FILE_TYPE', 'LATEST_RUN', 'SCOPE'
}

def load_master_columns():
    """Load existing master column files."""
    master_col_dir = Path("docs/snowflake/chatdemo/master/columns")
    if master_col_dir.exists():
        for f in master_col_dir.glob("*.md"):
            MASTER_COLUMNS.add(f.stem)

def fix_markdown_content(content: str, file_path: Path) -> Tuple[str, int]:
    """Fix all backtick issues in markdown content."""
    changes = 0
    original = content
    
    # 1. Fix fully qualified column references: SCHEMA.TABLE.`COLUMN` or `SCHEMA.TABLE.COLUMN`
    def fix_qualified_column(match):
        nonlocal changes
        full = match.group(0)
        # Extract components
        parts_match = re.match(r'`?([A-Z_]+)\.([A-Z_]+)\.`?([A-Z_]+)`?', full)
        if parts_match:
            schema, table, column = parts_match.groups()
            full_name = f"{schema}.{table}.{column}"
            if full_name in MASTER_COLUMNS:
                changes += 1
                return f"[[{full_name}]]"
        return full
    
    content = re.sub(
        r'(?<!\[)`?[A-Z_]+\.[A-Z_]+\.`?[A-Z_]+`?(?!\])',
        fix_qualified_column,
        content
    )
    
    # 2. Fix header column names: #### `column_name` (TYPE) -> #### column_name (TYPE)
    def fix_header_column(match):
        nonlocal changes
        changes += 1
        return f"{match.group(1)}{match.group(2)}{match.group(3)}"
    
    content = re.sub(r'(####\s+)`([a-z_]+)`(\s*\()', fix_header_column, content)
    
    # 3. Fix partition column references (year, month, day, hour)
    for col in ['year', 'month', 'day', 'hour']:
        pattern = f'`{col}`'
        if pattern in content:
            # Don't replace if it's in a markdown link or after specific keywords
            lines = content.split('\n')
            new_lines = []
            for line in lines:
                if pattern in line and '[[' not in line:
                    new_count = line.count(pattern)
                    line = line.replace(pattern, col)
                    changes += new_count
                new_lines.append(line)
            content = '\n'.join(new_lines)
    
    # 4. Fix parameter references in specific contexts
    # Pattern: `PARAM_NAME` in headers
    def fix_param_header(match):
        nonlocal changes
        param = match.group(2)
        if param not in KEEP_BACKTICKS:
            changes += 1
            return f"{match.group(1)}{param}"
        return match.group(0)
    
    content = re.sub(r'(####\s+パーティションカラム（)`([^`]+)`', fix_param_header, content)
    
    # 5. Fix simple column references in slashed lists
    # `TARGET_DB` / `TARGET_SCHEMA` / `TARGET_TABLE` / `TARGET_COLUMN`
    # Should become proper links if they exist in master
    def fix_slashed_columns(match):
        nonlocal changes
        columns_text = match.group(0)
        # Extract all column names
        col_pattern = r'`([A-Z_]+)`'
        found_cols = re.findall(col_pattern, columns_text)
        
        # Try to determine schema.table context from surrounding content
        # For now, just remove backticks from known column names
        result = columns_text
        for col in found_cols:
            if col in ['TARGET_DB', 'TARGET_SCHEMA', 'TARGET_TABLE', 'TARGET_COLUMN',
                       'RUN_ID', 'STARTED_AT', 'FINISHED_AT']:
                # These are likely column names, remove backticks
                result = result.replace(f'`{col}`', col)
                changes += 1
        return result
    
    # Pattern: multiple backtick items separated by /
    content = re.sub(
        r'`[A-Z_]+`(?:\s*/\s*`[A-Z_]+`)+',
        fix_slashed_columns,
        content
    )
    
    # 6. Fix uppercase identifiers that look like parameter/column names in lists
    # - `PARAM_NAME`: description
    def fix_list_param(match):
        nonlocal changes
        param = match.group(2)
        if param not in KEEP_BACKTICKS and param.isupper():
            changes += 1
            return f"{match.group(1)}{param}:{match.group(3)}"
        return match.group(0)
    
    content = re.sub(r'(^-\s+)`([A-Z_][A-Z_]+)`(:)', fix_list_param, content, flags=re.MULTILINE)
    
    return content, changes

def main():
    load_master_columns()
    print(f"Loaded {len(MASTER_COLUMNS)} master column definitions\n")
    
    design_dir = Path("docs/snowflake/chatdemo/design")
    total_changes = 0
    files_changed = 0
    
    for md_file in design_dir.rglob("*.md"):
        content = md_file.read_text(encoding="utf-8")
        new_content, changes = fix_markdown_content(content, md_file)
        
        if changes > 0 and new_content != content:
            md_file.write_text(new_content, encoding="utf-8")
            files_changed += 1
            total_changes += changes
            print(f"✓ {md_file.relative_to('docs/snowflake/chatdemo')}: {changes} changes")
    
    print(f"\n合計: {total_changes} 箇所を修正（{files_changed} ファイル）")

if __name__ == "__main__":
    main()
