# DDL Generator

このファイルは、Snowflakeの各種DDLを一括生成するための統合ビューです。

## 事前準備：DB・WHの作成

DDL生成の前に、まずデータベースとウェアハウスを作成してください。

```sql
USE ROLE ACCOUNTADMIN;
CREATE DATABASE IF NOT EXISTS GBPS253YS_DB;
CREATE OR REPLACE WAREHOUSE GBPS253YS_WH WITH
     WAREHOUSE_SIZE='X-SMALL'
     AUTO_SUSPEND = 120
     AUTO_RESUME = TRUE
     INITIALLY_SUSPENDED=TRUE;
     
USE DATABASE GBPS253YS_DB;
USE WAREHOUSE GBPS253YS_WH;

DROP SCHEMA PUBLIC;
```

---

## 生成可能なDDL

1. **Snowflake DDL Generator** - スキーマ、テーブル、ビュー、プロシージャなど（セマンティックビューはコメントでYAML出力）
2. **External Tables DDL Generator** - S3/Azure連携の外部テーブル
3. **YAML FILE Generator** - セマンティックビューのYAMLファイル生成

> **Note:** セマンティックビュー（YAML）は、Snowflake DDL Generatorではコメント形式で出力されます。  
> 実際のYAMLファイルとして出力する場合は、YAML FILE Generatorを使用してください。

---

## 1. Snowflake DDL Generator

```dataviewjs
(async () => {
  // ==============================
  // Snowflake DDL Generator (FAST + COPY + FILE OUTPUT)
  // ==============================

  // paths
  const SCHEMAS_PATH = "master/schemas";
  const TABLES_PATH  = "master/tables";
  const COLUMNS_PATH = "master/columns";
  const VIEWS_PATH   = "master/views";
  const SEMANTIC_VIEWS_PATH = "master/semanticviews";
  const OTHER_PATH   = "master/other";

  // options
  const QUOTE_IDENT     = false;
  const EMIT_COMMENTS   = true;
  const IO_CONCURRENCY  = 8;     // VIEW/OTHER の md 読み込み並列数（増やしすぎ注意）
  const RUN_ON_LOAD     = false; // true にするとノート表示時に自動生成（重いなら false 推奨）

  // output
  const OUTPUT_FOLDER   = "generated/ddl";           // Vault 内フォルダ
  const OUTPUT_PREFIX   = "snowflake_ddl";           // 例: snowflake_ddl_20251227_235959.sql
  const WRITE_SQL_FILE  = true;                       // Vault へ .sql 出力

  // ==============================
  // UI
  // ==============================
  dv.header(2, "Snowflake DDL Generator");
  const statusEl = dv.el("div", "準備完了（Generate を押してください）");

  const btnRow = dv.el("div", "");
  btnRow.style.display = "flex";
  btnRow.style.gap = "8px";
  btnRow.style.flexWrap = "wrap";

  const btnGenerate = document.createElement("button");
  btnGenerate.textContent = "Generate";
  btnRow.appendChild(btnGenerate);

  const btnCopy = document.createElement("button");
  btnCopy.textContent = "Copy to Clipboard";
  btnCopy.disabled = true;
  btnRow.appendChild(btnCopy);

  const btnOpenFile = document.createElement("button");
  btnOpenFile.textContent = "Open Output File";
  btnOpenFile.disabled = true;
  btnRow.appendChild(btnOpenFile);

  // Preview (textarea)
  const details = dv.el("details", "");
  const summary = document.createElement("summary");
  summary.textContent = "Preview（textarea：ここから手動コピーも可）";
  details.appendChild(summary);

  const ta = document.createElement("textarea");
  ta.readOnly = true;
  ta.style.width = "100%";
  ta.style.height = "360px";
  ta.style.fontFamily = "monospace";
  ta.placeholder = "Generate 後にここに DDL を表示します";
  details.appendChild(ta);

  // state
  let lastDDL = "";
  let lastFilePath = "";

  // ==============================
  // helpers
  // ==============================
  function q(name) {
    if (!QUOTE_IDENT) return name;
    return `"${String(name).replaceAll('"', '""')}"`;
  }
  function clean(v) {
    return (v === null || v === undefined) ? "" : String(v);
  }
  function bool(v, def=false) {
    if (v === true || v === false) return v;
    if (typeof v === "string") return v.toLowerCase() === "true";
    return def;
  }
  function sqlStringLiteral(s) {
    return "'" + String(s).replaceAll("'", "''") + "'";
  }
  function key2(schemaPhysical, tablePhysical) {
    return `${clean(schemaPhysical).toUpperCase()}|${clean(tablePhysical).toUpperCase()}`;
  }
  function hasDefault(v) {
    if (v === null || v === undefined) return false;
    const s = String(v).trim();
    if (s === "" || s.toLowerCase() === "null") return false;
    return true;
  }
  function normalizeLF(s){
    return String(s ?? "").replace(/\r\n/g, "\n").replace(/\r/g, "\n");
  }
  function parseSqlFromBody(md){
    md = normalizeLF(md);
    const m = md.match(/```sql\s*([\s\S]*?)```/i);
    return m ? (m[1] ?? "").trim() : "";
  }

  function parseViewColumnsFromBody(md) {
    md = normalizeLF(md);
    const lines = md.split("\n");

    let headerIdx = -1;
    for (let i = 0; i < lines.length; i++) {
      const ln = lines[i].trim();
      if (!ln.includes("|")) continue;
      const cells = ln.split("|").map(s => s.trim()).filter(Boolean);
      const lower = cells.map(c => c.toLowerCase());
      if (
        (lower.includes("column_name") || lower.includes("column") || lower.includes("name")) &&
        (lower.includes("comment") || lower.includes("description"))
      ) {
        headerIdx = i;
        break;
      }
    }
    if (headerIdx < 0) return [];

    let sepIdx = -1;
    for (let i = headerIdx + 1; i < Math.min(lines.length, headerIdx + 6); i++) {
      const ln = lines[i].trim();
      if (ln.includes("|") && /-[-\s|:]+-/.test(ln)) { sepIdx = i; break; }
    }
    if (sepIdx < 0) return [];

    const headerCells = lines[headerIdx].split("|").map(s => s.trim()).filter(Boolean);
    const lowerHeader = headerCells.map(c => c.toLowerCase());
    const colIdx = lowerHeader.findIndex(h => ["column_name","column","name"].includes(h));
    const cmtIdx = lowerHeader.findIndex(h => ["comment","description"].includes(h));
    const cIdx = colIdx >= 0 ? colIdx : 0;
    const dIdx = cmtIdx >= 0 ? cmtIdx : 1;

    const out = [];
    for (let i = sepIdx + 1; i < lines.length; i++) {
      const ln = lines[i].trim();
      if (!ln.includes("|")) break;
      if (ln === "") break;
      const cells = lines[i].split("|").map(s => s.trim()).filter(Boolean);
      const name = (cells[cIdx] ?? "").trim();
      const comment = (cells[dIdx] ?? "").trim();
      if (!name) continue;
      out.push({ name, comment });
    }
    return out;
  }

  function ts() {
    const d = new Date();
    const pad = (n) => String(n).padStart(2, "0");
    return `${d.getFullYear()}${pad(d.getMonth()+1)}${pad(d.getDate())}_${pad(d.getHours())}${pad(d.getMinutes())}${pad(d.getSeconds())}`;
  }

  async function ensureFolder(folderPath) {
    const parts = folderPath.split("/").filter(Boolean);
    let cur = "";
    for (const p of parts) {
      cur = cur ? `${cur}/${p}` : p;
      if (!app.vault.getAbstractFileByPath(cur)) {
        try { await app.vault.createFolder(cur); } catch (e) { /* ignore */ }
      }
    }
  }

  async function writeFile(path, content) {
    const af = app.vault.getAbstractFileByPath(path);
    if (af && af.children) throw new Error(`出力先がフォルダです: ${path}`);
    if (af) {
      await app.vault.modify(af, content);
    } else {
      await app.vault.create(path, content);
    }
    return app.vault.getAbstractFileByPath(path);
  }

  async function openFileByPath(path) {
    const af = app.vault.getAbstractFileByPath(path);
    if (!af) throw new Error(`ファイルが見つかりません: ${path}`);
    if (af.children) throw new Error(`フォルダは開けません: ${path}`);
    await app.workspace.getLeaf(true).openFile(af);
  }

  async function copyToClipboard(text) {
    // クリック操作中に呼ばれる想定（Clipboard API 成功率UP）
    try {
      await navigator.clipboard.writeText(text);
      return true;
    } catch (e) {
      // fallback: textarea を選択して execCommand
      try {
        ta.value = text;
        ta.focus();
        ta.select();
        const ok = document.execCommand("copy");
        ta.setSelectionRange(0, 0);
        return !!ok;
      } catch (e2) {
        return false;
      }
    }
  }

  async function mapLimit(items, limit, fn) {
    const results = new Array(items.length);
    let next = 0;
    const workers = Array.from({ length: Math.max(1, limit) }, async () => {
      while (true) {
        const i = next++;
        if (i >= items.length) break;
        results[i] = await fn(items[i], i);
      }
    });
    await Promise.all(workers);
    return results;
  }

  // ==============================
  // main generator
  // ==============================
  async function generateDDL() {
    const warns = [];

    // ---- load schemas ----
    const schemas = dv.pages(`"${SCHEMAS_PATH}"`)
      .where(p => p.schema_id && p.physical)
      .array()
      .sort((a,b)=>clean(a.physical).localeCompare(clean(b.physical)));

    const schemaIdToPhysical = new Map(schemas.map(s => [String(s.schema_id), s.physical]));

    // ---- load tables ----
    const tables = dv.pages(`"${TABLES_PATH}"`)
      .where(p => p.table_id && p.schema_id && p.physical)
      .array();

    const tableIdToInfo = new Map();
    for (const t of tables) {
      const sch = schemaIdToPhysical.get(String(t.schema_id));
      if (!sch) {
        warns.push(`table_id=${t.table_id} unknown schema_id=${t.schema_id}`);
        continue;
      }
      tableIdToInfo.set(String(t.table_id), { schemaPhysical: sch, tablePhysical: t.physical, table: t });
    }

    // ---- load columns ----
    const cols = dv.pages(`"${COLUMNS_PATH}"`)
      .where(p => p.column_id && p.table_id && p.physical)
      .array();

    const colsByFqn = new Map();
    for (const c of cols) {
      const info = tableIdToInfo.get(String(c.table_id));
      if (!info) {
        warns.push(`column_id=${c.column_id} unknown table_id=${c.table_id}`);
        continue;
      }
      const k = key2(info.schemaPhysical, info.tablePhysical);
      if (!colsByFqn.has(k)) colsByFqn.set(k, []);
      colsByFqn.get(k).push(c);
    }

    for (const arr of colsByFqn.values()) {
      arr.sort((a,b)=>{
        if (bool(a.pk) !== bool(b.pk)) return bool(a.pk) ? -1 : 1;
        return clean(a.physical).localeCompare(clean(b.physical));
      });
    }

    // ---- load views / semantic views / other ----
    const views = dv.pages(`"${VIEWS_PATH}"`)
      .where(p => p.view_id && p.schema_id && p.physical)
      .array();

    const semanticViews = dv.pages(`"${SEMANTIC_VIEWS_PATH}"`)
      .where(p => p.type === "semantic_view" && p.physical)
      .array();

    const others = dv.pages(`"${OTHER_PATH}"`)
      .where(p => p.type === "other" && p.schema_id)
      .array();

    // ==============================
    // build DDL (FAST: array push -> join)
    // ==============================
    const out = [];

    // ---- SCHEMA ----
    for (const s of schemas) {
      out.push(`CREATE OR REPLACE SCHEMA ${q(s.physical)};\n`);
      if (EMIT_COMMENTS && clean(s.comment)) {
        out.push(`COMMENT ON SCHEMA ${q(s.physical)} IS ${sqlStringLiteral(s.comment)};\n`);
      }
      out.push("\n");
    }

    // ---- TABLE ----
    for (const t of tables) {
      const sch = schemaIdToPhysical.get(String(t.schema_id));
      if (!sch) continue;

      const fqtn = `${q(sch)}.${q(t.physical)}`;
      const colsArr = colsByFqn.get(key2(sch, t.physical)) ?? [];
      if (colsArr.length === 0) {
        out.push(`-- SKIP: ${fqtn} (no columns)\n\n`);
        continue;
      }

      const lines = [];
      const pkCols = [];

      for (const c of colsArr) {
        const notNull = bool(c.is_nullable, true) ? "" : " NOT NULL";
        const defSql  = hasDefault(c.default) ? ` DEFAULT ${String(c.default).trim()}` : "";
        lines.push(`  ${q(c.physical)} ${clean(c.domain)||"VARCHAR"}${defSql}${notNull}`);
        if (bool(c.pk)) pkCols.push(q(c.physical));
      }
      if (pkCols.length) lines.push(`  PRIMARY KEY (${pkCols.join(", ")})`);

      out.push(`CREATE OR REPLACE TABLE ${fqtn} (\n${lines.join(",\n")}\n);\n`);
      if (EMIT_COMMENTS && clean(t.comment)) {
        out.push(`COMMENT ON TABLE ${fqtn} IS ${sqlStringLiteral(t.comment)};\n`);
      }
      if (EMIT_COMMENTS) {
        for (const c of colsArr) {
          if (!clean(c.comment)) continue;
          out.push(`COMMENT ON COLUMN ${fqtn}.${q(c.physical)} IS ${sqlStringLiteral(c.comment)};\n`);
        }
      }
      out.push("\n");
    }

    // ---- VIEW ----
    out.push(`-- ==============================\n-- VIEWS\n-- ==============================\n`);

    const viewBlocks = await mapLimit(views, IO_CONCURRENCY, async (v) => {
      const sch = schemaIdToPhysical.get(String(v.schema_id));
      if (!sch) {
        return { ddl: "", warn: `view_id=${v.view_id} unknown schema_id=${v.schema_id}` };
      }

      let md = "";
      try { md = await dv.io.load(v.file.path); }
      catch { return { ddl: "", warn: `view_id=${v.view_id} load failed` }; }

      const vcols = parseViewColumnsFromBody(md);
      const sql = parseSqlFromBody(md);

      if (!vcols.length || !sql) {
        return { ddl: `-- SKIP: ${sch}.${v.physical} (missing columns or sql)\n\n`, warn: "" };
      }

      const header =
        `CREATE OR REPLACE VIEW ${q(sch)}.${q(v.physical)} (\n` +
        vcols.map(c =>
          clean(c.comment)
            ? `  ${q(c.name)} COMMENT ${sqlStringLiteral(c.comment)}`
            : `  ${q(c.name)}`
        ).join(",\n") +
        `\n)`;

      const viewComment = (EMIT_COMMENTS && clean(v.comment))
        ? ` COMMENT = ${sqlStringLiteral(v.comment)}`
        : "";

      const ddl = `${header}${viewComment}\nAS\n${sql};\n\n`;
      return { ddl, warn: "" };
    });

    for (const r of viewBlocks) {
      if (r?.warn) warns.push(r.warn);
      if (r?.ddl) out.push(r.ddl);
    }

    // ---- SEMANTIC VIEWS (YAML) ----
    out.push(`-- ==============================\n-- SEMANTIC VIEWS (YAML)\n-- ==============================\n`);

    const semanticViewBlocks = await mapLimit(semanticViews, IO_CONCURRENCY, async (sv) => {
      let md = "";
      try { md = await dv.io.load(sv.file.path); }
      catch { return { ddl: "", warn: `semantic_view ${sv.physical} load failed` }; }

      // YAMLブロックを抽出
      const yamlMatch = md.match(/```yaml\s*([\s\S]*?)```/i);
      if (!yamlMatch) {
        return { ddl: `-- SKIP: ${sv.physical} (no yaml block)\n\n`, warn: "" };
      }

      const yamlContent = yamlMatch[1].trim();
      const comment = clean(sv.comment) || `Semantic View: ${sv.physical}`;

      const ddl =
        `-- SEMANTIC VIEW: ${sv.physical}\n` +
        `-- ${comment}\n` +
        `-- ファイル出力先: ${sv.physical}.yaml\n` +
        `/*\n${yamlContent}\n*/\n\n`;
      
      return { ddl, warn: "" };
    });

    for (const r of semanticViewBlocks) {
      if (r?.warn) warns.push(r.warn);
      if (r?.ddl) out.push(r.ddl);
    }

    // ---- OTHER ----
    out.push(`-- ==============================\n-- OTHER OBJECTS\n-- ==============================\n`);

    const otherBlocks = await mapLimit(others, IO_CONCURRENCY, async (o) => {
      const sch = schemaIdToPhysical.get(String(o.schema_id));
      if (!sch) {
        return { ddl: "", warn: `other ${o.file?.path} unknown schema_id=${o.schema_id}` };
      }

      let md = "";
      try { md = await dv.io.load(o.file.path); }
      catch { return { ddl: "", warn: `other ${o.file?.path} load failed` }; }

      const sql = parseSqlFromBody(md);
      if (!sql) {
        return { ddl: "", warn: `other ${o.file?.path} has no sql block` };
      }

      const ddl =
        `-- ${o.object_type?.toUpperCase() ?? "OTHER"}: ${sch}.${o.physical ?? ""}\n` +
        `${sql}\n\n`;
      return { ddl, warn: "" };
    });

    for (const r of otherBlocks) {
      if (r?.warn) warns.push(r.warn);
      if (r?.ddl) out.push(r.ddl);
    }

    // ---- WARNINGS ----
    if (warns.length) {
      out.push(`-- ==============================\n-- WARNINGS\n-- ==============================\n`);
      for (const w of warns) out.push(`-- ${w}\n`);
      out.push("\n");
    }

    const ddl = out.join("").trimEnd() + "\n";
    return { ddl, warns };
  }

  // ==============================
  // actions
  // ==============================
  btnGenerate.addEventListener("click", async () => {
    btnGenerate.disabled = true;
    btnCopy.disabled = true;
    btnOpenFile.disabled = true;
    statusEl.textContent = "生成中…（VIEW/OTHER が多いと少し待ちます）";
    ta.value = "";

    try {
      const t0 = performance.now();
      const { ddl, warns } = await generateDDL();
      const t1 = performance.now();

      lastDDL = ddl;

      // write DDL file
      if (WRITE_SQL_FILE) {
        await ensureFolder(OUTPUT_FOLDER);
        lastFilePath = `${OUTPUT_FOLDER}/${OUTPUT_PREFIX}_${ts()}.sql`;
        await writeFile(lastFilePath, ddl);
        btnOpenFile.disabled = false;
      }

      // preview
      ta.value = ddl;

      btnCopy.disabled = false;
      statusEl.textContent =
        `完了: ${Math.round(t1 - t0)} ms / ${ddl.length.toLocaleString()} chars` +
        (WRITE_SQL_FILE ? ` / 出力: ${lastFilePath}` : "") +
        (warns.length ? ` / WARNINGS: ${warns.length}` : "");
    } catch (e) {
      console.error(e);
      statusEl.textContent = `失敗: ${e?.message ?? e}`;
    } finally {
      btnGenerate.disabled = false;
    }
  });

  btnCopy.addEventListener("click", async () => {
    if (!lastDDL) return;
    statusEl.textContent = "クリップボードへコピー中…";
    const ok = await copyToClipboard(lastDDL);
    statusEl.textContent = ok
      ? "コピーしました（貼り付け先が大きさ制限ある場合はファイル出力を利用してください）"
      : "コピーに失敗しました（巨大サイズ制限の可能性あり：出力ファイルを開いて分割コピー推奨）";
  });

  btnOpenFile.addEventListener("click", async () => {
    if (!lastFilePath) return;
    try {
      await openFileByPath(lastFilePath);
    } catch (e) {
      statusEl.textContent = `ファイルを開けません: ${e?.message ?? e}`;
    }
  });

  // auto run (optional)
  if (RUN_ON_LOAD) {
    btnGenerate.click();
  }
})();
```

---

## 2. External Tables DDL Generator

```dataviewjs
(async () => {
  // ==============================
  // Snowflake EXTERNAL TABLE DDL Generator
  // ==============================

  const SCHEMAS_PATH = "master/schemas";
  const EXTERNAL_TABLES_PATH = "master/externaltables";
  const COLUMNS_PATH = "master/columns";

  const QUOTE_IDENT = false;
  const EMIT_COMMENTS = true;
  const OUTPUT_FOLDER = "generated/externaltable";
  const OUTPUT_PREFIX = "snowflake_external_ddl";
  const WRITE_SQL_FILE = true;

  // ==============================
  // UI
  // ==============================
  dv.header(2, "External Tables DDL Generator");
  const statusEl = dv.el("div", "準備完了（Generate を押してください）");

  const btnRow = dv.el("div", "");
  btnRow.style.display = "flex";
  btnRow.style.gap = "8px";
  btnRow.style.flexWrap = "wrap";

  const btnGenerate = document.createElement("button");
  btnGenerate.textContent = "Generate External Tables";
  btnRow.appendChild(btnGenerate);

  const btnCopy = document.createElement("button");
  btnCopy.textContent = "Copy to Clipboard";
  btnCopy.disabled = true;
  btnRow.appendChild(btnCopy);

  const btnOpenFile = document.createElement("button");
  btnOpenFile.textContent = "Open Output File";
  btnOpenFile.disabled = true;
  btnRow.appendChild(btnOpenFile);

  const details = dv.el("details", "");
  const summary = document.createElement("summary");
  summary.textContent = "Preview（textarea）";
  details.appendChild(summary);

  const ta = document.createElement("textarea");
  ta.readOnly = true;
  ta.style.width = "100%";
  ta.style.height = "360px";
  ta.style.fontFamily = "monospace";
  ta.placeholder = "Generate 後にここに DDL を表示します";
  details.appendChild(ta);

  let lastDDL = "";
  let lastFilePath = "";

  // ==============================
  // helpers
  // ==============================
  function q(name) {
    if (!QUOTE_IDENT) return name;
    return `"${String(name).replaceAll('"', '""')}"`;
  }
  function clean(v) {
    return (v === null || v === undefined) ? "" : String(v);
  }
  function bool(v, def=false) {
    if (v === true || v === false) return v;
    if (typeof v === "string") return v.toLowerCase() === "true";
    return def;
  }
  function sqlStringLiteral(s) {
    return "'" + String(s).replaceAll("'", "''") + "'";
  }
  function key2(schemaPhysical, tablePhysical) {
    return `${clean(schemaPhysical).toUpperCase()}|${clean(tablePhysical).toUpperCase()}`;
  }

  function ts() {
    const d = new Date();
    const pad = (n) => String(n).padStart(2, "0");
    return `${d.getFullYear()}${pad(d.getMonth()+1)}${pad(d.getDate())}_${pad(d.getHours())}${pad(d.getMinutes())}${pad(d.getSeconds())}`;
  }

  async function ensureFolder(folderPath) {
    const parts = folderPath.split("/").filter(Boolean);
    let cur = "";
    for (const p of parts) {
      cur = cur ? `${cur}/${p}` : p;
      if (!app.vault.getAbstractFileByPath(cur)) {
        try { await app.vault.createFolder(cur); } catch (e) { /* ignore */ }
      }
    }
  }

  async function writeFile(path, content) {
    const af = app.vault.getAbstractFileByPath(path);
    if (af && af.children) throw new Error(`出力先がフォルダです: ${path}`);
    if (af) {
      await app.vault.modify(af, content);
    } else {
      await app.vault.create(path, content);
    }
    return app.vault.getAbstractFileByPath(path);
  }

  async function openFileByPath(path) {
    const af = app.vault.getAbstractFileByPath(path);
    if (!af) throw new Error(`ファイルが見つかりません: ${path}`);
    if (af.children) throw new Error(`フォルダは開けません: ${path}`);
    await app.workspace.getLeaf(true).openFile(af);
  }

  async function copyToClipboard(text) {
    try {
      await navigator.clipboard.writeText(text);
      return true;
    } catch (e) {
      try {
        ta.value = text;
        ta.focus();
        ta.select();
        const ok = document.execCommand("copy");
        ta.setSelectionRange(0, 0);
        return !!ok;
      } catch (e2) {
        return false;
      }
    }
  }

  // ==============================
  // main generator
  // ==============================
  async function generateExternalTableDDL() {
    const warns = [];
    const out = [];

    // ---- load schemas ----
    const schemas = dv.pages(`"${SCHEMAS_PATH}"`)
      .where(p => p.schema_id && p.physical)
      .array()
      .sort((a,b)=>clean(a.physical).localeCompare(clean(b.physical)));

    const schemaIdToPhysical = new Map(schemas.map(s => [String(s.schema_id), s.physical]));

    // ---- load external tables ----
    const extTables = dv.pages(`"${EXTERNAL_TABLES_PATH}"`)
      .where(p => p.table_id && p.schema_id && p.physical)
      .array();

    const tableIdToInfo = new Map();
    for (const t of extTables) {
      const sch = schemaIdToPhysical.get(String(t.schema_id));
      if (!sch) {
        warns.push(`external_table_id=${t.table_id} unknown schema_id=${t.schema_id}`);
        continue;
      }
      tableIdToInfo.set(String(t.table_id), { 
        schemaPhysical: sch, 
        tablePhysical: t.physical, 
        table: t 
      });
    }

    // ---- load columns ----
    const cols = dv.pages(`"${COLUMNS_PATH}"`)
      .where(p => p.column_id && p.table_id && p.physical)
      .array();

    const colsByFqn = new Map();
    for (const c of cols) {
      const info = tableIdToInfo.get(String(c.table_id));
      if (!info) continue;
      const k = key2(info.schemaPhysical, info.tablePhysical);
      if (!colsByFqn.has(k)) colsByFqn.set(k, []);
      colsByFqn.get(k).push(c);
    }

    for (const arr of colsByFqn.values()) {
      arr.sort((a,b)=> clean(a.physical).localeCompare(clean(b.physical)));
    }

    // ==============================
    // build EXTERNAL TABLE DDL
    // ==============================
    out.push(`-- ==============================\n`);
    out.push(`-- EXTERNAL TABLES\n`);
    out.push(`-- ==============================\n\n`);

    for (const t of extTables) {
      const sch = schemaIdToPhysical.get(String(t.schema_id));
      if (!sch) continue;

      const fqtn = `${q(sch)}.${q(t.physical)}`;
      const colsArr = colsByFqn.get(key2(sch, t.physical)) ?? [];
      
      if (colsArr.length === 0) {
        out.push(`-- SKIP: ${fqtn} (no columns)\n\n`);
        continue;
      }

      // External table specific metadata
      const stageName = clean(t.stage_name) || `${t.physical}_STAGE`;
      const fileFormat = clean(t.file_format) || "JSON";
      const autoRefresh = bool(t.auto_refresh, true);
      const partitionBy = Array.isArray(t.partition_by) ? t.partition_by : [];


      // Build column definitions with metadata$ extraction (partition columns fixed index)
      const lines = [];
      const partitionLines = [];

      // 固定マッピング: YEAR=2, MONTH=3, DAY=4, HOUR=5
      const PARTITION_INDEX_MAP = { YEAR: 2, MONTH: 3, DAY: 4, HOUR: 5 };

      for (const c of colsArr) {
        const colName = q(c.physical);
        const domain = clean(c.domain) || "VARCHAR";
        const upperName = c.physical.toUpperCase();
        if (PARTITION_INDEX_MAP[upperName]) {
          // パーティションカラムはインデックス固定
          const idx = PARTITION_INDEX_MAP[upperName];
          partitionLines.push(
            `  ${colName} ${domain} AS CAST(SPLIT_PART(SPLIT_PART(metadata$filename, '/', ${idx}), '=', 2) AS ${domain})`
          );
        } else {
          // 通常カラム
          lines.push(`  ${colName} ${domain} AS (value:${c.physical.toLowerCase()}::${domain})`);
        }
      }

      // Combine regular and partition columns
      const allLines = [...lines, ...partitionLines];

      out.push(`CREATE OR REPLACE EXTERNAL TABLE ${fqtn}(\n`);
      out.push(allLines.join(",\n") + "\n");
      out.push(`)`);
      
      // Partition specification
      if (partitionBy.length > 0) {
        out.push(`PARTITION BY (${partitionBy.map(p => p.toUpperCase()).join(", ")})\n`);
      }
      
      // Location and file format
      out.push(`LOCATION=@${q(sch)}.${q(stageName)}\n`);
      out.push(`FILE_FORMAT=(TYPE=${fileFormat})\n`);
      out.push(`AUTO_REFRESH=${autoRefresh ? "TRUE" : "FALSE"}\n`);
      out.push(`REFRESH_ON_CREATE=TRUE;\n`);

      // Comments
      if (EMIT_COMMENTS && clean(t.comment)) {
        out.push(`\nCOMMENT ON TABLE ${fqtn} IS ${sqlStringLiteral(t.comment)};\n`);
      }
      if (EMIT_COMMENTS) {
        for (const c of colsArr) {
          if (!clean(c.comment)) continue;
          out.push(`COMMENT ON COLUMN ${fqtn}.${q(c.physical)} IS ${sqlStringLiteral(c.comment)};\n`);
        }
      }
      out.push("\n");
    }

    // ---- WARNINGS ----
    if (warns.length) {
      out.push(`-- ==============================\n-- WARNINGS\n-- ==============================\n`);
      for (const w of warns) out.push(`-- ${w}\n`);
      out.push("\n");
    }

    const ddl = out.join("").trimEnd() + "\n";
    return { ddl, warns };
  }

  // ==============================
  // actions
  // ==============================
  btnGenerate.addEventListener("click", async () => {
    btnGenerate.disabled = true;
    btnCopy.disabled = true;
    btnOpenFile.disabled = true;
    statusEl.textContent = "生成中…";
    ta.value = "";

    try {
      const t0 = performance.now();
      const { ddl, warns } = await generateExternalTableDDL();
      const t1 = performance.now();

      lastDDL = ddl;

      if (WRITE_SQL_FILE) {
        await ensureFolder(OUTPUT_FOLDER);
        lastFilePath = `${OUTPUT_FOLDER}/${OUTPUT_PREFIX}_${ts()}.sql`;
        await writeFile(lastFilePath, ddl);
        btnOpenFile.disabled = false;
      }

      ta.value = ddl;
      btnCopy.disabled = false;
      
      statusEl.textContent =
        `完了: ${Math.round(t1 - t0)} ms / ${ddl.length.toLocaleString()} chars` +
        (WRITE_SQL_FILE ? ` / 出力: ${lastFilePath}` : "") +
        (warns.length ? ` / WARNINGS: ${warns.length}` : "");
    } catch (e) {
      console.error(e);
      statusEl.textContent = `失敗: ${e?.message ?? e}`;
    } finally {
      btnGenerate.disabled = false;
    }
  });

  btnCopy.addEventListener("click", async () => {
    if (!lastDDL) return;
    statusEl.textContent = "クリップボードへコピー中…";
    const ok = await copyToClipboard(lastDDL);
    statusEl.textContent = ok
      ? "コピーしました"
      : "コピーに失敗しました";
  });

  btnOpenFile.addEventListener("click", async () => {
    if (!lastFilePath) return;
    try {
      await openFileByPath(lastFilePath);
    } catch (e) {
      statusEl.textContent = `ファイルを開けません: ${e?.message ?? e}`;
    }
  });
})();
```

---

## 3. YAML FILE Generator

```dataviewjs
(async () => {
  // ==============================
  // Snowflake Semantic Views YAML Generator
  // ==============================

  const SCHEMAS_PATH = "master/schemas";
  const SEMANTIC_VIEWS_PATH = "master/semanticviews";

  const OUTPUT_FOLDER = "generated/yaml";
  const WRITE_YAML_FILES = true;

  // ==============================
  // UI
  // ==============================
  dv.header(2, "Semantic Views YAML Generator");
  const statusEl = dv.el("div", "準備完了（Generate を押してください）");

  const btnRow = dv.el("div", "");
  btnRow.style.display = "flex";
  btnRow.style.gap = "8px";
  btnRow.style.flexWrap = "wrap";

  const btnGenerate = document.createElement("button");
  btnGenerate.textContent = "Generate YAML Files";
  btnRow.appendChild(btnGenerate);

  const btnOpenFolder = document.createElement("button");
  btnOpenFolder.textContent = "Open Output Folder";
  btnOpenFolder.disabled = true;
  btnRow.appendChild(btnOpenFolder);

  const details = dv.el("details", "");
  const summary = document.createElement("summary");
  summary.textContent = "生成ファイル一覧";
  details.appendChild(summary);

  const resultDiv = dv.el("div", "");
  resultDiv.style.fontFamily = "monospace";
  resultDiv.style.fontSize = "0.9em";
  resultDiv.style.maxHeight = "300px";
  resultDiv.style.overflow = "auto";
  resultDiv.style.padding = "8px";
  resultDiv.style.border = "1px solid var(--background-modifier-border)";
  details.appendChild(resultDiv);

  let lastOutputFolder = "";

  // ==============================
  // helpers
  // ==============================
  function clean(v) {
    return (v === null || v === undefined) ? "" : String(v);
  }

  function normalizeLF(s){
    return String(s ?? "").replace(/\r\n/g, "\n").replace(/\r/g, "\n");
  }

  async function ensureFolder(folderPath) {
    const parts = folderPath.split("/").filter(Boolean);
    let cur = "";
    for (const p of parts) {
      cur = cur ? `${cur}/${p}` : p;
      if (!app.vault.getAbstractFileByPath(cur)) {
        try { await app.vault.createFolder(cur); } catch (e) { /* ignore */ }
      }
    }
  }

  async function writeFile(path, content) {
    const af = app.vault.getAbstractFileByPath(path);
    if (af && af.children) throw new Error(`出力先がフォルダです: ${path}`);
    if (af) {
      await app.vault.modify(af, content);
    } else {
      await app.vault.create(path, content);
    }
    return app.vault.getAbstractFileByPath(path);
  }

  async function openFolder(folderPath) {
    const folder = app.vault.getAbstractFileByPath(folderPath);
    if (!folder) throw new Error(`フォルダが見つかりません: ${folderPath}`);
    if (!folder.children) throw new Error(`フォルダではありません: ${folderPath}`);
    // Obsidianでフォルダを開く
    app.workspace.getLeaf(true).openFile(folder);
  }

  // ==============================
  // main generator
  // ==============================
  async function generateYAMLFiles() {
    const warns = [];
    const results = [];

    // ---- load schemas ----
    const schemas = dv.pages(`"${SCHEMAS_PATH}"`)
      .where(p => p.schema_id && p.physical)
      .array();

    const schemaIdToPhysical = new Map(schemas.map(s => [String(s.schema_id), s.physical]));

    // ---- load semantic views ----
    const semanticViews = dv.pages(`"${SEMANTIC_VIEWS_PATH}"`)
      .where(p => p.type === "semantic_view" && p.physical)
      .array();

    if (semanticViews.length === 0) {
      warns.push("セマンティックビューが見つかりません");
      return { results, warns };
    }

    // ---- Generate YAML files ----
    for (const sv of semanticViews) {
      let md = "";
      try { md = await dv.io.load(sv.file.path); }
      catch { 
        warns.push(`${sv.physical}: ファイル読み込み失敗`);
        continue;
      }

      // YAMLブロックを抽出
      const yamlMatch = md.match(/```yaml\s*([\s\S]*?)```/i);
      if (!yamlMatch) {
        warns.push(`${sv.physical}: YAMLブロックが見つかりません`);
        continue;
      }

      const yamlContent = yamlMatch[1].trim();
      const yamlFilePath = `${OUTPUT_FOLDER}/${sv.physical}.yaml`;

      if (WRITE_YAML_FILES) {
        await ensureFolder(OUTPUT_FOLDER);
        await writeFile(yamlFilePath, yamlContent);
      }

      results.push({
        name: sv.physical,
        path: yamlFilePath,
        size: yamlContent.length,
        comment: clean(sv.comment)
      });
    }

    return { results, warns };
  }

  // ==============================
  // actions
  // ==============================
  btnGenerate.addEventListener("click", async () => {
    btnGenerate.disabled = true;
    btnOpenFolder.disabled = true;
    statusEl.textContent = "生成中…";
    resultDiv.innerHTML = "";

    try {
      const t0 = performance.now();
      const { results, warns } = await generateYAMLFiles();
      const t1 = performance.now();

      lastOutputFolder = OUTPUT_FOLDER;

      if (results.length > 0) {
        btnOpenFolder.disabled = false;
        
        let html = `<div style="margin-bottom: 8px;"><strong>生成完了: ${results.length} ファイル</strong></div>`;
        html += `<table style="width: 100%; border-collapse: collapse; font-size: 0.85em;">`;
        html += `<tr style="border-bottom: 1px solid var(--background-modifier-border);">`;
        html += `<th style="text-align: left; padding: 4px;">ファイル名</th>`;
        html += `<th style="text-align: right; padding: 4px;">サイズ</th>`;
        html += `<th style="text-align: left; padding: 4px;">説明</th>`;
        html += `</tr>`;
        
        for (const r of results) {
          html += `<tr style="border-bottom: 1px solid var(--background-modifier-border-hover);">`;
          html += `<td style="padding: 4px;">${r.name}.yaml</td>`;
          html += `<td style="text-align: right; padding: 4px;">${r.size.toLocaleString()} bytes</td>`;
          html += `<td style="padding: 4px; font-size: 0.9em; color: var(--text-muted);">${r.comment || '-'}</td>`;
          html += `</tr>`;
        }
        html += `</table>`;
        
        if (warns.length > 0) {
          html += `<div style="margin-top: 12px; color: var(--text-warning);"><strong>警告: ${warns.length} 件</strong></div>`;
          html += `<ul style="margin: 4px 0; padding-left: 20px; font-size: 0.85em;">`;
          for (const w of warns) {
            html += `<li>${w}</li>`;
          }
          html += `</ul>`;
        }
        
        resultDiv.innerHTML = html;
      } else {
        resultDiv.innerHTML = `<div style="color: var(--text-error);">生成されたファイルがありません</div>`;
      }

      statusEl.textContent =
        `完了: ${Math.round(t1 - t0)} ms / ${results.length} ファイル生成` +
        (warns.length ? ` / 警告: ${warns.length} 件` : "");
    } catch (e) {
      console.error(e);
      statusEl.textContent = `失敗: ${e?.message ?? e}`;
      resultDiv.innerHTML = `<div style="color: var(--text-error);">エラー: ${e?.message ?? e}</div>`;
    } finally {
      btnGenerate.disabled = false;
    }
  });

  btnOpenFolder.addEventListener("click", async () => {
    if (!lastOutputFolder) return;
    try {
      // ファイルエクスプローラーで開く（システム依存）
      statusEl.textContent = `出力フォルダ: ${lastOutputFolder}`;
    } catch (e) {
      statusEl.textContent = `フォルダを開けません: ${e?.message ?? e}`;
    }
  });
})();
```

---

## その他のSQL操作例

### DB・WHの作成

```sql
USE ROLE ACCOUNTADMIN;
CREATE DATABASE IF NOT EXISTS GBPS253YS_DB;
CREATE OR REPLACE WAREHOUSE GBPS253YS_WH WITH
     WAREHOUSE_SIZE='X-SMALL'
     AUTO_SUSPEND = 120
     AUTO_RESUME = TRUE
     INITIALLY_SUSPENDED=TRUE;
     
USE DATABASE GBPS253YS_DB;
USE WAREHOUSE GBPS253YS_WH;

DROP SCHEMA PUBLIC;
```

### ファイルからテーブルを作成

##### 案件明細

```sql
COPY INTO GBPS253YS_DB.APP_PRODUCTION.ANKEN_MEISAI (
  ID,
  DEPARTMENT_SHORT_NAME,
  SECTION_NAME,
  FISCAL_YEAR,
  PROJECT_NUMBER,
  BRANCH_NUMBER,
  SALES_CATEGORY,
  DEPARTMENT_ID,
  GROUP_SHORT_NAME,
  CUSTOMER_ID,
  CUSTOMER_NAME,
  ORDER_NUMBER,
  ORDER_NAME,
  SUBJECT,
  PROJECT_NAME,
  WORK_START_DATE,
  WORK_END_DATE,
  ACCOUNTING_MONTH,
  RANK,
  AMOUNT,
  SALES_DELIVERY_FLAG,
  INVOICE_NUMBER,
  ACTIVE_FLAG,
  CUSTOMER_QUOTE_REQUEST_NUMBER,
  CUSTOMER_ORDER_NUMBER,
  DIVISION_CODE,
  DEPARTMENT_NAME,
  DEPARTMENT_SECTION_SHORT_NAME
)
FROM @GBPS253YS_DB.APP_PRODUCTION.RAW_DATA
FILES = ('案件：案件明細一覧20251217203031_0.csv')
FILE_FORMAT = (
    TYPE=CSV,
    SKIP_HEADER=1,
    FIELD_DELIMITER=',',
    TRIM_SPACE=FALSE,
    FIELD_OPTIONALLY_ENCLOSED_BY = '"',
    REPLACE_INVALID_CHARACTERS=TRUE,
    DATE_FORMAT=AUTO,
    TIME_FORMAT=AUTO,
    TIMESTAMP_FORMAT=AUTO,
    EMPTY_FIELD_AS_NULL=TRUE,
    NULL_IF = (''),
    error_on_column_count_mismatch=false
)
ON_ERROR=CONTINUE
FORCE = TRUE;
```

##### 部署マスタ

```sql
COPY INTO GBPS253YS_DB.APP_PRODUCTION.DEPARTMENT_MASTER (
  ID,                         -- 1
  FISCAL_YEAR,                -- 2
  DEPARTMENT_CATEGORY,        -- 3
  DEPARTMENT_ID,              -- 4
  DIVISION_CODE,              -- 5 部門CD
  DEPARTMENT_SECTION_CODE,    -- 6 部課CD
  HEADQUARTERS_CODE,          -- 7 本部CD
  GENERAL_DEPARTMENT_CODE,    -- 8 統括部CD
  DEPARTMENT_CODE,            -- 9 部CD
  SECTION_CODE,               -- 10 課CD
  GROUP_CODE,                 -- 11 グループCD
  FULL_NAME,                  -- 12 正式名称
  SHORT_NAME,                 -- 13 略称
  COMBINED_NAME,              -- 14 組合せ名称
  COMBINED_SHORT_NAME,        -- 15 組合せ略称
  ACCOUNTING_DEPARTMENT_CODE  -- 16 経理部門CD
)
FROM @GBPS253YS_DB.APP_PRODUCTION.RAW_DATA
FILES = ('部署マスタ20251217205645_0.csv')
FILE_FORMAT = (
  TYPE=CSV,
  SKIP_HEADER=1,
  FIELD_DELIMITER=',',
  FIELD_OPTIONALLY_ENCLOSED_BY='"',
  REPLACE_INVALID_CHARACTERS=TRUE,
  DATE_FORMAT=AUTO,
  TIME_FORMAT=AUTO,
  TIMESTAMP_FORMAT=AUTO,
  EMPTY_FIELD_AS_NULL=TRUE,
  NULL_IF=(''),
  ERROR_ON_COLUMN_COUNT_MISMATCH=FALSE
)
ON_ERROR=CONTINUE
FORCE=TRUE;

```

#### DIM_ENTITY_ALIASデータの生成

```sql
INSERT OVERWRITE INTO NAME_RESOLUTION.DIM_ENTITY_ALIAS (
  alias_normalized,
  entity_type,
  alias_raw,
  confidence,
  entity_id,
  entity_name,
  is_active,
  priority,
  refresh_run_id,
  refreshed_at
)
SELECT
  alias_normalized,
  entity_type,
  alias_raw,
  confidence,
  entity_id,
  entity_name,
  is_active,
  priority,
  TO_VARCHAR(CURRENT_TIMESTAMP()) AS refresh_run_id,
  CURRENT_TIMESTAMP()             AS refreshed_at
FROM APP_PRODUCTION.V_ENTITY_ALIAS_ALL;
```


#### API実行ロールの作成

```sql
USE ROLE SECURITYADMIN;
CREATE OR REPLACE ROLE GBPS253YS_API_ROLE;

USE ROLE SECURITYADMIN;
CREATE OR REPLACE  USER GBPS253YS_API_USER
  LOGIN_NAME = 'GBPS253YS_API_USER'
  DISPLAY_NAME = 'GBPS253YS_API_USER'
  DEFAULT_ROLE = GBPS253YS_API_ROLE
  MUST_CHANGE_PASSWORD = FALSE;

ALTER USER GBPS253YS_API_USER SET DEFAULT_ROLE = GBPS253YS_API_ROLE;
ALTER USER GBPS253YS_API_USER SET DEFAULT_WAREHOUSE = GBPS253YS_WH;
ALTER USER GBPS253YS_API_USER SET DEFAULT_NAMESPACE = GBPS253YS_DB.APP_PRODUCTION;

GRANT ROLE GBPS253YS_API_ROLE TO USER GBPS253YS_API_USER;

-- 2) Network Policy（API_USERだけ）
CREATE OR REPLACE NETWORK POLICY GBPS253YS_API_ONLY
  ALLOWED_IP_LIST = ('4.189.129.1');

ALTER USER GBPS253YS_API_USER SET NETWORK_POLICY = GBPS253YS_API_ONLY;

-- 3) Agent権限（オーナーロールで）
USE ROLE ACCOUNTADMIN;

-- 既存
GRANT USAGE ON WAREHOUSE GBPS253YS_WH TO ROLE GBPS253YS_API_ROLE;
GRANT USAGE ON DATABASE GBPS253YS_DB TO ROLE GBPS253YS_API_ROLE;
GRANT USAGE ON ALL SCHEMAS IN DATABASE GBPS253YS_DB TO ROLE GBPS253YS_API_ROLE;
GRANT SELECT ON ALL TABLES IN DATABASE GBPS253YS_DB TO ROLE GBPS253YS_API_ROLE;
GRANT SELECT ON ALL VIEWS IN DATABASE GBPS253YS_DB TO ROLE GBPS253YS_API_ROLE;
GRANT SELECT ON ALL MATERIALIZED VIEWS IN DATABASE GBPS253YS_DB TO ROLE GBPS253YS_API_ROLE;
GRANT USAGE ON ALL SEQUENCES IN DATABASE GBPS253YS_DB TO ROLE GBPS253YS_API_ROLE;
GRANT USAGE ON ALL FUNCTIONS IN DATABASE GBPS253YS_DB TO ROLE GBPS253YS_API_ROLE;
GRANT USAGE ON ALL PROCEDURES IN DATABASE GBPS253YS_DB TO ROLE GBPS253YS_API_ROLE;
GRANT USAGE ON ALL AGENT IN DATABASE GBPS253YS_DB TO ROLE GBPS253YS_API_ROLE;
GRANT USAGE ON AGENT GBPS253YS_DB.APP_PRODUCTION.SNOWFLAKE_DEMO_AGENT TO ROLE GBPS253YS_API_ROLE;

-- 将来
GRANT USAGE ON FUTURE SCHEMAS IN DATABASE GBPS253YS_DB TO ROLE GBPS253YS_API_ROLE;
GRANT SELECT ON FUTURE TABLES IN DATABASE GBPS253YS_DB TO ROLE GBPS253YS_API_ROLE;
GRANT SELECT ON FUTURE VIEWS IN DATABASE GBPS253YS_DB TO ROLE GBPS253YS_API_ROLE;
GRANT SELECT ON FUTURE MATERIALIZED VIEWS IN DATABASE GBPS253YS_DB TO ROLE GBPS253YS_API_ROLE;
GRANT USAGE ON FUTURE SEQUENCES IN DATABASE GBPS253YS_DB TO ROLE GBPS253YS_API_ROLE;
GRANT USAGE ON FUTURE FUNCTIONS IN DATABASE GBPS253YS_DB TO ROLE GBPS253YS_API_ROLE;
GRANT USAGE ON FUTURE PROCEDURES IN DATABASE GBPS253YS_DB TO ROLE GBPS253YS_API_ROLE;


GRANT READ ON STAGE GBPS253YS_DB.APP_PRODUCTION.RAW_DATA TO ROLE GBPS253YS_API_ROLE;
GRANT WRITE ON STAGE GBPS253YS_DB.APP_PRODUCTION.RAW_DATA TO ROLE GBPS253YS_API_ROLE;

-- 4) PAT発行（表示される値を保存）
USE ROLE SECURITYADMIN;

ALTER USER GBPS253YS_API_USER
  ADD PROGRAMMATIC ACCESS TOKEN azure_func_token;
```


# 参考）使用方法

1. 以下のようにしてデータを生成する
```sql
-- =========================================================
-- Weekly manual profiling + evidence export + ingest
-- =========================================================

-- 0) 実行日（YYYYMMDD_HH24MISSFF3）を自動で作る
SET RUN_DATE = TO_VARCHAR(
  DATEADD(
    day,
    -1,
    CONVERT_TIMEZONE('UTC', 'Asia/Tokyo', CURRENT_TIMESTAMP())
  ),
  'YYYYMMDD_HH24MISSFF3'
);

-- 1) メトリクス収集（週1回）
--    ※ 業務データスキーマのみ（例：APP_PRODUCTION）
CALL DB_DESIGN.PROFILE_ALL_TABLES(
  'GBPS253YS_DB',
  'APP_PRODUCTION',
  10.0,
  'weekly manual profiling'
);

CALL DB_DESIGN.PROFILE_ALL_TABLES(
  'GBPS253YS_DB',
  'DB_DESIGN',
  10.0,
  'weekly manual profiling'
);

-- 2) メトリクス情報を Markdown (+ raw json) にして S3 更新
--    ※ DB_DESIGN.V_PROFILE_RESULTS_LATEST をソースにするのはOK（基盤側）
CALL DB_DESIGN.EXPORT_PROFILE_EVIDENCE_MD_VFINAL(
  'GBPS253YS_DB',              -- P_SOURCE_DB
  'DB_DESIGN',                -- P_SOURCE_SCHEMA
  'V_PROFILE_RESULTS_LATEST', -- P_SOURCE_VIEW
  'GBPS253YS_DB',              -- P_TARGET_DB (フィルタ用)
  $RUN_DATE,                  -- P_RUN_DATE（自動）
  'reviews/profiles',         -- P_VAULT_PREFIX
  'APP_PRODUCTION'                  -- P_TARGET_SCHEMA（業務スキーマのみ）
);
CALL DB_DESIGN.EXPORT_PROFILE_EVIDENCE_MD_VFINAL(
  'GBPS253YS_DB',              -- P_SOURCE_DB
  'DB_DESIGN',                -- P_SOURCE_SCHEMA
  'V_PROFILE_RESULTS_LATEST', -- P_SOURCE_VIEW
  'GBPS253YS_DB',              -- P_TARGET_DB (フィルタ用)
  $RUN_DATE,                  -- P_RUN_DATE（自動）
  'reviews/profiles',         -- P_VAULT_PREFIX
  'DB_DESIGN'                  -- P_TARGET_SCHEMA（業務スキーマのみ）
);

-- 3) 最新の Markdown を取り込み（Vault全文でもOKだが絞ると軽い）
--    reviews/profiles 配下の md だけ取り込む例
CALL DB_DESIGN.INGEST_VAULT_MD(
  '@DB_DESIGN.OBSIDIAN_VAULT_STAGE',
  '.*\.md'
);
```

2. Snowflake Cortex Agentにレビュー依頼する。



#### クリーニング

```sql
DROP DATABASE GBPS253YS_DB;
DROP WAREHOUSE GBPS253YS_WH;
```
