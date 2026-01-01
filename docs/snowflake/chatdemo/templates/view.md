<%*
/**
 * View template (Snowflake) - Recommended (最適解)
 * - YAML (Properties) keeps only machine-truth minimal fields:
 *   type / view_id / schema_id / physical / comment
 * - VIEW columns & SQL are written in BODY (Markdown), not YAML
 *   (because Obsidian Properties UI is weak for list-of-objects + multiline)
 *
 * - schema_id selectable (shows schema physical)
 * - filename: <schemaPhysical>.<viewPhysical>.md
 * - moves file to master/views/
 */
const folder = "master/views";
const dv = app.plugins.plugins["dataview"]?.api;
if (!dv) { new Notice("Dataview が見つかりません"); throw new Error("Dataview not found"); }

function safe(name){
  return String(name ?? "")
    .trim()
    .replaceAll("/", "_")
    .replaceAll("\\", "_")
    .replaceAll(":", "_");
}

// ---------- load schemas ----------
const schemaPages = dv.pages('"master/schemas"')
  .where(s => s.schema_id && s.physical)
  .array();

if (schemaPages.length === 0) {
  new Notice("schema が存在しません");
  throw new Error("No schema");
}

// 表示用（schema_id | physical）
const schemaDisplay = schemaPages.map(s => `${s.schema_id}  |  ${s.physical}`);
const schemaIds     = schemaPages.map(s => s.schema_id);

// ---------- select schema ----------
const schemaId = await tp.system.suggester(
  schemaDisplay,
  schemaIds,
  false,
  "schema を選択（schema_id | schema physical）"
);

const schema = schemaPages.find(s => s.schema_id === schemaId);
const schemaPhysical = safe(schema?.physical ?? schemaId);

// ---------- inputs ----------
const viewId = "VW_" + tp.date.now("YYYYMMDDHHmmss");

const physicalRaw = await tp.system.prompt("物理名（例: V_CUSTOMER_MASTER）");
const viewPhysical = safe(physicalRaw);

const comment = (await tp.system.prompt("comment（任意）")) ?? "";

// ---------- move file ----------
const fileName = `${schemaPhysical}.${viewPhysical}`;
await tp.file.move(`${folder}/${fileName}`);
-%>
---
type: view
view_id: <%- viewId %>
schema_id: <%- schemaId %>
physical: <%- physicalRaw %>
comment: <%- comment %>
---

# <%- physicalRaw %>

## View Columns
> ここは VIEW の括弧内定義（列名＋列コメント）を書く（型は不要）

| column_name | comment |
|---|---|
| CUSTOMER_ID | 取引先ID |
| CUSTOMER_NAME | 取引先名 |
| ACTIVE_FLAG | 有効無効フラグ |

## SQL
```sql
SELECT
  customer_id,
  ANY_VALUE(customer_name) AS customer_name,
  MAX(active_flag) AS active_flag
FROM ANKEN_MEISAI
WHERE customer_id IS NOT NULL
GROUP BY customer_id
```
