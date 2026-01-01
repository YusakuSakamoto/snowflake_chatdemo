#!/usr/bin/env python3
"""
Final comprehensive fix for all backtick issues.
"""
import re
from pathlib import Path

def fix_file_content(content: str, filepath: Path) -> tuple[str, int]:
    """Fix all backtick issues comprehensively."""
    changes = 0
    original_content = content
    
    # 1. Remove backticks from TARGET_* when not in links
    # `TARGET_SCHEMA`, `TARGET_TABLE`, `TARGET_COLUMN` -> TARGET_SCHEMA, TARGET_TABLE, TARGET_COLUMN
    for term in ['TARGET_SCHEMA', 'TARGET_TABLE', 'TARGET_COLUMN', 'TARGET_DB',
                 'INCLUDE_COLUMNS', 'MAX_COLUMNS', 'FILE_TYPE', 'SCOPE',
                 'PATHS_JSON', 'MAX_CHARS', 'RUN_ID', 'LATEST_RUN']:
        pattern = f'`{term}`'
        if pattern in content:
            # Don't replace if already in a link [[...]]
            lines = content.split('\n')
            new_lines = []
            for line in lines:
                if pattern in line and '[[' not in line:
                    count = line.count(pattern)
                    line = line.replace(pattern, term)
                    changes += count
                new_lines.append(line)
            content = '\n'.join(new_lines)
    
    # 2. Remove backticks from simple identifiers in context like: design.<`SCHEMA`>.md
    pattern = r'<`([A-Z_]+)`>'
    if re.search(pattern, content):
        content = re.sub(pattern, r'<\1>', content)
        changes += len(re.findall(pattern, original_content))
    
    # 3. Remove backticks from partition columns
    for col in ['year', 'month', 'day', 'hour']:
        pattern = f'`{col}`'
        if pattern in content:
            count = content.count(pattern)
            content = content.replace(pattern, col)
            changes += count
    
    # 4. Remove backticks from header column names: #### `column_name` (TYPE)
    pattern = r'(####\s+)`([a-z_]+)`(\s*\()'
    matches = re.findall(pattern, content)
    if matches:
        content = re.sub(pattern, r'\1\2\3', content)
        changes += len(matches)
    
    # 5. Remove backticks from header parameters: #### パーティションカラム（`year`, `month`）
    # Already covered by partition column fix above
    
    # 6. Fix conversation_id, session_id, user_id, etc. (lowercase with underscores)
    for term in ['conversation_id', 'session_id', 'user_id', 'agent_name',
                 'message_role', 'message_content', 'timestamp', 'metadata',
                 'log_id', 'function_name', 'invocation_id', 'level',
                 'duration_ms', 'status_code', 'exception',
                 'request_id', 'user_agent', 'url', 'method',
                 'response_time_ms', 'client_ip', 'target_schema',
                 'target_table', 'target_column', 'target_db']:
        pattern = f'`{term}`'
        if pattern in content:
            count = content.count(pattern)
            content = content.replace(pattern, term)
            changes += count
    
    # 7. Remove backticks from uppercase parameter names in lists: - `PARAM`: description
    pattern = r'(^-\s+)`([A-Z_][A-Z_]+)`:' 
    matches = re.findall(pattern, content, re.MULTILINE)
    if matches:
        content = re.sub(pattern, r'\1\2:', content, flags=re.MULTILINE)
        changes += len(matches)
    
    return content, changes

def main():
    design_dir = Path("docs/snowflake/chatdemo/design")
    total_changes = 0
    files_changed = 0
    
    for md_file in design_dir.rglob("*.md"):
        content = md_file.read_text(encoding="utf-8")
        new_content, changes = fix_file_content(content, md_file)
        
        if changes > 0 and new_content != content:
            md_file.write_text(new_content, encoding="utf-8")
            files_changed += 1
            total_changes += changes
            print(f"✓ {md_file.relative_to('docs/snowflake/chatdemo')}: {changes} changes")
    
    print(f"\n合計: {total_changes} 箇所を修正（{files_changed} ファイル）")

if __name__ == "__main__":
    main()
