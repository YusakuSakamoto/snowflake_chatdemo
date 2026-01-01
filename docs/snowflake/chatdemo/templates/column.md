<%*
/**
 * Column template
 * - table_id selectable (shows table physical + schema physical)
 * - filename: <schema>.<table>.<column>.md
 * - moves file to master/columns/
 */
const folder = "master/columns";
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
const schemas = dv.pages('"master/schemas"')
  .where(s => s.schema_id && s.physical)
  .array();
const schemaMap = new Map(schemas.map(s => [s.schema_id, s.physical]));

// ---------- load tables ----------
const tables = dv.pages('"master/tables"')
  .where(t => t.table_id && t.physical && t.schema_id)
  .array();
if (tables.length === 0) {
  new Notice("table が存在しません");
  throw new Error("No table");
}

// 表示用（補足情報付き）
const tableDisplay = tables.map(t =>
  `${t.table_id}  |  ${t.physical}  |  ${schemaMap.get(t.schema_id) ?? t.schema_id}`
);
const tableIds = tables.map(t => t.table_id);

// ---------- select table ----------
const tableId = await tp.system.suggester(
  tableDisplay,
  tableIds,
  false,
  "table を選択（table_id | table physical | schema physical）"
);

// 選択した table を取得
const table = tables.find(t => t.table_id === tableId);
const schemaPhysical = safe(schemaMap.get(table.schema_id) ?? table.schema_id);
const tablePhysical  = safe(table.physical);

// ---------- inputs ----------
const columnId = "COL_" + tp.date.now("YYYYMMDDHHmmss");
const physicalRaw = await tp.system.prompt("物理名（例: USER_ID）");
const columnPhysical = safe(physicalRaw);

const domain = await tp.system.prompt(
  "domain（例: VARCHAR / NUMBER / TIMESTAMP_NTZ / BOOLEAN）",
  "VARCHAR"
);

const pkStr       = "false";
const nullableStr = "true";
const defaultVal  = await tp.system.prompt("DEFAULT（任意。例: CURRENT_TIMESTAMP()）") ?? "";
const comment     = await tp.system.prompt("comment（任意）") ?? "";

const pk = String(pkStr).toLowerCase() === "true";
const isNullable = String(nullableStr).toLowerCase() === "true";

// ---------- move file ----------
// schema.table.column.md
const fileName = `${schemaPhysical}.${tablePhysical}.${columnPhysical}`;
await tp.file.move(`${folder}/${fileName}`);
-%>
---
type: column
column_id: <%- columnId %>
table_id: <%- tableId %>
physical: <%- physicalRaw %>
domain: <%- domain %>
pk: <%- pk %>
is_nullable: <%- isNullable %>
default: <%- defaultVal %>
comment: <%- comment %>
---

# <%- physicalRaw %>
