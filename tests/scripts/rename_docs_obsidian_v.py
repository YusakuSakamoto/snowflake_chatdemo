#!/usr/bin/env python3
"""
Rename DOCS_OBSIDIAN_V to V_DOCS_OBSIDIAN throughout all files.
"""
import re
from pathlib import Path

def rename_view_references(content: str) -> tuple[str, int]:
    """Replace all references to DOCS_OBSIDIAN_V with V_DOCS_OBSIDIAN."""
    changes = 0
    
    # Pattern 1: [[design.DOCS_OBSIDIAN_V]] -> [[design.V_DOCS_OBSIDIAN]]
    pattern1 = r'\[\[design\.DOCS_OBSIDIAN_V\]\]'
    if re.search(pattern1, content):
        content = re.sub(pattern1, '[[design.V_DOCS_OBSIDIAN]]', content)
        changes += len(re.findall(pattern1, content))
    
    # Pattern 2: [[DB_DESIGN.DOCS_OBSIDIAN_V]] -> [[DB_DESIGN.V_DOCS_OBSIDIAN]]
    pattern2 = r'\[\[DB_DESIGN\.DOCS_OBSIDIAN_V\]\]'
    if re.search(pattern2, content):
        content = re.sub(pattern2, '[[DB_DESIGN.V_DOCS_OBSIDIAN]]', content)
        changes += len(re.findall(pattern2, content))
    
    # Pattern 3: Plain text DOCS_OBSIDIAN_V (not in links)
    # DB_DESIGN.DOCS_OBSIDIAN_V -> DB_DESIGN.V_DOCS_OBSIDIAN
    pattern3 = r'DB_DESIGN\.DOCS_OBSIDIAN_V(?!\])'
    if re.search(pattern3, content):
        content = re.sub(pattern3, 'DB_DESIGN.V_DOCS_OBSIDIAN', content)
        changes += len(re.findall(pattern3, content))
    
    # Pattern 4: Just DOCS_OBSIDIAN_V (not in links, not after DB_DESIGN.)
    pattern4 = r'(?<!DB_DESIGN\.)(?<!\[\[design\.)DOCS_OBSIDIAN_V(?!\])'
    if re.search(pattern4, content):
        content = re.sub(pattern4, 'V_DOCS_OBSIDIAN', content)
        changes += len(re.findall(pattern4, content))
    
    # Pattern 5: # DOCS_OBSIDIAN_V (header) -> # V_DOCS_OBSIDIAN
    pattern5 = r'^# DOCS_OBSIDIAN_V$'
    if re.search(pattern5, content, re.MULTILINE):
        content = re.sub(pattern5, '# V_DOCS_OBSIDIAN', content, flags=re.MULTILINE)
        changes += len(re.findall(pattern5, content, re.MULTILINE))
    
    # Pattern 6: physical: DOCS_OBSIDIAN_V -> physical: V_DOCS_OBSIDIAN
    pattern6 = r'physical: DOCS_OBSIDIAN_V'
    if pattern6 in content:
        content = content.replace(pattern6, 'physical: V_DOCS_OBSIDIAN')
        changes += content.count(pattern6)
    
    return content, changes

def main():
    docs_dir = Path("docs/snowflake/chatdemo")
    total_changes = 0
    files_changed = 0
    
    for md_file in docs_dir.rglob("*.md"):
        content = md_file.read_text(encoding="utf-8")
        new_content, changes = rename_view_references(content)
        
        if changes > 0 and new_content != content:
            md_file.write_text(new_content, encoding="utf-8")
            files_changed += 1
            total_changes += changes
            print(f"✓ {md_file.relative_to('docs/snowflake/chatdemo')}: {changes} changes")
    
    print(f"\n合計: {total_changes} 箇所を修正（{files_changed} ファイル）")

if __name__ == "__main__":
    main()
