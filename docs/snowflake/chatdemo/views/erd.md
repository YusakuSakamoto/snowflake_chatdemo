


```dataviewjs
(async () => {
const SCHEMA_PATH = "master/schemas";
const TABLE_PATH  = "master/tables";
const COLUMN_PATH = "master/columns";
const VIEW_PATH   = "master/views";

const schemas = dv.pages(`"${SCHEMA_PATH}"`).where(p => p.schema_id && p.physical);
const tables  = dv.pages(`"${TABLE_PATH}"`).where(p => p.table_id && p.schema_id && p.physical);
const cols    = dv.pages(`"${COLUMN_PATH}"`).where(p => p.column_id && p.table_id && p.physical);
const views   = dv.pages(`"${VIEW_PATH}"`).where(p => p.view_id && p.schema_id && p.physical);

// maps
const schemaById = new Map(schemas.array().map(s => [String(s.schema_id), s]));
const tableById  = new Map(tables.array().map(t => [String(t.table_id), t]));

// FQN helpers
function fqnOfTable(t){
  const sch = schemaById.get(String(t.schema_id));
  if (!sch) return null;
  return `${sch.physical}.${t.physical}`;
}
function fqnOfView(v){
  const sch = schemaById.get(String(v.schema_id));
  if (!sch) return null;
  return `${sch.physical}.${v.physical}`;
}
// Mermaid id ('.'嫌う)
function mId(fqn){ return String(fqn).replaceAll(".", "__"); }

function clean(v){ return v === null || v === undefined ? "" : String(v); }

// ---- view body parsers (same robust approach as DDL generator) ----
function parseViewColumnsFromBody(md) {
  md = String(md ?? "").replace(/\r\n/g, "\n").replace(/\r/g, "\n");
  const lines = md.split("\n");

  let headerIdx = -1;
  for (let i = 0; i < lines.length; i++) {
    const ln = lines[i].trim();
    if (!ln.includes("|")) continue;
    const cells = ln.split("|").map(s => s.trim()).filter(s => s !== "");
    const lower = cells.map(c => c.toLowerCase());
    const hasCol = lower.includes("column_name") || lower.includes("column") || lower.includes("name");
    const hasCmt = lower.includes("comment") || lower.includes("description");
    if (hasCol && hasCmt) { headerIdx = i; break; }
  }
  if (headerIdx < 0) return [];

  let sepIdx = -1;
  for (let i = headerIdx + 1; i < Math.min(lines.length, headerIdx + 6); i++) {
    const ln = lines[i].trim();
    if (ln.includes("|") && /-[-\s|:]+-/.test(ln)) { sepIdx = i; break; }
  }
  if (sepIdx < 0) return [];

  const headerCells = lines[headerIdx].split("|").map(s => s.trim()).filter(s => s !== "");
  const lowerHeader = headerCells.map(c => c.toLowerCase());
  const colIdx = lowerHeader.findIndex(h => h === "column_name" || h === "column" || h === "name");
  const cmtIdx = lowerHeader.findIndex(h => h === "comment" || h === "description");
  const cIdx = colIdx >= 0 ? colIdx : 0;
  const dIdx = cmtIdx >= 0 ? cmtIdx : 1;

  const out = [];
  for (let i = sepIdx + 1; i < lines.length; i++) {
    const ln = lines[i].trim();
    if (ln === "") break;
    if (!ln.includes("|")) break;
    if (/^\s*##\s+/.test(ln)) break;

    const rowCells = lines[i].split("|").map(s => s.trim()).filter(s => s !== "");
    const name = (rowCells[cIdx] ?? "").trim();
    const comment = (rowCells[dIdx] ?? "").trim();
    if (!name) continue;
    out.push({ name, comment });
  }
  return out;
}

function parseSqlFromBody(md){
  md = String(md ?? "").replace(/\r\n/g, "\n").replace(/\r/g, "\n");
  const m = md.match(/```sql\s*([\s\S]*?)```/i);
  return m ? (m[1] ?? "").trim() : "";
}

// ざっくり依存抽出：FROM/JOIN の直後の識別子を拾う（別名は落とす）
function extractDepsFromSql(sql){
  const s = String(sql ?? "");
  // コメント除去（雑に）
  const noLineComments = s.replace(/--.*$/gm, "");
  const noBlockComments = noLineComments.replace(/\/\*[\s\S]*?\*\//g, "");

  const deps = new Set();
  const re = /\b(from|join)\s+([a-zA-Z0-9_."]+)/gi;
  let m;
  while ((m = re.exec(noBlockComments)) !== null) {
    let tok = m[2];
    tok = tok.replaceAll('"', "").trim();
    // サブクエリ from (select...) は除外
    if (tok.startsWith("(")) continue;
    // カンマ付き等を除外
    tok = tok.replace(/[;,]/g, "");
    if (tok) deps.add(tok);
  }
  return Array.from(deps);
}

// テーブル名を FQN っぽく解決：
// - もし "SCHEMA.TABLE" ならそのまま
// - もし "TABLE" なら "VIEWと同じschema.TABLE" を試す
function resolveTableFqn(token, viewSchemaPhysical){
  const t = token.replaceAll('"', "");
  if (t.includes(".")) {
    // db.schema.table は長すぎるので最後2要素を採用（必要なら拡張）
    const parts = t.split(".").filter(Boolean);
    if (parts.length >= 2) return parts.slice(-2).join(".");
    return t;
  }
  // bare table name
  return `${viewSchemaPhysical}.${t}`;
}

// -------------------- build ERD --------------------
let warns = [];
let out = [];
out.push("erDiagram");

// ---- entities: TABLES ----
for (const t of tables.array()) {
  const name = fqnOfTable(t);
  if (!name) {
    warns.push(`table_id=${t.table_id} unknown schema_id=${t.schema_id}`);
    continue;
  }
  out.push(`  ${mId(name)} {`);
  const myCols = cols.array().filter(c => String(c.table_id) === String(t.table_id));
  const pkCols = myCols.filter(c => c.pk === true);
  const fkCols = myCols.filter(c => c.ref_table_id);

  const pick = [...pkCols, ...fkCols].slice(0, 50);
  for (const c of pick) {
    const typ = (c.domain ?? "VARCHAR").toString().replace(/\s+/g,"_");
    const tag = c.pk ? " PK" : (c.ref_table_id ? " FK" : "");
    out.push(`    ${typ} ${c.physical}${tag}`);
  }
  out.push(`  }`);
}

// ---- entities: VIEWS ----
for (const v of views.array()) {
  const vfqn = fqnOfView(v);
  if (!vfqn) {
    warns.push(`view_id=${v.view_id} unknown schema_id=${v.schema_id}`);
    continue;
  }

  // load body
  let md = "";
  try {
    md = await dv.io.load(v.file.path);
  } catch (e) {
    warns.push(`view_id=${v.view_id} failed to load (${v.file?.path})`);
    continue;
  }

  const vcols = parseViewColumnsFromBody(md);
  if (vcols.length === 0) {
    warns.push(`view_id=${v.view_id} has no View Columns table (${v.file?.path})`);
  }

  out.push(`  ${mId(vfqn)} {`);
  for (const c of vcols.slice(0, 50)) {
    // VIEWは型不明なので "STRING" 固定表記（ERD表示用）
    out.push(`    STRING ${c.name}`);
  }
  out.push(`  }`);
}

// ---- relations: TABLE FK ----
for (const c of cols.array().filter(c => c.ref_table_id)) {
  const fromT = tableById.get(String(c.table_id));
  const toT   = tableById.get(String(c.ref_table_id));

  if (!fromT) { warns.push(`column_id=${c.column_id} unknown table_id=${c.table_id}`); continue; }
  if (!toT)   { warns.push(`column_id=${c.column_id} unknown ref_table_id=${c.ref_table_id}`); continue; }

  const from = fqnOfTable(fromT);
  const to   = fqnOfTable(toT);
  if (!from || !to) continue;

  const card = (c.ref_cardinality ?? "N:1").toString();
  const label = `${c.physical} -> ${c.ref_column ?? "?"} (${card})`;

  out.push(`  ${mId(from)} }o--|| ${mId(to)} : "${label}"`);
}

// ---- relations: VIEW depends on TABLE (from SQL FROM/JOIN) ----
for (const v of views.array()) {
  const vfqn = fqnOfView(v);
  if (!vfqn) continue;

  const sch = schemaById.get(String(v.schema_id));
  const viewSchemaPhysical = sch?.physical;
  if (!viewSchemaPhysical) continue;

  let md = "";
  try { md = await dv.io.load(v.file.path); } catch { continue; }

  const sql = parseSqlFromBody(md);
  if (!sql) {
    warns.push(`view_id=${v.view_id} has no SQL block (${v.file?.path})`);
    continue;
  }

  const deps = extractDepsFromSql(sql);
  for (const d of deps) {
    const tfqn = resolveTableFqn(d, viewSchemaPhysical);

    // そのテーブルが master/tables に存在する時だけ線を引く（ノイズ低減）
    const exists = tables.array().some(t => fqnOfTable(t) === tfqn);
    if (!exists) continue;

    // Mermaid ERDは本来リレーション用なので、依存はラベルで表現（1..*等は意味を持たない）
    out.push(`  ${mId(vfqn)} }o--o{ ${mId(tfqn)} : "depends"`);
  }
}

// render
dv.paragraph("```mermaid\n" + out.join("\n") + "\n```");

if (warns.length) {
  dv.header(3, "Warnings");
  dv.list(warns.map(w => `⚠️ ${w}`));
}
})();

```