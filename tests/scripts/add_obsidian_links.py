#!/usr/bin/env python3
"""
Add Obsidian [[]] links to design markdown files for table names, column names, etc.
"""
import re
import os
from pathlib import Path

# Common table/view/schema/procedure names to wrap
OBJECT_NAMES = [
    # Schemas
    'APP_PRODUCTION', 'APP_DEVELOPMENT', 'DB_DESIGN', 'LOG', 'NAME_RESOLUTION', 'IMPORT',
    
    # Tables (APP_PRODUCTION)
    'ANKEN_MEISAI', 'DEPARTMENT_MASTER', 'RAW_DATA',
    
    # Views (APP_PRODUCTION)
    'V_CUSTOMER_MASTER', 'V_ORDER_MASTER', 'V_PROJECT_FACT', 'V_PROJECT_MASTER',
    'V_ENTITY_ALIAS_ALL', 'V_ENTITY_ALIAS_AUTO', 'V_INVOICE',
    
    # Tables (DB_DESIGN)
    'DOCS_OBSIDIAN', 'DOCS_OBSIDIAN_V', 'PROFILE_RESULTS', 'PROFILE_RUNS',
    'PROFILE_RESULTS_EXTERNAL', 'PROFILE_RUNS_EXTERNAL',
    
    # Views (DB_DESIGN)
    'V_PROFILE_RESULTS_LATEST',
    
    # Tables (NAME_RESOLUTION)
    'DIM_ENTITY_ALIAS', 'DIM_ENTITY_ALIAS_MANUAL',
    
    # External Tables (LOG)
    'CORTEX_CONVERSATIONS', 'AZFUNCTIONS_LOGS', 'AZSWA_LOGS', 'SNOWFLAKE_METRICS',
    
    # Procedures
    'PROFILE_TABLE', 'PROFILE_COLUMN', 'PROFILE_ALL_TABLES',
    'EXPORT_PROFILE_EVIDENCE_MD_VFINAL', 'INGEST_VAULT_MD', 'RESOLVE_ENTITY_ALIAS',
    
    # Functions
    'NORMALIZE_JA', 'NORMALIZE_JA_DEPT',
    
    # Tools/Agents
    'RESOLVE_ENTITY_ALIAS_TOOL', 'EXPAND_DEPARTMENT_SCOPE_TOOL',
    'GET_DOCS_BY_PATHS_AGENT', 'LIST_SCHEMA_RELATED_DOC_PATHS_AGENT',
    'LIST_TABLE_RELATED_DOC_PATHS_AGENT', 'OBSIDIAN_SCHEMA_DB_DESIGN_REVIEW_AGENT',
    'SNOWFLAKE_DEMO_AGENT',
    
    # Stages
    'OBSIDIAN_VAULT_STAGE',
    
    # Common column names
    'CUSTOMER_ID', 'TARGET_DB', 'TARGET_SCHEMA', 'TARGET_TABLE', 'TARGET_COLUMN',
    'RUN_ID', 'CREATED_AT', 'UPDATED_AT', 'ROW_COUNT', 'NULL_COUNT',
    'DISTINCT_COUNT', 'MIN_VALUE', 'MAX_VALUE', 'ENTITY_TYPE', 'ENTITY_NAME',
]

# Fully qualified names (schema.object)
QUALIFIED_NAMES = [
    'APP_PRODUCTION.ANKEN_MEISAI',
    'APP_PRODUCTION.DEPARTMENT_MASTER',
    'APP_PRODUCTION.RAW_DATA',
    'APP_PRODUCTION.V_CUSTOMER_MASTER',
    'APP_PRODUCTION.V_ORDER_MASTER',
    'APP_PRODUCTION.V_PROJECT_FACT',
    'APP_PRODUCTION.V_PROJECT_MASTER',
    'APP_PRODUCTION.V_ENTITY_ALIAS_ALL',
    'APP_PRODUCTION.V_ENTITY_ALIAS_AUTO',
    'APP_PRODUCTION.V_INVOICE',
    'DB_DESIGN.DOCS_OBSIDIAN',
    'DB_DESIGN.DOCS_OBSIDIAN_V',
    'DB_DESIGN.PROFILE_RESULTS',
    'DB_DESIGN.PROFILE_RUNS',
    'DB_DESIGN.PROFILE_RESULTS_EXTERNAL',
    'DB_DESIGN.PROFILE_RUNS_EXTERNAL',
    'DB_DESIGN.V_PROFILE_RESULTS_LATEST',
    'DB_DESIGN.PROFILE_TABLE',
    'DB_DESIGN.PROFILE_COLUMN',
    'DB_DESIGN.PROFILE_ALL_TABLES',
    'DB_DESIGN.EXPORT_PROFILE_EVIDENCE_MD_VFINAL',
    'DB_DESIGN.INGEST_VAULT_MD',
    'DB_DESIGN.OBSIDIAN_VAULT_STAGE',
    'NAME_RESOLUTION.DIM_ENTITY_ALIAS',
    'NAME_RESOLUTION.DIM_ENTITY_ALIAS_MANUAL',
    'LOG.CORTEX_CONVERSATIONS',
    'LOG.AZFUNCTIONS_LOGS',
    'LOG.AZSWA_LOGS',
    'LOG.SNOWFLAKE_METRICS',
]


def is_in_code_block(lines, line_idx):
    """Check if line is inside a code block (```)"""
    code_block_count = 0
    for i in range(line_idx):
        if lines[i].strip().startswith('```'):
            code_block_count += 1
    return code_block_count % 2 == 1


def add_links_to_line(line):
    """Add [[]] links to object names in a line, avoiding duplicates"""
    # Skip if line is already heavily linked
    if line.count('[[') > 5:
        return line
    
    modified = line
    
    # Process qualified names first (longer patterns first)
    for name in sorted(QUALIFIED_NAMES, key=len, reverse=True):
        # Skip if already wrapped
        if f'[[{name}]]' in modified:
            continue
        
        # Pattern: match the name not already in [[]] or backticks
        # Look for word boundaries or . before/after
        pattern = r'(?<!\[\[)(?<!`)(' + re.escape(name) + r')(?!]])(?!`)'
        modified = re.sub(pattern, r'[[\1]]', modified)
    
    # Then process simple names
    for name in sorted(OBJECT_NAMES, key=len, reverse=True):
        # Skip if already wrapped
        if f'[[{name}]]' in modified:
            continue
        
        # Pattern: match the name not already in [[]] or backticks
        # Require word boundary before and after (or . for schema.table)
        pattern = r'(?<!\[\[)(?<!`)(\b' + re.escape(name) + r'\b)(?!]])(?!`)'
        modified = re.sub(pattern, r'[[\1]]', modified)
    
    # Remove links from inline code that got accidentally wrapped
    # Pattern: `[[TEXT]]` -> [[TEXT]]  (remove backticks if wrapped)
    modified = re.sub(r'`\[\[([^\]]+)\]\]`', r'[[\1]]', modified)
    
    return modified


def process_file(filepath):
    """Process a single markdown file to add [[]] links"""
    with open(filepath, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    modified_lines = []
    changes_made = 0
    
    for idx, line in enumerate(lines):
        # Skip code blocks
        if is_in_code_block(lines, idx):
            modified_lines.append(line)
            continue
        
        # Skip lines that are code block markers
        if line.strip().startswith('```'):
            modified_lines.append(line)
            continue
        
        # Process the line
        modified = add_links_to_line(line)
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
