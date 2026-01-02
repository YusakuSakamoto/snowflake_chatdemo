# Snowflake × Amazon S3 連携ノウハウ・設計原則まとめ

---

## 1. Snowflake から S3 に接続する基本原則

- Snowflake は **IAM Role 経由**で S3 にアクセスする（Access Key / Secret Key の直接指定は非推奨）
- Snowflake 側では **Storage Integration** を作成し、それを使って **External Stage** を定義する
- 実体としての接続制御・境界は **AWS IAM** にある

> 本質：
> **「Snowflake は IAM Role を Assume して S3 に入る」**

---

## 2. 接続手順の全体像

1. AWS 側で IAM Role を作成（S3 の `GetObject / PutObject / ListBucket` 等を許可）
2. Snowflake で Storage Integration を作成
3. `DESC STORAGE INTEGRATION` で取得した
   - `STORAGE_AWS_IAM_USER_ARN`
   - `STORAGE_AWS_EXTERNAL_ID`
   を IAM Role の信頼ポリシーに設定
4. Snowflake で External Stage を作成
5. `COPY INTO` 等でデータ連携

---

## 3. Storage Integration の役割

- Storage Integration は **「S3 への権限の器」**
- Stage は Integration を参照するだけ
- Integration 自体が **アクセス可能な S3 パスの上限**を定義する

```sql
CREATE STORAGE INTEGRATION s3_int
  TYPE = EXTERNAL_STAGE
  STORAGE_PROVIDER = S3
  ENABLED = TRUE
  STORAGE_AWS_ROLE_ARN = 'arn:aws:iam::123456789012:role/snowflake-role'
  STORAGE_ALLOWED_LOCATIONS = (
    's3://bucket-a/data/',
    's3://bucket-b/logs/'
  );
```

---

## 4. 複数 S3 バケットと Storage Integration の関係

### 結論
**複数バケットでも、1つの Storage Integration で問題ない。条件付きで。**

### 1つでまとめられる条件
- 同一 AWS アカウント
- 同一 IAM Role
- 権限レベル（Read / Write）が同じ
- セキュリティ境界を分ける必要がない

- `STORAGE_ALLOWED_LOCATIONS` には **複数 S3 パスを指定可能**
- Integration 1つに対して Stage は **何個でも作成可能**

---

## 5. Storage Integration を分けるべきケース

以下の場合は **Integration を分割するのが正解**：

- AWS アカウントが異なる
- IAM Role を分けたい
- Read 専用 / Write 可を明確に分離したい
- 監査・セキュリティ要件で用途分離が求められる
- 将来、片方だけ権限を落とす可能性がある

> 原則：
> **Integration は「後から割る」より「最初から割る」ほうが楽**

---

## 6. よくある誤解・落とし穴

- バケットごとに必ず Integration が必要だと思ってしまう
- Stage ごとに Integration が必要だと思ってしまう
- Snowflake 側でパス制御しているつもりになる

**実際の境界線は IAM Role と S3 ポリシー**。

---

## 7. 実務的な設計ベストプラクティス

| レイヤ | 分割単位 |
|------|---------|
| Storage Integration | 権限・セキュリティ境界 |
| External Stage | 用途・テーブル・処理単位 |
| S3 Prefix | データ種別・ドメイン単位 |

---

## 8. 要点の一文要約

- Snowflake × S3 連携は **認証と権限設計が9割**
- 同じ鍵（IAM Role）で開けるなら Integration は1つ
- 鍵を分けたいなら Integration を分ける

---

> 本ドキュメントは [[awss3.S3_DESIGN_VAULT_DB_DOCS]] および [[awss3.S3_DESIGN_LOG_EXTERNAL_TABLES]] の設計・運用知見をもとにまとめています。

---

（記載場所：docs/snowflake/chatdemo/README.md 末尾、または新規「S3連携設計ノウハウ」セクション推奨）
