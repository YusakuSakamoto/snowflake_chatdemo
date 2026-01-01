---
type: other
schema_id: SCH_20251225131727
physical: RESOLVE_ENTITY_ALIAS
object_type: procedure
comment: RAWデータ格納用ステージ
---

# SQL
```sql
create or replace procedure APP_PRODUCTION.RESOLVE_ENTITY_ALIAS(
    term string,
    max_candidates string,                 -- ★ NUMBER(38,0) 回避のため string で受ける
    entity_type_hint string default null   -- 'department' / 'customer' / 'project' / 'order' / null
)
returns variant
language javascript
execute as owner
as
$$
/* =========================
 * Utility
 * ========================= */
function q1(sqlText, binds) {
  const st = snowflake.createStatement({
    sqlText: sqlText,
    binds: binds || []
  });
  return st.execute();
}

function firstValue(rs) {
  if (rs.next()) return rs.getColumnValue(1);
  return null;
}

// JS SPでは列名でのgetColumnValueが効かないことがあるため、列番号で取得する
function rowsToArray(rs) {
  const out = [];
  while (rs.next()) {
    out.push({
      alias_raw:        rs.getColumnValue(1),
      alias_normalized: rs.getColumnValue(2),
      entity_type:      rs.getColumnValue(3),
      entity_id:        rs.getColumnValue(4),
      entity_name:      rs.getColumnValue(5),
      confidence:       Number(rs.getColumnValue(6)),
      priority:         Number(rs.getColumnValue(7))
    });
  }
  return out;
}

function toInt(v, defVal, minVal, maxVal) {
  const n = parseInt(v, 10);
  const x = Number.isFinite(n) ? n : defVal;
  return Math.max(minVal, Math.min(maxVal, x));
}

try {
  /* =========================
   * Params (Snowflake JS SP: use arguments[])
   * ========================= */
  const termArg           = arguments[0];
  const maxCandidatesArg  = arguments[1];
  const entityTypeHintArg = arguments[2];

  const t = (termArg === null || termArg === undefined) ? "" : String(termArg);

  const max = toInt(maxCandidatesArg, 8, 1, 50);
  const limitClause = " limit " + max;

  const hasHint =
    entityTypeHintArg !== null &&
    entityTypeHintArg !== undefined &&
    String(entityTypeHintArg).length > 0;

  const typeClause = hasHint ? " and entity_type = ? " : "";

  /* =========================
   * Normalize
   * ※UDFは完全修飾推奨。必要に応じてスキーマ名を修正してください。
   * ========================= */
  const normJa = firstValue(
    q1("select GBPS253YS_DB.APP_PRODUCTION.NORMALIZE_JA(?)", [t])
  );

  const normDept = firstValue(
    q1("select GBPS253YS_DB.APP_PRODUCTION.NORMALIZE_JA_DEPT(?)", [t])
  );

  /* =========================
   * Candidate Resolver
   * ========================= */
  function fetchCandidates(sqlBase, binds) {
    const rs = q1(sqlBase, binds);
    const candidates = rowsToArray(rs);

    // 1件のみ → 確定
    if (candidates.length === 1) {
      return { decided: true, resolved: candidates[0], candidates: candidates };
    }

    // 上位が十分強い場合 → 自動確定（任意チューニング）
    if (candidates.length >= 2) {
      const top = candidates[0];
      const second = candidates[1];
      if (
        top.confidence >= 0.95 &&
        (top.confidence - second.confidence) >= 0.10
      ) {
        return { decided: true, resolved: top, candidates: candidates };
      }
    }

    return { decided: false, resolved: null, candidates: candidates };
  }

  /* =========================
   * Step ① raw 完全一致（alias_raw）
   * ========================= */
  {
    const sql = `
      select
        alias_raw,
        alias_normalized,
        entity_type,
        entity_id,
        entity_name,
        confidence,
        priority
      from GBPS253YS_DB.NAME_RESOLUTION.DIM_ENTITY_ALIAS
      where is_active = true
        and alias_raw = ?
        ${typeClause}
      order by
        priority asc,
        confidence desc,
        length(alias_normalized) asc
      ${limitClause}
    `;

    const binds = hasHint ? [t, entityTypeHintArg] : [t];
    const r = fetchCandidates(sql, binds);

    if (r.decided) {
      return {
        ok: true,
        step: 1,
        next: "aggregate",
        term: t,
        normalized: normJa,
        resolved: r.resolved
      };
    }
  }

  /* =========================
   * Step ② 正規化 完全一致（alias_normalized）
   * departmentは normJa / normDept の両方で試す
   * ========================= */
  {
    const sql = `
      select
        alias_raw,
        alias_normalized,
        entity_type,
        entity_id,
        entity_name,
        confidence,
        priority
      from GBPS253YS_DB.NAME_RESOLUTION.DIM_ENTITY_ALIAS
      where is_active = true
        and (
              alias_normalized = ?
           or (entity_type = 'department' and alias_normalized = ?)
        )
        ${typeClause}
      order by
        priority asc,
        confidence desc,
        length(alias_normalized) asc
      ${limitClause}
    `;

    const binds = hasHint
      ? [normJa, normDept, entityTypeHintArg]
      : [normJa, normDept];

    const r = fetchCandidates(sql, binds);

    if (r.decided) {
      return {
        ok: true,
        step: 2,
        next: "aggregate",
        term: t,
        normalized: normJa,
        resolved: r.resolved
      };
    }
  }

  /* =========================
   * Step ③ 正規化 部分一致（候補提示）
   * ========================= */
  {
    const sql = `
      select
        alias_raw,
        alias_normalized,
        entity_type,
        entity_id,
        entity_name,
        confidence,
        priority
      from GBPS253YS_DB.NAME_RESOLUTION.DIM_ENTITY_ALIAS
      where is_active = true
        and (
             alias_normalized like '%' || ? || '%'
          or (entity_type = 'department' and alias_normalized like '%' || ? || '%')
        )
        ${typeClause}
      order by
        priority asc,
        confidence desc,
        length(alias_normalized) asc
      ${limitClause}
    `;

    const binds = hasHint
      ? [normJa, normDept, entityTypeHintArg]
      : [normJa, normDept];

    const r = fetchCandidates(sql, binds);

    return {
      ok: true,
      step: 3,
      next: "disambiguate",
      term: t,
      normalized: normJa,
      candidates: r.candidates
    };
  }

} catch (err) {
  // Agent経由でも原因が追えるように返す
  return {
    ok: false,
    next: "error",
    message: String(err),
    stack: err && err.stack ? String(err.stack) : null
  };
}
$$;
```

