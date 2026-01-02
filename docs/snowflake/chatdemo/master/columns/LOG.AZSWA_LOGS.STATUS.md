# LOG.AZSWA_LOGS.STATUS

- domain: VARCHAR
- nullable: true
- comment: リクエスト処理状態（RUNNING/SUCCEEDED/FAILED）
- check: STATUS IN ('RUNNING', 'SUCCEEDED', 'FAILED')
- design_judgement: 許可値はRUNNING, SUCCEEDED, FAILEDのみ。状態遷移はRUNNING→SUCCEEDED|FAILEDのみ許容。不正値混入防止のためCHECK制約を設計。
- obsidian_link: [[LOG.AZSWA_LOGS.STATUS]]
