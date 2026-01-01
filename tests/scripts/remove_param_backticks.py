#!/usr/bin/env python3
"""
Remove backticks from parameter names in markdown files.
Converts `P_PARAM` to P_PARAM in table rows and list items.
"""
import re
from pathlib import Path

def remove_param_backticks(content: str) -> tuple[str, int]:
    """Remove backticks from parameter names."""
    changes = 0
    
    # Pattern 1: Table rows with `P_PARAM` format
    # Example: | `P_TARGET_DB` | STRING | ✅ | - |
    def replace_table_param(match):
        nonlocal changes
        changes += 1
        return f"| {match.group(1)} |"
    
    content = re.sub(r'\|\s*`(P_[A-Z_]+)`\s*\|', replace_table_param, content)
    
    # Pattern 2: List items with - P_PARAM: format (without backticks)
    # These are already correct, just verify
    
    # Pattern 3: Inline backticks around parameters in explanatory text
    # Example: - `P_SAMPLE_PCT`: PROFILE_TABLEから受け渡され
    def replace_list_param(match):
        nonlocal changes
        changes += 1
        return f"- {match.group(1)}:"
    
    content = re.sub(r'^-\s*`(P_[A-Z_]+)`:', replace_list_param, content, flags=re.MULTILINE)
    
    return content, changes

def main():
    design_dir = Path("docs/snowflake/chatdemo/design")
    total_changes = 0
    files_changed = 0
    
    for md_file in design_dir.rglob("*.md"):
        content = md_file.read_text(encoding="utf-8")
        new_content, changes = remove_param_backticks(content)
        
        if changes > 0:
            md_file.write_text(new_content, encoding="utf-8")
            files_changed += 1
            total_changes += changes
            print(f"✓ {md_file.relative_to('docs/snowflake/chatdemo')}: {changes} changes")
    
    print(f"\n合計: {total_changes} 箇所を修正（{files_changed} ファイル）")

if __name__ == "__main__":
    main()
