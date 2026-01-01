#!/usr/bin/env python3
"""
DB設計レビューエージェント テストスクリプト

使用方法:
    python test_review_agent.py
    python test_review_agent.py --schema APP_PRODUCTION
    python test_review_agent.py --local
"""
import sys
import os
import json
import argparse
import requests
from datetime import datetime

# プロジェクトルートをパスに追加
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..'))
azfunc_path = os.path.join(project_root, 'app/azfunctions/chatdemo')
sys.path.insert(0, azfunc_path)

try:
    from db_review_agent import DBReviewAgent
except ModuleNotFoundError:
    # ローカル環境ではHTTPエンドポイントのみ使用可能
    DBReviewAgent = None


def test_direct_call(target_schema: str, max_tables: int = None):
    """
    直接モジュールを呼び出してテスト
    """
    if DBReviewAgent is None:
        print("ERROR: DBReviewAgentモジュールが見つかりません")
        print("直接呼び出しテストをスキップして、HTTPエンドポイント経由でテストしてください")
        print("使用方法: python test_review_agent.py --local")
        return False
    
    print(f"=== DB設計レビュー 直接呼び出しテスト ===")
    print(f"対象スキーマ: {target_schema}")
    if max_tables:
        print(f"最大テーブル数: {max_tables}")
    print()
    
    agent = DBReviewAgent()
    success, message, markdown = agent.review_schema(
        target_schema=target_schema,
        max_tables=max_tables
    )
    
    print(f"実行結果: {'成功' if success else '失敗'}")
    print(f"メッセージ: {message}")
    print()
    
    if success and markdown:
        print("=== レビュー結果（Markdown） ===")
        print(markdown[:500])  # 先頭500文字のみ表示
        if len(markdown) > 500:
            print(f"\n... (省略: 残り {len(markdown) - 500} 文字)")
        print()
        
        # ファイルに保存
        output_dir = "tests/output"
        os.makedirs(output_dir, exist_ok=True)
        
        review_date = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = f"{output_dir}/review_{target_schema}_{review_date}.md"
        
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(markdown)
        
        print(f"✓ レビュー結果を保存: {output_file}")
    
    return success


def test_http_endpoint(target_schema: str, max_tables: int = None, base_url: str = None):
    """
    HTTPエンドポイント経由でテスト
    """
    print(f"=== DB設計レビュー HTTPエンドポイントテスト ===")
    
    if not base_url:
        base_url = "http://localhost:7071"
    
    endpoint = f"{base_url}/api/review/schema"
    
    payload = {
        "target_schema": target_schema
    }
    if max_tables:
        payload["max_tables"] = max_tables
    
    print(f"エンドポイント: {endpoint}")
    print(f"リクエスト: {json.dumps(payload, ensure_ascii=False)}")
    print()
    
    try:
        response = requests.post(
            endpoint,
            json=payload,
            headers={"Content-Type": "application/json"},
            timeout=300  # 5分タイムアウト
        )
        
        print(f"ステータスコード: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"成功: {data.get('success')}")
            print(f"メッセージ: {data.get('message')}")
            print()
            
            markdown = data.get('markdown', '')
            if markdown:
                print("=== レビュー結果（Markdown） ===")
                print(markdown[:500])
                if len(markdown) > 500:
                    print(f"\n... (省略: 残り {len(markdown) - 500} 文字)")
                
                # ファイルに保存
                output_dir = "tests/output"
                os.makedirs(output_dir, exist_ok=True)
                
                metadata = data.get('metadata', {})
                review_date = metadata.get('review_date', datetime.now().strftime("%Y-%m-%d"))
                output_file = f"{output_dir}/review_{target_schema}_{review_date.replace('-', '')}.md"
                
                with open(output_file, 'w', encoding='utf-8') as f:
                    f.write(markdown)
                
                print(f"\n✓ レビュー結果を保存: {output_file}")
                return True
        else:
            print(f"エラー: {response.text}")
            return False
            
    except requests.exceptions.RequestException as e:
        print(f"リクエストエラー: {str(e)}")
        return False


def main():
    parser = argparse.ArgumentParser(description='DB設計レビューエージェント テスト')
    parser.add_argument(
        '--schema',
        default='DB_DESIGN',
        help='レビュー対象のスキーマ名（デフォルト: DB_DESIGN）'
    )
    parser.add_argument(
        '--max-tables',
        type=int,
        help='最大テーブル数（省略可）'
    )
    parser.add_argument(
        '--local',
        action='store_true',
        help='ローカルAzure Functions（localhost:7071）に接続'
    )
    parser.add_argument(
        '--url',
        help='Azure FunctionsのベースURL（カスタム）'
    )
    
    args = parser.parse_args()
    
    if args.local or args.url:
        # HTTPエンドポイント経由
        base_url = args.url or "http://localhost:7071"
        success = test_http_endpoint(
            target_schema=args.schema,
            max_tables=args.max_tables,
            base_url=base_url
        )
    else:
        # 直接呼び出し
        success = test_direct_call(
            target_schema=args.schema,
            max_tables=args.max_tables
        )
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
