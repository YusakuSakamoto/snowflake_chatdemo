#!/usr/bin/env python3
"""
Fix Obsidian links in design markdown files.
- Object names with design files: [[OBJECT_NAME]] -> [[design.OBJECT_NAME|OBJECT_NAME]]
- Column names (no design files): [[COLUMN_NAME]] -> `COLUMN_NAME`
- Qualified names: [[SCHEMA.OBJECT]] -> [[design.OBJECT|SCHEMA.OBJECT]] or just SCHEMA.[[design.OBJECT|OBJECT]]
"""
import re
import os
from pathlib import Path

# Design files that exist (from find command output)
EXISTING_DESIGNS = {
    'ANKEN_MEISAI', 'APP_PRODUCTION', 'AZFUNCTIONS_LOGS', 'AZSWA_LOGS',
    'CORTEX_CONVERSATIONS', 'DB_DESIGN', 'DEPARTMENT_MASTER', 'DIM_ENTITY_ALIAS',
    'DIM_ENTITY_ALIAS_MANUAL', 'DOCS_OBSIDIAN', 'DOCS_OBSIDIAN_V',
    'EXPAND_DEPARTMENT_SCOPE_TOOL', 'EXPORT_PROFILE_EVIDENCE_MD_VFINAL',
    'GET_DOCS_BY_PATHS_AGENT', 'INGEST_VAULT_MD', 'LIST_SCHEMA_RELATED_DOC_PATHS_AGENT',
    'LIST_TABLE_RELATED_DOC_PATHS_AGENT', 'LOG', 'NAME_RESOLUTION', 'NORMALIZE_JA',
    'NORMALIZE_JA_DEPT', 'OBSIDIAN_SCHEMA_DB_DESIGN_REVIEW_AGENT', 'OBSIDIAN_VAULT_STAGE',
    'PROFILE_ALL_TABLES', 'PROFILE_COLUMN', 'PROFILE_RESULTS', 'PROFILE_RESULTS_EXTERNAL',
    'PROFILE_RUNS', 'PROFILE_RUNS_EXTERNAL', 'PROFILE_TABLE', 'RAW_DATA',
    'RESOLVE_ENTITY_ALIAS', 'RESOLVE_ENTITY_ALIAS_TOOL', 'SNOWFLAKE_DEMO_AGENT',
    'SNOWFLAKE_METRICS', 'V_CUSTOMER_MASTER', 'V_ENTITY_ALIAS_ALL', 'V_ENTITY_ALIAS_AUTO',
    'V_INVOICE', 'V_ORDER_MASTER', 'V_PROFILE_RESULTS_LATEST', 'V_PROJECT_FACT',
    'V_PROJECT_MASTER',
}

# Column names that should NOT be linked (no design files exist)
COLUMN_NAMES = {
    'CUSTOMER_ID', 'TARGET_DB', 'TARGET_SCHEMA', 'TARGET_TABLE', 'TARGET_COLUMN',
    'RUN_ID', 'CREATED_AT', 'UPDATED_AT', 'ROW_COUNT', 'NULL_COUNT',
    'DISTINCT_COUNT', 'MIN_VALUE', 'MAX_VALUE', 'ENTITY_TYPE', 'ENTITY_NAME',
    'TABLE_NAME', 'COLUMN_NAME', 'DATA_TYPE', 'FILE_PATH', 'LINE_NUMBER',
    'TOTAL_ROWS', 'NULL_RATIO', 'UNIQUE_RATIO',
}


def is_in_code_block(lines, line_idx):
    """Check if line is inside a code block"""
    code_block_count = 0
    for i in range(line_idx):
        if lines[i].strip().startswith('```'):
            code_block_count += 1
    return code_block_count % 2 == 1


def fix_links_in_line(line):
    """Fix Obsidian links in a line"""
    modified = line
    
    # Pattern 1: [[design.OBJECT|OBJECT]] -> [[design.OBJECT]] (simplify)
    # Obsidian automatically shows the alias, so we don't need |OBJECT
    pattern1 = r'\[\[design\.([A-Z_][A-Z0-9_]*)\|[A-Z_][A-Z0-9_]*\]\]'
    modified = re.sub(pattern1, r'[[design.\1]]', modified)
    
    # Pattern 2: SCHEMA.[[design.OBJECT|OBJECT]] -> SCHEMA.[[design.OBJECT]]
    pattern2 = r'([A-Z_]+)\.\[\[design\.([A-Z_][A-Z0-9_]*)\|[A-Z_][A-Z0-9_]*\]\]'
    modified = re.sub(pattern2, r'\1.[[design.\2]]', modified)
    
    # Pattern 3: [[SCHEMA.OBJECT]] -> SCHEMA.[[design.OBJECT]] (if OBJECT has design file)
    pattern3 = r'\[\[([A-Z_]+)\.([A-Z_]+)\]\]'
    def replace3(match):
        schema = match.group(1)
        obj = match.group(2)
        if obj in EXISTING_DESIGNS:
            return f'{schema}.[[design.{obj}]]'
        else:
            # No design file, remove link
            return f'{schema}.{obj}'
    modified = re.sub(pattern3, replace3, modified)
    
    # Pattern 4: [[OBJECT_NAME]] (plain) -> [[design.OBJECT_NAME]] or `COLUMN_NAME`
    pattern4 = r'\[\[([A-Z_][A-Z0-9_]*)\]\]'
    def replace4(match):
        obj = match.group(1)
        if obj in EXISTING_DESIGNS:
            # Has design file
            return f'[[design.{obj}]]'
        elif obj in COLUMN_NAMES:
            # Column name, remove link
            return f'`{obj}`'
        else:
            # Unknown, remove link (likely column or non-existent)
            return f'`{obj}`'
    modified = re.sub(pattern4, replace4, modified)
    
    return modified


def process_file(filepath):
    """Process a single markdown file"""
    with open(filepath, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    modified_lines = []
    changes_made = 0
    
    for idx, line in enumerate(lines):
        # Skip code blocks
        if is_in_code_block(lines, idx):
            modified_lines.append(line)
            continue
        
        # Skip code block markers
        if line.strip().startswith('```'):
            modified_lines.append(line)
            continue
        
        # Fix links
        modified = fix_links_in_line(line)
        if modified != line:
            changes_made += 1
        modified_lines.append(modified)
    
    if changes_made > 0:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.writelines(modified_lines)
        return changes_made
    
    return 0


def main():
    """Process all design markdown files"""
    design_root = Path('/home/yolo/pg/snowflake_chatdemo/docs/snowflake/chatdemo/design')
    
    if not design_root.exists():
        print(f"Error: {design_root} does not exist")
        return
    
    # Find all design.*.md files
    md_files = list(design_root.rglob('design.*.md'))
    
    print(f"Found {len(md_files)} design files")
    print(f"Existing design files: {len(EXISTING_DESIGNS)}")
    print()
    
    total_changes = 0
    modified_files = []
    
    for filepath in sorted(md_files):
        changes = process_file(filepath)
        if changes > 0:
            relative_path = filepath.relative_to(design_root.parent)
            print(f"✓ {relative_path}: {changes} lines modified")
            modified_files.append(str(relative_path))
            total_changes += changes
    
    print()
    print(f"=== Summary ===")
    print(f"Total files processed: {len(md_files)}")
    print(f"Files modified: {len(modified_files)}")
    print(f"Total lines changed: {total_changes}")
    
    if modified_files:
        print()
        print("Modified files:")
        for f in modified_files:
            print(f"  - {f}")


if __name__ == '__main__':
    main()
