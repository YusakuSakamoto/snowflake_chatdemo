<%*
/**
 * Design template for SCHEMA
 * - moves file to design/
 */
const folder = "design";
const title = tp.file.title;

await tp.file.move(`${folder}/${title}.md`);
-%>
# スキーマ設計：<schema名>

## 概要
[[master/schemas/SCH_xxx.md|<schema>]] は、〜用途のスキーマである。

## 役割
- このスキーマに配置するテーブルの性質
- セキュリティ・権限の考え方

## 設計方針
- スキーマ分割の理由
- Snowflake での運用前提

## 注意点
- schema 跨ぎ参照の扱い
- 将来のスキーマ追加方針
