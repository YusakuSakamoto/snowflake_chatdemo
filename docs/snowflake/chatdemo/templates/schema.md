<%*
/**
 * Schema template (Snowflake)
 * - schema_id: SCH_YYYYMMDDHHmmss
 * - filename: <physical>.md
 * - moves file to master/schemas/
 */
const folder = "master/schemas";

function safeFileName(name){
  return String(name ?? "SCHEMA")
    .trim()
    .replaceAll("/", "_")
    .replaceAll("\\", "_")
    .replaceAll(":", "_");
}

const schemaId = "SCH_" + tp.date.now("YYYYMMDDHHmmss");
const physicalRaw = await tp.system.prompt("物理名（例: PUBLIC）");
const physical = safeFileName(physicalRaw);
const comment  = await tp.system.prompt("comment（任意）") ?? "";

// 配置先＋ファイル名を physical にする
await tp.file.move(`${folder}/${physical}`);
-%>
---
type: schema
schema_id: <%- schemaId %>
physical: <%- physicalRaw %>
comment: <%- comment %>
---

# <%- physicalRaw %>
