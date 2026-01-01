---
type: other
schema_id: SCH_20251225131727
physical: EXPAND_DEPARTMENT_SCOPE_TOOL
object_type: procedure
comment: RAWデータ格納用ステージ
---

# SQL

```sql
create or replace procedure APP_PRODUCTION.EXPAND_DEPARTMENT_SCOPE_TOOL(
  payload_json string
)
returns variant
language javascript
execute as owner
as
$$
function q1(sqlText, binds) {
  return snowflake.createStatement({ sqlText: sqlText, binds: binds || [] }).execute();
}
function toInt(v, defVal, minVal, maxVal) {
  const n = parseInt(v, 10);
  const x = Number.isFinite(n) ? n : defVal;
  return Math.max(minVal, Math.min(maxVal, x));
}
function upper(v) { return (v===null||v===undefined) ? "" : String(v).toUpperCase(); }
function trim(v) { return (v===null||v===undefined) ? "" : String(v).trim(); }

try {
  // --- parse payload_json ---
  const arg = arguments[0];
  const jsonText = (arg === null || arg === undefined || String(arg).length === 0) ? "{}" : String(arg);

  const prs = q1("select parse_json(?)", [jsonText]);
  prs.next();
  const p = prs.getColumnValue(1) || {};

  let fy = (p.fiscal_year === null || p.fiscal_year === undefined) ? "" : String(p.fiscal_year);
  let deptId = (p.department_id === null || p.department_id === undefined) ? "" : String(p.department_id); // logical department_id expected
  const includeSelf = (upper(p.include_self) === "Y") ? "Y" : "N";
  const maxNodes = toInt(p.max_nodes, 500, 1, 5000);

  if (!fy) {
    const rsFy = q1("select max(FISCAL_YEAR) from GBPS253YS_DB.APP_PRODUCTION.DEPARTMENT_MASTER", []);
    fy = rsFy.next() ? String(rsFy.getColumnValue(1)) : "";
    if (!fy) return { ok:false, next:"error", message:"cannot determine fiscal_year", payload:p };
  }
  if (!deptId) return { ok:false, next:"error", message:"department_id is required (logical dept id)", payload:p };

  // --- 1) find root by DEPARTMENT_ID ---
  let rsRoot = q1(`
    select
      DEPARTMENT_ID,
      DEPARTMENT_CATEGORY,
      DIVISION_CODE,
      DEPARTMENT_SECTION_CODE,
      HEADQUARTERS_CODE,
      GENERAL_DEPARTMENT_CODE,
      COMBINED_NAME,
      COMBINED_SHORT_NAME
    from GBPS253YS_DB.APP_PRODUCTION.DEPARTMENT_MASTER
    where FISCAL_YEAR = ?
      and DEPARTMENT_ID = ?
    limit 1
  `, [fy, deptId]);

  // --- 2) fallback: maybe input was physical ID column "ID" ---
  if (!rsRoot.next()) {
    const rsMap = q1(`
      select DEPARTMENT_ID
      from GBPS253YS_DB.APP_PRODUCTION.DEPARTMENT_MASTER
      where FISCAL_YEAR = ?
        and ID = ?
      limit 1
    `, [fy, deptId]);

    if (rsMap.next()) {
      deptId = String(rsMap.getColumnValue(1));
      rsRoot = q1(`
        select
          DEPARTMENT_ID,
          DEPARTMENT_CATEGORY,
          DIVISION_CODE,
          DEPARTMENT_SECTION_CODE,
          HEADQUARTERS_CODE,
          GENERAL_DEPARTMENT_CODE,
          COMBINED_NAME,
          COMBINED_SHORT_NAME
        from GBPS253YS_DB.APP_PRODUCTION.DEPARTMENT_MASTER
        where FISCAL_YEAR = ?
          and DEPARTMENT_ID = ?
        limit 1
      `, [fy, deptId]);

      if (!rsRoot.next()) {
        return {
          ok:false,
          next:"error",
          message:"mapped from ID but root row still not found",
          fiscal_year:fy,
          input_id:p.department_id,
          mapped_department_id:deptId
        };
      }
    } else {
      return {
        ok:false,
        next:"error",
        message:"department_id not found (and also not found as ID)",
        fiscal_year:fy,
        input_value:p.department_id
      };
    }
  }

  // rsRoot is currently on a valid row
  const root_department_id = String(rsRoot.getColumnValue(1));
  const category = trim(rsRoot.getColumnValue(2));
  const divisionCode = rsRoot.getColumnValue(3) === null ? null : String(rsRoot.getColumnValue(3));
  const deptSectionCode = rsRoot.getColumnValue(4) === null ? null : String(rsRoot.getColumnValue(4));
  const hqCode   = rsRoot.getColumnValue(5) === null ? null : String(rsRoot.getColumnValue(5));
  const genCode  = rsRoot.getColumnValue(6) === null ? null : String(rsRoot.getColumnValue(6));
  const nameFull = rsRoot.getColumnValue(7);
  const nameShort= rsRoot.getColumnValue(8);

  // --- decide scope key + allowed categories ---
  let whereKey = "";
  let bindsKey = [];
  let allowCats = null;

  if (category === "グループ") {
    whereKey = "FISCAL_YEAR = ? and DEPARTMENT_ID = ?";
    bindsKey = [fy, root_department_id];
  } else if (category === "課") {
    if (!deptSectionCode) {
      return {
        ok:false,
        next:"error",
        message:"department_section_code is null for 課",
        fiscal_year:fy,
        department_id:root_department_id
      };
    }
    whereKey = "FISCAL_YEAR = ? and DEPARTMENT_SECTION_CODE = ?";
    bindsKey = [fy, deptSectionCode];
    allowCats = (includeSelf === "Y") ? ["課","グループ"] : ["グループ"];
  } else if (category === "部") {
    if (!divisionCode) {
      return {
        ok:false,
        next:"error",
        message:"division_code is null for 部",
        fiscal_year:fy,
        department_id:root_department_id
      };
    }
    whereKey = "FISCAL_YEAR = ? and DIVISION_CODE = ?";
    bindsKey = [fy, divisionCode];
    allowCats = (includeSelf === "Y") ? ["部","課","グループ"] : ["課","グループ"];
  } else if (category === "本部") {
    if (!hqCode) {
      return {
        ok:false,
        next:"error",
        message:"headquarters_code is null for 本部",
        fiscal_year:fy,
        department_id:root_department_id
      };
    }
    whereKey = "FISCAL_YEAR = ? and HEADQUARTERS_CODE = ?";
    bindsKey = [fy, hqCode];
    allowCats = (includeSelf === "Y") ? ["本部","部","課","グループ"] : ["部","課","グループ"];
  } else {
    return {
      ok:false,
      next:"error",
      message:"unsupported department_category",
      department_category:category,
      fiscal_year:fy,
      department_id:root_department_id
    };
  }

  let extra = "";
  if (allowCats && allowCats.length > 0) {
    const quoted = allowCats.map(x => "'" + String(x).replace(/'/g,"''") + "'").join(",");
    extra = ` and DEPARTMENT_CATEGORY in (${quoted}) `;
  }

  const rs = q1(`
    select
      DEPARTMENT_ID,
      DEPARTMENT_CATEGORY,
      DIVISION_CODE,
      DEPARTMENT_SECTION_CODE,
      DEPARTMENT_CODE,
      SECTION_CODE,
      GROUP_CODE,
      COMBINED_NAME,
      COMBINED_SHORT_NAME
    from GBPS253YS_DB.APP_PRODUCTION.DEPARTMENT_MASTER
    where ${whereKey}
      ${extra}
    order by
      case DEPARTMENT_CATEGORY when '本部' then 1 when '部' then 2 when '課' then 3 when 'グループ' then 4 else 9 end,
      DEPARTMENT_ID
    limit ${maxNodes}
  `, bindsKey);

  const ids = [];
  const members = [];
  while (rs.next()) {
    const did = String(rs.getColumnValue(1));
    ids.push(did);
    members.push({
      department_id: did,
      department_category: String(rs.getColumnValue(2)),
      division_code: rs.getColumnValue(3) === null ? null : String(rs.getColumnValue(3)),
      department_section_code: rs.getColumnValue(4) === null ? null : String(rs.getColumnValue(4)),
      department_code: rs.getColumnValue(5) === null ? null : String(rs.getColumnValue(5)),
      section_code: rs.getColumnValue(6) === null ? null : String(rs.getColumnValue(6)),
      group_code: rs.getColumnValue(7) === null ? null : String(rs.getColumnValue(7)),
      name_full: rs.getColumnValue(8),
      name_short: rs.getColumnValue(9)
    });
  }

  return {
    ok: true,
    next: "aggregate",
    fiscal_year: fy,
    resolved: {
      department_id: root_department_id,
      department_category: category,
      division_code: divisionCode,
      department_section_code: deptSectionCode,
      headquarters_code: hqCode,
      general_department_code: genCode,
      name_full: nameFull,
      name_short: nameShort
    },
    scope: {
      include_self: includeSelf,
      department_ids: ids,
      count: ids.length,
      members: members
    }
  };

} catch (err) {
  return { ok:false, next:"error", message:String(err), stack: err && err.stack ? String(err.stack) : null };
}
$$;
```

