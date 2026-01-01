---
type: other
schema_id: SCH_20251225131727
physical: RESOLVE_ENTITY_ALIAS_TOOL
object_type: procedure
comment: RAWデータ格納用ステージ
---
# SQL

```sql
create or replace procedure GBPS253YS_DB.APP_PRODUCTION.RESOLVE_ENTITY_ALIAS_TOOL(payload_json string)
returns variant
language javascript
execute as owner
as
$$
try {
  // ✅ Snowflake JS SP は arguments[0] で受ける
  const arg0 = arguments[0];

  const s =
    (arg0 === null || arg0 === undefined || String(arg0).length === 0)
      ? "{}"
      : String(arg0);

  const rs = snowflake.createStatement({
    sqlText: "select parse_json(?)",
    binds: [s]
  }).execute();
  rs.next();
  const p = rs.getColumnValue(1) || {};

  const term = (p.term ?? "").toString();
  const maxCandidates = (p.max_candidates ?? "8").toString();
  const hintRaw = (p.entity_type_hint ?? "").toString().trim();

  if (!term) {
    return { ok:false, next:"error", message:"term is required", payload:p };
  }

  let st;
  if (hintRaw.length === 0) {
    // ✅ hintなし：2引数（nullを渡さない）
    st = snowflake.createStatement({
      sqlText: "call GBPS253YS_DB.APP_PRODUCTION.RESOLVE_ENTITY_ALIAS(?, ?)",
      binds: [term, maxCandidates]
    });
  } else {
    // ✅ hintあり：3引数
    st = snowflake.createStatement({
      sqlText: "call GBPS253YS_DB.APP_PRODUCTION.RESOLVE_ENTITY_ALIAS(?, ?, ?)",
      binds: [term, maxCandidates, hintRaw]
    });
  }

  const r2 = st.execute();
  r2.next();
  return r2.getColumnValue(1);

} catch (err) {
  return {
    ok:false,
    next:"error",
    message:String(err),
    stack: err && err.stack ? String(err.stack) : null
  };
}
$$;

```

