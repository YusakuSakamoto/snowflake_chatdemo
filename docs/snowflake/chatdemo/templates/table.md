<%*
/**
 * Table template (Snowflake)
 * - schema_id selectable (shows schema physical)
 * - filename: <schema>.<table>.md
 * - moves file to master/tables/
 */
const folder = "master/tables";
const dv = app.plugins.plugins["dataview"]?.api;
if (!dv) { new Notice("Dataview が見つかりません"); throw new Error("Dataview not found"); }

function safe(name){
  return String(name ?? "")
    .trim()
    .replaceAll("/", "_")
    .replaceAll("\\", "_")
    .replaceAll(":", "_");
}

// schema 一覧（schema_id + physical）
const schemaPages = dv.pages('"master/schemas"')
  .where(s => s.schema_id && s.physical)
  .array();

if (schemaPages.length === 0) {
  new Notice("schema が存在しません");
  throw new Error("No schema");
}

// 表示（補足情報付き）と実値（schema_id）
const schemaDisplay = schemaPages.map(s => `${s.schema_id}  |  ${s.physical}`);
const schemaIds     = schemaPages.map(s => s.schema_id);

// 選択（戻り値は schema_id）
const schemaId = await tp.system.suggester(
  schemaDisplay,
  schemaIds,
  false,
  "schema を選択（schema_id | schema physical）"
);

// 選択した schema の physical を引く
const schema = schemaPages.find(s => s.schema_id === schemaId);
const schemaPhysical = safe(schema?.physical ?? schemaId);

// 入力
const tableId  = "TBL_" + tp.date.now("YYYYMMDDHHmmss");
const physicalRaw = await tp.system.prompt("物理名（例: USERS）");
const tablePhysical = safe(physicalRaw);
const comment  = await tp.system.prompt("comment（任意）") ?? "";

// ファイル名：schema.table.md
const fileName = `${schemaPhysical}.${tablePhysical}`;

// 配置先＋ファイル名
await tp.file.move(`${folder}/${fileName}`);
-%>
---
type: table
table_id: <%- tableId %>
schema_id: <%- schemaId %>
physical: <%- physicalRaw %>
comment: <%- comment %>
---

# <%- physicalRaw %>
