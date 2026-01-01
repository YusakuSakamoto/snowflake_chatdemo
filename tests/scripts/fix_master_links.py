#!/usr/bin/env python3
"""
Fix Obsidian links: Use [[SCHEMA.OBJECT]] for master file references,
keep [[design.OBJECT]] only for design document references.
"""
import re
from pathlib import Path


# Master files that exist (schema.object format)
MASTER_FILES = {
    # Tables
    'APP_PRODUCTION.ANKEN_MEISAI',
    'APP_PRODUCTION.DEPARTMENT_MASTER',
    'DB_DESIGN.DOCS_OBSIDIAN',
    'DB_DESIGN.PROFILE_RESULTS',
    'DB_DESIGN.PROFILE_RUNS',
    'NAME_RESOLUTION.DIM_ENTITY_ALIAS',
    'NAME_RESOLUTION.DIM_ENTITY_ALIAS_MANUAL',
    
    # Views
    'APP_PRODUCTION.V_CUSTOMER_MASTER',
    'APP_PRODUCTION.V_ENTITY_ALIAS_ALL',
    'APP_PRODUCTION.V_ENTITY_ALIAS_AUTO',
    'APP_PRODUCTION.V_INVOICE',
    'APP_PRODUCTION.V_ORDER_MASTER',
    'APP_PRODUCTION.V_PROJECT_FACT',
    'APP_PRODUCTION.V_PROJECT_MASTER',
    'DB_DESIGN.DOCS_OBSIDIAN_V',
    'DB_DESIGN.V_PROFILE_RESULTS_LATEST',
    
    # Procedures/Functions/Tools (other)
    'APP_PRODUCTION.EXPAND_DEPARTMENT_SCOPE_TOOL',
    'APP_PRODUCTION.NORMALIZE_JA',
    'APP_PRODUCTION.NORMALIZE_JA_DEPT',
    'APP_PRODUCTION.RAW_DATA',
    'APP_PRODUCTION.RESOLVE_ENTITY_ALIAS',
    'APP_PRODUCTION.RESOLVE_ENTITY_ALIAS_TOOL',
    'APP_PRODUCTION.SNOWFLAKE_DEMO_AGENT',
    'DB_DESIGN.EXPORT_PROFILE_EVIDENCE_MD_VFINAL',
    'DB_DESIGN.GET_DOCS_BY_PATHS_AGENT',
    'DB_DESIGN.INGEST_VAULT_MD',
    'DB_DESIGN.LIST_SCHEMA_RELATED_DOC_PATHS_AGENT',
    'DB_DESIGN.LIST_TABLE_RELATED_DOC_PATHS_AGENT',
    'DB_DESIGN.OBSIDIAN_SCHEMA_DB_DESIGN_REVIEW_AGENT',
    'DB_DESIGN.OBSIDIAN_VAULT_STAGE',
    'DB_DESIGN.PROFILE_ALL_TABLES',
    'DB_DESIGN.PROFILE_COLUMN',
    'DB_DESIGN.PROFILE_TABLE',
    
    # External tables
    'DB_DESIGN.PROFILE_RESULTS_EXTERNAL',
    'DB_DESIGN.PROFILE_RUNS_EXTERNAL',
    'LOG.AZFUNCTIONS_LOGS',
    'LOG.AZSWA_LOGS',
    'LOG.CORTEX_CONVERSATIONS',
    'LOG.SNOWFLAKE_METRICS',
}

# Extract object names from master files
MASTER_OBJECTS = {name.split('.', 1)[1] for name in MASTER_FILES}


def is_in_code_block(lines, line_idx):
    """Check if line is inside a code block"""
    code_block_count = 0
    for i in range(line_idx):
        if lines[i].strip().startswith('```'):
            code_block_count += 1
    return code_block_count % 2 == 1


def is_design_context(line):
    """Check if the line is referencing design/intent, not the entity itself"""
    design_keywords = [
        '設計方針',
        '設計思想',
        '設計判断',
        '設計上の',
        '詳細は',
        '設計：',
        'の設計',
    ]
    return any(keyword in line for keyword in design_keywords)


def fix_links_in_line(line):
    """Fix links: plain SCHEMA.OBJECT -> [[SCHEMA.OBJECT]] for master references"""
    modified = line
    
    # Skip if this line is about design philosophy/intent
    if is_design_context(line):
        return modified
    
    # Pattern: plain SCHEMA.OBJECT (not linked) -> [[SCHEMA.OBJECT]] (link to master)
    # Only convert if master file exists
    for master_file in sorted(MASTER_FILES, key=len, reverse=True):
        # Pattern: SCHEMA.OBJECT not already in [[]]
        pattern = r'(?<!\[\[)(?<!\.)' + re.escape(master_file) + r'(?!\]\])(?!\.)'
        
        def replace(match):
            # Don't replace if it's already part of a link or code
            return f'[[{master_file}]]'
        
        modified = re.sub(pattern, replace, modified)
    
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
        
        # Skip if line starts with # (headers)
        if line.strip().startswith('#'):
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
    print(f"Master files available: {len(MASTER_FILES)}")
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
