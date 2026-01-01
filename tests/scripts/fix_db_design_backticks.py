#!/usr/bin/env python3
"""DB_DESIGN設計書のバッククォートとハードコードDB名を修正"""
from pathlib import Path
import re

def fix_backticks(content: str) -> tuple[str, int]:
    """バッククォートで囲まれたカラム名・パラメータ名を修正"""
    changes = 0
    
    # パターン1: `COLUMN_NAME` (単独のカラム名/パラメータ名)
    pattern1 = r'`([A-Z_][A-Z0-9_]*)`'
    new_content, count1 = re.subn(pattern1, r'\1', content)
    changes += count1
    
    # パターン2: `column_name` (小文字のパラメータ名)
    pattern2 = r'`([a-z_][a-z0-9_]*)`'
    new_content, count2 = re.subn(pattern2, r'\1', new_content)
    changes += count2
    
    return new_content, changes

def fix_hardcoded_db(content: str) -> tuple[str, int]:
    """ハードコードされたDB名を削除"""
    changes = 0
    
    # パターン: GBPS253YS_DB.DB_DESIGN. -> DB_DESIGN.
    pattern = r'GBPS253YS_DB\.DB_DESIGN\.'
    new_content, count = re.subn(pattern, 'DB_DESIGN.', content)
    changes += count
    
    return new_content, changes

def main():
    design_dir = Path("docs/snowflake/chatdemo/design/DB_DESIGN")
    master_views_dir = Path("docs/snowflake/chatdemo/master/views")
    
    total_changes = 0
    files_changed = 0
    
    print("=== DB_DESIGN設計書の修正 ===\n")
    
    # design/DB_DESIGN/*.md のバッククォート修正
    print("1. design/DB_DESIGN/*.md のバッククォート修正:")
    for md_file in design_dir.glob("*.md"):
        content = md_file.read_text(encoding="utf-8")
        new_content, changes = fix_backticks(content)
        
        if changes > 0:
            md_file.write_text(new_content, encoding="utf-8")
            files_changed += 1
            total_changes += changes
            print(f"  ✓ {md_file.name}: {changes} 箇所")
    
    # master/views/*.md のハードコードDB名修正
    print("\n2. master/views/*.md のハードコードDB名修正:")
    for md_file in master_views_dir.glob("DB_DESIGN.*.md"):
        content = md_file.read_text(encoding="utf-8")
        new_content, changes = fix_hardcoded_db(content)
        
        if changes > 0:
            md_file.write_text(new_content, encoding="utf-8")
            files_changed += 1
            total_changes += changes
            print(f"  ✓ {md_file.name}: {changes} 箇所")
    
    print(f"\n合計: {total_changes} 箇所を修正（{files_changed} ファイル）")

if __name__ == "__main__":
    main()
