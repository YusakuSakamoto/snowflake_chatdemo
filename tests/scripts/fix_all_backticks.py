#!/usr/bin/env python3
"""
Fix all backtick-wrapped identifiers in markdown files.
Converts:
1. Column names with schema.table prefix: `SCHEMA.TABLE.COLUMN` or SCHEMA.TABLE.`COLUMN` -> [[SCHEMA.TABLE.COLUMN]]
2. Simple column names in headers: #### `column_name` -> #### column_name
3. Partition column references: `year`, `month`, `day`, `hour` -> year, month, day, hour
4. Other technical identifiers (function names, constants) keep backticks
"""
import re
from pathlib import Path
from typing import Tuple

# Master column files that exist
MASTER_COLUMNS = set()

def load_master_columns():
    """Load list of existing master column files."""
    master_col_dir = Path("docs/snowflake/chatdemo/master/columns")
    if master_col_dir.exists():
        for f in master_col_dir.glob("*.md"):
            # Remove .md extension
            col_name = f.stem
            MASTER_COLUMNS.add(col_name)

def should_convert_to_link(identifier: str) -> bool:
    """Check if identifier should be converted to Obsidian link."""
    # Check if it's a fully qualified column name (SCHEMA.TABLE.COLUMN)
    parts = identifier.split('.')
    if len(parts) == 3:
        # Check if master column file exists
        return identifier in MASTER_COLUMNS
    return False

def fix_column_references(content: str) -> Tuple[str, int]:
    """Fix column references with backticks."""
    changes = 0
    
    # Pattern 1: Full column path like DB_DESIGN.PROFILE_RUNS.`RUN_ID` or `DB_DESIGN.PROFILE_RUNS.RUN_ID`
    def replace_full_column(match):
        nonlocal changes
        prefix = match.group(1) or ""
        schema = match.group(2)
        table = match.group(3)
        column = match.group(4)
        full_name = f"{schema}.{table}.{column}"
        
        if should_convert_to_link(full_name):
            changes += 1
            return f"{prefix}[[{full_name}]]"
        return match.group(0)
    
    # Match: SCHEMA.TABLE.`COLUMN` or `SCHEMA.TABLE.COLUMN`
    content = re.sub(
        r'([^\[`])?`?([A-Z_]+)\.([A-Z_]+)\.`?([A-Z_]+)`?(?!\])',
        replace_full_column,
        content
    )
    
    # Pattern 2: Simple column names in specific contexts (TARGET_*, RUN_ID, etc.)
    # Only in specific patterns like: `TARGET_DB` / `TARGET_SCHEMA` / ...
    def replace_simple_column_in_list(match):
        nonlocal changes
        columns = match.group(0)
        # Check if these are actual column names that need linking
        # For now, keep backticks on simple identifiers in slashed lists
        return columns
    
    # Pattern 3: Header column names #### `column_name` -> #### column_name
    def replace_header_column(match):
        nonlocal changes
        prefix = match.group(1)
        col_name = match.group(2)
        suffix = match.group(3)
        changes += 1
        return f"{prefix}{col_name}{suffix}"
    
    content = re.sub(
        r'(####\s+)`([a-z_]+)`(\s*\()',
        replace_header_column,
        content
    )
    
    # Pattern 4: Partition columns year/month/day/hour in backticks -> remove backticks
    partition_cols = ['year', 'month', 'day', 'hour']
    for col in partition_cols:
        old = f'`{col}`'
        if old in content:
            content = content.replace(old, col)
            changes += content.count(old)
    
    return content, changes

def fix_parameter_references(content: str) -> Tuple[str, int]:
    """Fix parameter name backticks in headers and lists."""
    changes = 0
    
    # Pattern 1: Header parameter names #### `PARAM_NAME` -> #### PARAM_NAME
    def replace_header_param(match):
        nonlocal changes
        prefix = match.group(1)
        param = match.group(2)
        changes += 1
        return f"{prefix}{param}"
    
    content = re.sub(
        r'(####\s+)`([A-Z_]+)`',
        replace_header_param,
        content
    )
    
    return content, changes

def smart_fix_file(file_path: Path) -> Tuple[str, int]:
    """Intelligently fix backticks in a markdown file."""
    content = file_path.read_text(encoding="utf-8")
    total_changes = 0
    
    # Fix column references
    content, changes = fix_column_references(content)
    total_changes += changes
    
    # Fix parameter references
    content, changes = fix_parameter_references(content)
    total_changes += changes
    
    return content, total_changes

def main():
    # Load master column list
    load_master_columns()
    print(f"Loaded {len(MASTER_COLUMNS)} master column definitions")
    
    design_dir = Path("docs/snowflake/chatdemo/design")
    total_changes = 0
    files_changed = 0
    
    for md_file in design_dir.rglob("*.md"):
        content = md_file.read_text(encoding="utf-8")
        new_content, changes = smart_fix_file(md_file)
        
        if changes > 0 and new_content != content:
            md_file.write_text(new_content, encoding="utf-8")
            files_changed += 1
            total_changes += changes
            print(f"✓ {md_file.relative_to('docs/snowflake/chatdemo')}: {changes} changes")
    
    print(f"\n合計: {total_changes} 箇所を修正（{files_changed} ファイル）")

if __name__ == "__main__":
    main()
