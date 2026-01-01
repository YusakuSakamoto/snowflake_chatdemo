#!/usr/bin/env python3
"""外部テーブル用のカラム定義を内部テーブルから生成"""
from pathlib import Path
import yaml

def generate_columns_for_external_table(internal_table_id: str, external_table_id: str, prefix: str):
    """内部テーブルのカラム定義から外部テーブル用のカラム定義を生成"""
    master_columns = Path("docs/snowflake/chatdemo/master/columns")
    
    # 内部テーブルのカラム定義を取得
    internal_columns = []
    for md_file in master_columns.glob(f"{prefix}.*.md"):
        content = md_file.read_text(encoding="utf-8")
        if content.startswith("---"):
            parts = content.split("---", 2)
            if len(parts) >= 3:
                fm = yaml.safe_load(parts[1])
                if fm.get("type") == "column" and fm.get("table_id") == internal_table_id:
                    internal_columns.append({
                        "file": md_file,
                        "frontmatter": fm,
                        "body": parts[2] if len(parts) > 2 else ""
                    })
    
    # 外部テーブル用のカラム定義を生成
    created_files = []
    for col in internal_columns:
        fm = col["frontmatter"]
        physical = fm["physical"]
        
        # 新しいcolumn_idを生成（EXTプレフィックス付き）
        new_column_id = fm["column_id"].replace("COL_", "COL_EXT_")
        
        # 外部テーブル用のファイル名
        external_file = master_columns / f"{prefix}_EXTERNAL.{physical}.md"
        
        # 新しいfrontmatter
        new_fm = {
            "type": "column",
            "column_id": new_column_id,
            "table_id": external_table_id,
            "physical": physical,
            "domain": fm.get("domain", ""),
            "pk": fm.get("pk", False),
            "is_nullable": fm.get("is_nullable", True),
            "default": fm.get("default"),
            "comment": fm.get("comment", "") + " (外部テーブル版)"
        }
        
        # ファイル内容を生成
        content = "---\n"
        content += yaml.dump(new_fm, allow_unicode=True, default_flow_style=False, sort_keys=False)
        content += "---\n"
        content += f"\n# {physical}\n"
        
        # ファイル作成
        external_file.write_text(content, encoding="utf-8")
        created_files.append(external_file.name)
    
    return created_files

def main():
    print("=== 外部テーブルカラム定義生成 ===\n")
    
    # PROFILE_RUNS_EXTERNAL
    print("1. PROFILE_RUNS_EXTERNAL のカラム定義生成:")
    files1 = generate_columns_for_external_table(
        internal_table_id="TBL_20251226180943",
        external_table_id="TBL_20260102230002",
        prefix="DB_DESIGN.PROFILE_RUNS"
    )
    for f in files1:
        print(f"  ✓ {f}")
    
    print()
    
    # PROFILE_RESULTS_EXTERNAL
    print("2. PROFILE_RESULTS_EXTERNAL のカラム定義生成:")
    files2 = generate_columns_for_external_table(
        internal_table_id="TBL_20251226182257",
        external_table_id="TBL_20260102230001",
        prefix="DB_DESIGN.PROFILE_RESULTS"
    )
    for f in files2:
        print(f"  ✓ {f}")
    
    print()
    print(f"合計: {len(files1) + len(files2)} ファイル生成")

if __name__ == "__main__":
    main()
