# S3ストレージ設計：LOG外部テーブル用データレイク

## 概要
本ドキュメントは、Snowflake LOGスキーマの外部テーブルが参照する AWS S3 バケットの設計を定義する。

4つの外部テーブル（CORTEX_CONVERSATIONS、AZFUNCTIONS_LOGS、AZSWA_LOGS、SNOWFLAKE_METRICS）のログデータを、S3に長期保管し、Snowflakeから効率的にクエリできる構造を設計する。

## 設計目標
1. コスト最適化：S3ストレージコストとSnowflakeコンピュートコストの最小化
2. クエリ効率：パーティションプルーニングによる高速クエリ
3. 運用性：自動化されたログ収集・ライフサイクル管理
4. セキュリティ：IAMポリシーと暗号化によるデータ保護
5. スケーラビリティ：データ量の増加に対する拡張性

## S3バケット構造

### バケット名
```
s3://135365622922-snowflake-chatdemo-logs-prod/
```

- AWS Account ID: `135365622922`
- 環境: `prod`

### ディレクトリ階層
```
135365622922-snowflake-chatdemo-logs-prod/
├── cortex_conversations/           # Cortex Agent会話ログ
│   └── year=2026/
│       └── month=01/
│           └── day=02/
│               └── hour=14/
│                   ├── 20260102-140523-abc123.json
│                   ├── 20260102-140615-def456.json
│                   └── ...
├── azfunctions/                    # Azure Functions APIログ
│   └── year=2026/
│       └── month=01/
│           └── day=02/
│               └── hour=14/
│                   ├── 20260102-140501-ghi789.json
│                   └── ...
├── azswa/                          # Azure SWA アクセスログ
│   └── year=2026/
│       └── month=01/
│           └── day=02/
│               └── hour=14/
│                   ├── 20260102-140502-jkl012.json
│                   └── ...
├── snowflake_metrics/              # Snowflake メトリクス
│   └── year=2026/
│       └── month=01/
│           └── day=02/
│               └── hour=14/
│                   ├── 20260102-140000-mno345.json
│                   └── ...
└── _backup/                        # バックアップ・アーカイブ用（任意）
```

### パーティション戦略

#### Hive形式のパーティション
- 形式：`year=YYYY/month=MM/day=DD/hour=HH/`
- 理由：Snowflake External Tableの`PARTITION BY`が`key=value`形式を認識
- パーティションプルーニング：WHERE句で`year`, `month`, `day`, `hour`を指定することで、必要なファイルのみスキャン

#### パーティション粒度の選択理由
- 時間単位（hour）：
  - 利点：クエリ範囲を細かく絞り込める、ファイルサイズが適切（数MB〜数十MB）
  - 欠点：ディレクトリ数が多くなる（LIST操作のコスト）
- 日単位（day）ではない理由：
  - 1日分のログが巨大になる可能性（特にアクセスログ）
  - 時間帯別の分析（ピーク時間帯の特定）が重要
- 分単位（minute）ではない理由：
  - ディレクトリ数が爆発的に増加
  - ファイルサイズが小さくなりすぎる（small file problem）

## ファイル命名規則

### 命名パターン
```
{YYYYMMDD}-{HHMMSS}-{uuid}.json
```

- YYYYMMDD：日付（パーティションと重複するが、ファイル単位での識別に便利）
- HHMMSS：時刻（秒単位）
- uuid：一意識別子（8文字の短縮UUID）
- 拡張子：`.json`（JSON Lines形式）

### 例
```
20260102-140523-abc123de.json
```

### 命名規則の利点
- ファイル名のソートで時系列順になる
- タイムスタンプから生成時刻が明確
- UUIDで衝突回避（複数のログライターが並行書き込みしても安全）

## ファイルフォーマット

### JSON Lines（NDJSON）
各ログエントリは1行の JSON オブジェクトとして記録される。

#### フォーマット例（cortex_conversations）
```json
{"conversation_id":"conv-123","session_id":"sess-456","user_id":"user-789","agent_name":"SNOWFLAKE_DEMO_AGENT","message_role":"user","message_content":{"text":"営業部の売上は？","tokens":12},"timestamp":"2026-01-02T14:05:23Z","metadata":{"ip":"192.168.1.100","user_agent":"Mozilla/5.0"}}
{"conversation_id":"conv-123","session_id":"sess-456","user_id":"user-789","agent_name":"SNOWFLAKE_DEMO_AGENT","message_role":"assistant","message_content":{"text":"営業部の売上は1,234万円です。","tokens":28,"latency_ms":1200},"timestamp":"2026-01-02T14:05:25Z","metadata":{"model":"mistral-large"}}
```

#### フォーマット選択理由
- 追記専用（Append-Only）に最適：新しいログを行単位で追記可能
- スキーマレス：VARIANT型で柔軟にメタデータを格納
- 圧縮効率：gzip圧縮で70-80%削減
- パース効率：Snowflakeの半構造化データ処理に最適

### 圧縮形式
- 圧縮：gzip（`.json.gz` も検討）
- 圧縮レベル：6（デフォルト、バランス型）
- 非圧縮の場合：リアルタイム性が必要な直近データのみ

## ライフサイクルポリシー

### ストレージクラスの移行

#### Tier 1：ホットデータ（直近30日）
- ストレージクラス：S3 Standard
- アクセス頻度：高頻度（日次クエリ）
- 料金：$0.023/GB/月（us-east-1）
- 対象：全テーブル

#### Tier 2：ウォームデータ（31-90日）
- ストレージクラス：S3 Standard-IA（Infrequent Access）
- アクセス頻度：週次程度
- 料金：$0.0125/GB/月
- 取得料金：$0.01/GB（アクセス時）
- 対象：cortex_conversations, azfunctions, azswa

#### Tier 3：コールドデータ（91-365日）
- ストレージクラス：S3 Intelligent-Tiering
- アクセス頻度：月次程度
- 料金：自動最適化（$0.0025-0.023/GB/月）
- 対象：全テーブル

#### Tier 4：アーカイブ（1年超）
- ストレージクラス：S3 Glacier Flexible Retrieval
- アクセス頻度：監査・コンプライアンス用（ほぼアクセスなし）
- 料金：$0.004/GB/月
- 取得時間：数時間〜12時間
- 対象：cortex_conversations, azfunctions, azswa（snowflake_metricsは削除）

### ライフサイクルルール定義

```json
{
  "Rules": [
    {
      "Id": "TransitionToIA",
      "Status": "Enabled",
      "Prefix": "",
      "Transitions": [
        {
          "Days": 30,
          "StorageClass": "STANDARD_IA"
        }
      ]
    },
    {
      "Id": "TransitionToIntelligentTiering",
      "Status": "Enabled",
      "Prefix": "",
      "Transitions": [
        {
          "Days": 90,
          "StorageClass": "INTELLIGENT_TIERING"
        }
      ]
    },
    {
      "Id": "TransitionToGlacier",
      "Status": "Enabled",
      "Prefix": "",
      "Transitions": [
        {
          "Days": 365,
          "StorageClass": "GLACIER"
        }
      ]
    },
    {
      "Id": "DeleteMetricsAfter1Year",
      "Status": "Enabled",
      "Prefix": "snowflake_metrics/",
      "Expiration": {
        "Days": 365
      }
    }
  ]
}
```

### データ保持期間

| テーブル | 直近30日 | 31-90日 | 91-365日 | 1年超 |
|---------|---------|---------|----------|-------|
| CORTEX_CONVERSATIONS | Standard | Standard-IA | Intelligent-Tiering | Glacier |
| AZFUNCTIONS_LOGS | Standard | Standard-IA | Intelligent-Tiering | Glacier |
| AZSWA_LOGS | Standard | Standard-IA | Intelligent-Tiering | Glacier |
| SNOWFLAKE_METRICS | Standard | Standard-IA | Intelligent-Tiering | 削除 |

## セキュリティ設計

### 暗号化

#### サーバーサイド暗号化（SSE）
- 方式：SSE-S3（AES-256）
- 設定：バケットのデフォルト暗号化を有効化
- コスト：無料

```json
{
  "Rules": [
    {
      "ApplyServerSideEncryptionByDefault": {
        "SSEAlgorithm": "AES256"
      },
      "BucketKeyEnabled": true
    }
  ]
}
```

#### クライアントサイド暗号化（任意）
- PII（個人情報）を含むフィールドは、アプリケーション側で暗号化してから書き込み
- Snowflake側で復号化用のUDFを提供

### アクセス制御

#### IAMポリシー（Snowflake用）
Snowflake External TableがS3にアクセスするためのIAMロール：

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "s3:GetObject",
        "s3:GetObjectVersion",
        "s3:ListBucket"
      ],
      "Resource": [
        "arn:aws:s3:::snowflake-chatdemo-logs-prod",
        "arn:aws:s3:::snowflake-chatdemo-logs-prod/*"
      ]
    }
  ]
}
```

#### IAMポリシー（ログライター用）
Azure Functions / SWA がログを書き込むためのIAMユーザー：

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "s3:PutObject",
        "s3:PutObjectAcl"
      ],
      "Resource": [
        "arn:aws:s3:::snowflake-chatdemo-logs-prod/cortex_conversations/*",
        "arn:aws:s3:::snowflake-chatdemo-logs-prod/azfunctions/*",
        "arn:aws:s3:::snowflake-chatdemo-logs-prod/azswa/*",
        "arn:aws:s3:::snowflake-chatdemo-logs-prod/snowflake_metrics/*"
      ]
    }
  ]
}
```

### バケットポリシー
パブリックアクセスを完全にブロック：

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "DenyPublicAccess",
      "Effect": "Deny",
      "Principal": "*",
      "Action": "s3:*",
      "Resource": [
        "arn:aws:s3:::snowflake-chatdemo-logs-prod",
        "arn:aws:s3:::snowflake-chatdemo-logs-prod/*"
      ],
      "Condition": {
        "StringNotEquals": {
          "aws:PrincipalAccount": "123456789012"
        }
      }
    }
  ]
}
```

## コスト見積もり

### 前提条件
- 1日あたりのログ量：
  - CORTEX_CONVERSATIONS：100MB/日
  - AZFUNCTIONS_LOGS：500MB/日
  - AZSWA_LOGS：1GB/日
  - SNOWFLAKE_METRICS：200MB/日
- 合計：1.8GB/日 ≈ 54GB/月

### ストレージコスト（月次）

| 期間 | データ量 | ストレージクラス | 単価 | 月額コスト |
|------|---------|---------------|------|----------|
| 0-30日 | 54GB | S3 Standard | $0.023/GB | $1.24 |
| 31-90日 | 108GB | S3 Standard-IA | $0.0125/GB | $1.35 |
| 91-365日 | 486GB | Intelligent-Tiering | $0.01/GB（平均） | $4.86 |
| 1年超 | 640GB/年 | Glacier | $0.004/GB | $2.56/年 |

月次合計：約$7.45 + Glacier $0.21 = $7.66/月

### データ転送コスト
- S3 → Snowflake：同一リージョン内であれば無料（us-east-1同士など）
- クロスリージョン：$0.02/GB（us-east-1 → us-west-2の場合）

### API リクエストコスト
- LIST操作：$0.005 per 1,000 requests（External Table REFRESH時）
- GET操作：$0.0004 per 1,000 requests（クエリ時）
- PUT操作：$0.005 per 1,000 requests（ログ書き込み時）

月次推定：
- LIST：1,000回/日 × 30日 = 30,000回 → $0.15
- GET：10,000回/日（クエリ） × 30日 = 300,000回 → $0.12
- PUT：100,000回/日（ログ書き込み） × 30日 = 3,000,000回 → $15.00

API合計：約$15.27/月

### 総コスト見積もり
- ストレージ：$7.66/月
- API：$15.27/月
- 合計：約$23/月

## 運用設計

### ログ書き込みフロー

#### 1. Cortex Agent 会話ログ
```python
# Azure Functions内
import boto3
import json
from datetime import datetime, timezone

s3 = boto3.client('s3')

def write_conversation_log(conversation_data):
    now = datetime.now(timezone.utc)
    
    # パーティションパス生成
    partition_path = f"year={now.year}/month={now.month:02d}/day={now.day:02d}/hour={now.hour:02d}"
    
    # ファイル名生成
    filename = f"{now.strftime('%Y%m%d-%H%M%S')}-{uuid.uuid4().hex[:8]}.json"
    
    # S3キー
    s3_key = f"cortex_conversations/{partition_path}/{filename}"
    
    # JSON Lines形式で書き込み
    s3.put_object(
        Bucket='snowflake-chatdemo-logs-prod',
        Key=s3_key,
        Body=json.dumps(conversation_data) + '\n',
        ContentType='application/json',
        ServerSideEncryption='AES256'
    )
```

#### 2. Azure Functions ログ
Application Insights → Stream Analytics → S3 のパイプラインで自動転送。

#### 3. Azure SWA ログ
Azure Monitor → Event Hub → Azure Function → S3 のパイプラインで転送。

#### 4. Snowflake メトリクス
Snowflake Task で定期実行し、S3 に PUT。

### モニタリング

#### CloudWatch メトリクス
- BucketSize：バケットサイズの推移
- NumberOfObjects：オブジェクト数の推移
- AllRequests：API リクエスト数
- 4xxErrors / 5xxErrors：エラー率

#### アラート設定
```json
{
  "AlarmName": "HighS3ErrorRate",
  "MetricName": "4xxErrors",
  "Threshold": 100,
  "ComparisonOperator": "GreaterThanThreshold",
  "EvaluationPeriods": 2,
  "Period": 300
}
```

### バックアップ

#### クロスリージョンレプリケーション（任意）
- レプリケーション先：us-west-2（DR用）
- 対象：cortex_conversations のみ（重要度が高い）
- コスト：+$0.02/GB（転送） + ストレージ

注記：ログデータは追記専用（Append-Only）のため、バージョニングは不要。誤削除のリスクは IAM ポリシーとバケットポリシーで制御する。

## 拡張計画

### 1. リアルタイムストリーミング
Kinesis Data Firehose でリアルタイムにS3へ配信：
```
Azure Functions → Kinesis Firehose → S3 → Snowflake (AUTO_REFRESH)
```

利点：
- バッチ書き込みでS3 PUT APIコストを削減
- バッファリング（5分または5MB）で小ファイル問題を回避

### 2. データレイク統合
S3をデータレイクとして、複数の分析基盤から参照：
- Snowflake（現在）
- AWS Athena（SQL分析）
- Spark / Databricks（機械学習）
- QuickSight（BI可視化）

### 3. パーティション最適化
アクセスパターンに応じて、パーティション戦略を見直し：
- 日単位パーティション（ファイルサイズが大きい場合）
- カスタムパーティション（user_id別など）

### 4. コスト最適化
S3 Storage Lens でストレージ分析し、不要なデータを削除：
```sql
-- Snowflakeから古いパーティションを削除
ALTER EXTERNAL TABLE LOG.CORTEX_CONVERSATIONS
  DROP PARTITION (year=2025, month=1);
```

## 設計レビュー時のチェックポイント
- [ ] パーティション戦略が Snowflake の PARTITION BY と一致しているか
- [ ] ライフサイクルポリシーが適切に設定されているか
- [ ] IAMポリシーが最小権限の原則に従っているか
- [ ] 暗号化が有効化されているか（SSE-S3）
- [ ] コスト見積もりが予算内か（月$25以内を想定）
- [ ] モニタリング・アラートが設定されているか
- [ ] クロスリージョンレプリケーション（DR）の必要性を検討したか

## 参考リンク
- AWS S3 Pricing: https://aws.amazon.com/s3/pricing/
- Snowflake External Tables: https://docs.snowflake.com/en/sql-reference/sql/create-external-table
- S3 Lifecycle Configuration: https://docs.aws.amazon.com/AmazonS3/latest/userguide/object-lifecycle-mgmt.html
