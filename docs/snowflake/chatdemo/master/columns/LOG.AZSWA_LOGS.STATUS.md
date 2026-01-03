---
column: STATUS
domain: VARCHAR
nullable: true
comment: リクエスト処理状態（RUNNING/SUCCEEDED/FAILED）
design_judgement: 許可値はRUNNING, SUCCEEDED, FAILEDのみ。状態遷移はRUNNING→SUCCEEDED|FAILEDのみ許容。不正値混入防止はアプリケーション側で担保。外部テーブルのためCHECK制約は未記載。
obsidian_link: [[LOG.AZSWA_LOGS.STATUS]]
---
