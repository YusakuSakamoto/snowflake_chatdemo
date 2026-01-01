---
type: other
schema_id: SCH_20251225131727
physical: NORMALIZE_JA
object_type: function
comment: RAWデータ格納用ステージ
---

# SQL
```sql
create or replace function APP_PRODUCTION.NORMALIZE_JA(s string)
returns string
language javascript
as
$$
  // Snowflake JavaScript UDF は arguments[0] を使う
  var s0 = arguments[0];
  if (s0 === null) return null;
  let t = String(s0);
  t = t.normalize("NFKC");
  t = t.trim();
  t = t.toLowerCase();
  t = t.replace(
    /(株式会社|有限会社|合同会社|（株）|\(株\)|㈱|（有）|\(有\)|㈲|（同）|\(同\)|inc\.?|llc|ltd\.?|co\.?|company|limited)/gi,
    ""
  );
  t = t.replace(/[\s\u3000]+/g, "");
  t = t.replace(
    /[()\[\]{}<>「」『』【】（）・,，．.／\/\\\-＿_―ー…:：;；!！?？'"“”‘’&＋+*＝=]/g,
    ""
  );
  t = t.replace(/[\u3041-\u3096]/g, function (ch) {
    return String.fromCharCode(ch.charCodeAt(0) + 0x60);
  });
  t = t.replace(/第(\d+)期/g, "$1期");
  t = t.replace(/ー{2,}/g, "ー");
  t = t.trim();
  return t;
$$;
```

