<%*
/**
 * Design template for TABLE
 * - moves file to design/
 * - no YAML properties
 */
const folder = "design";
const title = tp.file.title;

// 配置先を design/ に強制
await tp.file.move(`${folder}/${title}.md`);
-%>
# テーブル設計：<テーブル名>

## 概要
[[master/tables/TBL_xxx.md|<物理名>]] は、〜を管理するテーブルである。

## 業務上の意味
- このテーブルが表す概念
- どの業務で使われるか

## 設計方針
- 主キーの選定理由
- Snowflake 前提の考慮点

## 注意点
- NULL可否の考え方
- 将来拡張の余地

## 関連
- Schema：[[master/schemas/SCH_xxx.md|<schema>]]
- Columns：
  - [[master/columns/COL_xxx.md|<column>]]
