#!/usr/bin/env python3
"""レビュー結果のメトリクス集計

使用方法:
    python tests/scripts/analyze_reviews.py

出力:
    レビュー総数、優先度別指摘数、平均指摘数等の統計情報
"""
from pathlib import Path
import re
from datetime import datetime


def analyze_reviews(review_dir: Path):
    """レビュー結果を集計して統計情報を出力"""
    metrics = {
        'total_reviews': 0,
        'critical_count': 0,
        'high_count': 0,
        'med_count': 0,
        'low_count': 0,
        'reviews': []
    }
    
    for md_file in sorted(review_dir.glob("*.md")):
        content = md_file.read_text(encoding="utf-8")
        
        # ファイル名から日時を抽出
        # 例: DB_DESIGN_20260102_092948.md
        match = re.search(r'(\w+)_(\d{8})_(\d{6})\.md', md_file.name)
        if not match:
            print(f"Warning: Skipping {md_file.name} (invalid format)")
            continue
        
        schema, date_str, time_str = match.groups()
        review_date = datetime.strptime(f"{date_str} {time_str}", "%Y%m%d %H%M%S")
        
        # 優先度別カウント
        # 例: #### Critical-1: タイトル
        critical = len(re.findall(r'^#### Critical-', content, re.M))
        high = len(re.findall(r'^#### High-', content, re.M))
        med = len(re.findall(r'^#### Med-', content, re.M))
        low = len(re.findall(r'^#### Low-', content, re.M))
        
        metrics['total_reviews'] += 1
        metrics['critical_count'] += critical
        metrics['high_count'] += high
        metrics['med_count'] += med
        metrics['low_count'] += low
        
        metrics['reviews'].append({
            'schema': schema,
            'date': review_date,
            'critical': critical,
            'high': high,
            'med': med,
            'low': low,
            'total': critical + high + med + low
        })
    
    # サマリ出力
    print("=" * 60)
    print("DB Design Review Metrics")
    print("=" * 60)
    print(f"Total Reviews: {metrics['total_reviews']}")
    print(f"\nIssues by Priority:")
    print(f"  Critical: {metrics['critical_count']}")
    print(f"  High:     {metrics['high_count']}")
    print(f"  Med:      {metrics['med_count']}")
    print(f"  Low:      {metrics['low_count']}")
    total_issues = (metrics['critical_count'] + metrics['high_count'] + 
                   metrics['med_count'] + metrics['low_count'])
    print(f"  Total:    {total_issues}")
    
    if metrics['total_reviews'] > 0:
        avg_issues = total_issues / metrics['total_reviews']
        print(f"\nAvg Issues per Review: {avg_issues:.2f}")
    
    # レビュー履歴
    if metrics['reviews']:
        print(f"\nReview History:")
        print("-" * 60)
        for review in metrics['reviews']:
            date_str = review['date'].strftime('%Y-%m-%d %H:%M')
            print(f"{date_str} | {review['schema']:15} | "
                  f"C:{review['critical']} H:{review['high']} M:{review['med']} L:{review['low']} | "
                  f"Total: {review['total']}")


def main():
    """メインエントリポイント"""
    review_dir = Path("docs/snowflake/chatdemo/reviews/schemas")
    
    if not review_dir.exists():
        print(f"Error: {review_dir} not found")
        print(f"Current directory: {Path.cwd()}")
        print("\nPlease run this script from the repository root:")
        print("  cd /home/yolo/pg/snowflake_chatdemo")
        print("  python tests/scripts/analyze_reviews.py")
        return 1
    
    md_files = list(review_dir.glob("*.md"))
    if not md_files:
        print(f"No review files found in {review_dir}")
        return 0
    
    analyze_reviews(review_dir)
    return 0


if __name__ == "__main__":
    exit(main())
