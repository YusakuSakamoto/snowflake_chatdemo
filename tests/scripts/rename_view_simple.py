#!/usr/bin/env python3
"""
Simple string replacement for DOCS_OBSIDIAN_V to V_DOCS_OBSIDIAN.
"""
from pathlib import Path

def replace_all_occurrences(content: str) -> tuple[str, int]:
    """Replace all forms of DOCS_OBSIDIAN_V with V_DOCS_OBSIDIAN."""
    changes = 0
    
    replacements = [
        ('[[design.DOCS_OBSIDIAN_V]]', '[[design.V_DOCS_OBSIDIAN]]'),
        ('[[DB_DESIGN.DOCS_OBSIDIAN_V]]', '[[DB_DESIGN.V_DOCS_OBSIDIAN]]'),
        ('DB_DESIGN.DOCS_OBSIDIAN_V', 'DB_DESIGN.V_DOCS_OBSIDIAN'),
        ('# DOCS_OBSIDIAN_V', '# V_DOCS_OBSIDIAN'),
        ('physical: DOCS_OBSIDIAN_V', 'physical: V_DOCS_OBSIDIAN'),
        # These need to be after the above to avoid double replacement
        ('DOCS_OBSIDIAN_V', 'V_DOCS_OBSIDIAN'),
    ]
    
    for old, new in replacements:
        if old in content:
            count = content.count(old)
            content = content.replace(old, new)
            changes += count
    
    return content, changes

def main():
    docs_dir = Path("docs/snowflake/chatdemo")
    total_changes = 0
    files_changed = 0
    
    for md_file in docs_dir.rglob("*.md"):
        content = md_file.read_text(encoding="utf-8")
        new_content, changes = replace_all_occurrences(content)
        
        if changes > 0:
            md_file.write_text(new_content, encoding="utf-8")
            files_changed += 1
            total_changes += changes
            print(f"✓ {md_file.relative_to('docs/snowflake/chatdemo')}: {changes} replacements")
    
    print(f"\n合計: {total_changes} 箇所を修正（{files_changed} ファイル）")

if __name__ == "__main__":
    main()
