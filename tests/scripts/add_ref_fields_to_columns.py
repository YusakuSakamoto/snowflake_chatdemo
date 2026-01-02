#!/usr/bin/env python3
"""全カラム定義ファイルに ref_table_id, ref_column, ref_cardinality フィールドを追加"""
from pathlib import Path
import re

def process_file(content: str) -> tuple[str, bool]:
    """YAMLフロントマターに ref_* フィールドを追加"""
    
    # 既に ref_table_id がある場合はスキップ
    if "ref_table_id:" in content:
        return content, False
    
    # YAML frontmatter のパターン
    yaml_pattern = r'^---\n(.*?)\n---'
    match = re.search(yaml_pattern, content, re.DOTALL)
    
    if not match:
        return content, False
    
    yaml_content = match.group(1)
    
    # pk: の後に ref_* フィールドを挿入
    # pk: が存在する場合
    if "pk:" in yaml_content:
        new_yaml = re.sub(
            r'(pk: (?:true|false)\n)',
            r'\1ref_table_id:\nref_column:\nref_cardinality:\n',
            yaml_content
        )
    # pk: が存在しない場合、domain: の後に挿入
    elif "domain:" in yaml_content:
        new_yaml = re.sub(
            r'(domain: \w+\n)',
            r'\1pk: false\nref_table_id:\nref_column:\nref_cardinality:\n',
            yaml_content
        )
    else:
        return content, False
    
    new_content = content.replace(yaml_content, new_yaml)
    return new_content, True

def main():
    columns_dir = Path("docs/snowflake/chatdemo/master/columns")
    total_changes = 0
    files_changed = 0
    
    for md_file in sorted(columns_dir.glob("*.md")):
        content = md_file.read_text(encoding="utf-8")
        new_content, changed = process_file(content)
        
        if changed:
            md_file.write_text(new_content, encoding="utf-8")
            files_changed += 1
            total_changes += 1
            print(f"✓ {md_file.name}")
    
    print(f"\n合計: {total_changes} ファイルを更新")

if __name__ == "__main__":
    main()
