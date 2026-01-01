#!/usr/bin/env python3
"""
Fix malformed Obsidian links in design markdown files.
- design.[[design.OBJECT]] → [[design.OBJECT]]
- [[master/path/SCHEMA.[[design.OBJECT]] → [[design.OBJECT]]
"""
import re
import os
from pathlib import Path


def is_in_code_block(lines, line_idx):
    """Check if line is inside a code block"""
    code_block_count = 0
    for i in range(line_idx):
        if lines[i].strip().startswith('```'):
            code_block_count += 1
    return code_block_count % 2 == 1


def fix_links_in_line(line):
    """Fix malformed Obsidian links in a line"""
    modified = line
    
    # Pattern 1: design.[[design.OBJECT]] → [[design.OBJECT]]
    # Remove the prefix "design." before [[design.
    pattern1 = r'design\.\[\[design\.([A-Z_][A-Z0-9_]*)\]\]'
    modified = re.sub(pattern1, r'[[design.\1]]', modified)
    
    # Pattern 2: [[master/path/SCHEMA.[[design.OBJECT]] → [[design.OBJECT]]
    # Remove the broken [[master/ prefix and schema prefix
    pattern2 = r'\[\[master/[^/]+/[A-Z_]+\.\[\[design\.([A-Z_][A-Z0-9_]*)\]\]'
    modified = re.sub(pattern2, r'[[design.\1]]', modified)
    
    # Pattern 3: SCHEMA.[[design.OBJECT]] in text that got prefixed with [[
    # This handles incomplete fixes from previous runs
    pattern3 = r'\[\[[^/\]]*?/[A-Z_]+\.\[\[design\.([A-Z_][A-Z0-9_]*)\]\]'
    modified = re.sub(pattern3, r'[[design.\1]]', modified)
    
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
