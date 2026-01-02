# メンテナンスガイド

## 概要
本ドキュメントは、Snowflake設計ドキュメント（Obsidian Vault）のメンテナンス規則と手順を定義します。

---

## 命名規則

詳細は [NAMING_CONVENTIONS_GUIDE.md](NAMING_CONVENTIONS_GUIDE.md) を参照してください。

### 主要ルール
- **ビュー（View）**: `V_` プレフィックス必須
  - 例: `V_CUSTOMER_MASTER`, `V_DOCS_OBSIDIAN`
- **マテリアライズドビュー（Materialized View）**: `MV_` プレフィックス必須
  - 例: `MV_DAILY_SALES_SUMMARY`
- **テーブル（Table）**: `UPPERCASE_UNDERSCORE` 形式
  - 例: `DOCS_OBSIDIAN`, `PROFILE_RESULTS`

---

## Obsidianリンク規則

### 基本原則
すべてのスキーマオブジェクト参照には `[[]]` 形式のObsidianリンクを使用します。これにより、Obsidianのファイル名変更機能で自動的にリンクが更新されます。

### リンク形式の使い分け

#### 1. 設計ドキュメント参照
設計思想や意図を参照する場合：
```markdown
[[design.OBJECT_NAME]]
```

例：
- `[[design.DOCS_OBSIDIAN]]` - テーブルの設計思想
- `[[design.PROFILE_TABLE]]` - プロシージャの設計意図
- `[[design.APP_PRODUCTION]]` - スキーマの設計方針

#### 2. エンティティ（実体）参照
実際のデータベースオブジェクトを参照する場合：
```markdown
[[SCHEMA.OBJECT]]
```

例：
- `[[DB_DESIGN.DOCS_OBSIDIAN]]` - テーブル実体
- `[[DB_DESIGN.PROFILE_TABLE]]` - プロシージャ実体
- `[[APP_PRODUCTION.V_CUSTOMER_MASTER]]` - ビュー実体

#### 3. カラム参照
カラムを参照する場合：
```markdown
[[SCHEMA.TABLE.COLUMN]]
```

例：
- `[[DB_DESIGN.DOCS_OBSIDIAN.PATH]]` - PATHカラム
- `[[DB_DESIGN.PROFILE_RESULTS.RUN_ID]]` - RUN_IDカラム
- `[[APP_PRODUCTION.ANKEN_MEISAI.CUSTOMER_ID]]` - CUSTOMER_IDカラム

### 禁止事項

#### ❌ バッククォート（`）の使用禁止
カラム名やパラメータ名を `` ` `` で囲むことは禁止です。

**悪い例：**
```markdown
- `TARGET_SCHEMA` / `TARGET_TABLE` / `TARGET_COLUMN` により特定
- | `P_TARGET_DB` | STRING | ✅ | - |
- DB_DESIGN.PROFILE_RUNS.`RUN_ID` を起点として
```

**良い例：**
```markdown
- TARGET_SCHEMA / TARGET_TABLE / TARGET_COLUMN により特定
- | P_TARGET_DB | STRING | ✅ | - |
- [[DB_DESIGN.PROFILE_RUNS.RUN_ID]] を起点として
```

**例外（バッククォート使用OK）：**
- コード例の値：`user` / `assistant`
- 技術用語：`logging`, `AUTO_REFRESH`
- Markdownテーブル内のサンプルデータ：`CUSTOMER_ID`, `EMAIL`
- SQL関数名：`FLATTEN`, `GET`, `ANY_VALUE`

#### ❌ パス付きリンクの禁止
```markdown
❌ [[master/tables/DB_DESIGN.DOCS_OBSIDIAN]]
❌ [[design/DB_DESIGN/design.PROFILE_TABLE]]
✅ [[DB_DESIGN.DOCS_OBSIDIAN]]
✅ [[design.PROFILE_TABLE]]
```

#### ❌ 重複プレフィックスの禁止
```markdown
❌ design.[[design.OBJECT]]
❌ [[design.SCHEMA.TABLE]]
✅ [[design.OBJECT]]
```

---

## 設計レビュー（Snowflake Agent）

### 概要
Snowflake Cortex Agentを使用した自動設計レビューシステムです。Obsidian Vault上の設計ドキュメント（Markdown）を根拠に、スキーマ・テーブル単位で静的レビューを実行します。

### 重要な原則

#### 🚨 AgentはREST API経由でのみ実行可能

**❌ SQLでの実行は不可:**
```sql
-- これは動作しません
SELECT SNOWFLAKE.CORTEX.COMPLETE_AGENT(
    'DB_DESIGN.OBSIDIAN_SCHEMA_DB_DESIGN_REVIEW_AGENT',
    'レビューを実行'
);
```

**✅ REST API経由で実行:**
```bash
# Azure Functions経由（推奨）
curl -X POST http://localhost:7071/api/review/schema \
  -H "Content-Type: application/json" \
  -d '{"target_schema":"DB_DESIGN","max_tables":3}'

# Snowflake REST API直接呼び出し
curl -X POST "https://{account}.snowflakecomputing.com/api/v2/databases/{db}/schemas/{schema}/agents/{agent}:run" \
  -H "Authorization: Bearer {token}" \
  -H "Content-Type: application/json" \
  -d '{"messages":[{"role":"user","content":[{"type":"text","text":"レビュー実行"}]}]}'
```

### レビュー実行手順

#### 1. Azure Functionsの起動
```bash
cd /home/yolo/pg/snowflake_chatdemo/app/azfunctions/chatdemo
func start --port 7071
```

#### 2. レビュー実行
```bash
curl -s -X POST http://localhost:7071/api/review/schema \
  -H "Content-Type: application/json" \
  -d '{"target_schema":"DB_DESIGN","max_tables":3}'
```

#### 3. 出力ファイルの確認
レビュー結果は以下に自動保存されます：
```
docs/snowflake/chatdemo/reviews/schemas/{SCHEMA}_{YYYYMMDD_HHMMSS}.md
```

例：
- `DB_DESIGN_20260102_092948.md`

### レビュー結果の読み方と活用方法

#### ファイル構造
各レビュー結果は以下のセクションで構成されています：

1. **メタ情報（YAML frontmatter）**
   ```yaml
   ---
   type: agent_review
   review_date: 2026-01-02
   target: DB_DESIGN
   ---
   ```

2. **0. メタ情報**
   - 対象スキーマ
   - レビュー日時
   - 参照したドキュメントのPATH一覧

3. **1. サマリ（3行）**
   - 全体評価の要約
   - 主要な問題点のハイライト
   - 設計ドキュメントの充実度評価

4. **2. Findings（優先度別）**
   - **Critical**: 本番障害リスクレベル（FK制約欠如、データ整合性違反等）
   - **High**: 重大な設計問題（CHECK制約不足、状態遷移不整合等）
   - **Med**: パフォーマンス・保守性問題（VARCHAR長未指定、複合PK妥当性等）
   - **Low**: 軽微な改善提案（コメント統一、文書整合性等）

5. **3. 【仮説】の検証**
   - 設計書内の【仮説】タグへの回答

6. **4. 追加で集めたい情報**
   - 不足している調査事項

7. **5. 改善提案（次アクション）**
   - 実装難易度・影響範囲・推奨実施時期付き

#### 各Finding項目の構成

各指摘には以下の情報が含まれています：

- **指摘**: 問題の内容
- **影響**: ビジネス/技術的影響
- **提案**: 具体的な解決策
- **DDL例**: 実装可能なSQL（Critical/Highは必須）
- **移行手順**: 既存データへの適用手順（該当時）
- **Evidence**: Vault上のMarkdownからの引用（2-3件）
  - 設計思想ファイル（design/）
  - カラム定義ファイル（master/columns/）
  - テーブル定義ファイル（master/tables/）
- **Vault差分案**: 設計ドキュメント修正案
- **実装メタ情報**:
  - 影響範囲: [小/中/大]
  - 実装難易度: [低/中/高]
  - 推奨実施時期: [即時/今週/今月/Q1]

#### Critical/High指摘への対応フロー

**1. 即座に対応すべき項目の特定**
```bash
# レビュー結果から優先度を確認
grep -A 5 "### Critical" docs/snowflake/chatdemo/reviews/schemas/DB_DESIGN_*.md
```

**2. 設計意図の再確認**
```bash
# Evidence欄のPATHを確認し、設計思想を再確認
cat docs/snowflake/chatdemo/design/DB_DESIGN/design.PROFILE_RESULTS.md
cat docs/snowflake/chatdemo/master/columns/DB_DESIGN.PROFILE_RESULTS.RUN_ID.md
```

**3. DDL実行**
```sql
-- レビュー結果のDDL例をそのまま使用可能
ALTER TABLE DB_DESIGN.PROFILE_RESULTS
ADD CONSTRAINT FK_PROFILE_RESULTS_RUN_ID
FOREIGN KEY (RUN_ID) REFERENCES DB_DESIGN.PROFILE_RUNS(RUN_ID);

-- 移行手順（既存データがある場合）
-- 1. 既存データの整合性検証
SELECT r.RUN_ID
FROM DB_DESIGN.PROFILE_RESULTS r
LEFT JOIN DB_DESIGN.PROFILE_RUNS p ON r.RUN_ID = p.RUN_ID
WHERE p.RUN_ID IS NULL;

-- 2. 不整合データのクリーンアップ
-- (必要に応じて実施)

-- 3. 外部キー制約追加
-- (上記のALTER TABLE実行)

-- 4. 整合性検証
SELECT COUNT(*) FROM DB_DESIGN.PROFILE_RESULTS;
```

**4. 設計ドキュメント更新**
```bash
# Vault差分案を参考に、該当するMarkdownファイルを更新
# 例: master/tables/DB_DESIGN.PROFILE_RESULTS.md

# 制約追加の理由・背景を設計書に記載
# - なぜこの制約が必要なのか
# - どのような問題を防ぐのか
# - 既存データへの影響は何か
```

#### Med/Low指摘への対応

- **Med指摘**: 次回の設計見直しタイミングで検討
  - 技術的負債として Issue/Ticket 管理
  - スプリント計画に組み込み
  - パフォーマンス影響が大きい場合は前倒し

- **Low指摘**: 随時対応
  - コメント改善等の軽微な項目
  - ドキュメント整合性の向上
  - コードレビュー時に合わせて修正

### 定期レビューの自動化

#### GitHub Actions連携例（未実装）

週次でレビューを実行し、結果をリポジトリにコミットする例：

```yaml
# .github/workflows/weekly-db-review.yml
name: Weekly DB Design Review

on:
  schedule:
    - cron: '0 9 * * 1'  # 毎週月曜9時（JST 18時）
  workflow_dispatch:      # 手動実行も可能

jobs:
  review:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Run DB Design Review
        env:
          AZURE_FUNCTION_URL: ${{ secrets.AZURE_FUNCTION_URL }}
        run: |
          response=$(curl -s -X POST "$AZURE_FUNCTION_URL/api/review/schema" \
            -H "Content-Type: application/json" \
            -d '{"schema": "DB_DESIGN"}')
          
          echo "Review completed: $response"
      
      - name: Commit review results
        run: |
          git config --local user.email "action@github.com"
          git config --local user.name "GitHub Action"
          git add docs/snowflake/chatdemo/reviews/
          git diff --staged --quiet || git commit -m "chore: 定期DB設計レビュー結果追加"
          git push
```

#### cron連携例（Linux/WSL）

```bash
# crontab -e で以下を追加
# 毎週月曜9時に実行し、ログを保存
0 9 * * 1 cd /home/yolo/pg/snowflake_chatdemo && curl -X POST http://localhost:7071/api/review/schema -H "Content-Type: application/json" -d '{"schema": "DB_DESIGN"}' >> /tmp/db_review.log 2>&1
```

### メトリクス収集例

#### レビュー結果の統計分析スクリプト

```python
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
        match = re.search(r'(\w+)_(\d{8})_(\d{6})\.md', md_file.name)
        if not match:
            continue
        
        schema, date_str, time_str = match.groups()
        review_date = datetime.strptime(f"{date_str} {time_str}", "%Y%m%d %H%M%S")
        
        # 優先度別カウント
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
    print(f"  Total:    {metrics['critical_count'] + metrics['high_count'] + metrics['med_count'] + metrics['low_count']}")
    
    if metrics['total_reviews'] > 0:
        avg_issues = (metrics['critical_count'] + metrics['high_count'] + 
                     metrics['med_count'] + metrics['low_count']) / metrics['total_reviews']
        print(f"\nAvg Issues per Review: {avg_issues:.2f}")
    
    # レビュー履歴
    print(f"\nReview History:")
    print("-" * 60)
    for review in metrics['reviews']:
        print(f"{review['date'].strftime('%Y-%m-%d %H:%M')} | {review['schema']:15} | "
              f"C:{review['critical']} H:{review['high']} M:{review['med']} L:{review['low']} | Total: {review['total']}")

if __name__ == "__main__":
    review_dir = Path("docs/snowflake/chatdemo/reviews/schemas")
    if not review_dir.exists():
        print(f"Error: {review_dir} not found")
        exit(1)
    
    analyze_reviews(review_dir)
```

#### 実行例

```bash
$ python tests/scripts/analyze_reviews.py

============================================================
DB Design Review Metrics
============================================================
Total Reviews: 2

Issues by Priority:
  Critical: 1
  High:     2
  Med:      2
  Low:      1
  Total:    6

Avg Issues per Review: 3.00

Review History:
------------------------------------------------------------
2026-01-02 09:12 | DB_DESIGN       | C:0 H:0 M:0 L:0 | Total: 0
2026-01-02 09:29 | DB_DESIGN       | C:1 H:2 M:2 L:1 | Total: 6
```

### レビュー品質指標

#### 評価項目と目標値

| 評価項目 | 目標値 | 現在値（v2） | 説明 |
|----------|--------|-------------|------|
| **網羅性** | 9/10 | 9/10 | Snowflake特化観点の追加 |
| **指摘の深さ** | 8/10 | 8/10 | 論理矛盾の検出 |
| **Evidence具体性** | 10/10 | 10/10 | 3件のEvidence（設計思想+実装+運用） |
| **提案実用性** | 9/10 | 9/10 | DDL例・移行手順の提示 |
| **優先度妥当性** | 9/10 | 9/10 | Critical/High/Med/Low 4段階 |
| **Snowflake特化** | 8/10 | 8/10 | コスト最適化、クラスタリングキー等 |
| **構成・可読性** | 9/10 | 9/10 | YAML frontmatter + 構造化 |
| **総合評価** | 9/10 | 9/10 | 本番運用可能レベル |

#### 改善履歴

**v1（初期版）: 7.5/10点**
- 優先度: High/Med/Low 3段階
- DDL例: なし
- Evidence: 各2件
- 実装メタ情報: なし

**v2（改善版）: 9.0/10点**
- 優先度: Critical/High/Med/Low 4段階
- DDL例: すべてのCritical/Highに追加
- Evidence: Critical/High 2-3件、Med 2件、Low 1件以上
- 実装メタ情報: 影響範囲、実装難易度、推奨実施時期を追加
- Snowflake特化観点: VARCHAR長最適化、ストレージ効率化等を追加

### Agent定義の主要改善点

#### 1. Snowflakeキーワードの明示化
```yaml
instructions:
  orchestration: >
    あなたはSnowflakeのデータベース設計レビュー専用のアシスタントです。
```

#### 2. レビュー観点の拡充
- **Snowflake特化**: クラスタリングキー、Time Travel、ストリーム/タスク
- **パフォーマンス**: データ型適切性、VARIANT濫用チェック
- **運用監視**: ログ設計、アラート条件（SLI/SLO）
- **セキュリティ**: 列レベルマスキング、タグベースポリシー
- **コスト最適化**: VARCHAR長、圧縮効率、Warehouse適正サイズ

#### 3. 実装支援の強化
各Findingに以下を追加：
- **DDL例**: 即座に実装可能なALTER TABLE文
- **移行手順**: 既存データがある場合の4ステップ手順
- **実装メタ情報**:
  - 影響範囲: [小/中/大]
  - 実装難易度: [低/中/高]
  - 推奨実施時期: [即時/今週/今月/Q1]

### GitHub Copilot との役割分担

| 項目 | GitHub Copilot | Snowflake Agent |
|------|----------------|----------------|
| **主要対象** | 実装コード | 設計ドキュメント |
| **レビュー単位** | PRベース、ファイルベース | スキーマ・テーブル単位 |
| **実行タイミング** | PR作成時（自動） | 設計フェーズ（オンデマンド） |
| **検出可能な問題** | 構文・セキュリティ・コーディング規約 | FK/PK設計、状態遷移、Snowflake最適化 |
| **強み** | 即座性、脆弱性検出 | 論理整合性、設計思想検証 |

#### 相互補完による開発フロー

```
1. 設計フェーズ
   ├─ Obsidian Vaultで設計ドキュメント作成
   ├─ 【Snowflake Agent実行】← 設計品質の番人
   ├─ Critical/High指摘を修正
   └─ 設計レビュー完了

2. DDL生成フェーズ
   ├─ Dataviewで自動DDL生成
   └─ generated/ddl/配下にDDL出力

3. 実装フェーズ
   ├─ DDL/Procedure/Pythonコード実装
   ├─ PR作成
   ├─ 【GitHub Copilot自動レビュー】← 実装品質の番人
   ├─ 構文・セキュリティ検証
   └─ マージ

4. デプロイフェーズ
   └─ 本番適用
```

### トラブルシューティング

#### よくあるエラーと対処法

##### 1. Agent実行エラー: `snowflake_error`

**エラー内容:**
```json
{"success": false, "error": "Agent実行エラー: snowflake_error"}
```

**原因:**
- Agent実行権限不足
- Agent定義の不備
- データベース/スキーマ権限不足

**解決策:**
```sql
-- 1. Agent権限の確認と付与
USE ROLE ACCOUNTADMIN;
GRANT USAGE ON AGENT DB_DESIGN.OBSIDIAN_SCHEMA_DB_DESIGN_REVIEW_AGENT 
  TO ROLE GBPS253YS_API_ROLE;

-- 2. データベース/スキーマ権限の確認
GRANT USAGE ON DATABASE CHATDEMO TO ROLE GBPS253YS_API_ROLE;
GRANT USAGE ON SCHEMA DB_DESIGN TO ROLE GBPS253YS_API_ROLE;

-- 3. Agent定義の確認
SHOW AGENTS IN SCHEMA DB_DESIGN;
DESC AGENT DB_DESIGN.OBSIDIAN_SCHEMA_DB_DESIGN_REVIEW_AGENT;
```

##### 2. SSEレスポンスが空/取得できない

**エラー内容:**
- Agentからのレスポンスが空
- `full_response` が空文字列

**原因:**
- SSEレスポンス形式の誤解析
- `delta.content` 構造の誤解

**正しい解析方法:**
```python
# ❌ 誤った解析（これは動作しない）
if hasattr(delta, 'content'):
    text = delta.content  # このプロパティは存在しない

# ✅ 正しい解析
for line in response.iter_lines():
    if line.startswith(b'data: '):
        decoded = line.decode('utf-8')
        json_str = decoded.replace('data: ', '')
        
        if json_str == '[DONE]':
            break
        
        try:
            data = json.loads(json_str)
            # Snowflake Agent SSE形式: {"content_index": N, "text": "..."}
            if 'text' in data:
                full_response += data['text']
        except json.JSONDecodeError:
            continue
```

**デバッグ方法:**
```python
# レスポンスの生データを確認
for line in response.iter_lines():
    print(f"DEBUG: {line}")  # バイナリ形式で出力
    if line:
        decoded = line.decode('utf-8')
        print(f"DECODED: {decoded}")  # デコード後
```

##### 3. Bearer Token期限切れ

**エラー内容:**
```
401 Unauthorized
Authentication token expired
```

**原因:**
- Bearer Tokenの有効期限切れ（通常3600秒）
- Private Key認証への切り替えが必要

**解決策:**

**方法1: トークン再生成（短期的）**
```bash
# Snowflakeコンソールで新しいトークンを生成
# local.settings.jsonを更新
```

**方法2: Private Key認証への切り替え（推奨）**
```python
# snowflake_auth.py
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.backends import default_backend
import jwt
import time

def get_jwt_token(account: str, user: str, private_key_path: str) -> str:
    """Private Keyを使用してJWTトークンを生成"""
    with open(private_key_path, 'rb') as key_file:
        private_key = serialization.load_pem_private_key(
            key_file.read(),
            password=None,
            backend=default_backend()
        )
    
    now = int(time.time())
    payload = {
        'iss': f'{account}.{user}',
        'sub': f'{account}.{user}',
        'iat': now,
        'exp': now + 3600
    }
    
    token = jwt.encode(payload, private_key, algorithm='RS256')
    return token
```

##### 4. Markdown抽出失敗

**エラー内容:**
- `~~~md ... ~~~` ブロックが見つからない
- レビュー結果が保存されない

**原因:**
- Agent出力形式の変更
- コードブロック形式の誤認識

**デバッグ方法:**
```python
# db_review_agent.py
def _extract_markdown(self, content: str) -> str:
    # デバッグ: 生レスポンスを出力
    logging.info(f"Raw response length: {len(content)}")
    logging.info(f"First 500 chars: {content[:500]}")
    
    # パターン確認
    if '~~~md' in content:
        logging.info("Found ~~~md marker")
    elif '```markdown' in content:
        logging.info("Found ```markdown marker")
    else:
        logging.warning("No markdown block found")
        return content  # 全体を返す
```

**回避策:**
```python
# 複数パターンに対応
def _extract_markdown(self, content: str) -> str:
    patterns = [
        (r'~~~md\n(.*?)\n~~~', re.DOTALL),
        (r'```markdown\n(.*?)\n```', re.DOTALL),
        (r'```md\n(.*?)\n```', re.DOTALL),
    ]
    
    for pattern, flags in patterns:
        match = re.search(pattern, content, flags)
        if match:
            return match.group(1).strip()
    
    # マーカーが見つからない場合は全体を返す
    logging.warning("No markdown block markers found, returning full content")
    return content
```

##### 5. 日本語文字化け

**エラー内容:**
- レビュー結果の日本語が文字化け
- ファイル保存時にエラー

**原因:**
- エンコーディング指定の不足
- Windows環境でのデフォルトエンコーディング

**解決策:**
```python
# 必ずencoding="utf-8"を指定
def _save_markdown(self, content: str, schema: str):
    output_file = output_dir / f"{schema}_{timestamp}.md"
    output_file.write_text(content, encoding="utf-8")  # ← 明示的に指定
```

##### 6. Windows Vault同期の失敗

**エラー内容:**
- WSL → Windows へのファイルコピーが失敗
- パーミッションエラー

**原因:**
- Windows側のファイルが開かれている（Obsidian等）
- パス区切り文字の違い

**解決策:**
```bash
# WSL側スクリプト
#!/bin/bash
WINDOWS_VAULT="/mnt/c/Users/yolo/Documents/Obsidian/chatdemo"

# ファイルが開かれていないか確認
if lsof "$file" 2>/dev/null; then
    echo "Warning: File is open, skipping sync"
    exit 1
fi

# rsyncを使用（より安全）
rsync -av --update \
    docs/snowflake/chatdemo/ \
    "$WINDOWS_VAULT/docs/snowflake/chatdemo/"
```

#### デバッグTips

##### ログレベルの調整
```python
# function_app.py
import logging

# 詳細ログを有効化
logging.basicConfig(
    level=logging.DEBUG,  # INFO → DEBUG
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
```

##### curlでの動作確認
```bash
# レスポンスヘッダーも含めて確認
curl -v -X POST http://localhost:7071/api/review/schema \
  -H "Content-Type: application/json" \
  -d '{"schema": "DB_DESIGN"}' \
  2>&1 | tee debug.log

# SSE形式の生データを確認
curl -N -X POST "https://{account}.snowflakecomputing.com/api/v2/databases/CHATDEMO/schemas/DB_DESIGN/agents/OBSIDIAN_SCHEMA_DB_DESIGN_REVIEW_AGENT:run" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"messages":[{"role":"user","content":"test"}]}' \
  2>&1 | tee sse_raw.log
```

##### Python REPLでの確認
```python
# Snowflake接続テスト
import snowflake.connector
conn = snowflake.connector.connect(
    account='your_account',
    user='your_user',
    authenticator='oauth',
    token='your_token'
)
cursor = conn.cursor()
cursor.execute("SELECT CURRENT_USER(), CURRENT_ROLE()")
print(cursor.fetchone())

# Agent存在確認
cursor.execute("SHOW AGENTS IN SCHEMA DB_DESIGN")
print(cursor.fetchall())
```
```

2. Bearer Token有効期限の確認
```bash
# トークンを再生成してlocal.settings.jsonを更新
```

#### SSEレスポンスが空

**問題:** Agentからのレスポンスが取得できない

**原因:** SSEレスポンス形式の誤解析

**正しい形式:**
```python
# ❌ 誤った解析
delta.content  # これは存在しない

# ✅ 正しい解析
data = json.loads(line.replace("data: ", ""))
text = data["text"]  # {"content_index": N, "text": "..."}
```

---

## マスターファイル構造

### ディレクトリ構成
```
master/
├── schemas/          # スキーマ定義
├── tables/           # テーブル定義
├── views/            # ビュー定義
├── externaltables/   # 外部テーブル定義
├── columns/          # カラム定義（152ファイル）
└── other/            # プロシージャ・関数・ツール
```

### ファイル命名規則
- スキーマ: `SCHEMA_NAME.md`
- テーブル: `SCHEMA.TABLE.md`
- ビュー: `SCHEMA.VIEW.md`
- カラム: `SCHEMA.TABLE.COLUMN.md`
- プロシージャ: `SCHEMA.PROCEDURE.md`

---

## デザインファイル構造

### ディレクトリ構成
```
design/
├── design.SCHEMA.md           # スキーマ設計方針
├── APP_PRODUCTION/            # APP_PRODUCTIONスキーマ設計
│   └── design.OBJECT.md
├── DB_DESIGN/                 # DB_DESIGNスキーマ設計
│   └── design.OBJECT.md
├── LOG/                       # LOGスキーマ設計
│   └── design.OBJECT.md
└── NAME_RESOLUTION/           # NAME_RESOLUTIONスキーマ設計
    └── design.OBJECT.md
```

### ファイル命名規則
- スキーマ設計: `design.SCHEMA.md`
- オブジェクト設計: `design.OBJECT.md`

---

## メンテナンス手順

### 1. 新規オブジェクト追加時

#### 手順
1. masterファイルを作成（master/tables/, master/views/, etc.）
2. designファイルを作成（design/SCHEMA/design.OBJECT.md）
3. カラム定義ファイルを作成（必要に応じて）
4. naming_conventions.md に準拠しているか確認
5. リンクが正しく設定されているか確認

#### チェックリスト
- [ ] 命名規則に準拠している
- [ ] masterファイルが存在する
- [ ] designファイルが存在する
- [ ] カラム定義が作成されている（テーブル・ビューの場合）
- [ ] すべての参照が [[]] リンクになっている
- [ ] バッククォートが使用されていない

### 2. 既存オブジェクト変更時

#### 手順
1. 変更内容をdesignファイルに記載
2. masterファイルを更新
3. 関連するカラム定義を更新
4. リンク切れがないか確認

#### 注意点
- Obsidianのファイル名変更機能を使うと、リンクが自動更新される
- 手動でファイル名を変更した場合は、すべての参照を手動更新する必要がある

### 3. 命名規則違反の修正

#### 検出方法
```bash
# ビューで V_ プレフィックスがないものを検出
cd docs/snowflake/chatdemo/master/views
ls -1 | grep -v '^[A-Z_]*\.V_'
```

#### 修正手順
1. ファイル名をリネーム
2. 全ての参照を更新（スクリプト使用推奨）
3. Windows Vaultに同期
4. コミット・プッシュ

### 4. バッククォート削除

#### 検出方法
```bash
# バッククォートで囲まれた大文字の識別子を検出
grep -r '`[A-Z_]\+`' docs/snowflake/chatdemo/design/
```

#### 修正手順
1. tests/scripts/ 配下のスクリプトを参考に修正スクリプトを作成
2. 対象ファイルを一括変換
3. 手動で確認（例外ケースの確認）
4. Windows Vaultに同期
5. コミット・プッシュ

---

## 自動化スクリプト

### 配置場所
すべてのメンテナンススクリプトは `tests/scripts/` に配置します。

### 既存スクリプト一覧

#### リンク修正系
- `add_obsidian_links.py` - 初期Obsidianリンク追加
- `fix_obsidian_links.py` - Obsidianリンク修正（design.プレフィックス追加）
- `fix_malformed_links.py` - 不正リンク修正（重複プレフィックス削除）
- `fix_schema_table_links.py` - 実体参照修正（SCHEMA.TABLE形式に変換）
- `fix_master_links.py` - masterリンク修正（[[SCHEMA.OBJECT]]形式に変換）

#### バッククォート削除系
- `remove_param_backticks.py` - パラメータ名のバッククォート削除
- `fix_all_backticks.py` - 包括的バッククォート削除（第1版）
- `fix_all_backticks_v2.py` - 包括的バッククォート削除（第2版）
- `fix_all_backticks_final.py` - 最終バッククォート削除
- `fix_backticks_additional.py` - 追加バッククォート削除

#### 命名規則修正系
- `rename_docs_obsidian_v.py` - ビュー名変更（正規表現版）
- `rename_view_simple.py` - ビュー名変更（単純置換版）

### スクリプト作成ガイドライン

#### 基本構造
```python
#!/usr/bin/env python3
"""
スクリプトの説明
"""
from pathlib import Path

def process_file(content: str) -> tuple[str, int]:
    """ファイル内容を処理して変更箇所数を返す"""
    changes = 0
    # 処理内容
    return content, changes

def main():
    design_dir = Path("docs/snowflake/chatdemo/design")
    total_changes = 0
    files_changed = 0
    
    for md_file in design_dir.rglob("*.md"):
        content = md_file.read_text(encoding="utf-8")
        new_content, changes = process_file(content)
        
        if changes > 0 and new_content != content:
            md_file.write_text(new_content, encoding="utf-8")
            files_changed += 1
            total_changes += changes
            print(f"✓ {md_file.relative_to('docs/snowflake/chatdemo')}: {changes} changes")
    
    print(f"\n合計: {total_changes} 箇所を修正（{files_changed} ファイル）")

if __name__ == "__main__":
    main()
```

#### 注意事項
- UTF-8エンコーディングを使用
- 変更前後の比較を必ず行う
- dry-runモードの実装を推奨
- 処理結果を明確にログ出力

---

## Windows Vault同期

### 同期先
```
/mnt/c/Users/Owner/Documents/snowflake-db/
```

### 同期コマンド
```bash
# 全ファイル同期（削除も含む）
rsync -av --delete docs/snowflake/chatdemo/ /mnt/c/Users/Owner/Documents/snowflake-db/

# 特定ファイル同期
cp "docs/snowflake/chatdemo/design/DB_DESIGN/design.OBJECT.md" \
   "/mnt/c/Users/Owner/Documents/snowflake-db/design/DB_DESIGN/"
```

### 同期タイミング
- 重要な変更後は必ず同期
- コミット前に同期推奨
- 大量のファイル変更時は rsync 使用

---

## ベストプラクティス

### 設計ドキュメントの書き方

#### 1. 設計思想を明確に記載する

**良い例:**
```markdown
## 設計思想

本テーブルは、プロファイル実行の履歴を管理するため、以下の原則に基づいて設計されている：

1. **実行単位の一意性**: RUN_IDで実行を一意に識別
2. **状態遷移の明確化**: RUNNING → SUCCEEDED | FAILED のみ許可
3. **時系列追跡**: STARTED_AT, FINISHED_AT で実行期間を記録
4. **結果との分離**: 結果はPROFILE_RESULTSテーブルに格納（正規化）
```

**悪い例:**
```markdown
## 設計思想

実行履歴を保存するテーブル。
```

#### 2. Evidence（根拠）を残す

設計判断には必ず理由を記載：

```markdown
## カラム定義

### STATUS
- **型**: VARCHAR
- **制約**: NOT NULL, CHECK (STATUS IN ('RUNNING', 'SUCCEEDED', 'FAILED'))
- **設計理由**:
  - 状態遷移を制限することで、不正な状態値の混入を防ぐ
  - 監視システムが確実に状態を判別できるようにする
  - ENUMではなくVARCHARにすることで、将来の状態追加に柔軟に対応
```

#### 3. 関連を明示する

テーブル・カラム間の関連は必ずObsidianリンクで記載：

```markdown
## 関連テーブル

- [[DB_DESIGN.PROFILE_RESULTS]] - 本テーブルの[[DB_DESIGN.PROFILE_RUNS.RUN_ID]]を外部キーとして参照
- [[DB_DESIGN.DOCS_OBSIDIAN]] - プロファイル対象のドキュメントを管理
```

#### 4. 【仮説】タグで検証事項を明記

設計時の仮説や未確定事項には【仮説】タグを使用：

```markdown
## 性能要件

### 【仮説】クラスタリングキーは不要

- 理由: 
  - データ量が月間10万行程度と小規模
  - STARTED_ATでの範囲検索がメイン
  - Time Travel機能で過去データ参照が可能
- 検証方法: 本番稼働後、クエリパフォーマンスを監視
- 見直しタイミング: データ量が100万行を超えた場合
```

Agent実行時に【仮説】タグに対する検証コメントが返されます。

### レビュー品質を上げるコツ

#### 1. 設計書を充実させる

Agentは設計書の内容を根拠にレビューします：

**充実した設計書の例:**
- 設計思想: なぜこの設計なのか
- カラム定義: 各カラムの役割・制約・理由
- 関連: 他のテーブルとの関係
- 制約: PK/FK/CHECK/UNIQUE の設計意図
- 性能: クラスタリングキー・インデックスの方針

#### 2. 具体的な質問をする

レビュー実行時に具体的な観点を指定：

```bash
# 一般的なレビュー
curl -X POST http://localhost:7071/api/review/schema \
  -d '{"schema": "DB_DESIGN"}'

# 観点を絞ったレビュー
curl -X POST http://localhost:7071/api/review/schema \
  -d '{"schema": "DB_DESIGN", "focus": "FK制約とデータ整合性"}'
```

#### 3. 定期的にレビューを実行する

- **設計フェーズ**: 初期設計完了時
- **実装前**: DDL生成前
- **変更時**: スキーマ変更のたび
- **定期**: 月次レビュー（自動化推奨）

### よくある指摘事例と対策

#### Critical指摘の典型例

**1. 外部キー制約の欠如**
```
指摘: PROFILE_RESULTS.RUN_ID に対する外部キー制約が未定義
影響: 存在しないRUN_IDでの結果登録、参照整合性不整合
対策: FK制約を追加し、参照整合性を保証
```

**対策コード:**
```sql
ALTER TABLE DB_DESIGN.PROFILE_RESULTS
ADD CONSTRAINT FK_PROFILE_RESULTS_RUN_ID
FOREIGN KEY (RUN_ID) REFERENCES DB_DESIGN.PROFILE_RUNS(RUN_ID);
```

**設計書への反映:**
```markdown
## 制約

### 外部キー
- RUN_ID → PROFILE_RUNS.RUN_ID
  - 理由: 存在しないRUN_IDでの結果登録を防ぐ
  - 動作: CASCADE削除により、RUN削除時に結果も自動削除
```

#### High指摘の典型例

**2. CHECK制約の不足**
```
指摘: STATUS列でCHECK制約が未定義
影響: 無効な状態値混入リスク
対策: 許可値を明示的に制限
```

**対策コード:**
```sql
ALTER TABLE DB_DESIGN.PROFILE_RUNS
ADD CONSTRAINT CHK_STATUS
CHECK (STATUS IN ('RUNNING', 'SUCCEEDED', 'FAILED'));
```

**3. 状態遷移の整合性**
```
指摘: FINISHED_ATとSTATUSの整合性が制約で保証されていない
影響: 論理的不整合データの混入
対策: 複合制約の追加
```

**対策コード:**
```sql
ALTER TABLE DB_DESIGN.PROFILE_RUNS
ADD CONSTRAINT CHK_STATUS_FINISHED_CONSISTENCY
CHECK (
  (STATUS = 'RUNNING' AND FINISHED_AT IS NULL) OR
  (STATUS IN ('SUCCEEDED', 'FAILED') AND FINISHED_AT IS NOT NULL)
);
```

#### Med指摘の典型例

**4. VARCHAR長の未指定**
```
指摘: VARCHAR列で長さ未指定（デフォルト16MB）
影響: ストレージ非効率、パフォーマンス劣化
対策: 適切な長さを指定
```

**対策:**
```sql
-- Before
RUN_ID VARCHAR

-- After
RUN_ID VARCHAR(36)  -- UUID想定
STATUS VARCHAR(10)  -- 最長値'SUCCEEDED'=9文字
```

### 他スキーマへの展開手順

#### 1. Agent定義の複製

```sql
-- 1. 既存Agentの定義を確認
DESC AGENT DB_DESIGN.OBSIDIAN_SCHEMA_DB_DESIGN_REVIEW_AGENT;

-- 2. 新しいスキーマ用にAgent作成
CREATE OR REPLACE AGENT APP_PRODUCTION.OBSIDIAN_SCHEMA_APP_PRODUCTION_REVIEW_AGENT
  MODEL = CLAUDE_SONNET_4_5
  INSTRUCTIONS = $$ 
    あなたはSnowflakeのデータベース設計レビュー専用のアシスタントです。
    対象スキーマ: APP_PRODUCTION
    ...
  $$
  TOOLS = (
    FUNCTION DB_DESIGN.GET_DOCS_BY_PATHS_AGENT(paths ARRAY)
  )
  TOKEN_BUDGET = 614400;

-- 3. 権限付与
GRANT USAGE ON AGENT APP_PRODUCTION.OBSIDIAN_SCHEMA_APP_PRODUCTION_REVIEW_AGENT
  TO ROLE GBPS253YS_API_ROLE;
```

#### 2. 設計ドキュメントの準備

```bash
# 対象スキーマの設計ドキュメント構造を確認
tree docs/snowflake/chatdemo/design/APP_PRODUCTION/
tree docs/snowflake/chatdemo/master/tables/ | grep APP_PRODUCTION
```

確認事項：
- [ ] design.SCHEMA.md が存在する
- [ ] design/SCHEMA/ ディレクトリ配下に設計ファイルが存在する
- [ ] master/tables/ 配下にテーブル定義が存在する
- [ ] master/columns/ 配下にカラム定義が存在する

#### 3. Azure Functionsの更新

```python
# db_review_agent.py に新しいスキーマを追加

SCHEMA_AGENT_MAP = {
    "DB_DESIGN": "DB_DESIGN.OBSIDIAN_SCHEMA_DB_DESIGN_REVIEW_AGENT",
    "APP_PRODUCTION": "APP_PRODUCTION.OBSIDIAN_SCHEMA_APP_PRODUCTION_REVIEW_AGENT",  # 追加
}

def review_schema(schema: str) -> dict:
    if schema not in SCHEMA_AGENT_MAP:
        return {"success": False, "error": f"Unknown schema: {schema}"}
    
    agent_name = SCHEMA_AGENT_MAP[schema]
    # ...
```

#### 4. レビュー実行とテスト

```bash
# テストレビュー実行（max_tables=1で軽量化）
curl -X POST http://localhost:7071/api/review/schema \
  -H "Content-Type: application/json" \
  -d '{"schema": "APP_PRODUCTION", "max_tables": 1}'

# 結果確認
ls -lh docs/snowflake/chatdemo/reviews/schemas/APP_PRODUCTION_*.md

# メトリクス確認
python3 tests/scripts/analyze_reviews.py
```

### パフォーマンス最適化Tips

#### 1. レビュー対象の絞り込み

大規模スキーマでは `max_tables` パラメータで対象を制限：

```bash
# 全テーブルレビュー（時間がかかる）
curl -X POST ... -d '{"schema": "APP_PRODUCTION"}'

# 上位3テーブルのみ（高速）
curl -X POST ... -d '{"schema": "APP_PRODUCTION", "max_tables": 3}'
```

#### 2. Token予算の調整

Agent定義の `TOKEN_BUDGET` を調整：

```sql
-- 軽量レビュー（コスト重視）
TOKEN_BUDGET = 307200;  -- 約半分

-- 標準レビュー
TOKEN_BUDGET = 614400;  -- 推奨値

-- 詳細レビュー（品質重視）
TOKEN_BUDGET = 1228800;  -- 2倍
```

#### 3. 並行実行の制御

複数スキーマを並行レビューする場合：

```bash
# シーケンシャル実行（安全）
for schema in DB_DESIGN APP_PRODUCTION NAME_RESOLUTION; do
  curl -X POST ... -d "{\"schema\": \"$schema\"}"
  sleep 10  # Agentリソース解放待ち
done

# 並行実行（高速だが負荷大）
for schema in DB_DESIGN APP_PRODUCTION NAME_RESOLUTION; do
  curl -X POST ... -d "{\"schema\": \"$schema\"}" &
done
wait
```

### 運用監視の推奨事項

#### 1. レビュー実行のログ記録

```python
# db_review_agent.py
import logging

logger = logging.getLogger(__name__)

def review_schema(schema: str) -> dict:
    logger.info(f"Review started: schema={schema}")
    start_time = time.time()
    
    try:
        # レビュー処理
        result = call_agent(...)
        elapsed = time.time() - start_time
        logger.info(f"Review completed: schema={schema}, elapsed={elapsed:.2f}s")
        return result
    except Exception as e:
        logger.error(f"Review failed: schema={schema}, error={e}")
        raise
```

#### 2. メトリクスの定期集計

```bash
# 週次でメトリクスをSlack通知
0 9 * * 1 cd /path/to/repo && python3 tests/scripts/analyze_reviews.py | \
  curl -X POST https://hooks.slack.com/services/XXX/YYY/ZZZ \
    -d @- -H "Content-Type: application/json"
```

#### 3. Critical指摘のアラート

```python
# analyze_reviews.py に追加
def check_critical_issues(review_dir: Path) -> bool:
    """Critical指摘が存在するかチェック"""
    for md_file in review_dir.glob("*.md"):
        content = md_file.read_text(encoding="utf-8")
        if re.search(r'^#### Critical-', content, re.M):
            print(f"⚠️  ALERT: Critical issue found in {md_file.name}")
            return True
    return False

if __name__ == "__main__":
    has_critical = check_critical_issues(review_dir)
    exit(1 if has_critical else 0)  # CI/CDで使用可能
```

---

## Git運用規則

詳細は [GIT_WORKFLOW.md](../../git/chatdemo/GIT_WORKFLOW.md) を参照してください。

### 重要ポイント
- **コミットメッセージは日本語で記載**
- プレフィックス使用推奨（`feat:`, `fix:`, `docs:`, `refactor:` など）
- コミット前にWindows Vaultへの同期を確認

---

## トラブルシューティング

### リンク切れの検出
Obsidianの「リンク切れを表示」機能を使用するか、以下のスクリプトで検出：
```bash
# 存在しないファイルへのリンクを検出
grep -rho '\[\[[^]]*\]\]' docs/snowflake/chatdemo/design/ | \
  sort -u | \
  while read link; do
    file=$(echo "$link" | sed 's/\[\[\(.*\)\]\]/\1/')
    # ファイル存在チェックロジック
  done
```

### バッククォートの残存確認
```bash
# カラム名・パラメータ名のバッククォートを検出
grep -rn '`[A-Z_][A-Z_]*`' docs/snowflake/chatdemo/design/ | \
  grep -v 'AUTO_REFRESH\|logging\|user\|assistant'
```

### 命名規則違反の検出
```bash
# V_ プレフィックスがないビューを検出
cd docs/snowflake/chatdemo/master/views
ls -1 | grep -v '\.V_' | grep -v '^V_'

# MV_ プレフィックスがないマテリアライズドビューを検出
# （現在は該当なし）
```

---

## 参考資料

- [naming_conventions.md](naming_conventions.md) - 命名規則詳細
- [README.md](README.md) - プロジェクト概要
- [tests/scripts/README.md](../../tests/scripts/README.md) - スクリプト一覧

---

## 変更履歴

| 日付 | 変更内容 |
|------|---------|
| 2026-01-02 | 初版作成：命名規則、リンク規則、メンテナンス手順を定義 |
