<%*
const folder = "design";
const title = tp.file.title;

await tp.file.move(`${folder}/${title}.md`);
-%>
# カラム設計：<column名>

## 概要
[[master/columns/COL_xxx.md|<column>]] は、〜を表すカラムである。

## 設計意図
- なぜこの型なのか
- なぜ NULL 可 / 不可なのか

## 注意点
- 値の制約
- 利用時の注意
