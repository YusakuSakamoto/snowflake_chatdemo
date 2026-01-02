# Cortex Agent / Analyst ログ取得・モニタリング設計ガイド

本ドキュメントは、Cortex Analyst/Agentのログ取得・モニタリングに関する事実（仕様）と実務ノウハウ（やるべき設計）を体系的にまとめたものです。

---

## 1. Cortex Analyst Monitoring の正体

- Monitoring UI のログは `LOG.CORTEX_CONVERSATIONS` ではなく、**テーブル関数**から取得する：

```sql
SNOWFLAKE.LOCAL.CORTEX_ANALYST_REQUESTS(
  'FILE_ON_STAGE',
  '@<db>.<schema>.<stage>/<path>/<semantic_model>.yaml'
)
```
- これは完了後のサマリログ（成功/失敗、質問、生成SQL、エラー等）
- **途中経過は含まれない**

---

## 2. REQUEST_ID の意味

- `REQUEST_ID` = Cortex Analyst が1回の解析実行に付与する内部ID
- Monitoring UI の1行 = 1 REQUEST_ID
- 同じ質問でも再実行すれば別 REQUEST_ID

| ID | 意味 |
|----|------|
| conversation_id | 会話スレッド単位（Agent / API 側） |
| analyst request_id | Analyst 実行単位（Monitoring） |

- conversation_id : request_id = 1 : N
- REST API の request_id / trace_id とは別物

---

## 3. LOG.CORTEX_CONVERSATIONS が使えない理由

- LOG.CORTEX_CONVERSATIONS は Cortex Agent 系 or 別用途のログ
- Analyst Monitoring の公式取得先ではない
- Analyst の精度改善目的では誤った入口

---

## 4. Cortex REST API のレスポンス仕様

### 4.1 非ストリーミング（stream=false）
- 最終結果のみ返却
- 途中経過はすべて失われる
- 精度改善・デバッグには不十分

### 4.2 ストリーミング（stream=true）
- Server-Sent Events (SSE)
- `Content-Type: text/event-stream`
- イベントが順次流れる

主な event_type:
- `status`：進行フェーズ
- `message.content.delta`：生成途中のテキスト断片（超重要）
- `tool_call` / `tool_result`：Agent 内ツール実行
- `warnings`：精度劣化の前兆
- `response_metadata`：ここに analyst request_id が出ることがある
- `done`：終了

---

## 5. 「途中経過ログ」を全量取得する唯一の方法

- Snowflake 側で途中経過を自動保存する仕組みはない
- Monitoring は「結果サマリ専用」
- ➡ **REST API を stream=true（SSE）で呼び、クライアント側ですべて保存するしかない**

---

## 6. Python (requests) での正しい SSE 受信方法

```python
with requests.post(url, headers=headers, json=payload, stream=True) as r:
    for line in r.iter_lines(decode_unicode=True):
        if line.startswith("event:"):
            event_type = ...
        elif line.startswith("data:"):
            payload = ...
            # ここで必ずログ保存
```
- `.json()` は使ってはいけない（SSEは1つのJSONではない）

---

## 7. 精度向上のためのログ設計（実務ノウハウ）

- SSEイベント1件 = 1ログレコード（正規化しない、VARIANTで丸ごと）
- 推奨ログ項目：
    - conversation_id
    - analyst_request_id（response_metadata から）
    - event_type
    - payload（JSON丸ごと）
    - event_ts / ingested_at

---

## 8. S3 × Snowflake 連携の王道パターン

1. Agent REST API を SSEで呼ぶ
2. SSEイベントをNDJSONでS3に保存
3. Snowflake External Stage を作成
4. Snowpipe / COPY INTO で VARIANT 取り込み
5. Monitoring（CORTEX_ANALYST_REQUESTS）と JOIN

---

## 9. 最強の運用構成（結論）

- **SSE全量ログ**：途中経過、迷い、警告、ツール呼び出しを完全保存
- **CORTEX_ANALYST_REQUESTS**：成功率、生成SQL、エラー率の公式サマリ
- この2つを conversation_id × analyst_request_id で結ぶことで、Agent / Analyst の精度改善が「勘」ではなく「工学」になる

---

## 10. 核心メッセージ

- 精度向上に本当に必要なのは最終回答ではない
- `message.content.delta` がどう積み上がったか
- それを取れるかどうかはSSEを正しく処理しているかで決まる

---

> 本ガイドはCortex Agent/Analystのログ設計・運用のベストプラクティスをまとめたものです。詳細な運用ルール・命名規則は[MAINTENANCE_GUIDE.md](MAINTENANCE_GUIDE.md)等を参照してください。
